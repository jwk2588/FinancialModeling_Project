#!/usr/bin/env python3
"""
NEXUS — Two-Layer ChatGPT / LLM Export Ingest Pipeline

Layer 1 (Deterministic — no API key needed):
  Parse ChatGPT conversations.json → extract assistant messages →
  keyword-map to domains → generate GR nodes + evidence anchors

Layer 2 (Claude API enrichment — optional):
  Feed Layer-1 extracted text back through NexusAgent →
  Claude identifies deeper intelligence, cross-links, GR routings,
  flywheel scores — writing results back to the live data store

Usage:
    python nexus_ingest_chatgpt.py <conversations.json>         # Layer 1 only
    python nexus_ingest_chatgpt.py <conversations.json> --l2    # + Layer 2
    python nexus_ingest_chatgpt.py <conversations.json> --l2 --api-key sk-ant-...
"""

import json
import re
import sys
import os
import hashlib
from pathlib import Path
from typing import Iterator

# ---------------------------------------------------------------------------
# ChatGPT conversations.json format helpers
# ---------------------------------------------------------------------------

def extract_messages(conversation: dict) -> list[dict]:
    """
    Extract ordered messages from a ChatGPT conversation dict.
    Supports both old flat format and new 'mapping' tree format.
    Returns list of {role, text, ts} dicts.
    """
    messages = []

    # New format: conversation has a 'mapping' dict of nodes
    if "mapping" in conversation:
        mapping = conversation["mapping"]
        # Walk the tree: find root node and traverse children
        nodes = {nid: node for nid, node in mapping.items()}

        # Build child lookup
        children_of = {}
        root_id = None
        for nid, node in nodes.items():
            parent = node.get("parent")
            if parent is None or parent not in nodes:
                root_id = nid
            else:
                children_of.setdefault(parent, []).append(nid)

        # DFS to get ordered messages
        def walk(nid):
            node = nodes.get(nid, {})
            msg = node.get("message")
            if msg and msg.get("content"):
                role = msg.get("author", {}).get("role", "unknown")
                content = msg["content"]
                # Extract text parts
                parts = content.get("parts", [])
                text = " ".join(str(p) for p in parts if isinstance(p, str)).strip()
                if text and role in ("user", "assistant"):
                    messages.append({
                        "role": role,
                        "text": text,
                        "ts": msg.get("create_time", 0),
                    })
            for child_id in sorted(children_of.get(nid, [])):
                walk(child_id)

        if root_id:
            walk(root_id)

    # Old/simple format: flat list of messages
    elif "messages" in conversation:
        for msg in conversation["messages"]:
            role = msg.get("role", "unknown")
            text = msg.get("content", "")
            if isinstance(text, list):
                text = " ".join(str(p) for p in text)
            if text and role in ("user", "assistant"):
                messages.append({"role": role, "text": str(text).strip(), "ts": 0})

    return messages


