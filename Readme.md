# Intelligent Account Servicing Workflow (IASW)
### Legal Name Change — Full Flow

---

## Table of Contents

1. [Phase 1 — Intake](#phase-1--intake)
2. [Phase 2 — Synchronous Validation](#phase-2--synchronous-validation)
3. [Phase 3 — Async Job Queue](#phase-3--async-job-queue)
4. [Phase 4 — Document Processing Pipeline](#phase-4--document-processing-pipeline)
5. [Phase 5 — Confidence Scoring](#phase-5--confidence-scoring)
6. [Phase 6 — Summary Generation](#phase-6--summary-generation)
7. [Phase 7 — Staging](#phase-7--staging)
8. [Phase 8 — Human Checker Review](#phase-8--human-checker-review)
9. [Phase 9 — Outcomes](#phase-9--outcomes)
10. [Phase 10 — Audit Log](#phase-10--immutable-audit-log)
11. [Metrics & Observability](#metrics--observability)
12. [Forgery Detection — Deep Dive](#forgery-detection--deep-dive)

---

## Phase 1 — Intake

Staff submit a request through the intake form with the following fields:

| Field | Example Value |
|---|---|
| Customer ID | C001 |
| Current Name | Priya Sharma |
| Requested New Name | Priya Mehta |
| Change Type | Legal Name Change |
| Document Type | Marriage Certificate |
| Uploaded Document | marriage_cert.pdf |

**On Submit, the system:**

1. Generates an `idempotency_key = hash(customer_id + change_type + timestamp_minute + file_hash)`
2. Checks if the key already exists in DB → if yes, returns the existing request (prevents duplicates)
3. Creates a new request record with status: `INTAKE_RECEIVED`

---

## Phase 2 — Synchronous Validation

> **Target:** ≤ 500ms. Staff are blocked here only — they can move on once validation passes.

Six checks run in parallel. **All must pass** before the request is queued.

| # | Check | Logic | Pass / Fail |
|---|---|---|---|
| 1 | RPS Lookup | Customer ID exists in core banking | Yes → PASS / No → FAIL |
| 2 | Name Match | Input "Old Name" fuzzy-matches RPS record (≥95%) | Match → PASS / Mismatch → FAIL |
| 3 | Doc Type Validation | Uploaded doc type is allowed for this change type | Allowed → PASS / Not allowed → FAIL |
| 4 | File Check | Format is PDF/JPEG/PNG/TIFF and ≤10MB | Valid → PASS / Invalid → FAIL |
| 5 | Virus Scan | ClamAV quick scan (timeout: 200ms) | Clean → PASS / Threat → FAIL |
| 6 | Duplicate Check | No IN_PROGRESS request for same customer + change type | No dup → PASS / Dup → WARN |

**Allowed document types for Legal Name Change:** Marriage Certificate, Gazette Notification, Deed Poll, Court Order

**On any failure:** Staff sees an inline error message (e.g., `"Name mismatch: expected Priya Sharma, got Priya Singh"`) and must fix and resubmit.

**On all passing:** Request status → `VALIDATED`. Staff see a reference number and are **released** to handle the next customer. All further processing is async.

---

## Phase 3 — Async Job Queue

The job queue handles all further processing asynchronously. Staff are never blocked by this phase.

**Queue Properties:**
- At-least-once delivery guarantee
- Idempotent processing (dedup by `request_id`)
- Priority levels: `EXPEDITE > NORMAL > RESUBMIT`
- Visibility timeout: 10 minutes

**Timeout Policy:**

| Step | Timeout |
|---|---|
| Document processing (overall) | 90 seconds |
| OCR extraction | 30 seconds/page |
| LLM parsing | 20 seconds |
| Forgery detection | 45 seconds |
| Confidence scoring | 10 seconds |
| Summary generation | 15 seconds |
| **Overall job timeout** | **5 minutes** |

**Retry Policy:** 3 attempts with exponential backoff. On max retries → Dead Letter Queue + ops alert.

**Message Payload:**

```json
{
  "request_id": "REQ-12345",
  "customer_id": "C001",
  "change_type": "LEGAL_NAME",
  "old_value": "Priya Sharma",
  "new_value": "Priya Mehta",
  "document_type": "MARRIAGE_CERTIFICATE",
  "document_storage_path": "s3://intake-bucket/REQ-12345/marriage_cert.pdf",
  "attempt_number": 1,
  "resubmit_count": 0,
  "max_resubmits": 3,
  "priority": "NORMAL"
}
```

---

## Phase 4 — Document Processing Pipeline

> Steps run **sequentially** because each depends on the prior. Parallelism occurs at the **page level** within OCR.

### Step 4.1 — File Handling & Virus Re-Check

**Defense-in-depth:** The file is virus-scanned again (deep scan) before any content processing.

On a clean scan, the file type determines the processing path:

**PDF with embedded text layer:**
- Extract text directly
- Skip OCR for this content

**PDF (scanned) or Image (JPG/PNG/TIFF):**
1. Rasterize to 300 DPI PNG per page
2. Run Image Pre-Processing (can be parallelized per page):
    - **Deskew** — Hough transform to detect and correct skew angle
    - **Binarize** — Sauvola adaptive threshold to handle uneven lighting
    - **Denoise** — Median filter + morphological open to remove speckles
    - **Upsample** — Bicubic interpolation to 300 DPI if below threshold
    - **Sharpen** — Edge enhancement for text clarity
3. Run OCR

**Unknown format:** Reject immediately with `"Unsupported file type"` error.

**OCR Engine:**
- Primary: Tesseract 5 (LSTM mode)
- Fallback: Google Cloud Vision API

OCR outputs: raw text, per-word confidence scores, bounding box coordinates, page-level average confidence.

**OCR Confidence Thresholds:**

| Confidence | Action |
|---|---|
| > 90% | Proceed normally |
| 60–90% | Flag `OCR_MEDIUM_CONF`, surface to checker |
| < 60% | Flag `OCR_LOW_QUALITY`, prompt re-upload or manual review |

**Post-Processing (after OCR):**
- Spell check (proper noun aware)
- Date normalization (DD/MM/YYYY → ISO 8601)
- Name case normalization (PRIYA SHARMA → Priya Sharma)
- Layout re-assembly (reading order reconstruction)
- OCR artifact removal

---

### Step 4.2 — Document Classification

**Purpose:** Verify that the uploaded document actually matches the declared document type.

An LLM classifier receives the OCR text and returns:

```json
{ "detected_type": "MARRIAGE_CERTIFICATE", "confidence": 0.93, "signals": ["header_match", "layout_match"] }
```

**Possible detected types:** MARRIAGE_CERTIFICATE, GAZETTE_NOTIFICATION, DEED_POLL, COURT_ORDER, UTILITY_BILL, BIRTH_CERTIFICATE, PASSPORT, OTHER

**Classification outcomes:**

| Result | Condition | Action |
|---|---|---|
| MATCH | detected = declared | Proceed normally |
| MISMATCH | detected ≠ declared | Flag `DOC_TYPE_MISMATCH` → auto-reject or flag for review |
| UNCERTAIN | confidence < 70% | Flag `DOC_TYPE_UNCERTAIN` → surface to checker |

---

### Step 4.3 — LLM Field Extraction

The LLM extracts structured fields from the OCR text. Fields vary by document type.

**For a Marriage Certificate, required fields are:**

| Field | Mapped To | Required? |
|---|---|---|
| `bride_name` | Old Name | ✅ Critical |
| `married_name` | New Name | ✅ Critical |
| `marriage_date` | Reference | Recommended |
| `groom_name` | Context | Optional |
| `issuing_authority` | Authenticity | Optional |
| `certificate_number` | Dedup reference | Optional |

Each field is returned with a `value`, `confidence` (0–1), and `source_snippet`.

**Field Confidence Outcomes:**

| Result | Condition | Action |
|---|---|---|
| ALL REQUIRED FOUND | Both critical fields, conf > 0.7 | Proceed to scoring |
| PARTIAL | Some fields missing or low confidence | Flag `PARTIAL_EXTRACTION`, checker sees gaps |
| CRITICAL MISSING | `bride_name` or `married_name` absent | Flag `EXTRACTION_FAILED`, checker must manually review or request re-upload |

**Example output:**

```json
{
  "bride_name":    { "value": "Priya Sharma", "confidence": 0.97 },
  "married_name":  { "value": "Priya Mehta",  "confidence": 0.94 },
  "marriage_date": { "value": "2024-03-15",   "confidence": 0.91 },
  "groom_name":    { "value": "Rahul Mehta",  "confidence": 0.88 },
  "ocr_confidence": 0.92,
  "llm_confidence": 0.94,
  "flags": ["OCR_MEDIUM_CONF"]
}
```

---

### Step 4.4 — Forgery Detection

> See [Forgery Detection — Deep Dive](#forgery-detection--deep-dive) for full implementation guidance.

Four detection layers run and are aggregated into a single score:

| Layer | Weight | What it checks |
|---|---|---|
| Metadata Analysis | 20% | Creation vs modification dates, software used, EXIF anomalies |
| Error Level Analysis (ELA) | 30% | Re-compression differences that reveal edited regions |
| Font Consistency | 20% | Font mismatches in name fields, kerning/baseline irregularities |
| ML Model | 30% | Pre-trained forgery pattern detection, template matching |

**Forgery Score = (metadata × 0.2) + (ela × 0.3) + (font × 0.2) + (ml × 0.3)**

| Score | Result | Action |
|---|---|---|
| > 0.85 | PASS | Likely authentic, proceed |
| 0.60–0.85 | FLAG | Needs human review |
| < 0.60 | FAIL | Likely forged, route to senior checker |

---

### Step 4.5 — Archive to FileNet (Two-Phase)

**Phase 1 — Staging (immediately after processing):**

Stored at `filenet://staging/{request_id}/`:
- `original_document.pdf`
- `processed_pages/page_001.png` etc.
- `extraction_result.json`
- `forgery_analysis.json`
- `metadata.json` (request context, engine versions, timestamps)

**Phase 2 — Permanent Archive (after checker decision):**

| Decision | Path | Retention |
|---|---|---|
| APPROVE | `filenet://approved/{year}/{customer_id}/{request_id}/` | 7 years |
| REJECT | `filenet://rejected/{year}/{request_id}/` | 90 days, then auto-purge |

---

## Phase 5 — Confidence Scoring

The Confidence Scorer aggregates all signals into a single score and risk tier.

**Name Matching (Jaro-Winkler similarity):**

| Match Score | Outcome |
|---|---|
| > 0.95 | PASS |
| 0.85–0.95 | FLAG — possible OCR typo |
| < 0.85 | FAIL — significant mismatch |

**Confidence Score Card:**

| Signal | Weight | Example Score |
|---|---|---|
| Name Match (Old + New) | 40% | 100% |
| Document Authenticity | 30% | 87% |
| OCR Confidence | 15% | 92% |
| LLM Extraction Confidence | 15% | 94% |
| **Overall Weighted Score** | | **94.6%** |

**Risk Tier Classification:**

| Tier | Condition | Routing |
|---|---|---|
| 🟢 LOW | Score ≥ 90%, no flags | Standard checker queue |
| 🟡 MEDIUM | Score 70–90%, OR minor flags (e.g., `OCR_MEDIUM_CONF`) | Standard checker, concerns highlighted |
| 🔴 HIGH | Score < 70%, OR major flags (`FORGERY_FLAG`, `DOC_MISMATCH`) | Senior checker queue |

---

## Phase 6 — Summary Generation

The Summary Agent generates a concise 2–3 sentence brief for the human checker, including:

1. What was verified and how
2. Any flags or concerns
3. A clear AI recommendation: **APPROVE / REJECT / MANUAL_REVIEW**

**AI Recommendation Logic:**

| Recommendation | Conditions |
|---|---|
| APPROVE | Overall score ≥ 85%, name matches ≥ 95%, no HIGH severity flags, forgery = PASS |
| MANUAL_REVIEW | Score 60–85%, OR any MEDIUM severity flag, OR forgery = FLAG |
| REJECT | Score < 60%, OR name match < 70%, OR forgery = FAIL, OR doc type mismatch confirmed |

**Example summary (clean case):**
> "Marriage Certificate verified. Old name 'Priya Sharma' matches bride name field (100%). New name 'Priya Mehta' matches married name field (100%). Document authenticity check passed (87%). No forgery signals detected. **Recommendation: APPROVE**"

**Example flag messages:**

| Severity | Flag | Message |
|---|---|---|
| ⚠️ | `OCR_LOW_QUALITY` | Page 2 had 58% OCR confidence. Text may be inaccurate. Consider requesting clearer scan. |
| ⚠️ | `NAME_FUZZY_MATCH` | Old name matched at 89%. Extracted "Priya Sharna" vs expected "Priya Sharma". Possible OCR error. |
| 🚨 | `FORGERY_FLAG` | ELA analysis detected potential tampering in name region. Recommend manual document inspection. |
| 🚨 | `DOC_TYPE_MISMATCH` | Declared Marriage Certificate, but document appears to be a Utility Bill. REJECT or investigate. |

---

## Phase 7 — Staging

The processed request is written to the `pending_requests` table and the SLA clock starts.

**Key fields in the pending table:**

```
-- Identity
request_id          "REQ-12345"
idempotency_key     "hash..."
customer_id         "C001"
change_type         "LEGAL_NAME"
document_type       "MARRIAGE_CERTIFICATE"

-- Request Data
requested_old_value "Priya Sharma"
requested_new_value "Priya Mehta"

-- Scores
old_name_match      1.0000
new_name_match      1.0000
ocr_confidence      0.9200
doc_authenticity    0.8700
overall_score       0.9460
forgery_result      "PASS"

-- Routing
risk_tier           "LOW"
flags               []
ai_recommendation   "APPROVE"
ai_summary          "Marriage Certificate verified..."

-- Status
status              "AI_VERIFIED_PENDING_HUMAN"

-- Resubmit Tracking
resubmit_count      0
max_resubmits       3
original_request_id NULL
```

---

## Phase 8 — Human Checker Review

### Queue & Assignment

| Queue | Who uses it | Contents |
|---|---|---|
| Standard Checker Queue | All checkers | LOW and MEDIUM risk requests |
| Senior Checker Queue | Senior checkers only | HIGH risk requests |

**Claim Flow:**
1. Checker opens workbench → sees queue filtered by their role
2. Checker clicks "Claim Next" or picks a specific request
3. System sets `assigned_checker`, `checker_lock_until = NOW + 15 min`, status → `IN_REVIEW`
4. If checker abandons (lock expires): request is released, logged with `review_abandoned_by_{checker_id}`, and returned to the queue for a different checker

### Checker Workbench

The workbench shows:
- Request details (customer, change type, old/new name, doc type)
- Inline document viewer (with download original / view processed)
- Extracted fields with per-field confidence scores
- Visual confidence score card (progress bars)
- AI summary and recommendation
- Flags and alerts panel
- FileNet reference link

### Checker Actions

| Action | Notes |
|---|---|
| ✅ APPROVE | Triggers RPS update |
| ❌ REJECT | Reason field mandatory |
| ❓ MORE INFO | Notifies branch, customer can upload new document; resubmit counter checked |
| ⬆️ ESCALATE | Reason mandatory; routed to supervisor / senior queue |
| 🔄 RE-PROCESS | Re-queues the job with new OCR params (cloud OCR, manual hints, image rotation) |

---

## Phase 9 — Outcomes

### APPROVE
- RPS Update Microservice called (gated behind circuit breaker)
- Core banking record updated
- Status → `COMPLETED`
- FileNet: staging → `approved/` (7-year retention)

### REJECT
- Reason logged
- Branch notified
- FileNet: staging → `rejected/` (90-day retention, then auto-purge)

### MORE INFO
- Status → `PENDING_INFO`
- Branch notified
- Customer invited to re-upload document
- **Resubmit counter checked:** if `resubmit_count < max_resubmits (3)`, resubmission allowed; else auto-escalate

### ESCALATE
- Status → `ESCALATED`
- Routed to supervisor / senior queue
- Higher authority can APPROVE or REJECT with override

### RE-PROCESS
- Status → `REPROCESSING`
- Checker selects re-process options: force cloud OCR, manual OCR hints, rotate image
- Job re-queued → loops back to Phase 4

---

## Phase 10 — Immutable Audit Log

Every state transition generates an immutable audit record with tamper detection.

**Schema:**

```
audit_id            UUID PK
request_id          "REQ-12345"
event_type          STATE_CHANGE | HUMAN_ACTION | SYSTEM_EVENT | ERROR
previous_state      "IN_REVIEW"
new_state           "APPROVED"
actor_type          SYSTEM | HUMAN | AI_AGENT
actor_id            "checker_jane"
agent_name          "confidence_scorer" (or null)
agent_version       "1.2.3"
llm_model           "claude-3.5-sonnet-20240620"
action_details      { decision: "approve", ... }
record_snapshot     Full pending_table row at this moment
timestamp           "2024-03-20T11:15:32.456Z"
checksum            SHA-256 of record (tamper detection)
```

**Example audit trail for REQ-12345:**

| Time | Actor | Event | State |
|---|---|---|---|
| 10:30:00 | SYSTEM | Request created | → INTAKE |
| 10:30:02 | validation_agent | Validation passed | → VALIDATED |
| 10:30:03 | SYSTEM | Queued for processing | → QUEUED |
| 10:30:05 | doc_processor | Processing started | → PROCESSING |
| 10:30:45 | doc_processor | OCR completed | (no change) |
| 10:30:47 | confidence_scorer | Scoring done | (no change) |
| 10:30:48 | summary_agent | Summary generated | → AI_VERIFIED |
| 10:30:48 | SYSTEM | Staged for review | → PENDING_HUMAN |
| 11:10:00 | checker_jane | Claimed request | → IN_REVIEW |
| 11:15:32 | checker_jane | Approved | → APPROVED |
| 11:15:33 | rps_service | Core banking updated | → COMPLETED |

---

## Metrics & Observability

### Operational Metrics

**Throughput:**
- Requests per hour (by change type)
- Average processing time (queue → staged)
- Average review time (staged → decision)
- End-to-end latency (intake → completed)

**Quality:**
- OCR confidence distribution (histogram)
- Extraction success rate
- Forgery detection rate (PASS / FLAG / FAIL breakdown)

### AI Performance Metrics

Track AI recommendation accuracy against human decisions using a confusion matrix:

|  | Human: Approved | Human: Rejected |
|---|---|---|
| **AI: APPROVE** | TP (correct) | FP (AI too lenient) |
| **AI: REJECT** | FN (AI too strict) | TN (correct) |

**Key derived metrics:**
- Override rate = (FP + FN) / Total
- False positive rate = FP / (TP + FP) — AI approved, human rejected
- False negative rate = FN / (FN + TN) — AI rejected, human approved

**Alert thresholds:**
- FP rate > 5%: AI is approving too many bad requests → tighten scoring thresholds
- FN rate > 10%: AI is too conservative, slowing throughput → loosen thresholds
- Override rate > 15%: Model likely needs retraining

### Per-Agent Structured Logging

All agents emit JSON logs (ELK / Datadog compatible) with no PII in log payloads:

```json
{
  "timestamp": "2024-03-20T10:30:45.123Z",
  "request_id": "REQ-12345",
  "agent": "doc_processor",
  "step": "ocr_extraction",
  "duration_ms": 2340,
  "status": "success",
  "ocr_confidence": 0.92,
  "pages_processed": 1,
  "llm_tokens": { "input": 1250, "output": 180 },
  "llm_latency_ms": 890
}
```

---

## Forgery Detection — Deep Dive

> This section expands on Step 4.4 with practical implementation guidance, recommended libraries, and additional techniques worth considering.

### Current Four-Layer Model

#### Layer 1: Metadata Analysis (Weight: 20%)

**What to check:**
- PDF `CreationDate` vs `ModDate` — a certificate created in 2020 but modified yesterday is suspicious
- PDF producer field — `Photoshop` or `Canva` as producer is a red flag for government documents; `Adobe Acrobat Scan` or government software is expected
- EXIF data for images — GPS coordinates, device model, timestamp consistency
- Resolution consistency — if page 1 is 150 DPI and page 2 is 300 DPI, the doc was assembled from different sources

**Recommended library:** `PyMuPDF` (fitz) for PDF metadata; `Pillow` / `exifread` for image EXIF

**Practical note:** Metadata is easily stripped or spoofed, so this layer carries only 20% weight. Treat it as a signal, not a verdict.

---

#### Layer 2: Error Level Analysis — ELA (Weight: 30%)

**How it works:**
1. Re-save the image at a known compression level (e.g., JPEG quality 90)
2. Compute the pixel-level difference between the re-saved and original
3. Authentic regions that were already compressed will show low error; edited/pasted regions that were compressed at a different level will show high error

**What to look for:** Bright spots in the ELA heatmap concentrated around name fields, dates, or stamps are the highest-risk signal.

**Recommended library:** `Pillow` for re-saving; `numpy` for difference computation; `opencv-python` for heatmap visualization

**Limitation:** ELA is less reliable on already low-quality or heavily compressed source images. Weight down this layer's contribution when OCR confidence was already flagged as low.

**Practical addition — Copy-Move Detection:** Alongside ELA, run a block-matching algorithm to detect if a region of the document was duplicated (e.g., a seal copied from another document). This is a common forgery technique not caught by ELA alone.

---

#### Layer 3: Font Consistency Analysis (Weight: 20%)

**What to check:**
- Extract font names used throughout the document (`PyMuPDF` can enumerate fonts per text span)
- Flag if name fields or date fields use a font not present in the rest of the document
- Check character spacing (kerning) — hand-typed text over an original has subtly different baseline and inter-character spacing
- For scanned documents, compare stroke width and pixel density of name text vs surrounding body text

**Recommended library:** `PyMuPDF` for digital PDFs; for scanned docs, compare bounding-box-level texture features using `opencv`

**Practical note:** This layer is highly effective for digital PDFs where metadata is available per text span. For scanned image documents, font analysis degrades to texture comparison and is less reliable — adjust weight accordingly.

---

#### Layer 4: ML Model (Weight: 30%)

**Options (in order of recommendation):**

**Option A — Fine-tuned Vision Model (best long-term)**
- Fine-tune a vision model (e.g., EfficientNet or ViT) on a labeled dataset of authentic vs forged documents
- Your institution builds this dataset over time from confirmed forgery cases in the audit log
- Highest accuracy; requires ongoing training infrastructure

**Option B — Pre-trained Document Forgery APIs**
- Services like **Microsoft Azure AI Document Intelligence** or **AWS Textract** offer some authenticity signals
- Easier to start with; less control over model behavior

**Option C — Template Matching (good interim approach)**
- Maintain a library of known-good government document templates (fonts, layouts, seal positions, watermark patterns)
- Compare uploaded document structure against templates using feature matching (`opencv` ORB/SIFT)
- Flag documents that don't match any known template as `UNKNOWN_TEMPLATE` rather than `FORGED`
- This is practical to implement now while a trained model is being built

**Recommended starter approach:** Begin with Option C (template matching) + Options A/B as the ML signal. Gradually replace with a fine-tuned model as labeled training data accumulates from the audit log.

---

### Additional Detection Techniques to Consider

These are not in the current four-layer model but are worth adding, especially as volume grows:

**Seal / Stamp Verification**
- Government certificates carry official seals. Train a small object detection model to locate the seal region, then verify its shape, color profile, and texture against known authentic seals.
- A missing seal, a pixelated seal, or a seal whose edge feathering looks digitally composed are strong forgery signals.

**Watermark Verification**
- Many marriage certificates and gazette notifications embed security watermarks (visible or UV-visible). In scanned documents, frequency-domain analysis (FFT) can detect whether a watermark pattern is present or has been disrupted by editing.

**Cross-field Logical Consistency**
- This is an LLM-friendly check: ask the LLM whether the extracted fields are internally consistent.
    - Does the marriage date precede the certificate issue date?
    - Does the issuing authority match the region implied by the address?
    - Is the certificate number format consistent with the declared issuing authority?
- Flag inconsistencies as `LOGICAL_INCONSISTENCY`. This catches fabricated documents even when visual forgery detection passes.

**External Verification (Future)**
- For high-risk cases, integrate with government APIs where available (e.g., marriage certificate verification via the registrar's API) to cryptographically confirm a certificate number exists in the source registry. This converts a probabilistic check into a definitive one.

---

### Forgery Score Calibration

As real-world data accumulates from the audit log (where checker decisions serve as ground truth), the four layer weights and the 0.60 / 0.85 thresholds should be recalibrated periodically:

1. Extract all cases where `forgery_result = FLAG` and map to checker decisions (approved or rejected)
2. Run a logistic regression or threshold grid-search to find the weights and cutoffs that maximize precision on forgery detection while minimizing false positive rate
3. Target: < 2% false positive rate (authentic docs flagged as forged) and > 90% recall on confirmed forgeries
4. Recalibrate quarterly or after any significant volume increase

---

