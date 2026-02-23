import json
import logging

from agents.state import RegulatoryAnalysisState
from core.llm import get_llm

logger = logging.getLogger(__name__)

# Rule-based keyword sets
_FS_KEYWORDS = {
    "BASEL", "DORA", "MiFID", "AML", "KYC", "capital adequacy", "systemic risk",
    "liquidity coverage", "leverage ratio", "stress test", "CRD", "CRR",
    "Dodd-Frank", "Volcker", "FINRA", "prudential", "LIBOR", "SOFR",
}
_HC_KEYWORDS = {
    "FDA", "GMP", "clinical trial", "IND", "NDA", "HIPAA", "PHI",
    "adverse event", "pharmacovigilance", "GCP", "GLP", "510(k)", "PMA",
    "REMS", "bioequivalence", "drug substance", "medical device", "CE marking",
    "EHR", "HL7", "FHIR", "CMS", "Medicaid", "Medicare",
}
_FS_ISSUERS = {
    "Federal Reserve", "OCC", "FDIC", "EBA", "PRA", "FCA", "SEC",
    "CFPB", "CFTC", "FinCEN", "BIS", "FSB", "FINMA", "BaFin",
}
_HC_ISSUERS = {
    "FDA", "EMA", "WHO", "CMS", "MHRA", "TGA", "Health Canada",
    "ICH", "NIH", "CDC",
}

# Sub-domain keywords
_FS_SUB_DOMAINS = {
    "banking_capital": ["capital requirement", "Basel", "RWA", "Tier 1", "CET1", "ICAAP", "leverage ratio"],
    "payments_settlement": ["payment system", "settlement", "intraday liquidity", "TARGET2", "SWIFT"],
    "consumer_protection": ["consumer", "UDAAP", "fair lending", "disclosure", "complaint", "CFPB"],
    "aml_kyc": ["AML", "KYC", "beneficial owner", "SAR", "transaction monitoring", "FinCEN"],
    "data_privacy_fintech": ["data governance", "open banking", "PSD2", "GDPR", "third-party", "API"],
}
_HC_SUB_DOMAINS = {
    "pharma_clinical_trials": ["clinical trial", "IND", "NDA", "BLA", "GCP", "protocol", "investigator"],
    "medical_devices": ["medical device", "510(k)", "PMA", "UDI", "design control", "CE marking"],
    "data_privacy_hipaa": ["HIPAA", "PHI", "ePHI", "Business Associate", "breach notification", "EHR"],
    "pharmacovigilance": ["adverse event", "pharmacovigilance", "REMS", "signal detection", "FAERS"],
    "billing_coding": ["ICD", "CPT", "claims", "billing", "revenue cycle", "coding", "Medicaid"],
}

_CLASSIFY_PROMPT = """Classify this regulatory document into an industry and sub-domain.

DOCUMENT EXCERPT:
Regulation: {regulation_name}
Issuing Body: {issuing_body}
Text sample: {text_sample}

Return ONLY a valid JSON object:
{{
  "industry": "financial_services" or "healthcare" or "other",
  "sub_domain": one of the sub-domains listed below,
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation"
}}

Financial Services sub-domains: banking_capital, payments_settlement, consumer_protection, aml_kyc, data_privacy_fintech
Healthcare sub-domains: pharma_clinical_trials, medical_devices, data_privacy_hipaa, pharmacovigilance, billing_coding

JSON:"""


def _rule_based_classify(
    text: str,
    regulation_name: str,
    issuing_body: str,
) -> tuple[str | None, float]:
    """Return (industry, confidence) using keyword rules. None if below threshold."""
    combined = f"{regulation_name or ''} {issuing_body or ''} {text[:3000]}".lower()
    upper_combined = f"{regulation_name or ''} {issuing_body or ''} {text[:3000]}"

    fs_hits = sum(1 for kw in _FS_KEYWORDS if kw.lower() in combined)
    hc_hits = sum(1 for kw in _HC_KEYWORDS if kw.lower() in combined)
    fs_issuer_hits = sum(1 for iss in _FS_ISSUERS if iss.lower() in combined)
    hc_issuer_hits = sum(1 for iss in _HC_ISSUERS if iss.lower() in combined)

    fs_score = fs_hits * 0.1 + fs_issuer_hits * 0.3
    hc_score = hc_hits * 0.1 + hc_issuer_hits * 0.3

    fs_conf = min(fs_score, 1.0)
    hc_conf = min(hc_score, 1.0)

    if fs_conf >= 0.7 and fs_conf > hc_conf:
        return "financial_services", fs_conf
    if hc_conf >= 0.7 and hc_conf > fs_conf:
        return "healthcare", hc_conf
    return None, max(fs_conf, hc_conf)


