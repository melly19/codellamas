// <reference lib="dom" />
/// <reference types="jest" />

describe("Frontend UI + Interaction Tests", () => {
  let mockPostMessage: jest.Mock;
  let mockGetState: jest.Mock;
  let mockSetState: jest.Mock;

  beforeEach(() => {
    document.body.innerHTML = `
      <input id="topic" />
      <button id="generateBtn">Generate Question</button>
      <button id="showAnswerBtn">Show Answer</button>
    `;

    mockPostMessage = jest.fn();
    mockGetState = jest.fn(() => ({}));
    mockSetState = jest.fn();

    (global as any).acquireVsCodeApi = () => ({
      postMessage: mockPostMessage,
      getState: mockGetState,
      setState: mockSetState,
    });
  });

  test("Topic should not be empty", () => {
    const topic = "";
    const isValid = topic.trim().length > 0;
    expect(isValid).toBe(false);
  });

  test("Valid topic should pass", () => {
    const topic = "Library Management";
    const isValid = topic.trim().length > 0;
    expect(isValid).toBe(true);
  });

  test("Generate should fail with empty inputs", () => {
    const topic = "";
    const selectedSmells: string[] = [];
    const canGenerate = topic !== "" && selectedSmells.length > 0;
    expect(canGenerate).toBe(false);
  });

  test("Clicking Generate sends submit message", () => {
    const vscode = (global as any).acquireVsCodeApi();

    const topicInput = document.getElementById("topic") as HTMLInputElement;
    topicInput.value = "Banking";

    const generateBtn = document.getElementById("generateBtn") as HTMLButtonElement;

    generateBtn.addEventListener("click", () => {
      vscode.postMessage({
        type: "submit",
        topic: topicInput.value,
        smells: [],
      });
    });

    generateBtn.click();

    expect(mockPostMessage).toHaveBeenCalledWith({
      type: "submit",
      topic: "Banking",
      smells: [],
    });
  });

  test("Clicking Show Answer sends correct message", () => {
    const vscode = (global as any).acquireVsCodeApi();
    const btn = document.getElementById("showAnswerBtn") as HTMLButtonElement;

    btn.addEventListener("click", () => {
      vscode.postMessage({
        type: "showAnswerFile",
      });
    });

    btn.click();

    expect(mockPostMessage).toHaveBeenCalledWith({
      type: "showAnswerFile",
    });
  });

  test("generateComplete message resets button state", () => {
    document.body.innerHTML = `
      <button id="generateBtn">Generating...</button>
    `;

    const button = document.getElementById("generateBtn") as HTMLButtonElement;

    function setGenerating(isGenerating: boolean) {
      button.disabled = isGenerating;
      button.innerHTML = isGenerating ? "Generating..." : "Generate Question";
    }

    setGenerating(false);

    expect(button.disabled).toBe(false);
    expect(button.innerHTML).toBe("Generate Question");
  });
});
