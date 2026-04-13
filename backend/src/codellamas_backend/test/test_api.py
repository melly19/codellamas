import os
import csv
import json
import pytest
import tempfile
import datetime
from unittest.mock import patch, MagicMock, mock_open
from typing import List

from fastapi import HTTPException

from codellamas_backend.api import (
    ingest_code_smells,
    normalize_project_files,
    run_maven_verification,
    build_solution_override_files,
    should_retry_single_generation,
    build_maven_failure_context,
    extract_package_decl,
    expected_package_from_path,
    validate_contract,
    validate_exercise_payload,
    compose_exercise,
    get_backend,
    append_to_csv,
    save_exercise_to_repo,
    default_base_project_files,
    build_preflight_failure_context,
    generate_single_contract,
)
from codellamas_backend.crews.crew_single import (
    ContractSpec,
    ImplementationSpec,
    SpringBootExercise,
)
from codellamas_backend.schemas.files import ProjectFile


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def pf(path="src/main/java/App.java", content="class App {}") -> ProjectFile:
    return ProjectFile(path=path, content=content)


def make_exercise(**kwargs) -> SpringBootExercise:
    defaults = dict(
        problem_description="Fix the bug",
        project_files=[
            pf("pom.xml", "<project/>"),
            pf("src/main/java/App.java", "package com.example;\nclass App {}"),
        ],
        test_files=[pf("src/test/java/AppTest.java", "package com.example;\nclass AppTest {}")],
        solution_explanation_md="## Solution",
        paths_to_ex=["src/main/java/App.java"],
        answers_list=[pf("src/main/java/App.java", "fixed")],
    )
    return SpringBootExercise(**{**defaults, **kwargs})


def make_contract(**kwargs) -> ContractSpec:
    defaults = dict(
        problem_description="Fix the bug",
        test_files=[pf("src/test/java/AppTest.java", "package com.example;\nclass AppTest {}")],
        paths_to_ex=["src/main/java/App.java"],
    )
    return ContractSpec(**{**defaults, **kwargs})


def make_implementation(**kwargs) -> ImplementationSpec:
    defaults = dict(
        project_files=[
            pf("pom.xml", "<project/>"),
            pf("src/main/java/App.java", "package com.example;\nclass App {}"),
        ],
        solution_explanation_md="## Solution",
        answers_list=[pf("src/main/java/App.java", "fixed")],
    )
    return ImplementationSpec(**{**defaults, **kwargs})


# ─────────────────────────────────────────────
# ingest_code_smells
# ─────────────────────────────────────────────

class TestIngestCodeSmells:
    def test_empty_list_returns_none(self):
        assert ingest_code_smells([]) == "None"

    def test_single_smell(self):
        assert ingest_code_smells(["god class"]) == "god class"

    def test_multiple_smells_joined(self):
        result = ingest_code_smells(["god class", "long method"])
        assert result == "god class, long method"

    def test_none_list(self):
        assert ingest_code_smells(None) == "None"

    def test_whitespace_smell_preserved(self):
        result = ingest_code_smells(["  god class  "])
        assert result == "  god class  "


# ─────────────────────────────────────────────
# normalize_project_files
# ─────────────────────────────────────────────

class TestNormalizeProjectFiles:
    def test_project_file_passthrough(self):
        files = [pf()]
        result = normalize_project_files(files)
        assert result == files

    def test_dict_converted(self):
        files = [{"path": "src/App.java", "content": "class App {}"}]
        result = normalize_project_files(files)
        assert isinstance(result[0], ProjectFile)
        assert result[0].path == "src/App.java"

    def test_invalid_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Invalid project file entry"):
            normalize_project_files([123])

    def test_none_returns_empty(self):
        result = normalize_project_files(None)
        assert result == []

    def test_empty_list_returns_empty(self):
        result = normalize_project_files([])
        assert result == []

    def test_mixed_list(self):
        files = [
            pf("src/App.java"),
            {"path": "src/Foo.java", "content": "class Foo {}"},
        ]
        result = normalize_project_files(files)
        assert len(result) == 2
        assert all(isinstance(f, ProjectFile) for f in result)


