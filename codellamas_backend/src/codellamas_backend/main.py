#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from codellamas_backend.crew import CodellamasBackend

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def generate():
    """
    Step 1: Generate a new exercise.
    """
    inputs = {
        'topic': 'Online Shopping',
        'code_smell': 'Feature Envy'
    }

    print(f"Generating exercise for {inputs['topic']}...")

    try:
        result = CodellamasBackend().generation_crew().kickoff(inputs=inputs)
        print("Exercise generated successfully!")
        return result
    except Exception as e:
        raise Exception(f"An error occurred while generating the exercise: {e}")


def evaluate():
    """
    Step 2: Evaluate a student's solution.
    """

    inputs = {
        'problem_description': 'asd',
        'original_code': 'sdasd',
        'student_code': '... (code passed from VS Code) ...',
        'test_results': 'Tests passed: 5/5'
    }

    print("Evaluating student solution...")
    
    try:
        result = CodellamasBackend().evaluation_crew().kickoff(inputs=inputs)
        print("Evaluation completed!")
        return result
    except Exception as e:
        raise Exception(f"An error occurred while evaluating the solution: {e}")

# def run():
#     """
#     Run the crew.
#     """
#     inputs = {
#         'topic': 'Library',
#         'code_smell': 'Duplicate method'
#     }

#     try:
#         CodellamasBackend().crew().kickoff(inputs=inputs)
#     except Exception as e:
#         raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        'topic': 'Shopping',
        'code_smell': 'Long method'
    }
    try:
        CodellamasBackend().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        CodellamasBackend().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        'topic': 'Shopping',
        'code_smell': 'Long method'
    }

    try:
        CodellamasBackend().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "Shopping",
        "code_smell": "Long method"
    }

    try:
        result = CodellamasBackend().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
