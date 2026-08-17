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
import sqlite3
import sys
import os
import re
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import anthropic

try:
    from google import genai
except ImportError:
    genai = None

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_MODEL = "claude-opus-4-6"
GEMINI_MODEL = "gemini-2.5-pro"
DB_PATH = Path(__file__).parent / "data" / "nexus" / "nexus_masterdb.db"

FLYWHEEL_DEFAULTS = {
    "revenue_recognition": {"score": 0, "rationale": ""},
    "platform_economics": {"score": 0, "rationale": ""},
    "privacy_tos": {"score": 0, "rationale": ""},
    "governance": {"score": 0, "rationale": ""},
    "litigation_risk": {"score": 0, "rationale": ""},
}

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
# Data persistence — SQLite (schema mirrors nexus-masterdb-hub)
# ---------------------------------------------------------------------------

def _get_db() -> sqlite3.Connection:
    """Return an open SQLite connection, bootstrapping the schema on first use."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _bootstrap_schema(conn)
    return conn


def _bootstrap_schema(conn: sqlite3.Connection):
    """Create tables if they don't exist yet."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS gr_nodes (
            gr_id      TEXT PRIMARY KEY,
            title      TEXT NOT NULL,
            health     REAL DEFAULT 0.5,
            status     TEXT DEFAULT 'ACTIVE',
            metadata   TEXT DEFAULT '{}',
            updated_at TEXT DEFAULT (datetime('now','utc'))
        );
        CREATE TABLE IF NOT EXISTS evidence (
            ev_id       TEXT PRIMARY KEY,
            shortname   TEXT NOT NULL,
            source_file TEXT,
            domain      TEXT,
            gr_links    TEXT DEFAULT '[]',
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now','utc'))
        );
        CREATE TABLE IF NOT EXISTS hub_state (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT DEFAULT (datetime('now','utc'))
        );
    """)
    conn.commit()


_NODE_RESERVED_FIELDS = frozenset(("node_id", "name", "nuclear_impact"))


def load_gr_nodes() -> dict:
    """Return all GR nodes as {gr_id: node_dict}."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT gr_id, title, health, status, metadata FROM gr_nodes"
        ).fetchall()
    finally:
        conn.close()
    result = {}
    for row in rows:
        meta = json.loads(row["metadata"] or "{}")
        node = {
            "node_id": row["gr_id"],
            "name": row["title"],
            "nuclear_impact": round((row["health"] or 0.5) * 100),
            "status": row["status"],
        }
        node.update(meta)
        result[row["gr_id"]] = node
    return result


def load_flywheel() -> dict:
    """Return flywheel domain scores from hub_state."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT key, value FROM hub_state WHERE key LIKE 'flywheel::%'"
        ).fetchall()
    finally:
        conn.close()
    result = {k: dict(v) for k, v in FLYWHEEL_DEFAULTS.items()}
    for row in rows:
        domain = row["key"].split("::", 1)[1]
        result[domain] = json.loads(row["value"])
    return result


def load_evidence() -> dict:
    """Return all evidence anchors as {ev_id: anchor_dict}."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT ev_id, shortname, source_file, domain, gr_links, notes FROM evidence"
        ).fetchall()
    finally:
        conn.close()
    result = {}
    for row in rows:
        gr_links = json.loads(row["gr_links"] or "[]")
        result[row["ev_id"]] = {
            "anchor_id": row["ev_id"],
            "text": row["notes"] or "",
            "source": row["source_file"] or "",
            "domain": row["domain"] or "",
            "gr_node": gr_links[0] if gr_links else "",
        }
    return result


