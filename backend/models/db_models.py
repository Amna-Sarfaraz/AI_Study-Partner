# models/db_models.py

from sqlalchemy import Column, String, Boolean, Integer, Text, TIMESTAMP, ARRAY, ForeignKey, CHAR, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


# ─────────────────────────────────────────
# 1. Users
# ─────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name          = Column(String(100), nullable=False)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(TIMESTAMP, server_default=func.now())
    last_active   = Column(TIMESTAMP, server_default=func.now())

    # relationships
    documents      = relationship("Document", back_populates="uploader")
    questions      = relationship("Question", back_populates="asker")
    study_sessions = relationship("StudySession", back_populates="user")
    qa_history     = relationship("QAHistory", back_populates="asker")


# ─────────────────────────────────────────
# 2. Study Rooms
# ─────────────────────────────────────────
class StudyRoom(Base):
    __tablename__ = "study_rooms"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(255), nullable=False, unique=True)
    description = Column(String(500), default="")
    user1_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user2_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(TIMESTAMP, server_default=func.now())

    # relationships
    documents      = relationship("Document",     back_populates="room", cascade="all, delete")
    questions      = relationship("Question",     back_populates="room")
    flashcards     = relationship("Flashcard",    back_populates="room")
    quiz_sessions  = relationship("QuizSession",  back_populates="room")
    study_sessions = relationship("StudySession", back_populates="room")
    qa_history     = relationship("QAHistory",    back_populates="room")


# ─────────────────────────────────────────
# 3. Documents
# ─────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id     = Column(UUID(as_uuid=True), ForeignKey("study_rooms.id", ondelete="CASCADE"))
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id",       ondelete="SET NULL"), nullable=True)
    file_name   = Column(String(255), nullable=False)
    file_type   = Column(String(50),  nullable=False)
    file_path   = Column(String(500), nullable=False)
    summary     = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP, server_default=func.now())

    # relationships
    room          = relationship("StudyRoom",     back_populates="documents")
    uploader      = relationship("User",          back_populates="documents")
    chunks        = relationship("DocumentChunk", back_populates="document", cascade="all, delete")
    flashcards    = relationship("Flashcard",     back_populates="document")
    quiz_sessions = relationship("QuizSession",   back_populates="document")
    questions     = relationship("Question",      back_populates="document")
    qa_history    = relationship("QAHistory",     back_populates="document")


# ─────────────────────────────────────────
# 4. Document Chunks
# ─────────────────────────────────────────
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id  = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index  = Column(Integer, nullable=False)
    content      = Column(Text,    nullable=False)
    embedding_id = Column(String(255), nullable=True)
    created_at   = Column(TIMESTAMP, server_default=func.now())

    # relationships
    document = relationship("Document", back_populates="chunks")


# ─────────────────────────────────────────
# 5. Questions
# ─────────────────────────────────────────
class Question(Base):
    __tablename__ = "questions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id       = Column(UUID(as_uuid=True), ForeignKey("study_rooms.id", ondelete="CASCADE"))
    asked_by      = Column(UUID(as_uuid=True), ForeignKey("users.id",       ondelete="SET NULL"), nullable=True)
    document_id   = Column(UUID(as_uuid=True), ForeignKey("documents.id",   ondelete="SET NULL"), nullable=True)
    question_text = Column(Text, nullable=False)
    created_at    = Column(TIMESTAMP, server_default=func.now())

    # relationships
    room     = relationship("StudyRoom", back_populates="questions")
    asker    = relationship("User",      back_populates="questions")
    document = relationship("Document",  back_populates="questions")
    answers  = relationship("Answer",    back_populates="question")


# ─────────────────────────────────────────
# 6. Answers
# ─────────────────────────────────────────
class Answer(Base):
    __tablename__ = "answers"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id   = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"))
    answer_text   = Column(Text, nullable=False)
    source_chunks = Column(ARRAY(Text), nullable=True)
    was_helpful   = Column(Boolean, nullable=True)
    created_at    = Column(TIMESTAMP, server_default=func.now())

    # relationships
    question = relationship("Question", back_populates="answers")


