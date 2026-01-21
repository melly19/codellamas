from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class CodellamasBackend():
    """CodellamasBackend crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def general_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['general_agent'], # type: ignore[index]
            verbose=True,
            max_execution_time=300
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def generate_exercise(self) -> Task:
        return Task(
            config=self.tasks_config['generate_exercise'], # type: ignore[index]
        )

    @task
    def review_solution(self) -> Task:
        return Task(
            config=self.tasks_config['review_solution'],
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
