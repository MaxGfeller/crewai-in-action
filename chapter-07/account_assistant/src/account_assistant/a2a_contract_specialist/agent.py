"""Optional A2A specialist setup.

The main chapter path delegates to a local specialist crew through a tool.
This file shows the small change readers make when that specialist is owned
by another service and exposed through A2A.
"""

from __future__ import annotations

from crewai import Agent
from crewai.a2a import A2AClientConfig, A2AServerConfig


def build_contract_risk_server_agent() -> Agent:
    return Agent(
        role="Contract risk specialist",
        goal="Analyze contract and renewal risk for account teams.",
        backstory=(
            "You are a remote specialist service. You receive structured renewal "
            "context and return structured risk findings."
        ),
        llm="gpt-5.4",
        a2a=A2AServerConfig(
            url="http://127.0.0.1:8091",
            name="Contract Risk Specialist",
            description="Reviews renewal contracts and account signals for risk.",
            version="0.1.0",
            default_input_modes=["application/json"],
            default_output_modes=["application/json"],
        ),
    )


def build_contract_risk_client_agent() -> Agent:
    return Agent(
        role="Risk delegation coordinator",
        goal="Delegate contract-risk analysis to the remote A2A specialist.",
        backstory="You call the A2A specialist when contract analysis is needed.",
        llm="gpt-5.4",
        a2a=A2AClientConfig(
            endpoint="http://127.0.0.1:8091/.well-known/agent-card.json",
            timeout=90,
            max_turns=3,
            fail_fast=False,
            accepted_output_modes=["application/json"],
        ),
    )
