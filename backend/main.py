# 1. Creates the FastAPI app instance
# 2. Connects all your routes (auth, documents, Q&A, quiz)
# 3. Sets up CORS (allows frontend to talk to backend)
# 4. Connects to the database on startup
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import auth, documents, qa, quiz, flashcards, rooms


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5000",
    "https://ai-study-partner-five.vercel.app",
]


def get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "")
    if not raw_origins.strip():
        return DEFAULT_CORS_ORIGINS

    parsed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return parsed_origins or DEFAULT_CORS_ORIGINS



# Create FastAPI app
app= FastAPI(
    title="AI Study Partner",
    description="RAG-based study assistant for two users",
    version="1.0.0")

# Setup CORS (allow frontend to talk to backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

# Connect all routes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(rooms.router, prefix="/rooms", tags=["Rooms"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(qa.router, prefix="/qa", tags=["Q&A"])
app.include_router(quiz.router, prefix="/quiz", tags=["Quiz"])
app.include_router(flashcards.router, prefix="/flashcards", tags=["Flashcards"])

# Root endpoint to test if server is running

@app.get("/")
def root():
    return {"message": "AI Study Partner API is running"}