# ─────────────────────────────────────────────
# run_maven_verification
# ─────────────────────────────────────────────

class TestRunMavenVerification:
    def test_disabled_when_verify_maven_false(self):
        result = run_maven_verification(
            verify_maven=False,
            project_files=[pf()],
            override_files=[],
            injected_tests=[],
        )
        assert result == {"enabled": False}

    def test_enabled_true_when_verify_maven_true(self):
        with patch("codellamas_backend.api.MavenVerifier") as mock_verifier:
            mock_v = MagicMock()
            mock_v.status = "PASS"
            mock_v.failed_tests = []
            mock_v.errors = []
            mock_v.summary.return_value = ""
            mock_verifier.return_value.verify.return_value = mock_v
            result = run_maven_verification(
                verify_maven=True,
                project_files=[pf()],
                override_files=[],
                injected_tests=[],
            )
            assert result["enabled"] is True

    def test_skipped_when_no_project_files(self):
        result = run_maven_verification(
            verify_maven=True,
            project_files=[],
            override_files=[],
            injected_tests=[],
        )
        assert result["status"] == "SKIPPED"
        assert result["enabled"] is True

    def test_custom_skipped_reason(self):
        result = run_maven_verification(
            verify_maven=True,
            project_files=[],
            override_files=[],
            injected_tests=[],
            skipped_reason="custom reason",
        )
        assert result["reason"] == "custom reason"

    @patch("codellamas_backend.api.MavenVerifier")
    def test_pass_result_propagated(self, mock_verifier):
        mock_v = MagicMock()
        mock_v.status = "PASS"
        mock_v.failed_tests = []
        mock_v.errors = []
        mock_v.summary.return_value = "BUILD SUCCESS"
        mock_verifier.return_value.verify.return_value = mock_v

        result = run_maven_verification(
            verify_maven=True,
            project_files=[pf()],
            override_files=[],
            injected_tests=[],
        )
        assert result["status"] == "PASS"
        assert result["failed_tests"] == []

    @patch("codellamas_backend.api.MavenVerifier")
    def test_fail_result_propagated(self, mock_verifier):
        mock_v = MagicMock()
        mock_v.status = "FAIL"
        mock_v.failed_tests = ["AppTest"]
        mock_v.errors = ["Compilation error"]
        mock_v.summary.return_value = "BUILD FAILURE"
        mock_verifier.return_value.verify.return_value = mock_v

        result = run_maven_verification(
            verify_maven=True,
            project_files=[pf()],
            override_files=[],
            injected_tests=[],
        )
        assert result["status"] == "FAIL"
        assert "AppTest" in result["failed_tests"]

    @patch("codellamas_backend.api.MavenVerifier")
    def test_timeout_sec_passed_to_verifier(self, mock_verifier):
        mock_v = MagicMock()
        mock_v.status = "PASS"
        mock_v.failed_tests = []
        mock_v.errors = []
        mock_v.summary.return_value = ""
        mock_verifier.return_value.verify.return_value = mock_v

        run_maven_verification(
            verify_maven=True,
            project_files=[pf()],
            override_files=[],
            injected_tests=[],
            timeout_sec=300,
        )
        mock_verifier.assert_called_once_with(timeout_sec=300, quiet=True)

    @patch("codellamas_backend.api.MavenVerifier")
    def test_injected_tests_converted_to_dict(self, mock_verifier):
        mock_v = MagicMock()
        mock_v.status = "PASS"
        mock_v.failed_tests = []
        mock_v.errors = []
        mock_v.summary.return_value = ""
        mock_verifier.return_value.verify.return_value = mock_v

        injected = [pf("src/Test.java", "test")]
        run_maven_verification(
            verify_maven=True,
            project_files=[pf()],
            override_files=[],
            injected_tests=injected,
        )
        kwargs = mock_verifier.return_value.verify.call_args[1]
        assert kwargs["injected_tests"] == {"src/Test.java": "test"}


