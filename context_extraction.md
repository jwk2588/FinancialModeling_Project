# FinancialModeling_Project — Full Contextual Code Extraction
> Generated: Fri Aug 21 20:55:57 UTC 2026
> Purpose: AI-agnostic ingestion of all source code and documentation

---

---

## `README.md`

```markdown
# Conda_Financial_Modeling
Financial Forecast Model using Anaconda for Python


## NEXUS AI Provider Setup

`nexus_ai.py` now supports both Anthropic and Gemini providers.

- Anthropic (default): set `ANTHROPIC_API_KEY`
- Gemini: set `GEMINI_API_KEY` or pass `--api-key`

Examples:

```bash
python nexus_ai.py ask "Summarize risk" --provider anthropic
python nexus_ai.py ask "Summarize risk" --provider gemini --api-key "$GEMINI_API_KEY"
```

> Note: GhostRecon tool execution (`--tools`) is currently supported with Anthropic provider only.
```

---

## `requirements.txt`

```text
pandas
openpyxl
yfinance
numpy
matplotlib
xlwings
fuzzywuzzy
python-Levenshtein
anthropic>=0.89.0
google-genai>=0.7.0
```

---

## `__init__.py`

```python
```

---

## `main.py`

```python
import os
import sys

# Add the project root to the system path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts.data_ingestion.data_retrieval import main as data_retrieval_main
from scripts.data_preprocessing.balance_sheet_transformation import BalanceSheetTransformer
from scripts.data_preprocessing.income_statement_transformation import IncomeStatementTransformer
from scripts.data_preprocessing.cash_flow_transformation import CashFlowTransformer
from scripts.generate_scripts import main as generate_scripts_main
from scripts.utilities.data_transformation_utils import (
    get_data_paths,
    archive_files,
    prune_archives,
    logger
)

def validate_and_archive_folders():
    """Validates the folder structure and archives existing files."""
    raw_data_dir, processed_data_dir = get_data_paths()

    # Define archive folders
    raw_archive_dir = os.path.join(raw_data_dir, 'archive')
    processed_archive_dir = os.path.join(processed_data_dir, 'archive')

    # Ensure directories exist
    for directory in [raw_data_dir, processed_data_dir, raw_archive_dir, processed_archive_dir]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Validated or created directory: {directory}")

def run_data_ingestion():
    """Runs the data ingestion process."""
    ticker_symbol = 'GM'  # Replace with desired default ticker symbol
    data_retrieval_main(ticker_symbol)

def run_data_preprocessing():
    """Runs the data preprocessing steps."""

    # Process balance sheet data
    balance_sheet_transformer = BalanceSheetTransformer()
    balance_sheet_transformer.transform()

    # Process income statement data
    income_statement_transformer = IncomeStatementTransformer()
    income_statement_transformer.transform()

    # Process cash flow data
    cash_flow_transformer = CashFlowTransformer()
    cash_flow_transformer.transform()

    # Generate baseline values
    generate_scripts_main()

def main():
    """Main function to run the data processing pipeline."""
    try:
        validate_and_archive_folders()

        # Run processes
        run_data_ingestion()
        run_data_preprocessing()

        logger.info("Main workflow completed successfully.")
    except Exception as e:
        logger.exception(f"An error occurred in the main execution: {e}")

if __name__ == "__main__":
    main()```

---

## `nexus_ai.py`

```python
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

try:
    from google import genai
except ImportError:
    genai = None

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANTHROPIC_MODEL = "claude-opus-4-6"
GEMINI_MODEL = "gemini-2.5-pro"
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
                thinking={"type": "adaptive"},
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
    print(f"  Data saved to:   {DATA_DIR}")

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
                    if agent.provider == "gemini":
                        response = agent.client.models.generate_content(
                            model=GEMINI_MODEL,
                            contents=f"{system}\n\nUser prompt:\n{prompt}",
                        )
                        chunk = json.dumps({"text": getattr(response, "text", "") or ""})
                        self.wfile.write(f"data: {chunk}\n\n".encode())
                        self.wfile.write(b"data: [DONE]\n\n")
                        self.wfile.flush()
                    else:
                        with agent.client.messages.stream(
                            model=ANTHROPIC_MODEL,
                            max_tokens=1024,
                            thinking={"type": "adaptive"},
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
```

---

## `setup_project.py`

```python
import os

# Define the project structure
project_name = "financial_modeling_project"
folders = [
    "data",
    "notebooks",
    "scripts"
]

subfolders = {
    "scripts": [
        "data_retrieval",
        "data_transformation",
        "financial_forecast",
        "depreciation_schedule"
    ],
    "data": [
        "raw",  # Store raw datasets or Excel files here
        "processed"  # Store cleaned or processed versions
    ]
}

# Create the main project folder if it doesn't exist
if not os.path.exists(project_name):
    os.mkdir(project_name)

# Create each main folder and subfolders
for folder in folders:
    path = os.path.join(project_name, folder)
    if not os.path.exists(path):
        os.mkdir(path)
    # If the folder has subfolders, create them
    if folder in subfolders:
        for subfolder in subfolders[folder]:
            subfolder_path = os.path.join(path, subfolder)
            if not os.path.exists(subfolder_path):
                os.mkdir(subfolder_path)

# Create additional files
open(os.path.join(project_name, "integrate_to_excel.py"), 'a').close()
open(os.path.join(project_name, "environment_setup.md"), 'a').close()
open(os.path.join(project_name, "requirements.txt"), 'a').close()

print("Project structure created successfully.")
```

---

## `.gitignore`

```
# Ignore data files
/data/raw/
/data/processed/
/data/archive/

# Ignore Python compiled files
*.pyc
__pycache__/

# Ignore virtual environment
/venv/

# Ignore Jupyter Notebook checkpoints
.ipynb_checkpoints/

```

---

## `.gitattributes`

```
* text=auto
```

---

## `FinancialModeling_Project.code-workspace`

```
{
	"folders": [
		{
			"path": "."
		}
	],
	"settings": {}
}```

---

## `.claude/NEXUS CODEX`

```
gh repo clone github/copilot-cli```

---

## `.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

---

## `archive/# Code Citations.md`

```markdown
# Code Citations

## License: MIT
https://github.com/microsoft/vscode/tree/ef9f5d7f6f53c69f8536057d49a7a476c48d1605/src/vs/workbench/contrib/url/browser/trustedDomainsFileSystemProvider.ts

```
in the list below can be opened without link protection.
// The following examples show what entries can look like:
// - "https://microsoft.com": Matches this specific domain using https
// - "https://microsoft.com:8080
```


## License: MIT
https://github.com/opensumi/monaco-editor-core/tree/a14c678ec28ec804b37984e07a794b9c22acf737/src/vs/workbench/contrib/url/browser/trustedDomainsFileSystemProvider.ts

```
https://microsoft.com": Matches this specific domain using https
// - "https://microsoft.com:8080": Matches this specific domain on this port using https
// - "https://microsoft.com:*": Matches
```

```

---

## `scripts/__init__.py`

```python
```

---

## `scripts/balance_sheet_test.py`

```python
# Standalone testing script (balance_sheet_test.py)

from scripts.data_preprocessing.financial_statement_transformer import FinancialStatementTransformer

# Initialize transformer with testing mode
transformer = FinancialStatementTransformer("balance_sheet")

# Load, transform, and display data without saving files
transformer.load_data()
transformer.transform_data()
print("Transformed Data:")
print(transformer.df)
```

---

## `scripts/generate_scripts.py`

```python
# scripts/generate_scripts.py

import os
import pandas as pd
from scripts.utilities.data_transformation_utils import (
    get_data_paths,
    archive_files,
    prune_archives,
    logger
)

def load_historical_data():
    """Loads the transformed and tagged financial statements."""
    try:
        _, processed_data_dir = get_data_paths()
        balance_sheet_path = os.path.join(processed_data_dir, 'tagged_balance_sheet.csv')
        income_statement_path = os.path.join(processed_data_dir, 'tagged_income_statement.csv')
        cash_flow_path = os.path.join(processed_data_dir, 'tagged_cash_flow.csv')

        logger.info("Loading processed financial statements...")

        balance_sheet = pd.read_csv(balance_sheet_path, index_col='Category')
        income_statement = pd.read_csv(income_statement_path, index_col='Category')
        cash_flow = pd.read_csv(cash_flow_path, index_col='Category')

        logger.info("Financial statements loaded successfully.")
        return balance_sheet, income_statement, cash_flow
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except Exception as e:
        logger.error(f"An error occurred while loading data: {e}")
        raise

def combine_statements(balance_sheet, income_statement, cash_flow):
    """Combines the financial statements into a single DataFrame."""
    try:
        balance_sheet['Statement Type'] = 'Balance Sheet'
        income_statement['Statement Type'] = 'Income Statement'
        cash_flow['Statement Type'] = 'Cash Flow Statement'

        balance_sheet.reset_index(inplace=True)
        income_statement.reset_index(inplace=True)
        cash_flow.reset_index(inplace=True)

        balance_sheet_melted = balance_sheet.melt(
            id_vars=['Category', 'Statement Type'],
            var_name='Period',
            value_name='Amount'
        )
        income_statement_melted = income_statement.melt(
            id_vars=['Category', 'Statement Type'],
            var_name='Period',
            value_name='Amount'
        )
        cash_flow_melted = cash_flow.melt(
            id_vars=['Category', 'Statement Type'],
            var_name='Period',
            value_name='Amount'
        )

        combined_df = pd.concat(
            [balance_sheet_melted, income_statement_melted, cash_flow_melted],
            ignore_index=True
        )

        logger.info("Financial statements combined successfully.")
        return combined_df
    except Exception as e:
        logger.error(f"An error occurred while combining statements: {e}")
        raise

def calculate_baseline(dataframe):
    """Calculates baseline values for selected line items."""
    logger.info("Calculating baseline values for selected line items...")
    try:
        selected_line_items = {
            'Income Statement': [
                'Revenue', 'Cost of Goods Sold', 'Gross Profit',
                'Operating Expenses', 'Operating Income', 'Net Income'
            ],
            'Cash Flow Statement': [
                'Net Cash Provided by Operating Activities',
                'Net Cash Used in Investing Activities',
                'Net Cash Used in Financing Activities',
                'Free Cash Flow'
            ],
            'Balance Sheet': [
                'Total Assets', 'Total Liabilities', 'Total Equity',
                'Cash and Cash Equivalents', 'Accounts Receivable',
                'Inventory', 'Accounts Payable',
                'Allowance for Doubtful Accounts',
                'Deferred Tax Assets', 'Deferred Tax Liabilities'
            ]
        }

        dataframe['Amount'] = pd.to_numeric(dataframe['Amount'], errors='coerce')
        dataframe = dataframe.dropna(subset=['Amount'])

        baseline_list = []

        for statement_type, line_items in selected_line_items.items():
            df_statement = dataframe[dataframe['Statement Type'] == statement_type]
            df_selected = df_statement[df_statement['Category'].isin(line_items)]

            if statement_type in ['Income Statement', 'Cash Flow Statement']:
                baseline = df_selected.groupby(['Category'])['Amount'].mean().reset_index()
            elif statement_type == 'Balance Sheet':
                latest_period = df_selected['Period'].max()
                baseline = df_selected[df_selected['Period'] == latest_period][['Category', 'Amount']]
            else:
                continue

            baseline['Statement Type'] = statement_type
            baseline_list.append(baseline)

        baseline_combined = pd.concat(baseline_list, ignore_index=True)
        baseline_combined = baseline_combined[['Category', 'Statement Type', 'Amount']]

        logger.info(f"Baseline calculated successfully:\n{baseline_combined.head()}")
        return baseline_combined
    except Exception as e:
        logger.error(f"Error while calculating baseline: {e}")
        raise

def save_baseline_to_csv(baseline, output_path):
    """Saves the baseline values to a CSV file."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        baseline.to_csv(output_path, index=False)
        logger.info(f"Baseline saved to {output_path}")
    except Exception as e:
        logger.error(f"Error while saving baseline: {e}")
        raise

def main():
    try:
        _, processed_data_dir = get_data_paths()
        archive_dir = os.path.join(processed_data_dir, 'archive')

        # Load the transformed and tagged financial statements before archiving
        balance_sheet, income_statement, cash_flow = load_historical_data()

        # Archive old files after loading
        archive_files(processed_data_dir, archive_dir)

        # Combine the statements
        combined_df = combine_statements(balance_sheet, income_statement, cash_flow)
        combined_filepath = os.path.join(processed_data_dir, 'combined_statements.csv')
        combined_df.to_csv(combined_filepath, index=False)
        logger.info(f"Combined statements saved to {combined_filepath}")

        # Calculate the baseline
        baseline_values = calculate_baseline(combined_df)
        baseline_filepath = os.path.join(processed_data_dir, 'baseline_values.csv')
        save_baseline_to_csv(baseline_values, baseline_filepath)

        # Prune archives
        prune_archives(archive_dir, retention_days=30, max_versions=5)

    except Exception as e:
        logger.error(f"An error occurred in the script: {e}")
        raise

if __name__ == "__main__":
    main()
```

---

## `scripts/data_ingestion/__init__.py`

```python
```

---

## `scripts/data_ingestion/data_retrieval.py`

```python
import yfinance as yf
import pandas as pd
import os
from typing import Dict
from scripts.utilities.data_transformation_utils import get_data_paths, logger

def get_financial_data_yfinance(ticker_symbol: str) -> Dict[str, pd.DataFrame]:
    """
    Fetches financial statements for the given ticker symbol using yfinance.

    Args:
        ticker_symbol (str): The ticker symbol of the company (e.g., "GM").

    Returns:
        Dict[str, pd.DataFrame]: A dictionary containing financial statements
        as DataFrames for income statement, balance sheet, and cash flow.
    """
    try:
        logger.info(f"Fetching financial data for ticker: {ticker_symbol}")
        ticker = yf.Ticker(ticker_symbol)

        # Fetch financial statements
        income_statement = ticker.financials
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow

        if income_statement.empty or balance_sheet.empty or cash_flow.empty:
            logger.warning(f"No financial data found for ticker: {ticker_symbol}")
            return {}

        logger.info(f"Successfully fetched financial data for {ticker_symbol}")
        return {
            'income_statement': income_statement,
            'balance_sheet': balance_sheet,
            'cash_flow': cash_flow
        }
    except Exception as e:
        logger.error(f"An error occurred while fetching financial data for {ticker_symbol}: {e}")
        return {}

def save_financial_data_to_csv(financial_data: Dict[str, pd.DataFrame]):
    """
    Saves the financial data to separate CSV files in the 'raw' subfolder.

    Args:
        financial_data (Dict[str, pd.DataFrame]): Dictionary of DataFrames to save.
    """
    if not financial_data:
        logger.error("No financial data available to save.")
        return

    try:
        raw_data_dir, _ = get_data_paths()
        raw_data_dir = os.path.abspath(raw_data_dir)
        os.makedirs(raw_data_dir, exist_ok=True)
        logger.info(f"Saving financial data to directory: {raw_data_dir}")

        for statement_type, df in financial_data.items():
            if df.empty:
                logger.warning(f"{statement_type} DataFrame is empty. Skipping save.")
                continue

            csv_path = os.path.join(raw_data_dir, f"{statement_type}.csv")
            df.to_csv(csv_path, index=True)
            logger.info(f"Saved {statement_type} data to {csv_path}")

        logger.info("Financial data saved successfully.")
    except Exception as e:
        logger.error(f"An error occurred while saving financial data: {e}")

def main(ticker_symbol=None):
    """
    Main function to retrieve and save financial data for a given ticker symbol.
    """
    if ticker_symbol is None:
        ticker_symbol = input("Enter the ticker symbol (e.g., GM): ").strip().upper()
    else:
        ticker_symbol = ticker_symbol.strip().upper()

    if not ticker_symbol:
        logger.error("No ticker symbol provided. Exiting.")
        return

    financial_data = get_financial_data_yfinance(ticker_symbol)
    if financial_data:
        save_financial_data_to_csv(financial_data)

if __name__ == "__main__":
    main()
```

