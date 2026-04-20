from fastapi import HTTPException


def _member_ids(room) -> set[str]:
    return {
        str(member_id)
        for member_id in [room.created_by, room.user1_id, room.user2_id]
        if member_id is not None
    }


def can_access_room(room, current_user) -> bool:
    return str(current_user.id) in _member_ids(room)


def ensure_room_access(room, current_user):
    if not can_access_room(room, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this room")
