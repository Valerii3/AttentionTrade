import { createContext, useContext, useState, useCallback } from "react";
import { getStoredProfile, PROFILE_KEY } from "@/lib/profile";
import type { StoredProfile } from "@/lib/profile";

type ProfileContextValue = {
  profile: StoredProfile | null;
  setProfile: (p: StoredProfile | null) => void;
  saveProfile: (p: StoredProfile) => void;
};

const ProfileContext = createContext<ProfileContextValue | null>(null);

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<StoredProfile | null>(getStoredProfile);

  const saveProfile = useCallback((p: StoredProfile) => {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(p));
    setProfile(p);
  }, []);

  return (
    <ProfileContext.Provider value={{ profile, setProfile, saveProfile }}>
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error("useProfile must be used within ProfileProvider");
  return ctx;
}