---

## `scripts/data_preprocessing/__init__.py`

```python
```

---

## `scripts/data_preprocessing/balance_sheet_transformation.py`

```python
from scripts.data_preprocessing.financial_statement_transformer import BalanceSheetTransformer

if __name__ == "__main__":
    transformer = BalanceSheetTransformer()
    transformer.transform()
```

---

## `scripts/data_preprocessing/cash_flow_transformation.py`

```python
# scripts/data_preprocessing/cash_flow_transformation.py

from scripts.data_preprocessing.financial_statement_transformer import CashFlowTransformer

if __name__ == "__main__":
    transformer = CashFlowTransformer()
    transformer.transform()
```

---

## `scripts/data_preprocessing/financial_statement_transformer.py`

```python
import os
import pandas as pd
from scripts.utilities.data_transformation_utils import (
    get_data_paths,
    tag_line_item_indices,
    line_item_dict,
    logger
)

class FinancialStatementTransformer:
    """Base class for transforming financial statements with validation and testing entry points."""

    def __init__(self, statement_type: str):
        self.statement_type = statement_type  # e.g., 'balance_sheet', 'income_statement', or 'cash_flow'
        self.raw_file, self.processed_file, self.tagged_file = self.get_file_paths()
        self.df = None  # Placeholder for the loaded DataFrame

    def get_file_paths(self):
        """Constructs file paths for raw, processed, and tagged files."""
        raw_dir, processed_dir = get_data_paths()
        raw_file = os.path.join(raw_dir, f'{self.statement_type}.csv')
        processed_file = os.path.join(processed_dir, f'processed_{self.statement_type}.csv')
        tagged_file = os.path.join(processed_dir, f'tagged_{self.statement_type}.csv')
        return raw_file, processed_file, tagged_file

    def load_data(self):
        """Loads raw financial statement data."""
        if not os.path.exists(self.raw_file):
            raise FileNotFoundError(f"Raw file not found: {self.raw_file}")
        self.df = pd.read_csv(self.raw_file)
        logger.info(f"Loaded {self.statement_type} data:\n{self.df.head()}")

    def validate_data(self):
        """
        Validates the raw data to ensure it can proceed with transformations.
        Example checks: non-empty DataFrame, numeric values, and appropriate structure.
        """
        if self.df is None or self.df.empty:
            raise ValueError(f"The raw data for {self.statement_type} is empty. Please check the source file.")

        # Example validation: Ensure the first column exists
        first_column_name = self.df.columns[0]
        if first_column_name == '':
            raise ValueError(f"The first column in the {self.statement_type} data is unnamed or blank.")

        # Example validation: Ensure at least one numeric column exists
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        if numeric_cols.empty:
            raise ValueError(f"No numeric columns found in {self.statement_type} data for calculations.")

        logger.info(f"{self.statement_type} data passed validation checks.")

    def transform_data(self):
        """Applies necessary transformations to the financial statement."""
        try:
            self.validate_data()

            # Step 1: Reset index if any
            if self.df.index.name:
                self.df.reset_index(inplace=True)

            # Step 2: Set the first column as 'Category' if it's unnamed
            if 'Unnamed: 0' in self.df.columns:
                self.df.rename(columns={'Unnamed: 0': 'Category'}, inplace=True)
            elif self.df.columns[0] != 'Category':
                self.df.rename(columns={self.df.columns[0]: 'Category'}, inplace=True)

            # Step 3: Sort columns (dates) in chronological order
            date_columns = [col for col in self.df.columns if col != 'Category']
            date_columns = sorted(date_columns, reverse=True)  # Sort dates in descending order
            column_order = ['Category'] + date_columns
            self.df = self.df[column_order]

            # Step 4: Remove any rows where Category is NaN or empty
            self.df = self.df[self.df['Category'].notna()]
            self.df = self.df[self.df['Category'] != '']

            # Step 5: Apply statement-specific transformations
            if self.statement_type == 'income_statement':
                # For income statement, keep natural order (Revenue at top, Net Income at bottom)
                self.df = self.df.iloc[::-1]
            elif self.statement_type == 'cash_flow':
                # For cash flow, maintain operating/investing/financing sections
                self.df = self.df.iloc[::-1]
            elif self.statement_type == 'balance_sheet':
                # For balance sheet, maintain Assets -> Liabilities -> Equity order
                self.df = self.df.iloc[::-1]  # Reverse to get Assets at top

            # Step 6: Replace any NaN values with empty string
            self.df = self.df.fillna('')

            logger.info(f"Transformed {self.statement_type} data:\n{self.df.head()}")

        except Exception as e:
            logger.error(f"Error during transformation of {self.statement_type}: {e}")
            raise

    def tag_data(self):
        """Tags line items using the predefined dictionary."""
        if 'LineItem' not in self.df.columns:
            logger.warning(f"Column 'LineItem' not found in {self.statement_type} data.")
            return
        self.df = tag_line_item_indices(self.df, line_item_dict)
        logger.info(f"Tagged {self.statement_type} data:\n{self.df.head()}")

    def save_data(self, filename: str, data: pd.DataFrame):
        """Saves DataFrame to a specified file."""
        _, processed_dir = get_data_paths()
        output_path = os.path.join(processed_dir, filename)
        data.to_csv(output_path, index=False)
        logger.info(f"Saved data to {output_path}")

    def transform(self):
        """
        Executes the full transformation pipeline.
        Can be stopped or rerun from specific steps during testing.
        """
        try:
            self.load_data()
            self.transform_data()

            # Save intermediate data for inspection
            self.save_data(f'processed_{self.statement_type}.csv', self.df)

            # Tag and save tagged data
            self.tag_data()
            self.save_data(f'tagged_{self.statement_type}.csv', self.df)

        except Exception as e:
            logger.error(f"Error transforming {self.statement_type}: {e}")

# Child classes for specific financial statements
class BalanceSheetTransformer(FinancialStatementTransformer):
    def __init__(self):
        super().__init__('balance_sheet')

class IncomeStatementTransformer(FinancialStatementTransformer):
    def __init__(self):
        super().__init__('income_statement')

class CashFlowTransformer(FinancialStatementTransformer):
    def __init__(self):
        super().__init__('cash_flow')

if __name__ == "__main__":
    # Entry points for testing transformations
    logger.info("Starting transformations for selected statements...")
    for Transformer in [BalanceSheetTransformer, IncomeStatementTransformer, CashFlowTransformer]:
        transformer = Transformer()
        transformer.transform()
```

---

## `scripts/data_preprocessing/income_statement_transformation.py`

```python
from scripts.data_preprocessing.financial_statement_transformer import IncomeStatementTransformer

if __name__ == "__main__":
    transformer = IncomeStatementTransformer()
    transformer.transform()
```

---

## `scripts/models/depreciation_schedule.py`

```python
import pandas as pd  # Ensure this path is correctly set based on environment configuration
import yfinance as yf
import os

# Import necessary functions from other modules
from scripts.data_retrieval.data_retrieval import get_financial_data
from scripts.data_transformation.data_transformation import transform_financial_data
from scripts.financial_forecast.financial_forecast import generate_forecast

# Step 5: Create a Depreciation Schedule
# This function creates a depreciation schedule using the straight-line method
def create_depreciation_schedule(initial_capex, useful_life, depreciation_method="straight-line"):
    if depreciation_method != "straight-line":
        raise NotImplementedError("Only straight-line depreciation is currently implemented.")

    # Calculate annual depreciation
    annual_depreciation = initial_capex / useful_life
    depreciation_schedule = pd.DataFrame({
        "Year": list(range(1, useful_life + 1)),
        "Depreciation Expense": [annual_depreciation] * useful_life
    })
    return depreciation_schedule

# Step 6: Integrate Depreciation into Excel Output
# Extend the function to include the depreciation schedule in the output
def integrate_to_excel(ticker_symbol, financial_data, forecast_data, depreciation_schedule, output_dir="."):
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_path = os.path.join(output_dir, f'{ticker_symbol}_financial_model.xlsx')
    
    with pd.ExcelWriter(output_path) as writer:
        # Write the income statement, balance sheet, and cash flow statement to separate sheets
        financial_data['income_statement'].to_excel(writer, sheet_name='Income Statement')
        financial_data['balance_sheet'].to_excel(writer, sheet_name='Balance Sheet')
        financial_data['cash_flow'].to_excel(writer, sheet_name='Cash Flow Statement')
        
        # Write the forecast data to separate sheets
        forecast_data['income_statement'].to_excel(writer, sheet_name='Forecast Income Statement')
        forecast_data['balance_sheet'].to_excel(writer, sheet_name='Forecast Balance Sheet')
        forecast_data['cash_flow'].to_excel(writer, sheet_name='Forecast Cash Flow')

        # Write the depreciation schedule to a separate sheet
        depreciation_schedule.to_excel(writer, sheet_name='Depreciation Schedule')

    print(f'{output_path} has been created successfully.')

# Main Script
if __name__ == "__main__":
    # Define the ticker symbol
    ticker_symbol = 'GM'
    
    # Step 1: Get Financial Data from Yahoo Finance
    financial_data = get_financial_data(ticker_symbol)
    
    # Step 2: Transform Financial Data
    transformed_financial_data = transform_financial_data(financial_data)
    
    # Step 3: Generate Forecast for 3 years
    forecast_data = generate_forecast(transformed_financial_data, forecast_years=3)
    
    # Step 4: Create Depreciation Schedule
    initial_capex = 1000000  # Example CapEx in dollars
    useful_life = 5  # Useful life in years
    depreciation_schedule = create_depreciation_schedule(initial_capex, useful_life)
    
    # Step 5: Export to Excel
    output_directory = "./financial_models"  # Change this to your desired output directory
    integrate_to_excel(ticker_symbol, transformed_financial_data, forecast_data, depreciation_schedule, output_dir=output_directory)
```

---

## `scripts/models/financial_forecast.py`

```python
import pandas as pd

def generate_forecast(financial_data, forecast_years=3):
    forecast = {}
    for key, df in financial_data.items():
        # Calculate mean values of each column to use for forecasts
        forecast_values = df.mean(axis=0)
        # Repeat the forecast values for the given number of forecast years
        forecast[key] = pd.DataFrame([forecast_values] * forecast_years)
        forecast[key].columns = df.columns  # Ensure forecast DataFrame has the same columns as the original
    return forecast
```

---

## `scripts/outputs/integrate_to_excel.py`

```python
import os
import pandas as pd
from scripts.data_ingestion.data_retrieval import get_financial_data
from scripts.data_preprocessing.data_transformation import transform_financial_data
from scripts.models.financial_forecast import generate_forecast
from scripts.models.depreciation_schedule import generate_depreciation_schedule

def integrate_to_excel(ticker_symbol, financial_data, forecast_data, depreciation_data, output_dir="."):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_path = os.path.join(output_dir, f'{ticker_symbol}_financial_model.xlsx')
    
    with pd.ExcelWriter(output_path) as writer:
        financial_data['income_statement'].to_excel(writer, sheet_name='Income Statement', index=False)
        financial_data['balance_sheet'].to_excel(writer, sheet_name='Balance Sheet', index=False)
        financial_data['cash_flow'].to_excel(writer, sheet_name='Cash Flow Statement', index=False)
        
        forecast_data['income_statement'].to_excel(writer, sheet_name='Forecast Income Statement', index=False)
        forecast_data['balance_sheet'].to_excel(writer, sheet_name='Forecast Balance Sheet', index=False)
        forecast_data['cash_flow'].to_excel(writer, sheet_name='Forecast Cash Flow', index=False)
        
        depreciation_data.to_excel(writer, sheet_name='Depreciation Schedule', index=False)

    print(f'{output_path} has been created successfully.')

# Run Integration
if __name__ == "__main__":
    ticker_symbol = 'GM'
    financial_data = get_financial_data(ticker_symbol)
    transformed_financial_data = transform_financial_data(financial_data)
    forecast_data = generate_forecast(transformed_financial_data, forecast_years=3)
    initial_capex = 1000000
    useful_life = 5
    depreciation_data = generate_depreciation_schedule(initial_capex, useful_life)

    output_directory = "./financial_models"
    integrate_to_excel(ticker_symbol, transformed_financial_data, forecast_data, depreciation_data, output_dir=output_directory)
```

---

## `scripts/utilities/__init__.py`

```python
```

---

## `scripts/utilities/data_transformation_utils.py`

