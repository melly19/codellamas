import os
import logging
import datetime
import json
import csv
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from codellamas_backend.crews.crew_single import CodellamasBackend, SpringBootExercise
from codellamas_backend.crews.crew_multi import CodellamasBackendMulti
from codellamas_backend.runtime.verifier import MavenVerifier
from codellamas_backend.schemas.files import ProjectFile


logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)


app = FastAPI()
CSV_FILE_PATH = "output/exercises_evaluation.csv"


def get_backend(mode: str):
    if mode not in {"single", "multi"}:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Use 'single' or 'multi'."
        )
    return CodellamasBackendMulti() if mode == "multi" else CodellamasBackend()


class GenerateRequest(BaseModel):
    topic: str
    code_smells: List[str]
    existing_codebase: str = "NONE"
    mode: str = "single"  # "single" or "multi"
    verify_maven: bool = False
    project_files: List[ProjectFile] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    question_json: Dict[str, Any] = Field(default_factory=dict)
    student_code: List[ProjectFile] = Field(default_factory=list)
    code_smells: List[str]
    mode: str = "single"  # "single" or "multi"
    query: str = ""  # additional context or specific questions for the review
    test_results: str = ""  # output of mvn test in the frontend
    verify_maven: bool = False


def ingest_code_smells(code_smells: List[str]) -> str:
    return "None" if not code_smells else ", ".join(code_smells)


def append_to_csv(exercise: SpringBootExercise, topic: str, model: str, response_data: dict = None):
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

        with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["timestamp", "topic", "problem_description", "single_or_multi", "response_json"]
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

    with open(os.path.join(base_repo_dir, "PROBLEM.md"), "w") as f:
        f.write(exercise.problem_description)

    for file in exercise.project_files:
        full_path = os.path.join(base_repo_dir, file.path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(file.content)

    for file in exercise.test_files:
        full_path = os.path.join(base_repo_dir, file.path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(file.content)

    with open(os.path.join(base_repo_dir, "SOLUTION_EXP.md"), "w") as f:
        f.write(exercise.solution_explanation_md)

    if hasattr(exercise, 'answers_list') and exercise.answers_list:
        answers_dir = os.path.join(base_repo_dir, "answers")
        os.makedirs(answers_dir, exist_ok=True)
        for file in exercise.answers_list:
            full_path = os.path.join(answers_dir, file.path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(file.content)

    return base_repo_dir


def run_maven_verification(*, verify_maven: bool, project_files: List[ProjectFile], override_files: List[Any], injected_tests: List[Any],
                           timeout_sec: int = 180, skipped_reason: str = "verify_maven=true but no project_files provided") -> Dict[str, Any]:

    maven_verification: Dict[str, Any] = {"enabled": False}

    if not verify_maven:
        return maven_verification

    maven_verification["enabled"] = True

    if not project_files:
        maven_verification.update({"status": "SKIPPED", "reason": skipped_reason})
        return maven_verification

    verifier = MavenVerifier(timeout_sec=timeout_sec, quiet=True)
    inject_tests = {f.path: f.content for f in (injected_tests or [])}

    verification = verifier.verify(
        base_project=project_files,
        override_files=override_files,
        injected_tests=inject_tests,
    )

    maven_verification.update({
            "status": verification.status,
            "failed_tests": verification.failed_tests,
            "errors": verification.errors,
            "raw_log_head": verification.summary(),
    })

    return maven_verification


def normalize_project_files(items: list) -> list:
    out: list[ProjectFile] = []
    for item in items or []:
        if isinstance(item, ProjectFile):
            out.append(item)
        elif isinstance(item, dict):
            out.append(ProjectFile(**item))
        else:
            raise TypeError(f"Invalid project file entry: {type(item)}")
    return out


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
        "exercise_format": "Spring Boot with PROBLEM.md, SOLUTION_EXP.md, project files and test files.",
    }


@app.post("/generate")
async def generate_exercise(body: GenerateRequest):
    formatted_code_smells = ingest_code_smells(body.code_smells)

    try:
        backend = get_backend(body.mode)

        if body.mode == "multi" and body.verify_maven and body.project_files:
            exercise_data, loop_meta = backend.generate_with_fix_loop(
                topic=body.topic,
                code_smells=body.code_smells,
                existing_codebase=body.existing_codebase,
                project_files=body.project_files
            )
        else:
            result = backend.generation_crew().kickoff(inputs={
                    "topic": body.topic,
                    "code_smells": formatted_code_smells,
                    "existing_codebase": body.existing_codebase
                })
            exercise_data = SpringBootExercise(**result.json_dict)
            loop_meta = None

        saved_path = save_exercise_to_repo(exercise_data, body.topic)

        maven_verification = run_maven_verification(
            verify_maven=body.verify_maven,
            project_files=body.project_files,
            override_files=exercise_data.project_files,
            injected_tests=exercise_data.test_files,
            timeout_sec=180,
        )

        response_data: Dict[str, Any] = {
            "status": "success",
            "message": f"Exercise generated and saved to {saved_path}",
            "data": exercise_data.model_dump(),
            "maven_verification": maven_verification,
        }

        if loop_meta is not None:
            response_data["meta"] = loop_meta

        append_to_csv(exercise_data, body.topic, model=body.mode, response_data=response_data)
        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        if (maven_verification.get("enabled") and maven_verification.get("status") not in (None, "SKIPPED")
                and maven_verification.get("raw_log_head")):
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
            "verify_maven": body.verify_maven
        }

        backend = get_backend(body.mode)
        raw = backend.review_crew().kickoff(inputs=inputs)

        return {"feedback": str(raw), "maven_verification": maven_verification}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review crew failed: {e}")
