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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

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
};

// Health API
export const healthApi = {
  check: async (): Promise<{ status: string; environment: string }> => {
    const response = await api.get("/health");
    return response.data;
  },
};

export default api;
