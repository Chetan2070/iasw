"""
Field Extractor Node

Extracts structured fields from the document using LLM.
"""

import logging
import json
from typing import Dict, Any, List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import ProcessingState
from app.agents.prompts import EXTRACTOR_SYSTEM_PROMPT, FIELD_SCHEMAS, build_extraction_prompt
from app.config import settings

logger = logging.getLogger(__name__)


async def extractor_node(state: ProcessingState) -> Dict[str, Any]:
    """
    Extracts structured fields from document using LLM.

    Process:
        1. Select extraction schema based on document type
        2. Send OCR text to LLM with extraction prompt
        3. Parse structured response with field values and confidence

    Input State:
        - ocr_text
        - detected_document_type (or document_type)

    Output State Updates:
        - extracted_fields: dict
        - extraction_confidence: float
        - extracted_old_value: str
        - extracted_new_value: str
        - flags: may add PARTIAL_EXTRACTION or EXTRACTION_FAILED
        - current_step: "extractor"
    """
    request_id = state.get('request_id', 'unknown')
    ocr_text = state.get('ocr_text', '')
    document_type = state.get('detected_document_type') or state.get('document_type', 'MARRIAGE_CERTIFICATE')
    requested_old = state.get('requested_old_value', '')
    requested_new = state.get('requested_new_value', '')

    logger.info(f"[{request_id}] Extracting fields for {document_type}")

    try:
        # Initialize LLM with optional proxy
        llm_kwargs = {
            "model": settings.LLM_MODEL,
            "api_key": settings.ANTHROPIC_API_KEY,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": 2048,
        }
        if settings.ANTHROPIC_BASE_URL:
            llm_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL

        llm = ChatAnthropic(**llm_kwargs)

        # Truncate text if too long
        max_text_length = 8000
        text_to_analyze = ocr_text[:max_text_length] if len(ocr_text) > max_text_length else ocr_text

        # Build extraction prompt with requested names for context
        extraction_prompt = build_extraction_prompt(document_type, text_to_analyze, requested_old, requested_new)

        # Create messages
        messages = [
            SystemMessage(content=EXTRACTOR_SYSTEM_PROMPT),
            HumanMessage(content=extraction_prompt)
        ]

        # Call LLM
        response = await llm.ainvoke(messages)
        response_text = response.content

        # Parse JSON response
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            logger.warning(f"[{request_id}] Failed to parse extractor response: {e}")
            result = {"fields": {}}

        extracted_fields = result.get('fields', {})

        # Handle new flexible format (old_name/new_name at root level)
        if 'old_name' in result and isinstance(result['old_name'], dict):
            extracted_fields = {
                'old_name': result['old_name'],
                'new_name': result.get('new_name', {}),
            }
            # Also store alternative names if present
            if 'alternative_names' in result:
                extracted_fields['alternative_names'] = result['alternative_names']

        # Calculate average confidence
        confidences = []
        for field_data in extracted_fields.values():
            if isinstance(field_data, dict) and field_data.get('value'):
                confidences.append(field_data.get('confidence', 0.5))

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Extract old/new values - now using unified old_name/new_name format
        extracted_old_value = ""
        extracted_new_value = ""

        # First try the new format (old_name/new_name)
        old_name_data = extracted_fields.get('old_name', {})
        new_name_data = extracted_fields.get('new_name', {})

        if isinstance(old_name_data, dict):
            extracted_old_value = old_name_data.get('value', '') or ''
        if isinstance(new_name_data, dict):
            extracted_new_value = new_name_data.get('value', '') or ''

        # Fallback to old format for backwards compatibility
        if not extracted_old_value and document_type == "MARRIAGE_CERTIFICATE":
            bride_name = extracted_fields.get('bride_name', {})
            if isinstance(bride_name, dict):
                extracted_old_value = bride_name.get('value', '') or ''
        if not extracted_new_value and document_type == "MARRIAGE_CERTIFICATE":
            married_name = extracted_fields.get('married_name', {})
            if isinstance(married_name, dict):
                extracted_new_value = married_name.get('value', '') or ''

        # Update flags based on extraction quality
        flags = list(state.get('flags', []))

        # Check if we got both names
        has_old_name = bool(extracted_old_value and extracted_old_value.strip())
        has_new_name = bool(extracted_new_value and extracted_new_value.strip())

        if not has_old_name and not has_new_name:
            flags.append("EXTRACTION_FAILED")
            logger.warning(f"[{request_id}] Extraction failed - no names extracted")
        elif not has_old_name or not has_new_name:
            flags.append("PARTIAL_EXTRACTION")
            missing = "old name" if not has_old_name else "new name"
            logger.warning(f"[{request_id}] Partial extraction - missing: {missing}")

        # Track LLM call
        llm_calls = list(state.get('llm_calls', []))
        llm_calls.append({
            "node": "extractor",
            "model": settings.LLM_MODEL,
            "input_tokens": len(text_to_analyze.split()),
            "output_tokens": len(response_text.split()),
        })

        logger.info(f"[{request_id}] Extraction complete - {len(extracted_fields)} fields, confidence: {avg_confidence:.2f}")

        return {
            "extracted_fields": extracted_fields,
            "extraction_confidence": float(avg_confidence),
            "extracted_old_value": extracted_old_value or "",
            "extracted_new_value": extracted_new_value or "",
            "flags": flags,
            "llm_calls": llm_calls,
            "current_step": "extractor",
        }

    except Exception as e:
        logger.error(f"[{request_id}] Extraction failed: {str(e)}")

        return {
            "extracted_fields": {},
            "extraction_confidence": 0.0,
            "extracted_old_value": "",
            "extracted_new_value": "",
            "flags": state.get('flags', []) + ["EXTRACTION_FAILED"],
            "errors": state.get('errors', []) + [f"Extraction failed: {str(e)}"],
            "current_step": "extractor",
        }
