from datetime import datetime, timezone
from typing import Any, List

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str
    embedding: list[float] | None = Field(default=None)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    token_count: int = Field(default=0)
    metadata: dict[str, Any] | None = Field(default=None)


class Conversation(BaseModel):
    messages: List[Message] = Field(default_factory=list)


class BaseTool(BaseModel):
    tool_name: str
    description: str = Field(default="")
    tool_params: dict[str, Any] = Field(default_factory=dict)

    func: Any = Field(default=None, exclude=True)


class ContextBlock(BaseModel):
    title: str
    content: str


class AgentContext(BaseModel):
    agent_current_response: str | None = Field(default=None)
    assistant_plain_response: str | None = Field(default=None)
    should_end: bool = Field(default=False)
    context: dict[str, ContextBlock]

    def serialize(self) -> str:
        output = ""

        for key, block in self.context.items():
            output += block.model_dump_json(indent=4)
            output += "\n"

        return output
