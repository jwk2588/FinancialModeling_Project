"""
NEXUS Chess Framework — Proprietary Project Translation Engine
Takes a customer's broad objective and maps it into a structured Nexus workspace config.

Chess metaphors map to analytical roles:
  King   → Primary case objective (must be protected/advanced)
  Queen  → Master Nexus Agent (most powerful, all-directions reasoning)
  Rooks  → Structural pillars (Forensic + Regulatory — fortress foundations)
  Bishops→ Cross-domain bridges (Wolf + Tiger on diagonal attack vectors)
  Knights→ Novel/unconventional moves (surprise legal theories, analogical leaps)
  Pawns  → Granular evidence nodes (individual facts that can promote to Queen)

The mapper classifies the objective, then returns a full workspace config:
  - posture (adversarial / investigatory / analytical / regulatory / mixed)
  - primary domains + subdomain emphasis
  - agent lead assignment
  - flywheel priorities
  - opening moves (first 3 recommended actions)
  - chess piece assignments per domain
"""
from __future__ import annotations
import re
from dataclasses import dataclass, asdict, field


# ── CHESS PIECE ROLES ─────────────────────────────────────────────────────────

CHESS_PIECE_ROLES = {
    "king":   "Primary case objective — the outcome being protected or advanced",
    "queen":  "Master Nexus Agent — orchestrates all reasoning directions",
    "rook_1": "Rook Alpha — Forensic/Accounting structural pillar",
    "rook_2": "Rook Beta — Regulatory/Legal structural pillar",
    "bishop_1": "Wolf Agent — precision diagonal attack on evidence and doctrine",
    "bishop_2": "Tiger Agent — expansive diagonal bridge across domains",
    "knight_1": "Novel legal theory #1 — unconventional move, high surprise value",
    "knight_2": "Novel legal theory #2 — second unconventional vector",
    "pawns":  "Granular GR nodes — individual facts with promotion potential",
}

# ── POSTURE CLASSIFIER ────────────────────────────────────────────────────────

POSTURE_SIGNALS: dict[str, list[str]] = {
    "adversarial": [
        "sue", "litigation", "lawsuit", "claim", "fraud", "damages", "breach",
        "arbitration", "settlement", "plaintiff", "defendant", "complaint",
        "motion", "discovery", "deposition", "trial",
    ],
    "regulatory": [
        "regulatory", "compliance", "audit", "mgcb", "cftc", "sec", "ftc",
        "license", "violation", "enforcement", "investigation", "nfa", "fincen",
    ],
    "investigatory": [
        "investigate", "analyze", "map", "document", "research", "find",
        "identify", "trace", "uncover", "discover", "evidence",
    ],
    "analytical": [
        "model", "calculate", "quantify", "estimate", "project", "simulate",
        "score", "measure", "benchmark", "assess",
    ],
    "governance": [
        "board", "governance", "fiduciary", "oversight", "caremark", "director",
        "officer", "corporate", "adr", "settlement", "negotiation",
    ],
}

# ── DOMAIN SIGNAL MAP ─────────────────────────────────────────────────────────

DOMAIN_SIGNALS: dict[str, list[str]] = {
    "forensic_accounting": [
        "accounting", "revenue", "gaap", "asc", "icfr", "sox", "audit",
        "breakage", "virtual currency", "financial statement", "restatement",
    ],
    "regulatory_cftc": [
        "cftc", "commodity", "cea", "mgcb", "michigan", "gaming", "nfa",
        "derivatives", "binary option", "exchange act",
    ],
    "corp_accountability": [
        "board", "fiduciary", "caremark", "vie", "gps llc", "arbitration",
        "illusory", "forum", "governance", "consolidation",
    ],
    "neuropharm": [
        "addiction", "dopamine", "behavioral", "harm", "vulnerable", "gambling",
        "design", "aops", "variable reward",
    ],
    "privacy_tech": [
        "privacy", "terms of service", "tos", "data", "consent", "platform",
        "gdpr", "ccpa", "any reason",
    ],
    "harm_reduction": [
        "mcpa", "consumer", "udap", "evidence", "authentication", "class action",
        "restitution", "smith v", "mcpa §445",
    ],
}

# ── OPENING MOVE LIBRARY ──────────────────────────────────────────────────────

