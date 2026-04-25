# Intelligent Account Servicing Workflow (IASW)
## High-Level Design Document

---

## 1. Overview

### 1.1 Purpose
The Intelligent Account Servicing Workflow (IASW) automates the processing of customer account change requests (e.g., Legal Name Change) by combining document processing, AI-powered verification, and human oversight.

### 1.2 Goals
- Reduce manual effort for staff by automating document validation and extraction
- Ensure compliance through immutable audit trails
- Minimize fraud risk via multi-layer forgery detection
- Maintain human-in-the-loop for final decision making

### 1.3 Scope
**In Scope:**
- Legal Name Change requests (Marriage Certificate, Gazette Notification, Deed Poll, Court Order)
- Document ingestion, OCR, classification, and field extraction
- Forgery detection and confidence scoring
- Human checker review workflow
- Core banking (RPS) integration

**Out of Scope:**
- Other account servicing requests (address change, KYC refresh, etc.) — future phases
- Customer self-service portal

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          INTAKE LAYER (SYNCHRONOUS)                              │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐                 │
│  │ Staff Portal│───▶│ Intake Service   │───▶│ Validation      │                 │
│  │ (Web UI)    │    │ (API Gateway)    │    │ Agent           │                 │
│  └─────────────┘    └──────────────────┘    └────────┬────────┘                 │
│                                                      │                          │
│         Staff blocked here until validation passes (< 500ms)                    │
└──────────────────────────────────────────────────────┼──────────────────────────┘
                                                       │
                              ═══════════════════════════════════════════
                                    ASYNC BOUNDARY (Staff Released)
                              ═══════════════════════════════════════════
                                                       │
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          PROCESSING LAYER (ASYNCHRONOUS)                         │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐                 │
│  │ Job Queue   │───▶│ Document         │───▶│ AI Processing   │                 │
│  │ (Async)     │    │ Processor Agent  │    │ Pipeline        │                 │
│  └─────────────┘    └──────────────────┘    └────────┬────────┘                 │
│                                                      │                          │
│  ┌─────────────────────────────────────────────────────────────────────┐        │
│  │                     AI Processing Pipeline                          │        │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │        │
│  │  │  OCR    │─▶│ Doc     │─▶│ Field   │─▶│ Forgery │─▶│Confidence│  │        │
│  │  │         │  │Classifier│  │Extractor│  │Detector │  │ Scorer  │   │        │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └────┬────┘   │        │
│  │                                                           │        │        │
│  │                                                    ┌──────▼──────┐ │        │
│  │                                                    │  Summary    │ │        │
│  │                                                    │  Agent      │ │        │
│  │                                                    └─────────────┘ │        │
│  └─────────────────────────────────────────────────────────────────────┘        │
│                                                                                 │
│         Background processing, no user waiting                                  │
└──────────────────────────────────────────────────────┬──────────────────────────┘
                                                       │
                              ═══════════════════════════════════════════
                                   STAGING (Pending Table Write)
                              ═══════════════════════════════════════════
                                                       │
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          REVIEW LAYER (HUMAN-GATED)                              │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐                 │
│  │ Checker     │◀──▶│ Review Service   │───▶│ Decision        │                 │
│  │ Workbench   │    │                  │    │ Engine          │                 │
│  │ (Web UI)    │    │                  │    │                 │                 │
│  └─────────────┘    └──────────────────┘    └────────┬────────┘                 │
│                                                      │                          │
│         Human Checker must APPROVE/REJECT — AI cannot proceed past this point   │
└──────────────────────────────────────────────────────┼──────────────────────────┘
                                                       │
                              ═══════════════════════════════════════════
                                   HITL BOUNDARY (Human Approval Required)
                              ═══════════════════════════════════════════
                                                       │
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          INTEGRATION LAYER (SYNCHRONOUS)                         │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐                 │
│  │ RPS Update  │    │ FileNet          │    │ Notification    │                 │
│  │ Microservice│    │ (Document Store) │    │ Service         │                 │
│  └─────────────┘    └──────────────────┘    └─────────────────┘                 │
│                                                                                 │
│         Triggered ONLY by human Checker approval                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                                       │
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CROSS-CUTTING CONCERNS                              │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐                 │
│  │ Audit Log   │    │ Metrics &        │    │ Dead Letter     │                 │
│  │ Service     │    │ Observability    │    │ Queue           │                 │
│  └─────────────┘    └──────────────────┘    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Boundary Summary:**

