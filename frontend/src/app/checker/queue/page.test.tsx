/**
 * Tests for Checker Queue page
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import QueuePage from "@/app/checker/queue/page";
import { checkerApi } from "@/lib/api";

// Mock the API
jest.mock("@/lib/api", () => ({
  checkerApi: {
    getQueue: jest.fn(),
    claim: jest.fn(),
  },
}));

// Mock next/navigation
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("QueuePage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render queue page title", async () => {
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    expect(screen.getByText("Review Queue")).toBeInTheDocument();
  });

  it("should display queue items", async () => {
    const mockItems = [
      {
        request_id: "req-123",
        customer_id: "CUST-001",
        change_type: "LEGAL_NAME",
        document_type: "MARRIAGE_CERTIFICATE",
        risk_tier: "LOW",
        ai_recommendation: "APPROVE",
        overall_score: 0.95,
        flags: [],
        queued_at: new Date().toISOString(),
        time_in_queue_minutes: 15,
      },
      {
        request_id: "req-456",
        customer_id: "CUST-002",
        change_type: "ADDRESS",
        document_type: "UTILITY_BILL",
        risk_tier: "HIGH",
        ai_recommendation: "MANUAL_REVIEW",
        overall_score: 0.65,
        flags: ["low_confidence", "potential_forgery"],
        queued_at: new Date().toISOString(),
        time_in_queue_minutes: 45,
      },
    ];

    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: mockItems,
      total: 2,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    await waitFor(() => {
      expect(screen.getByText("CUST-001")).toBeInTheDocument();
      expect(screen.getByText("CUST-002")).toBeInTheDocument();
    });
  });

  it("should show risk tier badges", async () => {
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [
        {
          request_id: "req-1",
          customer_id: "CUST-001",
          change_type: "LEGAL_NAME",
          document_type: "MARRIAGE_CERTIFICATE",
          risk_tier: "HIGH",
          ai_recommendation: "MANUAL_REVIEW",
          overall_score: 0.5,
          flags: [],
          queued_at: new Date().toISOString(),
          time_in_queue_minutes: 10,
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    await waitFor(() => {
      expect(screen.getByText("HIGH")).toBeInTheDocument();
    });
  });

  it("should display flags for items", async () => {
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [
        {
          request_id: "req-1",
          customer_id: "CUST-001",
          change_type: "LEGAL_NAME",
          document_type: "MARRIAGE_CERTIFICATE",
          risk_tier: "MEDIUM",
          ai_recommendation: "MANUAL_REVIEW",
          overall_score: 0.75,
          flags: ["low_ocr_confidence", "name_mismatch"],
          queued_at: new Date().toISOString(),
          time_in_queue_minutes: 10,
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    await waitFor(() => {
      expect(screen.getByText("low_ocr_confidence")).toBeInTheDocument();
      expect(screen.getByText("name_mismatch")).toBeInTheDocument();
    });
  });

  it("should filter by risk tier", async () => {
    const user = userEvent.setup();
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    const riskTierSelect = screen.getByDisplayValue("All Risk Tiers");
    await user.selectOptions(riskTierSelect, "HIGH");

    await waitFor(() => {
      expect(checkerApi.getQueue).toHaveBeenCalledWith(
        expect.objectContaining({ risk_tier: "HIGH" })
      );
    });
  });

  it("should filter by AI recommendation", async () => {
    const user = userEvent.setup();
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    const recommendationSelect = screen.getByDisplayValue("All Recommendations");
    await user.selectOptions(recommendationSelect, "APPROVE");

    await waitFor(() => {
      expect(checkerApi.getQueue).toHaveBeenCalledWith(
        expect.objectContaining({ ai_recommendation: "APPROVE" })
      );
    });
  });

  it("should claim request when review button is clicked", async () => {
    const user = userEvent.setup();
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [
        {
          request_id: "req-123",
          customer_id: "CUST-001",
          change_type: "LEGAL_NAME",
          document_type: "MARRIAGE_CERTIFICATE",
          risk_tier: "LOW",
          ai_recommendation: "APPROVE",
          overall_score: 0.95,
          flags: [],
          queued_at: new Date().toISOString(),
          time_in_queue_minutes: 15,
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    });
    (checkerApi.claim as jest.Mock).mockResolvedValue({
      request_id: "req-123",
      assigned_to: "CHK-001",
    });

    render(<QueuePage />);

    await waitFor(() => {
      expect(screen.getByText("Review")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Review"));

    await waitFor(() => {
      expect(checkerApi.claim).toHaveBeenCalledWith("req-123", "CHK-001");
      expect(mockPush).toHaveBeenCalledWith("/checker/review/req-123");
    });
  });

  it("should show error when claim fails", async () => {
    const user = userEvent.setup();
    const alertMock = jest.spyOn(window, "alert").mockImplementation(() => {});

    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [
        {
          request_id: "req-123",
          customer_id: "CUST-001",
          change_type: "LEGAL_NAME",
          document_type: "MARRIAGE_CERTIFICATE",
          risk_tier: "LOW",
          ai_recommendation: "APPROVE",
          overall_score: 0.95,
          flags: [],
          queued_at: new Date().toISOString(),
          time_in_queue_minutes: 15,
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    });
    (checkerApi.claim as jest.Mock).mockRejectedValue({
      response: { data: { detail: "Already claimed" } },
    });

    render(<QueuePage />);

    await waitFor(() => {
      expect(screen.getByText("Review")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Review"));

    await waitFor(() => {
      expect(alertMock).toHaveBeenCalledWith("Already claimed");
    });

    alertMock.mockRestore();
  });

  it("should show empty state when queue is empty", async () => {
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    await waitFor(() => {
      expect(screen.getByText("No items in queue")).toBeInTheDocument();
    });
  });

  it("should refresh queue when refresh button is clicked", async () => {
    const user = userEvent.setup();
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    await waitFor(() => {
      expect(checkerApi.getQueue).toHaveBeenCalledTimes(1);
    });

    await user.click(screen.getByText("Refresh"));

    await waitFor(() => {
      expect(checkerApi.getQueue).toHaveBeenCalledTimes(2);
    });
  });

  it("should display wait time for items", async () => {
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [
        {
          request_id: "req-1",
          customer_id: "CUST-001",
          change_type: "LEGAL_NAME",
          document_type: "MARRIAGE_CERTIFICATE",
          risk_tier: "LOW",
          ai_recommendation: "APPROVE",
          overall_score: 0.95,
          flags: [],
          queued_at: new Date().toISOString(),
          time_in_queue_minutes: 30,
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    await waitFor(() => {
      expect(screen.getByText("30m")).toBeInTheDocument();
    });
  });

  it("should clear filters when clear button is clicked", async () => {
    const user = userEvent.setup();
    (checkerApi.getQueue as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      limit: 10,
    });

    render(<QueuePage />);

    // Set a filter
    const riskTierSelect = screen.getByDisplayValue("All Risk Tiers");
    await user.selectOptions(riskTierSelect, "HIGH");

    await waitFor(() => {
      expect(screen.getByText("Clear filters")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Clear filters"));

    await waitFor(() => {
      expect(screen.queryByText("Clear filters")).not.toBeInTheDocument();
    });
  });
});
