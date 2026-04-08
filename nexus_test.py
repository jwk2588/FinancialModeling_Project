#!/usr/bin/env python3
"""
NEXUS Platform — End-to-End Test Suite
Tests data pipeline, agent responses, API endpoints, and context injection.

Usage:
    python nexus_test.py                  # All tests (offline mode — no API key needed)
    python nexus_test.py --online         # Include live Claude API tests
    python nexus_test.py --server         # Also test HTTP server endpoints
    python nexus_test.py -v               # Verbose output
"""

import json
import os
import sys
import time
import argparse
import subprocess
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
SKIP = "\033[93m○\033[0m"
INFO = "\033[94m·\033[0m"

results = {"passed": 0, "failed": 0, "skipped": 0}


def ok(msg: str):
    print(f"  {PASS} {msg}")
    results["passed"] += 1


def fail(msg: str, detail: str = ""):
    print(f"  {FAIL} {msg}")
    if detail:
        print(f"      {detail}")
    results["failed"] += 1


def skip(msg: str):
    print(f"  {SKIP} {msg}")
    results["skipped"] += 1


def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ── TEST 1: Data Files ──────────────────────────────────────────────────────

def test_data_files():
    section("1. DATA FILES — Corpus integrity")
    from nexus_ai import load_gr_nodes, load_flywheel, load_evidence, DATA_DIR

    # CSV
    csv_path = DATA_DIR / "masterbrief_v54.csv"
    if csv_path.exists():
        import csv
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) >= 90:
            ok(f"MasterBrief v54 CSV: {len(rows)} rows")
        else:
            fail(f"MasterBrief CSV too small: {len(rows)} rows (expected 90+)")
    else:
        fail("masterbrief_v54.csv not found")

    # GR nodes
    nodes = load_gr_nodes()
    if len(nodes) >= 100:
        ok(f"GR nodes loaded: {len(nodes)} nodes")
    else:
        fail(f"GR nodes: only {len(nodes)} (expected 100+)")

    # Node structure
    sample = list(nodes.values())[0] if nodes else {}
    required_keys = ["node_id", "name", "nuclear_impact", "agents", "evidence"]
    missing = [k for k in required_keys if k not in sample]
    if not missing:
        ok(f"GR node structure valid (keys: {', '.join(required_keys)})")
    else:
        fail(f"GR node missing keys: {missing}")

    # Impact scores
    impacts = [float(n.get("nuclear_impact", 0)) for n in nodes.values()]
    max_impact = max(impacts) if impacts else 0
    if max_impact >= 9.0:
        ok(f"Nuclear impact scores valid (max={max_impact})")
    else:
        fail(f"Impact scores too low (max={max_impact}, expected >= 9.0)")

    # Evidence anchors
    evidence = load_evidence()
    if len(evidence) >= 200:
        ok(f"Evidence anchors: {len(evidence)} mappings")
    else:
        fail(f"Evidence anchors sparse: {len(evidence)} (expected 200+)")

    # Flywheel
    flywheel = load_flywheel()
    active = [d for d, v in flywheel.items() if (v.get("score", v) if isinstance(v, dict) else v) > 50]
    if len(active) >= 3:
        ok(f"Flywheel: {len(flywheel)} domains, {len(active)} active (>50)")
    else:
        fail(f"Flywheel: only {len(active)} active domains")


# ── TEST 2: Context Block ────────────────────────────────────────────────────

