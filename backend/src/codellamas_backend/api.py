import os
import datetime
import json
import csv
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.src.codellamas_backend.crews.crew_single import CodellamasBackend, SpringBootExercise
from backend.src.codellamas_backend.crews.crew_multi import CodellamasBackendMulti
from codellamas_backend.tools.maven_tool import MavenTool
from codellamas_backend.tools.workspace import FileLike

app = FastAPI()
CSV_FILE_PATH = "output/exercises_evaluation.csv"

class ProjectFile(BaseModel):
    path: str
    content: str

def get_backend(mode: str):
    return CodellamasBackendMulti() if mode == "multi" else CodellamasBackend()

class GenerateRequest(BaseModel):
    topic: str
    code_smells: List[str]
    existing_codebase: str = "NONE"
    mode: str = "single" # "single" or "multi"
    # optional
    verify_maven: bool = False
    project_files: List[ProjectFile] = []
    save_full_project: bool = False

class EvaluateRequest(BaseModel):
    problem_description: str
    original_code: str
    student_code: str
    test_results: str
    reference_solution: str
    code_smells: List[str]
    mode: str = "single"

    # optional
    verify_maven: bool = False
    project_files: List[ProjectFile] = [] # base Spring Boot project
    student_files: List[ProjectFile] = [] # overrides (what student changed)
    injected_tests: List[ProjectFile] = [] # generated tests you want to enforce

def to_filelikes(files: List[ProjectFile]) -> List[FileLike]:
    return [FileLike(path=f.path, content=f.content) for f in files]


def ingest_code_smells(code_smells: List[str]) -> str:
    """
    Transforms a list of code smells into a single formatted string.
    """
    if not code_smells:
        return "None"
    return ", ".join(code_smells)

def append_to_csv(exercise: SpringBootExercise, topic: str):
    """
    Appends the generated exercise fields to a CSV file for evaluation.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    project_files_str = json.dumps([{ "path": f.path, "content": f.content } for f in exercise.project_files])
    test_files_str = json.dumps([{ "path": f.path, "content": f.content } for f in exercise.test_files])

    row = {
        "timestamp": timestamp,
        "topic": topic,
        "problem_description": exercise.problem_description,
        "project_files": project_files_str,
        "test_files": test_files_str,
        "reference_solution": exercise.reference_solution_markdown
    }

    file_exists = os.path.isfile(CSV_FILE_PATH)

    with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["timestamp", "topic", "problem_description", "project_files", "test_files", "reference_solution"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow(row)

    return os.path.abspath(CSV_FILE_PATH)

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

@app.post("/generate")
async def generate_exercise(body: GenerateRequest):
    formatted_code_smells = ingest_code_smells(body.code_smells)

    try:
        backend = get_backend(body.mode)
        result = backend.generation_crew().kickoff(inputs={
            "topic": body.topic,
            "code_smells": formatted_code_smells,
            "existing_codebase": body.existing_codebase
        })

        exercise_data = SpringBootExercise(**result.json_dict)
        append_to_csv(exercise_data, body.topic)
        saved_path = save_exercise_to_repo(exercise_data, body.topic)

        maven_verification: Dict[str, Any] = {"enabled": False}

        if getattr(body, "verify_maven", False):
            maven_verification["enabled"] = True

            if not getattr(body, "project_files", []):
                maven_verification.update({
                    "status": "SKIPPED",
                    "reason": "verify_maven=true but no project_files provided"
                })
            else:
                mvn = MavenTool(timeout_sec=180, quiet=True)

                base_project = to_filelikes(body.project_files)

                # Generated Java files override scaffold
                override_files = [
                    FileLike(path=f.path, content=f.content)
                    for f in exercise_data.project_files
                ]

                # Generated tests are injected
                inject_tests = {
                    f.path: f.content
                    for f in exercise_data.test_files
                }

                test_result = mvn.run_tests(
                    project_files=base_project,
                    override_files=override_files,
                    inject_tests=inject_tests
                )

                maven_verification.update({
                    "status": test_result.status,
                    "failed_tests": test_result.failed_tests,
                    "errors": test_result.errors,
                    "raw_log_head": test_result.raw_log_head(4000)
                })

        return {
            "status": "success",
            "message": f"Exercise generated and saved to {saved_path}",
            "data": result.json_dict,
            "maven_verification": maven_verification
        }
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
        "code_smells": formatted_code_smells
    }

    maven_verification: Dict[str, Any] = {"enabled": False}

    try:
        if getattr(body, "verify_maven", False):
            maven_verification["enabled"] = True

            if not getattr(body, "project_files", []):
                maven_verification.update({
                    "status": "SKIPPED",
                    "reason": "verify_maven=true but no project_files provided"
                })
            else:
                mvn = MavenTool(timeout_sec=180, quiet=True)

                base_project = to_filelikes(body.project_files)
                student_overrides = to_filelikes(body.student_files or [])

                inject_tests = {
                    f.path: f.content
                    for f in (body.injected_tests or [])
                }

                test_result = mvn.run_tests(
                    project_files=base_project,
                    override_files=student_overrides,
                    inject_tests=inject_tests
                )

                maven_verification.update({
                    "status": test_result.status,
                    "failed_tests": test_result.failed_tests,
                    "errors": test_result.errors,
                    "raw_log_head": test_result.raw_log_head(4000)
                })

                # IMPORTANT: feed real test result into LLM
                inputs["test_results"] = test_result.raw_log_head(4000)

        backend = get_backend(body.mode)
        raw = backend.review_crew().kickoff(inputs=inputs)
        return {
            "feedback": str(raw),
            "maven_verification": maven_verification
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review crew failed: {e}")

@app.get("/")
async def root():
    return {"status": "ok"}
