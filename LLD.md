# Intelligent Account Servicing Workflow (IASW)
## Low-Level Design Document

---

## 1. Project Structure

```
iasw/
├── frontend/                     # Next.js 14 Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── staff/                    # Staff Portal
│   │   │   │   ├── page.tsx              # Dashboard
│   │   │   │   ├── requests/
│   │   │   │   │   ├── page.tsx          # Request list
│   │   │   │   │   ├── new/
│   │   │   │   │   │   └── page.tsx      # New request form
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx      # Request details
│   │   │   │   └── layout.tsx
│   │   │   ├── checker/                  # Checker Workbench
│   │   │   │   ├── page.tsx              # Queue dashboard
│   │   │   │   ├── queue/
│   │   │   │   │   └── page.tsx          # Request queue
│   │   │   │   ├── review/
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx      # Review screen
│   │   │   │   └── layout.tsx
│   │   │   └── api/                      # API Routes (BFF)
│   │   │       ├── requests/
│   │   │       │   └── route.ts
│   │   │       ├── checker/
│   │   │       │   └── route.ts
│   │   │       └── health/
│   │   │           └── route.ts
│   │   ├── components/
│   │   │   ├── ui/                       # Shared UI components
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Table.tsx
│   │   │   │   ├── Badge.tsx
│   │   │   │   ├── ProgressBar.tsx
│   │   │   │   └── FileUpload.tsx
│   │   │   ├── staff/                    # Staff-specific components
│   │   │   │   ├── RequestForm.tsx
│   │   │   │   ├── RequestList.tsx
│   │   │   │   ├── DocumentUploader.tsx
│   │   │   │   └── RequestStatus.tsx
│   │   │   ├── checker/                  # Checker-specific components
│   │   │   │   ├── QueueTable.tsx
│   │   │   │   ├── ReviewPanel.tsx
│   │   │   │   ├── DocumentViewer.tsx
│   │   │   │   ├── ConfidenceScoreCard.tsx
│   │   │   │   ├── AISummaryPanel.tsx
│   │   │   │   ├── FlagsPanel.tsx
│   │   │   │   ├── DecisionButtons.tsx
│   │   │   │   └── ExtractedFieldsTable.tsx
│   │   │   └── shared/
│   │   │       ├── Header.tsx
│   │   │       ├── Sidebar.tsx
│   │   │       └── LoadingSpinner.tsx
│   │   ├── hooks/
│   │   │   ├── useRequest.ts
│   │   │   ├── useQueue.ts
│   │   │   ├── useWebSocket.ts
│   │   │   └── useAuth.ts
│   │   ├── lib/
│   │   │   ├── api.ts                    # API client
│   │   │   ├── constants.ts
│   │   │   └── utils.ts
│   │   ├── types/
│   │   │   ├── request.ts
│   │   │   ├── checker.ts
│   │   │   └── api.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── next.config.js
│
├── backend/                      # FastAPI Application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                       # FastAPI entry point
│   │   ├── config.py                     # Configuration settings
│   │   ├── dependencies.py               # Dependency injection
│   │   │
│   │   ├── api/                          # API Layer
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py             # Main router
│   │   │   │   ├── requests.py           # Request endpoints
│   │   │   │   ├── checker.py            # Checker endpoints
│   │   │   │   ├── documents.py          # Document endpoints
│   │   │   │   └── health.py             # Health check
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── logging.py
│   │   │       └── error_handler.py
│   │   │
│   │   ├── models/                       # Database Models (SQLAlchemy)
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── request.py                # PendingRequest model
│   │   │   ├── audit.py                  # AuditLog model
│   │   │   ├── customer.py               # Customer (RPS mock) model
│   │   │   └── checker.py                # Checker model
│   │   │
│   │   ├── schemas/                      # Pydantic Schemas
│   │   │   ├── __init__.py
│   │   │   ├── request.py
│   │   │   ├── document.py
│   │   │   ├── checker.py
│   │   │   ├── confidence.py
│   │   │   └── common.py
│   │   │
│   │   ├── services/                     # Business Logic Layer
│   │   │   ├── __init__.py
│   │   │   ├── request_service.py
│   │   │   ├── validation_service.py
│   │   │   ├── checker_service.py
│   │   │   ├── rps_service.py            # Core banking mock
│   │   │   ├── filenet_service.py        # Document storage mock
│   │   │   └── notification_service.py
│   │   │
│   │   ├── agents/                       # LangGraph Agents
│   │   │   ├── __init__.py
│   │   │   ├── graph.py                  # Main LangGraph definition
│   │   │   ├── state.py                  # Graph state definition
│   │   │   ├── nodes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── validation.py         # Validation Agent
│   │   │   │   ├── ocr.py                # OCR Node
│   │   │   │   ├── classifier.py         # Document Classifier Agent
│   │   │   │   ├── extractor.py          # Field Extractor Agent
│   │   │   │   ├── forgery.py            # Forgery Detector Agent
│   │   │   │   ├── scorer.py             # Confidence Scorer Agent
│   │   │   │   └── summary.py            # Summary Agent
│   │   │   ├── prompts/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── classifier_prompt.py
│   │   │   │   ├── extractor_prompt.py
│   │   │   │   └── summary_prompt.py
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── ocr_tool.py
│   │   │       ├── name_matcher.py
│   │   │       └── forgery_tools.py
│   │   │
│   │   ├── workers/                      # Celery Workers
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py             # Celery configuration
│   │   │   ├── tasks.py                  # Task definitions
│   │   │   └── callbacks.py              # Task callbacks
│   │   │
│   │   ├── db/                           # Database Layer
│   │   │   ├── __init__.py
│   │   │   ├── session.py                # DB session management
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── request_repo.py
│   │   │   │   ├── audit_repo.py
│   │   │   │   └── customer_repo.py
│   │   │   └── migrations/
│   │   │       └── versions/
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── id_generator.py
│   │       ├── hash_utils.py
│   │       ├── date_utils.py
│   │       └── file_utils.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_validation.py
│   │   │   ├── test_scorer.py
│   │   │   └── test_extractor.py
│   │   ├── integration/
│   │   │   ├── test_graph.py
│   │   │   └── test_api.py
│   │   └── fixtures/
│   │       ├── documents/
│   │       │   └── marriage_cert_sample.pdf
│   │       └── mock_data.py
│   │
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
│
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

---

## 2. Backend Classes & Modules

### 2.1 API Layer

#### `app/api/v1/requests.py`
```python
"""
Request API endpoints for staff intake operations.
"""

