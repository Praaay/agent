import * as vscode from 'vscode';
import WebSocket from 'ws';

interface ErrorContext {
    error_type: string;
    error_message: string;
    file_path: string;
    line_number: number;
    severity: string;
    timestamp: string;
}

interface FixSuggestion {
    title: string;
    description: string;
    code_snippet: string;
    confidence_score: number;
    agent_source: string;
    explanation?: string;
}

interface BugfreeResponse {
    suggestions: FixSuggestion[];
    session_id?: string;
    processing_time?: number;
}

class BugfreeProvider implements vscode.TreeDataProvider<BugfreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<BugfreeItem | undefined | null | void> = new vscode.EventEmitter<BugfreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<BugfreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private currentErrors: ErrorContext[] = [];
    private currentSuggestions: FixSuggestion[] = [];
    private ws: WebSocket | null = null;
    private isConnected = false;

    constructor() {
        this.connectToBugfree();
    }

    private connectToBugfree() {
        const config = vscode.workspace.getConfiguration('bugfree');
        const host = config.get<string>('serverHost', 'localhost');
        const port = config.get<number>('serverPort', 8003);

        try {
            this.ws = new WebSocket(`ws://${host}:${port}`);
            
            this.ws.on('open', () => {
                this.isConnected = true;
                vscode.window.showInformationMessage('Connected to Bugfree system');
                this.refresh();
            });

            this.ws.on('message', (data: WebSocket.Data) => {
                try {
                    const message = JSON.parse(data.toString());
                    this.handleBugfreeMessage(message);
                } catch (error) {
                    console.error('Error parsing Bugfree message:', error);
                }
            });

            this.ws.on('close', () => {
                this.isConnected = false;
                vscode.window.showWarningMessage('Disconnected from Bugfree system');
                this.refresh();
            });

            this.ws.on('error', (error: Error) => {
                console.error('WebSocket error:', error);
                vscode.window.showErrorMessage('Failed to connect to Bugfree system');
            });

        } catch (error) {
            console.error('Error connecting to Bugfree:', error);
        }
    }

    private handleBugfreeMessage(message: any) {
        if (message.type === 'error_detected') {
            this.currentErrors.push(message.error);
            this.refresh();
        } else if (message.type === 'suggestions_ready') {
            this.currentSuggestions = message.suggestions || [];
            this.refresh();
        }
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: BugfreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: BugfreeItem): Promise<BugfreeItem[]> {
        if (!element) {
            // Root level - show connection status and errors
            const items: BugfreeItem[] = [];
            
            // Connection status
            const statusItem = new BugfreeItem(
                this.isConnected ? '🟢 Connected' : '🔴 Disconnected',
                vscode.TreeItemCollapsibleState.None
            );
            statusItem.tooltip = this.isConnected ? 'Connected to Bugfree system' : 'Not connected to Bugfree system';
            items.push(statusItem);

            // Current errors
            if (this.currentErrors.length > 0) {
                const errorsItem = new BugfreeItem(
                    `🐛 Current Errors (${this.currentErrors.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed
                );
                errorsItem.contextValue = 'errors';
                items.push(errorsItem);
            }

            // Suggestions
            if (this.currentSuggestions.length > 0) {
                const suggestionsItem = new BugfreeItem(
                    `💡 Fix Suggestions (${this.currentSuggestions.length})`,
                    vscode.TreeItemCollapsibleState.Collapsed
                );
                suggestionsItem.contextValue = 'suggestions';
                items.push(suggestionsItem);
            }

            return Promise.resolve(items);
        } else if (element.contextValue === 'errors') {
            // Error items
            return Promise.resolve(this.currentErrors.map((error, index) => {
                const errorItem = new BugfreeItem(
                    `${error.error_type}: ${error.error_message.substring(0, 50)}...`,
                    vscode.TreeItemCollapsibleState.None
                );
                errorItem.tooltip = `${error.file_path}:${error.line_number}\n${error.error_message}`;
                errorItem.contextValue = 'error';
                errorItem.command = {
                    command: 'bugfree.showErrorDetails',
                    title: 'Show Error Details',
                    arguments: [error]
                };
                return errorItem;
            }));
        } else if (element.contextValue === 'suggestions') {
            // Suggestion items
            return Promise.resolve(this.currentSuggestions.map((suggestion, index) => {
                const suggestionItem = new BugfreeItem(
                    `${suggestion.title} (${Math.round(suggestion.confidence_score * 100)}%)`,
                    vscode.TreeItemCollapsibleState.None
                );
                suggestionItem.tooltip = `${suggestion.description}\n\nAgent: ${suggestion.agent_source}`;
                suggestionItem.contextValue = 'suggestion';
                suggestionItem.command = {
                    command: 'bugfree.showSuggestionDetails',
                    title: 'Show Suggestion Details',
                    arguments: [suggestion]
                };
                return suggestionItem;
            }));
        }

        return Promise.resolve([]);
    }

    async startSystem(): Promise<void> {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify({ type: 'start_system' }));
            vscode.window.showInformationMessage('Starting Bugfree system...');
        } else {
            vscode.window.showErrorMessage('Not connected to Bugfree system');
        }
    }

    async stopSystem(): Promise<void> {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify({ type: 'stop_system' }));
            vscode.window.showInformationMessage('Stopping Bugfree system...');
        }
    }

    async applyFix(suggestion: FixSuggestion): Promise<void> {
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'apply_fix',
                suggestion: suggestion
            }));
            vscode.window.showInformationMessage(`Applying fix: ${suggestion.title}`);
        }
    }

    async explainFix(suggestion: FixSuggestion): Promise<void> {
        const explanation = suggestion.explanation || 'No explanation available';
        const panel = vscode.window.createWebviewPanel(
            'bugfreeExplanation',
            `Fix Explanation: ${suggestion.title}`,
            vscode.ViewColumn.One,
            {}
        );

        panel.webview.html = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Fix Explanation</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }
                    .title { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
                    .description { margin-bottom: 15px; color: #666; }
                    .code { background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: 'Courier New', monospace; }
                    .explanation { margin-top: 15px; }
                    .agent { color: #007acc; font-weight: bold; }
                    .confidence { color: #28a745; font-weight: bold; }
                </style>
            </head>
            <body>
                <div class="title">${suggestion.title}</div>
                <div class="description">${suggestion.description}</div>
                <div class="code">${suggestion.code_snippet}</div>
                <div class="explanation">${explanation}</div>
                <div style="margin-top: 20px;">
                    <span class="agent">Agent: ${suggestion.agent_source}</span> | 
                    <span class="confidence">Confidence: ${Math.round(suggestion.confidence_score * 100)}%</span>
                </div>
            </body>
            </html>
        `;
    }

    dispose(): void {
        if (this.ws) {
            this.ws.close();
        }
    }
}

class BugfreeItem extends vscode.TreeItem {
    public tooltip?: string;
    public contextValue?: string;
    public command?: vscode.Command;

    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(label, collapsibleState);
    }
}

export function activate(context: vscode.ExtensionContext) {
    const bugfreeProvider = new BugfreeProvider();
    
    // Register tree data provider
    const errorTreeView = vscode.window.createTreeView('bugfreeErrorPanel', {
        treeDataProvider: bugfreeProvider
    });
    
    const suggestionsTreeView = vscode.window.createTreeView('bugfreeSuggestionsPanel', {
        treeDataProvider: bugfreeProvider
    });

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('bugfree.startSystem', () => {
            bugfreeProvider.startSystem();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bugfree.stopSystem', () => {
            bugfreeProvider.stopSystem();
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bugfree.analyzeError', () => {
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                const position = editor.selection.active;
                const line = position.line + 1;
                const file = editor.document.fileName;
                
                // Send error analysis request
                if (bugfreeProvider['ws'] && bugfreeProvider['isConnected']) {
                    bugfreeProvider['ws'].send(JSON.stringify({
                        type: 'analyze_error',
                        file: file,
                        line: line
                    }));
                    vscode.window.showInformationMessage('Analyzing error...');
                } else {
                    vscode.window.showErrorMessage('Not connected to Bugfree system');
                }
            } else {
                vscode.window.showErrorMessage('No active editor');
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bugfree.applyFix', (suggestion: FixSuggestion) => {
            bugfreeProvider.applyFix(suggestion);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bugfree.explainFix', (suggestion: FixSuggestion) => {
            bugfreeProvider.explainFix(suggestion);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bugfree.ignoreError', (error: ErrorContext) => {
            vscode.window.showInformationMessage(`Ignored error: ${error.error_message}`);
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bugfree.showErrorDetails', (error: ErrorContext) => {
            const panel = vscode.window.createWebviewPanel(
                'bugfreeErrorDetails',
                `Error Details: ${error.error_type}`,
                vscode.ViewColumn.One,
                {}
            );

            panel.webview.html = `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Error Details</title>
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }
                        .error-type { color: #dc3545; font-weight: bold; font-size: 18px; }
                        .error-message { margin: 10px 0; padding: 10px; background: #f8d7da; border-radius: 4px; }
                        .file-info { color: #007acc; margin: 10px 0; }
                        .timestamp { color: #666; font-size: 12px; }
                    </style>
                </head>
                <body>
                    <div class="error-type">${error.error_type}</div>
                    <div class="error-message">${error.error_message}</div>
                    <div class="file-info">File: ${error.file_path}:${error.line_number}</div>
                    <div class="timestamp">Detected: ${error.timestamp}</div>
                </body>
                </html>
            `;
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('bugfree.showSuggestionDetails', (suggestion: FixSuggestion) => {
            bugfreeProvider.explainFix(suggestion);
        })
    );

    // Auto-start if configured
    const config = vscode.workspace.getConfiguration('bugfree');
    if (config.get<boolean>('autoStart', false)) {
        global.setTimeout(() => {
            bugfreeProvider.startSystem();
        }, 1000);
    }

    // Cleanup on deactivate
    context.subscriptions.push({
        dispose: () => {
            bugfreeProvider.dispose();
        }
    });
}

export function deactivate() {} 