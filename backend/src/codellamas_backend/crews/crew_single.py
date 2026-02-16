from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from pydantic import BaseModel, Field
import os


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "openrouter/qwen/qwen3-coder-30b-a3b-instruct"
# MODEL = "openrouter/deepseek/deepseek-v3.2"

class ProjectFile(BaseModel):
    path: str = Field(..., description="Relative path including package (e.g., 'src/main/java/com/example/demo/App.java')")
    content: str



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

    @agent
    def general_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['general_agent'],  # type: ignore[index]
            # llm=LLM(model="ollama/phi4", base_url="http://localhost:11434"),
            llm = LLM(model=MODEL, base_url=BASE_URL,api_key=OPENROUTER_API_KEY, max_tokens=20000),
            timeout="1800s",
            verbose=True,
        )

    @task
    def generate_exercise(self) -> Task:
        return Task(
            # type: ignore[index]
            config=self.tasks_config['generate_exercise'],
            output_json=SpringBootExercise
        )

    @task
    def review_solution(self) -> Task:
        return Task(
            config=self.tasks_config['review_solution'],  # type: ignore[index]
        )

    @crew
    def generation_crew(self) -> Crew:
        """Creates the generation crew"""
        return Crew(
            agents=[self.general_agent()],
            tasks=[self.generate_exercise()],
            process=Process.sequential,
            verbose=True
        )

    @crew
    def review_crew(self) -> Crew:
        """Creates the evaluation crew"""
        return Crew(
            agents=[self.general_agent()],
            tasks=[self.review_solution()],
            process=Process.sequential,
            verbose=True
        )
