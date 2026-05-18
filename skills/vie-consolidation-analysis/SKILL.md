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
