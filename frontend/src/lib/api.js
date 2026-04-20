const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "ai-study-partner-token";
const USER_KEY = "ai-study-partner-user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message =
      typeof payload === "string"
        ? payload
        : payload?.detail || "Request failed";
    throw new Error(message);
  }

  return payload;
}

function withAuth(headers = {}) {
  const token = getToken();
  return token ? { ...headers, Authorization: `Bearer ${token}` } : headers;
}

export async function login({ email, password }) {
  const body = new URLSearchParams({
    grant_type: "password",
    username: email,
    password,
    scope: "",
    client_id: "",
    client_secret: "",
  });

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });

  return parseResponse(response);
}

export async function register({ name, email, password }) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name, email, password }),
  });

  return parseResponse(response);
}

export async function fetchMe() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: withAuth(),
  });
  return parseResponse(response);
}

export async function fetchRooms() {
  const response = await fetch(`${API_BASE_URL}/rooms/`, {
    headers: withAuth(),
  });
  return parseResponse(response);
}

export async function fetchRoom(roomId) {
  const response = await fetch(`${API_BASE_URL}/rooms/${roomId}`, {
    headers: withAuth(),
  });
  return parseResponse(response);
}

export async function joinRoom(roomId) {
  const response = await fetch(`${API_BASE_URL}/rooms/${roomId}/join`, {
    method: "POST",
    headers: withAuth(),
  });
  return parseResponse(response);
}

export async function createRoom({ name, description }) {
  const response = await fetch(`${API_BASE_URL}/rooms/`, {
    method: "POST",
    headers: withAuth({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({ name, description }),
  });
  return parseResponse(response);
}

export async function deleteRoom(roomId) {
  const response = await fetch(`${API_BASE_URL}/rooms/${roomId}`, {
    method: "DELETE",
    headers: withAuth(),
  });
  return parseResponse(response);
}

export async function fetchDocuments(roomId) {
  const response = await fetch(`${API_BASE_URL}/documents/?room_id=${encodeURIComponent(roomId)}`, {
    headers: withAuth(),
  });
  return parseResponse(response);
}

export async function fetchDocument(documentId) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    headers: withAuth(),
  });
  return parseResponse(response);
}

export async function uploadDocument({ roomId, file }) {
  const formData = new FormData();
  formData.append("room_id", roomId);
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    headers: withAuth(),
    body: formData,
  });

  return parseResponse(response);
}

export async function generateSummary(documentId) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/summary`, {
    method: "POST",
    headers: withAuth(),
  });

  return parseResponse(response);
}

export async function deleteDocument(documentId) {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
    method: "DELETE",
    headers: withAuth(),
  });

  return parseResponse(response);
}

export async function fetchQaHistory(roomId) {
  const response = await fetch(`${API_BASE_URL}/qa/history/${roomId}`, {
    headers: withAuth(),
  });

  return parseResponse(response);
}

export async function askQuestion({ roomId, question }) {
  const response = await fetch(`${API_BASE_URL}/qa/ask`, {
    method: "POST",
    headers: withAuth({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      question,
      room_id: roomId,
    }),
  });

  return parseResponse(response);
}

export async function generateQuiz({ documentId, roomId, numQuestions = 5 }) {
  const response = await fetch(`${API_BASE_URL}/quiz/generate`, {
    method: "POST",
    headers: withAuth({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      document_id: documentId,
      room_id: roomId,
      num_questions: numQuestions,
    }),
  });

  return parseResponse(response);
}

export async function submitQuizAnswer({ quizSessionId, questionId, userAnswer }) {
  const response = await fetch(`${API_BASE_URL}/quiz/submit-answer`, {
    method: "POST",
    headers: withAuth({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      quiz_session_id: quizSessionId,
      question_id: questionId,
      user_answer: userAnswer,
    }),
  });

  return parseResponse(response);
}

export async function fetchQuizResults(quizSessionId) {
  const response = await fetch(`${API_BASE_URL}/quiz/results/${quizSessionId}`, {
    headers: withAuth(),
  });

  return parseResponse(response);
}

export async function fetchFlashcards(documentId) {
  const response = await fetch(`${API_BASE_URL}/flashcards/${documentId}`, {
    headers: withAuth(),
  });

  return parseResponse(response);
}

export async function generateFlashcards({ documentId, roomId, numCards = 10 }) {
  const response = await fetch(`${API_BASE_URL}/flashcards/generate`, {
    method: "POST",
    headers: withAuth({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      document_id: documentId,
      room_id: roomId,
      num_cards: numCards,
    }),
  });

  return parseResponse(response);
}
