import os
import re
import logging
import datetime
import json
import csv
import time
from typing import List, Dict, Any, Tuple
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from codellamas_backend.crews.crew_single import CodellamasBackend, SpringBootExercise
from codellamas_backend.crews.crew_multi import CodellamasBackendMulti
from codellamas_backend.runtime.verifier import MavenVerifier
from codellamas_backend.schemas.files import ProjectFile
from codellamas_backend.crews.crew_single import MODEL as MODEL_SINGLE
from codellamas_backend.crews.crew_multi import MODEL as MODEL_MULTI

# Prevent LiteLLM from flooding the logs
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

app = FastAPI()
CSV_FILE_PATH = "output/exercises_evaluation.csv"
REVIEW_CSV_FILE_PATH = "output/reviews_evaluation.csv"

# --- Models ---

class GenerateRequest(BaseModel):
    topic: str
    code_smells: List[str]
    existing_codebase: str = "NONE"
    mode: str = "single"
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
    mode: str = "single"
    query: str = ""
    test_results: str = ""
    verify_maven: bool = False
    model_name: str | None = None
    api_endpoint: str | None = None
    api_key: str | None = None

# --- Helper Functions ---

def get_backend(mode: str, model_name: str | None = None, api_endpoint: str | None = None, api_key: str | None = None):
    if mode not in {"single", "multi"}:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Use 'single' or 'multi'."
        )
    return CodellamasBackendMulti(model_name, api_endpoint, api_key) if mode == "multi" else CodellamasBackend(model_name, api_endpoint, api_key)

def ingest_code_smells(code_smells: List[str]) -> str:
    return "None" if not code_smells else ", ".join(code_smells)

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

# --- CSV Persistence ---

def append_to_csv(
    folder_name: str,
    model: str,
    topic: str,
    code_smells: List[str],
    problem: str,
    project_files: str,
    test_files: str,
    solution_explanation: str,
    solution_code: str
):
    try:
        os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        fieldnames = [
            "timestamp", 
            "name", 
            "model", 
            "topic", 
            "code_smells", 
            "problem", 
            "project_files", 
            "test_files", 
            "solution_explanation", 
            "solution_code"
        ]

        row = {
            "timestamp": timestamp,
            "name": folder_name,
            "model": model,
            "topic": topic,
            "code_smells": json.dumps(code_smells) if isinstance(code_smells, list) else code_smells,
            "problem": problem,
            "project_files": project_files,
            "test_files": test_files,
            "solution_explanation": solution_explanation,
            "solution_code": solution_code
        }

        file_exists = os.path.isfile(CSV_FILE_PATH)
        with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        return os.path.abspath(CSV_FILE_PATH)
    except Exception as e:
        print(f"Error appending to CSV: {e}")
        raise

