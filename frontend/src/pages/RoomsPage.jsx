import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import BrandMark from "../components/ui/BrandMark";
import { clearSession, createRoom, deleteRoom, fetchRooms, getStoredUser, joinRoom } from "../lib/api";
import "../styles/rooms.css";

export default function RoomsPage() {
  const navigate = useNavigate();
  const user = useMemo(() => getStoredUser(), []);
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: "", description: "" });
  const [submitting, setSubmitting] = useState(false);
  const [deletingRoomId, setDeletingRoomId] = useState("");

  async function loadRooms() {
    setLoading(true);
    setError("");

    try {
      const result = await fetchRooms();
      setRooms(result);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRooms();
  }, []);

  async function handleCreateRoom(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await createRoom(formData);
      setFormData({ name: "", description: "" });
      setIsModalOpen(false);
      await loadRooms();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteRoom(roomId) {
    setDeletingRoomId(roomId);
    setError("");

    try {
      await deleteRoom(roomId);
      setRooms((current) => current.filter((room) => room.id !== roomId));
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setDeletingRoomId("");
    }
  }

  async function handleOpenRoom(room) {
    setError("");

    try {
      if (!room.is_member && !room.can_join) {
        throw new Error("You do not have access to this room.");
      }
      if (!room.is_member && room.can_join) {
        await joinRoom(room.id);
      }
      navigate(`/documents?room_id=${room.id}`);
    } catch (roomError) {
      setError(roomError.message);
    }
  }

  function TrashButton({ label, onClick, disabled }) {
    return (
      <button
        className="room-card__delete"
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

  return (
    <main className="rooms-shell">
      <div className="rooms-app">
        <header className="rooms-topbar">
          <div className="rooms-brand">
            <BrandMark className="rooms-brand__mark" />
            <div>
              <strong>AI Study Partner</strong>
              <span>Learn smarter, together</span>
            </div>
          </div>

          <div className="rooms-userbar">
            <span>Hi, {user?.name?.toLowerCase() || "student"}</span>
            <button
              className="rooms-logout"
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

        <section className="rooms-content">
          <div className="rooms-heading-row">
            <div>
              <p className="rooms-eyebrow">Welcome back, {user?.name?.toLowerCase() || "student"}</p>
              <h1>Your study rooms</h1>
              <p className="rooms-subtitle">
                Each room is a focused space for one topic, upload material, generate summaries, and study with AI.
              </p>
            </div>

            <button className="rooms-primary-button" type="button" onClick={() => setIsModalOpen(true)}>
              <span aria-hidden="true">+</span>
              New room
            </button>
          </div>

          {error ? <div className="rooms-error">{error}</div> : null}

          {loading ? (
            <div className="rooms-empty">Loading rooms...</div>
          ) : rooms.length === 0 ? (
            <div className="rooms-empty">No rooms yet. Create your first study room.</div>
          ) : (
            <div className="rooms-grid">
              {rooms.map((room) => (
                <article className="room-card" key={room.id} onClick={() => handleOpenRoom(room)} role="button" tabIndex={0}>
                  <div className="room-card__icon">
                    <span />
                  </div>
                  <button
                    className="room-card__arrow"
                    type="button"
                    aria-label={`Open ${room.name}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      handleOpenRoom(room);
                    }}
                  >
                    →
                  </button>
                  {String(room.created_by) === String(user?.user_id) ? (
                    <TrashButton
                      label={`Delete ${room.name}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDeleteRoom(room.id);
                      }}
                      disabled={deletingRoomId === room.id}
                    />
                  ) : null}
                  <h2>{room.name}</h2>
                  <footer className="room-card__meta">
                    <span>{room.document_count} docs</span>
                    <span>{new Date(room.created_at).toLocaleDateString()}</span>
                  </footer>
                </article>
              ))}
            </div>
          )}
        </section>

        {isModalOpen ? (
          <div className="rooms-modal-backdrop" role="presentation" onClick={() => setIsModalOpen(false)}>
            <section className="rooms-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
              <header className="rooms-modal__header">
                <h2>Create a new study room</h2>
                <button type="button" onClick={() => setIsModalOpen(false)}>
                  ×
                </button>
              </header>

              <form className="rooms-modal__form" onSubmit={handleCreateRoom}>
                <label className="rooms-field">
                  <span>Room name</span>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(event) => setFormData((current) => ({ ...current, name: event.target.value }))}
                    placeholder="Organic Chemistry Final"
                    required
                  />
                </label>

                <label className="rooms-field">
                  <span>Description</span>
                  <textarea
                    value={formData.description}
                    onChange={(event) => setFormData((current) => ({ ...current, description: event.target.value }))}
                    placeholder="What are you studying in this room?"
                    rows="4"
                  />
                </label>

                <div className="rooms-modal__actions">
                  <button className="rooms-primary-button rooms-primary-button--small" type="submit" disabled={submitting}>
                    {submitting ? "Creating..." : "Create room"}
                  </button>
                </div>
              </form>
            </section>
          </div>
        ) : null}
      </div>
    </main>
  );
}
