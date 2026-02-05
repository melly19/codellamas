from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from crewai import Agent, Crew, Process, Task, LLM

from codellamas_backend.runtime.verifier import MavenVerifier, to_filelikes


# =========================
# Shared output models
# =========================

class ProjectFile(BaseModel):
    path: str = Field(..., description="Relative file path (e.g., src/main/java/... or pom.xml)")
    content: str


class SpringBootExercise(BaseModel):
    problem_description: str
    project_files: List[ProjectFile]
    test_files: List[ProjectFile]
    reference_solution_markdown: str


class PatchOutput(BaseModel):
    """
    Fixer output: can update code files and/or tests. Keep it simple:
    - Provide full updated project_files and test_files (not diffs)
    - reference_solution_markdown may be updated if needed
    """
    project_files: List[ProjectFile] = Field(default_factory=list)
    test_files: List[ProjectFile] = Field(default_factory=list)
    reference_solution_markdown: str = ""


# =========================
# Multi-agent backend with fix loop
# =========================

class CodellamasBackendMulti:
    """
    Multi-agent backend. Provides:
    - generation_crew(): basic multi-agent one-shot crew
    - review_crew(): review crew
    - generate_with_fix_loop(): Python-orchestrated multi-agent loop with MavenVerifier
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model: str = "ollama/phi4",
        max_iters: int = 3,
        maven_timeout_sec: int = 180,
    ):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.max_iters = max_iters
        self.maven_timeout_sec = maven_timeout_sec

        self.llm = LLM(model=self.model, base_url=self.ollama_base_url)

        # Runtime verifier (ground truth)
        self.verifier = MavenVerifier(timeout_sec=self.maven_timeout_sec, quiet=True)

    # -------------------------
    # Agents (programmatic; no YAML)
    # -------------------------

    def _problem_agent(self) -> Agent:
        return Agent(
            role="Problem Designer",
            goal="Design a small Spring Boot exercise domain and constraints.",
            backstory="You create realistic student-level refactoring exercises with clear requirements.",
            llm=self.llm,
            verbose=True,
        )

    def _test_agent(self) -> Agent:
        return Agent(
            role="Test Author",
            goal="Write JUnit 5 tests defining expected behavior that must remain unchanged after refactoring.",
            backstory="You write concise, deterministic unit tests for Java code without external services.",
            llm=self.llm,
            verbose=True,
        )

    def _solution_agent(self) -> Agent:
        return Agent(
            role="Exercise Generator",
            goal="Produce a small Spring Boot codebase containing the requested smells, plus a refactored reference solution.",
            backstory="You generate 2–4 classes with intentional smells and provide clean refactoring.",
            llm=self.llm,
            verbose=True,
        )

    def _fixer_agent(self) -> Agent:
        return Agent(
            role="Bug Fixer",
            goal="Fix compilation/test failures while preserving intended behavior and keeping the smells/refactoring objectives.",
            backstory="You patch Java code/tests based on Maven logs. You do not invent dependencies or external services.",
            llm=self.llm,
            verbose=True,
        )

    def _review_agent(self) -> Agent:
        return Agent(
            role="Reviewer",
            goal="Provide concise feedback on student solutions relative to smells and tests.",
            backstory="You assess refactoring quality and correctness at undergraduate level.",
            llm=self.llm,
            verbose=True,
        )

    # -------------------------
    # Crews (one-shot mode)
    # -------------------------

    def generation_crew(self) -> Crew:
        """
        Basic multi-agent pipeline without execution loop.
        Keeps compatibility with existing api.py routing for multi-mode if verify_maven=false.
        """
        problem_task = Task(
            description=(
                "Design a refactoring exercise scenario.\n"
                "Inputs:\n"
                "- topic: {topic}\n"
                "- code_smells: {code_smells}\n"
                "- existing_codebase: {existing_codebase}\n"
                "Output: a clear problem description and constraints.\n"
            ),
            agent=self._problem_agent(),
        )

        tests_task = Task(
            description=(
                "Write JUnit 5 tests for the described behavior.\n"
                "Inputs:\n"
                "- topic: {topic}\n"
                "- code_smells: {code_smells}\n"
                "- existing_codebase: {existing_codebase}\n"
                "Output: tests requirements and test code ideas.\n"
            ),
            agent=self._test_agent(),
        )

        solution_task = Task(
            description=(
                "Generate the full exercise artifacts.\n"
                "Inputs:\n"
                "- topic: {topic}\n"
                "- code_smells: {code_smells}\n"
                "- existing_codebase: {existing_codebase}\n"
                "Return a SpringBootExercise object.\n"
            ),
            agent=self._solution_agent(),
            output_json=SpringBootExercise,
        )

        return Crew(
            agents=[self._problem_agent(), self._test_agent(), self._solution_agent()],
            tasks=[problem_task, tests_task, solution_task],
            process=Process.sequential,
            verbose=True,
        )

    def review_crew(self) -> Crew:
        review_task = Task(
            description=(
                "Review the student submission.\n"
                "Inputs:\n"
                "- problem_description: {problem_description}\n"
                "- original_code: {original_code}\n"
                "- student_code: {student_code}\n"
                "- test_results: {test_results}\n"
                "- reference_solution: {reference_solution}\n"
                "- code_smells: {code_smells}\n"
            ),
            agent=self._review_agent(),
        )
        return Crew(
            agents=[self._review_agent()],
            tasks=[review_task],
            process=Process.sequential,
            verbose=True,
        )

    # -------------------------
    # Fix-loop (Python orchestration)
    # -------------------------

    def generate_with_fix_loop(
        self,
        *,
        topic: str,
        code_smells: List[str],
        existing_codebase: str,
        project_files: List[Any],  # accepts your Pydantic ProjectFile objects from api.py
        max_iters: Optional[int] = None,
    ) -> Tuple[SpringBootExercise, Dict[str, Any]]:
        """
        Orchestrates:
        1) multi-agent generation
        2) mvn test verify
        3) if fail => fixer agent patches artifacts
        4) repeat up to max_iters

        Returns:
          (exercise_data, meta)
        """
        max_iters = max_iters or self.max_iters

        # Step 1: initial generation (one-shot crew)
        crew = self.generation_crew()
        kickoff_result = crew.kickoff(inputs={
            "topic": topic,
            "code_smells": code_smells,
            "existing_codebase": existing_codebase,
        })

        # CrewAI returns an object; SpringBootExercise is in kickoff_result.json_dict if output_json is used.
        exercise = SpringBootExercise(**kickoff_result.json_dict)

        # Prepare base scaffold and run verifier
        base_project = to_filelikes(project_files)

        meta: Dict[str, Any] = {
            "mode": "multi",
            "fix_loop": True,
            "iterations": 0,
            "maven": None,
        }

        def _exercise_to_override_files(ex: SpringBootExercise):
            return to_filelikes(ex.project_files)

        def _exercise_tests_dict(ex: SpringBootExercise) -> Dict[str, str]:
            return {f.path: f.content for f in ex.test_files}

        # Loop
        for i in range(1, max_iters + 1):
            meta["iterations"] = i

            verification = self.verifier.verify(
                base_project=base_project,
                override_files=_exercise_to_override_files(exercise),
                injected_tests=_exercise_tests_dict(exercise),
            )

            meta["maven"] = {
                "status": verification.status,
                "failed_tests": verification.failed_tests,
                "errors": verification.errors,
                "raw_log_head": verification.summary(),
            }

            if verification.status == "PASS":
                return exercise, meta

            # Step: Fix once based on logs
            fix_task = Task(
                description=(
                    "You must fix compilation/test failures based on Maven output.\n\n"
                    "INPUTS:\n"
                    f"- topic: {topic}\n"
                    f"- code_smells: {code_smells}\n"
                    f"- existing_codebase: {existing_codebase}\n\n"
                    "CURRENT ARTIFACTS:\n"
                    f"- problem_description:\n{exercise.problem_description}\n\n"
                    f"- reference_solution_markdown:\n{exercise.reference_solution_markdown}\n\n"
                    "CURRENT PROJECT FILES (path then content):\n"
                    + "\n".join([f"\n### {pf.path}\n{pf.content}" for pf in exercise.project_files])
                    + "\n\nCURRENT TEST FILES (path then content):\n"
                    + "\n".join([f"\n### {tf.path}\n{tf.content}" for tf in exercise.test_files])
                    + "\n\nMAVEN OUTPUT (HEAD):\n"
                    + verification.summary()
                    + "\n\nTASK:\n"
                      "- Update project_files and/or test_files so that `mvn test` passes.\n"
                      "- Do NOT add external dependencies.\n"
                      "- Keep scope small (2–4 classes + tests).\n"
                      "- Preserve intended behavior.\n"
                      "- Return full updated artifacts (not diffs).\n"
                ),
                agent=self._fixer_agent(),
                output_json=PatchOutput,
            )

            fix_crew = Crew(
                agents=[self._fixer_agent()],
                tasks=[fix_task],
                process=Process.sequential,
                verbose=True,
            )

            fix_result = fix_crew.kickoff(inputs={})
            patch = PatchOutput(**fix_result.json_dict)

            # Apply patch (only replace if provided; otherwise keep old)
            if patch.project_files:
                exercise.project_files = patch.project_files
            if patch.test_files:
                exercise.test_files = patch.test_files
            if patch.reference_solution_markdown.strip():
                exercise.reference_solution_markdown = patch.reference_solution_markdown

        # If still failing after max_iters, return last attempt + meta
        meta["note"] = f"Reached max fix iterations ({max_iters}) without PASS."
        return exercise, meta
