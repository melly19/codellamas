from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, task, crew
from crewai.tools import BaseTool

from codellamas_backend.runtime.verifier import MavenVerifier, to_filelikes

# =========================
# Shared models
# =========================

class ProjectFile(BaseModel):
    path: str = Field(..., description="Relative path (e.g., src/main/java/... or pom.xml)")
    content: str


class SpringBootExercise(BaseModel):
    problem_description: str
    project_files: List[ProjectFile]
    test_files: List[ProjectFile]
    reference_solution_markdown: str


class PatchOutput(BaseModel):
    """Debug/patch agent output."""
    project_files: List[ProjectFile] = Field(default_factory=list)
    test_files: List[ProjectFile] = Field(default_factory=list)
    reference_solution_markdown: str = ""


class VerifyToolInput(BaseModel):
    """
    Minimal runtime inputs for verification.
    IMPORTANT: `base_project_files` must be the Spring Initializr scaffold.
    """
    base_project_files: List[ProjectFile]
    override_project_files: List[ProjectFile] = Field(default_factory=list)
    injected_tests: List[ProjectFile] = Field(default_factory=list)
    timeout_sec: int = 180


class VerifyToolOutput(BaseModel):
    status: str
    failed_tests: List[str]
    errors: List[str]
    raw_log_head: str

# =========================
# Tool: Maven verifier wrapped as a CrewAI tool
# =========================

class MavenVerifyTool(BaseTool):
    name: str = "maven_verify"
    description: str = (
        "Runs mvn test in an isolated workspace (includes compilation) and returns PASS/FAIL plus a log head."
    )
    args_schema: Type[BaseModel] = VerifyToolInput

    def _run(
        self,
        base_project_files: List[Dict[str, str]],
        override_project_files: Optional[List[Dict[str, str]]] = None,
        injected_tests: Optional[List[Dict[str, str]]] = None,
        timeout_sec: int = 180,
    ) -> str:
        override_project_files = override_project_files or []
        injected_tests = injected_tests or []

        base_pf = [ProjectFile(path=f["path"], content=f["content"]) for f in base_project_files]
        override_pf = [ProjectFile(path=f["path"], content=f["content"]) for f in override_project_files]
        test_pf = [ProjectFile(path=f["path"], content=f["content"]) for f in injected_tests]

        verifier = MavenVerifier(timeout_sec=timeout_sec, quiet=True)
        verification = verifier.verify(
            base_project=to_filelikes(base_pf),
            override_files=to_filelikes(override_pf),
            injected_tests={f.path: f.content for f in test_pf},
        )

        out = VerifyToolOutput(
            status=verification.status,
            failed_tests=verification.failed_tests,
            errors=verification.errors,
            raw_log_head=verification.summary()[:2000],
        )

        return out.model_dump_json()

