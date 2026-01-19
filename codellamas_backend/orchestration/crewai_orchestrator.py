import json
from crewai import Crew, Process
from app.api_models import GenerateExerciseRequest, GenerateExerciseResponse, ExerciseArtifact
from app.logging_utils import log_event
from app.settings import settings
from utils.context_packer import pack_context
from llm.json_guard import extract_json_object
from executor.maven_runner import run_maven_tests
from .crewai_agents import build_agents
from .crewai_tasks import task_problem, task_tests, task_solution, task_debug, task_review

def _to_json_str(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)

def generate_exercise_crewai(run_id: str, req: GenerateExerciseRequest) -> GenerateExerciseResponse:
    agents = build_agents()
    smells = ", ".join(req.code_smells)
    project_context = pack_context(req.project)

    # 1) Problem
    t1 = task_problem(agents["problem"], req.topic, smells, req.seed, project_context)
    crew1 = Crew(agents=[agents["problem"]], tasks=[t1], process=Process.sequential, verbose=False)
    raw_problem = str(crew1.kickoff())
    log_event(run_id, "crewai.problem.raw", {"raw_head": raw_problem[:1500]})
    problem_obj = extract_json_object(raw_problem)

    # 2) Tests
    t2 = task_tests(agents["tests"], _to_json_str(problem_obj), req.seed)
    crew2 = Crew(agents=[agents["tests"]], tasks=[t2], process=Process.sequential, verbose=False)
    raw_tests = str(crew2.kickoff())
    log_event(run_id, "crewai.tests.raw", {"raw_head": raw_tests[:1500]})
    tests_obj = extract_json_object(raw_tests)

    # 3) Solution
    t3 = task_solution(agents["solution"], _to_json_str(problem_obj), _to_json_str(tests_obj), req.seed)
    crew3 = Crew(agents=[agents["solution"]], tasks=[t3], process=Process.sequential, verbose=False)
    raw_solution = str(crew3.kickoff())
    log_event(run_id, "crewai.solution.raw", {"raw_head": raw_solution[:1500]})
    solution_obj = extract_json_object(raw_solution)

    # Execute + Debug loop
    last_exec = None
    for attempt in range(settings.MAX_DEBUG_RETRIES + 1):
        # Write generated solution+tests into workspace and run mvn test
        exec_result = run_maven_tests(
            run_id=run_id,
            project=req.project,
            override_files=[],  # don't overwrite student's files here; we are generating exercise artifacts
            inject_tests=tests_obj.get("tests", {}),
            # We inject solution by overriding relevant src/main/java files
            # We'll pass them as "override_files" using ProjectFile list shape in runner call:
        )

        # Our runner expects override_files as ProjectFile list; simplest:
        # Re-run with override_files set to solution files.
        from app.api_models import ProjectFile
        override_files = [ProjectFile(path=p, content=c) for p, c in solution_obj.get("solution", {}).items()]
        exec_result = run_maven_tests(
            run_id=run_id,
            project=req.project,
            override_files=override_files,
            inject_tests=tests_obj.get("tests", {}),
        )

        last_exec = exec_result
        log_event(run_id, "crewai.exec", {"attempt": attempt, "status": exec_result["status"], "errors": exec_result["errors"]})

        if exec_result["status"] == "PASS":
            break

        if attempt >= settings.MAX_DEBUG_RETRIES:
            break

        # 4) Debugger
        exec_report = json.dumps(
            {
                "status": exec_result["status"],
                "failed_tests": exec_result["failed_tests"],
                "errors": exec_result["errors"],
                "raw_log_head": (exec_result.get("raw_log", "")[:2500]),
            },
            ensure_ascii=False
        )

        tdbg = task_debug(
            agents["debugger"],
            _to_json_str(problem_obj),
            _to_json_str(tests_obj),
            _to_json_str(solution_obj),
            exec_report,
            req.seed,
        )
        crew_dbg = Crew(agents=[agents["debugger"]], tasks=[tdbg], process=Process.sequential, verbose=False)
        raw_fix = str(crew_dbg.kickoff())
        log_event(run_id, "crewai.debug.raw", {"raw_head": raw_fix[:1500]})
        fix_obj = extract_json_object(raw_fix)

        # Debugger returns updated tests/solution (and optional notes)
        tests_obj = fix_obj.get("tests_obj", tests_obj)
        solution_obj = fix_obj.get("solution_obj", solution_obj)

    # 5) Review
    trev = task_review(
        agents["review"],
        _to_json_str(problem_obj),
        _to_json_str(tests_obj),
        _to_json_str(solution_obj),
        req.seed
    )
    crew_rev = Crew(agents=[agents["review"]], tasks=[trev], process=Process.sequential, verbose=False)
    raw_review = str(crew_rev.kickoff())
    log_event(run_id, "crewai.review.raw", {"raw_head": raw_review[:1500]})
    review_obj = extract_json_object(raw_review)

    artifacts = ExerciseArtifact(
        problem_md=problem_obj["problem_md"],
        instructions_md=problem_obj.get("instructions_md", ""),
        tests=tests_obj.get("tests", {}),
        solution=solution_obj.get("solution", {}),
        review_notes=review_obj.get("review_notes", "")
    )

    diagnostics = {
        "mode": "multi",
        "debug_attempts": settings.MAX_DEBUG_RETRIES,
        "final_exec_status": last_exec["status"] if last_exec else "UNKNOWN",
        "final_exec_errors": last_exec["errors"] if last_exec else [],
    }

    return GenerateExerciseResponse(
        run_id=run_id,
        seed=req.seed,
        mode=req.mode,
        artifacts=artifacts,
        diagnostics=diagnostics
    )
