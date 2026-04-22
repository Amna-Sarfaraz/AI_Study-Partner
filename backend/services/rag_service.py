# services/rag_service.py

import os
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from sqlalchemy.orm import Session
from models.db_models import DocumentChunk
import fitz  # PyMuPDF — for reading PDFs
from services.ai_service import generate_text

# ─────────────────────────────────────────
# SETUP — runs once when the file is imported
# ─────────────────────────────────────────

CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma_store")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")

_collection = None
_embeddings_model = None


def get_collection():
    """
    Lazily create the collection so the API can boot without initializing
    the full retrieval layer during startup.
    """
    global _collection
    if _collection is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = chroma_client.get_or_create_collection(
            name="study_chunks",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def get_embeddings_model():
    """
    Load the embedding model only when a request needs it.
    This reduces startup memory pressure on Render.
    """
    global _embeddings_model
    if _embeddings_model is None:
        _embeddings_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embeddings_model

# ─────────────────────────────────────────
# TEXT SPLITTER SETUP
# ─────────────────────────────────────────

# RecursiveCharacterTextSplitter tries to split at paragraphs first,
# then sentences, then words — it's "smart" splitting
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # each chunk is max 500 characters
    chunk_overlap=50,      # 50 chars overlap between chunks so context isn't lost at boundaries
    separators=["\n\n", "\n", ". ", " ", ""]  # tries these split points in order
)


# ─────────────────────────────────────────
# STEP 1 — EXTRACT TEXT FROM FILE
# ─────────────────────────────────────────

def extract_text(file_path: str, file_type: str) -> str:
    """
    Read the uploaded file and return its raw text.
    Handles PDF (using PyMuPDF) and plain TXT files.
    """
    if file_type == "application/pdf":
        # Open the PDF and extract text from every page
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()  # extract text from one page
        doc.close()
        return text

    elif file_type == "text/plain":
        # TXT files are simple — just read them directly
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported file type: {file_type}")


