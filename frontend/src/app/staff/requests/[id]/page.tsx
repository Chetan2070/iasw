"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle,
  Clock,
  AlertCircle,
  XCircle,
  FileText,
  User,
  Calendar,
  Trash2,
  Loader2,
} from "lucide-react";
import { requestsApi } from "@/lib/api";
import {
  RequestStatus,
  STATUS_LABELS,
  CHANGE_TYPE_LABELS,
  DOCUMENT_TYPE_LABELS,
  RISK_TIER_COLORS,
} from "@/types";
import { cn, formatDate } from "@/lib/utils";

interface RequestDetail {
  request_id: string;
  idempotency_key: string | null;
  customer_id: string;
  change_type: string;
  document_type: string;
  requested_old_value: string;
  requested_new_value: string;
  extracted_old_value: string | null;
  extracted_new_value: string | null;
  extraction_details: Array<{
    field_name: string;
    value: string;
    confidence: number;
    source_snippet: string | null;
  }>;
  confidence: {
    old_name_match: number | null;
    new_name_match: number | null;
    ocr_confidence: number | null;
    extraction_confidence: number | null;
    doc_authenticity: number | null;
    overall: number | null;
  } | null;
  forgery: {
    score: number;
    result: string;
    metadata_score: number | null;
    ela_score: number | null;
    font_score: number | null;
    ml_score: number | null;
  } | null;
  risk_tier: string | null;
  flags: string[];
  ai_recommendation: string | null;
  ai_summary: string | null;
  document_storage_path: string | null;
  filenet_staging_id: string | null;
  filenet_permanent_id: string | null;
  status: RequestStatus;
  assigned_checker: string | null;
  checker_decision: string | null;
  checker_decision_reason: string | null;
  created_at: string;
  validated_at: string | null;
  processing_started_at: string | null;
  processing_completed_at: string | null;
  staged_at: string | null;
  claimed_at: string | null;
  decided_at: string | null;
  completed_at: string | null;
  is_locked: boolean;
  can_be_claimed: boolean;
  time_in_current_status_minutes: number | null;
}

const WORKFLOW_STAGES = [
  { key: "INTAKE_RECEIVED", label: "Intake Received", description: "Request created and validated" },
  { key: "VALIDATED", label: "Document Uploaded", description: "Supporting document uploaded and validated" },
  { key: "QUEUED", label: "Queued", description: "Waiting for Celery worker to pick up the task" },
  { key: "PROCESSING", label: "AI Processing", description: "Document being analyzed by AI pipeline" },
  { key: "AI_VERIFIED_PENDING_HUMAN", label: "AI Verified", description: "AI analysis complete, pending human review" },
  { key: "IN_REVIEW", label: "In Review", description: "Human checker reviewing the request" },
  { key: "APPROVED", label: "Approved", description: "Request approved by checker" },
  { key: "COMPLETED", label: "Completed", description: "Changes applied to core banking system" },
];

const PROCESSING_SUBSTEPS = [
  { key: "validation", label: "Document Validation", description: "Verifying document exists and is readable" },
  { key: "ocr", label: "OCR Extraction", description: "Extracting text from document using Tesseract" },
  { key: "classifier", label: "Document Classification", description: "LLM classifying document type" },
  { key: "extractor", label: "Field Extraction", description: "LLM extracting names, dates, and other fields" },
  { key: "forgery", label: "Forgery Detection", description: "Analyzing for tampering (metadata, ELA, fonts)" },
  { key: "scorer", label: "Confidence Scoring", description: "Calculating match scores and risk tier" },
  { key: "summary", label: "Summary Generation", description: "LLM generating human-readable summary" },
];

const STATUS_ORDER: Record<string, number> = {
  INTAKE_RECEIVED: 0,
  VALIDATED: 1,
  QUEUED: 2,
  PROCESSING: 3,
  AI_VERIFIED_PENDING_HUMAN: 4,
  IN_REVIEW: 5,
  PENDING_INFO: 5,
  ESCALATED: 5,
  APPROVED: 6,
  REJECTED: 6,
  COMPLETED: 7,
  FAILED: -1,
};

