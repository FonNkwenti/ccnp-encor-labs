# Product Guidelines — CCNP ENCOR Lab Series

## Voice and Tone
- **Narrative & Scenario-Based:** Lab workbooks must contextualize tasks within a realistic professional scenario (e.g., "As a lead engineer for a global enterprise, your task is to...").
- **Professional & Authoritative:** Maintain a voice that positions these labs as the definitive resource for CCNP ENCOR mastery.

## Visual and Technical Standards
- **Standardized Diagrams:** Cisco-style Draw.io icons with consistent labeling (interface IDs on or near the corresponding link).
- **Formatted CLI Output:** Use code blocks for all CLI output. Verification steps must highlight expected values.

## Workbook Structure
- **Challenge-First Approach:** Present topology and high-level objectives first. Detailed configuration steps only in the collapsible solution section.
- **Detailed Physical Context:** Every workbook MUST include a "Cabling & Connectivity Table" detailing exact local/remote interface mappings and subnets.
- **Automated Environment Readiness:** Every lab MUST include a `setup_lab.py` Python script for automated initial config deployment via Netmiko telnet.

## Terminology and Conventions
- **Cisco Official Terminology:** Strictly adhere to official Cisco terminology aligned with the CCNP ENCOR (350-401) exam blueprint.

