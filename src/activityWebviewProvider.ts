import * as vscode from "vscode";

export class ActivityWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "codellamas_activityView";

  constructor(private readonly context: vscode.ExtensionContext) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView
  ) {
    webviewView.webview.options = {
      enableScripts: true
    };

    webviewView.webview.html = this.getHtml(webviewView.webview);
    // Listen for messages from the webview
    webviewView.webview.onDidReceiveMessage(message => {
      if (message.type === "activity") {
        // Do something with the message
        vscode.window.showInformationMessage(`Activity: ${message.text}`);
      }
    });
  }

  private getHtml(webview: vscode.Webview): string {
    return /* html */ `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>CodeLlamas Activity</title>
        <style>
          body {
            font-family: var(--vscode-font-family);
            padding: 12px;
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
          }
          .item {
            margin-bottom: 8px;
            padding: 8px;
            border-radius: 4px;
            background: var(--vscode-editorWidget-background);
          }
          button {
            margin-top: 12px;
          }
        </style>
      </head>
      <body>
        <h3>🦙 CodeLlamas Activity</h3>

        <div class="item">Extension activated</div>
        <div class="item">No refactors yet</div>

        <button onclick="logActivity()">Simulate Activity</button>

        <script>
          const vscode = acquireVsCodeApi();

          function logActivity() {
            vscode.postMessage({
              type: "activity",
              text: "Refactor executed"
            });
          }
        </script>
      </body>
      </html>
    `;
  }
}
