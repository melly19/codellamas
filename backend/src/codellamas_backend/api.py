import os
import re
import logging
import datetime
import json
import csv
import time
import asyncio
from typing import List, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from codellamas_backend.crews.crew_single import (
    CodellamasBackend,
    SpringBootExercise,
    ContractSpec,
    ImplementationSpec,
)
from codellamas_backend.crews.crew_multi import CodellamasBackendMulti
from codellamas_backend.runtime.verifier import MavenVerifier
from codellamas_backend.schemas.files import ProjectFile


logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

app = FastAPI()
CSV_FILE_PATH = "output/exercises_evaluation.csv"
csv_write_lock = asyncio.Lock()
request_queue_counter = 0
request_current_turn = 0
write_condition = asyncio.Condition()

def get_backend(
    mode: str,
    model_name: str | None = None,
    api_endpoint: str | None = None,
    api_key: str | None = None,
):
    if mode not in {"single", "multi"}:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Use 'single' or 'multi'.",
        )
    return (
        CodellamasBackendMulti(model_name, api_endpoint, api_key)
        if mode == "multi"
        else CodellamasBackend(model_name, api_endpoint, api_key)
    )


class GenerateRequest(BaseModel):
    topic: str
    code_smells: List[str]
    existing_codebase: str = "NONE"
    mode: str = "single"
    count: int = 1
    verify_maven: bool = True
    project_files: List[ProjectFile] = Field(default_factory=list)
    model_name: str | None = None
    api_endpoint: str | None = None
    api_key: str | None = None


class EvaluateRequest(BaseModel):
    question_json: Dict[str, Any] = Field(default_factory=dict)
    student_code: List[ProjectFile] = Field(default_factory=list)
    code_smells: List[str]
    mode: str = "single"
    query: str = ""
    test_results: str = ""
    verify_maven: bool = False
    model_name: str | None = None
    api_endpoint: str | None = None
    api_key: str | None = None


def ingest_code_smells(code_smells: List[str]) -> str:
    return "None" if not code_smells else ", ".join(code_smells)


def append_to_csv(
    exercise: SpringBootExercise,
    topic: str,
    model: str,
    response_data: dict | None = None,
):
    try:
        os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "timestamp": timestamp,
            "topic": topic,
            "problem_description": exercise.problem_description,
            "single_or_multi": model,
            "response_json": json.dumps(response_data),
        }

        file_exists = os.path.isfile(CSV_FILE_PATH)

        with open(CSV_FILE_PATH, mode="a", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "timestamp",
                "topic",
                "problem_description",
                "single_or_multi",
                "response_json",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)

        return os.path.abspath(CSV_FILE_PATH)

    except Exception as e:
        print(f"Error appending to CSV: {e}")
        raise


