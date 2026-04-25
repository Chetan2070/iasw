/**
 * Tests for TypeScript type definitions
 */

import {
  ChangeType,
  DocumentType,
  RequestStatus,
  RiskTier,
  Recommendation,
  Decision,
  ALLOWED_DOCUMENTS,
  CHANGE_TYPE_LABELS,
  DOCUMENT_TYPE_LABELS,
  STATUS_LABELS,
  RISK_TIER_COLORS,
  RECOMMENDATION_COLORS,
} from "@/types";

describe("Type Constants", () => {
  describe("ALLOWED_DOCUMENTS", () => {
    it("should have correct document types for LEGAL_NAME", () => {
      expect(ALLOWED_DOCUMENTS.LEGAL_NAME).toContain("MARRIAGE_CERTIFICATE");
      expect(ALLOWED_DOCUMENTS.LEGAL_NAME).toContain("GAZETTE_NOTIFICATION");
      expect(ALLOWED_DOCUMENTS.LEGAL_NAME).toContain("DEED_POLL");
      expect(ALLOWED_DOCUMENTS.LEGAL_NAME).toContain("COURT_ORDER");
      expect(ALLOWED_DOCUMENTS.LEGAL_NAME).not.toContain("UTILITY_BILL");
    });

    it("should have correct document types for ADDRESS", () => {
      expect(ALLOWED_DOCUMENTS.ADDRESS).toContain("UTILITY_BILL");
      expect(ALLOWED_DOCUMENTS.ADDRESS).toContain("LEASE_AGREEMENT");
      expect(ALLOWED_DOCUMENTS.ADDRESS).toContain("PASSPORT");
      expect(ALLOWED_DOCUMENTS.ADDRESS).not.toContain("MARRIAGE_CERTIFICATE");
    });

    it("should have correct document types for DOB", () => {
      expect(ALLOWED_DOCUMENTS.DOB).toContain("BIRTH_CERTIFICATE");
      expect(ALLOWED_DOCUMENTS.DOB).toContain("PASSPORT");
      expect(ALLOWED_DOCUMENTS.DOB).toContain("PAN_CARD");
      expect(ALLOWED_DOCUMENTS.DOB).not.toContain("UTILITY_BILL");
    });

    it("should have correct document types for CONTACT", () => {
      expect(ALLOWED_DOCUMENTS.CONTACT).toContain("CONSENT_FORM");
      expect(ALLOWED_DOCUMENTS.CONTACT).toHaveLength(1);
    });

    it("should cover all change types", () => {
      const changeTypes: ChangeType[] = ["LEGAL_NAME", "ADDRESS", "DOB", "CONTACT"];
      changeTypes.forEach((type) => {
        expect(ALLOWED_DOCUMENTS[type]).toBeDefined();
        expect(Array.isArray(ALLOWED_DOCUMENTS[type])).toBe(true);
        expect(ALLOWED_DOCUMENTS[type].length).toBeGreaterThan(0);
      });
    });
  });

  describe("CHANGE_TYPE_LABELS", () => {
    it("should have labels for all change types", () => {
      expect(CHANGE_TYPE_LABELS.LEGAL_NAME).toBe("Legal Name Change");
      expect(CHANGE_TYPE_LABELS.ADDRESS).toBe("Address Change");
      expect(CHANGE_TYPE_LABELS.DOB).toBe("Date of Birth Correction");
      expect(CHANGE_TYPE_LABELS.CONTACT).toBe("Contact / Email Update");
    });

    it("should be user-friendly labels", () => {
      Object.values(CHANGE_TYPE_LABELS).forEach((label) => {
        expect(label.length).toBeGreaterThan(0);
        expect(label).not.toMatch(/[_]/); // No underscores
        expect(label[0]).toBe(label[0].toUpperCase()); // Capitalized
      });
    });
  });

  describe("DOCUMENT_TYPE_LABELS", () => {
    it("should have labels for all document types", () => {
      const documentTypes: DocumentType[] = [
        "MARRIAGE_CERTIFICATE",
        "GAZETTE_NOTIFICATION",
        "DEED_POLL",
        "COURT_ORDER",
        "UTILITY_BILL",
        "LEASE_AGREEMENT",
        "BIRTH_CERTIFICATE",
        "PASSPORT",
        "PAN_CARD",
        "CONSENT_FORM",
      ];

      documentTypes.forEach((type) => {
        expect(DOCUMENT_TYPE_LABELS[type]).toBeDefined();
        expect(DOCUMENT_TYPE_LABELS[type].length).toBeGreaterThan(0);
      });
    });

    it("should be user-friendly labels", () => {
      Object.values(DOCUMENT_TYPE_LABELS).forEach((label) => {
        expect(label).not.toMatch(/[_]/); // No underscores
        expect(label[0]).toBe(label[0].toUpperCase()); // Capitalized
      });
    });
  });

  describe("STATUS_LABELS", () => {
    it("should have labels for all statuses", () => {
      const statuses: RequestStatus[] = [
        "INTAKE_RECEIVED",
        "VALIDATED",
        "QUEUED",
        "PROCESSING",
        "AI_VERIFIED_PENDING_HUMAN",
        "IN_REVIEW",
        "PENDING_INFO",
        "ESCALATED",
        "REPROCESSING",
        "APPROVED",
        "REJECTED",
        "COMPLETED",
        "FAILED",
      ];

      statuses.forEach((status) => {
        expect(STATUS_LABELS[status]).toBeDefined();
        expect(STATUS_LABELS[status].length).toBeGreaterThan(0);
      });
    });

    it("should be user-friendly labels", () => {
      Object.values(STATUS_LABELS).forEach((label) => {
        expect(label).not.toMatch(/[_]/); // No underscores
      });
    });
  });

  describe("RISK_TIER_COLORS", () => {
    it("should have colors for all risk tiers", () => {
      expect(RISK_TIER_COLORS.LOW).toBeDefined();
      expect(RISK_TIER_COLORS.MEDIUM).toBeDefined();
      expect(RISK_TIER_COLORS.HIGH).toBeDefined();
    });

    it("should use appropriate color semantics", () => {
      expect(RISK_TIER_COLORS.LOW).toContain("green");
      expect(RISK_TIER_COLORS.MEDIUM).toContain("yellow");
      expect(RISK_TIER_COLORS.HIGH).toContain("red");
    });

    it("should be valid Tailwind classes", () => {
      Object.values(RISK_TIER_COLORS).forEach((classes) => {
        expect(classes).toMatch(/bg-\w+-\d+/);
        expect(classes).toMatch(/text-\w+-\d+/);
      });
    });
  });

  describe("RECOMMENDATION_COLORS", () => {
    it("should have colors for all recommendations", () => {
      expect(RECOMMENDATION_COLORS.APPROVE).toBeDefined();
      expect(RECOMMENDATION_COLORS.REJECT).toBeDefined();
      expect(RECOMMENDATION_COLORS.MANUAL_REVIEW).toBeDefined();
    });

    it("should use appropriate color semantics", () => {
      expect(RECOMMENDATION_COLORS.APPROVE).toContain("green");
      expect(RECOMMENDATION_COLORS.REJECT).toContain("red");
      expect(RECOMMENDATION_COLORS.MANUAL_REVIEW).toContain("yellow");
    });
  });
});

describe("Type Consistency", () => {
  it("should have matching keys in CHANGE_TYPE_LABELS and ALLOWED_DOCUMENTS", () => {
    const labelKeys = Object.keys(CHANGE_TYPE_LABELS);
    const documentKeys = Object.keys(ALLOWED_DOCUMENTS);

    expect(labelKeys.sort()).toEqual(documentKeys.sort());
  });

  it("should have all document types from ALLOWED_DOCUMENTS in DOCUMENT_TYPE_LABELS", () => {
    const allDocTypes = new Set<string>();
    Object.values(ALLOWED_DOCUMENTS).forEach((docs) => {
      docs.forEach((doc) => allDocTypes.add(doc));
    });

    allDocTypes.forEach((docType) => {
      expect(DOCUMENT_TYPE_LABELS[docType as DocumentType]).toBeDefined();
    });
  });
});
