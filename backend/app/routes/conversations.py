"""Conversations routes - manage chat conversations"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models import User, Conversation, Message, ProviderEnum, MessageRoleEnum
from app.routes.auth import get_current_user

router = APIRouter()


# Pydantic schemas
class ConversationCreate(BaseModel):
    title: Optional[str] = None
    agent_type: str
    provider: ProviderEnum


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str]
    agent_type: str
    provider: ProviderEnum
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: MessageRoleEnum
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessages(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


# Routes
@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conv_data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation.

    The agent_type can be:
    - "langgraph" - LangGraph agent
    - "openai_direct" - Direct OpenAI API
    - "anthropic_direct" - Direct Anthropic API
    - Or any custom agent you implement
    """
    # Auto-generate title if not provided
    title = conv_data.title or f"New Chat - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    conversation = Conversation(
        user_id=current_user.id,
        title=title,
        agent_type=conv_data.agent_type,
        provider=conv_data.provider
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


@router.get("/", response_model=list[ConversationResponse])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """
    Get all conversations for the current user.

    Returns conversations ordered by most recently updated.
    """
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(
        Conversation.updated_at.desc()
    ).offset(skip).limit(limit).all()

    # Add message count to each conversation
    result = []
    for conv in conversations:
        message_count = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).count()

        conv_dict = {
            "id": conv.id,
            "title": conv.title,
            "agent_type": conv.agent_type,
            "provider": conv.provider,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "message_count": message_count
        }
        result.append(conv_dict)

    return result


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific conversation with all its messages.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()

    return {
        "conversation": conversation,
        "messages": messages
    }


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    title: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update conversation title.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    conversation.title = title
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)

    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its messages.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    db.delete(conversation)
    db.commit()

    return None


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get messages for a conversation.

    Useful for pagination or loading messages separately.
    """
    # Verify conversation belongs to user
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(
        Message.created_at.asc()
    ).offset(skip).limit(limit).all()

    return messages
