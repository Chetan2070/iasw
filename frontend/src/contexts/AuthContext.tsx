"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
} from "react";
import { useRouter } from "next/navigation";
import {
  User,
  UserRole,
  LoginRequest,
  AuthState,
  TokenResponse,
} from "@/types/auth";
import {
  authApi,
  getStoredAuth,
  setStoredAuth,
  clearStoredAuth,
} from "@/lib/api";

interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
  hasRole: (roles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Initialize auth state from localStorage
  useEffect(() => {
    const stored = getStoredAuth();
    if (stored) {
      setState({
        user: stored.user,
        accessToken: stored.accessToken,
        refreshToken: stored.refreshToken,
        isAuthenticated: true,
        isLoading: false,
      });
    } else {
      setState((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const login = useCallback(
    async (credentials: LoginRequest) => {
      const response = await authApi.login(credentials);

      const authData = {
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
        user: response.user,
      };

      setState({
        user: response.user,
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });

      setStoredAuth(authData);

      // Redirect based on role
      // Use router.replace to avoid adding to history stack
      switch (response.user.role) {
        case "admin":
          router.replace("/admin");
          break;
        case "staff":
          router.replace("/staff");
          break;
        case "checker":
          router.replace("/checker");
          break;
        default:
          router.replace("/");
      }
    },
    [router]
  );

  const logout = useCallback(() => {
    setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
    clearStoredAuth();
    router.push("/login");
  }, [router]);

  const refreshAuth = useCallback(async () => {
    if (!state.refreshToken) {
      logout();
      return;
    }

    try {
      const response = await authApi.refresh(state.refreshToken);

      const authData = {
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
        user: response.user,
      };

      setState({
        user: response.user,
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });

      setStoredAuth(authData);
    } catch {
      logout();
    }
  }, [state.refreshToken, logout]);

  const hasRole = useCallback(
    (roles: UserRole[]) => {
      if (!state.user) return false;
      return roles.includes(state.user.role);
    },
    [state.user]
  );

  return (
    <AuthContext.Provider
      value={{ ...state, login, logout, refreshAuth, hasRole }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
