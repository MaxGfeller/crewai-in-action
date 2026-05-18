"""Feature-request crew."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from gmail_support_flow.state import SpecialistOutput


@CrewBase
class FeatureRequestCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks_feature_request.yaml"

    @agent
    def feature_request_logger(self) -> Agent:
        return Agent(
            config=self.agents_config["feature_request_logger"],  # type: ignore[index]
            verbose=False,
        )

    @task
    def feature_request_task(self) -> Task:
        return Task(
            config=self.tasks_config["feature_request_task"],  # type: ignore[index]
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
