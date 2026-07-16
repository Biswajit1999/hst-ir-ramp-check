"""WFC3/IR data-quality bit interpretation.

Bit values verified directly against the real CALWF3 source
(spacetelescope/hstcal, pkg/wfc3/include/wf3dq.h), not assumed from memory.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hst_wfc3ir_ramp_linearity_audit.exceptions import DataSchemaError, InsufficientDataError

# Verified bit values (spacetelescope/hstcal, pkg/wfc3/include/wf3dq.h)
HOTPIX = 16
UNSTABLE = 32  # IR-specific: "IR unstable pixel"
WARMPIX = 64
SATPIXEL = 256  # full-well saturated pixel
SPIKE = 1024  # IR-specific: "CR spike detected during cridcalc IR"
ZEROSIG = 2048  # IR-specific: "IR zero-read signal correction"
DATAREJECT = 8192  # rejected during image combination
HIGH_CURVATURE = 16384  # "pixel has more than max CR's"

# Bits treated as excluding a read from the linearity fit for this audit.
DEFAULT_EXCLUSION_MASK = SPIKE | SATPIXEL | DATAREJECT | HIGH_CURVATURE


def is_flagged(dq_value: int | np.ndarray, bit: int) -> np.ndarray:
    return (np.asarray(dq_value, dtype=np.int64) & bit) != 0


@dataclass(frozen=True)
class CosmicRayFraction:
    n_flagged: int
    n_total: int
    fraction: float


def cosmic_ray_fraction(dq_stack: np.ndarray, bit: int = SPIKE) -> CosmicRayFraction:
    """Fraction of pixel-reads flagged with `bit` (default SPIKE) across a DQ stack.

    `dq_stack` is expected to have shape (n_reads, ...); raises
    DataSchemaError if it has fewer than 1 dimension.
    """
    dq_stack = np.asarray(dq_stack)
    if dq_stack.ndim < 1:
        raise DataSchemaError("dq_stack must have at least 1 dimension (n_reads, ...)")
    flagged = is_flagged(dq_stack, bit)
    n_total = int(flagged.size)
    if n_total == 0:
        raise InsufficientDataError("dq_stack is empty")
    n_flagged = int(np.sum(flagged))
    return CosmicRayFraction(n_flagged=n_flagged, n_total=n_total, fraction=n_flagged / n_total)


def exclusion_mask(dq_value: np.ndarray, mask: int = DEFAULT_EXCLUSION_MASK) -> np.ndarray:
    """Boolean array: True where a pixel-read should be excluded from the linearity fit."""
    return is_flagged(dq_value, mask)
