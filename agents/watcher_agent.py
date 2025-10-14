"""Agent for analyzing watcher requirements and executing actions."""

import json
import os
import re
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional, cast

from langchain_aws import ChatBedrockConverse
from rich.console import Console
from watchdog.events import FileSystemEvent

from agents.base_agent import BaseAgent
from conversation_manager.base_conversation_manager import BaseConversationManager
from text_embedding.base_text_embedder import BaseTextEmbedder
from tools.file_watcher import WatcherMetadata, file_watcher_manager

console = Console()


class WatcherAgent(BaseAgent):
    """Agent that analyzes watcher requirements and executes file change actions."""

    def __init__(
        self,
        conversation_manager: BaseConversationManager,
        text_embedder: BaseTextEmbedder,
    ):
        self.llm = ChatBedrockConverse(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region_name="us-east-1",
            max_tokens=2048,
            credentials_profile_name=os.getenv("AWS_PROFILE", "searchexpert"),
        )
        self.conversation_manager = conversation_manager
        self.text_embedder = text_embedder

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response (not implemented for this agent)."""
        yield "Streaming not supported for WatcherAgent"

    def send_message(self, user_message: str) -> str:
        """Process user message (not the main interface for this agent)."""
        return str(self.analyze_watch_request(user_message))

    def analyze_watch_request(self, user_request: str) -> Dict[str, Any]:
        """Analyze user request and determine what to watch.

        Args:
            user_request: User's natural language request

        Returns:
            Analysis result dictionary
        """
        system_prompt = """
You are a file watcher analysis agent. Your job is to analyze user requests about watching files and directories, then provide specific recommendations.

Given a user request, analyze it and provide a JSON response with the following structure:
{
    "paths": ["list of paths to watch"],
    "patterns": ["list of file patterns like *.py, *.md"],
    "ignore_patterns": ["patterns to ignore like __pycache__/*, .git/*"],
    "recursive": true/false,
    "action_prompt": "specific prompt to execute when files change",
    "description": "human readable description of what this watcher does"
}

Be specific and practical. If the user mentions:
- "Python files" -> patterns: ["*.py"]
- "documentation" -> patterns: ["*.md", "*.rst", "*.txt"] 
- "ignore cache" -> ignore_patterns: ["__pycache__/*", "*.pyc"]
- "git changes" -> action_prompt should mention analyzing git status
- "tests" -> patterns: ["test_*.py", "*_test.py"]

Always provide actionable action_prompts that describe what should happen when files change.
"""

        try:
            response = self.llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_request},
                ]
            )

            # Extract JSON from response
            response_text = response.content
            if not isinstance(response_text, str):
                response_text = str(response_text)

            # Try to extract JSON from the response
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                try:
                    analysis = json.loads(json_match.group())
                    # Ensure we return the correct type
                    if isinstance(analysis, dict):
                        return analysis
                except json.JSONDecodeError:
                    pass

            # If no valid JSON found, return default structure
            return {
                "paths": ["."],
                "patterns": [],
                "ignore_patterns": ["__pycache__/*", ".git/*"],
                "recursive": True,
                "action_prompt": f"Analyze changes based on: {user_request}",
                "description": f"Watch for changes related to: {user_request}",
            }

        except Exception as e:
            console.print(f"[red]Error analyzing watch request: {e}[/red]")
            return {
                "paths": ["."],
                "patterns": [],
                "ignore_patterns": ["__pycache__/*", ".git/*"],
                "recursive": True,
                "action_prompt": f"Analyze changes based on: {user_request}",
                "description": f"Error in analysis - watch for: {user_request}",
            }

    def execute_action(
        self, metadata: WatcherMetadata, event: FileSystemEvent, execution_agent: Any
    ) -> None:
        """Execute action when file changes are detected.

        Args:
            metadata: Watcher metadata containing action prompt
            event: File system event that triggered the action
            execution_agent: Agent to execute the action prompt
        """
        try:
            # Create context-aware prompt
            # Handle both string and bytes paths
            file_path = event.src_path
            if isinstance(file_path, bytes):
                file_path = file_path.decode("utf-8", errors="replace")

            context_prompt = f"""
{metadata.action_prompt}

File Event Details:
- Event Type: {event.event_type}
- File Path: {file_path}
- Watcher ID: {metadata.watcher_id}
- Description: {metadata.description}

Please analyze this file change and execute the appropriate action.
"""

            console.print(
                f"[blue]Executing action for watcher {metadata.watcher_id}[/blue]"
            )
            result = execution_agent.send_message(context_prompt)

            console.print("[green]Action completed:[/green]")
            console.print(result)

        except Exception as e:
            console.print(f"[red]Error executing action: {e}[/red]")
