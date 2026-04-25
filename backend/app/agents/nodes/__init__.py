"""
Processing Nodes Module

Individual nodes for the LangGraph document processing pipeline.
Each node is an async function that takes ProcessingState and returns state updates.

Node Execution Order:
1. validation_node - Validate request and document existence
2. ocr_node - Extract text from document
3. classifier_node - Classify document type
4. extractor_node - Extract old/new names using LLM
5. forgery_node - Detect document tampering
6. scorer_node - Calculate confidence scores and risk tier
7. summary_node - Generate human-readable summary
"""

from app.agents.nodes.validation import validation_node, route_after_validation
from app.agents.nodes.ocr import ocr_node, fallback_ocr_node, route_after_ocr
from app.agents.nodes.classifier import classifier_node
from app.agents.nodes.extractor import extractor_node
from app.agents.nodes.forgery import forgery_node
from app.agents.nodes.scorer import scorer_node
from app.agents.nodes.summary import summary_node

__all__ = [
    "validation_node",
    "route_after_validation",
    "ocr_node",
    "fallback_ocr_node",
    "route_after_ocr",
    "classifier_node",
    "extractor_node",
    "forgery_node",
    "scorer_node",
    "summary_node",
]
