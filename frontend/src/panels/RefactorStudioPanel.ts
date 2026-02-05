import * as vscode from "vscode";
import * as fs from "fs";

export class RefactorStudioPanel {
  private static currentPanel: RefactorStudioPanel | undefined;
  private readonly panel: vscode.WebviewPanel;

  // BACKEND STATE (in-memory only)
  private questions: string[] = [];

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this.panel = panel;
    this.panel.webview.html = this.getHtml(extensionUri);

    this.panel.webview.onDidReceiveMessage((message) => {
      if (message.command === "generateExercise") {
        this.questions = [
          "Refactor Long Method – Banking Service"
        ];
        this.renderQuestions();
      }
    });
  }

  public static createOrShow(extensionUri: vscode.Uri) {
    if (RefactorStudioPanel.currentPanel) {
      RefactorStudioPanel.currentPanel.panel.reveal();
      RefactorStudioPanel.currentPanel.renderQuestions();
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "refactorStudio",
      "CodeLlamas – Refactoring Studio",
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [
          vscode.Uri.joinPath(extensionUri, "src", "webview")
        ]
      }
    );

    RefactorStudioPanel.currentPanel =
      new RefactorStudioPanel(panel, extensionUri);
  }

  private renderQuestions() {
    this.panel.webview.postMessage({
      command: "renderQuestions",
      questions: this.questions
    });
  }

  private getHtml(extensionUri: vscode.Uri): string {
    const htmlPath = vscode.Uri.joinPath(
      extensionUri,
      "src",
      "webview",
      "index.html"
    );

    let html = fs.readFileSync(htmlPath.fsPath, "utf8");

    const baseUri = this.panel.webview.asWebviewUri(
      vscode.Uri.joinPath(extensionUri, "src", "webview")
    );

    return html.replace(/{{BASE_URI}}/g, baseUri.toString());
  }
}