class RequestRouter:
    """
    Handles all request-related API endpoints.
    
    Endpoints:
        POST   /api/v1/requests           - Create new change request
        GET    /api/v1/requests           - List requests (with filters)
        GET    /api/v1/requests/{id}      - Get request details
        POST   /api/v1/requests/{id}/upload - Upload document
    """
```

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/requests` | Create new request | `CreateRequestSchema` | `RequestResponse` |
| GET | `/requests` | List with filters | Query params | `List[RequestSummary]` |
| GET | `/requests/{id}` | Get details | - | `RequestDetail` |
| POST | `/requests/{id}/upload` | Upload document | `multipart/form-data` | `UploadResponse` |

---

#### `app/api/v1/checker.py`
```python
"""
Checker API endpoints for review operations.
"""

class CheckerRouter:
    """
    Handles all checker workbench API endpoints.
    
    Endpoints:
        GET    /api/v1/checker/queue      - Get pending requests queue
        POST   /api/v1/checker/claim/{id} - Claim a request for review
        POST   /api/v1/checker/decide/{id} - Submit decision (approve/reject)
        POST   /api/v1/checker/release/{id} - Release claimed request
    """
```

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | `/checker/queue` | Get queue | Query: `risk_tier`, `status` | `List[QueueItem]` |
| POST | `/checker/claim/{id}` | Claim request | - | `ClaimResponse` |
| POST | `/checker/decide/{id}` | Submit decision | `DecisionSchema` | `DecisionResponse` |
| POST | `/checker/release/{id}` | Release lock | - | `ReleaseResponse` |

---

### 2.2 Database Models

#### `app/models/request.py`
```python
"""
PendingRequest SQLAlchemy model - core entity for change requests.
"""

class PendingRequest(Base):
    """
    Represents a change request in the pending table.
    
    Attributes:
        request_id (str): Primary key, format "REQ-XXXXX"
        idempotency_key (str): Hash for duplicate detection
        customer_id (str): Reference to RPS customer
        change_type (ChangeType): Enum - LEGAL_NAME, ADDRESS, DOB, CONTACT
        document_type (DocumentType): Enum - MARRIAGE_CERT, GAZETTE, etc.
        
        # Request Data
        requested_old_value (str): Value to be changed
        requested_new_value (str): New value requested
        
        # Extracted Data
        extracted_old_value (str): Value extracted from document
        extracted_new_value (str): New value from document
        extraction_metadata (JSON): All extracted fields with confidence
        
        # Scores
        old_name_match_score (Decimal): 0.0000 - 1.0000
        new_name_match_score (Decimal): 0.0000 - 1.0000
        ocr_confidence (Decimal): OCR quality score
        extraction_confidence (Decimal): LLM extraction confidence
        doc_authenticity_score (Decimal): Forgery detection score
        overall_confidence (Decimal): Weighted aggregate
        
        # Forgery
        forgery_score (Decimal): 0.0 (forged) to 1.0 (authentic)
        forgery_result (ForgeryResult): Enum - PASS, FLAG, FAIL
        forgery_details (JSON): Per-layer breakdown
        
        # Routing
        risk_tier (RiskTier): Enum - LOW, MEDIUM, HIGH
        flags (JSON): Array of flag codes
        ai_recommendation (Recommendation): APPROVE, REJECT, MANUAL_REVIEW
        ai_summary (str): Human-readable summary
        
        # Document Storage
        document_storage_path (str): S3/local path
        filenet_staging_id (str): FileNet staging reference
        filenet_permanent_id (str): FileNet permanent reference
        
        # Workflow
        status (RequestStatus): Current state enum
        assigned_checker (str): Checker who claimed
        checker_lock_until (datetime): Lock expiry
        checker_decision (Decision): APPROVE, REJECT, MORE_INFO, ESCALATE
        checker_decision_reason (str): Mandatory for reject/escalate
        
        # Timestamps
        created_at, validated_at, processing_started_at, 
        processing_completed_at, staged_at, claimed_at, 
        decided_at, completed_at (datetime)
    """
    
    __tablename__ = "pending_requests"
```

---

#### `app/models/audit.py`
```python
"""
AuditLog SQLAlchemy model - immutable audit trail.
"""

class AuditLog(Base):
    """
    Immutable audit record for every state transition.
    
    Attributes:
        audit_id (UUID): Primary key
        request_id (str): Foreign key to PendingRequest
        event_type (EventType): STATE_CHANGE, HUMAN_ACTION, SYSTEM_EVENT, ERROR
        previous_state (str): State before transition
        new_state (str): State after transition
        actor_type (ActorType): SYSTEM, HUMAN, AI_AGENT
        actor_id (str): Identifier of actor
        agent_name (str): AI agent name if applicable
        agent_version (str): Version of agent
        llm_model (str): LLM model used
        action_details (JSON): Detailed action data
        record_snapshot (JSON): Full request state at this moment
        timestamp (datetime): When event occurred
        checksum (str): SHA-256 for tamper detection
    """
    
    __tablename__ = "audit_logs"
```

---

### 2.3 Pydantic Schemas

#### `app/schemas/request.py`
```python
"""
Pydantic schemas for request validation and serialization.
"""

class CreateRequestSchema(BaseModel):
    """
    Schema for creating a new change request.
    
    Fields:
        customer_id: str - Customer ID from RPS
        change_type: ChangeType - Type of change requested
        document_type: DocumentType - Type of supporting document
        current_value: str - Current value (e.g., current name)
        new_value: str - Requested new value
    """
    customer_id: str = Field(..., min_length=1, max_length=20)
    change_type: ChangeType
    document_type: DocumentType
    current_value: str = Field(..., min_length=1, max_length=255)
    new_value: str = Field(..., min_length=1, max_length=255)


class RequestResponse(BaseModel):
    """
    Response after creating a request.
    
    Fields:
        request_id: str - Generated request ID
        status: RequestStatus - Current status
        message: str - User-friendly message
    """
    request_id: str
    status: RequestStatus
    message: str


class RequestDetail(BaseModel):
    """
    Full request details for viewing.
    
    Includes all fields from PendingRequest model
    plus computed fields for UI display.
    """
    # ... all fields from model
    
    # Computed fields
    time_in_current_status: timedelta
    can_be_claimed: bool
    is_locked: bool
```

---