| Boundary | Type | Description |
|----------|------|-------------|
| Intake → Processing | **ASYNC** | Staff released after validation; processing happens in background |
| Processing → Review | **STAGING** | AI writes to Pending Table with status `AI_VERIFIED_PENDING_HUMAN` |
| Review → Integration | **HITL GATE** | Human Checker must approve; AI cannot trigger RPS update |
| Integration calls | **SYNC** | RPS update is synchronous with circuit breaker protection |

---

## 3. Component Design

### 3.1 Intake Service

**Responsibility:** Accept and validate incoming requests from staff portal

**Key Functions:**
- Generate idempotency key to prevent duplicates
- Perform synchronous validation (< 500ms)
- Create request record and return reference number

**Validation Checks:**
| Check | Description |
|-------|-------------|
| RPS Lookup | Verify customer exists in core banking |
| Name Match | Fuzzy match input name against RPS record (≥95%) |
| Doc Type Validation | Verify document type is allowed for change type |
| File Check | Validate format (PDF/JPEG/PNG/TIFF) and size (≤10MB) |
| Virus Scan | ClamAV quick scan (timeout: 200ms) |
| Duplicate Check | No in-progress request for same customer + change type |

---

### 3.2 Job Queue

**Responsibility:** Manage async processing with reliability guarantees

**Properties:**
- At-least-once delivery
- Idempotent processing (dedup by request_id)
- Priority levels: EXPEDITE > NORMAL > RESUBMIT
- Visibility timeout: 10 minutes
- Retry policy: 3 attempts with exponential backoff
- Dead Letter Queue for failed jobs

**Timeouts:**
| Step | Timeout |
|------|---------|
| Document processing (overall) | 90 seconds |
| OCR extraction | 30 seconds/page |
| LLM parsing | 20 seconds |
| Forgery detection | 45 seconds |
| Confidence scoring | 10 seconds |
| Summary generation | 15 seconds |
| **Overall job timeout** | **5 minutes** |

---

### 3.3 Document Processor

**Responsibility:** Handle file ingestion and prepare for AI processing

**Processing Flow:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Virus Scan   │────▶│ File Type    │────▶│ Image Pre-   │
│ (Deep)       │     │ Detection    │     │ Processing   │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                     ┌───────────────────────────┴───────────────────────────┐
                     │                                                       │
                     ▼                                                       ▼
              ┌──────────────┐                                    ┌──────────────┐
              │ PDF with     │                                    │ Scanned PDF  │
              │ Text Layer   │                                    │ or Image     │
              └──────┬───────┘                                    └──────┬───────┘
                     │                                                   │
                     │ Extract text directly                             │ OCR Pipeline
                     │                                                   │
                     └───────────────────────────┬───────────────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │ Post-Process │
                                          │ (Normalize)  │
                                          └──────────────┘
