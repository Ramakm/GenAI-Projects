def get_simulation_report_prompt(state: dict) -> str:
    title = state.get("decision_title", "Strategic Decision")
    decision_text = state.get("decision_text", "")
    decision_type = state.get("decision_type", "unknown")
    decision_domain = state.get("decision_domain", "")
    decision_framing = state.get("decision_framing", "")
    industry_context = state.get("industry_context", "")
    time_horizon = state.get("time_horizon", "medium_term")
    scenarios = state.get("scenarios", [])
    outcome_projections = state.get("outcome_projections", [])
    risk_factors = state.get("risk_factors", [])
    expected_value_pct = state.get("expected_value_pct", 0.0)
    expected_roi = state.get("expected_roi", 0.0)
    overall_risk_score = state.get("overall_risk_score", 0.0)

    # Build scenario table
    scenario_rows = []
    for s in scenarios:
        assumptions = "; ".join(s.get("key_assumptions", [])[:3])
        scenario_rows.append(
            f"| {s['name']} | {s['probability']:.0%} | {s.get('macro_conditions','')[:60]} | {assumptions[:80]} |"
        )
    scenario_table = "\n".join(scenario_rows) if scenario_rows else "| No scenarios |"

    # Build outcome table
    outcome_map = {o["scenario_id"]: o for o in outcome_projections}
    outcome_rows = []
    for s in scenarios:
        o = outcome_map.get(s["scenario_id"], {})
        outcome_rows.append(
            f"| {s['name']} | {o.get('revenue_impact_pct', 0):+.1f}% "
            f"({o.get('revenue_impact_low', 0):+.1f}% to {o.get('revenue_impact_high', 0):+.1f}%) "
            f"| {o.get('cost_impact_pct', 0):+.1f}% "
            f"| {o.get('roi_estimate', 0):+.1f}% "
            f"| {o.get('success_probability', 0):.0%} "
            f"| {o.get('npv_qualitative', 'uncertain')} |"
        )
    outcome_table = "\n".join(outcome_rows) if outcome_rows else "| No outcomes |"

    # Build top-5 risk table
    top_risks = sorted(risk_factors, key=lambda r: r.get("risk_score", 0), reverse=True)[:5]
    risk_rows = []
    for r in top_risks:
        risk_rows.append(
            f"| {r['name']} | {r['category']} | {r.get('likelihood', 0):.2f} "
            f"| {r.get('impact', 0):.2f} | {r.get('risk_score', 0):.2f} | {r.get('mitigation','')[:80]} |"
        )
    risk_table = "\n".join(risk_rows) if risk_rows else "| No risks identified |"

    return f"""You are a strategic management consultant generating a comprehensive simulation report.

Decision: {title}
Industry Context: {industry_context}
Decision Type: {decision_type}
Domain: {decision_domain}
Time Horizon: {time_horizon}
Decision Description: {decision_text}

Decision Framing: {decision_framing}

Scenario Summary:
| Scenario | Probability | Macro Conditions | Key Assumptions |
|----------|-------------|-----------------|-----------------|
{scenario_table}

Outcome Projections:
| Scenario | Revenue Impact | Cost Impact | ROI | Success % | NPV |
|----------|---------------|-------------|-----|-----------|-----|
{outcome_table}

Probability-Weighted Expected Value: {expected_value_pct:+.2f}% revenue impact
Expected ROI: {expected_roi:+.2f}%

Top-5 Risk Factors:
| Risk | Category | Likelihood | Impact | Score | Mitigation |
|------|----------|------------|--------|-------|------------|
{risk_table}

Overall Risk Score: {overall_risk_score:.2f} / 1.00

Generate a comprehensive strategic simulation report in Markdown with the following sections:

# Strategic Simulation Report: {title}

## Executive Summary
(3-4 paragraphs covering decision overview, key findings, probability-weighted outcomes, and primary recommendation rationale)

## Decision Analysis
(Detailed framing: decision type, domain, key parameters, and what makes this decision significant)

## Scenario Overview
(Prose description of each scenario — Bull Case, Base Case, Bear Case, Tail Risk — with the scenario table)

| Scenario | Probability | Macro Conditions | Key Assumptions |
|----------|-------------|-----------------|-----------------|
{scenario_table}

## Outcome Projections
(Interpretation of projected outcomes per scenario)

| Scenario | Revenue Impact | Cost Impact | ROI | Success % | NPV |
|----------|---------------|-------------|-----|-----------|-----|
{outcome_table}

## Probability-Weighted Expected Value
(Analysis of EV = {expected_value_pct:+.2f}% and what it means for the decision)

## Risk Assessment
(Risk landscape overview, category breakdown, top risks)

| Risk | Category | Likelihood | Impact | Score | Mitigation |
|------|----------|------------|--------|-------|------------|
{risk_table}

## Sensitivity Analysis
(Which variables most affect outcomes; how changing key assumptions shifts the EV)

## Strategic Recommendation
(Clear recommendation with rationale, confidence level, and conditions)

## Implementation Roadmap
(If proceeding: phased milestones, quick wins, key dependencies, governance checkpoints)

Write in clear, professional consulting language. Be specific and quantitative where possible."""