# ─────────────────────────────────────────────
# build_solution_override_files
# ─────────────────────────────────────────────

class TestBuildSolutionOverrideFiles:
    def test_empty_answers_returns_empty(self):
        result = build_solution_override_files(
            project_files=[pf()],
            answers_list=[],
            paths_to_ex=[],
        )
        assert result == []

    def test_none_answers_returns_empty(self):
        result = build_solution_override_files(
            project_files=[pf()],
            answers_list=None,
            paths_to_ex=[],
        )
        assert result == []

    def test_exact_path_match_replaces(self):
        project_files = [pf("src/main/java/App.java", "original")]
        answers = [pf("src/main/java/App.java", "fixed")]
        result = build_solution_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=["src/main/java/App.java"],
        )
        assert result[0].content == "fixed"

    def test_pom_xml_replaced(self):
        project_files = [pf("pom.xml", "original")]
        answers = [pf("pom.xml", "updated")]
        result = build_solution_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],
        )
        match = next(f for f in result if f.path == "pom.xml")
        assert match.content == "updated"

    def test_pom_xml_not_in_project_added(self):
        project_files = [pf("src/main/java/App.java")]
        answers = [pf("pom.xml", "new pom")]
        result = build_solution_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],
        )
        paths = [f.path for f in result]
        assert "pom.xml" in paths

    def test_basename_match_single_candidate(self):
        project_files = [pf("src/main/java/App.java", "original")]
        answers = [pf("App.java", "fixed")]
        result = build_solution_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],
        )
        match = next(f for f in result if f.path == "src/main/java/App.java")
        assert match.content == "fixed"

    def test_preferred_candidate_used_from_paths_to_ex(self):
        project_files = [
            pf("src/main/App.java", "main"),
            pf("src/test/App.java", "test"),
        ]
        answers = [pf("App.java", "fixed")]
        result = build_solution_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=["src/main/App.java"],
        )
        match = next(f for f in result if f.path == "src/main/App.java")
        assert match.content == "fixed"

    def test_unmatched_answer_added_as_new(self):
        project_files = [pf("src/main/java/App.java")]
        answers = [pf("src/main/java/NewFile.java", "new")]
        result = build_solution_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],
        )
        paths = [f.path for f in result]
        assert "src/main/java/NewFile.java" in paths

    def test_returns_list_of_project_files(self):
        result = build_solution_override_files(
            project_files=[pf()],
            answers_list=[pf()],
            paths_to_ex=[],
        )
        assert all(isinstance(f, ProjectFile) for f in result)


# ─────────────────────────────────────────────
# should_retry_single_generation
# ─────────────────────────────────────────────

class TestShouldRetrySingleGeneration:
    def test_not_enabled_returns_false(self):
        assert should_retry_single_generation({"enabled": False}) is False

    def test_enabled_false_key_missing_returns_false(self):
        assert should_retry_single_generation({}) is False

    def test_enabled_pass_returns_false(self):
        assert should_retry_single_generation({"enabled": True, "status": "PASS"}) is False

    def test_enabled_fail_returns_true(self):
        assert should_retry_single_generation({"enabled": True, "status": "FAIL"}) is True

    def test_enabled_skipped_returns_false(self):
        assert should_retry_single_generation({"enabled": True, "status": "SKIPPED"}) is False

    def test_enabled_no_status_returns_false(self):
        assert should_retry_single_generation({"enabled": True}) is False


# ─────────────────────────────────────────────
# build_maven_failure_context
# ─────────────────────────────────────────────

