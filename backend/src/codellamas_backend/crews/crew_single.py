from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
# from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from pydantic import BaseModel
from codellamas_backend.schemas.files import ProjectFile
import os


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openrouter/qwen/qwen3-coder-30b-a3b-instruct"


# MODEL = "openrouter/openrouter/free"
# MODEL = "openrouter/qwen/qwen3-coder-30b-a3b-instruct"
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
class CodellamasBackend():
    agents_config = "../config/agents_single.yaml"
    tasks_config = "../config/tasks_single.yaml"

    @agent
    def general_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['general_agent'],
            llm=LLM(model=MODEL, base_url=BASE_URL, api_key=OPENROUTER_API_KEY, max_tokens=20000),
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
            config=self.tasks_config['review_solution'],  # type: ignore[index]
            output_json=ReviewResult
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
