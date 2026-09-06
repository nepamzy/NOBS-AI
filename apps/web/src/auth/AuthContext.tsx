import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, clearStoredToken, getStoredToken, storeToken } from "../api/client";
import type { AdminUser } from "../api/types";

interface AuthContextValue {
  user: AdminUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    pinCode: string,
    email: string,
    password: string,
    displayName: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getStoredToken()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => clearStoredToken())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.login({ email, password });
    storeToken(response.token);
    setUser(response.user);
  }, []);

  const signup = useCallback(
    async (pinCode: string, email: string, password: string, displayName: string) => {
      const response = await api.signup({
        pin_code: pinCode,
        email,
        password,
        display_name: displayName,
      });
      storeToken(response.token);
      setUser(response.user);
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      clearStoredToken();
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