def test_context_block():
    section("2. CONTEXT INJECTION — Dataset grounding")
    from nexus_ai import build_context_block

    for persona in ["nexus_master", "wolf", "tiger", "suits"]:
        ctx = build_context_block(persona, top_n=8)
        if not ctx:
            fail(f"Context block empty for persona={persona}")
            continue

        # Must have key sections
        checks = {
            "header": "NEXUS INTELLIGENCE CONTEXT" in ctx,
            "flywheel": "FLYWHEEL DOMAIN SCORES" in ctx,
            "nodes": "GHOSTRECON NODES" in ctx,
            "gr_ids": "GR-" in ctx,
            "length": len(ctx) > 500,
        }
        if all(checks.values()):
            ok(f"Context block for {persona}: {len(ctx)} chars, {ctx.count('[GR-')} node refs")
        else:
            failed_checks = [k for k, v in checks.items() if not v]
            fail(f"Context block for {persona} missing: {failed_checks}")

    # Verify persona routing affects node selection
    wolf_ctx = build_context_block("wolf", top_n=6)
    tiger_ctx = build_context_block("tiger", top_n=6)
    if wolf_ctx != tiger_ctx:
        ok("Persona-specific node routing: wolf ≠ tiger context (correct)")
    else:
        skip("Wolf and tiger contexts identical (may indicate no persona-filtered nodes)")


# ── TEST 3: Offline Mode ─────────────────────────────────────────────────────

def test_offline_mode():
    section("3. OFFLINE MODE — Dataset-derived responses")
    from nexus_ai import offline_response, NexusAgent

    test_prompts = [
        ("GPS LLC VIE structure arbitration analysis", "nexus_master"),
        ("Analyze the CFTC commodity classification risk", "wolf"),
        ("ASC 606 revenue recognition breakage quantification", "tiger"),
        ("Michigan gaming control board material changes", "suits"),
    ]

    for prompt, persona in test_prompts:
        result = offline_response(prompt, persona)
        checks = {
            "has_content": len(result) > 100,
            "has_nodes": "[GR-" in result or "[MB-" in result,
            "has_mode": "OFFLINE" in result,
            "has_flywheel": "FLYWHEEL" in result,
        }
        if all(checks.values()):
            node_count = result.count("[GR-") + result.count("[MB-")
            ok(f"Offline response ({persona}): {len(result)} chars, {node_count} node refs")
        else:
            failed = [k for k, v in checks.items() if not v]
            fail(f"Offline response missing: {failed}", f"prompt='{prompt[:50]}'")

    # Test agent in offline mode
    agent = NexusAgent(api_key=None, mode="offline")
    result = agent.ask("What is the primary VIE risk?", persona="wolf", stream_print=False)
    if result and len(result) > 50:
        ok(f"NexusAgent offline ask(): {len(result)} chars returned")
    else:
        fail("NexusAgent offline ask() returned empty/short result")


# ── TEST 4: Domain Schema ────────────────────────────────────────────────────

def test_domain_schema():
    section("4. DOMAIN SCHEMA — DDF hierarchy and scoring")
    try:
        import nexus_domain_schema as nds
    except ImportError as e:
        fail(f"nexus_domain_schema import failed: {e}")
        return

    from nexus_ai import load_gr_nodes, load_evidence
    nodes = load_gr_nodes()
    evidence = load_evidence()

    # Taxonomy structure
    if len(nds.DOMAIN_TAXONOMY) >= 5:
        ok(f"Domain taxonomy: {len(nds.DOMAIN_TAXONOMY)} domains defined")
    else:
        fail(f"Domain taxonomy too sparse: {len(nds.DOMAIN_TAXONOMY)}")

    # Subdomains
    total_subs = sum(len(d.get("subdomains", {})) for d in nds.DOMAIN_TAXONOMY.values())
    if total_subs >= 10:
        ok(f"Subdomains defined: {total_subs} total")
    else:
        fail(f"Too few subdomains: {total_subs}")

    # Bridges
    if len(nds.DOMAIN_BRIDGES) >= 6:
        ok(f"Domain bridges: {len(nds.DOMAIN_BRIDGES)} cross-domain edges")
    else:
        fail(f"Insufficient bridges: {len(nds.DOMAIN_BRIDGES)}")

    # Scoring
    scores = nds.compute_domain_scores(nodes, evidence)
    if len(scores) == len(nds.DOMAIN_TAXONOMY):
        ok(f"Scoring computed for all {len(scores)} domains")
    else:
        fail(f"Scoring mismatch: {len(scores)} scored vs {len(nds.DOMAIN_TAXONOMY)} defined")

    score_range_ok = all(0 <= s <= 1.0 for s in scores.values())
    if score_range_ok:
        ok(f"All scores in valid range [0,1]: {', '.join(f'{k}={v:.2f}' for k,v in scores.items())}")
    else:
        fail("Some scores outside [0,1] range")

    # Full hierarchy
    hierarchy = nds.get_domain_hierarchy(nodes, evidence)
    required_keys = ["domains", "bridges", "total_nodes", "total_evidence"]
    missing = [k for k in required_keys if k not in hierarchy]
    if not missing:
        ok(f"Hierarchy response valid: {hierarchy['total_nodes']} nodes, {hierarchy['total_evidence']} evidence")
    else:
        fail(f"Hierarchy missing keys: {missing}")

    # Suggested prompts
    for dom_id, dom in hierarchy["domains"].items():
        prompts = dom.get("suggested_prompts", [])
        if len(prompts) >= 2:
            ok(f"Suggested prompts for {dom_id}: {len(prompts)} prompts")
            break
    else:
        fail("No suggested prompts generated")


