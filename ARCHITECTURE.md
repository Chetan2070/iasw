# IASW Architecture & Design Document

This document provides the complete system architecture, agent design, AI/ML implementation, and Human-in-the-Loop (HITL) design for the Intelligent Account Servicing Workflow (IASW) system.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Visual Architecture Diagrams](#3-visual-architecture-diagrams)
4. [Agent Design](#4-agent-design)
5. [AI/ML Implementation](#5-aiml-implementation)
6. [Human-in-the-Loop Design](#6-human-in-the-loop-design)
7. [Data Model](#7-data-model)
8. [Technology Stack Justification](#8-technology-stack-justification)
9. [Observability & Operations](#9-observability--operations)
10. [Trade-offs & Design Decisions](#10-trade-offs--design-decisions)

---

## 1. Executive Summary

### 1.1 What is IASW?

The **Intelligent Account Servicing Workflow (IASW)** is an AI-powered document verification system that automates the processing of customer account change requests for banks. When a customer wants to change their legal name on their bank account (e.g., after marriage), they must submit supporting documents like a marriage certificate. IASW uses AI to verify these documents, extract relevant information, detect potential forgery, and route requests to human checkers for final approval.

### 1.2 The Problem It Solves

**Before IASW:**
- Bank staff manually review each document (time-consuming)
- Inconsistent verification quality across different staff members
- No systematic forgery detection
- Paper-based audit trails prone to gaps
- High operational cost per request

**After IASW:**
- AI pre-processes documents and extracts key fields automatically
- Consistent verification using multi-layer analysis (OCR, forgery detection, name matching)
- Human checkers focus on decision-making, not data extraction
- Complete digital audit trail with tamper detection
- Risk-based routing ensures high-risk cases get senior review

### 1.3 Core Principle

**"AI assists, humans decide."** The system never auto-approves requests. Every change to a customer's bank account requires explicit human approval. AI provides recommendations and analysis; humans make the final call.

### 1.4 Scope

**In Scope (Current Implementation):**
- Legal Name Change requests
- Supporting documents: Marriage Certificate, Gazette Notification, Deed Poll, Court Order
- Document ingestion, OCR, classification, field extraction
- Multi-layer forgery detection
- Confidence scoring and risk-based routing
- Human checker review workflow
- Complete audit trail

**Out of Scope (Future Phases):**
- Other account servicing requests (address change, KYC refresh)
- Customer self-service portal
- External government API verification

---

## 2. System Architecture

### 2.1 Architecture Overview

The system is organized into four distinct layers, each with clear boundaries and responsibilities. See [Diagram 1](#diagram-1-high-level-system-architecture) in the Visual Architecture Diagrams section for the complete overview.

### 2.2 Boundary Summary

| Boundary | Type | What Happens |
|----------|------|--------------|
| Intake → Processing | **ASYNC** | Staff get a reference number and are released. Heavy AI processing happens in background. |
| Processing → Review | **STAGING** | AI writes results to database with status `AI_VERIFIED_PENDING_HUMAN`. Request enters checker queue. |
| Review → Integration | **HITL GATE** | Human checker must approve. Only human approval can trigger core banking update. |

### 2.3 Component Responsibilities

| Component | Technology | What It Does |
|-----------|------------|--------------|
| **Staff Portal** | Next.js 14, TypeScript | Web interface for bank staff to submit change requests and upload documents |
| **Checker Workbench** | Next.js 14, TypeScript | Web interface for checkers to review AI analysis and make approve/reject decisions |
| **API Gateway** | FastAPI (Python) | REST API handling authentication, routing, and business logic |
| **Task Queue** | Celery + Redis | Manages async document processing with retry logic |
| **AI Pipeline** | LangGraph + Claude | Orchestrates AI agents for document verification |
| **Database** | PostgreSQL + SQLAlchemy | Stores requests, audit logs, customer data |
| **Document Storage** | Local filesystem | Stores uploaded documents |

---

## 3. Visual Architecture Diagrams

> **Comprehensive visual system design reference**

### Table of Contents

| # | Diagram | Purpose | Best For |
|---|---------|---------|----------|
| [1](#diagram-1-high-level-system-architecture) | **High-Level System Architecture** | 4-layer overview | First-time viewers, executive summary |
| [2](#diagram-2-supervisor-worker-agent-architecture) | **Supervisor-Worker Architecture** | Agent orchestration | AI pipeline deep dive |
| [3](#diagram-3-langgraph-pipeline-with-conditional-routing) | **LangGraph Pipeline** | Processing flow with routing | Implementation details |
| [4](#diagram-4-forgery-detection-multi-layer) | **Forgery Detection** | 4-layer security analysis | Security review |
| [5](#diagram-5-confidence-scoring-model) | **Confidence Scoring** | Score calculation logic | Quality assurance |
| [6](#diagram-6-human-in-the-loop-boundaries) | **HITL Boundaries** | AI vs Human zones | Compliance & governance |
| [7](#diagram-7-database-schema-erd) | **Database Schema** | Entity relationships | Database design |
| [8](#diagram-8-checker-workflow-sequence) | **Checker Workflow** | Human review process | User training |
| [9](#diagram-9-real-time-processing-updates) | **Real-Time Updates** | Polling mechanism | Performance optimization |

---

### Diagram 1: High-Level System Architecture

**Purpose:** Shows the complete 4-layer architecture with clear boundaries  
**Key Insight:** Async boundary after intake, HITL gate before integration

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#EEF2FF',
    'primaryTextColor': '#1e1b4b',
    'primaryBorderColor': '#6366f1',
    'lineColor': '#6366f1',
    'secondaryColor': '#f0fdf4',
    'tertiaryColor': '#faf5ff',
    'background': '#ffffff',
    'mainBkg': '#EEF2FF',
    'nodeBorder': '#6366f1',
    'clusterBkg': '#f8fafc',
    'clusterBorder': '#cbd5e1',
    'titleColor': '#1e1b4b',
    'edgeLabelBackground': '#ffffff',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif'
  }
}}%%
graph TB
    subgraph INTAKE["🔵 INTAKE LAYER synchronous"]

        SP["**Staff Portal**<br/>Next.js"]
        IS["**Intake Service**<br/>FastAPI"]
        VA["**Validation Agent**<br/>Schema + rules"]
        SP -->|Submit request| IS
        IS -->|Validate| VA
    end

    subgraph PROCESSING["🟢 PROCESSING LAYER  asynchronous"]
        CW["**Celery Worker**<br/>Task dispatcher"]
        DP["**Doc Processor**<br/>Normalise + store"]
        LG["**LangGraph**<br/>Orchestrator"]

        VA -.->|Queue task| CW
        CW --> DP
        DP --> LG

        subgraph PIPELINE["AI Pipeline · sequential"]
            META["Metadata<br/>agent"]
            OCR["OCR<br/>agent"]
            CLASS["Classifier<br/>agent"]
            EXTR["Extractor<br/>agent"]
            FORG["Forgery<br/>agent"]
            SCORE["Scorer<br/>agent"]
            SUMM["Summary<br/>agent"]

            META --> OCR --> CLASS --> EXTR --> FORG --> SCORE --> SUMM
        end

        LG --> META
    end

    subgraph REVIEW["🟡 REVIEW LAYER · human-gated"]
        CW2["**Checker Workbench**<br/>Next.js"]
        RS["**Review Service**<br/>JWT protected"]
        DE["**Decision Engine**<br/>State machine"]

        SUMM -.->|Stage result| DB[(PostgreSQL)]
        DB -->|Queue item| CW2
        CW2 -->|Claim / decide| RS
        RS --> DE
    end

    subgraph INTEGRATION["🔴 INTEGRATION LAYER · human-triggered"]
        RPS["**RPS**<br/>Core banking"]
        FN["**FileNet**<br/>Document store"]
        NS["**Notifications**<br/>Email / SMS"]

        DE -->|Approved| RPS
        DE -->|Archive| FN
        DE -->|Notify| NS
    end

    subgraph INFRA["⚙️ INFRASTRUCTURE"]
        DB
        REDIS[(Redis<br/>Task queue)]
        STORE[("Object Store<br/>S3 / filesystem")]
    end

    CW -.->|Enqueue| REDIS
    IS --> STORE
    LG -.->|Read doc| STORE

    style INTAKE fill:#eff6ff,stroke:#93c5fd,color:#1e3a5f
    style PROCESSING fill:#f0fdf4,stroke:#86efac,color:#14532d
    style PIPELINE fill:#faf5ff,stroke:#c4b5fd,color:#3b0764
    style REVIEW fill:#fefce8,stroke:#fde047,color:#713f12
    style INTEGRATION fill:#fff1f2,stroke:#fda4af,color:#881337
    style INFRA fill:#f8fafc,stroke:#cbd5e1,color:#334155
    style DB fill:#dbeafe,stroke:#93c5fd,color:#1e3a5f
    style REDIS fill:#dbeafe,stroke:#93c5fd,color:#1e3a5f
    style STORE fill:#dbeafe,stroke:#93c5fd,color:#1e3a5f
```

**Key Components:**
- **Intake Layer:** Synchronous validation, then staff released
- **Processing Layer:** Async AI pipeline, 7 specialized agents
- **Review Layer:** Human checkpoint, JWT-protected
- **Integration Layer:** Only triggered by human approval

---

### Diagram 2: Supervisor-Worker Agent Architecture

**Purpose:** Shows how supervisor orchestrates 7 specialized worker agents  
**Key Insight:** Clean separation of concerns, each worker has specific tools

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#fdf4ff',
    'primaryTextColor': '#3b0764',
    'primaryBorderColor': '#a855f7',
    'lineColor': '#a855f7',
    'secondaryColor': '#eff6ff',
    'tertiaryColor': '#f0fdf4',
    'background': '#ffffff',
    'clusterBkg': '#fdf4ff',
    'clusterBorder': '#d8b4fe',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif',
    'edgeLabelBackground': '#fdf4ff'
  }
}}%%
graph TB
    subgraph SUPERVISOR["🟣 SUPERVISOR"]
        SUP["**Supervisor**<br/>Orchestrator"]
        PLAN["**Planning engine**"]
        ROUTE["**Routing logic**"]
        STATE["**State manager**"]
        SUP --> PLAN --> ROUTE --> STATE
    end

    subgraph ANALYSIS["🔵 Document analysis workers"]
        W1["**Metadata worker**<br/>PDF / image analysis"]
        W2["**OCR worker**<br/>Tesseract + Google Vision"]
        W3["**Classifier worker**<br/>Document type detection"]
    end

    subgraph EXTRACTION["🟢 Extraction workers"]
        W4["**Extractor worker**<br/>Field extraction"]
        W5["**Forgery worker**<br/>Multi-layer detection"]
    end

    subgraph SYNTHESIS["🟡 Synthesis workers"]
        W6["**Scorer worker**<br/>Confidence calculation"]
        W7["**Summary worker**<br/>Report generation"]
    end

    STATE -->|Task 1| W1
    STATE -->|Task 2| W2
    STATE -->|Task 3| W3
    STATE -->|Task 4| W4
    STATE -->|Task 5| W5
    STATE -->|Task 6| W6
    STATE -->|Task 7| W7

    W1 & W2 & W3 & W4 & W5 & W6 & W7 -.->|Result| STATE

    subgraph TOOLS["🔧 Tools & services"]
        PYMUPDF["PyMuPDF"]
        TESS["Tesseract OCR"]
        GV["Google Vision API"]
        LLM["Claude 3.5 Sonnet"]
        ELA["ELA analyser"]
        FONT["Font checker"]
        ML["ML model"]
    end

    W1 --> PYMUPDF
    W2 --> TESS & GV
    W3 & W4 & W6 & W7 --> LLM
    W5 --> ELA & FONT & ML

    style SUPERVISOR fill:#fdf4ff,stroke:#d8b4fe,color:#3b0764
    style ANALYSIS fill:#eff6ff,stroke:#93c5fd,color:#1e3a5f
    style EXTRACTION fill:#f0fdf4,stroke:#86efac,color:#14532d
    style SYNTHESIS fill:#fefce8,stroke:#fde047,color:#713f12
    style TOOLS fill:#f8fafc,stroke:#cbd5e1,color:#334155
```

**Worker Responsibilities:**
- **Analysis:** Metadata extraction, OCR, document classification
- **Extraction:** Field extraction, forgery detection
- **Synthesis:** Score calculation, summary generation

---

### Diagram 3: LangGraph Pipeline with Conditional Routing

**Purpose:** Detailed processing flow with decision points  
**Key Insight:** Fallback OCR when confidence low, skip forgery on type mismatch

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#f0f9ff',
    'primaryTextColor': '#0c4a6e',
    'primaryBorderColor': '#0ea5e9',
    'lineColor': '#64748b',
    'background': '#ffffff',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif',
    'edgeLabelBackground': '#f8fafc'
  }
}}%%
graph TD
    START(["▶ Start"]) --> VALIDATE{"Validate<br/>document"}

    VALIDATE -->|Pass| METADATA["**Extract metadata**<br/>PDF dates · software · EXIF"]
    VALIDATE -->|Fail| END_FAIL(["✖ Validation failed"])

    METADATA --> OCR["**Run OCR**<br/>Tesseract"]

    OCR --> CHECK_OCR{"OCR<br/>confidence<br/>≥ 60%?"}
    CHECK_OCR -->|Yes| CLASSIFY
    CHECK_OCR -->|No| FALLBACK["**Fallback OCR**<br/>Google Vision"]
    FALLBACK --> CLASSIFY["**Classify document**<br/>Marriage cert · Gazette · etc.<br/><br/>Compare with declared type"]

    CLASSIFY --> CHECK_TYPE{"Declared type<br/>matches<br/>detected type?"}
    
    CHECK_TYPE -->|✓ Match| EXTRACT_MATCH["**Extract fields**<br/>Use declared type schema<br/>Old name · new name · date"]
    CHECK_TYPE -->|✗ Mismatch| FLAG_TYPE["⚠ Flag: DOC_TYPE_MISMATCH<br/>Set risk tier = HIGH"]
    
    FLAG_TYPE --> EXTRACT_BEST["**Extract fields (best effort)**<br/>Try both declared & detected schemas<br/>Return what we can find"]
    
    EXTRACT_MATCH --> FORGERY["**Forgery detection**<br/>Type-specific checks:<br/>• Metadata analysis<br/>• ELA<br/>• Font consistency<br/>• ML model"]
    
    EXTRACT_BEST --> SKIP_FORGERY["⚠ Skip forgery detection<br/>Reason: Type mismatch makes<br/>forgery checks unreliable"]
    
    FORGERY --> SCORER["**Calculate scores**<br/>• Name match (Jaro-Winkler)<br/>• OCR confidence<br/>• Extraction confidence<br/>• Forgery score<br/>• Overall weighted score"]
    
    SKIP_FORGERY --> SCORER_ADJUSTED["**Calculate scores (adjusted)**<br/>• Name match (Jaro-Winkler)<br/>• OCR confidence<br/>• Extraction confidence<br/>• Forgery score = 0.0 (N/A)<br/>• Force risk tier = HIGH<br/>• Add flag: FORGERY_SKIPPED"]

    SCORER --> CHECK_RISK{"Risk<br/>tier<br/>(calculated)"}
    SCORER_ADJUSTED --> FORCE_HIGH["Risk tier = HIGH<br/>(forced due to mismatch)"]
    
    CHECK_RISK -->|LOW| SUMM_LOW["**Generate summary**<br/>Recommendation: APPROVE<br/>Confidence: High"]
    CHECK_RISK -->|MEDIUM| SUMM_MED["**Generate summary**<br/>Recommendation: MANUAL_REVIEW<br/>Confidence: Medium"]
    CHECK_RISK -->|HIGH| SUMM_HIGH["**Generate summary**<br/>Recommendation: REJECT<br/>Confidence: Low"]
    
    FORCE_HIGH --> SUMM_REJECT["**Generate summary**<br/>Recommendation: REJECT<br/>Reason: Document type mismatch<br/>Declared: {declared_type}<br/>Detected: {detected_type}"]

    SUMM_LOW & SUMM_MED & SUMM_HIGH & SUMM_REJECT --> SAVE["**Save to database**<br/>Status: AI_VERIFIED_PENDING_HUMAN<br/>Store all flags and scores"]
    
    SAVE --> NOTIFY["**Notify UI**<br/>Real-time step update<br/>current_processing_step = NULL"]
    
    NOTIFY --> END_OK(["✔ AI complete<br/>Ready for human review"])

    style START fill:#dcfce7,stroke:#86efac,color:#14532d
    style END_OK fill:#dcfce7,stroke:#86efac,color:#14532d
    style END_FAIL fill:#fff1f2,stroke:#fda4af,color:#881337
    style CHECK_OCR fill:#fefce8,stroke:#fde047,color:#713f12
    style CHECK_TYPE fill:#fefce8,stroke:#fde047,color:#713f12
    style CHECK_RISK fill:#fefce8,stroke:#fde047,color:#713f12
    style FLAG_TYPE fill:#fff1f2,stroke:#fda4af,color:#881337
    style SKIP_FORGERY fill:#fff7ed,stroke:#fdba74,color:#7c2d12
    style FORCE_HIGH fill:#fff1f2,stroke:#fda4af,color:#881337
    style FORGERY fill:#fff7ed,stroke:#fdba74,color:#7c2d12
    style SUMM_LOW fill:#dcfce7,stroke:#86efac,color:#14532d
    style SUMM_MED fill:#fefce8,stroke:#fde047,color:#713f12
    style SUMM_HIGH fill:#fff1f2,stroke:#fda4af,color:#881337
    style SUMM_REJECT fill:#fff1f2,stroke:#fda4af,color:#881337
    style EXTRACT_BEST fill:#fef3c7,stroke:#fbbf24,color:#78350f
    style SCORER_ADJUSTED fill:#fef3c7,stroke:#fbbf24,color:#78350f
```

**Decision Points:**
- **OCR < 60%:** Fallback to Google Vision API
- **Type mismatch:** Skip forgery detection, flag for manual review
- **Risk tier:** LOW → APPROVE, MEDIUM → MANUAL_REVIEW, HIGH → REJECT

---

### Diagram 4: Forgery Detection Multi-Layer

**Purpose:** 4-layer security analysis with weighted aggregation  
**Key Insight:** Combined score from metadata (20%), ELA (30%), fonts (20%), ML (30%)

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#fff7ed',
    'primaryTextColor': '#431407',
    'primaryBorderColor': '#fb923c',
    'lineColor': '#64748b',
    'background': '#ffffff',
    'clusterBkg': '#fff7ed',
    'clusterBorder': '#fdba74',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif'
  }
}}%%
graph TB
    INPUT(["📄 Document file"]) --> DISPATCH["**Forgery dispatcher**<br/>asyncio.gather — all layers parallel"]

    DISPATCH --> L1 & L2 & L3 & L4

    subgraph L1["🔵 Layer 1 · Metadata (20 %)"]
        M1["Extract PDF metadata<br/>or EXIF via getexif()"]
        M2["Parse D: dates<br/>creation vs mod"]
        M3["Check producer software<br/>expanded signatures list"]
        M4["Penalise from<br/>metadata_flags cache"]
        M1 --> M2 --> M3 --> M4 --> S1["Score 0 – 1"]
    end

    subgraph L2["🟠 Layer 2 · ELA (30 %)"]
        E1["Skip PNG — lossless,<br/>ELA unreliable"]
        E2["Re-save JPEG at 90 %<br/>unique temp path per request"]
        E3["All pages analysed<br/>not just first page"]
        E4["std_diff vs per-doc<br/>baseline — not hardcoded 50"]
        E1 --> E2 --> E3 --> E4 --> S2["Score 0 – 1<br/>worst page wins"]
    end

    subgraph L3["🟢 Layer 3 · Fonts (20 %)"]
        F1["Extract font names<br/>from all PDF pages"]
        F2["Deduplicate to<br/>base font families"]
        F3["Apply per-doc threshold<br/>ID=2, slip=3, invoice=4"]
        F4["Flag if base families<br/>exceed threshold"]
        F1 --> F2 --> F3 --> F4 --> S3["Score 0 – 1"]
    end

    subgraph L4["🟡 Layer 4 · ML (30 %)"]
        ML1["Render doc to<br/>224×224 image"]
        ML2["EfficientNet-B0<br/>pretrained ImageNet"]
        ML3["Softmax over<br/>2 classes"]
        ML4["SHA-256 hash<br/>for audit trail"]
        ML1 --> ML2 --> ML3 --> ML4 --> S4["Score 0 – 1<br/>authentic probability"]
    end

    S1 & S2 & S3 & S4 --> AGG["**Weighted aggregation**<br/>meta×0.2 + ela×0.3 + font×0.2 + ml×0.3"]

    AGG --> FINAL{"Final<br/>score"}
    FINAL -->|"≥ 0.75"| PASS["✔ PASS<br/>Likely authentic"]
    FINAL -->|"0.50 – 0.75"| FLAG["⚑ FLAG<br/>Manual review"]
    FINAL -->|"< 0.50"| FAIL["✖ FAIL<br/>Likely forged"]

    style PASS fill:#dcfce7,stroke:#86efac,color:#14532d
    style FLAG fill:#fefce8,stroke:#fde047,color:#713f12
    style FAIL fill:#fff1f2,stroke:#fda4af,color:#881337
    style L1 fill:#eff6ff,stroke:#93c5fd,color:#1e3a5f
    style L2 fill:#fff7ed,stroke:#fdba74,color:#7c2d12
    style L3 fill:#f0fdf4,stroke:#86efac,color:#14532d
    style L4 fill:#fefce8,stroke:#fde047,color:#713f12
```

**Layer Weights:**
- **Metadata (20%):** PDF `D:` date parsing, `getexif()` public API, expanded software signatures, reuses `metadata_flags` cache from parallel metadata node
- **ELA (30%):** Skips PNG (lossless), unique temp path per request prevents race conditions, all PDF pages analysed, per-document-type baseline replaces hardcoded `50.0`
- **Fonts (20%):** Deduplicates to base font families (Arial-Bold → Arial), per-document-type threshold (ID card=2, salary slip=3, invoice=4)
- **ML Model (30%):** Real EfficientNet-B0 replacing simulated heuristics, softmax authentic probability, SHA-256 hash for audit trail

**Thresholds:**
- **≥ 0.75:** PASS (Likely authentic)
- **0.50 – 0.75:** FLAG (Requires manual review)
- **< 0.50:** FAIL (Likely forged)

---

### Diagram 5: Confidence Scoring Model

**Purpose:** Weighted formula for overall confidence score  
**Key Insight:** Name matching (40%) most important, then forgery (30%)

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#f8fafc',
    'primaryTextColor': '#0f172a',
    'primaryBorderColor': '#64748b',
    'lineColor': '#64748b',
    'background': '#ffffff',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif',
    'edgeLabelBackground': '#f8fafc'
  }
}}%%
graph LR
    subgraph SIGNALS["📥 Input signals"]
        S1["Old name match<br/>*Jaro-Winkler* · 20 %"]
        S2["New name match<br/>*Jaro-Winkler* · 20 %"]
        S3["OCR confidence<br/>*Tesseract* · 15 %"]
        S4["Extraction confidence<br/>*LLM certainty* · 15 %"]
        S5["Forgery score<br/>*Multi-layer* · 30 %"]
    end

    S1 & S2 & S3 & S4 & S5 --> SUM["**Weighted sum**<br/>Overall score 0 – 1"]

    SUM --> CHECK{"Score<br/>& flags"}

    CHECK -->|"≥ 0.90<br/>no critical flags"| LOW["🟢 LOW risk<br/>Standard queue"]
    CHECK -->|"0.70 – 0.90"| MED["🟡 MEDIUM risk<br/>Highlighted"]
    CHECK -->|"< 0.70<br/>or critical flags"| HIGH["🔴 HIGH risk<br/>Senior checker"]

    LOW --> R1{"Score ≥ 0.85<br/>name ≥ 0.95<br/>forgery = PASS?"}
    MED --> R2["Recommend:<br/>MANUAL REVIEW"]
    HIGH --> R3["Recommend:<br/>REJECT"]
    R1 -->|Yes| R1A["Recommend:<br/>APPROVE"]
    R1 -->|No| R2

    style LOW fill:#dcfce7,stroke:#86efac,color:#14532d
    style MED fill:#fefce8,stroke:#fde047,color:#713f12
    style HIGH fill:#fff1f2,stroke:#fda4af,color:#881337
    style R1A fill:#dcfce7,stroke:#86efac,color:#14532d
    style R2 fill:#fefce8,stroke:#fde047,color:#713f12
    style R3 fill:#fff1f2,stroke:#fda4af,color:#881337
```

**Scoring Formula:**
```
overall_score = 
    0.20 × old_name_match +
    0.20 × new_name_match +
    0.15 × ocr_confidence +
    0.15 × extraction_confidence +
    0.30 × forgery_score
```

**Risk Tiers:**
- **LOW (≥ 0.90):** Standard queue
- **MEDIUM (0.70-0.90):** Highlighted in queue
- **HIGH (< 0.70 OR critical flags):** Senior checker queue

**AI Recommendations:**
- **APPROVE:** Score ≥ 0.85, name ≥ 0.95, forgery = PASS
- **MANUAL_REVIEW:** Score 0.60-0.85 or any MEDIUM flag
- **REJECT:** Score < 0.60 or forgery = FAIL

---

### Diagram 6: Human-in-the-Loop Boundaries

**Purpose:** Shows AI autonomous zone vs human-gated operations  
**Key Insight:** Hard boundary enforced by 4 mechanisms (state machine, JWT, actor validation, audit)

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#eff6ff',
    'primaryTextColor': '#1e3a5f',
    'primaryBorderColor': '#60a5fa',
    'lineColor': '#64748b',
    'background': '#ffffff',
    'clusterBkg': '#f8fafc',
    'clusterBorder': '#cbd5e1',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif'
  }
}}%%
graph TB
    subgraph AI_ZONE["🤖 AI ZONE — autonomous"]
        AI1["Request intake & validation"]
        AI2["Document upload & storage"]
        AI3["OCR & text extraction"]
        AI4["Document classification"]
        AI5["Field extraction"]
        AI6["Forgery detection"]
        AI7["Confidence scoring"]
        AI8["Summary generation"]
        AI9["Queue routing by risk"]
        AI1 --> AI2 --> AI3 --> AI4 --> AI5 --> AI6 --> AI7 --> AI8 --> AI9
    end

    GATE["🚧 HITL BOUNDARY<br/>AI cannot proceed past this point"]

    AI9 --> GATE

    subgraph HUMAN_ZONE["👤 HUMAN ZONE — gated"]
        H1["View AI analysis"]
        H2["Review document"]
        H3["Verify extracted data"]
        H4["Check forgery signals"]
        H5{"Human decision"}
        H6["✔ APPROVE with comment"]
        H7["✖ REJECT with reason"]
        H8["ℹ REQUEST MORE INFO"]
        H9["⬆ ESCALATE to senior"]

        GATE --> H1 --> H2 --> H3 --> H4 --> H5
        H5 -->|Approve| H6
        H5 -->|Reject| H7
        H5 -->|Need info| H8
        H5 -->|Escalate| H9
    end

    subgraph INTEGRATION_ZONE["🔗 INTEGRATION ZONE — human-triggered only"]
        I1["Update core banking (RPS)"]
        I2["Archive to FileNet"]
        I3["Send notifications"]
        I4["Write audit log"]

        H6 --> I1 & I2
        H7 --> I4
        I1 --> I3
    end

    subgraph ENFORCEMENT["🔒 Enforcement mechanisms"]
        E1["State machine guard<br/>APPROVED / REJECTED only from IN_REVIEW"]
        E2["JWT authentication<br/>Checker role required"]
        E3["Actor validation<br/>actor_type must be HUMAN"]
        E4["Audit trail<br/>Every action logged with actor"]
    end

    GATE -.->|enforced by| E1 & E2 & E3 & E4

    style GATE fill:#dc2626,stroke:#991b1b,color:#ffffff
    style AI_ZONE fill:#eff6ff,stroke:#93c5fd,color:#1e3a5f
    style HUMAN_ZONE fill:#fefce8,stroke:#fde047,color:#713f12
    style INTEGRATION_ZONE fill:#f0fdf4,stroke:#86efac,color:#14532d
    style ENFORCEMENT fill:#f8fafc,stroke:#cbd5e1,color:#334155
    style H6 fill:#dcfce7,stroke:#86efac,color:#14532d
    style H7 fill:#fff1f2,stroke:#fda4af,color:#881337
```

**HITL Enforcement:**
1. **State Machine Guard:** APPROVED/REJECTED only from IN_REVIEW
2. **JWT Authentication:** Checker role required for review endpoints
3. **Actor Validation:** `actor_type` must be HUMAN for final decisions
4. **Audit Trail:** Every action logged with actor identity

**What AI Cannot Do:**
- ❌ Approve requests
- ❌ Reject requests
- ❌ Update core banking (RPS)
- ❌ Make final decisions

---

### Diagram 7: Database Schema (ERD)

**Purpose:** Entity relationships and key fields  
**Key Insight:** JSONB for flexible metadata, comprehensive audit trail

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#f0f9ff',
    'primaryTextColor': '#0c4a6e',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#38bdf8',
    'background': '#ffffff',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif'
  }
}}%%
erDiagram
    CUSTOMERS ||--o{ REQUESTS : "has"
    REQUESTS ||--o{ AUDIT_LOGS : "logs"

    CUSTOMERS {
        varchar customer_id PK
        varchar account_number UK
        varchar legal_name
        date    date_of_birth
        text    address
        varchar phone
        varchar email
        timestamp created_at
        timestamp updated_at
    }

    REQUESTS {
        varchar  request_id PK
        varchar  idempotency_key UK
        varchar  customer_id FK
        varchar  change_type
        varchar  document_type
        varchar  requested_old_value
        varchar  requested_new_value
        varchar  extracted_old_value
        varchar  extracted_new_value
        jsonb    extraction_metadata
        decimal  old_name_match_score
        decimal  new_name_match_score
        decimal  ocr_confidence
        decimal  extraction_confidence
        decimal  doc_authenticity_score
        decimal  overall_confidence
        decimal  forgery_score
        varchar  forgery_result
        jsonb    forgery_details
        varchar  risk_tier
        jsonb    flags
        varchar  ai_recommendation
        text     ai_summary
        varchar  document_storage_path
        varchar  filenet_staging_id
        varchar  filenet_permanent_id
        varchar  status
        varchar  current_processing_step
        varchar  assigned_checker
        timestamp checker_lock_until
        varchar  checker_decision
        text     checker_decision_reason
        timestamp created_at
        timestamp decided_at
        timestamp completed_at
    }

    AUDIT_LOGS {
        uuid      id PK
        varchar   request_id FK
        varchar   event_type
        varchar   actor_type
        varchar   actor_id
        varchar   agent_name
        varchar   agent_version
        varchar   llm_model
        varchar   previous_state
        varchar   new_state
        jsonb     action_details
        jsonb     record_snapshot
        timestamp timestamp
        varchar   checksum
    }
```

**Key Indexes:**
- `idx_requests_status` on `status`
- `idx_requests_risk_tier` on `(risk_tier, status)`
- `idx_requests_checker` on `(assigned_checker, status)`
- `idx_audit_request` on `request_id`
- `idx_audit_timestamp` on `timestamp`

---

### Diagram 8: Checker Workflow Sequence

**Purpose:** Complete checker interaction flow from queue to decision  
**Key Insight:** 15-min lock, override detection, RPS update on approval

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#f0f9ff',
    'primaryTextColor': '#0c4a6e',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#64748b',
    'background': '#ffffff',
    'actorBkg': '#eff6ff',
    'actorBorder': '#60a5fa',
    'actorTextColor': '#1e3a5f',
    'activationBkgColor': '#dbeafe',
    'activationBorderColor': '#60a5fa',
    'noteBkgColor': '#fefce8',
    'noteBorderColor': '#fde047',
    'noteTextColor': '#713f12',
    'loopTextColor': '#1e3a5f',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif'
  }
}}%%
sequenceDiagram
    actor C as Checker
    participant UI as Checker workbench
    participant API as Review service
    participant DB as PostgreSQL
    participant RPS as Core banking
    participant AL as Audit log

    Note over C,AL: Checker authenticates with JWT

    C->>UI: Navigate to queue
    UI->>API: GET /api/v1/checker/queue
    API->>DB: SELECT requests WHERE status = 'AI_VERIFIED_PENDING_HUMAN'
    DB-->>API: Queue items
    API-->>UI: List with AI recommendations
    UI-->>C: Display queue (sorted by risk tier)

    Note over C,AL: Checker selects a request

    C->>UI: Click "Claim" on REQ-12345
    UI->>API: POST /checker/claim/REQ-12345
    API->>DB: BEGIN — SELECT FOR UPDATE

    alt Already claimed
        DB-->>API: lock not expired
        API-->>UI: 409 Conflict
        UI-->>C: "Another checker is reviewing"
    else Available
        API->>DB: UPDATE — assign checker, lock 15 min, status = IN_REVIEW
        API->>AL: Log HUMAN_ACTION: claimed
        API-->>UI: 200 OK — claimed for 15 min
        UI-->>C: Show review screen
    end

    Note over C,AL: Checker reviews document and AI analysis

    UI->>API: GET /requests/REQ-12345
    API->>DB: SELECT full request
    DB-->>API: Request + AI summary + scores
    API-->>UI: Full detail
    UI-->>C: Document viewer + analysis panel

    Note over C,AL: Checker makes a decision

    alt Approve
        C->>UI: Click "Approve"
        UI->>API: POST /checker/decide/REQ-12345 · decision=APPROVE
        API->>DB: UPDATE — status = APPROVED
        API->>RPS: Update customer legal name
        RPS-->>API: Name updated
        API->>DB: UPDATE — status = COMPLETED
        API->>AL: Log HUMAN_ACTION: approved by checker_jane
        API-->>UI: 200 OK
        UI-->>C: Success
    else Reject
        C->>UI: Click "Reject" + enter reason
        UI->>API: POST /checker/decide/REQ-12345 · decision=REJECT
        API->>DB: UPDATE — status = REJECTED + reason
        API->>AL: Log HUMAN_ACTION: rejected
        API-->>UI: 200 OK
        UI-->>C: Request rejected
    end

    Note over C,AL: Override detection

    alt AI said APPROVE, human said REJECT
        API->>AL: Log AI_TOO_LENIENT
    else AI said REJECT, human said APPROVE
        API->>AL: Log AI_TOO_STRICT
    end
```

**Workflow Steps:**
1. **View Queue:** Sorted by risk tier (HIGH first)
2. **Claim Request:** 15-minute lock acquired
3. **Review:** Document + AI analysis + confidence scores
4. **Decision:** APPROVE or REJECT (reason required for reject)
5. **Integration:** RPS update only on approval
6. **Override Tracking:** Logged for model calibration

---

### Diagram 9: Real-Time Processing Updates

**Purpose:** Shows how UI polls for real-time step updates  
**Key Insight:** Polling every 2 seconds, callback updates `current_processing_step`

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#f0fdf4',
    'primaryTextColor': '#14532d',
    'primaryBorderColor': '#4ade80',
    'lineColor': '#64748b',
    'background': '#ffffff',
    'actorBkg': '#f0fdf4',
    'actorBorder': '#4ade80',
    'actorTextColor': '#14532d',
    'activationBkgColor': '#dcfce7',
    'activationBorderColor': '#4ade80',
    'noteBkgColor': '#eff6ff',
    'noteBorderColor': '#93c5fd',
    'noteTextColor': '#1e3a5f',
    'fontFamily': 'ui-sans-serif, system-ui, sans-serif'
  }
}}%%
sequenceDiagram
    participant Staff as Staff portal
    participant API as FastAPI backend
    participant Celery as Celery worker
    participant LG as LangGraph pipeline
    participant DB as PostgreSQL

    Staff->>API: POST /requests — create request
    API->>DB: INSERT — status = VALIDATED
    API-->>Staff: 201 Created — REQ-12345

    Staff->>API: POST /requests/REQ-12345/upload
    API->>DB: UPDATE — status = QUEUED
    API->>Celery: Enqueue process_document(REQ-12345)
    API-->>Staff: 200 OK — processing will begin

    Note over Staff,DB: Staff navigates to request detail page

    Staff->>API: GET /requests/REQ-12345
    API->>DB: SELECT status, current_processing_step
    DB-->>API: status = QUEUED
    API-->>Staff: Show "Queued for processing"

    Note over Celery,LG: Worker picks up task

    Celery->>DB: UPDATE — status = PROCESSING
    Celery->>LG: Start pipeline

    loop For each pipeline step
        LG->>LG: Execute step
        LG->>Celery: on_step_change(REQ-12345, "Running OCR")
        Celery->>DB: UPDATE — current_processing_step = "Running OCR"

        Note over Staff,DB: UI polls every 2 s

        Staff->>API: GET /requests/REQ-12345
        API->>DB: SELECT status, current_processing_step
        DB-->>API: status = PROCESSING · step = "Running OCR"
        API-->>Staff: Spinner — "Running OCR"
    end

    LG-->>Celery: Pipeline complete
    Celery->>DB: UPDATE — status = AI_VERIFIED_PENDING_HUMAN · all AI results

    Note over Staff,DB: Final poll

    Staff->>API: GET /requests/REQ-12345
    API->>DB: SELECT *
    DB-->>API: status = AI_VERIFIED_PENDING_HUMAN · confidence = 0.946
    API-->>Staff: Full AI analysis — "Ready for checker review"
    Staff-->>Staff: "AI verification complete ✓"
```

**Processing Steps:**
1. Validating Document
2. Extracting Metadata
3. Running OCR
4. Classifying Document
5. Extracting Fields
6. Detecting Forgery
7. Calculating Scores
8. Generating Summary
9. AI Verification Complete

**Polling Strategy:**
- Interval: 2 seconds
- Endpoint: `GET /api/v1/requests/{id}`
- Field: `current_processing_step`
- Duration: 30s - 2min (average 45s)

---

## 4. Agent Design

### 4.1 Architecture Choice: Supervisor-Worker Pattern

IASW uses a **supervisor-worker architecture** where a central supervisor orchestrates specialized AI agents. This pattern provides modularity (agents can be improved independently), observability (clear logging boundaries), and fault isolation (one agent failing doesn't crash the pipeline). See [Diagram 2](#diagram-2-supervisor-worker-agent-architecture) for the complete architecture.

### 4.2 Agent Design Table

| Agent | Responsibility | Input | Output | Tools/Methods |
|-------|----------------|-------|--------|---------------|
| **Metadata Agent** | Extract document metadata (creation date, software, resolution) | Document path | Metadata dict, anomaly flags | PyMuPDF, Pillow/exifread |
| **OCR Agent** | Extract text from document images | Document path | Raw text, per-word confidence, bounding boxes | Tesseract 5 (primary), Google Vision API (fallback) |
| **Classifier Agent** | Verify document type matches declared type | OCR text, declared type | Detected type, confidence, match flag | LLM-based keyword analysis |
| **Extractor Agent** | Extract structured fields (names, dates) from document | OCR text, document type | Field values with confidence scores | LLM extraction with schema validation |
| **Forgery Agent** | Detect document tampering | Document path | Forgery score (0-1), PASS/FLAG/FAIL result | Metadata analysis, ELA, font consistency, ML model |
| **Scorer Agent** | Calculate overall confidence and risk tier | All previous outputs | Weighted score, risk tier (LOW/MEDIUM/HIGH), flags | Jaro-Winkler similarity, weighted formula |
| **Summary Agent** | Generate human-readable review brief | Score card, flags | Natural language summary, AI recommendation | LLM summarization |

### 4.3 Real-Time Processing Updates

The pipeline streams processing step updates to the database in real-time, allowing the UI to show progress. See [Diagram 9](#diagram-9-real-time-processing-updates) for the complete flow.

| Step Name | Display Text |
|-----------|--------------|
| validation | "Validating Document" |
| metadata | "Extracting Metadata" |
| ocr | "Running OCR" |
| fallback_ocr | "Running Fallback OCR" |
| classifier | "Classifying Document" |
| extractor | "Extracting Fields" |
| forgery | "Detecting Forgery" |
| scorer | "Calculating Scores" |
| summary | "Generating Summary" |
| complete | "AI Verification Complete" |

---

## 5. AI/ML Implementation

### 5.1 Confidence Scoring Model

The system calculates an overall confidence score using a weighted formula. See [Diagram 5](#diagram-5-confidence-scoring-model) for the complete model.

```
overall_score = (
    name_match_weight × avg(old_name_score, new_name_score) +
    authenticity_weight × forgery_score +
    ocr_weight × ocr_confidence +
    extraction_weight × extraction_confidence
)
```

**Default Weights:**
| Signal | Weight | Why This Weight |
|--------|--------|-----------------|
| Name Match (old + new) | 40% | Most critical for identity verification |
| Document Authenticity | 30% | Forgery detection is second priority |
| OCR Confidence | 15% | Affects downstream extraction quality |
| LLM Extraction Confidence | 15% | Reflects extraction reliability |

### 5.2 Risk Tier Determination

| Risk Tier | Condition | AI Recommendation | Routing |
|-----------|-----------|-------------------|---------|
| **LOW** | score ≥ 0.90 AND no critical flags | APPROVE | Standard queue |
| **MEDIUM** | 0.70 ≤ score < 0.90 | MANUAL_REVIEW | Standard queue (highlighted) |
| **HIGH** | score < 0.70 OR critical flags | REJECT | Senior checker queue |

**Critical Flags That Force HIGH Risk:**
- `DOC_TYPE_MISMATCH` — Document type doesn't match declaration
- `FORGERY_DETECTED` — Forgery score below 0.60
- `EXTRACTION_FAILED` — Could not extract required name fields
- `NAME_SEVERE_MISMATCH` — Name similarity below 70%

### 5.3 Forgery Detection (Multi-Layer)

Forgery detection uses four complementary analysis layers. See [Diagram 4](#diagram-4-forgery-detection-multi-layer) for the complete architecture.

| Layer | Weight | What It Checks |
|-------|--------|----------------|
| **Metadata Analysis** | 20% | PDF creation/modification dates, editing software signatures, EXIF anomalies |
| **Error Level Analysis (ELA)** | 30% | Re-compression artifacts that reveal edited regions |
| **Font Consistency** | 20% | Font mismatches in text, kerning irregularities |
| **ML Model** | 30% | Pattern detection, template matching against known authentic documents |

**Forgery Score Thresholds:**
| Score | Result | Action |
|-------|--------|--------|
| > 0.85 | PASS | Likely authentic |
| 0.60–0.85 | FLAG | Human review required |
| < 0.60 | FAIL | Likely forged, route to senior checker |

### 5.4 Name Matching Algorithm

Names are compared using **Jaro-Winkler similarity**, which is optimized for names:
- Handles transpositions ("Sharma" vs "Shrama")
- Gives extra weight to matching prefixes
- Returns a score from 0.0 to 1.0

| Match Score | Outcome |
|-------------|---------|
| > 0.95 | PASS — Names match |
| 0.85–0.95 | FLAG — Possible OCR typo |
| < 0.85 | FAIL — Significant mismatch |

---

## 6. Human-in-the-Loop Design

### 6.1 Core Principle

**AI assists, humans decide.** No customer data is modified in core banking (RPS) without explicit human approval. This is enforced at multiple levels. See [Diagram 6](#diagram-6-human-in-the-loop-boundaries) for the complete enforcement architecture.

### 6.2 What AI Can vs Cannot Do

| Action | AI Can Do? | Rationale |
|--------|------------|-----------|
| Validate file format, size, virus scan | ✅ Yes | Technical checks, no business judgment |
| Perform OCR and text extraction | ✅ Yes | Data transformation, no decision |
| Classify document type | ✅ Yes | Detection only, mismatch flagged for human |
| Extract fields from document | ✅ Yes | Data extraction, not modification |
| Detect potential forgery | ✅ Yes | Flag generation, human reviews flags |
| Calculate confidence scores | ✅ Yes | Transparent scoring algorithm |
| Generate summary and recommendation | ✅ Yes | Advisory only |
| Route to appropriate queue | ✅ Yes | Based on risk tier rules |
| **Approve request** | ❌ No | Human must approve |
| **Reject request** | ❌ No | Human must confirm rejection |
| **Update core banking (RPS)** | ❌ No | Only triggered by human APPROVE |

### 6.3 HITL Enforcement Mechanisms

**Technical Enforcement:**

1. **State Machine Guard:** The `APPROVED` and `REJECTED` states can only be reached from `IN_REVIEW` state, which requires a human checker to claim the request.

2. **JWT Authentication:** Checker endpoints require valid JWT token with `checker` role. Requests must include authenticated user identity.

3. **Actor Validation:** RPS Update Service validates that `actor_type = HUMAN` before processing. System-initiated calls are rejected and logged as security events.

4. **Audit Trail:** Every state transition logs `actor_type` (SYSTEM/HUMAN/AI_AGENT). Compliance can verify no AI actor triggered final decisions.

5. **UI-Only Actions:** APPROVE, REJECT, MORE_INFO, ESCALATE buttons exist only in the Checker Workbench UI. No API endpoint allows AI agents to invoke these actions.

### 6.4 Checker Workflow

See [Diagram 8](#diagram-8-checker-workflow-sequence) for the complete workflow sequence.

1. **View Queue:** Checker sees pending items sorted by risk tier (HIGH first)
2. **Claim Item:** Lock acquired for 15 minutes (prevents conflicts)
3. **Review:** See document, AI analysis, confidence scores, flags
4. **Decide:** APPROVE (with optional comment) or REJECT (reason required)
5. **Audit:** Decision logged with timestamp, actor, and reasoning

### 6.5 Override Tracking

When a checker disagrees with AI recommendation:

| AI Said | Human Said | Logged As | Implication |
|---------|------------|-----------|-------------|
| APPROVE | REJECT | `AI_TOO_LENIENT` | AI may need stricter thresholds |
| REJECT | APPROVE | `AI_TOO_STRICT` | AI may need looser thresholds |
| MANUAL_REVIEW | APPROVE/REJECT | None (expected) | AI correctly identified uncertainty |

Override metrics feed back into model calibration.

---

## 7. Data Model

### 7.1 Core Schema (Pending Requests Table)

See [Diagram 7](#diagram-7-database-schema-erd) for the complete entity relationship diagram.

```sql
CREATE TABLE pending_requests (
    -- Identity
    request_id              VARCHAR(36) PRIMARY KEY,    -- "REQ-12345"
    idempotency_key         VARCHAR(64) UNIQUE,         -- Duplicate detection
    customer_id             VARCHAR(20) NOT NULL,       -- "C001"
    
    -- Request Details
    change_type             VARCHAR(50) NOT NULL,       -- "LEGAL_NAME"
    document_type           VARCHAR(50) NOT NULL,       -- "MARRIAGE_CERTIFICATE"
    requested_old_value     VARCHAR(255) NOT NULL,      -- "Priya Sharma"
    requested_new_value     VARCHAR(255) NOT NULL,      -- "Priya Mehta"
    
    -- Extracted Values (from document)
    extracted_old_value     VARCHAR(255),               -- "Priya Sharma"
    extracted_new_value     VARCHAR(255),               -- "Priya Mehta"
    extraction_metadata     JSONB,                      -- All extracted fields
    
    -- Confidence Scores
    old_name_match_score    DECIMAL(5,4),               -- 1.0000 (100%)
    new_name_match_score    DECIMAL(5,4),               -- 1.0000 (100%)
    ocr_confidence          DECIMAL(5,4),               -- 0.9200 (92%)
    extraction_confidence   DECIMAL(5,4),               -- 0.9400 (94%)
    doc_authenticity_score  DECIMAL(5,4),               -- 0.8700 (87%)
    overall_confidence      DECIMAL(5,4),               -- Weighted aggregate
    
    -- Forgery Detection
    forgery_score           DECIMAL(5,4),               -- 0.0 (forged) to 1.0 (authentic)
    forgery_result          VARCHAR(10),                -- PASS / FLAG / FAIL
    forgery_details         JSONB,                      -- Per-layer scores
    
    -- Risk & Routing
    risk_tier               VARCHAR(10),                -- LOW / MEDIUM / HIGH
    flags                   JSONB,                      -- Array of flag codes
    ai_recommendation       VARCHAR(20),                -- APPROVE / REJECT / MANUAL_REVIEW
    ai_summary              TEXT,                       -- Human-readable summary
    
    -- Document Storage
    document_storage_path   VARCHAR(255),               -- Path to original
    filenet_staging_id      VARCHAR(100),               -- Staging reference
    filenet_permanent_id    VARCHAR(100),               -- Permanent reference
    
    -- Workflow Status
    status                  VARCHAR(30) NOT NULL,       -- Current state
    current_processing_step VARCHAR(50),                -- Real-time step tracking
    assigned_checker        VARCHAR(50),                -- Checker who claimed
    checker_lock_until      TIMESTAMP,                  -- Lock expiry time
    checker_decision        VARCHAR(20),                -- APPROVE / REJECT / MORE_INFO
    checker_decision_reason TEXT,                       -- Mandatory for REJECT
    
    -- Timestamps
    created_at              TIMESTAMP NOT NULL,
    validated_at            TIMESTAMP,
    processing_started_at   TIMESTAMP,
    processing_completed_at TIMESTAMP,
    staged_at               TIMESTAMP,
    claimed_at              TIMESTAMP,
    decided_at              TIMESTAMP,
    completed_at            TIMESTAMP
);
```

### 7.2 Status State Machine

```
INTAKE_RECEIVED → VALIDATED → QUEUED → PROCESSING → AI_VERIFIED_PENDING_HUMAN
                                              │                    │
                                              │                    ▼
                                              │               IN_REVIEW
                                              │                    │
                                              │     ┌──────────────┼──────────────┐
                                              │     ▼              ▼              ▼
                                              │  APPROVED      REJECTED      PENDING_INFO
                                              │     │                              │
                                              │     ▼                              │
                                              │  COMPLETED                    (resubmit)
                                              │
                                              └──▶ FAILED (on error)
```

### 7.3 Example Record

```json
{
  "request_id": "REQ-12345",
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
  
  "status": "AI_VERIFIED_PENDING_HUMAN",
  "current_processing_step": null
}
```

---

## 8. Technology Stack Justification

### 8.1 Technology Choices

| Layer | Technology | Why This Choice |
|-------|------------|-----------------|
| **Frontend** | Next.js 14 (React, TypeScript) | Server-side rendering for fast initial load; API routes for BFF pattern; TypeScript for type safety; file-based routing suits two-UI structure (Staff + Checker) |
| **Backend API** | FastAPI (Python) | Native async/await for non-blocking I/O; Python ecosystem has best ML/AI library support; Pydantic models provide automatic validation; auto-generated OpenAPI docs |
| **AI Orchestration** | LangGraph | Graph-based workflow fits pipeline perfectly; conditional routing based on confidence; state management across nodes; checkpointing for resumable workflows |
| **LLM** | Claude 3.5 Sonnet | Excellent structured data extraction; lower cost than GPT-4; strong reasoning for forgery analysis; consistent JSON output |
| **OCR** | Tesseract 5 + Google Vision | Tesseract is free, runs locally; Google Vision as fallback for poor quality scans |
| **Task Queue** | Celery + Redis | Simple setup; reliable; good monitoring with Flower; handles async/sync boundaries well |
| **Database** | PostgreSQL | JSONB for flexible metadata; robust ACID compliance; excellent for audit trails |
| **Document Storage** | Local filesystem (S3-ready) | Standard interface; easy to mock for development; production-ready with S3 swap |

### 8.2 Key Design Decisions

**Why LangGraph over alternatives?**

| Alternative | Why Not Chosen |
|-------------|----------------|
| Plain LangChain | LangGraph adds graph structure, conditional routing, and state management |
| CrewAI | Better for autonomous multi-agent collaboration; our pipeline is sequential with clear handoffs |
| Custom orchestration | LangGraph provides checkpointing, visualization, and built-in error handling |

**Why Claude 3.5 Sonnet over GPT-4o?**
- Better at structured data extraction from documents
- Lower cost per token for high-volume processing
- More consistent JSON output formatting
- Strong reasoning for interpreting forgery signals

**Why Celery for task queue?**
- Handles the async/sync boundary cleanly
- Built-in retry with exponential backoff
- Dead letter queue for failed tasks
- Flower dashboard for monitoring

### 8.3 Async/Sync Boundaries

The system carefully manages boundaries between synchronous and asynchronous operations:

| Operation | Sync/Async | Why |
|-----------|------------|-----|
| Request validation | Sync | Staff need immediate feedback (<500ms) |
| Document processing | Async | Heavy AI work (30s-2min), don't block staff |
| Checker review | Sync | Human interaction is inherently synchronous |
| RPS update | Sync | Transaction safety, immediate confirmation |

**Event Loop Handling in Celery:**
Celery workers run synchronously, but the LangGraph pipeline is async. We handle this with a `run_async()` wrapper that properly manages event loops without conflicts.

---

## 9. Observability & Operations

### 9.1 Logging Architecture

All logs follow a structured JSON format:

```json
{
  "timestamp": "2024-03-20T10:30:45.123Z",
  "level": "INFO",
  "service": "iasw-backend",
  "request_id": "REQ-12345",
  "agent": "scorer",
  "step": "calculate_name_match",
  "duration_ms": 45,
  "status": "success",
  "ocr_confidence": 0.92,
  "overall_score": 0.946
}
```

**Important:** No PII in log payloads. Customer IDs are hashed for log correlation.

### 9.2 Metrics Tracked

| Metric | Purpose |
|--------|---------|
| `request_processing_time` | Pipeline performance |
| `ocr_confidence_avg` | Document quality trend |
| `approval_rate` | Process efficiency |
| `ai_recommendation_accuracy` | AI calibration |
| `checker_override_rate` | Human vs AI alignment |

### 9.3 Audit Trail

Every action is logged in the `audit_logs` table:

| Field | Description |
|-------|-------------|
| `audit_id` | UUID primary key |
| `request_id` | Associated request |
| `event_type` | STATE_CHANGE, HUMAN_ACTION, SYSTEM_EVENT, ERROR |
| `actor_type` | SYSTEM, HUMAN, AI_AGENT |
| `actor_id` | Who performed the action |
| `previous_state` | State before |
| `new_state` | State after |
| `action_details` | JSON with context |
| `checksum` | SHA-256 for tamper detection |

### 9.4 Error Handling

| Level | Strategy |
|-------|----------|
| Agent-level | Errors return partial results with error flag |
| Pipeline-level | Failed pipelines set status to `FAILED` |
| Task-level | Celery retries 3 times with exponential backoff |
| System-level | Dead letter queue for unrecoverable failures |

---

## Assumptions & Limitations

### Assumptions

1. **Document Quality:** Uploaded documents are reasonably legible (>60% OCR confidence expected)
2. **English Language:** OCR and extraction tuned for English-language documents
3. **Network Availability:** Stable connection to LLM provider (Claude API)
4. **Browser Support:** Modern browsers (Chrome, Firefox, Safari, Edge)

### Limitations

1. **No Offline Mode:** Requires network connectivity
2. **No Mobile App:** Web-only interface
3. **Limited Document Types:** Currently only Marriage Certificate, Gazette, Deed Poll, Court Order
4. **Mock Integrations:** RPS (core banking) and FileNet are mocked for demo
5. **No External Verification:** No integration with government certificate databases

