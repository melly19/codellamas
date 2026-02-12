// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';

import { ActivityWebviewProvider } from './activityWebviewProvider';
import { buildReviewPayload } from "./buildReviewPayload";

// This method is called when your extension is activated
export function activate(context: vscode.ExtensionContext) {

	console.log('Congratulations, your extension "code-llamas" is now active!');

	// -----------------------------
	// Activity view (unchanged)
	// -----------------------------
	const provider = new ActivityWebviewProvider(context);

	context.subscriptions.push(
		vscode.window.registerWebviewViewProvider(
			ActivityWebviewProvider.viewType,
			provider
		)
	);

	// -----------------------------
	// Hello World command (unchanged)
	// -----------------------------
	const helloWorldDisposable = vscode.commands.registerCommand(
		'code-llamas.helloWorld',
		() => {
			vscode.window.showInformationMessage('Hello World from code llamas!');
		}
	);

	context.subscriptions.push(helloWorldDisposable);

	// =====================================================
	//  Submit Code command
	// =====================================================
	const submitCodeDisposable = vscode.commands.registerCommand(
		"code-llamas.submitCode",
		async () => {
			const payload = await buildReviewPayload(provider);
			console.log("Review payload:", JSON.stringify(payload, null, 2));
			if (!payload) return;

			try {
				const response = await fetch("http://localhost:8000/review", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(payload),
				});
				if (!response.ok) throw new Error(`Backend error: ${response.statusText}`);

				const reviewResultsRaw = await response.json() as Record<string, any>;
				// Parse the nested feedback JSON
				const feedback = JSON.parse(reviewResultsRaw.feedback);

				// Build a string to show in the editor
				const content = `=== Code Review Feedback ===
Functional Correctness: ${feedback.functional_correctness_assessment}
Rating: ${feedback.rating}

Maven Verification: ${JSON.stringify(reviewResultsRaw.maven_verification, null, 2)}
`;

				// Create a new untitled document
				const doc = await vscode.workspace.openTextDocument({
					content,
					language: "markdown", // optional, gives nice formatting
				});

				// Show it in a new editor tab
				await vscode.window.showTextDocument(doc, { preview: false });



				// provider.revealReviewPanel();
				// provider.postMessage({ type: "reviewResponse", ...reviewResults });
				// console.log("Response status:", response.status);
				// console.log(reviewResults);
				vscode.window.showInformationMessage("Code submitted successfully!");
			} catch (err: any) {
				vscode.window.showErrorMessage("Failed to submit code: " + String(err));
			}
		}
	);

	context.subscriptions.push(submitCodeDisposable);

	// =====================================================
	// Status bar button
	// =====================================================
	const submitButton = vscode.window.createStatusBarItem(
		vscode.StatusBarAlignment.Right,
		100
	);

	submitButton.text = '$(cloud-upload) Submit';
	submitButton.tooltip = 'Submit current file to Code Llamas';
	submitButton.command = 'code-llamas.submitCode';

	submitButton.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
	submitButton.show();

	context.subscriptions.push(submitButton);
}

// This method is called when your extension is deactivated
export function deactivate() { }
