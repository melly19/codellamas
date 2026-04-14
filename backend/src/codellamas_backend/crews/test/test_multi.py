import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError
from crewai import Process, Agent

from codellamas_backend.crews.crew_multi import (
    CodellamasBackendMulti,
    SpringBootExercise,
    VerifyToolInput,
    VerifyToolOutput,
    MavenVerifyTool,
)
from codellamas_backend.schemas.files import ProjectFile


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def pf(path="src/App.java", content="class App {}") -> ProjectFile:
    return ProjectFile(path=path, content=content)


def make_exercise(**kwargs) -> SpringBootExercise:
    defaults = dict(
        problem_description="Fix the bug",
        project_files=[pf("src/App.java")],
        test_files=[pf("src/AppTest.java")],
        solution_explanation_md="## Solution",
        paths_to_ex=["src/App.java"],
        answers_list=[pf("src/App.java", "fixed")],
    )
    return SpringBootExercise(**{**defaults, **kwargs})


def make_verify_output(status="PASS") -> VerifyToolOutput:
    return VerifyToolOutput(
        status=status,
        failed_tests=[] if status == "PASS" else ["AppTest"],
        errors=[] if status == "PASS" else ["Test failures"],
        raw_log_head="",
    )


def patch_test_runner():
    return patch.object(
        CodellamasBackendMulti,
        "test_runner",
        return_value=MagicMock(spec=Agent)
    )


def make_backend(**kwargs) -> CodellamasBackendMulti:
    with patch("codellamas_backend.crews.crew_multi.LLM"):
        with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool"):
            with patch_test_runner():
                return CodellamasBackendMulti(**kwargs)


# ─────────────────────────────────────────────
# SpringBootExercise
# ─────────────────────────────────────────────

class TestSpringBootExercise:
    def test_valid(self):
        ex = make_exercise()
        assert ex.problem_description == "Fix the bug"

    def test_missing_problem_description_raises(self):
        with pytest.raises(ValidationError):
            SpringBootExercise(
                project_files=[], test_files=[],
                solution_explanation_md="", paths_to_ex=[], answers_list=[]
            )

    def test_paths_to_ex_defaults_to_empty_list(self):
        ex = SpringBootExercise(
            problem_description="desc",
            project_files=[], test_files=[],
            solution_explanation_md="",
        )
        assert ex.paths_to_ex == []

    def test_answers_list_defaults_to_empty_list(self):
        ex = SpringBootExercise(
            problem_description="desc",
            project_files=[], test_files=[],
            solution_explanation_md="",
        )
        assert ex.answers_list == []

    def test_empty_lists_allowed(self):
        ex = SpringBootExercise(
            problem_description="desc",
            project_files=[], test_files=[],
            solution_explanation_md="",
        )
        assert ex.project_files == []
        assert ex.test_files == []


# ─────────────────────────────────────────────
# VerifyToolInput
# ─────────────────────────────────────────────

class TestVerifyToolInput:
    def test_valid(self):
        inp = VerifyToolInput(base_project_files=[pf()])
        assert inp.timeout_sec == 180

    def test_missing_base_project_files_raises(self):
        with pytest.raises(ValidationError):
            VerifyToolInput()

    def test_override_defaults_to_empty(self):
        inp = VerifyToolInput(base_project_files=[pf()])
        assert inp.override_project_files == []

    def test_injected_tests_defaults_to_empty(self):
        inp = VerifyToolInput(base_project_files=[pf()])
        assert inp.injected_tests == []

    def test_custom_timeout(self):
        inp = VerifyToolInput(base_project_files=[pf()], timeout_sec=300)
        assert inp.timeout_sec == 300


# ─────────────────────────────────────────────
# VerifyToolOutput
# ─────────────────────────────────────────────

class TestVerifyToolOutput:
    def test_valid_pass(self):
        out = VerifyToolOutput(status="PASS")
        assert out.status == "PASS"
        assert out.failed_tests == []
        assert out.errors == []
        assert out.raw_log_head == ""

    def test_valid_fail(self):
        out = VerifyToolOutput(status="FAIL", failed_tests=["AppTest"], errors=["err"])
        assert out.status == "FAIL"
        assert "AppTest" in out.failed_tests

    def test_missing_status_raises(self):
        with pytest.raises(ValidationError):
            VerifyToolOutput()


