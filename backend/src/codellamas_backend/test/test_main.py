import sys
import json
import pytest
from unittest.mock import patch, MagicMock


from codellamas_backend.main import (
    generate,
    review,
    train,
    replay,
    test as main_test_func,
    run_with_trigger,
)


# ─────────────────────────────────────────────
# generate
# ─────────────────────────────────────────────

class TestGenerate:
    @patch("codellamas_backend.main.CodellamasBackend")
    def test_returns_result_on_success(self, mock_backend):
        mock_backend.return_value.contract_crew.return_value.kickoff.return_value = "result"
        result = generate()
        assert result == "result"

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_kickoff_called_with_correct_inputs(self, mock_backend):
        mock_backend.return_value.contract_crew.return_value.kickoff.return_value = "result"
        generate()
        kickoff_kwargs = mock_backend.return_value.contract_crew.return_value.kickoff.call_args[1]
        assert kickoff_kwargs["inputs"]["topic"] == "Online Shopping"
        assert "Feature Envy" in kickoff_kwargs["inputs"]["code_smells"]

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_raises_exception_on_failure(self, mock_backend):
        mock_backend.return_value.contract_crew.return_value.kickoff.side_effect = \
            RuntimeError("crew failed")
        with pytest.raises(Exception, match="An error occurred while generating"):
            generate()

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_exception_message_contains_original_error(self, mock_backend):
        mock_backend.return_value.contract_crew.return_value.kickoff.side_effect = \
            RuntimeError("original error")
        with pytest.raises(Exception, match="original error"):
            generate()


# ─────────────────────────────────────────────
# review
# ─────────────────────────────────────────────

class TestReview:
    @patch("codellamas_backend.main.CodellamasBackend")
    def test_returns_result_on_success(self, mock_backend):
        mock_backend.return_value.review_crew.return_value.kickoff.return_value = "feedback"
        result = review()
        assert result == "feedback"

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_kickoff_called_with_correct_inputs(self, mock_backend):
        mock_backend.return_value.review_crew.return_value.kickoff.return_value = "feedback"
        review()
        kickoff_kwargs = mock_backend.return_value.review_crew.return_value.kickoff.call_args[1]
        assert "problem_description" in kickoff_kwargs["inputs"]
        assert "student_code" in kickoff_kwargs["inputs"]
        assert "test_results" in kickoff_kwargs["inputs"]

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_raises_exception_on_failure(self, mock_backend):
        mock_backend.return_value.review_crew.return_value.kickoff.side_effect = \
            RuntimeError("review failed")
        with pytest.raises(Exception, match="An error occurred while evaluating"):
            review()

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_exception_message_contains_original_error(self, mock_backend):
        mock_backend.return_value.review_crew.return_value.kickoff.side_effect = \
            RuntimeError("original error")
        with pytest.raises(Exception, match="original error"):
            review()


# ─────────────────────────────────────────────
# train
# ─────────────────────────────────────────────

class TestTrain:
    @patch("codellamas_backend.main.CodellamasBackend")
    def test_train_called_with_correct_args(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "3", "output.pkl"]):
            train()
            mock_backend.return_value.contract_crew.return_value.train.assert_called_once_with(
                n_iterations=3,
                filename="output.pkl",
                inputs={
                    "topic": "Shopping",
                    "code_smells": ["Long method"],
                    "seed": 42,
                    "project_context": "",
                },
            )

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_raises_exception_on_failure(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "3", "output.pkl"]):
            mock_backend.return_value.contract_crew.return_value.train.side_effect = \
                RuntimeError("train failed")
            with pytest.raises(Exception, match="An error occurred while training"):
                train()

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_exception_message_contains_original_error(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "3", "output.pkl"]):
            mock_backend.return_value.contract_crew.return_value.train.side_effect = \
                RuntimeError("original error")
            with pytest.raises(Exception, match="original error"):
                train()


# ─────────────────────────────────────────────
# replay
# ─────────────────────────────────────────────

