import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

export async function saveToSpringBootProject(
  topic: string,
  smells: string[],
  questionCode: string, // AI-generated main class code
  //testCode: string, // AI-generated test case code
  panel: vscode.WebviewPanel
) {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!workspaceFolder) {
    vscode.window.showErrorMessage("No Spring Boot project detected!");
    return;
  }

  try {
    // Detect src/main/java and src/test/java
    const srcMainJava = path.join(workspaceFolder, "src", "main", "java");
    const srcTestJava = path.join(workspaceFolder, "src", "test", "java");
    const mainClass = findSpringBootMainClass(srcMainJava);
    if (!mainClass) {
      vscode.window.showErrorMessage("Could not find Spring Boot main class.");
      return;
    }

    const packageName = extractPackageName(mainClass);
    if (!packageName) {
      vscode.window.showErrorMessage("Could not extract package name.");
      return;
    }

    const packagePath = path.join(srcMainJava, ...packageName.split("."));
    const testPackagePath = path.join(srcTestJava, ...packageName.split("."));
    
    // Create directories for main class and test case
    fs.mkdirSync(packagePath, { recursive: true });
    fs.mkdirSync(testPackagePath, { recursive: true });

    // Extract public class name from AI-generated question code
    const className = extractPublicClassName(questionCode);
    const javaFilePath = path.join(packagePath, `${className}.java`);
    const testFilePath = path.join(testPackagePath, `${className}Test.java`);

    // Wrap AI code in package declaration for main class
    const javaContent = `package ${packageName};

${questionCode}
    `.trim();

    // Wrap AI code in package declaration for the test case
  //   const testContent = `package com.example.${packageName};

  //   ${testCode}
  //   `.trim();

    // Write both main class and test case files
    fs.writeFileSync(javaFilePath, javaContent, "utf8");
  //   fs.writeFileSync(testFilePath, testContent, "utf8");

    vscode.window.showInformationMessage(`Java files created at ${javaFilePath} and ${testFilePath}`);

    panel.webview.postMessage({
      type: "response",
      data: { topic, smells, question: `Saved to ${javaFilePath} and ${testFilePath}` },
    });
  } catch (err) {
    console.error(err);
    vscode.window.showErrorMessage("Failed to save Java files to Spring Boot project");
  }
}

// --- Helpers ---
function findSpringBootMainClass(dir: string): string | null {
  const files = fs.readdirSync(dir, { withFileTypes: true });
  for (const file of files) {
    const fullPath = path.join(dir, file.name);
    if (file.isDirectory()) {
      const found = findSpringBootMainClass(fullPath);
      if (found) return found;
    } else if (file.isFile() && file.name.endsWith(".java")) {
      const content = fs.readFileSync(fullPath, "utf8");
      if (content.includes("@SpringBootApplication")) return fullPath;
    }
  }
  return null;
}

function extractPackageName(filePath: string): string | null {
  const content = fs.readFileSync(filePath, "utf8");
  const match = content.match(/package\s+([a-zA-Z0-9_.]+);/);
  return match ? match[1] : null;
}

// --- Extract public class name from AI code ---
function extractPublicClassName(javaCode: string): string {
  const match = javaCode.match(/public\s+class\s+([A-Za-z0-9_]+)/);
  if (match && match[1]) {
    return match[1];
  }
  // fallback if AI didn’t include a public class
  return `GeneratedQuestion${Date.now()}`;
}
