import * as vscode from "vscode";
import { saveToSpringBootProject } from "./springBootSaver"; 

export class ActivityWebviewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "codellamas_activityView";

  constructor(private readonly context: vscode.ExtensionContext) {}

  resolveWebviewView(webviewView: vscode.WebviewView) {
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.getHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(async (message) => {
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

    panel.webview.onDidReceiveMessage(async (msg) => {
      if (msg.type === "submit") {
        try {
          // Call backend to retrieve AI-generated questions
          const aiQuestions = await this.fetchAiQuestionsFromBackend(msg.topic, msg.smells);

          // const aiTestCases = await this.fetchAiTestCasesFromBackend(aiQuestions);
          // Save to Spring Boot project
          await saveToSpringBootProject(msg.topic, msg.smells, aiQuestions,/*aiTestCases,*/ panel);
        }catch (error) {
          vscode.window.showErrorMessage("Error generating questions: " + error);
        }
      }
    });
  }

private async fetchAiQuestionsFromBackend(topic: string, smells: string[]): Promise<string> {
  const response = await fetch("http://localhost:8000/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, smells }),
  });

  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`);
  }

  // Assume the backend returns a single string of Java code
  const data = (await response.json()) as { questions: string };
  // Directly return the AI-generated code (already formatted as Java lines)
  return data.questions;
}


  // private async fetchAiTestCasesFromBackend(questionCode: string): Promise<string> {
  //   const testResponse = await fetch("http://localhost:5000/", {
  //     method: "POST",
  //     headers: { "Content-Type": "application/json" },
  //     body: JSON.stringify({ questionCode }),
  //   });
  //   const testData = (await testResponse.json()) as { testCases: string };
  //   return testData.testCases;
  // }

//   private async fetchAiQuestionsFromBackend(
//     topic: string,
//     smells: string[]
//   ): Promise<string> {

//     // TEMPORARY MOCK AI RESPONSE
//     return `
// import java.util.ArrayList;
// import java.util.List;

// /**
//  * Topic: Traffic Lights
//  * Smells: Change Preventers, Dispensables, Couplers
//  */
// public class TrafficLightController {

//     private List<String> lights = new ArrayList<>();
//     private int currentIndex = 0;

//     // Initialize lights (Red, Yellow, Green)
//     public TrafficLightController() {
//         lights.add("RED");
//         lights.add("YELLOW");
//         lights.add("GREEN");
//     }

//     // Change Preventer: Hard-coded sequence, hard to extend
//     public void nextLight() {
//         if (currentIndex == 0) {
//             System.out.println("RED light ON");
//             currentIndex = 1;
//         } else if (currentIndex == 1) {
//             System.out.println("YELLOW light ON");
//             currentIndex = 2;
//         } else if (currentIndex == 2) {
//             System.out.println("GREEN light ON");
//             currentIndex = 0;
//         }
//     }

//     // Dispensables: Unused method that confuses the design
//     public void resetLights() {
//         lights.clear();
//         lights.add("RED");
//         lights.add("YELLOW");
//         lights.add("GREEN");
//     }

//     // Couplers: Directly accessing another class (tight coupling)
//     public void alertPedestrian(PedestrianCrossing crossing) {
//         if (currentIndex == 2) {
//             crossing.allowCrossing();
//         } else {
//             crossing.stopCrossing();
//         }
//     }

// }

// // Coupled class (tight coupling example)
// class PedestrianCrossing {
//     public void allowCrossing() {
//         System.out.println("Pedestrians can cross");
//     }

//     public void stopCrossing() {
//         System.out.println("Pedestrians must wait");
//     }
// }

//   `;
//   }


  private getHtml(webview: vscode.Webview): string {
    return /* html */ `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <title>CodeLlamas</title>
        <style>
          body { font-family: var(--vscode-font-family); padding: 12px; }
          button {
            background-color: #8ecbff;
            border: none;
            padding: 10px 14px;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
          }
          button:hover { background-color: #6bbcff; }
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
          body { font-family: var(--vscode-font-family); padding: 16px; }
          .header { text-align: center; margin-bottom: 20px; }
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
          <h1>Generating Code Smell Activity</h1>
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
        </script>
      </body>
      </html>
    `;
  }
}
