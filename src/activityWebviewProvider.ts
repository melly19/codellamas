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
      if (message.type === "openGenerator") {
        this.openQuestionGenerator();
      }
    });
  }


private openQuestionGenerator() {
  const panel = vscode.window.createWebviewPanel(
    "codellamasGenerator",
    "Code Smells",
    vscode.ViewColumn.One,
    { enableScripts: true }
  );

  panel.webview.html = this.getGeneratorHtml(panel.webview);

  panel.webview.onDidReceiveMessage(async msg => {
    if (msg.type === "submit") {
      await this.sendToEndpoint(msg.topic, msg.smells, panel);
    }
  });
}


private getHtml(webview: vscode.Webview): string {
    return /* html */ `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>codellamas_activity</title>
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

      <button onclick="generate()">Generate Questions</button>

      <script>
        const vscode = acquireVsCodeApi();

        function generate() {
          vscode.postMessage({ type: "openGenerator" });
        }
      </script>
    </body>
    </html>
    `;
  }

private getGeneratorHtml(webview: vscode.Webview): string {
  return /* html */ `
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>Code Smells</title>
    <style>
      body {
        font-family: var(--vscode-font-family);
        padding: 16px;
      }

      .header {
        text-align: center;
        margin-bottom: 20px;
      }

      .header h1 {
        margin: 0;
        font-size: 1.5em;
      }

      h2 {
        margin-bottom: 8px;
      }

      .section {
        margin-bottom: 16px;
      }

      input[type="text"] {
        width: 60%;
        max-width: 400px;
        min-width: 260px;
        padding: 10px;

        border: 1px solid var(--vscode-input-border);
        border-radius: 2px;
      }

      .submit-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
      }

      button {
        background-color: #8ecbff;
        border: none;
        padding: 10px 14px;
        border-radius: 6px;
        font-weight: bold;
        cursor: pointer;
      }
    </style>
  </head>
  <body>
    <div class="header">
      <h1>Generating Code Smell Activity For Refactoring Practice</h1>
    </div>
    <h2>Code Smells</h2>

    <div class="section">
      <label><input type="checkbox" value="Bloaters"> Bloaters</label><br />
      <label><input type="checkbox" value="Object-Orientation Abusers"> Object-Orientation Abusers</label><br />
      <label><input type="checkbox" value="Change Preventers"> Change Preventers</label><br />         
      <label><input type="checkbox" value="Dispensables"> Dispensables</label><br />
      <label><input type="checkbox" value="Couplers"> Couplers</label><br />
    </div>

    <h3>Topic</h3>
    <input id="topic" type="text" placeholder="Enter topic" />

    <div id="result" style="
        display: none;
        max-height: 70vh;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 4px;
        white-space: pre-wrap;
    "></div>

    <br /><br />
    <div class="submit-container">
    <button onclick="submit()">Submit</button>
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

      // Listen for messages from the extension
      window.addEventListener("message", event => {
          const message = event.data;
          if (message.type === "response") {
              const container = document.getElementById("result");

              // Make it visible
              container.style.display = "block";

              // Clear previous content
              container.innerHTML = "";

              // Fill in response
              const topic = message.data.topic ?? "";
              const smells = Array.isArray(message.data.smells) ? message.data.smells.join(", ") : "";
              const question = message.data.question ?? "";

              container.innerHTML = "<h3>Generated Question</h3>" +
                                    "<p><strong>Topic:</strong> " + topic + "</p>" +
                                    "<p><strong>Smells:</strong> " + smells + "</p>" +
                                    "<p><strong>Question:</strong> " + question + "</p>";
          }
      });
    </script>
  </body>
  </html>
  `;
}

private async sendToEndpoint(topic: string, smells: string[], panel: vscode.WebviewPanel) {
  const endpoint = "https://YOUR_ENDPOINT_HERE";

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
        // Authorization: "Bearer YOUR_TOKEN"  // if needed
      },
      body: JSON.stringify({
        topic,
        smells
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();

    panel.webview.postMessage({
      type: "response",
      data: result
    });

    vscode.window.showInformationMessage("Code smell activity submitted!");

    return result;

  } catch (error) {
    console.error(error);
    vscode.window.showErrorMessage("Failed to submit activity");
  }
}

}
