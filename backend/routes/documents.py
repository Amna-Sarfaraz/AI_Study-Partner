# # routes/documents.py
# Frontend uploads PDF/TXT
#         ↓
# documents.py receives it
#         ↓
# 1. Saves file to disk
# 2. Extracts text from it
# 3. Splits text into chunks
# 4. Sends chunks to ChromaDB (vector store)
# 5. Saves metadata to PostgreSQL
#         ↓
# Document is now ready for Q&A

# POST /documents/upload          → upload PDF or TXT file
# GET  /documents/                → list all documents in a room
# GET  /documents/{id}            → get one document's details
# DELETE /documents/{id}          → delete a document
# POST /documents/{id}/summary    → generate AI summary (calls OpenAI)

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os, shutil, uuid

from database import get_db
from models.db_models import Document, DocumentChunk, StudyRoom
from routes.auth import get_current_user
from models.db_models import User
from services.access_service import ensure_room_access
from services.rag_service import process_document, delete_document_chunks

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)   # creates folder if it doesn't exist

ALLOWED_TYPES = ["application/pdf", "text/plain"]


# ─────────────────────────────────────────
# UPLOAD DOCUMENT
# ─────────────────────────────────────────
@router.post("/upload", status_code=201)
async def upload_document(
    room_id: str = Form(...),                        # which study room
    file: UploadFile = File(...),                    # the actual file
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # must be logged in
):
    # 1. Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are allowed"
        )

    # 2. Check room exists
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Study room not found")
    ensure_room_access(room, current_user)

    # 3. Save file to disk
    # Give it a unique name so two files with same name don't clash
    file_extension = os.path.splitext(file.filename)[1]        # .pdf or .txt
    unique_filename = f"{uuid.uuid4()}{file_extension}"        # random-uuid.pdf
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)                  # write to disk

    # 4. Save document metadata to PostgreSQL
    new_doc = Document(
        room_id=room_id,
        uploaded_by=current_user.id,
        file_name=file.filename,                               # original name
        file_type=file.content_type,
        file_path=file_path,                                   # where it's saved
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 5. Process document through RAG pipeline
    # This extracts text, chunks it, and stores in ChromaDB
    try:
        chunk_count = await process_document(
            doc_id=str(new_doc.id),
            room_id=room_id,
            file_path=file_path,
            file_type=file.content_type,
            db=db
        )
    except Exception as e:
        # If RAG fails, delete the doc record to keep DB clean
        db.delete(new_doc)
        db.commit()
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

    return {
        "message": "Document uploaded and processed successfully",
        "document_id": str(new_doc.id),
        "file_name": file.filename,
        "chunks_created": chunk_count
    }


# ─────────────────────────────────────────
# LIST ALL DOCUMENTS IN A ROOM
# ─────────────────────────────────────────
@router.get("/")
def list_documents(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Study room not found")
    ensure_room_access(room, current_user)

    documents = db.query(Document)\
                  .filter(Document.room_id == room_id)\
                  .order_by(Document.created_at.desc())\
                  .all()

    return [
        {
            "id": str(doc.id),
            "file_name": doc.file_name,
            "file_type": doc.file_type,
            "chunk_count": len(doc.chunks),
            "has_summary": doc.summary is not None,
            "uploaded_by": str(doc.uploaded_by),
            "created_at": doc.created_at
        }
        for doc in documents
    ]


# ─────────────────────────────────────────
# GET ONE DOCUMENT DETAILS
# ─────────────────────────────────────────
@router.get("/{doc_id}")
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_room_access(doc.room, current_user)

    return {
        "id": str(doc.id),
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "summary": doc.summary,
        "chunk_count": len(doc.chunks),          # how many chunks were created
        "uploaded_by": str(doc.uploaded_by),
        "created_at": doc.created_at
    }


# ─────────────────────────────────────────
# GENERATE AI SUMMARY
# ─────────────────────────────────────────
@router.post("/{doc_id}/summary")
async def generate_summary(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Find the document
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_room_access(doc.room, current_user)

    # 2. Get all its chunks from DB
    chunks = db.query(DocumentChunk)\
               .filter(DocumentChunk.document_id == doc_id)\
               .order_by(DocumentChunk.chunk_index)\
               .all()

    if not chunks:
        raise HTTPException(status_code=400, detail="No content found in document")

    # 3. Summarize document chunks with a Gemini-friendly summary pipeline
    from services.ai_service import generate_summary_from_chunks
    summary = await generate_summary_from_chunks([chunk.content for chunk in chunks])

    # 5. Save summary back to document
    doc.summary = summary
    db.commit()

    return {
        "document_id": doc_id,
        "summary": summary
    }


# ─────────────────────────────────────────
# DELETE DOCUMENT
# ─────────────────────────────────────────
@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    ensure_room_access(doc.room, current_user)

    # 1. Delete physical file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # 2. Delete vectors from ChromaDB
    delete_document_chunks(str(doc.id))

    # 3. Delete from PostgreSQL
    # (chunks delete automatically due to CASCADE in your DB schema)
    db.delete(doc)
    db.commit()

    return {"message": "Document deleted successfully"}
