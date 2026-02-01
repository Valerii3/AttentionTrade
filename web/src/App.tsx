import { useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import { Header } from "@/components/header";
import Home from "./pages/Home";
import EventDetail from "./pages/EventDetail";
import { CreateEventForm } from "./pages/CreateEvent";
import Profile from "./pages/Profile";
import { NameModal } from "./components/name-modal";
import { ProfileProvider, useProfile } from "@/contexts/profile-context";

function AppContent() {
  const { profile, saveProfile } = useProfile();
  const [nameDismissed, setNameDismissed] = useState(false);
  const [createEventOpen, setCreateEventOpen] = useState(false);
  const showNameModal = !profile && !nameDismissed;
  const navigate = useNavigate();

  function handleCreateEventSuccess(eventId?: string) {
    setCreateEventOpen(false);
    if (eventId) {
      navigate(`/events/${eventId}`);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header onOpenCreateEvent={() => setCreateEventOpen(true)} />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/events/:id" element={<EventDetail />} />
      </Routes>
      {showNameModal && (
        <NameModal
          onSubmit={saveProfile}
          onSkip={() => setNameDismissed(true)}
        />
      )}
      {createEventOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setCreateEventOpen(false)}
        >
          <div onClick={(e) => e.stopPropagation()} className="w-full flex justify-center">
            <CreateEventForm
              onClose={() => setCreateEventOpen(false)}
              onSuccess={handleCreateEventSuccess}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <ProfileProvider>
      <AppContent />
    </ProfileProvider>
  );
}

export default App;
