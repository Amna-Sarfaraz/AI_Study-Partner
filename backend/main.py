# 1. Creates the FastAPI app instance
# 2. Connects all your routes (auth, documents, Q&A, quiz)
# 3. Sets up CORS (allows frontend to talk to backend)
# 4. Connects to the database on startup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routes import auth, documents, qa, quiz, flashcards, rooms



# Create FastAPI app
app= FastAPI(
    title="AI Study Partner",
    description="RAG-based study assistant for two users",
    version="1.0.0")

# Setup CORS (allow frontend to talk to backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",   # React frontend
                   "http://localhost:5000"],  # HTML fronend
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers= ["*"],

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
