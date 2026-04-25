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
  Brain,
  Shield,
  ChevronRight,
} from "lucide-react";
import { requestsApi } from "@/lib/api";
import {
  RequestStatus,
  STATUS_LABELS,
  CHANGE_TYPE_LABELS,
  DOCUMENT_TYPE_LABELS,
} from "@/types";
import { cn, formatDate } from "@/lib/utils";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, StatusBadge, RiskBadge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";

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
  current_processing_step: string | null;
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
  { key: "validation", label: "Document Validation", description: "Verifying document exists" },
  { key: "ocr", label: "OCR Extraction", description: "Extracting text via Tesseract" },
  { key: "classifier", label: "Classification", description: "LLM classifying document type" },
  { key: "extractor", label: "Field Extraction", description: "LLM extracting fields" },
  { key: "forgery", label: "Forgery Detection", description: "Analyzing for tampering" },
  { key: "scorer", label: "Confidence Scoring", description: "Calculating risk tier" },
  { key: "summary", label: "Summary Generation", description: "Generating summary" },
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
  const { success, error: showError } = useToast();
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
        const detail = err.response?.data?.detail;
        const errorMsg = typeof detail === "string" ? detail : detail?.message || "Failed to load request";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchRequest();

    const interval = setInterval(async () => {
      try {
        const data = await requestsApi.get(requestId);
        const req = data as unknown as RequestDetail;
        setRequest(req);

        if (["COMPLETED", "FAILED", "REJECTED"].includes(req.status)) {
          clearInterval(interval);
        }
      } catch (err) {
        // Silently fail on polling errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [requestId]);

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete this request?`)) {
      return;
    }

    setDeleting(true);
    try {
      await requestsApi.delete(requestId);
      success("Request deleted", "The request has been removed.");
      router.push("/staff/requests");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === "string" ? detail : detail?.message || "Failed to delete request";
      showError("Delete failed", errorMsg);
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

    if (request.status === "COMPLETED" || request.status === "APPROVED") {
      if (stageOrder <= currentOrder) return "completed";
      return "pending";
    }

    if (stageKey === request.status) return "current";
    if (stageOrder < currentOrder) return "completed";
    return "pending";
  };

  const getStageIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case "current":
        return (
          <div className="h-5 w-5 rounded-full bg-blue-600 flex items-center justify-center">
            <div className="h-2 w-2 rounded-full bg-white animate-pulse" />
          </div>
        );
      case "failed":
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <div className="h-5 w-5 rounded-full border-2 border-gray-300 bg-white" />;
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Card>
          <Skeleton className="h-64 w-full" />
        </Card>
        <div className="grid grid-cols-2 gap-6">
          <Card><Skeleton className="h-48 w-full" /></Card>
          <Card><Skeleton className="h-48 w-full" /></Card>
        </div>
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card className="bg-red-50 border-red-200 text-center py-12">
          <AlertCircle className="h-12 w-12 text-red-600 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error Loading Request</h2>
          <p className="text-red-600 mb-6">{error || "Request not found"}</p>
          <Link href="/staff/requests">
            <Button variant="outline" icon={<ArrowLeft className="h-4 w-4" />}>
              Back to Requests
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/staff/requests">
            <Button variant="ghost" size="sm" icon={<ArrowLeft className="h-4 w-4" />} />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">
                {request.request_id.slice(0, 12)}...
              </h1>
              <StatusBadge status={request.status} size="md" />
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Created {formatDate(request.created_at)}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          onClick={handleDelete}
          loading={deleting}
          icon={<Trash2 className="h-4 w-4" />}
          className="text-red-600 hover:text-red-700 hover:bg-red-50"
        >
          Delete
        </Button>
      </div>

      {/* Progress Timeline */}
      <Card padding="lg">
        <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
          <Clock className="h-5 w-5 text-gray-400" />
          Request Progress
        </h2>
        <div className="relative">
          <div className="absolute left-[9px] top-4 bottom-4 w-0.5 bg-gray-200" />

          <div className="space-y-4">
            {WORKFLOW_STAGES.map((stage, index) => {
              const status = getStageStatus(stage.key);
              const isProcessing = stage.key === "PROCESSING" && (status === "current" || status === "completed");

              return (
                <div key={stage.key} className="relative flex items-start gap-4">
                  <div className="relative z-10 bg-white p-0.5">
                    {getStageIcon(status)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3
                        className={cn(
                          "font-medium text-sm",
                          status === "completed" && "text-green-700",
                          status === "current" && "text-blue-700",
                          status === "failed" && "text-red-700",
                          status === "pending" && "text-gray-400"
                        )}
                      >
                        {stage.label}
                      </h3>
                      {status === "current" && (
                        <Badge variant="info" size="sm">In Progress</Badge>
                      )}
                    </div>
                    <p className={cn(
                      "text-xs mt-0.5",
                      status === "pending" ? "text-gray-400" : "text-gray-500"
                    )}>
                      {stage.description}
                    </p>

                    {/* Processing substeps */}
                    {isProcessing && (
                      <div className="mt-3 ml-2 space-y-2 border-l-2 border-gray-200 pl-3">
                        {PROCESSING_SUBSTEPS.map((substep, subIndex) => {
                          const processingComplete = status === "completed";
                          const currentStepKey = request?.current_processing_step || "";
                          const currentStepIndex = PROCESSING_SUBSTEPS.findIndex(s => s.key === currentStepKey);

                          let substepStatus: "completed" | "current" | "pending" = "pending";
                          if (processingComplete) {
                            substepStatus = "completed";
                          } else if (currentStepIndex >= 0) {
                            if (subIndex < currentStepIndex) substepStatus = "completed";
                            else if (subIndex === currentStepIndex) substepStatus = "current";
                          }

                          return (
                            <div key={substep.key} className="flex items-center gap-2">
                              {substepStatus === "completed" ? (
                                <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                              ) : substepStatus === "current" ? (
                                <Loader2 className="h-3.5 w-3.5 text-blue-500 animate-spin" />
                              ) : (
                                <div className="h-3.5 w-3.5 rounded-full border border-gray-300" />
                              )}
                              <span className={cn(
                                "text-xs",
                                substepStatus === "completed" ? "text-green-700" :
                                substepStatus === "current" ? "text-blue-700" : "text-gray-400"
                              )}>
                                {substep.label}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* QUEUED helper */}
                    {stage.key === "QUEUED" && status === "current" && (
                      <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                        <p className="text-xs text-amber-800">
                          <strong>Note:</strong> Waiting for Celery worker. Run:
                          <code className="ml-1 bg-amber-100 px-1.5 py-0.5 rounded font-mono">
                            celery -A app.workers.celery_app worker --loglevel=info
                          </code>
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Request Details */}
        <Card padding="lg">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-gray-400" />
            Request Details
          </h2>
          <dl className="space-y-4">
            <div className="flex justify-between items-center">
              <dt className="text-sm text-gray-500">Change Type</dt>
              <dd className="text-sm font-medium text-gray-900">
                {CHANGE_TYPE_LABELS[request.change_type as keyof typeof CHANGE_TYPE_LABELS] || request.change_type}
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-sm text-gray-500">Document Type</dt>
              <dd className="text-sm font-medium text-gray-900">
                {DOCUMENT_TYPE_LABELS[request.document_type as keyof typeof DOCUMENT_TYPE_LABELS] || request.document_type}
              </dd>
            </div>
            {request.risk_tier && (
              <div className="flex justify-between items-center">
                <dt className="text-sm text-gray-500">Risk Tier</dt>
                <dd><RiskBadge tier={request.risk_tier as "HIGH" | "MEDIUM" | "LOW"} /></dd>
              </div>
            )}
          </dl>
        </Card>

        {/* Customer Info */}
        <Card padding="lg">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <User className="h-5 w-5 text-gray-400" />
            Customer Information
          </h2>
          <dl className="space-y-4">
            <div className="flex justify-between items-center">
              <dt className="text-sm text-gray-500">Customer ID</dt>
              <dd className="text-sm font-medium text-gray-900">{request.customer_id}</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-sm text-gray-500">Old Value</dt>
              <dd className="text-sm font-medium text-gray-900">{request.requested_old_value}</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-sm text-gray-500">New Value</dt>
              <dd className="text-sm font-medium text-gray-900">{request.requested_new_value}</dd>
            </div>
          </dl>
        </Card>

        {/* Timeline */}
        <Card padding="lg">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Calendar className="h-5 w-5 text-gray-400" />
            Timeline
          </h2>
          <dl className="space-y-4">
            <div className="flex justify-between items-center">
              <dt className="text-sm text-gray-500">Created</dt>
              <dd className="text-sm font-medium text-gray-900">{formatDate(request.created_at)}</dd>
            </div>
            {request.validated_at && (
              <div className="flex justify-between items-center">
                <dt className="text-sm text-gray-500">Validated</dt>
                <dd className="text-sm font-medium text-gray-900">{formatDate(request.validated_at)}</dd>
              </div>
            )}
            {request.processing_completed_at && (
              <div className="flex justify-between items-center">
                <dt className="text-sm text-gray-500">AI Processed</dt>
                <dd className="text-sm font-medium text-gray-900">{formatDate(request.processing_completed_at)}</dd>
              </div>
            )}
            {request.decided_at && (
              <div className="flex justify-between items-center">
                <dt className="text-sm text-gray-500">Decision Made</dt>
                <dd className="text-sm font-medium text-gray-900">{formatDate(request.decided_at)}</dd>
              </div>
            )}
          </dl>
        </Card>

        {/* AI Analysis */}
        {(request.confidence || request.ai_recommendation) && (
          <Card padding="lg">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Brain className="h-5 w-5 text-gray-400" />
              AI Analysis
            </h2>
            <dl className="space-y-4">
              {request.ai_recommendation && (
                <div className="flex justify-between items-center">
                  <dt className="text-sm text-gray-500">Recommendation</dt>
                  <dd>
                    <Badge
                      variant={
                        request.ai_recommendation === "APPROVE" ? "success" :
                        request.ai_recommendation === "REJECT" ? "danger" : "warning"
                      }
                    >
                      {request.ai_recommendation}
                    </Badge>
                  </dd>
                </div>
              )}
              {request.confidence?.overall && (
                <div className="flex justify-between items-center">
                  <dt className="text-sm text-gray-500">Confidence</dt>
                  <dd className="text-sm font-bold text-gray-900">
                    {(request.confidence.overall * 100).toFixed(1)}%
                  </dd>
                </div>
              )}
            </dl>
            {request.ai_summary && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-sm text-gray-500 mb-2">AI Summary</p>
                <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
                  {request.ai_summary}
                </p>
              </div>
            )}
          </Card>
        )}
      </div>

      {/* Flags */}
      {request.flags && request.flags.length > 0 && (
        <Card className="bg-amber-50 border-amber-200">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <AlertCircle className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <h3 className="font-medium text-amber-800 mb-2">Flags</h3>
              <div className="flex flex-wrap gap-2">
                {request.flags.map((flag, index) => (
                  <Badge key={index} variant="warning">{flag}</Badge>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