OPENING_MOVES: dict[str, list[str]] = {
    "adversarial": [
        "Map all GR nodes by nuclear_impact — identify the top 5 Silver Bullets",
        "Run arbitration kill chain: enumerate all 7 grounds with controlling citations",
        "Build authenticated evidence chain (FRE 901) for core damages event",
    ],
    "regulatory": [
        "Enumerate all material changes requiring MGCB approval — cross-reference R 432.206(2)",
        "Map CFTC CEA §1a(10) Crowey Test elements to DK product architecture",
        "Identify SOX 302/404 false certification chain from ICFR failures",
    ],
    "investigatory": [
        "Run GhostRecon sweep: extract all GR nodes with pending_content_summary",
        "Map evidence anchors to GR nodes — identify coverage gaps",
        "Cross-reference front linkages: which Fronts have no active GR node support?",
    ],
    "analytical": [
        "Compute domain flywheel scores — identify weakest domain for enrichment",
        "Model settlement band: expected value vs. litigation cost vs. SEC exposure",
        "Quantify 483% TC inflation across 3.6M users — calculate restitution floor",
    ],
    "governance": [
        "Apply Caremark standard — what specific board failures create director liability?",
        "Run board rational choice model: settlement NPV vs. continued litigation cost",
        "Map ADR posture: which fronts compress to settlement fastest?",
    ],
}


@dataclass
class ChessWorkspaceConfig:
    """Full workspace configuration produced by the Chess Framework mapper."""
    project_id: str
    objective_raw: str
    posture: str
    posture_confidence: float
    primary_domains: list[str]
    secondary_domains: list[str]
    agent_lead: str                   # nexus_master / wolf / tiger / suits
    flywheel_priority: list[str]      # ordered list of domain IDs to emphasize
    chess_board: dict[str, str]       # piece → domain/agent/theory assignment
    opening_moves: list[str]          # first 3 recommended actions
    domain_emphasis: dict[str, float] # domain_id → emphasis weight 0-1
    knight_theories: list[str]        # novel/unconventional move candidates
    king_objective: str               # refined single-sentence objective


def classify_objective(text: str) -> dict[str, float]:
    """Score the objective against all postures. Returns {posture: confidence}."""
    lower = text.lower()
    scores: dict[str, float] = {}
    for posture, signals in POSTURE_SIGNALS.items():
        hits = sum(1 for s in signals if s in lower)
        scores[posture] = min(1.0, hits / max(len(signals) * 0.3, 1))
    return scores


def detect_domains(text: str) -> tuple[list[str], list[str]]:
    """Return (primary_domains, secondary_domains) detected from objective text."""
    lower = text.lower()
    domain_scores: dict[str, int] = {}
    for dom, signals in DOMAIN_SIGNALS.items():
        domain_scores[dom] = sum(1 for s in signals if s in lower)
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    primary = [d for d, s in sorted_domains if s > 0][:3]
    secondary = [d for d, s in sorted_domains if s > 0][3:]
    if not primary:
        primary = ["forensic_accounting", "corp_accountability"]  # sensible default
    return primary, secondary


def _assign_chess_board(primary_domains: list[str], posture: str, agent_lead: str) -> dict[str, str]:
    """Assign chess pieces to project elements based on domains and posture."""
    board: dict[str, str] = {
        "king": f"PRIMARY OBJECTIVE — {posture.upper()} posture",
        "queen": f"Master Nexus Agent — orchestrates {', '.join(primary_domains[:2])}",
    }
    if len(primary_domains) >= 1:
        board["rook_1"] = f"Rook Alpha: {primary_domains[0]} structural pillar"
    if len(primary_domains) >= 2:
        board["rook_2"] = f"Rook Beta: {primary_domains[1]} structural pillar"
    board["bishop_1"] = f"Wolf Agent: precision extraction in {primary_domains[0] if primary_domains else 'evidence'}"
    board["bishop_2"] = f"Tiger Agent: cross-domain bridging → {primary_domains[-1] if primary_domains else 'analogy'}"
    board["knight_1"] = "Novel theory slot 1 — populate from GR node P1-MUST pending queue"
    board["knight_2"] = "Novel theory slot 2 — Tiger analog mapping across corpus"
    board["pawns"] = f"GR nodes ({len(primary_domains)} domain clusters) — each promotes on activation"
    return board


