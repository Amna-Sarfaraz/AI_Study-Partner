# routes/quiz.py
# Generates MCQ quiz from a document and handles answer submission

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.db_models import User, Document, QuizSession, QuizQuestion
from routes.auth import get_current_user
from services.access_service import ensure_room_access
from services.ai_service import generate_quiz_questions
from services.rag_service import retrieve_document_context

router = APIRouter()


# ─────────────────────────────────────────
# REQUEST SHAPES
# ─────────────────────────────────────────

class GenerateQuizRequest(BaseModel):
    document_id: str
    room_id: str
    num_questions: int = 5   # default 5 questions


class SubmitAnswerRequest(BaseModel):
    quiz_session_id: str
    question_id: str
    user_answer: str         # "A", "B", "C", or "D"


# ─────────────────────────────────────────
# GENERATE QUIZ
# ─────────────────────────────────────────

@router.post("/generate", status_code=201)
async def generate_quiz(
    data: GenerateQuizRequest,
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

    # 2. Retrieve a focused context from the vector store for quiz generation
    try:
        retrieved_chunks = await retrieve_document_context(
            document_id=data.document_id,
            purpose="quiz"
        )
        if not retrieved_chunks:
            raise HTTPException(status_code=400, detail="Document has no retrievable content to quiz on")

        context_text = "\n\n---\n\n".join(retrieved_chunks)
        questions = await generate_quiz_questions(context_text, data.num_questions)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")

    # 3. Save quiz session to DB
    session = QuizSession(
        room_id=data.room_id,
        document_id=data.document_id,
        created_by=current_user.id,
        total_questions=len(questions)
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # 4. Save each question to DB
    db_questions = []
    for q in questions:
        quiz_q = QuizQuestion(
            quiz_session_id=session.id,
            question_text=q["question"],
            option_a=q["option_a"],
            option_b=q["option_b"],
            option_c=q["option_c"],
            option_d=q["option_d"],
            correct_option=q["correct_option"].upper()
        )
        db.add(quiz_q)
        db_questions.append(quiz_q)

    db.commit()

    # 5. Return quiz to frontend
    return {
        "quiz_session_id": str(session.id),
        "total_questions": len(questions),
        "questions": [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d
                # correct_option NOT sent to frontend — revealed after answer
            }
            for q in db_questions
        ]
    }


# ─────────────────────────────────────────
# SUBMIT AN ANSWER
# ─────────────────────────────────────────

@router.post("/submit-answer")
def submit_answer(
    data: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(QuizSession).filter(QuizSession.id == data.quiz_session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    if str(session.created_by) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You do not have access to this quiz session")

    question = db.query(QuizQuestion).filter(QuizQuestion.id == data.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if str(question.quiz_session_id) != data.quiz_session_id:
        raise HTTPException(status_code=400, detail="Question does not belong to this quiz session")

    # Save user's answer and check if correct
    question.user_answer = data.user_answer.upper()
    question.is_correct = (question.user_answer == question.correct_option)
    db.commit()

    # Return result immediately so frontend can show correct/wrong
    return {
        "is_correct": question.is_correct,
        "correct_option": question.correct_option,
        "your_answer": question.user_answer
    }


# ─────────────────────────────────────────
# GET QUIZ RESULTS
# ─────────────────────────────────────────

@router.get("/results/{quiz_session_id}")
def get_results(
    quiz_session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(QuizSession).filter(QuizSession.id == quiz_session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    if str(session.created_by) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You do not have access to this quiz session")

    questions = db.query(QuizQuestion)\
                  .filter(QuizQuestion.quiz_session_id == quiz_session_id)\
                  .all()

    correct = sum(1 for q in questions if q.is_correct)

    return {
        "quiz_session_id": quiz_session_id,
        "total_questions": session.total_questions,
        "correct_answers": correct,
        "score_percent": round((correct / session.total_questions) * 100),
        "questions": [
            {
                "question_text": q.question_text,
                "your_answer": q.user_answer,
                "correct_option": q.correct_option,
                "is_correct": q.is_correct
            }
            for q in questions
        ]
    }
