"""Escalation crew - drafts the Slack summary; Flow method posts it."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from gmail_support_flow.state import EscalationSummary


@CrewBase
class EscalationCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks_escalation.yaml"

    @agent
    def escalation_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["escalation_writer"],  # type: ignore[index]
            verbose=False,
        )

    @task
    def escalation_task(self) -> Task:
        return Task(
            config=self.tasks_config["escalation_task"],  # type: ignore[index]
            output_pydantic=EscalationSummary,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore[attr-defined]
            tasks=self.tasks,  # type: ignore[attr-defined]
            process=Process.sequential,
            verbose=False,
        )
