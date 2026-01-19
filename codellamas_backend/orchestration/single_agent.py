from pathlib import Path
from app.api_models import GenerateExerciseRequest, GenerateExerciseResponse, ExerciseArtifact
from app.logging_utils import log_event
from utils.context_packer import pack_context
from llm.json_guard import extract_json_object
from llm.crewai_llm import build_crewai_llm

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "single_agent_exercise.md"

def generate_exercise_single(run_id: str, req: GenerateExerciseRequest) -> GenerateExerciseResponse:
    ctx = pack_context(req.project)
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    prompt = prompt_template.format(
        topic=req.topic,
        smells=", ".join(req.code_smells),
        seed=req.seed,
        project_context=ctx
    )

    log_event(run_id, "single.prompt", {"chars": len(prompt)})

    llm = build_crewai_llm()
    raw = llm.invoke(prompt).content  # LangChain Chat Model response
    log_event(run_id, "single.raw", {"raw_head": raw[:1500]})

    data = extract_json_object(raw)

    artifacts = ExerciseArtifact(
        problem_md=data["problem_md"],
        instructions_md=data["instructions_md"],
        tests=data["tests"],
        solution=data["solution"],
        review_notes=data.get("review_notes", "")
    )

    return GenerateExerciseResponse(
        run_id=run_id,
        seed=req.seed,
        mode=req.mode,
        artifacts=artifacts,
        diagnostics={"llm": "ollama", "model": "phi4", "mode": "single"}
    )
