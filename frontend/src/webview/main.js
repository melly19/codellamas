const vscode = acquireVsCodeApi();

window.addEventListener("DOMContentLoaded", () => {
  const generateBtn = document.getElementById("generateBtn");
  const submitBtn = document.getElementById("submitBtn");
  const output = document.getElementById("questionList");

  if (!generateBtn || !output) {
    console.error("Required elements not found");
    return;
  }

 
  generateBtn.addEventListener("click", () => {
    vscode.postMessage({ command: "generateExercise" });
  });

 
  if (submitBtn) {
    submitBtn.addEventListener("click", () => {
      vscode.postMessage({ command: "submitExercise" });
    });
  }

  
  window.addEventListener("message", (event) => {
    const message = event.data;

    if (message.command === "renderQuestions") {
      if (!message.questions || message.questions.length === 0) {
        output.innerHTML = `<li>No questions generated yet.</li>`;
        return;
      }

      output.innerHTML = message.questions
        .map(
          () => `
<li class="exercise">
  <h3>Refactor Long Method – Banking Service</h3>

  <p><strong>Problem context:</strong><br/>
  We'll create a simple banking system that manages accounts and performs basic banking operations.</p>

  <p><strong>Refactoring Task:</strong><br/>
  Identify and refactor the long method code smell in the banking service.</p>

  <p><strong>Constraint:</strong></p>
  <ul class="constraints">
    <li>Behaviour must remain unchanged</li>
    <li>Only refactor the long method</li>
    <li>Maintain all existing test cases</li>
    <li>Keep all tests passing</li>
  </ul>

  <p class="hint">
    The Java file has been generated in the Explorer.<br/>
    Open <code>BankingService.java</code> and refactor directly.
  </p>
</li>
          `
        )
        .join("");
    }
  });
});