# ─────────────────────────────────────────
# STEP 2 — CHUNK THE TEXT
# ─────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    """
    Split a long piece of text into smaller overlapping chunks.
    Returns a list of strings (the chunks).

    Why chunk? Because embedding models have a max input size,
    and smaller chunks give more precise search results.
    """
    chunks = text_splitter.split_text(text)
    return chunks  # e.g. ["Photosynthesis is...", "...which occurs in the chloroplast..."]


# ─────────────────────────────────────────
# STEP 3 — EMBED THE CHUNKS
# ─────────────────────────────────────────

def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """
    Convert each text chunk into a vector (list of numbers).
    These numbers capture the "meaning" of the text.

    Similar text → similar vectors → can be searched later.
    """
    # embed_documents() handles a batch of texts at once
    embeddings_model = get_embeddings_model()
    vectors = embeddings_model.embed_documents(chunks)
    return vectors  # e.g. [[0.12, -0.34, 0.56, ...], [...], ...]


# ─────────────────────────────────────────
# STEP 4 — STORE IN CHROMADB + POSTGRESQL
# ─────────────────────────────────────────

def store_chunks(
    doc_id: str,
    room_id: str,
    chunks: list[str],
    vectors: list[list[float]],
    db: Session
) -> int:
    """
    Save each chunk in two places:
    1. ChromaDB — stores the vector (for fast similarity search)
    2. PostgreSQL — stores the text + metadata (for retrieval and display)

    Returns the number of chunks stored.
    """
    chroma_ids = []    # unique ID for each chunk in ChromaDB
    chroma_docs = []   # the actual text of each chunk
    chroma_vecs = []   # the vector for each chunk
    chroma_meta = []   # metadata attached to each chunk

    for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
        # Create a unique ID for this chunk: "doc_id_chunkindex"
        chunk_id = f"{doc_id}_{i}"

        # ── Save to PostgreSQL ──
        db_chunk = DocumentChunk(
            document_id=doc_id,
            chunk_index=i,      # position of this chunk in the document
            content=chunk_text  # the actual text
        )
        db.add(db_chunk)

        # ── Collect for ChromaDB (we'll batch-insert below) ──
        chroma_ids.append(chunk_id)
        chroma_docs.append(chunk_text)
        chroma_vecs.append(vector)
        chroma_meta.append({
            "document_id": doc_id,
            "room_id": room_id,
            "chunk_index": i
        })

    # Commit all PostgreSQL records at once
    db.commit()

    # Insert all chunks into ChromaDB at once (more efficient than one by one)
    collection = get_collection()
    collection.add(
        ids=chroma_ids,
        documents=chroma_docs,
        embeddings=chroma_vecs,
        metadatas=chroma_meta
    )

    return len(chunks)


# ─────────────────────────────────────────
# MAIN INGESTION FUNCTION (called by documents.py)
# ─────────────────────────────────────────

async def process_document(
    doc_id: str,
    room_id: str,
    file_path: str,
    file_type: str,
    db: Session
) -> int:
    """
    Full pipeline for a newly uploaded document:
    extract → chunk → embed → store

    Called from documents.py after a file is saved to disk.
    Returns number of chunks created.
    """
    # Step 1: Pull text out of the file
    raw_text = extract_text(file_path, file_type)

    if not raw_text.strip():
        raise ValueError("Document appears to be empty or unreadable")

    # Step 2: Split into chunks
    chunks = chunk_text(raw_text)

    if not chunks:
        raise ValueError("No chunks could be created from document")

    # Step 3: Convert chunks to vectors
    vectors = embed_chunks(chunks)

    # Step 4: Save everything to ChromaDB + PostgreSQL
    chunk_count = store_chunks(doc_id, room_id, chunks, vectors, db)

    return chunk_count  # e.g. 42 (documents.py shows this to the user)


# ─────────────────────────────────────────
# QUERY FUNCTION — used when user asks a question
# ─────────────────────────────────────────

async def answer_question(question: str, room_id: str = None) -> dict:
    """
    Full RAG query pipeline:
    embed question → search ChromaDB → build prompt → call GPT-4o-mini

    Returns a dict with the answer and the source chunks used.
    """

    # Step 1: Embed the question using the SAME model used for documents
    # (they must match — same model = same vector space = comparable)
    embeddings_model = get_embeddings_model()
    collection = get_collection()
    question_vector = embeddings_model.embed_query(question)

    # Step 2: Search ChromaDB for the 5 most similar chunks
    # where= filter is optional — can filter by room if needed
    search_kwargs = {
        "query_embeddings": [question_vector],
        "n_results": 5  # return top 5 most relevant chunks
    }

    # Optional: filter chunks to only this study room's documents
    if room_id:
        search_kwargs["where"] = {"room_id": room_id}

    results = collection.query(**search_kwargs)

    # results["documents"][0] is a list of the matching chunk texts
    retrieved_chunks = results["documents"][0]
    retrieved_metadatas = results.get("metadatas", [[]])[0]

    if not retrieved_chunks:
        return {
            "answer": "I couldn't find relevant information in the uploaded documents.",
            "sources": []
        }

    # Step 3: Build the prompt — inject retrieved chunks as context
    context = "\n\n---\n\n".join(retrieved_chunks)  # join chunks with separator
    prompt = f"""You are a study assistant. Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't have enough information to answer that."

Context:
{context}

Question: {question}

