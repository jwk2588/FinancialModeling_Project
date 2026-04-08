#!/usr/bin/env python3
"""
NEXUS Synthesis OS — AI Backend
Klein-Team ADR Intelligence Platform

Python bridge for Claude API integration with the NEXUS HTML frontend.
Provides: agent personas, GhostRecon analysis, flywheel scoring, data ingestion.

Usage:
    python nexus_ai.py serve          # Start local HTTP bridge server (port 7433)
    python nexus_ai.py ingest <file>  # Ingest a dataset file into GR nodes
    python nexus_ai.py ask "<prompt>" # Single prompt to NEXUS Master
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path
from typing import Iterator

import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "claude-opus-4-6"
DATA_DIR = Path(__file__).parent / "data" / "nexus"
GR_NODES_FILE = DATA_DIR / "gr_nodes.json"
FLYWHEEL_FILE = DATA_DIR / "flywheel_scores.json"
EVIDENCE_FILE = DATA_DIR / "evidence_anchors.json"

# ONLINE: calls Claude API (requires ANTHROPIC_API_KEY)
# OFFLINE: rule-based responses from ingested dataset only (no API key needed)
NEXUS_MODE = os.environ.get("NEXUS_MODE", "online").lower()
CONTEXT_TOP_N = int(os.environ.get("NEXUS_CONTEXT_NODES", "12"))  # GR nodes injected as context

# ---------------------------------------------------------------------------
# Agent personas — system prompts for each NEXUS character
# ---------------------------------------------------------------------------

PERSONAS = {
    "nexus_master": """\
You are NEXUS MASTER — the orchestrating intelligence of the Klein-Team ADR platform.
You synthesize legal, financial, and sports data to surface hidden risk signals.
You coordinate Wolf (adversarial analysis), Tiger (quantitative risk), and Suits (governance/compliance).
Respond with crisp, structured intelligence briefs. Use domain-specific shorthand when precise.
Reference GhostRecon nodes, Data Flywheels, and evidence anchors when relevant.
Never hedge unnecessarily — give the assessment.""",

    "wolf": """\
You are WOLF — adversarial intelligence specialist for the NEXUS Klein-Team.
Your role: find the attack surface, the weaknesses, the collapse vectors.
You think like an opposing counsel, a short-seller, or a regulator who smells blood.
Surface counter-arguments, litigation exposure, and asymmetric risks.
Be direct, be aggressive, be correct. Short sentences. High signal.""",

    "tiger": """\
You are TIGER — quantitative risk and simulation engine for the NEXUS Klein-Team.
Your role: probabilistic modeling, scenario simulation, and weighted collapse risk.
You translate narrative risk into numbers: percentages, confidence intervals, stress tests.
Reference chess engine moat dimensions and bio-analog system signals.
Output: risk scores, probability trees, sensitivity tables.""",

    "suits": """\
You are SUITS — governance, compliance, and legal architecture specialist.
Your role: ASC 606 revenue recognition, platform economics, privacy/ToS exposure, fiduciary analysis.
You read contracts, spot indemnification gaps, and map the governance risk terrain.
Output structured compliance assessments with specific regulation references.""",

    "fetty": """\