```python
import os
import logging
from datetime import datetime, timedelta

import pandas as pd
from fuzzywuzzy import process

# Configure logger at the module level
logger = logging.getLogger("FinancialModeling")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Get project paths
def get_data_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    data_dir = os.path.join(project_root, "data")
    raw_data_dir = os.path.join(data_dir, "raw")
    processed_data_dir = os.path.join(data_dir, "processed")
    return raw_data_dir, processed_data_dir

# Disable scientific notation globally for Pandas
def disable_scientific_notation():
    pd.options.display.float_format = "{:,.0f}".format

# Expanded line item dictionary for fuzzy matching
line_item_dict = {
    "Revenue": ["Revenue", "Total Revenue", "Net Revenue", "Sales"],
    "Cost of Goods Sold": ["Cost of Goods Sold", "COGS", "Cost of Sales", "Cost of Revenue"],
    "Gross Profit": ["Gross Profit", "Gross Income", "Gross Margin"],
    "Operating Expenses": ["Operating Expenses", "OPEX", "Total Operating Expenses"],
    "Operating Income": ["Operating Income", "Operating Profit", "EBIT"],
    "Net Income": ["Net Income", "Net Profit", "Income After Tax", "Earnings"],
    "Research and Development": ["Research and Development", "R&D Expenses", "Research & Development"],
    "Selling General and Administrative": [
        "Selling General and Administrative",
        "SG&A",
        "Selling, General & Administrative",
    ],
    "Interest Expense": ["Interest Expense", "Finance Costs", "Interest and Other Expenses"],
    "Income Tax Expense": ["Income Tax Expense", "Taxes", "Provision for Income Taxes"],
    "Other Income/Expense": ["Other Income/Expense", "Other Income", "Other Expense"],
    "Total Operating Income": ["Total Operating Income", "Income from Operations"],
    "Total Assets": ["Total Assets", "Assets"],
    "Total Liabilities": ["Total Liabilities", "Liabilities"],
    "Total Equity": ["Total Equity", "Shareholders' Equity", "Stockholders' Equity"],
    "Cash and Cash Equivalents": ["Cash and Cash Equivalents", "Cash", "Cash Equivalents"],
    "Short-Term Investments": ["Short-Term Investments", "Marketable Securities"],
    "Accounts Receivable": ["Accounts Receivable", "Receivables", "Trade Receivables"],
    "Inventory": ["Inventory", "Inventories"],
    "Other Current Assets": ["Other Current Assets", "Prepaid Expenses"],
    "Long-Term Investments": ["Long-Term Investments", "Non-Current Investments"],
    "Property Plant and Equipment": ["Property, Plant & Equipment", "PP&E", "Fixed Assets"],
    "Goodwill": ["Goodwill"],
    "Intangible Assets": ["Intangible Assets", "Intangibles"],
    "Other Assets": ["Other Assets", "Miscellaneous Assets"],
    "Accounts Payable": ["Accounts Payable", "Payables", "Trade Payables"],
    "Short-Term Debt": ["Short-Term Debt", "Current Portion of Long-Term Debt"],
    "Other Current Liabilities": ["Other Current Liabilities", "Accrued Liabilities"],
    "Long-Term Debt": ["Long-Term Debt", "Non-Current Debt"],
    "Deferred Tax Liabilities": ["Deferred Tax Liabilities", "DTL"],
    "Deferred Tax Assets": ["Deferred Tax Assets", "DTA"],
    "Other Liabilities": ["Other Liabilities", "Miscellaneous Liabilities"],
    "Common Stock": ["Common Stock", "Ordinary Shares"],
    "Retained Earnings": ["Retained Earnings", "Accumulated Earnings"],
    "Accumulated Other Comprehensive Income": [
        "Accumulated Other Comprehensive Income",
        "AOCI",
    ],
    "Treasury Stock": ["Treasury Stock", "Treasury Shares"],
    "Allowance for Doubtful Accounts": [
        "Allowance for Doubtful Accounts",
        "Bad Debt Allowance",
        "Provision for Credit Losses",
    ],
    "Net Cash Provided by Operating Activities": [
        "Net Cash Provided by Operating Activities",
        "Cash from Operating Activities",
        "Operating Cash Flow",
        "Net Cash from Operating Activities",
    ],
    "Net Cash Used in Investing Activities": [
        "Net Cash Used in Investing Activities",
        "Cash from Investing Activities",
        "Investing Cash Flow",
        "Net Cash from Investing Activities",
    ],
    "Net Cash Provided by Financing Activities": [
        "Net Cash Provided by Financing Activities",
        "Cash from Financing Activities",
        "Financing Cash Flow",
        "Net Cash from Financing Activities",
    ],
    "Net Change in Cash": ["Net Change in Cash", "Change in Cash and Cash Equivalents"],
    "Capital Expenditure": ["Capital Expenditure", "CapEx", "Purchases of Property, Plant & Equipment"],
    "Depreciation and Amortization": ["Depreciation & Amortization", "D&A", "Depreciation", "Amortization"],
    "Free Cash Flow": ["Free Cash Flow", "FCF"],
    "Dividends Paid": ["Dividends Paid", "Dividends"],
    "Stock Based Compensation": ["Stock-Based Compensation", "Share-Based Compensation"],
    "Change in Working Capital": ["Change in Working Capital", "Working Capital Changes"],
    "Other Non-Cash Items": ["Other Non-Cash Items", "Non-Cash Adjustments"],
    # Add more mappings as necessary
}

# Refactored tag_line_item_indices function
def tag_line_item_indices(df, line_item_dict):
    """
    Tag line items in the DataFrame based on the line_item_dict.

    Args:
        df (pd.DataFrame): DataFrame containing a 'Category' column.
        line_item_dict (dict): Dictionary of standard line items and their aliases.

    Returns:
        pd.DataFrame: DataFrame with an additional 'Standardized Category' column.
    """
    if 'Category' not in df.columns:
        logger.warning("Column 'Category' not found in DataFrame.")
        return df

    # Handle NaN values in 'Category' column
    df['Category'] = df['Category'].fillna('Unknown')

    def match_line_item(item):
        if item == 'Unknown':
            return item
        match, score = process.extractOne(item, [key for key in line_item_dict.keys()])
        if score >= 80:
            return match
        return item

    df['Standardized Category'] = df['Category'].apply(match_line_item)
    return df

# Archiving files
def archive_files(source_dir, archive_dir):
    """
    Archives files in a source directory.
    """
    try:
        os.makedirs(archive_dir, exist_ok=True)
        for file in os.listdir(source_dir):
            file_path = os.path.join(source_dir, file)
            if os.path.isfile(file_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archived_file = f"{os.path.splitext(file)[0]}_{timestamp}.csv"
                os.rename(file_path, os.path.join(archive_dir, archived_file))
                logger.info(f"Archived: {file}")
    except Exception as e:
        logger.error(f"Error archiving files: {e}")
        
# Pruning old archives
def prune_archives(archive_dir, retention_days=30):
    """
    Deletes files older than `retention_days` in the archive directory.
    """
    try:
        if not os.path.exists(archive_dir):
            logger.warning(f"Archive directory does not exist: {archive_dir}")
            return

        cutoff_time = datetime.now() - timedelta(days=retention_days)
        for file in os.listdir(archive_dir):
            file_path = os.path.join(archive_dir, file)
            if os.path.isfile(file_path) and datetime.fromtimestamp(os.path.getmtime(file_path)) < cutoff_time:
                os.remove(file_path)
                logger.info(f"Pruned archive file: {file}")
    except Exception as e:
        logger.error(f"Error pruning archives: {e}")


```

---

## `scripts/utilities/dt.py`

```python
import os
import logging
import pandas as pd
from fuzzywuzzy import process
from datetime import datetime
from scripts.utilities.data_transformation_utils import (
    configure_logging,
    get_data_paths,
    tag_line_item_indices,
    line_item_dict,
)

# Configure logging
def configure_logging():
    logger = logging.getLogger("FinancialModeling")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = configure_logging()

def get_data_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    data_dir = os.path.join(project_root, "data")
    raw_data_dir = os.path.join(data_dir, "raw")
    processed_data_dir = os.path.join(data_dir, "processed")
    return raw_data_dir, processed_data_dir

def disable_scientific_notation():
    pd.options.display.float_format = "{:,.0f}".format

# Full expanded line item dictionary for fuzzy matching
line_item_dict = {
    "Revenue": ["Revenue", "Total Revenue", "Net Revenue", "Sales"],
    "Cost of Goods Sold": ["Cost of Goods Sold", "COGS", "Cost of Sales", "Cost of Revenue"],
    "Gross Profit": ["Gross Profit", "Gross Income", "Gross Margin"],
    "Operating Expenses": ["Operating Expenses", "OPEX", "Total Operating Expenses"],
    "Operating Income": ["Operating Income", "Operating Profit", "EBIT"],
    "Net Income": ["Net Income", "Net Profit", "Income After Tax", "Earnings"],
    "Research and Development": ["Research and Development", "R&D Expenses", "Research & Development"],
    "Selling General and Administrative": [
        "Selling General and Administrative",
        "SG&A",
        "Selling, General & Administrative",
    ],
    "Interest Expense": ["Interest Expense", "Finance Costs", "Interest and Other Expenses"],
    "Income Tax Expense": ["Income Tax Expense", "Taxes", "Provision for Income Taxes"],
    "Other Income/Expense": ["Other Income/Expense", "Other Income", "Other Expense"],
    "Total Operating Income": ["Total Operating Income", "Income from Operations"],
    "Total Assets": ["Total Assets", "Assets"],
    "Total Liabilities": ["Total Liabilities", "Liabilities"],
    "Total Equity": ["Total Equity", "Shareholders' Equity", "Stockholders' Equity"],
    "Cash and Cash Equivalents": ["Cash and Cash Equivalents", "Cash", "Cash Equivalents"],
    "Short-Term Investments": ["Short-Term Investments", "Marketable Securities"],
    "Accounts Receivable": ["Accounts Receivable", "Receivables", "Trade Receivables"],
    "Inventory": ["Inventory", "Inventories"],
    "Other Current Assets": ["Other Current Assets", "Prepaid Expenses"],
    "Long-Term Investments": ["Long-Term Investments", "Non-Current Investments"],
    "Property Plant and Equipment": ["Property, Plant & Equipment", "PP&E", "Fixed Assets"],
    "Goodwill": ["Goodwill"],
    "Intangible Assets": ["Intangible Assets", "Intangibles"],
    "Other Assets": ["Other Assets", "Miscellaneous Assets"],
    "Accounts Payable": ["Accounts Payable", "Payables", "Trade Payables"],
    "Short-Term Debt": ["Short-Term Debt", "Current Portion of Long-Term Debt"],
    "Other Current Liabilities": ["Other Current Liabilities", "Accrued Liabilities"],
    "Long-Term Debt": ["Long-Term Debt", "Non-Current Debt"],
    "Deferred Tax Liabilities": ["Deferred Tax Liabilities", "DTL"],
    "Deferred Tax Assets": ["Deferred Tax Assets", "DTA"],
    "Other Liabilities": ["Other Liabilities", "Miscellaneous Liabilities"],
    "Common Stock": ["Common Stock", "Ordinary Shares"],
    "Retained Earnings": ["Retained Earnings", "Accumulated Earnings"],
    "Accumulated Other Comprehensive Income": [
        "Accumulated Other Comprehensive Income",
        "AOCI",
    ],
    "Treasury Stock": ["Treasury Stock", "Treasury Shares"],
    "Allowance for Doubtful Accounts": [
        "Allowance for Doubtful Accounts",
        "Bad Debt Allowance",
        "Provision for Credit Losses",
    ],
    "Net Cash Provided by Operating Activities": [
        "Net Cash Provided by Operating Activities",
        "Cash from Operating Activities",
        "Operating Cash Flow",
        "Net Cash from Operating Activities",
    ],
    "Net Cash Used in Investing Activities": [
        "Net Cash Used in Investing Activities",
        "Cash from Investing Activities",
        "Investing Cash Flow",
        "Net Cash from Investing Activities",
    ],
    "Net Cash Provided by Financing Activities": [
        "Net Cash Provided by Financing Activities",
        "Cash from Financing Activities",
        "Financing Cash Flow",
        "Net Cash from Financing Activities",
    ],
    "Net Change in Cash": ["Net Change in Cash", "Change in Cash and Cash Equivalents"],
    "Capital Expenditure": ["Capital Expenditure", "CapEx", "Purchases of Property, Plant & Equipment"],
    "Depreciation and Amortization": ["Depreciation & Amortization", "D&A", "Depreciation", "Amortization"],
    "Free Cash Flow": ["Free Cash Flow", "FCF"],
    "Dividends Paid": ["Dividends Paid", "Dividends"],
    "Stock Based Compensation": ["Stock-Based Compensation", "Share-Based Compensation"],
    "Change in Working Capital": ["Change in Working Capital", "Working Capital Changes"],
    "Other Non-Cash Items": ["Other Non-Cash Items", "Non-Cash Adjustments"],
    # Add more as needed
}

def tag_line_item_indices(dataframe, dictionary):
    """Apply mapping to line items using fuzzy matching."""
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")

    def map_item(item):
        
        if not isinstance(item, str):
            return item
        # Find the best match from the dictionary
        matches = [(key, process.extractOne(item, dictionary[key])) for key in dictionary]
        best_match, (best_item, score) = max(matches, key=lambda x: x[1][1])
        return best_match if score >= 80 else item  # Threshold is 80

    # Check for the "Category" column
    if "Category" in dataframe.columns:
        dataframe["Category"] = dataframe["Category"].apply(map_item)
    else:
        raise KeyError("Column 'Category' not found in the DataFrame.")
    return dataframe```

---

## `scripts/utilities/dynamic_assumptions.py`

```python
import pandas as pd
import os
import logging
from scripts.utilities.data_transformation_utils import get_data_paths, line_item_dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_baselines(tagged_data_dir):
    """
    Calculate baselines for all tagged financial statements.
    """
    baselines = {}

    # Load tagged data
    for file_name in ["tagged_balance_sheet.csv", "tagged_income_statement.csv", "tagged_cash_flow.csv"]:
        file_path = os.path.join(tagged_data_dir, file_name)
        if os.path.exists(file_path):
            logger.info(f"Processing file: {file_name}")
            data = pd.read_csv(file_path, index_col=0)

            # Calculate baselines for numeric columns
            for column in data.columns:
                try:
                    if data[column].dtype in ['float64', 'int64']:
                        baseline_value = data[column].mean()
                        baselines[column] = baseline_value
                except Exception as e:
                    logger.error(f"Error calculating baseline for column {column}: {e}")

    return baselines

def generate_scenarios(baselines, thresholds):
    """
    Generate weak, base, and strong scenarios based on baselines and thresholds.
    """
    scenarios = []
    for metric, baseline_value in baselines.items():
        threshold = thresholds.get(metric, 0.05)  # Default threshold of 5% if not specified
        scenarios.append({
            "Metric": metric,
            "Weak": baseline_value * (1 - threshold),
            "Base": baseline_value,
            "Strong": baseline_value * (1 + threshold)
        })
    return pd.DataFrame(scenarios)

def save_scenarios(scenarios):
    """
    Save generated scenarios to CSV.
    """
    output_file = "./data/outputs/dynamic_scenarios.csv"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    scenarios.to_csv(output_file, index=False)
    logger.info(f"Scenarios saved to {output_file}")

def main():
    """
    Main function to calculate baselines and generate scenarios.
    """
    _, tagged_data_dir = get_data_paths()

    # Step 1: Calculate baselines
    baselines = calculate_baselines(tagged_data_dir)
    logger.info(f"Baselines calculated: {baselines}")

    # Step 2: Generate scenarios
    thresholds = {
        "Revenue Growth Rate": 0.02,
        "COGS % Revenue": 0.05,
        "CapEx Growth Rate": 0.01
    }
    scenarios = generate_scenarios(baselines, thresholds)

    # Step 3: Save scenarios
    save_scenarios(scenarios)

if __name__ == "__main__":
    main()
```

---

## `scripts/utilities/new_data_transformation_utils.py`

