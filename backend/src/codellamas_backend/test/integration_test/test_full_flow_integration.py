import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from codellamas_backend.api import app
from codellamas_backend.crews.crew_single import (
    SpringBootExercise,
    ContractSpec,
    ImplementationSpec,
)
from codellamas_backend.schemas.files import ProjectFile


client = TestClient(app)


def make_exercise():
    return SpringBootExercise(
        problem_description="Fix the god class smell",
        project_files=[
            ProjectFile(path="pom.xml", content="<project/>"),
            ProjectFile(
                path="src/main/java/com/example/App.java",
                content="package com.example;\npublic class App {}"
            ),
        ],
        test_files=[
            ProjectFile(
                path="src/test/java/com/example/AppTest.java",
                content="package com.example;\nimport org.junit.jupiter.api.Test;\npublic class AppTest { @Test void test() {} }"
            )
        ],
        solution_explanation_md="## Solution\nRefactor the class.",
        paths_to_ex=["src/main/java/com/example/App.java"],
        answers_list=[
            ProjectFile(
                path="src/main/java/com/example/App.java",
                content="package com.example;\npublic class App { // fixed }"
            )
        ],
    )


@pytest.mark.integration
class TestFullFlowIntegration:
    """
    End-to-end flow:
    generate exercise → maven verify → review student solution
    LLM is mocked, everything else is real
    """

    @patch("codellamas_backend.api.append_to_csv")
    @patch("codellamas_backend.api.save_exercise_to_repo")
    @patch("codellamas_backend.api.run_maven_verification",
           return_value={"enabled": False})
    @patch("codellamas_backend.api.generate_single_implementation_with_retries")
    @patch("codellamas_backend.api.generate_single_contract")
    @patch("codellamas_backend.api.get_backend")
    def test_generate_then_review(
        self, mock_backend, mock_contract, mock_impl,
        mock_maven, mock_save, mock_csv
    ):
        exercise = make_exercise()
        mock_save.return_value = "/tmp/saved"

        # Step 1 — generate
        mock_contract.return_value = ContractSpec(
            problem_description="Fix god class",
            test_files=exercise.test_files,
            paths_to_ex=exercise.paths_to_ex,
        )
        mock_impl.return_value = (exercise, {"mode": "single"})

        generate_response = client.post("/generate", json={
            "topic": "refactoring",
            "code_smells": ["god class"],
            "verify_maven": False,
        })
        assert generate_response.status_code == 200
        generated_data = generate_response.json()["data"]

        # Step 2 — review using generated exercise data
        mock_raw = MagicMock()
        mock_raw.__str__ = lambda self: "Good refactoring!"
        mock_backend.return_value.review_crew.return_value.kickoff.return_value = mock_raw

        review_response = client.post("/review", json={
            "code_smells": ["god class"],
            "question_json": generated_data,
            "student_code": [
                {"path": "src/main/java/com/example/App.java",
                 "content": "package com.example;\npublic class App { // student fix }"}
            ],
            "verify_maven": False,
        })
        assert review_response.status_code == 200
        assert "feedback" in review_response.json()

    @patch("codellamas_backend.api.append_to_csv")
    @patch("codellamas_backend.api.save_exercise_to_repo")
    @patch("codellamas_backend.api.run_maven_verification")
    @patch("codellamas_backend.api.generate_single_implementation_with_retries")
    @patch("codellamas_backend.api.generate_single_contract")
    @patch("codellamas_backend.api.get_backend")
    def test_generate_with_maven_verification(
        self, mock_backend, mock_contract, mock_impl,
        mock_maven, mock_save, mock_csv
    ):
        exercise = make_exercise()
        mock_save.return_value = "/tmp/saved"
        mock_maven.return_value = {
            "enabled": True,
            "status": "PASS",
            "failed_tests": [],
            "errors": [],
            "raw_log_head": "BUILD SUCCESS",
        }
        mock_contract.return_value = ContractSpec(
            problem_description="Fix god class",
            test_files=exercise.test_files,
            paths_to_ex=exercise.paths_to_ex,
        )
        mock_impl.return_value = (exercise, {"mode": "single"})

        response = client.post("/generate", json={
            "topic": "refactoring",
            "code_smells": ["god class"],
            "verify_maven": True,
        })
        assert response.status_code == 200
        body = response.json()
        assert "maven_verification" in body

    @patch("codellamas_backend.api.append_to_csv")
    @patch("codellamas_backend.api.save_exercise_to_repo")
    @patch("codellamas_backend.api.run_maven_verification",
           return_value={"enabled": False})
    @patch("codellamas_backend.api.generate_single_implementation_with_retries")
    @patch("codellamas_backend.api.generate_single_contract")
    @patch("codellamas_backend.api.get_backend")
    def test_generated_exercise_saved_to_disk(
        self, mock_backend, mock_contract, mock_impl,
        mock_maven, mock_save, mock_csv
    ):
        exercise = make_exercise()

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_save.return_value = tmpdir
            mock_contract.return_value = ContractSpec(
                problem_description="Fix god class",
                test_files=exercise.test_files,
                paths_to_ex=exercise.paths_to_ex,
            )
            mock_impl.return_value = (exercise, {"mode": "single"})

            response = client.post("/generate", json={
                "topic": "refactoring",
                "code_smells": ["god class"],
            })
            assert response.status_code == 200
            mock_save.assert_called_once()

    @patch("codellamas_backend.api.append_to_csv")
    @patch("codellamas_backend.api.save_exercise_to_repo")
    @patch("codellamas_backend.api.run_maven_verification",
           return_value={"enabled": False})
    @patch("codellamas_backend.api.generate_single_implementation_with_retries")
    @patch("codellamas_backend.api.generate_single_contract")
    @patch("codellamas_backend.api.get_backend")
    def test_exercise_data_structure_is_complete(
        self, mock_backend, mock_contract, mock_impl,
        mock_maven, mock_save, mock_csv
    ):
        exercise = make_exercise()
        mock_save.return_value = "/tmp/saved"
        mock_contract.return_value = ContractSpec(
            problem_description="Fix god class",
            test_files=exercise.test_files,
            paths_to_ex=exercise.paths_to_ex,
        )
        mock_impl.return_value = (exercise, {"mode": "single"})

        response = client.post("/generate", json={
            "topic": "refactoring",
            "code_smells": ["god class"],
        })
        data = response.json()["data"]
        assert "problem_description" in data
        assert "project_files" in data
        assert "test_files" in data
        assert "solution_explanation_md" in data
        assert "paths_to_ex" in data
        assert "answers_list" in data