from crewai import Task
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

def task_problem(agent, topic: str, smells: str, seed: int, project_context: str):
    prompt = (PROMPTS_DIR / "crew_problem.md").read_text(encoding="utf-8").format(
        topic=topic, smells=smells, seed=seed, project_context=project_context
    )
    return Task(description=prompt, agent=agent, expected_output="A single JSON object.")

def task_tests(agent, problem_json: str, seed: int):
    prompt = (PROMPTS_DIR / "crew_tests.md").read_text(encoding="utf-8").format(
        problem_json=problem_json, seed=seed
    )
    return Task(description=prompt, agent=agent, expected_output="A single JSON object.")

def task_solution(agent, problem_json: str, tests_json: str, seed: int):
    prompt = (PROMPTS_DIR / "crew_solution.md").read_text(encoding="utf-8").format(
        problem_json=problem_json, tests_json=tests_json, seed=seed
    )
    return Task(description=prompt, agent=agent, expected_output="A single JSON object.")

def task_debug(agent, problem_json: str, tests_json: str, solution_json: str, exec_report: str, seed: int):
    prompt = (PROMPTS_DIR / "crew_debug.md").read_text(encoding="utf-8").format(
        problem_json=problem_json,
        tests_json=tests_json,
        solution_json=solution_json,
        exec_report=exec_report,
        seed=seed,
    )
    return Task(description=prompt, agent=agent, expected_output="A single JSON object.")

def task_review(agent, problem_json: str, tests_json: str, solution_json: str, seed: int):
    prompt = (PROMPTS_DIR / "crew_review.md").read_text(encoding="utf-8").format(
        problem_json=problem_json,
        tests_json=tests_json,
        solution_json=solution_json,
        seed=seed,
    )
    return Task(description=prompt, agent=agent, expected_output="A single JSON object.")
