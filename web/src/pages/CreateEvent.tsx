import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createEvent } from "../api-client/client";

export default function CreateEvent() {
  const [name, setName] = useState("");
  const [windowMinutes, setWindowMinutes] = useState(60);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setLoading(true);
    try {
      const event = await createEvent(name.trim(), windowMinutes);
      navigate(`/events/${event.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create event");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Create event</h1>
      <form onSubmit={handleSubmit} style={{ maxWidth: "400px" }}>
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "0.25rem" }}>Event name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Cursor Hackathon Dec 24"
            style={{
              width: "100%",
              padding: "0.5rem",
              background: "#27272a",
              border: "1px solid #3f3f46",
              color: "#e4e4e7",
              borderRadius: "4px",
            }}
          />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "0.25rem" }}>Window (minutes)</label>
          <input
            type="number"
            min={1}
            value={windowMinutes}
            onChange={(e) => setWindowMinutes(Number(e.target.value) || 60)}
            style={{
              width: "100%",
              padding: "0.5rem",
              background: "#27272a",
              border: "1px solid #3f3f46",
              color: "#e4e4e7",
              borderRadius: "4px",
            }}
          />
        </div>
        {error && (
          <p style={{ color: "#f87171", marginBottom: "1rem" }}>{error}</p>
        )}
        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "0.5rem 1rem",
            background: "#7c3aed",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Creating…" : "Create"}
        </button>
      </form>
    </div>
  );
}