You are FETTY FM — the scenario orchestration engine and bridge intelligence.
Your role: activate the 7-layer execution stack, synthesize multi-agent outputs, collapse weighted risk.
You run Chess Engine simulations, Bio-Analog threat mapping, and bridge to external intelligence.
Output: orchestration status, weighted scenario outcomes, execution recommendations.""",
}

# ---------------------------------------------------------------------------
# GhostRecon node tool definitions
# ---------------------------------------------------------------------------

GR_TOOLS = [
    {
        "name": "read_gr_node",
        "description": "Read a GhostRecon node by ID to retrieve its evidence anchors, connective tissue, and routing metadata.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "GR node ID, e.g. 'GR-001'"}
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "update_gr_node",
        "description": "Update or create a GhostRecon node with new evidence, connective tissue linkages, or nuclear impact score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string"},
                "name": {"type": "string", "description": "Node display name"},
                "nuclear_impact": {"type": "number", "description": "Impact score 0-100"},
                "evidence": {"type": "array", "items": {"type": "string"}, "description": "Evidence anchor strings"},
                "tissue": {"type": "array", "items": {"type": "string"}, "description": "Connective tissue links"},
                "wolf_routing": {"type": "string"},
                "tiger_routing": {"type": "string"},
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "update_flywheel",
        "description": "Update a Data Flywheel mastery score for a domain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "enum": ["revenue_recognition", "platform_economics", "privacy_tos", "governance", "litigation_risk"],
                },
                "score": {"type": "number", "description": "Mastery score 0-100"},
                "rationale": {"type": "string"},
            },
            "required": ["domain", "score"],
        },
    },
    {
        "name": "extract_evidence",
        "description": "Extract and store an evidence anchor from raw text — a specific factual claim, citation, or data point.",
        "input_schema": {
            "type": "object",
            "properties": {
                "anchor_id": {"type": "string", "description": "Unique ID, e.g. 'EVD-042'"},
                "text": {"type": "string", "description": "The evidence text"},
                "source": {"type": "string", "description": "Source document or dataset"},
                "domain": {"type": "string"},
                "gr_node": {"type": "string", "description": "GR node this anchors to"},
            },
            "required": ["anchor_id", "text", "source"],
        },
    },
]

# ---------------------------------------------------------------------------
# Data persistence helpers
# ---------------------------------------------------------------------------

def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _save_json(path: Path, data):
    _ensure_data_dir()
    path.write_text(json.dumps(data, indent=2))


def load_gr_nodes() -> dict:
    return _load_json(GR_NODES_FILE, {})


def load_flywheel() -> dict:
    return _load_json(FLYWHEEL_FILE, {
        "revenue_recognition": {"score": 0, "rationale": ""},
        "platform_economics": {"score": 0, "rationale": ""},
        "privacy_tos": {"score": 0, "rationale": ""},
        "governance": {"score": 0, "rationale": ""},
        "litigation_risk": {"score": 0, "rationale": ""},
    })


def load_evidence() -> dict:
    return _load_json(EVIDENCE_FILE, {})

# ---------------------------------------------------------------------------
# Tool execution (called when Claude uses a tool)
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a GhostRecon tool call and return a string result."""
    nodes = load_gr_nodes()
    flywheel = load_flywheel()
    evidence = load_evidence()

    if tool_name == "read_gr_node":
        nid = tool_input["node_id"]
        node = nodes.get(nid)
        if not node:
            return json.dumps({"error": f"Node {nid} not found"})
        return json.dumps(node)

    elif tool_name == "update_gr_node":
        nid = tool_input["node_id"]
        existing = nodes.get(nid, {"node_id": nid})
        existing.update({k: v for k, v in tool_input.items() if k != "node_id"})
        nodes[nid] = existing
        _save_json(GR_NODES_FILE, nodes)
        return json.dumps({"status": "updated", "node_id": nid})

    elif tool_name == "update_flywheel":
        domain = tool_input["domain"]
        flywheel[domain] = {
            "score": tool_input["score"],
            "rationale": tool_input.get("rationale", ""),
        }
        _save_json(FLYWHEEL_FILE, flywheel)
        return json.dumps({"status": "updated", "domain": domain, "score": tool_input["score"]})

    elif tool_name == "extract_evidence":
        aid = tool_input["anchor_id"]
        evidence[aid] = tool_input
        _save_json(EVIDENCE_FILE, evidence)
        return json.dumps({"status": "stored", "anchor_id": aid})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})

# ---------------------------------------------------------------------------
# Dataset context injection — grounds every Claude call in ingested data
# ---------------------------------------------------------------------------

