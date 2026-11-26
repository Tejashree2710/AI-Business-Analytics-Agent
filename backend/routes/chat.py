
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from backend.database import get_db
from backend.models import ChatSession, ChatMessage, User
from backend.routes.auth import get_current_user
from backend.services.rag_service import answer_question

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: int


@router.post("/ask")
def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat_session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if not chat_session:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    user_message = ChatMessage(
        session_id=chat_session.id,
        role="user",
        content=question
    )

    db.add(user_message)
    chat_session.updated_at = func.now()
    db.commit()

    try:
        result = answer_question(
            question,
            session_id=chat_session.id
        )

        assistant_message = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=result["answer"]
        )

        db.add(assistant_message)
        chat_session.updated_at = func.now()
        db.commit()

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        import traceback
        db.rollback()
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Unable to generate an answer. Please try again."
    )
