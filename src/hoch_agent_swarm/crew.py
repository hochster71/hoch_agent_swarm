from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
import os


@CrewBase
class HochAgentSwarm():
    """HochAgentSwarm crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @property
    def local_llm(self) -> LLM:
        model_name = os.getenv("MODEL", "ollama/llama3.1:8b")
        base_url = os.getenv("API_BASE", "http://localhost:11434")
        return LLM(
            model=model_name,
            base_url=base_url,
        )

    @agent
    def asset_mapper(self) -> Agent:
        return Agent(
            config=self.agents_config['asset_mapper'], # type: ignore[index]
            llm=self.local_llm,
            verbose=True
        )

    @agent
    def swarm_architect(self) -> Agent:
        return Agent(
            config=self.agents_config['swarm_architect'], # type: ignore[index]
            llm=self.local_llm,
            verbose=True
        )

    @agent
    def agent_combinator(self) -> Agent:
        return Agent(
            config=self.agents_config['agent_combinator'], # type: ignore[index]
            llm=self.local_llm,
            verbose=True
        )

    @agent
    def security_operator(self) -> Agent:
        return Agent(
            config=self.agents_config['security_operator'], # type: ignore[index]
            llm=self.local_llm,
            verbose=True
        )

    @agent
    def execution_planner(self) -> Agent:
        return Agent(
            config=self.agents_config['execution_planner'], # type: ignore[index]
            llm=self.local_llm,
            verbose=True
        )

    @agent
    def synthesis_director(self) -> Agent:
        return Agent(
            config=self.agents_config['synthesis_director'], # type: ignore[index]
            llm=self.local_llm,
            verbose=True
        )

    @agent
    def antigravity_integration_operator(self) -> Agent:
        return Agent(
            config=self.agents_config['antigravity_integration_operator'], # type: ignore[index]
            llm=self.local_llm,
            verbose=True
        )

    @task
    def map_assets_task(self) -> Task:
        # Root task: no prior context required
        return Task(
            config=self.tasks_config['map_assets_task'], # type: ignore[index]
        )

    @task
    def design_architecture_task(self) -> Task:
        # Depends on discovered asset map
        return Task(
            config=self.tasks_config['design_architecture_task'], # type: ignore[index]
            context=[self.map_assets_task()],
        )

    @task
    def assemble_agents_task(self) -> Task:
        # Depends on architecture design to know which agent wrappers to build
        return Task(
            config=self.tasks_config['assemble_agents_task'], # type: ignore[index]
            context=[self.design_architecture_task()],
        )

    @task
    def audit_security_task(self) -> Task:
        # Depends on assembled agent configs to audit their tool access and bounds
        return Task(
            config=self.tasks_config['audit_security_task'],  # type: ignore[index]
            context=[self.assemble_agents_task()],
        )

    @task
    def plan_execution_task(self) -> Task:
        # Depends on security audit clearance before scheduling execution
        return Task(
            config=self.tasks_config['plan_execution_task'], # type: ignore[index]
            context=[self.audit_security_task()],
        )

    @task
    def direct_synthesis_task(self) -> Task:
        # Depends on execution plan to compile release packet
        return Task(
            config=self.tasks_config['direct_synthesis_task'], # type: ignore[index]
            context=[self.plan_execution_task()],
        )

    @task
    def antigravity_integration_task(self) -> Task:
        # Depends on all prior outputs: uses synthesis report as primary source
        return Task(
            config=self.tasks_config['antigravity_integration_task'],  # type: ignore[index]
            context=[self.direct_synthesis_task()],
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