def parse_conversations_json(raw: str) -> list[dict]:
    """
    Parse a ChatGPT conversations.json export (list of conversations).
    Also handles single conversation dict or Claude project JSON variants.
    Returns list of conversation dicts with normalized structure.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    # Normalize to list
    if isinstance(data, dict):
        # Claude project export has {conversations: [...]} or {chats: [...]}
        if "conversations" in data:
            data = data["conversations"]
        elif "chats" in data:
            data = data["chats"]
        elif "mapping" in data or "messages" in data:
            data = [data]  # Single conversation
        else:
            data = [data]

    if not isinstance(data, list):
        raise ValueError("Expected JSON array of conversations")

    return data


# ---------------------------------------------------------------------------
# Domain detection — maps text to NEXUS flywheel domains
# ---------------------------------------------------------------------------

DOMAIN_PATTERNS = {
    "forensic_accounting": re.compile(
        r"asc[\s_-]?606|asc[\s_-]?810|icfr|revenue recognition|breakage|"
        r"principal.agent|restatement|audit|pcaob|sox\s*404|icfr|gaap|"
        r"virtual currency|tier credit|tc inflation|off.balance",
        re.I,
    ),
    "regulatory_cftc": re.compile(
        r"cftc|cea\s*§|commodity exchange|nfa|mgcb|michigan gaming|"
        r"r\s*432\.\d+|crowey test|derivatives|options.*classif|sec\s+filing|"
        r"exchange act|material change",
        re.I,
    ),
    "corp_accountability": re.compile(
        r"caremark|fiduciary|board.*oversight|vie.*structure|gps llc|"
        r"dynasty store|arbitration|autozone|klapp|illusory consideration|"
        r"forum.*destabil|asc\s*810|consolidat",
        re.I,
    ),
    "privacy_tech": re.compile(
        r"privacy|tos|terms of service|gdpr|ccpa|data collect|consent|"
        r"platform liability|section 230|att bypass|apple.*removal",
        re.I,
    ),
    "harm_reduction": re.compile(
        r"mcpa|§445\.903|consumer protection|udap|smith.*globe|anti.exemption|"
        r"fre 901|fre 803|evidence chain|authentication|chain of custody|"
        r"mcpa demand|arbitration kill",
        re.I,
    ),
    "neuropharm": re.compile(
        r"dopamine|addictive design|variable reward|harm reduction|aops|"
        r"dsm.5|gambling disorder|behavioral economics|sunk cost|loss aversion",
        re.I,
    ),
    "litigation_risk": re.compile(
        r"rico|class action|hermalyn|settlement|damages|restitution|"
        r"class cert|standing|3\.6 million|demand letter",
        re.I,
    ),
}

# GR node tag extraction patterns
ENTITY_PATTERNS = {
    "gps_llc": re.compile(r"gps\s*llc|dynasty store", re.I),
    "tier_credits": re.compile(r"tier credit|tc inflation|483%|crown.*tier|diamond.*onyx", re.I),
    "arbitration": re.compile(r"arbitration|autozone|klapp|ground\s*[1-7]", re.I),
    "vie": re.compile(r"vie\s+structure|asc\s*810|primary beneficiary|consolidat", re.I),
    "cftc": re.compile(r"cftc|cea\s*§|crowey|binary.*option|commodity option", re.I),
    "mgcb": re.compile(r"mgcb|r\s*432|material change|michigan gaming", re.I),
    "evidence": re.compile(r"ev-\d+|exhibit\s+[A-Z]|exhibit\s+\d+|fre\s+\d+", re.I),
    "ioc_credits": re.compile(r"ioc|off.book credit|alex franks|lemmyexcel", re.I),
}

EVIDENCE_CODE_PATTERN = re.compile(r"\bEV-[A-Z0-9\-]+\b|\bSB-[A-Z0-9\-]+\b|\bEX-[A-Z]+\b", re.I)


def detect_domains(text: str) -> list[str]:
    """Return list of matching domain keys for a text block."""
    return [dom for dom, pat in DOMAIN_PATTERNS.items() if pat.search(text)]


def extract_evidence_codes(text: str) -> list[str]:
    """Extract EV-NNN, SB-NNN, EX-B style codes from text."""
    return list(set(m.upper() for m in EVIDENCE_CODE_PATTERN.findall(text)))


def detect_entities(text: str) -> list[str]:
    """Return list of entity tags found in text."""
    return [tag for tag, pat in ENTITY_PATTERNS.items() if pat.search(text)]


def node_id_from_conv(conv_title: str, index: int) -> str:
    h = hashlib.md5(f"{conv_title}{index}".encode()).hexdigest()[:6].upper()
    return f"CGT-{h}"


# ---------------------------------------------------------------------------
# Layer 1 — Deterministic extraction
# ---------------------------------------------------------------------------

def layer1_extract(conversations: list[dict]) -> dict:
    """
    Layer 1: Parse conversations → structured intelligence records.
    No API calls. Returns dict with gr_nodes, evidence_anchors, flywheel_deltas.
    """
    gr_nodes = {}
    evidence_anchors = {}
    domain_hit_counts: dict[str, int] = {}
    stats = {"conversations": 0, "messages": 0, "nodes_created": 0, "ev_codes": 0}

    for conv_idx, conv in enumerate(conversations):
        title = conv.get("title", f"Conversation-{conv_idx+1}")
        messages = extract_messages(conv)
        stats["conversations"] += 1

        # Concatenate assistant turns as the intelligence content
        assistant_text = " ".join(
            m["text"] for m in messages if m["role"] == "assistant"
        )
        user_text = " ".join(
            m["text"] for m in messages if m["role"] == "user"
        )
        full_text = f"{title} {user_text} {assistant_text}"

        if not assistant_text.strip():
            continue

        stats["messages"] += len(messages)

        # Domain detection
        domains = detect_domains(full_text)
        if not domains:
            domains = ["litigation_risk"]  # default for DK case content

        for d in domains:
            domain_hit_counts[d] = domain_hit_counts.get(d, 0) + 1

        # Evidence code extraction
        ev_codes = extract_evidence_codes(full_text)
        stats["ev_codes"] += len(ev_codes)

        # Entity tags
        entities = detect_entities(full_text)

        # Nuclear impact: scored by domain count × entity count × assistant length signal
        raw_impact = min(90, 40 + len(domains) * 8 + len(entities) * 5 + min(20, len(assistant_text) // 500))

        # Build GR node
        nid = node_id_from_conv(title, conv_idx)
        summary_text = assistant_text[:600].replace("\n", " ")

        # Build agent routing from content
        wolf_routing = ""
        tiger_routing = ""
        suits_routing = ""

        if "forensic_accounting" in domains or "harm_reduction" in domains:
            suits_routing = f"Layer-1 extract: {summary_text[:200]}"
        if "regulatory_cftc" in domains or "corp_accountability" in domains:
            wolf_routing = f"Layer-1 regulatory: {', '.join(entities[:4])} | domains: {', '.join(domains)}"
        if any(d in domains for d in ("forensic_accounting", "litigation_risk")):
            tiger_routing = f"Layer-1 quant signal: {len(ev_codes)} EV codes | impact={raw_impact}"

        node = {
            "node_id": nid,
            "name": title[:80],
            "nuclear_impact": raw_impact,
            "agents": _agents_for_domains(domains),
            "flywheel_domains": domains,
            "ev_codes": " | ".join(ev_codes[:8]) if ev_codes else "",
            "mb_refs": "",
            "sb_refs": "",
            "evidence": [summary_text[:400]],
            "wolf_routing": wolf_routing,
            "tiger_routing": tiger_routing,
            "suits_routing": suits_routing,
            "source": "chatgpt_export",
            "entities": entities,
        }

        gr_nodes[nid] = node
        stats["nodes_created"] += 1

        # Evidence anchor mappings
        for ev in ev_codes:
            if ev not in evidence_anchors:
                evidence_anchors[ev] = []
            if nid not in evidence_anchors[ev]:
                evidence_anchors[ev].append(nid)

    # Flywheel delta: proportional to domain hit counts
    total_hits = max(1, sum(domain_hit_counts.values()))
    flywheel_deltas = {
        dom: round(min(5.0, (hits / total_hits) * 10), 2)
        for dom, hits in domain_hit_counts.items()
    }

    return {
        "gr_nodes": gr_nodes,
        "evidence_anchors": evidence_anchors,
        "flywheel_deltas": flywheel_deltas,
        "domain_distribution": domain_hit_counts,
        "stats": stats,
    }


def _agents_for_domains(domains: list[str]) -> list[str]:
    agents = set()
    if any(d in domains for d in ("forensic_accounting", "corp_accountability")):
        agents.update(["TIGER", "SUITS"])
    if any(d in domains for d in ("regulatory_cftc", "litigation_risk", "harm_reduction")):
        agents.update(["WOLF", "SUITS"])
    if any(d in domains for d in ("privacy_tech", "neuropharm")):
        agents.add("WOLF")
    return sorted(agents) if agents else ["NEXUS_MASTER"]


# ---------------------------------------------------------------------------
# Layer 2 — Claude API enrichment
# ---------------------------------------------------------------------------

def layer2_enrich(layer1_result: dict, api_key: str | None = None, max_nodes: int = 8) -> dict:
    """
    Layer 2: Feed top Layer-1 nodes back through Claude API for deep enrichment.

    For each top-impact node, Claude:
    - Identifies additional GR node cross-links
    - Assigns precise wolf/tiger/suits routings
    - Scores flywheel domain impact
    - Extracts additional evidence anchors

    Returns enriched gr_nodes dict (merged with layer1 nodes).
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from nexus_ai import NexusAgent, build_context_block, load_gr_nodes, load_flywheel

    agent = NexusAgent(api_key=api_key, mode="online")
    if not agent._api_key:
        print("  [Layer 2] No API key — skipping Claude enrichment")
        return layer1_result

    enriched_nodes = dict(layer1_result["gr_nodes"])
    nodes_by_impact = sorted(
        enriched_nodes.values(),
        key=lambda n: float(n.get("nuclear_impact", 0)),
        reverse=True,
    )[:max_nodes]

    print(f"  [Layer 2] Enriching {len(nodes_by_impact)} nodes via Claude API...")

    for node in nodes_by_impact:
        nid = node["node_id"]
        name = node["name"]
        evidence_text = " ".join(node.get("evidence", []))[:800]
        domains = node.get("flywheel_domains", [])

        prompt = f"""\
NEXUS Layer-2 Enrichment: Analyze this ChatGPT-extracted intelligence node.

Node: {nid} — "{name}"
Domains: {', '.join(domains)}
Raw extract: {evidence_text}

Tasks:
1. WOLF routing (adversarial/litigation attack vector — 1-2 sentences)
2. TIGER routing (quantitative risk score and model signal — 1-2 sentences)
3. SUITS routing (compliance/governance implication — 1-2 sentences)
4. Revised nuclear_impact score (0-100, DK case relevance)
5. Cross-links to existing GR nodes if relevant (list GR-NNN IDs)

Format response as JSON only:
{{"wolf":"...","tiger":"...","suits":"...","nuclear_impact":XX,"cross_links":["GR-NNN"]}}"""

        try:
            result = agent.ask(
                prompt,
                persona="nexus_master",
                use_tools=False,
                stream_print=False,
                inject_context=True,
            )
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]+\}', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                node["wolf_routing"] = parsed.get("wolf", node.get("wolf_routing", ""))
                node["tiger_routing"] = parsed.get("tiger", node.get("tiger_routing", ""))
                node["suits_routing"] = parsed.get("suits", node.get("suits_routing", ""))
                if "nuclear_impact" in parsed:
                    node["nuclear_impact"] = float(parsed["nuclear_impact"])
                if "cross_links" in parsed:
                    node["cross_links"] = parsed["cross_links"]
                enriched_nodes[nid] = node
                print(f"    ✓ {nid} enriched (impact={node['nuclear_impact']})")
        except Exception as e:
            print(f"    ✗ {nid} enrichment failed: {e}")

    layer1_result["gr_nodes"] = enriched_nodes
    layer1_result["layer2_enriched"] = True
    return layer1_result


