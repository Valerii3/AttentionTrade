export const PROFILE_KEY = "attentionTrade.profile";

export interface StoredProfile {
  displayName: string;
  traderId: string;
}

export function getStoredProfile(): StoredProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return null;
    const p = JSON.parse(raw) as StoredProfile;
    return p?.displayName && p?.traderId ? p : null;
  } catch {
    return null;
  }
}