Answer:"""

    # Step 4: Call the configured LLM with the prompt
    answer = await generate_text(
        prompt,
        temperature=0.2,
        max_tokens=500,
    )

    document_counts = {}
    for metadata in retrieved_metadatas:
        document_id = metadata.get("document_id") if metadata else None
        if document_id:
            document_counts[document_id] = document_counts.get(document_id, 0) + 1

    primary_document_id = None
    if document_counts:
        primary_document_id = max(document_counts, key=document_counts.get)

    return {
        "answer": answer,
        "sources": retrieved_chunks,  # frontend can show these as "sources used"
        "document_id": primary_document_id
    }


# ─────────────────────────────────────────
# DOCUMENT CONTEXT RETRIEVAL — used by quiz/flashcards generation
# ─────────────────────────────────────────

async def retrieve_document_context(
    document_id: str,
    purpose: str,
    chunks_per_query: int = 4
) -> list[str]:
    """
    Retrieve a focused subset of chunks for study-content generation.

    This keeps quiz/flashcard generation grounded in retrieved context
    instead of concatenating the whole document.
    """
    retrieval_profiles = {
        "quiz": {
            "queries": [
                "core concepts and definitions",
                "important facts, processes, and relationships",
                "details suitable for multiple choice questions",
                "contrasts, causes, effects, and examples"
            ],
            "target_chunks": 8,
            "min_chunk_gap": 2
        },
        "flashcards": {
            "queries": [
                "key terms and definitions",
                "important concepts worth memorizing",
                "short facts, formulas, and direct recall items",
                "named items, classifications, and concise explanations"
            ],
            "target_chunks": 10,
            "min_chunk_gap": 1
        }
    }

    profile = retrieval_profiles.get(
        purpose,
        {
            "queries": ["important study material"],
            "target_chunks": 6,
            "min_chunk_gap": 1
        }
    )

    candidate_map = {}

    for query in profile["queries"]:
        embeddings_model = get_embeddings_model()
        collection = get_collection()
        query_vector = embeddings_model.embed_query(query)
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=chunks_per_query * 2,
            where={"document_id": document_id}
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for rank, chunk in enumerate(documents):
            normalized_chunk = chunk.strip()
            if not normalized_chunk:
                continue

            metadata = metadatas[rank] if rank < len(metadatas) else {}
            chunk_index = metadata.get("chunk_index")
            distance = distances[rank] if rank < len(distances) else 1.0

            # Lower score is better: closer semantic match and higher rank.
            score = float(distance) + (rank * 0.05)
            existing = candidate_map.get(normalized_chunk)

            if existing is None or score < existing["score"]:
                candidate_map[normalized_chunk] = {
                    "text": normalized_chunk,
                    "chunk_index": chunk_index,
                    "score": score
                }

    ranked_candidates = sorted(
        candidate_map.values(),
        key=lambda item: (item["score"], item["chunk_index"] if item["chunk_index"] is not None else 10**9)
    )

    def is_diverse_enough(selected: list[dict], candidate: dict, min_gap: int) -> bool:
        if candidate["chunk_index"] is None:
            return True
        for existing in selected:
            if existing["chunk_index"] is None:
                continue
            if abs(existing["chunk_index"] - candidate["chunk_index"]) < min_gap:
                return False
        return True

    selected = []

    # First pass: prefer semantic quality plus spread across chunk positions.
    for candidate in ranked_candidates:
        if is_diverse_enough(selected, candidate, profile["min_chunk_gap"]):
            selected.append(candidate)
        if len(selected) >= profile["target_chunks"]:
            break

    # Second pass: backfill with best remaining chunks if diversity filtering was too strict.
    if len(selected) < profile["target_chunks"]:
        selected_texts = {item["text"] for item in selected}
        for candidate in ranked_candidates:
            if candidate["text"] not in selected_texts:
                selected.append(candidate)
                selected_texts.add(candidate["text"])
            if len(selected) >= profile["target_chunks"]:
                break

    # Preserve document order so the model sees a coherent study flow.
    selected.sort(key=lambda item: item["chunk_index"] if item["chunk_index"] is not None else 10**9)

    return [item["text"] for item in selected]


# ─────────────────────────────────────────
# CLEANUP — delete a document's chunks from ChromaDB
# Called from documents.py when a doc is deleted
# ─────────────────────────────────────────

def delete_document_chunks(doc_id: str):
    """
    Remove all vectors for a document from ChromaDB.
    PostgreSQL chunks are deleted automatically via CASCADE.
    """
    # ChromaDB can delete by metadata filter
    collection = get_collection()
    collection.delete(
        where={"document_id": doc_id}
    )