```

**Image Pre-Processing Steps:**
1. Deskew (Hough transform)
2. Binarize (Sauvola adaptive threshold)
3. Denoise (Median filter + morphological open)
4. Upsample to 300 DPI
5. Sharpen edges

**OCR Engine:**
- Primary: Tesseract 5 (LSTM mode)
- Fallback: Google Cloud Vision API

---

### 3.4 AI Processing Pipeline

#### 3.4.1 Document Classifier

**Responsibility:** Verify uploaded document matches declared type

**Input:** OCR text
**Output:** Detected type, confidence, signals

**Classification Outcomes:**
| Result | Action |
|--------|--------|
| MATCH (detected = declared) | Proceed |
| MISMATCH | Flag `DOC_TYPE_MISMATCH` → reject or review |
| UNCERTAIN (confidence < 70%) | Flag `DOC_TYPE_UNCERTAIN` → checker review |

#### 3.4.2 Field Extractor

**Responsibility:** Extract structured fields from document

**For Marriage Certificate:**
| Field | Purpose | Required |
|-------|---------|----------|
| bride_name | Maps to Old Name | Critical |
| married_name | Maps to New Name | Critical |
| marriage_date | Reference | Recommended |
| groom_name | Context | Optional |
| issuing_authority | Authenticity | Optional |
| certificate_number | Dedup reference | Optional |

#### 3.4.3 Forgery Detector

**Responsibility:** Detect document tampering using multi-layer analysis

**Detection Layers:**
```
┌─────────────────────────────────────────────────────────────┐
│                    FORGERY DETECTION                         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Metadata    │  │ ELA         │  │ Font        │         │
│  │ Analysis    │  │ Analysis    │  │ Consistency │         │
│  │ (20%)       │  │ (30%)       │  │ (20%)       │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│                          ▼                                  │
│                   ┌─────────────┐                           │
│                   │ ML Model    │                           │
│                   │ (30%)       │                           │
│                   └──────┬──────┘                           │
│                          │                                  │
│                          ▼                                  │
│                   ┌─────────────┐                           │
│                   │ Aggregated  │                           │
│                   │ Score       │                           │
│                   └─────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

**Score Thresholds:**
| Score | Result | Action |
|-------|--------|--------|
| > 0.85 | PASS | Likely authentic |
| 0.60–0.85 | FLAG | Human review required |
| < 0.60 | FAIL | Likely forged → senior checker |

#### 3.4.4 Confidence Scorer

**Responsibility:** Aggregate all signals into risk tier

**Score Components:**
| Signal | Weight |
|--------|--------|
| Name Match (Old + New) | 40% |
| Document Authenticity | 30% |
| OCR Confidence | 15% |
| LLM Extraction Confidence | 15% |

**Risk Tiers:**
| Tier | Condition | Routing |
|------|-----------|---------|
| LOW | Score ≥ 90%, no flags | Standard queue |
| MEDIUM | Score 70–90%, or minor flags | Standard queue, highlighted |
| HIGH | Score < 70%, or major flags | Senior checker queue |

#### 3.4.5 Summary Generator

**Responsibility:** Generate human-readable brief with AI recommendation

**Recommendation Logic:**
| Recommendation | Conditions |
|----------------|------------|
| APPROVE | Score ≥ 85%, name match ≥ 95%, no HIGH flags, forgery = PASS |
| MANUAL_REVIEW | Score 60–85%, or MEDIUM flag, or forgery = FLAG |
| REJECT | Score < 60%, or name match < 70%, or forgery = FAIL |

---

### 3.5 Review Service

**Responsibility:** Manage checker workflow and request assignment

**Queues:**
| Queue | Access | Contents |
|-------|--------|----------|
| Standard | All checkers | LOW and MEDIUM risk |
| Senior | Senior checkers only | HIGH risk |

**Claim Flow:**
1. Checker opens workbench
2. Clicks "Claim Next" or selects specific request
3. System sets lock (15 min timeout)
4. Status → IN_REVIEW
5. On lock expiry: release back to queue

**Checker Actions:**
| Action | Effect |
|--------|--------|
| APPROVE | Trigger RPS update |
| REJECT | Log reason, notify branch |
| MORE INFO | Notify branch, allow resubmit (max 3) |
| ESCALATE | Route to supervisor/senior |
| RE-PROCESS | Re-queue with different OCR params |

---

### 3.6 Integration Services

#### 3.6.1 RPS Update Service
- Updates core banking system
- Protected by circuit breaker
- Triggered only on APPROVE

#### 3.6.2 FileNet Service
- Two-phase storage: Staging → Permanent
- Approved: 7-year retention
- Rejected: 90-day retention, auto-purge

