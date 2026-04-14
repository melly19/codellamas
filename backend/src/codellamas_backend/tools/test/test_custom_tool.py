import json
import os
import subprocess
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from codellamas_backend.tools.custom_tool import JavaTestRunnerTool, TestRunnerInput


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_proc(returncode=0, stdout="BUILD SUCCESS", stderr="") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


SAMPLE_SOURCE = {"src/main/java/App.java": "public class App {}"}
SAMPLE_TESTS = {"src/test/java/AppTest.java": "public class AppTest {}"}


# ─────────────────────────────────────────────
# TestRunnerInput schema
# ─────────────────────────────────────────────

class TestTestRunnerInput:
    def test_valid_input(self):
        inp = TestRunnerInput(source_files=SAMPLE_SOURCE, test_files=SAMPLE_TESTS)
        assert inp.build_tool == "maven"

    def test_custom_build_tool(self):
        inp = TestRunnerInput(source_files=SAMPLE_SOURCE, test_files=SAMPLE_TESTS, build_tool="gradle")
        assert inp.build_tool == "gradle"

    def test_missing_source_files_raises(self):
        with pytest.raises(Exception):
            TestRunnerInput(test_files=SAMPLE_TESTS)

    def test_missing_test_files_raises(self):
        with pytest.raises(Exception):
            TestRunnerInput(source_files=SAMPLE_SOURCE)

    def test_empty_dicts_allowed(self):
        inp = TestRunnerInput(source_files={}, test_files={})
        assert inp.source_files == {}
        assert inp.test_files == {}


# ─────────────────────────────────────────────
# JavaTestRunnerTool._default_pom
# ─────────────────────────────────────────────

class TestDefaultPom:
    def setup_method(self):
        self.tool = JavaTestRunnerTool()

    def test_returns_string(self):
        assert isinstance(self.tool._default_pom(), str)

    def test_contains_junit_jupiter(self):
        pom = self.tool._default_pom()
        assert "junit-jupiter" in pom

    def test_contains_surefire_plugin(self):
        pom = self.tool._default_pom()
        assert "maven-surefire-plugin" in pom

    def test_contains_group_id(self):
        pom = self.tool._default_pom()
        assert "edu.exercise" in pom

    def test_is_valid_xml_structure(self):
        pom = self.tool._default_pom()
        assert "<project" in pom
        assert "</project>" in pom


# ─────────────────────────────────────────────
# JavaTestRunnerTool._write_project_files
# ─────────────────────────────────────────────

class TestWriteProjectFiles:
    def setup_method(self):
        self.tool = JavaTestRunnerTool()

    def test_writes_source_and_test_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tool._write_project_files(tmpdir, SAMPLE_SOURCE, SAMPLE_TESTS)
            assert os.path.exists(os.path.join(tmpdir, "src/main/java/App.java"))
            assert os.path.exists(os.path.join(tmpdir, "src/test/java/AppTest.java"))

    def test_writes_correct_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tool._write_project_files(tmpdir, SAMPLE_SOURCE, SAMPLE_TESTS)
            with open(os.path.join(tmpdir, "src/main/java/App.java")) as f:
                assert f.read() == "public class App {}"

    def test_creates_pom_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tool._write_project_files(tmpdir, SAMPLE_SOURCE, SAMPLE_TESTS)
            assert os.path.exists(os.path.join(tmpdir, "pom.xml"))

    def test_does_not_overwrite_existing_pom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pom_path = os.path.join(tmpdir, "pom.xml")
            with open(pom_path, "w") as f:
                f.write("<custom>pom</custom>")
            self.tool._write_project_files(tmpdir, SAMPLE_SOURCE, SAMPLE_TESTS)
            with open(pom_path) as f:
                assert f.read() == "<custom>pom</custom>"

    def test_creates_nested_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deep = {"src/main/java/com/example/deep/App.java": "class App {}"}
            self.tool._write_project_files(tmpdir, deep, {})
            assert os.path.exists(os.path.join(tmpdir, "src/main/java/com/example/deep/App.java"))

    def test_empty_source_and_test_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # should not raise, just write pom
            self.tool._write_project_files(tmpdir, {}, {})
            assert os.path.exists(os.path.join(tmpdir, "pom.xml"))

    def test_test_files_override_source_files_on_same_path(self):
        # dict merge: test_files wins on collision
        with tempfile.TemporaryDirectory() as tmpdir:
            source = {"src/Foo.java": "source content"}
            tests = {"src/Foo.java": "test content"}
            self.tool._write_project_files(tmpdir, source, tests)
            with open(os.path.join(tmpdir, "src/Foo.java")) as f:
                assert f.read() == "test content"

    def test_pom_content_is_default_pom(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.tool._write_project_files(tmpdir, {}, {})
            with open(os.path.join(tmpdir, "pom.xml")) as f:
                content = f.read()
            assert "junit-jupiter" in content


# ─────────────────────────────────────────────
# JavaTestRunnerTool._run_tests
# ─────────────────────────────────────────────

class TestRunTestsMethod:
    def setup_method(self):
        self.tool = JavaTestRunnerTool()

    @patch("subprocess.run")
    def test_success_on_returncode_zero(self, mock_run):
        mock_run.return_value = make_proc(returncode=0, stdout="BUILD SUCCESS")
        result = self.tool._run_tests("/tmp/project", "maven")
        assert result["success"] is True
        assert result["return_code"] == 0

    @patch("subprocess.run")
    def test_failure_on_nonzero_returncode(self, mock_run):
        mock_run.return_value = make_proc(returncode=1, stdout="BUILD FAILURE")
        result = self.tool._run_tests("/tmp/project", "maven")
        assert result["success"] is False
        assert result["return_code"] == 1

    @patch("subprocess.run")
    def test_stdout_and_stderr_returned(self, mock_run):
        mock_run.return_value = make_proc(stdout="OUT", stderr="ERR")
        result = self.tool._run_tests("/tmp/project", "maven")
        assert result["stdout"] == "OUT"
        assert result["stderr"] == "ERR"

    @patch("subprocess.run")
    def test_calls_mvn_test(self, mock_run):
        mock_run.return_value = make_proc()
        self.tool._run_tests("/tmp/project", "maven")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd == "mvn test"

    @patch("subprocess.run")
    def test_cwd_is_project_dir(self, mock_run):
        mock_run.return_value = make_proc()
        self.tool._run_tests("/tmp/myproject", "maven")
        kwargs = mock_run.call_args[1]
        assert kwargs["cwd"] == "/tmp/myproject"

    @patch("subprocess.run")
    def test_timeout_set_to_60(self, mock_run):
        mock_run.return_value = make_proc()
        self.tool._run_tests("/tmp/project", "maven")
        kwargs = mock_run.call_args[1]
        assert kwargs["timeout"] == 60

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="mvn", timeout=60))
    def test_timeout_returns_error(self, mock_run):
        result = self.tool._run_tests("/tmp/project", "maven")
        assert result["success"] is False
        assert "timed out" in result["error"]

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="mvn", timeout=60))
    def test_timeout_has_no_return_code(self, mock_run):
        result = self.tool._run_tests("/tmp/project", "maven")
        assert "return_code" not in result

    @patch("subprocess.run")
    def test_result_has_all_keys_on_success(self, mock_run):
        mock_run.return_value = make_proc()
        result = self.tool._run_tests("/tmp/project", "maven")
        assert all(k in result for k in ("success", "return_code", "stdout", "stderr"))


