/**
 * Type definitions for the IASW application
 */

// Enums
export type ChangeType = "LEGAL_NAME" | "ADDRESS" | "DOB" | "CONTACT";

export type DocumentType =
  | "MARRIAGE_CERTIFICATE"
  | "GAZETTE_NOTIFICATION"
  | "DEED_POLL"
  | "COURT_ORDER"
  | "UTILITY_BILL"
  | "LEASE_AGREEMENT"
  | "BIRTH_CERTIFICATE"
  | "PASSPORT"
  | "PAN_CARD"
  | "CONSENT_FORM";

export type RequestStatus =
  | "INTAKE_RECEIVED"
  | "VALIDATED"
  | "QUEUED"
  | "PROCESSING"
  | "AI_VERIFIED_PENDING_HUMAN"
  | "IN_REVIEW"
  | "PENDING_INFO"
  | "ESCALATED"
  | "REPROCESSING"
  | "APPROVED"
  | "REJECTED"
  | "COMPLETED"
  | "FAILED";

export type RiskTier = "LOW" | "MEDIUM" | "HIGH";

export type Recommendation = "APPROVE" | "REJECT" | "MANUAL_REVIEW";

export type Decision = "APPROVE" | "REJECT" | "MORE_INFO" | "ESCALATE";

// Request Types
export interface CreateRequestData {
  account_number: string;
  change_type: ChangeType;
  document_type: DocumentType;
  current_value: string;
  new_value: string;
}

export interface RequestResponse {
  request_id: string;
  status: RequestStatus;
  message: string;
  customer_name?: string;
}

export interface RequestSummary {
  request_id: string;
  customer_id: string;
  change_type: ChangeType;
  document_type: DocumentType;
  status: RequestStatus;
  risk_tier: RiskTier | null;
  ai_recommendation: Recommendation | null;
  overall_confidence: number | null;
  flags: string[];
  created_at: string;
  time_in_current_status_minutes: number | null;
}

export interface FieldScore {
  field_name: string;
  extracted_value: string;
  expected_value: string;
  match_score: number;
  match_method: string;
}

export interface ReviewData {
  request_id: string;
  customer_id: string;
  change_type: ChangeType;
  document_type: DocumentType;
  requested_old_value: string;
  requested_new_value: string;
  extracted_old_value: string | null;
  extracted_new_value: string | null;
  field_scores: FieldScore[];
  ocr_confidence: number | null;
  extraction_confidence: number | null;
  doc_authenticity_score: number | null;
  overall_score: number | null;
  forgery_score: number | null;
  forgery_result: string | null;
  forgery_details: Record<string, any> | null;
  risk_tier: RiskTier | null;
  flags: string[];
  ai_recommendation: Recommendation | null;
  ai_summary: string | null;
  document_url: string | null;
  filenet_reference: string | null;
  assigned_checker: string | null;
  created_at: string;
  staged_at: string | null;
  claimed_at: string | null;
}

// Queue Types
export interface QueueItem {
  request_id: string;
  customer_id: string;
  change_type: ChangeType;
  document_type: DocumentType;
  risk_tier: RiskTier;
  ai_recommendation: Recommendation;
  overall_score: number;
  flags: string[];
  queued_at: string;
  time_in_queue_minutes: number;
}

export interface QueueResponse {
  items: QueueItem[];
  total: number;
  page: number;
  limit: number;
}

// Decision Types
export interface DecisionRequest {
  decision: Decision;
  reason?: string;
}

export interface DecisionResponse {
  request_id: string;
  decision: Decision;
  new_status: RequestStatus;
  rps_updated: boolean;
  message: string;
}

// Upload Types
export interface UploadResponse {
  request_id: string;
  status: RequestStatus;
  document_id: string;
  message: string;
}

// Claim Types
export interface ClaimResponse {
  request_id: string;
  status: string;
  assigned_to: string;
  lock_expires_at: string;
  message: string;
}

// Allowed document types per change type
export const ALLOWED_DOCUMENTS: Record<ChangeType, DocumentType[]> = {
  LEGAL_NAME: [
    "MARRIAGE_CERTIFICATE",
    "GAZETTE_NOTIFICATION",
    "DEED_POLL",
    "COURT_ORDER",
  ],
  ADDRESS: ["UTILITY_BILL", "LEASE_AGREEMENT", "PASSPORT"],
  DOB: ["BIRTH_CERTIFICATE", "PASSPORT", "PAN_CARD"],
  CONTACT: ["CONSENT_FORM"],
};

// Display names
export const CHANGE_TYPE_LABELS: Record<ChangeType, string> = {
  LEGAL_NAME: "Legal Name Change",
  ADDRESS: "Address Change",
  DOB: "Date of Birth Correction",
  CONTACT: "Contact / Email Update",
};

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  MARRIAGE_CERTIFICATE: "Marriage Certificate",
  GAZETTE_NOTIFICATION: "Gazette Notification",
  DEED_POLL: "Deed Poll",
  COURT_ORDER: "Court Order",
  UTILITY_BILL: "Utility Bill",
  LEASE_AGREEMENT: "Lease Agreement",
  BIRTH_CERTIFICATE: "Birth Certificate",
  PASSPORT: "Passport",
  PAN_CARD: "PAN Card",
  CONSENT_FORM: "Consent Form",
};

export const STATUS_LABELS: Record<RequestStatus, string> = {
  INTAKE_RECEIVED: "Intake Received",
  VALIDATED: "Validated",
  QUEUED: "Queued for Processing",
  PROCESSING: "Processing",
  AI_VERIFIED_PENDING_HUMAN: "Pending Review",
  IN_REVIEW: "In Review",
  PENDING_INFO: "Pending Information",
  ESCALATED: "Escalated",
  REPROCESSING: "Reprocessing",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

export const RISK_TIER_COLORS: Record<RiskTier, string> = {
  LOW: "bg-green-100 text-green-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
  HIGH: "bg-red-100 text-red-800",
};

export const RECOMMENDATION_COLORS: Record<Recommendation, string> = {
  APPROVE: "text-green-600",
  REJECT: "text-red-600",
  MANUAL_REVIEW: "text-yellow-600",
};
