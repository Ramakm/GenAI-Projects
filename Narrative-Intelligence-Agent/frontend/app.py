import json

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from config import (
    HEALTH_ENDPOINT, ANALYZE_ENDPOINT, STREAM_ENDPOINT,
    TOPICS_ENDPOINT, FEEDS_ENDPOINT, PRESETS_ENDPOINT,
)

st.set_page_config(
    page_title="Narrative Intelligence Agent",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
for key, default in [
    ("analysis_result", None),
    ("agent_statuses", {}),
    ("agent_messages", {}),
    ("streaming_report", ""),
    ("analysis_done", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
AGENT_ORDER = [
    "source_aggregator", "sentiment_analyzer",
    "narrative_extractor", "pattern_mapper", "intelligence_reporter",
]
AGENT_LABELS = {
    "source_aggregator":    "Source Aggregator",
    "sentiment_analyzer":   "Sentiment Analyzer",
    "narrative_extractor":  "Narrative Extractor",
    "pattern_mapper":       "Pattern Mapper",
    "intelligence_reporter": "Intel Reporter",
}
NARRATIVE_TYPE_COLORS = {
    "dominant":  "#3B82F6",
    "emerging":  "#22C55E",
    "fading":    "#9CA3AF",
    "contested": "#F59E0B",
    "fringe":    "#A855F7",
}
FRAMING_COLORS = {
    "positive":   "#22C55E",
    "negative":   "#EF4444",
    "neutral":    "#6B7280",
    "alarmist":   "#F97316",
    "optimistic": "#06B6D4",
}
PATTERN_ICONS = {
    "convergence":   "🔀",
    "divergence":    "↔️",
    "amplification": "📢",
    "suppression":   "🔇",
    "reversal":      "🔄",
    "echo_chamber":  "🔁",
}
SENTIMENT_COLORS = {
    "positive": "#22C55E",
    "negative": "#EF4444",
    "neutral":  "#6B7280",
    "mixed":    "#F59E0B",
}
TIME_WINDOW_LABELS = {
    "24h": "Last 24 hours",
    "7d":  "Last 7 days",
    "30d": "Last 30 days",
    "all": "All time",
}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_health() -> dict:
    try:
        return requests.get(HEALTH_ENDPOINT, timeout=5).json()
    except Exception:
        return {"status": "unreachable", "ollama_connected": False, "model_available": False}


@st.cache_data(ttl=300)
def fetch_presets() -> dict:
    try:
        return requests.get(PRESETS_ENDPOINT, timeout=5).json().get("presets", {})
    except Exception:
        return {}


@st.cache_data(ttl=300)
def fetch_feed_presets() -> dict:
    try:
        return requests.get(FEEDS_ENDPOINT, timeout=5).json().get("presets", {})
    except Exception:
        return {}


def render_agent_status(statuses: dict, messages: dict):
    cols = st.columns(len(AGENT_ORDER))
    for col, agent in zip(cols, AGENT_ORDER):
        status = statuses.get(agent, "pending")
        icon = {"pending": "⏳", "running": "🔄", "done": "✅", "error": "❌"}.get(status, "⏳")
        col.metric(
            label=f"{icon} {AGENT_LABELS[agent]}",
            value=status.upper(),
            delta=messages.get(agent, "")[:28] if messages.get(agent) else None,
        )


def sentiment_gauge(score: float, label: str = "Overall Sentiment"):
    color = "#22C55E" if score > 0.1 else "#EF4444" if score < -0.1 else "#6B7280"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "", "valueformat": "+.2f"},
        title={"text": label, "font": {"size": 14}},
        gauge={
            "axis": {"range": [-1, 1], "tickwidth": 1},
            "bar": {"color": color},
            "steps": [
                {"range": [-1, -0.15], "color": "#FCA5A5"},
                {"range": [-0.15, 0.15], "color": "#D1D5DB"},
                {"range": [0.15, 1], "color": "#86EFAC"},
            ],
            "threshold": {"line": {"color": "white", "width": 3}, "thickness": 0.75, "value": score},
        },
    ))
    fig.update_layout(height=200, margin=dict(t=40, b=10, l=20, r=20))
    return fig


