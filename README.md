# Bugfree Multi-Agent Debugging System

A sophisticated multi-agent debugging system that uses specialized AI agents to diagnose, explain, and suggest fixes for runtime errors through MCP (Model Context Protocol) integration.

## 🚀 Features

### Core MVP (Phase 1) ✅

- **Log Agent**: Monitors runtime logs and extracts error information
- **Code Agent**: Analyzes codebase context and suggests fixes
- **Orchestrator Agent**: Coordinates between agents and ranks suggestions
- **MCP Integration**: Seamless communication between agents
- **Real-time Error Processing**: Instant error analysis and fix suggestions
- **Rich CLI Interface**: Beautiful terminal interface with progress indicators
- **VS Code Extension**: Sidebar UI with Apply/Explain/Ignore functionality
- **Real-time Runtime Monitoring**: Automatic error detection from running Python processes
- **WebSocket Bridge**: Communication between VS Code and Python backend

### Planned Features (Future Phases)

- **Knowledge Agent**: StackOverflow and GitHub integration
- **Test Agent**: Automated fix verification and testing
- **Memory Agent**: Project-wide error history and learning
- **Multi-language Support**: JavaScript, Java, and more
- **Web Dashboard**: Cross-project monitoring and analytics

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Log Agent     │    │  Code Agent     │    │  Orchestrator   │
│                 │    │                 │    │     Agent       │
│ • Monitors logs │    │ • Reads code    │    │ • Coordinates   │
│ • Extracts      │    │ • Suggests      │    │ • Ranks fixes   │
│   errors        │    │   fixes         │    │ • Manages       │
│ • Broadcasts    │    │ • Analyzes      │    │   sessions      │
│   to others     │    │   context       │    │ • Returns top   │
└─────────────────┘    └─────────────────┘    │   suggestions   │
         │                       │            └─────────────────┘
         └───────────────────────┘                       │
                    MCP Protocol                        │
                                                        │
                                              ┌─────────────────┐
                                              │   IDE Panel     │
                                              │                 │
                                              │ • Shows errors  │
                                              │ • Lists fixes   │
                                              │ • Apply/Explain │
                                              │ • Ignore        │
                                              └─────────────────┘
```

## 📦 Installation

### Prerequisites

- Python 3.11 or higher
- uv package manager

### Quick Start

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd bugfree
   ```

2. **Install dependencies**

   ```bash
   uv sync
   ```

3. **Run the system**
   ```bash
   python main.py start
   ```

## 🎯 Usage

### Basic Commands

```bash
# Start the Bugfree system
python main.py start

# Stop the system
python main.py stop

# Show system status
python main.py status

# Analyze a specific error
python main.py analyze "NameError: name 'undefined_variable' is not defined" --file example.py --line 10

# Run a demo with sample errors
python main.py demo
```

### Example Workflow

1. **Start the system**

   ```bash
   python main.py start
   ```

2. **Analyze an error**

   ```bash
   python main.py analyze "ModuleNotFoundError: No module named 'requests'" --file api_client.py --line 5
   ```

3. **View suggestions**
   The system will display:
   - Ranked list of fix suggestions
   - Confidence scores
   - Code snippets
   - Explanations from different agents

## 🔧 Configuration

### Agent Configuration

Each agent can be configured through environment variables or configuration files:

```bash
# Log Agent
LOG_AGENT_MONITOR_DIRS="/var/log,./logs,./tmp"
LOG_AGENT_FILE_PATTERNS="*.log,*.txt,*.err"

# Code Agent
CODE_AGENT_PROJECT_ROOT="./"
CODE_AGENT_CACHE_SIZE=1000

# Orchestrator
ORCHESTRATOR_MAX_SUGGESTIONS=3
ORCHESTRATOR_CONFIDENCE_THRESHOLD=0.6
```

## 🧪 Testing

### Run Tests

```bash
uv run pytest
```

### Run Demo

```bash
python main.py demo
```

## 📊 Error Types Supported

The system currently supports analysis of:

- **Syntax Errors**: Missing parentheses, brackets, quotes
- **Type Errors**: Incorrect object types, callable issues
- **Attribute Errors**: Missing object attributes
- **Import Errors**: Missing modules, import issues
- **File Errors**: File not found, permission issues
- **Index Errors**: List/array index out of range
- **Key Errors**: Dictionary key errors
- **Runtime Errors**: General runtime exceptions

## 🔌 MCP Integration

The system uses MCP (Model Context Protocol) for agent communication:

### Message Types

- `analyze_error`: Request error analysis from agents
- `get_code_context`: Request code context information
- `suggest_fixes`: Request fix suggestions
- `process_error`: Orchestrator processes error with all agents

### Agent Communication Flow

1. **Log Agent** detects error → broadcasts to other agents
2. **Code Agent** receives error → analyzes code context → suggests fixes
3. **Orchestrator** collects all suggestions → ranks them → returns top results

## 🛠️ Development

### Project Structure

```
bugfree/
├── agents/           # Agent implementations
│   ├── log_agent.py
│   └── code_agent.py
├── core/             # Core system components
│   └── orchestrator.py
├── models/           # Data models
│   ├── error_models.py
│   └── mcp_models.py
├── mcp/              # MCP integration
│   ├── client.py
│   └── server.py
├── utils/            # Utility functions
│   ├── file_utils.py
│   └── log_utils.py
└── __init__.py
```

### Adding New Agents

1. Create agent class in `agents/` directory
2. Implement required MCP handlers
3. Register with orchestrator
4. Update configuration

### Example Agent Template

```python
class NewAgent:
    def __init__(self, name: str = "new_agent"):
        self.name = name
        self.mcp_client = MCPClient(name)
        self.mcp_server = SimpleMCPServer(name)

        # Register handlers
        self.mcp_server.register_handler("analyze_error", self._handle_error_analysis)

    async def start(self):
        print(f"New Agent {self.name} started")

    async def stop(self):
        await self.mcp_client.close()
```

## 🚧 Roadmap

### Phase 1 - Core MVP ✅

- [x] Log Agent implementation
- [x] Code Agent implementation
- [x] Orchestrator Agent implementation
- [x] MCP integration
- [x] CLI interface
- [x] Error parsing and analysis
- [x] Real-time runtime error monitoring
- [x] VS Code extension with sidebar UI
- [x] WebSocket communication bridge
- [x] Apply/Explain/Ignore functionality

### Phase 2 - External Knowledge (2-3 weeks)

- [ ] Knowledge Agent (StackOverflow/GitHub)
- [ ] External resource integration
- [ ] Enhanced suggestion ranking

### Phase 3 - Verification & Sandbox (2-3 weeks)

- [ ] Test Agent implementation
- [ ] Automated fix verification
- [ ] Sandboxed execution
- [ ] Safety checks

### Phase 4 - Memory & History (2 weeks)

- [ ] Memory Agent implementation
- [ ] Project-wide error history
- [ ] Learning from past fixes
- [ ] Pattern recognition

### Phase 5 - Advanced Features (3-4 weeks)

- [ ] Multi-language support
- [ ] Web dashboard
- [ ] Auto-learning capabilities
- [ ] Natural language requests

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [uv](https://github.com/astral-sh/uv) for fast Python package management
- Uses [MCP](https://modelcontextprotocol.io/) for agent communication
- Rich CLI interface powered by [Rich](https://github.com/Textualize/rich)
- CLI framework by [Typer](https://typer.tiangolo.com/)

## 📞 Support

For questions, issues, or contributions:

- Open an issue on GitHub
- Join our Discord community
- Check the documentation

---

**Bugfree** - Making debugging smarter, one error at a time! 🐛✨
