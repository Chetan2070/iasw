"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Loader2, CheckCircle, Upload, FileText, ArrowRight } from "lucide-react";
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
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";

interface FormData {
  account_number: string;
  change_type: ChangeType | "";
  document_type: DocumentType | "";
  current_value: string;
  new_value: string;
}

export default function RequestForm() {
  const router = useRouter();
  const { success: showSuccess, error: showError } = useToast();
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

      await new Promise(resolve => setTimeout(resolve, 500));

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
      showError("Submission failed", errorMessage);
      setStep("form");
    } finally {
      setIsSubmitting(false);
    }
  };

  const fieldLabels = getFieldLabels();

  if (step === "uploading") {
    return (
      <div className="max-w-2xl mx-auto">
        <Card padding="lg" className="text-center">
          <div className="py-8">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Processing Request</h2>
            <p className="text-gray-600 mb-6">{progressMessage || "Processing..."}</p>

            <div className="w-full bg-gray-100 rounded-full h-3 mb-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-sm text-gray-500">{uploadProgress}%</p>

            <div className="mt-8 text-left space-y-3">
              {[
                { progress: 10, label: "Validating account number" },
                { progress: 30, label: "Account verified in RPS" },
                { progress: 50, label: "Uploading document" },
                { progress: 80, label: "Queued for AI processing" },
              ].map((item) => (
                <div
                  key={item.progress}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg transition-all",
                    uploadProgress >= item.progress ? "bg-green-50" : "bg-gray-50"
                  )}
                >
                  <CheckCircle
                    className={cn(
                      "h-5 w-5 transition-colors",
                      uploadProgress >= item.progress ? "text-green-500" : "text-gray-300"
                    )}
                  />
                  <span
                    className={cn(
                      "text-sm font-medium",
                      uploadProgress >= item.progress ? "text-green-700" : "text-gray-400"
                    )}
                  >
                    {item.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (step === "success") {
    return (
      <div className="max-w-2xl mx-auto">
        <Card padding="lg" className="text-center">
          <div className="py-8">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Request Submitted Successfully</h2>
            <p className="text-gray-600 mb-4">
              Your request for <strong className="text-gray-900">{customerName}</strong> has been created and the document is being processed by our AI verification system.
            </p>
            {createdRequestId && (
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
                <FileText className="h-4 w-4 text-gray-500" />
                <span className="text-sm text-gray-600">Request ID:</span>
                <span className="text-sm font-mono font-medium text-gray-900">{createdRequestId.slice(0, 16)}...</span>
              </div>
            )}
            <p className="text-sm text-gray-500 mt-6 flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Redirecting to requests list...
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <Card padding="none">
        <CardHeader
          title="New Change Request"
          description="Submit a customer account change request with supporting documentation"
          className="px-6 pt-6"
        />
        <CardContent className="px-6 pb-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <Input
              label="Account Number"
              name="account_number"
              value={formData.account_number}
              onChange={handleInputChange}
              placeholder="e.g., 1234567890"
              hint="Enter the customer's account number"
            />

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Change Type
              </label>
              <select
                name="change_type"
                value={formData.change_type}
                onChange={handleInputChange}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-200 focus:border-blue-500 bg-white text-gray-900"
              >
                <option value="">Select a change type</option>
                {Object.entries(CHANGE_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Document Type
              </label>
              <select
                name="document_type"
                value={formData.document_type}
                onChange={handleInputChange}
                disabled={!formData.change_type}
                className={cn(
                  "w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-200 focus:border-blue-500 bg-white",
                  !formData.change_type && "bg-gray-50 cursor-not-allowed text-gray-400"
                )}
              >
                <option value="">
                  {formData.change_type ? "Select a document type" : "Select change type first"}
                </option>
                {availableDocTypes.map((docType) => (
                  <option key={docType} value={docType}>
                    {DOCUMENT_TYPE_LABELS[docType]}
                  </option>
                ))}
              </select>
              {formData.change_type && (
                <p className="text-xs text-gray-500">
                  Only document types valid for {CHANGE_TYPE_LABELS[formData.change_type]} are shown
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Input
                label={fieldLabels.current}
                name="current_value"
                value={formData.current_value}
                onChange={handleInputChange}
                placeholder={`Enter ${fieldLabels.current.toLowerCase()}`}
              />
              <Input
                label={fieldLabels.new}
                name="new_value"
                value={formData.new_value}
                onChange={handleInputChange}
                placeholder={`Enter ${fieldLabels.new.toLowerCase()}`}
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-700">
                Supporting Document
              </label>
              <DocumentUploader
                onFileSelect={setSelectedFile}
                selectedFile={selectedFile}
                disabled={isSubmitting}
              />
            </div>

            <div className="pt-4 border-t border-gray-100">
              <Button
                type="submit"
                fullWidth
                size="lg"
                loading={isSubmitting}
                icon={<ArrowRight className="h-5 w-5" />}
                iconPosition="right"
              >
                Submit Request
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
