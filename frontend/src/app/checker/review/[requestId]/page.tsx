"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  User,
  Calendar,
  Shield,
  Eye,
  MessageSquare,
  Loader2,
} from "lucide-react";
import { checkerApi } from "@/lib/api";
import {
  ReviewData,
  Decision,
  CHANGE_TYPE_LABELS,
  DOCUMENT_TYPE_LABELS,
  RISK_TIER_COLORS,
  RECOMMENDATION_COLORS,
} from "@/types";
import { cn, formatPercentage, formatDate } from "@/lib/utils";

const CHECKER_ID = "CHK-001";

export default function ReviewPage() {
  const router = useRouter();
  const params = useParams();
  const requestId = params.requestId as string;

  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [decision, setDecision] = useState<Decision | "">("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReviewData() {
      try {
        const data = await checkerApi.getReviewData(requestId);
        setReviewData(data);
      } catch (err: any) {
        console.error("Failed to fetch review data:", err);
        setError(err.response?.data?.detail || "Failed to load review data");
      } finally {
        setLoading(false);
      }
    }

    fetchReviewData();
  }, [requestId]);

  const handleDecision = async () => {
    if (!decision) {
      alert("Please select a decision");
      return;
    }

    if (decision !== "APPROVE" && !reason.trim()) {
      alert("Please provide a reason for your decision");
      return;
    }

    setSubmitting(true);
    try {
      await checkerApi.submitDecision(requestId, CHECKER_ID, {
        decision,
        reason: reason.trim() || undefined,
      });
      router.push("/checker/queue");
    } catch (err: any) {
      console.error("Failed to submit decision:", err);
      alert(err.response?.data?.detail || "Failed to submit decision");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRelease = async () => {
    if (confirm("Release this request back to the queue?")) {
      try {
        await checkerApi.release(requestId, CHECKER_ID);
        router.push("/checker/queue");
      } catch (err: any) {
        console.error("Failed to release:", err);
        alert(err.response?.data?.detail || "Failed to release request");
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-green-600 animate-spin" />
      </div>
    );
  }

  if (error || !reviewData) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Failed to Load Review
        </h2>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={() => router.push("/checker/queue")}
          className="text-green-600 hover:text-green-700"
        >
          Return to Queue
        </button>
      </div>
    );
  }

  const getScoreColor = (score: number | null) => {
    if (score === null) return "text-gray-400";
    if (score >= 0.9) return "text-green-600";
    if (score >= 0.7) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/checker/queue")}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Review Request</h1>
            <p className="text-sm text-gray-500">ID: {requestId}</p>
          </div>
        </div>
        <button
          onClick={handleRelease}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Release to Queue
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Left 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Request Details */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <User className="h-5 w-5" />
              Request Details
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Customer ID</p>
                <p className="font-medium">{reviewData.customer_id}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Change Type</p>
                <p className="font-medium">
                  {CHANGE_TYPE_LABELS[reviewData.change_type]}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Document Type</p>
                <p className="font-medium">
                  {DOCUMENT_TYPE_LABELS[reviewData.document_type]}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Created</p>
                <p className="font-medium">{formatDate(reviewData.created_at)}</p>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-sm text-gray-500">Requested Old Value</p>
                  <p className="font-medium">{reviewData.requested_old_value}</p>
                </div>
                <div className="bg-green-50 p-3 rounded-lg">
                  <p className="text-sm text-gray-500">Requested New Value</p>
                  <p className="font-medium">{reviewData.requested_new_value}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Extracted Data */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Extracted Data
            </h2>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-blue-50 p-3 rounded-lg">
                <p className="text-sm text-gray-500">Extracted Old Value</p>
                <p className="font-medium">
                  {reviewData.extracted_old_value || "N/A"}
                </p>
              </div>
              <div className="bg-blue-50 p-3 rounded-lg">
                <p className="text-sm text-gray-500">Extracted New Value</p>
                <p className="font-medium">
                  {reviewData.extracted_new_value || "N/A"}
                </p>
              </div>
            </div>

            {reviewData.field_scores.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-medium text-gray-700 mb-2">
                  Field Match Scores
                </p>
                <div className="space-y-2">
                  {reviewData.field_scores.map((field, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded"
                    >
                      <div>
                        <span className="text-sm font-medium">
                          {field.field_name}
                        </span>
                        <span className="text-xs text-gray-500 ml-2">
                          ({field.match_method})
                        </span>
                      </div>
                      <div className="text-right">
                        <span
                          className={cn(
                            "font-medium",
                            getScoreColor(field.match_score)
                          )}
                        >
                          {formatPercentage(field.match_score)}
                        </span>
                        <p className="text-xs text-gray-500">
                          {field.extracted_value} → {field.expected_value}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Forgery Analysis */}
          {reviewData.forgery_score !== null && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Forgery Analysis
              </h2>
              <div className="flex items-center gap-4 mb-4">
                <div
                  className={cn(
                    "text-3xl font-bold",
                    reviewData.forgery_score < 0.3
                      ? "text-green-600"
                      : reviewData.forgery_score < 0.6
                      ? "text-yellow-600"
                      : "text-red-600"
                  )}
                >
                  {formatPercentage(1 - reviewData.forgery_score)}
                </div>
                <div>
                  <p className="font-medium">Authenticity Score</p>
                  <p className="text-sm text-gray-500">
                    {reviewData.forgery_result || "Analysis complete"}
                  </p>
                </div>
              </div>
              {reviewData.forgery_details && (
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(reviewData.forgery_details).map(
                    ([key, value]) => (
                      <div key={key} className="p-2 bg-gray-50 rounded text-sm">
                        <span className="text-gray-500">{key}: </span>
                        <span className="font-medium">
                          {typeof value === "number"
                            ? formatPercentage(value)
                            : String(value)}
                        </span>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          )}

          {/* AI Summary */}
          {reviewData.ai_summary && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                AI Summary
              </h2>
              <p className="text-gray-700 whitespace-pre-wrap">
                {reviewData.ai_summary}
              </p>
            </div>
          )}
        </div>

        {/* Sidebar - Right column */}
        <div className="space-y-6">
          {/* Confidence Scores */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Confidence Scores
            </h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-500">Overall Score</span>
                  <span
                    className={cn(
                      "font-medium",
                      getScoreColor(reviewData.overall_score)
                    )}
                  >
                    {formatPercentage(reviewData.overall_score)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn(
                      "h-2 rounded-full",
                      (reviewData.overall_score || 0) >= 0.9
                        ? "bg-green-500"
                        : (reviewData.overall_score || 0) >= 0.7
                        ? "bg-yellow-500"
                        : "bg-red-500"
                    )}
                    style={{
                      width: `${(reviewData.overall_score || 0) * 100}%`,
                    }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="p-2 bg-gray-50 rounded">
                  <p className="text-gray-500">OCR</p>
                  <p className={cn("font-medium", getScoreColor(reviewData.ocr_confidence))}>
                    {formatPercentage(reviewData.ocr_confidence)}
                  </p>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                  <p className="text-gray-500">Extraction</p>
                  <p
                    className={cn(
                      "font-medium",
                      getScoreColor(reviewData.extraction_confidence)
                    )}
                  >
                    {formatPercentage(reviewData.extraction_confidence)}
                  </p>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                  <p className="text-gray-500">Authenticity</p>
                  <p
                    className={cn(
                      "font-medium",
                      getScoreColor(reviewData.doc_authenticity_score)
                    )}
                  >
                    {formatPercentage(reviewData.doc_authenticity_score)}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Risk & Recommendation */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              AI Assessment
            </h2>
            <div className="space-y-3">
              {reviewData.risk_tier && (
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Risk Tier</span>
                  <span
                    className={cn(
                      "px-3 py-1 rounded-full text-sm font-medium",
                      RISK_TIER_COLORS[reviewData.risk_tier]
                    )}
                  >
                    {reviewData.risk_tier}
                  </span>
                </div>
              )}
              {reviewData.ai_recommendation && (
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Recommendation</span>
                  <span
                    className={cn(
                      "font-medium",
                      RECOMMENDATION_COLORS[reviewData.ai_recommendation]
                    )}
                  >
                    {reviewData.ai_recommendation.replace("_", " ")}
                  </span>
                </div>
              )}
            </div>

            {reviewData.flags.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm text-gray-500 mb-2">Flags</p>
                <div className="flex flex-wrap gap-1">
                  {reviewData.flags.map((flag, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-2 py-1 rounded text-xs bg-orange-100 text-orange-800"
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Decision Panel */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Your Decision
            </h2>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setDecision("APPROVE")}
                  className={cn(
                    "flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-colors",
                    decision === "APPROVE"
                      ? "border-green-500 bg-green-50 text-green-700"
                      : "border-gray-200 hover:border-green-300"
                  )}
                >
                  <CheckCircle className="h-5 w-5" />
                  Approve
                </button>
                <button
                  onClick={() => setDecision("REJECT")}
                  className={cn(
                    "flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-colors",
                    decision === "REJECT"
                      ? "border-red-500 bg-red-50 text-red-700"
                      : "border-gray-200 hover:border-red-300"
                  )}
                >
                  <XCircle className="h-5 w-5" />
                  Reject
                </button>
                <button
                  onClick={() => setDecision("MORE_INFO")}
                  className={cn(
                    "flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-colors",
                    decision === "MORE_INFO"
                      ? "border-yellow-500 bg-yellow-50 text-yellow-700"
                      : "border-gray-200 hover:border-yellow-300"
                  )}
                >
                  <Eye className="h-5 w-5" />
                  More Info
                </button>
                <button
                  onClick={() => setDecision("ESCALATE")}
                  className={cn(
                    "flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-colors",
                    decision === "ESCALATE"
                      ? "border-purple-500 bg-purple-50 text-purple-700"
                      : "border-gray-200 hover:border-purple-300"
                  )}
                >
                  <AlertTriangle className="h-5 w-5" />
                  Escalate
                </button>
              </div>

              {decision && decision !== "APPROVE" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Reason <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                    placeholder="Provide reason for your decision..."
                  />
                </div>
              )}

              <button
                onClick={handleDecision}
                disabled={!decision || submitting}
                className={cn(
                  "w-full py-3 rounded-lg font-medium transition-colors",
                  !decision || submitting
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                    : "bg-green-600 text-white hover:bg-green-700"
                )}
              >
                {submitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Submitting...
                  </span>
                ) : (
                  "Submit Decision"
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
