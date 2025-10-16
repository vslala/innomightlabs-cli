# Innomight Labs CLI

A rich terminal-based CLI assistant for developers, similar to Claude Code but with faster inference and accuracy.

## Features

- Rich terminal interface with color formatting and Innomight Labs branding
- Multi-line command input with history and continuation prompts
- Command processor with extensible slash commands
- Professional development environment with dependency injection
- Persistent conversation storage capabilities
- 2-agent Re-ACT model for intelligent task delegation

## Project Structure

```
.
├── main.py                    # Application entry point
├── command_processor.py       # Command processing logic
├── container.py              # Dependency injection container
├── tools/                    # Tool implementations
│   ├── file_system_tool.py   # File system operations (read, write, find, search)
│   ├── shell_tool.py         # Shell command execution
│   ├── sub_agent_tools.py    # Multi-agent task delegation
│   ├── memory_tool.py        # Memory and context management
│   └── send_message.py       # Message sending capabilities
├── conversation_manager/     # Conversation handling
│   ├── base_conversation_manager.py
│   ├── sliding_window_conversation_manager.py
│   └── token_aware_conversation_manager.py
├── agents/                   # AI agent implementations
│   ├── base_agent.py         # Abstract agent interface
│   └── plan_act_observe_agent/ # Re-ACT model implementation
├── text_embedding/           # Semantic search and embeddings
├── prompts/                  # System prompts and instructions
├── common/                   # Shared utilities and models
├── pyproject.toml           # Project configuration
├── README.md                # This file
├── CLAUDE.md                # Development guidelines
└── PROJECT_UPDATES.md       # Progress tracking
```

## Architecture

The CLI implements a **2-agent Re-ACT (Plan-Act-Observe) model** for intelligent task execution:

- **Planner Agent**: High-level planning and orchestration using advanced language models
- **Sub-Agent**: Specialized execution agent with file system and shell capabilities
- **Re-ACT Pattern**: Plan → Act → Observe → Finalize workflow for complex tasks
- **Tool-based Architecture**: Modular tools for extensible functionality
- **Dependency Injection**: Clean separation of concerns for maintainable code

## Current Capabilities

### Available Commands

- `/help` - Display available commands and usage instructions
- `/version` - Show current version (v0.1.0)
- `/exit` - Exit the application gracefully

### AI-Powered Features

- **File System Operations**: Read, write, find, and search files with intelligent context
- **Shell Command Execution**: Direct terminal command execution with safety checks
- **Multi-Agent Task Delegation**: Complex tasks automatically split across specialized agents
- **Persistent Conversations**: Context retention across sessions with semantic search
- **Token Usage Tracking**: Real-time monitoring of AI model usage

### Rich Interface Features

- Professional welcome banner with Innomight Labs branding
- Multi-line input with smart continuation prompts
- Command history navigation
- Color-coded output and beautiful diff visualization
- Real-time token usage display in status bar

### Available Tools

- **fs_read** - Read files with line range and formatting options
- **fs_write** - Write, edit, and modify files with multiple editing modes
- **fs_find** - Locate files and directories using flexible filters
- **fs_search** - Search file contents with regex and context support
- **shell_command** - Execute terminal commands safely
- **sub_agent** - Delegate complex tasks to specialized execution agent

## Installation

### Prerequisites

- Python 3.13+
- `uv` package manager
- AWS credentials configured for Bedrock access

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd innomightlabs-cli
   ```

2. Install dependencies:
   ```bash
   uv pip install -e .
   ```

3. Configure AWS credentials:
   ```bash
   export AWS_PROFILE=your-profile-name
   ```

4. Run the application:
   ```bash
   python main.py
   ```

## Future Roadmap

### Phase 1: Core AI Integration
- [x] **Tool Calling System** - Extensible tool calling functionality ✅
- [x] **Multi-Agent Collaboration** - Multiple AI agents working together ✅
- [ ] **Memory Augmentation** - Enhanced GPT memory features for context retention
- [ ] **Enhanced Command Processing** - Expand command system with more developer utilities

### Phase 2: Persistence & Storage
- [x] **Conversation Filesystem** - Persistent storage for conversations and context ✅
- [x] **Vector-Based Semantic Retrieval** - Intelligent context management using embeddings ✅
- [ ] **Session Management** - Save and restore work sessions
- [ ] **Context Search** - Advanced search through conversation history

### Phase 3: Automation & Intelligence
- [ ] **Task Scheduling** - Automated task execution and reminders
- [ ] **Sleeping Agent Hooks** - Background processes for automatic updates
- [ ] **Code Analysis Integration** - Real-time code quality and suggestion features

### Phase 4: Advanced Features
- [ ] **Plugin System** - Extensible plugin architecture
- [ ] **Web Integration** - Browser-based interface option
- [ ] **Team Collaboration** - Shared workspaces and contexts
- [ ] **Advanced Multi-Agent Workflows** - Complex agent orchestration patterns

## Development Guidelines

- **Package Management**: Use `uv` for all dependency management
- **Code Quality**: Clean, readable code prioritized over performance optimizations
- **Documentation**: Keep CLAUDE.md updated with development progress
- **Architecture**: Utilize dependency injection for maintainable, testable code
- **Testing**: Comprehensive testing for all agent interactions and tool usage

## Dependencies

- **prompt-toolkit** (^3.0.52) - Rich terminal interface
- **rich** (^14.1.0) - Beautiful terminal formatting
- **dependency-injector** (^4.48.2) - Dependency injection framework
- **langchain-aws** (^0.2.35) - AI integration capabilities
- **pydantic** - Data validation and modeling

## Contributing

1. Follow the coding guidelines in CLAUDE.md
2. Update PROJECT_UPDATES.md with progress
3. Ensure all features are properly tested
4. Maintain clean, comment-free code
5. Test agent interactions thoroughly before submitting

## License

See LICENSE file for details.
