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
from app.config import settings

logger = logging.getLogger(__name__)

# Field schemas for different document types
FIELD_SCHEMAS = {
    "MARRIAGE_CERTIFICATE": {
        "required": ["bride_name", "married_name"],
        "optional": ["marriage_date", "groom_name", "issuing_authority", "certificate_number"],
        "field_descriptions": {
            "bride_name": "The bride's name before marriage (maiden name)",
            "married_name": "The bride's name after marriage",
            "marriage_date": "Date of marriage in YYYY-MM-DD format",
            "groom_name": "The groom's full name",
            "issuing_authority": "The authority that issued the certificate",
            "certificate_number": "The certificate/registration number",
        }
    },
    "GAZETTE_NOTIFICATION": {
        "required": ["old_name", "new_name"],
        "optional": ["publication_date", "gazette_number", "notification_number"],
        "field_descriptions": {
            "old_name": "The person's previous name",
            "new_name": "The person's new name after change",
            "publication_date": "Date of gazette publication",
            "gazette_number": "Gazette issue number",
            "notification_number": "Notification reference number",
        }
    },
    "DEED_POLL": {
        "required": ["old_name", "new_name"],
        "optional": ["execution_date", "witness_names"],
        "field_descriptions": {
            "old_name": "The person's previous name",
            "new_name": "The person's new name",
            "execution_date": "Date the deed poll was executed",
            "witness_names": "Names of witnesses",
        }
    },
}

EXTRACTOR_SYSTEM_PROMPT = """You are a document data extraction expert for a banking system.
Your task is to extract specific fields from document text for a NAME CHANGE request.

CONTEXT: The customer is requesting to change their name on their bank account.
They have provided a supporting document (marriage certificate, gazette notification, etc.)

Your job is to find and extract the names from the DOCUMENT that show:
1. The person's name BEFORE the change (bride_name/old_name)
2. The person's name AFTER the change (married_name/new_name)

IMPORTANT RULES:
1. Only extract information that is EXPLICITLY stated in the text
2. Do not infer or guess values
3. If a field is not found, set its value to null
4. Provide a confidence score (0.0-1.0) for each extracted value
5. Include a source_snippet showing where you found the value
6. For marriage certificates:
   - bride_name = the bride's maiden/previous name (name before marriage)
   - married_name = her full name AFTER marriage (typically: FirstName + Husband's Surname)
7. FOCUS on extracting the PRIMARY person's names, not witnesses, officials, or other parties
8. If the document shows "Name of Bride: X" and "Name after marriage: Y", extract X as bride_name and Y as married_name

Respond in JSON format only:
{{
    "fields": {{
        "field_name": {{
            "value": "extracted value or null",
            "confidence": 0.0 to 1.0,
            "source_snippet": "relevant text snippet where value was found"
        }}
    }},
    "extraction_notes": "any relevant notes about the extraction"
}}"""


def build_extraction_prompt(document_type: str, ocr_text: str, requested_old: str = "", requested_new: str = "") -> str:
    """Build the extraction prompt based on document type."""
    schema = FIELD_SCHEMAS.get(document_type, FIELD_SCHEMAS.get("MARRIAGE_CERTIFICATE"))

    fields_description = "\n".join([
        f"- {field}: {schema['field_descriptions'].get(field, 'No description')}"
        for field in schema['required'] + schema['optional']
    ])

    required_fields = ", ".join(schema['required'])
    optional_fields = ", ".join(schema['optional'])

    # Add context about what names we're looking for
    name_context = ""
    if requested_old or requested_new:
        name_context = f"""
CUSTOMER'S NAME CHANGE REQUEST:
- Current name on bank account (old name): {requested_old or 'Not provided'}
- Requested new name: {requested_new or 'Not provided'}

Look for these names (or similar) in the document to verify the name change.
"""

    return f"""Document Type: {document_type}
{name_context}
REQUIRED FIELDS (must extract if present):
{required_fields}

OPTIONAL FIELDS:
{optional_fields}

Field Descriptions:
{fields_description}

DOCUMENT TEXT:
{ocr_text}

Extract all fields from the document text above. Focus on finding the names that match or are similar to the customer's requested name change. Remember to include confidence scores and source snippets."""


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

        # Calculate average confidence
        confidences = []
        for field_data in extracted_fields.values():
            if isinstance(field_data, dict) and field_data.get('value'):
                confidences.append(field_data.get('confidence', 0.5))

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Map to old/new values based on document type
        extracted_old_value = ""
        extracted_new_value = ""

        if document_type == "MARRIAGE_CERTIFICATE":
            bride_name = extracted_fields.get('bride_name', {})
            married_name = extracted_fields.get('married_name', {})
            extracted_old_value = bride_name.get('value', '') if isinstance(bride_name, dict) else ''
            extracted_new_value = married_name.get('value', '') if isinstance(married_name, dict) else ''
        else:
            old_name = extracted_fields.get('old_name', {})
            new_name = extracted_fields.get('new_name', {})
            extracted_old_value = old_name.get('value', '') if isinstance(old_name, dict) else ''
            extracted_new_value = new_name.get('value', '') if isinstance(new_name, dict) else ''

        # Update flags
        flags = list(state.get('flags', []))
        schema = FIELD_SCHEMAS.get(document_type, {})
        required_fields = schema.get('required', [])

        # Check for missing required fields
        missing_required = []
        for field in required_fields:
            field_data = extracted_fields.get(field, {})
            if not isinstance(field_data, dict) or not field_data.get('value'):
                missing_required.append(field)

        if missing_required:
            if len(missing_required) == len(required_fields):
                flags.append("EXTRACTION_FAILED")
                logger.warning(f"[{request_id}] Extraction failed - all required fields missing")
            else:
                flags.append("PARTIAL_EXTRACTION")
                logger.warning(f"[{request_id}] Partial extraction - missing: {missing_required}")

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