```python
import os
import logging
import pandas as pd
from fuzzywuzzy import process

logger = logging.getLogger("FinancialModeling")
logger.setLevel(logging.INFO)

# Configure logging
def configure_logging():
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

# Get data paths
def get_data_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    data_dir = os.path.join(project_root, "data")
    raw_data_dir = os.path.join(data_dir, "raw")
    processed_data_dir = os.path.join(data_dir, "processed")
    return raw_data_dir, processed_data_dir

# Line item dictionary for tagging
line_item_dict = {
    "Revenue": ["Revenue", "Total Revenue", "Net Revenue", "Sales"],
    "Cost of Goods Sold": ["Cost of Goods Sold", "COGS", "Cost of Sales", "Cost of Revenue"],
    "Gross Profit": ["Gross Profit", "Gross Income", "Gross Margin"],
    "Operating Expenses": ["Operating Expenses", "OPEX", "Total Operating Expenses"],
    "Operating Income": ["Operating Income", "Operating Profit", "EBIT"],
    "Net Income": ["Net Income", "Net Profit", "Income After Tax", "Earnings"],
    "Research and Development": ["Research and Development", "R&D Expenses", "Research & Development"],
    "Selling General and Administrative": [
        "Selling General and Administrative",
        "SG&A",
        "Selling, General & Administrative",
    ],
    "Interest Expense": ["Interest Expense", "Finance Costs", "Interest and Other Expenses"],
    "Income Tax Expense": ["Income Tax Expense", "Taxes", "Provision for Income Taxes"],
    "Other Income/Expense": ["Other Income/Expense", "Other Income", "Other Expense"],
    "Total Operating Income": ["Total Operating Income", "Income from Operations"],
    "Total Assets": ["Total Assets", "Assets"],
    "Total Liabilities": ["Total Liabilities", "Liabilities"],
    "Total Equity": ["Total Equity", "Shareholders' Equity", "Stockholders' Equity"],
    "Cash and Cash Equivalents": ["Cash and Cash Equivalents", "Cash", "Cash Equivalents"],
    "Short-Term Investments": ["Short-Term Investments", "Marketable Securities"],
    "Accounts Receivable": ["Accounts Receivable", "Receivables", "Trade Receivables"],
    "Inventory": ["Inventory", "Inventories"],
    "Other Current Assets": ["Other Current Assets", "Prepaid Expenses"],
    "Long-Term Investments": ["Long-Term Investments", "Non-Current Investments"],
    "Property Plant and Equipment": ["Property, Plant & Equipment", "PP&E", "Fixed Assets"],
    "Goodwill": ["Goodwill"],
    "Intangible Assets": ["Intangible Assets", "Intangibles"],
    "Other Assets": ["Other Assets", "Miscellaneous Assets"],
    "Accounts Payable": ["Accounts Payable", "Payables", "Trade Payables"],
    "Short-Term Debt": ["Short-Term Debt", "Current Portion of Long-Term Debt"],
    "Other Current Liabilities": ["Other Current Liabilities", "Accrued Liabilities"],
    "Long-Term Debt": ["Long-Term Debt", "Non-Current Debt"],
    "Deferred Tax Liabilities": ["Deferred Tax Liabilities", "DTL"],
    "Deferred Tax Assets": ["Deferred Tax Assets", "DTA"],
    "Other Liabilities": ["Other Liabilities", "Miscellaneous Liabilities"],
    "Common Stock": ["Common Stock", "Ordinary Shares"],
    "Retained Earnings": ["Retained Earnings", "Accumulated Earnings"],
    "Accumulated Other Comprehensive Income": [
        "Accumulated Other Comprehensive Income",
        "AOCI",
    ],
    "Treasury Stock": ["Treasury Stock", "Treasury Shares"],
    "Allowance for Doubtful Accounts": [
        "Allowance for Doubtful Accounts",
        "Bad Debt Allowance",
        "Provision for Credit Losses",
    ],
    "Net Cash Provided by Operating Activities": [
        "Net Cash Provided by Operating Activities",
        "Cash from Operating Activities",
        "Operating Cash Flow",
        "Net Cash from Operating Activities",
    ],
    "Net Cash Used in Investing Activities": [
        "Net Cash Used in Investing Activities",
        "Cash from Investing Activities",
        "Investing Cash Flow",
        "Net Cash from Investing Activities",
    ],
    "Net Cash Provided by Financing Activities": [
        "Net Cash Provided by Financing Activities",
        "Cash from Financing Activities",
        "Financing Cash Flow",
        "Net Cash from Financing Activities",
    ],
    "Net Change in Cash": ["Net Change in Cash", "Change in Cash and Cash Equivalents"],
    "Capital Expenditure": ["Capital Expenditure", "CapEx", "Purchases of Property, Plant & Equipment"],
    "Depreciation and Amortization": ["Depreciation & Amortization", "D&A", "Depreciation", "Amortization"],
    "Free Cash Flow": ["Free Cash Flow", "FCF"],
    "Dividends Paid": ["Dividends Paid", "Dividends"],
    "Stock Based Compensation": ["Stock-Based Compensation", "Share-Based Compensation"],
    "Change in Working Capital": ["Change in Working Capital", "Working Capital Changes"],
    "Other Non-Cash Items": ["Other Non-Cash Items", "Non-Cash Adjustments"],
    # Add more mappings as necessary
}

# Tagging function
def tag_line_item_indices(dataframe: pd.DataFrame, dictionary: dict) -> pd.DataFrame:
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")

    if "Category" not in dataframe.columns:
        raise KeyError("Column 'Category' not found in the DataFrame.")

    def map_item(item: str):
        if not isinstance(item, str):
            return item
        matches = [(key, process.extractOne(item, dictionary[key])) for key in dictionary]
        best_match, (best_item, score) = max(matches, key=lambda x: x[1][1])
        return best_match if score >= 80 else item

    dataframe["Category"] = dataframe["Category"].apply(map_item)
    return dataframe

# Archiving files
def archive_files(source_dir, archive_dir):
    """
    Archives files in a source directory.
    """
    try:
        os.makedirs(archive_dir, exist_ok=True)
        for file in os.listdir(source_dir):
            file_path = os.path.join(source_dir, file)
            if os.path.isfile(file_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archived_file = f"{os.path.splitext(file)[0]}_{timestamp}.csv"
                os.rename(file_path, os.path.join(archive_dir, archived_file))
                logger.info(f"Archived: {file}")
    except Exception as e:
        logger.error(f"Error archiving files: {e}")

# Pruning old archives
def prune_archives(archive_dir, retention_days=30):
    """
    Deletes files older than `retention_days` in the archive directory.
    """
    try:
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        for file in os.listdir(archive_dir):
            file_path = os.path.join(archive_dir, file)
            if os.path.isfile(file_path) and datetime.fromtimestamp(os.path.getmtime(file_path)) < cutoff_time:
                os.remove(file_path)
                logger.info(f"Pruned archive file: {file}")
    except Exception as e:
        logger.error(f"Error pruning archives: {e}")
```

---

## `scripts/utilities/path_setup.py`

```python
# scripts/utilities/path_setup.py

import sys
import os

def setup_project_paths():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    return project_root
```

---

## `scripts/utilities/samplevalidation.py`

```python
import pandas as pd

# Define paths to tagged files
processed_dir = './data/processed'
files = ['tagged_balance_sheet.csv', 'tagged_income_statement.csv', 'tagged_cash_flow.csv']

# Load and inspect each file
for file in files:
    file_path = f"{processed_dir}/{file}"
    try:
        df = pd.read_csv(file_path)
        print(f"Preview of {file}:")
        print(df.head())
        print("\nColumn Names:", df.columns.tolist())
    except Exception as e:
        print(f"Error loading {file}: {e}")
```

---

## `skills/vie-consolidation-analysis/SKILL.md`

```markdown
---
name: vie-consolidation-analysis
description: >
  Analyzes Variable Interest Entity (VIE) consolidation requirements, focusing on principal-agent relationships, financial restatement complexities, and regulatory compliance (PCAOB, SEC, CFTC). Use for: evaluating consolidation mandates, assessing financial reporting risks, and understanding the ramifications of non-compliance in complex business structures like loyalty programs.
license: Complete terms in LICENSE.txt
---

# VIE Consolidation Analysis Skill

This skill provides a structured approach to analyzing Variable Interest Entity (VIE) consolidation, particularly in scenarios involving principal-agent relationships and significant financial reporting implications.

## Core Functionality

This skill helps in:

1.  **Identifying Principal-Agent Relationships**: Evaluates the control elements (manifestation, consent, control) to determine if an agency relationship exists, which can trigger VIE consolidation.
2.  **Assessing VIE Consolidation Mandates**: Applies ASC 810 criteria, including the power and economics tests, to determine if consolidation is required.
3.  **Analyzing Financial Restatement Complexities**: Examines the logistical and technical challenges of restating financial statements, especially for large customer bases and complex revenue recognition scenarios (e.g., ASC 606 for loyalty programs).
4.  **Evaluating Regulatory Compliance**: Identifies potential violations of regulatory frameworks such as PCAOB, SEC, CFTC, IRC §6041 (1099-MISC), and consumer protection laws (e.g., MCPA, Magnuson-Moss Warranty Act).

## Usage Guidelines

To effectively use this skill, provide detailed information regarding:

-   The relationship between the entities in question (e.g., contracts, operational agreements).
-   Financial data, including revenue recognition policies and loyalty program mechanics.
-   Relevant legal and regulatory context.

## Deployment to Agents and Sub-Agents

This skill is designed to be deployed to other agents and sub-agents for wide research and specialized analysis. The core logic can be integrated into their workflows to ensure consistent and authoritative evaluation of VIE consolidation issues.

To deploy this skill, the `SKILL.md` file, along with any supporting scripts or reference materials, should be made available to the target agents. The `github-gem-seeker` skill can be used to manage and distribute such analytical tools within a GitHub repository, ensuring that all agents have access to the latest version of the analysis framework.

### Example Deployment Steps (Conceptual):

1.  **Commit Skill to GitHub**: Ensure this `vie-consolidation-analysis` skill directory is committed to a designated GitHub repository (e.g., `FinancialModeling_Project`).
2.  **Agent Integration**: Other agents or sub-agents can then clone or pull updates from this repository.
3.  **Execution**: Agents can invoke the analytical components of this skill (e.g., Python scripts for specific calculations or data processing) as part of their research workflow.

## Bundled Resources

-   `scripts/`: Contains Python scripts for data analysis, regulatory checks, or financial modeling related to VIEs.
    -   `execute_research.py`: Orchestrates the parallel research for VIE consolidation analysis.
-   `references/`: Includes detailed documentation on ASC 810, relevant SEC/PCAOB guidance, and legal precedents.
-   `templates/`: Provides templates for structured output reports or compliance checklists.
```

---

## `skills/vie-consolidation-analysis/references/api_reference.md`

```markdown
# Reference Documentation for Vie Consolidation Analysis

This is a placeholder for detailed reference documentation.
Replace with actual reference content or delete if not needed.

Example real reference docs from other skills:
- product-management/references/communication.md - Comprehensive guide for status updates
- product-management/references/context_building.md - Deep-dive on gathering context
- bigquery/references/ - API references and query examples

## When Reference Docs Are Useful

Reference docs are ideal for:
- Comprehensive API documentation
- Detailed workflow guides
- Complex multi-step processes
- Information too lengthy for main SKILL.md
- Content that's only needed for specific use cases

## Structure Suggestions

### API Reference Example
- Overview
- Authentication
- Endpoints with examples
- Error codes
- Rate limits

### Workflow Guide Example
- Prerequisites
- Step-by-step instructions
- Common patterns
- Troubleshooting
- Best practices
```

---

## `skills/vie-consolidation-analysis/scripts/example.py`

```python
#!/usr/bin/env python3
"""
Example helper script for vie-consolidation-analysis

This is a placeholder script that can be executed directly.
Replace with actual implementation or delete if not needed.

Example real scripts from other skills:
- pdf/scripts/fill_fillable_fields.py - Fills PDF form fields
- pdf/scripts/convert_pdf_to_images.py - Converts PDF pages to images
"""

def main():
    print("This is an example script for vie-consolidation-analysis")
    # TODO: Add actual script logic here
    # This could be data processing, file conversion, API calls, etc.

if __name__ == "__main__":
    main()
```

---

## `skills/vie-consolidation-analysis/scripts/execute_research.py`

```python
import json
import subprocess
import os

def run_research_task(topic):
    print(f"Starting research for: {topic["title"]}")
    # In a real scenario, this would involve dispatching tasks to sub-agents
    # or using specialized tools for deep research on each topic.
    # For this simulation, we'll just return a placeholder.
    return topic["id"], f"Research content for {topic["id"]}"

def main():
    # First, generate the research topics using research_vie.py
    subprocess.run(["python3", "research_vie.py"], cwd=os.path.dirname(os.path.abspath(__file__)))

    # Then, load the generated topics
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "research_topics.json"), "r") as f:
        topics = json.load(f)

    results = {}
    # Simulate parallel execution
    for topic in topics:
        topic_id, content = run_research_task(topic)
        results[topic_id] = content

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "research_results.json"), "w") as f:
        json.dump(results, f, indent=4)
    print("Parallel research simulation completed.")

if __name__ == "__main__":
    main()
```

---

## `skills/vie-consolidation-analysis/templates/example_template.txt`

```text
# Example Template File

This placeholder represents where template files would be stored.
Replace with actual template files (templates, images, fonts, etc.) or delete if not needed.

Template files are NOT intended to be loaded into context, but rather used within
the output Manus produces.

Example template files from other skills:
- Brand guidelines: logo.png, slides_template.pptx
- Frontend builder: hello-world/ directory with HTML/React boilerplate
- Typography: custom-font.ttf, font-family.woff2
- Data: sample_data.csv, test_dataset.json

## Common Template Types

- Templates: .pptx, .docx, boilerplate directories
- Images: .png, .jpg, .svg, .gif
- Fonts: .ttf, .otf, .woff, .woff2
- Boilerplate code: Project directories, starter files
- Icons: .ico, .svg
- Data files: .csv, .json, .xml, .yaml

Note: This is a text placeholder. Actual templates can be any file type.
```

---

## Notebooks (source cells)

### `notebooks/data_exploration.ipynb`

