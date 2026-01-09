# Usage (PowerShell):
#   python -m venv .venv
#   .\.venv\Scripts\Activate.ps1
#   pip install -r requirements-core.txt
#   # Optional: pip install -r requirements-chem.txt
#   python -m alk_visdock build --out site --ligands examples\ligands.csv --pdb-id 2XP2
#   python -m alk_visdock serve --site site --port 8000
