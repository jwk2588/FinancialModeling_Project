"""
NEXUS Layer 2B — ChatGPT Export Ingestion
Parses a static conversations.json export from ChatGPT.
No OpenAI API access required — works entirely from the export file.

Usage:
    python ingestion/layer2_chatgpt.py /path/to/conversations.json
    from ingestion.layer2_chatgpt import ingest_chatgpt_export
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

DATA_DIR = Path(__file__).parent.parent / "data" / "nexus"
CHATGPT_FILE = DATA_DIR / "chatgpt_corpus.json"


# ── DOMAIN KEYWORD CLASSIFIER ─────────────────────────────────────────────────

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "forensic_accounting": [
        "asc 606", "gaap", "breakage", "revenue recognition", "icfr", "sox",
        "internal controls", "material weakness", "restatement", "bdo", "audit",
        "tier credit", "crown coin", "virtual currency",
    ],
    "regulatory_cftc": [
        "cftc", "commodity exchange", "cea §", "mgcb", "michigan gaming",
        "nfa", "crowey", "binary option", "derivatives", "dufoe", "gus ii",
        "registration gap", "unlicensed",
    ],
    "corp_accountability": [
        "caremark", "board oversight", "fiduciary", "vie", "gps llc", "dynasty store",
        "asc 810", "arbitration", "autozone", "illusory consideration",
        "unconscionability", "forum", "kill ground",
    ],
    "neuropharm": [
        "dopamine", "addiction", "variable reward", "harm reduction", "aops",
        "behavioral", "dsg", "dsg-7", "vulnerable", "problem gambling",
        "sunk cost", "loss aversion",
    ],
    "privacy_tech": [
        "privacy", "terms of service", "tos", "data collection", "ccpa", "gdpr",
        "consent", "any reason or no reason", "platform liability", "§230",
    ],
    "harm_reduction": [
        "mcpa", "consumer protection", "udap", "fre 901", "authentication",
        "chain of custody", "evidence", "class action", "class standing",
        "restitution", "smith v", "globe life",
    ],
}


def _classify_domains(text: str) -> list[str]:
    """Classify text into domain tags using keyword matching."""
    lower = text.lower()
    matched = [dom for dom, kws in DOMAIN_KEYWORDS.items() if any(kw in lower for kw in kws)]
    return matched or ["general"]


def _classify_agent_routing(text: str) -> str:
    """Determine which Nexus agent best fits this content chunk."""
    lower = text.lower()
    wolf_signals = ["evidence", "fre", "chain of custody", "authentication", "mcpa", "tos clause"]
    tiger_signals = ["analogy", "like", "similar to", "compare", "pattern", "framework", "model"]
    if any(s in lower for s in wolf_signals):
        return "wolf"
    if any(s in lower for s in tiger_signals):
        return "tiger"
    return "nexus_master"


def _extract_message_tree(mapping: dict) -> list[dict]:
    """
    Flatten ChatGPT conversation tree (mapping dict) into ordered message list.
    ChatGPT exports use a linked-list-style mapping with parent UUIDs.
    """
    if not mapping:
        return []

    # Build parent→children adjacency
    children: dict[str | None, list[str]] = {}
    for node_id, node in mapping.items():
        parent = node.get("parent")
        children.setdefault(parent, []).append(node_id)

    messages: list[dict] = []

    def traverse(node_id: str | None) -> None:
        if node_id is None:
            roots = children.get(None, [])
            for r in roots:
                traverse(r)
            return
        node = mapping.get(node_id, {})
        msg = node.get("message")
        if msg:
            role = msg.get("author", {}).get("role", "unknown")
            # Content can be a string or a list of content parts
            content_raw = msg.get("content", {})
            if isinstance(content_raw, dict):
                parts = content_raw.get("parts", [])
                text = " ".join(str(p) for p in parts if isinstance(p, str))
            elif isinstance(content_raw, str):
                text = content_raw
            else:
                text = ""
            if text.strip() and role in ("user", "assistant"):
                messages.append({
                    "role": role,
                    "text": text.strip(),
                    "create_time": msg.get("create_time"),
                    "node_id": node_id,
                })
        for child_id in children.get(node_id, []):
            traverse(child_id)

    traverse(None)
    return messages


def _chunk_text(text: str, max_chars: int = 1500) -> list[str]:
    """Split long text into overlapping chunks for indexing."""
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) > max_chars and current:
            chunks.append(current.strip())
            current = sent
        else:
            current += " " + sent
    if current.strip():
        chunks.append(current.strip())
    return chunks


def ingest_chatgpt_export(export_path: str | Path, project_id: str = "draftkings_masterbrief") -> dict:
    """
    Ingest a ChatGPT conversations.json export into the Nexus corpus.

    Args:
        export_path: Path to conversations.json from ChatGPT data export
        project_id:  Nexus project identifier for tagging

    Returns:
        Summary dict with ingestion stats
    """
    export_path = Path(export_path)
    if not export_path.exists():
        raise FileNotFoundError(f"ChatGPT export not found: {export_path}")

    with open(export_path, encoding="utf-8") as f:
        conversations = json.load(f)

    if not isinstance(conversations, list):
        raise ValueError("Expected conversations.json to be a JSON array")

    corpus: list[dict] = []
    stats = {"conversations": 0, "messages": 0, "chunks": 0, "domains_hit": set()}

    for convo in conversations:
        title = convo.get("title", "Untitled")
        create_time = convo.get("create_time")
        mapping = convo.get("mapping", {})

        messages = _extract_message_tree(mapping)
        stats["conversations"] += 1
        stats["messages"] += len(messages)

        for msg in messages:
            text = msg["text"]
            for chunk_text in _chunk_text(text):
                domains = _classify_domains(chunk_text)
                agent = _classify_agent_routing(chunk_text)
                stats["domains_hit"].update(domains)
                stats["chunks"] += 1

                corpus.append({
                    "source": "chatgpt_export",
                    "source_platform": "openai",
                    "conversation_title": title,
                    "conversation_create_time": create_time,
                    "message_role": msg["role"],
                    "message_create_time": msg.get("create_time"),
                    "text": chunk_text,
                    "word_count": len(chunk_text.split()),
                    "domain_tags": domains,
                    "agent_routing": agent,
                    "project_id": project_id,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                })

    # Persist to data/nexus/chatgpt_corpus.json
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing: list = []
    if CHATGPT_FILE.exists():
        try:
            existing = json.loads(CHATGPT_FILE.read_text())
        except Exception:
            existing = []

    # Deduplicate by (conversation_title, text hash) — avoid re-ingesting same export
    existing_keys = {(e.get("conversation_title"), len(e.get("text", ""))) for e in existing}
    new_items = [c for c in corpus if (c["conversation_title"], len(c["text"])) not in existing_keys]
    CHATGPT_FILE.write_text(json.dumps(existing + new_items, indent=2, ensure_ascii=False))

    stats["domains_hit"] = sorted(stats["domains_hit"])
    stats["new_chunks_added"] = len(new_items)
    stats["total_corpus_size"] = len(existing) + len(new_items)

    print(f"\nNEXUS LAYER 2B — ChatGPT Export Ingested")
    print(f"  Conversations: {stats['conversations']}")
    print(f"  Messages:      {stats['messages']}")
    print(f"  Chunks:        {stats['chunks']} ({stats['new_chunks_added']} new)")
    print(f"  Domains hit:   {', '.join(stats['domains_hit'])}")
    print(f"  Corpus total:  {stats['total_corpus_size']} chunks\n")

    return stats


def get_corpus_summary() -> dict:
    """Return stats about the current ChatGPT corpus."""
    if not CHATGPT_FILE.exists():
        return {"status": "empty", "chunks": 0}
    try:
        corpus = json.loads(CHATGPT_FILE.read_text())
        domain_counts: dict[str, int] = {}
        for chunk in corpus:
            for dom in chunk.get("domain_tags", []):
                domain_counts[dom] = domain_counts.get(dom, 0) + 1
        return {
            "status": "active",
            "chunks": len(corpus),
            "conversations": len({c.get("conversation_title") for c in corpus}),
            "domain_distribution": domain_counts,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ingestion/layer2_chatgpt.py /path/to/conversations.json")
        print("\nCurrent corpus status:")
        import json; print(json.dumps(get_corpus_summary(), indent=2))
        sys.exit(0)
    ingest_chatgpt_export(sys.argv[1], project_id=sys.argv[2] if len(sys.argv) > 2 else "nexus")
