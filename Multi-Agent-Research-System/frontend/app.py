import json

import requests
import streamlit as st

from config import HEALTH_ENDPOINT, RESEARCH_ENDPOINT, STREAM_ENDPOINT

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Multi-Agent Research System",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Helper: health check ──────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def fetch_health():
    try:
        resp = requests.get(HEALTH_ENDPOINT, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


# ── Progress tracking helpers ─────────────────────────────────────────────────
AGENT_LABELS = {
    "source_gatherer": "Source Gatherer",
    "citation_verifier": "Citation Verifier",
    "report_writer": "Report Writer",
}
AGENT_ORDER = ["source_gatherer", "citation_verifier", "report_writer"]


def render_agent_status(statuses: dict, messages: dict):
    cols = st.columns(3)
    for i, agent_key in enumerate(AGENT_ORDER):
        label = AGENT_LABELS[agent_key]
        status = statuses.get(agent_key, "pending")
        msgs = messages.get(agent_key, [])
        icon = {"pending": "⏳", "running": "🔄", "done": "✅", "error": "❌"}.get(status, "⏳")
        with cols[i]:
            st.markdown(f"**{icon} {label}**")
            for msg in msgs[-3:]:
                st.caption(msg)


def render_result_details(result_data: dict, report_md: str):
    """Render source details and download button below the report."""
    st.markdown("---")

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Overall Confidence", f"{result_data.get('overall_confidence', 0):.2f}")
    citations = result_data.get("citations", [])
    usable = [c for c in citations if c.get("is_usable")]
    m2.metric("Usable Sources", f"{len(usable)}/{len(citations)}")
    m3.metric("Failed URLs", result_data.get("sources_failed", 0))
    m4.metric("Total Citations", len(citations))

    # Source details expander
    with st.expander("Source Details", expanded=False):
        if not citations:
            st.info("No citations available.")
        else:
            # Confidence bar chart
            chart_data = {
                "Domain": [c["domain"] for c in citations],
                "Confidence": [c["confidence_score"] for c in citations],
            }
            try:
                import pandas as pd
                df = pd.DataFrame(chart_data)
                st.bar_chart(df.set_index("Domain"))
            except ImportError:
                pass

            # Per-citation cards
            for i, c in enumerate(citations, 1):
                status_icon = "✅" if c.get("is_usable") else "⚠️"
                with st.container():
                    st.markdown(
                        f"**[{i}] {status_icon} {c['domain']}** — "
                        f"confidence: `{c['confidence_score']:.2f}` "
                        f"(domain: `{c['domain_score']:.1f}`, "
                        f"relevance: `{c['relevance_score']:.2f}`)"
                    )
                    st.caption(f"URL: {c['url']}")
                    if c.get("key_claims"):
                        with st.expander("Claims"):
                            for claim in c["key_claims"]:
                                st.markdown(f"- {claim}")
                    if c.get("credibility_reasoning"):
                        st.caption(f"Reasoning: {c['credibility_reasoning']}")
                    st.markdown("---")

    # Failed URLs
    if result_data.get("failed_urls"):
        with st.expander(f"Failed URLs ({len(result_data['failed_urls'])})", expanded=False):
            for url in result_data["failed_urls"]:
                st.markdown(f"- {url}")

    # Download button
    if report_md:
        topic_slug = result_data.get("topic", "research").replace(" ", "_")[:40]
        st.download_button(
            label="Download Report (.md)",
            data=report_md,
            file_name=f"research_{topic_slug}.md",
            mime="text/markdown",
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔬 Research System")
    st.markdown("---")

    st.subheader("System Status")
    health = fetch_health()
    if health:
        st.markdown(
            f"**Backend**: :{'green' if health.get('status') == 'healthy' else 'red'}[{'Online' if health.get('status') == 'healthy' else 'Degraded'}]"
        )
        st.markdown(
            f"**Ollama**: :{'green' if health.get('ollama_connected') else 'red'}[{'Connected' if health.get('ollama_connected') else 'Disconnected'}]"
        )
        model_ok = health.get("model_available", False)
        st.markdown(
            f"**Model**: :{'green' if model_ok else 'orange'}[{'Available' if model_ok else 'Not pulled'}]"
        )
        if health.get("available_models"):
            with st.expander("Available models"):
                for m in health["available_models"]:
                    st.text(m)
    else:
        st.error("Backend unreachable")

    st.markdown("---")

    with st.expander("Quick Start Guide", expanded=False):
        st.markdown(
            """
**How to use:**
1. Enter your research topic
2. Paste URLs (one per line, http/https)
3. Choose streaming or blocking mode
4. Click **Run Research**

**Agent Pipeline:**
- **Source Gatherer** — fetches each URL and extracts factual claims
- **Citation Verifier** — scores credibility and relevance
- **Report Writer** — compiles a structured Markdown report

**Tips:**
- Use 2–5 high-quality URLs for best results
- Academic (.edu), government (.gov), and org (.org) domains score higher
- Streaming mode shows live progress
            """
        )

    st.markdown("---")
    st.caption("Multi-Agent Research System v1.0")


# ── Main area ─────────────────────────────────────────────────────────────────
st.title("Multi-Agent Research System")
st.markdown(
    "Provide a research topic and URLs. Three specialized agents will gather, verify, and report."
)

col_topic, col_mode = st.columns([3, 1])
with col_topic:
    topic = st.text_input(
        "Research Topic",
        placeholder="e.g. Impact of large language models on software development",
    )
with col_mode:
    streaming_mode = st.toggle("Streaming", value=True, help="Show live agent progress")

urls_raw = st.text_area(
    "URLs to Research (one per line, http/https)",
    height=120,
    placeholder="https://example.com/article\nhttps://another.org/paper",
)

run_btn = st.button("Run Research", type="primary", use_container_width=True)


# ── Run Research ──────────────────────────────────────────────────────────────
if run_btn:
    if not topic.strip():
        st.error("Please enter a research topic.")
        st.stop()

    urls = [u.strip() for u in urls_raw.strip().splitlines() if u.strip()]
    if not urls:
        st.error("Please enter at least one URL.")
        st.stop()

    invalid = [u for u in urls if not (u.startswith("http://") or u.startswith("https://"))]
    if invalid:
        st.error("Invalid URLs (must start with http:// or https://):\n" + "\n".join(invalid))
        st.stop()

    if len(urls) > 10:
        st.error("Maximum 10 URLs allowed.")
        st.stop()

    payload = {"topic": topic.strip(), "urls": urls}

    st.markdown("---")

    # ── Streaming mode ────────────────────────────────────────────────────────
    if streaming_mode:
        st.subheader("Live Agent Progress")

        agent_statuses = {a: "pending" for a in AGENT_ORDER}
        agent_messages = {a: [] for a in AGENT_ORDER}

        progress_placeholder = st.empty()
        report_placeholder = st.empty()

        full_report_tokens = []
        result_data = None
        error_occurred = False

        try:
            with requests.post(STREAM_ENDPOINT, json=payload, stream=True, timeout=300) as resp:
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
                        agent_statuses[agent] = "running"
                        agent_messages[agent].append(event.get("message", ""))
                        with progress_placeholder.container():
                            render_agent_status(agent_statuses, agent_messages)

                    elif evt_type == "agent_update":
                        msg = event.get("message", "")
                        if not msg and "confidence" in event:
                            msg = (
                                f"{event.get('url', '')}: "
                                f"confidence={event.get('confidence', 0):.2f} "
                                f"{'✓' if event.get('is_usable') else '✗'}"
                            )
                        if msg and agent:
                            agent_messages[agent].append(msg)
                        with progress_placeholder.container():
                            render_agent_status(agent_statuses, agent_messages)

                    elif evt_type == "agent_complete":
                        agent_statuses[agent] = "done"
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
                        agent_statuses["report_writer"] = "done"
                        with progress_placeholder.container():
                            render_agent_status(agent_statuses, agent_messages)
                        result_data = event.get("result", {})

                    elif evt_type == "error":
                        err_agent = event.get("agent", "unknown")
                        if err_agent and err_agent in agent_statuses:
                            agent_statuses[err_agent] = "error"
                        with progress_placeholder.container():
                            render_agent_status(agent_statuses, agent_messages)
                        st.error(f"Error in {err_agent}: {event.get('message', '')}")
                        error_occurred = True
                        break

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Is it running?")
            st.stop()
        except Exception as e:
            st.error(f"Streaming error: {e}")
            st.stop()

        if full_report_tokens:
            full_report = "".join(full_report_tokens)
            if not full_report.endswith("*Generated by Multi-Agent Research System*"):
                full_report += "\n\n---\n*Generated by Multi-Agent Research System*"
            report_placeholder.markdown(full_report, unsafe_allow_html=False)

        if result_data and not error_occurred:
            render_result_details(result_data, "".join(full_report_tokens))

    # ── Blocking mode ─────────────────────────────────────────────────────────
    else:
        with st.spinner("Running research pipeline (this may take a few minutes)..."):
            try:
                resp = requests.post(RESEARCH_ENDPOINT, json=payload, timeout=300)
                resp.raise_for_status()
                result_data = resp.json()
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Is it running?")
                st.stop()
            except requests.exceptions.HTTPError as e:
                st.error(f"Backend error {e.response.status_code}: {e.response.text[:500]}")
                st.stop()
            except Exception as e:
                st.error(f"Request failed: {e}")
                st.stop()

        report_md = result_data.get("report_markdown", "")
        st.markdown(report_md, unsafe_allow_html=False)
        render_result_details(result_data, report_md)
