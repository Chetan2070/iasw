"""
Validation Node

Validates the request before document processing begins.
"""

import os
import logging
from typing import Dict, Any

from app.agents.state import ProcessingState

logger = logging.getLogger(__name__)


async def validation_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Validates the request can proceed to document processing.

    Checks:
        1. Request has required fields
        2. Document file exists and is accessible
        3. Document file is not empty

    Input State:
        - request_id
        - document_path
        - customer_id

    Output State Updates:
        - validation_passed: bool
        - validation_errors: List[str]
        - current_step: "validation"
    """
    logger.info(f"[{state['request_id']}] Starting validation")

    errors = []

    # Check required fields
    if not state.get("request_id"):
        errors.append("Missing request_id")

    if not state.get("customer_id"):
        errors.append("Missing customer_id")

    if not state.get("document_path"):
        errors.append("Missing document_path")

    # Check document file exists
    document_path = state.get("document_path", "")
    if document_path:
        if not os.path.exists(document_path):
            errors.append(f"Document file not found: {document_path}")
        elif os.path.getsize(document_path) == 0:
            errors.append("Document file is empty")

    validation_passed = len(errors) == 0

    if validation_passed:
        logger.info(f"[{state['request_id']}] Validation passed")
    else:
        logger.warning(f"[{state['request_id']}] Validation failed: {errors}")

    return {
        "validation_passed": validation_passed,
        "validation_errors": errors,
        "current_step": "validation",
    }


def route_after_validation(state: ProcessingState) -> str:
    """
    Route after validation node.

    Returns:
        - "continue" if validation passed
        - "fail" if validation failed
    """
    if state.get("validation_passed", False):
        return "continue"
    return "fail"
