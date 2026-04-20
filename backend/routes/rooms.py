# What rooms.py does
# In your project a Study Room is basically a shared workspace where 2 users can:

# Upload documents together
# Ask questions about those documents
# See each other's chat history

# Think of it like a WhatsApp group but for studying:
# Study Room "Biology Exam"
#         │
#         ├── Documents uploaded here
#         │     ├── chapter1.pdf
#         │     └── notes.txt
#         │
#         └── Q&A happens here
#               ├── User1: "what is photosynthesis?"
#               └── User2: "explain cell division"

# Endpoints it will have
# POST /rooms/          → create a new room
# GET  /rooms/          → list all rooms (both users see same list)
# GET  /rooms/{id}      → get one room's details + its documents
# DELETE /rooms/{id}    → delete a roomA

# routes/rooms.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from models.db_models import User, StudyRoom, Document
from routes.auth import get_current_user
from services.access_service import can_access_room, ensure_room_access

router = APIRouter()


# ─────────────────────────────────────────
# REQUEST / RESPONSE SHAPES
# ─────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    name: str          # e.g. "Biology Exam Prep"
    description: str = ""  # optional description


@router.post("/{room_id}/join")
def join_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if can_access_room(room, current_user):
        return {"message": "Already a member", "room_id": str(room.id)}

    if room.user1_id is None:
        room.user1_id = current_user.id
    elif room.user2_id is None:
        room.user2_id = current_user.id
    else:
        raise HTTPException(status_code=403, detail="This room is full")

    db.commit()
    db.refresh(room)

    return {"message": "Joined room successfully", "room_id": str(room.id)}


# ─────────────────────────────────────────
# CREATE A ROOM
# ─────────────────────────────────────────

@router.post("/", status_code=201)
def create_room(
    data: CreateRoomRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # must be logged in
):
    # Check a room with this name doesn't already exist
    existing = db.query(StudyRoom).filter(StudyRoom.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="A room with this name already exists")

    # Create the room — created_by tracks who made it
    new_room = StudyRoom(
        name=data.name,
        description=data.description,
        user1_id=current_user.id,
        created_by=current_user.id
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return {
        "message": "Room created successfully",
        "room_id": str(new_room.id),
        "name": new_room.name
    }


# ─────────────────────────────────────────
# LIST ALL ROOMS
# ─────────────────────────────────────────

@router.get("/")
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all study rooms.
    Both users see the same list — rooms are shared by design.
    """
    rooms = db.query(StudyRoom)\
              .order_by(StudyRoom.created_at.desc())\
              .all()

    return [
        {
            "id": str(room.id),
            "name": room.name,
            "description": room.description,
            "created_by": str(room.created_by),
            "is_member": can_access_room(room, current_user),
            "can_join": not can_access_room(room, current_user) and (room.user1_id is None or room.user2_id is None),
            "document_count": len(room.documents),  # how many docs uploaded
            "created_at": room.created_at
        }
        for room in rooms
        if can_access_room(room, current_user) or room.user1_id is None or room.user2_id is None
    ]


# ─────────────────────────────────────────
# GET ONE ROOM WITH ITS DOCUMENTS
# ─────────────────────────────────────────

@router.get("/{room_id}")
def get_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a single room's details plus all documents uploaded to it.
    Frontend uses this when user clicks into a room.
    """
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    ensure_room_access(room, current_user)

    # Get all documents in this room
    documents = db.query(Document)\
                  .filter(Document.room_id == room_id)\
                  .order_by(Document.created_at.desc())\
                  .all()

    return {
        "id": str(room.id),
        "name": room.name,
        "description": room.description,
        "created_by": str(room.created_by),
        "is_member": True,
        "created_at": room.created_at,
        "documents": [
            {
                "id": str(doc.id),
                "file_name": doc.file_name,
                "file_type": doc.file_type,
                "has_summary": doc.summary is not None,
                "created_at": doc.created_at
            }
            for doc in documents
        ]
    }


# ─────────────────────────────────────────
# DELETE A ROOM
# ─────────────────────────────────────────

@router.delete("/{room_id}")
def delete_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room = db.query(StudyRoom).filter(StudyRoom.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    ensure_room_access(room, current_user)

    # Only the person who created the room can delete it
    if str(room.created_by) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Only the room creator can delete it")

    # Deleting the room cascades to documents + chunks + qa_history
    # because of CASCADE set in db_models.py
    db.delete(room)
    db.commit()

    return {"message": "Room deleted successfully"}