```python
# --- CODE ---
import sys
import os

# Dynamically add the project root to sys.path
current_dir = os.getcwd()  # The directory where the notebook is located (notebooks/)
project_root = os.path.abspath(os.path.join(current_dir, '..'))  # Move up to the project root
if project_root not in sys.path:
    sys.path.append(project_root)
    
# Optional: Debugging to confirm paths
print(f"Current Directory: {current_dir}")
print(f"Project Root: {project_root}")
print(f"sys.path: {sys.path}")

import pandas as pd


# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)
df.columns.values[0] = 'Year'

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (alphabetically)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Step 6: Diagnostic display before sorting
print("Step 6 - Diagnostic: DataFrame before sorting:")
display(df_transposed.head())

# Step 7: Sort the DataFrame by 'Sort' column in ascending order
df_transposed_sorted = df_transposed.sort_values(by='Sort', ascending=True)

# Diagnostic Display after sorting
print("Step 7 - Diagnostic: DataFrame after sorting:")
display(df_transposed_sorted.head())

# **Step 8: Clean up the DataFrame**

# Create a copy of the sorted DataFrame
df_final = df_transposed_sorted.copy()

# Drop the 'Sort' column as it's no longer needed
df_final.drop(columns=['Sort'], inplace=True)

# Assign a name to the index
df_final.index.name = 'Category'  # Set index name to 'Category'

# Final Diagnostic Display
print("Final DataFrame:")
display(df_final)

# Step 9: Save the final DataFrame to a CSV file
output_file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/processed/complete_balance_sheet.csv'
df_final.to_csv(output_file_path, index=True)  # Set index=True to keep the 'Category' index


# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

def main():
    # Step 1: Load the data
    file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
    df = pd.read_csv(file_path)

    # Step 2: Identify the first column (which has a blank header)
    first_column_name = df.columns[0]

    # Step 3: Sort data by the first column in ascending order (alphabetically)
    df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

    # Step 4: Transpose the sorted DataFrame
    df_transposed = df.set_index(first_column_name).T

    # Step 5: Add a helper column with incremental values for sorting
    df_transposed['Sort'] = range(len(df_transposed), 0, -1)

    # Diagnostic Display to check the structure after adding 'Sort'
    print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
    print(df_transposed.head())

    # Step 6: Diagnostic display before sorting
    print("\nStep 6 - Diagnostic: DataFrame before sorting:")
    print(df_transposed.head())

    # Step 7: Sort the DataFrame by 'Sort' column in ascending order
    df_transposed_sorted = df_transposed.sort_values(by='Sort', ascending=True)

    # Diagnostic Display after sorting
    print("\nStep 7 - Diagnostic: DataFrame after sorting:")
    print(df_transposed_sorted.head())

    # **Step 8: Clean up the DataFrame**

    # Create a copy of the sorted DataFrame
    df_final = df_transposed_sorted.copy()

    # Drop the 'Sort' column as it's no longer needed
    df_final.drop(columns=['Sort'], inplace=True)

    # Assign a name to the index
    df_final.index.name = 'Category'  # Set index name to 'Category'

    # Final Diagnostic Display
    print("\nFinal DataFrame:")
    print(df_final.head())

    # Step 9: Save the final DataFrame to a CSV file
    output_file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/processed/complete_balance_sheet.csv'
    df_final.to_csv(output_file_path, index=True)  # Set index=True to keep the 'Category' index

if __name__ == "__main__":
    main()


# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (alphabetically)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Step 6: Diagnostic display before sorting
print("Step 6 - Diagnostic: DataFrame before sorting:")
display(df_transposed.head())

# Step 7: Sort the DataFrame by 'Sort' column in ascending order
df_transposed_sorted = df_transposed.sort_values(by='Sort', ascending=True)

# Diagnostic Display after sorting
print("Step 7 - Diagnostic: DataFrame after sorting:")
display(df_transposed_sorted.head())

# **Step 8: Clean up the DataFrame and Transpose Back**

# Drop the 'Sort' column as it's no longer needed
df_transposed_sorted.drop(columns=['Sort'], inplace=True)

# **Transpose back to have financial categories as index**
df_final = df_transposed_sorted.T

# **Assign a name to the index**
df_final.index.name = 'Category'  # Set index name to 'Category'

# Final Diagnostic Display
print("Final DataFrame:")
display(df_final)

# Step 9: Save the final DataFrame to a CSV file
output_file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/processed/complete_balance_sheet.csv'
df_final.to_csv(output_file_path, index=True)  # Set index=True to keep the 'Category' index


# --- CODE ---
import pandas as pd
from tabulate import tabulate
import os

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

def transform_financial_statement(statement_type):
    # Define file paths
    input_file = f'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/{statement_type}.csv'
    output_file = f'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/processed/processed_{statement_type}.csv'

    # Step 1: Load the data
    df = pd.read_csv(input_file)

    # Step 2: Identify the first column (which has a blank header)
    first_column_name = df.columns[0]

    # Step 3: Sort data by the first column in ascending order (alphabetically)
    df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

    # Step 4: Transpose the sorted DataFrame
    df_transposed = df.set_index(first_column_name).T

    # Step 5: Add a helper column with incremental values for sorting
    df_transposed['Sort'] = range(len(df_transposed), 0, -1)

    # Diagnostic Display to check the structure after adding 'Sort'
    print(f"{statement_type.title()} - Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
    print(tabulate(df_transposed.head(), headers='keys', tablefmt='psql'))

    # Step 6: Diagnostic display before sorting
    print(f"\n{statement_type.title()} - Step 6 - Diagnostic: DataFrame before sorting:")
    print(tabulate(df_transposed.head(), headers='keys', tablefmt='psql'))

    # Step 7: Sort the DataFrame by 'Sort' column in ascending order
    df_transposed_sorted = df_transposed.sort_values(by='Sort', ascending=True)

    # Diagnostic Display after sorting
    print(f"\n{statement_type.title()} - Step 7 - Diagnostic: DataFrame after sorting:")
    print(tabulate(df_transposed_sorted.head(), headers='keys', tablefmt='psql'))

    # **Step 8: Clean up the DataFrame**

    # Create a copy of the sorted DataFrame
    df_final = df_transposed_sorted.copy()

    # Drop the 'Sort' column as it's no longer needed
    df_final.drop(columns=['Sort'], inplace=True)

    # Assign a name to the index
    df_final.index.name = 'Category'  # Set index name to 'Category'

    # Final Diagnostic Display
    print(f"\n{statement_type.title()} - Final DataFrame:")
    print(tabulate(df_final.head(), headers='keys', tablefmt='psql'))

    # Step 9: Save the final DataFrame to a CSV file
    df_final.to_csv(output_file, index=True)  # Set index=True to keep the 'Category' index

    print(f"\n{statement_type.title()} transformation completed. Output saved to {output_file}")

if __name__ == "__main__":
    # List of financial statements to process
    statements = ['balance_sheet', 'income_statement', 'cash_flow']

    for statement in statements:
        transform_financial_statement(statement)


# --- CODE ---
# Step 2: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# --- CODE ---
# Step 3: Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T

# --- CODE ---
# Step 4: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(1, len(df_transposed) + 1)

# --- CODE ---
# Step 5: Reorder the columns to place 'Sort' at the beginning if needed
cols = ['Sort'] + [col for col in df_transposed.columns if col != 'Sort']
df_final = df_transposed[cols]

# --- CODE ---
# Step 6: Sort by 'Sort' column in descending order and reset the index
df_final = df_final.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# --- CODE ---
# Step 7: Remove the 'Sort' column from the final display
df_final = df_final.drop(columns=['Sort'])

# Display final DataFrame
display(df_final)  # Use 'display' in Jupyter; use 'print' in other environments

# --- CODE ---
import pandas as pd


# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)
df.columns.values[0] = 'Year'

# Step 2: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 3: Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T

# Step 4: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(1, len(df_transposed) + 1)

# Step 5: Reorder the columns to place 'Sort' at the beginning if needed
cols = ['Sort'] + [col for col in df_transposed.columns if col != 'Sort']
df_final = df_transposed[cols]

# Step 6: Sort by 'Sort' column in descending order and reset the index
df_final = df_final.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Step 7: Remove the 'Sort' column from the final display
df_final = df_final.drop(columns=['Sort'])

# Display final DataFrame
display(df_final)  # Use 'display' in Jupyter; use 'print' in other environments

# --- CODE ---
import pandas as pd

# Define the file path
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'  # Replace with your actual file path
df = pd.read_csv(file_path)

# Step 1: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 2: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 3: Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T  # Set 'Year' as index and transpose



# --- CODE ---
# Step 4: Add a helper column after transposing for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)  # Add descending incremental numbers for Sort

# Reorder the columns to place 'Sort' at the beginning if needed
cols = ['Sort'] + [col for col in df_transposed.columns if col != 'Sort']
df_final = df_transposed[cols]  # Reorder columns with 'Sort' as the first column


# --- CODE ---
# Step 5: Format all numeric values to avoid scientific notation
pd.options.display.float_format = '{:,.0f}'.format  # Format numbers with comma and no decimal places

# Step 6: Sort by the helper column 'Sort' in descending order
df_final = df_final.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Display the final DataFrame
display(df_final)


# --- CODE ---
import pandas as pd

# Define the file path
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'  # Replace with your actual file path
df = pd.read_csv(file_path)

# Step 1: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 2: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 3: Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T  # Set 'Year' as index and transpose

# Step 4: Add a helper column after transposing for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)  # Add descending incremental numbers for Sort

# Reorder the columns to place 'Sort' at the beginning if needed
cols = ['Sort'] + [col for col in df_transposed.columns if col != 'Sort']
df_final = df_transposed[cols]  # Reorder columns with 'Sort' as the first column

# Step 5: Format all numeric values to avoid scientific notation
pd.options.display.float_format = '{:,.0f}'.format  # Format numbers with comma and no decimal places

# Step 6: Sort by the helper column 'Sort' in descending order
df_final = df_final.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Display the final DataFrame
display(df_final)



# --- CODE ---
import pandas as pd

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 2: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 3: Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T  # Set 'Year' as index and transpose

# Step 4: Add a helper column 'Sort' at the end with descending values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Step 5: Diagnostic Step - Display the transposed DataFrame to verify structure
display(df_transposed)  # Check here to ensure all financial statement line items are intact

# --- CODE ---
# Step 6: Sort by 'Sort' column in descending order
df_final = df_transposed.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Step 7: Remove the 'Sort' column
df_final = df_final.drop(columns=['Sort'])

# Step 8: Display the final DataFrame
display(df_final)  # Final check to ensure output is as expected

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# --- CODE ---
# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 2: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 3: Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T  # Set 'Year' as index and transpose
print("Step 3 - Transposed DataFrame:")
display(df_transposed.head())  # Display to verify that financial statement line items are intact

# --- CODE ---
# Step 4: Add a helper column 'Sort' with descending values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)  # Add Sort as descending numbers at the end
print("Step 4 - Added 'Sort' column:")
display(df_transposed.head())  # Verify 'Sort' column has been added correctly

# --- CODE ---
# Step 5: Reorder columns to place 'Sort' at the start
cols = ['Sort'] + [col for col in df_transposed.columns if col != 'Sort']
df_final = df_transposed[cols]  # Reorder columns with 'Sort' at the beginning
print("Step 5 - Reordered columns with 'Sort' at the start:")
display(df_final.head())  # Check reordering

# --- CODE ---
# Step 6: Sort by 'Sort' column in descending order and reset the index
df_final = df_final.sort_values(by='Sort', ascending=False).reset_index(drop=True)
print("Step 6 - Sorted by 'Sort' in descending order:")
display(df_final.head())  # Check sorting order


# --- CODE ---
import pandas as pd

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 2: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 3: Transpose the sorted DataFrame, with 'Year' as index
df_transposed = df.set_index('Year').T  # Set 'Year' as index and transpose

# Step 4: Add a helper column 'Sort' at the end with descending values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Step 5: Diagnostic Step - Display 'df_transposed' to ensure all financial statement labels are intact
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' added")
display(df_transposed.head())


# --- CODE ---
# Step 6: Reorder the columns to place 'Sort' at the beginning if needed
cols = ['Sort'] + [col for col in df_transposed.columns if col != 'Sort']
df_final = df_transposed[cols]

print("Step 6 - Reordered columns with 'Sort' at the start")
display(df_final.head())  # Check if 'Sort' is the first column and labels are intact


# --- CODE ---
# Step 7: Sort by 'Sort' column in descending order and reset the index
df_final = df_final.sort_values(by='Sort', ascending=False).reset_index(drop=True)
print("Step 7 - Sorted by 'Sort' in descending order")
display(df_final.head())


# --- CODE ---
import pandas as pd

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 2: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 3: Transpose the sorted DataFrame, with 'Year' as index
df_transposed = df.set_index('Year').T  # Set 'Year' as index and transpose

# Step 4: Add a helper column 'Sort' at the end with descending values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Step 5: Diagnostic Step - Display 'df_transposed' to ensure all financial statement labels are intact
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' added")
display(df_transposed.head())

# Step 6: Use Data Wrangler to manipulate the DataFrame
dw_df = dw.DataFrame(df_transposed)
dw_df


# --- CODE ---
# Step 6: Reorder the columns to place 'Sort' at the beginning if needed
cols = ['Sort'] + [col for col in df_transposed.columns if col != 'Sort']
df_final = df_transposed[cols]

print("Step 6 - Reordered columns with 'Sort' at the start")
display(df_final.head())  # Check if 'Sort' is the first column and labels are intact


# --- CODE ---
import pandas as pd

# Load your data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T

# Add a helper 'Sort' column at the end with descending numbers
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Add a secondary helper column 'ID' to uniquely identify rows (avoids potential drops)
df_transposed['ID'] = range(1, len(df_transposed) + 1)

# Diagnostic Step: Check DataFrame after adding helper columns
print("After adding 'Sort' and 'ID' columns:")
display(df_transposed.head())

# --- CODE ---
# Sort by the 'Sort' column in descending order, with 'ID' column as backup for structure
df_final = df_transposed.sort_values(by=['Sort', 'ID'], ascending=[False, True]).reset_index(drop=True)

# Remove the 'Sort' and 'ID' columns after sorting if they are no longer needed
df_final = df_final.drop(columns=['Sort', 'ID'])

# Final display of the DataFrame to confirm result
print("Final sorted DataFrame without helper columns:")
display(df_final)

# --- CODE ---
import pandas as pd

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 3: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame, making 'Year' the index temporarily
df_transposed = df.set_index('Year').T

# Step 5: Add helper columns at the end
# 'Sort' with descending order, and 'ID' as a unique identifier
df_transposed['Sort'] = range(len(df_transposed), 0, -1)
df_transposed['ID'] = range(1, len(df_transposed) + 1)

# Step 6: Diagnostic Checkpoint
print("Diagnostic: Transposed DataFrame with 'Sort' and 'ID' columns added:")
display(df_transposed.head())  # Check the structure at this stage

# --- CODE ---
# Step 7: Sort by the 'Sort' column (descending) and 'ID' (ascending) to maintain structure
df_final = df_transposed.sort_values(by=['Sort', 'ID'], ascending=[False, True]).reset_index(drop=True)

# Step 8: Remove helper columns after sorting if they are no longer needed
df_final = df_final.drop(columns=['Sort', 'ID'])

# Final Diagnostic to confirm structure and data integrity
print("Final sorted DataFrame without helper columns:")
display(df_final)

# --- CODE ---
import pandas as pd

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 3: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame, making 'Year' the index temporarily
df_transposed = df.set_index('Year').T

# Step 5: Add helper columns
# 'Sort' in descending order for sorting and 'ID' to uniquely identify rows
# Both columns will start with the number of rows in the DataFrame and decrement
df_transposed['Sort'] = range(len(df_transposed), 0, -1)
df_transposed['ID'] = range(len(df_transposed), 0, -1)

# Diagnostic Checkpoint: Display after adding helper columns
print("Diagnostic - Transposed DataFrame with 'Sort' and 'ID' columns:")
display(df_transposed.head())

# Step 6: Sort by the 'Sort' column (descending) and 'ID' for stable sorting
df_final = df_transposed.sort_values(by=['Sort', 'ID'], ascending=[False, True]).reset_index(drop=True)

# Step 7: Remove helper columns
df_final = df_final.drop(columns=['Sort', 'ID'])

# Final Diagnostic: Confirm data integrity and structure
print("Final sorted DataFrame without helper columns:")
display(df_final)


# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 3: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame, making 'Year' the index temporarily
df_transposed = df.set_index('Year').T

# Step 5: Add a helper 'Sort' column in descending order and keep original index as a separate column
df_transposed['Sort'] = range(len(df_transposed), 0, -1)
df_transposed['Original_Index'] = df_transposed.index  # Adding the original index as a separate column

# Diagnostic Step: Display the DataFrame to verify the changes after adding 'Sort' and 'Original_Index'
print("Diagnostic - Transposed DataFrame with 'Sort' and 'Original_Index' columns added:")
display(df_transposed.head())  # Display the first few rows to check structure

# --- CODE ---
# Step 6: Sort by the 'Sort' column in descending order
df_final = df_transposed.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Step 7: Remove the 'Sort' column after sorting if it's no longer needed
df_final = df_final.drop(columns=['Sort'])

# Final Diagnostic: Confirm structure and data integrity without the 'Sort' column
print("Final sorted DataFrame without 'Sort' column:")
display(df_final.head())  # Display the first few rows of the final result to verify

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 3: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 4: Transpose the DataFrame and add helper columns
df_transposed = df.set_index('Year').T.reset_index()  # Resetting index to make 'index' a column

# Step 5: Add 'Sort' column in descending order, and keep 'index' as a column for financial items
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic: Check the structure after adding 'Sort' and flattening the structure
print("Step 5 - Diagnostic Check after adding 'Sort':")
display(df_transposed.head())

# --- CODE ---
# Step 6: Sort by 'Sort' column in descending order
df_sorted = df_transposed.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Display the sorted DataFrame
print("Step 6 - Sorted by 'Sort' in descending order:")
display(df_sorted)  # Corrected display statement


# --- CODE ---
import pandas as pd

# Disable scientific notation for readability
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 3: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame and make 'Year' the index temporarily
df_transposed = df.set_index('Year').T

# Step 5: Add a helper 'Sort' column at the end with descending numbers
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Step: Display DataFrame after transposing and adding 'Sort' to confirm layout
print("Diagnostic Step: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Step 6: Sort the entire DataFrame by 'Sort' column in descending order
# Confirm that this operation is sorting all rows across all columns, not just the 'Sort' column
df_sorted = df_transposed.sort_values(by='Sort', ascending=False).reset_index()

# Final Diagnostic: Confirm structure and sorting across all columns
print("Final sorted DataFrame by 'Sort' across all columns:")
display(df_sorted)

# Save sorted DataFrame to CSV
output_file_path = 'sorted_balance_sheet.csv'
df_sorted.to_csv(output_file_path, index=False)
print(f"DataFrame saved as '{output_file_path}'")



# --- CODE ---
# Step 6: Sort the entire DataFrame by 'Sort' column in descending order
# Confirm that this operation is sorting all rows across all columns, not just the 'Sort' column
df_sorted = df_transposed.sort_values(by='Sort', ascending=False).reset_index()

# Final Diagnostic: Confirm structure and sorting across all columns
print("Final sorted DataFrame by 'Sort' across all columns:")
display(df_sorted)

# Save sorted DataFrame to CSV
output_file_path = 'sorted_balance_sheet.csv'
df_sorted.to_csv(output_file_path, index=False)
print(f"DataFrame saved as '{output_file_path}'")



# --- CODE ---
import pandas as pd

# Load data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Ensure 'Year' is the first column
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Sort by 'Year' and transpose
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)
df_transposed = df.set_index('Year').T

# Add helper column 'Sort'
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Sort by 'Sort' column and reset index to remove residual effects
df_sorted = df_transposed.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Final display to confirm if all data has sorted correctly
print("Final sorted DataFrame in Jupyter:")
display(df_sorted)

df_sorted.to_csv('sorted_balance_sheet.csv', index=False)


# --- CODE ---
import pandas as pd

# Disable scientific notation for readability
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Sort by 'Year' in ascending order and transpose
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)
df_transposed = df.set_index('Year').T

# Add a helper 'Sort' column with descending order numbers
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Check for Transposed DataFrame with 'Sort'
display(df_transposed.head())

# Save the initial sorted and transposed DataFrame to a CSV file
output_file_path = 'sorted_balance_sheet.csv'
df_transposed.to_csv(output_file_path, index=True)
print(f"Initial sorted and transposed DataFrame saved as '{output_file_path}'")


# --- CODE ---
# Load the sorted CSV
sorted_file_path = 'sorted_balance_sheet.csv'
df_sorted = pd.read_csv(sorted_file_path)

# Apply additional sort if needed (e.g., sorting by 'Year' column)
# For example, you might sort by 'Year' in ascending order
df_sorted = df_sorted.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Diagnostic Check for Final Sorted DataFrame
display(df_sorted.head())

# Save the final sorted DataFrame to another CSV file
final_output_path = 'final_sorted_balance_sheet.csv'
df_sorted.to_csv(final_output_path, index=False)
print(f"Final sorted DataFrame saved as '{final_output_path}'")


# --- CODE ---
import pandas as pd

# Disable scientific notation for readability
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load and preprocess the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Sort by 'Year' in ascending order
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Transpose the DataFrame and add 'Sort' column
df_transposed = df.set_index('Year').T
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Save the transposed and sorted DataFrame
intermediate_file_path = 'transposed_balance_sheet.csv'
df_transposed.to_csv(intermediate_file_path)

# Step 2: Reload, recheck structure, and sort by 'Sort' column if needed
df_final = pd.read_csv(intermediate_file_path)

# Check column names and structure after reloading
print("Column names after reloading intermediate file:", df_final.columns)

# Sort by 'Sort' column
df_final = df_final.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Final display to verify
display(df_final)

# Save the final output
final_output_path = 'final_sorted_balance_sheet.csv'
df_final.to_csv(final_output_path, index=False)
print(f"DataFrame saved as '{final_output_path}'")


# --- CODE ---
import pandas as pd

# Disable scientific notation for readability
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load and preprocess the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Sort by 'Year' in ascending order
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Transpose the DataFrame and add 'Sort' column
df_transposed = df.set_index('Year').T
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Save the transposed and sorted DataFrame without the index
intermediate_file_path = 'transposed_balance_sheet.csv'
df_transposed.to_csv(intermediate_file_path, index=False)

# Step 2: Reload the intermediate CSV without the unwanted index column
df_final = pd.read_csv(intermediate_file_path)

# Verify structure after reloading to ensure 'Unnamed: 0' does not appear
print("Column names after reloading intermediate file:", df_final.columns)

# Sort by 'Sort' column
df_final = df_final.sort_values(by='Sort', ascending=False).reset_index(drop=True)

# Final display to verify
print("Final sorted DataFrame by 'Sort' across all columns:")
display(df_final)

# Save the final output
final_output_path = 'final_sorted_balance_sheet.csv'
df_final.to_csv(final_output_path, index=False)
print(f"DataFrame saved as '{final_output_path}'")


# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)
df.columns.values[0] = 'Year'

# Step 2: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 3: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Reset the index to make 'Year' a column again
df_transposed.reset_index(inplace=True)

# Rename the 'index' column to 'Year'
df_transposed.rename(columns={'index': 'Year'}, inplace=True)

# Remove the name of the index
df_transposed.index.name = None




# --- CODE ---
# Step 6: Assign df_transposed to df_final and then sort by 'Sort' column
df_final = df_transposed.copy()  # Ensures df_final retains all columns from df_transposed

# Diagnostic Display to check columns in df_final before sorting
print("Columns in df_final before sorting:", df_final.columns)

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)
df.columns.values[0] = 'Year'

# Step 2: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 3: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index('Year').T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Reset the index to make 'Year' a column again
df_transposed.reset_index(inplace=True)

# Rename the 'index' column to 'Year'
df_transposed.rename(columns={'index': 'Year'}, inplace=True)

# Remove the name of the index
df_transposed.index.name = None

# Step 6: Assign df_transposed to df_final and then sort by 'Sort' column
df_final = df_transposed.copy()  # Ensures df_final retains all columns from df_transposed

# Diagnostic Display to check columns in df_final before sorting
print(df_final)

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)
df.columns.values[0] = 'Year'

# Step 2: Ensure the first column is labeled 'Year'
if df.columns[0] != 'Year':
    df.columns.values[0] = 'Year'

# Step 3: Sort data by 'Year' in ascending order (oldest to newest)
df = df.sort_values(by='Year', ascending=True).reset_index(drop=True)

# Step 4: Rename the 'Year' column to 'YearC' before transposing
df.rename(columns={'Year': 'YearC'}, inplace=True)

# Step 5: Transpose the sorted DataFrame
df_transposed = df.set_index('YearC').T

# Step 6: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 6 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Reset the index to make 'YearC' a column again
df_transposed.reset_index(inplace=True)

# Rename the 'index' column to 'YearC'
df_transposed.rename(columns={'index': 'YearC'}, inplace=True)

# Step 7: Assign df_transposed to df_final and then sort by 'Sort' column
df_final = df_transposed.copy()  # Ensures df_final retains all columns from df_transposed

# Diagnostic Display to check columns in df_final before sorting
print("Columns in df_final before sorting:", df_final.columns)

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (oldest to newest)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# --- CODE ---
# Step 6: Reset the index to make the first column a column again
df_transposed.reset_index(inplace=True)

# Rename the 'index' column to something appropriate, e.g., 'Category'
df_transposed.rename(columns={'index': 'Category'}, inplace=True)

# Rename the first column to 'Year'
df_transposed.rename(columns={df_transposed.columns[0]: 'Year'}, inplace=True)

# Step 7: Assign df_transposed to df_final and then sort by 'Sort' column
df_final = df_transposed.copy()  # Ensures df_final retains all columns from df_transposed

# Diagnostic Display to check columns in df_final before sorting
print("Columns in df_final before sorting:", df_final.columns)



# --- CODE ---
# Optional: Rename the first column to 'Year' if needed
df_final.rename(columns={first_column_name: 'Year'}, inplace=True)

# Final Diagnostic Display
print("Final DataFrame:")
print(df_final)

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (oldest to newest)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())





# --- CODE ---
# Step 6: Reset the index to make the first column a column again
df_transposed.reset_index(inplace=True)
print (df_transposed)



# --- CODE ---
# Rename the 'index' column to 'Category'
df_transposed.rename(columns={'index': 'Category'}, inplace=True)
print (df_transposed)

# Rename the first column to 'Year'
df_transposed.rename(columns={df_transposed.columns[0]: 'Year'}, inplace=True)

# Step 7: Assign df_transposed to df_final and then sort by 'Sort' column
df_final = df_transposed.copy()  # Ensures df_final retains all columns from df_transposed
print (df_final)


# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (oldest to newest)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Step 6: Reset the index to make the first column a column again
df_transposed.reset_index(inplace=True)

# Rename the 'index' column to 'Category'
df_transposed.rename(columns={'index': 'Category'}, inplace=True)

# Rename the first column to 'Year'
df_transposed.rename(columns={df_transposed.columns[0]: 'Year'}, inplace=True)

# Step 7: Drop the 'Unnamed: 0' column if it exists
if 'Unnamed: 0' in df_transposed.columns:
    df_transposed.drop(columns=['Unnamed: 0'], inplace=True)

# Step 8: Assign df_transposed to df_final and then sort by 'Sort' column
df_final = df_transposed.copy()  # Ensures df_final retains all columns from df_transposed

# Diagnostic Display to check columns in df_final before sorting
print("Columns in df_final before sorting:", df_final.columns)

# Final Diagnostic Display
print("Final DataFrame:")
print(df_final)

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (oldest to newest)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())



# --- CODE ---
# Step 6: Reset the index to make the first column a column again
df_transposed.reset_index(inplace=True)

# Rename the 'index' column to 'Category'
df_transposed.rename(columns={'index': 'Category'}, inplace=True)

# Rename the first column to 'Year'
df_transposed.rename(columns={df_transposed.columns[0]: 'Year'}, inplace=True)

# Step 7: Drop the 'Unnamed: 0' column if it exists
if 'Unnamed: 0' in df_transposed.columns:
    df_transposed.drop(columns=['Unnamed: 0'], inplace=True)

# Step 8: Assign df_transposed to df_final and then sort by 'Sort' column
df_final = df_transposed.copy()  # Ensures df_final retains all columns from df_transposed

# Diagnostic Display to check columns in df_final before sorting
print("Columns in df_final before sorting:", df_final.columns)


# --- CODE ---
# Final Diagnostic Display
print("Final DataFrame:")
print(df_final)

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (oldest to newest)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())


# --- CODE ---
# Step 6: Reset the index to make the first column a column again
df_transposed.reset_index(inplace=True)

# Rename the 'index' column to 'Category'
df_transposed.rename(columns={'index': 'Category'}, inplace=True)

# Rename the first column to 'Year'
df_transposed.rename(columns={df_transposed.columns[0]: 'Year'}, inplace=True)

# Step 7: Drop the 'Unnamed: 0' column if it exists
if 'Unnamed: 0' in df_transposed.columns:
    df_transposed.drop(columns=['Unnamed: 0'], inplace=True)

# Step 8: Assign df_transposed to df_final and then sort by 'Sort' column
df_final = df_transposed.copy()  # Ensures df_final retains all columns from df_transposed

# Diagnostic Display to check columns in df_final before sorting
print("Columns in df_final before sorting:", df_final.columns)

# Final Diagnostic Display
print("Final DataFrame:")
print(df_final)

# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data, specifying that the first column is the index
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path, index_col=0)

# Reset the index to make the index column a regular column
df.reset_index(inplace=True)

# Rename the index column to 'Category' (or any appropriate name)
df.rename(columns={'index': 'Category'}, inplace=True)

# Step 2: Identify the first column (which is now 'Category')
first_column_name = 'Category'

# Step 3: Sort data by the first column in ascending order (oldest to newest)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Step 6: Reset the index to make the index column a regular column
df_transposed.reset_index(inplace=True)

# Rename the 'index' column to 'Year' (since it now contains year data)
df_transposed.rename(columns={'index': 'Year'}, inplace=True)

# Step 7: Assign df_transposed to df_final and then sort by 'Sort' column if needed
df_final = df_transposed.copy()

# If you need to sort the DataFrame using the 'Sort' column
df_final.sort_values(by='Sort', ascending=False, inplace=True)

# Step 8: Drop the 'Sort' column if it's no longer needed
df_final.drop(columns=['Sort'], inplace=True)

# Diagnostic Display to check columns in df_final
print("Columns in df_final:", df_final.columns)

# Final Diagnostic Display
print("Final DataFrame:")
print(df_final)


# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (oldest to newest)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# **Step 6: Diagnostic display before sorting**
print("Step 6 - Diagnostic: DataFrame before sorting:")
display(df_transposed.head())

# **Step 7: Sort the DataFrame by 'Sort' column in ascending order**
df_transposed_sorted = df_transposed.sort_values(by='Sort', ascending=True)

# Diagnostic Display after sorting
print("Step 7 - Diagnostic: DataFrame after sorting:")
display(df_transposed_sorted.head())

# **Step 8: Assign the sorted DataFrame to df_final**
df_final = df_transposed_sorted.copy()

# Optional: Drop the 'Sort' column if you no longer need it
df_final.drop(columns=['Sort'], inplace=True)

# Final Diagnostic Display
print("Final DataFrame:")
display(df_final)


# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Step 1: Load the data
file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
df = pd.read_csv(file_path)

# Step 2: Identify the first column (which has a blank header)
first_column_name = df.columns[0]

# Step 3: Sort data by the first column in ascending order (oldest to newest)
df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

# Step 4: Transpose the sorted DataFrame
df_transposed = df.set_index(first_column_name).T

# Step 5: Add a helper column with incremental values for sorting
df_transposed['Sort'] = range(len(df_transposed), 0, -1)

# Diagnostic Display to check the structure after adding 'Sort'
print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
display(df_transposed.head())

# Step 6: Diagnostic display before sorting
print("Step 6 - Diagnostic: DataFrame before sorting:")
display(df_transposed.head())

# Step 7: Sort the DataFrame by 'Sort' column in ascending order
df_transposed_sorted = df_transposed.sort_values(by='Sort', ascending=True)

# Diagnostic Display after sorting
print("Step 7 - Diagnostic: DataFrame after sorting:")
display(df_transposed_sorted.head())

# Step 8: Assign the sorted DataFrame to df_final
df_final = df_transposed_sorted.copy()

# Optional: Drop the 'Sort' column if you no longer need it
df_final.drop(columns=['Sort'], inplace=True)

# Final Diagnostic Display
print("Final DataFrame:")
display(df_final)

df_final.index.name = 'Category'

# Step 9: Save the final DataFrame to a CSV file
output_file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/processed/complete_balance_sheet.csv'
df_final.to_csv(output_file_path, index=True)  # Set index=True to keep the 'Category' index


# --- CODE ---
# Jupyter Notebook: Balance Sheet Transformation Test

from scripts.data_preprocessing.financial_statement_transformer import FinancialStatementTransformer

# Initialize the transformer for balance sheet
transformer = FinancialStatementTransformer("balance_sheet")

# Step 1: Load Data
transformer.load_data()  # Loads the raw balance sheet data from the specified file
print("Raw Data:")
display(transformer.df.head())

# Step 2: Transform Data
transformer.transform_data()  # Applies sorting, transposing, and other transformations
print("Transformed Data:")
display(transformer.df.head())

# Step 3: Validate Transformation (Optional)
# Perform any validation checks you need to ensure transformations worked correctly

# Step 4: Inspect Tagged Data (Optional)
transformer.tag_data()  # Applies tagging logic using the line item dictionary
print("Tagged Data:")
display(transformer.df.head())


# --- CODE ---
conda install -c anaconda ipykernel
python -m ipykernel install --user --name=<your_env_name> --display-name "Python (<your_env_name>)"



# --- CODE ---
!pip install fuzzywuzzy python-Levenshtein


# --- CODE ---
conda activate <financial_modeling>
pip install ipykernel
python -m ipykernel install --user --name=<financial_modeling> --display-name "Python (<financial_modeling>)"



# --- CODE ---
import pandas as pd

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

# Define the file paths
input_file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
output_file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/processed/complete_balance_sheet_alt.csv'

# Step 1: Load the data and set the first column as the index
df = pd.read_csv(input_file_path, index_col=0)

# Step 2: Assign a name to the index
df.index.name = 'Category'

# Step 3: Sort the DataFrame by the index (financial categories)
df.sort_index(inplace=True)

# Step 4: Convert the column headers (dates) to datetime objects and sort them
# This ensures the date columns are in chronological order
df.columns = pd.to_datetime(df.columns, errors='coerce')

# Drop any columns that couldn't be converted to datetime (if any)
df = df.loc[:, df.columns.notnull()]

# Sort the columns (dates) in ascending order
df = df.reindex(sorted(df.columns), axis=1)

# Optional: If you want the dates formatted back to strings in a specific format
# For example, formatting dates as 'YYYY-MM-DD'
df.columns = df.columns.strftime('%Y-%m-%d')

# Step 5: Save the processed DataFrame to a CSV file
df.to_csv(output_file_path, index=True)


# --- CODE ---
import pandas as pd
from tabulate import tabulate

# Disable scientific notation globally
pd.options.display.float_format = '{:,.0f}'.format

def main():
    # Step 1: Load the data
    file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/raw/balance_sheet.csv'
    df = pd.read_csv(file_path)

    # Step 2: Identify the first column (which has a blank header)
    first_column_name = df.columns[0]

    # Step 3: Sort data by the first column in ascending order (alphabetically)
    df = df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

    # Step 4: Transpose the sorted DataFrame
    df_transposed = df.set_index(first_column_name).T

    # Step 5: Add a helper column with incremental values for sorting
    df_transposed['Sort'] = range(len(df_transposed), 0, -1)

    # Diagnostic Display to check the structure after adding 'Sort'
    print("Step 5 - Diagnostic: Transposed DataFrame with 'Sort' column added:")
    print(tabulate(df_transposed.head(), headers='keys', tablefmt='psql'))

    # Step 6: Diagnostic display before sorting
    print("\nStep 6 - Diagnostic: DataFrame before sorting:")
    print(tabulate(df_transposed.head(), headers='keys', tablefmt='psql'))

    # Step 7: Sort the DataFrame by 'Sort' column in ascending order
    df_transposed_sorted = df_transposed.sort_values(by='Sort', ascending=True)

    # Diagnostic Display after sorting
    print("\nStep 7 - Diagnostic: DataFrame after sorting:")
    print(tabulate(df_transposed_sorted.head(), headers='keys', tablefmt='psql'))

    # **Step 8: Clean up the DataFrame**

    # Create a copy of the sorted DataFrame
    df_final = df_transposed_sorted.copy()

    # Drop the 'Sort' column as it's no longer needed
    df_final.drop(columns=['Sort'], inplace=True)

    # Assign a name to the index
    df_final.index.name = 'Category'  # Set index name to 'Category'

    # Final Diagnostic Display
    print("\nFinal DataFrame:")
    print(tabulate(df_final.head(), headers='keys', tablefmt='psql'))

    # Step 9: Save the final DataFrame to a CSV file
    output_file_path = 'C:/Users/jklei/OneDrive - Convergix Automation/Documents/FinancialModeling_Project/data/processed/complete_balance_sheet.csv'
    df_final.to_csv(output_file_path, index=True)  # Set index=True to keep the 'Category' index

if __name__ == "__main__":
    main()


# --- CODE ---
python

# --- CODE ---
import os

file_path = r'C:\Users\jklei\OneDrive - Convergix Automation\Documents\FinancialModeling_Project\notebooks\scripts\data_ingestion\data_retrieval.py'
print(os.path.exists(file_path))


# --- CODE ---
import os

directory = r'C:\Users\jklei\OneDrive - Convergix Automation\Documents\FinancialModeling_Project\notebooks\scripts\data_ingestion'
print(os.listdir(directory))


# --- CODE ---
import os

output_folder = './data/raw'
print(os.path.exists(output_folder))


# --- CODE ---
# PowerShell script to list connected USB devices
Get-WmiObject -Query "SELECT * FROM Win32_USBHub WHERE DeviceID LIKE 'USB%'"

# Alternatively, you can use the following command to get detailed information
Get-WmiObject -Query "SELECT * FROM Win32_USBControllerDevice" | Select-Object DeviceID, Name, Manufacturer, PNPDeviceID


# --- CODE ---
import sys
import os
import logging

# Adjust sys.path to include project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir
sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import scripts
from scripts.data_ingestion.data_retrieval import main as data_retrieval_main
from scripts.data_preprocessing.balance_sheet_transformation import BalanceSheetTransformer
from scripts.data_preprocessing.income_statement_transformation import IncomeStatementTransformer
from scripts.data_preprocessing.cash_flow_transformation import CashFlowTransformer
from scripts.utilities.data_transformation_utils import get_data_paths

def run_data_ingestion():
    """Run the data ingestion process."""
    logger.info("Starting data ingestion...")
    data_retrieval_main()
    logger.info("Data ingestion completed.")

def run_data_preprocessing():
    """Run the data preprocessing for each financial statement."""
    logger.info("Starting data preprocessing...")
    BalanceSheetTransformer().transform()
    IncomeStatementTransformer().transform()
    CashFlowTransformer().transform()
    logger.info("Data preprocessing completed.")

def main():
    """Main execution workflow."""
    try:
        # Validate directories
        raw_data_dir, processed_data_dir = get_data_paths()
        for directory in [raw_data_dir, processed_data_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created missing directory: {directory}")

        # Run processes
        run_data_ingestion()
        run_data_preprocessing()

        # Note: Scenario analysis and sensitivity analysis are placeholders and not executed yet.
        logger.info("Main workflow completed successfully.")
    except Exception as e:
        logger.exception(f"An error occurred in the main execution: {e}")

if __name__ == "__main__":
    main()


# --- CODE ---
import sys
import os
import logging

# Use the current working directory in Jupyter
current_dir = os.getcwd()  # This gets the current working directory
project_root = current_dir  # Adjust if the project root is elsewhere
sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import scripts
from scripts.data_ingestion.data_retrieval import main as data_retrieval_main
from scripts.data_preprocessing.balance_sheet_transformation import BalanceSheetTransformer
from scripts.data_preprocessing.income_statement_transformation import IncomeStatementTransformer
from scripts.data_preprocessing.cash_flow_transformation import CashFlowTransformer
from scripts.utilities.data_transformation_utils import get_data_paths

def validate_directories():
    """Ensure that required directories exist."""
    raw_data_dir, processed_data_dir = get_data_paths()
    for directory in [raw_data_dir, processed_data_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created missing directory: {directory}")
    return raw_data_dir, processed_data_dir

def run_data_ingestion():
    """Run the data ingestion process."""
    logger.info("Starting data ingestion...")
    try:
        data_retrieval_main()
        logger.info("Data ingestion completed.")
    except Exception as e:
        logger.exception(f"Error during data ingestion: {e}")

def run_data_preprocessing():
    """Run the data preprocessing for each financial statement."""
    logger.info("Starting data preprocessing...")
    try:
        BalanceSheetTransformer().transform()
        IncomeStatementTransformer().transform()
        CashFlowTransformer().transform()
        logger.info("Data preprocessing completed.")
    except Exception as e:
        logger.exception(f"Error during data preprocessing: {e}")

def main():
    """Main execution workflow."""
    try:
        # Validate directories
        validate_directories()

        # Run processes
        run_data_ingestion()
        run_data_preprocessing()

        logger.info("Main workflow completed successfully.")
    except Exception as e:
        logger.exception(f"An error occurred in the main execution: {e}")

if __name__ == "__main__":
    main()


# --- CODE ---
from scripts.data_ingestion.data_retrieval import main as data_retrieval_main
print("Module imported successfully!")


# --- CODE ---
from path_setup import setup_project_paths
project_root = setup_project_paths()
print(f"Project root added to sys.path: {project_root}")


```

