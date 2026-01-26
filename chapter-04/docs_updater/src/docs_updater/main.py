#!/usr/bin/env python
import sys
import warnings
import atexit

from docs_updater.crew import DocsUpdater
from docs_updater.tools.browser_tools import close_browser

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Ensure browser is closed on exit
atexit.register(close_browser)


def run():
    """
    Run the crew.
    """
    docs_path = '/Users/mg/projects/crewai-book-examples/chapter-04/demo-docs'

    inputs = {
        'latest_changes': 'In the dashboard, we have removed the average age column.',
    }

    try:
        DocsUpdater(docs_base_directory=docs_path).crew().kickoff(inputs=inputs)
    finally:
        close_browser()


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs"
    }
    try:
        DocsUpdater().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        DocsUpdater().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs"
    }
    try:
        DocsUpdater().crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")
