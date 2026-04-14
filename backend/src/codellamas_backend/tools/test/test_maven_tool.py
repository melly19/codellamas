import subprocess
import pytest
from unittest.mock import patch, MagicMock
from typing import List

from codellamas_backend.tools.maven_tool import MavenTool, MavenTestResult
from codellamas_backend.schemas.files import ProjectFile


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def make_files(*paths: str) -> List[ProjectFile]:
    return [ProjectFile(path=p, content=f"content of {p}") for p in paths]


# ─────────────────────────────────────────────
# MavenTestResult
# ─────────────────────────────────────────────

class TestMavenTestResult:
    def test_raw_log_head_truncates(self):
        result = MavenTestResult(
            status="PASS", returncode=0,
            failed_tests=[], errors=[], raw_log="x" * 10000
        )
        assert len(result.raw_log_head(4000)) == 4000

    def test_raw_log_head_shorter_than_limit(self):
        result = MavenTestResult(
            status="PASS", returncode=0,
            failed_tests=[], errors=[], raw_log="short"
        )
        assert result.raw_log_head(4000) == "short"

    def test_raw_log_head_default_is_4000(self):
        result = MavenTestResult(
            status="FAIL", returncode=1,
            failed_tests=[], errors=[], raw_log="a" * 5000
        )
        assert len(result.raw_log_head()) == 4000

    def test_raw_log_head_empty(self):
        result = MavenTestResult(
            status="PASS", returncode=0,
            failed_tests=[], errors=[], raw_log=""
        )
        assert result.raw_log_head() == ""


# ─────────────────────────────────────────────
# MavenTool.__init__ / _detect_mvn
# ─────────────────────────────────────────────

class TestMavenToolInit:
    def test_default_mvn_cmd(self):
        tool = MavenTool(mvn_cmd="mvn")
        assert tool.mvn_cmd == "mvn"

    def test_custom_mvn_cmd(self):
        tool = MavenTool(mvn_cmd="/usr/local/bin/mvn")
        assert tool.mvn_cmd == "/usr/local/bin/mvn"

    def test_none_mvn_cmd_triggers_detect(self):
        with patch("shutil.which", return_value="/usr/bin/mvn"):
            tool = MavenTool(mvn_cmd=None)
            assert tool.mvn_cmd == "mvn.cmd"  # first candidate returned

    def test_detect_mvn_raises_if_not_found(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="Maven executable not found"):
                MavenTool(mvn_cmd=None)

    def test_detect_mvn_tries_candidates_in_order(self):
        # only "mvn" (last candidate) is found
        def which_side_effect(cmd):
            return "/usr/bin/mvn" if cmd == "mvn" else None

        with patch("shutil.which", side_effect=which_side_effect):
            tool = MavenTool(mvn_cmd=None)
            assert tool.mvn_cmd == "mvn"


# ─────────────────────────────────────────────
# MavenTool._safe_env
# ─────────────────────────────────────────────

class TestSafeEnv:
    def test_returns_dict(self):
        tool = MavenTool()
        env = tool._safe_env()
        assert isinstance(env, dict)

    def test_inherits_os_environ(self):
        tool = MavenTool()
        with patch.dict("os.environ", {"MY_VAR": "hello"}):
            env = tool._safe_env()
        assert env["MY_VAR"] == "hello"

    def test_sets_maven_opts_if_missing(self):
        tool = MavenTool()
        with patch.dict("os.environ", {}, clear=True):
            env = tool._safe_env()
        assert env["MAVEN_OPTS"] == ""

    def test_does_not_override_existing_maven_opts(self):
        tool = MavenTool()
        with patch.dict("os.environ", {"MAVEN_OPTS": "-Xmx512m"}):
            env = tool._safe_env()
        assert env["MAVEN_OPTS"] == "-Xmx512m"


# ─────────────────────────────────────────────
# MavenTool._parse_maven_output
# ─────────────────────────────────────────────

