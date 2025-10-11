from pydantic import BaseModel

from common.models import BaseTool


class Action(BaseModel):
    thought: str
    tool: BaseTool
    # request_heartbeat: bool = Field(default=False, description="assistant will be invoked right after the action so can chain multiple actions together")
    
    
class ActionPlan(BaseModel):
    plan: list[Action]