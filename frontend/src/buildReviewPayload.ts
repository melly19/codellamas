import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { ActivityWebviewProvider } from "./activityWebviewProvider";

interface ProjectFile {
  path: string;
  content: string;
}

interface ReviewPayload {
  question_json: Record<string, any>;
  student_code: ProjectFile[];
  mode?: string;
  query?: string;
  test_results?: string;
  verify_maven?: boolean;
  code_smells: string[];
}

export async function buildReviewPayload(
  provider: ActivityWebviewProvider,
  codeSmells: string[] = [],
  pathsToEx: string[] = []
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
  const studentCode: ProjectFile[] = [];
  const originalCode: ProjectFile[] = [];

  if (!pathsToEx || pathsToEx.length === 0) {
    vscode.window.showWarningMessage("No paths_to_ex provided. Nothing to review.");
    return null;
  }

  for (const relPath of pathsToEx) {
    const studentFullPath = path.join(workspaceRoot, relPath);

    if (fs.existsSync(studentFullPath)) {
      const content = fs.readFileSync(studentFullPath, "utf8");
      studentCode.push({
        path: relPath,
        content,
      });
    } else {
      vscode.window.showWarningMessage(`Student file missing: ${relPath}`);
    }

    const starterFullPath = path.join(workspaceRoot, "starter", relPath);
    if (fs.existsSync(starterFullPath)) {
      const originalContent = fs.readFileSync(starterFullPath, "utf8");
      originalCode.push({
        path: relPath,
        content: originalContent,
      });
    } else {
      vscode.window.showWarningMessage(`Starter file missing: ${relPath}`);
    }
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

  const questionObj: any = {
    problem_description: problemDescription,
    original_code: originalCode,
    answers_list: solutionExp,
    code_smells: codeSmells,
  };

  const payload: ReviewPayload = {
    question_json: questionObj,
    student_code: studentCode,
    mode: "single",
    query: "",
    test_results: testResults,
    verify_maven: false,
    code_smells: codeSmells,
  };

  return payload;
}
