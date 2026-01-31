import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import { Header } from "@/components/header";
import Home from "./pages/Home";
import EventDetail from "./pages/EventDetail";
import CreateEvent from "./pages/CreateEvent";
import Profile from "./pages/Profile";
import { NameModal } from "./components/name-modal";
import { ProfileProvider, useProfile } from "@/contexts/profile-context";

function AppContent() {
  const { profile, saveProfile } = useProfile();
  const [nameDismissed, setNameDismissed] = useState(false);
  const showNameModal = !profile && !nameDismissed;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/create" element={<CreateEvent />} />
        <Route path="/events/:id" element={<EventDetail />} />
      </Routes>
      {showNameModal && (
        <NameModal
          onSubmit={saveProfile}
          onSkip={() => setNameDismissed(true)}
        />
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