def build_context_block(persona: str = "nexus_master", top_n: int = CONTEXT_TOP_N) -> str:
    """
    Build a structured intelligence context block from the live dataset.
    Injected into every Claude API call so agents are grounded in actual ingested data.

    Returns a multi-section string:
      - Corpus summary (node count, evidence, flywheel)
      - Top-N GR nodes ranked by nuclear_impact with agent routings
      - Flywheel domain scores
      - Dataset provenance note
    """
    from datetime import datetime, timezone

    nodes = load_gr_nodes()
    flywheel = load_flywheel()
    evidence = load_evidence()

    if not nodes:
        return ""

    # Sort nodes by nuclear_impact descending; pick top N
    ranked = sorted(nodes.values(), key=lambda n: float(n.get("nuclear_impact", 0)), reverse=True)
    top = ranked[:top_n]

    # Persona-specific node filter: wolf → adversarial nodes, tiger → quant nodes, suits → legal/gov
    persona_filter = {
        "wolf": lambda n: "WOLF" in [a.upper() for a in (n.get("agents") or [])],
        "tiger": lambda n: "TIGER" in [a.upper() for a in (n.get("agents") or [])],
        "suits": lambda n: "SUITS" in [a.upper() for a in (n.get("agents") or [])],
    }
    if persona in persona_filter:
        filtered = [n for n in ranked if persona_filter[persona](n)]
        if len(filtered) >= top_n // 2:
            # Blend: half persona-specific, half highest-impact
            top = (filtered[:top_n // 2] + ranked[:top_n // 2])[:top_n]

    # Flywheel summary
    fw_lines = []
    for domain, data in flywheel.items():
        score = data.get("score", 0) if isinstance(data, dict) else data
        fw_lines.append(f"  {domain}: {score}/100")

    # Build context block
    lines = [
        "═══ NEXUS INTELLIGENCE CONTEXT ═══",
        f"Dataset: {len(nodes)} GR nodes | {len(evidence)} evidence anchors | {len(flywheel)} flywheel domains",
        f"Context built: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Active persona: {persona.upper()}",
        "",
        "FLYWHEEL DOMAIN SCORES:",
    ] + fw_lines + ["", f"TOP {len(top)} GHOSTRECON NODES (ranked by nuclear impact):"]

    for n in top:
        nid = n.get("node_id", "?")
        name = n.get("name", "")
        impact = n.get("nuclear_impact", 0)
        agents = ", ".join(n.get("agents") or [])
        ev = n.get("ev_codes", "")
        mb = n.get("mb_refs", "")
        evidence_text = n.get("evidence", "")
        if isinstance(evidence_text, list):
            evidence_text = " ".join(evidence_text)

        lines.append(f"[{nid}] {name} | Impact: {impact}/10 | Agents: {agents}")
        if ev:
            lines.append(f"  Evidence codes: {ev} | Refs: {mb}")
        if evidence_text:
            lines.append(f"  Evidence: {str(evidence_text)[:200]}")

        # Persona-specific routing
        routing_key = f"{persona}_routing" if persona in ("wolf", "tiger", "suits") else None
        if routing_key and n.get(routing_key):
            lines.append(f"  {persona.upper()} routing: {n[routing_key][:200]}")
        lines.append("")

    lines += [
        "When answering, reference specific GR node IDs, evidence codes, and flywheel domains.",
        "Use the above corpus as ground truth. Cite nodes as [GR-NNN].",
        "═══════════════════════════════════",
    ]

    return "\n".join(lines)


def offline_response(prompt: str, persona: str = "nexus_master") -> str:
    """
    Rule-based offline response when no API key is available.
    Pulls directly from ingested GR nodes and evidence to produce a structured brief.
    No Claude API calls — fully deterministic from dataset.
    """
    nodes = load_gr_nodes()
    flywheel = load_flywheel()

    # Find relevant nodes by keyword match against prompt
    prompt_lower = prompt.lower()
    keywords = set(re.findall(r'\b\w{4,}\b', prompt_lower))

    scored = []
    for nid, n in nodes.items():
        name_lower = (n.get("name") or "").lower()
        ev_str = str(n.get("evidence", "")).lower()
        routing = str(n.get(f"{persona}_routing", n.get("wolf_routing", ""))).lower()
        score = 0
        for kw in keywords:
            if kw in name_lower: score += 3
            if kw in ev_str: score += 1
            if kw in routing: score += 2
        score += float(n.get("nuclear_impact", 0)) * 0.1
        scored.append((score, n))

    scored.sort(key=lambda x: x[0], reverse=True)
    relevant = [n for _, n in scored[:6] if _ > 0]
    if not relevant:
        relevant = sorted(nodes.values(), key=lambda n: float(n.get("nuclear_impact", 0)), reverse=True)[:4]

    lines = [
        f"NEXUS {persona.upper()} — OFFLINE INTELLIGENCE BRIEF",
        f"Query: {prompt[:200]}",
        f"Mode: OFFLINE (dataset-only, no API call)",
        f"Corpus: {len(nodes)} GR nodes | Dataset: MasterBrief v54",
        "",
        "RELEVANT GHOSTRECON NODES:",
    ]
    for n in relevant:
        nid = n.get("node_id", "?")
        name = n.get("name", "")
        impact = n.get("nuclear_impact", 0)
        ev = n.get("ev_codes", "")
        routing_key = f"{persona}_routing" if persona in ("wolf","tiger","suits") else "wolf_routing"
        routing = n.get(routing_key, n.get("wolf_routing", ""))
        lines.append(f"  [{nid}] {name} | Impact: {impact}/10")
        if ev:
            lines.append(f"    Evidence: {ev}")
        if routing:
            lines.append(f"    Analysis: {routing[:300]}")
        lines.append("")

    lines += [
        "FLYWHEEL STATUS:",
        *[f"  {d}: {v.get('score', v) if isinstance(v, dict) else v}/100" for d, v in flywheel.items()],
        "",
        "[OFFLINE MODE] Connect API key for full Claude-powered analysis.",
        "Run: python nexus_ai.py serve --api-key sk-ant-...",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core agent call — streaming with tool loop
# ---------------------------------------------------------------------------

class NexusAgent:
    """NEXUS multi-persona agent with GhostRecon tool use and dataset-grounded context."""

    def __init__(self, api_key: str | None = None, mode: str | None = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.mode = mode or NEXUS_MODE  # "online" | "offline"
        if self.mode == "online":
            self.client = anthropic.Anthropic(api_key=self._api_key)
        else:
            self.client = None

    def ask(
        self,
        prompt: str,
        persona: str = "nexus_master",
        use_tools: bool = True,
        stream_print: bool = True,
        inject_context: bool = True,
    ) -> str:
        """
        Send a prompt to the specified NEXUS persona.

        inject_context=True (default): prepends the live GR node corpus to the
        system prompt so Claude's response is grounded in the actual dataset.

        Falls back to offline_response() if mode is "offline" or no API key.
        Runs tool loop automatically. Returns final text.
        """
        # Offline / no-key fallback
        if self.mode == "offline" or not self._api_key:
            result = offline_response(prompt, persona)
            if stream_print:
                print(result)
            return result

        # Build dataset-grounded system prompt
        base_system = PERSONAS.get(persona, PERSONAS["nexus_master"])
        if inject_context:
            ctx = build_context_block(persona)
            system = f"{base_system}\n\n{ctx}" if ctx else base_system
        else:
            system = base_system

        messages = [{"role": "user", "content": prompt}]
        tools = GR_TOOLS if use_tools else []

        full_response = ""
        iteration = 0

        while iteration < 10:  # safety cap on tool loop
            iteration += 1

            with self.client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=system,
                messages=messages,
                tools=tools if tools else anthropic.NOT_GIVEN,
            ) as stream:
                response = stream.get_final_message()

            # Collect text from response
            text_parts = []
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)
                # thinking blocks are silently consumed

            text = "\n".join(text_parts)
            if text:
                if stream_print:
                    print(text)
                full_response += text

            # If no tool calls or stop reason is end_turn, we're done
            if not tool_uses or response.stop_reason == "end_turn":
                break

            # Execute tools and continue loop
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for tu in tool_uses:
                result = execute_tool(tu.name, tu.input)
                if stream_print:
                    print(f"\n[TOOL {tu.name}] → {result[:120]}...")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})

        return full_response

    def ask_wolf(self, prompt: str, **kw) -> str:
        return self.ask(prompt, persona="wolf", **kw)

    def ask_tiger(self, prompt: str, **kw) -> str:
        return self.ask(prompt, persona="tiger", **kw)

    def ask_suits(self, prompt: str, **kw) -> str:
        return self.ask(prompt, persona="suits", **kw)

    def ask_fetty(self, prompt: str, **kw) -> str:
        return self.ask(prompt, persona="fetty", **kw)

