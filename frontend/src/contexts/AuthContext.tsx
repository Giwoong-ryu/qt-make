"use client";

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

// 사용자 타입
export interface User {
  id: string;
  email: string;
  name: string | null;
  church_id: string | null;
  church_name: string | null;
  role: string;
  subscription_tier: "free" | "basic" | "premium";
  monthly_usage: number;
  usage_limit: number;
}

// 교회 타입
export interface Church {
  id: string;
  name: string;
}

// AuthContext 타입
interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  setChurch: (churchId: string) => Promise<void>;
  churches: Church[];
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 토큰 저장/로드 (다른 컴포넌트에서도 사용 가능하도록 export)
export const TOKEN_KEY = "qt_access_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// API 요청 헬퍼
async function authFetch(endpoint: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "요청 실패" }));
    throw new Error(error.detail || "요청 실패");
  }

  return response.json();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [churches, setChurches] = useState<Church[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // 교회 목록 로드
  const loadChurches = useCallback(async () => {
    try {
      const data = await authFetch("/api/auth/churches");
      setChurches(data.churches || []);
    } catch (error) {
      console.error("Failed to load churches:", error);
    }
  }, []);

  // 현재 사용자 정보 로드
  const refreshUser = useCallback(async () => {
    const token = getToken();
    console.log("refreshUser called, token exists:", !!token);

    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      console.log("Calling /api/auth/me with token:", token.substring(0, 20) + "...");
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        // 토큰이 유효하지 않으면 삭제
        console.log("Token invalid, removing...");
        removeToken();
        setUser(null);
        return;
      }

      const data = await response.json();
      console.log("User loaded:", data);

      // 구독 정보 추가 로드
      if (data.church_id) {
        try {
          const [subscriptionRes, usageRes] = await Promise.all([
            fetch(`${API_URL}/api/subscription/status?church_id=${data.church_id}`, {
              headers: { "Authorization": `Bearer ${token}` },
            }),
            fetch(`${API_URL}/api/subscription/usage?church_id=${data.church_id}`, {
              headers: { "Authorization": `Bearer ${token}` },
            }),
          ]);

          if (subscriptionRes.ok && usageRes.ok) {
            const subscription = await subscriptionRes.json();
            const usage = await usageRes.json();

            data.subscription_tier = subscription.tier || "free";
            data.monthly_usage = usage.video_count || 0;
            data.usage_limit = usage.limit || 7;
          } else {
            // 기본값 설정
            data.subscription_tier = "free";
            data.monthly_usage = 0;
            data.usage_limit = 7;
          }
        } catch (err) {
          console.error("구독 정보 로드 실패:", err);
          // 기본값 설정
          data.subscription_tier = "free";
          data.monthly_usage = 0;
          data.usage_limit = 7;
        }
      } else {
        // church_id 없으면 기본값
        data.subscription_tier = "free";
        data.monthly_usage = 0;
        data.usage_limit = 7;
      }

      setUser(data);
    } catch (error) {
      console.error("Failed to load user:", error);
      removeToken();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 초기 로드
  useEffect(() => {
    loadChurches();
    refreshUser();
  }, [loadChurches, refreshUser]);

  // 로그인
  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "로그인 실패" }));
      throw new Error(error.detail || "로그인 실패");
    }

    const data = await response.json();
    console.log("Login response:", data);

    if (data.access_token) {
      // 토큰 저장
      setToken(data.access_token);
      console.log("Token saved:", data.access_token.substring(0, 20) + "...");

      // 사용자 설정
      setUser(data.user);
      setIsLoading(false);
    } else {
      throw new Error("토큰을 받지 못했습니다.");
    }
  }, []);

  // 회원가입
  const signup = useCallback(async (email: string, password: string, name?: string) => {
    const response = await fetch(`${API_URL}/api/auth/signup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password, name }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "회원가입 실패" }));
      throw new Error(error.detail || "회원가입 실패");
    }

    const data = await response.json();

    if (data.access_token) {
      setToken(data.access_token);
      setUser(data.user);
      setIsLoading(false);
    } else {
      throw new Error("토큰을 받지 못했습니다.");
    }
  }, []);

  // 로그아웃
  const logout = useCallback(async () => {
    try {
      await authFetch("/api/auth/logout", { method: "POST" });
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      removeToken();
      setUser(null);
    }
  }, []);

  // 교회 설정
  const setChurch = useCallback(async (churchId: string) => {
    const data = await authFetch("/api/auth/set-church", {
      method: "POST",
      body: JSON.stringify({ church_id: churchId }),
    });

    setUser(data.user);
  }, []);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    signup,
    logout,
    setChurch,
    churches,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
