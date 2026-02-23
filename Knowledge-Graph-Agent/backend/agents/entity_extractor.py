import json
import logging
import re

from core.llm import get_llm
from agents.state import KnowledgeGraphState
from config import ENTITY_TYPES, MAX_ENTITIES_PER_CHUNK, MAX_GRAPH_NODES

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _dedup_entities(raw: list) -> list:
    seen: dict = {}  # normalized_name -> entity dict
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        key = name.lower()
        if key not in seen:
            seen[key] = {
                "name": name,
                "entity_type": item.get("entity_type", "CONCEPT"),
                "description": str(item.get("description", "")),
                "aliases": list(item.get("aliases", [])),
                "confidence": float(item.get("confidence", 0.8)),
            }
            result.append(seen[key])
        else:
            # Merge aliases into existing
            new_aliases = item.get("aliases", [])
            seen[key]["aliases"] = list(set(seen[key]["aliases"] + new_aliases))
    return result


def entity_extractor(state: KnowledgeGraphState) -> KnowledgeGraphState:
    logger.info("Node 2: entity_extractor — extracting named entities")
    messages = list(state.get("progress_messages", []))
    messages.append("Extracting entities from document chunks...")

    chunks = state.get("text_chunks", [])
    domain = state.get("domain", "")
    if not chunks:
        messages.append("No text chunks to process")
        return {**state, "entities": [], "entity_types_found": [],
                "current_agent": "entity_extractor", "progress_messages": messages}

    llm = get_llm()
    raw_entities: list = []

    for i, chunk in enumerate(chunks):
        prompt = f"""Extract named entities from the following text.
Domain hint: {domain if domain else 'general'}

Text:
{chunk}

Return ONLY a JSON array of up to {MAX_ENTITIES_PER_CHUNK} entities:
[
  {{
    "name": "<entity name>",
    "entity_type": "<one of: {', '.join(ENTITY_TYPES)}>",
    "description": "<1–2 sentence description>",
    "aliases": ["<alternative name>"],
    "confidence": <0.0–1.0>
  }}
]

Only extract entities clearly present in the text. Return valid JSON array only."""

        try:
            response = llm.invoke(prompt)
            raw = _strip_fence(response.content)
            data = json.loads(raw)
            if isinstance(data, list):
                raw_entities.extend(data)
                logger.debug(f"Chunk {i+1}: extracted {len(data)} entities")
        except Exception as e:
            logger.warning(f"Entity extraction failed on chunk {i+1}: {e}")
            continue

    # Deduplicate and validate
    entities = _dedup_entities(raw_entities)

    # Enforce type whitelist
    for e in entities:
        if e["entity_type"] not in ENTITY_TYPES:
            e["entity_type"] = "CONCEPT"

    # Limit total
    entities = entities[:MAX_GRAPH_NODES]

    # Assign sequential IDs
    for i, e in enumerate(entities):
        e["entity_id"] = f"E{i+1:03d}"

    entity_types_found = sorted(set(e["entity_type"] for e in entities))
    messages.append(
        f"Extracted {len(entities)} unique entities across {len(chunks)} chunks. "
        f"Types: {', '.join(entity_types_found)}"
    )

    return {
        **state,
        "entities": entities,
        "entity_types_found": entity_types_found,
        "current_agent": "entity_extractor",
        "progress_messages": messages,
    }
