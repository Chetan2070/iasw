"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  AlertTriangle,
  FileText,
  User,
  Shield,
  Eye,
  MessageSquare,
  Loader2,
  Lock,
  Brain,
  TrendingUp,
} from "lucide-react";
import { checkerApi } from "@/lib/api";
import {
  ReviewData,
  Decision,
  CHANGE_TYPE_LABELS,
  DOCUMENT_TYPE_LABELS,
} from "@/types";
import { cn, formatPercentage, formatDate } from "@/lib/utils";
import { useChecker } from "@/contexts/CheckerContext";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, RiskBadge } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";

export default function ReviewPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const { checkerId } = useChecker();
  const { success, error: showError } = useToast();
  const requestId = params.requestId as string;
  const readonly = searchParams.get("readonly") === "true";

  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [decision, setDecision] = useState<Decision | "">("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reviewDataRef = useRef<ReviewData | null>(null);
  useEffect(() => {
    reviewDataRef.current = reviewData;
  }, [reviewData]);

  useEffect(() => {
    let cancelled = false;

    async function fetchReviewData() {
      try {
        const data = await checkerApi.getReviewData(requestId);
        if (!cancelled) {
          setReviewData(data);
        }
      } catch (err: any) {
        if (!cancelled) {
          console.error("Failed to fetch review data:", err);
          const detail = err.response?.data?.detail;
          const errorMsg = typeof detail === "string" ? detail : detail?.message || "Failed to load review data";
          setError(errorMsg);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchReviewData();

    return () => {
      cancelled = true;
      if (!readonly && reviewDataRef.current?.assigned_checker === checkerId) {
        checkerApi.release(requestId, checkerId).catch((err) => {
          console.error("Failed to release on exit:", err);
        });
      }
    };
  }, [requestId, readonly, checkerId]);

  useEffect(() => {
    if (readonly) return;

    const handleBeforeUnload = () => {
      const url = `/api/v1/checker/release/${requestId}?checker_id=${checkerId}`;
      navigator.sendBeacon(url);
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [readonly, requestId, checkerId]);

  const handleBack = async () => {
    if (!readonly) {
      try {
        await checkerApi.release(requestId, checkerId);
      } catch (err) {
        console.error("Failed to release:", err);
      }
    }
    router.push(readonly ? "/checker/reviews" : "/checker/queue");
  };

  const handleDecision = async () => {
    if (!decision) {
      showError("Select a decision", "Please choose approve, reject, or another option.");
      return;
    }

    if (decision !== "APPROVE" && !reason.trim()) {
      showError("Reason required", "Please provide a reason for your decision.");
      return;
    }

    setSubmitting(true);
    try {
      await checkerApi.submitDecision(requestId, checkerId, {
        decision,
        reason: reason.trim() || undefined,
      });
      success("Decision submitted", `Request has been ${decision.toLowerCase()}ed.`);
      router.push("/checker/queue");
    } catch (err: any) {
      console.error("Failed to submit decision:", err);
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === "string" ? detail : detail?.message || "Failed to submit decision";
      showError("Submission failed", errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRelease = async () => {
    if (confirm("Release this request back to the queue?")) {
      try {
        await checkerApi.release(requestId, checkerId);
        success("Released", "Request returned to queue.");
        router.push("/checker/queue");
      } catch (err: any) {
        console.error("Failed to release:", err);
        const detail = err.response?.data?.detail;
        const errorMsg = typeof detail === "string" ? detail : detail?.message || "Failed to release request";
        showError("Release failed", errorMsg);
      }
    }
  };

  const getScoreColor = (score: number | null) => {
    if (score === null) return "text-gray-400";
    if (score >= 0.9) return "text-green-600";
    if (score >= 0.7) return "text-amber-600";
    return "text-red-600";
  };

  const getScoreBarColor = (score: number | null) => {
    if (score === null) return "bg-gray-300";
    if (score >= 0.9) return "bg-green-500";
    if (score >= 0.7) return "bg-amber-500";
    return "bg-red-500";
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card><Skeleton className="h-48 w-full" /></Card>
            <Card><Skeleton className="h-64 w-full" /></Card>
          </div>
          <div className="space-y-6">
            <Card><Skeleton className="h-48 w-full" /></Card>
            <Card><Skeleton className="h-64 w-full" /></Card>
          </div>
        </div>
      </div>
    );
  }

  if (error || !reviewData) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card className="bg-red-50 border-red-200 text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-red-800 mb-2">Failed to Load Review</h2>
          <p className="text-red-600 mb-6">{error}</p>
          <Button variant="outline" onClick={() => router.push("/checker/queue")} icon={<ArrowLeft className="h-4 w-4" />}>
            Return to Queue
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={handleBack} icon={<ArrowLeft className="h-4 w-4" />} />
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">
                {readonly ? "Review Details" : "Review Request"}
              </h1>
              {readonly && (
                <Badge variant="default" size="sm">
                  <Lock className="h-3 w-3 mr-1" />
                  Read Only
                </Badge>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-1">ID: {requestId.slice(0, 16)}...</p>
          </div>
        </div>
        {!readonly && (
          <Button variant="ghost" size="sm" onClick={handleRelease} className="text-gray-500">
            Release to Queue
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Left 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Request Details */}
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <User className="h-5 w-5 text-gray-400" />
              Request Details
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Customer ID</p>
                <p className="font-medium text-gray-900">{reviewData.customer_id}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Change Type</p>
                <p className="font-medium text-gray-900">{CHANGE_TYPE_LABELS[reviewData.change_type]}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Document Type</p>
                <p className="font-medium text-gray-900">{DOCUMENT_TYPE_LABELS[reviewData.document_type]}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Created</p>
                <p className="font-medium text-gray-900">{formatDate(reviewData.created_at)}</p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-gray-100">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-sm text-gray-500 mb-1">Requested Old Value</p>
                  <p className="font-semibold text-gray-900">{reviewData.requested_old_value}</p>
                </div>
                <div className="p-4 bg-green-50 rounded-xl border border-green-100">
                  <p className="text-sm text-green-700 mb-1">Requested New Value</p>
                  <p className="font-semibold text-green-800">{reviewData.requested_new_value}</p>
                </div>
              </div>
            </div>
          </Card>

          {/* Extracted Data */}
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5 text-gray-400" />
              Extracted Data
            </h2>
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                <p className="text-sm text-blue-700 mb-1">Extracted Old Value</p>
                <p className="font-semibold text-blue-900">{reviewData.extracted_old_value || "N/A"}</p>
              </div>
              <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                <p className="text-sm text-blue-700 mb-1">Extracted New Value</p>
                <p className="font-semibold text-blue-900">{reviewData.extracted_new_value || "N/A"}</p>
              </div>
            </div>

            {reviewData.field_scores.length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-700 mb-3">Field Match Scores</p>
                <div className="space-y-2">
                  {reviewData.field_scores.map((field, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <span className="text-sm font-medium text-gray-900">{field.field_name}</span>
                        <span className="text-xs text-gray-500 ml-2">({field.match_method})</span>
                      </div>
                      <div className="text-right">
                        <span className={cn("font-bold", getScoreColor(field.match_score))}>
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
          </Card>

          {/* Forgery Analysis */}
          {reviewData.forgery_score !== null && (
            <Card padding="lg">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Shield className="h-5 w-5 text-gray-400" />
                Forgery Analysis
              </h2>
              <div className="flex items-center gap-6 mb-6">
                <div className={cn("text-4xl font-bold", getScoreColor(reviewData.forgery_score))}>
                  {formatPercentage(reviewData.forgery_score)}
                </div>
                <div>
                  <p className="font-semibold text-gray-900">Authenticity Score</p>
                  <p className="text-sm text-gray-500">{reviewData.forgery_result || "Analysis complete"}</p>
                </div>
              </div>

              {reviewData.forgery_details && (
                <div className="space-y-4">
                  {reviewData.forgery_details.combined?.assessment && (
                    <div className="p-4 bg-gray-50 rounded-xl">
                      <p className="text-sm text-gray-700">{reviewData.forgery_details.combined.assessment}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-4">
                    {reviewData.forgery_details.metadata && (
                      <div className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
                        <p className="text-xs text-blue-700 font-medium">Metadata</p>
                        <p className={cn("text-lg font-bold", getScoreColor(reviewData.forgery_details.metadata.score))}>
                          {formatPercentage(reviewData.forgery_details.metadata.score)}
                        </p>
                      </div>
                    )}
                    {reviewData.forgery_details.ela && (
                      <div className="p-3 bg-purple-50 rounded-lg border-l-4 border-purple-400">
                        <p className="text-xs text-purple-700 font-medium">ELA</p>
                        <p className={cn("text-lg font-bold", getScoreColor(reviewData.forgery_details.ela.score))}>
                          {formatPercentage(reviewData.forgery_details.ela.score)}
                        </p>
                      </div>
                    )}
                    {reviewData.forgery_details.font && (
                      <div className="p-3 bg-orange-50 rounded-lg border-l-4 border-orange-400">
                        <p className="text-xs text-orange-700 font-medium">Font</p>
                        <p className={cn("text-lg font-bold", getScoreColor(reviewData.forgery_details.font.score))}>
                          {formatPercentage(reviewData.forgery_details.font.score)}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* AI Summary */}
          {reviewData.ai_summary && (
            <Card padding="lg">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Brain className="h-5 w-5 text-gray-400" />
                AI Summary
              </h2>
              <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">{reviewData.ai_summary}</p>
            </Card>
          )}
        </div>

        {/* Sidebar - Right column */}
        <div className="space-y-6">
          {/* Confidence Scores */}
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-gray-400" />
              Confidence Scores
            </h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">Overall Score</span>
                  <span className={cn("font-bold", getScoreColor(reviewData.overall_score))}>
                    {formatPercentage(reviewData.overall_score)}
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                  <div
                    className={cn("h-3 rounded-full transition-all duration-500", getScoreBarColor(reviewData.overall_score))}
                    style={{ width: `${(reviewData.overall_score || 0) * 100}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-600">OCR Confidence</span>
                  <span className={cn("font-semibold", getScoreColor(reviewData.ocr_confidence))}>
                    {formatPercentage(reviewData.ocr_confidence)}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-600">Extraction</span>
                  <span className={cn("font-semibold", getScoreColor(reviewData.extraction_confidence))}>
                    {formatPercentage(reviewData.extraction_confidence)}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-600">Authenticity</span>
                  <span className={cn("font-semibold", getScoreColor(reviewData.doc_authenticity_score))}>
                    {formatPercentage(reviewData.doc_authenticity_score)}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Risk & Recommendation */}
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Assessment</h2>
            <div className="space-y-4">
              {reviewData.risk_tier && (
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Risk Tier</span>
                  <RiskBadge tier={reviewData.risk_tier as "HIGH" | "MEDIUM" | "LOW"} size="md" />
                </div>
              )}
              {reviewData.ai_recommendation && (
                <div className="flex items-center justify-between">
                  <span className="text-gray-500">Recommendation</span>
                  <Badge
                    variant={
                      reviewData.ai_recommendation === "APPROVE" ? "success" :
                      reviewData.ai_recommendation === "REJECT" ? "danger" : "warning"
                    }
                    size="md"
                  >
                    {reviewData.ai_recommendation.replace("_", " ")}
                  </Badge>
                </div>
              )}
            </div>

            {reviewData.flags.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-sm text-gray-500 mb-2">Flags</p>
                <div className="flex flex-wrap gap-2">
                  {reviewData.flags.map((flag, idx) => (
                    <Badge key={idx} variant="warning" size="sm">{flag}</Badge>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Decision Panel */}
          {!readonly && (
            <Card padding="lg" className="border-2 border-green-100">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Decision</h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { value: "APPROVE", label: "Approve", icon: CheckCircle, color: "green" },
                    { value: "REJECT", label: "Reject", icon: XCircle, color: "red" },
                    { value: "MORE_INFO", label: "More Info", icon: Eye, color: "amber" },
                    { value: "ESCALATE", label: "Escalate", icon: AlertTriangle, color: "purple" },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setDecision(opt.value as Decision)}
                      className={cn(
                        "flex items-center justify-center gap-2 p-3 rounded-xl border-2 transition-all font-medium text-sm",
                        decision === opt.value
                          ? `border-${opt.color}-500 bg-${opt.color}-50 text-${opt.color}-700`
                          : "border-gray-200 hover:border-gray-300 text-gray-600"
                      )}
                      style={decision === opt.value ? {
                        borderColor: opt.color === "green" ? "#22c55e" : opt.color === "red" ? "#ef4444" : opt.color === "amber" ? "#f59e0b" : "#a855f7",
                        backgroundColor: opt.color === "green" ? "#f0fdf4" : opt.color === "red" ? "#fef2f2" : opt.color === "amber" ? "#fffbeb" : "#faf5ff",
                        color: opt.color === "green" ? "#15803d" : opt.color === "red" ? "#b91c1c" : opt.color === "amber" ? "#b45309" : "#7e22ce",
                      } : {}}
                    >
                      <opt.icon className="h-4 w-4" />
                      {opt.label}
                    </button>
                  ))}
                </div>

                {decision && decision !== "APPROVE" && (
                  <Textarea
                    label="Reason"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={3}
                    placeholder="Provide reason for your decision..."
                    hint="Required for non-approval decisions"
                  />
                )}

                <Button
                  onClick={handleDecision}
                  disabled={!decision}
                  loading={submitting}
                  fullWidth
                  size="lg"
                  className="bg-green-600 hover:bg-green-700"
                >
                  Submit Decision
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
