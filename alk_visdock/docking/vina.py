from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Tuple


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n\nSTDOUT:\n{p.stdout}\n\nSTDERR:\n{p.stderr}"
        )
    return p


def run_vina(
    vina_exe: str,
    receptor_pdbqt: Path,
    ligand_pdbqt: Path,
    out_pdbqt: Path,
    log_path: Path,
    center: Tuple[float, float, float],
    size: Tuple[float, float, float],
    exhaustiveness: int = 8,
    num_modes: int = 9,
) -> dict:
    out_pdbqt.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        vina_exe,
        "--receptor", str(receptor_pdbqt),
        "--ligand", str(ligand_pdbqt),
        "--center_x", str(center[0]),
        "--center_y", str(center[1]),
        "--center_z", str(center[2]),
        "--size_x", str(size[0]),
        "--size_y", str(size[1]),
        "--size_z", str(size[2]),
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", str(num_modes),
        "--out", str(out_pdbqt),
        "--log", str(log_path),
    ]

    p = _run(cmd)

    # parse best affinity from log if present
    best = None
    try:
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            # Vina table rows: "   1  -7.5  0.0  0.0"
            if line.strip().startswith("1") or line.strip().startswith("1 "):
                parts = line.split()
                if len(parts) >= 2:
                    best = float(parts[1])
                    break
    except Exception:
        pass

    return {
        "backend": "vina",
        "best_affinity_kcal_mol": best,
        "out_pdbqt": str(out_pdbqt),
        "log": str(log_path),
    }
