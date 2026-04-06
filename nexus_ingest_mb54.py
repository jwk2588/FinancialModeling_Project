#!/usr/bin/env python3
"""
NEXUS MasterBrief v54 Ingest Pipeline
Parses the structured MB v54 CSV and populates GR nodes, evidence anchors,
and flywheel scores without requiring a Claude API call.

Usage:
    python nexus_ingest_mb54.py                          # ingest data/nexus/masterbrief_v54.csv
    python nexus_ingest_mb54.py --csv path/to/file.csv  # custom CSV path
    python nexus_ingest_mb54.py --report                 # print current state summary
"""

import csv
import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data" / "nexus"
GR_NODES_FILE = DATA_DIR / "gr_nodes.json"
FLYWHEEL_FILE = DATA_DIR / "flywheel_scores.json"
EVIDENCE_FILE = DATA_DIR / "evidence_anchors.json"

# ---------------------------------------------------------------------------
# Priority → nuclear impact mapping
# ---------------------------------------------------------------------------

PRIORITY_IMPACT = {
    "P1-MUST": 95,
    "P2-HIGH": 82,
    "P3-MEDIUM": 70,
    "P4-STANDARD": 60,
    "—": 75,   # IN_MB_v54 active sections default
}

# Front linkage → flywheel domain mapping
FRONT_DOMAIN = {
    "BDO F01":   "revenue_recognition",
    "PCAOB F07": "revenue_recognition",
    "SEC F04":   "governance",
    "MGCB":      "governance",
    "MCPA":      "privacy_tos",
    "CFTC F08":  "platform_economics",
    "CFTC F08-01": "platform_economics",
    "Apple F02": "privacy_tos",
    "IRS F05":   "governance",
    "FinCEN F06":"platform_economics",
    "DOJ":       "litigation_risk",
    "RICO":      "litigation_risk",
    "AutoZone":  "litigation_risk",
    "All fronts":"litigation_risk",
    "All":       "litigation_risk",
}