class TestReplay:
    @patch("codellamas_backend.main.CodellamasBackend")
    def test_replay_called_with_correct_task_id(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "task-123"]):
            replay()
            mock_backend.return_value.contract_crew.return_value.replay.assert_called_once_with(
                task_id="task-123"
            )

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_raises_exception_on_failure(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "task-123"]):
            mock_backend.return_value.contract_crew.return_value.replay.side_effect = \
                RuntimeError("replay failed")
            with pytest.raises(Exception, match="An error occurred while replaying"):
                replay()

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_exception_message_contains_original_error(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "task-123"]):
            mock_backend.return_value.contract_crew.return_value.replay.side_effect = \
                RuntimeError("original error")
            with pytest.raises(Exception, match="original error"):
                replay()


# ─────────────────────────────────────────────
# test
# ─────────────────────────────────────────────

class TestTestFunction:
    @patch("codellamas_backend.main.CodellamasBackend")
    def test_test_called_with_correct_args(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "5", "gpt-4"]):
            main_test_func()
            mock_backend.return_value.contract_crew.return_value.test.assert_called_once_with(
                n_iterations=5,
                eval_llm="gpt-4",
                inputs={
                    "topic": "Shopping",
                    "code_smells": ["Long method"],
                    "seed": 42,
                    "project_context": "",
                },
            )

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_raises_exception_on_failure(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "5", "gpt-4"]):
            mock_backend.return_value.contract_crew.return_value.test.side_effect = \
                RuntimeError("test failed")
            with pytest.raises(Exception, match="An error occurred while testing"):
                main_test_func()

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_exception_message_contains_original_error(self, mock_backend):
        with patch.object(sys, "argv", ["main.py", "5", "gpt-4"]):
            mock_backend.return_value.contract_crew.return_value.test.side_effect = \
                RuntimeError("original error")
            with pytest.raises(Exception, match="original error"):
                main_test_func()


# ─────────────────────────────────────────────
# run_with_trigger
# ─────────────────────────────────────────────

class TestRunWithTrigger:
    @patch("codellamas_backend.main.CodellamasBackend")
    def test_returns_result_on_valid_payload(self, mock_backend):
        payload = json.dumps({"event": "trigger"})
        mock_backend.return_value.contract_crew.return_value.kickoff.return_value = "result"
        with patch.object(sys, "argv", ["main.py", payload]):
            result = run_with_trigger()
            assert result == "result"

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_kickoff_called_with_trigger_payload(self, mock_backend):
        payload = json.dumps({"event": "trigger"})
        mock_backend.return_value.contract_crew.return_value.kickoff.return_value = "result"
        with patch.object(sys, "argv", ["main.py", payload]):
            run_with_trigger()
            kickoff_kwargs = mock_backend.return_value.contract_crew.return_value.kickoff.call_args[1]
            assert kickoff_kwargs["inputs"]["crewai_trigger_payload"] == {"event": "trigger"}

    def test_raises_exception_when_no_args(self):
        with patch.object(sys, "argv", ["main.py"]):
            with pytest.raises(Exception, match="No trigger payload provided"):
                run_with_trigger()

    def test_raises_exception_on_invalid_json(self):
        with patch.object(sys, "argv", ["main.py", "not valid json"]):
            with pytest.raises(Exception, match="Invalid JSON payload"):
                run_with_trigger()

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_raises_exception_on_crew_failure(self, mock_backend):
        payload = json.dumps({"event": "trigger"})
        mock_backend.return_value.contract_crew.return_value.kickoff.side_effect = \
            RuntimeError("crew failed")
        with patch.object(sys, "argv", ["main.py", payload]):
            with pytest.raises(Exception, match="An error occurred while running"):
                run_with_trigger()

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_exception_contains_original_error(self, mock_backend):
        payload = json.dumps({"event": "trigger"})
        mock_backend.return_value.contract_crew.return_value.kickoff.side_effect = \
            RuntimeError("original error")
        with patch.object(sys, "argv", ["main.py", payload]):
            with pytest.raises(Exception, match="original error"):
                run_with_trigger()

    @patch("codellamas_backend.main.CodellamasBackend")
    def test_inputs_contain_default_topic(self, mock_backend):
        payload = json.dumps({"event": "trigger"})
        mock_backend.return_value.contract_crew.return_value.kickoff.return_value = "result"
        with patch.object(sys, "argv", ["main.py", payload]):
            run_with_trigger()
            kickoff_kwargs = mock_backend.return_value.contract_crew.return_value.kickoff.call_args[1]
            assert kickoff_kwargs["inputs"]["topic"] == "Shopping"