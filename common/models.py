from datetime import datetime, timezone
from typing import Any, List

from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str
    content: str
    embedding: list[float] | None = Field(default=None)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    
class Conversation(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    
    
class BaseTool(BaseModel):
    tool_name: str
    description: str = Field(default="")
    tool_params: dict[str, Any] = Field(default_factory=dict)

    func: Any = Field(default=None, exclude=True)
    
class Action(BaseModel):
    tool: BaseTool
    request_heartbeat: bool = Field(default=False)




    
    