export default function RequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const requestId = params.id as string;

  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const fetchRequest = async () => {
      try {
        const data = await requestsApi.get(requestId);
        setRequest(data as unknown as RequestDetail);
      } catch (err: any) {
        setError(err.response?.data?.detail?.message || "Failed to load request");
      } finally {
        setLoading(false);
      }
    };

    fetchRequest();

    // Auto-refresh every 3 seconds if status is still processing
    const interval = setInterval(async () => {
      try {
        const data = await requestsApi.get(requestId);
        const req = data as unknown as RequestDetail;
        setRequest(req);

        // Stop polling if request is in a terminal state
        if (["COMPLETED", "FAILED", "REJECTED", "APPROVED", "AI_VERIFIED_PENDING_HUMAN", "IN_REVIEW"].includes(req.status)) {
          clearInterval(interval);
        }
      } catch (err) {
        // Silently fail on polling errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [requestId]);

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete request ${requestId}?`)) {
      return;
    }

    setDeleting(true);
    try {
      await requestsApi.delete(requestId);
      router.push("/staff/requests");
    } catch (err: any) {
      alert(err.response?.data?.detail?.message || "Failed to delete request");
    } finally {
      setDeleting(false);
    }
  };

  const getStageStatus = (stageKey: string) => {
    if (!request) return "pending";

    const currentOrder = STATUS_ORDER[request.status] ?? -1;
    const stageOrder = STATUS_ORDER[stageKey] ?? -1;

    if (request.status === "FAILED" || request.status === "REJECTED") {
      if (stageKey === request.status) return "failed";
      if (stageOrder < currentOrder) return "completed";
      return "pending";
    }

    if (stageKey === request.status) return "current";
    if (stageOrder < currentOrder) return "completed";
    return "pending";
  };

  const getStageIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-6 w-6 text-green-600" />;
      case "current":
        return <Clock className="h-6 w-6 text-blue-600 animate-pulse" />;
      case "failed":
        return <XCircle className="h-6 w-6 text-red-600" />;
      default:
        return <div className="h-6 w-6 rounded-full border-2 border-gray-300" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <AlertCircle className="h-12 w-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Request</h2>
          <p className="text-red-600 mb-4">{error || "Request not found"}</p>
          <Link
            href="/staff/requests"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Requests
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/staff/requests"
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{request.request_id}</h1>
            <p className="text-sm text-gray-500">
              Created {formatDate(request.created_at)}
            </p>
          </div>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="inline-flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
        >
          <Trash2 className={cn("h-4 w-4", deleting && "animate-pulse")} />
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>

      {/* Progress Timeline */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">Request Progress</h2>
        <div className="relative">
          {/* Progress Line */}
          <div className="absolute left-3 top-3 bottom-3 w-0.5 bg-gray-200" />

          <div className="space-y-6">
            {WORKFLOW_STAGES.map((stage, index) => {
              const status = getStageStatus(stage.key);
              const isLast = index === WORKFLOW_STAGES.length - 1;

              return (
                <div key={stage.key} className="relative flex items-start gap-4">
                  <div className="relative z-10 bg-white">
                    {getStageIcon(status)}
                  </div>
                  <div className={cn("flex-1 pb-2", !isLast && "border-b border-gray-100")}>
                    <div className="flex items-center justify-between">
                      <h3
                        className={cn(
                          "font-medium",
                          status === "completed" && "text-green-700",
                          status === "current" && "text-blue-700",
                          status === "failed" && "text-red-700",
                          status === "pending" && "text-gray-400"
                        )}
                      >
                        {stage.label}
                      </h3>
                      {status === "current" && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
                          Current Stage
                        </span>
                      )}
                    </div>
                    <p
                      className={cn(
                        "text-sm",
                        status === "pending" ? "text-gray-400" : "text-gray-500"
                      )}
                    >
                      {stage.description}
                    </p>

                    {/* Show processing substeps when at PROCESSING stage or beyond */}
                    {stage.key === "PROCESSING" && (status === "current" || status === "completed") && (
                      <div className="mt-4 ml-2 space-y-2 border-l-2 border-gray-200 pl-4">
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                          AI Pipeline Steps
                        </p>
                        {PROCESSING_SUBSTEPS.map((substep, subIndex) => {
                          const isSubstepComplete = status === "completed";
                          const isLastSubstep = subIndex === PROCESSING_SUBSTEPS.length - 1;

                          return (
                            <div key={substep.key} className="flex items-start gap-2">
                              {isSubstepComplete ? (
                                <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                              ) : status === "current" ? (
                                <Clock className="h-4 w-4 text-blue-500 animate-pulse mt-0.5 flex-shrink-0" />
                              ) : (
                                <div className="h-4 w-4 rounded-full border border-gray-300 mt-0.5 flex-shrink-0" />
                              )}
                              <div>
                                <p className={cn(
                                  "text-sm font-medium",
                                  isSubstepComplete ? "text-green-700" : status === "current" ? "text-blue-700" : "text-gray-400"
                                )}>
                                  {substep.label}
                                </p>
                                <p className={cn(
                                  "text-xs",
                                  isSubstepComplete ? "text-gray-500" : "text-gray-400"
                                )}>
                                  {substep.description}
                                </p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Show helpful message when stuck at QUEUED */}
                    {stage.key === "QUEUED" && status === "current" && (
                      <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p className="text-xs text-yellow-800">
                          <strong>Note:</strong> Request is waiting for the Celery worker to process it.
                          Make sure Redis is running and start the worker with:
                        </p>
                        <code className="block mt-1 text-xs bg-yellow-100 p-2 rounded font-mono">
                          celery -A app.workers.celery_app worker --loglevel=info
                        </code>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Request Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Basic Info */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-gray-400" />
            Request Details
          </h2>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Change Type</dt>
              <dd className="text-sm font-medium text-gray-900">
                {CHANGE_TYPE_LABELS[request.change_type as keyof typeof CHANGE_TYPE_LABELS] || request.change_type}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Document Type</dt>
              <dd className="text-sm font-medium text-gray-900">
                {DOCUMENT_TYPE_LABELS[request.document_type as keyof typeof DOCUMENT_TYPE_LABELS] || request.document_type}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Current Status</dt>
              <dd>
                <span
                  className={cn(
                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                    request.status === "APPROVED" || request.status === "COMPLETED"
                      ? "bg-green-100 text-green-800"
                      : request.status === "REJECTED" || request.status === "FAILED"
                      ? "bg-red-100 text-red-800"
                      : "bg-yellow-100 text-yellow-800"
                  )}
                >
                  {STATUS_LABELS[request.status]}
                </span>
              </dd>
            </div>
            {request.risk_tier && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Risk Tier</dt>
                <dd>
                  <span
                    className={cn(
                      "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                      RISK_TIER_COLORS[request.risk_tier as keyof typeof RISK_TIER_COLORS]
                    )}
                  >
                    {request.risk_tier}
                  </span>
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Customer Info */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <User className="h-5 w-5 text-gray-400" />
            Customer Information
          </h2>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Customer ID</dt>
              <dd className="text-sm font-medium text-gray-900">{request.customer_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Requested Old Value</dt>
              <dd className="text-sm font-medium text-gray-900">{request.requested_old_value}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Requested New Value</dt>
              <dd className="text-sm font-medium text-gray-900">{request.requested_new_value}</dd>
            </div>
          </dl>
        </div>

        {/* Timestamps */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Calendar className="h-5 w-5 text-gray-400" />
            Timeline
          </h2>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Created</dt>
              <dd className="text-sm font-medium text-gray-900">{formatDate(request.created_at)}</dd>
            </div>
            {request.validated_at && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Validated</dt>
                <dd className="text-sm font-medium text-gray-900">{formatDate(request.validated_at)}</dd>
              </div>
            )}
            {request.processing_started_at && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Processing Started</dt>
                <dd className="text-sm font-medium text-gray-900">{formatDate(request.processing_started_at)}</dd>
              </div>
            )}
            {request.processing_completed_at && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Processing Completed</dt>
                <dd className="text-sm font-medium text-gray-900">{formatDate(request.processing_completed_at)}</dd>
              </div>
            )}
            {request.decided_at && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Decision Made</dt>
                <dd className="text-sm font-medium text-gray-900">{formatDate(request.decided_at)}</dd>
              </div>
            )}
            {request.completed_at && (
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Completed</dt>
                <dd className="text-sm font-medium text-gray-900">{formatDate(request.completed_at)}</dd>
              </div>
            )}
          </dl>
        </div>

        {/* AI Analysis (if available) */}
        {(request.confidence || request.ai_recommendation) && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Analysis</h2>
            <dl className="space-y-3">
              {request.ai_recommendation && (
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Recommendation</dt>
                  <dd
                    className={cn(
                      "text-sm font-medium",
                      request.ai_recommendation === "APPROVE"
                        ? "text-green-600"
                        : request.ai_recommendation === "REJECT"
                        ? "text-red-600"
                        : "text-yellow-600"
                    )}
                  >
                    {request.ai_recommendation}
                  </dd>
                </div>
              )}
              {request.confidence?.overall && (
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Overall Confidence</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {(request.confidence.overall * 100).toFixed(1)}%
                  </dd>
                </div>
              )}
              {request.confidence?.ocr_confidence && (
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">OCR Confidence</dt>
                  <dd className="text-sm font-medium text-gray-900">
                    {(request.confidence.ocr_confidence * 100).toFixed(1)}%
                  </dd>
                </div>
              )}
            </dl>
            {request.ai_summary && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <dt className="text-sm text-gray-500 mb-2">AI Summary</dt>
                <dd className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
                  {request.ai_summary}
                </dd>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Flags */}
      {request.flags && request.flags.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-yellow-800 mb-2 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            Flags
          </h3>
          <div className="flex flex-wrap gap-2">
            {request.flags.map((flag, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800"
              >
                {flag}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
