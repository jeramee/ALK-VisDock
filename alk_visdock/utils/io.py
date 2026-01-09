from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from ..models import Ligand


def read_ligands_csv_tsv(path: Path) -> list[Ligand]:
    """Read ligands from CSV/TSV with headers: name,smiles,pubchem_cid,chembl_id,notes."""
    delim = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
    out: list[Ligand] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            name = (row.get("name") or row.get("Name") or "").strip()
            if not name:
                continue
            out.append(Ligand(
                name=name,
                smiles=(row.get("smiles") or row.get("SMILES") or "").strip(),
                pubchem_cid=(row.get("pubchem_cid") or row.get("PubChemCID") or row.get("cid") or "").strip(),
                chembl_id=(row.get("chembl_id") or row.get("ChEMBL") or "").strip(),
                notes=(row.get("notes") or row.get("Notes") or "").strip(),
            ))
    return out


def find_case_snapshots(recon_dir: Path) -> list[Path]:
    """Heuristic: find any JSON files that look like ALK-RECON case snapshots."""
    if not recon_dir.exists():
        return []
    hits: list[Path] = []
    for p in recon_dir.rglob("*.json"):
        name = p.name.lower()
        if "case" in name and "snapshot" in name:
            hits.append(p)
            continue
        if name.endswith("casesnapshot.json") or name.endswith("case_snapshot.json"):
            hits.append(p)
    return sorted(set(hits))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
