"""Technical specialist crew."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from gmail_support_flow.state import SpecialistOutput
from gmail_support_flow.tools import CheckActiveIncidentsTool, SearchKbTool


@CrewBase
class TechnicalCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks_technical.yaml"

    @agent
    def technical_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["technical_specialist"],  # type: ignore[index]
            tools=[CheckActiveIncidentsTool(), SearchKbTool()],
            verbose=False,
        )

    @task
    def technical_task(self) -> Task:
        return Task(
            config=self.tasks_config["technical_task"],  # type: ignore[index]
            output_pydantic=SpecialistOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore[attr-defined]
            tasks=self.tasks,  # type: ignore[attr-defined]
            process=Process.sequential,
            verbose=False,
        )