#### `app/schemas/confidence.py`
```python
"""
Pydantic schemas for confidence scoring.
"""

class FieldScore(BaseModel):
    """
    Score for a single extracted field.
    
    Fields:
        field_name: str - Name of the field
        extracted_value: str - Value extracted from document
        expected_value: str - Value from request
        match_score: float - 0.0 to 1.0
        match_method: str - Algorithm used (e.g., "jaro_winkler")
        confidence: float - Extraction confidence
    """
    field_name: str
    extracted_value: str
    expected_value: str
    match_score: float = Field(..., ge=0.0, le=1.0)
    match_method: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class ConfidenceScoreCard(BaseModel):
    """
    Complete confidence score card for a request.
    
    Fields:
        request_id: str
        field_scores: List[FieldScore] - Per-field breakdown
        ocr_confidence: float - OCR quality
        extraction_confidence: float - LLM extraction quality
        doc_authenticity_score: float - Forgery detection
        overall_score: float - Weighted aggregate
        risk_tier: RiskTier - LOW/MEDIUM/HIGH
        flags: List[str] - Flag codes
        recommendation: Recommendation - AI recommendation
    """
    request_id: str
    field_scores: List[FieldScore]
    ocr_confidence: float
    extraction_confidence: float
    doc_authenticity_score: float
    overall_score: float
    risk_tier: RiskTier
    flags: List[str]
    recommendation: Recommendation
```

---

### 2.4 Services

#### `app/services/request_service.py`
```python
"""
Business logic for request operations.
"""

class RequestService:
    """
    Handles request creation, validation, and lifecycle.
    
    Methods:
        create_request(data: CreateRequestSchema) -> RequestResponse
            - Generates idempotency key
            - Checks for duplicates
            - Creates DB record
            - Enqueues for processing
        
        get_request(request_id: str) -> RequestDetail
            - Fetches request with all related data
        
        list_requests(filters: RequestFilters) -> List[RequestSummary]
            - Paginated list with filtering
        
        upload_document(request_id: str, file: UploadFile) -> UploadResponse
            - Validates file (format, size, virus scan)
            - Stores in S3/local
            - Updates request with document path
            - Triggers processing pipeline
    
    Dependencies:
        - RequestRepository
        - ValidationService
        - FileNetService
        - CeleryApp (for async processing)
    """
    
    def __init__(
        self,
        request_repo: RequestRepository,
        validation_service: ValidationService,
        filenet_service: FileNetService,
        celery_app: Celery
    ):
        ...
```

---

#### `app/services/validation_service.py`
```python
"""
Synchronous validation logic (< 500ms).
"""

class ValidationService:
    """
    Performs quick validations before accepting a request.
    
    Methods:
        validate_request(data: CreateRequestSchema) -> ValidationResult
            - Runs all checks in parallel
            - Returns aggregated result
        
        validate_customer(customer_id: str) -> bool
            - Checks customer exists in RPS
        
        validate_name_match(input_name: str, rps_name: str) -> float
            - Fuzzy match score (Jaro-Winkler)
        
        validate_document_type(change_type: ChangeType, doc_type: DocumentType) -> bool
            - Checks doc type is allowed for change type
        
        validate_file(file: UploadFile) -> FileValidationResult
            - Format check (PDF/JPEG/PNG/TIFF)
            - Size check (≤ 10MB)
            - Quick virus scan (ClamAV, 200ms timeout)
        
        check_duplicate(customer_id: str, change_type: ChangeType) -> Optional[str]
            - Returns existing request_id if duplicate found
    
    Dependencies:
        - RPSService
        - CustomerRepository
    """
```

---

#### `app/services/checker_service.py`
```python
"""
Business logic for checker operations.
"""

class CheckerService:
    """
    Handles checker workflow operations.
    
    Methods:
        get_queue(checker_id: str, filters: QueueFilters) -> List[QueueItem]
            - Returns requests available for review
            - Filters by risk tier based on checker role
        
        claim_request(request_id: str, checker_id: str) -> ClaimResult
            - Sets assigned_checker
            - Sets lock expiry (15 min)
            - Updates status to IN_REVIEW
            - Creates audit record
        
        release_request(request_id: str, checker_id: str) -> bool
            - Clears assignment and lock
            - Returns to queue
            - Creates audit record
        
        submit_decision(
            request_id: str, 
            checker_id: str, 
            decision: Decision, 
            reason: Optional[str]
        ) -> DecisionResult
            - Validates checker owns the lock
            - Validates reason provided for reject/escalate
            - Updates request status
            - Triggers downstream actions (RPS update for approve)
            - Creates audit record
        
        check_lock_expiry() -> List[str]
            - Background job to release expired locks
            - Returns list of released request_ids
    
    Dependencies:
        - RequestRepository
        - AuditRepository
        - RPSService
        - NotificationService
    """
```

---

#### `app/services/rps_service.py`
```python
"""
Core banking system integration (mock).
"""

class RPSService:
    """
    Mock RPS (core banking) service.
    
    Methods:
        get_customer(customer_id: str) -> Optional[CustomerRecord]
            - Fetches customer from mock RPS
        
        update_customer(
            customer_id: str, 
            field: str, 
            new_value: str,
            actor_id: str,
            actor_type: ActorType
        ) -> UpdateResult
            - CRITICAL: Validates actor_type == HUMAN
            - Updates customer record
            - Returns success/failure
    
    HITL Enforcement:
        The update_customer method MUST verify that actor_type is HUMAN.
        Any call with actor_type != HUMAN will be rejected and logged
        as a security event.
    """
    
    def update_customer(self, ...):
        # HITL ENFORCEMENT
        if actor_type != ActorType.HUMAN:
            self.audit_service.log_security_event(
                event="RPS_UPDATE_BLOCKED",
                reason="Non-human actor attempted RPS update",
                actor_id=actor_id,
                actor_type=actor_type
            )
            raise HITLViolationError("Only human actors can update RPS")
        
        # Proceed with update...
```

---

### 2.5 LangGraph Agents

#### `app/agents/state.py`
```python
"""
LangGraph state definition for the processing pipeline.
"""

class ProcessingState(TypedDict):
    """
    State that flows through the LangGraph pipeline.
    
    Fields:
        # Input
        request_id: str
        customer_id: str
        change_type: str
        document_type: str
        requested_old_value: str
        requested_new_value: str
        document_path: str
        
        # OCR Output
        ocr_text: str
        ocr_confidence: float
        ocr_word_confidences: List[dict]
        ocr_method: str  # "tesseract" or "google_vision"
        
        # Classification Output
        detected_document_type: str
        classification_confidence: float
        classification_match: bool
        
        # Extraction Output
        extracted_fields: dict
        extraction_confidence: float
        
        # Forgery Output
        forgery_score: float
        forgery_result: str  # PASS, FLAG, FAIL
        forgery_details: dict
        
        # Scoring Output
        field_scores: List[dict]
        overall_score: float
        risk_tier: str
        flags: List[str]
        
        # Summary Output
        ai_summary: str
        ai_recommendation: str
        
        # Error Handling
        errors: List[str]
        current_step: str
    """
```

