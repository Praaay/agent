# Bugfree VS Code Extension

A VS Code extension that integrates with the Bugfree Multi-Agent Debugging System to provide real-time error detection and fix suggestions.

## Features

- **Real-time Error Detection**: Automatically detects errors in your Python code
- **Fix Suggestions**: Shows ranked suggestions from multiple AI agents
- **Apply Fixes**: One-click fix application with preview
- **Error History**: Track errors and fixes across your project
- **Agent Insights**: See which AI agent provided each suggestion

## Installation

### Prerequisites

1. **Install the Python Bugfree System**:

   ```bash
   cd /path/to/bugfree
   uv sync
   python main.py start
   ```

2. **Install the VS Code Extension**:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "Bugfree Debugger"
   - Click Install

### Manual Installation

1. **Clone the extension**:

   ```bash
   git clone <repository-url>
   cd vscode-extension
   ```

2. **Install dependencies**:

   ```bash
   npm install
   ```

3. **Build the extension**:

   ```bash
   npm run compile
   ```

4. **Install in VS Code**:
   - Press F5 in VS Code to run the extension in development mode
   - Or package it: `vsce package` and install the .vsix file

## Usage

### Starting the System

1. **Start the Python Backend**:

   ```bash
   python main.py start
   ```

2. **Connect from VS Code**:
   - Open the Bugfree sidebar (🐛 icon in the activity bar)
   - Click "Start Bugfree System" if not already running
   - You should see "🟢 Connected" status

### Analyzing Errors

1. **Automatic Detection**:

   - The system automatically detects runtime errors
   - Errors appear in the "Current Errors" panel

2. **Manual Analysis**:
   - Place cursor on a line with an error
   - Right-click and select "Bugfree: Analyze Current Error"
   - Or use Command Palette: `Bugfree: Analyze Current Error`

### Applying Fixes

1. **View Suggestions**:

   - Click on "Fix Suggestions" in the sidebar
   - Each suggestion shows confidence score and agent source

2. **Apply a Fix**:

   - Right-click on a suggestion
   - Select "Apply Fix" to apply it to your code
   - Or select "Explain Fix" to see detailed explanation

3. **Ignore Errors**:
   - Right-click on an error
   - Select "Ignore Error" to dismiss it

## Configuration

Open VS Code settings and search for "Bugfree" to configure:

- **Server Host**: Host for Bugfree server (default: localhost)
- **Server Port**: Port for Bugfree server (default: 8000)
- **Auto Start**: Automatically start system when opening workspace
- **Max Suggestions**: Maximum number of suggestions to show (default: 3)

## Troubleshooting

### Connection Issues

1. **Check if Python backend is running**:

   ```bash
   python main.py status
   ```

2. **Verify WebSocket server**:

   - Backend should show "WebSocket server started successfully"
   - Check if port 8000 is available

3. **Check VS Code extension logs**:
   - Open Command Palette: `Developer: Show Logs`
   - Select "Extension Host" and look for Bugfree errors

### No Suggestions

1. **Ensure agents are connected**:

   - Check that Log Agent and Code Agent are running
   - Look for connection messages in the backend

2. **Check error format**:
   - Make sure errors are in standard Python format
   - Try manual analysis on a simple error first

## Development

### Building from Source

1. **Clone and setup**:

   ```bash
   git clone <repository-url>
   cd vscode-extension
   npm install
   ```

2. **Development mode**:

   ```bash
   npm run watch
   ```

   Then press F5 in VS Code

3. **Testing**:
   ```bash
   npm test
   ```

### Architecture

The extension communicates with the Python backend via WebSocket:

```
VS Code Extension ←→ WebSocket Server ←→ Orchestrator Agent
                                      ←→ Log Agent
                                      ←→ Code Agent
```

### Key Files

- `src/extension.ts`: Main extension logic
- `package.json`: Extension manifest and configuration
- `resources/`: Icons and assets

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