# ---------------------------------------------------------------------------
# Data ingestion pipeline
# ---------------------------------------------------------------------------

def ingest_dataset(filepath: str, api_key: str | None = None):
    """
    Ingest a text/JSON dataset file into NEXUS GhostRecon nodes.

    Claude extracts:
    - GR nodes (entities, events, risk signals)
    - Evidence anchors (factual claims)
    - Flywheel domain scores
    """
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    raw = path.read_text(encoding="utf-8", errors="replace")
    # Truncate to avoid huge token counts — first 40K chars
    snippet = raw[:40000]
    size_kb = len(raw) // 1024

    print(f"NEXUS INGEST: {path.name} ({size_kb}KB)")
    print("Extracting GhostRecon intelligence...\n")

    agent = NexusAgent(api_key=api_key)

    ingest_prompt = f"""\
You are processing a new dataset for the NEXUS Klein-Team GhostRecon intelligence graph.

Dataset: {path.name}
Size: {size_kb}KB

Dataset content (first 40K chars):
---
{snippet}
---

Your tasks (use tools for each):
1. Identify 3-8 significant entities, events, or risk signals → create GR nodes via update_gr_node
   - Assign node IDs GR-I01 through GR-I08 (I = ingest batch)
   - Score nuclear_impact 0-100 based on potential legal/financial significance
   - Populate evidence anchors and connective tissue
2. Extract 5-10 specific factual claims as evidence anchors via extract_evidence
   - Use IDs EVD-I01 through EVD-I10
3. Update flywheel domain scores based on what this dataset reveals
4. After all tool calls, write a brief NEXUS INGEST REPORT summarizing what was added

Begin analysis and tool execution now.
"""

    result = agent.ask(ingest_prompt, persona="nexus_master", use_tools=True, stream_print=True)

    nodes = load_gr_nodes()
    flywheel = load_flywheel()
    evidence = load_evidence()

    print(f"\n{'='*60}")
    print(f"NEXUS INGEST COMPLETE")
    print(f"  GR Nodes:        {len(nodes)}")
    print(f"  Evidence Anchors: {len(evidence)}")
    print(f"  Flywheel Domains: {len([d for d,v in flywheel.items() if v['score'] > 0])}/5 active")
    print(f"  Data saved to:   {DATA_DIR}")