#### 3.6.3 Notification Service
- Branch notifications (MORE INFO, REJECT)
- Ops alerts (failures, DLQ)

---

### 3.7 Audit Log Service

**Responsibility:** Maintain immutable, tamper-evident audit trail

**Record Schema:**
| Field | Description |
|-------|-------------|
| audit_id | UUID primary key |
| request_id | Associated request |
| event_type | STATE_CHANGE, HUMAN_ACTION, SYSTEM_EVENT, ERROR |
| previous_state | State before transition |
| new_state | State after transition |
| actor_type | SYSTEM, HUMAN, AI_AGENT |
| actor_id | Identifier of actor |
| agent_name | AI agent name (if applicable) |
| agent_version | Version of AI agent |
| llm_model | LLM model used |
| action_details | JSON details |
| record_snapshot | Full state at this moment |
| timestamp | ISO 8601 timestamp |
| checksum | SHA-256 for tamper detection |

---

## 4. Agent Design Summary

| Component | Responsibility | Input | Output |
|-----------|----------------|-------|--------|
| Validation Agent | Validate intake fields against RPS + document type check | Change request form + uploaded file metadata | Field-level validation result (PASS/FAIL per check) |
| Document Processor Agent | OCR + text extraction + image pre-processing | Uploaded document (PDF/image) | Raw text, per-word confidence, bounding boxes |
| Document Classifier Agent | Verify document matches declared type | OCR text | Detected type, confidence score, match/mismatch flag |
| Field Extractor Agent | Extract structured fields from document | OCR text + document type | Extracted fields with per-field confidence + source snippets |
| Forgery Detector Agent | Detect document tampering | Original document + processed images | Forgery score (0-1), layer-wise scores, PASS/FLAG/FAIL result |
| Confidence Scorer Agent | Score each field match and aggregate risk | Extracted fields + request data + forgery result | Confidence Score Card + risk tier (LOW/MEDIUM/HIGH) |
| Summary Agent | Generate human-readable review summary | Score card + document metadata + flags | Natural language summary + recommended action (APPROVE/REJECT/MANUAL_REVIEW) |

---

## 5. HITL (Human-in-the-Loop) Boundary Design

### 5.1 Core Principle

**AI assists, humans decide.** No customer data is modified in core banking (RPS) without explicit human approval.

### 5.2 What AI Can Do Autonomously

| Action | Autonomous? | Rationale |
|--------|-------------|-----------|
| Validate file format, size, virus scan | ✅ Yes | Technical checks, no business judgment |
| Perform OCR and text extraction | ✅ Yes | Data transformation, no decision |
| Classify document type | ✅ Yes | Detection only, mismatch flagged for human |
| Extract fields from document | ✅ Yes | Data extraction, not modification |
| Detect potential forgery | ✅ Yes | Flag generation, human reviews flags |
| Calculate confidence scores | ✅ Yes | Scoring algorithm, transparent to checker |
| Generate summary and recommendation | ✅ Yes | Recommendation only, not execution |
| Route to appropriate queue | ✅ Yes | Based on risk tier rules |
| **Reject request** | ❌ No | Human must confirm rejection |
| **Approve request** | ❌ No | Human must approve |
| **Update core banking (RPS)** | ❌ No | Only triggered by human APPROVE action |
| **Request more information** | ❌ No | Human decides what's needed |

### 5.3 HITL Enforcement Mechanisms

```
┌─────────────────────────────────────────────────────────────────┐
│                      HITL BOUNDARY                               │
│                                                                 │
│   AI ZONE (Autonomous)          │    HUMAN ZONE (Gated)         │
│   ─────────────────────         │    ──────────────────         │
│                                 │                               │
│   • Intake validation           │    • Final APPROVE/REJECT     │
│   • Document processing         │    • RPS update trigger       │
│   • OCR & extraction       ─────┼───▶• Escalation decisions     │
│   • Forgery detection           │    • More info requests       │
│   • Confidence scoring          │    • Override AI recommendation│
│   • Summary generation          │                               │
│   • Queue routing               │                               │
│                                 │                               │
└─────────────────────────────────────────────────────────────────┘
```

