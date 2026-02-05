import os
import datetime
import json
import csv
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from crews.single_agent_crew import SingleAgentBackend, SpringBootExercise
from crews.multi_agent_crew import MultiAgentBackend

app = FastAPI()
CSV_FILE_PATH = "generated_exercises/exercises_evaluation.csv"

# --- Request Models ---
class GenerateRequest(BaseModel):
    topic: str
    code_smells: List[str]
    existing_codebase: str = "NONE"

class EvaluateRequest(BaseModel):
    problem_description: str
    original_code: str
    student_code: str
    reference_solution: str
    code_smells: List[str]
    test_suite: str 

# --- Helper Functions ---
def ingest_code_smells(code_smells: List[str]) -> str:
    if not code_smells:
        return "None"
    return ", ".join(code_smells)

def append_to_csv(exercise: SpringBootExercise, topic: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    proj_files = exercise.project_files or []
    test_files = exercise.test_files or []

    project_files_str = json.dumps([{"path": f.path, "content": f.content} for f in proj_files])
    test_files_str = json.dumps([{"path": f.path, "content": f.content} for f in test_files])

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
        f.write(exercise.problem_description or "")

    if exercise.project_files:
        for file in exercise.project_files:
            full_path = os.path.join(base_repo_dir, file.path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(file.content)

    if exercise.test_files:
        for file in exercise.test_files:
            full_path = os.path.join(base_repo_dir, file.path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(file.content)

    with open(os.path.join(base_repo_dir, "REFERENCE_SOLUTION.md"), "w") as f:
        f.write(exercise.reference_solution_markdown or "")
    
    return base_repo_dir

# --- Endpoints ---
@app.get("/")
async def root():
    return {"status": "ok", "backends": ["single-agent", "multi-agent"]}

# Single Agent Generation
@app.post("/generate")
async def generate_exercise_single(body: GenerateRequest):
    formatted_code_smells = ingest_code_smells(body.code_smells)
    try:
        result = SingleAgentBackend().generation_crew().kickoff(inputs={
            "topic": body.topic,
            "code_smells": formatted_code_smells,
            "existing_codebase": body.existing_codebase
        })
        exercise_data = SpringBootExercise(**result.json_dict)

        append_to_csv(exercise_data, body.topic)
        saved_path = save_exercise_to_repo(exercise_data, body.topic)

        return {"status": "success", "data": result.json_dict, "path": saved_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Multi-Agent Generation
@app.post("/generate/multi-agent")
async def generate_exercise_multi(body: GenerateRequest):
    formatted_code_smells = ingest_code_smells(body.code_smells)
    
    try:
        result = MultiAgentBackend().generation_crew().kickoff(inputs={
            "topic": body.topic,
            "code_smells": formatted_code_smells,
            "existing_codebase": body.existing_codebase
        })

        if not result.json_dict:
            raise ValueError("Multi-agent crew did not return structured JSON. Check task configuration.")

        exercise_data = SpringBootExercise(**result.json_dict)
        
        append_to_csv(exercise_data, body.topic)
        saved_path = save_exercise_to_repo(exercise_data, body.topic)

        return {
            "status": "success", 
            "backend": "multi-agent",
            "message": f"Exercise generated and saved to {saved_path}",
            "data": result.json_dict
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# Multi-Agent Review
@app.post("/review/multi-agent")
async def review_solution_multi(body: EvaluateRequest):
    formatted_code_smells = ingest_code_smells(body.code_smells)

    inputs = {
        "problem_description": body.problem_description,
        "original_code": body.original_code,
        "student_code": body.student_code,
        "test_suite": body.test_code,
        "reference_solution": body.reference_solution,
        "code_smells": formatted_code_smells
    }

    try:
        result = MultiAgentBackend().review_crew().kickoff(inputs=inputs)
        return {"result": result.raw} 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))