class TestBuildMavenFailureContext:
    def test_label_in_output(self):
        result = build_maven_failure_context("SMELLY", {"failed_tests": [], "errors": [], "raw_log_head": ""})
        assert "SMELLY" in result

    def test_failed_tests_in_output(self):
        result = build_maven_failure_context("SMELLY", {
            "failed_tests": ["AppTest"],
            "errors": [],
            "raw_log_head": "",
        })
        assert "AppTest" in result

    def test_errors_in_output(self):
        result = build_maven_failure_context("SMELLY", {
            "failed_tests": [],
            "errors": ["Compilation error"],
            "raw_log_head": "",
        })
        assert "Compilation error" in result

    def test_error_lines_extracted_from_log(self):
        log = "[ERROR] cannot find symbol\n[INFO] normal line"
        result = build_maven_failure_context("SMELLY", {
            "failed_tests": [],
            "errors": [],
            "raw_log_head": log,
        })
        assert "cannot find symbol" in result
        assert "normal line" not in result

    def test_important_lines_capped_at_10(self):
        log = "\n".join(f"[ERROR] line {i}" for i in range(20))
        result = build_maven_failure_context("SMELLY", {
            "failed_tests": [],
            "errors": [],
            "raw_log_head": log,
        })
        error_lines = [l for l in result.splitlines() if "[ERROR]" in l]
        assert len(error_lines) <= 10

    def test_none_fields_handled(self):
        result = build_maven_failure_context("SMELLY", {
            "failed_tests": None,
            "errors": None,
            "raw_log_head": None,
        })
        assert "SMELLY" in result

    def test_compilation_error_line_extracted(self):
        log = "COMPILATION ERROR\nsome other line"
        result = build_maven_failure_context("SMELLY", {
            "failed_tests": [],
            "errors": [],
            "raw_log_head": log,
        })
        assert "COMPILATION ERROR" in result

    def test_assertion_error_line_extracted(self):
        log = "AssertionFailedError: expected 1 but was 2"
        result = build_maven_failure_context("SMELLY", {
            "failed_tests": [],
            "errors": [],
            "raw_log_head": log,
        })
        assert "AssertionFailedError" in result


# ─────────────────────────────────────────────
# extract_package_decl
# ─────────────────────────────────────────────

class TestExtractPackageDecl:
    def test_extracts_package(self):
        content = "package com.example;\nclass App {}"
        assert extract_package_decl(content) == "com.example"

    def test_no_package_returns_none(self):
        assert extract_package_decl("class App {}") is None

    def test_multiline_package(self):
        content = "\n\npackage com.example.service;\nclass App {}"
        assert extract_package_decl(content) == "com.example.service"

    def test_empty_string_returns_none(self):
        assert extract_package_decl("") is None

    def test_package_with_leading_spaces(self):
        content = "   package com.example;\nclass App {}"
        assert extract_package_decl(content) == "com.example"

    def test_comment_before_package(self):
        content = "// comment\npackage com.example;\nclass App {}"
        assert extract_package_decl(content) == "com.example"


# ─────────────────────────────────────────────
# expected_package_from_path
# ─────────────────────────────────────────────

class TestExpectedPackageFromPath:
    def test_valid_path(self):
        result = expected_package_from_path(
            "src/main/java/com/example/App.java",
            "src/main/java/"
        )
        assert result == "com.example"

    def test_path_not_starting_with_prefix_returns_none(self):
        result = expected_package_from_path(
            "src/test/java/com/example/App.java",
            "src/main/java/"
        )
        assert result is None

    def test_not_java_file_returns_none(self):
        result = expected_package_from_path(
            "src/main/java/App.xml",
            "src/main/java/"
        )
        assert result is None

    def test_file_directly_in_root_returns_none(self):
        # no package parts — file is directly under prefix
        result = expected_package_from_path(
            "src/main/java/App.java",
            "src/main/java/"
        )
        assert result is None

    def test_deep_nested_package(self):
        result = expected_package_from_path(
            "src/main/java/com/example/service/UserService.java",
            "src/main/java/"
        )
        assert result == "com.example.service"


