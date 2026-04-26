# Intelligent Account Servicing Workflow (IASW)

An AI-powered document verification system for automating bank account change requests with human-in-the-loop oversight.

---

## Executive Summary

### What is IASW?

IASW is a full-stack application that helps banks process customer account change requests (like legal name changes after marriage). Instead of manual document review, IASW uses AI to:

1. **Extract text** from uploaded documents using OCR
2. **Verify document type** matches what the customer declared
3. **Extract key fields** (names, dates) from the document
4. **Detect potential forgery** using multi-layer analysis
5. **Calculate confidence scores** to assess request reliability
6. **Route to human checkers** for final approval/rejection

**The core principle: AI assists, humans decide.** No account changes happen without explicit human approval.

### Who Uses It?

- **Bank Staff:** Submit change requests on behalf of customers, upload supporting documents
- **Checkers:** Review AI-analyzed requests, make approve/reject decisions
- **Admins:** Monitor system, view database records

### Key Features

- Real-time processing step updates in the UI
- Risk-based routing (HIGH risk → senior checkers)
- Complete audit trail with tamper detection
- JWT-authenticated checker endpoints
- Supervisor-worker AI architecture using LangGraph

---

## Working Demo Flow

This walkthrough demonstrates a complete Legal Name Change request from submission to approval.

### Demo Scenario: Customer C001 (Priya Sharma → Priya Mehta)

**Background:** Priya Sharma recently got married and wants to change her legal name on her bank account to Priya Mehta. She brings her Marriage Certificate to the bank branch.

### Step 1: Staff Submits Request

Bank staff logs into the **Staff Portal** and fills out the intake form:

| Field | Value |
|-------|-------|
| Account Number | 1234567890 |
| Change Type | Legal Name |
| Document Type | Marriage Certificate |
| Current Name | Priya Sharma |
| New Name | Priya Mehta |

Staff uploads the Marriage Certificate PDF.

**System Response:** 
- Request ID `REQ-12345` created
- Status: `VALIDATED`
- Staff sees: "Request created successfully. Document processing will begin shortly."

### Step 2: AI Processing Pipeline

The document enters the async processing queue. Staff can track progress in real-time:

```
[✓] Validating Document
[✓] Extracting Metadata
[✓] Running OCR
[✓] Classifying Document
[✓] Extracting Fields
[✓] Detecting Forgery
[✓] Calculating Scores
[✓] Generating Summary
[✓] AI Verification Complete
```

**Behind the scenes:**
1. **Metadata Agent** extracts PDF creation date, checks for editing software signatures
2. **OCR Agent** runs Tesseract, achieves 92% confidence
3. **Classifier Agent** confirms document is a Marriage Certificate (93% confidence)
4. **Extractor Agent** finds:
   - Bride Name: "Priya Sharma" (97% confidence)
   - Married Name: "Priya Mehta" (94% confidence)
   - Marriage Date: "2024-03-15"
5. **Forgery Agent** runs ELA analysis, font checks → PASS (87% score)
6. **Scorer Agent** calculates:
   - Old name match: 100%
   - New name match: 100%
   - Overall confidence: 94.6%
   - Risk Tier: LOW
7. **Summary Agent** generates:

> "Marriage Certificate verified. Old name 'Priya Sharma' matches bride name field (100%). New name 'Priya Mehta' matches married name field (100%). Document authenticity check passed (87%). No forgery signals detected. **Recommendation: APPROVE**"

**Status:** `AI_VERIFIED_PENDING_HUMAN`

### Step 3: Checker Reviews Request

A checker logs into the **Checker Workbench** and sees the request in the queue.

**Queue View:**
| Request ID | Customer | Change Type | Risk | AI Recommendation | Score |
|------------|----------|-------------|------|-------------------|-------|
| REQ-12345  | C001     | LEGAL_NAME  | LOW  |      APPROVE      | 94.6% |

Checker clicks "Claim" → Request locked for 15 minutes.

**Review Screen shows:**
- Document preview (original PDF)
- Extracted fields with confidence bars
- AI summary and recommendation
- Forgery detection results
- Flag alerts (none in this case)

### Step 4: Checker Approves

Checker reviews the AI analysis, confirms the document looks legitimate, and clicks **APPROVE**.

**System Response:**
- Status: `APPROVED` → `COMPLETED`
- Core banking (RPS) updated with new name
- Audit log entry created
- Document moved to permanent archive (7-year retention)

For detailed architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md).
For implementation details, see [LLD.md](./LLD.md).

---

## Confidence Scoring

The system calculates an overall confidence score using weighted signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| Name Match | 40% | Jaro-Winkler similarity between extracted and requested names |
| Document Authenticity | 30% | Forgery detection score |
| OCR Confidence | 15% | Quality of text extraction |
| Extraction Confidence | 15% | LLM extraction reliability |

### Risk Tier Classification

| Tier | Condition | Routing |
|------|-----------|---------|
| LOW | Score ≥ 90%, no flags | Standard queue |
| MEDIUM | Score 70-90% | Standard queue (highlighted) |
| HIGH | Score < 70% OR critical flags | Senior checker queue |

