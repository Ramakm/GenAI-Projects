import json
import logging

from agents.state import RegulatoryAnalysisState, ExtractedClause
from core.llm import get_llm

logger = logging.getLogger(__name__)

CLAUSE_TYPES = [
    # Obligations
    "mandatory_requirement", "prohibition", "conditional_obligation", "permissive_action",
    # Temporal
    "compliance_deadline", "reporting_frequency", "transition_period",
    # Governance
    "board_oversight", "designated_officer", "third_party_oversight", "internal_audit",
    # Data/Systems
    "data_retention", "data_localization", "cybersecurity_control", "system_resilience",
    # Financial/Capital
    "capital_requirement", "liquidity_requirement", "stress_testing", "provisioning",
    # Disclosure
    "mandatory_disclosure", "regulatory_reporting", "consumer_notification", "incident_reporting",
    # Enforcement
    "penalty_enforcement", "remediation_requirement", "systemic_risk_trigger",
    # Healthcare-specific
    "clinical_protocol", "patient_safety", "product_approval", "labeling_requirement",
    "manufacturing_standard",
    # Cross-cutting
    "definition_scope", "exemption_exclusion", "cross_reference",
]

_EXTRACT_PROMPT = """You are a regulatory compliance expert. Extract all regulatory clauses from the text below.

VALID CLAUSE TYPES (use exactly as listed):
{clause_types}

For each clause, extract:
- clause_type: one type from the list above
- raw_text: verbatim quote from the text (max 300 characters)
- section_reference: section/article reference if visible (e.g. "Section 4.2", "Article 12")
- keywords: list of 2-5 key regulatory terms

Return ONLY a valid JSON object:
{{
  "clauses": [
    {{
      "clause_type": "mandatory_requirement",
      "raw_text": "exact quote from the regulation...",
      "section_reference": "Section 4.2(b)",
      "keywords": ["capital", "adequacy", "ratio"]
    }}
  ],
  "total_found": <integer>
}}

REGULATION: {regulation_name}

TEXT:
{text}

JSON:"""


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def _extract_from_chunk(chunk: str, regulation_name: str) -> list[dict]:
    llm = get_llm()
    prompt = _EXTRACT_PROMPT.format(
        clause_types=", ".join(CLAUSE_TYPES),
        regulation_name=regulation_name or "Unknown",
        text=chunk,
    )
    try:
        response = llm.invoke(prompt)
        raw = _strip_fences(response.content)
        data = json.loads(raw)
        return data.get("clauses", [])
    except Exception as e:
        logger.warning(f"Clause extraction chunk failed: {e}")
        return []


def _deduplicate(clauses: list[dict]) -> list[dict]:
    seen_texts = set()
    unique = []
    for clause in clauses:
        text_key = clause.get("raw_text", "")[:100].lower().strip()
        if text_key and text_key not in seen_texts:
            seen_texts.add(text_key)
            unique.append(clause)
    return unique


def extract_clauses(state: RegulatoryAnalysisState) -> RegulatoryAnalysisState:
    """Node 2: Extract regulatory clauses from parsed text."""
    parsed_text = state.get("parsed_text") or ""
    regulation_name = state.get("regulation_name") or "Unknown"
    progress = list(state.get("progress_messages", []))
    progress.append("Node 2 (Clause Extractor): Extracting regulatory clauses...")

    if not parsed_text:
        return {
            **state,
            "extracted_clauses": [],
            "current_agent": "clause_extractor",
            "progress_messages": progress,
            "error": "No text available for clause extraction",
        }

    all_raw_clauses = []
    chunk_size = 4000
    overlap = 500

    if len(parsed_text) > chunk_size:
        chunks = []
        start = 0
        while start < len(parsed_text):
            end = min(start + chunk_size, len(parsed_text))
            chunks.append(parsed_text[start:end])
            start += chunk_size - overlap

        for i, chunk in enumerate(chunks):
            progress.append(f"Processing chunk {i+1}/{len(chunks)}...")
            raw_clauses = _extract_from_chunk(chunk, regulation_name)
            all_raw_clauses.extend(raw_clauses)
            progress.append(f"Chunk {i+1}: found {len(raw_clauses)} clauses")
    else:
        all_raw_clauses = _extract_from_chunk(parsed_text, regulation_name)
        progress.append(f"Found {len(all_raw_clauses)} raw clauses")

    unique_clauses = _deduplicate(all_raw_clauses)

    # Assign sequential IDs and validate types
    extracted: list[ExtractedClause] = []
    for i, clause in enumerate(unique_clauses, 1):
        clause_type = clause.get("clause_type", "mandatory_requirement")
        if clause_type not in CLAUSE_TYPES:
            clause_type = "mandatory_requirement"
        extracted.append({
            "clause_id": f"C{i:03d}",
            "clause_type": clause_type,
            "raw_text": str(clause.get("raw_text", ""))[:300],
            "section_reference": clause.get("section_reference", ""),
            "keywords": clause.get("keywords", [])[:5],
        })

    if not extracted:
        return {
            **state,
            "extracted_clauses": [],
            "current_agent": "clause_extractor",
            "progress_messages": progress,
            "error": "No regulatory clauses extracted",
        }

    progress.append(f"Total unique clauses extracted: {len(extracted)}")
    return {
        **state,
        "extracted_clauses": extracted,
        "current_agent": "clause_extractor",
        "progress_messages": progress,
        "error": None,
    }
