# NEXUS Platform — Changelog

All iterative builds tracked here. Format: `[version] date — description`.

---

## [0.5.0] 2026-04-08 — Full Test Pass + Dataset-Grounded Claude API

### Added
- `nexus_test.py` — end-to-end test suite (26 tests across 5 modules)
  - Data file integrity checks (108 GR nodes, 418+ evidence anchors)
  - Context injection validation (persona-specific node routing)
  - Offline mode verification (dataset-derived responses, no API key needed)
  - Domain schema + scoring validation
  - Ingest pipeline idempotency check
  - HTTP server endpoint tests (`--server` flag)
  - Live Claude API tests (`--online` flag)
- `build_context_block(persona, top_n)` in `nexus_ai.py`
  - Injects live GR corpus into every Claude API system prompt
  - Persona-aware node routing: wolf/tiger/suits get filtered top-N nodes
  - Includes flywheel scores, evidence codes, agent-specific routing text
  - Grounding format: `[GR-NNN] Name | Impact | Evidence | Agent routing`
- `offline_response(prompt, persona)` in `nexus_ai.py`
  - Keyword-scored GR node retrieval without any API call
  - Returns structured brief with matched nodes, flywheel status
  - Enables full demo with zero API credits
- `NEXUS_MODE` env var (`online`|`offline`) — auto-detects from API key presence
- `NEXUS_CONTEXT_NODES` env var — controls how many GR nodes injected (default: 12)
- `/api/domains` endpoint added to HTTP server (serves domain hierarchy + scores)
- `/api/state` now returns `mode`, `model`, `corpus_size` metadata

### Fixed
- `NexusAgent.ask()` had `thinking={"type":"adaptive"}` — invalid param, removed
- `NexusAgent` now properly falls back to offline mode when no API key present
- SSE handler in `serve()` now uses `build_context_block` for dataset grounding
- `nexus_domain_schema.py` background agent corruption — restored from git

### Architecture
```
User prompt
  │
  ├─ ONLINE mode ──► build_context_block(persona)
  │                    ├─ Top-N GR nodes by nuclear_impact
  │                    ├─ Persona-filtered routing (wolf/tiger/suits)
  │                    └─ Flywheel scores injected into system prompt
  │                  ──► Claude API (claude-opus-4-6)
  │                        GR Tool Loop (read/update nodes, evidence)
  │                  ──► SSE stream → HTML frontend
  │
  └─ OFFLINE mode ─► offline_response(prompt, persona)
                       ├─ Keyword-score GR nodes against prompt
                       └─ Return deterministic dataset-derived brief
```

---

## [0.4.0] 2026-04-08 — Beta Build: Domain DFW + JS Fix

### Added
- `nexus_domain_schema.py` — 3-level domain taxonomy (Domain → Subdomain → Granular)
  - 6 domains: forensic_accounting, regulatory_cftc, corp_accountability, neuropharm, privacy_tech, harm_reduction
  - 15 subdomains with legal standards
  - `compute_domain_scores()` — objective scoring from GR node nuclear_impact weights
  - `get_domain_hierarchy()` — full enriched hierarchy for `/api/domains`
  - 9 cross-domain bridge edges for DSB view
- DOMAIN DATA FLYWHEEL (DDF) view in HTML — 3-panel drill-down (L1/L2/L3)
- DOMAIN SKILL BRIDGE (DSB) view in HTML — cross-domain edge visualization
- `--host` flag for `nexus_ai.py serve` — bind to `0.0.0.0` for LAN/mobile access
- `/api/ingest_csv` endpoint — structured CSV ingest from browser without API key

### Fixed
- JS `SyntaxError` on page load: unescaped single quotes in `onclick` handlers inside JS string literals
  - `askNexus('gr',''+n.id+'')` → `askNexus(\'gr\',\''+n.id+'\')`
  - `selectGRNode(''+n.id+'')` → `selectGRNode(\''+n.id+'\')`

---

## [0.3.0] 2026-04-07 — Full MasterBrief v54 Ingest (98 sections)

### Added
- Complete MB54 CSV saved (98 rows — up from 32-row partial)
- Re-ran `nexus_ingest_mb54.py`: 108 GR nodes, 237 evidence anchors
- All 6 Engines, 11 v52 sections, 6 v52 Engines, 17 Bunkers, 13 Exhibits, 9 Fronts, 16 Pending sections

### Data Growth
```
GR Nodes:         32 → 108  (+76)
Evidence anchors: 56 → 237  (+181)
Flywheel:         5 domains all active
```

---

## [0.2.0] 2026-04-06 — Python Backend + HTML Frontend Integration

### Added
- `nexus_ai.py` — Python bridge (22KB)
  - `NexusAgent` class with 5 personas (nexus_master, wolf, tiger, suits, fetty)
  - GhostRecon tool loop (read/update GR nodes, flywheel scoring, evidence anchors)
  - HTTP bridge server port 7433 with SSE streaming
  - `serve`, `ingest`, `ask`, `state`, `mb54` CLI subcommands
- `nexus_ingest_mb54.py` — rule-based CSV ingest (no API key needed)
  - Priority → nuclear_impact mapping (P1-MUST=96, P2-HIGH=82, P3-MEDIUM=70)
  - Front linkage → flywheel domain inference
  - Section type → agent routing
- `nexus_synthesis_os.html` updated:
  - Python Bridge URL + SYNC STATE button in Settings panel
  - `syncFromBackend()` — fetches `/api/state`, merges GR nodes + flywheel
  - `askNexus()` routes to backend SSE or direct Anthropic API
- `data/nexus/` directory seeded with 10 HTML GR nodes + initial flywheel

---

## [0.1.0] 2026-04-05 — Initial NEXUS Synthesis OS v8

### Added
- `nexus_synthesis_os.html` — 178KB standalone HTML application
  - 20+ views: CORPUS, GHOST RECON, FLYWHEELS, SIM, JUDGE MODE, ADR FRONTS, etc.
  - Safari/iOS compatible
  - Direct Anthropic API mode (browser → API key → Claude)
  - GhostRecon node panel (GR-001 through GR-010 seeded)
  - Data Flywheel view (6 domain mastery tracks)
  - Chess Engine simulation (7-turn convergence)
  - FettyFM orchestration console
- `requirements.txt` with `anthropic>=0.89.0`
- Git repository on branch `claude/setup-nexus-v7-3OcCD`
