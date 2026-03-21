from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from typing import List
from pydantic import BaseModel
from codellamas_backend.schemas.files import ProjectFile
import os


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openrouter/qwen/qwen3-coder-30b-a3b-instruct"


class SpringBootExercise(BaseModel):
    problem_description: str
    project_files: List[ProjectFile]
    test_files: List[ProjectFile]
    solution_explanation_md: str
    paths_to_ex: List[str]
    answers_list: List[ProjectFile]


@CrewBase
class CodellamasBackend():
    agents_config = "../config/agents_single.yaml"
    tasks_config = "../config/tasks_single.yaml"

    def __init__(self, model_name: str = None, api_endpoint: str = None, api_key: str = None):
        self.model_name = model_name or MODEL
        self.api_endpoint = api_endpoint or BASE_URL
        self.api_key = api_key or OPENROUTER_API_KEY

    @agent
    def general_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['general_agent'],
            llm=LLM(model=self.model_name, base_url=self.api_endpoint, api_key=self.api_key, max_tokens=20000),
            timeout="1800s",
            verbose=True,
        )

    @task
    def generate_exercise(self) -> Task:
        return Task(
            config=self.tasks_config['generate_exercise'],
            output_json=SpringBootExercise
        )

    @task
    def review_solution(self) -> Task:
        return Task(
            config=self.tasks_config['review_solution'],
        )

    @crew
    def generation_crew(self) -> Crew:
        return Crew(
            agents=[self.general_agent()],
            tasks=[self.generate_exercise()],
            process=Process.sequential,
            verbose=True
        )

    @crew
    def review_crew(self) -> Crew:
        return Crew(
            agents=[self.general_agent()],
            tasks=[self.review_solution()],
            process=Process.sequential,
            verbose=True
        )
