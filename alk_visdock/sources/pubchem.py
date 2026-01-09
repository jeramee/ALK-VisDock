from __future__ import annotations

import requests
from pathlib import Path

UA = {"User-Agent": "ALK-VisDock/0.1 (research tool)"}
BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"


def _get(url: str, params: dict | None = None, timeout: int = 60) -> requests.Response:
    r = requests.get(url, params=params, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r


def resolve_name_to_cid(name: str) -> str:
    """Resolve a common name to a PubChem CID (best-effort)."""
    url = f"{BASE}/name/{requests.utils.quote(name)}/cids/JSON"
    js = _get(url).json()
    cids = js.get("IdentifierList", {}).get("CID", [])
    return str(cids[0]) if cids else ""


def props_by_cid(cid: str) -> dict:
    props = ",".join(
        [
            "CanonicalSMILES",
            "IUPACName",
            "MolecularWeight",
            "XLogP",
            "HBondDonorCount",
            "HBondAcceptorCount",
            "TPSA",
            "RotatableBondCount",
            "MolecularFormula",
        ]
    )
    url = f"{BASE}/cid/{cid}/property/{props}/JSON"
    js = _get(url).json()
    rows = js.get("PropertyTable", {}).get("Properties", [])
    return rows[0] if rows else {}


def props_by_smiles(smiles: str) -> dict:
    """Fetch properties using a SMILES string as identifier.

    Useful fallback when RDKit is not installed.
    """
    props = ",".join(
        [
            "CanonicalSMILES",
            "IUPACName",
            "MolecularWeight",
            "XLogP",
            "HBondDonorCount",
            "HBondAcceptorCount",
            "TPSA",
            "RotatableBondCount",
            "MolecularFormula",
        ]
    )
    smi = requests.utils.quote(smiles, safe="")
    url = f"{BASE}/smiles/{smi}/property/{props}/JSON"
    js = _get(url).json()
    rows = js.get("PropertyTable", {}).get("Properties", [])
    return rows[0] if rows else {}


def download_png_by_cid(cid: str, out_png: Path, size: int = 420) -> bool:
    url = f"{BASE}/cid/{cid}/PNG"
    r = _get(url, params={"image_size": str(size)}, timeout=60)
    if not r.headers.get("content-type", "").lower().startswith("image/"):
        return False
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(r.content)
    return True


def download_png_by_smiles(smiles: str, out_png: Path, size: int = 420) -> bool:
    smi = requests.utils.quote(smiles, safe="")
    url = f"{BASE}/smiles/{smi}/PNG"
    r = _get(url, params={"image_size": str(size)}, timeout=60)
    if not r.headers.get("content-type", "").lower().startswith("image/"):
        return False
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_png.write_bytes(r.content)
    return True
