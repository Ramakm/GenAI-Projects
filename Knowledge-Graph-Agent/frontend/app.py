import json
import os
import tempfile

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

from config import (
    HEALTH_ENDPOINT,
    BUILD_ENDPOINT,
    STREAM_ENDPOINT,
    GRAPHS_ENDPOINT,
    QUERY_ENDPOINT,
)

st.set_page_config(
    page_title="Knowledge Graph Agent",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────
for key, default in [
    ("graph_result", None),
    ("agent_statuses", {}),
    ("agent_messages", {}),
    ("streaming_summary", ""),
    ("build_done", False),
    ("query_result", None),
    ("active_graph_id", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
AGENT_ORDER = [
    "document_ingester",
    "entity_extractor",
    "relationship_extractor",
    "graph_builder",
    "graph_summarizer",
]
AGENT_LABELS = {
    "document_ingester": "Doc Ingester",
    "entity_extractor": "Entity Extractor",
    "relationship_extractor": "Rel. Extractor",
    "graph_builder": "Graph Builder",
    "graph_summarizer": "Summarizer",
}
ENTITY_COLORS = {
    "PERSON":       "#FF6B6B",
    "ORGANIZATION": "#4ECDC4",
    "TECHNOLOGY":   "#45B7D1",
    "CONCEPT":      "#96CEB4",
    "LOCATION":     "#FFEAA7",
    "EVENT":        "#DDA0DD",
    "PRODUCT":      "#98D8C8",
    "PROCESS":      "#F0E68C",
}
QUERY_TYPE_LABELS = {
    "neighborhood":    "Neighborhood Search",
    "path_finding":    "Path Finding",
    "keyword_search":  "Keyword Search",
    "semantic":        "Semantic Search",
}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_health() -> dict:
    try:
        r = requests.get(HEALTH_ENDPOINT, timeout=5)
        return r.json()
    except Exception as e:
        return {"status": "unreachable", "ollama_connected": False, "model_available": False}


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


def build_pyvis_html(entities: list, relationships: list) -> str:
    try:
        from pyvis.network import Network
    except ImportError:
        return "<p>pyvis not installed. Run: pip install pyvis</p>"

    net = Network(
        height="560px", width="100%",
        directed=True, bgcolor="#0e1117", font_color="#ffffff",
    )
    net.set_options("""{
        "physics": {
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -60,
                "centralGravity": 0.005,
                "springLength": 120,
                "springConstant": 0.05
            },
            "stabilization": {"iterations": 120}
        },
        "edges": {
            "smooth": {"type": "dynamic"},
            "font": {"size": 10, "color": "#aaaaaa"},
            "arrows": {"to": {"enabled": true, "scaleFactor": 0.6}}
        },
        "interaction": {"hover": true, "navigationButtons": true, "tooltipDelay": 200},
        "nodes": {"font": {"size": 13}}
    }""")

    for e in entities:
        color = ENTITY_COLORS.get(e.get("entity_type", ""), "#888888")
        tooltip = (
            f"<b>{e.get('name', '')}</b><br/>"
            f"Type: {e.get('entity_type', '')}<br/>"
            f"{e.get('description', '')[:120]}"
        )
        net.add_node(
            e["entity_id"],
            label=e["name"],
            title=tooltip,
            color=color,
            size=16,
        )

    for r in relationships:
        net.add_edge(
            r["source_entity_id"],
            r["target_entity_id"],
            label=r["relationship_type"].replace("_", " "),
            title=r.get("description", ""),
            color="#555577",
        )

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
        fname = f.name
    net.save_graph(fname)
    with open(fname) as f:
        html = f.read()
    os.unlink(fname)
    return html


def run_streaming_build(
    raw_content: str, document_title: str, domain: str, source_type: str
):
    st.session_state.agent_statuses = {a: "pending" for a in AGENT_ORDER}
    st.session_state.agent_messages = {a: "" for a in AGENT_ORDER}
    st.session_state.streaming_summary = ""
    st.session_state.graph_result = None
    st.session_state.build_done = False

    payload = {
        "raw_content": raw_content,
        "document_title": document_title,
        "domain": domain,
        "source_type": source_type,
        "source_identifier": raw_content[:200] if source_type == "url" else "inline",
    }

    progress_placeholder = st.empty()
    summary_placeholder = st.empty()

    with requests.post(STREAM_ENDPOINT, json=payload, stream=True, timeout=600) as resp:
        if resp.status_code != 200:
            st.error(f"Backend error {resp.status_code}: {resp.text[:300]}")
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
                pass  # entity/rel updates — status bar already reflects progress

            elif event == "token":
                token_buffer += data.get("token", "")
                token_count += 1
                if token_count % 20 == 0:
                    st.session_state.streaming_summary = token_buffer
                    summary_placeholder.markdown(token_buffer)

            elif event == "done":
                st.session_state.streaming_summary = token_buffer
                summary_placeholder.markdown(token_buffer)
                result = data.get("result", {})
                st.session_state.graph_result = result
                st.session_state.active_graph_id = result.get("graph_id")
                st.session_state.build_done = True
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


def render_graph_stats(result: dict):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Entities (Nodes)", result.get("node_count", 0))
    c2.metric("Relationships (Edges)", result.get("edge_count", 0))
    c3.metric("Graph Density", f"{result.get('graph_density', 0):.4f}")
    c4.metric("Components", result.get("connected_components", 0))
    c5.metric("Graph ID", result.get("graph_id", "—"))

    central = result.get("central_entities", [])
    if central:
        st.info(f"**Most connected entities:** {' · '.join(central)}")


def render_explore_tab(result: dict):
    entities = result.get("entities", [])
    relationships = result.get("relationships", [])

    # Entity type filter
    all_types = sorted(set(e["entity_type"] for e in entities))
    selected_types = st.multiselect(
        "Filter by entity type", options=all_types, default=all_types,
    )
    filtered_entities = [e for e in entities if e["entity_type"] in selected_types]

    col_left, col_right = st.columns([1, 2])
    with col_left:
        st.subheader(f"Entities ({len(filtered_entities)})")
        if filtered_entities:
            df_entities = pd.DataFrame([
                {
                    "ID": e["entity_id"],
                    "Name": e["name"],
                    "Type": e["entity_type"],
                    "Description": e.get("description", "")[:80],
                    "Confidence": f"{e.get('confidence', 0):.0%}",
                }
                for e in filtered_entities
            ])
            st.dataframe(df_entities, use_container_width=True, height=320)
        else:
            st.info("No entities match the filter.")

    with col_right:
        st.subheader(f"Relationships ({len(relationships)})")
        if relationships:
            df_rels = pd.DataFrame([
                {
                    "Source": r["source_name"],
                    "Type": r["relationship_type"],
                    "Target": r["target_name"],
                    "Description": r.get("description", "")[:80],
                    "Weight": f"{r.get('weight', 0):.2f}",
                }
                for r in relationships
            ])
            st.dataframe(df_rels, use_container_width=True, height=320)
        else:
            st.info("No relationships extracted.")

    # Pyvis graph
    st.subheader("Interactive Knowledge Graph")
    if filtered_entities:
        # Only show edges between filtered entities
        filtered_ids = {e["entity_id"] for e in filtered_entities}
        filtered_rels = [
            r for r in relationships
            if r["source_entity_id"] in filtered_ids and r["target_entity_id"] in filtered_ids
        ]
        html = build_pyvis_html(filtered_entities, filtered_rels)
        components.html(html, height=580, scrolling=False)

        # Legend
        st.markdown("**Entity type colour legend:**")
        leg_cols = st.columns(len(all_types) if len(all_types) <= 8 else 8)
        for col, et in zip(leg_cols, all_types):
            color = ENTITY_COLORS.get(et, "#888888")
            col.markdown(
                f'<span style="background:{color};padding:2px 8px;border-radius:4px;font-size:12px">{et}</span>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No entities to visualize.")

    # Type distribution
    st.subheader("Entity Type Distribution")
    if entities:
        type_counts = pd.DataFrame(
            pd.Series([e["entity_type"] for e in entities]).value_counts()
        ).reset_index()
        type_counts.columns = ["Entity Type", "Count"]
        st.bar_chart(type_counts.set_index("Entity Type"))

    # Downloads
    st.markdown("---")
    st.subheader("Downloads")
    dl_c1, dl_c2, dl_c3 = st.columns(3)

    dl_c1.download_button(
        "Download Full Export (.json)",
        data=json.dumps(result, indent=2),
        file_name=f"kg_{result.get('graph_id', 'export')}.json",
        mime="application/json",
    )
    if entities:
        df_e = pd.DataFrame([
            {"entity_id": e["entity_id"], "name": e["name"], "type": e["entity_type"],
             "description": e.get("description", ""), "aliases": "|".join(e.get("aliases", []))}
            for e in entities
        ])
        dl_c2.download_button(
            "Download Entities (.csv)",
            data=df_e.to_csv(index=False),
            file_name=f"entities_{result.get('graph_id', 'export')}.csv",
            mime="text/csv",
        )
    if relationships:
        df_r = pd.DataFrame([
            {"rel_id": r.get("rel_id", ""), "source": r["source_name"],
             "type": r["relationship_type"], "target": r["target_name"],
             "description": r.get("description", ""), "weight": r.get("weight", 0)}
            for r in relationships
        ])
        dl_c3.download_button(
            "Download Relationships (.csv)",
            data=df_r.to_csv(index=False),
            file_name=f"relationships_{result.get('graph_id', 'export')}.csv",
            mime="text/csv",
        )


def render_query_tab(graph_id: str):
    st.subheader("Semantic Graph Query")
    st.caption(
        "Query types auto-detected: entity name → **neighborhood** · two names → **path finding** · keywords → **search**"
    )

    query_text = st.text_input(
        "Ask a question about the knowledge graph",
        placeholder='e.g. "What is OpenAI?" or "How is Transformer related to BERT?" or "machine learning models"',
        key="query_input",
    )
    max_results = st.slider("Max results", min_value=5, max_value=30, value=15)

    if st.button("Run Query", type="primary") and query_text.strip():
        with st.spinner("Querying knowledge graph..."):
            try:
                resp = requests.post(
                    QUERY_ENDPOINT,
                    json={"graph_id": graph_id, "query_text": query_text, "max_results": max_results},
                    timeout=120,
                )
                if resp.status_code == 200:
                    st.session_state.query_result = resp.json()
                elif resp.status_code == 404:
                    st.error(f"Graph not found. Please build a graph first.")
                else:
                    st.error(f"Query failed: {resp.status_code} — {resp.text[:200]}")
            except Exception as e:
                st.error(f"Request failed: {e}")

    qr = st.session_state.query_result
    if qr and qr.get("graph_id") == graph_id:
        st.markdown("---")

        # Answer
        qt = QUERY_TYPE_LABELS.get(qr.get("query_type", ""), qr.get("query_type", ""))
        st.info(f"**Query type:** {qt} · **Time:** {qr.get('query_time_ms', 0):.0f} ms")
        st.markdown("### Answer")
        st.markdown(qr.get("answer", "No answer generated."))

        # Result entities
        r_entities = qr.get("result_entities", [])
        r_rels = qr.get("result_relationships", [])

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader(f"Result Entities ({len(r_entities)})")
            if r_entities:
                df_re = pd.DataFrame([
                    {"Name": e["name"], "Type": e["entity_type"],
                     "Description": e.get("description", "")[:80]}
                    for e in r_entities
                ])
                st.dataframe(df_re, use_container_width=True)

        with col_b:
            st.subheader(f"Result Relationships ({len(r_rels)})")
            if r_rels:
                df_rr = pd.DataFrame([
                    {"Source": r["source_name"], "→": r["relationship_type"], "Target": r["target_name"]}
                    for r in r_rels
                ])
                st.dataframe(df_rr, use_container_width=True)

        # Sub-graph visualization
        if r_entities:
            st.subheader("Sub-graph Visualization")
            html = build_pyvis_html(r_entities, r_rels)
            components.html(html, height=450, scrolling=False)


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.title("🕸️ Knowledge Graph")
    st.markdown("---")

    health = fetch_health()
    backend_ok   = health.get("status") not in ("unreachable",)
    ollama_ok    = health.get("ollama_connected", False)
    model_ok     = health.get("model_available", False)

    st.markdown("**System Status**")
    st.write(f"{'✅' if backend_ok else '❌'} Backend: {health.get('status', '—').upper()}")
    st.write(f"{'✅' if ollama_ok else '❌'} Ollama: {'Connected' if ollama_ok else 'Disconnected'}")
    st.write(f"{'✅' if model_ok else '❌'} Model: {health.get('model', '—')}")

    # Graph list
    st.markdown("---")
    st.markdown("**Built Graphs**")
    try:
        graphs_resp = requests.get(GRAPHS_ENDPOINT, timeout=5)
        graphs_list = graphs_resp.json() if graphs_resp.status_code == 200 else []
    except Exception:
        graphs_list = []

    if graphs_list:
        for g in graphs_list:
            if st.button(
                f"📊 {g['document_title'][:22]} ({g['node_count']}n, {g['edge_count']}e)",
                key=f"load_{g['graph_id']}",
            ):
                st.session_state.active_graph_id = g["graph_id"]
                try:
                    gdata = requests.get(f"{GRAPHS_ENDPOINT}/{g['graph_id']}", timeout=30).json()
                    st.session_state.graph_result = gdata
                    st.session_state.build_done = True
                except Exception as ex:
                    st.error(f"Load failed: {ex}")
    else:
        st.caption("No graphs built yet.")

    st.markdown("---")
    with st.expander("Entity Colour Legend"):
        for et, color in ENTITY_COLORS.items():
            st.markdown(
                f'<span style="background:{color};padding:2px 8px;border-radius:4px;'
                f'font-size:12px;color:#111">{et}</span>',
                unsafe_allow_html=True,
            )

    with st.expander("Query Tips"):
        st.markdown("""
- **Neighborhood**: Type one entity name → get its connections
- **Path finding**: Type two entity names → find how they're linked
- **Keyword search**: Use domain terms → find related entities
- **Examples**: "What is GPT?" / "BERT to Transformer" / "neural network training"
        """)


# ──────────────────────────────────────────────
# Main — 3 tabs
# ──────────────────────────────────────────────
st.title("🕸️ Knowledge Graph Agent")
st.caption("Extract entities & relationships from any domain document — then query the graph semantically")

build_tab, explore_tab, query_tab = st.tabs(["Build Graph", "Explore Graph", "Query Graph"])

with build_tab:
    st.subheader("Load a Domain Document")

    c1, c2 = st.columns(2)
    with c1:
        doc_title = st.text_input("Document Title", placeholder="e.g., AI Research Landscape 2024")
        domain    = st.text_input("Domain Hint (optional)", placeholder="e.g., Artificial Intelligence, Biotech, Finance")
    with c2:
        source_type = st.radio("Input Type", ["text", "url"], horizontal=True,
                               format_func=lambda x: "Plain Text" if x == "text" else "URL (fetch)")

    if source_type == "text":
        raw_content = st.text_area(
            "Document Content",
            placeholder="Paste your domain document here (research papers, reports, Wikipedia articles, etc.)",
            height=280,
        )
    else:
        raw_content = st.text_input("URL", placeholder="https://en.wikipedia.org/wiki/Artificial_intelligence")

    build_btn = st.button(
        "Build Knowledge Graph",
        type="primary",
        disabled=not (backend_ok and ollama_ok and model_ok),
    )

    if build_btn:
        if not doc_title.strip():
            st.error("Please provide a document title.")
        elif len(raw_content.strip()) < 20:
            st.error("Document content must be at least 20 characters.")
        else:
            with st.spinner("Building knowledge graph..."):
                run_streaming_build(
                    raw_content=raw_content.strip(),
                    document_title=doc_title.strip(),
                    domain=domain.strip(),
                    source_type=source_type,
                )

    if st.session_state.build_done and st.session_state.graph_result:
        st.markdown("---")
        render_graph_stats(st.session_state.graph_result)
        if st.session_state.streaming_summary:
            st.markdown("### Graph Summary")
            st.markdown(st.session_state.streaming_summary)

with explore_tab:
    if st.session_state.graph_result:
        render_graph_stats(st.session_state.graph_result)
        render_explore_tab(st.session_state.graph_result)
    else:
        st.info("Build a graph first to explore it here.")

with query_tab:
    if st.session_state.active_graph_id and st.session_state.graph_result:
        st.info(
            f"Querying graph: **{st.session_state.graph_result.get('document_title', '')}** "
            f"(ID: `{st.session_state.active_graph_id}`)"
        )
        render_query_tab(st.session_state.active_graph_id)
    else:
        st.info("Build a graph first to query it here.")