**Technical Enforcement:**

1. **State Machine Guard:** The `APPROVED` and `REJECTED` states can only be reached from `IN_REVIEW` state, which requires a human checker to claim the request.

2. **Actor Validation:** RPS Update Service validates that `actor_type = HUMAN` before processing any update. System-initiated calls are rejected.

3. **Audit Trail:** Every state transition logs `actor_type` (SYSTEM/HUMAN/AI_AGENT). Compliance can verify no AI actor triggered final decisions.

4. **UI-Only Actions:** APPROVE, REJECT, MORE_INFO, and ESCALATE buttons exist only in the Checker Workbench UI. No API endpoint allows AI agents to invoke these actions.

5. **Recommendation ≠ Decision:** AI generates `ai_recommendation` field (APPROVE/REJECT/MANUAL_REVIEW), but this is advisory. The `checker_decision` field is populated only by human action.

### 5.4 Override Tracking

When a human checker disagrees with AI recommendation:

| AI Recommendation | Human Decision | Logged As |
|-------------------|----------------|-----------|
| APPROVE | REJECT | `override_type: AI_TOO_LENIENT` |
| REJECT | APPROVE | `override_type: AI_TOO_STRICT` |
| MANUAL_REVIEW | APPROVE/REJECT | `override_type: NONE` (expected) |

Override metrics feed back into model calibration (see Metrics section).

---

## 6. Data Model — Pending Table Schema

### 6.1 Core Schema

```sql
CREATE TABLE pending_requests (
    -- Identity
    request_id              VARCHAR(36) PRIMARY KEY,    -- e.g., "REQ-12345"
    idempotency_key         VARCHAR(64) UNIQUE,         -- hash for dedup
    customer_id             VARCHAR(20) NOT NULL,       -- e.g., "C001"
    
    -- Request Details
    change_type             VARCHAR(50) NOT NULL,       -- e.g., "LEGAL_NAME"
    document_type           VARCHAR(50) NOT NULL,       -- e.g., "MARRIAGE_CERTIFICATE"
    
    -- Requested Values
    requested_old_value     VARCHAR(255) NOT NULL,      -- e.g., "Priya Sharma"
    requested_new_value     VARCHAR(255) NOT NULL,      -- e.g., "Priya Mehta"
    
    -- Extracted Values (from document)
    extracted_old_value     VARCHAR(255),               -- e.g., "Priya Sharma" (from bride_name)
    extracted_new_value     VARCHAR(255),               -- e.g., "Priya Mehta" (from married_name)
    extraction_metadata     JSONB,                      -- all extracted fields with confidence
    
    -- Confidence Scores (per field)
    old_name_match_score    DECIMAL(5,4),               -- e.g., 1.0000 (100%)
    new_name_match_score    DECIMAL(5,4),               -- e.g., 1.0000 (100%)
    ocr_confidence          DECIMAL(5,4),               -- e.g., 0.9200 (92%)
    extraction_confidence   DECIMAL(5,4),               -- e.g., 0.9400 (94%)
    doc_authenticity_score  DECIMAL(5,4),               -- e.g., 0.8700 (87%)
    overall_confidence      DECIMAL(5,4),               -- weighted aggregate
    
    -- Forgery Detection
    forgery_score           DECIMAL(5,4),               -- 0.0 (forged) to 1.0 (authentic)
    forgery_result          VARCHAR(10),                -- PASS / FLAG / FAIL
    forgery_details         JSONB,                      -- per-layer scores
    
    -- Risk & Routing
    risk_tier               VARCHAR(10),                -- LOW / MEDIUM / HIGH
    flags                   JSONB,                      -- array of flag codes
    ai_recommendation       VARCHAR(20),                -- APPROVE / REJECT / MANUAL_REVIEW
    ai_summary              TEXT,                       -- human-readable summary
    
    -- Document Storage
    document_storage_path   VARCHAR(255),               -- S3 path to original
    filenet_staging_id      VARCHAR(100),               -- FileNet staging reference
    filenet_permanent_id    VARCHAR(100),               -- FileNet permanent reference (after decision)
    
    -- Workflow Status
    status                  VARCHAR(30) NOT NULL,       -- current state
    assigned_checker        VARCHAR(50),                -- checker who claimed
    checker_lock_until      TIMESTAMP,                  -- lock expiry time
    checker_decision        VARCHAR(20),                -- APPROVE / REJECT / MORE_INFO / ESCALATE
    checker_decision_reason TEXT,                       -- mandatory for REJECT/ESCALATE
    
    -- Resubmit Tracking
    resubmit_count          INT DEFAULT 0,              -- times customer resubmitted
    max_resubmits           INT DEFAULT 3,              -- limit before auto-escalate
    original_request_id     VARCHAR(36),                -- links to first submission
    
    -- Timestamps
    created_at              TIMESTAMP NOT NULL,         -- intake time
    validated_at            TIMESTAMP,                  -- passed validation
    processing_started_at   TIMESTAMP,                  -- job picked up
    processing_completed_at TIMESTAMP,                  -- AI processing done
    staged_at               TIMESTAMP,                  -- ready for review
    claimed_at              TIMESTAMP,                  -- checker claimed
    decided_at              TIMESTAMP,                  -- final decision made
    completed_at            TIMESTAMP,                  -- RPS updated (if approved)
    
    -- Audit
    created_by              VARCHAR(50),                -- staff who submitted
    last_updated_at         TIMESTAMP,
    last_updated_by         VARCHAR(50)
);
```

