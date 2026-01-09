from __future__ import annotations

from pathlib import Path

import requests

UA = {"User-Agent": "ALK-VisDock/0.2 (local research tool)"}


def download_mmcif(pdb_id: str, out_cif: Path) -> bool:
    pdb_id = pdb_id.upper()
    url = f"https://files.rcsb.org/view/{pdb_id}.cif"
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    txt = r.text
    if txt and "data_" in txt[:200].lower():
        out_cif.parent.mkdir(parents=True, exist_ok=True)
        out_cif.write_text(txt, encoding="utf-8")
        return True
    return False
