from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from tools.custom_tool import JavaTestRunnerTool
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
class MultiAgentBackend():
    """CodellamasBackend crew with multi-agent implementation"""

    agents_config = "../config/multi_agent/agents.yaml"
    tasks_config = "../config/multi_agent/tasks.yaml"

    # Defining the agents
    @agent
    def problem_architect(self) -> Agent:
        return Agent(
            config=self.agents_config['problem_architect'],
            verbose=True
        )

    @agent
    def test_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['test_engineer'],
            verbose=True
        )

    @agent
    def smelly_developer(self) -> Agent:
        return Agent(
            config=self.agents_config['smelly_developer'],
            verbose=True
        )

    @agent
    def reference_solution_developer(self) -> Agent:
        return Agent(
            config=self.agents_config['reference_solution_developer'],
            verbose=True
        )

    @agent
    def test_runner(self) -> Agent:
        return Agent(
            config=self.agents_config['test_runner'],
            verbose=True,
            tools=[JavaTestRunnerTool()]
        )

    @agent
    def debug_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['debug_specialist'],
            verbose=True
        )

    @agent
    def quality_assurance(self) -> Agent:
        return Agent(
            config=self.agents_config['quality_assurance'],
            verbose=True
        )


    # Defining the tasks for the agents
    @task
    def define_problem(self) -> Task:
        return Task(
            config=self.tasks_config['define_problem'],
            agent=self.problem_architect()
        )


    @task
    def define_tests(self) -> Task:
        return Task(
            config=self.tasks_config['define_tests'],
            agent=self.test_engineer()
        )


    @task
    def implement_smelly_code(self) -> Task:
        return Task(
            config=self.tasks_config['implement_smelly_code'],
            agent=self.smelly_developer()
        )


    @task
    def run_tests_on_smelly_code(self) -> Task:
        return Task(
            config=self.tasks_config['run_tests_on_smelly_code'],
            agent=self.test_runner()
        )

    @task
    def patch_smelly_code(self) -> Task:
        return Task(
            config=self.tasks_config['patch_smelly_code'],
            agent=self.debug_specialist()
        )


    @task
    def generate_reference_solution(self) -> Task:
        return Task(
            config=self.tasks_config['generate_reference_solution'],
            agent=self.reference_solution_developer()
        )


    @task
    def run_tests_on_reference_solution(self) -> Task:
        return Task(
            config=self.tasks_config['run_tests_on_reference_solution'],
            agent=self.test_runner()
        )


    @task
    def patch_reference_solution(self) -> Task:
        return Task(
            config=self.tasks_config['patch_reference_solution'],
            agent=self.debug_specialist()
        )

    @task
    def audit_exercise(self) -> Task:
        return Task(
            config=self.tasks_config['audit_exercise'],
            agent=self.quality_assurance()
        )

    @task
    def check_functional_correctness(self) -> Task:
        return Task(
            config=self.tasks_config['check_functional_correctness'],
            agent=self.test_runner()
        )

    @task
    def evaluate_code_quality(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_code_quality'],
            agent=self.quality_assurance()
        )

    @task
    def generate_review_feedback(self) -> Task:
        return Task(
            config=self.tasks_config['generate_review_feedback'],
            agent=self.quality_assurance()
        )


    # Defining the crew
    @crew
    def generation_crew(self) -> Crew:
        return Crew(
            agents=[
                self.problem_architect(),
                self.test_engineer(),
                self.smelly_developer(),
                self.test_runner(),
                self.debug_specialist(),
                self.reference_solution_developer(),
                self.quality_assurance(),
            ],
            tasks=[
                self.define_problem(),
                self.define_tests(),
                self.implement_smelly_code(),
                self.run_tests_on_smelly_code(),
                self.patch_smelly_code(),
                self.generate_reference_solution(),
                self.run_tests_on_reference_solution(),
                self.patch_reference_solution(),
                self.audit_exercise(),
            ],
            process=Process.sequential,
            verbose=True
        )

    @crew
    def review_crew(self) -> Crew:
        return Crew(
            agents=[
                self.test_runner(),
                self.quality_assurance(),
            ],
            tasks=[
                self.check_functional_correctness(),
                self.evaluate_code_quality(),
                self.generate_review_feedback(),
            ],
            process=Process.sequential,
            verbose=True
        )
