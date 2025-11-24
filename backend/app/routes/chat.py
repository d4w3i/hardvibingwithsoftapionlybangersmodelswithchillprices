"""Chat routes - send messages and stream responses"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Conversation, Message, ApiKey, MessageRoleEnum
from app.routes.auth import get_current_user
from app.services.encryption import decrypt_api_key
from app.services.ai_service import AgentFactory

router = APIRouter()


class ChatRequest(BaseModel):
    conversation_id: int
    message: str


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message and stream the AI response.

    This endpoint:
    1. Validates the conversation belongs to the user
    2. Retrieves conversation history
    3. Gets the user's API key for the provider
    4. Creates the appropriate AI agent
    5. Streams the response back
    6. Saves both user message and AI response to database
    """
    # Get conversation and verify ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get user's API key for this provider
    api_key_record = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.id,
        ApiKey.provider == conversation.provider
    ).first()

    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No API key configured for {conversation.provider}"
        )

    # Decrypt API key
    api_key = decrypt_api_key(api_key_record.encrypted_key)

    # Get conversation history (last 20 messages for context)
    history_messages = db.query(Message).filter(
        Message.conversation_id == request.conversation_id
    ).order_by(Message.created_at.desc()).limit(20).all()

    # Convert to format expected by AI service
    history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in reversed(history_messages)
    ]

    # Save user message
    user_message = Message(
        conversation_id=request.conversation_id,
        role=MessageRoleEnum.USER,
        content=request.message
    )
    db.add(user_message)
    db.commit()

    # Create AI service
    try:
        service = AgentFactory.create(
            agent_type=conversation.agent_type,
            provider=conversation.provider.value,
            api_key=api_key
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Stream response
    async def generate():
        """Generate streaming response and save to database"""
        full_response = ""

        try:
            async for chunk in service.chat(request.message, history):
                full_response += chunk
                # Send as Server-Sent Events format
                yield f"data: {chunk}\n\n"

            # Signal end of stream
            yield "data: [DONE]\n\n"

            # Save assistant message after streaming completes
            assistant_message = Message(
                conversation_id=request.conversation_id,
                role=MessageRoleEnum.ASSISTANT,
                content=full_response
            )
            db.add(assistant_message)
            db.commit()

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield f"data: {error_msg}\n\n"
            # Still save error as message for debugging
            assistant_message = Message(
                conversation_id=request.conversation_id,
                role=MessageRoleEnum.ASSISTANT,
                content=f"[Error: {str(e)}]"
            )
            db.add(assistant_message)
            db.commit()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@router.post("/message")
async def chat_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a message and get complete response (non-streaming).

    Use this for simpler clients that don't support SSE.
    """
    # Get conversation and verify ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == request.conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get user's API key
    api_key_record = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.id,
        ApiKey.provider == conversation.provider
    ).first()

    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No API key configured for {conversation.provider}"
        )

    api_key = decrypt_api_key(api_key_record.encrypted_key)

    # Get history
    history_messages = db.query(Message).filter(
        Message.conversation_id == request.conversation_id
    ).order_by(Message.created_at.desc()).limit(20).all()

    history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in reversed(history_messages)
    ]

    # Save user message
    user_message = Message(
        conversation_id=request.conversation_id,
        role=MessageRoleEnum.USER,
        content=request.message
    )
    db.add(user_message)
    db.commit()

    # Create AI service
    try:
        service = AgentFactory.create(
            agent_type=conversation.agent_type,
            provider=conversation.provider.value,
            api_key=api_key
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Collect full response
    full_response = ""
    try:
        async for chunk in service.chat(request.message, history):
            full_response += chunk
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    # Save assistant message
    assistant_message = Message(
        conversation_id=request.conversation_id,
        role=MessageRoleEnum.ASSISTANT,
        content=full_response
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return {
        "message": full_response,
        "message_id": assistant_message.id
    }