### 6.2 Key Indexes

```sql
CREATE INDEX idx_pending_status ON pending_requests(status);
CREATE INDEX idx_pending_customer ON pending_requests(customer_id);
CREATE INDEX idx_pending_risk_tier ON pending_requests(risk_tier, status);
CREATE INDEX idx_pending_checker ON pending_requests(assigned_checker, status);
CREATE INDEX idx_pending_created ON pending_requests(created_at);
```

### 6.3 Status Values

| Status | Description |
|--------|-------------|
| `INTAKE_RECEIVED` | Request submitted, not yet validated |
| `VALIDATED` | Passed synchronous validation |
| `QUEUED` | Added to async job queue |
| `PROCESSING` | Document processing in progress |
| `AI_VERIFIED_PENDING_HUMAN` | AI complete, awaiting checker |
| `IN_REVIEW` | Checker has claimed and is reviewing |
| `PENDING_INFO` | Awaiting additional info from customer |
| `ESCALATED` | Routed to supervisor/senior |
| `REPROCESSING` | Re-queued for OCR with new params |
| `APPROVED` | Checker approved, RPS update pending |
| `REJECTED` | Checker rejected |
| `COMPLETED` | RPS updated successfully |
| `FAILED` | Processing failed, in DLQ |

### 6.4 Example Record

```json
{
  "request_id": "REQ-12345",
  "idempotency_key": "a1b2c3d4e5f6...",
  "customer_id": "C001",
  "change_type": "LEGAL_NAME",
  "document_type": "MARRIAGE_CERTIFICATE",
  
  "requested_old_value": "Priya Sharma",
  "requested_new_value": "Priya Mehta",
  "extracted_old_value": "Priya Sharma",
  "extracted_new_value": "Priya Mehta",
  
  "old_name_match_score": 1.0000,
  "new_name_match_score": 1.0000,
  "ocr_confidence": 0.9200,
  "extraction_confidence": 0.9400,
  "doc_authenticity_score": 0.8700,
  "overall_confidence": 0.9460,
  
  "forgery_score": 0.8700,
  "forgery_result": "PASS",
  
  "risk_tier": "LOW",
  "flags": [],
  "ai_recommendation": "APPROVE",
  "ai_summary": "Marriage Certificate verified. Old name matches (100%). New name matches (100%). Document authenticity passed (87%). Recommendation: APPROVE",
  
  "filenet_staging_id": "FN-STG-12345",
  "status": "AI_VERIFIED_PENDING_HUMAN",
  
  "created_at": "2024-03-20T10:30:00Z",
  "staged_at": "2024-03-20T10:30:48Z"
}
```