# ─────────────────────────────────────────────
# validate_contract
# ─────────────────────────────────────────────

class TestValidateContract:
    def test_valid_contract_no_errors(self):
        contract = make_contract()
        errors = validate_contract(contract)
        assert errors == []

    def test_empty_problem_description(self):
        contract = make_contract(problem_description="   ")
        errors = validate_contract(contract)
        assert any("problem_description" in e for e in errors)

    def test_empty_test_files(self):
        contract = make_contract(test_files=[])
        errors = validate_contract(contract)
        assert any("test_files" in e for e in errors)

    def test_empty_paths_to_ex(self):
        contract = make_contract(paths_to_ex=[])
        errors = validate_contract(contract)
        assert any("paths_to_ex" in e for e in errors)

    def test_invalid_paths_to_ex(self):
        contract = make_contract(paths_to_ex=["wrong/path/App.java"])
        errors = validate_contract(contract)
        assert any("invalid path" in e for e in errors)

    def test_invalid_test_file_path(self):
        contract = make_contract(
            test_files=[pf("wrong/path/AppTest.java", "package com.example;\nclass AppTest {}")]
        )
        errors = validate_contract(contract)
        assert any("invalid test file path" in e for e in errors)

    def test_duplicate_test_file_paths(self):
        test_file = pf("src/test/java/AppTest.java", "package com.example;\nclass AppTest {}")
        contract = make_contract(test_files=[test_file, test_file])
        errors = validate_contract(contract)
        assert any("duplicate" in e for e in errors)

    def test_package_mismatch_in_test_file(self):
        test_file = pf(
            "src/test/java/com/example/AppTest.java",
            "package com.wrong;\nclass AppTest {}"
        )
        contract = make_contract(test_files=[test_file])
        errors = validate_contract(contract)
        assert any("package mismatch" in e for e in errors)

    def test_correct_package_no_error(self):
        test_file = pf(
            "src/test/java/com/example/AppTest.java",
            "package com.example;\nclass AppTest {}"
        )
        contract = make_contract(test_files=[test_file])
        errors = validate_contract(contract)
        assert not any("package mismatch" in e for e in errors)


# ─────────────────────────────────────────────
# validate_exercise_payload
# ─────────────────────────────────────────────

