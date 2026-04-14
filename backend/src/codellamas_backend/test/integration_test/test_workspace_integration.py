import os
import pytest
import tempfile
from codellamas_backend.tools.workspace import Workspace
from codellamas_backend.schemas.files import ProjectFile


@pytest.mark.integration
class TestWorkspaceIntegration:
    """Real filesystem operations — no mocks"""

    def test_write_and_read_file(self):
        with Workspace() as ws:
            ws.write_file_map({"src/App.java": "class App {}"})
            content = ws.read("src/App.java")
            assert content == "class App {}"

    def test_write_multiple_files(self):
        with Workspace() as ws:
            ws.write_file_map({
                "src/App.java": "class App {}",
                "src/Foo.java": "class Foo {}",
                "pom.xml": "<project/>",
            })
            assert ws.read("src/App.java") == "class App {}"
            assert ws.read("src/Foo.java") == "class Foo {}"
            assert ws.read("pom.xml") == "<project/>"

    def test_nested_directories_created(self):
        with Workspace() as ws:
            ws.write_file_map({
                "src/main/java/com/example/App.java": "package com.example;\nclass App {}"
            })
            abs_path = os.path.join(ws.root, "src/main/java/com/example/App.java")
            assert os.path.exists(abs_path)

    def test_read_nonexistent_file_returns_none(self):
        with Workspace() as ws:
            result = ws.read("nonexistent.java")
            assert result is None

    def test_cleanup_removes_all_files(self):
        with Workspace() as ws:
            ws.write_file_map({"a.java": "a", "b/c.java": "c"})
            root = ws.root
        assert not os.path.exists(root)

    def test_write_project_files(self):
        files = [
            ProjectFile(path="src/App.java", content="class App {}"),
            ProjectFile(path="pom.xml", content="<project/>"),
        ]
        with Workspace() as ws:
            ws.write_files(files)
            assert ws.read("src/App.java") == "class App {}"
            assert ws.read("pom.xml") == "<project/>"

    def test_override_existing_file(self):
        with Workspace() as ws:
            ws.write_file_map({"App.java": "original"})
            ws.write_file_map({"App.java": "updated"})
            assert ws.read("App.java") == "updated"

    def test_multiple_workspaces_isolated(self):
        with Workspace() as ws1:
            with Workspace() as ws2:
                ws1.write_file_map({"file.java": "ws1 content"})
                ws2.write_file_map({"file.java": "ws2 content"})
                assert ws1.read("file.java") == "ws1 content"
                assert ws2.read("file.java") == "ws2 content"
                assert ws1.root != ws2.root

    def test_windows_path_normalized(self):
        with Workspace() as ws:
            ws.write_file_map({"src\\main\\App.java": "class App {}"})
            content = ws.read("src/main/App.java")
            assert content == "class App {}"

    def test_invalid_directory_path_raises(self):
        with Workspace() as ws:
            with pytest.raises(ValueError):
                ws.write_file_map({"src/": "content"})