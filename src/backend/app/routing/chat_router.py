import asyncio
from typing import Optional
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.routing.middleware import token_validator, user_id_extractor
from app.services import ChatService
from .contracts.chat_contracts import SendChatMessagePayload, CreateSessionResponse
from domain.enums.chat_enums import PromptType

router = APIRouter(
    prefix="/chat",
    dependencies=[
        Depends(token_validator),
        Depends(user_id_extractor)
    ]
)

@router.get("/session", response_model=CreateSessionResponse)
async def create_session(
    type: PromptType,
    id: Optional[uuid.UUID] = None,
    chat_service: ChatService = Depends(ChatService),
    user_id: str = Depends(user_id_extractor)
):
    session_id = await chat_service.create_session(
        user_id=user_id,
        prompt_type=type,
        resource_id=id
    )
    
    return CreateSessionResponse.model_construct(
        session_id=session_id
    )

@router.post("/{session_id}")
async def send_message(
    session_id: uuid.UUID,
    payload: SendChatMessagePayload,
    chat_service: ChatService = Depends(ChatService),
    user_id: str = Depends(user_id_extractor)
):
    # This function generates a stream of messages
    async def message_stream():
        async for message in chat_service.get_response(
            user_id=user_id, 
            session_id=session_id, 
            message=payload.message
        ):
            yield f"{message.model_dump_json()}\n\n"
            await asyncio.sleep(0.01)

    response = StreamingResponse(message_stream(), media_type="text/event-stream")
    return response
    
@router.get("/{session_id}/history")
async def get_chat_history(
    session_id: uuid.UUID,
    chat_service: ChatService = Depends(ChatService),
    user_id: str = Depends(user_id_extractor)
):
    messages = await chat_service.get_history(
        user_id=user_id, 
        session_id=session_id
    )
    return messages