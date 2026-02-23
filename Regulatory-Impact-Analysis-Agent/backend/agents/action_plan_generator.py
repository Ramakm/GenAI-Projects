import json
import logging

from agents.state import RegulatoryAnalysisState, ActionItem
from core.llm import get_llm
from core.templates.financial_services import get_fs_action_plan_template
from core.templates.healthcare import get_hc_action_plan_template

logger = logging.getLogger(__name__)

_PRIORITY_ORDER = {"immediate": 0, "short_term": 1, "long_term": 2}
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _build_clauses_summary(clauses, impact_scores) -> str:
    score_lookup = {s["clause_id"]: s for s in impact_scores}
    lines = []
    for clause in clauses[:20]:  # Cap at 20 for prompt size
        cid = clause["clause_id"]
        score = score_lookup.get(cid, {})
        severity = score.get("severity", "medium")
        lines.append(
            f"[{cid}] ({clause['clause_type']}, {severity}) "
            f"{clause['section_reference']}: {clause['raw_text'][:200]}"
        )
    return "\n".join(lines)


def _build_impact_summary(impact_scores) -> str:
    lines = []
    for s in impact_scores[:20]:
        lines.append(
            f"[{s['clause_id']}] {s['severity'].upper()} ({s['severity_score']:.2f}): "
            f"Affects {', '.join(s['affected_functions'][:3])}. {s['reasoning'][:150]}"
        )
    return "\n".join(lines)


def _build_action_items(
    clauses, impact_scores, industry: str
) -> list[ActionItem]:
    score_lookup = {s["clause_id"]: s for s in impact_scores}

    action_items: list[ActionItem] = []
    for i, clause in enumerate(clauses, 1):
        cid = clause["clause_id"]
        score = score_lookup.get(cid, {})
        severity = score.get("severity", "medium")
        severity_score = score.get("severity_score", 0.5)
        affected_functions = score.get("affected_functions", [])
        responsible = affected_functions[0] if affected_functions else "Compliance & Legal"

        if severity in ("critical", "high"):
            priority = "immediate"
            effort = "2-4 weeks"
        elif severity == "medium":
            priority = "short_term"
            effort = "1-3 months"
        else:
            priority = "long_term"
            effort = "3-6 months"

        action_items.append({
            "action_id": f"A{i:03d}",
            "clause_id": cid,
            "priority": priority,
            "responsible_function": responsible,
            "description": (
                f"Implement compliance measures for {clause['clause_type'].replace('_', ' ')} "
                f"({clause['section_reference']}): {clause['raw_text'][:150]}"
            ),
            "estimated_effort": effort,
            "dependencies": [],
        })

    # Sort: priority first, then severity_score desc
    action_items.sort(key=lambda a: (
        _PRIORITY_ORDER.get(a["priority"], 3),
        -score_lookup.get(a["clause_id"], {}).get("severity_score", 0.5),
    ))
    return action_items


def generate_action_plan(state: RegulatoryAnalysisState) -> RegulatoryAnalysisState:
    """Node 5: Generate industry-specific compliance action plan."""
    clauses = state.get("extracted_clauses", [])
    impact_scores = state.get("impact_scores", [])
    industry = state.get("detected_industry") or "financial_services"
    sub_domain = state.get("detected_sub_domain") or "general"

    progress = list(state.get("progress_messages", []))
    progress.append(f"Node 5 (Action Plan Generator): Generating {industry} action plan...")

    # Severity counts
    severity_counts = {k: sum(1 for s in impact_scores if s["severity"] == k)
                       for k in ("critical", "high", "medium", "low")}

    clauses_summary = _build_clauses_summary(clauses, impact_scores)
    impact_summary = _build_impact_summary(impact_scores)

    # Build structured action items
    action_items = _build_action_items(clauses, impact_scores, industry)

    # Select template
    kwargs = dict(
        regulation_name=state.get("regulation_name") or "",
        issuing_body=state.get("issuing_body") or "",
        effective_date=state.get("effective_date") or "",
        sub_domain=sub_domain,
        jurisdiction=state.get("jurisdiction") or "",
        clauses_summary=clauses_summary,
        impact_summary=impact_summary,
        critical_count=severity_counts["critical"],
        high_count=severity_counts["high"],
        medium_count=severity_counts["medium"],
        low_count=severity_counts["low"],
    )

    if industry == "healthcare":
        prompt = get_hc_action_plan_template(**kwargs)
    else:
        prompt = get_fs_action_plan_template(**kwargs)

    llm = get_llm()
    try:
        response = llm.invoke(prompt)
        action_plan_markdown = response.content.strip()
    except Exception as e:
        logger.error(f"Action plan generation failed: {e}")
        action_plan_markdown = (
            f"# Compliance Action Plan\n\n"
            f"**Error:** Action plan generation failed: {e}\n\n"
            f"**Clauses Found:** {len(clauses)}\n"
            f"**Critical Issues:** {severity_counts['critical']}\n"
            f"**High Issues:** {severity_counts['high']}\n"
        )

    progress.append("Action plan generated successfully")

    return {
        **state,
        "action_items": action_items,
        "action_plan_markdown": action_plan_markdown,
        "current_agent": "action_plan_generator",
        "progress_messages": progress,
    }