# ---------------------------------------------------------------------------
# Persistence — merge into live data store
# ---------------------------------------------------------------------------

def persist_results(result: dict) -> dict:
    """Merge Layer-1/2 results into the live NEXUS data store."""
    sys.path.insert(0, str(Path(__file__).parent))
    from nexus_ai import (
        load_gr_nodes, load_flywheel, load_evidence,
        _save_json, GR_NODES_FILE, FLYWHEEL_FILE, EVIDENCE_FILE,
    )

    # Load existing
    existing_nodes = load_gr_nodes()
    existing_flywheel = load_flywheel()
    existing_evidence = load_evidence()

    # Merge GR nodes (new nodes only — don't overwrite existing)
    new_node_count = 0
    for nid, node in result["gr_nodes"].items():
        if nid not in existing_nodes:
            existing_nodes[nid] = node
            new_node_count += 1
        else:
            # Update routings if Layer 2 enriched
            if result.get("layer2_enriched"):
                for key in ("wolf_routing", "tiger_routing", "suits_routing", "nuclear_impact"):
                    if node.get(key):
                        existing_nodes[nid][key] = node[key]

    # Merge evidence anchors
    new_ev_count = 0
    for ev_code, node_ids in result["evidence_anchors"].items():
        if ev_code not in existing_evidence:
            existing_evidence[ev_code] = node_ids
            new_ev_count += len(node_ids)
        else:
            for nid in node_ids:
                if nid not in existing_evidence[ev_code]:
                    existing_evidence[ev_code].append(nid)
                    new_ev_count += 1

    # Apply flywheel deltas
    for domain, delta in result.get("flywheel_deltas", {}).items():
        if domain in existing_flywheel:
            entry = existing_flywheel[domain]
            current = entry.get("score", entry) if isinstance(entry, dict) else entry
            new_score = min(100, float(current) + delta)
            if isinstance(existing_flywheel[domain], dict):
                existing_flywheel[domain]["score"] = round(new_score, 1)
            else:
                existing_flywheel[domain] = round(new_score, 1)

    # Save all
    _save_json(GR_NODES_FILE, existing_nodes)
    _save_json(FLYWHEEL_FILE, existing_flywheel)
    _save_json(EVIDENCE_FILE, existing_evidence)

    return {
        "new_nodes": new_node_count,
        "new_evidence": new_ev_count,
        "total_nodes": len(existing_nodes),
        "total_evidence": len(existing_evidence),
        "flywheel_deltas": result.get("flywheel_deltas", {}),
        "domain_distribution": result.get("domain_distribution", {}),
        "layer2_enriched": result.get("layer2_enriched", False),
        "stats": result.get("stats", {}),
    }


