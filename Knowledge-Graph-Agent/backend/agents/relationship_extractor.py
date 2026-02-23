import json
import logging
import re

from core.llm import get_llm
from agents.state import KnowledgeGraphState
from config import RELATIONSHIP_TYPES, MAX_RELS_PER_CHUNK

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _dedup_relationships(raw: list, name_to_id: dict) -> list:
    seen: set = set()
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source_name", "")).strip()
        tgt = str(item.get("target_name", "")).strip()
        rel_type = str(item.get("relationship_type", "RELATED_TO")).strip().upper()
        if not src or not tgt or src.lower() == tgt.lower():
            continue
        src_id = name_to_id.get(src.lower())
        tgt_id = name_to_id.get(tgt.lower())
        if not src_id or not tgt_id:
            continue
        key = (src_id, tgt_id, rel_type)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "source_entity_id": src_id,
            "target_entity_id": tgt_id,
            "source_name": src,
            "target_name": tgt,
            "relationship_type": rel_type if rel_type in RELATIONSHIP_TYPES else "RELATED_TO",
            "description": str(item.get("description", "")),
            "weight": min(1.0, max(0.0, float(item.get("weight", 0.7)))),
        })
    return result


def relationship_extractor(state: KnowledgeGraphState) -> KnowledgeGraphState:
    logger.info("Node 3: relationship_extractor — extracting entity relationships")
    messages = list(state.get("progress_messages", []))
    messages.append("Extracting relationships between entities...")

    chunks = state.get("text_chunks", [])
    entities = state.get("entities", [])
    domain = state.get("domain", "")

    if not entities or not chunks:
        messages.append("Skipping — no entities or chunks available")
        return {**state, "relationships": [], "relationship_types_found": [],
                "current_agent": "relationship_extractor", "progress_messages": messages}

    name_to_id = {e["name"].lower(): e["entity_id"] for e in entities}
    entity_names = [e["name"] for e in entities]
    entity_list_str = ", ".join(entity_names[:60])  # truncate if huge

    llm = get_llm()
    raw_relationships: list = []

    for i, chunk in enumerate(chunks):
        prompt = f"""Identify relationships between entities in the following text.

Domain: {domain if domain else 'general'}
Known entities: {entity_list_str}

Text:
{chunk}

Return ONLY a JSON array of up to {MAX_RELS_PER_CHUNK} relationships between the known entities above:
[
  {{
    "source_name": "<entity name from known list>",
    "target_name": "<entity name from known list>",
    "relationship_type": "<one of: {', '.join(RELATIONSHIP_TYPES)}>",
    "description": "<1 sentence describing the relationship>",
    "weight": <0.0–1.0 confidence>
  }}
]

Only use entity names from the known list. Do NOT invent new entities. Return valid JSON array only."""

        try:
            response = llm.invoke(prompt)
            raw = _strip_fence(response.content)
            data = json.loads(raw)
            if isinstance(data, list):
                raw_relationships.extend(data)
                logger.debug(f"Chunk {i+1}: extracted {len(data)} relationships")
        except Exception as e:
            logger.warning(f"Relationship extraction failed on chunk {i+1}: {e}")
            continue

    relationships = _dedup_relationships(raw_relationships, name_to_id)

    # Assign sequential IDs
    for i, r in enumerate(relationships):
        r["rel_id"] = f"R{i+1:03d}"

    rel_types_found = sorted(set(r["relationship_type"] for r in relationships))
    messages.append(
        f"Extracted {len(relationships)} relationships. "
        f"Types: {', '.join(rel_types_found) if rel_types_found else 'none'}"
    )

    return {
        **state,
        "relationships": relationships,
        "relationship_types_found": rel_types_found,
        "current_agent": "relationship_extractor",
        "progress_messages": messages,
    }
