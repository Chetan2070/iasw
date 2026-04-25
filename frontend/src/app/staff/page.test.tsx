/**
 * Tests for Staff Dashboard page
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import StaffDashboard from "@/app/staff/page";
import { requestsApi } from "@/lib/api";

// Mock the API
jest.mock("@/lib/api", () => ({
  requestsApi: {
    list: jest.fn(),
  },
}));

describe("StaffDashboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render dashboard title", () => {
    (requestsApi.list as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      pages: 0,
    });

    render(<StaffDashboard />);

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("should show loading state initially", () => {
    (requestsApi.list as jest.Mock).mockReturnValue(new Promise(() => {}));

    render(<StaffDashboard />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("should display stats cards", async () => {
    (requestsApi.list as jest.Mock)
      .mockResolvedValueOnce({ items: [], total: 0, pages: 0 })
      .mockResolvedValueOnce({
        items: [
          { request_id: "1", status: "APPROVED" },
          { request_id: "2", status: "REJECTED" },
          { request_id: "3", status: "PROCESSING" },
        ],
        total: 3,
        pages: 1,
      });

    render(<StaffDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Total Requests")).toBeInTheDocument();
      expect(screen.getByText("Pending")).toBeInTheDocument();
      expect(screen.getByText("Approved")).toBeInTheDocument();
      expect(screen.getByText("Rejected")).toBeInTheDocument();
    });
  });

  it("should display recent requests", async () => {
    const mockRequests = [
      {
        request_id: "req-1",
        customer_id: "CUST-001",
        change_type: "LEGAL_NAME",
        status: "APPROVED",
        created_at: new Date().toISOString(),
      },
      {
        request_id: "req-2",
        customer_id: "CUST-002",
        change_type: "ADDRESS",
        status: "PROCESSING",
        created_at: new Date().toISOString(),
      },
    ];

    (requestsApi.list as jest.Mock)
      .mockResolvedValueOnce({ items: mockRequests, total: 2, pages: 1 })
      .mockResolvedValueOnce({ items: mockRequests, total: 2, pages: 1 });

    render(<StaffDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Recent Requests")).toBeInTheDocument();
      expect(screen.getByText("CUST-001")).toBeInTheDocument();
      expect(screen.getByText("CUST-002")).toBeInTheDocument();
    });
  });

  it("should show empty state when no requests", async () => {
    (requestsApi.list as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      pages: 0,
    });

    render(<StaffDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/no requests yet/i)).toBeInTheDocument();
    });
  });

  it("should have link to create new request", async () => {
    (requestsApi.list as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      pages: 0,
    });

    render(<StaffDashboard />);

    await waitFor(() => {
      const newRequestLink = screen.getByText("New Request").closest("a");
      expect(newRequestLink).toHaveAttribute("href", "/staff/requests/new");
    });
  });

  it("should have link to view all requests", async () => {
    (requestsApi.list as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      pages: 0,
    });

    render(<StaffDashboard />);

    await waitFor(() => {
      const viewAllLink = screen.getByText("View all").closest("a");
      expect(viewAllLink).toHaveAttribute("href", "/staff/requests");
    });
  });

  it("should calculate stats correctly", async () => {
    const mockRequests = [
      { request_id: "1", status: "APPROVED" },
      { request_id: "2", status: "COMPLETED" },
      { request_id: "3", status: "REJECTED" },
      { request_id: "4", status: "FAILED" },
      { request_id: "5", status: "PROCESSING" },
      { request_id: "6", status: "IN_REVIEW" },
    ];

    (requestsApi.list as jest.Mock)
      .mockResolvedValueOnce({ items: mockRequests.slice(0, 5), total: 5, pages: 1 })
      .mockResolvedValueOnce({ items: mockRequests, total: 6, pages: 1 });

    render(<StaffDashboard />);

    await waitFor(() => {
      // Total should be 6
      expect(screen.getByText("6")).toBeInTheDocument();
    });
  });

  it("should handle API error gracefully", async () => {
    const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    (requestsApi.list as jest.Mock).mockRejectedValue(new Error("API Error"));

    render(<StaffDashboard />);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled();
    });

    consoleSpy.mockRestore();
  });
});