# ─────────────────────────────────────────────
# MavenVerifyTool._normalize_files
# ─────────────────────────────────────────────

class TestNormalizeFiles:
    def setup_method(self):
        self.tool = MavenVerifyTool()

    def test_project_file_passthrough(self):
        files = [pf("src/App.java")]
        result = self.tool._normalize_files(files)
        assert result == files

    def test_dict_converted_to_project_file(self):
        files = [{"path": "src/App.java", "content": "class App {}"}]
        result = self.tool._normalize_files(files)
        assert isinstance(result[0], ProjectFile)
        assert result[0].path == "src/App.java"

    def test_invalid_dict_skipped(self):
        files = [{"invalid_key": "value"}]
        result = self.tool._normalize_files(files)
        assert result == []

    def test_none_returns_empty(self):
        result = self.tool._normalize_files(None)
        assert result == []

    def test_empty_list_returns_empty(self):
        result = self.tool._normalize_files([])
        assert result == []

    def test_mixed_list(self):
        files = [
            pf("src/App.java"),
            {"path": "src/Foo.java", "content": "class Foo {}"},
            {"bad": "data"},
        ]
        result = self.tool._normalize_files(files)
        assert len(result) == 2
        assert result[0].path == "src/App.java"
        assert result[1].path == "src/Foo.java"


# ─────────────────────────────────────────────
# MavenVerifyTool._run
# ─────────────────────────────────────────────

