# Intelligent Account Servicing Workflow (IASW)
## Low-Level Design Document

This document provides detailed implementation specifications including project structure, code components, API contracts, and configuration.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Backend Components](#2-backend-components)
3. [Frontend Components](#3-frontend-components)
4. [LangGraph Pipeline](#4-langgraph-pipeline)
5. [API Contracts](#5-api-contracts)
6. [Database Schema](#6-database-schema)
7. [Configuration](#7-configuration)
8. [Error Handling](#8-error-handling)

---

## 1. Project Structure

```
iasw/
├── frontend/                     # Next.js 14 Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx              # Home portal
│   │   │   ├── login/
│   │   │   │   └── page.tsx          # Sign in / Sign up
│   │   │   ├── staff/                # Staff Portal
│   │   │   │   ├── page.tsx          # Dashboard
│   │   │   │   ├── layout.tsx
│   │   │   │   └── requests/
│   │   │   │       ├── page.tsx      # Request list
│   │   │   │       ├── new/
│   │   │   │       │   └── page.tsx  # New request form
│   │   │   │       └── [id]/
│   │   │   │           └── page.tsx  # Request details
│   │   │   ├── checker/              # Checker Workbench
│   │   │   │   ├── page.tsx          # Dashboard
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── queue/
│   │   │   │   │   └── page.tsx      # Review queue
│   │   │   │   ├── reviews/
│   │   │   │   │   └── page.tsx      # Review history
│   │   │   │   └── review/
│   │   │   │       └── [requestId]/
│   │   │   │           └── page.tsx  # Review screen
│   │   │   └── admin/
│   │   │       └── page.tsx          # Database viewer
│   │   ├── components/
│   │   │   ├── ui/                   # Shared UI components
│   │   │   ├── staff/                # Staff-specific
│   │   │   └── checker/              # Checker-specific
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   └── useApi.ts
│   │   ├── lib/
│   │   │   ├── api.ts                # API client
│   │   │   └── auth.ts               # Auth utilities
│   │   └── types/
│   │       └── index.ts
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── backend/                      # FastAPI Application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI entry point
│   │   ├── config.py             # Configuration settings
│   │   ├── dependencies.py       # Dependency injection
│   │   ├── logging_config.py     # Structured logging setup
│   │   ├── metrics.py            # Prometheus metrics
│   │   │
│   │   ├── api/                  # API Layer
│   │   │   ├── v1/
│   │   │   │   ├── router.py     # Main router
│   │   │   │   ├── requests.py   # Request endpoints
│   │   │   │   ├── checker.py    # Checker endpoints (JWT protected)
│   │   │   │   ├── admin.py      # Admin endpoints
│   │   │   │   └── health.py     # Health check
│   │   │   └── middleware/
│   │   │       ├── auth.py       # JWT authentication
│   │   │       └── error_handler.py
│   │   │
│   │   ├── models/               # SQLAlchemy Models
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── request.py        # Request model
│   │   │   ├── audit.py          # AuditLog model
│   │   │   ├── customer.py       # Customer (RPS mock)
│   │   │   └── enums.py          # Status, Risk, Decision enums
│   │   │
│   │   ├── schemas/              # Pydantic Schemas
│   │   │   ├── request.py
│   │   │   ├── checker.py
│   │   │   └── auth.py
│   │   │
│   │   ├── services/             # Business Logic
│   │   │   ├── request_service.py
│   │   │   ├── checker_service.py
│   │   │   └── auth_service.py   # JWT token handling
│   │   │
│   │   ├── agents/               # LangGraph Pipeline
│   │   │   ├── graph.py          # Main pipeline definition
│   │   │   ├── state.py          # ProcessingState schema
│   │   │   ├── nodes/            # Pipeline nodes
│   │   │   │   ├── validation.py
│   │   │   │   ├── metadata.py   # Metadata extraction
│   │   │   │   ├── ocr.py
│   │   │   │   ├── classifier.py
│   │   │   │   ├── extractor.py
│   │   │   │   ├── forgery.py
│   │   │   │   ├── scorer.py
│   │   │   │   └── summary.py
│   │   │   ├── specialized/      # Supervisor-worker agents
│   │   │   │   ├── supervisor.py # Orchestrator with step tracking
│   │   │   │   ├── forgery_tools.py
│   │   │   │   ├── ocr_tools.py
│   │   │   │   └── workers/
│   │   │   ├── prompts/          # Centralized prompts
│   │   │   │   ├── agent_prompts.py
│   │   │   │   └── node_prompts.py
│   │   │   └── tools/
│   │   │       ├── ocr_tool.py
│   │   │       ├── name_matcher.py
│   │   │       └── forgery_tools.py
│   │   │
│   │   ├── workers/              # Celery Tasks
│   │   │   ├── celery_app.py
│   │   │   └── tasks.py          # process_document task
│   │   │
│   │   └── db/
│   │       └── session.py
│   │
│   ├── storage/                  # Document uploads
│   │   └── documents/
│   ├── tests/
│   ├── requirements.txt
│   ├── seed_db.py                # Database seeding script
│   └── edit_db.py                # Database edit utility for testing
│
├── ARCHITECTURE.md
├── LLD.md
└── Readme.md
```

---

## 2. Backend Components

### 2.1 Models (`app/models/`)

#### Request Model (`request.py`)

```python
class Request(Base):
    """
    Core entity representing a change request.
    
    Key Fields:
        request_id: Primary key (format: "REQ-XXXXX")
        customer_id: Reference to customer
        status: Current workflow state (RequestStatus enum)
        current_processing_step: Real-time step tracking for UI
        
    Confidence Scores:
        ocr_confidence: OCR quality (0.0-1.0)
        extraction_confidence: LLM extraction quality
        old_name_match_score: Similarity for current name
        new_name_match_score: Similarity for new name
        overall_confidence: Weighted aggregate
        
    Forgery Detection:
        forgery_score: Authenticity score (0.0-1.0)
        forgery_result: PASS/FLAG/FAIL enum
        forgery_details: JSON with per-layer breakdown
        
    Workflow:
        assigned_checker: Checker who claimed (null if unclaimed)
        checker_lock_until: Lock expiry timestamp
        checker_decision: Final decision enum
        checker_decision_reason: Required for REJECT
    """
    __tablename__ = "requests"
```

#### Audit Log Model (`audit.py`)

```python
class AuditLog(Base):
    """
    Immutable audit record with tamper detection.
    
    Fields:
        event_type: STATE_CHANGE, HUMAN_ACTION, SYSTEM_EVENT, ERROR
        actor_type: SYSTEM, HUMAN, AI_AGENT
        actor_id: Identifier of who performed action
        agent_name: AI agent name (if applicable)
        llm_model: LLM model used
        previous_state: State before transition
        new_state: State after transition
        action_details: JSON with context
        record_snapshot: Full request state at this moment
        checksum: SHA-256 for tamper detection
    """
    __tablename__ = "audit_logs"
```

#### Enums (`enums.py`)

```python
class RequestStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    AI_VERIFIED_PENDING_HUMAN = "AI_VERIFIED_PENDING_HUMAN"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ForgeryResult(str, Enum):
    PASS = "PASS"
    FLAG = "FLAG"
    FAIL = "FAIL"

class Recommendation(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MANUAL_REVIEW = "MANUAL_REVIEW"

class Decision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MORE_INFO = "MORE_INFO"
    ESCALATE = "ESCALATE"
```

### 2.2 Schemas (`app/schemas/`)

#### Request Schemas (`request.py`)

```python
class CreateRequestSchema(BaseModel):
    """Input schema for creating a new request."""
    account_number: str = Field(..., min_length=1, max_length=20)
    change_type: ChangeType
    document_type: DocumentType
    current_value: str = Field(..., min_length=1, max_length=255)
    new_value: str = Field(..., min_length=1, max_length=255)
    
    @field_validator("new_value")
    def new_value_different(cls, v, info):
        """Ensure new value is different from current value."""
        if "current_value" in info.data and v == info.data["current_value"]:
            raise ValueError("New value must be different from current value")
        return v

class RequestResponse(BaseModel):
    """Response after creating a request."""
    request_id: str
    status: RequestStatus
    message: str
    customer_name: Optional[str] = None

class RequestDetail(BaseModel):
    """Full request details for viewing."""
    request_id: str
    customer_id: str
    change_type: ChangeType
    document_type: DocumentType
    status: RequestStatus
    
    # Requested vs Extracted values
    requested_old_value: str
    requested_new_value: str
    extracted_old_value: Optional[str] = None
    extracted_new_value: Optional[str] = None
    extraction_details: List[ExtractionDetail] = []
    
    # Confidence breakdown
    confidence: Optional[ConfidenceBreakdown] = None
    
    # Forgery detection
    forgery: Optional[ForgeryDetail] = None
    
    # Risk and routing
    risk_tier: Optional[RiskTier] = None
    flags: List[str] = []
    ai_recommendation: Optional[Recommendation] = None
    ai_summary: Optional[str] = None
    
    # Workflow
    current_processing_step: Optional[str] = None
    assigned_checker: Optional[str] = None
    checker_decision: Optional[Decision] = None
    
    # Computed fields
    is_locked: bool = False
    can_be_claimed: bool = False
    time_in_current_status_minutes: Optional[int] = None

class ExtractionDetail(BaseModel):
    """Details of a single extracted field."""
    field_name: str
    value: Optional[str] = None  # Nullable for failed extractions
    confidence: float
    source_snippet: Optional[str] = None
```

#### Checker Schemas (`checker.py`)

```python
class ClaimRequest(BaseModel):
    """Request to claim a request for review."""
    checker_id: str

class DecisionRequest(BaseModel):
    """Request to submit a decision."""
    decision: Decision
    reason: Optional[str] = None
    
    @field_validator("reason")
    def reason_required_for_reject(cls, v, info):
        """Reason is required for REJECT and ESCALATE."""
        if info.data.get("decision") in [Decision.REJECT, Decision.ESCALATE]:
            if not v or not v.strip():
                raise ValueError("Reason is required for reject/escalate")
        return v

class QueueItem(BaseModel):
    """Item in the checker queue."""
    request_id: str
    customer_id: str
    change_type: ChangeType
    risk_tier: Optional[RiskTier] = None
    ai_recommendation: Optional[Recommendation] = None
    overall_confidence: Optional[float] = None
    flags: List[str] = []
    created_at: datetime
    time_in_queue_minutes: int
```

### 2.3 API Routes (`app/api/v1/`)

#### Requests API (`requests.py`)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/requests` | Create new request | None |
| GET | `/api/v1/requests` | List requests (with filters) | None |
| GET | `/api/v1/requests/{id}` | Get request details | None |
| POST | `/api/v1/requests/{id}/upload` | Upload document | None |
| GET | `/api/v1/requests/{id}/document` | Get uploaded document (inline or download) | None |

#### Checker API (`checker.py`) — JWT Protected

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/checker/queue` | Get pending requests | JWT |
| POST | `/api/v1/checker/claim/{id}` | Claim request for review | JWT |
| POST | `/api/v1/checker/release/{id}` | Release claimed request | JWT |
| POST | `/api/v1/checker/decide/{id}` | Submit decision | JWT |
| GET | `/api/v1/checker/reviews` | Get checker's review history | JWT |

**JWT Authentication:**
```python
# Checker endpoints require valid JWT token
@router.post("/claim/{request_id}")
async def claim_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)  # JWT validation
):
    checker_id = current_user["username"]
    # ... claim logic
```

### 2.4 Celery Tasks (`app/workers/tasks.py`)

```python
@celery_app.task(bind=True, base=ProcessDocumentTask)
def process_document(self, request_id: str) -> Dict[str, Any]:
    """
    Process document through LangGraph pipeline.
    
    Flow:
        1. Load request from database
        2. Update status to PROCESSING
        3. Run LangGraph pipeline with step callback
        4. Save results to database
        5. Update status to AI_VERIFIED_PENDING_HUMAN
    
    Step Tracking:
        The on_step_change callback persists each step to the database,
        allowing the UI to show real-time progress.
    
    Async/Sync Handling:
        Uses run_async() wrapper to properly handle event loops
        in Celery's synchronous context.
    """
    
    # Run pipeline with step tracking callback
    final_state = run_async(
        pipeline.process(
            request_id=request.request_id,
            customer_id=request.customer_id,
            change_type=request.change_type.value,
            document_type=request.document_type.value,
            requested_old_value=request.requested_old_value,
            requested_new_value=request.requested_new_value,
            document_path=document_path,
            on_step_change=update_processing_step,  # Real-time step updates
        )
    )
```

**Event Loop Handling:**

```python
def run_async(coro):
    """
    Safely run async coroutine from synchronous Celery task.
    
    Handles event loop management to avoid conflicts with
    existing loops that might be running in Celery workers.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, use thread
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
```

---

## 3. Frontend Components

### 3.1 Page Structure

| Page | Path | Purpose |
|------|------|---------|
| Home | `/` | Portal selection (Staff/Checker/Admin) |
| Login | `/login` | Sign in / Sign up tabs |
| Staff Dashboard | `/staff` | Stats + recent requests |
| Staff Requests | `/staff/requests` | Request list with filters |
| New Request | `/staff/requests/new` | Create request form |
| Request Detail | `/staff/requests/[id]` | View request + processing status |
| Checker Dashboard | `/checker` | Queue stats + quick actions |
| Checker Queue | `/checker/queue` | Pending requests to review |
| Review Screen | `/checker/review/[requestId]` | Document + AI analysis + decision |
| Admin | `/admin` | Database viewer |

### 3.2 Key Components

#### Processing Status Display

Shows real-time processing step with spinner animation:

```typescript
// Request detail page shows processing steps
const PROCESSING_STEPS = [
  { key: 'validating', label: 'Validating Document' },
  { key: 'metadata', label: 'Extracting Metadata' },
  { key: 'ocr', label: 'Running OCR' },
  { key: 'classifying', label: 'Classifying Document' },
  { key: 'extracting', label: 'Extracting Fields' },
  { key: 'forgery', label: 'Detecting Forgery' },
  { key: 'scoring', label: 'Calculating Scores' },
  { key: 'summary', label: 'Generating Summary' },
  { key: 'complete', label: 'AI Verification Complete' },
];
```

#### Document Preview Component (Checker Workbench)

Interactive document viewer with zoom controls:

```typescript
// Document preview with zoom controls (25%-200%)
<DocumentViewer 
  documentUrl={reviewData.document_url}
  zoom={documentZoom}
  onZoomChange={setDocumentZoom}
/>

// Features:
// - Zoom in/out buttons (25% increments)
// - Reset to 100% button
// - Scrollable container (max-height: 600px)
// - Quick reference panel showing old/new names to verify
// - Inline display (not download)
```

#### Confidence Score Card

Visual display of confidence scores with progress bars:

```typescript
interface ConfidenceBreakdown {
  old_name_match: number;  // 0.0 - 1.0
  new_name_match: number;
  ocr_confidence: number;
  extraction_confidence: number;
  doc_authenticity: number;
  overall: number;
}
```

Color coding:
- Green: ≥ 90%
- Yellow: 70-89%
- Red: < 70%

#### Decision Buttons (Checker)

```typescript
// Actions available to checker
type CheckerAction = 'APPROVE' | 'REJECT' | 'MORE_INFO' | 'ESCALATE';

// APPROVE: immediate action
// REJECT/MORE_INFO/ESCALATE: opens modal for required reason
```

---

## 4. LangGraph Pipeline

### 4.1 Pipeline Architecture

Two modes available (configured via `USE_SUPERVISOR_AGENTS` setting):

1. **Linear Pipeline** (`graph.py`): Sequential nodes with conditional routing
2. **Supervisor-Agent** (`specialized/supervisor.py`): Supervisor orchestrates worker agents

### 4.2 Processing State Schema

```python
class ProcessingState(TypedDict):
    """State that flows through the LangGraph pipeline."""
    
    # Input
    request_id: str
    customer_id: str
    change_type: str
    document_type: str
    requested_old_value: str
    requested_new_value: str
    document_path: str
    
    # Metadata Output (NEW)
    metadata: Dict[str, Any]
    metadata_anomalies: List[str]
    
    # OCR Output
    ocr_text: str
    ocr_confidence: float
    ocr_method: str  # "tesseract" or "google_vision"
    
    # Classification Output
    detected_document_type: str
    classification_confidence: float
    classification_match: bool
    
    # Extraction Output
    extracted_fields: Dict[str, Any]
    extracted_old_value: str
    extracted_new_value: str
    extraction_confidence: float
    
    # Forgery Output
    forgery_score: float
    forgery_result: str  # PASS, FLAG, FAIL
    forgery_details: Dict[str, float]
    
    # Scoring Output
    old_name_match_score: float
    new_name_match_score: float
    overall_score: float
    risk_tier: str
    flags: List[str]
    
    # Summary Output
    ai_summary: str
    ai_recommendation: str
    
    # Step Tracking
    current_step: str
    errors: List[str]
```

### 4.3 Node Implementations

#### Metadata Node (`nodes/metadata.py`)

```python
async def metadata_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Extract document metadata before OCR.
    
    Checks:
        - PDF creation/modification dates
        - Producer software (Photoshop = suspicious)
        - Resolution consistency
        - EXIF data for images
    
    Fast (~10ms), runs before OCR.
    """
    document_path = state.get('document_path')
    metadata = extract_metadata(document_path)  # PyMuPDF / Pillow
    anomalies = detect_anomalies(metadata)
    
    return {
        "metadata": metadata,
        "metadata_anomalies": anomalies,
        "current_step": "metadata"
    }
```

#### Supervisor Pipeline with Step Tracking (`specialized/supervisor.py`)

```python
async def process(
    self,
    request_id: str,
    customer_id: str,
    change_type: str,
    document_type: str,
    requested_old_value: str,
    requested_new_value: str,
    document_path: str,
    on_step_change: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    """
    Process a document through the supervisor pipeline.
    
    Args:
        on_step_change: Optional callback for real-time step updates
                       (ignored in supervisor mode - supervisor handles
                       steps internally)
    
    Returns:
        Final processing state
    """
```

#### Conditional Routing

```python
def route_after_ocr(state: ProcessingState) -> str:
    """Route based on OCR confidence."""
    if state.get("ocr_confidence", 0) < 0.6:
        return "fallback"  # Use Google Vision
    return "continue"

def route_after_classifier(state: ProcessingState) -> str:
    """Route based on document type match."""
    if not state.get("classification_match", True):
        return "skip_forgery"  # Skip forgery, go to scorer
    return "continue"
```

### 4.4 Real-Time Step Tracking

The pipeline streams step updates to the database:

```python
class DocumentProcessingPipeline:
    STEP_DISPLAY_NAMES = {
        "validation": "Validating Document",
        "metadata": "Extracting Metadata",
        "ocr": "Running OCR",
        "fallback_ocr": "Running Fallback OCR",
        "classifier": "Classifying Document",
        "extractor": "Extracting Fields",
        "forgery": "Detecting Forgery",
        "scorer": "Calculating Scores",
        "summary": "Generating Summary",
        "save_results": "Finalizing Results",
        "complete": "AI Verification Complete",
    }
    
    async def process(self, ..., on_step_change: Callable[[str, str], None]):
        """
        Process with streaming for step tracking.
        
        Uses astream() instead of ainvoke() to get real-time updates.
        """
        async for event in self.compiled_graph.astream(initial_state):
            for node_name, node_output in event.items():
                current_step = node_output.get('current_step', node_name)
                display_name = self.STEP_DISPLAY_NAMES.get(current_step, current_step)
                
                if on_step_change:
                    on_step_change(request_id, display_name)
```

---

## 5. API Contracts

### 5.1 Request Endpoints

#### POST `/api/v1/requests`

```json
// Request
{
  "account_number": "1234567890",
  "change_type": "LEGAL_NAME",
  "document_type": "MARRIAGE_CERTIFICATE",
  "current_value": "Priya Sharma",
  "new_value": "Priya Mehta"
}

// Response (201 Created)
{
  "request_id": "REQ-12345",
  "status": "VALIDATED",
  "message": "Request created successfully. Please upload supporting document.",
  "customer_name": "Priya Sharma"
}
```

#### POST `/api/v1/requests/{id}/upload`

```json
// Request: multipart/form-data
// - file: binary (PDF/JPEG/PNG/TIFF, max 10MB)

// Response (200 OK)
{
  "request_id": "REQ-12345",
  "status": "QUEUED",
  "document_id": "DOC-67890",
  "message": "Document uploaded. Processing will begin shortly."
}
```

#### GET `/api/v1/requests/{id}/document`

```json
// Query Parameters:
// - download: boolean (default: false) - Set to true to force download

// Response (200 OK)
// Content-Type: application/pdf | image/jpeg | image/png | image/tiff
// Content-Disposition: inline (or attachment if download=true)
// Binary file content

// Error Responses:
// 404: Request not found
// 404: No document uploaded for this request
// 404: Document file not found on server
```

#### GET `/api/v1/requests/{id}`

```json
// Response (200 OK)
{
  "request_id": "REQ-12345",
  "customer_id": "C001",
  "change_type": "LEGAL_NAME",
  "document_type": "MARRIAGE_CERTIFICATE",
  "status": "AI_VERIFIED_PENDING_HUMAN",
  
  "requested_old_value": "Priya Sharma",
  "requested_new_value": "Priya Mehta",
  "extracted_old_value": "Priya Sharma",
  "extracted_new_value": "Priya Mehta",
  
  "extraction_details": [
    {"field_name": "bride_name", "value": "Priya Sharma", "confidence": 0.97},
    {"field_name": "married_name", "value": "Priya Mehta", "confidence": 0.94}
  ],
  
  "confidence": {
    "old_name_match": 1.0,
    "new_name_match": 1.0,
    "ocr_confidence": 0.92,
    "extraction_confidence": 0.94,
    "doc_authenticity": 0.87,
    "overall": 0.946
  },
  
  "forgery": {
    "score": 0.87,
    "result": "PASS",
    "metadata_score": 0.95,
    "ela_score": 0.85,
    "font_score": 0.82,
    "ml_score": 0.88
  },
  
  "risk_tier": "LOW",
  "flags": [],
  "ai_recommendation": "APPROVE",
  "ai_summary": "Marriage Certificate verified. Old name matches (100%)...",
  
  "document_url": "/api/v1/requests/REQ-12345/document",
  
  "current_processing_step": null,
  "is_locked": false,
  "can_be_claimed": true,
  "time_in_current_status_minutes": 15
}
```

### 5.2 Checker Endpoints (JWT Protected)

#### GET `/api/v1/checker/queue`

```json
// Headers: Authorization: Bearer <jwt_token>
// Query: ?risk_tier=HIGH&status=AI_VERIFIED_PENDING_HUMAN&page=1&limit=20

// Response (200 OK)
{
  "items": [
    {
      "request_id": "REQ-12345",
      "customer_id": "C001",
      "change_type": "LEGAL_NAME",
      "risk_tier": "LOW",
      "ai_recommendation": "APPROVE",
      "overall_confidence": 0.946,
      "flags": [],
      "created_at": "2024-03-20T10:30:00Z",
      "time_in_queue_minutes": 15
    }
  ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

#### POST `/api/v1/checker/claim/{id}`

```json
// Headers: Authorization: Bearer <jwt_token>

// Response (200 OK)
{
  "request_id": "REQ-12345",
  "claimed": true,
  "lock_until": "2024-03-20T11:25:00Z",
  "message": "Request claimed for 15 minutes"
}

// Response (409 Conflict)
{
  "detail": "Request already claimed by another checker"
}
```

#### POST `/api/v1/checker/decide/{id}`

```json
// Headers: Authorization: Bearer <jwt_token>
// Request
{
  "decision": "APPROVE",
  "reason": null
}

// Response (200 OK)
{
  "request_id": "REQ-12345",
  "decision": "APPROVE",
  "new_status": "APPROVED",
  "rps_updated": true,
  "message": "Decision recorded. Core banking updated successfully."
}

// For REJECT (reason required)
{
  "decision": "REJECT",
  "reason": "Document appears to be a photocopy, not original"
}
```

### 5.3 Authentication Endpoints

#### POST `/api/v1/auth/login`

```json
// Request
{
  "username": "checker_jane",
  "password": "password123"
}

// Response (200 OK)
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "username": "checker_jane",
    "role": "checker"
  }
}
```

---

## 6. Database Schema

### 6.1 Tables

```sql
-- Requests table
CREATE TABLE requests (
    request_id VARCHAR(36) PRIMARY KEY,
    idempotency_key VARCHAR(64) UNIQUE,
    customer_id VARCHAR(20) NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    
    requested_old_value VARCHAR(255) NOT NULL,
    requested_new_value VARCHAR(255) NOT NULL,
    extracted_old_value VARCHAR(255),
    extracted_new_value VARCHAR(255),
    extraction_metadata JSONB,
    
    old_name_match_score DECIMAL(5,4),
    new_name_match_score DECIMAL(5,4),
    ocr_confidence DECIMAL(5,4),
    extraction_confidence DECIMAL(5,4),
    doc_authenticity_score DECIMAL(5,4),
    overall_confidence DECIMAL(5,4),
    
    forgery_score DECIMAL(5,4),
    forgery_result VARCHAR(10),
    forgery_details JSONB,
    
    risk_tier VARCHAR(10),
    flags JSONB,
    ai_recommendation VARCHAR(20),
    ai_summary TEXT,
    
    document_storage_path VARCHAR(255),
    filenet_staging_id VARCHAR(100),
    filenet_permanent_id VARCHAR(100),
    
    status VARCHAR(30) NOT NULL,
    current_processing_step VARCHAR(50),
    assigned_checker VARCHAR(50),
    checker_lock_until TIMESTAMP,
    checker_decision VARCHAR(20),
    checker_decision_reason TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    staged_at TIMESTAMP,
    claimed_at TIMESTAMP,
    decided_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(36) REFERENCES requests(request_id),
    event_type VARCHAR(20) NOT NULL,
    actor_type VARCHAR(20) NOT NULL,
    actor_id VARCHAR(50),
    agent_name VARCHAR(50),
    agent_version VARCHAR(20),
    llm_model VARCHAR(50),
    previous_state VARCHAR(30),
    new_state VARCHAR(30),
    action_details JSONB,
    record_snapshot JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);

-- Customers table (RPS mock)
CREATE TABLE customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    legal_name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_requests_status ON requests(status);
CREATE INDEX idx_requests_customer ON requests(customer_id);
CREATE INDEX idx_requests_risk_tier ON requests(risk_tier, status);
CREATE INDEX idx_requests_checker ON requests(assigned_checker, status);
CREATE INDEX idx_audit_request ON audit_logs(request_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
```

---

## 7. Configuration

### 7.1 Backend Configuration (`app/config.py`)

```python
class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # App
    APP_NAME: str = "IASW"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str  # PostgreSQL async URL
    DATABASE_SYNC_URL: str  # PostgreSQL sync URL (for Celery)
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM
    ANTHROPIC_API_KEY: str
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.0
    
    # OCR
    OCR_CONFIDENCE_THRESHOLD: float = 0.6
    
    # Forgery Detection
    FORGERY_PASS_THRESHOLD: float = 0.85
    FORGERY_FAIL_THRESHOLD: float = 0.60
    
    # JWT Authentication
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24
    
    # Pipeline Mode
    USE_SUPERVISOR_AGENTS: bool = True  # True = supervisor mode, False = linear
    
    # Storage
    STORAGE_PATH: str = "./storage"
    
    class Config:
        env_file = ".env"
```

### 7.2 Environment Variables

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/iasw
DATABASE_SYNC_URL=postgresql://user:pass@localhost:5432/iasw
REDIS_URL=redis://localhost:6379/0

ANTHROPIC_API_KEY=sk-ant-...

JWT_SECRET_KEY=your-secret-key-here

# Optional
USE_SUPERVISOR_AGENTS=true
DEBUG=false
```

### 7.3 Database Edit Utility (`edit_db.py`)

Interactive CLI tool for testing and database management:

```python
# Run with: python backend/edit_db.py

# Features:
# 1. List all requests - view recent requests with status
# 2. Reset specific request to PENDING_HUMAN - for re-testing checker workflow
# 3. Reset ALL completed requests - bulk reset for testing
# 4. Delete a request - remove request and audit logs
# 5. Update a field on a request - modify any field directly
# 6. Exit

# Example usage:
# - Reset a request after testing approval flow
# - Delete test requests created during development
# - Update risk_tier or ai_recommendation for testing different scenarios
```

---

## 8. Error Handling

### 8.1 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `CUSTOMER_NOT_FOUND` | 404 | Customer ID not found in RPS |
| `DUPLICATE_REQUEST` | 409 | Active request exists for same customer + change type |
| `INVALID_DOCUMENT_TYPE` | 400 | Document type not allowed for change type |
| `FILE_TOO_LARGE` | 400 | File exceeds 10MB limit |
| `INVALID_FILE_FORMAT` | 400 | File is not PDF/JPEG/PNG/TIFF |
| `REQUEST_NOT_FOUND` | 404 | Request ID not found |
| `REQUEST_ALREADY_CLAIMED` | 409 | Request locked by another checker |
| `LOCK_EXPIRED` | 409 | Checker's lock has expired |
| `REASON_REQUIRED` | 400 | Reason required for reject/escalate |
| `UNAUTHORIZED` | 401 | Invalid or missing JWT token |
| `FORBIDDEN` | 403 | User lacks required role |
| `PROCESSING_FAILED` | 500 | Document processing pipeline failed |

### 8.2 Error Response Format

```json
{
  "error": "REQUEST_ALREADY_CLAIMED",
  "detail": "Request is currently being reviewed by another checker",
  "request_id": "REQ-12345"
}
```

### 8.3 Pipeline Error Handling

```python
# Agent-level: Return partial results with error flag
return {
    **state,
    "extraction_error": str(e),
    "flags": state.get("flags", []) + ["EXTRACTION_FAILED"]
}

# Pipeline-level: Set status to FAILED
request.status = RequestStatus.FAILED

# Task-level: Retry with exponential backoff
raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```
