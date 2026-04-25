/**
 * Tests for API client functions
 */

import axios from "axios";
import { requestsApi, checkerApi, healthApi } from "@/lib/api";

jest.mock("axios");
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock axios.create to return the mocked axios
mockedAxios.create.mockReturnValue(mockedAxios as any);

describe("requestsApi", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("create", () => {
    it("should create a new request", async () => {
      const mockResponse = {
        data: {
          request_id: "req-123",
          status: "INTAKE_RECEIVED",
          message: "Request created successfully",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await requestsApi.create({
        customer_id: "CUST-001",
        change_type: "LEGAL_NAME",
        document_type: "MARRIAGE_CERTIFICATE",
        current_value: "John Doe",
        new_value: "John Smith",
      });

      expect(mockedAxios.post).toHaveBeenCalledWith("/requests", {
        customer_id: "CUST-001",
        change_type: "LEGAL_NAME",
        document_type: "MARRIAGE_CERTIFICATE",
        current_value: "John Doe",
        new_value: "John Smith",
      });
      expect(result.request_id).toBe("req-123");
    });

    it("should handle creation error", async () => {
      mockedAxios.post.mockRejectedValueOnce(new Error("Network error"));

      await expect(
        requestsApi.create({
          customer_id: "CUST-001",
          change_type: "LEGAL_NAME",
          document_type: "MARRIAGE_CERTIFICATE",
          current_value: "John Doe",
          new_value: "John Smith",
        })
      ).rejects.toThrow("Network error");
    });
  });

  describe("uploadDocument", () => {
    it("should upload a document", async () => {
      const mockResponse = {
        data: {
          request_id: "req-123",
          status: "VALIDATED",
          document_id: "doc-456",
          message: "Document uploaded",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const file = new File(["test content"], "test.pdf", {
        type: "application/pdf",
      });
      const result = await requestsApi.uploadDocument("req-123", file);

      expect(mockedAxios.post).toHaveBeenCalledWith(
        "/requests/req-123/upload",
        expect.any(FormData),
        expect.objectContaining({
          headers: { "Content-Type": "multipart/form-data" },
        })
      );
      expect(result.document_id).toBe("doc-456");
    });
  });

  describe("list", () => {
    it("should list requests without filters", async () => {
      const mockResponse = {
        data: {
          items: [
            { request_id: "req-1", status: "INTAKE_RECEIVED" },
            { request_id: "req-2", status: "APPROVED" },
          ],
          total: 2,
          pages: 1,
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await requestsApi.list();

      expect(mockedAxios.get).toHaveBeenCalledWith("/requests", {
        params: undefined,
      });
      expect(result.items).toHaveLength(2);
    });

    it("should list requests with filters", async () => {
      const mockResponse = {
        data: {
          items: [{ request_id: "req-1", status: "APPROVED" }],
          total: 1,
          pages: 1,
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await requestsApi.list({
        status: "APPROVED",
        customer_id: "CUST-001",
      });

      expect(mockedAxios.get).toHaveBeenCalledWith("/requests", {
        params: { status: "APPROVED", customer_id: "CUST-001" },
      });
      expect(result.items).toHaveLength(1);
    });

    it("should handle pagination", async () => {
      const mockResponse = {
        data: {
          items: [],
          total: 100,
          pages: 10,
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      await requestsApi.list({ page: 2, limit: 10 });

      expect(mockedAxios.get).toHaveBeenCalledWith("/requests", {
        params: { page: 2, limit: 10 },
      });
    });
  });

  describe("get", () => {
    it("should get a specific request", async () => {
      const mockResponse = {
        data: {
          request_id: "req-123",
          customer_id: "CUST-001",
          status: "APPROVED",
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await requestsApi.get("req-123");

      expect(mockedAxios.get).toHaveBeenCalledWith("/requests/req-123");
      expect(result.request_id).toBe("req-123");
    });

    it("should handle not found error", async () => {
      mockedAxios.get.mockRejectedValueOnce({
        response: { status: 404, data: { detail: "Not found" } },
      });

      await expect(requestsApi.get("non-existent")).rejects.toEqual({
        response: { status: 404, data: { detail: "Not found" } },
      });
    });
  });
});

describe("checkerApi", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("getQueue", () => {
    it("should get queue items", async () => {
      const mockResponse = {
        data: {
          items: [
            {
              request_id: "req-1",
              risk_tier: "HIGH",
              ai_recommendation: "MANUAL_REVIEW",
            },
          ],
          total: 1,
          page: 1,
          limit: 10,
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await checkerApi.getQueue();

      expect(mockedAxios.get).toHaveBeenCalledWith("/checker/queue", {
        params: undefined,
      });
      expect(result.items).toHaveLength(1);
    });

    it("should filter queue by risk tier", async () => {
      const mockResponse = {
        data: {
          items: [],
          total: 0,
          page: 1,
          limit: 10,
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      await checkerApi.getQueue({ risk_tier: "HIGH" });

      expect(mockedAxios.get).toHaveBeenCalledWith("/checker/queue", {
        params: { risk_tier: "HIGH" },
      });
    });
  });

  describe("claim", () => {
    it("should claim a request", async () => {
      const mockResponse = {
        data: {
          request_id: "req-123",
          status: "IN_REVIEW",
          assigned_to: "CHK-001",
          lock_expires_at: "2024-03-15T11:00:00Z",
          message: "Request claimed",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await checkerApi.claim("req-123", "CHK-001");

      expect(mockedAxios.post).toHaveBeenCalledWith(
        "/checker/claim/req-123",
        null,
        { params: { checker_id: "CHK-001" } }
      );
      expect(result.assigned_to).toBe("CHK-001");
    });

    it("should handle already claimed error", async () => {
      mockedAxios.post.mockRejectedValueOnce({
        response: { status: 409, data: { detail: "Already claimed" } },
      });

      await expect(checkerApi.claim("req-123", "CHK-001")).rejects.toEqual({
        response: { status: 409, data: { detail: "Already claimed" } },
      });
    });
  });

  describe("getReviewData", () => {
    it("should get review data for a request", async () => {
      const mockResponse = {
        data: {
          request_id: "req-123",
          customer_id: "CUST-001",
          risk_tier: "LOW",
          ai_recommendation: "APPROVE",
          overall_score: 0.95,
          field_scores: [],
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await checkerApi.getReviewData("req-123");

      expect(mockedAxios.get).toHaveBeenCalledWith("/checker/review/req-123");
      expect(result.ai_recommendation).toBe("APPROVE");
    });
  });

  describe("submitDecision", () => {
    it("should submit approval decision", async () => {
      const mockResponse = {
        data: {
          request_id: "req-123",
          decision: "APPROVE",
          new_status: "APPROVED",
          rps_updated: true,
          message: "Decision recorded",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await checkerApi.submitDecision("req-123", "CHK-001", {
        decision: "APPROVE",
      });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        "/checker/decide/req-123",
        { decision: "APPROVE" },
        { params: { checker_id: "CHK-001" } }
      );
      expect(result.rps_updated).toBe(true);
    });

    it("should submit rejection with reason", async () => {
      const mockResponse = {
        data: {
          request_id: "req-123",
          decision: "REJECT",
          new_status: "REJECTED",
          rps_updated: false,
          message: "Decision recorded",
        },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await checkerApi.submitDecision("req-123", "CHK-001", {
        decision: "REJECT",
        reason: "Document appears forged",
      });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        "/checker/decide/req-123",
        { decision: "REJECT", reason: "Document appears forged" },
        { params: { checker_id: "CHK-001" } }
      );
      expect(result.rps_updated).toBe(false);
    });
  });

  describe("release", () => {
    it("should release a claimed request", async () => {
      const mockResponse = {
        data: { message: "Request released" },
      };
      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await checkerApi.release("req-123", "CHK-001");

      expect(mockedAxios.post).toHaveBeenCalledWith(
        "/checker/release/req-123",
        null,
        { params: { checker_id: "CHK-001" } }
      );
      expect(result.message).toContain("released");
    });
  });
});

describe("healthApi", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("check", () => {
    it("should return health status", async () => {
      const mockResponse = {
        data: {
          status: "healthy",
          environment: "development",
        },
      };
      mockedAxios.get.mockResolvedValueOnce(mockResponse);

      const result = await healthApi.check();

      expect(mockedAxios.get).toHaveBeenCalledWith("/health");
      expect(result.status).toBe("healthy");
    });
  });
});
