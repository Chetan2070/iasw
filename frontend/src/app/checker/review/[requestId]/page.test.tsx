/**
 * Tests for Review page
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ReviewPage from "@/app/checker/review/[requestId]/page";
import { checkerApi } from "@/lib/api";

// Mock the API
jest.mock("@/lib/api", () => ({
  checkerApi: {
    getReviewData: jest.fn(),
    submitDecision: jest.fn(),
    release: jest.fn(),
  },
}));

// Mock next/navigation
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useParams: () => ({
    requestId: "req-123",
  }),
}));

const mockReviewData = {
  request_id: "req-123",
  customer_id: "CUST-001",
  change_type: "LEGAL_NAME",
  document_type: "MARRIAGE_CERTIFICATE",
  requested_old_value: "John Doe",
  requested_new_value: "John Smith",
  extracted_old_value: "John Doe",
  extracted_new_value: "John Smith",
  field_scores: [
    {
      field_name: "old_name",
      extracted_value: "John Doe",
      expected_value: "John Doe",
      match_score: 1.0,
      match_method: "exact",
    },
    {
      field_name: "new_name",
      extracted_value: "John Smith",
      expected_value: "John Smith",
      match_score: 1.0,
      match_method: "exact",
    },
  ],
  ocr_confidence: 0.95,
  extraction_confidence: 0.93,
  doc_authenticity_score: 0.91,
  overall_score: 0.92,
  forgery_score: 0.08,
  forgery_result: "Document appears authentic",
  forgery_details: {
    metadata_score: 0.05,
    ela_score: 0.1,
  },
  risk_tier: "LOW",
  flags: [],
  ai_recommendation: "APPROVE",
  ai_summary: "Document verified successfully. High confidence match.",
  document_url: null,
  filenet_reference: null,
  created_at: new Date().toISOString(),
  staged_at: new Date().toISOString(),
  claimed_at: new Date().toISOString(),
};

describe("ReviewPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render review page with data", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Review Request")).toBeInTheDocument();
      expect(screen.getByText("CUST-001")).toBeInTheDocument();
    });
  });

  it("should display request details", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Request Details")).toBeInTheDocument();
      expect(screen.getByText("Legal Name Change")).toBeInTheDocument();
      expect(screen.getByText("Marriage Certificate")).toBeInTheDocument();
    });
  });

  it("should display extracted data", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Extracted Data")).toBeInTheDocument();
      expect(screen.getByText("John Doe")).toBeInTheDocument();
      expect(screen.getByText("John Smith")).toBeInTheDocument();
    });
  });

  it("should display confidence scores", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Confidence Scores")).toBeInTheDocument();
      expect(screen.getByText("Overall Score")).toBeInTheDocument();
      expect(screen.getByText("92%")).toBeInTheDocument();
    });
  });

  it("should display AI recommendation", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("AI Assessment")).toBeInTheDocument();
      expect(screen.getByText("LOW")).toBeInTheDocument();
      expect(screen.getByText("APPROVE")).toBeInTheDocument();
    });
  });

  it("should display AI summary", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("AI Summary")).toBeInTheDocument();
      expect(
        screen.getByText(/document verified successfully/i)
      ).toBeInTheDocument();
    });
  });

  it("should display forgery analysis", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Forgery Analysis")).toBeInTheDocument();
      expect(screen.getByText("Authenticity Score")).toBeInTheDocument();
    });
  });

  it("should show decision buttons", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Approve")).toBeInTheDocument();
      expect(screen.getByText("Reject")).toBeInTheDocument();
      expect(screen.getByText("More Info")).toBeInTheDocument();
      expect(screen.getByText("Escalate")).toBeInTheDocument();
    });
  });

  it("should submit approval decision", async () => {
    const user = userEvent.setup();
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);
    (checkerApi.submitDecision as jest.Mock).mockResolvedValue({
      request_id: "req-123",
      decision: "APPROVE",
      new_status: "APPROVED",
      rps_updated: true,
    });

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Approve")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Approve"));
    await user.click(screen.getByText("Submit Decision"));

    await waitFor(() => {
      expect(checkerApi.submitDecision).toHaveBeenCalledWith(
        "req-123",
        "CHK-001",
        { decision: "APPROVE" }
      );
      expect(mockPush).toHaveBeenCalledWith("/checker/queue");
    });
  });

  it("should require reason for rejection", async () => {
    const user = userEvent.setup();
    const alertMock = jest.spyOn(window, "alert").mockImplementation(() => {});
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Reject")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Reject"));
    await user.click(screen.getByText("Submit Decision"));

    expect(alertMock).toHaveBeenCalledWith(
      expect.stringContaining("reason")
    );

    alertMock.mockRestore();
  });

  it("should submit rejection with reason", async () => {
    const user = userEvent.setup();
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);
    (checkerApi.submitDecision as jest.Mock).mockResolvedValue({
      request_id: "req-123",
      decision: "REJECT",
      new_status: "REJECTED",
      rps_updated: false,
    });

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Reject")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Reject"));

    const reasonInput = screen.getByPlaceholderText(/provide reason/i);
    await user.type(reasonInput, "Document appears forged");

    await user.click(screen.getByText("Submit Decision"));

    await waitFor(() => {
      expect(checkerApi.submitDecision).toHaveBeenCalledWith(
        "req-123",
        "CHK-001",
        { decision: "REJECT", reason: "Document appears forged" }
      );
    });
  });

  it("should release request when release button is clicked", async () => {
    const user = userEvent.setup();
    const confirmMock = jest.spyOn(window, "confirm").mockReturnValue(true);
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);
    (checkerApi.release as jest.Mock).mockResolvedValue({ message: "Released" });

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Release to Queue")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Release to Queue"));

    await waitFor(() => {
      expect(checkerApi.release).toHaveBeenCalledWith("req-123", "CHK-001");
      expect(mockPush).toHaveBeenCalledWith("/checker/queue");
    });

    confirmMock.mockRestore();
  });

  it("should handle error loading review data", async () => {
    (checkerApi.getReviewData as jest.Mock).mockRejectedValue({
      response: { data: { detail: "Not found" } },
    });

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it("should display flags when present", async () => {
    const dataWithFlags = {
      ...mockReviewData,
      flags: ["low_confidence", "name_mismatch"],
    };
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(dataWithFlags);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("low_confidence")).toBeInTheDocument();
      expect(screen.getByText("name_mismatch")).toBeInTheDocument();
    });
  });

  it("should display field match scores", async () => {
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Field Match Scores")).toBeInTheDocument();
      expect(screen.getByText("old_name")).toBeInTheDocument();
      expect(screen.getByText("new_name")).toBeInTheDocument();
    });
  });

  it("should show loading state initially", () => {
    (checkerApi.getReviewData as jest.Mock).mockReturnValue(
      new Promise(() => {})
    );

    render(<ReviewPage />);

    // Loading indicator should be visible
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("should highlight selected decision button", async () => {
    const user = userEvent.setup();
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Approve")).toBeInTheDocument();
    });

    const approveButton = screen.getByText("Approve").closest("button");
    await user.click(approveButton!);

    // Button should have selected styling
    expect(approveButton?.className).toContain("green");
  });

  it("should show reason input only for non-approve decisions", async () => {
    const user = userEvent.setup();
    (checkerApi.getReviewData as jest.Mock).mockResolvedValue(mockReviewData);

    render(<ReviewPage />);

    await waitFor(() => {
      expect(screen.getByText("Approve")).toBeInTheDocument();
    });

    // Select approve - no reason input
    await user.click(screen.getByText("Approve"));
    expect(screen.queryByPlaceholderText(/provide reason/i)).not.toBeInTheDocument();

    // Select reject - reason input appears
    await user.click(screen.getByText("Reject"));
    expect(screen.getByPlaceholderText(/provide reason/i)).toBeInTheDocument();
  });
});
