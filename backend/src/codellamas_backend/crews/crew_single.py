import os
from typing import List

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel

from codellamas_backend.schemas.files import ProjectFile


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openrouter/qwen/qwen3-coder-30b-a3b-instruct"
# MODEL = "gemini/gemini-3.1-flash-lite-preview"


# MODEL = "openrouter/z-ai/glm-4.5-air:free"
# MODEL = "openrouter/deepseek/deepseek-v3.2"


class SpringBootExercise(BaseModel):
    problem_description: str
    project_files: List[ProjectFile]
    test_files: List[ProjectFile]
    solution_explanation_md: str
    paths_to_ex: List[str]
    answers_list: List[ProjectFile]
    
class ReviewResult(BaseModel):
    problem_statement_clarity: str
    smell_incorporation: str
    
    avoids_unrelated_bad_practices: str
    naming_conventions: str
    structure_quality: str
    undergraduate_suitability: str

    minimal_boilerplate: str
    readability: str
    reasonable_optimisation: str

    overall_rating: float

@CrewBase
class CodellamasBackend:
    agents_config = "../config/agents_single.yaml"
    tasks_config = "../config/tasks_single.yaml"

    def __init__(
        self,
        model_name: str | None = None,
        api_endpoint: str | None = None,
        api_key: str | None = None,
    ):
        self.model_name = model_name or MODEL
        self.api_endpoint = api_endpoint or BASE_URL
        self.api_key = api_key or OPENROUTER_API_KEY

    @agent
    def general_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["general_agent"],
            llm=self.llm,
            timeout="1800s",
            verbose=True,
        )

    @task
    def generate_contract(self) -> Task:
        return Task(
            config=self.tasks_config["generate_contract"],
            output_json=ContractSpec,
        )

    @task
    def generate_implementation(self) -> Task:
        return Task(
            config=self.tasks_config["generate_implementation"],
            output_json=ImplementationSpec,
        )

    @task
    def review_solution(self) -> Task:
        return Task(
            config=self.tasks_config['review_solution'],  # type: ignore[index]
            output_json=ReviewResult
        )

    @crew
    def implementation_crew(self) -> Crew:
        return Crew(
            agents=[self.general_agent()],
            tasks=[self.generate_implementation()],
            process=Process.sequential,
            verbose=True,
        )

    @crew
    def review_crew(self) -> Crew:
        return Crew(
            agents=[self.general_agent()],
            tasks=[self.review_solution()],
            process=Process.sequential,
            verbose=True,
        )
