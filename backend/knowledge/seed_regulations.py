"""Seed regulation text for the Compliance Agent, keyed by regulation pack.

These are illustrative placeholder clauses (matching the reference codes already shown
in the frontend's compliance panel) — NOT verified legal text. Before relying on this in
a real deployment, the plant's actual compliance/legal team must load the real clause
text for whichever pack applies (see plant.config.yaml's `regulation_pack` field).
"""

REGULATIONS: dict[str, list[dict]] = {
    "india-oisd-dgms-factoryact-v1": [
        {
            "source": "OISD",
            "clause_ref": "OISD-GDN-237",
            "content": (
                "Before confined space entry, gas clearance must be verified and documented "
                "for the specific space, and re-verified if work is interrupted or conditions "
                "change. A confined-space permit issued without a current gas clearance reading "
                "is non-compliant."
            ),
        },
        {
            "source": "OISD",
            "clause_ref": "OISD-GDN-237",
            "content": (
                "Simultaneous permits affecting the same zone or adjoining equipment must be "
                "cross-checked for conflicting hazards before both are allowed to remain active "
                "at once."
            ),
        },
        {
            "source": "Factory Act",
            "clause_ref": "Factory Act Sec 7A",
            "content": (
                "Hot work permits require a documented proximity check against any zone with "
                "elevated flammable-gas readings before work commences."
            ),
        },
        {
            "source": "DGMS",
            "clause_ref": "DGMS Circular 2023",
            "content": (
                "A documented safety briefing is required at every shift handover for any zone "
                "with an active high-risk permit, covering outstanding hazards to the incoming shift."
            ),
        },
        {
            "source": "OISD",
            "clause_ref": "OISD-STD-116",
            "content": "Emergency evacuation drills must be conducted and logged at least monthly.",
        },
        {
            "source": "OISD",
            "clause_ref": "OISD-STD-189",
            "content": "Fire detection systems must remain operational and be tested per manufacturer schedule.",
        },
        {
            "source": "Factory Act",
            "clause_ref": "Factory Act Sec 35",
            "content": "Appropriate PPE is mandatory for all personnel working within classified hazardous zones.",
        },
        {
            "source": "OISD",
            "clause_ref": "OISD-RP-149",
            "content": "Gas detectors must be calibrated at least quarterly, with calibration dates logged per sensor.",
        },
    ],
}