# ---------------------------------------------------------------------------
# Main ingest entry point
# ---------------------------------------------------------------------------

def ingest_chatgpt(
    path_or_json: str,
    run_layer2: bool = False,
    api_key: str | None = None,
    max_l2_nodes: int = 8,
) -> dict:
    """
    Full two-layer ChatGPT ingest pipeline.

    Args:
        path_or_json: File path to conversations.json OR raw JSON string
        run_layer2:   Whether to run Claude API enrichment after Layer 1
        api_key:      Anthropic API key (or set ANTHROPIC_API_KEY env var)
        max_l2_nodes: Max nodes to enrich in Layer 2 (cost control)

    Returns:
        Summary dict with new_nodes, new_evidence, flywheel_deltas, stats
    """
    # Load raw JSON
    path = Path(path_or_json)
    if path.exists():
        raw = path.read_text(encoding="utf-8", errors="replace")
        source_name = path.name
    else:
        raw = path_or_json
        source_name = "pasted_json"

    print(f"\nNEXUS INGEST: {source_name} (Layer 1 — deterministic parse)")
    conversations = parse_conversations_json(raw)
    print(f"  Parsed: {len(conversations)} conversations")

    # Layer 1
    l1 = layer1_extract(conversations)
    stats = l1["stats"]
    print(f"  Layer 1 complete: {stats['nodes_created']} nodes | "
          f"{stats['ev_codes']} EV codes | "
          f"{stats['messages']} messages")
    print(f"  Domains: {dict(sorted(l1['domain_distribution'].items(), key=lambda x: -x[1]))}")

    # Layer 2 (optional)
    if run_layer2:
        print(f"\n  Layer 2 — Claude API enrichment (max {max_l2_nodes} nodes):")
        l1 = layer2_enrich(l1, api_key=api_key, max_nodes=max_l2_nodes)

    # Persist
    result = persist_results(l1)

    bar = "█" * min(40, result["new_nodes"] // 2)
    print(f"\n{'='*60}")
    print(f"NEXUS CHATGPT INGEST COMPLETE")
    print(f"  New GR nodes:     {result['new_nodes']} (total: {result['total_nodes']})")
    print(f"  New EV anchors:   {result['new_evidence']} (total: {result['total_evidence']})")
    print(f"  Layer 2 enriched: {'YES' if result['layer2_enriched'] else 'NO (pass --l2 to enable)'}")
    print(f"  Flywheel deltas:  {result['flywheel_deltas']}")
    print(f"{'='*60}\n")

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NEXUS ChatGPT/LLM Export Ingest")
    parser.add_argument("file", help="Path to conversations.json (ChatGPT export)")
    parser.add_argument("--l2", action="store_true", help="Run Layer 2 Claude enrichment")
    parser.add_argument("--api-key", help="Anthropic API key for Layer 2")
    parser.add_argument("--max-nodes", type=int, default=8, help="Max nodes for Layer 2 (default: 8)")
    args = parser.parse_args()

    result = ingest_chatgpt(
        args.file,
        run_layer2=args.l2,
        api_key=args.api_key or os.environ.get("ANTHROPIC_API_KEY"),
        max_l2_nodes=args.max_nodes,
    )
    sys.exit(0)
