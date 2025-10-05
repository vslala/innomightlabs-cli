# Innomight Labs CLI

A rich terminal-based CLI assistant for developers, similar to Claude Code but with faster inference and accuracy.

## Features

- Rich terminal interface with color formatting
- Multi-line command input with history
- Command processor with extensible commands
- Support for slash commands (e.g., `/help`, `/version`)

## Coming Soon

- Tool calling functionality
- Memory augmentation for context retention
- Filesystem for conversation storage
- Task scheduling
- Sleeping agent hooks for automated updates

## Installation

1. Ensure you have Python 3.13+ installed
2. Clone the repository
3. Install dependencies with `uv pip install prompt_toolkit rich`

## Usage

Run the CLI application:

```bash
python main.py
```

### Available Commands

- `/help` - Display available commands
- `/version` - Show current version
- `/exit` - Exit the application

## Development

This project follows these guidelines:

- Use `uv` as the package manager
- Prioritize clean code over performance
- Update CLAUDE.md with progress on features