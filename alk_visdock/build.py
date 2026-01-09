from __future__ import annotations

import json
import shutil
from pathlib import Path

from .models import Ligand
from .sources import pubchem
from .sources import chembl
from .sources import rcsb
from .utils.io import read_ligands_csv_tsv
from .utils.rdkit_tools import (
    have_rdkit,
    compute_descriptors,
    draw_2d_png,
    smiles_to_3d_sdf,
)
from .docking.swissdock import SwissDockClient
from .docking.vina import run_vina


DEFAULT_LIGANDS = [
    Ligand(name="crizotinib", notes="1st-gen ALK/ROS1/MET inhibitor (reference drug)"),
    Ligand(name="ceritinib", notes="2nd-gen ALK inhibitor"),
    Ligand(name="alectinib", notes="2nd-gen ALK inhibitor"),
    Ligand(name="brigatinib", notes="2nd-gen ALK inhibitor"),
    Ligand(name="lorlatinib", notes="3rd-gen ALK inhibitor (macrocyclic scaffold)"),
]


def _safe_slug(s: str) -> str:
    import re

    s = (s or "").strip()
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s[:80] if s else "item"


def _parse_xyz(s: str) -> tuple[float, float, float]:
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) != 3:
        raise ValueError(f"Expected x,y,z but got: {s}")
    return float(parts[0]), float(parts[1]), float(parts[2])


def _pdbqt_to_pdb(pdbqt_path: Path, out_pdb: Path) -> bool:
    """Best-effort conversion for visualization in 3Dmol.

    PDBQT is almost PDB; we truncate lines to PDB-like columns.
    This is *not* chemically perfect, but it usually renders.
    """
    try:
        lines = pdbqt_path.read_text(encoding="utf-8", errors="replace").splitlines()
        out_lines = []
        for ln in lines:
            if ln.startswith(("ATOM", "HETATM")):
                out_lines.append(ln[:66])
            elif ln.startswith("MODEL") or ln.startswith("ENDMDL") or ln.startswith("END"):
                out_lines.append(ln)
        if not out_lines:
            return False
        out_pdb.parent.mkdir(parents=True, exist_ok=True)
        out_pdb.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        return True
    except Exception:
        return False


