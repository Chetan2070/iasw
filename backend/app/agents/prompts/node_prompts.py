"""
Node-Level Prompts

Prompts used directly by pipeline nodes for LLM calls (not via ReAct agents).
These prompts are typically more detailed as they handle the complete task.
"""

# =============================================================================
# Field Schemas for Document Types
# =============================================================================

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

# =============================================================================
# Document Classifier Prompt
# =============================================================================

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

# =============================================================================
# Field Extractor Prompt
# =============================================================================

EXTRACTOR_SYSTEM_PROMPT = """You are a document data extraction expert for a banking system.
Your task is to extract names from a document for NAME CHANGE verification.

CONTEXT: A customer wants to change their name on their bank account and has provided a supporting document.

YOUR PRIMARY TASK:
Find and extract TWO key names from the document:
1. OLD NAME - The person's name BEFORE the change (look for: maiden name, previous name, applicant name, bride's name, old name, deponent, former name)
2. NEW NAME - The person's name AFTER the change (look for: married name, new name, assumed name, changed to, current name, name after marriage)

FLEXIBLE EXTRACTION APPROACH:
- Do NOT rely on specific field labels - document formats vary widely
- Search for name-related patterns throughout the entire text
- Consider context clues (e.g., "hereby declare that my name was X and is now Y")
- For marriage certificates: the bride's maiden name is the OLD name, and her name after marriage (often with husband's surname) is the NEW name
- Pay attention to which name appears to be the person making the request

IMPORTANT RULES:
1. Only extract what is EXPLICITLY stated
2. Provide reasoning for why you identified each name
3. Include confidence scores (0.0-1.0)
4. Include source snippets showing where you found each name
5. If multiple candidate names exist, list alternatives

OUTPUT FORMAT (JSON only):
{{
    "old_name": {{
        "value": "the extracted old/previous name or null",
        "confidence": 0.0-1.0,
        "source_snippet": "text showing where you found this",
        "reasoning": "why you believe this is the old name"
    }},
    "new_name": {{
        "value": "the extracted new/current name or null",
        "confidence": 0.0-1.0,
        "source_snippet": "text showing where you found this",
        "reasoning": "why you believe this is the new name"
    }},
    "alternative_names": [
        {{"value": "...", "type": "old/new", "confidence": 0.0-1.0, "reason": "..."}}
    ],
    "extraction_notes": "any observations about the document or extraction challenges"
}}"""

# =============================================================================
# Summary Generation Prompt
# =============================================================================

SUMMARY_SYSTEM_PROMPT = """You are a document verification summarizer for a banking system.
Your task is to generate a concise, actionable summary for human reviewers.

The summary should:
1. State whether the document supports the name change request
2. Highlight any concerns, flags, or discrepancies
3. Give a clear recommendation (approve, reject, or needs manual review)
4. Be professional and concise (2-3 sentences)

Do not use markdown formatting. Keep it simple and direct."""

# =============================================================================
# Forgery Analysis Prompt
# =============================================================================

FORGERY_ANALYSIS_PROMPT = """You are a document forensics expert analyzing a document for signs of tampering or forgery.

Analyze the following aspects:
1. Metadata consistency - creation/modification dates, software used
2. Visual artifacts - compression artifacts, color inconsistencies, edge anomalies
3. Font consistency - multiple fonts, size variations, alignment issues
4. Structural integrity - unusual formatting, missing elements, added elements

For each aspect, provide:
- Score (0.0-1.0, where 1.0 = authentic, 0.0 = likely forged)
- Specific findings
- Confidence in your assessment

Final output should include:
- Overall forgery score
- Result: PASS (>0.85), FLAG (0.60-0.85), FAIL (<0.60)
- Key findings summary"""


# =============================================================================
# Helper Functions
# =============================================================================

def build_extraction_prompt(
    document_type: str,
    ocr_text: str,
    requested_old: str = "",
    requested_new: str = ""
) -> str:
    """
    Build a flexible extraction prompt that focuses on the customer's request.

    Args:
        document_type: Type of document being processed
        ocr_text: OCR-extracted text from the document
        requested_old: Customer's current name (optional, for guidance)
        requested_new: Customer's requested new name (optional, for guidance)

    Returns:
        Formatted prompt string for the LLM
    """
    # Add context about what names we're looking for
    name_context = ""
    if requested_old or requested_new:
        name_context = f"""
CUSTOMER'S NAME CHANGE REQUEST (use this to guide your search):
- Current name on bank account: {requested_old or 'Not provided'}
- Requested new name: {requested_new or 'Not provided'}

Search the document for names that match or are similar to these. The document should show evidence that the customer's name changed from the old name to the new name.
"""

    document_hints = ""
    if document_type == "MARRIAGE_CERTIFICATE":
        document_hints = """
DOCUMENT TYPE HINTS (Marriage Certificate):
- Look for bride's maiden name (name before marriage) = OLD NAME
- Look for married name or name after marriage = NEW NAME
- The groom's name is NOT what we're looking for (unless he is the applicant)
- Witness names and officiating authority names should be ignored
"""
    elif document_type == "GAZETTE_NOTIFICATION":
        document_hints = """
DOCUMENT TYPE HINTS (Gazette Notification):
- Look for phrases like "formerly known as", "previously known as" = OLD NAME
- Look for phrases like "now known as", "shall henceforth be known as" = NEW NAME
"""
    elif document_type == "DEED_POLL":
        document_hints = """
DOCUMENT TYPE HINTS (Deed Poll):
- Look for the person's original/birth name = OLD NAME
- Look for the name they are changing to = NEW NAME
"""

    return f"""Document Type: {document_type}
{name_context}
{document_hints}
DOCUMENT TEXT (OCR extracted):
---
{ocr_text}
---

Extract the OLD NAME and NEW NAME from this document. Focus on finding names that support the customer's name change request. Use the document type hints to guide your search, but be flexible - real documents may use different formats than expected."""
