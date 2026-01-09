from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple


def have_rdkit() -> bool:
    try:
        import rdkit  # noqa: F401
        return True
    except Exception:
        return False


def smiles_to_mol(smiles: str):
    from rdkit import Chem
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("Could not parse SMILES")
    return mol


def descriptors(smiles: str) -> dict[str, str]:
    """Return a small descriptor set as strings for easy JSON."""
    from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors
    mol = smiles_to_mol(smiles)
    return {
        "mw": f"{Descriptors.MolWt(mol):.2f}",
        "xlogp": f"{Crippen.MolLogP(mol):.2f}",
        "hbd": str(rdMolDescriptors.CalcNumHBD(mol)),
        "hba": str(rdMolDescriptors.CalcNumHBA(mol)),
        "tpsa": f"{rdMolDescriptors.CalcTPSA(mol):.2f}",
        "rotb": str(rdMolDescriptors.CalcNumRotatableBonds(mol)),
    }


def draw_2d_png(smiles: str, out_png: Path, size: int = 420) -> None:
    from rdkit import Chem
    from rdkit.Chem import Draw
    mol = smiles_to_mol(smiles)
    img = Draw.MolToImage(mol, size=(size, size))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_png))


def smiles_to_3d_sdf(smiles: str, out_sdf: Path, max_iters: int = 200) -> None:
    """Embed + MMFF optimize; writes 1 conformer SDF."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.AddHs(smiles_to_mol(smiles))
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    res = AllChem.EmbedMolecule(mol, params)
    if res != 0:
        # fall back with random coordinates
        res = AllChem.EmbedMolecule(mol, randomSeed=42, useRandomCoords=True)
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=max_iters)
    except Exception:
        try:
            AllChem.UFFOptimizeMolecule(mol, maxIters=max_iters)
        except Exception:
            pass

    out_sdf.parent.mkdir(parents=True, exist_ok=True)
    w = Chem.SDWriter(str(out_sdf))
    w.write(mol)
    w.close()

# Backward-compatible alias used by the builder
def compute_descriptors(smiles: str) -> dict[str, str]:
    return descriptors(smiles)
