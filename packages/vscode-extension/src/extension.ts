import * as vscode from 'vscode';
// import * as WebSocket from 'ws';

export function activate(context: vscode.ExtensionContext) {
    console.log('Congratulations, your extension "pcn-ai-ide" is now active!');

    let disposable = vscode.commands.registerCommand('pcn.submitTask', async () => {
        const userInput = await vscode.window.showInputBox({
            prompt: 'Enter your coding task',
            placeHolder: 'e.g., Create a REST API endpoint for user authentication'
        });

        if (userInput) {
            vscode.window.showInformationMessage(`Task submitted: ${userInput}`);
            // Logic to connect to API gateway and submit the task goes here.
        }
    });

    context.subscriptions.push(disposable);
}

export function deactivate() {}
