import os
import datetime
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from codellamas_backend.crew import CodellamasBackend, SpringBootExercise

app = FastAPI()

class GenerateRequest(BaseModel):
    topic: str
    code_smells: List[str]
    existing_codebase: str = "NONE"

class EvaluateRequest(BaseModel):
    problem_description: str
    original_code: str
    student_code: str
    test_results: str
    reference_solution: str
    code_smells: List[str]

def ingest_code_smells(code_smells: List[str]) -> str:
    """
    Transforms a list of code smells into a single formatted string.
    """
    if not code_smells:
        return "None"
    return ", ".join(code_smells)

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
        result = CodellamasBackend().generation_crew().kickoff(inputs={
            "topic": body.topic,
            "code_smells": formatted_code_smells,
            "existing_codebase": body.existing_codebase
        })

        exercise_data = SpringBootExercise(**result.json_dict)
        saved_path = save_exercise_to_repo(exercise_data, body.topic)

        return {
            "status": "success",
            "message": f"Exercise generated and saved to {saved_path}",
            "data": result.json_dict
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
    try:
        raw = CodellamasBackend().review_crew().kickoff(inputs=inputs)
        return {"feedback": str(raw)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review crew failed: {e}")

@app.get("/")
async def root():
    return {"status": "ok"}
