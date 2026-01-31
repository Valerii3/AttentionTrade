import { Routes, Route, Link } from "react-router-dom";
import EventList from "./pages/EventList";
import EventDetail from "./pages/EventDetail";
import CreateEvent from "./pages/CreateEvent";

function App() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          padding: "1rem 1.5rem",
          borderBottom: "1px solid #27272a",
          display: "flex",
          alignItems: "center",
          gap: "1rem",
        }}
      >
        <Link to="/" style={{ fontWeight: 700, fontSize: "1.25rem", color: "#e4e4e7" }}>
          Attention Markets
        </Link>
        <Link to="/create">Create event</Link>
      </header>
      <main style={{ flex: 1, padding: "1.5rem" }}>
        <Routes>
          <Route path="/" element={<EventList />} />
          <Route path="/create" element={<CreateEvent />} />
          <Route path="/events/:id" element={<EventDetail />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