---

## 7. Data Flow

### 7.1 Happy Path Flow

```
Staff Submit ──▶ Validation ──▶ Queue ──▶ Doc Process ──▶ AI Pipeline
     │               │            │            │              │
     │               │            │            │              ▼
     │               │            │            │         Confidence
     │               │            │            │         Scoring
     │               │            │            │              │
     │               │            │            │              ▼
     │               │            │            │         Summary
     │               │            │            │         Generation
     │               │            │            │              │
     ▼               ▼            ▼            ▼              ▼
INTAKE_RECEIVED → VALIDATED → QUEUED → PROCESSING → AI_VERIFIED_PENDING_HUMAN
                                                              │
                                                              ▼
                                                      Checker Review
                                                              │
                                                              ▼
                                                         APPROVED
                                                              │
                                                              ▼
                                                      RPS Update ──▶ COMPLETED
```

### 7.2 State Machine

```
                                    ┌──────────────┐
                                    │   INTAKE     │
                                    │   RECEIVED   │
                                    └──────┬───────┘
                                           │ validation passes
                                           ▼
                                    ┌──────────────┐
                              ┌─────│  VALIDATED   │
                              │     └──────┬───────┘
                              │            │ queued
                              │            ▼
                              │     ┌──────────────┐
                              │     │   QUEUED     │
                              │     └──────┬───────┘
                              │            │ processing starts
                              │            ▼
                              │     ┌──────────────┐
                              │     │  PROCESSING  │◀──────────────────┐
                              │     └──────┬───────┘                   │
                              │            │ AI complete               │
                              │            ▼                           │
                              │     ┌──────────────┐                   │
                              │     │  AI_VERIFIED │                   │
                              │     │  PENDING_    │                   │
                              │     │  HUMAN       │                   │
                              │     └──────┬───────┘                   │
                              │            │ checker claims            │
                              │            ▼                           │
                              │     ┌──────────────┐                   │
                              │     │  IN_REVIEW   │───────────────────┤
                              │     └──────┬───────┘   RE-PROCESS      │
                              │            │                           │
                     ┌────────┼────────────┼────────────┐              │
                     │        │            │            │              │
                     ▼        ▼            ▼            ▼              │
              ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
              │ APPROVED │ │ REJECTED │ │ PENDING  │ │ ESCALATED│     │
              └────┬─────┘ └──────────┘ │ INFO     │ └──────────┘     │
                   │                    └────┬─────┘                   │
                   │                         │ resubmit                │
                   │                         └─────────────────────────┘
                   │ RPS update
                   ▼
              ┌──────────┐
              │ COMPLETED│
              └──────────┘
```

---

## 8. Technology Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Frontend** | Next.js 14 (React) | Server-side rendering for fast initial load, API routes for BFF pattern, TypeScript support |
| **Backend / API** | FastAPI (Python) | Async support, automatic OpenAPI docs, excellent for ML/AI integration |
| **Orchestration** | LangGraph | Graph-based workflows for multi-agent pipelines, conditional routing, state management |
| **LLM** | Claude 3.5 Sonnet | Strong document understanding, structured output, cost-effective |
| **OCR** | Google Document AI | High accuracy on government documents, handles poor scans well |
| **Queue** | Redis + Celery | Simple setup, reliable, good monitoring with Flower |
| **Database** | PostgreSQL | JSONB for flexible metadata, robust, ACID compliance |
| **Document Storage** | S3 (mock: local filesystem) | Standard interface, easy to mock for development |
| **Observability** | LangSmith | Native LangChain integration, tracks LLM calls, prompt debugging |