class TestValidateExercisePayload:
    def test_valid_exercise_no_errors(self):
        exercise = make_exercise()
        errors = validate_exercise_payload(exercise)
        assert errors == []

    def test_empty_project_files(self):
        exercise = make_exercise(project_files=[])
        errors = validate_exercise_payload(exercise)
        assert any("project_files is empty" in e for e in errors)

    def test_missing_pom_xml(self):
        exercise = make_exercise(project_files=[pf("src/main/java/App.java")])
        errors = validate_exercise_payload(exercise)
        assert any("pom.xml" in e for e in errors)

    def test_duplicate_project_file_paths(self):
        file = pf("pom.xml", "<project/>")
        exercise = make_exercise(project_files=[file, file])
        errors = validate_exercise_payload(exercise)
        assert any("duplicate" in e for e in errors)

    def test_empty_answers_list(self):
        exercise = make_exercise(answers_list=[])
        errors = validate_exercise_payload(exercise)
        assert any("answers_list is empty" in e for e in errors)

    def test_paths_to_ex_not_in_project_files(self):
        exercise = make_exercise(paths_to_ex=["src/main/java/Missing.java"])
        errors = validate_exercise_payload(exercise)
        assert any("not found in project_files" in e for e in errors)

    def test_package_mismatch_in_project_file(self):
        exercise = make_exercise(project_files=[
            pf("pom.xml", "<project/>"),
            pf("src/main/java/com/example/App.java", "package com.wrong;\nclass App {}"),
        ])
        errors = validate_exercise_payload(exercise)
        assert any("package mismatch" in e for e in errors)

    def test_invalid_answers_list_path(self):
        exercise = make_exercise(answers_list=[pf("wrong/path/App.java", "fixed")])
        errors = validate_exercise_payload(exercise)
        assert any("answers_list contains invalid path" in e for e in errors)

    def test_valid_answers_list_path(self):
        exercise = make_exercise(
            answers_list=[pf("src/main/java/App.java", "fixed")]
        )
        errors = validate_exercise_payload(exercise)
        assert not any("answers_list" in e for e in errors)

    def test_pom_xml_in_answers_list_allowed(self):
        exercise = make_exercise(
            answers_list=[pf("pom.xml", "<project/>")]
        )
        errors = validate_exercise_payload(exercise)
        assert not any("answers_list contains invalid path" in e for e in errors)

    def test_package_mismatch_in_test_file_within_project_files(self):
        exercise = make_exercise(project_files=[
            pf("pom.xml", "<project/>"),
            pf("src/test/java/com/example/AppTest.java", "package com.wrong;\nclass AppTest {}"),
        ])
        errors = validate_exercise_payload(exercise)
        assert any("package mismatch" in e for e in errors)

    def test_correct_test_package_in_project_files_no_error(self):
        exercise = make_exercise(project_files=[
            pf("pom.xml", "<project/>"),
            pf("src/test/java/com/example/AppTest.java", "package com.example;\nclass AppTest {}"),
        ])
        errors = validate_exercise_payload(exercise)
        assert not any("package mismatch" in e for e in errors)


# ─────────────────────────────────────────────
# compose_exercise
# ─────────────────────────────────────────────

class TestComposeExercise:
    def test_returns_spring_boot_exercise(self):
        result = compose_exercise(make_contract(), make_implementation())
        assert isinstance(result, SpringBootExercise)

    def test_problem_description_from_contract(self):
        contract = make_contract(problem_description="custom desc")
        result = compose_exercise(contract, make_implementation())
        assert result.problem_description == "custom desc"

    def test_test_files_from_contract(self):
        test_file = pf("src/test/java/AppTest.java", "package com.example;\nclass AppTest {}")
        contract = make_contract(test_files=[test_file])
        result = compose_exercise(contract, make_implementation())
        assert result.test_files[0].path == "src/test/java/AppTest.java"

    def test_paths_to_ex_from_contract(self):
        contract = make_contract(paths_to_ex=["src/main/java/App.java"])
        result = compose_exercise(contract, make_implementation())
        assert result.paths_to_ex == ["src/main/java/App.java"]

    def test_project_files_from_implementation(self):
        impl = make_implementation(project_files=[pf("pom.xml"), pf("src/main/java/Foo.java")])
        result = compose_exercise(make_contract(), impl)
        paths = [f.path for f in result.project_files]
        assert "src/main/java/Foo.java" in paths

    def test_solution_explanation_from_implementation(self):
        impl = make_implementation(solution_explanation_md="## Custom")
        result = compose_exercise(make_contract(), impl)
        assert result.solution_explanation_md == "## Custom"

    def test_answers_list_from_implementation(self):
        impl = make_implementation(answers_list=[pf("src/main/java/App.java", "fixed")])
        result = compose_exercise(make_contract(), impl)
        assert result.answers_list[0].content == "fixed"


# ─────────────────────────────────────────────
# get_backend
# ─────────────────────────────────────────────