def sentiment_by_source_chart(by_source: dict) -> go.Figure:
    sorted_items = sorted(by_source.items(), key=lambda x: x[1])
    sources = [s for s, _ in sorted_items]
    scores  = [v for _, v in sorted_items]
    colors  = ["#22C55E" if s > 0.1 else "#EF4444" if s < -0.1 else "#6B7280" for s in scores]
    fig = go.Figure(go.Bar(
        x=scores, y=sources, orientation="h",
        marker_color=colors,
        text=[f"{s:+.2f}" for s in scores],
        textposition="outside",
    ))
    fig.update_layout(
        title="Sentiment Score by Source", xaxis_title="Score",
        xaxis={"range": [-1, 1]}, height=max(200, len(sources) * 32 + 80),
        margin=dict(l=10, r=60, t=40, b=20),
    )
    return fig


def narrative_type_chart(narratives: list) -> go.Figure:
    from collections import Counter
    counts = Counter(n["narrative_type"] for n in narratives)
    labels = list(counts.keys())
    values = list(counts.values())
    colors = [NARRATIVE_TYPE_COLORS.get(l, "#888") for l in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, marker_colors=colors,
        hole=0.4, textinfo="label+percent",
    ))
    fig.update_layout(title="Narrative Type Distribution", height=280, margin=dict(t=40, b=10))
    return fig


def render_narrative_card(n: dict):
    type_color  = NARRATIVE_TYPE_COLORS.get(n["narrative_type"], "#6B7280")
    frame_color = FRAMING_COLORS.get(n["framing"], "#6B7280")
    momentum_filled = int(n["momentum"] * 10)
    momentum_bar = "█" * momentum_filled + "░" * (10 - momentum_filled)
    claims_html = "".join(f'<li style="font-size:12px">{c}</li>' for c in n.get("key_claims", [])[:3])
    actors = ", ".join(n.get("key_actors", [])[:4])
    st.markdown(
        f'<div style="border-left:4px solid {type_color};padding:12px 14px;'
        f'margin-bottom:10px;background:#1e1e2e;border-radius:6px">'
        f'<b style="font-size:14px">{n["title"]}</b><br/>'
        f'<span style="background:{type_color};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px">'
        f'{n["narrative_type"].upper()}</span>&nbsp;'
        f'<span style="background:{frame_color};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px">'
        f'{n["framing"].upper()}</span><br/><br/>'
        f'<span style="font-size:12px;color:#ccc">{n["description"]}</span><br/><br/>'
        f'<b style="font-size:11px">Momentum:</b> '
        f'<span style="font-family:monospace;color:{type_color}">{momentum_bar}</span> {n["momentum"]:.0%}<br/>'
        f'<b style="font-size:11px">Key actors:</b> <span style="font-size:11px;color:#aaa">{actors or "—"}</span><br/>'
        f'<b style="font-size:11px">Key claims:</b><ul style="margin:4px 0 0 0;padding-left:16px">'
        f'{claims_html}</ul></div>',
        unsafe_allow_html=True,
    )


def render_pattern_card(p: dict):
    icon = PATTERN_ICONS.get(p["pattern_type"], "🔍")
    strength_bar = "█" * int(p["strength"] * 10) + "░" * (10 - int(p["strength"] * 10))
    narratives_str = " · ".join(p.get("involved_narratives", [])[:3])
    st.markdown(
        f'<div style="border:1px solid #374151;padding:10px 14px;margin-bottom:8px;border-radius:6px">'
        f'{icon} <b>{p["pattern_type"].replace("_", " ").title()}</b> '
        f'<span style="font-family:monospace;font-size:11px;color:#60a5fa">{strength_bar} {p["strength"]:.0%}</span><br/>'
        f'<span style="font-size:12px;color:#ccc">{p["description"]}</span><br/>'
        f'<span style="font-size:11px;color:#9ca3af">Narratives: {narratives_str or "—"}</span></div>',
        unsafe_allow_html=True,
    )