def build_site(
    out_dir: str = "site",
    ligands_path: str = "",
    recon_path: str = "",
    receptor_path: str = "",
    pdb_id: str = "",
    docking: str = "none",
    # Back-compat alias (some earlier CLI versions used docking_backend)
    docking_backend: str = "",
    swissdock_retrieve: bool = False,
    # Back-compat alias (some earlier CLI versions used vina_path)
    vina_path: str = "",
    vina_exe: str = "vina",
    receptor_pdbqt: str = "",
    # CLI aliases: PowerShell users often pass these names
    box_center: str = "",
    box_size: str = "",
    exhaust: int = 0,
    max_poses: int = 0,
    center: str = "",
    size: str = "",
    exhaustiveness: int = 8,
    image_size: int = 420,
    no_chembl: bool = False,
    highlight_resi: list[int] | None = None,
    **_ignored: object,
) -> Path:
    """Build a static site folder with ligand cards (and optional docking)."""

    # Normalize back-compat args
    if docking_backend and (not docking or docking == "none"):
        docking = docking_backend
    if vina_path and (not vina_exe or vina_exe == "vina"):
        vina_exe = vina_path
    if box_center and not center:
        center = box_center
    if box_size and not size:
        size = box_size
    if exhaust and (not exhaustiveness or exhaustiveness == 8):
        exhaustiveness = exhaust

    out = Path(out_dir).resolve()
    data = out / "data"
    assets = out / "assets"
    out.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)

    # Copy frontend template
    # Prefer a bundled template inside the Python package (works with pip installs),
    # then fall back to the repo-root template for editable/dev runs.
    tmpl = Path(__file__).resolve().parent / "site_template"
    if not tmpl.exists():
        tmpl = Path(__file__).resolve().parent.parent / "site_template"
    for name in ["index.html", "app.js"]:
        src = tmpl / name
        if src.exists():
            shutil.copy2(src, out / name)

    # Load ligands
    if ligands_path:
        ligs = read_ligands_csv_tsv(Path(ligands_path).resolve())
    else:
        ligs = list(DEFAULT_LIGANDS)

    # Receptor/structure for viewer
    structure_url = ""
    if receptor_path:
        rp = Path(receptor_path).resolve()
        dst = assets / rp.name
        shutil.copy2(rp, dst)
        structure_url = f"assets/{dst.name}"
    elif pdb_id:
        cif = assets / f"{pdb_id.upper()}.cif"
        if not cif.exists():
            try:
                rcsb.download_mmcif(pdb_id, cif)
            except Exception as e:
                # Network/DNS issues are common in locked-down environments.
                print(f"[WARN] Could not download mmCIF for {pdb_id}: {e}")
        # If download failed, just omit the structure; the site still builds.
        structure_url = f"assets/{cif.name}" if cif.exists() else ""

    # Optional recon ingest (best-effort: just collect any case_snapshot*.json)
    cases = []
    if recon_path:
        rp = Path(recon_path).resolve()
        if rp.exists():
            for p in rp.rglob("*.json"):
                if "case_snapshot" in p.name:
                    try:
                        js = json.loads(p.read_text(encoding="utf-8"))
                        cases.append({"path": str(p), "snapshot": js})
                    except Exception:
                        continue
        (data / "cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")

    # Docking config
    dock_mode = (docking or "none").lower()
    dock_center = _parse_xyz(center) if center else None
    dock_size = _parse_xyz(size) if size else None

    # Process ligands
    rdkit_ok = have_rdkit()

    for lig in ligs:
        slug = _safe_slug(lig.name)
        lig.out_dir = f"assets/{slug}"
        lig_dir = out / lig.out_dir
        lig_dir.mkdir(parents=True, exist_ok=True)

        # PubChem enrich
        if not lig.pubchem_cid:
            try:
                lig.pubchem_cid = pubchem.resolve_name_to_cid(lig.name)
            except Exception:
                lig.pubchem_cid = ""

        props = {}
        if lig.pubchem_cid:
            try:
                props = pubchem.props_by_cid(lig.pubchem_cid)
            except Exception:
                props = {}

        # If we still don't have properties and we do have SMILES, try PubChem-by-SMILES.
        # This provides a Windows-friendly fallback when RDKit isn't installed.
        if (not props) and lig.smiles:
            try:
                props = pubchem.props_by_smiles(lig.smiles)
            except Exception:
                props = {}

        if props:
            lig.smiles = lig.smiles or props.get("CanonicalSMILES", "") or ""
            lig.iupac = props.get("IUPACName", "") or lig.iupac
            lig.formula = str(props.get("MolecularFormula", "") or lig.formula)
            lig.mw = str(props.get("MolecularWeight", "") or lig.mw)
            lig.xlogp = str(props.get("XLogP", "") or lig.xlogp)
            lig.hbd = str(props.get("HBondDonorCount", "") or lig.hbd)
            lig.hba = str(props.get("HBondAcceptorCount", "") or lig.hba)
            lig.tpsa = str(props.get("TPSA", "") or lig.tpsa)
            lig.rotb = str(props.get("RotatableBondCount", "") or lig.rotb)

        # Optional ChEMBL id
        if (not no_chembl) and (not lig.chembl_id):
            try:
                lig.chembl_id = chembl.name_search(lig.name)
            except Exception:
                lig.chembl_id = ""

        # 2D image
        img_path = lig_dir / f"{slug}_2d.png"
        ok = False
        if lig.pubchem_cid:
            try:
                ok = pubchem.download_png_by_cid(lig.pubchem_cid, img_path, size=image_size)
            except Exception:
                ok = False
        # PubChem-by-SMILES fallback (works without RDKit)
        if (not ok) and lig.smiles:
            try:
                ok = pubchem.download_png_by_smiles(lig.smiles, img_path, size=image_size)
            except Exception:
                ok = False
        if (not ok) and lig.smiles and rdkit_ok:
            ok = draw_2d_png(lig.smiles, img_path, size=image_size)
        if ok:
            lig.image_png = f"{lig.out_dir}/{img_path.name}"

        # RDKit descriptors + optional 3D
        if lig.smiles and rdkit_ok:
            try:
                desc = compute_descriptors(lig.smiles)
                lig.descriptors.update(desc)
                # fill missing numeric fields (if PubChem missing)
                lig.mw = lig.mw or str(desc.get("MW", ""))
                lig.xlogp = lig.xlogp or str(desc.get("LogP", ""))
                lig.hbd = lig.hbd or str(desc.get("HBD", ""))
                lig.hba = lig.hba or str(desc.get("HBA", ""))
                lig.tpsa = lig.tpsa or str(desc.get("TPSA", ""))
            except Exception:
                pass

            # 3D conformer
            try:
                sdf = lig_dir / f"{slug}_3d.sdf"
                ok3d = smiles_to_3d_sdf(lig.smiles, sdf)
                if ok3d:
                    lig.ligand3d = f"{lig.out_dir}/{sdf.name}"
            except Exception:
                pass

        # Optional docking
        if dock_mode in {"swissdock", "vina"}:
            if not dock_center or not dock_size:
                lig.docking = {"backend": dock_mode, "error": "Docking requested but --center/--size not provided"}
            else:
                if dock_mode == "swissdock":
                    # requires obabel if you only have SMILES
                    receptor = Path(receptor_path).resolve() if receptor_path else None
                    if receptor is None or not receptor.exists():
                        lig.docking = {"backend": "swissdock", "error": "SwissDock needs --receptor (PDB file)."}
                    elif not lig.smiles:
                        lig.docking = {"backend": "swissdock", "error": "SwissDock needs SMILES (or extend client to upload MOL2)."}
                    else:
                        client = SwissDockClient()
                        try:
                            session = client.submit_vina_from_smiles(
                                name=lig.name,
                                smiles=lig.smiles,
                                receptor_pdb=receptor,
                                center=dock_center,
                                size=dock_size,
                                exhaust=exhaustiveness,
                                work_dir=lig_dir,
                            )
                            lig.docking = {"backend": "swissdock", "session": session, "center": dock_center, "size": dock_size}

                            if swissdock_retrieve:
                                tgz = lig_dir / f"{slug}_swissdock.tgz"
                                client.retrieve_session(session, tgz)
                                lig.docking["result_archive"] = f"{lig.out_dir}/{tgz.name}"
                        except Exception as e:
                            lig.docking = {"backend": "swissdock", "error": str(e)}

                elif dock_mode == "vina":
                    # expects receptor_pdbqt and ligand_pdbqt
                    if not receptor_pdbqt:
                        lig.docking = {"backend": "vina", "error": "Vina requires --receptor-pdbqt"}
                    elif not lig.smiles:
                        lig.docking = {"backend": "vina", "error": "Vina path here expects you provide ligand PDBQT (extend to auto-prep)."}
                    else:
                        # best-effort: create ligand PDBQT via obabel if present
                        ligand_pdbqt = lig_dir / f"{slug}.pdbqt"
                        try:
                            import subprocess

                            cmd = [
                                "obabel",
                                f"-:{lig.smiles}",
                                "--gen3d",
                                "-O",
                                str(ligand_pdbqt),
                                "-h",
                            ]
                            subprocess.run(cmd, check=True, capture_output=True, text=True)
                            out_pose = lig_dir / f"{slug}_vina_out.pdbqt"
                            out_log = lig_dir / f"{slug}_vina.log"
                            meta = run_vina(
                                vina_exe=vina_exe,
                                receptor_pdbqt=Path(receptor_pdbqt).resolve(),
                                ligand_pdbqt=ligand_pdbqt,
                                out_pdbqt=out_pose,
                                log_path=out_log,
                                center=dock_center,
                                size=dock_size,
                                exhaustiveness=exhaustiveness,
                            )
                            lig.docking = meta
                            lig.docking["pose"] = f"{lig.out_dir}/{out_pose.name}"
                            lig.docking["log"] = f"{lig.out_dir}/{out_log.name}"

                            # create PDB for 3Dmol viewer
                            pose_pdb = lig_dir / f"{slug}_vina_pose.pdb"
                            if _pdbqt_to_pdb(out_pose, pose_pdb):
                                lig.pose = {"format": "pdb", "path": f"{lig.out_dir}/{pose_pdb.name}"}
                        except Exception as e:
                            lig.docking = {"backend": "vina", "error": str(e)}

    # Write JSON outputs
    (data / "molecules.json").write_text(
        json.dumps([lig.to_dict() for lig in ligs], indent=2),
        encoding="utf-8",
    )

    # Frontend uses this list to highlight "hot" residues in the 3D view.
    # Default: ALK gatekeeper (L1196) + solvent-front (G1202).
    hot = highlight_resi if highlight_resi else [1196, 1202]
    manifest = {
        "project": "ALK-VisDock",
        "structure_url": structure_url,
        "highlight_resi": hot,
        "has_cases": bool(cases),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return out
