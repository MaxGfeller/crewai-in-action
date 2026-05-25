"""Factory for the main conversational CrewAI agent."""

from __future__ import annotations

from crewai import Agent

from account_assistant.tools import (
    AnalyzeRenewalRiskTool,
    DraftFollowupEmailTool,
    LoadAccountContextTool,
    ProposeMeetingSlotsTool,
    StageFollowupTaskTool,
)


def build_main_agent() -> Agent:
    return Agent(
        role="Customer account assistant",
        goal=(
            "Hold a useful account-management conversation and call tools for "
            "account context, specialist analysis, scheduling, and staged actions."
        ),
        backstory=(
            "You are the primary conversational agent inside a business application. "
            "You coordinate with specialist tools, keep the user oriented, and avoid "
            "unapproved side effects."
        ),
        llm="gpt-5.4",
        tools=[
            LoadAccountContextTool(),
            AnalyzeRenewalRiskTool(),
            ProposeMeetingSlotsTool(),
            StageFollowupTaskTool(),
            DraftFollowupEmailTool(),
        ],
        respect_context_window=True,
        verbose=False,
    )
