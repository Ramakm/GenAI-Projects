import json
import time

import pandas as pd
import requests
import streamlit as st

from config import (
    HEALTH_ENDPOINT,
    SIMULATE_ENDPOINT,
    STREAM_ENDPOINT,
    DECISIONS_ENDPOINT,
)

st.set_page_config(
    page_title="Strategic Simulation Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Session state initialisation
# ──────────────────────────────────────────────
for key, default in [
    ("simulation_result", None),
    ("agent_statuses", {}),
    ("agent_messages", {}),
    ("streaming_report", ""),
    ("simulation_done", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
AGENT_ORDER = [
    "decision_framer",
    "scenario_generator",
    "outcome_simulator",
    "risk_analyzer",
    "report_generator",
]

AGENT_LABELS = {
    "decision_framer": "Decision Framer",
    "scenario_generator": "Scenario Generator",
    "outcome_simulator": "Outcome Simulator",
    "risk_analyzer": "Risk Analyzer",
    "report_generator": "Report Generator",
}

RECOMMENDATION_BADGES = {
    "proceed": ("Proceed", "green"),
    "proceed_with_caution": ("Proceed with Caution", "orange"),
    "defer": ("Defer", "red"),
    "do_not_proceed": ("Do Not Proceed", "red"),
}

TIME_HORIZON_LABELS = {
    "short_term": "Short-term (<1yr)",
    "medium_term": "Medium-term (1–3yr)",
    "long_term": "Long-term (3–5yr+)",
}


@st.cache_data(ttl=30)
def fetch_health() -> dict:
    try:
        r = requests.get(HEALTH_ENDPOINT, timeout=5)
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "ollama_connected": False, "model_available": False, "error": str(e)}


def render_agent_status(statuses: dict, messages: dict):
    cols = st.columns(len(AGENT_ORDER))
    for col, agent in zip(cols, AGENT_ORDER):
        status = statuses.get(agent, "pending")
        label = AGENT_LABELS[agent]
        msg = messages.get(agent, "")
        icon = {"pending": "⏳", "running": "🔄", "done": "✅", "error": "❌"}.get(status, "⏳")
        col.metric(label=f"{icon} {label}", value=status.upper(), delta=msg[:30] if msg else None)


def _scenario_color(name: str) -> str:
    return {"Bull Case": "#22c55e", "Base Case": "#3b82f6",
            "Bear Case": "#f97316", "Tail Risk": "#ef4444"}.get(name, "#6b7280")


def run_streaming_simulation(
    decision_text: str,
    decision_title: str,
    industry_context: str,
    time_horizon: str,
):
    st.session_state.agent_statuses = {a: "pending" for a in AGENT_ORDER}
    st.session_state.agent_messages = {a: "" for a in AGENT_ORDER}
    st.session_state.streaming_report = ""
    st.session_state.simulation_result = None
    st.session_state.simulation_done = False

    payload = {
        "decision_text": decision_text,
        "decision_title": decision_title,
        "industry_context": industry_context,
        "time_horizon": time_horizon,
    }

    progress_placeholder = st.empty()
    report_placeholder = st.empty()
    status_placeholder = st.empty()

    with requests.post(STREAM_ENDPOINT, json=payload, stream=True, timeout=300) as resp:
        if resp.status_code != 200:
            st.error(f"Backend error: {resp.status_code} — {resp.text}")
            return

        token_buffer = ""
        token_count = 0

        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            event = data.get("event")

            if event == "agent_start":
                agent = data.get("agent", "")
                if agent in st.session_state.agent_statuses:
                    st.session_state.agent_statuses[agent] = "running"
                    st.session_state.agent_messages[agent] = data.get("message", "")
                with progress_placeholder.container():
                    render_agent_status(st.session_state.agent_statuses, st.session_state.agent_messages)

            elif event == "agent_complete":
                agent = data.get("agent", "")
                if agent in st.session_state.agent_statuses:
                    st.session_state.agent_statuses[agent] = "done"
                with progress_placeholder.container():
                    render_agent_status(st.session_state.agent_statuses, st.session_state.agent_messages)

            elif event == "agent_update":
                pass  # internal updates, no UI change needed

            elif event == "token":
                token = data.get("token", "")
                token_buffer += token
                token_count += 1
                if token_count % 20 == 0:
                    st.session_state.streaming_report = token_buffer
                    report_placeholder.markdown(token_buffer)

            elif event == "done":
                st.session_state.streaming_report = token_buffer
                report_placeholder.markdown(token_buffer)
                result = data.get("result", {})
                st.session_state.simulation_result = result
                st.session_state.simulation_done = True
                for agent in AGENT_ORDER:
                    if st.session_state.agent_statuses.get(agent) == "running":
                        st.session_state.agent_statuses[agent] = "done"
                with progress_placeholder.container():
                    render_agent_status(st.session_state.agent_statuses, st.session_state.agent_messages)

            elif event == "error":
                agent = data.get("agent", "")
                msg = data.get("message", "Unknown error")
                if agent in st.session_state.agent_statuses:
                    st.session_state.agent_statuses[agent] = "error"
                    st.session_state.agent_messages[agent] = msg
                st.error(f"Error in {agent}: {msg}")
                with progress_placeholder.container():
                    render_agent_status(st.session_state.agent_statuses, st.session_state.agent_messages)


def render_results(result: dict):
    scenarios = result.get("scenarios", [])
    projections = result.get("outcome_projections", [])
    risk_factors = result.get("risk_factors", [])

    # Decision banner
    rec = result.get("strategic_recommendation", "")
    rec_label, rec_color = RECOMMENDATION_BADGES.get(rec, (rec, "gray"))
    conf = result.get("confidence_level", "")
    ev = result.get("expected_value_pct")
    roi = result.get("expected_roi")

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.info(f"**Type:** {result.get('decision_type', '—')}")
    col2.info(f"**Domain:** {result.get('decision_domain', '—')[:40]}")
    col3.info(f"**Horizon:** {TIME_HORIZON_LABELS.get(result.get('time_horizon',''), '—')}")
    col4.info(f"**Confidence:** {conf.upper() if conf else '—'}")

    # Scenario probability summary
    st.subheader("Scenario Probabilities")
    prob_cols = st.columns(4)
    for col, s in zip(prob_cols, scenarios):
        col.metric(
            label=s["name"],
            value=f"{s['probability']:.0%}",
            delta=s.get("macro_conditions", "")[:40],
        )

    # EV and ROI metrics
    ev_cols = st.columns(3)
    ev_cols[0].metric("Expected Value (EV)", f"{ev:+.2f}%" if ev is not None else "—")
    ev_cols[1].metric("Expected ROI", f"{roi:+.2f}%" if roi is not None else "—")
    ev_cols[2].metric(
        "Strategic Recommendation",
        rec_label,
        delta=f"Confidence: {conf}" if conf else None,
    )

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Scenario Comparison", "Risk Matrix", "Report"])

    with tab1:
        _render_scenario_tab(scenarios, projections)

    with tab2:
        _render_risk_tab(risk_factors, result.get("risk_category_scores", {}))

    with tab3:
        report_md = result.get("simulation_report_markdown", "")
        if report_md:
            st.markdown(report_md)
        else:
            st.info("Report not available.")

    # Downloads
    st.markdown("---")
    st.subheader("Downloads")
    dl_cols = st.columns(3)
    if result.get("simulation_report_markdown"):
        dl_cols[0].download_button(
            label="Download Report (.md)",
            data=result["simulation_report_markdown"],
            file_name=f"simulation_report_{result.get('decision_title','')[:30]}.md",
            mime="text/markdown",
        )
    dl_cols[1].download_button(
        label="Download Full Result (.json)",
        data=json.dumps(result, indent=2),
        file_name="simulation_result.json",
        mime="application/json",
    )
    if scenarios and projections:
        df_dl = _build_scenario_df(scenarios, projections)
        dl_cols[2].download_button(
            label="Download Scenarios (.csv)",
            data=df_dl.to_csv(index=False),
            file_name="scenarios.csv",
            mime="text/csv",
        )


def _build_scenario_df(scenarios: list, projections: list) -> pd.DataFrame:
    proj_map = {p["scenario_id"]: p for p in projections}
    rows = []
    for s in scenarios:
        p = proj_map.get(s["scenario_id"], {})
        rows.append({
            "Scenario": s["name"],
            "Probability": f"{s['probability']:.0%}",
            "Revenue Impact (%)": p.get("revenue_impact_pct", 0),
            "Revenue Low (%)": p.get("revenue_impact_low", 0),
            "Revenue High (%)": p.get("revenue_impact_high", 0),
            "Cost Impact (%)": p.get("cost_impact_pct", 0),
            "ROI (%)": p.get("roi_estimate", 0),
            "Success %": f"{p.get('success_probability', 0):.0%}",
            "NPV": p.get("npv_qualitative", ""),
            "Payback (months)": p.get("payback_months", ""),
        })
    return pd.DataFrame(rows)


def _render_scenario_tab(scenarios: list, projections: list):
    st.subheader("Scenario Cards")
    cols = st.columns(4)
    for col, s in zip(cols, scenarios):
        with col:
            color = _scenario_color(s["name"])
            st.markdown(
                f'<div style="border-left:4px solid {color};padding:8px;">'
                f'<b>{s["name"]}</b><br/>'
                f'<span style="font-size:1.5em">{s["probability"]:.0%}</span><br/>'
                f'<small>{s.get("macro_conditions","")[:80]}</small>'
                f'</div>',
                unsafe_allow_html=True,
            )
            for assumption in s.get("key_assumptions", [])[:3]:
                st.caption(f"• {assumption}")

    st.subheader("Outcome Comparison Table")
    if projections:
        df = _build_scenario_df(scenarios, projections)
        st.dataframe(df, use_container_width=True)

        # Bar chart
        st.subheader("Revenue & ROI by Scenario")
        chart_data = pd.DataFrame({
            "Scenario": [s["name"] for s in scenarios],
            "Revenue Impact (%)": [
                next((p["revenue_impact_pct"] for p in projections if p["scenario_id"] == s["scenario_id"]), 0)
                for s in scenarios
            ],
            "ROI (%)": [
                next((p["roi_estimate"] for p in projections if p["scenario_id"] == s["scenario_id"]), 0)
                for s in scenarios
            ],
        }).set_index("Scenario")
        st.bar_chart(chart_data)


def _render_risk_tab(risk_factors: list, category_scores: dict):
    if not risk_factors:
        st.info("No risk factors available.")
        return

    st.subheader("Risk Category Scores")
    cat_cols = st.columns(5)
    categories = ["market", "operational", "financial", "strategic", "regulatory"]
    for col, cat in zip(cat_cols, categories):
        score = category_scores.get(cat, 0.0)
        col.metric(label=cat.capitalize(), value=f"{score:.2f}", delta=None)

    st.subheader("Risk Scatter Chart (Likelihood vs Impact)")
    scatter_df = pd.DataFrame([
        {"Likelihood": r["likelihood"], "Impact": r["impact"], "Risk": r["name"]}
        for r in risk_factors
    ])
    st.scatter_chart(scatter_df, x="Likelihood", y="Impact")

    st.subheader("Risk Factors (sorted by score)")
    risk_df = pd.DataFrame([
        {
            "ID": r["risk_id"],
            "Name": r["name"],
            "Category": r["category"],
            "Likelihood": r["likelihood"],
            "Impact": r["impact"],
            "Score": r["risk_score"],
            "Mitigation": r["mitigation"][:80],
        }
        for r in sorted(risk_factors, key=lambda x: x["risk_score"], reverse=True)
    ])
    st.dataframe(risk_df, use_container_width=True)


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 Strategic Simulation")
    st.markdown("---")

    health = fetch_health()
    backend_ok = health.get("status") not in ("unreachable",)
    ollama_ok = health.get("ollama_connected", False)
    model_ok = health.get("model_available", False)

    st.markdown("**System Status**")
    st.write(f"{'✅' if backend_ok else '❌'} Backend: {health.get('status', '—').upper()}")
    st.write(f"{'✅' if ollama_ok else '❌'} Ollama: {'Connected' if ollama_ok else 'Disconnected'}")
    st.write(f"{'✅' if model_ok else '❌'} Model: {health.get('model', '—')}")

    st.markdown("---")
    sidebar_horizon = st.selectbox(
        "Default Time Horizon",
        options=["short_term", "medium_term", "long_term"],
        index=1,
        format_func=lambda x: TIME_HORIZON_LABELS[x],
    )

    st.markdown("---")
    with st.expander("Tips"):
        st.markdown("""
- Describe the decision clearly (min 20 chars)
- Add industry context for better results
- Use the streaming endpoint for live progress
- Download the full JSON for data analysis
        """)


# ──────────────────────────────────────────────
# Main layout — 3 tabs
# ──────────────────────────────────────────────
st.title("🎯 Strategic Simulation Agent")
st.caption("Probabilistic scenario analysis powered by LangGraph + Ollama (llama3.2)")

new_tab, scenario_tab, risk_tab = st.tabs(["New Decision", "Scenario Comparison", "Risk Matrix"])

with new_tab:
    st.subheader("Define Your Strategic Decision")

    col_title, col_industry = st.columns(2)
    with col_title:
        decision_title = st.text_input(
            "Decision Title",
            placeholder="e.g., European Market Expansion for SaaS Platform",
            key="title_input",
        )
    with col_industry:
        industry_context = st.text_input(
            "Industry Context (optional)",
            placeholder="e.g., B2B SaaS, 500 enterprise customers, $50M ARR",
            key="industry_input",
        )

    decision_text = st.text_area(
        "Decision Description",
        placeholder="Describe the strategic decision in detail. What are you considering? What are the key factors? What does success look like?",
        height=250,
        key="decision_input",
    )

    time_horizon = st.radio(
        "Time Horizon",
        options=["short_term", "medium_term", "long_term"],
        index=["short_term", "medium_term", "long_term"].index(sidebar_horizon),
        format_func=lambda x: TIME_HORIZON_LABELS[x],
        horizontal=True,
    )

    simulate_btn = st.button(
        "Run Simulation",
        type="primary",
        disabled=not backend_ok or not ollama_ok or not model_ok,
    )

    if simulate_btn:
        if not decision_title.strip():
            st.error("Please provide a decision title.")
        elif len(decision_text.strip()) < 20:
            st.error("Decision description must be at least 20 characters.")
        else:
            with st.spinner("Running strategic simulation..."):
                run_streaming_simulation(
                    decision_text=decision_text.strip(),
                    decision_title=decision_title.strip(),
                    industry_context=industry_context.strip(),
                    time_horizon=time_horizon,
                )

    if st.session_state.simulation_done and st.session_state.simulation_result:
        render_results(st.session_state.simulation_result)

with scenario_tab:
    if st.session_state.simulation_result:
        result = st.session_state.simulation_result
        _render_scenario_tab(
            result.get("scenarios", []),
            result.get("outcome_projections", []),
        )
    else:
        st.info("Run a simulation first to see scenario comparison.")

with risk_tab:
    if st.session_state.simulation_result:
        result = st.session_state.simulation_result
        _render_risk_tab(
            result.get("risk_factors", []),
            result.get("risk_category_scores", {}),
        )
    else:
        st.info("Run a simulation first to see the risk matrix.")
