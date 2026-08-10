"""Location resolution, the precision gate, and projections."""

from .loader import load_admin_units, load_anchor
from .rings import assign_rings
from .straddle import owning_gmina

__all__ = ["assign_rings", "load_admin_units", "load_anchor", "owning_gmina"]