def run_streaming_analysis(topic: str, query: str, sources: list, time_window: str):
    st.session_state.agent_statuses = {a: "pending" for a in AGENT_ORDER}
    st.session_state.agent_messages = {a: "" for a in AGENT_ORDER}
    st.session_state.streaming_report = ""
    st.session_state.analysis_result = None
    st.session_state.analysis_done = False

    payload = {"topic": topic, "query": query, "sources": sources, "time_window": time_window}

    progress_placeholder = st.empty()
    report_placeholder   = st.empty()

    with requests.post(STREAM_ENDPOINT, json=payload, stream=True, timeout=600) as resp:
        if resp.status_code != 200:
            st.error(f"Backend error {resp.status_code}: {resp.text[:300]}")
            return

        token_buf = ""
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
                pass

            elif event == "token":
                token_buf += data.get("token", "")
                token_count += 1
                if token_count % 20 == 0:
                    st.session_state.streaming_report = token_buf
                    report_placeholder.markdown(token_buf)

            elif event == "done":
                st.session_state.streaming_report = token_buf
                report_placeholder.markdown(token_buf)
                result = data.get("result", {})
                st.session_state.analysis_result = result
                st.session_state.analysis_done = True
                for a in AGENT_ORDER:
                    if st.session_state.agent_statuses.get(a) == "running":
                        st.session_state.agent_statuses[a] = "done"
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


