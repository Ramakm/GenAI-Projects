import json
import logging

from agents.state import RegulatoryAnalysisState, ImpactScore
from core.llm import get_llm

logger = logging.getLogger(__name__)

# Severity floor rule
_FLOOR_HIGH_TYPES = {"penalty_enforcement", "mandatory_disclosure", "systemic_risk_trigger"}

_FS_FUNCTIONS = [
    "Risk Management", "Capital Planning", "Compliance & Legal",
    "IT & Cybersecurity", "Operations", "Treasury",
    "Audit", "Customer Onboarding", "Reporting & Disclosure",
]
_HC_FUNCTIONS = [
    "Clinical Operations", "Quality Assurance", "Regulatory Affairs",
    "IT & Data Systems", "Pharmacovigilance", "Medical Affairs",
    "Finance & Billing", "Patient Safety",
]

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_ASSESS_PROMPT = """You are a regulatory compliance expert. Assess the impact severity of these regulatory clauses.

INDUSTRY: {industry}
EFFECTIVE DATE: {effective_date}
AVAILABLE BUSINESS FUNCTIONS: {functions}

CLAUSES TO ASSESS:
{clauses_json}

For each clause, provide a severity assessment. Return ONLY a valid JSON array:
[
  {{
    "clause_id": "C001",
    "severity": "critical" or "high" or "medium" or "low",
    "severity_score": 0.0 to 1.0,
    "affected_functions": ["function1", "function2"],
    "compliance_deadline": "date or null",
    "reasoning": "brief explanation of impact"
  }}
]

Use these severity guidelines:
- critical (0.85-1.0): Immediate legal/financial risk, potential license revocation, patient safety threat
- high (0.65-0.84): Significant compliance burden, financial penalties likely if missed
- medium (0.40-0.64): Moderate effort required, manageable compliance risk
- low (0.0-0.39): Administrative, informational, or low-risk requirement

JSON array:"""


def _apply_severity_floor(score: ImpactScore, clause_type: str) -> ImpactScore:
    if clause_type in _FLOOR_HIGH_TYPES:
        if _SEVERITY_ORDER.get(score["severity"], 3) > _SEVERITY_ORDER["high"]:
            score = {**score, "severity": "high", "severity_score": max(score["severity_score"], 0.65)}
    return score


def assess_impact(state: RegulatoryAnalysisState) -> RegulatoryAnalysisState:
    """Node 4: Score impact severity for each extracted clause."""
    clauses = state.get("extracted_clauses", [])
    industry = state.get("detected_industry") or "financial_services"
    sub_domain = state.get("detected_sub_domain") or "general"
    effective_date = state.get("effective_date") or "TBD"

    progress = list(state.get("progress_messages", []))
    progress.append(f"Node 4 (Impact Assessor): Assessing {len(clauses)} clauses...")

    functions = _FS_FUNCTIONS if industry == "financial_services" else _HC_FUNCTIONS
    batch_size = 5
    all_scores: list[ImpactScore] = []

    llm = get_llm()

    # Build a lookup for clause_type by clause_id
    type_lookup = {c["clause_id"]: c["clause_type"] for c in clauses}

    for i in range(0, len(clauses), batch_size):
        batch = clauses[i:i + batch_size]
        clauses_json = json.dumps([{
            "clause_id": c["clause_id"],
            "clause_type": c["clause_type"],
            "raw_text": c["raw_text"],
            "section_reference": c["section_reference"],
            "keywords": c["keywords"],
        } for c in batch], indent=2)

        prompt = _ASSESS_PROMPT.format(
            industry=industry,
            effective_date=effective_date,
            functions=", ".join(functions),
            clauses_json=clauses_json,
        )

        try:
            response = llm.invoke(prompt)
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            scores_data = json.loads(raw)

            for item in scores_data:
                clause_id = item.get("clause_id", "")
                severity = item.get("severity", "medium")
                if severity not in _SEVERITY_ORDER:
                    severity = "medium"
                severity_score = float(item.get("severity_score", 0.5))
                severity_score = max(0.0, min(1.0, severity_score))

                score: ImpactScore = {
                    "clause_id": clause_id,
                    "severity": severity,
                    "severity_score": severity_score,
                    "affected_functions": item.get("affected_functions", [])[:4],
                    "compliance_deadline": item.get("compliance_deadline"),
                    "reasoning": item.get("reasoning", ""),
                }

                clause_type = type_lookup.get(clause_id, "")
                score = _apply_severity_floor(score, clause_type)
                all_scores.append(score)

            progress.append(
                f"Batch {i//batch_size + 1}: assessed {len(scores_data)} clauses"
            )

        except Exception as e:
            logger.warning(f"Impact assessment batch {i//batch_size + 1} failed: {e}")
            # Fallback: assign medium to all in batch
            for c in batch:
                score: ImpactScore = {
                    "clause_id": c["clause_id"],
                    "severity": "medium",
                    "severity_score": 0.5,
                    "affected_functions": [functions[0]],
                    "compliance_deadline": None,
                    "reasoning": "Assessment failed; defaulted to medium",
                }
                score = _apply_severity_floor(score, c["clause_type"])
                all_scores.append(score)

    counts = {k: sum(1 for s in all_scores if s["severity"] == k) for k in _SEVERITY_ORDER}
    progress.append(
        f"Impact assessment complete: critical={counts['critical']}, "
        f"high={counts['high']}, medium={counts['medium']}, low={counts['low']}"
    )

    return {
        **state,
        "impact_scores": all_scores,
        "current_agent": "impact_assessor",
        "progress_messages": progress,
    }