# section_type → agent routing defaults
SECTION_AGENT = {
    "FRONT":             ["WOLF", "TIGER"],
    "ENGINE":            ["TIGER", "SUITS"],
    "BUNKER":            ["WOLF", "TIGER", "SUITS"],
    "BUNKER-PENDING":    ["WOLF", "TIGER", "SUITS"],
    "SECTION":           ["SUITS"],
    "SUBSECTION":        ["SUITS"],
    "SUBSECTION-PENDING":["SUITS", "WOLF"],
    "EXHIBIT":           ["TIGER"],
    "DISCOVERY-PENDING": ["WOLF"],
    "CASELAW-PENDING":   ["SUITS"],
    "CORRECTION-PENDING":["SUITS"],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default

def save_json(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def parse_ev_refs(raw: str) -> list[str]:
    """Extract individual EV codes from 'EV-004 | EV-055 | EV-091'."""
    if not raw:
        return []
    return [x.strip() for x in re.split(r'\s*\|\s*', raw.strip()) if x.strip()]

def parse_front_linkage(raw: str) -> list[str]:
    if not raw or raw in ("—", ""):
        return []
    return [x.strip() for x in raw.split(";")]

def infer_domains(fronts: list[str], section_type: str, legal_standards: str) -> list[str]:
    domains = set()
    for f in fronts:
        for key, domain in FRONT_DOMAIN.items():
            if key in f:
                domains.add(domain)
    # Keyword scan on legal standards
    ls = legal_standards.lower()
    if "asc 606" in ls or "asc 810" in ls or "bdo" in ls or "pcaob" in ls:
        domains.add("revenue_recognition")
    if "cftc" in ls or "cea" in ls or "howey" in ls or "dufoe" in ls:
        domains.add("platform_economics")
    if "mcpa" in ls or "mcl §445" in ls or "ftc" in ls or "privacy" in ls:
        domains.add("privacy_tos")
    if "sox" in ls or "sec " in ls or "caremark" in ls or "governance" in ls:
        domains.add("governance")
    if "rico" in ls or "18 u.s.c" in ls or "doj" in ls or "arb" in ls:
        domains.add("litigation_risk")
    return list(domains) if domains else ["litigation_risk"]

def node_id_from_section(section_id: str, counter: int) -> str:
    """Generate a GR node ID from a section_id."""
    # Clean up special chars for a compact key
    clean = re.sub(r'[§\-\.\s]', '', section_id.upper())
    return f"MB-{clean[:8]}"

# ---------------------------------------------------------------------------
# Main ingest
# ---------------------------------------------------------------------------

def ingest_csv(csv_path: Path):
    nodes = load_json(GR_NODES_FILE, {})
    flywheel = load_json(FLYWHEEL_FILE, {
        "revenue_recognition": {"score": 0, "rationale": "", "nodes": []},
        "platform_economics":  {"score": 0, "rationale": "", "nodes": []},
        "privacy_tos":         {"score": 0, "rationale": "", "nodes": []},
        "governance":          {"score": 0, "rationale": "", "nodes": []},
        "litigation_risk":     {"score": 0, "rationale": "", "nodes": []},
    })
    evidence = load_json(EVIDENCE_FILE, {})

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"NEXUS INGEST: {csv_path.name} — {len(rows)} sections")

    ev_counter = len(evidence) + 1
    new_nodes = 0
    new_evidence = 0

    # Accumulate domain signal scores per row
    domain_signal: dict[str, list[float]] = {d: [] for d in flywheel}

    for row in rows:
        sid = row.get("section_id", "").strip()
        stype = row.get("section_type", "").strip()
        title = row.get("section_title", "").strip()
        status = row.get("status", "").strip()
        priority = row.get("integration_priority", "—").strip()
        theory = row.get("key_theory_summary", "").strip()
        legal = row.get("legal_standards", "").strip()
        ev_raw = row.get("ev_references", "").strip()
        sb_raw = row.get("sb_references", "").strip()
        fronts_raw = row.get("front_linkage", "").strip()
        notes = row.get("notes", "").strip()
        pending = row.get("pending_content_summary", "").strip()

        if not sid:
            continue

        ev_codes = parse_ev_refs(ev_raw)
        fronts = parse_front_linkage(fronts_raw)
        domains = infer_domains(fronts, stype, legal)
        agents = SECTION_AGENT.get(stype, ["SUITS"])
        impact = PRIORITY_IMPACT.get(priority, 75)

        # Bump impact for P1 pending sections — they are HIGH priority additions
        if "PENDING" in status and priority == "P1-MUST":
            impact = 96

        # Construct GR node
        nid = node_id_from_section(sid, 0)
        evidence_list = []
        if theory:
            evidence_list.append(theory)
        if notes:
            evidence_list.append(f"NOTE: {notes}")
        if pending:
            evidence_list.append(f"PENDING: {pending[:200]}")

        # Build routing strings
        wolf_r = ""
        tiger_r = ""
        suits_r = ""
        if legal:
            suits_r = legal[:150]
        if "WOLF" in agents:
            wolf_r = f"{title[:80]} — {(theory[:80] if theory else '')}"
        if "TIGER" in agents:
            tiger_r = f"Standards: {(legal[:80] if legal else 'See section')} | EV: {ev_raw[:60]}"

        node = nodes.get(nid, {})
        node.update({
            "node_id": nid,
            "name": title[:80],
            "section_id": sid,
            "section_type": stype,
            "status": status,
            "integration_priority": priority,
            "nuclear_impact": max(node.get("nuclear_impact", 0), impact),
            "agents": agents,
            "evidence": list(set(node.get("evidence", []) + evidence_list)),
            "ev_codes": ev_raw,
            "sb_codes": sb_raw,
            "legal_standards": legal[:200] if legal else "",
            "wolf_routing": wolf_r,
            "tiger_routing": tiger_r,
            "suits_routing": suits_r,
            "fronts": fronts,
            "domains": domains,
            "tissue": fronts,
            "source": "MB_v54",
            "ingested_at": datetime.now().isoformat()[:19],
        })
        nodes[nid] = node
        new_nodes += 1

        # Create evidence anchors for each EV code referenced
        for ev_code in ev_codes:
            if ev_code not in evidence:
                eid = f"EVD-{ev_counter:04d}"
                ev_counter += 1
                evidence[eid] = {
                    "anchor_id": eid,
                    "ev_code": ev_code,
                    "text": f"{ev_code} referenced in {sid}: {title[:80]}",
                    "source": f"MB_v54/{sid}",
                    "domain": domains[0] if domains else "litigation_risk",
                    "gr_node": nid,
                    "legal_standards": legal[:150] if legal else "",
                    "theory": theory[:150] if theory else "",
                }
                new_evidence += 1

        # Flywheel signal: weight by nuclear_impact
        for domain in domains:
            if domain in flywheel:
                # Signal = normalized impact score contribution
                domain_signal[domain].append(impact / 100.0)

    # Recompute flywheel scores as weighted averages
    for domain, signals in domain_signal.items():
        if signals:
            avg = sum(signals) / len(signals)
            # Blend with existing score (take higher)
            existing = flywheel[domain].get("score", 0)
            new_score = round(min(100, max(existing, avg * 100)), 1)
            # Build node list for this domain
            domain_nodes = [
                n["node_id"] for n in nodes.values()
                if domain in n.get("domains", [])
            ]
            # Build rationale from top sections
            top = sorted(
                [n for n in nodes.values() if domain in n.get("domains", [])],
                key=lambda x: x.get("nuclear_impact", 0), reverse=True
            )[:3]
            rationale = "; ".join(n["name"][:50] for n in top)
            flywheel[domain] = {
                "score": new_score,
                "rationale": rationale,
                "nodes": domain_nodes[:10],
                "section_count": len(signals),
                "last_updated": datetime.now().isoformat()[:19],
            }

    save_json(GR_NODES_FILE, nodes)
    save_json(FLYWHEEL_FILE, flywheel)
    save_json(EVIDENCE_FILE, evidence)

    print(f"\n{'='*60}")
    print(f"NEXUS INGEST COMPLETE — MasterBrief v54")
    print(f"  GR Nodes total:      {len(nodes)} (+{new_nodes} from MB54)")
    print(f"  Evidence anchors:    {len(evidence)} (+{new_evidence} new EV mappings)")
    print(f"\n  FLYWHEEL SCORES:")
    for domain, v in flywheel.items():
        bar = "█" * int(v["score"] / 5)
        print(f"  {domain:25s} {v['score']:5.1f}/100 {bar}")
    print(f"\n  Data → {DATA_DIR}")
    print(f"{'='*60}")

    # Print P1-MUST pending items as action queue
    pending_p1 = [
        n for n in nodes.values()
        if n.get("integration_priority") == "P1-MUST" and "PENDING" in n.get("status", "")
    ]
    if pending_p1:
        print(f"\nP1-MUST ACTION QUEUE ({len(pending_p1)} items):")
        for n in sorted(pending_p1, key=lambda x: x.get("nuclear_impact", 0), reverse=True):
            print(f"  [{n['nuclear_impact']:3.0f}] {n['section_id']:20s} {n['name'][:55]}")

    return nodes, flywheel, evidence


def print_report():
    nodes = load_json(GR_NODES_FILE, {})
    flywheel = load_json(FLYWHEEL_FILE, {})
    evidence = load_json(EVIDENCE_FILE, {})

    print(f"NEXUS STATE REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"GR Nodes: {len(nodes)}   Evidence: {len(evidence)}")
    print()
    print("FLYWHEEL:")
    for domain, v in flywheel.items():
        score = v.get("score", 0)
        bar = "█" * int(score / 5)
        print(f"  {domain:25s} {score:5.1f}/100 {bar}")

    print()
    print("TOP 10 GR NODES BY IMPACT:")
    top = sorted(nodes.values(), key=lambda x: x.get("nuclear_impact", 0), reverse=True)[:10]
    for n in top:
        tag = f"[{n.get('status','?')[:8]}]"
        print(f"  {n['nuclear_impact']:5.1f}  {n.get('section_id','?'):15s}  {n.get('name','')[:50]}  {tag}")

    p1 = [n for n in nodes.values() if n.get("integration_priority") == "P1-MUST"]
    if p1:
        print(f"\nP1-MUST PENDING: {len(p1)} items require integration")


def main():
    parser = argparse.ArgumentParser(description="NEXUS MasterBrief v54 Ingest")
    parser.add_argument("--csv", help="CSV file path", default=str(DATA_DIR / "masterbrief_v54.csv"))
    parser.add_argument("--report", action="store_true", help="Print current state only")
    args = parser.parse_args()

    if args.report:
        print_report()
        return

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        sys.exit(1)

    ingest_csv(csv_path)


if __name__ == "__main__":
    main()
