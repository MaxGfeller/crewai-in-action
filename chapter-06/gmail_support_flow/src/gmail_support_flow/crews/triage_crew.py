"""Triage crew - one agent, one task, single pydantic output."""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from gmail_support_flow.state import TriageDecision


@CrewBase
class TriageCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks_triage.yaml"

    @agent
    def triage_classifier(self) -> Agent:
        # LLM comes from the ``MODEL`` env var (see .env); CrewAI's Agent
        # auto-constructs an LLM from env when ``llm=`` is omitted.
        return Agent(
            config=self.agents_config["triage_classifier"],  # type: ignore[index]
            verbose=False,
        )

    @task
    def triage_task(self) -> Task:
        return Task(
            config=self.tasks_config["triage_task"],  # type: ignore[index]
            output_pydantic=TriageDecision,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore[attr-defined]
            tasks=self.tasks,  # type: ignore[attr-defined]
            process=Process.sequential,
            verbose=False,
        )
