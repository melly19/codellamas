from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from codellamas_backend.crew import CodellamasBackend

app = FastAPI()


class GenerateRequest(BaseModel):
    topic: str
    code_smell: str


class EvaluateRequest(BaseModel):
    problem_description: str
    original_code: str
    student_code: str
    test_results: str
    reference_solution: str
    code_smell: str


@app.post("/generate")
async def generate_exercise(body: GenerateRequest):
    inputs = {
        "topic": body.topic,
        "code_smell": body.code_smell,
    }

    try:
        result = CodellamasBackend().generation_crew().kickoff(inputs=inputs)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/review")
async def review_solution(body: EvaluateRequest):
    inputs = {
        "problem_description": body.problem_description,
        "original_code": body.original_code,
        "student_code": body.student_code,
        "test_results": body.test_results,
        "reference_solution": body.reference_solution,
        "code_smell": body.code_smell
    }

    try:
        result = CodellamasBackend().review_crew().kickoff(inputs=inputs)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"status": "ok"}
