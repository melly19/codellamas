from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, task, crew
from crewai.tools import BaseTool

from codellamas_backend.runtime.verifier import MavenVerifier
from codellamas_backend.schemas.files import ProjectFile


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openrouter/qwen/qwen3-coder-30b-a3b-instruct"


class SpringBootExercise(BaseModel):
    problem_description: str
    project_files: List[ProjectFile]
    test_files: List[ProjectFile]
    solution_explanation_md: str
    paths_to_ex: List[str] = Field(default_factory=list)
    answers_list: List[ProjectFile] = Field(default_factory=list)


class VerifyToolInput(BaseModel):
    base_project_files: List[ProjectFile]
    override_project_files: List[ProjectFile] = Field(default_factory=list)
    injected_tests: List[ProjectFile] = Field(default_factory=list)
    timeout_sec: int = 180


class VerifyToolOutput(BaseModel):
    status: str
    failed_tests: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    raw_log_head: str = ""


class MavenVerifyTool(BaseTool):
    name: str = "maven_verify"
    description: str = (
        "Runs mvn test in an isolated workspace and returns PASS/FAIL plus diagnostics."
    )
    args_schema: Type[BaseModel] = VerifyToolInput

    def _normalize_files(self, items: Optional[List[Any]]) -> List[ProjectFile]:
        out: List[ProjectFile] = []
        for item in items or []:
            if isinstance(item, ProjectFile):
                out.append(item)
            elif isinstance(item, dict):
                try:
                    out.append(ProjectFile(**item))
                except Exception:
                    pass
        return out

    def _run(
        self,
        base_project_files: List[ProjectFile],
        override_project_files: Optional[List[ProjectFile]] = None,
        injected_tests: Optional[List[ProjectFile]] = None,
        timeout_sec: int = 180,
    ) -> str:
        base_project_files = self._normalize_files(base_project_files)
        override_project_files = self._normalize_files(override_project_files)
        injected_tests = self._normalize_files(injected_tests)

        if not base_project_files:
            return VerifyToolOutput(
                status="SKIPPED",
                failed_tests=[],
                errors=["No base_project_files provided."],
                raw_log_head="",
            ).model_dump_json()

        verifier = MavenVerifier(timeout_sec=timeout_sec, quiet=True)
        verification = verifier.verify(
            base_project=base_project_files,
            override_files=override_project_files,
            injected_tests={f.path: f.content for f in injected_tests},
        )

        return VerifyToolOutput(
            status=verification.status,
            failed_tests=verification.failed_tests,
            errors=verification.errors,
            raw_log_head=verification.summary()[:2000],
        ).model_dump_json()


