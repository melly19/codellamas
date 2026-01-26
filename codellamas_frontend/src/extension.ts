// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';

import { ActivityWebviewProvider } from './activityWebviewProvider';

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
	// 🦙 NEW: Submit Code command
	// =====================================================
	const submitCodeDisposable = vscode.commands.registerCommand(
		'code-llamas.submitCode',
		() => {
			const editor = vscode.window.activeTextEditor;

			if (!editor) {
				vscode.window.showWarningMessage('No active editor to submit.');
				return;
			}

			const document = editor.document;

			const payload = {
				fileName: document.fileName,
				language: document.languageId,
				text: document.getText()
			};

			// TODO: replace this with real submission logic
			console.log('Submitting code:', payload);

			vscode.window.showInformationMessage('🦙 Code submitted to Code Llamas!');
			
			// OPTIONAL: send to your webview
			// provider.postMessage?.({ type: 'submitCode', payload });
		}
	);

	context.subscriptions.push(submitCodeDisposable);

	// =====================================================
	// 🦙 NEW: Status bar button
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
export function deactivate() {}