@CrewBase
class CodellamasBackendMulti:

    agents_config = "../config/agents_multi.yaml"
    tasks_config = "../config/tasks_multi.yaml"

    request_timeout_sec: int = 1800
    maven_timeout_sec: int = 180
    max_patch_iters: int = 2

    def __init__(self):
        self.llm = LLM(
            model="ollama/phi4",
            base_url="http://localhost:11434",
            request_timeout=self.request_timeout_sec,
        )

        # Single tool instance is fine
        self.verify_tool = MavenVerifyTool()

    @agent
    def problem_architect(self) -> Agent:
        return Agent(
            config=self.agents_config['problem_architect'],
            verbose=True
        )

    @agent
    def test_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['test_engineer'],
            verbose=True
        )

    @agent
    def smelly_developer(self) -> Agent:
        return Agent(
            config=self.agents_config['smelly_developer'],
            verbose=True
        )

    @agent
    def reference_solution_developer(self) -> Agent:
        return Agent(
            config=self.agents_config['reference_solution_developer'],
            verbose=True
        )

    @agent
    def test_runner(self) -> Agent:
        return Agent(
            config=self.agents_config['test_runner'],
            verbose=True,
            tools=[self.verify_tool]
        )

    @agent
    def debug_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['debug_specialist'],
            verbose=True
        )

    @agent
    def quality_assurance(self) -> Agent:
        return Agent(
            config=self.agents_config['quality_assurance'],
            verbose=True
        )

    # -------------------------
    # Tasks (same stage set as other-branch)
    # -------------------------

    @task
    def define_problem(self) -> Task:
        return Task(
            config=self.tasks_config['define_problem'],
            agent=self.problem_architect()
        )

    @task
    def define_tests(self) -> Task:
        return Task(
            config=self.tasks_config['define_tests'],
            agent=self.test_engineer()
        )


    @task
    def implement_smelly_code(self) -> Task:
        return Task(
            config=self.tasks_config['implement_smelly_code'],
            agent=self.smelly_developer()
        )


    @task
    def run_tests_on_smelly_code(self) -> Task:
        return Task(
            config=self.tasks_config['run_tests_on_smelly_code'],
            agent=self.test_runner()
        )

    @task
    def patch_smelly_code(self) -> Task:
        return Task(
            config=self.tasks_config['patch_smelly_code'],
            agent=self.debug_specialist(),
            output_json=PatchOutput
        )

    @task
    def generate_reference_solution(self) -> Task:
        return Task(
            config=self.tasks_config['generate_reference_solution'],
            agent=self.reference_solution_developer(),
            output_json=PatchOutput
        )

    @task
    def run_tests_on_reference_solution(self) -> Task:
        return Task(
            config=self.tasks_config['run_tests_on_reference_solution'],
            agent=self.test_runner()
        )

    @task
    def patch_reference_solution(self) -> Task:
        return Task(
            config=self.tasks_config['patch_reference_solution'],
            agent=self.debug_specialist(),
            output_json=PatchOutput
        )

    @task
    def audit_exercise(self) -> Task:
        return Task(
            config=self.tasks_config['audit_exercise'],
            agent=self.quality_assurance(),
            output_json=SpringBootExercise
        )

    @task
    def check_functional_correctness(self) -> Task:
        return Task(
            config=self.tasks_config['check_functional_correctness'],
            agent=self.test_runner()
        )

    @task
    def evaluate_code_quality(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_code_quality'],
            agent=self.quality_assurance()
        )

    @task
    def generate_review_feedback(self) -> Task:
        return Task(
            config=self.tasks_config['generate_review_feedback'],
            agent=self.quality_assurance()
        )

    @crew
    def generation_crew(self) -> Crew:
        return Crew(
            agents=[
                self.problem_architect(),
                self.test_engineer(),
                self.smelly_developer(),
                self.test_runner(),
                self.debug_specialist(),
                self.reference_solution_developer(),
                self.quality_assurance(),
            ],
            tasks=[
                self.define_problem(),
                self.define_tests(),
                self.implement_smelly_code(),
                self.run_tests_on_smelly_code(),
                self.patch_smelly_code(),
                self.generate_reference_solution(),
                self.run_tests_on_reference_solution(),
                self.patch_reference_solution(),
                self.audit_exercise(),
            ],
            process=Process.sequential,
            verbose=True,
        )

    @crew
    def review_crew(self) -> Crew:
        return Crew(
            agents=[
                self.test_runner(),
                self.quality_assurance(),
            ],
            tasks=[
                self.check_functional_correctness(),
                self.evaluate_code_quality(),
                self.generate_review_feedback(),
            ],
            process=Process.sequential,
            verbose=True,
        )

    # -------------------------
    # Optional: reliable Python fix-loop using verifier (recommended)
    # -------------------------

    def generate_with_fix_loop(
        self,
        *,
        topic: str,
        code_smells: List[str],
        existing_codebase: str,
        project_files: List[Any],  # scaffold from API (ProjectFile-like)
    ) -> tuple[SpringBootExercise, Dict[str, Any]]:
        """
        A simpler + more reliable implementation of the same stage functionality as generation_crew,
        but with deterministic verification + patching loops in Python.

        Use this from api.py when:
          mode == "multi" AND verify_maven == True AND project_files provided
        """
        base_project_files = [ProjectFile(path=f.path, content=f.content) for f in project_files]
        base_filelikes = to_filelikes(base_project_files)

        meta: Dict[str, Any] = {
            "mode": "multi",
            "fix_loop": True,
            "smelly_iterations": 0,
            "reference_iterations": 0,
            "smelly_maven": None,
            "reference_maven": None,
        }

        # 1) One-shot for initial exercise artifacts
        kickoff = self.implement_smelly_code().agent  # for clarity: we just kickoff a small crew
        initial = Crew(
            agents=[self.problem_architect(), self.test_engineer(), self.smelly_developer()],
            tasks=[self.define_problem(), self.define_tests(), self.implement_smelly_code()],
            process=Process.sequential,
            verbose=True,
        ).kickoff(inputs={"topic": topic, "code_smells": code_smells, "existing_codebase": existing_codebase})

        exercise = SpringBootExercise(**initial.json_dict)

        # 2) Verify + patch smelly
        for i in range(1, self.max_patch_iters + 1):
            meta["smelly_iterations"] = i
            ver = MavenVerifier(timeout_sec=self.maven_timeout_sec, quiet=True).verify(
                base_project=base_filelikes,
                override_files=to_filelikes(exercise.project_files),
                injected_tests={t.path: t.content for t in exercise.test_files},
            )
            meta["smelly_maven"] = {
                "status": ver.status,
                "failed_tests": ver.failed_tests,
                "errors": ver.errors,
                "raw_log_head": ver.summary()[:2000],
            }
            if ver.status == "PASS":
                break

            patch = Crew(
                agents=[self.debug_specialist()],
                tasks=[self.patch_smelly_code()],
                process=Process.sequential,
                verbose=True,
            ).kickoff(inputs={
                "maven_log_head": ver.summary()[:2000],
                "smelly_project_files": [p.model_dump() for p in exercise.project_files],
                "test_files": [t.model_dump() for t in exercise.test_files],
            })
            p = PatchOutput(**patch.json_dict)
            if p.project_files:
                exercise.project_files = p.project_files
            if p.test_files:
                exercise.test_files = p.test_files

        # 3) Generate reference solution
        ref = Crew(
            agents=[self.reference_solution_developer()],
            tasks=[self.generate_reference_solution()],
            process=Process.sequential,
            verbose=True,
        ).kickoff(inputs={
            "problem_description": exercise.problem_description,
            "smelly_project_files": [p.model_dump() for p in exercise.project_files],
            "test_files": [t.model_dump() for t in exercise.test_files],
        })
        ref_patch = PatchOutput(**ref.json_dict)
        reference_project_files = ref_patch.project_files or exercise.project_files
        reference_test_files = ref_patch.test_files or exercise.test_files
        reference_md = ref_patch.reference_solution_markdown or exercise.reference_solution_markdown

        # 4) Verify + patch reference
        for i in range(1, self.max_patch_iters + 1):
            meta["reference_iterations"] = i
            ver = MavenVerifier(timeout_sec=self.maven_timeout_sec, quiet=True).verify(
                base_project=base_filelikes,
                override_files=to_filelikes(reference_project_files),
                injected_tests={t.path: t.content for t in reference_test_files},
            )
            meta["reference_maven"] = {
                "status": ver.status,
                "failed_tests": ver.failed_tests,
                "errors": ver.errors,
                "raw_log_head": ver.summary()[:2000],
            }
            if ver.status == "PASS":
                break

            patch = Crew(
                agents=[self.debug_specialist()],
                tasks=[self.patch_reference_solution()],
                process=Process.sequential,
                verbose=True,
            ).kickoff(inputs={
                "maven_log_head": ver.summary()[:2000],
                "reference_project_files": [p.model_dump() for p in reference_project_files],
                "reference_test_files": [t.model_dump() for t in reference_test_files],
                "reference_solution_markdown": reference_md,
            })
            p = PatchOutput(**patch.json_dict)
            if p.project_files:
                reference_project_files = p.project_files
            if p.test_files:
                reference_test_files = p.test_files
            if p.reference_solution_markdown.strip():
                reference_md = p.reference_solution_markdown

        # 5) Audit + package final
        audited = Crew(
            agents=[self.quality_assurance()],
            tasks=[self.audit_exercise()],
            process=Process.sequential,
            verbose=True,
        ).kickoff(inputs={
            "problem_description": exercise.problem_description,
            "smelly_project_files": [p.model_dump() for p in exercise.project_files],
            "test_files": [t.model_dump() for t in exercise.test_files],
            "reference_solution_markdown": reference_md,
        })

        final_exercise = SpringBootExercise(**audited.json_dict)
        return final_exercise, meta