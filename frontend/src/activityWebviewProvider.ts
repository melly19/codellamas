import * as vscode from "vscode";
import { saveToSpringBootProject } from "./springBootSaver";

export class ActivityWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "codellamas_activityView";

  private referenceSolution: any[] | string | null = null;

  constructor(private readonly context: vscode.ExtensionContext) { }

  /* =========================
     ACTIVITY BAR VIEW
     ========================= */

  resolveWebviewView(webviewView: vscode.WebviewView) {
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.getActivityHtml();

    webviewView.webview.onDidReceiveMessage(async (message) => {
      if (message.type === "submit") {
        try {
          const responseData = await this.fetchAiQuestionsFromBackend(
            message.topic,
            message.smells
          );
          await saveToSpringBootProject(responseData, webviewView);
          this.referenceSolution = responseData.data.reference_solution_markdown ?? null;
        } catch (error) {
          vscode.window.showErrorMessage(
            "Error generating questions: " + String(error)
          );
        } finally {
          webviewView.webview.postMessage({
            type: "generateComplete"
          });
        }
      } else if (message.type === "review") {
        try {
          const reviewResult = await this.fetchReviewFromBackend(
            message.payload
          );

          webviewView.webview.postMessage({
            type: "reviewResponse",
            ...reviewResult
          });
        } catch (error) {
          const errorMessage = "Error running review: " + String(error);
          vscode.window.showErrorMessage(errorMessage);
          webviewView.webview.postMessage({
            type: "reviewError",
            error: errorMessage
          });
        }
      }
      else if (message.type === "showAnswerFile") {
        if (!this.referenceSolution) {
          vscode.window.showErrorMessage("No reference solution available");
          return;
        }
        try {
          if (typeof this.referenceSolution === "string") {
            await this.showReferenceSolutionAsCode(this.referenceSolution);
          } else if (Array.isArray(this.referenceSolution)) {
            for (const file of this.referenceSolution) {
              await this.showReferenceSolutionAsCode(
                file.content,
                file.path.replace(/\//g, "_")
              );
            }
          } else {
            vscode.window.showErrorMessage(
              "Reference solution format is invalid"
            );
          }
        } catch (err: any) {
          vscode.window.showErrorMessage(
            "Failed to show reference solution: " + String(err)
          );
        }
      }

    });
  }

  private async showReferenceSolutionAsCode(
    markdown: string,
    filename = "ReferenceSolution.java"
  ) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
      vscode.window.showErrorMessage("No workspace folder open!");
      return;
    }
    const workspaceRoot = workspaceFolders[0].uri.fsPath;

    const codeBlockRegex = /```java\s*([\s\S]*?)```/g;
    let match;
    let codeContent = "";

    while ((match = codeBlockRegex.exec(markdown)) !== null) {
      codeContent += match[1].trim() + "\n\n";
    }

    if (!codeContent.trim()) {
      vscode.window.showErrorMessage("No Java code found in reference solution.");
      return;
    }
    const path = require("path");
    const fs = require("fs");
    const outputDir = path.join(workspaceRoot, "reference_solution");
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

    const outputPath = path.join(outputDir, filename);
    fs.writeFileSync(outputPath, codeContent, "utf8");

    const doc = await vscode.workspace.openTextDocument(outputPath);
    await vscode.window.showTextDocument(doc);

    vscode.window.showInformationMessage("Reference solution opened as code!");
  }

  private getActivityHtml(): string {
    return /* html */ `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Codellamas</title>
  <style>
    body {
      font-family: var(--vscode-font-family);
      padding: 16px 20px;
      background-color: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
      height: 100vh;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
    }

    h1 {
      margin: 0 0 12px 0;
      font-size: 1.2rem;
    }

    .header {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 12px;
    }

    .brand {
      font-weight: 600;
    }

    .subtitle {
      font-size: 0.85rem;
      color: var(--vscode-descriptionForeground);
    }

    .tabs {
      display: flex;
      gap: 4px;
      margin: 12px 0 16px 0;
      border-bottom: 1px solid var(--vscode-editorGroup-border);
    }

    .tab {
      padding: 4px 10px;
      border-radius: 4px 4px 0 0;
      border: 1px solid transparent;
      border-bottom: none;
      cursor: pointer;
      font-size: 0.85rem;
      background-color: transparent;
      color: var(--vscode-foreground);
    }

    .tab.active {
      border-color: var(--vscode-editorGroup-border);
      background-color: var(--vscode-editor-background);
      font-weight: 600;
    }

    .panel {
      display: none;
    }

    .panel.active {
      display: block;
    }

    /* Review panel layout */
    #panel-review.panel.active {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .section-title {
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 4px;
    }

    .section-subtitle {
      font-size: 0.85rem;
      color: var(--vscode-descriptionForeground);
      margin-bottom: 12px;
    }

    details {
      margin-bottom: 8px;
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
      padding: 2px 0;
      font-size: 0.9rem;
    }

    input[type="checkbox"] {
      accent-color: var(--vscode-checkbox-border, #007acc);
      width: 14px;
      height: 14px;
    }

    .topic {
      margin-top: 16px;
    }

    .topic label {
      display: block;
      font-size: 0.85rem;
      margin-bottom: 4px;
      color: var(--vscode-foreground);
    }

    input[type="text"] {
      width: 100%;
      padding: 6px 8px;
      border: 1px solid var(--vscode-input-border);
      border-radius: 4px;
      background-color: var(--vscode-input-background);
      color: var(--vscode-input-foreground);
      box-sizing: border-box;
    }

    .submit-container {
      margin-top: 20px;
      text-align: right;
    }

    button {
      background-color: var(--vscode-button-secondaryBackground);
      color: var(--vscode-button-secondaryForeground);
      border: 1px solid var(--vscode-button-border, transparent);
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.85rem;
    }

    button:hover {
      background-color: var(--vscode-button-secondaryHoverBackground);
    }

    button:disabled {
      opacity: 0.7;
      cursor: not-allowed;
    }

    .spinner {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid var(--vscode-input-border);
      border-top-color: var(--vscode-progressBar-background);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-right: 6px;
      vertical-align: middle;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .panel-placeholder {
      font-size: 0.9rem;
      color: var(--vscode-descriptionForeground);
      margin-top: 4px;
    }

    .chat-container {
      flex: 1;
      min-height: 0;
      margin-top: 8px;
      border: 1px solid var(--vscode-editorGroup-border);
      border-radius: 4px;
      background-color: var(--vscode-editor-background);
      display: flex;
      flex-direction: column;
    }

    .chat-messages {
      flex: 1;
      padding: 8px 10px;
      overflow-y: auto;
      box-sizing: border-box;
      font-size: 0.9rem;
    }

    .chat-message {
      margin-bottom: 8px;
      line-height: 1.4;
      white-space: pre-wrap;
      word-wrap: break-word;
    }

    .chat-message-ai {
      background-color: var(--vscode-editor-inactiveSelectionBackground);
      border-radius: 4px;
      padding: 6px 8px;
    }

    .chat-placeholder {
      color: var(--vscode-descriptionForeground);
      font-style: italic;
    }

    .review-footer {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--vscode-editorGroup-border);
      text-align: right;
    }
  </style>
</head>
<body>
  <div class="tabs">
    <button class="tab active" data-panel="generate">Generate</button>
    <button class="tab" data-panel="review">Review</button>
    <button class="tab" data-panel="answer">Answer</button>
  </div>

  <div id="panel-generate" class="panel active">
    <h1>Generating Code Smell Activity</h1>

    <div class="section-title">Select Code Smells</div>
    <div class="section-subtitle">
      Choose one or more refactoring topics to practise.
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
          <input type="checkbox" value="Duplicate Code" /> Duplicate Code
        </label>
        <label class="smell-option">
          <input type="checkbox" value="Dead Code" /> Dead Code
        </label>
      </div>
    </details>

    <details>
      <summary>Couplers</summary>
      <div class="smell-options">
        <label class="smell-option">
          <input type="checkbox" value="Feature Envy" /> Feature Envy
        </label>
        <label class="smell-option">
          <input type="checkbox" value="Message Chains" /> Message Chains
        </label>
      </div>
    </details>

    <div class="topic">
      <label for="topic">Topic</label>
      <input id="topic" type="text" placeholder="e.g. Banking, E-Commerce" />
    </div>

    <div class="submit-container">
      <button id="generateBtn" type="button">Generate Question</button>
    </div>
  </div>

  <div id="panel-review" class="panel">
    <div class="section-title">Review</div>
    <div class="chat-container">
      <div id="chat-messages" class="chat-messages">
        <div class="chat-placeholder">
          Run a review to see feedback from your backend AI.
        </div>
      </div>
    </div>
    <div class="review-footer">
      <button id="reviewBtn" type="button">Review</button>
    </div>
  </div>

  <div id="panel-answer" class="panel">
    <div class="section-title">Model Answer</div>
    <div class="panel-placeholder">
      Show the solution file for this activity.
    </div>
    <div class="review-footer">
      <button id="showAnswerBtn" type="button">
        Show Answer File
      </button>
    </div>
  </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();

    const tabs = Array.from(document.querySelectorAll('.tab'));
    const panels = {
      generate: document.getElementById('panel-generate'),
      review: document.getElementById('panel-review'),
      answer: document.getElementById('panel-answer'),
    };

    function showPanel(name) {
      tabs.forEach(tab => {
        const isActive = tab.dataset.panel === name;
        tab.classList.toggle('active', isActive);
      });

      Object.entries(panels).forEach(([key, el]) => {
        el.classList.toggle('active', key === name);
      });
    }

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const panelName = tab.dataset.panel;
        if (panelName) {
          showPanel(panelName);
        }
      });
    });

    const generateBtn = document.getElementById("generateBtn");
    const reviewBtn = document.getElementById("reviewBtn");
    const chatMessages = document.getElementById("chat-messages");
    const showAnswerBtn = document.getElementById("showAnswerBtn");
    if (showAnswerBtn){
      showAnswerBtn.addEventListener("click",() => {
        vscode.postMessage({
          type:"showAnswerFile"
          });
        });
    }

    function setGenerating(isGenerating) {
      generateBtn.disabled = isGenerating;
      generateBtn.innerHTML = isGenerating
        ? '<span class="spinner"></span> Generating...'
        : "Generate Question";
    }

    function setReviewing(isReviewing) {
      if (!reviewBtn) return;
      reviewBtn.disabled = isReviewing;
      reviewBtn.textContent = isReviewing ? "Reviewing..." : "Review";
    }

    function appendChatMessage(text, role) {
      if (!chatMessages) return;

      // Remove placeholder on first real message
      const placeholder = chatMessages.querySelector(".chat-placeholder");
      if (placeholder) {
        placeholder.remove();
      }

      const row = document.createElement("div");
      row.classList.add("chat-message");
      if (role === "ai") {
        row.classList.add("chat-message-ai");
      }
      row.textContent = text;
      chatMessages.appendChild(row);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    window.addEventListener("message", (event) => {
      const msg = event.data;
      if (msg.type === "generateComplete") {
        setGenerating(false);
      }
      if (msg.type === "reviewResponse") {
        setReviewing(false);
        if (Array.isArray(msg.messages)) {
          msg.messages.forEach(function (m) {
            if (typeof m === "string") {
              appendChatMessage(m, "ai");
            } else if (m && typeof m.text === "string") {
              appendChatMessage(m.text, "ai");
            }
          });
        } else if (msg.message) {
          appendChatMessage(String(msg.message), "ai");
        }
      }
      if (msg.type === "reviewError") {
        setReviewing(false);
        const text = msg.error || "Review failed. See extension logs for details.";
        appendChatMessage(String(text), "ai");
      }
    });

    generateBtn.addEventListener("click", () => {
      if (generateBtn.disabled) return;

      const smells = Array.from(
        document.querySelectorAll('input[type="checkbox"]:checked')
      ).map(cb => cb.value);

      setGenerating(true);

      var topicInput = document.getElementById("topic");
      var topicValue = topicInput && "value" in topicInput ? topicInput.value : "";

      vscode.postMessage({
        type: "submit",
        topic: topicValue,
        smells
      });
    });

    if (reviewBtn) {
      reviewBtn.addEventListener("click", () => {
        if (reviewBtn.disabled) return;
        setReviewing(true);

        // TODO: add any payload you want to send to your backend here
        vscode.postMessage({
          type: "review",
          payload: {
            // example: fileName, code, metadata, etc.
          }
        });
      });
    }
  </script>
</body>
</html>
    `;
  }

  /* =========================
     BACKEND CALL
     ========================= */

  private async fetchAiQuestionsFromBackend(
    topic: string,
    smells: string[]
  ): Promise<any> {
    const controller = new AbortController();
    const timeoutMs = 20 * 60 * 1000; // 20 minutes
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch("http://localhost:8000/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, code_smells: smells }),
        signal: controller.signal
      });

      clearTimeout(timeout);

      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }

      const data: any = await response.json();

      if (data.status !== "success") {
        throw new Error(data.message || "Failed to generate exercise");
      }

      return data;
    } catch (err: any) {
      if (err && err.name === "AbortError") {
        throw new Error("Request timed out after 20 minutes. Please try again later.");
      }
      throw err;
    }
  }

  /**
   * Boilerplate for calling your backend AI review endpoint.
   * Configure the URL, payload shape, and response handling to match your backend.
   */
  private async fetchReviewFromBackend(payload: any): Promise<any> {
    // TODO: Replace the URL and payload with your own review endpoint.
    const response = await fetch("http://localhost:8000/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload ?? {})
    });

    if (!response.ok) {
      throw new Error(`Backend review error: ${response.statusText}`);
    }

    // Expected response shape (example):
    // { messages: string[] }
    // Adjust this to whatever your backend returns.
    return response.json();
  }
}
