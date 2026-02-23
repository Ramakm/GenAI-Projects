def get_report_prompt(state: dict) -> str:
    topic = state.get("topic", "Unknown Topic")
    query = state.get("query", "")
    time_window = state.get("time_window", "7d")
    article_count = state.get("article_count", 0)
    sources_found = state.get("sources_found", [])
    overall_sentiment = state.get("overall_sentiment", "neutral")
    overall_score = state.get("overall_sentiment_score", 0.0)
    distribution = state.get("sentiment_distribution", {})
    by_source = state.get("sentiment_by_source", {})
    shift_signal = state.get("sentiment_shift_signal", "stable")
    narratives = state.get("narratives", [])
    patterns = state.get("narrative_patterns", [])
    map_summary = state.get("narrative_map_summary", "")
    key_actors = state.get("key_actors", [])
    key_claims = state.get("key_claims", [])

    # Sentiment distribution table
    dist_rows = "\n".join(
        f"| {cat.capitalize()} | {pct:.0%} |"
        for cat, pct in sorted(distribution.items(), key=lambda x: -x[1])
    )

    # Source sentiment table
    src_rows = "\n".join(
        f"| {src} | {score:+.2f} | {'Positive' if score > 0.1 else 'Negative' if score < -0.1 else 'Neutral'} |"
        for src, score in sorted(by_source.items(), key=lambda x: -x[1])[:10]
    )

    # Narrative summary
    narrative_lines = "\n".join(
        f"- **{n['title']}** [{n['narrative_type'].upper()}] (momentum: {n['momentum']:.0%}): {n['description'][:120]}"
        for n in narratives[:8]
    )

    # Pattern summary
    pattern_lines = "\n".join(
        f"- **{p['pattern_type'].replace('_',' ').title()}** (strength: {p['strength']:.0%}): {p['description'][:100]}"
        for p in patterns
    )

    return f"""You are a senior narrative intelligence analyst. Write a comprehensive intelligence brief.

Topic: {topic}
Query: {query}
Time Window: {time_window}
Sources Analyzed: {article_count} articles from {len(sources_found)} sources: {', '.join(sources_found[:8])}

SENTIMENT LANDSCAPE
Overall Sentiment: {overall_sentiment.upper()} (score: {overall_score:+.2f})
Sentiment Shift Signal: {shift_signal.replace('_', ' ').upper()}

Sentiment Distribution:
| Category | Share |
|----------|-------|
{dist_rows}

Sentiment by Source:
| Source | Score | Direction |
|--------|-------|-----------|
{src_rows}

NARRATIVES IDENTIFIED ({len(narratives)} total):
{narrative_lines}

NARRATIVE PATTERNS:
{pattern_lines}

Narrative Landscape Summary:
{map_summary}

KEY ACTORS: {', '.join(key_actors[:10])}
KEY CLAIMS: {'; '.join(key_claims[:5])}

Write a comprehensive intelligence brief in Markdown with these exact sections:

# Narrative Intelligence Brief: {topic}

## Executive Summary
(3-4 paragraphs: what is being said, how it is being said, what is shifting, and what it means)

## Sentiment Landscape
(Analysis of the sentiment data — overall tone, source-by-source breakdown, shift signals, what is driving the emotional valence)

| Source | Sentiment Score | Direction |
|--------|----------------|-----------|
{src_rows}

## Narrative Analysis

### Dominant Narratives
(Deep analysis of the most prominent narratives — who is promoting them, what claims they make, what actors they feature)

### Emerging & Contested Narratives
(Narratives gaining traction or under active dispute — why they matter and what they signal)

## Narrative Pattern Map
(Analysis of how narratives interact — convergence, echo chambers, divergence points, amplification)

## Key Actors & Claims
(Who appears most across narratives; which claims are repeated vs. contested)

## Signal Detection
### Momentum Signals
(Which narratives are accelerating; early warning indicators)

### Divergence Points
(Where sources fundamentally disagree; contested facts; framing wars)

## Strategic Implications
(What this narrative landscape means for decision-makers, communicators, or researchers)

## Monitoring Recommendations
(What to watch next; leading indicators; sources to prioritize)

Write in clear, analytical prose. Be specific — cite narrative titles, actor names, and source names. Avoid generic statements."""
