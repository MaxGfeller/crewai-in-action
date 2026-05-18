"""Billing specialist crew."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from gmail_support_flow.state import SpecialistOutput
from gmail_support_flow.tools import (
    GetCustomerProfileTool,
    GetRecentOrdersTool,
    SearchKbTool,
)


@CrewBase
class BillingCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks_billing.yaml"

    @agent
    def billing_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["billing_specialist"],  # type: ignore[index]
            tools=[
                GetCustomerProfileTool(),
                GetRecentOrdersTool(),
                SearchKbTool(),
            ],
            verbose=False,
        )

    @task
    def billing_task(self) -> Task:
        return Task(
            config=self.tasks_config["billing_task"],  # type: ignore[index]
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
