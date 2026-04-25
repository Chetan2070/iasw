"""
Document Classifier Node

Classifies the document type using LLM analysis.
"""

import logging
import json
from typing import Dict, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.state import ProcessingState
from app.config import settings

logger = logging.getLogger(__name__)

CLASSIFIER_SYSTEM_PROMPT = """You are a document classification expert for a banking system.
Your task is to analyze the text extracted from a document and determine its type.

You must classify the document into ONE of these categories:
- MARRIAGE_CERTIFICATE: A certificate issued by a government authority certifying a marriage
- GAZETTE_NOTIFICATION: An official government gazette notification announcing a name change
- DEED_POLL: A legal document for changing one's name
- COURT_ORDER: A court order related to name change
- UTILITY_BILL: A bill from a utility company (electricity, water, gas, etc.)
- BIRTH_CERTIFICATE: A certificate of birth issued by government
- PASSPORT: A travel document/passport
- PAN_CARD: An Indian PAN card
- CONSENT_FORM: A consent/authorization form
- OTHER: If none of the above categories match

Analyze the text carefully for:
1. Document headers and titles
2. Official seals or authority mentions
3. Key phrases and terminology
4. Structure and format indicators

Respond in JSON format only:
{
    "detected_type": "DOCUMENT_TYPE",
    "confidence": 0.0 to 1.0,
    "signals": ["list", "of", "evidence", "found"],
    "reasoning": "Brief explanation"
}"""


async def classifier_node(state: ProcessingState) -> Dict[str, Any]:
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
        - classification_signals: List[str]
        - flags: adds DOC_TYPE_MISMATCH if applicable
        - current_step: "classifier"
    """
    request_id = state.get('request_id', 'unknown')
    ocr_text = state.get('ocr_text', '')
    declared_type = state.get('document_type', '')

    logger.info(f"[{request_id}] Classifying document (declared: {declared_type})")

    try:
        # Initialize LLM with optional proxy
        llm_kwargs = {
            "model": settings.LLM_MODEL,
            "api_key": settings.ANTHROPIC_API_KEY,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": 1024,
        }
        if settings.ANTHROPIC_BASE_URL:
            llm_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL

        llm = ChatAnthropic(**llm_kwargs)

        # Truncate text if too long
        max_text_length = 8000
        text_to_analyze = ocr_text[:max_text_length] if len(ocr_text) > max_text_length else ocr_text

        # Create messages
        messages = [
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=f"Please classify this document:\n\n{text_to_analyze}")
        ]

        # Call LLM
        response = await llm.ainvoke(messages)
        response_text = response.content

        # Parse JSON response
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response_text[json_start:json_end])
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            logger.warning(f"[{request_id}] Failed to parse classifier response: {e}")
            result = {
                "detected_type": "OTHER",
                "confidence": 0.5,
                "signals": [],
                "reasoning": "Failed to parse response"
            }

        detected_type = result.get('detected_type', 'OTHER')
        confidence = float(result.get('confidence', 0.5))
        signals = result.get('signals', [])

        # Check if detected type matches declared type
        is_match = detected_type.upper() == declared_type.upper()

        # Update flags
        flags = list(state.get('flags', []))
        if not is_match:
            flags.append("DOC_TYPE_MISMATCH")
            logger.warning(f"[{request_id}] Document type mismatch: declared={declared_type}, detected={detected_type}")
        elif confidence < 0.7:
            flags.append("DOC_TYPE_UNCERTAIN")

        # Track LLM call
        llm_calls = list(state.get('llm_calls', []))
        llm_calls.append({
            "node": "classifier",
            "model": settings.LLM_MODEL,
            "input_tokens": len(text_to_analyze.split()),
            "output_tokens": len(response_text.split()),
        })

        logger.info(f"[{request_id}] Classification: {detected_type} (confidence: {confidence:.2f}, match: {is_match})")

        return {
            "detected_document_type": detected_type,
            "classification_confidence": confidence,
            "classification_match": is_match,
            "classification_signals": signals,
            "flags": flags,
            "llm_calls": llm_calls,
            "current_step": "classifier",
        }

    except Exception as e:
        logger.error(f"[{request_id}] Classification failed: {str(e)}")

        # Return default values on error
        return {
            "detected_document_type": declared_type,  # Assume declared type
            "classification_confidence": 0.5,
            "classification_match": True,
            "classification_signals": [],
            "errors": state.get('errors', []) + [f"Classification failed: {str(e)}"],
            "current_step": "classifier",
        }
