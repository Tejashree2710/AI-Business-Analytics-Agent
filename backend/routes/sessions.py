
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatSession, ChatMessage, UploadedFile, User
from backend.routes.auth import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["Chat Sessions"])


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=255)


@router.post("/")
def create_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat_session = ChatSession(
        user_id=current_user.id,
        title=request.title.strip() or "New Chat"
    )

    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    return {
        "message": "Chat session created successfully",
        "session_id": chat_session.id,
        "title": chat_session.title
    }


@router.get("/")
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )

    return [
        {
            "session_id": session.id,
            "title": session.title,
            "created_at": session.created_at,
            "updated_at": session.updated_at
        }
        for session in sessions
    ]


@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat_session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if not chat_session:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )

    files = (
        db.query(UploadedFile)
        .filter(UploadedFile.session_id == session_id)
        .all()
    )

    return {
        "session_id": chat_session.id,
        "title": chat_session.title,
        "created_at": chat_session.created_at,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at
            }
            for message in messages
        ],
        "files": [
            {
                "file_id": file.id,
                "filename": file.filename,
                "file_type": file.file_type,
                "file_size": file.file_size,
                "uploaded_at": file.uploaded_at
            }
            for file in files
        ]
    }
