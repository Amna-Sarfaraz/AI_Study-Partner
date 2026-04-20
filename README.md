# AI Study Partner

AI Study Partner is a two-user study workspace for uploading documents, generating summaries, asking questions over document content, creating quizzes, and reviewing flashcards.

The project uses:
- `FastAPI` for the backend API
- `React + Vite` for the frontend
- `PostgreSQL` for app data
- `ChromaDB` + local embeddings for retrieval
- `Groq` for LLM-powered summary, quiz, flashcard, and Q&A generation

## Features

- User registration and login with JWT authentication
- Shared study rooms for up to two users
- PDF and TXT upload
- Document chunking and vector indexing
- AI-generated summaries
- Document-grounded Q&A
- Quiz generation with answer checking and results
- Flashcard generation with review flow
- Basic access control for rooms, documents, quizzes, and flashcards
- Basic login throttling against repeated failed sign-in attempts

## Project Structure

```text
AI_Study/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   │   └── db_models.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── rooms.py
│   │   ├── documents.py
│   │   ├── qa.py
│   │   ├── quiz.py
│   │   └── flashcards.py
│   └── services/
│       ├── access_service.py
│       ├── ai_service.py
│       ├── rag_service.py
│       └── notification_service.py
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/ui/
│   │   ├── lib/api.js
│   │   ├── pages/
│   │   └── styles/
│   └── package.json
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## How It Works

### Document Flow

1. User uploads a PDF or TXT file into a room.
2. Backend stores the file on disk.
3. Text is extracted and split into chunks.
4. Chunks are embedded using a local embedding model.
5. Vectors are stored in ChromaDB and metadata is stored in PostgreSQL.

### Summary Flow

1. Backend loads all chunks for the selected document.
2. Groq is used to generate a structured summary.
3. If provider rate limiting occurs, a local fallback summary is generated.
4. Summary is stored back on the document record.

### Q&A Flow

1. User asks a question in a room.
2. Backend retrieves the most relevant chunks from ChromaDB.
3. Retrieved context is sent to the LLM.
4. Answer and sources are saved in room chat history.

### Quiz / Flashcard Flow

1. Backend retrieves focused context for the selected document.
2. Groq generates MCQs or flashcards from that context.
3. Quiz sessions and flashcards are saved to the database.

## Environment Variables

Create a `.env` file in the project root using `.env.example` as a template.

Example keys:

```env
DATABASE_URL=postgresql://YOUR_DB_USER:YOUR_DB_PASSWORD@localhost/YOUR_DB_NAME
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
SECRET_KEY=your_secret_key_here
N8N_WEBHOOK_URL=http://localhost:5678/webhook/your-id
DB_PASSWORD=your_db_password_here
```

## Backend Setup

### 1. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the backend

```bash
cd backend
uvicorn main:app --reload
```

If `uvicorn` is not found:

```bash
cd backend
python3 -m uvicorn main:app --reload
```

Backend will run on:

```text
http://127.0.0.1:8000
```

Swagger docs:

```text
http://127.0.0.1:8000/docs
```

## Frontend Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Start the frontend

```bash
npm run dev
```

### 3. Production build

```bash
npm run build
```

## Database Notes

- PostgreSQL is required for relational data
- ChromaDB is used locally via `backend/chroma_store`
- tables are created on backend startup via `Base.metadata.create_all(bind=engine)`

## Security / Access Notes

Current codebase includes:
- JWT-protected routes
- room-based access control
- explicit room joining
- quiz session ownership checks
- flashcard/document access checks
- basic brute-force login throttling

Still recommended before public deployment:
- rotate any exposed secrets
- keep `.env` out of version control
- use a stronger production secret key
- replace in-memory login throttling with Redis or persistent rate limiting
- move uploads and vector storage to production-grade storage if scaling beyond a demo

## Demo Credentials / Users

This project is currently designed for a maximum of two registered users.

That limit is enforced in:

```text
backend/routes/auth.py
```

## Useful Commands

### Frontend build

```bash
cd frontend
npm run build
```

### Backend syntax check

```bash
python3 -m py_compile backend/routes/auth.py backend/routes/rooms.py backend/routes/documents.py backend/routes/qa.py backend/routes/quiz.py backend/routes/flashcards.py
```

## Git Setup

After creating your GitHub repository, run:

```bash
cd /home/amna/AI_Study
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin YOUR_REPO_URL
git push -u origin main
```

## Current Status

This project is in a solid demo-ready state:
- UI flows are implemented
- backend routes are connected
- Groq integration is active
- core access-control issues found in review were fixed

## Author Notes

This repository is structured to be easy to demo, easy to clone, and straightforward to extend with:
- explicit room invitations
- persistent login throttling
- richer study analytics
- collaborative notifications