class TestMavenVerifyToolRun:
    def setup_method(self):
        self.tool = MavenVerifyTool()

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_no_base_files_returns_skipped(self, mock_verifier):
        result = self.tool._run(base_project_files=[])
        import json
        parsed = json.loads(result)
        assert parsed["status"] == "SKIPPED"
        assert "No base_project_files" in parsed["errors"][0]
        mock_verifier.assert_not_called()

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_pass_result_returned(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "PASS"
        mock_verification.failed_tests = []
        mock_verification.errors = []
        mock_verification.summary.return_value = "BUILD SUCCESS"
        mock_verifier.return_value.verify.return_value = mock_verification

        result = self.tool._run(base_project_files=[pf()])
        import json
        parsed = json.loads(result)
        assert parsed["status"] == "PASS"

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_fail_result_returned(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "FAIL"
        mock_verification.failed_tests = ["AppTest"]
        mock_verification.errors = ["Test failures"]
        mock_verification.summary.return_value = "BUILD FAILURE"
        mock_verifier.return_value.verify.return_value = mock_verification

        result = self.tool._run(base_project_files=[pf()])
        import json
        parsed = json.loads(result)
        assert parsed["status"] == "FAIL"
        assert "AppTest" in parsed["failed_tests"]

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_raw_log_head_truncated_to_2000(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "PASS"
        mock_verification.failed_tests = []
        mock_verification.errors = []
        mock_verification.summary.return_value = "x" * 5000
        mock_verifier.return_value.verify.return_value = mock_verification

        result = self.tool._run(base_project_files=[pf()])
        import json
        parsed = json.loads(result)
        assert len(parsed["raw_log_head"]) == 2000

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_dict_files_normalized(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "PASS"
        mock_verification.failed_tests = []
        mock_verification.errors = []
        mock_verification.summary.return_value = ""
        mock_verifier.return_value.verify.return_value = mock_verification

        dict_files = [{"path": "src/App.java", "content": "class App {}"}]
        result = self.tool._run(base_project_files=dict_files)
        import json
        parsed = json.loads(result)
        assert parsed["status"] == "PASS"

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_timeout_sec_passed_to_verifier(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "PASS"
        mock_verification.failed_tests = []
        mock_verification.errors = []
        mock_verification.summary.return_value = ""
        mock_verifier.return_value.verify.return_value = mock_verification

        self.tool._run(base_project_files=[pf()], timeout_sec=300)
        mock_verifier.assert_called_once_with(timeout_sec=300, quiet=True)


# ─────────────────────────────────────────────
# CodellamasBackendMulti.__init__
# ─────────────────────────────────────────────

class TestCodellamasBackendMultiInit:
    def test_custom_model_stored(self):
        with patch("codellamas_backend.crews.crew_multi.LLM"):
            with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool"):
                with patch_test_runner():
                    backend = CodellamasBackendMulti(model_name="gpt-4")
                    assert backend.model_name == "gpt-4"

    def test_custom_endpoint_stored(self):
        with patch("codellamas_backend.crews.crew_multi.LLM"):
            with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool"):
                with patch_test_runner():
                    backend = CodellamasBackendMulti(api_endpoint="https://custom.com")
                    assert backend.api_endpoint == "https://custom.com"

    def test_custom_api_key_stored(self):
        with patch("codellamas_backend.crews.crew_multi.LLM"):
            with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool"):
                with patch_test_runner():
                    backend = CodellamasBackendMulti(api_key="my-key")
                    assert backend.api_key == "my-key"

    def test_none_model_falls_back_to_constant(self):
        with patch("codellamas_backend.crews.crew_multi.MODEL", "test-model"):
            with patch("codellamas_backend.crews.crew_multi.LLM"):
                with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool"):
                    with patch_test_runner():
                        backend = CodellamasBackendMulti(model_name=None)
                        assert backend.model_name == "test-model"

    def test_none_key_falls_back_to_constant(self):
        with patch("codellamas_backend.crews.crew_multi.OPENROUTER_API_KEY", "env-key"):
            with patch("codellamas_backend.crews.crew_multi.LLM"):
                with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool"):
                    with patch_test_runner():
                        backend = CodellamasBackendMulti(api_key=None)
                        assert backend.api_key == "env-key"

    def test_llm_created_with_correct_params(self):
        with patch("codellamas_backend.crews.crew_multi.LLM") as mock_llm:
            with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool"):
                with patch_test_runner():
                    CodellamasBackendMulti(
                        model_name="claude-3",
                        api_key="key",
                        api_endpoint="https://ep.com"
                    )
                    mock_llm.assert_called_once_with(
                        model="claude-3",
                        base_url="https://ep.com",
                        api_key="key",
                        request_timeout=1800,
                        max_tokens=30000,
                    )

    def test_verify_tool_created_on_init(self):
        with patch("codellamas_backend.crews.crew_multi.LLM"):
            with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool") as mock_tool:
                with patch_test_runner():
                    backend = CodellamasBackendMulti()
                    mock_tool.assert_called_once()
                    assert backend.verify_tool == mock_tool.return_value

    def test_default_constants(self):
        with patch("codellamas_backend.crews.crew_multi.LLM"):
            with patch("codellamas_backend.crews.crew_multi.MavenVerifyTool"):
                with patch_test_runner():
                    backend = make_backend()
                    assert backend.request_timeout_sec == 1800
                    assert backend.maven_timeout_sec == 180
                    assert backend.max_patch_iters == 2


# ─────────────────────────────────────────────
# CodellamasBackendMulti._to_project_files
# ─────────────────────────────────────────────

class TestToProjectFiles:
    def setup_method(self):
        self.backend = make_backend()

    def test_project_file_passthrough(self):
        files = [pf("src/App.java")]
        result = self.backend._to_project_files(files)
        assert result == files

    def test_dict_converted(self):
        files = [{"path": "src/App.java", "content": "class App {}"}]
        result = self.backend._to_project_files(files)
        assert isinstance(result[0], ProjectFile)
        assert result[0].path == "src/App.java"

    def test_object_with_path_content_attrs(self):
        obj = MagicMock()
        obj.path = "src/App.java"
        obj.content = "class App {}"
        result = self.backend._to_project_files([obj])
        assert result[0].path == "src/App.java"
        assert result[0].content == "class App {}"

    def test_none_returns_empty(self):
        result = self.backend._to_project_files(None)
        assert result == []

    def test_empty_list_returns_empty(self):
        result = self.backend._to_project_files([])
        assert result == []

    def test_mixed_list(self):
        obj = MagicMock()
        obj.path = "src/Foo.java"
        obj.content = "class Foo {}"
        files = [pf("src/App.java"), {"path": "src/Bar.java", "content": ""}, obj]
        result = self.backend._to_project_files(files)
        assert len(result) == 3


# ─────────────────────────────────────────────
# CodellamasBackendMulti._exercise_from_result
# ─────────────────────────────────────────────

class TestExerciseFromResult:
    def setup_method(self):
        self.backend = make_backend()

    def test_builds_exercise_from_result(self):
        mock_result = MagicMock()
        mock_result.json_dict = {
            "problem_description": "desc",
            "project_files": [],
            "test_files": [],
            "solution_explanation_md": "",
            "paths_to_ex": [],
            "answers_list": [],
        }
        exercise = self.backend._exercise_from_result(mock_result)
        assert isinstance(exercise, SpringBootExercise)
        assert exercise.problem_description == "desc"

    def test_missing_field_in_result_raises(self):
        mock_result = MagicMock()
        mock_result.json_dict = {"problem_description": "desc"}
        with pytest.raises(Exception):
            self.backend._exercise_from_result(mock_result)


# ─────────────────────────────────────────────
# CodellamasBackendMulti._verify
# ─────────────────────────────────────────────

class TestVerify:
    def setup_method(self):
        self.backend = make_backend()

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_returns_verify_tool_output(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "PASS"
        mock_verification.failed_tests = []
        mock_verification.errors = []
        mock_verification.summary.return_value = ""
        mock_verifier.return_value.verify.return_value = mock_verification

        result = self.backend._verify(
            base_project_files=[pf()],
            override_project_files=[],
            injected_tests=[],
        )
        assert isinstance(result, VerifyToolOutput)
        assert result.status == "PASS"

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_fail_status_propagated(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "FAIL"
        mock_verification.failed_tests = ["AppTest"]
        mock_verification.errors = ["err"]
        mock_verification.summary.return_value = "BUILD FAILURE"
        mock_verifier.return_value.verify.return_value = mock_verification

        result = self.backend._verify(
            base_project_files=[pf()],
            override_project_files=[],
            injected_tests=[],
        )
        assert result.status == "FAIL"
        assert "AppTest" in result.failed_tests

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_injected_tests_converted_to_dict(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "PASS"
        mock_verification.failed_tests = []
        mock_verification.errors = []
        mock_verification.summary.return_value = ""
        mock_verifier.return_value.verify.return_value = mock_verification

        injected = [pf("src/Test.java", "test content")]
        self.backend._verify(
            base_project_files=[pf()],
            override_project_files=[],
            injected_tests=injected,
        )
        call_kwargs = mock_verifier.return_value.verify.call_args[1]
        assert call_kwargs["injected_tests"] == {"src/Test.java": "test content"}

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_raw_log_head_truncated_to_2000(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "PASS"
        mock_verification.failed_tests = []
        mock_verification.errors = []
        mock_verification.summary.return_value = "x" * 5000
        mock_verifier.return_value.verify.return_value = mock_verification

        result = self.backend._verify(
            base_project_files=[pf()],
            override_project_files=[],
            injected_tests=[],
        )
        assert len(result.raw_log_head) == 2000

    @patch("codellamas_backend.crews.crew_multi.MavenVerifier")
    def test_maven_timeout_passed_to_verifier(self, mock_verifier):
        mock_verification = MagicMock()
        mock_verification.status = "PASS"
        mock_verification.failed_tests = []
        mock_verification.errors = []
        mock_verification.summary.return_value = ""
        mock_verifier.return_value.verify.return_value = mock_verification

        self.backend._verify(
            base_project_files=[pf()],
            override_project_files=[],
            injected_tests=[],
        )
        mock_verifier.assert_called_once_with(timeout_sec=180, quiet=True)


# ─────────────────────────────────────────────
# CodellamasBackendMulti._merge_exercise
# ─────────────────────────────────────────────

class TestMergeExercise:
    def setup_method(self):
        self.backend = make_backend()
        self.current = make_exercise(
            problem_description="current desc",
            project_files=[pf("src/Current.java")],
            test_files=[pf("src/CurrentTest.java")],
            solution_explanation_md="current explanation",
            paths_to_ex=["src/Current.java"],
            answers_list=[pf("src/Current.java", "current answer")],
        )
        self.updated = make_exercise(
            problem_description="updated desc",
            project_files=[pf("src/Updated.java")],
            test_files=[pf("src/UpdatedTest.java")],
            solution_explanation_md="updated explanation",
            paths_to_ex=["src/Updated.java"],
            answers_list=[pf("src/Updated.java", "updated answer")],
        )

    def test_updated_fields_win(self):
        result = self.backend._merge_exercise(self.current, self.updated)
        assert result.problem_description == "updated desc"
        assert result.solution_explanation_md == "updated explanation"

    def test_updated_answers_win_by_default(self):
        result = self.backend._merge_exercise(self.current, self.updated)
        assert result.answers_list[0].content == "updated answer"

    def test_current_answers_kept_when_prefer_updated_false(self):
        result = self.backend._merge_exercise(
            self.current, self.updated, prefer_updated_answers=False
        )
        assert result.answers_list[0].content == "current answer"

    def test_current_answers_kept_when_updated_answers_empty(self):
        updated_no_answers = make_exercise(answers_list=[])
        result = self.backend._merge_exercise(self.current, updated_no_answers)
        assert result.answers_list == self.current.answers_list

    def test_current_description_kept_when_updated_empty(self):
        updated_empty_desc = make_exercise(problem_description="")
        result = self.backend._merge_exercise(self.current, updated_empty_desc)
        assert result.problem_description == "current desc"

    def test_current_project_files_kept_when_updated_empty(self):
        updated_no_files = make_exercise(project_files=[])
        result = self.backend._merge_exercise(self.current, updated_no_files)
        assert result.project_files == self.current.project_files

    def test_returns_spring_boot_exercise(self):
        result = self.backend._merge_exercise(self.current, self.updated)
        assert isinstance(result, SpringBootExercise)


# ─────────────────────────────────────────────
# CodellamasBackendMulti._build_reference_override_files
# ─────────────────────────────────────────────

class TestBuildReferenceOverrideFiles:
    def setup_method(self):
        self.backend = make_backend()

    def test_empty_answers_returns_project_files(self):
        project_files = [pf("src/App.java")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=[],
            paths_to_ex=[],
        )
        assert len(result) == 1
        assert result[0].path == "src/App.java"

    def test_answer_matching_project_path_replaces_it(self):
        project_files = [pf("src/App.java", "original")]
        answers = [pf("src/App.java", "fixed")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=["src/App.java"],
        )
        match = next(f for f in result if f.path == "src/App.java")
        assert match.content == "fixed"

    def test_pom_xml_replaced(self):
        project_files = [pf("pom.xml", "original pom")]
        answers = [pf("pom.xml", "updated pom")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],
        )
        match = next(f for f in result if f.path == "pom.xml")
        assert match.content == "updated pom"

    def test_answer_matched_by_basename(self):
        project_files = [pf("src/main/java/App.java", "original")]
        answers = [pf("App.java", "fixed")]  # basename match
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=["src/main/java/App.java"],
        )
        match = next(f for f in result if f.path == "src/main/java/App.java")
        assert match.content == "fixed"

    def test_preferred_candidate_used_when_in_paths_to_ex(self):
        project_files = [
            pf("src/main/App.java", "main"),
            pf("src/test/App.java", "test"),
        ]
        answers = [pf("App.java", "fixed")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=["src/main/App.java"],  # prefer main
        )
        match = next(f for f in result if f.path == "src/main/App.java")
        assert match.content == "fixed"

    def test_unmatched_answer_added_as_new_file(self):
        project_files = [pf("src/App.java")]
        answers = [pf("src/NewFile.java", "new")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],
        )
        paths = [f.path for f in result]
        assert "src/NewFile.java" in paths

    def test_returns_list_of_project_files(self):
        result = self.backend._build_reference_override_files(
            project_files=[pf()],
            answers_list=[],
            paths_to_ex=[],
        )
        assert all(isinstance(f, ProjectFile) for f in result)

    def test_dict_project_files_normalized(self):
        project_files = [{"path": "src/App.java", "content": "original"}]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=[],
            paths_to_ex=[],
        )
        assert result[0].path == "src/App.java"

    def test_pom_xml_not_in_project_files_added(self):
        # pom.xml is in answers but NOT in project_files
        # so it hits the special pom.xml branch
        project_files = [pf("src/App.java", "original")]  # no pom.xml
        answers = [pf("pom.xml", "updated pom")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],
        )
        match = next(f for f in result if f.path == "pom.xml")
        assert match.content == "updated pom"

    def test_answer_matched_by_basename_single_candidate_not_in_paths_to_ex(self):
        # one candidate exists but it's NOT in paths_to_ex
        # so preferred_candidates is empty, falls to candidate_paths[0]
        project_files = [pf("src/main/java/App.java", "original")]
        answers = [pf("App.java", "fixed")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],  # empty — no preferred candidates
        )
        match = next(f for f in result if f.path == "src/main/java/App.java")
        assert match.content == "fixed"


# ─────────────────────────────────────────────
# CodellamasBackendMulti._run_single_task_crew
# ─────────────────────────────────────────────

class TestRunSingleTaskCrew:
    def setup_method(self):
        self.backend = make_backend()

    @patch("codellamas_backend.crews.crew_multi.Crew")
    def test_crew_created_with_sequential(self, mock_crew):
        task_obj = MagicMock()
        agent_obj = MagicMock()
        self.backend._run_single_task_crew(task_obj, agent_obj, inputs={})
        kwargs = mock_crew.call_args[1]
        assert kwargs["process"] == Process.sequential

    @patch("codellamas_backend.crews.crew_multi.Crew")
    def test_crew_created_with_verbose(self, mock_crew):
        task_obj = MagicMock()
        agent_obj = MagicMock()
        self.backend._run_single_task_crew(task_obj, agent_obj, inputs={})
        kwargs = mock_crew.call_args[1]
        assert kwargs["verbose"] is True

    @patch("codellamas_backend.crews.crew_multi.Crew")
    def test_kickoff_called_with_inputs(self, mock_crew):
        task_obj = MagicMock()
        agent_obj = MagicMock()
        inputs = {"topic": "refactoring"}
        self.backend._run_single_task_crew(task_obj, agent_obj, inputs=inputs)
        mock_crew.return_value.kickoff.assert_called_once_with(inputs=inputs)

    @patch("codellamas_backend.crews.crew_multi.Crew")
    def test_returns_kickoff_result(self, mock_crew):
        task_obj = MagicMock()
        agent_obj = MagicMock()
        mock_crew.return_value.kickoff.return_value = "result"
        result = self.backend._run_single_task_crew(task_obj, agent_obj, inputs={})
        assert result == "result"

    @patch("codellamas_backend.crews.crew_multi.Crew")
    def test_agent_and_task_passed_correctly(self, mock_crew):
        task_obj = MagicMock()
        agent_obj = MagicMock()
        self.backend._run_single_task_crew(task_obj, agent_obj, inputs={})
        kwargs = mock_crew.call_args[1]
        assert kwargs["agents"] == [agent_obj]
        assert kwargs["tasks"] == [task_obj]


# ─────────────────────────────────────────────
# Tasks — output_json wiring
# ─────────────────────────────────────────────

class TestTasks:
    def setup_method(self):
        self.backend = make_backend()
        self.patch_test_runner = patch.object(
            self.backend,
            "test_runner",
            return_value=MagicMock(spec=Agent)
        ).start()

    def teardown_method(self):
        patch.stopall()

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_implement_smelly_code_output_json(self, mock_task):
        self.backend.implement_smelly_code()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == SpringBootExercise

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_patch_smelly_code_output_json(self, mock_task):
        self.backend.patch_smelly_code()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == SpringBootExercise

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_run_tests_on_smelly_code_output_json(self, mock_task):
        self.backend.run_tests_on_smelly_code()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == VerifyToolOutput

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_generate_answers_list_output_json(self, mock_task):
        self.backend.generate_answers_list()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == SpringBootExercise

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_run_tests_on_answers_list_output_json(self, mock_task):
        self.backend.run_tests_on_answers_list()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == VerifyToolOutput

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_patch_answers_list_output_json(self, mock_task):
        self.backend.patch_answers_list()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == SpringBootExercise

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_audit_exercise_output_json(self, mock_task):
        self.backend.audit_exercise()
        kwargs = mock_task.call_args[1]
        assert kwargs["output_json"] == SpringBootExercise

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_check_functional_correctness_no_output_json(self, mock_task):
        self.backend.check_functional_correctness()
        kwargs = mock_task.call_args[1]
        assert "output_json" not in kwargs

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_evaluate_code_quality_no_output_json(self, mock_task):
        self.backend.evaluate_code_quality()
        kwargs = mock_task.call_args[1]
        assert "output_json" not in kwargs

    @patch("codellamas_backend.crews.crew_multi.Task")
    def test_generate_review_feedback_no_output_json(self, mock_task):
        self.backend.generate_review_feedback()
        kwargs = mock_task.call_args[1]
        assert "output_json" not in kwargs


# ─────────────────────────────────────────────
# Crews
# ─────────────────────────────────────────────

class TestCrews:
    def setup_method(self):
        self.backend = make_backend()
        self.patch_agent = patch("codellamas_backend.crews.crew_multi.Agent").start()
        self.patch_task = patch("codellamas_backend.crews.crew_multi.Task").start()
        self.patch_crew = patch("codellamas_backend.crews.crew_multi.Crew").start()

    def teardown_method(self):
        patch.stopall()

    def test_generation_crew_sequential(self):
        self.backend.generation_crew()
        kwargs = self.patch_crew.call_args[1]
        assert kwargs["process"] == Process.sequential

    def test_generation_crew_verbose(self):
        self.backend.generation_crew()
        kwargs = self.patch_crew.call_args[1]
        assert kwargs["verbose"] is True

    def test_generation_crew_returns_crew(self):
        result = self.backend.generation_crew()
        assert result == self.patch_crew.return_value

    def test_review_crew_sequential(self):
        self.backend.review_crew()
        kwargs = self.patch_crew.call_args[1]
        assert kwargs["process"] == Process.sequential

    def test_review_crew_verbose(self):
        self.backend.review_crew()
        kwargs = self.patch_crew.call_args[1]
        assert kwargs["verbose"] is True

    def test_review_crew_returns_crew(self):
        result = self.backend.review_crew()
        assert result == self.patch_crew.return_value


# ─────────────────────────────────────────────
# Config wiring
# ─────────────────────────────────────────────

class TestConfigWiring:
    def setup_method(self):
        self.backend = make_backend()

    def test_agents_config_has_problem_architect(self):
        assert "problem_architect" in self.backend.agents_config

    def test_agents_config_has_test_engineer(self):
        assert "test_engineer" in self.backend.agents_config

    def test_agents_config_has_smelly_developer(self):
        assert "smelly_developer" in self.backend.agents_config

    def test_agents_config_has_answers_list_developer(self):
        assert "answers_list_developer" in self.backend.agents_config

    def test_agents_config_has_test_runner(self):
        assert "test_runner" in self.backend.agents_config

    def test_agents_config_has_debug_specialist(self):
        assert "debug_specialist" in self.backend.agents_config

    def test_agents_config_has_quality_assurance(self):
        assert "quality_assurance" in self.backend.agents_config

    def test_tasks_config_has_define_problem(self):
        assert "define_problem" in self.backend.tasks_config

    def test_tasks_config_has_implement_smelly_code(self):
        assert "implement_smelly_code" in self.backend.tasks_config

    def test_tasks_config_has_patch_smelly_code(self):
        assert "patch_smelly_code" in self.backend.tasks_config

    def test_tasks_config_has_generate_answers_list(self):
        assert "generate_answers_list" in self.backend.tasks_config

    def test_tasks_config_has_audit_exercise(self):
        assert "audit_exercise" in self.backend.tasks_config


# -------------------------------------------------------------------------
# Python-side verification / patch loop
# -------------------------------------------------------------------------

class TestGenerateWithFixLoop:
    def setup_method(self):
        self.backend = make_backend()
        self.base_files = [pf("src/App.java")]

        # mock all internal methods so no real crewai/maven calls
        self.mock_exercise = make_exercise()

        self.backend._exercise_from_result = MagicMock(return_value=self.mock_exercise)
        self.backend._verify = MagicMock(return_value=make_verify_output("PASS"))
        self.backend._run_single_task_crew = MagicMock(return_value=MagicMock())
        self.backend._merge_exercise = MagicMock(return_value=self.mock_exercise)
        self.backend._build_reference_override_files = MagicMock(return_value=self.base_files)
        self.backend._to_project_files = MagicMock(return_value=self.base_files)

        # patch agents/tasks so no real crewai objects built
        self.patch_crew = patch("codellamas_backend.crews.crew_multi.Crew").start()
        self.patch_crew.return_value.kickoff.return_value = MagicMock()

    def teardown_method(self):
        patch.stopall()

    def test_returns_tuple_of_exercise_and_meta(self):
        result = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert isinstance(result, tuple)
        exercise, meta = result
        assert isinstance(exercise, SpringBootExercise)
        assert isinstance(meta, dict)

    def test_meta_has_correct_keys(self):
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["mode"] == "multi"
        assert meta["fix_loop"] is True
        assert "smelly_iterations" in meta
        assert "reference_iterations" in meta
        assert "smelly_maven" in meta
        assert "reference_maven" in meta

    def test_smelly_pass_breaks_loop_after_one_iteration(self):
        self.backend._verify.return_value = make_verify_output("PASS")
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["smelly_iterations"] == 1

    def test_smelly_fail_runs_patch_and_iterates(self):
        # FAIL on first verify, PASS on second
        self.backend._verify.side_effect = [
            make_verify_output("FAIL"),  # smelly loop iter 1
            make_verify_output("PASS"),  # smelly loop iter 2
            make_verify_output("PASS"),  # reference loop iter 1
        ]
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["smelly_iterations"] == 2
        # patch task crew called at least once for smelly patch
        self.backend._run_single_task_crew.assert_called()

    def test_smelly_fail_calls_merge_with_prefer_updated_false(self):
        self.backend._verify.side_effect = [
            make_verify_output("FAIL"),
            make_verify_output("PASS"),
            make_verify_output("PASS"),
        ]
        self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        # first merge call should have prefer_updated_answers=False
        first_merge_call = self.backend._merge_exercise.call_args_list[0]
        assert first_merge_call[1].get("prefer_updated_answers") is False

    def test_reference_pass_breaks_loop_after_one_iteration(self):
        self.backend._verify.return_value = make_verify_output("PASS")
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["reference_iterations"] == 1

    def test_reference_fail_runs_patch_answers_list(self):
        self.backend._verify.side_effect = [
            make_verify_output("PASS"),  # smelly pass
            make_verify_output("FAIL"),  # reference fail iter 1
            make_verify_output("PASS"),  # reference pass iter 2
        ]
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["reference_iterations"] == 2

    def test_smelly_maven_set_in_meta(self):
        self.backend._verify.return_value = make_verify_output("PASS")
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["smelly_maven"] is not None

    def test_reference_maven_set_in_meta(self):
        self.backend._verify.return_value = make_verify_output("PASS")
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["reference_maven"] is not None

    def test_max_patch_iters_respected_for_smelly(self):
        # always FAIL — should stop after max_patch_iters
        self.backend._verify.side_effect = [
            make_verify_output("FAIL"),  # smelly iter 1
            make_verify_output("FAIL"),  # smelly iter 2
            make_verify_output("PASS"),  # reference iter 1
        ]
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["smelly_iterations"] == self.backend.max_patch_iters

    def test_max_patch_iters_respected_for_reference(self):
        self.backend._verify.side_effect = [
            make_verify_output("PASS"),  # smelly pass
            make_verify_output("FAIL"),  # reference iter 1
            make_verify_output("FAIL"),  # reference iter 2
        ]
        _, meta = self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="code",
            project_files=self.base_files,
        )
        assert meta["reference_iterations"] == self.backend.max_patch_iters

    def test_initial_crew_kickoff_called_with_inputs(self):
        self.backend.generate_with_fix_loop(
            topic="refactoring",
            code_smells=["god class"],
            existing_codebase="my code",
            project_files=self.base_files,
        )
        kickoff_kwargs = self.patch_crew.return_value.kickoff.call_args[1]
        assert kickoff_kwargs["inputs"]["topic"] == "refactoring"
        assert kickoff_kwargs["inputs"]["code_smells"] == ["god class"]
        assert kickoff_kwargs["inputs"]["existing_codebase"] == "my code"
        