def _derive_knight_theories(objective: str, primary_domains: list[str]) -> list[str]:
    """Identify unconventional/novel move candidates from domain context."""
    theories = []
    lower = objective.lower()
    if "arbitration" in lower or "forum" in lower:
        theories.append("VIE Circular Disclaimer as independent unconscionability (Arb Ground 7)")
    if "cftc" in lower or "commodity" in lower:
        theories.append("Crown/DK$ as unregistered commodity exchange (CEA §9 price manipulation)")
    if "vie" in lower or "gps" in lower:
        theories.append("GPS LLC restatement cascade → BDO independence trigger → SEC inquiry")
    if "mcpa" in lower or "consumer" in lower:
        theories.append("Michigan licensed entity ≠ MCPA exempt — Smith v. Globe Life defeat")
    if not theories:
        theories = [
            "Dual-regulator pincer: simultaneous CFTC WB-TCR + MGCB material change filing",
            "Class action + individual ADR: parallel pressure tracks on DK's forum preference",
        ]
    return theories


def map_objective(objective: str, project_id: str = "nexus_project") -> ChessWorkspaceConfig:
    """
    Core Chess Framework function: translate a customer objective into workspace config.

    Args:
        objective:  The user's stated project goal (any length, any specificity)
        project_id: Nexus project identifier

    Returns:
        ChessWorkspaceConfig — full workspace initialization spec
    """
    posture_scores = classify_objective(objective)
    posture = max(posture_scores, key=posture_scores.get)  # type: ignore
    posture_confidence = posture_scores[posture]

    # Handle mixed posture (adversarial + regulatory is common)
    if posture_confidence < 0.25:
        posture = "adversarial"  # safe default for litigation context
        posture_confidence = 0.5

    primary_domains, secondary_domains = detect_domains(objective)

    # Determine agent lead
    agent_lead_map = {
        "adversarial": "wolf",
        "investigatory": "wolf",
        "regulatory": "suits",
        "governance": "suits",
        "analytical": "tiger",
    }
    agent_lead = agent_lead_map.get(posture, "nexus_master")

    # Flywheel priority: primary domains first
    flywheel_priority = primary_domains + [d for d in [
        "forensic_accounting", "regulatory_cftc", "corp_accountability",
        "harm_reduction", "privacy_tech", "neuropharm",
    ] if d not in primary_domains]

    # Domain emphasis weights
    n_primary = len(primary_domains)
    domain_emphasis: dict[str, float] = {}
    for i, dom in enumerate(primary_domains):
        domain_emphasis[dom] = round(1.0 - (i * 0.15), 2)
    for dom in secondary_domains:
        domain_emphasis[dom] = 0.4

    chess_board = _assign_chess_board(primary_domains, posture, agent_lead)
    opening_moves = OPENING_MOVES.get(posture, OPENING_MOVES["adversarial"])
    knight_theories = _derive_knight_theories(objective, primary_domains)

    # Refine the King objective to one sentence
    sentences = re.split(r'(?<=[.!?])\s+', objective.strip())
    king_objective = sentences[0] if sentences else objective[:120]

    return ChessWorkspaceConfig(
        project_id=project_id,
        objective_raw=objective,
        posture=posture,
        posture_confidence=round(posture_confidence, 2),
        primary_domains=primary_domains,
        secondary_domains=secondary_domains,
        agent_lead=agent_lead,
        flywheel_priority=flywheel_priority,
        chess_board=chess_board,
        opening_moves=opening_moves,
        domain_emphasis=domain_emphasis,
        knight_theories=knight_theories,
        king_objective=king_objective,
    )


def config_to_dict(cfg: ChessWorkspaceConfig) -> dict:
    """Serialize config for JSON API response."""
    return asdict(cfg)


if __name__ == "__main__":
    import json
    test_objective = (
        "Build a comprehensive litigation strategy against DraftKings for MCPA violations, "
        "CFTC commodity regulation failures, and ASC 810 VIE consolidation exposure. "
        "Goal is to force ADR settlement at maximum value or proceed to class action."
    )
    cfg = map_objective(test_objective, project_id="dk_masterbrief")
    print("\nCHESS FRAMEWORK OUTPUT")
    print("=" * 60)
    print(f"  Posture:       {cfg.posture} ({cfg.posture_confidence:.0%} confidence)")
    print(f"  Agent Lead:    {cfg.agent_lead}")
    print(f"  Primary Domains: {', '.join(cfg.primary_domains)}")
    print(f"\n  CHESS BOARD:")
    for piece, assignment in cfg.chess_board.items():
        print(f"    {piece:12s}: {assignment}")
    print(f"\n  OPENING MOVES:")
    for i, move in enumerate(cfg.opening_moves, 1):
        print(f"    {i}. {move}")
    print(f"\n  KNIGHT THEORIES:")
    for t in cfg.knight_theories:
        print(f"    ♞ {t}")
    print(f"\n  KING: {cfg.king_objective}")
