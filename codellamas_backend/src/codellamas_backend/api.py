from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal, Any

from codellamas_backend.crew import CodellamasBackend

app = FastAPI(title="CodeLlamas Backend")

class ProjectFile(BaseModel):
    path: str
    content: str


class GenerateExerciseRequest(BaseModel):
    topic: str = "Online Shopping"
    code_smells: List[str] = Field(default_factory=lambda: ["Feature Envy"])
    seed: int = 42
    mode: Literal["single", "multi"] = "multi"
    # VS Code should send selected project files (pom.xml + relevant src/**)
    project_files: List[ProjectFile] = Field(default_factory=list)


class GenerateExerciseArtifacts(BaseModel):
    problem_md: str
    instructions_md: str = ""
    tests: Dict[str, str] = Field(default_factory=dict)      # path -> content
    solution: Dict[str, str] = Field(default_factory=dict)   # path -> content
    review_notes: str = ""


class GenerateExerciseResponse(BaseModel):
    run_id: str
    artifacts: GenerateExerciseArtifacts
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class EvaluateSubmissionRequest(BaseModel):
    run_id: Optional[str] = None
    seed: int = 42
    project_files: List[ProjectFile] = Field(default_factory=list)
    student_files: List[ProjectFile] = Field(default_factory=list)
    tests: Dict[str, str] = Field(default_factory=dict)
    # Optional: you can pass problem context if you want an LLM feedback summary
    problem_md: str = ""


class EvaluateSubmissionResponse(BaseModel):
    run_id: str
    status: Literal["PASS", "FAIL"]
    failed_tests: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    raw_log_head: str = ""
    feedback: str = ""


def _make_run_id() -> str:
    # simple run id, replace with uuid if you like
    import uuid
    return str(uuid.uuid4())


def _safe_json_extract(text: str) -> dict:
    """
    Very lightweight JSON extraction:
    if your Crew output is already strict JSON, json.loads works.
    If not, this tries to find the first {...} block.
    """
    import json
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Crew output.")
    for end in range(len(text) - 1, start, -1):
        if text[end] == "}":
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                continue
    raise ValueError("Could not parse JSON from Crew output.")


@app.post("/generate/exercise", response_model=GenerateExerciseResponse)
async def generate_exercise(body: GenerateExerciseRequest):
    run_id = _make_run_id()

    inputs = {
        "topic": body.topic,
        # keep compatibility with existing YAML expecting `code_smell`
        "code_smell": ", ".join(body.code_smells),
        "code_smells": body.code_smells,
        "seed": body.seed,
        # pack project context into a big string for the prompt (minimal for now)
        "project_context": "\n\n".join(
            [f"### FILE: {f.path}\n{f.content}" for f in body.project_files]
        ),
    }

    try:
        raw_result = CodellamasBackend().generation_crew().kickoff(inputs=inputs)
        raw_text = str(raw_result)

        # Expect your YAML task to output strict JSON with:
        # { problem_md, instructions_md, tests: {..}, solution: {..} }
        obj = _safe_json_extract(raw_text)

        artifacts = GenerateExerciseArtifacts(
            problem_md=obj.get("problem_md", raw_text),
            instructions_md=obj.get("instructions_md", ""),
            tests=obj.get("tests", {}) or {},
            solution=obj.get("solution", {}) or {},
            review_notes=obj.get("review_notes", ""),
        )

        return GenerateExerciseResponse(
            run_id=run_id,
            artifacts=artifacts,
            diagnostics={
                "mode": body.mode,
                "seed": body.seed,
                "notes": "Execution/debug loop not wired yet (next step: Maven tool).",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate/submission", response_model=EvaluateSubmissionResponse)
async def evaluate_submission(body: EvaluateSubmissionRequest):
    run_id = body.run_id or _make_run_id()

    # For now, keep your teammate's LLM-based review path, BUT
    # we also prepare the integration point for real Maven execution.
    inputs = {
        "problem_description": body.problem_md,
        "original_code": "",  # optional: could include baseline later
        "student_code": "\n\n".join([f"### FILE: {f.path}\n{f.content}" for f in body.student_files]),
        "test_results": "",   # placeholder until Maven execution is wired
        "seed": body.seed,
    }

    try:
        raw_result = CodellamasBackend().review_crew().kickoff(inputs=inputs)
        raw_text = str(raw_result)

        # Until Maven tool is integrated, status is unknown; treat as FAIL-safe.
        # Once Maven runner is plugged in, you'll set PASS/FAIL from real tests.
        return EvaluateSubmissionResponse(
            run_id=run_id,
            status="FAIL",
            failed_tests=[],
            errors=["Maven execution not integrated yet; this is LLM-only review."],
            raw_log_head="",
            feedback=raw_text[:4000],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GenerateRequest(BaseModel):
    topic: str = "Online Shopping"
    code_smell: str = "Feature Envy"


class EvaluateRequest(BaseModel):
    problem_description: str
    original_code: str
    student_code: str
    test_results: str


@app.post("/generate")
async def generate_exercise_legacy(body: GenerateRequest):
    upgraded = GenerateExerciseRequest(
        topic=body.topic,
        code_smells=[body.code_smell],
        project_files=[],
        mode="multi",
    )
    return await generate_exercise(upgraded)


@app.post("/evaluate")
async def review_solution_legacy(body: EvaluateRequest):
    upgraded = EvaluateSubmissionRequest(
        problem_md=body.problem_description,
        student_files=[ProjectFile(path="STUDENT_CODE.java", content=body.student_code)],
    )
    return await evaluate_submission(upgraded)


@app.get("/")
async def root():
    return {"status": "ok"}
