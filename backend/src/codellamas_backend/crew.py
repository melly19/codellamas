from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from pydantic import BaseModel, Field

class ProjectFile(BaseModel):
    path: str = Field(..., description="Relative path including package (e.g., 'src/main/java/com/example/demo/App.java')")
    content: str

class SpringBootExercise(BaseModel):
    problem_description: str
    project_files: List[ProjectFile]
    test_files: List[ProjectFile]
    reference_solution_markdown: str

@CrewBase
class CodellamasBackend():

    """CodellamasBackend crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def general_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['general_agent'], # type: ignore[index]
            llm=LLM(model="ollama/phi4", base_url="http://localhost:11434"),
            verbose=True,
        )

    @task
    def generate_exercise(self) -> Task:
        return Task(
            config=self.tasks_config['generate_exercise'], # type: ignore[index]
            output_json=SpringBootExercise
        )

    @task
    def review_solution(self) -> Task:
        return Task(
            config=self.tasks_config['review_solution'], # type: ignore[index]
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
