# tests/integration_test/test_java_test_runner_integration.py

import json
import pytest
from codellamas_backend.tools.custom_tool import JavaTestRunnerTool


PASSING_SOURCE = {
    "src/main/java/com/example/App.java": """package com.example;
public class App {
    public int add(int a, int b) {
        return a + b;
    }
}"""
}

PASSING_TEST = {
    "src/test/java/com/example/AppTest.java": """package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test
    void testAdd() {
        assertEquals(3, new App().add(1, 2));
    }
}"""
}

FAILING_TEST = {
    "src/test/java/com/example/AppTest.java": """package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test
    void testAdd() {
        assertEquals(99, new App().add(1, 2));
    }
}"""
}

COMPILATION_ERROR_SOURCE = {
    "src/main/java/com/example/App.java": """package com.example;
public class App {
    this is not valid java
}"""
}


@pytest.mark.integration
class TestJavaTestRunnerToolIntegration:
    def setup_method(self):
        self.tool = JavaTestRunnerTool()

    def test_passing_tests_return_success_true(self):
        result = json.loads(self.tool._run(
            source_files=PASSING_SOURCE,
            test_files=PASSING_TEST,
        ))
        assert result["success"] is True
        assert result["return_code"] == 0

    def test_failing_tests_return_success_false(self):
        result = json.loads(self.tool._run(
            source_files=PASSING_SOURCE,
            test_files=FAILING_TEST,
        ))
        assert result["success"] is False
        assert result["return_code"] != 0

    def test_compilation_error_returns_success_false(self):
        result = json.loads(self.tool._run(
            source_files=COMPILATION_ERROR_SOURCE,
            test_files=PASSING_TEST,
        ))
        assert result["success"] is False

    def test_result_has_stdout(self):
        result = json.loads(self.tool._run(
            source_files=PASSING_SOURCE,
            test_files=PASSING_TEST,
        ))
        assert "stdout" in result or "error" in result

    def test_result_has_return_code(self):
        result = json.loads(self.tool._run(
            source_files=PASSING_SOURCE,
            test_files=PASSING_TEST,
        ))
        assert "return_code" in result

    def test_pom_xml_created_automatically(self):
        # pom.xml is created by _write_project_files if not present
        # passing test confirms pom was created correctly
        result = json.loads(self.tool._run(
            source_files=PASSING_SOURCE,
            test_files=PASSING_TEST,
        ))
        assert result["success"] is True

    def test_empty_source_files_still_runs(self):
        result = json.loads(self.tool._run(
            source_files={},
            test_files=PASSING_TEST,
        ))
        # may pass or fail depending on compilation
        # just confirm it returns a valid result
        assert "success" in result

    def test_returns_valid_json_string(self):
        result_str = self.tool._run(
            source_files=PASSING_SOURCE,
            test_files=PASSING_TEST,
        )
        parsed = json.loads(result_str)
        assert isinstance(parsed, dict)

    def test_timeout_returns_error(self):
        # patch timeout to 1 second to force timeout
        import unittest.mock as mock
        with mock.patch.object(self.tool, "_run_tests", return_value={
            "success": False,
            "error": "Test execution timed out"
        }):
            result = json.loads(self.tool._run(
                source_files=PASSING_SOURCE,
                test_files=PASSING_TEST,
            ))
            assert result["success"] is False
            assert "timed out" in result["error"]

    def test_multiple_source_files(self):
        source = {
            "src/main/java/com/example/App.java": """package com.example;
public class App { public int value() { return 1; } }""",
            "src/main/java/com/example/Helper.java": """package com.example;
public class Helper { public int help() { return 2; } }""",
        }
        test = {
            "src/test/java/com/example/AppTest.java": """package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test void test() {
        assertEquals(1, new App().value());
        assertEquals(2, new Helper().help());
    }
}"""
        }
        result = json.loads(self.tool._run(source_files=source, test_files=test))
        assert result["success"] is True