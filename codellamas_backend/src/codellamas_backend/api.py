from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from codellamas_backend.crew import CodellamasBackend

app = FastAPI()


class GenerateRequest(BaseModel):
    topic: str = "Online Shopping"
    code_smell: str = "Feature Envy"


class EvaluateRequest(BaseModel):
    problem_description: str
    original_code: str
    student_code: str
    test_results: str


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
    }

    try:
        result = CodellamasBackend().review_crew().kickoff(inputs=inputs)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"status": "ok"}
