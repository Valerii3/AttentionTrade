import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { getStoredProfile, PROFILE_KEY } from "@/lib/profile";
import type { StoredProfile } from "@/lib/profile";
import { getProfile } from "@/api-client/client";

type ProfileContextValue = {
  profile: StoredProfile | null;
  balance: number | null;
  setProfile: (p: StoredProfile | null) => void;
  saveProfile: (p: StoredProfile) => void;
  refreshBalance: () => Promise<void>;
  setBalance: (b: number) => void;
};

const ProfileContext = createContext<ProfileContextValue | null>(null);

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<StoredProfile | null>(getStoredProfile);
  const [balance, setBalance] = useState<number | null>(null);

  const saveProfile = useCallback((p: StoredProfile) => {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(p));
    setProfile(p);
  }, []);

  const refreshBalance = useCallback(async () => {
    if (!profile?.traderId) {
      setBalance(null);
      return;
    }
    try {
      const data = await getProfile(profile.traderId);
      setBalance(data.balance);
    } catch {
      // If profile doesn't exist yet, it will be created with default balance
      setBalance(100);
    }
  }, [profile?.traderId]);

  // Fetch balance when profile changes
  useEffect(() => {
    if (profile?.traderId) {
      refreshBalance();
    } else {
      setBalance(null);
    }
  }, [profile?.traderId, refreshBalance]);

  return (
    <ProfileContext.Provider value={{ profile, balance, setProfile, saveProfile, refreshBalance, setBalance }}>
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error("useProfile must be used within ProfileProvider");
  return ctx;
}
