import os
import datetime
import json
import csv
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from codellamas_backend.crews.crew_single import CodellamasBackend, SpringBootExercise
from codellamas_backend.crews.crew_multi import CodellamasBackendMulti
from codellamas_backend.runtime.verifier import MavenVerifier, to_filelikes

app = FastAPI()
CSV_FILE_PATH = "output/exercises_evaluation.csv"

class ProjectFile(BaseModel):
    path: str
    content: str

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
    mode: str = "single" # "single" or "multi"
    # optional
    verify_maven: bool = False
    project_files: List[ProjectFile] = []

class EvaluateRequest(BaseModel):
    problem_description: str
    original_code: str
    student_code: str
    test_results: str
    reference_solution: str
    code_smells: List[str]
    query: str = ""
    mode: str = "single"

    # optional
    verify_maven: bool = False
    project_files: List[ProjectFile] = [] # base Spring Boot project
    student_files: List[ProjectFile] = [] # overrides (what student changed)
    injected_tests: List[ProjectFile] = [] # generated tests you want to enforce

def ingest_code_smells(code_smells: List[str]) -> str:
    if not code_smells:
        return "None"
    return ", ".join(code_smells)

def append_to_csv(exercise: SpringBootExercise, topic: str, model: str, response_data: dict = None):
    try:
        # Create directory if it doesn't exist
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

    with open(os.path.join(base_repo_dir, "REFERENCE_SOLUTION.md"), "w") as f:
        f.write(exercise.reference_solution_markdown)
    
    return base_repo_dir

def run_maven_verification(*, verify_maven: bool, project_files: List[ProjectFile], override_files: List[Any], injected_tests: List[Any],
    timeout_sec: int = 180, skipped_reason: str = "verify_maven=true but no project_files provided (Spring Initializr scaffold required).") -> Dict[str, Any]:
    
    maven_verification: Dict[str, Any] = {"enabled": False}

    if not verify_maven:
        return maven_verification

    maven_verification["enabled"] = True

    if not project_files:
        maven_verification.update({"status": "SKIPPED", "reason": skipped_reason})
        return maven_verification

    verifier = MavenVerifier(timeout_sec=timeout_sec, quiet=True)

    base_project = to_filelikes(project_files)
    overrides = to_filelikes(override_files or [])
    inject_tests = {f.path: f.content for f in (injected_tests or [])}

    verification = verifier.verify(
        base_project=base_project,
        override_files=overrides,
        injected_tests=inject_tests,
    )

    maven_verification.update({
            "status": verification.status,
            "failed_tests": verification.failed_tests,
            "errors": verification.errors,
            "raw_log_head": verification.summary(),
    })

    return maven_verification

@app.get("/")
async def root():
    return {"status": "ok", "backends": ["single-agent", "multi-agent"]}

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
                project_files=body.project_files,
            )
            saved_path = save_exercise_to_repo(exercise_data, body.topic)
            response_data = {
                "status": "success",
                "message": f"Exercise generated and saved to {saved_path}",
                "data": exercise_data.model_dump(),
                "reference_solution": exercise_data.reference_solution_markdown,
                "meta": loop_meta
            }
        
            append_to_csv(exercise_data, body.topic, model=body.mode, response_data=response_data)
            return response_data

        result = backend.generation_crew().kickoff(inputs={
            "topic": body.topic,
            "code_smells": formatted_code_smells,
            "existing_codebase": body.existing_codebase
        })

        exercise_data = SpringBootExercise(**result.json_dict)
        saved_path = save_exercise_to_repo(exercise_data, body.topic)

        # Optional Maven verification (deduped)
        maven_verification = run_maven_verification(
            verify_maven=body.verify_maven,
            project_files=body.project_files,
            override_files=exercise_data.project_files,
            injected_tests=exercise_data.test_files,
            timeout_sec=180,
        )

        response_data = {
            "status": "success",
            "message": f"Exercise generated and saved to {saved_path}",
            "data": exercise_data.model_dump(),
            "reference_solution": exercise_data.reference_solution_markdown,
            "maven_verification": maven_verification,
        }

        append_to_csv(exercise_data, body.topic, model=body.mode, response_data=response_data)
        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/review")
async def review_solution(body: EvaluateRequest):
    formatted_code_smells = ingest_code_smells(body.code_smells)

    inputs = {
        "problem_description": body.problem_description,
        "original_code": body.original_code,
        "student_code": body.student_code,
        "test_results": body.test_results,
        "reference_solution": body.reference_solution,
        "code_smells": formatted_code_smells,
        "query": body.query
    }

    try:
        maven_verification = run_maven_verification(
            verify_maven=body.verify_maven,
            project_files=body.project_files,
            override_files=body.student_files or [],
            injected_tests=body.injected_tests or [],
            timeout_sec=180,
            skipped_reason="verify_maven=true but no project_files provided",
        )

        if (maven_verification.get("enabled") and maven_verification.get("status") not in (None, "SKIPPED")
            and maven_verification.get("raw_log_head")):
            inputs["test_results"] = maven_verification["raw_log_head"]

        backend = get_backend(body.mode)
        raw = backend.review_crew().kickoff(inputs=inputs)

        return {"feedback": str(raw), "maven_verification": maven_verification}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review crew failed: {e}")