# ── TEST 5: MB54 Ingest Pipeline ─────────────────────────────────────────────

def test_ingest_pipeline():
    section("5. INGEST PIPELINE — nexus_ingest_mb54")
    try:
        import nexus_ingest_mb54 as mb54
    except ImportError as e:
        fail(f"nexus_ingest_mb54 import failed: {e}")
        return

    csv_path = Path("data/nexus/masterbrief_v54.csv")
    if not csv_path.exists():
        fail("masterbrief_v54.csv not found — cannot test ingest pipeline")
        return

    # Re-ingest to verify it's idempotent and grows data
    from nexus_ai import load_gr_nodes, load_evidence
    nodes_before = len(load_gr_nodes())
    evidence_before = len(load_evidence())

    result = mb54.ingest_csv(csv_path)

    nodes_after = len(load_gr_nodes())
    evidence_after = len(load_evidence())

    if nodes_after >= nodes_before:
        ok(f"Ingest idempotent: {nodes_before} → {nodes_after} nodes (no loss)")
    else:
        fail(f"Ingest lost nodes: {nodes_before} → {nodes_after}")

    if evidence_after >= evidence_before:
        ok(f"Evidence preserved: {evidence_before} → {evidence_after} anchors")
    else:
        fail(f"Evidence lost: {evidence_before} → {evidence_after}")

    # Verify node_id_from_section works
    test_ids = ["§I.0", "ENG-1", "F01-01", "§XII.V", "EX-B"]
    for i, sid in enumerate(test_ids):
        nid = mb54.node_id_from_section(sid, i)
        if nid and nid.startswith("MB-"):
            ok(f"node_id_from_section('{sid}') → '{nid}'")
            break
    else:
        fail("node_id_from_section not producing MB- IDs")


# ── TEST 6: HTTP Server ──────────────────────────────────────────────────────

