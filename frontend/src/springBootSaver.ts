import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

interface ProjectFile {
  path: string;
  content: string;
}

interface ResponseData {
  status: string;
  message: string;
  data: {
    problem_description: string;
    project_files: ProjectFile[];
    test_files?: ProjectFile[];
  };
}

export async function saveToSpringBootProject(
  responseData: ResponseData,
  webviewHost: vscode.WebviewPanel | vscode.WebviewView
) {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders || workspaceFolders.length === 0) {
    vscode.window.showErrorMessage("No workspace folder open!");
    return;
  }

  const workspaceRoot = workspaceFolders[0].uri.fsPath;
  
  try {
    const { data } = responseData;
    const { project_files, test_files, problem_description } = data;

    if (!project_files || project_files.length === 0) {
      vscode.window.showErrorMessage("No project files to create!");
      return;
    }

    const createdFiles: string[] = [];

    const writeFiles = (files: ProjectFile[]) => {
      for (const file of files) {
        const fullPath = path.join(workspaceRoot, file.path);
        const directory = path.dirname(fullPath);

        // Create directory structure if it doesn't exist
        if (!fs.existsSync(directory)) {
          fs.mkdirSync(directory, { recursive: true });
        }

        // Write the file content
        fs.writeFileSync(fullPath, file.content, "utf8");
        createdFiles.push(file.path);
      }
    };

    // Create each file from the project_files array
    writeFiles(project_files);

    // Create each file from the test_files array (same format as project_files)
    if (test_files && test_files.length > 0) {
      writeFiles(test_files);
    }

    vscode.window.showInformationMessage(
      `Successfully created ${createdFiles.length} files in workspace!`
    );

    // Open the problem description if available
    if (problem_description) {
      const problemMdPath = path.join(workspaceRoot, "PROBLEM.md");
      fs.writeFileSync(problemMdPath, problem_description, "utf8");
      createdFiles.push("PROBLEM.md");
      
      // Open PROBLEM.md in editor
      const doc = await vscode.workspace.openTextDocument(problemMdPath);
      await vscode.window.showTextDocument(doc);
    }

    webviewHost.webview.postMessage({
      type: "response",
      data: { 
        message: `Created ${createdFiles.length} files`,
        files: createdFiles 
      }
    });

  } catch (err) {
    console.error(err);
    vscode.window.showErrorMessage(
      "Failed to create project files: " + String(err)
    );
  }
}