def _detect_sub_domain(industry: str, text: str) -> str:
    combined = text[:5000].lower()
    if industry == "financial_services":
        scores = {sd: sum(1 for kw in kws if kw.lower() in combined)
                  for sd, kws in _FS_SUB_DOMAINS.items()}
    elif industry == "healthcare":
        scores = {sd: sum(1 for kw in kws if kw.lower() in combined)
                  for sd, kws in _HC_SUB_DOMAINS.items()}
    else:
        return "general"

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def classify_industry(state: RegulatoryAnalysisState) -> RegulatoryAnalysisState:
    """Node 3: Classify industry and sub-domain using rules first, LLM fallback."""
    parsed_text = state.get("parsed_text") or ""
    clauses = state.get("extracted_clauses", [])
    user_industry = state.get("industry", "auto")
    regulation_name = state.get("regulation_name") or ""
    issuing_body = state.get("issuing_body") or ""

    progress = list(state.get("progress_messages", []))
    progress.append("Node 3 (Industry Classifier): Classifying industry and sub-domain...")

    # If user explicitly specified (not auto), trust it with high confidence
    if user_industry in ("financial_services", "healthcare"):
        sub_domain = _detect_sub_domain(user_industry, parsed_text)
        progress.append(f"User-specified industry: {user_industry}, sub-domain: {sub_domain}")
        return {
            **state,
            "detected_industry": user_industry,
            "detected_sub_domain": sub_domain,
            "industry_confidence": 1.0,
            "current_agent": "industry_classifier",
            "progress_messages": progress,
        }

    # Build text for classification
    clause_text = " ".join(c.get("raw_text", "") for c in clauses[:10])
    combined_text = f"{parsed_text} {clause_text}"

    # Rule-based first
    industry, confidence = _rule_based_classify(combined_text, regulation_name, issuing_body)

    if industry and confidence >= 0.7:
        sub_domain = _detect_sub_domain(industry, combined_text)
        progress.append(
            f"Rule-based classification: {industry} (conf={confidence:.2f}), sub-domain: {sub_domain}"
        )
        return {
            **state,
            "detected_industry": industry,
            "detected_sub_domain": sub_domain,
            "industry_confidence": confidence,
            "current_agent": "industry_classifier",
            "progress_messages": progress,
        }

    # LLM fallback
    progress.append(f"Rule confidence {confidence:.2f} < 0.7, using LLM classifier...")
    llm = get_llm()
    text_sample = combined_text[:1500]
    prompt = _CLASSIFY_PROMPT.format(
        regulation_name=regulation_name,
        issuing_body=issuing_body,
        text_sample=text_sample,
    )
    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())

        detected_industry = data.get("industry", "financial_services")
        if detected_industry not in ("financial_services", "healthcare"):
            detected_industry = "financial_services"
        llm_confidence = float(data.get("confidence", 0.6))
        sub_domain = data.get("sub_domain") or _detect_sub_domain(detected_industry, combined_text)

        progress.append(
            f"LLM classification: {detected_industry} (conf={llm_confidence:.2f}), sub-domain: {sub_domain}"
        )
        return {
            **state,
            "detected_industry": detected_industry,
            "detected_sub_domain": sub_domain,
            "industry_confidence": llm_confidence,
            "current_agent": "industry_classifier",
            "progress_messages": progress,
        }
    except Exception as e:
        logger.warning(f"LLM classification failed: {e}, defaulting to financial_services")
        return {
            **state,
            "detected_industry": "financial_services",
            "detected_sub_domain": "general",
            "industry_confidence": 0.4,
            "current_agent": "industry_classifier",
            "progress_messages": progress,
        }
