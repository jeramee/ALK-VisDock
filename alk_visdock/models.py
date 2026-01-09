from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class Ligand:
    name: str
    smiles: str = ""
    pubchem_cid: str = ""
    chembl_id: str = ""
    notes: str = ""

    # computed/enriched
    iupac: str = ""
    formula: str = ""
    mw: str = ""
    xlogp: str = ""
    hbd: str = ""
    hba: str = ""
    tpsa: str = ""
    rotb: str = ""

    # local assets (site-relative)
    image_2d: str = ""
    conformer_sdf: str = ""
    docking: Optional[dict[str, Any]] = None
    pose: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Remove empty docking/pose for cleanliness
        if not d.get("docking"):
            d.pop("docking", None)
        if not d.get("pose"):
            d.pop("pose", None)
        return d
