import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { proposeEvent } from "../api-client/client";

const inputStyle = {
  width: "100%",
  padding: "0.5rem",
  background: "#27272a",
  border: "1px solid #3f3f46",
  color: "#e4e4e7",
  borderRadius: "4px",
};

export default function CreateEvent() {
  const [name, setName] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successModal, setSuccessModal] = useState(false);
  const [acceptedEventId, setAcceptedEventId] = useState<string | null>(null);
  const [rejectionModal, setRejectionModal] = useState(false);
  const [rejectedMessage, setRejectedMessage] = useState<string | null>(null);

  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setRejectedMessage(null);
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setLoading(true);
    try {
      const event = await proposeEvent(name.trim(), {
        sourceUrl: sourceUrl.trim() || undefined,
        description: description.trim() || undefined,
      });
      if (event.status === "open") {
        setAcceptedEventId(event.id);
        setSuccessModal(true);
      } else if (event.status === "rejected") {
        setRejectedMessage(event.rejectReason ?? "This event is not accepted for trading.");
        setRejectionModal(true);
      } else {
        setRejectedMessage(event.rejectReason ?? "This event is not accepted for trading.");
        setRejectionModal(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to propose event");
    } finally {
      setLoading(false);
    }
  }

  function closeSuccessModal() {
    setSuccessModal(false);
    if (acceptedEventId) {
      navigate(`/events/${acceptedEventId}`);
      setAcceptedEventId(null);
    }
  }

  function closeRejectionModal() {
    setRejectionModal(false);
    setRejectedMessage(null);
  }

  return (
    <div>
      {successModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10,
          }}
          onClick={closeSuccessModal}
        >
          <div
            style={{
              background: "#27272a",
              padding: "1.5rem",
              borderRadius: "8px",
              border: "1px solid #3f3f46",
              maxWidth: "320px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <p style={{ margin: "0 0 1rem 0", fontSize: "1rem" }}>Event successfully created.</p>
            <button
              type="button"
              onClick={closeSuccessModal}
              style={{
                padding: "0.5rem 1rem",
                background: "#7c3aed",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              OK
            </button>
          </div>
        </div>
      )}
      {rejectionModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10,
          }}
          onClick={closeRejectionModal}
        >
          <div
            style={{
              background: "#27272a",
              padding: "1.5rem",
              borderRadius: "8px",
              border: "1px solid #3f3f46",
              maxWidth: "320px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: "0 0 0.75rem 0", fontSize: "1.1rem" }}>Event not tradable</h3>
            <p style={{ margin: "0 0 1rem 0", fontSize: "1rem", color: "#e4e4e7" }}>
              {rejectedMessage ?? "This event is not accepted for trading."}
            </p>
            <button
              type="button"
              onClick={closeRejectionModal}
              style={{
                padding: "0.5rem 1rem",
                background: "#7c3aed",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              OK
            </button>
          </div>
        </div>
      )}
      <h1 style={{ marginTop: 0 }}>Propose event</h1>
      <form onSubmit={handleSubmit} style={{ maxWidth: "400px" }}>
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "0.25rem" }}>Event name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Cursor Hackathon Dec 24"
            style={inputStyle}
          />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "0.25rem" }}>Source URL (optional)</label>
          <input
            type="url"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            placeholder="e.g. https://reddit.com/r/cursor/..."
            style={inputStyle}
          />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "0.25rem" }}>Description (optional)</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Short context if no URL"
            rows={2}
            style={inputStyle}
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
          {loading ? "Proposing… Analyzing… Building index…" : "Propose"}
        </button>
      </form>
    </div>
  );
}
