import pytest
from codellamas_backend.tools.maven_tool import MavenTool, MavenTestResult
from codellamas_backend.schemas.files import ProjectFile


SIMPLE_POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>test-project</artifactId>
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

PASSING_TEST = """package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test
    void testPass() {
        assertEquals(2, 1 + 1);
    }
}"""

FAILING_TEST = """package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test
    void testFail() {
        assertEquals(3, 1 + 1);
    }
}"""

COMPILATION_ERROR = """package com.example;
public class App {
    this is not valid java code
}"""


@pytest.mark.integration
class TestMavenToolIntegration:
    """Real mvn test runs — requires Maven installed"""

    def setup_method(self):
        self.tool = MavenTool(timeout_sec=120)
        self.base_files = [
            ProjectFile(path="pom.xml", content=SIMPLE_POM),
        ]

    def test_passing_tests_return_pass_status(self):
        result = self.tool.run_tests(
            project_files=self.base_files,
            inject_tests={
                "src/test/java/com/example/AppTest.java": PASSING_TEST
            }
        )
        assert result.status == "PASS"
        assert result.returncode == 0
        assert result.failed_tests == []

    def test_failing_tests_return_fail_status(self):
        result = self.tool.run_tests(
            project_files=self.base_files,
            inject_tests={
                "src/test/java/com/example/AppTest.java": FAILING_TEST
            }
        )
        assert result.status == "FAIL"
        assert result.returncode != 0

    def test_compilation_error_returns_fail(self):
        result = self.tool.run_tests(
            project_files=self.base_files + [
                ProjectFile(
                    path="src/main/java/com/example/App.java",
                    content=COMPILATION_ERROR
                )
            ],
            inject_tests={
                "src/test/java/com/example/AppTest.java": PASSING_TEST
            }
        )
        assert result.status == "FAIL"
        assert any("compilation" in e.lower() for e in result.errors)

    def test_raw_log_contains_maven_output(self):
        result = self.tool.run_tests(
            project_files=self.base_files,
            inject_tests={
                "src/test/java/com/example/AppTest.java": PASSING_TEST
            }
        )
        assert len(result.raw_log) > 0

    def test_override_files_applied(self):
        original = ProjectFile(
            path="src/main/java/com/example/App.java",
            content="package com.example;\npublic class App { public int value() { return 1; } }"
        )
        override = ProjectFile(
            path="src/main/java/com/example/App.java",
            content="package com.example;\npublic class App { public int value() { return 2; } }"
        )
        test_file = """package com.example;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class AppTest {
    @Test void test() { assertEquals(2, new App().value()); }
}"""
        result = self.tool.run_tests(
            project_files=self.base_files + [original],
            override_files=[override],
            inject_tests={"src/test/java/com/example/AppTest.java": test_file}
        )
        assert result.status == "PASS"

    def test_timeout_returns_fail(self):
        tool = MavenTool(timeout_sec=1)
        result = tool.run_tests(
            project_files=self.base_files,
            inject_tests={
                "src/test/java/com/example/AppTest.java": PASSING_TEST
            }
        )
        assert result.status == "FAIL"
        assert result.returncode == 124