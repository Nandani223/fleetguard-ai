from fastapi import APIRouter, HTTPException

from app.schemas.agent import ChatRequest, ChatResponse, DraftOutreachRequest, DraftOutreachResponse
from app.agent.agent import run_agent_turn
from app.agent.action import draft_outreach_message

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = run_agent_turn(request.message, request.conversation_history)
    return ChatResponse(
        reply=result["reply"],
        tool_calls=[
            {"tool": t["tool"], "input": t["input"], "result": t["result"]}
            for t in result["tool_calls"]
        ],
        conversation_history=result["messages"],
    )


@router.post("/draft-outreach", response_model=DraftOutreachResponse)
def draft_outreach(request: DraftOutreachRequest):
    result = draft_outreach_message(request.vin, request.part_code)
    return DraftOutreachResponse(**result)