### `notebooks/financial_modeling_nb.ipynb`

```python
# --- CODE ---
!which python

# --- CODE ---
import fuzzywuzzy
print("fuzzywuzzy is installed and working.")
import Levenshtein
print("Levenshtein is installed and working.")

# --- CODE ---
!where python


# --- CODE ---
import os
import pandas as pd
from scripts.utilities.data_transformation_utils import (
    configure_logging,
    get_data_paths,
    tag_line_item_indices,
    line_item_dict,
)

logger = configure_logging()

class FinancialStatementTransformer:
    """Base class for transforming financial statements with validation and testing entry points."""

    def __init__(self, statement_type: str):
        self.statement_type = statement_type  # e.g., 'balance_sheet', 'income_statement', or 'cash_flow'
        self.raw_file, self.processed_file, self.tagged_file = self.get_file_paths()
        self.df = None  # Placeholder for the loaded DataFrame

    def get_file_paths(self):
        """Constructs file paths for raw, processed, and tagged files."""
        raw_dir, processed_dir = get_data_paths()
        raw_file = os.path.join(raw_dir, f'{self.statement_type}.csv')
        processed_file = os.path.join(processed_dir, f'processed_{self.statement_type}.csv')
        tagged_file = os.path.join(processed_dir, f'tagged_{self.statement_type}.csv')
        return raw_file, processed_file, tagged_file

    def load_data(self):
        """Loads raw financial statement data."""
        if not os.path.exists(self.raw_file):
            raise FileNotFoundError(f"Raw file not found: {self.raw_file}")
        self.df = pd.read_csv(self.raw_file)
        logger.info(f"Loaded {self.statement_type} data:\n{self.df.head()}")

    def validate_data(self):
        """
        Validates the raw data to ensure it can proceed with transformations.
        Example checks: non-empty DataFrame, numeric values, and appropriate structure.
        """
        if self.df is None or self.df.empty:
            raise ValueError(f"The raw data for {self.statement_type} is empty. Please check the source file.")

        # Example validation: Ensure the first column exists
        first_column_name = self.df.columns[0]
        if first_column_name == '':
            raise ValueError(f"The first column in the {self.statement_type} data is unnamed or blank.")

        # Example validation: Ensure at least one numeric column exists
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        if numeric_cols.empty:
            raise ValueError(f"No numeric columns found in {self.statement_type} data for calculations.")

        logger.info(f"{self.statement_type} data passed validation checks.")

    def transform_data(self):
        """Applies necessary transformations to the financial statement."""
        self.validate_data()  # Perform data validation before transformations

        # Step 1: Identify and use the first column as the index
        first_column_name = self.df.columns[0]

        # Step 2: Sort data by the first column (ascending order)
        self.df = self.df.sort_values(by=first_column_name, ascending=True).reset_index(drop=True)

        # Step 3: Transpose the DataFrame
        df_transposed = self.df.set_index(first_column_name).T

        # Step 4: Add a helper column for sorting
        df_transposed['Sort'] = range(len(df_transposed), 0, -1)

        # Step 5: Validation checkpoint and diagnostic logging
        logger.info(f"Step 5 - Transposed data with 'Sort' column:\n{df_transposed.head()}")
        # Allow manual inspection here if testing interactively

        # Step 6: Sort by the helper column and drop it
        df_sorted = df_transposed.sort_values(by='Sort', ascending=True).drop(columns=['Sort'])

        # Step 7: Reset index and set new index as 'Category'
        df_sorted.index.name = 'Category'

        # Update the instance DataFrame
        self.df = df_sorted.reset_index()
        logger.info(f"Transformed {self.statement_type} data:\n{self.df.head()}")

    def tag_data(self):
        """Tags line items using the predefined dictionary."""
        if 'Category' not in self.df.columns:
            logger.warning(f"Column 'Category' not found in {self.statement_type} data.")
            return
        self.df = tag_line_item_indices(self.df, line_item_dict)
        logger.info(f"Tagged {self.statement_type} data:\n{self.df.head()}")

    def save_data(self, filename: str, data: pd.DataFrame):
        """Saves DataFrame to a specified file."""
        _, processed_dir = get_data_paths()
        output_path = os.path.join(processed_dir, filename)
        data.to_csv(output_path, index=False)
        logger.info(f"Saved data to {output_path}")

    def transform(self):
        """
        Executes the full transformation pipeline.
        Can be stopped or rerun from specific steps during testing.
        """
        try:
            self.load_data()
            self.transform_data()

            # Save intermediate data for inspection
            self.save_data(f'processed_{self.statement_type}.csv', self.df)

            # Tag and save tagged data
            self.tag_data()
            self.save_data(f'tagged_{self.statement_type}.csv', self.df)

        except Exception as e:
            logger.error(f"Error transforming {self.statement_type}: {e}")

# Child classes for specific financial statements
class BalanceSheetTransformer(FinancialStatementTransformer):
    def __init__(self):
        super().__init__('balance_sheet')

class IncomeStatementTransformer(FinancialStatementTransformer):
    def __init__(self):
        super().__init__('income_statement')

class CashFlowTransformer(FinancialStatementTransformer):
    def __init__(self):
        super().__init__('cash_flow')

if __name__ == "__main__":
    # Entry points for testing transformations
    logger.info("Starting transformations for selected statements...")
    for Transformer in [BalanceSheetTransformer, IncomeStatementTransformer, CashFlowTransformer]:
        transformer = Transformer()
        transformer.transform()


# scripts/data_preprocessing/balance_sheet_transformation.py

from scripts.data_preprocessing.financial_statement_transformer import FinancialStatementTransformer

class BalanceSheetTransformer(FinancialStatementTransformer):
    def __init__(self):
        super().__init__("balance_sheet")

if __name__ == "__main__":
    transformer = BalanceSheetTransformer()
    transformer.transform()


# --- CODE ---
from scripts.data_preprocessing.balance_sheet_transformation import BalanceSheetTransformer

# Initialize the transformer
transformer = BalanceSheetTransformer()

# Step 1: Load raw data
df_raw = transformer.load_data()
print("Raw Data:")
display(df_raw.head())

# Step 2: Transform the data
df_transformed = transformer.transform_data(df_raw)
print("Transformed Data:")
display(df_transformed.head())

# Step 3: Validate tagging
df_tagged = transformer.tag_data(df_transformed)
print("Tagged Data:")
display(df_tagged.head())


# --- CODE ---
# scripts/data_preprocessing/balance_sheet_transformation.py

from scripts.data_preprocessing.financial_statement_transformer import FinancialStatementTransformer

class BalanceSheetTransformer(FinancialStatementTransformer):
    def __init__(self):
        super().__init__("balance_sheet")

if __name__ == "__main__":
    transformer = BalanceSheetTransformer()
    transformer.transform()


# --- CODE ---
# Add the project root to sys.path if needed
import os
import sys
project_root = os.path.abspath("..")
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the BalanceSheetTransformer
from scripts.data_preprocessing.balance_sheet_transformation import BalanceSheetTransformer

# Initialize the transformer
transformer = BalanceSheetTransformer()

# Step 1: Load Data
print("Step 1: Loading Data")
df = transformer.load_data()
print("Raw Data:")
display(df.head())

# Step 2: Transform Data
print("Step 2: Transforming Data")
transformed_df = transformer.transform_data(df)
print("Transformed Data:")
display(transformed_df.head())

# Step 3: Tag Data
print("Step 3: Tagging Data")
tagged_df = transformer.tag_data(transformed_df)
print("Tagged Data:")
display(tagged_df.head())

# Optional: Save Data (if desired during testing)
# Uncomment the following lines if you want to save processed data during testing
# transformer.save_data(transformed_df, transformer.processed_file)
# transformer.save_data(tagged_df, transformer.tagged_file)


# --- CODE ---
import sys
import os

project_root = os.path.abspath("..")  # Adjust if needed
if project_root not in sys.path:
    sys.path.append(project_root)
from scripts.data_preprocessing.balance_sheet_transformation import BalanceSheetTransformer

# Initialize the transformer
transformer = BalanceSheetTransformer()

# Run the transformation process
transformer.transform()


# --- CODE ---
import pandas as pd
from scripts.utilities.data_transformation_utils import tag_line_item_indices, line_item_dict

# Sample DataFrame
data = {"Category": ["Revenue", "Operating Expenses", "Net Profit"]}
df = pd.DataFrame(data)

# Apply the tagging function
tagged_df = tag_line_item_indices(df, line_item_dict)
print(tagged_df)


# --- CODE ---
# Jupyter Notebook: Test Data Transformation Utilities

# Ensure the project directory is accessible
import os
import sys
project_root = os.path.abspath("..")  # Adjust path as needed
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the utilities module
from scripts.utilities.data_transformation_utils import (
    tag_line_item_indices,
    line_item_dict,
    configure_logging
)

import pandas as pd

# Configure logging for Jupyter notebook
logger = configure_logging()

# Sample DataFrame for Testing
data = {
    "Category": ["Revenue", "Operating Expenses", "Unknown Item"],
    "2022": [1000, 200, 50],
    "2023": [1100, 250, 60]
}

df = pd.DataFrame(data)
print("Original DataFrame:")
display(df)

# Apply the tagging function
try:
    tagged_df = tag_line_item_indices(df, line_item_dict)
    print("Tagged DataFrame:")
    display(tagged_df)
except KeyError as e:
    logger.error(f"Error during tagging: {e}")

# Archiving Example
source_dir = os.path.join(project_root, "data", "raw")
archive_dir = os.path.join(project_root, "data", "archive")
print("Archiving files...")
try:
    # Ensure directories exist for testing
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(archive_dir, exist_ok=True)

    # Run the archive function
    archive_files(source_dir, archive_dir)
    print(f"Files archived from {source_dir} to {archive_dir}")
except Exception as e:
    logger.error(f"Error during archiving: {e}")


# --- CODE ---
import sys
import os

# Add the project root to the system path
project_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the utilities module
from scripts.utilities.data_transformation_utils import (
    tag_line_item_indices,
    line_item_dict,
    configure_logging
)

import pandas as pd

# Configure logging for Jupyter notebook
logger = configure_logging()

# Example usage of tag_line_item_indices
df = pd.DataFrame({
    'LineItem': ['Revenue', 'Cost of Goods Sold', 'Gross Profit', 'Operating Expenses', 'Net Income'],
    'Value': [1000, 500, 500, 200, 300]
})

tagged_indices = tag_line_item_indices(df['LineItem'], line_item_dict)
print(tagged_indices)

# --- MARKDOWN ---
In Visual Studio Code (VS Code), the "Tab Moves Focus" feature allows you to use the `Tab` key to move the focus between different UI elements, such as panels, editors, and input fields, rather than inserting a tab character in the text editor.

### How to Use "Tab Moves Focus"

1. **Enable/Disable "Tab Moves Focus"**:
   - You can toggle this feature by pressing `Ctrl + M` (Windows/Linux) or `Cmd + M` (Mac).
   - When enabled, pressing the `Tab` key will move the focus to the next focusable element in the UI.
   - When disabled, pressing the `Tab` key will insert a tab character in the text editor.

2. **Use Cases**:
   - **Enabled**: Useful when you want to navigate between different UI elements without using the mouse. For example, moving from the editor to the Problems panel, then to the Terminal, etc.
   - **Disabled**: Useful when you are editing code and want to insert tab characters for indentation.

### Example Scenario

Let's say you are working in a Jupyter notebook and want to quickly switch focus between the editor and the Problems panel:

1. **Enable "Tab Moves Focus"**:
   - Press `Ctrl + M` to enable "Tab Moves Focus".

2. **Navigate Using Tab**:
   - Press the `Tab` key to move the focus from the editor to the Problems panel.
   - Press `Tab` again to move the focus to the Terminal.

3. **Disable "Tab Moves Focus"**:
   - Press `Ctrl + M` again to disable "Tab Moves Focus" and return to normal tab behavior in the editor.

### Practical Example

If you have an error in your Jupyter notebook and want to quickly navigate to the Problems panel to see the details:

1. **Enable "Tab Moves Focus"**:
   - Press `Ctrl + M`.

2. **Navigate to Problems Panel**:
   - Press `Tab` until the focus is on the Problems panel.

3. **View and Fix the Error**:
   - Click on the error message to navigate to the corresponding line in the notebook.
   - Fix the error in the notebook.

4. **Disable "Tab Moves Focus"**:
   - Press `Ctrl + M` to return to normal tab behavior.

By using the "Tab Moves Focus" feature, you can efficiently navigate between different parts of the VS Code interface without relying on the mouse.

# --- CODE ---
# Import pandas to handle data
import pandas as pd
import numpy_financial as npf

# Create sample financial data
data = pd.DataFrame({
    "Year": [2024, 2025, 2026, 2027],
    "Revenue": [1000, 1100, 1200, 1300],
    "Expenses": [700, 750, 800, 850],
})

# Save the data to a CSV file for testing
data.to_csv("financial_data.csv", index=False)

# Confirm that the file is saved and display its contents
print("Sample data created and saved to 'financial_data.csv':")
print(data)


# --- CODE ---
# Load the data from the CSV file
df = pd.read_csv("financial_data.csv")

# Display the loaded data
print("Loaded data:")
print(df)


# --- CODE ---
# Calculate Net Income and Cash Flows
df["Net Income"] = df["Revenue"] - df["Expenses"]
df["Cash Flow"] = df["Net Income"]  # Assuming cash flow = net income for simplicity

# Display the updated DataFrame with new columns
print("Data with calculated Net Income and Cash Flow:")
print(df)


# --- CODE ---
# Export the DataFrame to an Excel file
df.to_excel("financial_model_output.xlsx", index=False)

# Confirm export
print("Financial model data exported to 'financial_model_output.xlsx'.")


# --- CODE ---
pip install numpy-financial


# --- CODE ---
from openpyxl import Workbook
from openpyxl.styles import Font

# Create a new Excel workbook
wb = Workbook()
ws = wb.active

# Write the header row
header = list(df.columns)
ws.append(header)

# Write the data rows
for row in df.values.tolist():
    ws.append(row)

# Apply bold formatting to header
for cell in ws[1]:
    cell.font = Font(bold=True)

# Save the workbook
wb.save("financial_model_output_formatted.xlsx")

# Confirm export
print("Formatted financial model data exported to 'financial_model_output_formatted.xlsx'.")


# --- CODE ---
import numpy_financial as npf

# Define the discount rate (e.g., 10%)
discount_rate = 0.10

# Extract cash flows into a list
cash_flows = df["Cash Flow"].tolist()

# Perform NPV calculation using numpy
npv= npf.npv(discount_rate, cash_flows)

# Display the Net Present Value (NPV)
print(f"Net Present Value (NPV): {npv:.2f}")

# --- CODE ---
import numpy_financial as npf


# Prompt user for a new discount rate
new_discount_rate = float(input("Enter a new discount rate (e.g., 0.10 for 10%): "))

# Recalculate NPV with the new discount rate
updated_npv = npf.npv(new_discount_rate, cash_flows)

# Display the updated NPV
print(f"Updated Net Present Value (NPV) with discount rate: {new_discount_rate * 100:.1f}%: {updated_npv:.2f}")


# --- CODE ---
import os
import sys
import logging
from scripts.data_ingestion.data_retrieval import main as data_retrieval_main
from scripts.data_preprocessing.balance_sheet_transformation import BalanceSheetTransformer
from scripts.data_preprocessing.income_statement_transformation import IncomeStatementTransformer
from scripts.data_preprocessing.cash_flow_transformation import CashFlowTransformer
from scripts.generate_scripts import main as generate_scripts_main
from scripts.utilities.data_transformation_utils import (
    configure_logging,
    get_data_paths,
    archive_files,
    prune_archives,
)

# Configure logging
logger = configure_logging()

def validate_and_archive_folders():
    """Validates the folder structure and archives existing files."""
    raw_data_dir, processed_data_dir = get_data_paths()

    # Define archive folders
    raw_archive_dir = os.path.join(raw_data_dir, 'archive')
    processed_archive_dir = os.path.join(processed_data_dir, 'archive')

    # Ensure directories exist
    for directory in [raw_data_dir, processed_data_dir, raw_archive_dir, processed_archive_dir]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Validated or created directory: {directory}")

def main():
    """Main function to run the data processing pipeline."""
    validate_and_archive_folders()

    # Run data retrieval
    data_retrieval_main()

    # Process balance sheet data
    balance_sheet_transformer = BalanceSheetTransformer()
    balance_sheet_transformer.load_data()
    balance_sheet_transformer.process_data()
    balance_sheet_transformer.tag_data()
    balance_sheet_transformer.archive_files()

    # Process income statement data
    income_statement_transformer = IncomeStatementTransformer()
    income_statement_transformer.load_data()
    income_statement_transformer.process_data()
    income_statement_transformer.tag_data()
    income_statement_transformer.archive_files()

    # Process cash flow data
    cash_flow_transformer = CashFlowTransformer()
    cash_flow_transformer.load_data()
    cash_flow_transformer.process_data()
    cash_flow_transformer.tag_data()
    cash_flow_transformer.archive_files()

    # Generate scripts
    generate_scripts_main()

if __name__ == "__main__":
    main()

```

