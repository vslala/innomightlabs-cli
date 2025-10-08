# Innomight Labs CLI

A rich terminal-based CLI assistant for developers, similar to Claude Code but with faster inference and accuracy.

## Features

- Rich terminal interface with color formatting and Innomight Labs branding
- Multi-line command input with history and continuation prompts
- Command processor with extensible slash commands
- Professional development environment with dependency injection
- Persistent conversation storage capabilities

## Project Structure

```
.
├── main.py                    # Application entry point
├── command_processor.py       # Command processing logic
├── container.py              # Dependency injection container
├── tools/                    # Tool implementations
│   ├── send_message.py       # Message sending tool
│   └── file_system_tool.py   # File system operations
├── conversation_manager/     # Conversation handling
├── agents/                   # AI agent implementations
├── common/                   # Shared utilities
├── pyproject.toml           # Project configuration
├── README.md                # This file
├── CLAUDE.md                # Development guidelines
└── PROJECT_UPDATES.md       # Progress tracking
```

## Current Capabilities

### Available Commands

- `/help` - Display available commands and usage instructions
- `/version` - Show current version (v0.1.0)
- `/exit` - Exit the application gracefully

### Rich Interface Features

- Professional welcome banner with Innomight Labs branding
- Multi-line input with smart continuation prompts
- Command history navigation
- Color-coded output and formatting

## Installation

### Prerequisites

- Python 3.13+
- `uv` package manager

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

3. Run the application:
   ```bash
   python main.py
   ```

## Future Roadmap

### Phase 1: Core AI Integration
- [ ] **Tool Calling System** - Implement extensible tool calling functionality
- [ ] **Memory Augmentation** - Add GPT memory features for context retention across sessions
- [ ] **Enhanced Command Processing** - Expand command system with more developer utilities

### Phase 2: Persistence & Storage
- [ ] **Conversation Filesystem** - Persistent storage for conversations and context
- [ ] **Session Management** - Save and restore work sessions
- [ ] **Vector-Based Semantic Retrieval** - Intelligent context management using vector embeddings for semantic search and retrieval
- [ ] **Context Search** - Search through conversation history

### Phase 3: Automation & Intelligence
- [ ] **Task Scheduling** - Automated task execution and reminders
- [ ] **Sleeping Agent Hooks** - Background processes for automatic updates
- [ ] **Code Analysis Integration** - Real-time code quality and suggestion features

### Phase 4: Advanced Features
- [ ] **Multi-Agent Collaboration** - Multiple AI agents working together
- [ ] **Plugin System** - Extensible plugin architecture
- [ ] **Web Integration** - Browser-based interface option
- [ ] **Team Collaboration** - Shared workspaces and contexts

## Development Guidelines

- **Package Management**: Use `uv` for all dependency management
- **Code Quality**: Clean, readable code prioritized over performance optimizations
- **Documentation**: Keep CLAUDE.md updated with development progress
- **Architecture**: Utilize dependency injection for maintainable, testable code

## Dependencies

- **prompt-toolkit** (^3.0.52) - Rich terminal interface
- **rich** (^14.1.0) - Beautiful terminal formatting
- **dependency-injector** (^4.48.2) - Dependency injection framework
- **langchain-aws** (^0.2.35) - AI integration capabilities

## Contributing

1. Follow the coding guidelines in CLAUDE.md
2. Update PROJECT_UPDATES.md with progress
3. Ensure all features are properly tested
4. Maintain clean, comment-free code

## License

See LICENSE file for details.

---

**Built by Innomight Labs** - Empowering developers with intelligent CLI tools