def save_exercise_to_repo(exercise: SpringBootExercise, topic: str):
    timestamp = datetime.datetime.now().strftime("%d%m_%M%S")
    safe_topic = topic.replace(" ", "_")
    folder_name = f"{safe_topic}_{timestamp}"
    base_repo_dir = os.path.join(os.getcwd(), "generated_exercises", folder_name)
    os.makedirs(base_repo_dir, exist_ok=True)

    with open(os.path.join(base_repo_dir, "PROBLEM.md"), "w", encoding="utf-8") as f:
        f.write(exercise.problem_description)

    for file in exercise.project_files:
        full_path = os.path.join(base_repo_dir, file.path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(file.content)

    for file in exercise.test_files:
        full_path = os.path.join(base_repo_dir, file.path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(file.content)

    with open(os.path.join(base_repo_dir, "SOLUTION_EXP.md"), "w", encoding="utf-8") as f:
        f.write(exercise.solution_explanation_md)

    if exercise.answers_list:
        answers_dir = os.path.join(base_repo_dir, "answers")
        os.makedirs(answers_dir, exist_ok=True)
        for file in exercise.answers_list:
            full_path = os.path.join(answers_dir, file.path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(file.content)

    return base_repo_dir


def normalize_project_files(items: list) -> List[ProjectFile]:
    out: List[ProjectFile] = []
    for item in items or []:
        if isinstance(item, ProjectFile):
            out.append(item)
        elif isinstance(item, dict):
            out.append(ProjectFile(**item))
        else:
            raise TypeError(f"Invalid project file entry: {type(item)}")
    return out


def run_maven_verification(
    *,
    verify_maven: bool,
    project_files: List[ProjectFile],
    override_files: List[Any],
    injected_tests: List[Any],
    timeout_sec: int = 180,
    skipped_reason: str = "verify_maven=true but no project_files provided",
) -> Dict[str, Any]:
    maven_verification: Dict[str, Any] = {"enabled": False}

    if not verify_maven:
        return maven_verification

    maven_verification["enabled"] = True

    if not project_files:
        maven_verification.update({"status": "SKIPPED", "reason": skipped_reason})
        return maven_verification

    verifier = MavenVerifier(timeout_sec=timeout_sec, quiet=True)
    verification = verifier.verify(
        base_project=normalize_project_files(project_files),
        override_files=normalize_project_files(override_files or []),
        injected_tests={
            f.path: f.content for f in normalize_project_files(injected_tests or [])
        },
    )

    maven_verification.update(
        {
            "status": verification.status,
            "failed_tests": verification.failed_tests,
            "errors": verification.errors,
            "raw_log_head": verification.summary(),
        }
    )
    return maven_verification


def default_base_project_files() -> List[ProjectFile]:
    pom_xml = """<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>com.example</groupId>
  <artifactId>exercise</artifactId>
  <version>1.0-SNAPSHOT</version>
  <name>exercise</name>

  <properties>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <junit.jupiter.version>5.10.2</junit.jupiter.version>
  </properties>

  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>${junit.jupiter.version}</version>
      <scope>test</scope>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.2.5</version>
        <configuration>
          <useModulePath>false</useModulePath>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
"""
    return [ProjectFile(path="pom.xml", content=pom_xml)]


def build_solution_override_files(
    *,
    project_files: List[ProjectFile],
    answers_list: List[Any],
    paths_to_ex: List[str],
) -> List[ProjectFile]:
    normalized_answers = normalize_project_files(answers_list or [])
    if not normalized_answers:
        return []

    normalized_project_files = normalize_project_files(project_files or [])

    project_by_path: Dict[str, ProjectFile] = {
        f.path: f for f in normalized_project_files
    }
    filename_to_paths: Dict[str, List[str]] = {}
    for f in normalized_project_files:
        filename_to_paths.setdefault(os.path.basename(f.path), []).append(f.path)

    valid_paths = set(project_by_path.keys())
    editable_paths = set(paths_to_ex or [])

    resolved: Dict[str, ProjectFile] = {}

    for answer in normalized_answers:
        answer_path = answer.path

        if answer_path in valid_paths:
            resolved[answer_path] = answer
            continue

        if answer_path == "pom.xml":
            resolved["pom.xml"] = ProjectFile(path="pom.xml", content=answer.content)
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
            resolved[chosen_path] = ProjectFile(path=chosen_path, content=answer.content)
        else:
            resolved[answer_path] = answer

    return list(resolved.values())


def should_retry_single_generation(verification: Dict[str, Any]) -> bool:
    if not verification.get("enabled"):
        return False
    return verification.get("status") == "FAIL"


def build_maven_failure_context(label: str, verification: Dict[str, Any]) -> str:
    failed_tests = verification.get("failed_tests") or []
    errors = verification.get("errors") or []
    raw_log_head = verification.get("raw_log_head") or ""

    important_lines: List[str] = []
    for line in raw_log_head.splitlines():
        lowered = line.lower()
        if (
            "[error]" in lowered
            or "cannot find symbol" in lowered
            or "compilation error" in lowered
            or "failed to execute goal" in lowered
            or "assertionfailederror" in lowered
            or "expected:" in lowered
            or "but was:" in lowered
        ):
            important_lines.append(line)
        if len(important_lines) >= 10:
            break

    summary_lines = [
        f"{label} Maven verification failed.",
        f"Failed tests: {failed_tests[:5]}",
        f"Errors: {errors[:5]}",
    ]

    if important_lines:
        summary_lines.append("Important verifier lines:")
        summary_lines.extend(important_lines)

    return "\n".join(summary_lines)


def extract_package_decl(content: str) -> str | None:
    match = re.search(r"^\s*package\s+([a-zA-Z_][\w.]*)\s*;", content, re.MULTILINE)
    return match.group(1) if match else None


def expected_package_from_path(path: str, root_prefix: str) -> str | None:
    if not path.startswith(root_prefix) or not path.endswith(".java"):
        return None
    rel = path[len(root_prefix):]
    parts = rel.split("/")
    if len(parts) <= 1:
        return None
    package_parts = parts[:-1]
    return ".".join(package_parts) if package_parts else None


def validate_contract(contract: ContractSpec) -> List[str]:
    errors: List[str] = []

    if not contract.problem_description.strip():
        errors.append("problem_description is empty")

    if not contract.test_files:
        errors.append("test_files is empty")

    if not contract.paths_to_ex:
        errors.append("paths_to_ex is empty")

    for path in contract.paths_to_ex:
        if not path.startswith("src/main/java/") or not path.endswith(".java"):
            errors.append(f"paths_to_ex contains invalid path: {path}")

    seen_paths = set()
    for f in contract.test_files:
        if f.path in seen_paths:
            errors.append(f"duplicate test file path: {f.path}")
        seen_paths.add(f.path)

        if not f.path.startswith("src/test/java/") or not f.path.endswith(".java"):
            errors.append(f"invalid test file path: {f.path}")

        pkg = extract_package_decl(f.content)
        expected_pkg = expected_package_from_path(f.path, "src/test/java/")
        if pkg and expected_pkg and pkg != expected_pkg:
            errors.append(
                f"test file package mismatch: {f.path} declares package {pkg} but expected {expected_pkg}"
            )

    return errors


def validate_exercise_payload(exercise: SpringBootExercise) -> List[str]:
    errors: List[str] = []

    if not exercise.project_files:
        errors.append("project_files is empty")

    project_paths = [f.path for f in exercise.project_files]
    project_path_set = set(project_paths)

    if "pom.xml" not in project_path_set:
        errors.append("project_files must include pom.xml")

    if len(project_paths) != len(project_path_set):
        errors.append("project_files contains duplicate paths")

    if not exercise.answers_list:
        errors.append("answers_list is empty")

    for path in exercise.paths_to_ex:
        if path not in project_path_set:
            errors.append(f"paths_to_ex path not found in project_files: {path}")

    for f in exercise.project_files:
        if f.path == "pom.xml":
            continue
        if f.path.endswith(".java"):
            pkg = extract_package_decl(f.content)
            expected_pkg = None
            if f.path.startswith("src/main/java/"):
                expected_pkg = expected_package_from_path(f.path, "src/main/java/")
            elif f.path.startswith("src/test/java/"):
                expected_pkg = expected_package_from_path(f.path, "src/test/java/")
            if pkg and expected_pkg and pkg != expected_pkg:
                errors.append(
                    f"project file package mismatch: {f.path} declares package {pkg} but expected {expected_pkg}"
                )

    for f in exercise.answers_list:
        if f.path != "pom.xml" and not (
            f.path.startswith("src/main/java/") and f.path.endswith(".java")
        ):
            errors.append(f"answers_list contains invalid path: {f.path}")

    return errors


def build_preflight_failure_context(label: str, errors: List[str]) -> str:
    lines = [f"{label} preflight validation failed."]
    lines.extend(f"- {err}" for err in errors[:10])
    return "\n".join(lines)


def compose_exercise(contract: ContractSpec, implementation: ImplementationSpec) -> SpringBootExercise:
    return SpringBootExercise(
        problem_description=contract.problem_description,
        project_files=normalize_project_files(implementation.project_files),
        test_files=normalize_project_files(contract.test_files),
        solution_explanation_md=implementation.solution_explanation_md,
        paths_to_ex=list(contract.paths_to_ex),
        answers_list=normalize_project_files(implementation.answers_list),
    )


def generate_single_contract(
    backend: CodellamasBackend,
    *,
    topic: str,
    code_smells: str,
    existing_codebase: str,
) -> ContractSpec:
    raw = backend.contract_crew().kickoff(
        inputs={
            "topic": topic,
            "code_smells": code_smells,
            "existing_codebase": existing_codebase,
        }
    )
    contract = ContractSpec(**raw.json_dict)
    contract_errors = validate_contract(contract)
    if contract_errors:
        raise HTTPException(
            status_code=500,
            detail="Generated contract failed validation: " + "; ".join(contract_errors),
        )
    return contract


def generate_single_implementation_with_retries(
    backend: CodellamasBackend,
    *,
    topic: str,
    code_smells: str,
    contract: ContractSpec,
    base_project_files: List[ProjectFile],
    verify_maven: bool,
) -> Tuple[SpringBootExercise, Dict[str, Any]]:
    max_single_retries = 1
    implementation_attempts: List[Dict[str, Any]] = []
    failure_context = ""
    previous_exercise_json: Dict[str, Any] = {}
    exercise_data: SpringBootExercise | None = None

    contract_json = contract.model_dump()

    for attempt in range(1, max_single_retries + 2):
        raw = backend.implementation_crew().kickoff(
            inputs={
                "topic": topic,
                "code_smells": code_smells,
                "contract_json": contract_json,
                "maven_failure_context": failure_context,
                "previous_exercise_json": previous_exercise_json,
            }
        )

        implementation = ImplementationSpec(**raw.json_dict)
        exercise_data = compose_exercise(contract, implementation)

        preflight_errors = validate_exercise_payload(exercise_data)
        if preflight_errors:
            implementation_attempts.append(
                {
                    "attempt": attempt,
                    "preflight": {
                        "status": "FAIL",
                        "errors": preflight_errors,
                    },
                    "smelly": {"enabled": False, "status": "SKIPPED"},
                    "solution": {"enabled": False, "status": "SKIPPED"},
                }
            )

            if attempt > max_single_retries:
                break

            failure_context = build_preflight_failure_context("IMPLEMENTATION", preflight_errors)
            previous_exercise_json = exercise_data.model_dump()
            continue

        smelly_verification = run_maven_verification(
            verify_maven=verify_maven,
            project_files=base_project_files,
            override_files=exercise_data.project_files,
            injected_tests=exercise_data.test_files,
            timeout_sec=180,
        )

        solution_override_files = build_solution_override_files(
            project_files=exercise_data.project_files,
            answers_list=exercise_data.answers_list,
            paths_to_ex=exercise_data.paths_to_ex,
        )

        solution_verification = run_maven_verification(
            verify_maven=verify_maven,
            project_files=base_project_files,
            override_files=solution_override_files,
            injected_tests=exercise_data.test_files,
            timeout_sec=180,
            skipped_reason="verify_maven=true but no base project_files provided for solution verification",
        )

        implementation_attempts.append(
            {
                "attempt": attempt,
                "preflight": {"status": "PASS", "errors": []},
                "smelly": smelly_verification,
                "solution": solution_verification,
            }
        )

        smelly_ok = smelly_verification.get("status") == "PASS"
        solution_ok = solution_verification.get("status") == "PASS"

        if smelly_ok and solution_ok:
            break

        can_retry_smelly = should_retry_single_generation(smelly_verification)
        can_retry_solution = should_retry_single_generation(solution_verification)

        if attempt > max_single_retries or not (can_retry_smelly or can_retry_solution):
            break

        retry_parts: List[str] = []

        if can_retry_smelly:
            retry_parts.append(
                "Retry target: smelly implementation only.\n"
                "The contract is fixed and must not change.\n"
                "Fix only project_files so the smelly implementation passes while preserving the requested code smells.\n"
                + build_maven_failure_context("SMELLY", smelly_verification)
            )

        if can_retry_solution:
            retry_parts.append(
                "Retry target: clean reference solution only.\n"
                "The contract is fixed and must not change.\n"
                "Fix only answers_list so the clean solution compiles and passes the same tests.\n"
                + build_maven_failure_context("SOLUTION", solution_verification)
            )

        failure_context = "\n\n".join(retry_parts)
        previous_exercise_json = exercise_data.model_dump()

    if exercise_data is None:
        raise HTTPException(status_code=500, detail="Implementation generation returned no data.")

    loop_meta = {
        "mode": "single",
        "fix_loop": True,
        "contract_locked": True,
        "implementation_attempts": implementation_attempts,
        "single_retries_used": max(0, len(implementation_attempts) - 1),
    }

    return exercise_data, loop_meta


@app.get("/")
async def root():
    return {"status": "healthy", "backends": ["single-agent", "multi-agent"]}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "codellamas-backend",
        "backends": ["single-agent", "multi-agent"],
        "timestamp": datetime.datetime.now().isoformat(),
    }


@app.get("/capabilities")
async def capabilities():
    return {
        "backends": ["single-agent", "multi-agent"],
        "maven_verification": "available",
        "exercise_format": "Java Maven refactoring exercise with PROBLEM.md, SOLUTION_EXP.md, project files and test files.",
    }


def _execute_single_generation(body: GenerateRequest, max_retries: int = 3):
    last_error = None
    for attempt in range(max_retries):
        try:
            formatted_code_smells = ingest_code_smells(body.code_smells)
            backend = get_backend(
                body.mode,
                model_name=body.model_name,
                api_endpoint=body.api_endpoint,
                api_key=body.api_key,
            )

            base_project_files = (
                normalize_project_files(body.project_files)
                if body.project_files
                else default_base_project_files()
            )

            loop_meta = None

            if body.mode == "multi" and body.verify_maven:
                exercise_data, loop_meta = backend.generate_with_fix_loop(
                    topic=body.topic,
                    code_smells=body.code_smells,
                    existing_codebase=body.existing_codebase,
                    project_files=base_project_files,
                )
            else:
                contract = generate_single_contract(
                    backend=backend,
                    topic=body.topic,
                    code_smells=formatted_code_smells,
                    existing_codebase=body.existing_codebase,
                )

                exercise_data, loop_meta = generate_single_implementation_with_retries(
                    backend=backend,
                    topic=body.topic,
                    code_smells=formatted_code_smells,
                    contract=contract,
                    base_project_files=base_project_files,
                    verify_maven=body.verify_maven,
                )

            saved_path = save_exercise_to_repo(exercise_data, body.topic)

            smelly_verification = run_maven_verification(
                verify_maven=body.verify_maven,
                project_files=base_project_files,
                override_files=exercise_data.project_files,
                injected_tests=exercise_data.test_files,
                timeout_sec=180,
            )

            maven_verification: Dict[str, Any] = smelly_verification

            if body.mode == "single":
                solution_override_files = build_solution_override_files(
                    project_files=exercise_data.project_files,
                    answers_list=exercise_data.answers_list,
                    paths_to_ex=exercise_data.paths_to_ex,
                )

                solution_verification = run_maven_verification(
                    verify_maven=body.verify_maven,
                    project_files=base_project_files,
                    override_files=solution_override_files,
                    injected_tests=exercise_data.test_files,
                    timeout_sec=180,
                    skipped_reason="verify_maven=true but no base project_files provided for solution verification",
                )

                maven_verification = {
                    "smelly": smelly_verification,
                    "solution": solution_verification,
                }

            response_data: Dict[str, Any] = {
                "status": "success",
                "message": f"Exercise generated and saved to {saved_path}",
                "data": exercise_data.model_dump(),
                "maven_verification": maven_verification,
            }

            if loop_meta is not None:
                response_data["meta"] = loop_meta

            csv_row_args = {
                "exercise": exercise_data,
                "topic": body.topic,
                "model": body.mode,
                "response_data": response_data,
            }

            return response_data, csv_row_args

        except Exception as e:
            logging.warning(f"Generation attempt {attempt+1} failed: {e}")
            last_error = e

    return {"status": "error", "message": f"Generation failed after {max_retries} attempts: {last_error}"}, None

@app.post("/generate")
async def generate_exercise(body: GenerateRequest):
    global request_queue_counter, request_current_turn
    
    async with csv_write_lock:
        my_turn = request_queue_counter
        request_queue_counter += 1

    try:
        # Run generations in parallel in separate threads
        tasks = [asyncio.to_thread(_execute_single_generation, body, 3) for _ in range(body.count)]
        results = await asyncio.gather(*tasks)
    except Exception as e:
        # Prevent queue from blocking on exception
        async with write_condition:
            while request_current_turn != my_turn:
                await write_condition.wait()
            request_current_turn += 1
            write_condition.notify_all()
            
        logging.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Sequential write phase
    async with write_condition:
        while request_current_turn != my_turn:
            await write_condition.wait()
        
        try:
            for response, csv_args in results:
                if csv_args is not None:
                    append_to_csv(**csv_args)
        finally:
            request_current_turn += 1
            write_condition.notify_all()

    responses = [res for res, _ in results]
    if body.count == 1:
        if responses[0].get("status") == "error":
            raise HTTPException(status_code=500, detail=responses[0].get("message"))
        return responses[0]
    
    return {
        "status": "success",
        "message": f"Finished generating {body.count} exercises.",
        "results": responses
    }

@app.post("/review")
async def review_solution(body: EvaluateRequest):
    parsed_q: Dict[str, Any] = body.question_json or {}

    project_files_q = parsed_q.get("project_files", [])
    injected_tests_q = parsed_q.get("test_files", [])

    project_files = normalize_project_files(project_files_q)
    student_code = normalize_project_files(body.student_code or [])
    injected_tests = normalize_project_files(injected_tests_q)

    formatted_code_smells = ingest_code_smells(getattr(body, "code_smells", []))

    try:
        maven_verification = run_maven_verification(
            verify_maven=body.verify_maven,
            project_files=project_files,
            override_files=student_code or [],
            injected_tests=injected_tests or [],
            timeout_sec=180,
            skipped_reason="verify_maven=true but no project_files provided",
        )

        test_results = body.test_results or ""
        if (
            maven_verification.get("enabled")
            and maven_verification.get("status") not in (None, "SKIPPED")
            and maven_verification.get("raw_log_head")
        ):
            test_results = maven_verification["raw_log_head"]

        inputs: Dict[str, Any] = {
            "question_json": body.question_json,
            "project_files": [p.model_dump() for p in project_files],
            "student_code": [p.model_dump() for p in student_code],
            "injected_tests": [p.model_dump() for p in injected_tests],
            "test_results": test_results,
            "code_smells": formatted_code_smells,
            "mode": body.mode,
            "query": body.query or "",
            "verify_maven": body.verify_maven,
        }

        backend = get_backend(
            body.mode,
            model_name=body.model_name,
            api_endpoint=body.api_endpoint,
            api_key=body.api_key,
        )
        raw = backend.review_crew().kickoff(inputs=inputs)

        return {"feedback": str(raw), "maven_verification": maven_verification}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review crew failed: {e}")