class TestGetBackend:
    @patch("codellamas_backend.api.CodellamasBackend")
    def test_single_mode_returns_single_backend(self, mock_single):
        result = get_backend("single")
        mock_single.assert_called_once()
        assert result == mock_single.return_value

    @patch("codellamas_backend.api.CodellamasBackendMulti")
    def test_multi_mode_returns_multi_backend(self, mock_multi):
        result = get_backend("multi")
        mock_multi.assert_called_once()
        assert result == mock_multi.return_value

    def test_invalid_mode_raises_http_exception(self):
        with pytest.raises(HTTPException) as exc_info:
            get_backend("invalid")
        assert exc_info.value.status_code == 400
        assert "invalid" in exc_info.value.detail.lower()

    @patch("codellamas_backend.api.CodellamasBackend")
    def test_passes_model_name(self, mock_single):
        get_backend("single", model_name="gpt-4")
        mock_single.assert_called_once_with("gpt-4", None, None)

    @patch("codellamas_backend.api.CodellamasBackend")
    def test_passes_api_key(self, mock_single):
        get_backend("single", api_key="my-key")
        mock_single.assert_called_once_with(None, None, "my-key")


# ─────────────────────────────────────────────
# append_to_csv
# ─────────────────────────────────────────────

class TestAppendToCsv:
    def test_creates_file_with_header(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "output", "test.csv")
            with patch("codellamas_backend.api.CSV_FILE_PATH", csv_path):
                append_to_csv(exercise, "refactoring", "single", {})
                assert os.path.exists(csv_path)
                with open(csv_path) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                assert len(rows) == 1
                assert rows[0]["topic"] == "refactoring"

    def test_appends_without_duplicate_header(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "output", "test.csv")
            with patch("codellamas_backend.api.CSV_FILE_PATH", csv_path):
                append_to_csv(exercise, "topic1", "single", {})
                append_to_csv(exercise, "topic2", "single", {})
                with open(csv_path) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                assert len(rows) == 2

    def test_response_data_serialized_as_json(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "output", "test.csv")
            with patch("codellamas_backend.api.CSV_FILE_PATH", csv_path):
                append_to_csv(exercise, "topic", "single", {"key": "value"})
                with open(csv_path) as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                parsed = json.loads(rows[0]["response_json"])
                assert parsed["key"] == "value"

    def test_returns_absolute_path(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "output", "test.csv")
            with patch("codellamas_backend.api.CSV_FILE_PATH", csv_path):
                result = append_to_csv(exercise, "topic", "single", {})
                assert os.path.isabs(result)

    def test_append_to_csv_raises_on_error(self):
        exercise = make_exercise()
        with patch("builtins.open", side_effect=IOError("disk full")):
            with patch("os.makedirs"):
                with patch("os.path.isfile", return_value=False):
                    with pytest.raises(IOError):
                        append_to_csv(exercise, "topic", "single", {})


# ─────────────────────────────────────────────
# save_exercise_to_repo
# ─────────────────────────────────────────────

