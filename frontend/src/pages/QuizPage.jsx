import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import BrandMark from "../components/ui/BrandMark";
import SectionIcon from "../components/ui/SectionIcon";
import {
  clearSession,
  fetchDocuments,
  fetchQuizResults,
  fetchRoom,
  generateQuiz,
  getStoredUser,
  submitQuizAnswer,
} from "../lib/api";
import "../styles/study-tools.css";

export default function QuizPage() {
  const [searchParams] = useSearchParams();
  const roomId = searchParams.get("room_id");
  const initialDocumentId = searchParams.get("document_id") || "";
  const user = useMemo(() => getStoredUser(), []);
  const [room, setRoom] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState(initialDocumentId);
  const [quiz, setQuiz] = useState(null);
  const [results, setResults] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answerState, setAnswerState] = useState({});
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [submittingId, setSubmittingId] = useState("");
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

  async function handleGenerateQuiz() {
    if (!roomId || !selectedDocumentId) {
      setError("Choose a document first.");
      return;
    }

    setGenerating(true);
    setError("");
    setQuiz(null);
    setResults(null);
    setCurrentIndex(0);
    setAnswerState({});

    try {
      const nextQuiz = await generateQuiz({
        roomId,
        documentId: selectedDocumentId,
      });
      setQuiz(nextQuiz);
    } catch (generateError) {
      setError(generateError.message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleOptionClick(question, choice) {
    if (!quiz?.quiz_session_id || answerState[question.id]?.answered) {
      return;
    }

    setSubmittingId(question.id);
    setError("");

    try {
      const submission = await submitQuizAnswer({
        quizSessionId: quiz.quiz_session_id,
        questionId: question.id,
        userAnswer: choice,
      });

      setAnswerState((current) => ({
        ...current,
        [question.id]: {
          answered: true,
          selected: choice,
          correctOption: submission.correct_option,
          isCorrect: submission.is_correct,
        },
      }));

      const latestResults = await fetchQuizResults(quiz.quiz_session_id);
      setResults(latestResults);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmittingId("");
    }
  }

  const questions = quiz?.questions || [];
  const currentQuestion = questions[currentIndex];
  const currentAnswer = currentQuestion ? answerState[currentQuestion.id] : null;
  const quizComplete = Boolean(results && questions.length > 0 && currentIndex >= questions.length);

  function getOptionClass(questionId, optionLabel) {
    const state = answerState[questionId];
    if (!state) {
      return "";
    }
    if (!state.answered && state.selected === optionLabel) {
      return "is-selected";
    }
    if (state.answered && optionLabel === state.correctOption) {
      return "is-correct-option";
    }
    if (state.answered && optionLabel === state.selected) {
      return "is-wrong-option";
    }
    return "";
  }

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
              <h1>{room?.name || "Quiz"}</h1>
            </div>
          </header>

          <nav className="study-tabs" aria-label="Room sections">
            <Link className="study-tab" to={roomId ? `/documents?room_id=${roomId}` : "/rooms"}><SectionIcon name="documents" />Documents</Link>
            <Link className="study-tab" to={roomId ? `/documents?room_id=${roomId}&tab=summary` : "/rooms"}><SectionIcon name="summary" />Summary</Link>
            <Link className="study-tab" to={roomId ? `/documents?room_id=${roomId}&tab=qa` : "/rooms"}><SectionIcon name="qa" />Q&amp;A</Link>
            <button className="study-tab is-active" type="button"><SectionIcon name="quiz" />Quiz</button>
            <Link className="study-tab" to={roomId ? `/flashcards?room_id=${roomId}&document_id=${selectedDocumentId}` : "/rooms"}><SectionIcon name="flashcards" />Flashcards</Link>
          </nav>

          {error ? <div className="study-feedback study-feedback--error">{error}</div> : null}

          {loading ? (
            <div className="study-feedback">Loading quiz workspace...</div>
          ) : (
            <>
              {currentQuestion ? (
                <section className="study-stack">
                  <div className="quiz-progress-row">
                    <span>
                      Question {currentIndex + 1} of {questions.length}
                    </span>
                    <div className="quiz-progress-track" aria-hidden="true">
                      <div
                        className="quiz-progress-bar"
                        style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
                      />
                    </div>
                  </div>

                  <article className="study-question-card study-question-card--single">
                    <h3>{currentQuestion.question_text}</h3>

                    <div className="study-options study-options--grid">
                      {[
                        ["A", currentQuestion.option_a],
                        ["B", currentQuestion.option_b],
                        ["C", currentQuestion.option_c],
                        ["D", currentQuestion.option_d],
                      ].map(([label, value]) => (
                        <button
                          key={label}
                          className={`study-option study-option--button ${getOptionClass(currentQuestion.id, label)}`}
                          type="button"
                          onClick={() => handleOptionClick(currentQuestion, label)}
                          disabled={Boolean(currentAnswer?.answered) || submittingId === currentQuestion.id}
                        >
                          <span>{label}</span>
                          <p>{value}</p>
                          {currentAnswer?.answered ? (
                            <strong className="study-option__status">
                              {label === currentAnswer.correctOption ? "Correct" : label === currentAnswer.selected ? "Incorrect" : ""}
                            </strong>
                          ) : null}
                        </button>
                      ))}
                    </div>

                    {submittingId === currentQuestion.id ? (
                      <div className="study-feedback">Checking answer...</div>
                    ) : null}

                    {currentAnswer?.answered ? (
                      <div className="quiz-card-footer">
                        <strong className={currentAnswer.isCorrect ? "is-correct" : "is-incorrect"}>
                          {currentAnswer.isCorrect
                            ? "Correct answer"
                            : `Incorrect. Correct answer: ${currentAnswer.correctOption}`}
                        </strong>
                        <button
                          className="study-primary-button"
                          type="button"
                          onClick={() => setCurrentIndex((current) => current + 1)}
                        >
                          {currentIndex === questions.length - 1 ? "Finish quiz" : "Next question"}
                        </button>
                      </div>
                    ) : null}
                  </article>
                </section>
              ) : quizComplete ? (
                <section className="study-stack">
                  <section className="study-panel study-panel--score">
                    <h2>
                      Score: {results.correct_answers}/{results.total_questions}
                    </h2>
                    <p>{results.score_percent}% correct</p>
                  </section>
                  <section className="study-panel study-panel--empty">
                    <h2>Quiz complete</h2>
                    <p>Generate another quiz to keep practicing with this document.</p>
                  </section>
                </section>
              ) : (
                <section className="study-panel study-panel--empty">
                  <div className="study-empty-icon">
                    <SectionIcon name="quiz" />
                  </div>
                  <h2>Test what you know</h2>
                  <p>Generate a 5-question multiple choice quiz from your selected document.</p>
                  <div className="study-actions">
                    <button
                      className="study-primary-button"
                      type="button"
                      onClick={handleGenerateQuiz}
                      disabled={generating || !selectedDocumentId}
                    >
                      {generating ? "Generating..." : "Generate quiz"}
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
