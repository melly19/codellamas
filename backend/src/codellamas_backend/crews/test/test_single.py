import os

from crewai import Process
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError, BaseModel

from codellamas_backend.crews.crew_single import (
    CodellamasBackend,
    ContractSpec,
    ImplementationSpec,
    SpringBootExercise,
)
from codellamas_backend.schemas.files import ProjectFile
from typing import List



# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_project_file(path="src/App.java", content="class App {}") -> ProjectFile:
    return ProjectFile(path=path, content=content)


def make_crew_backend(**kwargs) -> CodellamasBackend:
    with patch("codellamas_backend.crews.crew_single.LLM"):
        return CodellamasBackend(**kwargs)


# ─────────────────────────────────────────────
# ContractSpec
# ─────────────────────────────────────────────

class TestContractSpec:
    def test_valid(self):
        spec = ContractSpec(
            problem_description="Fix the bug",
            test_files=[make_project_file()],
            paths_to_ex=["src/App.java"],
        )
        assert spec.problem_description == "Fix the bug"

    def test_missing_problem_description_raises(self):
        with pytest.raises(ValidationError):
            ContractSpec(test_files=[], paths_to_ex=[])

    def test_missing_test_files_raises(self):
        with pytest.raises(ValidationError):
            ContractSpec(problem_description="desc", paths_to_ex=[])

    def test_missing_paths_to_ex_raises(self):
        with pytest.raises(ValidationError):
            ContractSpec(problem_description="desc", test_files=[])

    def test_empty_lists_allowed(self):
        spec = ContractSpec(problem_description="desc", test_files=[], paths_to_ex=[])
        assert spec.test_files == []
        assert spec.paths_to_ex == []

    def test_multiple_test_files(self):
        files = [make_project_file(f"Test{i}.java") for i in range(3)]
        spec = ContractSpec(problem_description="desc", test_files=files, paths_to_ex=[])
        assert len(spec.test_files) == 3


# # ─────────────────────────────────────────────
# # ImplementationSpec
# # ─────────────────────────────────────────────

class TestImplementationSpec:
    def test_valid(self):
        spec = ImplementationSpec(
            project_files=[make_project_file()],
            solution_explanation_md="## Solution",
            answers_list=[make_project_file()],
        )
        assert spec.solution_explanation_md == "## Solution"

    def test_missing_project_files_raises(self):
        with pytest.raises(ValidationError):
            ImplementationSpec(solution_explanation_md="x", answers_list=[])

    def test_missing_solution_explanation_raises(self):
        with pytest.raises(ValidationError):
            ImplementationSpec(project_files=[], answers_list=[])

    def test_missing_answers_list_raises(self):
        with pytest.raises(ValidationError):
            ImplementationSpec(project_files=[], solution_explanation_md="x")

    def test_empty_lists_allowed(self):
        spec = ImplementationSpec(
            project_files=[], solution_explanation_md="", answers_list=[]
        )
        assert spec.project_files == []


# ─────────────────────────────────────────────
# SpringBootExercise
# ─────────────────────────────────────────────

class TestSpringBootExercise:
    def test_valid(self):
        spec = SpringBootExercise(
            problem_description="desc",
            project_files=[make_project_file()],
            test_files=[make_project_file()],
            solution_explanation_md="## sol",
            paths_to_ex=["src/App.java"],
            answers_list=[make_project_file()],
        )
        assert spec.problem_description == "desc"

    def test_missing_any_field_raises(self):
        with pytest.raises(ValidationError):
            SpringBootExercise(problem_description="desc")

    def test_empty_lists_allowed(self):
        spec = SpringBootExercise(
            problem_description="desc",
            project_files=[],
            test_files=[],
            solution_explanation_md="",
            paths_to_ex=[],
            answers_list=[],
        )
        assert spec.project_files == []


# # ─────────────────────────────────────────────
# # CodellamasBackend.__init__
# # ─────────────────────────────────────────────

class TestCodellamasBackendInit:
    def test_defaults_to_env_and_constants(self):
        with patch("codellamas_backend.crews.crew_single.OPENROUTER_API_KEY", "test-key"):
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
                with patch("codellamas_backend.crews.crew_single.LLM") as mock_llm:
                    crew = CodellamasBackend()
                    assert crew.api_key == "test-key"

    def test_custom_model_name(self):
        with patch("codellamas_backend.crews.crew_single.LLM"):
            crew = CodellamasBackend(model_name="gpt-4")
            assert crew.model_name == "gpt-4"

    def test_custom_api_endpoint(self):
        with patch("codellamas_backend.crews.crew_single.LLM"):
            crew = CodellamasBackend(api_endpoint="https://custom.api.com")
            assert crew.api_endpoint == "https://custom.api.com"

    def test_custom_api_key(self):
        with patch("codellamas_backend.crews.crew_single.LLM"):
            crew = CodellamasBackend(api_key="my-secret-key")
            assert crew.api_key == "my-secret-key"

    def test_llm_created_with_correct_params(self):
        with patch("codellamas_backend.crews.crew_single.LLM") as mock_llm:
            CodellamasBackend(model_name="claude-3", api_key="key", api_endpoint="https://ep.com")
            mock_llm.assert_called_once_with(
                model="claude-3",
                base_url="https://ep.com",
                api_key="key",
                request_timeout=1800,
                max_tokens=24000,
            )

    def test_none_model_falls_back_to_constant(self):
        with patch("codellamas_backend.crews.crew_single.MODEL", "test-model"):
            with patch("codellamas_backend.crews.crew_single.LLM"):
                crew = CodellamasBackend(model_name=None)
                assert crew.model_name == "test-model"  # MODEL constant default


