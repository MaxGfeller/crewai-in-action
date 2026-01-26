#!/usr/bin/env python3
"""Test script to run the screenshotter agent directly and see what tools it has."""

from crewai import Agent, Task, Crew
from crewai.mcp import MCPServerStdio

def test_screenshotter():
    print("Creating screenshotter agent with MCP tools...")
    print("-" * 50)

    # Create the agent exactly as defined in crew.py
    screenshotter = Agent(
        role="Application screenshot specialist",
        goal="""Navigate the web application through a browser and take screenshots.
        When you take a screenshot, report the exact file path returned by the tool.""",
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

    # Print what tools the agent thinks it has
    print(f"\nAgent tools: {screenshotter.tools}")
    print(f"Number of tools: {len(screenshotter.tools) if screenshotter.tools else 0}")

    if screenshotter.tools:
        print("\nTool names:")
        for tool in screenshotter.tools:
            print(f"  - {getattr(tool, 'name', str(tool))}")

    # Create a simple task
    task = Task(
        description="""
        Navigate to http://localhost:4100/ and take a screenshot of the page.
        Report the exact file path where the screenshot was saved.
        """,
        expected_output="The file path of the screenshot",
        agent=screenshotter,
    )

    # Run the crew
    print("\n" + "=" * 50)
    print("Running the screenshotter task...")
    print("=" * 50 + "\n")

    crew = Crew(
        agents=[screenshotter],
        tasks=[task],
        verbose=True,
        mcp_connect_timeout=90,
    )

    result = crew.kickoff()
    print("\n" + "=" * 50)
    print("Result:")
    print(result)

if __name__ == "__main__":
    test_screenshotter()
