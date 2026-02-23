import json
import io

import pandas as pd
import requests
import streamlit as st

from config import (
    HEALTH_ENDPOINT,
    INGEST_PDF_ENDPOINT,
    INGEST_URL_ENDPOINT,
    INGEST_TEXT_ENDPOINT,
    INGEST_RSS_ENDPOINT,
    ANALYZE_ENDPOINT,
    STREAM_ENDPOINT,
    FEEDS_LIST_ENDPOINT,
    FEEDS_POLL_ENDPOINT,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Regulatory Impact Analysis Agent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ─────────────────────────────────────────────────────────────────
AGENT_ORDER = [
    "document_parser",
    "clause_extractor",
    "industry_classifier",
    "impact_assessor",
    "action_plan_generator",
]
AGENT_LABELS = {
    "document_parser":       "Document Parser",
    "clause_extractor":      "Clause Extractor",
    "industry_classifier":   "Industry Classifier",
    "impact_assessor":       "Impact Assessor",
    "action_plan_generator": "Action Plan Generator",
}
INDUSTRY_MAP = {
    "Auto-detect": "auto",
    "Financial Services": "financial_services",
    "Healthcare": "healthcare",
}
SEVERITY_COLORS = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🟢",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def fetch_health():
    try:
        resp = requests.get(HEALTH_ENDPOINT, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


@st.cache_data(ttl=120)
def fetch_known_feeds():
    try:
        resp = requests.get(FEEDS_LIST_ENDPOINT, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def render_agent_status(statuses: dict, messages: dict):
    cols = st.columns(5)
    for i, agent_key in enumerate(AGENT_ORDER):
        label = AGENT_LABELS[agent_key]
        status = statuses.get(agent_key, "pending")
        msgs = messages.get(agent_key, [])
        icon = {"pending": "⏳", "running": "🔄", "done": "✅", "error": "❌"}.get(status, "⏳")
        with cols[i]:
            st.markdown(f"**{icon} {label}**")
            for msg in msgs[-2:]:
                st.caption(msg)


def render_results(result_data: dict, full_report: str):
    """Render the full results panel after analysis."""

    # Metadata banner
    reg_name = result_data.get("regulation_name") or "Unknown"
    issuer = result_data.get("issuing_body") or "Unknown"
    eff_date = result_data.get("effective_date") or "TBD"
    jurisdiction = result_data.get("jurisdiction") or "Unknown"
    industry = result_data.get("industry") or "unknown"
    sub_domain = result_data.get("sub_domain") or ""
    confidence = result_data.get("industry_confidence")
    conf_str = f" ({confidence:.0%})" if confidence else ""

    st.info(
        f"**Regulation:** {reg_name}  |  **Issuer:** {issuer}  |  "
        f"**Effective:** {eff_date}  |  **Jurisdiction:** {jurisdiction}  |  "
        f"**Industry:** `{industry}`{conf_str}  |  **Sub-domain:** `{sub_domain}`"
    )

    # Severity dashboard
    st.markdown("### Severity Dashboard")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔴 Critical", result_data.get("critical_count", 0), delta=None)
    m2.metric("🟠 High", result_data.get("high_count", 0))
    m3.metric("🟡 Medium", result_data.get("medium_count", 0))
    m4.metric("🟢 Low", result_data.get("low_count", 0))

    st.markdown("---")

    # Action plan markdown
    st.markdown("### Compliance Action Plan")
    if full_report:
        st.markdown(full_report, unsafe_allow_html=False)

    st.markdown("---")

    # Clause explorer
    clauses = result_data.get("extracted_clauses", [])
    impact_scores = result_data.get("impact_scores", [])
    score_lookup = {s["clause_id"]: s for s in impact_scores}

    with st.expander(f"Extracted Clauses ({len(clauses)})", expanded=False):
        if clauses:
            rows = []
            for c in clauses:
                sc = score_lookup.get(c["clause_id"], {})
                sev = sc.get("severity", "medium")
                rows.append({
                    "Clause ID": c["clause_id"],
                    "Type": c["clause_type"],
                    "Section": c["section_reference"],
                    "Severity": f"{SEVERITY_COLORS.get(sev, '')} {sev}",
                    "Affected Functions": ", ".join(sc.get("affected_functions", [])[:2]),
                    "Text (excerpt)": c["raw_text"][:120],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No clauses extracted.")

    # Impact matrix
    with st.expander("Impact Assessment", expanded=False):
        if impact_scores:
            chart_data = {
                "Clause ID": [s["clause_id"] for s in impact_scores],
                "Severity Score": [s["severity_score"] for s in impact_scores],
            }
            chart_df = pd.DataFrame(chart_data).set_index("Clause ID")
            st.bar_chart(chart_df, color="#e25822")
        else:
            st.info("No impact scores available.")

    # Downloads
    st.markdown("### Downloads")
    d1, d2, d3 = st.columns(3)

    reg_slug = (reg_name or "analysis").replace(" ", "_")[:30]

    with d1:
        st.download_button(
            label="Download Report (.md)",
            data=full_report or "",
            file_name=f"compliance_{reg_slug}.md",
            mime="text/markdown",
        )

    with d2:
        json_data = json.dumps(result_data, indent=2, default=str)
        st.download_button(
            label="Download Full JSON",
            data=json_data,
            file_name=f"compliance_{reg_slug}.json",
            mime="application/json",
        )

    with d3:
        if clauses:
            csv_rows = []
            for c in clauses:
                sc = score_lookup.get(c["clause_id"], {})
                csv_rows.append({
                    "clause_id": c["clause_id"],
                    "clause_type": c["clause_type"],
                    "section_reference": c["section_reference"],
                    "severity": sc.get("severity", ""),
                    "severity_score": sc.get("severity_score", ""),
                    "affected_functions": "|".join(sc.get("affected_functions", [])),
                    "compliance_deadline": sc.get("compliance_deadline", ""),
                    "raw_text": c["raw_text"],
                })
            csv_df = pd.DataFrame(csv_rows)
            st.download_button(
                label="Download Clauses (.csv)",
                data=csv_df.to_csv(index=False),
                file_name=f"clauses_{reg_slug}.csv",
                mime="text/csv",
            )


def run_streaming_analysis(source_id: str, industry: str):
    """Stream analysis and update UI components in real time."""
    payload = {"source_id": source_id, "industry": industry}

    st.markdown("---")
    st.subheader("Live Agent Progress")

    agent_statuses = {a: "pending" for a in AGENT_ORDER}
    agent_messages = {a: [] for a in AGENT_ORDER}

    progress_placeholder = st.empty()
    report_placeholder = st.empty()

    full_report_tokens: list[str] = []
    result_data = None
    error_occurred = False

    try:
        with requests.post(STREAM_ENDPOINT, json=payload, stream=True, timeout=600) as resp:
            resp.raise_for_status()
            current_agent = None

            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if not line.startswith("data:"):
                    continue

                try:
                    event = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue

                evt_type = event.get("event")
                agent = event.get("agent", current_agent)

                if evt_type == "agent_start":
                    current_agent = agent
                    if agent in agent_statuses:
                        agent_statuses[agent] = "running"
                        agent_messages[agent].append(event.get("message", ""))
                    with progress_placeholder.container():
                        render_agent_status(agent_statuses, agent_messages)

                elif evt_type == "agent_update":
                    msg = event.get("message", "")
                    if not msg:
                        # Build message from structured fields
                        parts = []
                        if "clause_id" in event:
                            parts.append(event["clause_id"])
                        if "severity" in event:
                            parts.append(f"{event['severity']} ({event.get('score', ''):.2f})")
                        if "industry" in event:
                            parts.append(f"industry={event['industry']}")
                        msg = " | ".join(parts)
                    if msg and agent and agent in agent_messages:
                        agent_messages[agent].append(msg)
                    with progress_placeholder.container():
                        render_agent_status(agent_statuses, agent_messages)

                elif evt_type == "agent_complete":
                    if agent in agent_statuses:
                        agent_statuses[agent] = "done"
                        # Add summary message
                        summary_parts = []
                        for key in ("char_count", "total_clauses", "industry", "confidence",
                                    "critical_count", "high_count"):
                            if key in event:
                                summary_parts.append(f"{key}={event[key]}")
                        if summary_parts and agent in agent_messages:
                            agent_messages[agent].append(", ".join(summary_parts))
                    with progress_placeholder.container():
                        render_agent_status(agent_statuses, agent_messages)

                elif evt_type == "token":
                    token = event.get("token", "")
                    full_report_tokens.append(token)
                    if len(full_report_tokens) % 20 == 0:
                        report_placeholder.markdown(
                            "".join(full_report_tokens), unsafe_allow_html=False
                        )

                elif evt_type == "done":
                    agent_statuses["action_plan_generator"] = "done"
                    with progress_placeholder.container():
                        render_agent_status(agent_statuses, agent_messages)
                    result_data = event.get("result", {})

                elif evt_type == "error":
                    err_agent = event.get("agent", "unknown")
                    if err_agent in agent_statuses:
                        agent_statuses[err_agent] = "error"
                    with progress_placeholder.container():
                        render_agent_status(agent_statuses, agent_messages)
                    st.error(f"Error in {err_agent}: {event.get('message', '')}")
                    error_occurred = True
                    break

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to backend. Is it running on port 8000?")
        return
    except Exception as e:
        st.error(f"Streaming error: {e}")
        return

    if full_report_tokens:
        full_report = "".join(full_report_tokens)
        report_placeholder.markdown(full_report, unsafe_allow_html=False)

    if result_data and not error_occurred:
        render_results(result_data, "".join(full_report_tokens))


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚖️ Reg Impact Agent")
    st.markdown("---")

    # System Status
    st.subheader("System Status")
    health = fetch_health()
    if health:
        status_color = "green" if health.get("status") == "healthy" else "red"
        st.markdown(f"**Backend**: :{status_color}[{'Online' if health.get('status') == 'healthy' else 'Degraded'}]")
        ollama_ok = health.get("ollama_connected", False)
        st.markdown(f"**Ollama**: :{'green' if ollama_ok else 'red'}[{'Connected' if ollama_ok else 'Disconnected'}]")
        model_ok = health.get("model_available", False)
        st.markdown(f"**Model**: :{'green' if model_ok else 'orange'}[{'Available' if model_ok else 'Not pulled'}]")
        if health.get("available_models"):
            with st.expander("Available models"):
                for m in health["available_models"]:
                    st.text(m)
    else:
        st.error("Backend unreachable")

    st.markdown("---")

    # Industry Selector
    st.subheader("Industry")
    industry_label = st.selectbox(
        "Select Industry",
        options=list(INDUSTRY_MAP.keys()),
        index=0,
        help="Auto-detect uses rule-based + LLM classification",
    )
    selected_industry = INDUSTRY_MAP[industry_label]

    st.markdown("---")

    # Known Regulatory Feeds
    with st.expander("RSS Feed Directory", expanded=False):
        known_feeds = fetch_known_feeds()
        fs_feeds = [f for f in known_feeds if f["industry"] == "financial_services"]
        hc_feeds = [f for f in known_feeds if f["industry"] == "healthcare"]

        if fs_feeds:
            st.markdown("**Financial Services**")
            for f in fs_feeds:
                st.markdown(f"- [{f['name']}]({f['url']})")

        if hc_feeds:
            st.markdown("**Healthcare**")
            for f in hc_feeds:
                st.markdown(f"- [{f['name']}]({f['url']})")

    st.markdown("---")
    st.caption("Regulatory Impact Analysis Agent v1.0")
    st.caption("Powered by Ollama (llama3.2) + LangGraph")


# ── Main area ─────────────────────────────────────────────────────────────────
st.title("⚖️ Regulatory Impact Analysis Agent")
st.markdown(
    "Analyze regulatory documents to extract clauses, assess compliance impact, "
    "and generate industry-specific action plans."
)

tab1, tab2, tab3, tab4 = st.tabs(["📄 Upload PDF", "🌐 Web URL", "📝 Paste Text", "📡 RSS Feeds"])


# ── Tab 1: Upload PDF ─────────────────────────────────────────────────────────
with tab1:
    st.subheader("Upload Regulatory PDF")
    uploaded_file = st.file_uploader(
        "Upload a PDF regulatory document",
        type=["pdf"],
        help="Maximum 20MB. Accepts regulatory documents, guidance, rules, etc.",
    )

    if uploaded_file:
        st.caption(f"File: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

        if st.button("Analyze PDF", type="primary", use_container_width=True, key="btn_pdf"):
            with st.spinner("Uploading and ingesting PDF..."):
                try:
                    resp = requests.post(
                        INGEST_PDF_ENDPOINT,
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                        data={"industry": selected_industry},
                        timeout=60,
                    )
                    resp.raise_for_status()
                    ingest_data = resp.json()
                    st.success(
                        f"Ingested: {ingest_data['char_count']:,} characters extracted. "
                        f"Preview: {ingest_data['preview'][:100]}..."
                    )
                    run_streaming_analysis(ingest_data["source_id"], selected_industry)
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to backend.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"Ingest failed {e.response.status_code}: {e.response.text[:300]}")
                except Exception as e:
                    st.error(f"Error: {e}")


# ── Tab 2: Web URL ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Analyze from Web URL")
    url_input = st.text_input(
        "Enter URL",
        placeholder="https://www.federalreserve.gov/...",
        help="Direct link to a regulatory document or press release",
    )

    if url_input and st.button("Analyze URL", type="primary", use_container_width=True, key="btn_url"):
        if not (url_input.startswith("http://") or url_input.startswith("https://")):
            st.error("URL must start with http:// or https://")
        else:
            with st.spinner("Fetching and ingesting URL..."):
                try:
                    resp = requests.post(
                        INGEST_URL_ENDPOINT,
                        json={"url": url_input, "industry": selected_industry},
                        timeout=60,
                    )
                    resp.raise_for_status()
                    ingest_data = resp.json()
                    st.success(
                        f"Fetched: {ingest_data['char_count']:,} characters. "
                        f"Preview: {ingest_data['preview'][:100]}..."
                    )
                    run_streaming_analysis(ingest_data["source_id"], selected_industry)
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to backend.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"Ingest failed {e.response.status_code}: {e.response.text[:300]}")
                except Exception as e:
                    st.error(f"Error: {e}")


# ── Tab 3: Paste Text ─────────────────────────────────────────────────────────
with tab3:
    st.subheader("Analyze Pasted Text")
    text_title = st.text_input(
        "Document Title",
        placeholder="e.g. HIPAA Privacy Rule Section 164.514",
        key="text_title",
    )
    text_content = st.text_area(
        "Paste regulatory text here",
        height=300,
        placeholder="Paste the full text of the regulation, guidance document, or regulatory notice...",
        key="text_content",
    )

    char_count = len(text_content)
    st.caption(f"{char_count:,} characters")

    if st.button("Analyze Text", type="primary", use_container_width=True, key="btn_text"):
        if not text_title.strip():
            st.error("Please enter a document title.")
        elif char_count < 50:
            st.error("Text must be at least 50 characters.")
        else:
            with st.spinner("Ingesting text..."):
                try:
                    resp = requests.post(
                        INGEST_TEXT_ENDPOINT,
                        json={
                            "content": text_content,
                            "title": text_title,
                            "industry": selected_industry,
                        },
                        timeout=30,
                    )
                    resp.raise_for_status()
                    ingest_data = resp.json()
                    st.success(f"Ingested: {ingest_data['char_count']:,} characters.")
                    run_streaming_analysis(ingest_data["source_id"], selected_industry)
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to backend.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"Ingest failed {e.response.status_code}: {e.response.text[:300]}")
                except Exception as e:
                    st.error(f"Error: {e}")


# ── Tab 4: RSS Feeds ──────────────────────────────────────────────────────────
with tab4:
    st.subheader("Poll Regulatory RSS Feeds")

    col_feed, col_entries = st.columns([3, 1])
    with col_feed:
        feed_url_input = st.text_input(
            "Feed URL",
            placeholder="https://www.fda.gov/.../press-releases/rss.xml",
            key="rss_feed_url",
        )
    with col_entries:
        max_rss_entries = st.number_input("Max entries", min_value=1, max_value=10, value=5)

    # Quick-select known feeds
    known_feeds_for_select = fetch_known_feeds()
    if known_feeds_for_select:
        feed_options = {f["name"]: f["url"] for f in known_feeds_for_select}
        selected_feed_name = st.selectbox(
            "Or select a known feed",
            options=["-- select --"] + list(feed_options.keys()),
            key="known_feed_select",
        )
        if selected_feed_name != "-- select --":
            feed_url_input = feed_options[selected_feed_name]

    if st.button("Poll Feed", type="primary", use_container_width=True, key="btn_rss_poll"):
        if not feed_url_input or not (feed_url_input.startswith("http://") or feed_url_input.startswith("https://")):
            st.error("Enter a valid feed URL.")
        else:
            with st.spinner(f"Polling feed..."):
                try:
                    resp = requests.get(
                        FEEDS_POLL_ENDPOINT,
                        params={"feed_url": feed_url_input, "max_entries": max_rss_entries},
                        timeout=30,
                    )
                    resp.raise_for_status()
                    feed_data = resp.json()
                    entries = feed_data.get("entries", [])

                    st.success(f"Found {len(entries)} entries")

                    for i, entry in enumerate(entries):
                        with st.expander(f"{i+1}. {entry['title'][:80]}", expanded=False):
                            st.caption(f"Published: {entry.get('published', 'N/A')}  |  Link: {entry.get('link', '')}")
                            if entry.get("summary"):
                                st.markdown(entry["summary"][:400])

                            if st.button(
                                f"Analyze this entry",
                                key=f"analyze_entry_{i}",
                                type="secondary",
                            ):
                                # Ingest the entry text
                                full_text = entry.get("content_preview", "") or entry.get("summary", "")
                                if len(full_text.strip()) < 50:
                                    st.warning("Entry content too short to analyze.")
                                else:
                                    with st.spinner("Ingesting entry..."):
                                        try:
                                            ingest_resp = requests.post(
                                                INGEST_TEXT_ENDPOINT,
                                                json={
                                                    "content": full_text,
                                                    "title": entry["title"] or "RSS Entry",
                                                    "industry": selected_industry,
                                                },
                                                timeout=30,
                                            )
                                            ingest_resp.raise_for_status()
                                            ingest_data = ingest_resp.json()
                                            run_streaming_analysis(
                                                ingest_data["source_id"], selected_industry
                                            )
                                        except Exception as e:
                                            st.error(f"Error: {e}")

                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to backend.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"Feed poll failed {e.response.status_code}: {e.response.text[:300]}")
                except Exception as e:
                    st.error(f"Error: {e}")