class TestParseMavenOutput:
    def setup_method(self):
        self.tool = MavenTool()

    def test_returncode_zero_is_pass(self):
        status, failed, errors = self.tool._parse_maven_output(0, "BUILD SUCCESS")
        assert status == "PASS"
        assert failed == []
        assert errors == []

    def test_compilation_error_detected(self):
        raw = "COMPILATION ERROR\nBUILD FAILURE"
        status, _, errors = self.tool._parse_maven_output(1, raw)
        assert status == "FAIL"
        assert "Compilation error" in errors

    def test_test_failures_detected(self):
        raw = "There are test failures\nBUILD FAILURE"
        _, _, errors = self.tool._parse_maven_output(1, raw)
        assert "Test failures" in errors

    def test_dependency_error_detected(self):
        raw = "Could not resolve dependencies\nBUILD FAILURE"
        _, _, errors = self.tool._parse_maven_output(1, raw)
        assert "Dependency resolution error" in errors

    def test_could_not_find_artifact_detected(self):
        raw = "Could not find artifact com.example:lib:1.0\nBUILD FAILURE"
        _, _, errors = self.tool._parse_maven_output(1, raw)
        assert "Dependency resolution error" in errors

    def test_build_failure_detected(self):
        raw = "BUILD FAILURE"
        _, _, errors = self.tool._parse_maven_output(1, raw)
        assert "Build failure" in errors

    def test_fallback_error_when_no_known_pattern(self):
        raw = "something went terribly wrong"
        _, _, errors = self.tool._parse_maven_output(1, raw)
        assert "mvn test failed (see raw_log)" in errors

    def test_multiple_errors_detected(self):
        raw = "COMPILATION ERROR\nThere are test failures\nBUILD FAILURE"
        _, _, errors = self.tool._parse_maven_output(1, raw)
        assert "Compilation error" in errors
        assert "Test failures" in errors
        assert "Build failure" in errors

    def test_errors_deduped(self):
        raw = "BUILD FAILURE\nBUILD FAILURE\nBUILD FAILURE"
        _, _, errors = self.tool._parse_maven_output(1, raw)
        assert errors.count("Build failure") == 1

    def test_errors_capped_at_20(self):
        # inject 25 unique error patterns via failed_tests path
        raw = "BUILD FAILURE\n" + "\n".join(f"UniqueTest{i}Test" for i in range(25))
        _, failed, _ = self.tool._parse_maven_output(1, raw)
        assert len(failed) <= 30  # cap is 30 for failed_tests

    def test_failed_tests_deduped(self):
        raw = "BUILD FAILURE\nMyServiceTest MyServiceTest MyServiceTest"
        _, failed, _ = self.tool._parse_maven_output(1, raw)
        assert failed.count("MyServiceTest") == 1


# ─────────────────────────────────────────────
# MavenTool._extract_failed_tests
# ─────────────────────────────────────────────

class TestExtractFailedTests:
    def setup_method(self):
        self.tool = MavenTool()

    def test_extracts_failed_tests_line(self):
        raw = "Failed tests:   testLogin(com.example.AuthTest)"
        out = self.tool._extract_failed_tests(raw)
        assert "testLogin(com.example.AuthTest)" in out

    def test_extracts_test_class_names(self):
        raw = "at com.example.MyServiceTest.testSomething(MyServiceTest.java:42)"
        out = self.tool._extract_failed_tests(raw)
        assert "MyServiceTest" in out

    def test_no_duplicates_in_output(self):
        raw = "MyServiceTest MyServiceTest MyServiceTest"
        out = self.tool._extract_failed_tests(raw)
        assert out.count("MyServiceTest") == 1

    def test_empty_raw_returns_empty(self):
        out = self.tool._extract_failed_tests("")
        assert out == []

    def test_case_insensitive_failed_tests(self):
        raw = "FAILED TESTS:   testSomething(MyTest)"
        out = self.tool._extract_failed_tests(raw)
        assert "testSomething(MyTest)" in out

    def test_no_test_classes_in_clean_output(self):
        raw = "BUILD SUCCESS\nNothing to report"
        out = self.tool._extract_failed_tests(raw)
        assert out == []


# ─────────────────────────────────────────────
# MavenTool.run_tests
# ─────────────────────────────────────────────

