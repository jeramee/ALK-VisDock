from __future__ import annotations

import requests

UA = {"User-Agent": "ALK-VisDock/0.2 (local research tool)"}


def _get(url: str, params: dict | None = None, timeout: int = 60) -> requests.Response:
    r = requests.get(url, params=params, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r


def name_search(name: str) -> str:
    """Very lightweight ChEMBL molecule search by name."""
    url = "https://www.ebi.ac.uk/chembl/api/data/molecule/search.json"
    js = _get(url, params={"q": name}, timeout=60).json()
    hits = js.get("molecules") or js.get("molecule") or []
    for h in hits:
        cid = h.get("molecule_chembl_id") or h.get("molecule", {}).get("molecule_chembl_id")
        if cid:
            return cid
    return ""
