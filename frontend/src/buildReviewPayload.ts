import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { ActivityWebviewProvider } from "./activityWebviewProvider";

interface ReviewPayload {
  problem_description: string;
  original_code: string;
  student_code: string;
  answers_list: string;
  test_results: string;
  code_smells: string[];
}

export async function buildReviewPayload(
  provider: ActivityWebviewProvider,
  codeSmells: string[] = []
): Promise<ReviewPayload | null> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders || workspaceFolders.length === 0) {
    vscode.window.showErrorMessage("No workspace folder open!");
    return null;
  }
  const workspaceRoot = workspaceFolders[0].uri.fsPath;

  function extractJavaCode(markdown: string | { path: string; content: string }[] | null): string {
    if (!markdown) return "";

    let code = "";

    if (typeof markdown === "string") {
      const codeBlockRegex = /```java\s*([\s\S]*?)```/g;
      let match;
      while ((match = codeBlockRegex.exec(markdown)) !== null) {
        code += match[1].trim() + "\n\n";
      }
    } else if (Array.isArray(markdown)) {
      for (const file of markdown) {
        if (file.content) {
          code += file.content + "\n\n";
        }
      }
    }

    return code.trim();
  }

  let problemDescription = "";
  const problemMdPath = path.join(workspaceRoot, "PROBLEM.md");
  if (fs.existsSync(problemMdPath)) {
    problemDescription = fs.readFileSync(problemMdPath, "utf8");
  } else {
    vscode.window.showWarningMessage("PROBLEM.md not found in workspace root. Using empty description.");
  }

  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage("No active editor found!");
    return null;
  }
  const studentFilePath = editor.document.fileName;
  const relPath = path.relative(workspaceRoot, studentFilePath);
  const studentCode = editor.document.getText();

  const starterFilePath = path.join(workspaceRoot, "starter", relPath);
  let originalCode = "";
  if (fs.existsSync(starterFilePath)) {
    originalCode = fs.readFileSync(starterFilePath, "utf8");
  } else {
    vscode.window.showWarningMessage(`Starter file not found for ${relPath}. Using empty string.`);
  }

  const ref = provider.getSolutionExp();
  const solutionExp = extractJavaCode(ref); 

  const testResults = "BUILD SUCCESS"; 

 // DEBUGGING OUTPUT
  console.log("=== Review Payload Inputs ===");
  console.log("Problem Description:", problemDescription);
  console.log("Original Code:", originalCode);
  console.log("Student Code:", studentCode);
  console.log("Reference Solution:", solutionExp);
  console.log("Test Results:", testResults);
  console.log("Code Smells:", codeSmells);

  return {
    problem_description: problemDescription,
    original_code: originalCode,
    student_code: studentCode,
    answers_list: solutionExp,
    test_results: testResults,
    code_smells: codeSmells,
  };
}
