from fastapi import FastAPI, HTTPException
from .api_models import (
    GenerateExerciseRequest, GenerateExerciseResponse,
    EvaluateSubmissionRequest, EvaluateSubmissionResponse
)
from .logging_utils import log_event
from orchestration.run_state import new_run_id
from orchestration.single_agent import generate_exercise_single
from orchestration.crewai_orchestrator import generate_exercise_crewai
from executor.maven_runner import run_maven_tests

app = FastAPI(title="CodeLlamas Backend", version="0.2.0")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/generate/exercise", response_model=GenerateExerciseResponse)
def generate_exercise(req: GenerateExerciseRequest):
    run_id = new_run_id()
    log_event(run_id, "generate.request", req.model_dump())

    try:
        if req.mode == "single":
            resp = generate_exercise_single(run_id, req)
        else:
            resp = generate_exercise_crewai(run_id, req)
    except Exception as e:
        log_event(run_id, "generate.error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

    log_event(run_id, "generate.response", resp.model_dump())
    return resp

@app.post("/evaluate/submission", response_model=EvaluateSubmissionResponse)
def evaluate_submission(req: EvaluateSubmissionRequest):
    run_id = req.run_id or new_run_id()
    log_event(run_id, "evaluate.request", req.model_dump())

    result = run_maven_tests(
        run_id=run_id,
        project=req.project,
        override_files=req.student_files,
        inject_tests=req.tests
    )

    feedback = "✅ All tests passed." if result["status"] == "PASS" else "❌ Some tests failed. Review failing tests and refactor accordingly."

    resp = EvaluateSubmissionResponse(
        run_id=run_id,
        status=result["status"],
        failed_tests=result["failed_tests"],
        errors=result["errors"],
        raw_log=result["raw_log"],
        feedback=feedback
    )

    log_event(run_id, "evaluate.response", resp.model_dump())
    return resp
