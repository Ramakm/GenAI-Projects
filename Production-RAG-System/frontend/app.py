import json
import requests
import streamlit as st

from config import (
    HEALTH_URL,
    UPLOAD_URL,
    DOCUMENTS_URL,
    QUERY_URL,
    STREAM_URL,
    SUPPORTED_TYPES,
    DEFAULT_TOP_K,
    MAX_TOP_K,
    HEALTH_TIMEOUT,
    UPLOAD_TIMEOUT,
    QUERY_TIMEOUT,
    STREAM_TIMEOUT,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Production RAG",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Session state ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "use_streaming" not in st.session_state:
    st.session_state.use_streaming = True


# ── Helper functions ───────────────────────────────────────────────────────────

def fetch_health():
    try:
        resp = requests.get(HEALTH_URL, timeout=HEALTH_TIMEOUT)
        return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None


def fetch_documents():
    try:
        resp = requests.get(DOCUMENTS_URL, timeout=HEALTH_TIMEOUT)
        return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []


def delete_document(doc_id: str) -> bool:
    try:
        resp = requests.delete(f"{DOCUMENTS_URL}/{doc_id}", timeout=HEALTH_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def upload_file(uploaded_file) -> dict | None:
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        resp = requests.post(UPLOAD_URL, files=files, timeout=UPLOAD_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": resp.json().get("detail", "Upload failed")}
    except Exception as e:
        return {"error": str(e)}


def query_blocking(question: str, top_k: int) -> dict | None:
    try:
        resp = requests.post(
            QUERY_URL,
            json={"question": question, "top_k": top_k},
            timeout=QUERY_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            detail = resp.json().get("detail", "Query failed")
            return {"error": detail}
    except Exception as e:
        return {"error": str(e)}


def query_streaming(question: str, top_k: int):
    """Generator that yields (event_type, data) tuples from the SSE stream."""
    try:
        with requests.post(
            STREAM_URL,
            json={"question": question, "top_k": top_k},
            stream=True,
            timeout=STREAM_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line and line.startswith(b"data: "):
                    payload = json.loads(line[6:])
                    event = payload.get("event")
                    yield event, payload
    except Exception as e:
        yield "error", {"message": str(e)}


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Production RAG")

    # Health status
    st.subheader("System Status")
    health = fetch_health()
    if health:
        status = health.get("status", "unknown")
        color = {"healthy": "green", "degraded": "orange", "unhealthy": "red"}.get(status, "gray")
        st.markdown(f"**Status:** :{color}[{status.upper()}]")
        st.markdown(f"Ollama: {'✅' if health.get('ollama_connected') else '❌'}")
        st.markdown(f"Model: `{health.get('ollama_model', '?')}`")
        st.markdown(f"Docs indexed: **{health.get('total_documents', 0)}**")
        st.markdown(f"Total chunks: **{health.get('total_chunks', 0)}**")
        if health.get("detail"):
            st.info(health["detail"])
    else:
        st.error("Cannot reach backend. Is it running?")

    st.divider()

    # File uploader
    st.subheader("Upload Document")
    uploaded = st.file_uploader(
        "Choose a file",
        type=SUPPORTED_TYPES,
        help=f"Supported: {', '.join(SUPPORTED_TYPES).upper()}",
    )
    if uploaded and st.button("Index Document", type="primary"):
        with st.spinner(f"Uploading and indexing '{uploaded.name}'…"):
            result = upload_file(uploaded)
        if result and "error" not in result:
            st.success(
                f"Indexed **{result['filename']}** — {result['chunk_count']} chunks created."
            )
            st.rerun()
        elif result:
            st.error(f"Upload failed: {result['error']}")

    st.divider()

    # Indexed documents list
    st.subheader("Indexed Documents")
    docs = fetch_documents()
    if docs:
        for doc in docs:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{doc['filename']}**  \n{doc['chunk_count']} chunks")
            if col2.button("🗑️", key=f"del_{doc['doc_id']}", help="Delete"):
                if delete_document(doc["doc_id"]):
                    st.success(f"Deleted '{doc['filename']}'")
                    st.rerun()
                else:
                    st.error("Delete failed")
    else:
        st.caption("No documents indexed yet.")

    st.divider()

    # Settings
    st.subheader("Query Settings")
    st.session_state.use_streaming = st.toggle(
        "Streaming mode", value=st.session_state.use_streaming
    )
    top_k = st.slider("Chunks to retrieve (top_k)", 1, MAX_TOP_K, DEFAULT_TOP_K)

    if st.button("Clear chat history"):
        st.session_state.messages = []
        st.rerun()


# ── Main chat area ─────────────────────────────────────────────────────────────
st.header("Ask your documents")

# Render existing messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"Sources ({len(msg['sources'])} chunks retrieved)"):
                for i, src in enumerate(msg["sources"], 1):
                    st.markdown(
                        f"**[{i}] {src['source']}** "
                        f"(chunk {src['chunk_index']}, score={src['score']:.4f})"
                    )
                    st.code(src["content"], language=None)

# Chat input
if prompt := st.chat_input("Ask a question about your documents…"):
    # Append and show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        if st.session_state.use_streaming:
            sources = []
            answer_placeholder = st.empty()
            full_answer = ""

            for event, data in query_streaming(prompt, top_k):
                if event == "sources":
                    sources = data.get("sources", [])
                elif event == "token":
                    full_answer += data.get("token", "")
                    answer_placeholder.markdown(full_answer + "▌")
                elif event == "done":
                    answer_placeholder.markdown(full_answer)
                elif event == "error":
                    st.error(f"Streaming error: {data.get('message', 'Unknown error')}")
                    full_answer = "An error occurred during streaming."

            if sources:
                with st.expander(f"Sources ({len(sources)} chunks retrieved)"):
                    for i, src in enumerate(sources, 1):
                        st.markdown(
                            f"**[{i}] {src['source']}** "
                            f"(chunk {src['chunk_index']}, score={src['score']:.4f})"
                        )
                        st.code(src["content"], language=None)

            st.session_state.messages.append(
                {"role": "assistant", "content": full_answer, "sources": sources}
            )

        else:
            with st.spinner("Thinking…"):
                result = query_blocking(prompt, top_k)

            if result and "error" not in result:
                answer = result.get("answer", "No answer returned.")
                sources = result.get("sources", [])
                model = result.get("model_used", "?")

                st.markdown(answer)
                st.caption(f"Model: `{model}` | Chunks retrieved: {result.get('chunks_retrieved', 0)}")

                if sources:
                    with st.expander(f"Sources ({len(sources)} chunks retrieved)"):
                        for i, src in enumerate(sources, 1):
                            st.markdown(
                                f"**[{i}] {src['source']}** "
                                f"(chunk {src['chunk_index']}, score={src['score']:.4f})"
                            )
                            st.code(src["content"], language=None)

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": sources}
                )
            elif result:
                error_msg = f"Error: {result['error']}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg, "sources": []}
                )
            else:
                st.error("No response from backend.")
