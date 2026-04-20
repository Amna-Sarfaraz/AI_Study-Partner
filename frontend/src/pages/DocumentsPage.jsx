import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import BrandMark from "../components/ui/BrandMark";
import SectionIcon from "../components/ui/SectionIcon";
import {
  askQuestion,
  clearSession,
  deleteDocument,
  fetchDocument,
  fetchDocuments,
  fetchQaHistory,
  fetchRoom,
  generateSummary,
  getStoredUser,
  uploadDocument,
} from "../lib/api";
import "../styles/documents.css";

export default function DocumentsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const roomId = searchParams.get("room_id");
  const requestedTab = searchParams.get("tab");
  const fileInputRef = useRef(null);
  const user = useMemo(() => getStoredUser(), []);
  const [room, setRoom] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState("");
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [activeTab, setActiveTab] = useState("documents");
  const [qaHistory, setQaHistory] = useState([]);
  const [questionInput, setQuestionInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [qaLoading, setQaLoading] = useState(false);
  const [deletingDocumentId, setDeletingDocumentId] = useState("");
  const [error, setError] = useState("");

  async function loadRoomData() {
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
      if (documentsResult.length > 0) {
        setSelectedDocumentId(documentsResult[0].id);
      } else {
        setSelectedDocument(null);
      }
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRoomData();
  }, [roomId]);

  useEffect(() => {
    if (requestedTab === "summary" || requestedTab === "qa" || requestedTab === "documents") {
      setActiveTab(requestedTab);
    }
  }, [requestedTab]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setSelectedDocument(null);
      return;
    }

    fetchDocument(selectedDocumentId)
      .then((result) => setSelectedDocument(result))
      .catch((loadError) => setError(loadError.message));
  }, [selectedDocumentId]);

  useEffect(() => {
    if (activeTab !== "qa" || !roomId) {
      return;
    }

    setQaLoading(true);
    fetchQaHistory(roomId)
      .then((result) => setQaHistory(result))
      .catch((loadError) => setError(loadError.message))
      .finally(() => setQaLoading(false));
  }, [activeTab, roomId]);

  async function handleFileSelection(event) {
    const file = event.target.files?.[0];
    if (!file || !roomId) {
      return;
    }

    setUploading(true);
    setError("");

    try {
      const result = await uploadDocument({ roomId, file });
      await loadRoomData();
      setSelectedDocumentId(result.document_id);
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleGenerateSummary() {
    if (!selectedDocumentId) {
      setError("Select a document first.");
      return;
    }

    setSummaryLoading(true);
    setError("");

    try {
      const result = await generateSummary(selectedDocumentId);
      setSelectedDocument((current) => ({
        ...(current || {}),
        id: selectedDocumentId,
        summary: result.summary,
      }));
      setDocuments((current) =>
        current.map((document) =>
          document.id === selectedDocumentId ? { ...document, has_summary: true } : document
        )
      );
    } catch (summaryError) {
      setError(summaryError.message);
    } finally {
      setSummaryLoading(false);
    }
  }

  async function handleAskQuestion(event) {
    event.preventDefault();
    if (!questionInput.trim()) {
      return;
    }

    setQaLoading(true);
    setError("");

    try {
      const result = await askQuestion({
        roomId,
        question: questionInput.trim(),
      });
      setQaHistory((current) => [...current, result]);
      setQuestionInput("");
    } catch (qaError) {
      setError(qaError.message);
    } finally {
      setQaLoading(false);
    }
  }

  async function handleDeleteDocument(documentId) {
    setDeletingDocumentId(documentId);
    setError("");

    try {
      await deleteDocument(documentId);
      const nextDocuments = documents.filter((document) => document.id !== documentId);
      setDocuments(nextDocuments);

      if (selectedDocumentId === documentId) {
        setSelectedDocumentId(nextDocuments[0]?.id || "");
        setSelectedDocument(nextDocuments[0] || null);
      }
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setDeletingDocumentId("");
    }
  }

  function renderInlineSummaryText(text) {
    const normalized = text.replace(/\*\*/g, "__BOLD__");
    const parts = normalized.split("__BOLD__");

    return parts.map((part, index) =>
      index % 2 === 1 ? <strong key={`${part}-${index}`}>{part}</strong> : part
    );
  }

  function TrashButton({ label, onClick, disabled }) {
    return (
      <button
        className="document-card__delete"
        type="button"
        aria-label={label}
        onClick={onClick}
        disabled={disabled}
      >
        <span aria-hidden="true" />
        <em>{disabled ? "Deleting..." : "Delete"}</em>
      </button>
    );
  }

  const summaryBlocks = selectedDocument?.summary
    ? selectedDocument.summary
        .split(/\n+/)
        .map((entry) => entry.trim())
        .filter(Boolean)
        .map((line, index) => {
          const plainLine = line.replace(/^\*\*(.*?)\*\*$/g, "$1").trim();
          const isHeading = /^(overview|key concepts|important details|quick takeaways)$/i.test(plainLine);
          const isBullet = /^[-*]\s+/.test(line);
          return {
            id: `${line}-${index}`,
            type: isHeading ? "heading" : isBullet ? "bullet" : "paragraph",
            content: isBullet ? line.replace(/^[-*]\s+/, "") : plainLine,
          };
        })
    : [];

  return (
    <main className="documents-shell">
      <div className="documents-app">
        <header className="documents-topbar">
          <div className="documents-brand">
            <BrandMark className="documents-brand__mark" />
            <div>
              <strong>AI Study Partner</strong>
              <span>Learn smarter, together</span>
            </div>
          </div>

          <div className="documents-userbar">
            <span>Hi, {user?.name?.toLowerCase() || "student"}</span>
            <button
              className="documents-userbar__button"
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

        <section className="documents-content">
          <Link to="/rooms" className="documents-backlink">All rooms</Link>

          <header className="documents-room-header">
            <h1>{room?.name || "Study room"}</h1>
          </header>

          <nav className="documents-tabs" aria-label="Room sections">
            <button className={`documents-tab ${activeTab === "documents" ? "is-active" : ""}`} type="button" onClick={() => setActiveTab("documents")}><SectionIcon name="documents" />Documents</button>
            <button className={`documents-tab ${activeTab === "summary" ? "is-active" : ""}`} type="button" onClick={() => setActiveTab("summary")}><SectionIcon name="summary" />Summary</button>
            <button className={`documents-tab ${activeTab === "qa" ? "is-active" : ""}`} type="button" onClick={() => setActiveTab("qa")}><SectionIcon name="qa" />Q&amp;A</button>
            <button
              className="documents-tab"
              type="button"
              onClick={() => navigate(`/quiz?room_id=${roomId}${selectedDocumentId ? `&document_id=${selectedDocumentId}` : ""}`)}
            >
              <SectionIcon name="quiz" />
              Quiz
            </button>
            <button
              className="documents-tab"
              type="button"
              onClick={() => navigate(`/flashcards?room_id=${roomId}${selectedDocumentId ? `&document_id=${selectedDocumentId}` : ""}`)}
            >
              <SectionIcon name="flashcards" />
              Flashcards
            </button>
          </nav>

          {error ? <div className="documents-error">{error}</div> : null}

          {activeTab === "documents" ? (
            <>
              <section className="documents-upload">
                <div className="documents-upload__icon" aria-hidden="true">
                  <span className="documents-upload__arrow" />
                </div>
                <h2>Drop your study material here</h2>
                <p>PDF or TXT, up to 20MB</p>
                <button
                  className="documents-upload__button"
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                >
                  {uploading ? "Uploading..." : "Choose file"}
                </button>
                <input
                  ref={fileInputRef}
                  className="documents-upload__input"
                  type="file"
                  accept=".pdf,.txt,text/plain,application/pdf"
                  onChange={handleFileSelection}
                />
              </section>

              <section className="documents-list-section">
                <div className="documents-section-header">
                  <h3><SectionIcon name="documents" className="documents-section-icon" />Documents in this room</h3>
                </div>

                {loading ? (
                  <div className="documents-empty">Loading documents...</div>
                ) : documents.length === 0 ? (
                  <div className="documents-empty">No documents uploaded yet.</div>
                ) : (
                  <div className="documents-grid">
                    {documents.map((document) => (
                      <article
                        key={document.id}
                        className={`document-card ${selectedDocumentId === document.id ? "is-selected" : ""}`}
                        onClick={() => setSelectedDocumentId(document.id)}
                      >
                        <div className="document-card__icon">
                          <span />
                        </div>
                        <div className="document-card__body">
                          <strong>{document.file_name}</strong>
                          <span>{typeof document.chunk_count === "number" ? `${document.chunk_count} chunks` : "Uploaded document"}</span>
                        </div>
                        <div className="document-card__actions">
                          <TrashButton
                            label={`Delete ${document.file_name}`}
                            onClick={(event) => {
                              event.stopPropagation();
                              handleDeleteDocument(document.id);
                            }}
                            disabled={deletingDocumentId === document.id}
                          />
                        </div>
                        <div className="document-card__status">
                          {selectedDocumentId === document.id ? <span /> : null}
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </>
          ) : null}

          {activeTab === "summary" ? (
            <section className="summary-section">
              <div className="summary-header">
                <div>
                  <h3>Document summary</h3>
                  <p>Get a clear overview of the key ideas in your document.</p>
                </div>

                <button className="summary-button" type="button" onClick={handleGenerateSummary} disabled={summaryLoading || !selectedDocumentId}>
                  {summaryLoading ? "Generating..." : selectedDocument?.summary ? "Regenerate" : "Generate summary"}
                </button>
              </div>

              {selectedDocument?.summary ? (
                <article className="summary-card">
                  {summaryBlocks.map((block) => {
                    if (block.type === "heading") {
                      return <h4 key={block.id}>{renderInlineSummaryText(block.content)}</h4>;
                    }
                    if (block.type === "bullet") {
                      return (
                        <div className="summary-card__bullet" key={block.id}>
                          <span />
                          <p>{renderInlineSummaryText(block.content)}</p>
                        </div>
                      );
                    }
                    return <p key={block.id}>{renderInlineSummaryText(block.content)}</p>;
                  })}
                </article>
              ) : (
                <article className="summary-empty-card">
                  <div className="summary-empty-card__icon">
                    <SectionIcon name="summary" />
                  </div>
                  <h4>Ready when you are</h4>
                  <p>Click "Generate summary" to distill this document into key takeaways.</p>
                </article>
              )}
            </section>
          ) : null}

          {activeTab === "qa" ? (
            <section className="qa-section">
              <div className="qa-chat-shell">
                <div className="qa-messages">
                  {qaLoading && qaHistory.length === 0 ? (
                    <div className="qa-empty">Loading conversation...</div>
                  ) : qaHistory.length === 0 ? (
                    <div className="qa-empty">Ask your first question about this room’s documents.</div>
                  ) : (
                    qaHistory.map((entry, index) => (
                      <div className="qa-message-thread" key={`${entry.asked_at}-${index}`}>
                        <div className="qa-message qa-message--question">{entry.question}</div>
                        <div className="qa-message qa-message--answer">
                          <p>{entry.answer}</p>
                          {entry.sources?.length ? (
                            <div className="qa-sources">
                              {entry.sources.map((source, sourceIndex) => (
                                <span className="qa-source-pill" key={`${sourceIndex}-${source.slice(0, 12)}`}>
                                  {source.length > 24 ? `${source.slice(0, 24)}...` : source}
                                </span>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ))
                  )}
                </div>

                <form className="qa-composer" onSubmit={handleAskQuestion}>
                  <input
                    type="text"
                    value={questionInput}
                    onChange={(event) => setQuestionInput(event.target.value)}
                    placeholder="Ask a question about your documents..."
                  />
                  <button type="submit" disabled={qaLoading}>
                    <span aria-hidden="true">↗</span>
                  </button>
                </form>
              </div>
            </section>
          ) : null}
        </section>
      </div>
    </main>
  );
}