---

#### `app/agents/graph.py`
```python
"""
Main LangGraph definition for document processing pipeline.
"""

from langgraph.graph import StateGraph, END

class DocumentProcessingGraph:
    """
    LangGraph pipeline for processing change requests.
    
    Graph Structure:
        START
          │
          ▼
        ┌─────────────────┐
        │  validation     │ ─── FAIL ──▶ END (status: VALIDATION_FAILED)
        └────────┬────────┘
                 │ PASS
                 ▼
        ┌─────────────────┐
        │     ocr         │ ─── LOW_CONF ──▶ fallback_ocr
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │   classifier    │ ─── MISMATCH ──▶ flag_and_continue
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │   extractor     │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │    forgery      │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │    scorer       │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │    summary      │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  save_results   │
        └────────┬────────┘
                 │
                 ▼
                END (status: AI_VERIFIED_PENDING_HUMAN)
    
    Conditional Routing:
        - After OCR: if confidence < 0.6, route to fallback_ocr
        - After classifier: if mismatch, add flag but continue
        - After forgery: if FAIL, set risk_tier to HIGH
    """
    
    def __init__(self, llm, ocr_service, db_session):
        self.llm = llm
        self.ocr_service = ocr_service
        self.db_session = db_session
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        graph = StateGraph(ProcessingState)
        
        # Add nodes
        graph.add_node("validation", self.validation_node)
        graph.add_node("ocr", self.ocr_node)
        graph.add_node("fallback_ocr", self.fallback_ocr_node)
        graph.add_node("classifier", self.classifier_node)
        graph.add_node("extractor", self.extractor_node)
        graph.add_node("forgery", self.forgery_node)
        graph.add_node("scorer", self.scorer_node)
        graph.add_node("summary", self.summary_node)
        graph.add_node("save_results", self.save_results_node)
        
        # Add edges
        graph.add_conditional_edges(
            "validation",
            self._route_after_validation,
            {"continue": "ocr", "fail": END}
        )
        graph.add_conditional_edges(
            "ocr",
            self._route_after_ocr,
            {"continue": "classifier", "fallback": "fallback_ocr"}
        )
        graph.add_edge("fallback_ocr", "classifier")
        graph.add_edge("classifier", "extractor")
        graph.add_edge("extractor", "forgery")
        graph.add_edge("forgery", "scorer")
        graph.add_edge("scorer", "summary")
        graph.add_edge("summary", "save_results")
        graph.add_edge("save_results", END)
        
        graph.set_entry_point("validation")
        
        return graph.compile()
    
    def _route_after_ocr(self, state: ProcessingState) -> str:
        if state["ocr_confidence"] < 0.6:
            return "fallback"
        return "continue"
```

---

#### `app/agents/nodes/validation.py`
```python
"""
Validation Agent - validates request before processing.
"""

class ValidationNode:
    """
    Validates the request can proceed to document processing.
    
    Checks:
        1. Request exists and is in correct status
        2. Document file exists and is accessible
        3. Customer still exists in RPS
    
    Input State:
        - request_id
        - document_path
        - customer_id
    
    Output State Updates:
        - validation_passed: bool
        - validation_errors: List[str]
    
    Routing:
        - If all checks pass: continue to OCR
        - If any check fails: END with VALIDATION_FAILED status
    """
    
    async def __call__(self, state: ProcessingState) -> ProcessingState:
        errors = []
        
        # Check document exists
        if not self._file_exists(state["document_path"]):
            errors.append("Document file not found")
        
        # Check customer exists
        customer = await self.rps_service.get_customer(state["customer_id"])
        if not customer:
            errors.append("Customer not found in RPS")
        
        return {
            **state,
            "validation_passed": len(errors) == 0,
            "validation_errors": errors,
            "current_step": "validation"
        }
```

---

#### `app/agents/nodes/ocr.py`
```python
"""
OCR Node - extracts text from document.
"""

class OCRNode:
    """
    Performs OCR on the uploaded document.
    
    Process:
        1. Load document (PDF or image)
        2. Pre-process images (deskew, binarize, denoise)
        3. Run Tesseract OCR
        4. Calculate confidence scores
    
    Input State:
        - document_path
    
    Output State Updates:
        - ocr_text: str - Extracted text
        - ocr_confidence: float - Average confidence
        - ocr_word_confidences: List[dict] - Per-word scores
        - ocr_method: str - "tesseract"
    
    Routing:
        - If confidence >= 0.6: continue to classifier
        - If confidence < 0.6: route to fallback_ocr
    """
    
    def __init__(self, tesseract_config: dict):
        self.tesseract_config = tesseract_config
    
    async def __call__(self, state: ProcessingState) -> ProcessingState:
        # Load and pre-process document
        images = self._load_document(state["document_path"])
        processed_images = [self._preprocess(img) for img in images]
        
        # Run OCR
        results = []
        for img in processed_images:
            result = pytesseract.image_to_data(
                img, 
                output_type=pytesseract.Output.DICT,
                config=self.tesseract_config
            )
            results.append(result)
        
        # Aggregate results
        text, confidence, word_confs = self._aggregate_results(results)
        
        return {
            **state,
            "ocr_text": text,
            "ocr_confidence": confidence,
            "ocr_word_confidences": word_confs,
            "ocr_method": "tesseract",
            "current_step": "ocr"
        }
    
    def _preprocess(self, image):
        """Apply image pre-processing pipeline."""
        image = self._deskew(image)
        image = self._binarize(image)
        image = self._denoise(image)
        image = self._sharpen(image)
        return image
```

---

#### `app/agents/nodes/classifier.py`
```python
"""
Document Classifier Agent - verifies document type.
"""

class ClassifierNode:
    """
    Classifies the document type using LLM.
    
    Process:
        1. Send OCR text to LLM with classification prompt
        2. Parse structured response
        3. Compare detected type with declared type
    
    Input State:
        - ocr_text
        - document_type (declared)
    
    Output State Updates:
        - detected_document_type: str
        - classification_confidence: float
        - classification_match: bool
        - flags: adds DOC_TYPE_MISMATCH if applicable
    """
    
    def __init__(self, llm, prompt_template: str):
        self.llm = llm
        self.prompt_template = prompt_template
    
    async def __call__(self, state: ProcessingState) -> ProcessingState:
        prompt = self.prompt_template.format(
            ocr_text=state["ocr_text"][:4000]  # Truncate for token limit
        )
        
        response = await self.llm.ainvoke(prompt)
        result = self._parse_response(response)
        
        # Check for match
        declared = state["document_type"]
        detected = result["detected_type"]
        is_match = declared.upper() == detected.upper()
        
        # Add flag if mismatch
        flags = state.get("flags", [])
        if not is_match:
            flags.append("DOC_TYPE_MISMATCH")
        
        return {
            **state,
            "detected_document_type": detected,
            "classification_confidence": result["confidence"],
            "classification_match": is_match,
            "flags": flags,
            "current_step": "classifier"
        }
```