---

## AI Recommendation Logic

| Recommendation | When Applied |
|----------------|--------------|
| **APPROVE** | Score ≥ 85%, name match ≥ 95%, no HIGH flags, forgery = PASS |
| **MANUAL_REVIEW** | Score 60-85%, OR any MEDIUM flag, OR forgery = FLAG |
| **REJECT** | Score < 60%, OR name match < 70%, OR forgery = FAIL |

---

## Assumptions

1. **Document Quality:** Uploaded documents are reasonably legible (>60% OCR confidence expected)
2. **Single Page Documents:** Optimized for single-page certificates
3. **English Language:** OCR and extraction tuned for English-language documents
4. **Network Availability:** Requires stable connection to Claude API
5. **Browser Support:** Modern browsers (Chrome, Firefox, Safari, Edge)

## Limitations

1. **Processing Time:** AI processing takes 30s-2min, not instant
2. **No Offline Mode:** Requires network connectivity
3. **Web Only:** No mobile app
4. **Limited Document Types:** Marriage Certificate, Gazette, Deed Poll, Court Order
5. **Mock Integrations:** RPS (core banking) and FileNet are simulated
6. **No External Verification:** No government database integration

---

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, agent design, HITL design, data model, tech stack justification |
| [LLD.md](./LLD.md) | Detailed code structure, API contracts, component specifications |

---

## Technology Stack & Justification

### Stack Overview

| Component | Technology | Why This Choice |
|-----------|------------|-----------------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS | Server-side rendering for fast initial load; TypeScript for type safety; Tailwind for rapid UI development; file-based routing suits two-UI structure (Staff + Checker) |
| **Backend API** | FastAPI, Python 3.11+ | Native async/await for non-blocking I/O; Python has best ML/AI library support; Pydantic auto-validation; auto-generated OpenAPI docs |
| **AI Orchestration** | LangGraph | Graph-based workflow fits pipeline perfectly; conditional routing based on confidence; state management across nodes; checkpointing for resumable workflows |
| **LLM** | Claude 3.5 Sonnet (Anthropic) | Excellent structured data extraction from documents; lower cost than GPT-4; strong reasoning for forgery analysis; consistent JSON output |
| **OCR** | Tesseract 5 + Google Vision (fallback) | Tesseract is free and runs locally; Google Vision as fallback for poor quality scans; complementary strengths |
| **Task Queue** | Celery + Redis | Simple setup; reliable with retry logic; good monitoring via Flower; handles async/sync boundaries cleanly |
| **Database** | PostgreSQL + SQLAlchemy | JSONB for flexible metadata storage; robust ACID compliance; excellent for audit trails with tamper detection |
| **Authentication** | JWT tokens | Stateless auth for scalability; role-based access (staff vs checker); industry standard |
| **Document Storage** | Local filesystem (S3-ready) | Simple for development; production-ready with S3 swap; standard interface for both |

---

### Key Design Decisions

#### 1. **Why Next.js over React SPA?**

**Chosen:** Next.js 14 with App Router

**Reasons:**
- Server-side rendering (SSR) provides faster initial page load
- API routes allow Backend-for-Frontend (BFF) pattern
- File-based routing naturally separates Staff Portal and Checker Workbench
- Built-in optimization for images, fonts, and code splitting
- TypeScript integration out of the box

**Alternatives Considered:**
- **Plain React:** No SSR, slower initial load, manual routing setup
- **Vite + React:** Fast development but no SSR or API routes
- **Remix:** Similar to Next.js but smaller ecosystem

---

#### 2. **Why FastAPI over Flask/Django?**

**Chosen:** FastAPI

**Reasons:**
- **Native async/await:** Non-blocking I/O critical for handling multiple document uploads
- **Automatic validation:** Pydantic models validate requests automatically (400 errors with clear messages)
- **Auto-generated docs:** OpenAPI/Swagger UI at `/docs` for free
- **Performance:** One of the fastest Python frameworks (comparable to Node.js)
- **Type hints:** Better IDE support and fewer runtime errors

**Alternatives Considered:**
- **Flask:** Synchronous by default, manual validation, no auto-docs
- **Django REST Framework:** Heavy for API-only backend, slower, more boilerplate
- **Express.js (Node):** Good, but Python has better ML/AI library ecosystem


---

#### 3. **Why LangGraph over alternatives?**

**Chosen:** LangGraph (by LangChain)

**Reasons:**
- **Graph structure:** Perfect fit for our pipeline with conditional routing (OCR → fallback OCR if low confidence)
- **State management:** Shared state flows through nodes, accumulating results
- **Conditional edges:** Route based on intermediate results (skip forgery if doc type mismatch)
- **Visualization:** Can generate visual graph for debugging
- **Streaming support:** Real-time step updates to UI

**Alternatives Considered:**
- **Plain LangChain:** No graph structure, harder to implement conditional routing
- **CrewAI:** Better for autonomous multi-agent collaboration, not sequential pipelines
- **Custom orchestration:** Would need to rebuild graph logic, state management, error handling

---

#### 4. **Why Claude 3.5 Sonnet over GPT-4?**