# ─────────────────────────────────────────────
# JavaTestRunnerTool._run (main entry point)
# ─────────────────────────────────────────────

class TestRun:
    def setup_method(self):
        self.tool = JavaTestRunnerTool()

    @patch("subprocess.run")
    def test_returns_json_string(self, mock_run):
        mock_run.return_value = make_proc()
        result = self.tool._run(SAMPLE_SOURCE, SAMPLE_TESTS)
        parsed = json.loads(result)   # should not raise
        assert isinstance(parsed, dict)

    @patch("subprocess.run")
    def test_success_true_on_pass(self, mock_run):
        mock_run.return_value = make_proc(returncode=0)
        result = json.loads(self.tool._run(SAMPLE_SOURCE, SAMPLE_TESTS))
        assert result["success"] is True

    @patch("subprocess.run")
    def test_success_false_on_fail(self, mock_run):
        mock_run.return_value = make_proc(returncode=1)
        result = json.loads(self.tool._run(SAMPLE_SOURCE, SAMPLE_TESTS))
        assert result["success"] is False

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="mvn", timeout=60))
    def test_timeout_in_run(self, mock_run):
        result = json.loads(self.tool._run(SAMPLE_SOURCE, SAMPLE_TESTS))
        assert result["success"] is False
        assert "timed out" in result["error"]

    @patch("subprocess.run")
    def test_temp_dir_cleaned_up_after_run(self, mock_run):
        mock_run.return_value = make_proc()
        captured = {}

        original_run_tests = self.tool._run_tests

        def capturing_run_tests(project_dir, build_tool):
            captured["dir"] = project_dir
            return original_run_tests(project_dir, build_tool)

        with patch.object(self.tool, "_run_tests", side_effect=capturing_run_tests):
            self.tool._run(SAMPLE_SOURCE, SAMPLE_TESTS)

        assert not os.path.exists(captured["dir"])

    @patch("subprocess.run")
    def test_temp_dir_cleaned_up_on_exception(self, mock_run):
        mock_run.side_effect = RuntimeError("unexpected")
        captured = {}

        original_run_tests = self.tool._run_tests

        def capturing_run_tests(project_dir, build_tool):
            captured["dir"] = project_dir
            return original_run_tests(project_dir, build_tool)

        with patch.object(self.tool, "_run_tests", side_effect=capturing_run_tests):
            with pytest.raises(RuntimeError):
                self.tool._run(SAMPLE_SOURCE, SAMPLE_TESTS)

        assert not os.path.exists(captured["dir"])

    @patch("subprocess.run")
    def test_empty_source_and_test_files(self, mock_run):
        mock_run.return_value = make_proc(returncode=1, stdout="BUILD FAILURE")
        result = json.loads(self.tool._run({}, {}))
        assert result["success"] is False

    @patch("subprocess.run")
    def test_default_build_tool_is_maven(self, mock_run):
        mock_run.return_value = make_proc()
        self.tool._run(SAMPLE_SOURCE, SAMPLE_TESTS)
        cmd = mock_run.call_args[0][0]
        assert "mvn" in cmd

    @patch("subprocess.run")
    def test_json_is_indented(self, mock_run):
        mock_run.return_value = make_proc()
        result = self.tool._run(SAMPLE_SOURCE, SAMPLE_TESTS)
        assert "\n" in result  # indent=2 produces newlines
