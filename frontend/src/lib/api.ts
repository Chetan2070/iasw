/**
 * API Client for IASW Backend
 */

import axios from "axios";
import {
  CreateRequestData,
  RequestResponse,
  RequestSummary,
  UploadResponse,
  QueueResponse,
  QueueItem,
  ReviewData,
  ClaimResponse,
  DecisionRequest,
  DecisionResponse,
  RiskTier,
  Recommendation,
} from "@/types";
import { LoginRequest, TokenResponse, User } from "@/types/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const TOKEN_STORAGE_KEY = "iasw_tokens";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to add auth header
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (stored) {
      try {
        const { accessToken } = JSON.parse(stored);
        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
      } catch {
        // Invalid stored data
      }
    }
  }
  return config;
});

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (typeof window !== "undefined") {
        const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
        if (stored) {
          try {
            const { refreshToken } = JSON.parse(stored);
            if (refreshToken) {
              // Try to refresh the token
              const response = await axios.post<TokenResponse>(
                `${API_BASE_URL}/auth/refresh`,
                { refresh_token: refreshToken }
              );

              // Store new tokens
              localStorage.setItem(
                TOKEN_STORAGE_KEY,
                JSON.stringify({
                  accessToken: response.data.access_token,
                  refreshToken: response.data.refresh_token,
                  user: response.data.user,
                })
              );

              // Retry original request with new token
              originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
              return api(originalRequest);
            }
          } catch {
            // Refresh failed, clear tokens and redirect to login
            localStorage.removeItem(TOKEN_STORAGE_KEY);
            window.location.href = "/login";
          }
        }
      }
    }

    return Promise.reject(error);
  }
);

// Auth APIs
export const authApi = {
  /**
   * Login with username and password
   */
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>("/auth/login", data);
    return response.data;
  },

  /**
   * Refresh access token
   */
  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  /**
   * Get current user info
   */
  me: async (): Promise<User> => {
    const response = await api.get<User>("/auth/me");
    return response.data;
  },

  /**
   * Change password
   */
  changePassword: async (
    currentPassword: string,
    newPassword: string
  ): Promise<{ message: string }> => {
    const response = await api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
};

// Request APIs
export const requestsApi = {
  /**
   * Create a new change request
   */
  create: async (data: CreateRequestData): Promise<RequestResponse> => {
    const response = await api.post<RequestResponse>("/requests", data);
    return response.data;
  },

  /**
   * Upload document for a request
   */
  uploadDocument: async (
    requestId: string,
    file: File
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post<UploadResponse>(
      `/requests/${requestId}/upload`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  },

  /**
   * List requests with optional filters
   */
  list: async (params?: {
    customer_id?: string;
    change_type?: string;
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<{ items: RequestSummary[]; total: number; pages: number }> => {
    const response = await api.get("/requests", { params });
    return response.data;
  },

  /**
   * Get request details
   */
  get: async (requestId: string): Promise<RequestSummary> => {
    const response = await api.get<RequestSummary>(`/requests/${requestId}`);
    return response.data;
  },

  /**
   * Delete a request
   */
  delete: async (requestId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/requests/${requestId}`);
    return response.data;
  },

  /**
   * Get summary statistics for dashboard
   */
  getStats: async (): Promise<{
    total: number;
    pending: number;
    approved: number;
    rejected: number;
  }> => {
    const response = await api.get("/requests/stats/summary");
    return response.data;
  },
};

// Checker APIs
export const checkerApi = {
  /**
   * Get queue of pending requests
   */
  getQueue: async (params?: {
    risk_tier?: RiskTier;
    ai_recommendation?: Recommendation;
    page?: number;
    limit?: number;
  }): Promise<QueueResponse> => {
    const response = await api.get<QueueResponse>("/checker/queue", { params });
    return response.data;
  },

  /**
   * Claim a request for review
   */
  claim: async (
    requestId: string,
    checkerId: string
  ): Promise<ClaimResponse> => {
    const response = await api.post<ClaimResponse>(
      `/checker/claim/${requestId}`,
      null,
      {
        params: { checker_id: checkerId },
      }
    );
    return response.data;
  },

  /**
   * Get review data for a request
   */
  getReviewData: async (requestId: string): Promise<ReviewData> => {
    const response = await api.get<ReviewData>(`/checker/review/${requestId}`);
    return response.data;
  },

  /**
   * Submit decision on a request
   */
  submitDecision: async (
    requestId: string,
    checkerId: string,
    decision: DecisionRequest
  ): Promise<DecisionResponse> => {
    const response = await api.post<DecisionResponse>(
      `/checker/decide/${requestId}`,
      decision,
      {
        params: { checker_id: checkerId },
      }
    );
    return response.data;
  },

  /**
   * Release a claimed request
   */
  release: async (
    requestId: string,
    checkerId: string
  ): Promise<{ message: string }> => {
    const response = await api.post(`/checker/release/${requestId}`, null, {
      params: { checker_id: checkerId },
    });
    return response.data;
  },

  /**
   * Get review history for a checker
   */
  getReviewHistory: async (
    checkerId: string,
    params?: { page?: number; limit?: number }
  ): Promise<{
    items: Array<{
      request_id: string;
      customer_id: string;
      change_type: string;
      document_type: string;
      decision: string;
      decision_reason: string | null;
      decided_at: string;
      reviewed_by: string;
      ai_recommendation: string | null;
      risk_tier: string | null;
      overall_score: number | null;
    }>;
    total: number;
    page: number;
    limit: number;
  }> => {
    const response = await api.get("/checker/reviews", {
      params: { checker_id: checkerId, ...params },
    });
    return response.data;
  },
};

// Health API
export const healthApi = {
  check: async (): Promise<{ status: string; environment: string }> => {
    const response = await api.get("/health");
    return response.data;
  },
};

// Helper to get stored tokens
export const getStoredAuth = () => {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as {
      accessToken: string;
      refreshToken: string;
      user: User;
    };
  } catch {
    return null;
  }
};

// Helper to store tokens
export const setStoredAuth = (data: {
  accessToken: string;
  refreshToken: string;
  user: User;
}) => {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(data));
};

// Helper to clear tokens
export const clearStoredAuth = () => {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_STORAGE_KEY);
};

export default api;
