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

}

// This method is called when your extension is deactivated
export function deactivate() { }
