#!/usr/bin/env python
import sys
import warnings

from docs_updater.crew import DocsUpdater

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew.
    """
    import os

    docs_path = os.environ.get('DOCS_PATH')
    if not docs_path:
        raise ValueError("DOCS_PATH environment variable must be set")

    inputs = {
        'latest_changes': 'In the dashboard, we have removed the average age column.',
    }

    crew_instance = DocsUpdater(docs_base_directory=docs_path)
    try:
        crew_instance.crew().kickoff(inputs=inputs)
    finally:
        crew_instance.close()


def _get_docs_path() -> str:
    import os

    docs_path = os.environ.get('DOCS_PATH')
    if not docs_path:
        raise ValueError("DOCS_PATH environment variable must be set")
    return docs_path


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        'latest_changes': 'In the dashboard, we have removed the average age column.',
    }
    crew_instance = DocsUpdater(docs_base_directory=_get_docs_path())
    try:
        crew_instance.crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")
    finally:
        crew_instance.close()

def replay():
    """
    Replay the crew execution from a specific task.
    """
    crew_instance = DocsUpdater(docs_base_directory=_get_docs_path())
    try:
        crew_instance.crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")
    finally:
        crew_instance.close()

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        'latest_changes': 'In the dashboard, we have removed the average age column.',
    }
    crew_instance = DocsUpdater(docs_base_directory=_get_docs_path())
    try:
        crew_instance.crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
    finally:
        crew_instance.close()
