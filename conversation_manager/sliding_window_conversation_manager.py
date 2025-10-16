import json
import os
from collections.abc import Iterable

from common.models import Message
from common.utils import ROOT
from conversation_manager.base_conversation_manager import BaseConversationManager


class SlidingWindowConversationManager(BaseConversationManager):
    conversation_file = f"{ROOT}/.krishna/conversation_history.ndjson"

    def __init__(
        self,
        persist_to_file: bool = True,
        conversation_file: str | None = None,
    ) -> None:
        self.messages: list[Message] = []
        self._persisted_count = 0
        self._decoder = json.JSONDecoder()
        self._persist_to_file = persist_to_file
        self._conversation_file = conversation_file or self.conversation_file

        if not self._persist_to_file:
            return

        if not os.path.exists(f"{ROOT}/.krishna/{self._conversation_file}"):
            return

        with open(self._conversation_file, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                for payload in self._decode_ndjson_line(raw_line):
                    self.messages.append(Message.model_validate(payload))

        self._persisted_count = len(self.messages)
        if self.messages:
            self._rewrite_history_file()

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def fetch_conversation(self, window_size: int = 50) -> list[Message]:
        filtered_messages = [msg for msg in self.messages if msg.role not in {"system"}]
        return filtered_messages[-window_size:]

    def finalize(self) -> None:
        if not self._persist_to_file:
            return

        if self._persisted_count >= len(self.messages):
            return

        new_messages = self.messages[self._persisted_count :]
        if not new_messages:
            return

        serialized: list[str] = [
            message.model_dump_json()
            for message in list(filter(lambda msg: msg.role != "system", new_messages))
        ]

        file_exists = os.path.exists(self._conversation_file)
        needs_leading_newline = False
        if file_exists and os.path.getsize(self._conversation_file) > 0:
            with open(self._conversation_file, "rb") as reader:
                reader.seek(-1, os.SEEK_END)
                needs_leading_newline = reader.read(1) not in {b"\n", b"\r"}

        with open(self._conversation_file, "a", encoding="utf-8") as writer:
            if needs_leading_newline:
                writer.write("\n")
            writer.write("\n".join(serialized))
            writer.write("\n")

        self._persisted_count = len(self.messages)

    def _decode_ndjson_line(self, raw_line: str) -> Iterable[dict[str, object]]:
        """Yield one or more JSON payloads contained in an NDJSON line."""
        buffer = raw_line
        while buffer:
            try:
                payload, index = self._decoder.raw_decode(buffer)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ValueError(
                    "Encountered malformed JSON while loading conversation history."
                ) from exc
            yield payload
            buffer = buffer[index:].lstrip()

    def _rewrite_history_file(self) -> None:
        serialized = [message.model_dump_json() for message in self.messages]
        with open(self._conversation_file, "w", encoding="utf-8") as writer:
            writer.write("\n".join(serialized))
            writer.write("\n")
