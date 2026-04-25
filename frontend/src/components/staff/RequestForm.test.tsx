/**
 * Tests for RequestForm component
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RequestForm from "@/components/staff/RequestForm";
import { requestsApi } from "@/lib/api";

// Mock the API
jest.mock("@/lib/api", () => ({
  requestsApi: {
    create: jest.fn(),
    uploadDocument: jest.fn(),
  },
}));

// Mock next/navigation
const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe("RequestForm", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render all form fields", () => {
    render(<RequestForm />);

    expect(screen.getByLabelText(/account number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/change type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/document type/i)).toBeInTheDocument();
    expect(screen.getByText(/submit request/i)).toBeInTheDocument();
  });

  it("should show document type options based on change type", async () => {
    const user = userEvent.setup();
    render(<RequestForm />);

    // Select LEGAL_NAME change type
    const changeTypeSelect = screen.getByLabelText(/change type/i);
    await user.selectOptions(changeTypeSelect, "LEGAL_NAME");

    // Check that appropriate document types are shown
    const docTypeSelect = screen.getByLabelText(/document type/i);
    expect(docTypeSelect).not.toBeDisabled();

    // Should have Marriage Certificate option for Legal Name change
    const options = docTypeSelect.querySelectorAll("option");
    const optionValues = Array.from(options).map((opt) => opt.value);
    expect(optionValues).toContain("MARRIAGE_CERTIFICATE");
    expect(optionValues).not.toContain("UTILITY_BILL"); // Not valid for LEGAL_NAME
  });

  it("should disable document type until change type is selected", () => {
    render(<RequestForm />);

    const docTypeSelect = screen.getByLabelText(/document type/i);
    expect(docTypeSelect).toBeDisabled();
  });

  it("should update field labels based on change type", async () => {
    const user = userEvent.setup();
    render(<RequestForm />);

    // Select LEGAL_NAME
    const changeTypeSelect = screen.getByLabelText(/change type/i);
    await user.selectOptions(changeTypeSelect, "LEGAL_NAME");

    expect(screen.getByLabelText(/current legal name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/new legal name/i)).toBeInTheDocument();
  });

  it("should show validation error for missing account number", async () => {
    const user = userEvent.setup();
    render(<RequestForm />);

    // Try to submit without filling anything
    const submitButton = screen.getByRole("button", { name: /submit request/i });
    await user.click(submitButton);

    expect(screen.getByText(/account number is required/i)).toBeInTheDocument();
  });

  it("should show validation error for missing change type", async () => {
    const user = userEvent.setup();
    render(<RequestForm />);

    // Fill account number only
    await user.type(screen.getByLabelText(/account number/i), "1234567890");
    await user.click(screen.getByRole("button", { name: /submit request/i }));

    expect(screen.getByText(/select a change type/i)).toBeInTheDocument();
  });

  it("should show validation error for missing document", async () => {
    const user = userEvent.setup();
    render(<RequestForm />);

    // Fill all fields except document
    await user.type(screen.getByLabelText(/account number/i), "1234567890");
    await user.selectOptions(screen.getByLabelText(/change type/i), "LEGAL_NAME");
    await user.selectOptions(
      screen.getByLabelText(/document type/i),
      "MARRIAGE_CERTIFICATE"
    );
    await user.type(screen.getByLabelText(/current legal name/i), "John Doe");
    await user.type(screen.getByLabelText(/new legal name/i), "John Smith");

    await user.click(screen.getByRole("button", { name: /submit request/i }));

    expect(screen.getByText(/upload a supporting document/i)).toBeInTheDocument();
  });

  it("should submit form successfully", async () => {
    const user = userEvent.setup();
    (requestsApi.create as jest.Mock).mockResolvedValueOnce({
      request_id: "req-123",
      status: "INTAKE_RECEIVED",
      message: "Success",
    });
    (requestsApi.uploadDocument as jest.Mock).mockResolvedValueOnce({
      document_id: "doc-456",
    });

    render(<RequestForm />);

    // Fill all fields
    await user.type(screen.getByLabelText(/account number/i), "1234567890");
    await user.selectOptions(screen.getByLabelText(/change type/i), "LEGAL_NAME");
    await user.selectOptions(
      screen.getByLabelText(/document type/i),
      "MARRIAGE_CERTIFICATE"
    );
    await user.type(screen.getByLabelText(/current legal name/i), "John Doe");
    await user.type(screen.getByLabelText(/new legal name/i), "John Smith");

    // Upload file
    const file = new File(["test"], "test.pdf", { type: "application/pdf" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    // Submit
    await user.click(screen.getByRole("button", { name: /submit request/i }));

    await waitFor(() => {
      expect(requestsApi.create).toHaveBeenCalledWith({
        account_number: "1234567890",
        change_type: "LEGAL_NAME",
        document_type: "MARRIAGE_CERTIFICATE",
        current_value: "John Doe",
        new_value: "John Smith",
      });
    });

    await waitFor(() => {
      expect(requestsApi.uploadDocument).toHaveBeenCalledWith(
        "req-123",
        expect.any(File)
      );
    });
  });

  it("should show success message after submission", async () => {
    const user = userEvent.setup();
    (requestsApi.create as jest.Mock).mockResolvedValueOnce({
      request_id: "req-123",
      status: "INTAKE_RECEIVED",
    });
    (requestsApi.uploadDocument as jest.Mock).mockResolvedValueOnce({
      document_id: "doc-456",
    });

    render(<RequestForm />);

    // Fill and submit
    await user.type(screen.getByLabelText(/account number/i), "1234567890");
    await user.selectOptions(screen.getByLabelText(/change type/i), "LEGAL_NAME");
    await user.selectOptions(
      screen.getByLabelText(/document type/i),
      "MARRIAGE_CERTIFICATE"
    );
    await user.type(screen.getByLabelText(/current legal name/i), "John Doe");
    await user.type(screen.getByLabelText(/new legal name/i), "John Smith");

    const file = new File(["test"], "test.pdf", { type: "application/pdf" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    await user.click(screen.getByRole("button", { name: /submit request/i }));

    await waitFor(() => {
      expect(screen.getByText(/submitted successfully/i)).toBeInTheDocument();
    });
  });

  it("should show error message on API failure", async () => {
    const user = userEvent.setup();
    (requestsApi.create as jest.Mock).mockRejectedValueOnce({
      response: { data: { detail: { message: "Account not found" } } },
    });

    render(<RequestForm />);

    // Fill and submit
    await user.type(screen.getByLabelText(/account number/i), "9999999999");
    await user.selectOptions(screen.getByLabelText(/change type/i), "LEGAL_NAME");
    await user.selectOptions(
      screen.getByLabelText(/document type/i),
      "MARRIAGE_CERTIFICATE"
    );
    await user.type(screen.getByLabelText(/current legal name/i), "John Doe");
    await user.type(screen.getByLabelText(/new legal name/i), "John Smith");

    const file = new File(["test"], "test.pdf", { type: "application/pdf" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    await user.click(screen.getByRole("button", { name: /submit request/i }));

    await waitFor(() => {
      expect(screen.getByText(/account not found/i)).toBeInTheDocument();
    });
  });

  it("should disable submit button while submitting", async () => {
    const user = userEvent.setup();
    let resolveCreate: (value: any) => void;
    (requestsApi.create as jest.Mock).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveCreate = resolve;
      })
    );

    render(<RequestForm />);

    // Fill all fields
    await user.type(screen.getByLabelText(/account number/i), "1234567890");
    await user.selectOptions(screen.getByLabelText(/change type/i), "LEGAL_NAME");
    await user.selectOptions(
      screen.getByLabelText(/document type/i),
      "MARRIAGE_CERTIFICATE"
    );
    await user.type(screen.getByLabelText(/current legal name/i), "John Doe");
    await user.type(screen.getByLabelText(/new legal name/i), "John Smith");

    const file = new File(["test"], "test.pdf", { type: "application/pdf" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    await user.click(screen.getByRole("button", { name: /submit request/i }));

    // Button should show loading state
    await waitFor(() => {
      expect(screen.getByText(/submitting/i)).toBeInTheDocument();
    });
  });

  it("should show correct document types for ADDRESS change", async () => {
    const user = userEvent.setup();
    render(<RequestForm />);

    await user.selectOptions(screen.getByLabelText(/change type/i), "ADDRESS");

    const docTypeSelect = screen.getByLabelText(/document type/i);
    const options = docTypeSelect.querySelectorAll("option");
    const optionValues = Array.from(options).map((opt) => opt.value);

    expect(optionValues).toContain("UTILITY_BILL");
    expect(optionValues).toContain("LEASE_AGREEMENT");
    expect(optionValues).not.toContain("MARRIAGE_CERTIFICATE");
  });
});