### `notebooks/main.ipynb`

```python
# --- CODE ---
# Add the project root to sys.path if needed
import os
import sys
project_root = os.path.abspath(".")
if project_root not in sys.path:
    sys.path.append(project_root)

# Import methods and functions from main.py
from scripts.utilities.data_transformation_utils import configure_logging
from main import validate_and_archive_folders, run_data_ingestion, run_data_preprocessing

# Configure Logging
logger = configure_logging()

# Step 1: Validate and Archive Folders
print("Step 1: Validating and Archiving Folders")
validate_and_archive_folders()

# Step 2: Run Data Ingestion
print("Step 2: Running Data Ingestion")
run_data_ingestion()

# Step 3: Run Data Preprocessing
print("Step 3: Running Data Preprocessing")
run_data_preprocessing()

# If you want to test the entire main workflow
# Uncomment the following lines
# from main import main
# main()


# --- CODE ---
import os
import sys
import logging
from scripts.data_ingestion.data_retrieval import main as data_retrieval_main
from scripts.data_preprocessing.balance_sheet_transformation import BalanceSheetTransformer
from scripts.data_preprocessing.income_statement_transformation import IncomeStatementTransformer
from scripts.data_preprocessing.cash_flow_transformation import CashFlowTransformer
from scripts.generate_scripts import main as generate_scripts_main
from scripts.utilities.data_transformation_utils import (
    configure_logging,
    get_data_paths,
    archive_files,
    prune_archives,
)

# Configure logging
logger = configure_logging()

def validate_and_archive_folders():
    """Validates the folder structure and archives existing files."""
    raw_data_dir, processed_data_dir = get_data_paths()

    # Define archive folders
    raw_archive_dir = os.path.join(raw_data_dir, 'archive')
    processed_archive_dir = os.path.join(processed_data_dir, 'archive')

    # Ensure directories exist
    for directory in [raw_data_dir, processed_data_dir, raw_archive_dir, processed_archive_dir]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Validated or created directory: {directory}")

def main():
    """Main function to run the data processing pipeline."""
    validate_and_archive_folders()

    # Run data retrieval
    data_retrieval_main()

    # Process balance sheet data
    balance_sheet_transformer = BalanceSheetTransformer()
    balance_sheet_transformer.load_data()
    balance_sheet_transformer.process_data()
    balance_sheet_transformer.tag_data()
    balance_sheet_transformer.archive_files()

    # Process income statement data
    income_statement_transformer = IncomeStatementTransformer()
    income_statement_transformer.load_data()
    income_statement_transformer.process_data()
    income_statement_transformer.tag_data()
    income_statement_transformer.archive_files()

    # Process cash flow data
    cash_flow_transformer = CashFlowTransformer()
    cash_flow_transformer.load_data()
    cash_flow_transformer.process_data()
    cash_flow_transformer.tag_data()
    cash_flow_transformer.archive_files()

    # Generate scripts
    generate_scripts_main()

if __name__ == "__main__":
    main()

# --- CODE ---
#

```

---

## Data Files (paths only — binary/CSV not inlined)

- `./.claude/settings.json`
- `./Apple Valuation .xlsx`
- `./Apple/Apple Valuation (1).xlsx`
- `./Apple/VC-03-CyberFence-Deal-Recommendation.pdf`
- `./data/combined_statements.csv`
- `./data/nexus/flywheel_scores.json`
- `./data/nexus/gr_nodes.json`
- `./data/outputs/baseline_values.csv`
- `./notebooks/Archive/df_sorted.csv`
- `./notebooks/Archive/final_sorted_balance_sheet.csv`
- `./notebooks/financial_data.csv`
- `./notebooks/financial_model_output.csv`
- `./notebooks/financial_model_output.xlsx`
- `./notebooks/financial_model_output_formatted.csv`
- `./notebooks/financial_model_output_formatted.xlsx`
