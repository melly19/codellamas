import * as vscode from "vscode";
import { saveToSpringBootProject } from "./springBootSaver";
import { buildReviewPayload } from "./buildReviewPayload";

interface Feedback {
  functional_correctness_assessment: string;
  code_quality_review: string;
  actionable_feedback: string;
  overall_verdict: string;
  rating: number;
}

interface ReviewResult {
  feedback: string;
  maven_verification: {
    enabled: boolean;
  };
}

export interface ProjectFile {
  path: string;
  content: string;
}

export interface ResponseData {
  status: string;
  message: string;
  data: {
    problem_description: string;
    project_files: ProjectFile[];
    test_files: ProjectFile[];
    solution_explanation_md: string;
    paths_to_ex: string[];
    answers_list: ProjectFile[];
  };
}

export class ActivityWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "codellamas_activityView";

  private solutionExp: any[] | string | null = null;
  private responseData: any = null;
  private webviewView: vscode.WebviewView | undefined;
  private selectedSmells: string[] = [];

  private backendUrl: string;
  private mode: string;
  private modelName: string;
  private apiEndpoint: string;
  private apiKey: string;

  public revealReviewPanel() {
    if (this.webviewView) {
      this.webviewView.show?.(true);
    }
  }

  public getSolutionExp(): any[] | string | null {
    return this.solutionExp;
  }
  constructor(private readonly context: vscode.ExtensionContext) { 
    require("dotenv").config({ path: require("path").join(this.context.extensionPath, '.env') });
    
    this.solutionExp =
      this.context.workspaceState.get<any[] | string | null>("solutionExp")??null;
    this.responseData =
      this.context.workspaceState.get<any>("responseData")??null;
    this.selectedSmells = 
      this.context.workspaceState.get<string[]>("selectedSmells")??[];
    this.backendUrl = 
      // this.context.workspaceState.get<string>("backendUrl") ?? "http://CS480G4@10.193.104.102:8000";
      vscode.workspace.getConfiguration("javaExerciseGenerator").get("backendBaseUrl") ?? "http://127.0.0.1:8000";
    this.mode = 
      this.context.workspaceState.get<string>("mode") ?? "single";

    this.modelName = this.context.workspaceState.get<string>("modelName") ?? process.env.AI_MODEL_NAME ?? "openrouter/qwen/qwen3-coder-30b-a3b-instruct";
    this.apiEndpoint = this.context.workspaceState.get<string>("apiEndpoint") ?? process.env.AI_API_ENDPOINT ?? "https://openrouter.ai/api/v1";
    this.apiKey = this.context.workspaceState.get<string>("apiKey") ?? process.env.AI_API_KEY ?? "";
  }

  /* =========================
     ACTIVITY BAR VIEW
     ========================= */

  resolveWebviewView(webviewView: vscode.WebviewView) {
    this.webviewView = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.getActivityHtml();

    webviewView.webview.onDidReceiveMessage(async (message) => {
      if (message.type === "submit") {
        try {
          this.selectedSmells = message.smells;
          this.responseData = await this.fetchAiQuestionsFromBackend(
            message.topic,
            message.smells
          );
          await saveToSpringBootProject(this.responseData, webviewView);
          this.solutionExp = this.responseData.data.answers_list ?? null;
          console.log("Full responseData:", this.responseData);
          console.log("Reference Solution in memory:", this.solutionExp);

          await this.context.workspaceState.update("selectedSmells", this.selectedSmells);
          await this.context.workspaceState.update("solutionExp", this.solutionExp);
          await this.context.workspaceState.update("responseData", this.responseData);
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
        // Load responseData from workspaceState if not in memory
        if (!this.responseData) {
          this.responseData = this.context.workspaceState.get<any>("responseData") ?? null;
        }
        
        if (!this.responseData || !this.responseData.data) {
          vscode.window.showErrorMessage("No reference solution available");
          return;
        }
        
        const solutionMd = this.responseData.data.solution_explanation_md;
        const answersList = this.responseData.data.answers_list;
        
        if (!solutionMd && (!answersList || answersList.length === 0)) {
          vscode.window.showErrorMessage("No reference solution content available");
          return;
        }
        
        try {
          // Write solution explanation markdown
          if (solutionMd) {
            await this.writeShowFile(solutionMd, "SOLUTION_EXPLANATION.md");
          }
          
          // Write each answer file
          if (answersList && Array.isArray(answersList)) {
            for (const file of answersList) {
              await this.writeShowFile(file.content, file.path);
            }
          }
          
          vscode.window.showInformationMessage("Reference solutions saved to /answers folder!");
        } catch (err: any) {
          vscode.window.showErrorMessage(
            "Failed to show reference solution: " + String(err)
          );
        }
      } else if (message.type === "updateSettings") {
        this.backendUrl = message.backendUrl;
        this.mode = message.mode;
        this.modelName = message.modelName;
        this.apiEndpoint = message.apiEndpoint;
        this.apiKey = message.apiKey;

        this.context.workspaceState.update("backendUrl", this.backendUrl);
        this.context.workspaceState.update("mode", this.mode);
        this.context.workspaceState.update("modelName", this.modelName);
        this.context.workspaceState.update("apiEndpoint", this.apiEndpoint);
        this.context.workspaceState.update("apiKey", this.apiKey);

        vscode.window.showInformationMessage("Settings saved!");
        
        // Refresh the webview to update injected strings
        if (this.webviewView) {
          this.webviewView.webview.html = this.getActivityHtml();
        }
      }

    });
  }

  private async writeShowFile(content: string, path: string) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
      vscode.window.showErrorMessage("No workspace folder open!");
      return;
    }
    
    const pathModule = require("path");
    const fs = require("fs");
    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const answersDir = pathModule.join(workspaceRoot, "answers");
    const filePath = pathModule.join(answersDir, path);
    const directory = pathModule.dirname(filePath);
    
    // Create directory if it doesn't exist
    if (!fs.existsSync(directory)) {
      fs.mkdirSync(directory, { recursive: true });
    }
    
    // Write the file
    fs.writeFileSync(filePath, content, "utf8");
    
    // Open the file
    const doc = await vscode.workspace.openTextDocument(filePath);
    await vscode.window.showTextDocument(doc);
  }

  public postMessage(message: any) {
    if (this.webviewView) {
      this.webviewView.webview.postMessage(message);
    } else {
      vscode.window.showWarningMessage(
        "Activity webview not open. Message cannot be sent."
      );
    }
  }


  private getActivityHtml(): string {
    const backendUrl = this.backendUrl;
    const mode = this.mode;
    const modelName = this.modelName;
    const apiEndpoint = this.apiEndpoint;
    const apiKey = this.apiKey;
    
    return /* html */ `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Codellamas</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/treeselectjs@0.14.2/dist/treeselectjs.css" />
  <style>
    :root {
      --treeselectjs-bg: var(--vscode-dropdown-background, #111e2c);
      --treeselectjs-border-color: var(--vscode-dropdown-border, #1c324a);
      --treeselectjs-border-focus: var(--vscode-focusBorder, #4aa6ff);
      --treeselectjs-tag-bg: var(--vscode-badge-background, #1c324a);
      --treeselectjs-tag-bg-hover: var(--vscode-list-hoverBackground, #264363);
      --treeselectjs-tag-remove-hover: var(--vscode-errorForeground, #ff6b6b);
      --treeselectjs-icon: var(--vscode-icon-foreground, #a0b9d9);
      --treeselectjs-icon-hover: var(--vscode-foreground, #ffffff);
      --treeselectjs-item-counter: var(--vscode-descriptionForeground, #8a9fb5);
      --treeselectjs-item-focus-bg: var(--vscode-list-activeSelectionBackground, #162a42);
      --treeselectjs-item-selected-bg: var(--vscode-list-inactiveSelectionBackground, #1c3654);
      --treeselectjs-item-disabled-text: var(--vscode-disabledForeground, #59738c);
      --treeselectjs-checkbox-bg: var(--vscode-checkbox-background, #0b141e);
      --treeselectjs-checkbox-border-color: var(--vscode-checkbox-border, #2a4b6e);
      --treeselectjs-checkbox-checked-bg: var(--vscode-button-background, #0e639c);
      --treeselectjs-checkbox-checked-icon: var(--vscode-button-foreground, #ffffff);
    }
    .treeselect-list {
      background: var(--treeselectjs-bg);
      border: 1px solid var(--treeselectjs-border-color);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
      color: var(--vscode-foreground, #ffffff);
    }
    .treeselect-input__edit {
      color: var(--vscode-input-foreground, #ffffff) !important;
    }
    .treeselect-input__tags-element {
      color: var(--vscode-badge-foreground, #ffffff) !important;
    }
    .treeselect-input__tags-name {
      color: var(--vscode-badge-foreground, #ffffff) !important;
    }
    .treeselect-item {
      color: var(--vscode-foreground, #ffffff) !important;
    }
    .treeselect-item__name {
      color: inherit;
    }
    .treeselect-input,
    .treeselect-input * {
      color: var(--vscode-foreground, #ffffff);
    }
    .treeselect-input__tags-count {
      color: var(--vscode-foreground, #ffffff);
    }

    body {
      font-family: var(--vscode-font-family);
      padding: 16px 20px;
      background-color: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
      height: 100vh;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;

    background:
    /* radial-gradient(circle at 85% 90%, rgba(24, 80, 130, 0.32), transparent 45%),
    radial-gradient(circle at 0% 0%, rgba(13, 110, 140, 0.3), transparent 40%),
    linear-gradient(135deg, #0A1A3F, #071433 60%, #050E23); */
    #111e2c;
    
    
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

  input[type="checkbox"]:focus {
  outline: none !important;
  box-shadow: none !important;
  }

  input[type="checkbox"]:focus-visible {
  outline: none !important;
  box-shadow: none !important;
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
      display: flex;
      flex-direction: column;
    }

    .chat-messages {
      flex: 1;
      padding: 8px 0;
      overflow-y: auto;
      box-sizing: border-box;
      font-size: 0.9rem;
    }

    .chat-message {
      padding: 12px 4px;
      margin-bottom: 0;
      line-height: 1.5;
      word-wrap: break-word;
      border-bottom: 1px solid var(--vscode-editorGroup-border);
    }
    
    .chat-message:last-child {
      border-bottom: none;
    }

    .chat-message-ai {
      background-color: transparent;
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

    /* Markdown chat styles */
    .chat-message p { margin: 0 0 8px 0; }
    .chat-message p:last-child { margin-bottom: 0; }
    .chat-message pre {
      background-color: #1e1e1e;
      color: #d4d4d4;
      padding: 8px;
      border-radius: 4px;
      overflow-x: auto;
      margin: 8px 0;
      border: 1px solid rgba(255,255,255,0.1);
    }
    .chat-message code {
      font-family: var(--vscode-editor-font-family, monospace);
      background-color: rgba(255,255,255,0.05);
      padding: 2px 4px;
      border-radius: 3px;
      font-size: 0.85em;
    }
    .chat-message h1, .chat-message h2, .chat-message h3 {
      font-size: 1.1em;
      margin: 12px 0 6px 0;
      font-weight: 600;
    }
    .chat-message ul, .chat-message ol {
      margin: 8px 0;
      padding-left: 20px;
    }

/* Selected smell chips */
.selected-smells {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 6px 0 12px 0;
}

.smell-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  background-color: var(--vscode-badge-background);
  color: var(--vscode-badge-foreground);
}

.smell-chip button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0;
  color: inherit;
}

  </style>
</head>
<body>
  <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--vscode-editorGroup-border); margin: 12px 0 16px 0; max-width: 100%;">
    <div class="tabs" style="border-bottom: none; margin: 0; overflow-x: auto; flex-wrap: nowrap; flex: 1; scrollbar-width: none;">
      <button class="tab active" data-panel="generate" style="flex-shrink: 0;">Generate</button>
      <button class="tab" data-panel="review" style="flex-shrink: 0;">Review</button>
      <button class="tab" data-panel="answer" style="flex-shrink: 0;">Answer</button>
    </div>
    <button id="settingsIconBtn" title="Settings" style="background: none; border: none; cursor: pointer; color: var(--vscode-foreground); padding: 4px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-left: 8px;">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path fill-rule="evenodd" clip-rule="evenodd" d="M9.1 0h-2.2l-.3 1.6c-.4.1-.8.3-1.2.6L4.1 1.4 2.5 3l.8 1.3c-.2.4-.4.8-.5 1.2L1.2 5.8v2.2l1.6.3c.1.4.3.8.6 1.2l-.8 1.3 1.6 1.6 1.3-.8c.4.2.8.4 1.2.5l.3 1.6h2.2l.3-1.6c.4-.1.8-.3 1.2-.6l1.3.8 1.6-1.6-.8-1.3c.2-.4.4-.8.5-1.2l1.6-.3V5.8l-1.6-.3c-.1-.4-.3-.8-.6-1.2l.8-1.3-1.6-1.6-1.3.8c-.4-.2-.8-.4-1.2-.5L9.1 0zM8 10a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/>
      </svg>
    </button>
  </div>

  <div id="panel-generate" class="panel active">
    <h1>Generating Code Smell Activity</h1>

    <div class="section-title">Select Code Smells</div>
    <div class="section-subtitle">
      Choose one or more refactoring topics to practise.
    </div>
    
    <div class="example" style="margin-bottom: 20px;"></div>

    <div class="topic">
      <label for="topic">Topic</label>
      <input id="topic" type="text" placeholder="e.g. Banking, E-Commerce" />
    </div>

    <div class="submit-container">
      <button id="generateBtn" type="button">Generate Question</button>
    </div>
  </div>

  <div id="panel-review" class="panel">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
      <div class="section-title" style="margin-bottom: 0;">Review</div>
      <button id="clearChatBtn" type="button" style="background-color: transparent; border: 1px solid var(--vscode-editorGroup-border); color: var(--vscode-descriptionForeground); padding: 2px 8px; font-size: 0.8rem;" title="Clear Chat">Clear</button>
    </div>
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

  <div id="panel-settings" class="panel">
    <div class="section-title">Settings</div>
    
    <div class="topic" style="margin-top: 12px;">
      <label for="settings-backendUrl">Backend Endpoint</label>
      <input id="settings-backendUrl" type="text" value="${backendUrl}" />
    </div>

    <div class="topic" style="margin-top: 12px;">
      <label for="settings-modelName">Model Name</label>
      <input id="settings-modelName" type="text" value="${modelName}" />
    </div>

    <div class="topic" style="margin-top: 12px;">
      <label for="settings-apiEndpoint">AI API Endpoint</label>
      <input id="settings-apiEndpoint" type="text" value="${apiEndpoint}" />
    </div>

    <div class="topic" style="margin-top: 12px;">
      <label for="settings-apiKey">AI API Key</label>
      <input id="settings-apiKey" type="password" value="${apiKey}" />
    </div>

    <div class="topic" style="margin-top: 16px;">
      <label>Mode</label>
      <div style="margin-top: 4px;">
        <button id="settings-modeBtn" type="button" style="width: 100%; text-align: center; font-weight: bold; font-size: 0.95rem; padding: 8px;">
          ${mode.toUpperCase()}
        </button>
      </div>
    </div>
    
    <div class="submit-container" style="margin-top: 24px;">
      <button id="saveSettingsBtn" type="button">Save Settings</button>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script type="module">
    import Treeselect from 'https://cdn.jsdelivr.net/npm/treeselectjs@0.14.2/dist/treeselectjs.mjs';
    const vscode = acquireVsCodeApi();

    // Persist webview state
    let state = vscode.getState() || { 
      topic: "", 
      smells: [], 
      messages: [],
      activeTab: "generate"
    };

    function saveState() {
      vscode.setState(state);
    }

    // Override settings from extension to keep them in sync
    state.backendUrl = "${backendUrl}";
    state.mode = "${mode}";
    state.modelName = "${modelName}";
    state.apiEndpoint = "${apiEndpoint}";
    state.apiKey = "${apiKey}";
    saveState();

    const tabs = Array.from(document.querySelectorAll('.tab'));
    const panels = {
      generate: document.getElementById('panel-generate'),
      review: document.getElementById('panel-review'),
      answer: document.getElementById('panel-answer'),
      settings: document.getElementById('panel-settings'),
    };

    function showPanel(name) {
      tabs.forEach(tab => {
        const isActive = tab.dataset.panel === name;
        tab.classList.toggle('active', isActive);
      });

      Object.entries(panels).forEach(([key, el]) => {
        if (!el) return;
        el.classList.toggle('active', key === name);
      });

      state.activeTab = name;
      saveState();
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
    const clearChatBtn = document.getElementById("clearChatBtn");
    const chatMessages = document.getElementById("chat-messages");
    const showAnswerBtn = document.getElementById("showAnswerBtn");
    const topicInput = document.getElementById("topic");

    const settingsIconBtn = document.getElementById("settingsIconBtn");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");
    const settingsBackendUrl = document.getElementById("settings-backendUrl");
    const settingsModelName = document.getElementById("settings-modelName");
    const settingsApiEndpoint = document.getElementById("settings-apiEndpoint");
    const settingsApiKey = document.getElementById("settings-apiKey");
    const settingsModeBtn = document.getElementById("settings-modeBtn");

    if (settingsIconBtn) {
      settingsIconBtn.addEventListener('click', () => {
        showPanel("settings");
      });
    }

    if (settingsModeBtn) {
      settingsModeBtn.addEventListener('click', () => {
        state.mode = state.mode === "single" ? "multi" : "single";
        settingsModeBtn.textContent = state.mode.toUpperCase();
        saveState();
      });
    }

    if (saveSettingsBtn) {
      saveSettingsBtn.addEventListener('click', () => {
        state.backendUrl = settingsBackendUrl.value;
        state.modelName = settingsModelName.value;
        state.apiEndpoint = settingsApiEndpoint.value;
        state.apiKey = settingsApiKey.value;
        saveState();
        vscode.postMessage({
          type: "updateSettings",
          backendUrl: state.backendUrl,
          modelName: state.modelName,
          apiEndpoint: state.apiEndpoint,
          apiKey: state.apiKey,
          mode: state.mode
        });
      });
    }

    if (topicInput) {
      topicInput.addEventListener("input", (e) => {
        state.topic = e.target.value;
        saveState();
      });
    }

    const treeselectOptions = [
      {
        name: 'Bloaters',
        value: 'Bloaters',
        children: [
          { name: 'Long Method', value: 'Long Method' },
          { name: 'Large Class', value: 'Large Class' },
          { name: 'Primitive Obsession', value: 'Primitive Obsession' },
          { name: 'Data Clumps', value: 'Data Clumps' },
          { name: 'Long Parameter List', value: 'Long Parameter List' }
        ]
      },
      {
        name: 'Dispensables',
        value: 'Dispensables',
        children: [
          { name: 'Duplicate Code', value: 'Duplicate Code' },
          { name: 'Dead Code', value: 'Dead Code' },
          { name: 'Comments', value: 'Comments' },
          { name: 'Data Class', value: 'Data Class' },
          { name: 'Lazy Class', value: 'Lazy Class' },
          { name: 'Speculative Generality', value: 'Speculative Generality' }
        ]
      },
      {
        name: 'Object-Orientation Abusers',
        value: 'Object-Orientation Abusers',
        children: [
          { name: 'Alternative Classes With Different Interfaces', value: 'Alternative Classes With Different Interfaces' },
          { name: 'Refused Bequest', value: 'Refused Bequest' },
          { name: 'Temporary Field', value: 'Temporary Field' },
          { name: 'Switch Statements', value: 'Switch Statements' }
        ]
      },
      {
        name: 'Change Preventers',
        value: 'Change Preventers',
        children: [
          { name: 'Divergent Change', value: 'Divergent Change' },
          { name: 'Parallel Inheritance Hierarchies', value: 'Parallel Inheritance Hierarchies' },
          { name: 'Shotgun Surgery', value: 'Shotgun Surgery' }
        ]
      },
      {
        name: 'Couplers',
        value: 'Couplers',
        children: [
          { name: 'Feature Envy', value: 'Feature Envy' },
          { name: 'Message Chains', value: 'Message Chains' },
          { name: 'Incomplete Library Class', value: 'Incomplete Library Class' },
          { name: 'Middle Man', value: 'Middle Man' },
          { name: 'Inappropriate Initimacy', value: 'Inappropriate Initimacy' }
        ]
      }
    ];

    const treeselect = new Treeselect({
      parentHtmlContainer: document.querySelector('.example'),
      value: state.smells || [],
      options: treeselectOptions,
      isGroupedValue: true,
      showTags: true,
      searchable: true,
      placeholder: 'Search Code Smells...',
      alwaysOpen: false
    });

    treeselect.srcElement.addEventListener('input', (e) => {
      // Treeselect passes the new value via e.detail
      state.smells = e.detail;
      saveState();
    });

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

    function appendChatMessage(text, role, persist = true) {
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
      
      if (typeof marked !== 'undefined') {
        row.innerHTML = marked.parse(text);
      } else {
        row.textContent = text;
      }
      
      chatMessages.appendChild(row);
      chatMessages.scrollTop = chatMessages.scrollHeight;

      if (persist) {
        state.messages.push({ text, role });
        saveState();
      }
    }

    // Initialize UI using State
    if (state.topic && topicInput) {
      topicInput.value = state.topic;
    }
    
    if (state.backendUrl && settingsBackendUrl) {
      settingsBackendUrl.value = state.backendUrl;
    }
    if (state.modelName && settingsModelName) {
      settingsModelName.value = state.modelName;
    }
    if (state.apiEndpoint && settingsApiEndpoint) {
      settingsApiEndpoint.value = state.apiEndpoint;
    }
    if (state.apiKey && settingsApiKey) {
      settingsApiKey.value = state.apiKey;
    }
    if (state.mode && settingsModeBtn) {
      settingsModeBtn.textContent = state.mode.toUpperCase();
    }
    
    if (state.messages && state.messages.length > 0) {
      state.messages.forEach(msg => {
        appendChatMessage(msg.text, msg.role, false);
      });
    }

    if (state.activeTab) {
      showPanel(state.activeTab === 'settings' ? 'generate' : state.activeTab);
    }

window.addEventListener("message", (event) => {
  const msg = event.data;

  if (msg.type === "switchTab" && msg.tab) {
    const panelName = msg.tab;
    if (panelName && panels[panelName]) {
      showPanel(panelName);
    }
  }

  if (msg.type === "generateComplete") {
    setGenerating(false);
  }

  if (msg.type === "reviewResponse") {
    setReviewing(false);
    if (Array.isArray(msg.messages)) {
      msg.messages.forEach((m) => {
        if (typeof m === "string") {
          appendChatMessage(m, "ai");
        } else if (m && typeof m.text === "string") {
          appendChatMessage(m.text, "ai");
        } else if (typeof m === "object" && m !== null) {
          appendChatMessage('\`\`\`json\\n' + JSON.stringify(m, null, 2) + '\\n\`\`\`', "ai");
        } else if (m) {
          appendChatMessage(String(m), "ai");
        }
      });
    } else if (msg.message) {
      const out = typeof msg.message === "object" ? '\`\`\`json\\n' + JSON.stringify(msg.message, null, 2) + '\\n\`\`\`' : String(msg.message);
      appendChatMessage(out, "ai");
    } else if (msg.feedback) {
      const out = typeof msg.feedback === "object" ? '\`\`\`json\\n' + JSON.stringify(msg.feedback, null, 2) + '\\n\`\`\`' : String(msg.feedback);
      appendChatMessage(out, "ai");
    }
  }

  if (msg.type === "reviewError") {
    setReviewing(false);
    const errObj = msg.error || "Review failed. See extension logs for details.";
    const text = typeof errObj === "object" ? '\`\`\`json\\n' + JSON.stringify(errObj, null, 2) + '\\n\`\`\`' : String(errObj);
    appendChatMessage(String(text), "ai");
  }
});


    generateBtn.addEventListener("click", () => {
      if (generateBtn.disabled) return;

      const rawSmells = state.smells || [];
      const expandedSmells = new Set();
      
      const optionsMap = {};
      treeselectOptions.forEach(group => {
        optionsMap[group.value] = group.children.map(child => child.value);
      });

      rawSmells.forEach(smell => {
        // If it's a category group, push all its children
        if (optionsMap[smell]) {
          optionsMap[smell].forEach(childVal => expandedSmells.add(childVal));
        } else {
          // Otherwise it's a specific subcategory
          expandedSmells.add(smell);
        }
      });

      const smells = Array.from(expandedSmells);

      setGenerating(true);

      var topicInput = document.getElementById("topic");
      var topicValue = topicInput && "value" in topicInput ? topicInput.value : "";

      vscode.postMessage({
        type: "submit",
        topic: topicValue,
        smells
      });
    });

    if (clearChatBtn) {
      clearChatBtn.addEventListener("click", () => {
        if (!chatMessages) return;
        chatMessages.innerHTML = '<div class="chat-placeholder">Run a review to see feedback from your backend AI.</div>';
        state.messages = [];
        saveState();
      });
    }

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
      const payload = { 
        topic, 
        code_smells: smells, 
        mode: this.mode,
        model_name: this.modelName,
        api_endpoint: this.apiEndpoint,
        api_key: this.apiKey 
      };
      console.log("=========================================");
      console.log("[POST /generate] Sending Payload:");
      console.log(JSON.stringify(payload, null, 2));
      console.log("=========================================");

      let baseUrl = (this.backendUrl || "").trim();
      if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
        baseUrl = "http://" + baseUrl;
      }
      if (baseUrl.endsWith("/")) {
        baseUrl = baseUrl.slice(0, -1);
      }

      const endpoint = `${baseUrl}/generate`;
      console.log(`[POST /generate] Endpoint: ${endpoint}`);
      
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeout);

      if (!response.ok) {
        throw new Error(`Backend error: ${response.statusText}`);
      }

      const data: any = await response.json();

      console.log("=========================================");
      console.log("[POST /generate] Received Response:");
      console.log(JSON.stringify(data, null, 2));
      console.log("=========================================");

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
    // Build payload using selected smells or fallback to generated exercise data
    try {
      const codeSmells = (this.selectedSmells && this.selectedSmells.length)
        ? this.selectedSmells
        : (this.responseData && this.responseData.data && this.responseData.data.code_smells) || [];

      const builtPayload = await buildReviewPayload(this, codeSmells, this.responseData.data.paths_to_ex);
      if (!builtPayload) {
        return;
      }
      
      // Attach the mode and other settings to the payload dynamically
      builtPayload.mode = this.mode;
      builtPayload.model_name = this.modelName;
      builtPayload.api_endpoint = this.apiEndpoint;
      builtPayload.api_key = this.apiKey;

      console.log("=========================================");
      console.log("[POST /review] Sending Payload:");
      console.log(JSON.stringify(builtPayload, null, 2));
      console.log("=========================================");

      let baseUrl = (this.backendUrl || "").trim();
      if (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://")) {
        baseUrl = "http://" + baseUrl;
      }
      if (baseUrl.endsWith("/")) {
        baseUrl = baseUrl.slice(0, -1);
      }

      const endpoint = `${baseUrl}/review`;
      console.log(`[POST /review] Endpoint: ${endpoint}`);

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(builtPayload)
      });
      if (!response.ok) {
        throw new Error(`Backend review error: ${response.statusText}`);
      }
      const reviewResult = (await response.json()) as ReviewResult;
      
      console.log("=========================================");
      console.log("[POST /review] Received Response:");
      console.log(JSON.stringify(reviewResult, null, 2));
      console.log("=========================================");

      let parsedFeedback = reviewResult.feedback;
      try {
        // If the model still happens to return JSON, gracefully parse it
        const extracted = typeof reviewResult.feedback === "string" 
           ? JSON.parse(reviewResult.feedback) 
           : reviewResult.feedback;
           
        if (typeof extracted === "object" && extracted !== null) {
          parsedFeedback = Object.entries(extracted)
            .map(([key, val]) => {
              const strVal = typeof val === "object" ? JSON.stringify(val, null, 2) : String(val);
              // Capitalize key for better appearance
              const formatKey = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ");
              return `### ${formatKey}\n${strVal}`;
            })
            .join("\n\n");
        } else {
          parsedFeedback = String(extracted);
        }
      } catch (e) {
        // Expected route: it's plain markdown text
        parsedFeedback = typeof reviewResult.feedback === "object" ? JSON.stringify(reviewResult.feedback, null, 2) : String(reviewResult.feedback);
      }

      this.postMessage({
        type: "reviewResponse",
        messages: [parsedFeedback]
      });
      vscode.window.showInformationMessage("Code submitted successfully!");
    } catch (err: any) {
      const errorMessage = "Error submitting code: " + String(err);
      vscode.window.showErrorMessage(errorMessage);
      this.postMessage({
        type: "reviewError",
        error: errorMessage
      });
    }
  }
}