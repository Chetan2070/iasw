/**
 * Tests for DocumentUploader component
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DocumentUploader from "@/components/staff/DocumentUploader";

describe("DocumentUploader", () => {
  const mockOnFileSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should render upload area when no file is selected", () => {
    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
      />
    );

    expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
    expect(screen.getByText(/browse/i)).toBeInTheDocument();
  });

  it("should display selected file information", () => {
    const file = new File(["test content"], "test-document.pdf", {
      type: "application/pdf",
    });

    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={file}
      />
    );

    expect(screen.getByText("test-document.pdf")).toBeInTheDocument();
  });

  it("should call onFileSelect when file is selected via input", async () => {
    const user = userEvent.setup();
    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
      />
    );

    const file = new File(["test content"], "test.pdf", {
      type: "application/pdf",
    });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    await user.upload(input, file);

    expect(mockOnFileSelect).toHaveBeenCalledWith(file);
  });

  it("should remove file when remove button is clicked", async () => {
    const user = userEvent.setup();
    const file = new File(["test content"], "test.pdf", {
      type: "application/pdf",
    });

    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={file}
      />
    );

    const removeButton = screen.getByRole("button");
    await user.click(removeButton);

    expect(mockOnFileSelect).toHaveBeenCalledWith(null);
  });

  it("should display error message when error prop is provided", () => {
    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
        error="Invalid file type"
      />
    );

    expect(screen.getByText("Invalid file type")).toBeInTheDocument();
  });

  it("should be disabled when disabled prop is true", () => {
    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
        disabled={true}
      />
    );

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeDisabled();
  });

  it("should show supported formats text", () => {
    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
      />
    );

    expect(screen.getByText(/PDF, JPG, PNG/i)).toBeInTheDocument();
  });

  it("should handle drag over state", () => {
    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
      />
    );

    const dropZone = screen.getByText(/drag and drop/i).closest("div");

    fireEvent.dragOver(dropZone!);
    // Visual state changes would be tested with visual regression tests
  });

  it("should handle drop event", async () => {
    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
      />
    );

    const file = new File(["test content"], "dropped.pdf", {
      type: "application/pdf",
    });
    const dropZone = screen.getByText(/drag and drop/i).closest("div");

    const dropEvent = {
      preventDefault: jest.fn(),
      dataTransfer: {
        files: [file],
      },
    };

    fireEvent.drop(dropZone!, dropEvent);

    await waitFor(() => {
      expect(mockOnFileSelect).toHaveBeenCalled();
    });
  });

  it("should reject files larger than 10MB", async () => {
    const alertMock = jest.spyOn(window, "alert").mockImplementation(() => {});
    const user = userEvent.setup();

    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
      />
    );

    // Create a file larger than 10MB
    const largeContent = new ArrayBuffer(11 * 1024 * 1024);
    const file = new File([largeContent], "large.pdf", {
      type: "application/pdf",
    });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    // Simulate the file selection
    Object.defineProperty(input, "files", {
      value: [file],
    });
    fireEvent.change(input);

    expect(alertMock).toHaveBeenCalledWith(expect.stringContaining("10MB"));
    expect(mockOnFileSelect).not.toHaveBeenCalled();

    alertMock.mockRestore();
  });

  it("should reject invalid file types", async () => {
    const alertMock = jest.spyOn(window, "alert").mockImplementation(() => {});

    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={null}
      />
    );

    const file = new File(["test"], "test.exe", {
      type: "application/x-msdownload",
    });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, "files", {
      value: [file],
    });
    fireEvent.change(input);

    expect(alertMock).toHaveBeenCalledWith(
      expect.stringContaining("PDF, JPG, and PNG")
    );
    expect(mockOnFileSelect).not.toHaveBeenCalled();

    alertMock.mockRestore();
  });

  it("should display file size correctly", () => {
    const file = new File(["x".repeat(1500000)], "medium.pdf", {
      type: "application/pdf",
    });
    Object.defineProperty(file, "size", { value: 1500000 });

    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={file}
      />
    );

    expect(screen.getByText(/MB|KB/)).toBeInTheDocument();
  });

  it("should show success indicator for valid file", () => {
    const file = new File(["test content"], "valid.pdf", {
      type: "application/pdf",
    });

    render(
      <DocumentUploader
        onFileSelect={mockOnFileSelect}
        selectedFile={file}
      />
    );

    // Check for green success styling
    const container = screen.getByText("valid.pdf").closest("div");
    expect(container?.className).toContain("green");
  });
});
