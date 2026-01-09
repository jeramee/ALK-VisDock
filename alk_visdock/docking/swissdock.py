from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Tuple

import requests

SWISSDOCK_BASE = "https://www.swissdock.ch/docking"
UA = {"User-Agent": "ALK-VisDock/0.2"}


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n\nSTDOUT:\n{p.stdout}\n\nSTDERR:\n{p.stderr}"
        )


def smiles_to_mol2_with_obabel(
    smiles: str,
    out_mol2: Path,
    title: str,
    obabel: str = "obabel",
) -> None:
    """Convert SMILES to 3D MOL2 using OpenBabel CLI (obabel).

    Requires OpenBabel installed and `obabel` on PATH.
    """
    out_mol2.parent.mkdir(parents=True, exist_ok=True)
    _run([obabel, f"-:{smiles}", "--gen3d", "-O", str(out_mol2), "-h", "--title", title])


def _extract_session_number(text: str) -> str:
    m = re.search(r"Session number:\s*([0-9]+)", text, flags=re.IGNORECASE)
    if not m:
        raise RuntimeError(f"Could not find session number in response (first 2000 chars):\n{text[:2000]}")
    return m.group(1)


def preplig_vina(mol2_path: Path) -> str:
    url = f"{SWISSDOCK_BASE}/preplig?Vina"
    with mol2_path.open("rb") as f:
        r = requests.post(url, files={"file": (mol2_path.name, f, "chemical/x-mol2")}, headers=UA, timeout=180)
    r.raise_for_status()
    return _extract_session_number(r.text)


def preptarget(session: str, pdb_path: Path) -> None:
    url = f"{SWISSDOCK_BASE}/preptarget"
    with pdb_path.open("rb") as f:
        r = requests.post(
            url,
            data={"sessionNumber": session},
            files={"file": (pdb_path.name, f, "chemical/x-pdb")},
            headers=UA,
            timeout=600,
        )
    r.raise_for_status()


def setparameters_vina(session: str, center: Tuple[float, float, float], size: Tuple[float, float, float], exhaust: int = 8) -> None:
    url = f"{SWISSDOCK_BASE}/setparameters"
    params = {
        "sessionNumber": session,
        "exhaust": str(exhaust),
        "boxCenter": f"{center[0]},{center[1]},{center[2]}",
        "boxSize": f"{size[0]},{size[1]},{size[2]}",
    }
    r = requests.get(url, params=params, headers=UA, timeout=180)
    r.raise_for_status()


def startdock(session: str) -> None:
    url = f"{SWISSDOCK_BASE}/startdock"
    r = requests.get(url, params={"sessionNumber": session}, headers=UA, timeout=120)
    r.raise_for_status()


def checkstatus(session: str) -> str:
    url = f"{SWISSDOCK_BASE}/checkstatus"
    r = requests.get(url, params={"sessionNumber": session}, headers=UA, timeout=120)
    r.raise_for_status()
    return r.text.strip()


def retrievesession(session: str, out_tgz: Path) -> None:
    url = f"{SWISSDOCK_BASE}/retrievesession"
    r = requests.get(url, params={"sessionNumber": session}, headers=UA, timeout=600, stream=True)
    r.raise_for_status()
    out_tgz.parent.mkdir(parents=True, exist_ok=True)
    with out_tgz.open("wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)


def submit_and_wait(
    name: str,
    smiles: str,
    receptor_pdb: Path,
    center: Tuple[float, float, float],
    size: Tuple[float, float, float],
    workdir: Path,
    obabel: str = "obabel",
    exhaust: int = 8,
    poll_s: int = 30,
    max_wait_s: int = 3600,
) -> dict:
    """End-to-end SwissDock Vina job.

    Returns a dict with session id + status; downloads tgz to workdir.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    mol2 = workdir / f"{name}.mol2"
    smiles_to_mol2_with_obabel(smiles, mol2, title=name, obabel=obabel)

    session = preplig_vina(mol2)
    preptarget(session, receptor_pdb)
    setparameters_vina(session, center=center, size=size, exhaust=exhaust)
    startdock(session)

    t0 = time.time()
    last = ""
    status = ""
    while True:
        status = checkstatus(session)
        if status != last:
            last = status
        low = status.lower()
        if "finished" in low or "done" in low:
            break
        if "error" in low or "failed" in low:
            raise RuntimeError(f"SwissDock job failed ({name}): {status}")
        if time.time() - t0 > max_wait_s:
            raise TimeoutError(f"SwissDock job timed out ({name}), session {session}")
        time.sleep(poll_s)

    out_tgz = workdir / f"{name}_swissdock_{session}.tgz"
    retrievesession(session, out_tgz)
    return {"backend": "swissdock", "session": session, "status": status, "archive": str(out_tgz)}


class SwissDockClient:
    """Tiny wrapper so the builder can treat SwissDock as a pluggable backend."""

    def __init__(self, obabel: str = "obabel"):
        self.obabel = obabel

    def submit(self, ligand_smiles: str, receptor_pdb: Path, work_dir: Path, name: str) -> str:
        """Submit a SwissDock Vina job and return the session id.

        SwissDock has a browser-oriented flow; this wrapper uses the same endpoints.
        """
        work_dir.mkdir(parents=True, exist_ok=True)
        mol2 = work_dir / f"{name}.mol2"
        smiles_to_mol2_with_obabel(ligand_smiles, mol2, obabel=self.obabel)
        session = preplig_vina(mol2)
        preptarget(session, receptor_pdb)
        startdock(session)
        return session
