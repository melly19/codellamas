from crewai import Agent
from llm.crewai_llm import build_crewai_llm

def build_agents():
    llm = build_crewai_llm()

    problem_agent = Agent(
        role="Problem Generator",
        goal="Generate a realistic refactoring/code review exercise problem description aligned with topic and selected smells.",
        backstory="You create realistic software engineering practice scenarios for Java Spring Boot projects.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    tests_agent = Agent(
        role="Test Case Generator",
        goal="Generate JUnit tests for the exercise that precisely validate correctness and are runnable via mvn test.",
        backstory="You write robust JUnit tests and think like a TDD engineer.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    solution_agent = Agent(
        role="Solution Generator",
        goal="Generate a correct Java solution/refactor that passes tests and addresses the selected smells.",
        backstory="You are a senior Java/Spring Boot engineer focused on clean code and correctness.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    debugger_agent = Agent(
        role="Debugger",
        goal="Fix failing tests by adjusting solution and/or tests while staying faithful to the problem statement.",
        backstory="You debug failing Maven/JUnit runs, using stack traces and failure output.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    review_agent = Agent(
        role="Reviewer",
        goal="Review the final problem, tests, and solution for consistency, correctness, and educational value.",
        backstory="You are a meticulous code reviewer and educator.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    return {
        "problem": problem_agent,
        "tests": tests_agent,
        "solution": solution_agent,
        "debugger": debugger_agent,
        "review": review_agent,
    }