def render_narrative_map_tab(result: dict):
    narratives = result.get("narratives", [])
    patterns   = result.get("narrative_patterns", [])
    by_source  = result.get("sentiment_by_source", {})
    overall    = result.get("overall_sentiment_score", 0.0)
    distribution = result.get("sentiment_distribution", {})
    shift_signal = result.get("sentiment_shift_signal", "stable")
    map_summary  = result.get("narrative_map_summary", "")

    # Sentiment overview row
    col_gauge, col_dist, col_type = st.columns([1, 1, 1])
    with col_gauge:
        st.plotly_chart(sentiment_gauge(overall), use_container_width=True)
        shift_color = {"stable": "blue", "shifting_positive": "green",
                       "shifting_negative": "red", "volatile": "orange"}.get(shift_signal, "gray")
        st.markdown(
            f'<p style="text-align:center;color:{shift_color};font-weight:bold">'
            f'Signal: {shift_signal.replace("_", " ").upper()}</p>',
            unsafe_allow_html=True,
        )

    with col_dist:
        if distribution:
            cats   = list(distribution.keys())
            vals   = list(distribution.values())
            colors = [SENTIMENT_COLORS.get(c, "#888") for c in cats]
            fig = go.Figure(go.Bar(
                x=cats, y=vals,
                marker_color=colors,
                text=[f"{v:.0%}" for v in vals], textposition="outside",
            ))
            fig.update_layout(
                title="Sentiment Distribution", yaxis_title="Share",
                height=200, margin=dict(t=40, b=10, l=10, r=10),
                yaxis={"tickformat": ".0%"},
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_type:
        if narratives:
            st.plotly_chart(narrative_type_chart(narratives), use_container_width=True)

    # Sentiment by source
    if by_source:
        st.subheader("Sentiment by Source")
        st.plotly_chart(sentiment_by_source_chart(by_source), use_container_width=True)

    # Narrative map summary
    if map_summary:
        st.info(f"**Narrative Landscape:** {map_summary}")

    # Narrative cards
    st.subheader(f"Narratives ({len(narratives)})")
    cols = st.columns(2)
    for i, n in enumerate(narratives):
        with cols[i % 2]:
            render_narrative_card(n)

    # Patterns
    if patterns:
        st.subheader(f"Narrative Patterns ({len(patterns)})")
        for p in patterns:
            render_pattern_card(p)

    # Key actors / claims
    key_actors = result.get("key_actors", [])
    key_claims = result.get("key_claims", [])
    col_a, col_c = st.columns(2)
    with col_a:
        if key_actors:
            st.subheader("Key Actors")
            for actor in key_actors[:8]:
                st.markdown(f"- {actor}")
    with col_c:
        if key_claims:
            st.subheader("Key Claims")
            for claim in key_claims[:5]:
                st.markdown(f"- {claim}")


def render_brief_tab(result: dict):
    # Key insights
    insights = result.get("key_insights", [])
    if insights:
        st.subheader("Key Insights")
        for insight in insights:
            st.markdown(f"- {insight}")
        st.markdown("---")

    # Report
    report = result.get("intelligence_report_markdown", "")
    if report:
        st.markdown(report)
    else:
        st.info("No report generated.")

    # Downloads
    st.markdown("---")
    dl_c1, dl_c2, dl_c3 = st.columns(3)
    if report:
        dl_c1.download_button(
            "Download Brief (.md)", data=report,
            file_name=f"narrative_brief_{result.get('topic','')[:30]}.md",
            mime="text/markdown",
        )
    dl_c2.download_button(
        "Download Full Result (.json)", data=json.dumps(result, indent=2),
        file_name="narrative_analysis.json", mime="application/json",
    )
    articles = result.get("articles", [])
    scores   = result.get("sentiment_scores", [])
    if articles and scores:
        score_map = {s["article_id"]: s for s in scores}
        rows = []
        for a in articles:
            s = score_map.get(a["article_id"], {})
            rows.append({
                "Article ID": a["article_id"], "Source": a["source"],
                "Title": a["title"][:80], "Published": a.get("published_at", ""),
                "Sentiment": s.get("sentiment", ""), "Score": s.get("score", ""),
                "Intensity": s.get("intensity", ""),
            })
        df = pd.DataFrame(rows)
        dl_c3.download_button(
            "Download Sentiment Data (.csv)", data=df.to_csv(index=False),
            file_name="sentiment_data.csv", mime="text/csv",
        )


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.title("📡 Narrative Intel")
    st.markdown("---")

    health = fetch_health()
    backend_ok = health.get("status") not in ("unreachable",)
    ollama_ok  = health.get("ollama_connected", False)
    model_ok   = health.get("model_available", False)

    st.markdown("**System Status**")
    st.write(f"{'✅' if backend_ok else '❌'} Backend: {health.get('status', '—').upper()}")
    st.write(f"{'✅' if ollama_ok else '❌'} Ollama: {'Connected' if ollama_ok else 'Disconnected'}")
    st.write(f"{'✅' if model_ok else '❌'} Model: {health.get('model', '—')}")

    st.markdown("---")
    st.markdown("**Narrative Types**")
    for ntype, color in NARRATIVE_TYPE_COLORS.items():
        st.markdown(
            f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;'
            f'font-size:11px;margin:2px;display:inline-block">{ntype}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    with st.expander("Pattern Types"):
        for ptype, icon in PATTERN_ICONS.items():
            st.caption(f"{icon} **{ptype.replace('_', ' ').title()}**")

    with st.expander("Tips"):
        st.markdown("""
- Add RSS feeds for real-time news monitoring
- Use multiple competing sources for divergence detection
- Paste social content as text sources
- Combine news + commentary sources for framing analysis
        """)


# ──────────────────────────────────────────────
# Main — 3 tabs
# ──────────────────────────────────────────────
st.title("📡 Narrative Intelligence Agent")
st.caption("Aggregate media · detect sentiment shifts · map evolving narrative patterns")

monitor_tab, map_tab, brief_tab = st.tabs(["Monitor", "Narrative Map", "Intelligence Brief"])

with monitor_tab:
    st.subheader("Configure Topic & Sources")

    # Topic presets
    presets = fetch_presets()
    if presets:
        st.markdown("**Quick-start presets:**")
        preset_cols = st.columns(len(presets))
        preset_selected = None
        for col, (key, preset) in zip(preset_cols, presets.items()):
            if col.button(preset["topic"][:20], key=f"preset_{key}"):
                preset_selected = preset

    col1, col2 = st.columns(2)
    with col1:
        topic_default = preset_selected["topic"] if preset_selected else ""
        topic = st.text_input("Topic / Subject", value=topic_default,
                              placeholder="e.g., AI regulation, Climate policy, Fed rate decisions")
        query = st.text_input("Keyword Filter (optional)",
                              placeholder="narrow focus, e.g., 'EU AI Act'")
    with col2:
        time_window = st.selectbox(
            "Time Window", options=["24h", "7d", "30d", "all"],
            format_func=lambda x: TIME_WINDOW_LABELS[x], index=1,
        )

    st.markdown("---")
    st.subheader("Sources")

    # Source builder
    feed_presets = fetch_feed_presets()
    source_type = st.radio(
        "Add source", ["RSS Feed", "URL", "Text / Paste"], horizontal=True,
    )

    if "sources_list" not in st.session_state:
        st.session_state.sources_list = []

    add_col, preset_col = st.columns([2, 1])
    with add_col:
        if source_type == "RSS Feed":
            src_value = st.text_input("RSS Feed URL", placeholder="https://feeds.bbci.co.uk/news/rss.xml")
            src_label = st.text_input("Label (optional)", placeholder="BBC News")
        elif source_type == "URL":
            src_value = st.text_input("Web Page URL", placeholder="https://example.com/article")
            src_label = st.text_input("Label (optional)", placeholder="Article label")
        else:
            src_value = st.text_area("Paste content", placeholder="Paste article text, social posts, discussion...", height=120)
            src_label = st.text_input("Label (optional)", placeholder="Reddit thread / Tweet collection")

    with preset_col:
        if feed_presets and source_type == "RSS Feed":
            st.markdown("**Feed presets:**")
            for cat, feeds in feed_presets.items():
                if st.button(cat.replace("_", " ").title(), key=f"feedcat_{cat}"):
                    for feed in feeds[:3]:
                        entry = {"type": "rss", "value": feed, "label": cat}
                        if entry not in st.session_state.sources_list:
                            st.session_state.sources_list.append(entry)

        # Auto-load preset sources
        if preset_selected and not st.session_state.sources_list:
            feed_cat = preset_selected.get("feed_category", "general_news")
            for feed in feed_presets.get(feed_cat, [])[:3]:
                st.session_state.sources_list.append({"type": "rss", "value": feed, "label": feed_cat})

    type_map = {"RSS Feed": "rss", "URL": "url", "Text / Paste": "text"}
    if st.button("Add Source") and src_value.strip():
        entry = {"type": type_map[source_type], "value": src_value.strip(), "label": src_label.strip()}
        if entry not in st.session_state.sources_list:
            st.session_state.sources_list.append(entry)

    # Display + manage sources
    if st.session_state.sources_list:
        st.markdown(f"**Sources ({len(st.session_state.sources_list)}):**")
        remove_idx = None
        for i, src in enumerate(st.session_state.sources_list):
            c1, c2 = st.columns([9, 1])
            c1.caption(f"[{src['type'].upper()}] {src.get('label') or src['value'][:60]}")
            if c2.button("✕", key=f"rm_{i}"):
                remove_idx = i
        if remove_idx is not None:
            st.session_state.sources_list.pop(remove_idx)
            st.rerun()
        if st.button("Clear All Sources"):
            st.session_state.sources_list = []
            st.rerun()
    else:
        st.info("Add at least one source (RSS feed, URL, or pasted text).")

    st.markdown("---")
    run_btn = st.button(
        "Run Analysis",
        type="primary",
        disabled=not (backend_ok and ollama_ok and model_ok) or not st.session_state.sources_list or not topic.strip(),
    )

    if run_btn:
        if not topic.strip():
            st.error("Please enter a topic.")
        elif not st.session_state.sources_list:
            st.error("Please add at least one source.")
        else:
            with st.spinner("Running narrative intelligence analysis..."):
                run_streaming_analysis(
                    topic=topic.strip(),
                    query=query.strip(),
                    sources=st.session_state.sources_list,
                    time_window=time_window,
                )

    if st.session_state.analysis_done and st.session_state.analysis_result:
        result = st.session_state.analysis_result
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Articles Analyzed", result.get("article_count", 0))
        m2.metric("Sources", len(result.get("sources_found", [])))
        m3.metric("Narratives Found", len(result.get("narratives", [])))
        m4.metric("Patterns Detected", len(result.get("narrative_patterns", [])))

        sent_color = {"positive": "green", "negative": "red", "neutral": "gray"}.get(
            result.get("overall_sentiment", "neutral"), "gray"
        )
        score = result.get("overall_sentiment_score", 0.0)
        signal = result.get("sentiment_shift_signal", "stable").replace("_", " ")
        st.markdown(
            f'<p style="color:{sent_color};font-size:16px;font-weight:bold">'
            f'Overall sentiment: {result.get("overall_sentiment","").upper()} '
            f'({score:+.2f}) · Signal: {signal.upper()}</p>',
            unsafe_allow_html=True,
        )

        if st.session_state.streaming_report:
            with st.expander("Preview Intelligence Brief", expanded=False):
                st.markdown(st.session_state.streaming_report[:2000] + "…")

with map_tab:
    if st.session_state.analysis_result:
        render_narrative_map_tab(st.session_state.analysis_result)
    else:
        st.info("Run an analysis first to see the narrative map.")

with brief_tab:
    if st.session_state.analysis_result:
        render_brief_tab(st.session_state.analysis_result)
    else:
        st.info("Run an analysis first to see the intelligence brief.")
