import * as vscode from "vscode";
import { saveToSpringBootProject } from "./springBootSaver";

export class ActivityWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "codellamas_activityView";

  private generatorPanel: vscode.WebviewPanel | undefined;

  constructor(private readonly context: vscode.ExtensionContext) {}

  /* =========================
     ACTIVITY BAR VIEW
     ========================= */

  resolveWebviewView(webviewView: vscode.WebviewView) {
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.getActivityHtml();

    webviewView.webview.onDidReceiveMessage((message) => {
      if (message.type === "openGenerator") {
        this.openQuestionGenerator();
      }
    });
  }

  private getActivityHtml(): string {
    return /* html */ `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>CodeLlamas</title>
  <style>
    body {
      font-family: var(--vscode-font-family);
      padding: 12px;
    }

    button {
      background-color: #8ecbff;
      border: none;
      padding: 10px 14px;
      border-radius: 6px;
      font-weight: bold;
      cursor: pointer;
    }

    button:hover {
      background-color: #6bbcff;
    }
  </style>
</head>
<body>
  <h3>🦙 CodeLlamas</h3>
  <button onclick="openGenerator()">Generate Page</button>

  <script>
    const vscode = acquireVsCodeApi();
    function openGenerator() {
      vscode.postMessage({ type: "openGenerator" });
    }
  </script>
</body>
</html>
    `;
  }

  /* =========================
     GENERATOR PANEL
     ========================= */

  private openQuestionGenerator() {
    if (this.generatorPanel) {
      this.generatorPanel.reveal(vscode.ViewColumn.One);
      return;
    }

    this.generatorPanel = vscode.window.createWebviewPanel(
      "codellamasGenerator",
      "Refactoring Studio",
      vscode.ViewColumn.One,
      { enableScripts: true }
    );

    this.generatorPanel.iconPath = vscode.Uri.file(
      this.context.asAbsolutePath("media/code-llamas.png")
    );

    this.generatorPanel.webview.html =
      this.getGeneratorHtml(this.generatorPanel.webview);

    this.generatorPanel.webview.onDidReceiveMessage(async (msg) => {
      if (msg.type === "submit") {
        try {
          const aiQuestions = await this.fetchAiQuestionsFromBackend(
            msg.topic,
            msg.smells
          );

          await saveToSpringBootProject(
            msg.topic,
            msg.smells,
            aiQuestions,
            this.generatorPanel!
          );
        } catch (error) {
          vscode.window.showErrorMessage(
            "Error generating questions: " + String(error)
          );
        }
      }
    });

    this.generatorPanel.onDidDispose(() => {
      this.generatorPanel = undefined;
    });
  }

  /* =========================
     BACKEND CALL
     ========================= */

  private async fetchAiQuestionsFromBackend(
    topic: string,
    smells: string[]
  ): Promise<string> {
    const response = await fetch("http://localhost:8000/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, smells })
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }

    const data = (await response.json()) as { questions: string };
    return data.questions;
  }

  /* =========================
     GENERATOR HTML
     ========================= */

  private getGeneratorHtml(webview: vscode.Webview): string {
    return /* html */ `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Refactoring Studio</title>

  <style>
    body {
      font-family: 'Times New Roman', Times, serif;
      padding: 24px 32px;
      background-color: #f0f0f0;
      color: #1e1e1e;
    }

    h1 {
      text-align: center;
      margin-bottom: 16px;
    }

    /* Attention box */
    .attention-box {
      background-color: #ffffff;
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 24px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }

    .attention-box h2 {
      color: #d32f2f;
      margin: 0 0 6px 0;
    }

    .attention-box a {
      color: #007acc;
      text-decoration: none;
    }

    .attention-box a:hover {
      text-decoration: underline;
    }

    /* Section */
    .section-title {
      font-size: 1.2rem;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .section-subtitle {
      font-size: 0.9rem;
      color: #6a6a6a;
      margin-bottom: 16px;
    }

    /* Tree view */
    details {
      margin-bottom: 10px;
    }

    summary {
      cursor: pointer;
      font-weight: 500;
      list-style: none;
    }

    summary::-webkit-details-marker {
      display: none;
    }

    summary::before {
      content: "▶";
      display: inline-block;
      margin-right: 6px;
      font-size: 0.7rem;
      transition: transform 0.15s ease;
    }

    details[open] summary::before {
      transform: rotate(90deg);
    }

    .smell-options {
      margin-left: 18px;
      margin-top: 6px;
    }

    .smell-option {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 0;
      font-size: 0.9rem;
    }

    input[type="checkbox"] {
      accent-color: #007acc;
      width: 14px;
      height: 14px;
    }

    /* Topic */
    .topic {
      margin-top: 28px;
    }

    .topic label {
      display: block;
      font-size: 0.85rem;
      margin-bottom: 6px;
      color: #444;
    }

    input[type="text"] {
      width: 100%;
      max-width: 420px;
      padding: 8px 10px;
      border: 1px solid #cfcfcf;
      border-radius: 4px;
    }

    /* Submit */
    .submit-container {
      margin-top: 32px;
      text-align: right;
    }

    button {
      background-color: #ffffff;
      border: 1px solid #cfcfcf;
      padding: 8px 14px;
      border-radius: 6px;
      cursor: pointer;
    }

    button:hover {
      background-color: #f5f5f5;
    }

    /* Tree container */
.tree-group {
  margin: 16px 0;
}

/* Summary row */
.tree-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  list-style: none;
}

/* Parent label */
.tree-summary .label {
  font-weight: 500;
}

/* Children container */
.tree-children {
  margin-left: 26px;
  margin-top: 11px;
  display: flex;
  gap: 6px;
}

/* Checkbox rows */
.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
  white-space: nowrap;
}

/* Checkbox alignment fix */
.checkbox-row input,
.tree-summary input {
  margin: 0;
}

.language-section {
  margin-top: 72px;   /* try 24–40px */
}


</style>
</head>

<body>

  <h1>Generating Code Smell Activity</h1>

  <div class="attention-box">
    <h2>Attention!</h2>
    <p>
      You must have a Spring Boot project open.
      Visit
      <a href="https://start.spring.io/" target="_blank">
        https://start.spring.io/
      </a>
      to create one.
    </p>
  </div>

  <div class="section-title">Select Code Smells</div>
  <div class="section-subtitle">
    Choose one or more refactoring topics to practise
  </div>

  <details open>
    <summary>Bloaters</summary>
    <div class="smell-options">
      <label class="smell-option">
        <input type="checkbox" value="Long Method" /> Long Method
      </label>
      <label class="smell-option">
        <input type="checkbox" value="Large Class" /> Large Class
      </label>
      <label class="smell-option">
        <input type="checkbox" value="Primitive Obsession" /> Primitive Obsession
      </label>
    </div>
  </details>

  
  <details>
    <summary>Dispensables</summary>
    <div class="smell-options">
      <label class="smell-option">
        <input type="checkbox" value="Long Method" /> Duplicate Code
      </label>
      <label class="smell-option">
        <input type="checkbox" value="Large Class" /> Dead Code 
      </label>
    </div>
  </details>

  <details>
    <summary>Couplers</summary>
    <div class="smell-options">
      <label class="smell-option">
        <input type="checkbox" value="Long Method" /> Feature Envy 
      </label>
      <label class="smell-option">
        <input type="checkbox" value="Large Class" /> Message Chains
      </label>
    </div>
  </details>
  
  <div class="topic">
    <label for="topic">Topic / Language</label>
    <input id="topic" type="text" placeholder="e.g. Banking, E-Commerce" />
  </div>

  <div class="submit-container">
    <button onclick="submit()">Generate Question</button>
  </div>

  <div class="output">
  <h2 class="output-title">📘 Generated Refactoring Questions</h2>

  <ul id="questionList" class="question-list">
    <li class="placeholder">No questions generated yet.</li>
  </ul>
</div>


  <script>
    const vscode = acquireVsCodeApi();

    function submit() {
      const smells = Array.from(
        document.querySelectorAll('input[type="checkbox"]:checked')
      ).map(cb => cb.value);

      vscode.postMessage({
        type: "submit",
        topic: document.getElementById("topic").value,
        smells
      });
    }
  </script>

</body>
</html>
    `;
  }
}