class TestSaveExerciseToRepo:
    def test_creates_problem_md(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                path = save_exercise_to_repo(exercise, "refactoring")
                assert os.path.exists(os.path.join(path, "PROBLEM.md"))

    def test_creates_solution_exp_md(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                path = save_exercise_to_repo(exercise, "refactoring")
                assert os.path.exists(os.path.join(path, "SOLUTION_EXP.md"))

    def test_writes_project_files(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                path = save_exercise_to_repo(exercise, "refactoring")
                assert os.path.exists(os.path.join(path, "src/main/java/App.java"))

    def test_writes_test_files(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                path = save_exercise_to_repo(exercise, "refactoring")
                assert os.path.exists(os.path.join(path, "src/test/java/AppTest.java"))

    def test_writes_answers_when_present(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                path = save_exercise_to_repo(exercise, "refactoring")
                answers_dir = os.path.join(path, "answers")
                assert os.path.exists(answers_dir)

    def test_no_answers_dir_when_empty(self):
        exercise = make_exercise(answers_list=[])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                path = save_exercise_to_repo(exercise, "refactoring")
                assert not os.path.exists(os.path.join(path, "answers"))

    def test_topic_in_folder_name(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                path = save_exercise_to_repo(exercise, "my topic")
                assert "my_topic" in path

    def test_returns_path_string(self):
        exercise = make_exercise()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("os.getcwd", return_value=tmpdir):
                result = save_exercise_to_repo(exercise, "refactoring")
                assert isinstance(result, str)


# ─────────────────────────────────────────────
# default_base_project_files
# ─────────────────────────────────────────────

class TestDefaultBaseProjectFiles:
    def test_returns_list(self):
        result = default_base_project_files()
        assert isinstance(result, list)

    def test_contains_pom_xml(self):
        result = default_base_project_files()
        assert any(f.path == "pom.xml" for f in result)

    def test_pom_contains_junit(self):
        result = default_base_project_files()
        pom = next(f for f in result if f.path == "pom.xml")
        assert "junit-jupiter" in pom.content


# ─────────────────────────────────────────────
# build_preflight_failure_context
# ─────────────────────────────────────────────

class TestBuildPreflightFailureContext:
    def test_label_in_output(self):
        result = build_preflight_failure_context("IMPLEMENTATION", ["error 1"])
        assert "IMPLEMENTATION" in result

    def test_errors_in_output(self):
        result = build_preflight_failure_context("IMPLEMENTATION", ["error 1", "error 2"])
        assert "error 1" in result
        assert "error 2" in result

    def test_errors_capped_at_10(self):
        errors = [f"error {i}" for i in range(20)]
        result = build_preflight_failure_context("IMPLEMENTATION", errors)
        lines = result.splitlines()
        error_lines = [l for l in lines if l.startswith("- ")]
        assert len(error_lines) == 10

    def test_empty_errors(self):
        result = build_preflight_failure_context("IMPLEMENTATION", [])
        assert "IMPLEMENTATION" in result


# ─────────────────────────────────────────────
# generate_single_contract
# ─────────────────────────────────────────────

class TestGenerateSingleContract:
    def _make_backend(self, contract: ContractSpec):
        mock_backend = MagicMock()
        mock_raw = MagicMock()
        mock_raw.json_dict = contract.model_dump()
        mock_backend.contract_crew.return_value.kickoff.return_value = mock_raw
        return mock_backend

    def test_returns_contract_on_valid_result(self):
        contract = make_contract()
        backend = self._make_backend(contract)
        result = generate_single_contract(
            backend=backend,
            topic="refactoring",
            code_smells="god class",
            existing_codebase="NONE",
        )
        assert isinstance(result, ContractSpec)
        assert result.problem_description == contract.problem_description

    def test_kickoff_called_with_correct_inputs(self):
        contract = make_contract()
        backend = self._make_backend(contract)
        generate_single_contract(
            backend=backend,
            topic="refactoring",
            code_smells="god class",
            existing_codebase="my code",
        )
        kickoff_kwargs = backend.contract_crew.return_value.kickoff.call_args[1]
        assert kickoff_kwargs["inputs"]["topic"] == "refactoring"
        assert kickoff_kwargs["inputs"]["code_smells"] == "god class"
        assert kickoff_kwargs["inputs"]["existing_codebase"] == "my code"

    def test_raises_http_exception_on_validation_failure(self):
        # return a contract with empty problem_description to trigger validation error
        bad_contract = make_contract(problem_description="   ")
        backend = self._make_backend(bad_contract)
        with pytest.raises(HTTPException) as exc_info:
            generate_single_contract(
                backend=backend,
                topic="refactoring",
                code_smells="god class",
                existing_codebase="NONE",
            )
        assert exc_info.value.status_code == 500
        assert "validation" in exc_info.value.detail.lower()

    def test_http_exception_contains_validation_errors(self):
        bad_contract = make_contract(problem_description="   ", test_files=[], paths_to_ex=[])
        backend = self._make_backend(bad_contract)
        with pytest.raises(HTTPException) as exc_info:
            generate_single_contract(
                backend=backend,
                topic="refactoring",
                code_smells="god class",
                existing_codebase="NONE",
            )
        assert "problem_description" in exc_info.value.detail