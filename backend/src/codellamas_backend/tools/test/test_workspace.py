import os
import pytest

from unittest.mock import patch
from codellamas_backend.tools.workspace import Workspace
from codellamas_backend.schemas.files import ProjectFile


class TestWorkspace:
    def test_workspace_initialization(self):
        """Test workspace creates temp directory with correct prefix."""
        ws = Workspace(prefix="test_")
        assert os.path.exists(ws.root)
        assert "test_" in ws.root
        ws.cleanup()

    def test_write_files_from_project_file_objects(self):
        """Test writing ProjectFile objects to workspace."""
        ws = Workspace()
        files = [
            ProjectFile(path="src/main.py", content="print('hello')"),
            ProjectFile(path="src/utils/helper.py", content="def help(): pass"),
        ]
        ws.write_files(files)

        assert ws.read("src/main.py") == "print('hello')"
        assert ws.read("src/utils/helper.py") == "def help(): pass"
        ws.cleanup()

    def test_write_file_map(self):
        """Test writing file map to workspace."""
        ws = Workspace()
        file_map = {
            "path_file_1": "content_1",
            "path_file_2": "content_2",
        }
        ws.write_file_map(file_map)

        assert ws.read("path_file_1") == "content_1"
        assert ws.read("path_file_2") == "content_2"
        ws.cleanup()

    def test_read_nonexistent_file(self):
        """Test reading non-existent file returns None."""
        ws = Workspace()
        assert ws.read("nonexistent.txt") is None
        ws.cleanup()

    def test_path_normalization(self):
        """Test path normalization with leading slashes and backslashes."""
        ws = Workspace()
        ws.write_file_map({"/src\\file.py": "content"})

        assert ws.read("/src\\file.py") == "content"
        assert ws.read("src/file.py") == "content"
        ws.cleanup()

    def test_context_manager(self):
        """Test workspace as context manager."""
        with Workspace() as ws:
            root = ws.root
            ws.write_file_map({"test.txt": "data"})
            assert os.path.exists(root)

        assert not os.path.exists(root)

    def test_cleanup_removes_directory(self):
        """Test cleanup removes workspace directory."""
        ws = Workspace()
        root = ws.root
        ws.write_file_map({"file.txt": "content"})

        assert os.path.exists(root)
        ws.cleanup()
        assert not os.path.exists(root)

    def test_nested_directory_creation(self):
        """Test nested directories are created automatically."""
        ws = Workspace()
        ws.write_file_map({"a/b/c/d/file.txt": "deep content"})

        assert ws.read("a/b/c/d/file.txt") == "deep content"
        ws.cleanup()

    def test_file_encoding_utf8(self):
        """Test files are written and read with UTF-8 encoding."""
        ws = Workspace()
        content = "Hello 世界 🌍"
        ws.write_file_map({"unicode.txt": content})

        assert ws.read("unicode.txt") == content
        ws.cleanup()

    def test_override_existing_file(self):
        """Test overwriting existing file."""
        ws = Workspace()
        ws.write_file_map({"file.txt": "original"})
        ws.write_file_map({"file.txt": "updated"})

        assert ws.read("file.txt") == "updated"
        ws.cleanup()

    def test_write_one_file(self):
        """Test _write_one writes a file correctly."""
        ws = Workspace()
        ws._write_one("test.txt", "hello world")

        # Verify the file exists and has correct content
        assert ws.read("test.txt") == "hello world"
        ws.cleanup()

    def test_read_directory_path_raises_error(self):
        """Test reading with directory path (trailing slash) raises ValueError."""
        ws = Workspace()
        ws.write_file_map({"file.txt": "content"})

        with pytest.raises(ValueError, match="Invalid path: must be a file, not a directory"):
            ws.read("file.txt/")  # Path ends with slash - should raise

        ws.cleanup()

    def test_write_one_directory_path_raises_error(self):
        """Test _write_one with directory path (trailing slash) raises ValueError."""
        ws = Workspace()

        with pytest.raises(ValueError, match="Invalid path: must be a file, not a directory"):
            ws._write_one("file/", "malicious")

        ws.cleanup()

    def test_cleanup_removes_files_inside(self):
        ws = Workspace()
        ws.write_file_map({"foo/bar.txt": "hello"})
        root = ws.root

        ws.cleanup()

        assert not os.path.exists(root)

    def test_cleanup_is_idempotent(self):
        ws = Workspace()
        ws.cleanup()
        ws.cleanup()  # second call should not raise

    def test_with_block_calls_cleanup_on_exit(self):
        with Workspace() as ws:
            root = ws.root
            assert os.path.exists(root)

        assert not os.path.exists(root)

    def test_exit_suppresses_nothing(self):
        """__exit__ should return None (falsy), letting exceptions propagate."""
        ws = Workspace()
        result = ws.__exit__(None, None, None)
        assert result is None

    def test_exit_calls_cleanup(self):
        ws = Workspace()
        with patch.object(ws, "cleanup") as mock_cleanup:
            ws.__exit__(None, None, None)
            mock_cleanup.assert_called_once()

    def test_with_block_cleans_up_on_exception(self):
        root = None
        with pytest.raises(ValueError):
            with Workspace() as ws:
                root = ws.root
                raise ValueError("boom")

        assert root is not None
        assert not os.path.exists(root)
