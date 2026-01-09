"""Docking backends.

This package is intentionally optional-dependency friendly.

The project can run in a "no-RDKit / no-Vina" mode where it only builds a
visual drug gallery using PubChem/ChEMBL + an ALK structure viewer.
"""

from .swissdock import SwissDockClient

# Vina is optional (CLI binary + helper code). Import defensively so a missing
# function or missing optional deps doesn't break the whole app at import-time.
try:
    from .vina import dock_vina  # noqa: F401
except Exception:  # pragma: no cover
    dock_vina = None  # type: ignore

__all__ = ["SwissDockClient", "dock_vina"]
