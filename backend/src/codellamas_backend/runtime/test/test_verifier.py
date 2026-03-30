import unittest
from unittest import result
from unittest.mock import Mock, patch, MagicMock
from codellamas_backend.runtime.verifier import MavenVerifier, VerificationResult
from codellamas_backend.schemas.files import ProjectFile

class TestVerificationResult(unittest.TestCase):
    def test_summary_returns_raw_log_truncated(self):
        long_log = "x" * 5000
        result = VerificationResult(
            status="PASS",
            failed_tests=[],
            errors=[],
            raw_log=long_log
        )
        summary = result.summary()
        self.assertEqual(len(summary), 4000)
        self.assertEqual(summary, long_log[:4000])

    def test_summary_short_log(self):
        short_log = "short log"
        result = VerificationResult(
            status="FAIL",
            failed_tests=["test1"],
            errors=[],
            raw_log=short_log
        )
        self.assertEqual(result.summary(), short_log)


class TestMavenVerifier(unittest.TestCase):
    @patch.dict('os.environ', {'MAVEN_CMD': '/usr/bin/mvn'})
    @patch('codellamas_backend.runtime.verifier.MavenTool')
    def test_init_with_env_var(self, mock_maven_tool):
        verifier = MavenVerifier(timeout_sec=300, quiet=False)
        mock_maven_tool.assert_called_once_with(mvn_cmd='/usr/bin/mvn', timeout_sec=300, quiet=False)

    @patch.dict('os.environ', {}, clear=True)
    @patch('codellamas_backend.runtime.verifier.MavenTool')
    def test_init_default_maven_cmd(self, mock_maven_tool):
        verifier = MavenVerifier()
        mock_maven_tool.assert_called_once_with(mvn_cmd='', timeout_sec=600, quiet=True)

    @patch('codellamas_backend.runtime.verifier.MavenTool')
    def test_verify_with_all_parameters(self, mock_maven_tool):
        mock_maven_instance = Mock()
        mock_maven_tool.return_value = mock_maven_instance
        
        mock_result = Mock()
        mock_result.status = "PASS"
        mock_result.failed_tests = []
        mock_result.errors = []
        mock_result.raw_log_head = Mock(return_value="test log")
        mock_maven_instance.run_tests.return_value = mock_result
        
        verifier = MavenVerifier()
        base_files = [Mock(spec=ProjectFile)]
        override_files = [Mock(spec=ProjectFile)]
        injected_tests = {"test.java": "code"}
        
        result = verifier.verify(base_files, override_files, injected_tests)
        
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.raw_log, "test log")
        self.assertEqual(result.failed_tests, [])
        self.assertEqual(result.errors, [])
        mock_maven_instance.run_tests.assert_called_once_with(
            project_files=base_files,
            override_files=override_files,
            inject_tests=injected_tests
        )

    @patch('codellamas_backend.runtime.verifier.MavenTool')
    def test_verify_with_fail_status(self, mock_maven_tool):
        mock_maven_instance = Mock()
        mock_maven_tool.return_value = mock_maven_instance
        
        mock_result = Mock()
        mock_result.status = "FAIL"
        mock_result.failed_tests = ["TestCase::testMethod"]
        mock_result.errors = ["Compilation error"]
        mock_result.raw_log_head = Mock(return_value="error log")
        mock_maven_instance.run_tests.return_value = mock_result
        
        verifier = MavenVerifier()
        base_files = [Mock(spec=ProjectFile)]
        
        result = verifier.verify(base_files)
        
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.failed_tests, ["TestCase::testMethod"])
        self.assertEqual(result.errors, ["Compilation error"])
        self.assertEqual(result.raw_log, "error log")
        mock_maven_instance.run_tests.assert_called_once_with(
            project_files=base_files,
            override_files=[],
            inject_tests={}
        )

    @patch('codellamas_backend.runtime.verifier.MavenTool')
    def test_verify_error_status(self, mock_maven_tool):
        mock_maven_instance = Mock()
        mock_maven_tool.return_value = mock_maven_instance
        
        mock_result = Mock()
        mock_result.status = "ERROR"
        mock_result.failed_tests = []
        mock_result.errors = ["Maven timeout"]
        mock_result.raw_log_head = Mock(return_value="x" * 8000)
        mock_maven_instance.run_tests.return_value = mock_result
        
        verifier = MavenVerifier()
        result = verifier.verify([Mock(spec=ProjectFile)])
        
        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.failed_tests, [])
        self.assertEqual(result.errors, ["Maven timeout"])
        self.assertEqual(result.raw_log, "x" * 8000)
        mock_result.raw_log_head.assert_called_once_with(8000)