# Frontend
#    ↓  (sends question)
# qa.py          ← just a route, thin layer
#    ↓  (calls)
# rag_service.py ← does all the heavy lifting
#    ↓  (returns answer)
# qa.py
#    ↓  (sends answer back)
# Frontend

# qa.py does almost no logic itself. Its job is just:

# Receive the question from frontend
# Check the user is logged in
# Pass question to answer_question() in rag_service
# Save the Q&A to PostgreSQL (chat history)
# Return the answer back
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models.db_models import User, QAHistory, StudyRoom
from routes.auth import get_current_user
from services.access_service import ensure_room_access
from services.rag_service import answer_question

router = APIRouter()


# ─────────────────────────────────────────
# REQUEST / RESPONSE SHAPES
# ─────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str      # the user's question
    room_id: str       # which study room they're asking in


class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]   # the chunks used to generate the answer
    asked_at: datetime


# ─────────────────────────────────────────
# ASK A QUESTION
# ─────────────────────────────────────────

@router.post("/ask", response_model=AnswerResponse)
async def ask_question(
    data: QuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # must be logged in
):
    # 1. Check the room exists
    room = db.query(StudyRoom).filter(StudyRoom.id == data.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Study room not found")
    ensure_room_access(room, current_user)

    # 2. Basic validation — don't send empty questions to OpenAI
    if not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # 3. Hand off to rag_service — this is the only real work qa.py does
    result = await answer_question(
        question=data.question,
        room_id=data.room_id
    )

    # 4. Save Q&A to PostgreSQL so users can see chat history later
    history_entry = QAHistory(
        room_id=data.room_id,
        document_id=result.get("document_id"),
        asked_by=current_user.id,
        question=data.question,
        answer=result["answer"],
        sources=result["sources"]   # stored as JSON array in DB
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    # 5. Return everything to the frontend
    return {
        "question": data.question,
        "answer": result["answer"],
        "sources": result["sources"],
        "asked_at": history_entry.created_at
    }


# ─────────────────────────────────────────
# GET CHAT HISTORY FOR A ROOM
# ─────────────────────────────────────────

# Practical example — imagine a user asks 5 questions in a study room, then closes the browser and comes back the next day. Without QAHistory, 
# the chat is gone forever. With it, you call GET /qa/history/{room_id} and the frontend can reload the full conversation
@router.get("/history/{room_id}")
def get_history(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all past Q&A in a study room.
    Frontend uses this to show conversation history when user reopens a room.
    """
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Study room not found")
    ensure_room_access(room, current_user)

    history = db.query(QAHistory)\
                .filter(QAHistory.room_id == room_id)\
                .order_by(QAHistory.created_at.asc())\
                .all()

    return [
        {
            "id": str(h.id),
            "question": h.question,
            "answer": h.answer,
            "sources": h.sources,
            "asked_by": str(h.asked_by),
            "asked_at": h.created_at
        }
        for h in history
    ]
