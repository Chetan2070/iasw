# IASW Architecture & Design Document

This document provides an overview of the system architecture, agent design, AI/ML implementation, and operational considerations for the Intelligent Account Servicing Workflow (IASW) system.

## Table of Contents

1. [System Design](#system-design)
2. [Agent Decomposition](#agent-decomposition)
3. [AI/ML Implementation](#aiml-implementation)
4. [Human-in-the-Loop Design](#human-in-the-loop-design)
5. [Observability & Operations](#observability--operations)
6. [Trade-offs & Design Decisions](#trade-offs--design-decisions)

---

## System Design

### High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend API   │────▶│   PostgreSQL    │
│   (Next.js)     │     │   (FastAPI)     │     │   Database      │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │   Celery       │
                        │   Worker       │
                        └────────┬───────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  LangGraph Pipeline    │
                    │  (Document Processing) │
                    └────────────────────────┘
                                 │
          ┌──────────┬──────────┼──────────┬──────────┐
          ▼          ▼          ▼          ▼          ▼
     ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
     │  OCR   │ │Classify│ │Extract │ │Forgery │ │ Score  │
     │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
     └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

### Component Responsibilities

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | Next.js 14, TypeScript | Staff portal, Checker workbench, Admin panel |
| API Gateway | FastAPI | REST API, request routing, authentication |
| Database | PostgreSQL + SQLAlchemy | Persistent storage, audit logs |
| Task Queue | Celery + Redis | Async document processing |
| AI Pipeline | LangGraph + Claude | Document verification workflow |
| Storage | Local filesystem (S3-ready) | Document storage |

### Request Flow

1. **Staff submits request** → Creates `PENDING` record
2. **Document upload** → Triggers Celery task
3. **LangGraph pipeline runs** → Sequential agent processing
4. **Results saved** → Status becomes `AI_VERIFIED_PENDING_HUMAN`
5. **Checker reviews** → Approves or rejects
6. **Final status** → `APPROVED` or `REJECTED`

---

## Agent Decomposition

### Architecture Choice: Supervisor-Worker Pattern

We implemented a **supervisor-worker architecture** using LangGraph where a supervisor orchestrates specialized agents:

```
┌─────────────────────────────────────────────────────┐
│                  SUPERVISOR                         │
│  (Routes tasks, handles errors, manages state)      │
└─────────────────────────────────────────────────────┘
          │           │           │           │
          ▼           ▼           ▼           ▼
     ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
     │   OCR   │ │Classifier│ │Extractor│ │ Forgery │
     │  Agent  │ │  Agent  │ │  Agent  │ │  Agent  │
     └─────────┘ └─────────┘ └─────────┘ └─────────┘
                                              │
                                              ▼
                                         ┌─────────┐
                                         │ Scorer  │
                                         │  Agent  │
                                         └─────────┘
```

### Agent Responsibilities

| Agent | Input | Output | Tools |
|-------|-------|--------|-------|
| **OCR Agent** | Document path | Extracted text, confidence | `extract_text_from_document`, `check_ocr_quality` |
| **Classifier Agent** | OCR text, declared type | Detected type, match flag | `analyze_document_keywords`, `determine_document_type` |
| **Extractor Agent** | OCR text, doc type | Old name, new name | `search_for_names`, `identify_name_roles`, LLM extraction |
| **Forgery Agent** | Document path | Forgery score (0-1), PASS/FLAG/FAIL | `analyze_metadata`, `run_ela`, `analyze_fonts` |
| **Scorer Agent** | All results, flags | Overall score, risk tier, recommendation | `calculate_name_similarity`, `calculate_overall_score` |

### Why This Architecture?

1. **Modularity**: Each agent can be tested, improved, or replaced independently
2. **Observability**: Clear boundaries for logging and debugging
3. **Scalability**: Agents can be parallelized for independent tasks
4. **Fault Isolation**: Agent failures don't crash the entire pipeline

---

## AI/ML Implementation

### Confidence Scoring Model

We use a weighted scoring formula that combines multiple signals:

```
overall_score = (
    name_match_weight × avg(old_name_score, new_name_score) +
    authenticity_weight × forgery_score +
    ocr_weight × ocr_confidence +
    extraction_weight × extraction_confidence
)

Default weights:
- name_match_weight = 0.40
- authenticity_weight = 0.30
- ocr_weight = 0.15
- extraction_weight = 0.15
```

### Risk Tier Determination

| Risk Tier | Condition | AI Recommendation |
|-----------|-----------|-------------------|
| **LOW** | score ≥ 0.90 AND no critical flags | APPROVE |
| **MEDIUM** | 0.70 ≤ score < 0.90 | MANUAL_REVIEW |
| **HIGH** | score < 0.70 OR critical flags | REJECT |

### Critical Flags That Force HIGH Risk

- `DOC_TYPE_MISMATCH` - Declared type doesn't match detected type
- `FORGERY_DETECTED` - Forgery score below threshold
- `EXTRACTION_FAILED` - Could not extract required names
- `NAME_SEVERE_MISMATCH` - Name similarity < 70%

### Forgery Detection

Multi-layer analysis approach:

1. **Metadata Analysis**
   - Check creation/modification timestamps
   - Detect editing software signatures
   - Verify producer metadata consistency

2. **Error Level Analysis (ELA)**
   - Detect compression artifacts from editing
   - Identify inconsistent JPEG quality regions
   - Flag potential paste operations

3. **Font Consistency**
   - Analyze character uniformity
   - Detect multiple font families
   - Check for kerning anomalies

### Prompt Design

Prompts are centralized in `app/agents/prompts/` for maintainability:

```
app/agents/prompts/
├── __init__.py          # Exports all prompts
├── agent_prompts.py     # ReAct agent system prompts
└── node_prompts.py      # Direct LLM call prompts
```

Key prompt design principles:
- **Explicit output format**: Always specify JSON structure
- **Context-aware**: Include document type hints
- **Confidence-based**: Request confidence scores for all extractions
- **Fallback-friendly**: Handle partial extraction gracefully

---

## Human-in-the-Loop Design

### Review Queue Architecture

```
                    ┌─────────────────────┐
                    │   AI Verification   │
                    │   (Async Pipeline)  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Review Queue     │
                    │ (Priority-Sorted)   │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
   │ HIGH Risk   │      │ MEDIUM Risk │      │  LOW Risk   │
   │ (First)     │      │ (Second)    │      │  (Last)     │
   └─────────────┘      └─────────────┘      └─────────────┘
```

### Checker Workflow

1. **View Queue**: See pending items sorted by risk tier
2. **Claim Item**: Lock for review (prevents conflicts)
3. **Review Details**: See document, AI analysis, confidence scores
4. **Make Decision**: APPROVE with reason or REJECT with reason
5. **Audit Log**: All decisions recorded with timestamp

### Key Design Choices

- **Always require human review**: Even HIGH confidence items need human sign-off
- **AI as assistant, not decider**: Recommendations, not auto-approvals
- **Clear audit trail**: Every decision is logged with reasoning
- **Claim-based workflow**: Prevents duplicate reviews

---

## Observability & Operations

### Logging Architecture

```python
# Structured logging with request context
logger.info(f"[{request_id}] Processing step: {step_name}")
logger.info(f"[{request_id}] OCR extracted {len(text)} chars, confidence: {conf:.2f}")
logger.error(f"[{request_id}] Extraction failed: {error}")
```

### Metrics Tracked

| Metric | Purpose |
|--------|---------|
| `request_processing_time` | Pipeline performance |
| `ocr_confidence_avg` | Document quality trend |
| `approval_rate` | Process efficiency |
| `ai_recommendation_accuracy` | AI calibration |
| `checker_override_rate` | Human vs AI alignment |

### Audit Trail

Every action is logged with:
- Timestamp (UTC)
- Actor (user/system)
- Action type
- Previous/new values
- Request context

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    request_id UUID REFERENCES requests(id),
    actor VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    old_value JSONB,
    new_value JSONB
);
```

### Error Handling

1. **Agent-level**: Errors return partial results with error flag
2. **Pipeline-level**: Failed pipelines set status to `PROCESSING_FAILED`
3. **Task-level**: Celery retries with exponential backoff
4. **System-level**: Dead letter queue for unrecoverable failures

---

## Trade-offs & Design Decisions

### 1. LangGraph vs Simple Sequential Processing

**Chose**: LangGraph with ReAct agents

**Reason**: Better observability, easier debugging, modularity for future improvements

**Trade-off**: More complexity, slight overhead

### 2. Sync Validation vs Full Async

**Chose**: Sync validation, async processing

**Reason**: Fast feedback for staff (< 500ms), no blocking for heavy AI work

**Trade-off**: Two-phase UX, need status polling

### 3. Single LLM vs Specialized Models

**Chose**: Single powerful LLM (Claude) for all tasks

**Reason**: Simpler deployment, consistent quality, good generalization

**Trade-off**: Higher per-request cost, dependency on single provider

### 4. Always Human Review vs Auto-Approve High Confidence

**Chose**: Always require human review

**Reason**: Regulatory compliance, liability, trust building

**Trade-off**: Higher operational cost, slower throughput

### 5. Risk-Based Prioritization

**Chose**: HIGH risk first in queue

**Reason**: Faster rejection of fraud, most impactful reviews first

**Trade-off**: LOW risk items wait longer (but these are safer to delay)

---

## Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| OCR failure | Retry with alternative engine, flag for manual review |
| Name not found | Partial extraction flag, checker sees raw document |
| Document type mismatch | High risk flag, requires justification |
| Forgery detected | Automatic REJECT recommendation |
| Duplicate request | Idempotency check at intake |
| Checker unavailable | Items remain in queue, no auto-timeout |
| Pipeline timeout | Retry once, then flag for manual review |

---

## Directory Structure

```
backend/
├── app/
│   ├── agents/               # LangGraph AI pipeline
│   │   ├── prompts/          # Centralized AI prompts
│   │   ├── nodes/            # Pipeline nodes (linear mode)
│   │   ├── specialized/      # Worker agents + supervisor
│   │   ├── graph.py          # Main pipeline definition
│   │   └── state.py          # Processing state schema
│   ├── api/                  # FastAPI routes
│   │   └── v1/               # Versioned API endpoints
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── workers/              # Celery async tasks
│   └── config.py             # Environment configuration
├── tests/                    # Pytest test suite
└── storage/                  # Document uploads
```

---

## Running the System

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Anthropic API key

### Quick Start
```bash
# Backend
cd backend
pip install -r requirements.txt
python seed_db.py
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Worker
cd backend
celery -A app.workers.celery_app worker -l info
```

### Testing
```bash
cd backend
pytest tests/ -v
```
