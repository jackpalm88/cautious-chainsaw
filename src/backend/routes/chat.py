"""Chat endpoints with proper authentication checks."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.dependencies import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    userId: str
    message: str
    reply: str


@router.post("", response_model=ChatResponse, summary="Send a chat message")
async def send_chat(
    payload: ChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> ChatResponse:
    """Echo chat handler that trusts the authenticated session, not the payload."""

    reply = f"Received: {payload.message}"
    return ChatResponse(userId=current_user.id, message=payload.message, reply=reply)


__all__ = ["router"]
