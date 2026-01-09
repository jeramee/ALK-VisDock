# ALK-VisDock (visual + docking pipeline)

**Goal:** take ligand inputs (SMILES / PubChem IDs / SDF) and generate a **local, browsable UI** of “drug cards” for ALK research:

- ✅ 2D structure images (PubChem PNG preferred; RDKit fallback)
- ✅ key properties (MW, XLogP, HBD/HBA, TPSA, RotB, formula)
- ✅ optional receptor viewer (3Dmol.js) using an ALK mmCIF pulled from RCSB
- ✅ optional docking:
  - local **AutoDock Vina** (private, fast) if installed
  - remote **SwissDock** (Vina backend) with session tracking
- ✅ output is a **static site** + a tiny local server for browsing

> Research/visualization only. This project does **not** provide chemical synthesis steps or “how to make” instructions.

---

## What you get in the output folder

When you run `build`, it creates:

```
site/
  index.html
  app.js
  manifest.json
  data/
    molecules.json
    recon_cases.json          # optional, if you point it at ALK-RECON outputs
  assets/
    ligands/<name>.png        # 2D structure image
    receptor/ALK.cif          # optional, if you pass --pdb-id
    docking/<name>/...        # optional, if docking enabled
```

Open the UI via the included server:

- Ligand list + filters
- Click a ligand card to load its pose (if you generated one)
- 3Dmol ALK viewer with hotspot residue highlighting

---

## Quickstart

### 1) Install

Core web/server deps:

```bash
pip install -r requirements-core.txt
```

Optional chemistry:

- **Fastest / simplest:** keep going with pip (project runs fine without RDKit; it will fall back to PubChem images).

  ```bash
  pip install -r requirements-chem.txt
  ```

- **Best on Windows (recommended):** use conda-forge for RDKit + OpenBabel.

  ```bash
  conda env create -f environment.yml
  conda activate alk-visdock

  # NOTE: `conda install -r <file>` is not a thing; use env YAML or install packages one-by-one.
  ```

  Then (optional, but nice for editable dev installs):

  ```bash
  pip install -e .
  ```

### 2) Build a site

Use the built-in ALK drug list:

```bash
python -m alk_visdock build --out site --pdb-id 2XP2
```

Or provide your own ligands file:

```bash
python -m alk_visdock build --out site \
  --ligands examples/ligands.csv \
  --pdb-id 2XP2
```

### 3) Serve the UI

```bash
python -m alk_visdock serve --site site --port 8000
```

Then open:

- http://127.0.0.1:8000

---

## Docking options

### A) Local AutoDock Vina

If you have `vina` installed and you can produce a receptor PDBQT + ligand PDBQT:

```bash
python -m alk_visdock build --out site \
  --ligands examples/ligands.csv \
  --receptor-pdbqt path/to/ALK.pdbqt \
  --docking vina \
  --vina path/to/vina.exe \
  --center 10.5 22.1 -3.4 \
  --size 22 22 22
```

The pipeline writes `site/assets/docking/<ligand>/vina_out.pdbqt` plus a parsed best score.

### B) SwissDock (remote)

SwissDock requires converting SMILES to MOL2 (OpenBabel `obabel` recommended) and is network-dependent.

```bash
python -m alk_visdock build --out site \
  --ligands examples/ligands.csv \
  --receptor-pdb path/to/ALK.pdb \
  --docking swissdock
```

This stores the SwissDock session ID per ligand in `molecules.json`.

---

## Using ALK-RECON outputs

If you already ran **ALK-RECON** and have case snapshot JSONs, point ALK-VisDock at that folder:

```bash
python -m alk_visdock build --out site \
  --ligands examples/ligands.csv \
  --recon /path/to/alk-recon/outputs
```

ALK-VisDock will bundle a compact `recon_cases.json` into the site.

---

## Files to edit

- `examples/ligands.csv` – your candidate list (name + smiles + optional CID)
- `site_template/index.html` + `site_template/app.js` – frontend
- `alk_visdock/build.py` – pipeline orchestrator
- `alk_visdock/docking/*` – docking backends

---

## Safety note

This repo is intended for **visualization, annotation, and docking exploration**.
It deliberately avoids any content that would help synthesize controlled substances or create harmful compounds.
