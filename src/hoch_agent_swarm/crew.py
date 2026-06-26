from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent


@CrewBase
class HochAgentSwarm():
    """HochAgentSwarm crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def asset_mapper(self) -> Agent:
        return Agent(
            config=self.agents_config['asset_mapper'], # type: ignore[index]
            verbose=True
        )

    @agent
    def swarm_architect(self) -> Agent:
        return Agent(
            config=self.agents_config['swarm_architect'], # type: ignore[index]
            verbose=True
        )

    @agent
    def agent_combinator(self) -> Agent:
        return Agent(
            config=self.agents_config['agent_combinator'], # type: ignore[index]
            verbose=True
        )

    @agent
    def security_operator(self) -> Agent:
        return Agent(
            config=self.agents_config['security_operator'], # type: ignore[index]
            verbose=True
        )

    @agent
    def execution_planner(self) -> Agent:
        return Agent(
            config=self.agents_config['execution_planner'], # type: ignore[index]
            verbose=True
        )

    @agent
    def synthesis_director(self) -> Agent:
        return Agent(
            config=self.agents_config['synthesis_director'], # type: ignore[index]
            verbose=True
        )

    @agent
    def antigravity_integration_operator(self) -> Agent:
        return Agent(
            config=self.agents_config['antigravity_integration_operator'], # type: ignore[index]
            verbose=True
        )

    @task
    def map_assets_task(self) -> Task:
        return Task(
            config=self.tasks_config['map_assets_task'], # type: ignore[index]
        )

    @task
    def design_architecture_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_architecture_task'], # type: ignore[index]
        )

    @task
    def assemble_agents_task(self) -> Task:
        return Task(
            config=self.tasks_config['assemble_agents_task'], # type: ignore[index]
        )

    @task
    def audit_security_task(self) -> Task:
        return Task(
            config=self.tasks_config['audit_security_task'], # type: ignore[index]
        )

    @task
    def plan_execution_task(self) -> Task:
        return Task(
            config=self.tasks_config['plan_execution_task'], # type: ignore[index]
        )

    @task
    def direct_synthesis_task(self) -> Task:
        return Task(
            config=self.tasks_config['direct_synthesis_task'], # type: ignore[index]
        )

    @task
    def antigravity_integration_task(self) -> Task:
        return Task(
            config=self.tasks_config['antigravity_integration_task'], # type: ignore[index]
            output_file='artifacts/antigravity/antigravity_execution_plan.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the HochAgentSwarm crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
