from typing import Optional, Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[list[dict]] = None  # pass back "messages" from prior response


class ToolCallLog(BaseModel):
    tool: str
    input: dict
    result: dict


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallLog]
    conversation_history: list[Any]  # opaque — pass back verbatim on the next call


class DraftOutreachRequest(BaseModel):
    vin: str
    part_code: str


class DraftOutreachResponse(BaseModel):
    error: Optional[str]
    draft: Optional[str]
    grounding_data: Optional[dict] = None