@CrewBase
class CodellamasBackendMulti:
    agents_config = "../config/agents_multi.yaml"
    tasks_config = "../config/tasks_multi.yaml"

    request_timeout_sec: int = 1800
    maven_timeout_sec: int = 180
    max_patch_iters: int = 2

    def __init__(self, model_name: str = None, api_endpoint: str = None, api_key: str = None):
        self.model_name = model_name or MODEL
        self.api_endpoint = api_endpoint or BASE_URL
        self.api_key = api_key or OPENROUTER_API_KEY
        self.llm = LLM(
            model=self.model_name,
            base_url=self.api_endpoint,
            api_key=self.api_key,
            request_timeout=self.request_timeout_sec,
            max_tokens=30000,
        )
        self.verify_tool = MavenVerifyTool()

    def _to_project_files(self, items: Optional[List[Any]]) -> List[ProjectFile]:
        out: List[ProjectFile] = []
        for item in items or []:
            if isinstance(item, ProjectFile):
                out.append(item)
            elif isinstance(item, dict):
                out.append(ProjectFile(**item))
            else:
                out.append(ProjectFile(path=item.path, content=item.content))
        return out

    def _exercise_from_result(self, result: Any) -> SpringBootExercise:
        return SpringBootExercise(**result.json_dict)

    def _verify(
        self,
        *,
        base_project_files: List[ProjectFile],
        override_project_files: List[ProjectFile],
        injected_tests: List[ProjectFile],
    ) -> VerifyToolOutput:
        verification = MavenVerifier(timeout_sec=self.maven_timeout_sec, quiet=True).verify(
            base_project=base_project_files,
            override_files=override_project_files,
            injected_tests={t.path: t.content for t in injected_tests},
        )
        return VerifyToolOutput(
            status=verification.status,
            failed_tests=verification.failed_tests,
            errors=verification.errors,
            raw_log_head=verification.summary()[:2000],
        )

    def _merge_exercise(
        self,
        current: SpringBootExercise,
        updated: SpringBootExercise,
        *,
        prefer_updated_answers: bool = True,
    ) -> SpringBootExercise:
        return SpringBootExercise(
            problem_description=current.problem_description or updated.problem_description,
            project_files=updated.project_files or current.project_files,
            test_files=updated.test_files or current.test_files,
            solution_explanation_md=updated.solution_explanation_md or current.solution_explanation_md,
            paths_to_ex=updated.paths_to_ex or current.paths_to_ex,
            answers_list=(
                updated.answers_list
                if (prefer_updated_answers and updated.answers_list is not None)
                else current.answers_list
            )
            or current.answers_list,
        )

    def _run_single_task_crew(self, task_obj: Task, agent_obj: Agent, inputs: Dict[str, Any]) -> Any:
        return Crew(
            agents=[agent_obj],
            tasks=[task_obj],
            process=Process.sequential,
            verbose=True,
        ).kickoff(inputs=inputs)

    def _build_reference_override_files(
        self,
        *,
        project_files: List[ProjectFile],
        answers_list: List[ProjectFile],
        paths_to_ex: List[str],
    ) -> List[ProjectFile]:
        normalized_project_files = self._to_project_files(project_files)
        normalized_answers = self._to_project_files(answers_list)

        if not normalized_answers:
            return normalized_project_files

        project_by_path: Dict[str, ProjectFile] = {f.path: f for f in normalized_project_files}
        filename_to_paths: Dict[str, List[str]] = {}
        for f in normalized_project_files:
            filename_to_paths.setdefault(os.path.basename(f.path), []).append(f.path)

        editable_paths = set(paths_to_ex or [])

        for answer in normalized_answers:
            answer_path = answer.path

            if answer_path in project_by_path:
                project_by_path[answer_path] = answer
                continue

            if answer_path == "pom.xml":
                project_by_path["pom.xml"] = ProjectFile(path="pom.xml", content=answer.content)
                continue

            basename = os.path.basename(answer_path)
            candidate_paths = filename_to_paths.get(basename, [])
            preferred_candidates = [p for p in candidate_paths if p in editable_paths]
            chosen_path = None

            if len(preferred_candidates) == 1:
                chosen_path = preferred_candidates[0]
            elif len(candidate_paths) == 1:
                chosen_path = candidate_paths[0]

            if chosen_path:
                project_by_path[chosen_path] = ProjectFile(path=chosen_path, content=answer.content)
            else:
                project_by_path[answer_path] = answer

        return list(project_by_path.values())

    def _exercise_json(self, exercise: SpringBootExercise) -> str:
        return exercise.model_dump_json(indent=2)

    def _verifier_json(self, verification: VerifyToolOutput) -> str:
        return verification.model_dump_json(indent=2)

    @agent
    def problem_architect(self) -> Agent:
        return Agent(config=self.agents_config["problem_architect"], llm=self.llm, timeout="1800s", verbose=True)

    @agent
    def test_engineer(self) -> Agent:
        return Agent(config=self.agents_config["test_engineer"], llm=self.llm, timeout="1800s", verbose=True)

    @agent
    def smelly_developer(self) -> Agent:
        return Agent(config=self.agents_config["smelly_developer"], llm=self.llm, timeout="1800s", verbose=True)

    @agent
    def answers_list_developer(self) -> Agent:
        return Agent(config=self.agents_config["answers_list_developer"], llm=self.llm, timeout="1800s", verbose=True)

    @agent
    def test_runner(self) -> Agent:
        return Agent(
            config=self.agents_config["test_runner"],
            llm=self.llm,
            timeout="1800s",
            verbose=True,
            tools=[self.verify_tool],
        )

    @agent
    def debug_specialist(self) -> Agent:
        return Agent(config=self.agents_config["debug_specialist"], llm=self.llm, timeout="1800s", verbose=True)

    @agent
    def quality_assurance(self) -> Agent:
        return Agent(config=self.agents_config["quality_assurance"], llm=self.llm, timeout="1800s", verbose=True)

    @task
    def define_problem(self) -> Task:
        return Task(config=self.tasks_config["define_problem"], agent=self.problem_architect())

    @task
    def define_tests(self) -> Task:
        return Task(config=self.tasks_config["define_tests"], agent=self.test_engineer())

    @task
    def implement_smelly_code(self) -> Task:
        return Task(
            config=self.tasks_config["implement_smelly_code"],
            agent=self.smelly_developer(),
            output_json=SpringBootExercise,
        )

    @task
    def patch_smelly_code(self) -> Task:
        return Task(
            config=self.tasks_config["patch_smelly_code"],
            agent=self.debug_specialist(),
            output_json=SpringBootExercise,
        )

    @task
    def generate_answers_list(self) -> Task:
        return Task(
            config=self.tasks_config["generate_answers_list"],
            agent=self.answers_list_developer(),
            output_json=SpringBootExercise,
        )

    @task
    def patch_answers_list(self) -> Task:
        return Task(
            config=self.tasks_config["patch_answers_list"],
            agent=self.debug_specialist(),
            output_json=SpringBootExercise,
        )

    @task
    def audit_exercise(self) -> Task:
        return Task(
            config=self.tasks_config["audit_exercise"],
            agent=self.quality_assurance(),
            output_json=SpringBootExercise,
        )

    @crew
    def generation_crew(self) -> Crew:
        return Crew(
            agents=[self.problem_architect(), self.test_engineer(), self.smelly_developer()],
            tasks=[self.define_problem(), self.define_tests(), self.implement_smelly_code()],
            process=Process.sequential,
            verbose=True,
        )

    def generate_with_fix_loop(
        self,
        *,
        topic: str,
        code_smells: List[str],
        existing_codebase: str,
        project_files: List[Any],
    ) -> tuple[SpringBootExercise, Dict[str, Any]]:
        base_project_files = self._to_project_files(project_files)

        meta: Dict[str, Any] = {
            "mode": "multi",
            "fix_loop": True,
            "smelly_iterations": 0,
            "reference_iterations": 0,
            "smelly_maven": None,
            "reference_maven": None,
        }

        initial_result = Crew(
            agents=[self.problem_architect(), self.test_engineer(), self.smelly_developer()],
            tasks=[self.define_problem(), self.define_tests(), self.implement_smelly_code()],
            process=Process.sequential,
            verbose=True,
        ).kickoff(
            inputs={
                "topic": topic,
                "code_smells": code_smells,
                "existing_codebase": existing_codebase,
            }
        )

        exercise = self._exercise_from_result(initial_result)

        for i in range(1, self.max_patch_iters + 1):
            meta["smelly_iterations"] = i

            verification = self._verify(
                base_project_files=base_project_files,
                override_project_files=exercise.project_files,
                injected_tests=exercise.test_files,
            )
            meta["smelly_maven"] = verification.model_dump()

            if verification.status == "PASS":
                break

            patched_result = self._run_single_task_crew(
                self.patch_smelly_code(),
                self.debug_specialist(),
                inputs={
                    "topic": topic,
                    "code_smells": code_smells,
                    "existing_codebase": existing_codebase,
                    "exercise_json": self._exercise_json(exercise),
                    "verifier_json": self._verifier_json(verification),
                },
            )
            patched_exercise = self._exercise_from_result(patched_result)
            exercise = self._merge_exercise(exercise, patched_exercise, prefer_updated_answers=False)

        ref_result = self._run_single_task_crew(
            self.generate_answers_list(),
            self.answers_list_developer(),
            inputs={
                "topic": topic,
                "code_smells": code_smells,
                "existing_codebase": existing_codebase,
                "exercise_json": self._exercise_json(exercise),
            },
        )
        exercise = self._merge_exercise(exercise, self._exercise_from_result(ref_result))

        for i in range(1, self.max_patch_iters + 1):
            meta["reference_iterations"] = i

            reference_override_files = self._build_reference_override_files(
                project_files=exercise.project_files,
                answers_list=exercise.answers_list,
                paths_to_ex=exercise.paths_to_ex,
            )

            verification = self._verify(
                base_project_files=base_project_files,
                override_project_files=reference_override_files,
                injected_tests=exercise.test_files,
            )
            meta["reference_maven"] = verification.model_dump()

            if verification.status == "PASS":
                break

            patched_result = self._run_single_task_crew(
                self.patch_answers_list(),
                self.debug_specialist(),
                inputs={
                    "topic": topic,
                    "code_smells": code_smells,
                    "existing_codebase": existing_codebase,
                    "exercise_json": self._exercise_json(exercise),
                    "verifier_json": self._verifier_json(verification),
                },
            )
            patched_exercise = self._exercise_from_result(patched_result)
            exercise = self._merge_exercise(exercise, patched_exercise)

        audited_result = self._run_single_task_crew(
            self.audit_exercise(),
            self.quality_assurance(),
            inputs={
                "topic": topic,
                "code_smells": code_smells,
                "existing_codebase": existing_codebase,
                "exercise_json": self._exercise_json(exercise),
            },
        )

        final_exercise = self._merge_exercise(exercise, self._exercise_from_result(audited_result))
        return final_exercise, meta
