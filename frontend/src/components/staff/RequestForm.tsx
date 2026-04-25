"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Loader2, CheckCircle } from "lucide-react";
import { requestsApi } from "@/lib/api";
import {
  ChangeType,
  DocumentType,
  CHANGE_TYPE_LABELS,
  DOCUMENT_TYPE_LABELS,
  ALLOWED_DOCUMENTS,
} from "@/types";
import DocumentUploader from "./DocumentUploader";
import { cn } from "@/lib/utils";

interface FormData {
  account_number: string;
  change_type: ChangeType | "";
  document_type: DocumentType | "";
  current_value: string;
  new_value: string;
}

export default function RequestForm() {
  const router = useRouter();
  const [formData, setFormData] = useState<FormData>({
    account_number: "",
    change_type: "",
    document_type: "",
    current_value: "",
    new_value: "",
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [availableDocTypes, setAvailableDocTypes] = useState<DocumentType[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [step, setStep] = useState<"form" | "uploading" | "success">("form");
  const [error, setError] = useState<string | null>(null);
  const [createdRequestId, setCreatedRequestId] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState<string | null>(null);

  useEffect(() => {
    if (formData.change_type) {
      setAvailableDocTypes(ALLOWED_DOCUMENTS[formData.change_type]);
      setFormData((prev) => ({ ...prev, document_type: "" }));
    } else {
      setAvailableDocTypes([]);
    }
  }, [formData.change_type]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError(null);
  };

  const getFieldLabels = () => {
    switch (formData.change_type) {
      case "LEGAL_NAME":
        return { current: "Current Legal Name", new: "New Legal Name" };
      case "ADDRESS":
        return { current: "Current Address", new: "New Address" };
      case "DOB":
        return { current: "Current Date of Birth", new: "Corrected Date of Birth" };
      case "CONTACT":
        return { current: "Current Contact/Email", new: "New Contact/Email" };
      default:
        return { current: "Current Value", new: "New Value" };
    }
  };

  const validateForm = (): boolean => {
    if (!formData.account_number.trim()) {
      setError("Account number is required");
      return false;
    }
    if (!formData.change_type) {
      setError("Please select a change type");
      return false;
    }
    if (!formData.document_type) {
      setError("Please select a document type");
      return false;
    }
    if (!formData.current_value.trim()) {
      setError("Current value is required");
      return false;
    }
    if (!formData.new_value.trim()) {
      setError("New value is required");
      return false;
    }
    if (!selectedFile) {
      setError("Please upload a supporting document");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) return;

    setIsSubmitting(true);
    setStep("uploading");

    try {
      // Step 1: Create the request (validates account)
      setUploadProgress(10);
      setProgressMessage("Validating account number...");

      const createResponse = await requestsApi.create({
        account_number: formData.account_number,
        change_type: formData.change_type as ChangeType,
        document_type: formData.document_type as DocumentType,
        current_value: formData.current_value,
        new_value: formData.new_value,
      });

      setUploadProgress(30);
      setProgressMessage(`Account verified: ${createResponse.customer_name || "Customer found"}`);
      setCreatedRequestId(createResponse.request_id);
      setCustomerName(createResponse.customer_name || null);

      // Brief pause to show the account verification message
      await new Promise(resolve => setTimeout(resolve, 500));

      // Step 2: Upload the document
      setUploadProgress(50);
      setProgressMessage("Uploading document...");

      if (selectedFile) {
        await requestsApi.uploadDocument(createResponse.request_id, selectedFile);
      }

      setUploadProgress(80);
      setProgressMessage("Document uploaded. Queuing for AI processing...");

      await new Promise(resolve => setTimeout(resolve, 500));

      setUploadProgress(100);
      setProgressMessage("Request submitted successfully!");
      setStep("success");

      // Redirect after a short delay
      setTimeout(() => {
        router.push("/staff/requests");
      }, 2000);
    } catch (err: any) {
      console.error("Submission error:", err);
      const errorDetail = err.response?.data?.detail;
      let errorMessage = "Failed to submit request. Please try again.";

      if (errorDetail) {
        if (typeof errorDetail === "object" && errorDetail.message) {
          errorMessage = errorDetail.message;
        } else if (typeof errorDetail === "string") {
          errorMessage = errorDetail;
        }
      } else if (err.message) {
        errorMessage = err.message;
      }

      setError(errorMessage);
      setStep("form");
    } finally {
      setIsSubmitting(false);
    }
  };

  const fieldLabels = getFieldLabels();

  if (step === "uploading") {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <Loader2 className="h-12 w-12 text-blue-600 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Processing Request
          </h2>
          <p className="text-gray-600 mb-4">
            {progressMessage || "Processing..."}
          </p>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-sm text-gray-500 mt-2">{uploadProgress}%</p>

          {/* Progress Steps */}
          <div className="mt-6 text-left space-y-2">
            <div className={`flex items-center gap-2 ${uploadProgress >= 10 ? "text-green-600" : "text-gray-400"}`}>
              <CheckCircle className={`h-4 w-4 ${uploadProgress >= 10 ? "" : "opacity-30"}`} />
              <span className="text-sm">Validating account number</span>
            </div>
            <div className={`flex items-center gap-2 ${uploadProgress >= 30 ? "text-green-600" : "text-gray-400"}`}>
              <CheckCircle className={`h-4 w-4 ${uploadProgress >= 30 ? "" : "opacity-30"}`} />
              <span className="text-sm">Account verified in RPS</span>
            </div>
            <div className={`flex items-center gap-2 ${uploadProgress >= 50 ? "text-green-600" : "text-gray-400"}`}>
              <CheckCircle className={`h-4 w-4 ${uploadProgress >= 50 ? "" : "opacity-30"}`} />
              <span className="text-sm">Uploading document</span>
            </div>
            <div className={`flex items-center gap-2 ${uploadProgress >= 80 ? "text-green-600" : "text-gray-400"}`}>
              <CheckCircle className={`h-4 w-4 ${uploadProgress >= 80 ? "" : "opacity-30"}`} />
              <span className="text-sm">Queued for AI processing</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (step === "success") {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Request Submitted Successfully
          </h2>
          <p className="text-gray-600 mb-4">
            Your request for <strong>{customerName}</strong> has been created and the document
            is being processed by our AI verification system.
          </p>
          {createdRequestId && (
            <p className="text-sm text-gray-500">
              Request ID: <span className="font-mono">{createdRequestId}</span>
            </p>
          )}
          <p className="text-sm text-gray-500 mt-4">
            Redirecting to requests list...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            New Change Request
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Submit a customer account change request with supporting documentation
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Account Number */}
          <div>
            <label
              htmlFor="account_number"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Account Number <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="account_number"
              name="account_number"
              value={formData.account_number}
              onChange={handleInputChange}
              placeholder="e.g., 1234567890"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Change Type */}
          <div>
            <label
              htmlFor="change_type"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Change Type <span className="text-red-500">*</span>
            </label>
            <select
              id="change_type"
              name="change_type"
              value={formData.change_type}
              onChange={handleInputChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a change type</option>
              {Object.entries(CHANGE_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Document Type */}
          <div>
            <label
              htmlFor="document_type"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Document Type <span className="text-red-500">*</span>
            </label>
            <select
              id="document_type"
              name="document_type"
              value={formData.document_type}
              onChange={handleInputChange}
              disabled={!formData.change_type}
              className={cn(
                "w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
                !formData.change_type && "bg-gray-100 cursor-not-allowed"
              )}
            >
              <option value="">
                {formData.change_type
                  ? "Select a document type"
                  : "Select change type first"}
              </option>
              {availableDocTypes.map((docType) => (
                <option key={docType} value={docType}>
                  {DOCUMENT_TYPE_LABELS[docType]}
                </option>
              ))}
            </select>
            {formData.change_type && (
              <p className="text-xs text-gray-500 mt-1">
                Only document types valid for {CHANGE_TYPE_LABELS[formData.change_type]} are shown
              </p>
            )}
          </div>

          {/* Current Value */}
          <div>
            <label
              htmlFor="current_value"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              {fieldLabels.current} <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="current_value"
              name="current_value"
              value={formData.current_value}
              onChange={handleInputChange}
              placeholder={`Enter ${fieldLabels.current.toLowerCase()}`}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* New Value */}
          <div>
            <label
              htmlFor="new_value"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              {fieldLabels.new} <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="new_value"
              name="new_value"
              value={formData.new_value}
              onChange={handleInputChange}
              placeholder={`Enter ${fieldLabels.new.toLowerCase()}`}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Document Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Supporting Document <span className="text-red-500">*</span>
            </label>
            <DocumentUploader
              onFileSelect={setSelectedFile}
              selectedFile={selectedFile}
              disabled={isSubmitting}
            />
          </div>

          {/* Submit Button */}
          <div className="pt-4 border-t border-gray-200">
            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                "w-full py-3 px-4 rounded-lg font-medium transition-colors",
                isSubmitting
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              )}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Submitting...
                </span>
              ) : (
                "Submit Request"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