---

#### `app/agents/nodes/extractor.py`
```python
"""
Field Extractor Agent - extracts structured fields.
"""

class ExtractorNode:
    """
    Extracts structured fields from document using LLM.
    
    Process:
        1. Select extraction prompt based on document type
        2. Send OCR text to LLM
        3. Parse structured response with field values and confidence
    
    Input State:
        - ocr_text
        - detected_document_type
    
    Output State Updates:
        - extracted_fields: dict with structure:
            {
                "bride_name": {"value": "...", "confidence": 0.97},
                "married_name": {"value": "...", "confidence": 0.94},
                ...
            }
        - extraction_confidence: float (average)
    
    Field Mapping (Marriage Certificate):
        - bride_name -> old_value
        - married_name -> new_value
    """
    
    FIELD_SCHEMAS = {
        "MARRIAGE_CERTIFICATE": {
            "required": ["bride_name", "married_name"],
            "optional": ["marriage_date", "groom_name", "issuing_authority", "certificate_number"]
        },
        "GAZETTE_NOTIFICATION": {
            "required": ["old_name", "new_name"],
            "optional": ["publication_date", "gazette_number"]
        }
    }
    
    async def __call__(self, state: ProcessingState) -> ProcessingState:
        doc_type = state["detected_document_type"]
        schema = self.FIELD_SCHEMAS.get(doc_type, {})
        
        prompt = self._build_extraction_prompt(
            state["ocr_text"],
            schema
        )
        
        response = await self.llm.ainvoke(prompt)
        fields = self._parse_fields(response)
        
        # Calculate average confidence
        confidences = [f["confidence"] for f in fields.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            **state,
            "extracted_fields": fields,
            "extraction_confidence": avg_confidence,
            "current_step": "extractor"
        }
```

---

#### `app/agents/nodes/forgery.py`
```python
"""
Forgery Detector Agent - detects document tampering.
"""

class ForgeryNode:
    """
    Detects potential document forgery using multiple layers.
    
    Detection Layers:
        1. Metadata Analysis (20%) - PDF creation/mod dates, software
        2. ELA Analysis (30%) - Error Level Analysis for edits
        3. Font Consistency (20%) - Font mismatches in text
        4. ML Model (30%) - Pre-trained forgery detection
    
    Input State:
        - document_path
    
    Output State Updates:
        - forgery_score: float (0.0 = forged, 1.0 = authentic)
        - forgery_result: str (PASS/FLAG/FAIL)
        - forgery_details: dict with per-layer scores
        - flags: adds FORGERY_FLAG if result is FLAG/FAIL
        - risk_tier: set to HIGH if result is FAIL
    
    Thresholds:
        - > 0.85: PASS
        - 0.60-0.85: FLAG
        - < 0.60: FAIL
    """
    
    LAYER_WEIGHTS = {
        "metadata": 0.20,
        "ela": 0.30,
        "font": 0.20,
        "ml": 0.30
    }
    
    async def __call__(self, state: ProcessingState) -> ProcessingState:
        document_path = state["document_path"]
        
        # Run all detection layers
        metadata_score = await self._analyze_metadata(document_path)
        ela_score = await self._analyze_ela(document_path)
        font_score = await self._analyze_fonts(document_path)
        ml_score = await self._run_ml_model(document_path)
        
        # Calculate weighted score
        forgery_score = (
            metadata_score * self.LAYER_WEIGHTS["metadata"] +
            ela_score * self.LAYER_WEIGHTS["ela"] +
            font_score * self.LAYER_WEIGHTS["font"] +
            ml_score * self.LAYER_WEIGHTS["ml"]
        )
        
        # Determine result
        if forgery_score > 0.85:
            result = "PASS"
        elif forgery_score >= 0.60:
            result = "FLAG"
        else:
            result = "FAIL"
        
        # Update flags and risk tier
        flags = state.get("flags", [])
        risk_tier = state.get("risk_tier", "LOW")
        
        if result in ["FLAG", "FAIL"]:
            flags.append("FORGERY_FLAG")
        if result == "FAIL":
            risk_tier = "HIGH"
        
        return {
            **state,
            "forgery_score": forgery_score,
            "forgery_result": result,
            "forgery_details": {
                "metadata": metadata_score,
                "ela": ela_score,
                "font": font_score,
                "ml": ml_score
            },
            "flags": flags,
            "risk_tier": risk_tier,
            "current_step": "forgery"
        }
    
    async def _analyze_ela(self, document_path: str) -> float:
        """
        Error Level Analysis - detects edited regions.
        
        Process:
            1. Re-save image at known compression level
            2. Compute pixel difference
            3. High difference in text regions = suspicious
        """
        ...
```

---

