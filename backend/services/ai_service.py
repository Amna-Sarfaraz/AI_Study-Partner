import json
import os
import re
from collections import Counter

import httpx

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")


async def generate_text(prompt: str, temperature: float, max_tokens: int) -> str:
    if LLM_PROVIDER != "groq":
        raise ValueError("Only the Groq provider is configured for this project")

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

    if response.status_code == 429:
        raise RuntimeError("provider_rate_limited")

    if response.status_code >= 400:
        try:
            payload = response.json()
        except Exception:
            payload = response.text
        raise RuntimeError(f"provider_error: {payload}")

    payload = response.json()
    return payload["choices"][0]["message"]["content"].strip()


async def generate_summary_from_text(text: str) -> str:
    return await generate_summary_from_chunks([text])


def clean_summary_source_text(text: str) -> str:
    normalized = text.replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"([a-z])-\n([a-z])", r"\1\2", normalized)
    normalized = re.sub(r"\s*\n\s*", "\n", normalized)
    return normalized.strip()


def build_structured_summary_prompt(source_text: str) -> str:
    return f"""Create a polished study summary from the material below.

Requirements:
- Use exactly these headings:
  Overview
  Key Concepts
  Important Details
  Quick Takeaways
- Keep the summary clear, accurate, and easy to review
- Prefer paraphrasing over copying source wording
- Keep total length under 350 words
- Under Key Concepts and Quick Takeaways, use bullet points

Material:
{source_text}"""


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def build_local_summary(source_text: str) -> str:
    text = clean_summary_source_text(source_text)
    if not text:
        raise ValueError("Document text is empty after cleanup")

    sentences = split_sentences(text)
    if not sentences:
        sentences = [text[:500]]

    stop_words = {
        "the", "and", "for", "that", "with", "this", "from", "are", "was", "were",
        "into", "their", "have", "has", "had", "will", "would", "should", "can",
        "could", "about", "than", "then", "them", "they", "you", "your", "our",
        "out", "not", "but", "use", "using", "used", "also", "such", "these",
        "those", "been", "being", "its", "it's", "his", "her", "she", "him",
        "who", "what", "when", "where", "why", "how", "which", "while", "over",
        "under", "more", "most", "some", "each", "other", "through", "between",
        "software", "study", "material", "document",
    }

    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    filtered_words = [word for word in words if word not in stop_words]
    frequencies = Counter(filtered_words)

    def score_sentence(sentence: str) -> float:
        sentence_words = re.findall(r"\b[a-zA-Z]{3,}\b", sentence.lower())
        if not sentence_words:
            return 0.0
        relevant_words = [word for word in sentence_words if word not in stop_words]
        if not relevant_words:
            return 0.0
        return sum(frequencies.get(word, 0) for word in relevant_words) / len(relevant_words)

    ranked_sentences = sorted(
        ((index, sentence, score_sentence(sentence)) for index, sentence in enumerate(sentences)),
        key=lambda item: item[2],
        reverse=True,
    )

    top_sentences = sorted(ranked_sentences[:5], key=lambda item: item[0])
    overview = top_sentences[0][1] if top_sentences else text[:240]
    key_concepts = [sentence for _, sentence, _ in top_sentences[:3]]
    important_details = [sentence for _, sentence, _ in top_sentences[3:5]]

    concept_terms = []
    for word, _count in frequencies.most_common(6):
        if word not in concept_terms:
            concept_terms.append(word.replace("_", " "))

    if not important_details and len(sentences) > 1:
        important_details = sentences[1:3]

    key_concepts_text = "\n".join(f"- {sentence}" for sentence in key_concepts[:3])
    important_details_text = " ".join(important_details[:2]).strip() or overview
    takeaways = "\n".join(f"- Focus on {term}" for term in concept_terms[:3]) or "- Review the main concepts and examples."

    return (
        "Overview\n"
        f"{overview}\n\n"
        "Key Concepts\n"
        f"{key_concepts_text}\n\n"
        "Important Details\n"
        f"{important_details_text}\n\n"
        "Quick Takeaways\n"
        f"{takeaways}"
    )


async def generate_summary_from_chunks(chunks: list[str]) -> str:
    cleaned_chunks = [clean_summary_source_text(chunk) for chunk in chunks]
    cleaned_chunks = [chunk for chunk in cleaned_chunks if chunk]
    if not cleaned_chunks:
        raise ValueError("Document text is empty after cleanup")

    full_text = "\n\n".join(cleaned_chunks)
    truncated_text = full_text[:12000]
    prompt = build_structured_summary_prompt(truncated_text)

    try:
        return await generate_text(prompt, temperature=0.2, max_tokens=650)
    except RuntimeError as exc:
        if str(exc) == "provider_rate_limited":
            return build_local_summary(truncated_text)
        raise


async def generate_quiz_questions(text: str, num_questions: int = 5) -> list[dict]:
    truncated = text[:12000]

    prompt = f"""Generate exactly {num_questions} multiple choice questions from this study material.

Return ONLY a JSON array, no extra text, no markdown, just raw JSON like this:
[
  {{
    "question": "What is photosynthesis?",
    "option_a": "Process of making food using sunlight",
    "option_b": "Process of breathing",
    "option_c": "Process of digestion",
    "option_d": "Process of reproduction",
    "correct_option": "A"
  }}
]

Study material:
{truncated}"""

    raw = await generate_text(prompt, temperature=0.5, max_tokens=2000)
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


async def generate_flashcards(text: str, num_cards: int = 10) -> list[dict]:
    truncated = text[:12000]

    prompt = f"""Generate exactly {num_cards} flashcards from this study material.
Each flashcard should have a clear question and a short precise answer.

Return ONLY a JSON array, no extra text, no markdown, just raw JSON like this:
[
  {{
    "question": "What is the powerhouse of the cell?",
    "answer": "The mitochondria"
  }}
]

Study material:
{truncated}"""

    raw = await generate_text(prompt, temperature=0.4, max_tokens=2000)
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
