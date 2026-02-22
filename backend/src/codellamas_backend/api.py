import os
import datetime
import json
import csv
import time
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from codellamas_backend.crews.crew_single import CodellamasBackend, SpringBootExercise
from codellamas_backend.crews.crew_multi import CodellamasBackendMulti
from codellamas_backend.runtime.verifier import MavenVerifier, to_filelikes

app = FastAPI()
CSV_FILE_PATH = "output/exercises_evaluation.csv"
REVIEW_CSV_FILE_PATH = "output/reviews_evaluation.csv"

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

def append_to_csv(exercise: SpringBootExercise, topic: str, code_smells: List[str], generation_time_sec: float, model: str, response_data: dict = None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "timestamp": timestamp,
        "topic": topic,
        "code_smells": code_smells,
        "problem_description": exercise.problem_description,
        "single_or_multi": model,
        "response_json": json.dumps(response_data),
        "generation_time_sec": generation_time_sec
    }

    file_exists = os.path.isfile(CSV_FILE_PATH)

    with open(CSV_FILE_PATH, mode='a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["timestamp", "topic", "code_smells", "problem_description", "single_or_multi", "response_json", "generation_time_sec"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow(row)

    return os.path.abspath(CSV_FILE_PATH)

def append_review_to_csv(
    problem_description: str,
    code_smells: List[str],
    mode: str,
    review_time_sec: float,
    feedback_dict: dict,
    maven_verification: dict
):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "timestamp": timestamp,
        "problem_description": problem_description,
        "code_smells": ", ".join(code_smells),
        "single_or_multi": mode,

        # 🔹 Extracted review JSON fields
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

        # 🔹 Maven info
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
            return {
                "status": "success",
                "message": f"Exercise generated and saved to {saved_path}",
                "data": exercise_data.model_dump(),
                "meta": loop_meta
            }

        start_time = time.perf_counter()

        result = backend.generation_crew().kickoff(inputs={
            "topic": body.topic,
            "code_smells": formatted_code_smells,
            "existing_codebase": body.existing_codebase
        })

        end_time = time.perf_counter()
        generation_time_sec = round(end_time - start_time, 3)

        exercise_data = SpringBootExercise(**result.json_dict)

        saved_path = save_exercise_to_repo(exercise_data, body.topic)

        # Optional Maven verification (using verifier layer)   
        maven_verification: dict = {"enabled": False}

        if body.verify_maven:
            maven_verification["enabled"] = True

            if not body.project_files:
                maven_verification.update({
                    "status": "SKIPPED",
                    "reason": "verify_maven=true but no project_files provided (Spring Initializr scaffold required)."
                })
            else:
                verifier = MavenVerifier(timeout_sec=180, quiet=True)

                # Convert scaffold files to FileLike using verifier helper
                base_project = to_filelikes(body.project_files)  # from verifier.py :contentReference[oaicite:4]{index=4}

                # Convert generated project files to FileLike (same helper)
                override_files = to_filelikes(exercise_data.project_files)

                # Inject generated tests (dict[path -> content])
                inject_tests = {f.path: f.content for f in exercise_data.test_files}

                verification = verifier.verify(
                    base_project=base_project,
                    override_files=override_files,
                    injected_tests=inject_tests
                )

                maven_verification.update({
                    "status": verification.status,
                    "failed_tests": verification.failed_tests,
                    "errors": verification.errors,
                    "raw_log_head": verification.summary()
                })

        # 5) Compile response early to save to CSV
        response_data = {
            "status": "success",
            "message": f"Exercise generated and saved to {saved_path}",
            "data": result.json_dict,
            "maven_verification": maven_verification,
        }

        append_to_csv(exercise_data, body.topic, body.code_smells, generation_time_sec, model=body.mode, response_data=response_data)

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
        "code_smells": formatted_code_smells
    }

    maven_verification: Dict[str, Any] = {"enabled": False}

    try:
        # Optional Maven verification
        if body.verify_maven:
            maven_verification["enabled"] = True

            if not body.project_files:
                maven_verification.update({
                    "status": "SKIPPED",
                    "reason": "verify_maven=true but no project_files provided"
                })
            else:
                verifier = MavenVerifier(timeout_sec=180, quiet=True)

                base_project = to_filelikes(body.project_files)
                student_overrides = to_filelikes(body.student_files or [])
                inject_tests = {f.path: f.content for f in (body.injected_tests or [])}

                verification = verifier.verify(
                    base_project=base_project,
                    override_files=student_overrides,
                    injected_tests=inject_tests
                )

                maven_verification.update({
                    "status": verification.status,
                    "failed_tests": verification.failed_tests,
                    "errors": verification.errors,
                    "raw_log_head": verification.summary()
                })

                inputs["test_results"] = verification.summary()

        # 🔹 Measure review time (same pattern as generate)
        start_time = time.perf_counter()

        backend = get_backend(body.mode)
        raw = backend.review_crew().kickoff(inputs=inputs)

        end_time = time.perf_counter()
        review_time_sec = round(end_time - start_time, 3)

        # 🔹 Extract structured JSON output
        feedback_dict = raw.json_dict if hasattr(raw, "json_dict") else json.loads(str(raw))

        # 🔹 Build response
        response_data = {
            "status": "success",
            "feedback": feedback_dict,
            "maven_verification": maven_verification
        }

        # 🔹 Append to separate review CSV
        append_review_to_csv(
            problem_description=body.problem_description,
            code_smells=body.code_smells,
            mode=body.mode,
            review_time_sec=review_time_sec,
            feedback_dict=feedback_dict,
            maven_verification=maven_verification
        )

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review crew failed: {e}")