#### `app/agents/nodes/scorer.py`
```python
"""
Confidence Scorer Agent - calculates overall confidence.
"""

class ScorerNode:
    """
    Calculates confidence scores and determines risk tier.
    
    Score Components:
        - Name Match (40%): Jaro-Winkler similarity
        - Document Authenticity (30%): Forgery score
        - OCR Confidence (15%): OCR quality
        - Extraction Confidence (15%): LLM extraction quality
    
    Input State:
        - extracted_fields
        - requested_old_value
        - requested_new_value
        - forgery_score
        - ocr_confidence
        - extraction_confidence
    
    Output State Updates:
        - field_scores: List[dict] - Per-field breakdown
        - overall_score: float
        - risk_tier: str (LOW/MEDIUM/HIGH)
        - flags: may add NAME_MISMATCH flag
    
    Risk Tier Thresholds:
        - LOW: score >= 0.90, no major flags
        - MEDIUM: score 0.70-0.90, or minor flags
        - HIGH: score < 0.70, or major flags
    """
    
    WEIGHTS = {
        "name_match": 0.40,
        "doc_authenticity": 0.30,
        "ocr_confidence": 0.15,
        "extraction_confidence": 0.15
    }
    
    async def __call__(self, state: ProcessingState) -> ProcessingState:
        # Calculate name match scores
        old_name_score = self._calculate_name_match(
            state["extracted_fields"].get("bride_name", {}).get("value", ""),
            state["requested_old_value"]
        )
        new_name_score = self._calculate_name_match(
            state["extracted_fields"].get("married_name", {}).get("value", ""),
            state["requested_new_value"]
        )
        avg_name_score = (old_name_score + new_name_score) / 2
        
        # Calculate overall score
        overall_score = (
            avg_name_score * self.WEIGHTS["name_match"] +
            state["forgery_score"] * self.WEIGHTS["doc_authenticity"] +
            state["ocr_confidence"] * self.WEIGHTS["ocr_confidence"] +
            state["extraction_confidence"] * self.WEIGHTS["extraction_confidence"]
        )
        
        # Determine risk tier
        flags = state.get("flags", [])
        major_flags = ["FORGERY_FLAG", "DOC_TYPE_MISMATCH"]
        has_major_flag = any(f in flags for f in major_flags)
        
        if overall_score >= 0.90 and not has_major_flag:
            risk_tier = "LOW"
        elif overall_score >= 0.70 and not has_major_flag:
            risk_tier = "MEDIUM"
        else:
            risk_tier = "HIGH"
        
        # Add name mismatch flag if needed
        if avg_name_score < 0.85:
            flags.append("NAME_MISMATCH")
        
        return {
            **state,
            "field_scores": [
                {"field": "old_name", "score": old_name_score},
                {"field": "new_name", "score": new_name_score}
            ],
            "old_name_match_score": old_name_score,
            "new_name_match_score": new_name_score,
            "overall_score": overall_score,
            "risk_tier": risk_tier,
            "flags": flags,
            "current_step": "scorer"
        }
    
    def _calculate_name_match(self, extracted: str, expected: str) -> float:
        """Calculate Jaro-Winkler similarity between names."""
        from jellyfish import jaro_winkler_similarity
        return jaro_winkler_similarity(
            extracted.lower().strip(),
            expected.lower().strip()
        )
```

---

#### `app/agents/nodes/summary.py`
```python
"""
Summary Agent - generates human-readable summary.
"""

class SummaryNode:
    """
    Generates AI summary and recommendation for checker.
    
    Recommendation Logic:
        - APPROVE: score >= 0.85, name match >= 0.95, no HIGH flags, forgery PASS
        - REJECT: score < 0.60, name match < 0.70, or forgery FAIL
        - MANUAL_REVIEW: everything else
    
    Input State:
        - All previous outputs (scores, flags, extracted fields)
    
    Output State Updates:
        - ai_summary: str - Human-readable summary
        - ai_recommendation: str - APPROVE/REJECT/MANUAL_REVIEW
    
    Summary Format:
        "{Document Type} verified. Old name '{extracted}' matches {field} 
        ({score}%). New name '{extracted}' matches {field} ({score}%). 
        Document authenticity check {result} ({score}%). 
        {Flag messages if any}. Recommendation: {recommendation}"
    """
    
    async def __call__(self, state: ProcessingState) -> ProcessingState:
        # Determine recommendation
        recommendation = self._determine_recommendation(state)
        
        # Generate summary using LLM
        summary = await self._generate_summary(state, recommendation)
        
        return {
            **state,
            "ai_summary": summary,
            "ai_recommendation": recommendation,
            "current_step": "summary"
        }
    
    def _determine_recommendation(self, state: ProcessingState) -> str:
        score = state["overall_score"]
        name_score = min(
            state["old_name_match_score"],
            state["new_name_match_score"]
        )
        forgery = state["forgery_result"]
        flags = state.get("flags", [])
        
        # REJECT conditions
        if score < 0.60:
            return "REJECT"
        if name_score < 0.70:
            return "REJECT"
        if forgery == "FAIL":
            return "REJECT"
        if "DOC_TYPE_MISMATCH" in flags:
            return "REJECT"
        
        # APPROVE conditions
        if (score >= 0.85 and 
            name_score >= 0.95 and 
            forgery == "PASS" and
            not any(f in flags for f in ["FORGERY_FLAG", "DOC_TYPE_MISMATCH"])):
            return "APPROVE"
        
        # Default to manual review
        return "MANUAL_REVIEW"
```

---

### 2.6 Celery Workers

#### `app/workers/celery_app.py`
```python
"""
Celery application configuration.
"""

from celery import Celery

celery_app = Celery(
    "iasw",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=270,  # Soft limit at 4.5 minutes
    worker_prefetch_multiplier=1,  # One task at a time
    task_acks_late=True,  # Ack after completion
    task_reject_on_worker_lost=True,
)
```

---

#### `app/workers/tasks.py`
```python
"""
Celery task definitions.
"""

from celery import Task

class ProcessDocumentTask(Task):
    """
    Async task to process a document through the LangGraph pipeline.
    
    Task Flow:
        1. Update request status to PROCESSING
        2. Initialize LangGraph with request state
        3. Execute graph
        4. Save results to database
        5. Update status to AI_VERIFIED_PENDING_HUMAN
    
    Error Handling:
        - On failure: increment retry count
        - Max 3 retries with exponential backoff
        - On max retries: move to DLQ, alert ops
    
    Idempotency:
        - Checks if already processed before starting
        - Uses request_id as idempotency key
    """
    
    name = "process_document"
    max_retries = 3
    default_retry_delay = 60  # 1 minute
    
    def run(self, request_id: str):
        # Check idempotency
        request = self.get_request(request_id)
        if request.status not in ["VALIDATED", "QUEUED"]:
            return {"status": "skipped", "reason": "already_processed"}
        
        # Update status
        self.update_status(request_id, "PROCESSING")
        
        try:
            # Build initial state
            state = self.build_initial_state(request)
            
            # Execute LangGraph
            graph = self.get_graph()
            result = graph.invoke(state)
            
            # Save results
            self.save_results(request_id, result)
            
            # Update status
            self.update_status(request_id, "AI_VERIFIED_PENDING_HUMAN")
            
            return {"status": "success", "request_id": request_id}
            
        except Exception as e:
            self.handle_failure(request_id, e)
            raise self.retry(exc=e)


@celery_app.task(bind=True, base=ProcessDocumentTask)
def process_document(self, request_id: str):
    return self.run(request_id)
```

---

## 3. Frontend Components

### 3.1 Staff Portal

