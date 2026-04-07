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
# Core agent call — streaming with tool loop
# ---------------------------------------------------------------------------

class NexusAgent:
    """NEXUS multi-persona agent with GhostRecon tool use and streaming."""

    def __init__(self, api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def ask(
        self,
        prompt: str,
        persona: str = "nexus_master",
        use_tools: bool = True,
        stream_print: bool = True,
    ) -> str:
        """
        Send a prompt to the specified NEXUS persona.
        Runs the tool loop automatically. Returns final text response.
        """
        system = PERSONAS.get(persona, PERSONAS["nexus_master"])
        messages = [{"role": "user", "content": prompt}]
        tools = GR_TOOLS if use_tools else []

        full_response = ""
        iteration = 0

        while iteration < 10:  # safety cap on tool loop
            iteration += 1

            with self.client.messages.stream(
                model=MODEL,
                max_tokens=2048,
                thinking={"type": "adaptive"},
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
    agent = NexusAgent(api_key=api_key)

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
                })
            else:
                self._send_json({"error": "not found"}, 404)

        def do_POST(self):
            if self.path == "/api/ask":
                body = self._read_body()
                prompt = body.get("prompt", "")
                persona = body.get("persona", "nexus_master")
                use_tools = body.get("use_tools", False)

                # SSE streaming response
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self._cors()
                self.end_headers()

                system = PERSONAS.get(persona, PERSONAS["nexus_master"])
                try:
                    with agent.client.messages.stream(
                        model=MODEL,
                        max_tokens=4096,
                        system=system,
                        messages=[{"role": "user", "content": prompt}],
                    ) as stream:
                        for text in stream.text_stream:
                            chunk = json.dumps({"text": text})
                            self.wfile.write(f"data: {chunk}\n\n".encode())
                            self.wfile.flush()
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                except Exception as e:
                    err = json.dumps({"error": str(e)})
                    self.wfile.write(f"data: {err}\n\n".encode())
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