# # ─────────────────────────────────────────────
# # CodellamasBackend.general_agent
# # ─────────────────────────────────────────────

class TestGeneralAgent:
    def setup_method(self):
        self.backend = make_crew_backend()

    def test_returns_something(self):
        result = self.backend.general_agent()
        assert result is not None

    def test_general_agent_returns_agent_instance(self):
        from crewai import Agent
        result = self.backend.general_agent()
        assert isinstance(result, Agent)

    def test_agent_has_correct_llm(self):
        result = self.backend.general_agent()
        assert result.llm is not None

    def test_agent_is_verbose(self):
        result = self.backend.general_agent()
        assert result.verbose is True

    def test_general_agent_role_from_config(self):
        result = self.backend.general_agent()
        # role comes from agents_single.yaml
        assert result.role is not None
        assert isinstance(result.role, str)
        assert len(result.role) > 0


# # ─────────────────────────────────────────────
# # CodellamasBackend tasks
# # ─────────────────────────────────────────────

class TestTasks:
    def setup_method(self):
        self.backend = make_crew_backend()

    @patch("codellamas_backend.crews.crew_single.Task")
    def test_generate_contract_output_json(self, mock_task):
        self.backend.generate_contract()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == ContractSpec

    @patch("codellamas_backend.crews.crew_single.Task")
    def test_generate_implementation_output_json(self, mock_task):
        self.backend.generate_implementation()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == ImplementationSpec

    @patch("codellamas_backend.crews.crew_single.Task")
    def test_review_solution_no_output_json(self, mock_task):
        self.backend.review_solution()
        kwargs = mock_task.call_args[1]
        assert "output_json" not in kwargs

    @patch("codellamas_backend.crews.crew_single.Task")
    def test_generate_contract_returns_task(self, mock_task):
        result = self.backend.generate_contract()
        assert result == mock_task.return_value


# # ─────────────────────────────────────────────
# # CodellamasBackend crews
# # ─────────────────────────────────────────────

class TestCrews:
    def setup_method(self):
        self.backend = make_crew_backend()

    @patch("codellamas_backend.crews.crew_single.Crew")
    @patch("codellamas_backend.crews.crew_single.Task")
    @patch("codellamas_backend.crews.crew_single.Agent")
    def test_contract_crew_uses_sequential(self, mock_agent, mock_task, mock_crew):
        self.backend.contract_crew()
        kwargs = mock_crew.call_args[1]
        assert kwargs["process"] == Process.sequential

    @patch("codellamas_backend.crews.crew_single.Crew")
    @patch("codellamas_backend.crews.crew_single.Task")
    @patch("codellamas_backend.crews.crew_single.Agent")
    def test_contract_crew_is_verbose(self, mock_agent, mock_task, mock_crew):
        self.backend.contract_crew()
        kwargs = mock_crew.call_args[1]
        assert kwargs["verbose"] is True

    @patch("codellamas_backend.crews.crew_single.Crew")
    @patch("codellamas_backend.crews.crew_single.Task")
    @patch("codellamas_backend.crews.crew_single.Agent")
    def test_implementation_crew_uses_sequential(self, mock_agent, mock_task, mock_crew):
        self.backend.implementation_crew()
        kwargs = mock_crew.call_args[1]
        assert kwargs["process"] == Process.sequential

    @patch("codellamas_backend.crews.crew_single.Crew")
    @patch("codellamas_backend.crews.crew_single.Task")
    @patch("codellamas_backend.crews.crew_single.Agent")
    def test_review_crew_uses_sequential(self, mock_agent, mock_task, mock_crew):
        self.backend.review_crew()
        kwargs = mock_crew.call_args[1]
        assert kwargs["process"] == Process.sequential

    @patch("codellamas_backend.crews.crew_single.Crew")
    @patch("codellamas_backend.crews.crew_single.Task")
    @patch("codellamas_backend.crews.crew_single.Agent")
    def test_contract_crew_returns_crew(self, mock_agent, mock_task, mock_crew):
        result = self.backend.contract_crew()
        assert result == mock_crew.return_value