#### `frontend/src/components/staff/RequestForm.tsx`
```typescript
/**
 * RequestForm - Staff intake form for new change requests.
 * 
 * Props:
 *   onSubmit: (data: CreateRequestData) => Promise<void>
 *   isLoading: boolean
 * 
 * Fields:
 *   - customerId: text input with validation
 *   - changeType: dropdown (LEGAL_NAME, ADDRESS, DOB, CONTACT)
 *   - documentType: dropdown (filtered by changeType)
 *   - currentValue: text input
 *   - newValue: text input
 * 
 * Validation:
 *   - All fields required
 *   - customerId format: alphanumeric, max 20 chars
 *   - currentValue != newValue
 * 
 * State:
 *   - formData: CreateRequestData
 *   - errors: Record<string, string>
 *   - isValidating: boolean
 */
```

---

#### `frontend/src/components/staff/DocumentUploader.tsx`
```typescript
/**
 * DocumentUploader - File upload component with validation.
 * 
 * Props:
 *   requestId: string
 *   onUploadComplete: (response: UploadResponse) => void
 *   onError: (error: string) => void
 * 
 * Features:
 *   - Drag and drop support
 *   - File type validation (PDF, JPEG, PNG, TIFF)
 *   - File size validation (max 10MB)
 *   - Upload progress indicator
 *   - Preview for images
 * 
 * State:
 *   - file: File | null
 *   - uploadProgress: number (0-100)
 *   - isUploading: boolean
 *   - error: string | null
 */
```

---

### 3.2 Checker Workbench

#### `frontend/src/components/checker/QueueTable.tsx`
```typescript
/**
 * QueueTable - Displays pending requests for checker review.
 * 
 * Props:
 *   items: QueueItem[]
 *   onClaim: (requestId: string) => Promise<void>
 *   isLoading: boolean
 *   filters: QueueFilters
 *   onFilterChange: (filters: QueueFilters) => void
 * 
 * Columns:
 *   - Request ID (sortable)
 *   - Customer ID
 *   - Change Type
 *   - Risk Tier (color-coded badge)
 *   - AI Recommendation
 *   - Time in Queue
 *   - Actions (Claim button)
 * 
 * Features:
 *   - Filter by risk tier
 *   - Sort by columns
 *   - Pagination
 *   - Auto-refresh every 30s
 */
```

---

#### `frontend/src/components/checker/ReviewPanel.tsx`
```typescript
/**
 * ReviewPanel - Main review screen for a claimed request.
 * 
 * Props:
 *   request: RequestDetail
 *   onDecision: (decision: Decision, reason?: string) => Promise<void>
 *   onRelease: () => Promise<void>
 * 
 * Layout:
 *   ┌─────────────────────────────────────────────────┐
 *   │  Request Header (ID, Customer, Status)          │
 *   ├──────────────────────┬──────────────────────────┤
 *   │  Document Viewer     │  Right Panel:            │
 *   │  (PDF/Image preview) │  - AI Summary            │
 *   │                      │  - Confidence Scores     │
 *   │                      │  - Extracted Fields      │
 *   │                      │  - Flags & Alerts        │
 *   ├──────────────────────┴──────────────────────────┤
 *   │  Decision Buttons (Approve/Reject/More Info)    │
 *   └─────────────────────────────────────────────────┘
 * 
 * State:
 *   - activeTab: "summary" | "scores" | "fields" | "flags"
 *   - decisionReason: string (for reject/escalate)
 *   - isSubmitting: boolean
 */
```

---

#### `frontend/src/components/checker/ConfidenceScoreCard.tsx`
```typescript
/**
 * ConfidenceScoreCard - Visual display of confidence scores.
 * 
 * Props:
 *   scoreCard: ConfidenceScoreCard
 * 
 * Display:
 *   - Overall Score (large, color-coded)
 *   - Risk Tier Badge
 *   - Per-field scores with progress bars:
 *     - Old Name Match: ████████░░ 85%
 *     - New Name Match: █████████░ 92%
 *     - OCR Confidence: ████████░░ 88%
 *     - Doc Authenticity: ███████░░░ 75%
 *   - Score breakdown tooltip
 * 
 * Color Coding:
 *   - Green: >= 90%
 *   - Yellow: 70-89%
 *   - Red: < 70%
 */
```

---

#### `frontend/src/components/checker/DecisionButtons.tsx`
```typescript
/**
 * DecisionButtons - Action buttons for checker decision.
 * 
 * Props:
 *   onApprove: () => void
 *   onReject: (reason: string) => void
 *   onMoreInfo: (reason: string) => void
 *   onEscalate: (reason: string) => void
 *   isDisabled: boolean
 *   aiRecommendation: string
 * 
 * Buttons:
 *   - ✅ Approve (green, highlighted if AI recommends)
 *   - ❌ Reject (red, opens reason modal)
 *   - ❓ More Info (orange, opens reason modal)
 *   - ⬆️ Escalate (gray, opens reason modal)
 * 
 * Behavior:
 *   - Approve: immediate action
 *   - Others: open modal for mandatory reason
 *   - Confirm dialog before action
 */
```

---

## 4. Database Migrations

#### `backend/app/db/migrations/versions/001_initial.py`
```python
"""
Initial database schema migration.

Creates:
    - pending_requests table
    - audit_logs table
    - customers table (mock RPS)
    - checkers table
    - All indexes
"""

def upgrade():
    # Create enum types
    op.execute("""
        CREATE TYPE change_type AS ENUM ('LEGAL_NAME', 'ADDRESS', 'DOB', 'CONTACT');
        CREATE TYPE document_type AS ENUM ('MARRIAGE_CERTIFICATE', 'GAZETTE_NOTIFICATION', 
            'DEED_POLL', 'COURT_ORDER', 'UTILITY_BILL', 'LEASE_AGREEMENT', 
            'BIRTH_CERTIFICATE', 'PASSPORT', 'PAN_CARD', 'CONSENT_FORM');
        CREATE TYPE request_status AS ENUM ('INTAKE_RECEIVED', 'VALIDATED', 'QUEUED', 
            'PROCESSING', 'AI_VERIFIED_PENDING_HUMAN', 'IN_REVIEW', 'PENDING_INFO', 
            'ESCALATED', 'REPROCESSING', 'APPROVED', 'REJECTED', 'COMPLETED', 'FAILED');
        CREATE TYPE risk_tier AS ENUM ('LOW', 'MEDIUM', 'HIGH');
        CREATE TYPE forgery_result AS ENUM ('PASS', 'FLAG', 'FAIL');
        CREATE TYPE recommendation AS ENUM ('APPROVE', 'REJECT', 'MANUAL_REVIEW');
        CREATE TYPE decision AS ENUM ('APPROVE', 'REJECT', 'MORE_INFO', 'ESCALATE');
        CREATE TYPE actor_type AS ENUM ('SYSTEM', 'HUMAN', 'AI_AGENT');
        CREATE TYPE event_type AS ENUM ('STATE_CHANGE', 'HUMAN_ACTION', 'SYSTEM_EVENT', 'ERROR');
    """)
    
    # Create pending_requests table
    op.create_table(
        'pending_requests',
        sa.Column('request_id', sa.String(36), primary_key=True),
        sa.Column('idempotency_key', sa.String(64), unique=True),
        sa.Column('customer_id', sa.String(20), nullable=False),
        # ... all other columns from schema
    )
    
    # Create indexes
    op.create_index('idx_pending_status', 'pending_requests', ['status'])
    op.create_index('idx_pending_customer', 'pending_requests', ['customer_id'])
    op.create_index('idx_pending_risk_tier', 'pending_requests', ['risk_tier', 'status'])
    # ... other indexes
```

