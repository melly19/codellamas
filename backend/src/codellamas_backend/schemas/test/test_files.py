import pytest
from pydantic import ValidationError
from codellamas_backend.schemas.files import ProjectFile


def test_project_file_valid():
    file_data = {
        "path": "src/main/java/com/example/App.java",
        "content": "public class App {}"
    }
    project_file = ProjectFile(**file_data)
    assert project_file.path == file_data["path"]
    assert project_file.content == file_data["content"]

def test_project_file_missing_path():
    file_data = {
        "content": "public class App {}"
    }
    with pytest.raises(ValidationError):
        ProjectFile(**file_data)
    
def test_project_file_missing_content():
    file_data = {
        "path": "src/main/java/com/example/App.java"
    }
    with pytest.raises(ValidationError):
        ProjectFile(**file_data)
    
# def test_project_file_empty_path():
#     file_data = {
#         "path": "",
#         "content": "public class App {}"
#     }
#     with pytest.raises(ValidationError):
#         ProjectFile(**file_data)
    
# def test_project_file_empty_content():
#     file_data = {
#         "path": "src/main/java/com/example/App.java",
#         "content": ""
#     }
#     with pytest.raises(ValidationError):
#         ProjectFile(**file_data)

def test_project_file_invalid_path_type():
    file_data = {
        "path": 123,
        "content": "public class App {}"
    }
    with pytest.raises(ValidationError):
        ProjectFile(**file_data)
    
def test_project_file_invalid_content_type():
    file_data = {
        "path": "src/main/java/com/example/App.java",
        "content": 123
    }
    with pytest.raises(ValidationError):
        ProjectFile(**file_data)