# routes/flashcards.py
# Generates flashcards from a document — user flips through them to study

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.db_models import User, Document, Flashcard
from routes.auth import get_current_user
from services.access_service import ensure_room_access
from services.ai_service import generate_flashcards
from services.rag_service import retrieve_document_context

router = APIRouter()


# ─────────────────────────────────────────
# REQUEST SHAPE
# ─────────────────────────────────────────

class GenerateFlashcardsRequest(BaseModel):
    document_id: str
    room_id: str
    num_cards: int = 10   # default 10 flashcards


# ─────────────────────────────────────────
# GENERATE FLASHCARDS
# ─────────────────────────────────────────

@router.post("/generate", status_code=201)
async def generate(
    data: GenerateFlashcardsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Check document exists
    document = db.query(Document).filter(Document.id == data.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if str(document.room_id) != data.room_id:
        raise HTTPException(status_code=400, detail="Document does not belong to the selected room")
    ensure_room_access(document.room, current_user)

    # 2. Retrieve a focused context from the vector store for flashcard generation
    try:
        retrieved_chunks = await retrieve_document_context(
            document_id=data.document_id,
            purpose="flashcards"
        )
        if not retrieved_chunks:
            raise HTTPException(status_code=400, detail="Document has no retrievable content")

        context_text = "\n\n---\n\n".join(retrieved_chunks)
        cards = await generate_flashcards(context_text, data.num_cards)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate flashcards: {str(e)}")

    db.query(Flashcard).filter(Flashcard.document_id == data.document_id).delete()

    # 3. Save each flashcard to PostgreSQL
    db_cards = []
    for card in cards:
        fc = Flashcard(
            document_id=data.document_id,
            room_id=data.room_id,
            question=card["question"],
            answer=card["answer"]
        )
        db.add(fc)
        db_cards.append(fc)

    db.commit()

    # 4. Return all flashcards to frontend
    return {
        "total_cards": len(db_cards),
        "flashcards": [
            {
                "id": str(fc.id),
                "question": fc.question,
                "answer": fc.answer
            }
            for fc in db_cards
        ]
    }


# ─────────────────────────────────────────
# GET EXISTING FLASHCARDS FOR A DOCUMENT
# ─────────────────────────────────────────

@router.get("/{document_id}")
def get_flashcards(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns previously generated flashcards.
    So user doesn't regenerate every time they open the page.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_room_access(document.room, current_user)

    cards = db.query(Flashcard)\
              .filter(Flashcard.document_id == document_id)\
              .all()

    return {
        "total_cards": len(cards),
        "flashcards": [
            {
                "id": str(fc.id),
                "question": fc.question,
                "answer": fc.answer
            }
            for fc in cards
        ]
    }


# ─────────────────────────────────────────
# DELETE FLASHCARDS FOR A DOCUMENT
# ─────────────────────────────────────────

@router.delete("/{document_id}")
def delete_flashcards(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_room_access(document.room, current_user)

    db.query(Flashcard)\
      .filter(Flashcard.document_id == document_id)\
      .delete()
    db.commit()

    return {"message": "Flashcards deleted successfully"}