---

## 5. Configuration

#### `backend/app/config.py`
```python
"""
Application configuration using pydantic-settings.
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Categories:
        - App: General application settings
        - Database: PostgreSQL connection
        - Redis: Cache and queue
        - LLM: Claude API configuration
        - OCR: Tesseract/Google Vision
        - Storage: S3/local file storage
        - Security: Auth and CORS
    """
    
    # App
    APP_NAME: str = "IASW"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/iasw"
    DB_POOL_SIZE: int = 10
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # LLM
    ANTHROPIC_API_KEY: str
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.0
    
    # OCR
    TESSERACT_CMD: str = "/usr/bin/tesseract"
    GOOGLE_VISION_ENABLED: bool = True
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    
    # Storage
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    STORAGE_PATH: str = "./storage"
    S3_BUCKET: str = ""
    S3_REGION: str = ""
    
    # Security
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # Processing
    OCR_CONFIDENCE_THRESHOLD: float = 0.6
    FORGERY_PASS_THRESHOLD: float = 0.85
    FORGERY_FAIL_THRESHOLD: float = 0.60
    
    class Config:
        env_file = ".env"
```

---

## 6. API Contracts

### 6.1 Request Endpoints

#### POST `/api/v1/requests`
```json
// Request
{
  "customer_id": "C001",
  "change_type": "LEGAL_NAME",
  "document_type": "MARRIAGE_CERTIFICATE",
  "current_value": "Priya Sharma",
  "new_value": "Priya Mehta"
}

// Response (201 Created)
{
  "request_id": "REQ-12345",
  "status": "VALIDATED",
  "message": "Request created successfully. Please upload supporting document."
}

// Error Response (400 Bad Request)
{
  "error": "validation_failed",
  "details": [
    {"field": "customer_id", "message": "Customer not found in RPS"}
  ]
}
```

---

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

// Error Response (400 Bad Request)
{
  "error": "file_validation_failed",
  "details": "File size exceeds 10MB limit"
}
```

---

### 6.2 Checker Endpoints

#### GET `/api/v1/checker/queue`
```json
// Query params: ?risk_tier=HIGH&status=AI_VERIFIED_PENDING_HUMAN&page=1&limit=20

// Response (200 OK)
{
  "items": [
    {
      "request_id": "REQ-12345",
      "customer_id": "C001",
      "change_type": "LEGAL_NAME",
      "risk_tier": "LOW",
      "ai_recommendation": "APPROVE",
      "overall_score": 0.946,
      "flags": [],
      "queued_at": "2024-03-20T10:30:48Z",
      "time_in_queue_minutes": 15
    }
  ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

---

#### POST `/api/v1/checker/decide/{id}`
```json
// Request
{
  "decision": "APPROVE",
  "reason": null  // Required for REJECT/ESCALATE
}

// Response (200 OK)
{
  "request_id": "REQ-12345",
  "decision": "APPROVE",
  "new_status": "APPROVED",
  "rps_updated": true,
  "message": "Decision recorded. Core banking updated successfully."
}

// Response for REJECT
{
  "request_id": "REQ-12345",
  "decision": "REJECT",
  "new_status": "REJECTED",
  "rps_updated": false,
  "message": "Request rejected. Branch has been notified."
}
```

---

## 7. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `CUSTOMER_NOT_FOUND` | 404 | Customer ID not found in RPS |
| `DUPLICATE_REQUEST` | 409 | Active request exists for same customer + change type |
| `INVALID_DOCUMENT_TYPE` | 400 | Document type not allowed for change type |
| `FILE_TOO_LARGE` | 400 | File exceeds 10MB limit |
| `INVALID_FILE_FORMAT` | 400 | File is not PDF/JPEG/PNG/TIFF |
| `VIRUS_DETECTED` | 400 | File failed virus scan |
| `REQUEST_NOT_FOUND` | 404 | Request ID not found |
| `REQUEST_ALREADY_CLAIMED` | 409 | Request is locked by another checker |
| `LOCK_EXPIRED` | 409 | Checker's lock has expired |
| `REASON_REQUIRED` | 400 | Reason required for reject/escalate |
| `HITL_VIOLATION` | 403 | Non-human actor attempted restricted action |
| `PROCESSING_FAILED` | 500 | Document processing pipeline failed |

---

## 8. Observability

### 8.1 Logging Structure

```python
# Every log entry follows this structure
{
    "timestamp": "2024-03-20T10:30:45.123Z",
    "level": "INFO",
    "service": "iasw-backend",
    "request_id": "REQ-12345",  # Correlation ID
    "trace_id": "abc123",
    "span_id": "def456",
    "agent": "scorer",  # Which agent/component
    "step": "calculate_name_match",
    "duration_ms": 45,
    "status": "success",
    
    # Context (no PII)
    "customer_id_hash": "sha256:...",  # Hashed, not raw
    "change_type": "LEGAL_NAME",
    "risk_tier": "LOW",
    
    # Metrics
    "ocr_confidence": 0.92,
    "overall_score": 0.946,
    "llm_tokens": {"input": 1250, "output": 180},
    "llm_latency_ms": 890
}
```

---

### 8.2 LangSmith Integration

```python
# backend/app/agents/graph.py

from langsmith import traceable

class DocumentProcessingGraph:
    
    @traceable(name="process_document", run_type="chain")
    def invoke(self, state: ProcessingState) -> ProcessingState:
        """
        LangSmith traces the entire graph execution.
        
        Tracked:
            - Each node execution time
            - LLM calls with prompts and responses
            - Token usage per call
            - State at each step
            - Errors and retries
        """
        return self.graph.invoke(state)
```

---

This LLD provides complete implementation guidance. Ready to start coding?