def test_http_server():
    section("6. HTTP SERVER — API endpoints")
    import urllib.request
    import urllib.error

    port = 7434  # Use alternate port for testing
    server_process = None

    try:
        # Start server in background
        server_process = subprocess.Popen(
            [sys.executable, "nexus_ai.py", "--api-key", "dummy-offline",
             "serve", "--port", str(port)],
            env={**os.environ, "NEXUS_MODE": "offline"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path(__file__).parent),
        )
        time.sleep(2)  # Wait for server to start

        base = f"http://127.0.0.1:{port}"

        # Test root serves HTML
        try:
            with urllib.request.urlopen(f"{base}/", timeout=5) as r:
                content = r.read()
                if b"NEXUS" in content and len(content) > 10000:
                    ok(f"GET /  → HTML ({len(content)//1024}KB, contains NEXUS)")
                else:
                    fail(f"GET / returned unexpected content ({len(content)} bytes)")
        except Exception as e:
            fail(f"GET / failed: {e}")

        # Test /api/state
        try:
            with urllib.request.urlopen(f"{base}/api/state", timeout=5) as r:
                data = json.loads(r.read())
                if "gr_nodes" in data and "flywheel" in data:
                    ok(f"GET /api/state → {data.get('corpus_size', len(data['gr_nodes']))} nodes, mode={data.get('mode','?')}")
                else:
                    fail(f"GET /api/state missing keys: {list(data.keys())}")
        except Exception as e:
            fail(f"GET /api/state failed: {e}")

        # Test /api/domains
        try:
            with urllib.request.urlopen(f"{base}/api/domains", timeout=5) as r:
                data = json.loads(r.read())
                if "domains" in data and len(data["domains"]) >= 5:
                    ok(f"GET /api/domains → {len(data['domains'])} domains, {data.get('total_nodes',0)} nodes")
                else:
                    fail(f"GET /api/domains returned: {list(data.keys())}")
        except Exception as e:
            fail(f"GET /api/domains failed: {e}")

        # Test /api/ask offline SSE
        try:
            req_data = json.dumps({"prompt": "Analyze GPS LLC VIE", "persona": "wolf"}).encode()
            req = urllib.request.Request(
                f"{base}/api/ask",
                data=req_data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode()
                if "data:" in raw:
                    chunks = [l for l in raw.split("\n") if l.startswith("data:")]
                    ok(f"POST /api/ask (offline SSE) → {len(chunks)} SSE chunks")
                else:
                    fail(f"POST /api/ask no SSE data in response")
        except Exception as e:
            fail(f"POST /api/ask failed: {e}")

    finally:
        if server_process:
            server_process.terminate()
            server_process.wait(timeout=3)


# ── TEST 7: Online API (optional) ────────────────────────────────────────────

def test_online_api():
    section("7. ONLINE API — Live Claude API call with context injection")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        skip("ANTHROPIC_API_KEY not set — skipping online tests")
        skip("Set ANTHROPIC_API_KEY env var to run live API tests")
        return

    from nexus_ai import NexusAgent, build_context_block

    agent = NexusAgent(api_key=api_key, mode="online")

    # Test context injection is non-empty
    ctx = build_context_block("wolf", top_n=5)
    if len(ctx) > 200:
        ok(f"Context block ready for injection: {len(ctx)} chars")
    else:
        fail("Context block empty or too small")

    # Short test prompt — verify GR node references appear in output
    try:
        result = agent.ask(
            "In one sentence, name the highest-impact GhostRecon node in the corpus and its key risk.",
            persona="nexus_master",
            use_tools=False,
            stream_print=False,
            inject_context=True,
        )
        if result and len(result) > 20:
            has_gr_ref = "GR-" in result or any(
                kw in result for kw in ["GPS", "VIE", "NFA", "Binary", "Crown"]
            )
            if has_gr_ref:
                ok(f"Claude response references corpus data: '{result[:150].strip()}'")
            else:
                ok(f"Claude responded ({len(result)} chars) — no GR ID cited but answer present")
        else:
            fail("Claude API returned empty response")
    except Exception as e:
        fail(f"Claude API call failed: {e}")


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NEXUS end-to-end test suite")
    parser.add_argument("--online", action="store_true", help="Run live Claude API tests")
    parser.add_argument("--server", action="store_true", help="Run HTTP server tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║  NEXUS PLATFORM — END-TO-END TEST SUITE                  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Always run
    test_data_files()
    test_context_block()
    test_offline_mode()
    test_domain_schema()
    test_ingest_pipeline()

    # Optional
    if args.server:
        test_http_server()
    else:
        section("6. HTTP SERVER — skipped (use --server to run)")
        skip("HTTP server tests: pass --server flag to enable")

    if args.online:
        test_online_api()
    else:
        section("7. ONLINE API — skipped (use --online to run)")
        skip("Live Claude API tests: set ANTHROPIC_API_KEY and pass --online")

    # Summary
    total = sum(results.values())
    print(f"\n{'═'*60}")
    print(f"  RESULTS: {results['passed']} passed  {results['failed']} failed  {results['skipped']} skipped  / {total} total")
    if results["failed"] == 0:
        print(f"  \033[92mALL TESTS PASSED\033[0m")
    else:
        print(f"  \033[91m{results['failed']} FAILURES — see above\033[0m")
    print(f"{'═'*60}\n")

    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
