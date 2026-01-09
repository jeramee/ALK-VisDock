from __future__ import annotations

import argparse
import sys

from .build import build_site
from .server import serve


def _build_cmd(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="alkvisdock build")
    ap.add_argument("--out", default="site", help="Output site directory")
    ap.add_argument("--ligands", default="", help="CSV/TSV with columns: name,smiles,pubchem_cid,notes")
    ap.add_argument("--pdb-id", default="", help="Optional RCSB PDB id to embed structure viewer (downloads mmCIF)")
    ap.add_argument("--receptor", default="", help="Optional local receptor file (PDB or mmCIF). Copied to site.")
    ap.add_argument("--highlight", default="1196,1202", help="Comma-separated residue numbers to highlight")
    ap.add_argument("--docking", choices=["none", "vina", "swissdock"], default="none", help="Docking backend")
    ap.add_argument("--vina-path", default="vina", help="Path to AutoDock Vina binary (when --docking vina)")
    ap.add_argument("--receptor-pdbqt", default="", help="Receptor PDBQT (required for Vina)")
    ap.add_argument("--box-center", default="", help='Docking box center: "x,y,z" (required for docking)')
    ap.add_argument("--box-size", default="", help='Docking box size: "sx,sy,sz" (required for docking)')
    ap.add_argument("--exhaust", type=int, default=8, help="Vina exhaustiveness")
    ap.add_argument("--max", type=int, default=50, help="Max ligands to process")
    ap.add_argument("--recon", default="", help="Optional path to ALK-RECON outputs folder (case_snapshot*.json)")

    args = ap.parse_args(argv)

    highlight = [int(x) for x in args.highlight.split(",") if x.strip()]
    box_center = tuple(float(x) for x in args.box_center.split(",")) if args.box_center else None
    box_size = tuple(float(x) for x in args.box_size.split(",")) if args.box_size else None

    build_site(
        out_dir=args.out,
        ligands_path=args.ligands or None,
        pdb_id=args.pdb_id or None,
        receptor_path=args.receptor or None,
        highlight_resi=highlight,
        docking=args.docking,
        vina_path=args.vina_path,
        receptor_pdbqt=args.receptor_pdbqt or None,
        box_center=box_center,
        box_size=box_size,
        exhaust=args.exhaust,
        max_ligands=args.max,
        recon_path=args.recon or None,
    )
    return 0


def _serve_cmd(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="alkvisdock serve")
    ap.add_argument("--site", default="site", help="Site directory built by alkvisdock build")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)
    serve(site_dir=args.site, host=args.host, port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print(
            "ALK-VisDock\n\n"
            "Commands:\n"
            "  build   Build a local browsable site (cards + optional docking/structure viewer)\n"
            "  serve   Serve the site with a local FastAPI server\n\n"
            "Examples:\n"
            "  python -m alk_visdock build --out site --ligands examples/ligands.csv --pdb-id 2XP2\n"
            "  python -m alk_visdock serve --site site\n"
        )
        return 0

    cmd, rest = argv[0], argv[1:]
    if cmd == "build":
        return _build_cmd(rest)
    if cmd == "serve":
        return _serve_cmd(rest)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