def delete_gr_node(node_id: str) -> bool:
    """Delete a GR node by ID. Returns True if a row was deleted."""
    conn = _get_db()
    try:
        cursor = conn.execute("DELETE FROM gr_nodes WHERE gr_id = ?", (node_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_evidence(ev_id: str) -> bool:
    """Delete an evidence anchor by ID. Returns True if a row was deleted."""
    conn = _get_db()
    try:
        cursor = conn.execute("DELETE FROM evidence WHERE ev_id = ?", (ev_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Tool execution (called when Claude uses a tool)
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a GhostRecon tool call and return a string result."""
    conn = _get_db()
    now = datetime.now(timezone.utc).isoformat()

    try:
        if tool_name == "read_gr_node":
            nid = tool_input["node_id"]
            row = conn.execute(
                "SELECT gr_id, title, health, status, metadata FROM gr_nodes WHERE gr_id = ?",
                (nid,),
            ).fetchone()
            if not row:
                return json.dumps({"error": f"Node {nid} not found"})
            meta = json.loads(row["metadata"] or "{}")
            node = {
                "node_id": row["gr_id"],
                "name": row["title"],
                "nuclear_impact": round((row["health"] or 0.5) * 100),
                "status": row["status"],
            }
            node.update(meta)
            return json.dumps(node)

        elif tool_name == "update_gr_node":
            nid = tool_input["node_id"]
            title = tool_input.get("name", nid)
            nuclear_impact = tool_input.get("nuclear_impact", 50)
            health = float(nuclear_impact) / 100.0
            # preserve existing metadata and merge new fields
            row = conn.execute(
                "SELECT metadata FROM gr_nodes WHERE gr_id = ?", (nid,)
            ).fetchone()
            existing_meta = json.loads(row["metadata"] or "{}") if row else {}
            new_meta = {k: v for k, v in tool_input.items()
                        if k not in _NODE_RESERVED_FIELDS}
            existing_meta.update(new_meta)
            conn.execute(
                """INSERT OR REPLACE INTO gr_nodes (gr_id, title, health, metadata, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (nid, title, health, json.dumps(existing_meta), now),
            )
            conn.commit()
            return json.dumps({"status": "updated", "node_id": nid})

        elif tool_name == "update_flywheel":
            domain = tool_input["domain"]
            value = json.dumps({
                "score": tool_input["score"],
                "rationale": tool_input.get("rationale", ""),
            })
            conn.execute(
                "INSERT OR REPLACE INTO hub_state (key, value, updated_at) VALUES (?, ?, ?)",
                (f"flywheel::{domain}", value, now),
            )
            conn.commit()
            return json.dumps({"status": "updated", "domain": domain, "score": tool_input["score"]})

        elif tool_name == "extract_evidence":
            aid = tool_input["anchor_id"]
            text = tool_input.get("text", "")
            shortname = text[:80] if text else aid
            gr_node = tool_input.get("gr_node", "")
            conn.execute(
                """INSERT OR REPLACE INTO evidence
                   (ev_id, shortname, source_file, domain, gr_links, notes, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    aid,
                    shortname,
                    tool_input.get("source", ""),
                    tool_input.get("domain", ""),
                    json.dumps([gr_node] if gr_node else []),
                    text,
                    now,
                ),
            )
            conn.commit()
            return json.dumps({"status": "stored", "anchor_id": aid})

        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Core agent call — streaming with tool loop
# ---------------------------------------------------------------------------

class NexusAgent:
    """NEXUS multi-persona agent with GhostRecon tool use and streaming."""

    def __init__(self, api_key: str | None = None, provider: str = "anthropic"):
        self.provider = provider
        if provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        elif provider == "gemini":
            if genai is None:
                raise ImportError("google-genai is not installed. Run: pip install google-genai")
            self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))
        else:
            raise ValueError(f"Unsupported provider: {provider}")

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

        if self.provider == "gemini":
            if use_tools:
                raise NotImplementedError("GhostRecon tool loop is currently only supported with Anthropic provider.")
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=f"{system}\n\nUser prompt:\n{prompt}",
            )
            text = getattr(response, "text", "") or ""
            if stream_print and text:
                print(text)
            return text

        messages = [{"role": "user", "content": prompt}]
        tools = GR_TOOLS if use_tools else []

        full_response = ""
        iteration = 0

        while iteration < 10:  # safety cap on tool loop
            iteration += 1

            with self.client.messages.stream(
                model=ANTHROPIC_MODEL,
                max_tokens=2048,
                thinking={"type": "enabled", "budget_tokens": 8000},
                system=system,
                messages=messages,
                tools=tools if tools else anthropic.NOT_GIVEN,
            ) as stream:
                response = stream.get_final_message()

            text_parts = []
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            text = "\n".join(text_parts)
            if text:
                if stream_print:
                    print(text)
                full_response += text

            if not tool_uses or response.stop_reason == "end_turn":
                break

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

    def orchestrate(self, prompt: str, stream_print: bool = True) -> dict:
        """
        Multi-agent orchestration: Wolf → Tiger → Suits → NEXUS Master synthesis.

        Each specialist analyses the prompt independently (no tools), then NEXUS Master
        synthesises their reports using the full GhostRecon tool loop.
        Returns a dict with keys: wolf, tiger, suits, synthesis.
        """
        results: dict[str, str] = {}

        if stream_print:
            print("\n" + "=" * 60)
            print("NEXUS ORCHESTRATION — Multi-Agent Analysis")
            print("=" * 60)

        for persona_key, label in [("wolf", "WOLF"), ("tiger", "TIGER"), ("suits", "SUITS")]:
            if stream_print:
                print(f"\n[{label}] Analysis:")
                print("-" * 40)
            results[persona_key] = self.ask(
                prompt, persona=persona_key, use_tools=False, stream_print=stream_print
            )

        synthesis_prompt = (
            f"Original prompt: {prompt}\n\n"
            f"Agent reports:\n"
            f"WOLF: {results.get('wolf', '')}\n\n"
            f"TIGER: {results.get('tiger', '')}\n\n"
            f"SUITS: {results.get('suits', '')}\n\n"
            "Synthesize the above into a unified NEXUS intelligence brief with "
            "actionable arbitration recommendations."
        )
        if stream_print:
            print("\n[NEXUS MASTER] Synthesis:")
            print("-" * 40)
        results["synthesis"] = self.ask(
            synthesis_prompt, persona="nexus_master", use_tools=True, stream_print=stream_print
        )

        return results

# ---------------------------------------------------------------------------
# Data ingestion pipeline
# ---------------------------------------------------------------------------

def ingest_dataset(filepath: str, api_key: str | None = None, provider: str = "anthropic"):
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

    agent = NexusAgent(api_key=api_key, provider=provider)

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
    print(f"  Data saved to:   {DB_PATH}")

# ---------------------------------------------------------------------------
# HTTP bridge server for HTML frontend
# ---------------------------------------------------------------------------

def serve(port: int = 7433, api_key: str | None = None, provider: str = "anthropic"):
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
    agent = NexusAgent(api_key=api_key, provider=provider)

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
            path = self.path.split("?")[0].rstrip("/")

            if path in ("", "/nexus"):
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

            elif path == "/api/health":
                self._send_json({
                    "status": "ok",
                    "provider": provider,
                    "db": str(DB_PATH),
                    "db_exists": DB_PATH.exists(),
                })

            elif path == "/api/state":
                self._send_json({
                    "gr_nodes": load_gr_nodes(),
                    "flywheel": load_flywheel(),
                    "evidence": load_evidence(),
                })

            elif path == "/api/nodes":
                self._send_json(load_gr_nodes())

            elif path.startswith("/api/nodes/"):
                node_id = path[len("/api/nodes/"):]
                nodes = load_gr_nodes()
                if node_id in nodes:
                    self._send_json(nodes[node_id])
                else:
                    self._send_json({"error": f"Node {node_id} not found"}, 404)

            elif path == "/api/evidence":
                self._send_json(load_evidence())

            elif path.startswith("/api/evidence/"):
                ev_id = path[len("/api/evidence/"):]
                evidence = load_evidence()
                if ev_id in evidence:
                    self._send_json(evidence[ev_id])
                else:
                    self._send_json({"error": f"Evidence {ev_id} not found"}, 404)

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
                    if agent.provider == "gemini":
                        response = agent.client.models.generate_content(
                            model=GEMINI_MODEL,
                            contents=f"{system}\n\nUser prompt:\n{prompt}",
                        )
                        chunk = json.dumps({"text": getattr(response, "text", "") or ""})
                        self.wfile.write(f"data: {chunk}\n\n".encode())
                        self.wfile.write(b"data: [DONE]\n\n")
                        self.wfile.flush()
                    elif use_tools:
                        # Full GhostRecon tool loop with SSE streaming
                        messages = [{"role": "user", "content": prompt}]
                        iteration = 0
                        while iteration < 10:
                            iteration += 1
                            with agent.client.messages.stream(
                                model=ANTHROPIC_MODEL,
                                max_tokens=2048,
                                thinking={"type": "enabled", "budget_tokens": 8000},
                                system=system,
                                messages=messages,
                                tools=GR_TOOLS,
                            ) as stream:
                                for text in stream.text_stream:
                                    chunk = json.dumps({"text": text})
                                    self.wfile.write(f"data: {chunk}\n\n".encode())
                                    self.wfile.flush()
                                response = stream.get_final_message()
                            tool_uses = [b for b in response.content if b.type == "tool_use"]
                            if not tool_uses or response.stop_reason == "end_turn":
                                break
                            messages.append({"role": "assistant", "content": response.content})
                            tool_results = []
                            for tu in tool_uses:
                                result = execute_tool(tu.name, tu.input)
                                chunk = json.dumps({"tool": tu.name, "result": result[:200]})
                                self.wfile.write(f"data: {chunk}\n\n".encode())
                                self.wfile.flush()
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tu.id,
                                    "content": result,
                                })
                            messages.append({"role": "user", "content": tool_results})
                        self.wfile.write(b"data: [DONE]\n\n")
                        self.wfile.flush()
                    else:
                        with agent.client.messages.stream(
                            model=ANTHROPIC_MODEL,
                            max_tokens=1024,
                            thinking={"type": "enabled", "budget_tokens": 8000},
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
                    ingest_dataset(tmp, api_key=api_key, provider=provider)
                    os.unlink(tmp)

                t = threading.Thread(target=run, daemon=True)
                t.start()
                self._send_json({"status": "ingestion started", "source": source})

            elif self.path == "/api/orchestrate":
                body = self._read_body()
                prompt = body.get("prompt", "")
                if not prompt:
                    self._send_json({"error": "no prompt provided"}, 400)
                    return

                # SSE streaming orchestration response
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self._cors()
                self.end_headers()

                def _sse(event_type: str, data: dict):
                    payload = json.dumps({"event": event_type, **data})
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()

                try:
                    _sse("phase", {"phase": "wolf", "label": "WOLF — Adversarial Analysis"})
                    wolf_resp = agent.ask(prompt, persona="wolf", use_tools=False, stream_print=False)
                    _sse("agent", {"agent": "wolf", "text": wolf_resp})

                    _sse("phase", {"phase": "tiger", "label": "TIGER — Quantitative Risk"})
                    tiger_resp = agent.ask(prompt, persona="tiger", use_tools=False, stream_print=False)
                    _sse("agent", {"agent": "tiger", "text": tiger_resp})

                    _sse("phase", {"phase": "suits", "label": "SUITS — Governance & Compliance"})
                    suits_resp = agent.ask(prompt, persona="suits", use_tools=False, stream_print=False)
                    _sse("agent", {"agent": "suits", "text": suits_resp})

                    synthesis_prompt = (
                        f"Original prompt: {prompt}\n\n"
                        f"WOLF: {wolf_resp}\n\nTIGER: {tiger_resp}\n\nSUITS: {suits_resp}\n\n"
                        "Synthesize into a unified NEXUS intelligence brief with actionable "
                        "arbitration recommendations. Use GhostRecon tools to persist findings."
                    )
                    _sse("phase", {"phase": "synthesis", "label": "NEXUS MASTER — Synthesis"})
                    synthesis_msgs = [{"role": "user", "content": synthesis_prompt}]
                    system = PERSONAS["nexus_master"]
                    iteration = 0
                    while iteration < 10:
                        iteration += 1
                        with agent.client.messages.stream(
                            model=ANTHROPIC_MODEL,
                            max_tokens=2048,
                            thinking={"type": "enabled", "budget_tokens": 8000},
                            system=system,
                            messages=synthesis_msgs,
                            tools=GR_TOOLS,
                        ) as stream:
                            for text in stream.text_stream:
                                _sse("text", {"text": text})
                            response = stream.get_final_message()
                        tool_uses = [b for b in response.content if b.type == "tool_use"]
                        if not tool_uses or response.stop_reason == "end_turn":
                            break
                        synthesis_msgs.append({"role": "assistant", "content": response.content})
                        tool_results = []
                        for tu in tool_uses:
                            result = execute_tool(tu.name, tu.input)
                            _sse("tool", {"tool": tu.name, "result": result[:200]})
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tu.id,
                                "content": result,
                            })
                        synthesis_msgs.append({"role": "user", "content": tool_results})
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                except Exception as e:
                    _sse("error", {"error": str(e)})

            elif self.path == "/api/nodes":
                body = self._read_body()
                node_id = body.get("node_id")
                if not node_id:
                    self._send_json({"error": "node_id required"}, 400)
                    return
                result = execute_tool("update_gr_node", body)
                self._send_json(json.loads(result))

            else:
                self._send_json({"error": "not found"}, 404)

        def do_PUT(self):
            path = self.path.rstrip("/")
            if path.startswith("/api/nodes/"):
                node_id = path[len("/api/nodes/"):]
                body = self._read_body()
                body["node_id"] = node_id
                result = execute_tool("update_gr_node", body)
                self._send_json(json.loads(result))
            elif path.startswith("/api/evidence/"):
                ev_id = path[len("/api/evidence/"):]
                body = self._read_body()
                body["anchor_id"] = ev_id
                result = execute_tool("extract_evidence", body)
                self._send_json(json.loads(result))
            else:
                self._send_json({"error": "not found"}, 404)

        def do_DELETE(self):
            path = self.path.rstrip("/")
            if path.startswith("/api/nodes/"):
                node_id = path[len("/api/nodes/"):]
                deleted = delete_gr_node(node_id)
                if deleted:
                    self._send_json({"status": "deleted", "node_id": node_id})
                else:
                    self._send_json({"error": f"Node {node_id} not found"}, 404)
            elif path.startswith("/api/evidence/"):
                ev_id = path[len("/api/evidence/"):]
                deleted = delete_evidence(ev_id)
                if deleted:
                    self._send_json({"status": "deleted", "anchor_id": ev_id})
                else:
                    self._send_json({"error": f"Evidence {ev_id} not found"}, 404)
            else:
                self._send_json({"error": "not found"}, 404)

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    print(f"NEXUS AI Bridge running at http://127.0.0.1:{port}/")
    print(f"  NEXUS App:  http://127.0.0.1:{port}/")
    print(f"  API state:  http://127.0.0.1:{port}/api/state")
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
    parser.add_argument("--provider", choices=["anthropic", "gemini"], default="anthropic", help="LLM provider")
    parser.add_argument("--api-key", help="Provider API key (overrides environment variables)")

    sub = parser.add_subparsers(dest="command")

    # serve
    sp = sub.add_parser("serve", help="Start HTTP bridge server")
    sp.add_argument("--port", type=int, default=7433, help="Port (default: 7433)")

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

    # orchestrate
    op = sub.add_parser("orchestrate", help="Run multi-agent orchestration (Wolf+Tiger+Suits→Synthesis)")
    op.add_argument("prompt", help="The prompt/scenario to analyse")

    # state
    sub.add_parser("state", help="Print current GR nodes and flywheel state")

    args = parser.parse_args()

    if args.command == "serve":
        serve(port=args.port, api_key=args.api_key, provider=args.provider)

    elif args.command == "ingest":
        ingest_dataset(args.file, api_key=args.api_key, provider=args.provider)

    elif args.command == "ask":
        agent = NexusAgent(api_key=args.api_key, provider=args.provider)
        agent.ask(args.prompt, persona=args.persona, use_tools=args.tools)

    elif args.command == "orchestrate":
        agent = NexusAgent(api_key=args.api_key, provider=args.provider)
        agent.orchestrate(args.prompt)

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
