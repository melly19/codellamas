from pydantic import BaseModel, Field
from typing import Dict
import subprocess
import tempfile
import os
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel
import json


class TestRunnerInput(BaseModel):
    """Input schema for running a Java JUnit 5 test suite."""
    
    source_files: Dict[str, str] = Field(
        ...,
        description="Mapping of Java source file paths to file contents."
    )
    test_files: Dict[str, str] = Field(
        ...,
        description="Mapping of JUnit 5 test file paths to file contents."
    )
    build_tool: str = Field(
        default="maven",
        description="Build tool to use: 'maven' or 'gradle'."
    )

class JavaTestRunnerTool(BaseTool):
    name: str = "java_junit_test_runner"
    description: str = (
        "Compiles Java source code and executes JUnit 5 tests. "
        "Returns compilation errors or test results for functional validation."
    )
    args_schema: Type[BaseModel] = TestRunnerInput

    def _run(
        self,
        source_files: dict,
        test_files: dict,
        build_tool: str = "maven"
    ) -> str:

        with tempfile.TemporaryDirectory() as project_dir:
            self._write_project_files(project_dir, source_files, test_files)
            result = self._run_tests(project_dir, build_tool)
            return json.dumps(result, indent=2)

    def _write_project_files(self, project_dir, source_files, test_files):
        for path, content in {**source_files, **test_files}.items():
            full_path = os.path.join(project_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        # Minimal Maven setup
        pom_path = os.path.join(project_dir, "pom.xml")
        if not os.path.exists(pom_path):
            with open(pom_path, "w") as f:
                f.write(self._default_pom())

    def _run_tests(self, project_dir, build_tool):
        try:
            process = subprocess.run(
                ["mvn", "test"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out"
            }

    def _default_pom(self):
        return """\
            <project xmlns="http://maven.apache.org/POM/4.0.0">
            <modelVersion>4.0.0</modelVersion>
            <groupId>edu.exercise</groupId>
            <artifactId>refactoring-exercise</artifactId>
            <version>1.0-SNAPSHOT</version>
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
            </project>
        """