**Chosen:** Claude 3.5 Sonnet (Anthropic)

**Reasons:**
- **Better structured extraction:** Excels at extracting fields from semi-structured documents
- **Lower cost:** ~60% cheaper than GPT-4 for equivalent quality
- **Consistent JSON output:** Less prompt engineering needed for reliable JSON
- **Strong reasoning:** Good at interpreting forgery signals and explaining confidence
- **Context window:** 200K tokens handles large documents


**Use Cases in IASW:**
- Classifier Agent: Determine document type from OCR text
- Extractor Agent: Extract names, dates from marriage certificates
- Summary Agent: Generate human-readable recommendations

---

#### 5. **Why Celery for background tasks?**

**Chosen:** Celery + Redis

**Reasons:**
- **Async/Sync bridge:** Celery workers are sync, LangGraph is async → we handle this cleanly
- **Retry logic:** Built-in exponential backoff (3 retries for failed tasks)
- **Monitoring:** Flower dashboard for task tracking
- **Reliability:** Tasks persist in Redis, survive worker restarts
- **Dead letter queue:** Unrecoverable failures go to DLQ for investigation

**Alternatives Considered:**
- **FastAPI BackgroundTasks:** No persistence, tasks lost on restart, no retries
- **RQ (Redis Queue):** Simpler but fewer features, no Celery Flower
- **ARQ:** Native async but less mature, smaller ecosystem

---

#### 6. **Why PostgreSQL over MongoDB/MySQL?**

**Chosen:** PostgreSQL

**Reasons:**
- **JSONB columns:** Store flexible metadata (forgery details, extracted fields) without schema changes
- **ACID compliance:** Critical for audit trail integrity
- **Full-text search:** Can search OCR text if needed
- **Strong consistency:** Ensures checker locks work correctly (15-min lock timeout)
- **Excellent Python support:** SQLAlchemy ORM + async drivers

**Alternatives Considered:**
- **MySQL:** Good but JSONB support not as mature as PostgreSQL
- **SQLite:** Too simple for production, no concurrent writes

---

#### 7. **Why Tesseract + Google Vision (not just one)?**

**Chosen:** Dual OCR strategy

**Reasons:**
- **Tesseract (primary):** Free, runs locally, no API costs, good for clean documents
- **Google Vision (fallback):** Cloud-based, better for poor quality scans, only used when Tesseract < 60% confidence
- **Cost optimization:** Use free Tesseract for ~80% of cases, pay for Vision only when needed

---

### Architecture Principles

#### 1. **Async/Sync Boundaries**

| Operation | Mode | Why |
|-----------|------|-----|
| Request validation | Sync | Staff need immediate feedback (<500ms) |
| Document processing | Async | Heavy AI work (30-60s), don't block API |
| Checker review | Sync | Human interaction is inherently synchronous |
| RPS update | Sync | Transaction safety, need immediate confirmation |

#### 2. **Human-in-the-Loop Enforcement**

**Principle:** AI can analyze, but only humans can approve/reject.

**Enforced via:**
1. **State machine:** APPROVED/REJECTED only reachable from IN_REVIEW (human-claimed)
2. **JWT auth:** Checker endpoints require `checker` role
3. **Actor validation:** RPS update checks `actor_type = HUMAN`
4. **Audit trail:** Every action logs actor type (SYSTEM/HUMAN/AI_AGENT)

#### 3. **Modularity via Supervisor-Worker Pattern**

**Why:** Each agent (OCR, Classifier, Extractor, Forgery, Scorer) is independent:
- Can be tested separately
- Can be improved without affecting others
- Can be replaced (swap Tesseract for AWS Textract)
- Clear logging boundaries

---

### Trade-offs Made

| Decision | Benefit | Cost |
|----------|---------|------|
| **Always require human review** | Regulatory compliance, trust | Higher operational cost, slower throughput |
| **Single LLM (Claude) for all tasks** | Simpler deployment, consistent quality | Higher per-request cost, vendor lock-in |
| **Sync validation + Async processing** | Fast feedback, non-blocking | Two-phase UX requires status polling |
| **HIGH risk first in queue** | Faster fraud detection | LOW risk cases wait longer |
| **Supervisor-worker architecture** | Modularity, fault isolation | More complexity than simple pipeline |

---

### Scalability Considerations

**Current Setup (MVP):**
- Single Celery worker
- Single PostgreSQL instance
- Local file storage

**Production Scaling Path:**
1. **Horizontal scaling:**
   - Multiple Celery workers behind Redis
   - PostgreSQL read replicas for checker queue queries
   - S3 for document storage (multi-region)

2. **Caching:**
   - Redis cache for frequently accessed requests
   - CDN for static assets (Next.js)

3. **Load balancing:**
   - Multiple FastAPI instances behind nginx/ALB
   - Connection pooling for PostgreSQL

4. **Monitoring:**
   - LangSmith for LLM call tracking
   - Prometheus + Grafana for metrics
   - Sentry for error tracking

---

For detailed architecture diagrams and agent design, see [ARCHITECTURE.md](./ARCHITECTURE.md).