### Technology Justification

**Why Next.js over plain React?**
- Server-side rendering improves initial page load for Checker Workbench
- API routes allow Backend-for-Frontend pattern (aggregate calls for Checker UI)
- Built-in image optimization for document previews
- File-based routing simplifies the two-UI structure (Staff Portal + Checker Workbench)

**Why FastAPI over Node.js?**
- Native async/await for non-blocking I/O (critical for queue processing)
- Python ecosystem has better ML/AI library support (LangChain, OpenCV, Tesseract bindings)
- Pydantic models provide automatic validation and serialization
- Auto-generated OpenAPI docs speed up frontend integration

**Why LangGraph over LangChain/CrewAI?**
- **Graph-based workflow** fits our pipeline perfectly — each agent (OCR → Classifier → Extractor → Forgery → Scorer → Summary) is a node
- **Conditional routing** — can skip steps or route to different paths based on confidence scores (e.g., low OCR confidence → fallback OCR)
- **State management** — maintains request state across nodes without manual passing
- **Built on LangChain** — still access to LangChain's document loaders, LLM integrations, and tools
- **Checkpointing** — can resume failed workflows from last successful node (important for 5-minute jobs)
- CrewAI is better for autonomous multi-agent collaboration, but our pipeline is sequential with clear handoffs

**Why Claude 3.5 Sonnet over GPT-4o?**
- Excellent at structured data extraction from documents
- Lower cost per token for high-volume processing
- Strong reasoning for forgery signal interpretation
- Consistent JSON output formatting

**Trade-offs Considered:**
- CrewAI would provide better multi-agent orchestration, but adds complexity for a single-flow prototype
- GPT-4o has faster response times, but Claude's extraction quality is higher for this use case
- AWS Textract is an alternative to Google Document AI, but Google handles Indian government documents better

---

## 9. Security Considerations

| Concern | Mitigation |
|---------|------------|
| Document tampering | Multi-layer forgery detection |
| Malware upload | Two-stage virus scanning (quick + deep) |
| Unauthorized access | Role-based access (standard vs senior checker) |
| Data integrity | SHA-256 checksums on audit records |
| PII protection | No PII in log payloads |
| Duplicate fraud | Idempotency keys, duplicate request detection |

---

## 10. Scalability Considerations

| Component | Scaling Strategy |
|-----------|------------------|
| Intake Service | Horizontal scaling behind load balancer |
| Job Queue | Partitioned by priority level |
| Document Processor | Parallel page-level processing |
| AI Pipeline | Async processing, timeout-protected |
| Checker Workbench | Claim-based locking prevents conflicts |

---

## 11. Failure Handling

| Failure | Handling |
|---------|----------|
| Validation failure | Inline error, staff corrects and resubmits |
| Processing timeout | Retry with exponential backoff (max 3) |
| Max retries exceeded | Dead Letter Queue + ops alert |
| OCR low confidence | Flag for human review or re-upload |
| Forgery detected | Route to senior checker |
| Checker abandons | Lock expires, request released to queue |
| RPS update failure | Circuit breaker, retry with backoff |

---

## 12. Metrics & Monitoring

**Operational Metrics:**
- Requests per hour (by change type)
- Average processing time (queue → staged)
- Average review time (staged → decision)
- End-to-end latency (intake → completed)

**Quality Metrics:**
- OCR confidence distribution
- Extraction success rate
- Forgery detection rate (PASS / FLAG / FAIL)

**AI Performance Metrics:**
- Override rate (AI recommendation vs human decision)
- False positive rate (AI approved, human rejected)
- False negative rate (AI rejected, human approved)

---

## 13. Future Enhancements

1. **Additional Change Types:** Address change, KYC refresh, account closure
2. **Customer Self-Service:** Portal for customers to submit requests directly
3. **External Verification:** Government API integration for certificate validation
4. **Advanced Forgery Detection:** Seal verification, watermark analysis
5. **Model Retraining Pipeline:** Automated recalibration based on audit log data