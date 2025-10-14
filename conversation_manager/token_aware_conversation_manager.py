from typing import List, Dict, Any, Optional, Callable
import tiktoken
from dataclasses import dataclass
from enum import Enum
import json

from conversation_manager.base_conversation_manager import BaseConversationManager
from common.models import Message


class OverflowStrategy(Enum):
    """Strategy for handling token overflow."""

    DROP_OLDEST = "drop_oldest"
    SUMMARIZE = "summarize"
    TRUNCATE_MIDDLE = "truncate_middle"


@dataclass
class TokenUsage:
    total_tokens: int
    available_tokens: int
    message_count: int


class TokenAwareConversationManager(BaseConversationManager):
    """Manages conversation history with token-aware overflow handling."""

    def __init__(
        self,
        max_tokens: int = 120000,
        model: str = "gpt-3.5-turbo",
        overflow_strategy: OverflowStrategy = OverflowStrategy.DROP_OLDEST,
        reserve_tokens: int = 500,  # Reserve for system messages and response
        summarizer_func: Optional[Callable[[List[Message]], str]] = None,
    ):
        """
        Initialize the conversation manager.

        Args:
            max_tokens: Maximum token limit for the conversation
            model: Model name for token encoding
            overflow_strategy: Strategy to handle token overflow
            reserve_tokens: Tokens to reserve for system messages and response
            summarizer_func: Function to summarize messages when using SUMMARIZE strategy
        """
        self.max_tokens = max_tokens
        self.model = model
        self.overflow_strategy = overflow_strategy
        self.reserve_tokens = reserve_tokens
        self.summarizer_func = summarizer_func

        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")

        # Conversation state
        self.messages: List[Message] = []
        self.total_tokens = 0
        self.system_message: Optional[Message] = None

    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation with token management.

        Args:
            message: Message to add to the conversation
        """
        # Count tokens for the new message
        message_tokens = self.count_message_tokens(message)

        # Store token count in message (now that it has the field)
        if message.token_count is None:
            message.token_count = message_tokens

        # Add message and update total
        self.messages.append(message)
        self.total_tokens += message_tokens

        # Handle overflow if necessary
        self._handle_overflow()

    def fetch_conversation(self, window_size: int = 20) -> List[Message]:
        """
        Fetch conversation messages, filtered and limited by window size.

        Args:
            window_size: Maximum number of messages to return

        Returns:
            List of messages within the window size, excluding system and tool messages
        """
        # Filter out system and tool messages (keep user and assistant)
        filtered_messages = [
            msg for msg in self.messages if msg.role not in ["system", "tool"]
        ]

        # Return the most recent messages within window size
        return filtered_messages[-window_size:]

    def finalize(self) -> None:
        """
        Placeholder for conversation persistence.
        Implementation can be added based on specific storage requirements.
        """
        # TODO: Implement persistence logic (e.g., save to file, database)
        pass

    def count_message_tokens(self, message: Message) -> int:
        """
        Count tokens in a message using tiktoken.

        Args:
            message: Message to count tokens for

        Returns:
            Number of tokens in the message
        """
        # Use cached count if available
        if message.token_count is not None:
            return message.token_count

        # Count tokens in message content
        content_tokens = len(self.encoding.encode(message.content))

        # Add overhead for role and formatting (approximate)
        role_tokens = len(self.encoding.encode(message.role))
        formatting_overhead = 4  # Approximate overhead for message structure

        total_tokens = content_tokens + role_tokens + formatting_overhead

        return total_tokens

    def get_token_usage(self) -> TokenUsage:
        """
        Get current token usage statistics.

        Returns:
            TokenUsage object with current statistics
        """
        available_tokens = max(
            0, self.max_tokens - self.total_tokens - self.reserve_tokens
        )

        return TokenUsage(
            total_tokens=self.total_tokens,
            available_tokens=available_tokens,
            message_count=len(self.messages),
        )

    def _handle_overflow(self) -> None:
        """
        Handle token overflow based on the configured strategy.
        """
        if self.total_tokens + self.reserve_tokens <= self.max_tokens:
            return

        # Calculate target tokens (leave room for reserve)
        target_tokens = self.max_tokens - self.reserve_tokens

        if self.overflow_strategy == OverflowStrategy.DROP_OLDEST:
            self._drop_oldest_messages(target_tokens)
        elif self.overflow_strategy == OverflowStrategy.SUMMARIZE:
            self._summarize_conversation(target_tokens)
        elif self.overflow_strategy == OverflowStrategy.TRUNCATE_MIDDLE:
            self._truncate_middle_messages(target_tokens)

    def _drop_oldest_messages(self, target_tokens: int) -> None:
        """
        Drop oldest messages until under token limit.

        Args:
            target_tokens: Target token count to reach
        """
        while self.total_tokens > target_tokens and self.messages:
            oldest_message = self.messages.pop(0)
            removed_tokens = self.count_message_tokens(oldest_message)
            self.total_tokens -= removed_tokens

    def _summarize_conversation(self, target_tokens: int) -> None:
        """
        Summarize older messages to reduce token count.

        Args:
            target_tokens: Target token count to reach
        """
        if not self.summarizer_func or len(self.messages) < 4:
            # Fallback to dropping oldest if no summarizer or too few messages
            self._drop_oldest_messages(target_tokens)
            return

        # Keep recent messages, summarize older ones
        messages_to_keep: List[Message] = []
        messages_to_summarize: List[Message] = []

        # Work backwards from newest messages
        temp_tokens = 0
        for message in reversed(self.messages):
            message_tokens = self.count_message_tokens(message)
            if temp_tokens + message_tokens < target_tokens // 2:  # Keep recent half
                messages_to_keep.insert(0, message)
                temp_tokens += message_tokens
            else:
                messages_to_summarize.insert(0, message)

        if messages_to_summarize:
            try:
                summary = self.summarizer_func(messages_to_summarize)
                summary_message = Message(
                    role="system",
                    content=f"[Conversation Summary]: {summary}",
                    metadata={
                        "type": "summary",
                        "summarized_count": len(messages_to_summarize),
                    },
                )

                # Replace old messages with summary
                self.messages = [summary_message] + messages_to_keep
                self._recalculate_tokens()

            except Exception:
                # Fallback to dropping oldest if summarization fails
                self._drop_oldest_messages(target_tokens)

    def _truncate_middle_messages(self, target_tokens: int) -> None:
        """
        Keep first few and last few messages, remove middle ones.

        Args:
            target_tokens: Target token count to reach
        """
        if len(self.messages) <= 4:
            self._drop_oldest_messages(target_tokens)
            return

        # Keep first 2 and last 2 messages
        first_messages = self.messages[:2]
        last_messages = self.messages[-2:]

        self.messages = first_messages + last_messages
        self._recalculate_tokens()

    def _recalculate_tokens(self) -> None:
        """
        Recalculate total token count.
        """
        self.total_tokens = sum(self.count_message_tokens(msg) for msg in self.messages)
