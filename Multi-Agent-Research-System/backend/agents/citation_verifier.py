import json
import logging

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE
from agents.state import ResearchState, CitationResult, SourceInfo

logger = logging.getLogger(__name__)


def _domain_score(domain: str) -> float:
    """Rule-based domain credibility score."""
    domain = domain.lower()
    if domain.endswith(".edu") or domain.endswith(".gov"):
        return 0.7
    if domain.endswith(".org"):
        return 0.6
    return 0.4


def _assess_relevance(
    source: SourceInfo,
    topic: str,
    llm: ChatOllama,
) -> tuple[float, str]:
    """LLM call to assess relevance and credibility. Returns (score, reasoning)."""
    claims_text = "\n".join(f"- {c}" for c in source["key_claims"]) or "(no claims extracted)"
    prompt = (
        f"You are evaluating research sources for credibility and relevance.\n\n"
        f"Research topic: {topic}\n"
        f"Source domain: {source['domain']}\n"
        f"Extracted claims:\n{claims_text}\n\n"
        f"Rate the relevance (0.0–1.0) of these claims to the topic. "
        f"Assess credibility (are claims specific, evidence-based, verifiable?). "
        f"Respond with JSON only in this exact format: "
        f'{{\"relevance\": 0.0, \"reasoning\": \"your assessment here\"}}'
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        relevance = float(data.get("relevance", 0.5))
        relevance = max(0.0, min(1.0, relevance))
        reasoning = str(data.get("reasoning", ""))
        return relevance, reasoning
    except Exception as e:
        logger.warning(f"Failed to parse relevance JSON for {source['domain']}: {e}")
        return 0.5, "Could not assess relevance."


def verify_citations(state: ResearchState) -> ResearchState:
    """Agent 2: Score each successfully fetched source for credibility and relevance."""
    topic = state["topic"]
    sources = state["sources"]
    citations: list[CitationResult] = []
    progress: list[str] = list(state.get("progress_messages", []))

    usable_sources = [s for s in sources if s["fetch_error"] is None]
    progress.append(
        f"[citation_verifier] Starting — verifying {len(usable_sources)} source(s)..."
    )

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=LLM_TEMPERATURE,
    )

    for source in usable_sources:
        domain = source["domain"]
        logger.info(f"Verifying: {domain}")

        d_score = _domain_score(domain)
        relevance_score, reasoning = _assess_relevance(source, topic, llm)

        # Composite: domain_score * 0.3 + relevance_score * 0.7
        confidence = round(d_score * 0.3 + relevance_score * 0.7, 4)
        is_usable = confidence >= 0.3

        citation: CitationResult = {
            "url": source["url"],
            "domain": domain,
            "key_claims": source["key_claims"],
            "confidence_score": confidence,
            "credibility_reasoning": reasoning,
            "domain_score": d_score,
            "relevance_score": relevance_score,
            "is_usable": is_usable,
        }
        citations.append(citation)
        progress.append(
            f"[citation_verifier] {domain}: confidence={confidence:.2f} "
            f"(domain={d_score:.1f}, relevance={relevance_score:.2f}) "
            f"{'✓ usable' if is_usable else '✗ low-confidence'}"
        )
        logger.info(
            f"{domain}: confidence={confidence:.2f}, is_usable={is_usable}"
        )

    usable_count = sum(1 for c in citations if c["is_usable"])
    avg = (
        sum(c["confidence_score"] for c in citations if c["is_usable"]) / usable_count
        if usable_count > 0
        else 0.0
    )
    progress.append(
        f"[citation_verifier] Complete — {usable_count}/{len(citations)} usable, "
        f"avg confidence={avg:.2f}"
    )

    return {
        **state,
        "citations": citations,
        "progress_messages": progress,
        "current_agent": "citation_verifier",
    }
