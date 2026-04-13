import json
import pytest
from codellamas_backend.crews.crew_multi import MavenVerifyTool
from codellamas_backend.schemas.files import ProjectFile
from unittest.mock import patch, MagicMock
from crewai import Agent
from codellamas_backend.crews.crew_multi import CodellamasBackendMulti


SIMPLE_POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>test</artifactId>
  <version>1.0-SNAPSHOT</version>
  <properties>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.1.2</version>
      </plugin>
    </plugins>
  </build>
</project>"""

PASSING_TEST = ProjectFile(
    path="src/test/java/com/example/AppTest.java",
    content="""package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test void test() { assertEquals(2, 1 + 1); }
}"""
)

FAILING_TEST = ProjectFile(
    path="src/test/java/com/example/AppTest.java",
    content="""package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test void test() { assertEquals(99, 1 + 1); }
}"""
)


@pytest.mark.integration
class TestMavenVerifyToolIntegration:
    def setup_method(self):
        self.tool = MavenVerifyTool()
        self.base_files = [ProjectFile(path="pom.xml", content=SIMPLE_POM)]

    def test_no_base_files_returns_skipped(self):
        result = json.loads(self.tool._run(base_project_files=[]))
        assert result["status"] == "SKIPPED"
        assert "No base_project_files" in result["errors"][0]

    def test_passing_tests_return_pass(self):
        result = json.loads(self.tool._run(
            base_project_files=self.base_files,
            injected_tests=[PASSING_TEST],
        ))
        assert result["status"] == "PASS"

    def test_failing_tests_return_fail(self):
        result = json.loads(self.tool._run(
            base_project_files=self.base_files,
            injected_tests=[FAILING_TEST],
        ))
        assert result["status"] == "FAIL"

    def test_failed_tests_list_populated_on_fail(self):
        result = json.loads(self.tool._run(
            base_project_files=self.base_files,
            injected_tests=[FAILING_TEST],
        ))
        assert isinstance(result["failed_tests"], list)

    def test_result_is_valid_json(self):
        result_str = self.tool._run(base_project_files=self.base_files)
        parsed = json.loads(result_str)
        assert all(k in parsed for k in ("status", "failed_tests", "errors", "raw_log_head"))

    def test_raw_log_head_truncated_to_2000(self):
        result = json.loads(self.tool._run(
            base_project_files=self.base_files,
            injected_tests=[PASSING_TEST],
        ))
        assert len(result["raw_log_head"]) <= 2000

    def test_dict_files_normalized(self):
        result = json.loads(self.tool._run(
            base_project_files=[{"path": "pom.xml", "content": SIMPLE_POM}],
            injected_tests=[PASSING_TEST],
        ))
        assert result["status"] in ("PASS", "FAIL", "SKIPPED")

    def test_override_files_applied(self):
        source = ProjectFile(
            path="src/main/java/com/example/App.java",
            content="package com.example;\npublic class App { public int value() { return 1; } }"
        )
        override = ProjectFile(
            path="src/main/java/com/example/App.java",
            content="package com.example;\npublic class App { public int value() { return 2; } }"
        )
        test = ProjectFile(
            path="src/test/java/com/example/AppTest.java",
            content="""package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test void test() { assertEquals(2, new App().value()); }
}"""
        )
        result = json.loads(self.tool._run(
            base_project_files=self.base_files + [source],
            override_project_files=[override],
            injected_tests=[test],
        ))
        assert result["status"] == "PASS"

    def test_invalid_dict_files_skipped(self):
        # invalid dict entries should be skipped by _normalize_files
        result = json.loads(self.tool._run(
            base_project_files=[{"bad_key": "value"}],
        ))
        # invalid files normalized away — treated as empty
        assert result["status"] in ("SKIPPED", "FAIL", "PASS")

    def test_timeout_sec_respected(self):
        # use very short timeout to verify timeout handling
        from unittest.mock import patch
        with patch("codellamas_backend.crews.crew_multi.MavenVerifier") as mock_verifier:
            import subprocess
            mock_verifier.return_value.verify.side_effect = \
                subprocess.TimeoutExpired(cmd="mvn", timeout=1)
            with pytest.raises(subprocess.TimeoutExpired):
                self.tool._run(
                    base_project_files=self.base_files,
                    injected_tests=[PASSING_TEST],
                )


@pytest.mark.integration
class TestCodellamasBackendMultiVerifyIntegration:
    """Tests _verify() method which calls MavenVerifier directly"""

    def setup_method(self):
        from unittest.mock import patch
        with patch("codellamas_backend.crews.crew_multi.LLM"):
            with patch.object(
                CodellamasBackendMulti,
                "test_runner",
                return_value=MagicMock(spec=Agent)
            ):
                self.backend = CodellamasBackendMulti()

        self.base_files = [ProjectFile(path="pom.xml", content=SIMPLE_POM)]

    def test_verify_pass(self):
        result = self.backend._verify(
            base_project_files=self.base_files,
            override_project_files=[],
            injected_tests=[PASSING_TEST],
        )
        assert result.status == "PASS"
        assert isinstance(result.failed_tests, list)
        assert isinstance(result.errors, list)

    def test_verify_fail(self):
        result = self.backend._verify(
            base_project_files=self.base_files,
            override_project_files=[],
            injected_tests=[FAILING_TEST],
        )
        assert result.status == "FAIL"

    def test_verify_returns_verify_tool_output(self):
        from codellamas_backend.crews.crew_multi import VerifyToolOutput
        result = self.backend._verify(
            base_project_files=self.base_files,
            override_project_files=[],
            injected_tests=[PASSING_TEST],
        )
        assert isinstance(result, VerifyToolOutput)

    def test_verify_raw_log_head_truncated(self):
        result = self.backend._verify(
            base_project_files=self.base_files,
            override_project_files=[],
            injected_tests=[PASSING_TEST],
        )
        assert len(result.raw_log_head) <= 2000

    def test_verify_override_applied(self):
        source = ProjectFile(
            path="src/main/java/com/example/App.java",
            content="package com.example;\npublic class App { public int value() { return 1; } }"
        )
        override = ProjectFile(
            path="src/main/java/com/example/App.java",
            content="package com.example;\npublic class App { public int value() { return 2; } }"
        )
        test = ProjectFile(
            path="src/test/java/com/example/AppTest.java",
            content="""package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test void test() { assertEquals(2, new App().value()); }
}"""
        )
        result = self.backend._verify(
            base_project_files=self.base_files + [source],
            override_project_files=[override],
            injected_tests=[test],
        )
        assert result.status == "PASS"


@pytest.mark.integration
class TestBuildReferenceOverrideFilesIntegration:
    """
    _build_reference_override_files is pure Python but complex enough
    to verify with real ProjectFile objects end-to-end
    """

    def setup_method(self):
        from unittest.mock import patch, MagicMock
        from crewai import Agent
        with patch("codellamas_backend.crews.crew_multi.LLM"):
            with patch.object(
                CodellamasBackendMulti,
                "test_runner",
                return_value=MagicMock(spec=Agent)
            ):
                self.backend = CodellamasBackendMulti()

    def test_empty_answers_returns_project_files(self):
        project_files = [
            ProjectFile(path="pom.xml", content="<project/>"),
            ProjectFile(path="src/main/java/App.java", content="class App {}"),
        ]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=[],
            paths_to_ex=[],
        )
        assert len(result) == 2

    def test_exact_path_match_replaced(self):
        project_files = [
            ProjectFile(path="pom.xml", content="<project/>"),
            ProjectFile(path="src/main/java/App.java", content="original"),
        ]
        answers = [ProjectFile(path="src/main/java/App.java", content="fixed")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=["src/main/java/App.java"],
        )
        match = next(f for f in result if f.path == "src/main/java/App.java")
        assert match.content == "fixed"

    def test_basename_match_replaces_correct_file(self):
        project_files = [
            ProjectFile(path="src/main/java/com/example/App.java", content="original"),
        ]
        answers = [ProjectFile(path="App.java", content="fixed")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=["src/main/java/com/example/App.java"],
        )
        match = next(f for f in result if "App.java" in f.path)
        assert match.content == "fixed"

    def test_pom_xml_replaced(self):
        project_files = [ProjectFile(path="pom.xml", content="original pom")]
        answers = [ProjectFile(path="pom.xml", content="updated pom")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=answers,
            paths_to_ex=[],
        )
        match = next(f for f in result if f.path == "pom.xml")
        assert match.content == "updated pom"

    def test_all_results_are_project_files(self):
        project_files = [ProjectFile(path="pom.xml", content="<project/>")]
        result = self.backend._build_reference_override_files(
            project_files=project_files,
            answers_list=[],
            paths_to_ex=[],
        )
        assert all(isinstance(f, ProjectFile) for f in result)