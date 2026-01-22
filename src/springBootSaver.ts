// springBootSaver.ts
import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

export async function saveToSpringBootProject(
  topic: string,
  smells: string[],
  questions: string, // AI-generated Java code
  panel: vscode.WebviewPanel
) {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!workspaceFolder) {
    vscode.window.showErrorMessage("No Spring Boot project detected!");
    return;
  }

  try {
    // Detect src/main/java
    const srcMainJava = path.join(workspaceFolder, "src", "main", "java");
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
    fs.mkdirSync(packagePath, { recursive: true });

    // Extract public class name from AI-generated code
    const className = extractPublicClassName(questions);
    const javaFilePath = path.join(packagePath, `${className}.java`);

    // Wrap AI code in package declaration
    const javaContent = `
package ${packageName};

${questions}
    `.trim();

    fs.writeFileSync(javaFilePath, javaContent, "utf8");

    vscode.window.showInformationMessage(`Java file created at ${javaFilePath}`);

    panel.webview.postMessage({
      type: "response",
      data: { topic, smells, question: `Saved to ${javaFilePath}` },
    });
  } catch (err) {
    console.error(err);
    vscode.window.showErrorMessage("Failed to save Java file to Spring Boot project");
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
