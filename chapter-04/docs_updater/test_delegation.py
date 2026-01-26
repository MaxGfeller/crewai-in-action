#!/usr/bin/env python3
"""Test script to verify delegation from docs_updater to screenshotter works."""

from crewai import Agent, Task, Crew, Process
from crewai.mcp import MCPServerStdio

def test_delegation():
    print("Testing delegation from docs_updater to screenshotter...")
    print("-" * 60)

    # Create screenshotter agent (the one being delegated to)
    screenshotter = Agent(
        role="Application screenshot specialist",
        goal="""Navigate the web application through a browser and take screenshots.
        When you take a screenshot, report the exact file path returned by the tool.
        Web application URL: http://localhost:4100/
        Demo credentials: demo@example.com / password123""",
        backstory="You are an experienced browser automation specialist.",
        allow_delegation=False,
        verbose=True,
        mcps=[
            MCPServerStdio(
                command="npx",
                args=["@playwright/mcp@latest"],
            ),
        ],
    )

    # Create docs_updater agent (the one that delegates)
    docs_updater = Agent(
        role="Technical documentation writer",
        goal="Update documentation based on latest changes.",
        backstory="Expert technical writer.",
        allow_delegation=True,
        verbose=True,
    )

    # Create a task that requires delegation
    task = Task(
        description="""
        You need to update documentation about the dashboard.
        The dashboard screenshot needs to be updated.

        Use the "Delegate work to coworker" tool to ask the screenshotter agent
        to take a screenshot of the dashboard page at http://localhost:4100/.

        Report back the file path of the screenshot that the screenshotter provides.
        """,
        expected_output="The file path of the new dashboard screenshot",
        agent=docs_updater,
    )

    # Run the crew
    print("\n" + "=" * 60)
    print("Running delegation test...")
    print("=" * 60 + "\n")

    crew = Crew(
        agents=[docs_updater, screenshotter],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
        mcp_connect_timeout=90,
    )

    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("Result:")
    print(result)

if __name__ == "__main__":
    test_delegation()