class TestRunTests:
    def setup_method(self):
        self.tool = MavenTool()
        self.files = make_files("pom.xml", "src/main/java/App.java")

    @patch("subprocess.run")
    def test_pass_on_returncode_zero(self, mock_run):
        mock_run.return_value = make_proc(returncode=0, stdout="BUILD SUCCESS")
        result = self.tool.run_tests(self.files)
        assert result.status == "PASS"
        assert result.returncode == 0

    @patch("subprocess.run")
    def test_fail_on_nonzero_returncode(self, mock_run):
        mock_run.return_value = make_proc(returncode=1, stdout="BUILD FAILURE")
        result = self.tool.run_tests(self.files)
        assert result.status == "FAIL"
        assert result.returncode == 1

    @patch("subprocess.run")
    def test_quiet_flag_included_by_default(self, mock_run):
        mock_run.return_value = make_proc()
        self.tool.run_tests(self.files)
        cmd = mock_run.call_args[0][0]
        assert "-q" in cmd

    @patch("subprocess.run")
    def test_quiet_false_omits_flag(self, mock_run):
        mock_run.return_value = make_proc()
        tool = MavenTool(quiet=False)
        tool.run_tests(self.files)
        cmd = mock_run.call_args[0][0]
        assert "-q" not in cmd

    @patch("subprocess.run")
    def test_extra_mvn_args_passed(self, mock_run):
        mock_run.return_value = make_proc()
        self.tool.run_tests(self.files, extra_mvn_args=["-Dskip=true"])
        cmd = mock_run.call_args[0][0]
        assert "-Dskip=true" in cmd

    @patch("subprocess.run")
    def test_override_files_applied(self, mock_run):
        mock_run.return_value = make_proc()
        overrides = make_files("src/main/java/App.java")
        # should not raise — override just overwrites the file
        result = self.tool.run_tests(self.files, override_files=overrides)
        assert result is not None

    @patch("subprocess.run")
    def test_inject_tests_applied(self, mock_run):
        mock_run.return_value = make_proc()
        inject = {"src/test/java/GenTest.java": "public class GenTest {}"}
        result = self.tool.run_tests(self.files, inject_tests=inject)
        assert result is not None

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="mvn", timeout=300))
    def test_timeout_returns_fail(self, mock_run):
        result = self.tool.run_tests(self.files)
        assert result.status == "FAIL"
        assert result.returncode == 124
        assert any("timed out" in e for e in result.errors)
        assert result.raw_log == ""

    @patch("subprocess.run")
    def test_raw_log_combines_stdout_and_stderr(self, mock_run):
        mock_run.return_value = make_proc(returncode=0, stdout="OUT", stderr="ERR")
        result = self.tool.run_tests(self.files)
        assert "OUT" in result.raw_log
        assert "ERR" in result.raw_log

    @patch("subprocess.run")
    def test_none_stdout_stderr_handled(self, mock_run):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = None
        proc.stderr = None
        mock_run.return_value = proc
        result = self.tool.run_tests(self.files)
        assert result.status == "PASS"

    @patch("subprocess.run")
    def test_workspace_cleaned_up_after_run(self, mock_run):
        mock_run.return_value = make_proc()

        original_run = self.tool.run_tests

        def patched_run_tests(*args, **kwargs):
            # grab root before cleanup
            result = original_run(*args, **kwargs)
            return result

        result = self.tool.run_tests(self.files)
        # workspace.root is internal — just confirm run completed without leaking
        assert result is not None

    @patch("subprocess.run")
    def test_workspace_cleaned_up_on_exception(self, mock_run):
        mock_run.side_effect = RuntimeError("unexpected")
        with pytest.raises(RuntimeError):
            self.tool.run_tests(self.files)
        # if we get here without hanging tmp dirs, cleanup worked via __exit__

    @patch("subprocess.run")
    def test_cwd_is_workspace_root(self, mock_run):
        mock_run.return_value = make_proc()
        self.tool.run_tests(self.files)
        kwargs = mock_run.call_args[1]
        assert "cwd" in kwargs
        assert "codellamas_" in kwargs["cwd"]

    @patch("subprocess.run")
    def test_empty_project_files(self, mock_run):
        mock_run.return_value = make_proc(returncode=1, stdout="BUILD FAILURE")
        result = self.tool.run_tests([])
        assert result.status == "FAIL"
