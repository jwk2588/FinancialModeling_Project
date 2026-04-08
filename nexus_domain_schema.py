"""
NEXUS Domain Schema — 3-Level Taxonomy + Objective Scoring
Domain Data Flywheel (DDF) architecture for the Nexus Platform Beta.

Hierarchy: Domain → Subdomain → Granular Nodes
Scoring:   computed from GR node nuclear_impact + evidence density + coverage
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

# ── DOMAIN TAXONOMY ──────────────────────────────────────────────────────────
# 6 primary domains, each with 2-3 subdomains, each with granular drill-down nodes

DOMAIN_TAXONOMY: dict = {
    "forensic_accounting": {
        "label": "Forensic / Accounting",
        "color": "cyan",
        "hex": "#00d4ff",
        "agent": "tiger",
        "flywheel_aliases": ["revenue_recognition", "platform_economics"],
        "keywords": ["asc 606", "gaap", "breakage", "icfr", "sox", "revenue", "accounting"],
        "subdomains": {
            "revenue_recognition": {
                "label": "Revenue Recognition",
                "standards": ["ASC 606", "ASC 606-10-25-27", "GAAP", "FRE 1006"],
                "granular": [
                    {"id": "asc606_app", "label": "ASC 606 Application to Virtual Currency",
                     "standards": ["ASC 606-10-25-27", "ASC 606-10-55-22"]},
                    {"id": "breakage_acct", "label": "Breakage Accounting — Proportional Method",
                     "standards": ["ASC 606-10-55-48"]},
                    {"id": "virt_currency", "label": "Virtual Currency Liability Treatment",
                     "standards": ["ASC 350-40"]},
                    {"id": "off_balance", "label": "Off-Balance-Sheet Contingent Liabilities",
                     "standards": ["ASC 450-20"]},
                ],
            },
            "platform_economics": {
                "label": "Platform Economics / TC Inflation",
                "standards": ["ASC 808", "FASB ASU 2014-09", "CEA §1a(10)"],
                "granular": [
                    {"id": "dk_exchange", "label": "DK$ Hidden Exchange Rate Architecture"},
                    {"id": "tc_inflation_483", "label": "483% Tier Credit Inflation — Pillar 9"},
                    {"id": "ioc_credits", "label": "IOC Off-Book Credit Remediation"},
                    {"id": "crown_tier_struct", "label": "Crown/Diamond/Onyx Contingent State"},
                ],
            },
            "internal_controls": {
                "label": "Internal Controls / ICFR / SOX",
                "standards": ["SOX §302", "SOX §404", "PCAOB AS 2201", "COSO 2013"],
                "granular": [
                    {"id": "sox404_weakness", "label": "SOX 404 Material Weakness"},
                    {"id": "icfr_gaps", "label": "ICFR Assessment Deficiencies"},
                    {"id": "audit_trail", "label": "Audit Trail Authentication Gaps"},
                    {"id": "bdo_withdraw", "label": "BDO Withdrawal — Independence Trigger"},
                    {"id": "coso_failure", "label": "COSO Framework Control Failure"},
                ],
            },
        },
    },

    "regulatory_cftc": {
        "label": "Regulatory / CFTC",
        "color": "gold",
        "hex": "#ffd766",
        "agent": "suits",
        "flywheel_aliases": [],
        "keywords": ["cftc", "cea", "mgcb", "michigan gaming", "regulatory", "derivatives",
                     "commodity", "nfa", "exchange act"],
        "subdomains": {
            "cftc_derivatives": {
                "label": "CFTC / Commodity Exchange Act",
                "standards": ["CEA §1a(10)", "CEA §4c(b)", "CEA §6c", "17 CFR Part 32"],
                "granular": [
                    {"id": "crowey_test", "label": "Crowey Test — Binary Option Classification",
                     "standards": ["CEA §1a(10)"]},
                    {"id": "cea_4cb_opts", "label": "CEA §4c(b) Options Element Analysis"},
                    {"id": "dufoe_prec", "label": "Dufoe v. DraftKings Application"},
                    {"id": "contingent_states", "label": "Diamond/Onyx Contingent Payoff States"},
                    {"id": "gus_nfa_timeline", "label": "Gus II→III NFA Registration Gap"},
                ],
            },
            "michigan_gaming": {
                "label": "Michigan Gaming Control Board",
                "standards": ["MCL §432.201", "R 432.206(2)", "R 432.632a(9)", "R 432.663(1)"],
                "granular": [
                    {"id": "8_material_changes", "label": "8 Unapproved Material Changes"},
                    {"id": "mgcb_r432", "label": "MGCB R 432.206(2) Violation Matrix"},
                    {"id": "license_compliance", "label": "License Compliance Audit"},
                    {"id": "two_prong_smith", "label": "Two-Prong Framework (Smith v. Globe Life)"},
                ],
            },
            "securities": {
                "label": "Securities / Exchange Act",
                "standards": ["Exchange Act §10(b)", "Rule 10b-5", "15 U.S.C. §78j"],
                "granular": [
                    {"id": "material_misrep", "label": "Material Misrepresentation — 6 Repetitions"},
                    {"id": "scienter_std", "label": "Scienter — Institutional Awareness"},
                    {"id": "reliance_causal", "label": "Reliance / Transaction Causation"},
                ],
            },
        },
    },

    "corp_accountability": {
        "label": "Corp. Accountability",
        "color": "#9b7fe8",
        "hex": "#9b7fe8",
        "agent": "suits",
        "flywheel_aliases": ["governance"],
        "keywords": ["caremark", "fiduciary", "board", "governance", "vie", "arbitration",
                     "asc 810", "gps llc", "illusory"],
        "subdomains": {
            "governance_fiduciary": {
                "label": "Board Governance / Fiduciary Duty",
                "standards": ["Caremark Standard", "Delaware §141", "Fiduciary Duty"],
                "granular": [
                    {"id": "caremark_board", "label": "Caremark Board Oversight Failures"},
                    {"id": "rational_choice", "label": "Board Rational Choice Settlement Model"},
                    {"id": "fiduciary_breach", "label": "Fiduciary Duty Breach Analysis"},
                    {"id": "adr_posture", "label": "ADR Settlement Containment Posture"},
                ],
            },
            "vie_consolidation": {
                "label": "VIE / Consolidation (ASC 810)",
                "standards": ["ASC 810", "ASC 810-10-15-14", "FIN 46R"],
                "granular": [
                    {"id": "gps_llc_vie", "label": "GPS LLC VIE Three-Track Definitive Analysis"},
                    {"id": "asc810_three_prong", "label": "ASC 810-10-15-14 Three-Prong Test"},
                    {"id": "dynasty_store", "label": "Dynasty Store Control-Responsibility Paradox"},
                    {"id": "circular_disclaimer", "label": "VIE Circular Disclaimer (Arb Ground 7)"},
                ],
            },
            "arbitration_forum": {
                "label": "Arbitration / Forum Collapse",
                "standards": ["FAA", "AutoZone v. Munroe", "Klapp v. United Ins. Group",
                              "Pakideh v. Franklin"],
                "granular": [
                    {"id": "autozone_illusory", "label": "AutoZone Illusory Consideration Precedent"},
                    {"id": "7_kill_grounds", "label": "7 Arbitration Kill Grounds (All Viable)"},
                    {"id": "forum_destabilize", "label": "Forum Destabilization Strategy"},
                    {"id": "vip_unconscionability", "label": "VIP Host Program Unconscionability"},
                ],
            },
        },
    },

    "neuropharm": {
        "label": "Neuropharm / Behavioral",
        "color": "#5de5a0",
        "hex": "#5de5a0",
        "agent": "tiger",
        "flywheel_aliases": [],
        "keywords": ["dopamine", "addiction", "behavioral", "variable reward", "harm", "aops",
                     "dsg", "vulnerable"],
        "subdomains": {
            "addictive_design": {
                "label": "Addictive Design / AOPS",
                "standards": ["FTC Act §5", "DSM-5 Gambling Disorder", "APA Guidelines"],
                "granular": [
                    {"id": "dopamine_loops", "label": "Dopamine Loop Architecture — Variable Reward"},
                    {"id": "variable_reward_sched", "label": "Variable Reward Schedule Design"},
                    {"id": "harm_reduction_fail", "label": "Harm Reduction Protocol Failures"},
                    {"id": "vulnerable_targeting", "label": "Vulnerable Population Targeting"},
                ],
            },
            "behavioral_economics": {
                "label": "Behavioral Economics / Nudge",
                "standards": ["Prospect Theory", "Nudge Theory", "Kahneman & Tversky"],
                "granular": [
                    {"id": "loss_aversion", "label": "Loss Aversion Exploitation — Crown Pricing"},
                    {"id": "anchoring_bias", "label": "Price Anchoring (550:1 Crown-to-MSRP)"},
                    {"id": "sunk_cost_esc", "label": "Sunk Cost Escalation Design"},
                    {"id": "status_anxiety", "label": "Status Anxiety (Diamond/Onyx Tier Design)"},
                ],
            },
        },
    },

    "privacy_tech": {
        "label": "Privacy / Tech Law",
        "color": "#e05c5c",
        "hex": "#e05c5c",
        "agent": "wolf",
        "flywheel_aliases": ["privacy_tos"],
        "keywords": ["privacy", "tos", "data collection", "ccpa", "gdpr", "platform", "consent",
                     "terms of service"],
        "subdomains": {
            "privacy_tos": {
                "label": "Privacy / ToS Analysis",
                "standards": ["CCPA", "GDPR Art. 6", "FTC Act §5", "MCL §445.903"],
                "granular": [
                    {"id": "tos_deception", "label": "ToS Deceptive Provisions — Any Reason Clause"},
                    {"id": "data_collection_scope", "label": "Data Collection Scope Analysis"},
                    {"id": "consent_validity", "label": "Consent Validity — Illusory Agreement"},
                    {"id": "privacy_notice_gap", "label": "Privacy Notice Adequacy Failures"},
                ],
            },
            "platform_liability": {
                "label": "Platform Liability / §230",
                "standards": ["47 U.S.C. §230", "DMCA", "CDA"],
                "granular": [
                    {"id": "publisher_vs_platform", "label": "Publisher vs. Platform Status Test"},
                    {"id": "sec230_limits", "label": "§230 Immunity Boundary Analysis"},
                ],
            },
        },
    },

    "harm_reduction": {
        "label": "Harm Reduction / AOPS",
        "color": "#00ffcc",
        "hex": "#00ffcc",
        "agent": "wolf",
        "flywheel_aliases": ["litigation_risk"],
        "keywords": ["mcpa", "consumer protection", "udap", "evidence", "authentication", "fre",
                     "chain of custody", "mcpa §445"],
        "subdomains": {
            "consumer_protection": {
                "label": "Consumer Protection (MCPA / UDAP)",
                "standards": ["MCPA §445.903", "FTC Act §5", "UDAP", "MCL §445.902"],
                "granular": [
                    {"id": "mcpa_903_viol", "label": "MCPA §445.903 Violation Enumeration"},
                    {"id": "globe_life_defeat", "label": "Smith v. Globe Life Defeat — Anti-Exemption"},
                    {"id": "anti_exemption", "label": "Anti-Exemption Framing (Licensed ≠ Exempt)"},
                    {"id": "class_action_stand", "label": "Class Action Standing — 3.6M Users"},
                ],
            },
            "evidence_authentication": {
                "label": "Evidence Chain / Authentication",
                "standards": ["FRE 901", "FRE 803(6)", "FRE 1006", "FRE 702"],
                "granular": [
                    {"id": "five_step_chain", "label": "Authenticated 5-Step Evidence Chain"},
                    {"id": "screenshot_auth", "label": "Screenshot Authentication Protocol"},
                    {"id": "chain_custody", "label": "Chain of Custody Documentation"},
                    {"id": "expert_forensic", "label": "Expert Forensic CPA Analysis"},
                ],
            },
        },
    },
}

# ── DOMAIN BRIDGES (DSB — Domain Skill Bridge view) ──────────────────────────

DOMAIN_BRIDGES: list = [
    {"from": "forensic_accounting", "to": "regulatory_cftc", "strength": 0.92,
     "label": "CEA §1a(10) + ASC 606 virtual currency — same instruments, two regulators"},
    {"from": "forensic_accounting", "to": "corp_accountability", "strength": 0.88,
     "label": "ASC 810 VIE consolidation → restatement → SOX 302/404 false certifications"},
    {"from": "regulatory_cftc", "to": "corp_accountability", "strength": 0.85,
     "label": "8 MGCB material changes + board awareness = Caremark failure"},
    {"from": "corp_accountability", "to": "privacy_tech", "strength": 0.79,
     "label": "ToS Any-Reason clause + VIE circular disclaimer = unconscionability stack"},
    {"from": "harm_reduction", "to": "privacy_tech", "strength": 0.83,
     "label": "MCPA §445.903 + data collection deception = unfair/deceptive act"},
    {"from": "neuropharm", "to": "harm_reduction", "strength": 0.90,
     "label": "Addictive design architecture → AOPS harm reduction failures"},
    {"from": "forensic_accounting", "to": "harm_reduction", "strength": 0.81,
     "label": "483% TC inflation → MCPA unfair practices → class standing"},
    {"from": "regulatory_cftc", "to": "neuropharm", "strength": 0.76,
     "label": "Variable reward schedule → contingent state → derivatives classification"},
    {"from": "corp_accountability", "to": "harm_reduction", "strength": 0.87,
     "label": "AutoZone illusory consideration → forum collapse → MCPA damages"},
]

# ── SCORING ALGORITHM ────────────────────────────────────────────────────────

# Map flywheel domain keys from GR nodes → our taxonomy keys
_FLYWHEEL_ALIAS: dict = {
    "revenue_recognition": "forensic_accounting",
    "platform_economics": "forensic_accounting",
    "governance": "corp_accountability",
    "litigation_risk": "harm_reduction",
    "privacy_tos": "privacy_tech",
}


def compute_domain_scores(gr_nodes: dict, evidence_anchors: dict) -> dict[str, float]:
    """
    Objective scoring: derives domain proficiency from ingested GR node data.

    Formula (per domain):
        score = (avg_nuclear_impact * 0.55)
              + (coverage_ratio     * 0.25)
              + (evidence_density   * 0.20)

    Floor of 0.55 for any domain with no matched nodes (baseline knowledge exists).
    Returns: {domain_id: float 0.0–1.0}
    """
    # Bucket GR nodes by domain
    domain_nodes: dict[str, list] = {k: [] for k in DOMAIN_TAXONOMY}

    for node in gr_nodes.values():
        # Match via flywheel_domains list
        fw_doms = node.get("flywheel_domains", [])
        if isinstance(fw_doms, str):
            fw_doms = [fw_doms]
        for fd in fw_doms:
            mapped = _FLYWHEEL_ALIAS.get(fd, fd)
            if mapped in domain_nodes:
                domain_nodes[mapped].append(node)

        # Match via keyword scan in summary + legal_standards
        text = " ".join([
            str(node.get("summary", "")),
            str(node.get("legal_standards", "")),
            str(node.get("name", "")),
        ]).lower()
        for dom_id, dom in DOMAIN_TAXONOMY.items():
            if any(kw in text for kw in dom["keywords"]):
                if node not in domain_nodes[dom_id]:
                    domain_nodes[dom_id].append(node)

    # Count evidence anchors per domain
    ev_per_domain: dict[str, int] = {k: 0 for k in DOMAIN_TAXONOMY}
    for _ev_code, anchor in evidence_anchors.items():
        if isinstance(anchor, dict):
            node_id = anchor.get("node_id", anchor.get("section_id", ""))
            node_ids = [node_id] if node_id else []
        elif isinstance(anchor, list):
            node_ids = [str(x) for x in anchor if isinstance(x, str)]
        else:
            node_ids = [str(anchor)]
        for nid in node_ids:
            node = gr_nodes.get(nid, {})
            fw_doms = node.get("flywheel_domains", [])
            if isinstance(fw_doms, str):
                fw_doms = [fw_doms]
            for fd in fw_doms:
                mapped = _FLYWHEEL_ALIAS.get(fd, fd)
                if mapped in ev_per_domain:
                    ev_per_domain[mapped] += 1

    scores: dict[str, float] = {}
    for dom_id, dom in DOMAIN_TAXONOMY.items():
        nodes = domain_nodes[dom_id]
        n_sub = len(dom.get("subdomains", {}))

        # Component 1: average nuclear_impact (0–100 → 0–1)
        impacts = [n.get("nuclear_impact", 65) for n in nodes]
        avg_impact = (sum(impacts) / len(impacts) / 100) if impacts else 0.0

        # Component 2: coverage (node count vs expected)
        expected = max(n_sub * 2, 1)
        coverage = min(1.0, len(nodes) / expected)

        # Component 3: evidence density (30 EV refs = saturated)
        ev_density = min(1.0, ev_per_domain[dom_id] / 30)

        # Apply floor for zero-node domains
        if not nodes:
            scores[dom_id] = 0.55
        else:
            raw = (avg_impact * 0.55) + (coverage * 0.25) + (ev_density * 0.20)
            scores[dom_id] = round(min(1.0, raw), 3)

    return scores


def get_domain_hierarchy(gr_nodes: dict, evidence_anchors: dict) -> dict:
    """
    Full enriched domain hierarchy for the /api/domains endpoint.
    Each domain includes score, node count, subdomains, suggested prompts.
    """
    scores = compute_domain_scores(gr_nodes, evidence_anchors)

    domains_out: dict = {}
    for dom_id, dom in DOMAIN_TAXONOMY.items():
        n_nodes = len([
            n for n in gr_nodes.values()
            if any(kw in " ".join([
                str(n.get("summary", "")),
                str(n.get("legal_standards", "")),
                str(n.get("name", "")),
            ]).lower() for kw in dom["keywords"])
        ])
        domains_out[dom_id] = {
            "label": dom["label"],
            "color": dom["color"],
            "hex": dom.get("hex", "#00d4ff"),
            "agent": dom["agent"],
            "score": scores[dom_id],
            "score_pct": round(scores[dom_id] * 100),
            "node_count": n_nodes,
            "subdomain_count": len(dom.get("subdomains", {})),
            "subdomains": dom.get("subdomains", {}),
            "suggested_prompts": _suggest_prompts(dom_id),
        }

    return {
        "domains": domains_out,
        "bridges": DOMAIN_BRIDGES,
        "total_nodes": len(gr_nodes),
        "total_evidence": len(evidence_anchors),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def _suggest_prompts(dom_id: str) -> list[str]:
    """Actionable, citation-specific prompts per domain."""
    prompts = {
        "forensic_accounting": [
            "Apply ASC 606-10-55-48 breakage accounting to DraftKings Tier Credits — what is the contingent liability?",
            "Model the 483% TC inflation impact on DraftKings FY2023/2024 deferred revenue balance",
            "Map ICFR material weakness chain: VIP host IOC credits → GL bypass → SOX 302 false certification",
            "Quantify ASC 810 VIE consolidation exposure: if GPS LLC consolidates, what is the restatement band?",
            "Run BDO withdrawal analysis: what triggered independence concern and what is the SEC disclosure obligation?",
        ],
        "regulatory_cftc": [
            "Apply Crowey Test element-by-element to DraftKings Crown Coins — satisfy CEA §1a(10) all prongs?",
            "Enumerate the 8 MGCB material changes with specific R 432.206(2) violations and regulatory citations",
            "Analyze Dufoe v. DraftKings (1st Cir.) application to Tier Credits as 'underlying commodity'",
            "Map the Gus II → III NFA registration gap: what is the unlicensed operation exposure window?",
            "Build CFTC WB-TCR timeline: filing, 30-day pre-suit, consciousness of guilt documentation chain",
        ],
        "corp_accountability": [
            "Apply Caremark standard: what board oversight failures enable individual director liability?",
            "Run ASC 810-10-15-14 three-prong VIE test on GPS LLC — does DK meet primary beneficiary criteria?",
            "Enumerate all 7 arbitration kill grounds with controlling case citations — which is strongest?",
            "Analyze GPS LLC / Dynasty Store circular disclaimer as Arbitration Ground 7 unconscionability",
            "Model ADR settlement band: board rational choice vs. litigation cost vs. SEC exposure compression",
        ],
        "neuropharm": [
            "Map DraftKings Crown pricing to dopamine variable reward schedule — which DSM-5 criteria does it satisfy?",
            "Analyze 550:1 Crown-to-MSRP rate as behavioral anchoring exploitation — quantify harm per user",
            "Compare DraftKings VIP host program design to Purdue Pharma OxyContin targeting methodology",
            "Identify AOPS harm reduction failures: what protocols were contractually promised vs. implemented?",
        ],
        "privacy_tech": [
            "Identify all deceptive provisions in DraftKings ToS under MCPA §445.903 — list each with clause reference",
            "Map DraftKings data collection scope (users, device signals, 3rd party) against CCPA consent requirements",
            "Analyze 'Any Reason or No Reason' ToS clause: does it render the entire agreement illusory?",
            "Cross-reference DraftKings privacy notice data uses against FTC Act §5 unfair/deceptive standard",
        ],
        "harm_reduction": [
            "Build authenticated 5-step evidence chain for FRE 901 admissibility: screenshot → metadata → server log",
            "Apply Smith v. Globe Life (460 Mich. 446) defeat to anti-exemption MCPA §445.903 framing",
            "Enumerate MCPA §445.903 unfair practice violations — which are per-transaction vs. per-class?",
            "Calculate restitution floor: 3.6M Michigan users × avg TC inflation damage × Pillar 9 multiplier",
        ],
    }
    return prompts.get(dom_id, ["Analyze this domain's data with the relevant AI agent"])


# ── CLI / TEST ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from pathlib import Path
    import json

    DATA = Path(__file__).parent / "data" / "nexus"

    def _load(f): return json.loads((DATA / f).read_text()) if (DATA / f).exists() else {}

    gr = _load("gr_nodes.json")
    ev = _load("evidence_anchors.json")

    scores = compute_domain_scores(gr, ev)
    hier = get_domain_hierarchy(gr, ev)

    print(f"\nNEXUS DOMAIN SCHEMA — {len(DOMAIN_TAXONOMY)} domains\n{'='*60}")
    for dom_id, data in hier["domains"].items():
        bar = "█" * (data["score_pct"] // 5)
        print(f"  {data['label']:35s} {data['score_pct']:3d}% {bar}")
    print(f"\n  Total GR nodes:  {hier['total_nodes']}")
    print(f"  Evidence anchors: {hier['total_evidence']}")
    print(f"  Domain bridges:  {len(hier['bridges'])}")
    print(f"  Computed at:     {hier['computed_at']}\n")