# ---------------------------------------------------------------------------
# HTTP bridge server for HTML frontend
# ---------------------------------------------------------------------------

def serve(port: int = 7433, api_key: str | None = None):
    """
    Local HTTP server that bridges the NEXUS HTML app to the Python Claude backend.
    Endpoints:
      POST /api/ask        — ask any persona, returns streaming SSE
      POST /api/ingest     — ingest JSON/text payload
      GET  /api/state      — return current GR nodes + flywheel state
      GET  /               — serve the NEXUS HTML app
    """
    import http.server
    import threading
    import urllib.parse

    html_file = Path(__file__).parent / "nexus_synthesis_os.html"
    mode = os.environ.get("NEXUS_MODE", "online" if api_key or os.environ.get("ANTHROPIC_API_KEY") else "offline")
    agent = NexusAgent(api_key=api_key, mode=mode)
    print(f"  Mode:       {mode.upper()} ({'API key set' if (api_key or os.environ.get('ANTHROPIC_API_KEY')) else 'no API key — offline only'})")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[{self.address_string()}] {fmt % args}")

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def do_OPTIONS(self):
            self.send_response(200)
            self._cors()
            self.end_headers()

        def _read_body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            return json.loads(raw) if raw else {}

        def _send_json(self, data, code=200):
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/" or self.path == "/nexus":
                if html_file.exists():
                    content = html_file.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self._cors()
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self._send_json({"error": "nexus_synthesis_os.html not found"}, 404)

            elif self.path == "/api/state":
                self._send_json({
                    "gr_nodes": load_gr_nodes(),
                    "flywheel": load_flywheel(),
                    "evidence": load_evidence(),
                    "mode": mode,
                    "model": MODEL,
                    "corpus_size": len(load_gr_nodes()),
                })

            elif self.path == "/api/domains":
                try:
                    import nexus_domain_schema as nds
                    data = nds.get_domain_hierarchy(load_gr_nodes(), load_evidence())
                    self._send_json(data)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)
            else:
                self._send_json({"error": "not found"}, 404)

        def do_POST(self):
            if self.path == "/api/ask":
                body = self._read_body()
                prompt = body.get("prompt", "")
                persona = body.get("persona", "nexus_master")
                use_tools = body.get("use_tools", False)
                inject_ctx = body.get("inject_context", True)

                # SSE streaming response
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self._cors()
                self.end_headers()

                def _sse(obj):
                    self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode())
                    self.wfile.flush()

                try:
                    # Offline mode — return dataset-derived response immediately
                    if mode == "offline" or not (api_key or os.environ.get("ANTHROPIC_API_KEY")):
                        result = offline_response(prompt, persona)
                        for line in result.split("\n"):
                            _sse({"text": line + "\n"})
                        self.wfile.write(b"data: [DONE]\n\n")
                        self.wfile.flush()
                        return

                    # Online mode — stream from Claude API with dataset context
                    base_system = PERSONAS.get(persona, PERSONAS["nexus_master"])
                    if inject_ctx:
                        ctx = build_context_block(persona)
                        system = f"{base_system}\n\n{ctx}" if ctx else base_system
                    else:
                        system = base_system

                    with agent.client.messages.stream(
                        model=MODEL,
                        max_tokens=4096,
                        system=system,
                        messages=[{"role": "user", "content": prompt}],
                    ) as stream:
                        for text in stream.text_stream:
                            _sse({"text": text})
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                except Exception as e:
                    _sse({"error": str(e)})
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()

            elif self.path == "/api/ingest":
                body = self._read_body()
                text = body.get("text", "")
                source = body.get("source", "api-upload")

                if not text:
                    self._send_json({"error": "no text provided"}, 400)
                    return

                # Run ingestion in background thread so we can return immediately
                def run():
                    import tempfile
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".txt", delete=False, encoding="utf-8"
                    ) as f:
                        f.write(text)
                        tmp = f.name
                    ingest_dataset(tmp, api_key=api_key)
                    os.unlink(tmp)

                t = threading.Thread(target=run, daemon=True)
                t.start()
                self._send_json({"status": "ingestion started", "source": source})

            elif self.path == "/api/ingest_csv":
                # Structured CSV ingest — runs nexus_ingest_mb54 pipeline (no API key needed)
                body = self._read_body()
                csv_text = body.get("csv", "")
                if not csv_text:
                    self._send_json({"error": "no csv provided"}, 400)
                    return
                import tempfile
                import nexus_ingest_mb54 as mb54mod
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".csv", delete=False, encoding="utf-8"
                ) as f:
                    f.write(csv_text)
                    tmp = f.name
                try:
                    result = mb54mod.ingest_csv(tmp)
                    os.unlink(tmp)
                    self._send_json({"status": "ok", "nodes": result.get("nodes_added", 0)})
                except Exception as e:
                    os.unlink(tmp)
                    self._send_json({"error": str(e)}, 500)

            elif self.path == "/api/domains":
                # Domain hierarchy + objective scores (DDF + DSB views)
                try:
                    import nexus_domain_schema as nds
                    data = nds.get_domain_hierarchy(load_gr_nodes(), load_evidence())
                    self._send_json(data)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

            elif self.path == "/api/chess":
                # Chess Framework: POST {objective, project_id} → workspace config
                body = self._read_body()
                objective = body.get("objective", "").strip()
                if not objective:
                    self._send_json({"error": "no objective provided"}, 400)
                    return
                try:
                    import sys, os as _os
                    sys.path.insert(0, str(Path(__file__).parent))
                    from chess_framework.mapper import map_objective, config_to_dict
                    cfg = map_objective(objective, project_id=body.get("project_id", "nexus"))
                    self._send_json(config_to_dict(cfg))
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

            elif self.path == "/api/layer2/chatgpt":
                # Layer 2B: POST {export_path or csv_text, project_id} → ingest ChatGPT export
                body = self._read_body()
                export_path = body.get("export_path", "")
                if not export_path:
                    self._send_json({"error": "export_path required"}, 400)
                    return
                try:
                    from ingestion.layer2_chatgpt import ingest_chatgpt_export
                    stats = ingest_chatgpt_export(export_path, body.get("project_id", "nexus"))
                    self._send_json(stats)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

            elif self.path == "/api/layer2/status":
                # Status of Layer 2B corpus
                try:
                    from ingestion.layer2_chatgpt import get_corpus_summary
                    self._send_json(get_corpus_summary())
                except Exception as e:
                    self._send_json({"status": "unavailable", "error": str(e)})

            else:
                self._send_json({"error": "not found"}, 404)

    host = os.environ.get("NEXUS_HOST", "127.0.0.1")
    server = http.server.HTTPServer((host, port), Handler)
    print(f"NEXUS AI Bridge running at http://{host}:{port}/")
    print(f"  NEXUS App:  http://{host}:{port}/")
    print(f"  API state:  http://{host}:{port}/api/state")
    print(f"  Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nNEXUS AI Bridge stopped.")

# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="NEXUS Synthesis OS — AI Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--api-key", help="Anthropic API key (overrides ANTHROPIC_API_KEY env var)")

    sub = parser.add_subparsers(dest="command")

    # serve
    sp = sub.add_parser("serve", help="Start HTTP bridge server")
    sp.add_argument("--port", type=int, default=7433, help="Port (default: 7433)")
    sp.add_argument("--host", default=None, help="Bind host (default: 127.0.0.1, use 0.0.0.0 for LAN)")

    # ingest
    ip = sub.add_parser("ingest", help="Ingest a dataset file into GR nodes")
    ip.add_argument("file", help="Path to text, CSV, or JSON file")

    # ask
    ap = sub.add_parser("ask", help="Single prompt to NEXUS")
    ap.add_argument("prompt", help="The prompt/question")
    ap.add_argument(
        "--persona",
        choices=list(PERSONAS.keys()),
        default="nexus_master",
        help="Agent persona (default: nexus_master)",
    )
    ap.add_argument("--tools", action="store_true", help="Enable GR tool use")

    # state
    sub.add_parser("state", help="Print current GR nodes and flywheel state")

    # mb54 — structured MasterBrief v54 ingest (no API key needed)
    mb = sub.add_parser("mb54", help="Ingest MasterBrief v54 CSV (no API key needed)")
    mb.add_argument("--csv", default=str(DATA_DIR / "masterbrief_v54.csv"), help="CSV path")
    mb.add_argument("--report", action="store_true", help="Print state report only")

    args = parser.parse_args()

    if args.command == "serve":
        if args.host:
            os.environ["NEXUS_HOST"] = args.host
        serve(port=args.port, api_key=args.api_key)

    elif args.command == "ingest":
        ingest_dataset(args.file, api_key=args.api_key)

    elif args.command == "mb54":
        import nexus_ingest_mb54 as mb54
        if args.report:
            mb54.print_report()
        else:
            mb54.ingest_csv(Path(args.csv))

    elif args.command == "ask":
        agent = NexusAgent(api_key=args.api_key)
        agent.ask(args.prompt, persona=args.persona, use_tools=args.tools)

    elif args.command == "state":
        state = {
            "gr_nodes": load_gr_nodes(),
            "flywheel": load_flywheel(),
            "evidence": load_evidence(),
        }
        print(json.dumps(state, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