def append_review_to_csv(
    problem_description: str,
    code_smells: List[str],
    mode: str,
    review_time_sec: float,
    feedback_dict: dict,
    maven_verification: dict
):
    os.makedirs(os.path.dirname(REVIEW_CSV_FILE_PATH), exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "timestamp": timestamp,
        "problem_description": problem_description,
        "code_smells": ", ".join(code_smells),
        "single_or_multi": mode,
        "problem_statement_clarity": feedback_dict.get("problem_statement_clarity"),
        "smell_incorporation": feedback_dict.get("smell_incorporation"),
        "avoids_unrelated_bad_practices": feedback_dict.get("avoids_unrelated_bad_practices"),
        "naming_conventions": feedback_dict.get("naming_conventions"),
        "structure_quality": feedback_dict.get("structure_quality"),
        "undergraduate_suitability": feedback_dict.get("undergraduate_suitability"),
        "minimal_boilerplate": feedback_dict.get("minimal_boilerplate"),
        "readability": feedback_dict.get("readability_flow"),
        "reasonable_optimisation": feedback_dict.get("reasonable_optimisation"),
        "overall_rating": feedback_dict.get("overall_rating"),
        "maven_status": maven_verification.get("status"),
        "failed_tests": json.dumps(maven_verification.get("failed_tests")),
        "review_time_sec": review_time_sec
    }

    file_exists = os.path.isfile(REVIEW_CSV_FILE_PATH)
    with open(REVIEW_CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
        fieldnames = list(row.keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    return os.path.abspath(REVIEW_CSV_FILE_PATH)

# --- Filesystem Operations ---

def save_exercise_to_repo(exercise: SpringBootExercise, topic: str, code_smells: List[str], mode: str) -> Tuple[str, str]:
    timestamp = datetime.datetime.now().strftime("%d%m_%M%S")
    safe_topic = topic.replace(" ", "_")
    model = MODEL_SINGLE if mode == "single" else MODEL_MULTI
    
    safe_model = model.replace("/", "-").replace(":", "-")
    formatted_smells = "_".join([smell.replace(" ", "_") for smell in code_smells])
    folder_name = f"{safe_topic}_{safe_model}_{formatted_smells}_{timestamp}"
    
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

    return base_repo_dir, folder_name

# --- Logic & Verifiers ---

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
    inject_tests_dict = {f.path: f.content for f in (injected_tests or [])}

    verification = verifier.verify(
        base_project=project_files,
        override_files=override_files,
        injected_tests=inject_tests_dict,
    )

    maven_verification.update(
        {
            "status": verification.status,
            "failed_tests": verification.failed_tests,
            "errors": verification.errors,
            "raw_log_head": verification.summary(),
    })
    return maven_verification

# --- API Endpoints ---

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

@app.post("/generate")
async def generate_exercise(body: GenerateRequest):
    formatted_code_smells = ingest_code_smells(body.code_smells)

    try:
        backend = get_backend(body.mode, model_name=body.model_name, api_endpoint=body.api_endpoint, api_key=body.api_key)
        
        start_time = time.perf_counter()

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
            result = backend.generation_crew().kickoff(inputs={
                    "topic": body.topic,
                    "code_smells": formatted_code_smells,
                    "existing_codebase": body.existing_codebase
                })
            exercise_data = SpringBootExercise(**result.json_dict)
            loop_meta = None

        end_time = time.perf_counter()
        generation_time_sec = round(end_time - start_time, 3)

        # Save to disk and get the folder name for CSV logging
        saved_path, folder_name = save_exercise_to_repo(exercise_data, body.topic, body.code_smells, body.mode)

        smelly_verification = run_maven_verification(
            verify_maven=body.verify_maven,
            project_files=base_project_files,
            override_files=exercise_data.project_files,
            injected_tests=exercise_data.test_files,
            timeout_sec=180,
        )

        # Prepare CSV data
        project_files_json = json.dumps([f.model_dump() for f in exercise_data.project_files])
        test_files_json = json.dumps([f.model_dump() for f in exercise_data.test_files])
        solution_code_json = ""
        if hasattr(exercise_data, 'answers_list') and exercise_data.answers_list:
            solution_code_json = json.dumps([f.model_dump() for f in exercise_data.answers_list])

        append_to_csv(
            folder_name=folder_name,
            model=MODEL_SINGLE if body.mode == "single" else MODEL_MULTI,
            topic=body.topic,
            code_smells=body.code_smells,
            problem=exercise_data.problem_description,
            project_files=project_files_json,
            test_files=test_files_json,
            solution_explanation=exercise_data.solution_explanation_md,
            solution_code=solution_code_json
        )

        response_data: Dict[str, Any] = {
            "status": "success",
            "message": f"Exercise generated and saved to {saved_path}",
            "data": exercise_data.model_dump(),
            "maven_verification": maven_verification,
            "generation_time_sec": generation_time_sec
        }

        if loop_meta is not None:
            response_data["meta"] = loop_meta

        return response_data

    except Exception as e:
        logging.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review")
async def review_solution(body: EvaluateRequest):
    parsed_q: Dict[str, Any] = body.question_json or {}

    project_files_q = parsed_q.get("project_files", [])
    injected_tests_q = parsed_q.get("test_files", [])

    project_files = normalize_project_files(project_files_q)
    student_code = normalize_project_files(body.student_code or [])
    injected_tests = normalize_project_files(injected_tests_q)

    formatted_code_smells = ingest_code_smells(body.code_smells)

    try:
        start_time = time.perf_counter()
        
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

        end_time = time.perf_counter()
        review_time_sec = round(end_time - start_time, 3)
        
        feedback_dict = raw.json_dict if hasattr(raw, "json_dict") else json.loads(str(raw))

        append_review_to_csv(
            problem_description=parsed_q.get("problem_description", ""),
            code_smells=body.code_smells,
            mode=body.mode,
            review_time_sec=review_time_sec,
            feedback_dict=feedback_dict,
            maven_verification=maven_verification
        )

        return {"feedback": str(raw), "maven_verification": maven_verification}

    except Exception as e:
        logging.error(f"Review crew failed: {e}")
        raise HTTPException(status_code=500, detail=f"Review crew failed: {e}")