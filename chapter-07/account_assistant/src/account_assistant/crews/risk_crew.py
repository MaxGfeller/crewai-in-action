"""Renewal-risk specialist crew."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from account_assistant.models import ContractRiskReview


@CrewBase
class RenewalRiskCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks_risk.yaml"

    @agent
    def renewal_risk_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["renewal_risk_specialist"],  # type: ignore[index]
            verbose=False,
        )

    @task
    def risk_task(self) -> Task:
        return Task(
            config=self.tasks_config["risk_task"],  # type: ignore[index]
            output_pydantic=ContractRiskReview,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore[attr-defined]
            tasks=self.tasks,  # type: ignore[attr-defined]
            process=Process.sequential,
            verbose=False,
        )
