import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { ActivityWebviewProvider } from "./activityWebviewProvider";

interface ReviewPayload {
  problem_description: string;
  original_code: string;
  student_code: string;
  reference_solution: string;
  test_results: string;
  code_smells: string[];
}

export async function buildReviewPayload(
  provider: ActivityWebviewProvider
): Promise<ReviewPayload | null> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders || workspaceFolders.length === 0) {
    vscode.window.showErrorMessage("No workspace folder open!");
    return null;
  }
  const workspaceRoot = workspaceFolders[0].uri.fsPath;

  // ----------------------------
  // Helper: extract Java code from markdown or array
  // ----------------------------
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

  // ----------------------------
  // 1. Problem description (PROBLEM.md)
  // ----------------------------
  let problemDescription = "";
  const problemMdPath = path.join(workspaceRoot, "PROBLEM.md");
  if (fs.existsSync(problemMdPath)) {
    problemDescription = fs.readFileSync(problemMdPath, "utf8");
  } else {
    vscode.window.showWarningMessage("PROBLEM.md not found in workspace root. Using empty description.");
  }

  // ----------------------------
  // 2. Current editor / student code
  // ----------------------------
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage("No active editor found!");
    return null;
  }
  const studentFilePath = editor.document.fileName;
  const relPath = path.relative(workspaceRoot, studentFilePath);
  const studentCode = editor.document.getText();

  // ----------------------------
  // 3. Original starter code
  // ----------------------------
  const starterFilePath = path.join(workspaceRoot, "starter", relPath);
  let originalCode = "";
  if (fs.existsSync(starterFilePath)) {
    originalCode = fs.readFileSync(starterFilePath, "utf8");
  } else {
    vscode.window.showWarningMessage(`Starter file not found for ${relPath}. Using empty string.`);
  }

  // ----------------------------
  // 4. Reference solution (Java code)
  // ----------------------------
  const ref = provider.getReferenceSolution();
  const referenceSolution = extractJavaCode(ref); // will be empty string if missing

  // ----------------------------
  // 5. Other required fields
  // ----------------------------
  const testResults = "BUILD SUCCESS"; // default placeholder
  const codeSmells: string[] = [];     // empty array by default

  // ----------------------------
  // 6. Build payload
  // ----------------------------
  return {
    problem_description: problemDescription,
    original_code: originalCode,
    student_code: studentCode,
    reference_solution: referenceSolution,
    test_results: testResults,
    code_smells: codeSmells,
  };
}
