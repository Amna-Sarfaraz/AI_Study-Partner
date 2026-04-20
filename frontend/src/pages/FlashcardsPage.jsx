import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import BrandMark from "../components/ui/BrandMark";
import SectionIcon from "../components/ui/SectionIcon";
import {
  clearSession,
  fetchDocuments,
  fetchFlashcards,
  fetchRoom,
  generateFlashcards,
  getStoredUser,
} from "../lib/api";
import "../styles/study-tools.css";

export default function FlashcardsPage() {
  const [searchParams] = useSearchParams();
  const roomId = searchParams.get("room_id");
  const initialDocumentId = searchParams.get("document_id") || "";
  const user = useMemo(() => getStoredUser(), []);
  const [room, setRoom] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState(initialDocumentId);
  const [cards, setCards] = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingCards, setLoadingCards] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadPageData() {
      if (!roomId) {
        setError("Missing room id.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");

      try {
        const [roomResult, documentsResult] = await Promise.all([
          fetchRoom(roomId),
          fetchDocuments(roomId),
        ]);

        setRoom(roomResult);
        setDocuments(documentsResult);
        setSelectedDocumentId(initialDocumentId || documentsResult[0]?.id || "");
      } catch (loadError) {
        setError(loadError.message);
      } finally {
        setLoading(false);
      }
    }

    loadPageData();
  }, [initialDocumentId, roomId]);

  useEffect(() => {
    async function loadSelectedDocument() {
      if (!selectedDocumentId) {
        setCards([]);
        setActiveIndex(0);
        setFlipped(false);
        return;
      }

      setLoadingCards(true);
      setError("");
      setFlipped(false);
      setActiveIndex(0);

      try {
        const cardsResult = await fetchFlashcards(selectedDocumentId);
        setCards(cardsResult.flashcards || []);
      } catch (loadError) {
        setError(loadError.message);
      } finally {
        setLoadingCards(false);
      }
    }

    loadSelectedDocument();
  }, [selectedDocumentId]);

  async function handleGenerateFlashcards() {
    if (!roomId || !selectedDocumentId) {
      setError("Choose a document first.");
      return;
    }

    setGenerating(true);
    setError("");

    try {
      const result = await generateFlashcards({
        roomId,
        documentId: selectedDocumentId,
      });
      setCards(result.flashcards || []);
      setActiveIndex(0);
      setFlipped(false);
    } catch (generateError) {
      setError(generateError.message);
    } finally {
      setGenerating(false);
    }
  }

  const activeCard = cards[activeIndex];

  return (
    <main className="study-shell">
      <div className="study-app">
        <header className="study-topbar">
          <div className="study-brand">
            <BrandMark className="study-brand__mark" />
            <div>
              <strong>AI Study Partner</strong>
              <span>Learn smarter, together</span>
            </div>
          </div>

          <div className="study-userbar">
            <span>Hi, {user?.name?.toLowerCase() || "student"}</span>
            <button
              className="study-userbar__button"
              type="button"
              onClick={() => {
                clearSession();
                window.location.href = "/auth";
              }}
            >
              Sign out
            </button>
          </div>
        </header>

        <section className="study-content">
          <Link to={roomId ? `/documents?room_id=${roomId}` : "/rooms"} className="study-backlink">
            All rooms
          </Link>

          <header className="study-header">
            <div>
              <h1>{room?.name || "Flashcards"}</h1>
            </div>
          </header>

          <nav className="study-tabs" aria-label="Room sections">
            <Link className="study-tab" to={roomId ? `/documents?room_id=${roomId}` : "/rooms"}><SectionIcon name="documents" />Documents</Link>
            <Link className="study-tab" to={roomId ? `/documents?room_id=${roomId}&tab=summary` : "/rooms"}><SectionIcon name="summary" />Summary</Link>
            <Link className="study-tab" to={roomId ? `/documents?room_id=${roomId}&tab=qa` : "/rooms"}><SectionIcon name="qa" />Q&amp;A</Link>
            <Link className="study-tab" to={roomId ? `/quiz?room_id=${roomId}&document_id=${selectedDocumentId}` : "/rooms"}><SectionIcon name="quiz" />Quiz</Link>
            <button className="study-tab is-active" type="button"><SectionIcon name="flashcards" />Flashcards</button>
          </nav>

          {error ? <div className="study-feedback study-feedback--error">{error}</div> : null}

          {loading ? (
            <div className="study-feedback">Loading flashcard workspace...</div>
          ) : (
            <>
              {loadingCards ? (
                <div className="study-feedback">Loading cards...</div>
              ) : activeCard ? (
                <section className="study-stack">
                  <div className="flashcard-toolbar">
                    <span>
                      {activeIndex + 1} of {cards.length}
                    </span>
                    <button
                      className="flashcard-regenerate"
                      type="button"
                      onClick={handleGenerateFlashcards}
                      disabled={generating || !selectedDocumentId}
                    >
                      {generating ? "Regenerating..." : "Regenerate"}
                    </button>
                  </div>

                  <button
                    className={`flashcard-stage flashcard-stage--single ${flipped ? "is-answer" : "is-question"}`}
                    type="button"
                    onClick={() => setFlipped((current) => !current)}
                  >
                    <div className="flashcard-stage__inner">
                      <span>{flipped ? "Answer" : "Question"}</span>
                      <h2>{flipped ? activeCard.answer : activeCard.question}</h2>
                      <p>Click to flip</p>
                    </div>
                  </button>

                  <div className="flashcard-nav">
                    <button
                      className="study-secondary-button"
                      type="button"
                      onClick={() => {
                        setActiveIndex((current) => Math.max(current - 1, 0));
                        setFlipped(false);
                      }}
                      disabled={activeIndex === 0}
                    >
                      Previous
                    </button>
                    <button
                      className="study-primary-button"
                      type="button"
                      onClick={() => {
                        setActiveIndex((current) => Math.min(current + 1, cards.length - 1));
                        setFlipped(false);
                      }}
                      disabled={activeIndex === cards.length - 1}
                    >
                      Next
                    </button>
                  </div>
                </section>
              ) : (
                <section className="study-panel study-panel--empty">
                  <div className="study-empty-icon">
                    <SectionIcon name="flashcards" />
                  </div>
                  <h2>No flashcards yet</h2>
                  <p>Generate a deck of flashcards from this document and start reviewing.</p>
                  <div className="study-actions">
                    <button
                      className="study-primary-button"
                      type="button"
                      onClick={handleGenerateFlashcards}
                      disabled={generating || !selectedDocumentId}
                    >
                      {generating ? "Generating..." : "Generate flashcards"}
                    </button>
                  </div>
                </section>
              )}
            </>
          )}
        </section>
      </div>
    </main>
  );
}