# ─────────────────────────────────────────
# 7. Flashcards
# ─────────────────────────────────────────
class Flashcard(Base):
    __tablename__ = "flashcards"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id",   ondelete="CASCADE"))
    room_id     = Column(UUID(as_uuid=True), ForeignKey("study_rooms.id", ondelete="CASCADE"))
    question    = Column(Text, nullable=False)
    answer      = Column(Text, nullable=False)
    created_at  = Column(TIMESTAMP, server_default=func.now())

    # relationships
    document = relationship("Document",  back_populates="flashcards")
    room     = relationship("StudyRoom", back_populates="flashcards")


# ─────────────────────────────────────────
# 8. Quiz Sessions
# ─────────────────────────────────────────
class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id         = Column(UUID(as_uuid=True), ForeignKey("study_rooms.id", ondelete="CASCADE"))
    document_id     = Column(UUID(as_uuid=True), ForeignKey("documents.id",   ondelete="SET NULL"), nullable=True)
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id",       ondelete="SET NULL"), nullable=True)
    total_questions = Column(Integer, default=0)
    created_at      = Column(TIMESTAMP, server_default=func.now())

    # relationships
    room      = relationship("StudyRoom",    back_populates="quiz_sessions")
    document  = relationship("Document",     back_populates="quiz_sessions")
    questions = relationship("QuizQuestion", back_populates="quiz_session", cascade="all, delete")


# ─────────────────────────────────────────
# 9. Quiz Questions
# ─────────────────────────────────────────
class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_session_id = Column(UUID(as_uuid=True), ForeignKey("quiz_sessions.id", ondelete="CASCADE"))
    question_text   = Column(Text,       nullable=False)
    option_a        = Column(String(500), nullable=False)
    option_b        = Column(String(500), nullable=False)
    option_c        = Column(String(500), nullable=False)
    option_d        = Column(String(500), nullable=False)
    correct_option  = Column(CHAR(1), nullable=False)
    user_answer     = Column(CHAR(1), nullable=True)
    is_correct      = Column(Boolean, nullable=True)
    created_at      = Column(TIMESTAMP, server_default=func.now())

    # relationships
    quiz_session = relationship("QuizSession", back_populates="questions")


# ─────────────────────────────────────────
# 10. Study Sessions
# ─────────────────────────────────────────
class StudySession(Base):
    __tablename__ = "study_sessions"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id          = Column(UUID(as_uuid=True), ForeignKey("study_rooms.id", ondelete="CASCADE"))
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id",       ondelete="CASCADE"))
    started_at       = Column(TIMESTAMP, server_default=func.now())
    ended_at         = Column(TIMESTAMP, nullable=True)
    duration_minutes = Column(Integer,   nullable=True)
    topics_covered   = Column(ARRAY(Text), nullable=True)

    # relationships
    room = relationship("StudyRoom", back_populates="study_sessions")
    user = relationship("User",      back_populates="study_sessions")


# ─────────────────────────────────────────
# 11. QA History
# ─────────────────────────────────────────
class QAHistory(Base):
    __tablename__ = "qa_history"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id     = Column(UUID(as_uuid=True), ForeignKey("study_rooms.id", ondelete="CASCADE"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id",   ondelete="SET NULL"), nullable=True)
    asked_by    = Column(UUID(as_uuid=True), ForeignKey("users.id",       ondelete="SET NULL"), nullable=True)
    question    = Column(Text, nullable=False)
    answer      = Column(Text, nullable=False)
    sources     = Column(JSON, default=list)
    created_at  = Column(TIMESTAMP, server_default=func.now())

    # relationships
    room     = relationship("StudyRoom", back_populates="qa_history")
    document = relationship("Document",  back_populates="qa_history")
    asker    = relationship("User",      back_populates="qa_history")