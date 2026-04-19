import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from codellamas_backend.api import app
from codellamas_backend.crews.crew_single import SpringBootExercise
from codellamas_backend.schemas.files import ProjectFile


client = TestClient(app)


def make_exercise():
    return SpringBootExercise(
        problem_description="Fix the bug",
        project_files=[
            ProjectFile(path="pom.xml", content="<project/>"),
            ProjectFile(path="src/main/java/App.java", content="package com.example;\nclass App {}"),
        ],
        test_files=[
            ProjectFile(path="src/test/java/AppTest.java", content="package com.example;\nclass AppTest {}")
        ],
        solution_explanation_md="## Solution",
        paths_to_ex=["src/main/java/App.java"],
        answers_list=[ProjectFile(path="src/main/java/App.java", content="fixed")],
    )


@pytest.mark.integration
class TestHealthEndpoints:
    """No mocks needed — pure FastAPI routing"""

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_healthy(self):
        response = client.get("/")
        assert response.json()["status"] == "healthy"

    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_has_timestamp(self):
        response = client.get("/health")
        assert "timestamp" in response.json()

    def test_capabilities_returns_200(self):
        response = client.get("/capabilities")
        assert response.status_code == 200

    def test_capabilities_has_backends(self):
        response = client.get("/capabilities")
        assert "backends" in response.json()


@pytest.mark.integration
class TestGenerateEndpointIntegration:
    """Mocks LLM but uses real FastAPI routing, validation, file saving"""

    @patch("codellamas_backend.api.save_exercise_to_repo", return_value="/tmp/saved")
    @patch("codellamas_backend.api.run_maven_verification", return_value={"enabled": False})
    @patch("codellamas_backend.api.generate_single_implementation_with_retries")
    @patch("codellamas_backend.api.generate_single_contract")
    @patch("codellamas_backend.api.get_backend")
    def test_generate_returns_200(
        self, mock_backend, mock_contract, mock_impl, mock_maven, mock_save
    ):
        from codellamas_backend.crews.crew_single import ContractSpec
        mock_contract.return_value = ContractSpec(
            problem_description="Fix bug",
            test_files=[ProjectFile(path="src/test/java/AppTest.java", content="class AppTest {}")],
            paths_to_ex=["src/main/java/App.java"],
        )
        mock_impl.return_value = (make_exercise(), {"mode": "single"})

        response = client.post("/generate", json={
            "topic": "refactoring",
            "code_smells": ["god class"],
        })
        assert response.status_code == 200

    @patch("codellamas_backend.api.save_exercise_to_repo", return_value="/tmp/saved")
    @patch("codellamas_backend.api.run_maven_verification", return_value={"enabled": False})
    @patch("codellamas_backend.api.generate_single_implementation_with_retries")
    @patch("codellamas_backend.api.generate_single_contract")
    @patch("codellamas_backend.api.get_backend")
    def test_generate_response_has_data(
        self, mock_backend, mock_contract, mock_impl, mock_maven, mock_save
    ):
        from codellamas_backend.crews.crew_single import ContractSpec
        mock_contract.return_value = ContractSpec(
            problem_description="Fix bug",
            test_files=[ProjectFile(path="src/test/java/AppTest.java", content="class AppTest {}")],
            paths_to_ex=["src/main/java/App.java"],
        )
        mock_impl.return_value = (make_exercise(), {"mode": "single"})

        response = client.post("/generate", json={
            "topic": "refactoring",
            "code_smells": ["god class"],
        })
        body = response.json()
        assert "data" in body
        assert "problem_description" in body["data"]

    def test_generate_invalid_mode_returns_400(self):
        response = client.post("/generate", json={
            "topic": "refactoring",
            "code_smells": ["god class"],
            "mode": "invalid",
        })
        assert response.status_code in (400, 500)

    def test_generate_missing_topic_returns_422(self):
        response = client.post("/generate", json={
            "code_smells": ["god class"],
        })
        assert response.status_code == 422

    def test_generate_missing_code_smells_returns_422(self):
        response = client.post("/generate", json={
            "topic": "refactoring",
        })
        assert response.status_code == 422

    @patch("codellamas_backend.api.save_exercise_to_repo", return_value="/tmp/saved")
    @patch("codellamas_backend.api.run_maven_verification", return_value={"enabled": False})
    @patch("codellamas_backend.api.generate_single_implementation_with_retries")
    @patch("codellamas_backend.api.generate_single_contract")
    @patch("codellamas_backend.api.get_backend")
    def test_generate_count_2_returns_results_list(
        self, mock_backend, mock_contract, mock_impl, mock_maven, mock_save
    ):
        from codellamas_backend.crews.crew_single import ContractSpec
        mock_contract.return_value = ContractSpec(
            problem_description="Fix bug",
            test_files=[ProjectFile(path="src/test/java/AppTest.java", content="class AppTest {}")],
            paths_to_ex=["src/main/java/App.java"],
        )
        mock_impl.return_value = (make_exercise(), {"mode": "single"})

        response = client.post("/generate", json={
            "topic": "refactoring",
            "code_smells": ["god class"],
            "count": 2,
        })
        assert response.status_code == 200
        assert "results" in response.json()
        assert len(response.json()["results"]) == 2


@pytest.mark.integration
class TestReviewEndpointIntegration:
    @patch("codellamas_backend.api.CodellamasBackend")
    @patch("codellamas_backend.api.run_maven_verification", return_value={"enabled": False})
    def test_review_returns_200(self, mock_maven, mock_backend_cls):
        mock_raw = MagicMock()
        mock_raw.__str__ = lambda self: "Good work!"
        mock_backend_cls.return_value.review_crew.return_value.kickoff.return_value = mock_raw

        response = client.post("/review", json={
            "code_smells": ["god class"],
            "question_json": {},
            "student_code": [],
        })
        assert response.status_code == 200

    @patch("codellamas_backend.api.CodellamasBackend")
    @patch("codellamas_backend.api.run_maven_verification", return_value={"enabled": False})
    def test_review_response_has_feedback(self, mock_maven, mock_backend_cls):
        mock_raw = MagicMock()
        mock_raw.__str__ = lambda self: "Good work!"
        mock_backend_cls.return_value.review_crew.return_value.kickoff.return_value = mock_raw

        response = client.post("/review", json={
            "code_smells": ["god class"],
            "question_json": {},
            "student_code": [],
        })
        assert "feedback" in response.json()

    @patch("codellamas_backend.api.CodellamasBackend")
    @patch("codellamas_backend.api.run_maven_verification", return_value={"enabled": False})
    def test_review_response_has_maven_verification(self, mock_maven, mock_backend_cls):
        mock_raw = MagicMock()
        mock_raw.__str__ = lambda self: "Good work!"
        mock_backend_cls.return_value.review_crew.return_value.kickoff.return_value = mock_raw

        response = client.post("/review", json={
            "code_smells": ["god class"],
            "question_json": {},
            "student_code": [],
        })
        assert "maven_verification" in response.json()

    @patch("codellamas_backend.api.get_backend")
    @patch("codellamas_backend.api.run_maven_verification",
           return_value={"enabled": False})
    def test_review_crew_failure_returns_500(self, mock_maven, mock_backend):
        mock_backend.return_value.review_crew.return_value.kickoff.side_effect = \
            RuntimeError("crew failed")

        response = client.post("/review", json={
            "code_smells": ["god class"],
            "question_json": {},
            "student_code": [],
        })
        assert response.status_code == 500

    def test_review_missing_code_smells_returns_422(self):
        response = client.post("/review", json={
            "question_json": {},
            "student_code": [],
        })
        assert response.status_code == 422
