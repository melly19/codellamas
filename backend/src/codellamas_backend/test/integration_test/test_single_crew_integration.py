import pytest
from unittest.mock import patch, MagicMock
from crewai import Process

from codellamas_backend.crews.crew_single import (
    CodellamasBackend,
    ContractSpec,
    ImplementationSpec,
    SpringBootExercise,
)
from codellamas_backend.schemas.files import ProjectFile


def make_backend():
    with patch("codellamas_backend.crews.crew_single.LLM"):
        return CodellamasBackend()


@pytest.mark.integration
class TestCodellamasBackendIntegration:
    """Tests real crewai object creation with mocked LLM"""

    def test_backend_initializes(self):
        backend = make_backend()
        assert backend is not None

    def test_contract_crew_is_sequential(self):
        backend = make_backend()
        crew = backend.contract_crew()
        assert crew.process == Process.sequential

    def test_implementation_crew_is_sequential(self):
        backend = make_backend()
        crew = backend.implementation_crew()
        assert crew.process == Process.sequential

    def test_review_crew_is_sequential(self):
        backend = make_backend()
        crew = backend.review_crew()
        assert crew.process == Process.sequential

    def test_contract_crew_has_one_task(self):
        backend = make_backend()
        crew = backend.contract_crew()
        assert len(crew.tasks) == 1

    def test_implementation_crew_has_one_task(self):
        backend = make_backend()
        crew = backend.implementation_crew()
        assert len(crew.tasks) == 1

    def test_review_crew_has_one_task(self):
        backend = make_backend()
        crew = backend.review_crew()
        assert len(crew.tasks) == 1

    def test_contract_crew_has_one_agent(self):
        backend = make_backend()
        crew = backend.contract_crew()
        assert len(crew.agents) == 1

    def test_generate_contract_task_has_output_json(self):
        with patch("codellamas_backend.crews.crew_single.Task") as mock_task:
            backend = make_backend()
            backend.generate_contract()
            kwargs = mock_task.call_args[1]
            assert kwargs["output_json"] == ContractSpec

    def test_generate_implementation_task_has_output_json(self):
        with patch("codellamas_backend.crews.crew_single.Task") as mock_task:
            backend = make_backend()
            backend.generate_implementation()
            kwargs = mock_task.call_args[1]
            assert kwargs["output_json"] == ImplementationSpec

    def test_review_solution_task_no_output_json(self):
        with patch("codellamas_backend.crews.crew_single.Task") as mock_task:
            backend = make_backend()
            backend.review_solution()
            kwargs = mock_task.call_args[1]
            assert "output_json" not in kwargs

    @patch("codellamas_backend.crews.crew_single.Crew")
    @patch("codellamas_backend.crews.crew_single.Task")
    @patch("codellamas_backend.crews.crew_single.Agent")
    def test_contract_crew_kickoff_called(self, mock_agent, mock_task, mock_crew):
        backend = make_backend()
        mock_crew.return_value.kickoff.return_value = MagicMock(
            json_dict={
                "problem_description": "Fix bug",
                "test_files": [],
                "paths_to_ex": [],
            }
        )
        backend.contract_crew().kickoff(inputs={
            "topic": "refactoring",
            "code_smells": "god class",
            "existing_codebase": "NONE",
        })
        mock_crew.return_value.kickoff.assert_called_once()