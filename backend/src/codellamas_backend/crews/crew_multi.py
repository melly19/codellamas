from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from typing import List
from pydantic import BaseModel, Field


# =========================
# Shared output models
# =========================

class ProjectFile(BaseModel):
    path: str = Field(
        ...,
        description="Relative path including package (e.g., 'src/main/java/com/example/demo/App.java')"
    )
    content: str


class SpringBootExercise(BaseModel):
    problem_description: str
    project_files: List[ProjectFile]
    test_files: List[ProjectFile]
    reference_solution_markdown: str


# =========================
# Multi-Agent Backend
# =========================

@CrewBase
class CodellamasBackendMulti:
    """
    Multi-agent implementation of the CodeLlamas backend.

    IMPORTANT DESIGN GOAL:
    - Expose the SAME interface as CodellamasBackend (single-agent)
    - Allow api.py to switch by mode without knowing internals
    """

    # Uses a DIFFERENT config set from single agent
    agents_config = "config/agents_multi.yaml"
    tasks_config = "config/tasks_multi.yaml"

    # -------------------------
    # Agents
    # -------------------------

    @agent
    def problem_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["problem_agent"],  # type: ignore[index]
            llm=LLM(model="ollama/phi4", base_url="http://localhost:11434"),
            verbose=True,
        )

    @agent
    def test_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["test_agent"],  # type: ignore[index]
            llm=LLM(model="ollama/phi4", base_url="http://localhost:11434"),
            verbose=True,
        )

    @agent
    def solution_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["solution_agent"],  # type: ignore[index]
            llm=LLM(model="ollama/phi4", base_url="http://localhost:11434"),
            verbose=True,
        )

    @agent
    def review_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["review_agent"],  # type: ignore[index]
            llm=LLM(model="ollama/phi4", base_url="http://localhost:11434"),
            verbose=True,
        )

    # -------------------------
    # Tasks
    # -------------------------

    @task
    def design_problem(self) -> Task:
        return Task(
            config=self.tasks_config["design_problem"],  # type: ignore[index]
        )

    @task
    def generate_tests(self) -> Task:
        return Task(
            config=self.tasks_config["generate_tests"],  # type: ignore[index]
        )

    @task
    def generate_solution(self) -> Task:
        return Task(
            config=self.tasks_config["generate_solution"],  # type: ignore[index]
            output_json=SpringBootExercise,
        )

    @task
    def review_solution_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_solution"],  # type: ignore[index]
        )

    # -------------------------
    # Crews (PUBLIC API)
    # -------------------------

    @crew
    def generation_crew(self) -> Crew:
        """
        Multi-agent generation crew.

        Pipeline:
        1. Problem agent designs the scenario
        2. Test agent defines expected behavior
        3. Solution agent produces smelly code + refactored solution

        NOTE:
        - Still returns SpringBootExercise to match single-agent API
        """
        return Crew(
            agents=[
                self.problem_agent(),
                self.test_agent(),
                self.solution_agent(),
            ],
            tasks=[
                self.design_problem(),
                self.generate_tests(),
                self.generate_solution(),
            ],
            process=Process.sequential,
            verbose=True,
        )

    @crew
    def review_crew(self) -> Crew:
        """
        Multi-agent review crew.

        For now:
        - Single review agent
        - Later you can split into: critic, smell-checker, pedagogy-checker
        """
        return Crew(
            agents=[self.review_agent()],
            tasks=[self.review_solution_task()],
            process=Process.sequential,
            verbose=True,
        )
