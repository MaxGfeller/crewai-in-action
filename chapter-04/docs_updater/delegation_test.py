"""
Minimal example to test CrewAI agent delegation.

This tests whether an agent with allow_delegation=True can delegate
work to another agent in the crew without a pre-defined task.
"""

from crewai import Agent, Crew, Process, Task


# Agent that will receive delegated work
calculator = Agent(
    role="Calculator specialist",
    goal="Perform mathematical calculations accurately",
    backstory="You are a math expert who can perform any calculation.",
    allow_delegation=False,
    verbose=True,
)

# Agent that will delegate work
coordinator = Agent(
    role="Task coordinator",
    goal="Coordinate work by delegating to specialists when needed",
    backstory="You coordinate tasks and delegate specialized work to experts.",
    allow_delegation=True,  # This should give it DelegateWorkTool
    verbose=True,
)

# Single task - coordinator should delegate the math to calculator
task = Task(
    description="""
    You need to find out what 42 * 17 equals.

    IMPORTANT: You are not a math expert. Delegate this calculation
    to the "Calculator specialist" coworker and report their answer.

    Use the "Delegate work to coworker" tool to ask the Calculator specialist
    to perform this calculation.
    """,
    expected_output="The result of 42 * 17, obtained from the Calculator specialist",
    agent=coordinator,
)

# Create crew with both agents but only one task
crew = Crew(
    agents=[coordinator, calculator],
    tasks=[task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("=" * 60)
    print("Testing CrewAI Delegation")
    print("=" * 60)
    print()
    print("Coordinator agent should delegate math to Calculator agent")
    print()

    result = crew.kickoff()

    print()
    print("=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(result)
