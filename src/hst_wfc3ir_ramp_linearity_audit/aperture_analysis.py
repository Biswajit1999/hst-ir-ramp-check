"""Ramp extraction for a chosen pixel or small aperture from a loaded IMA product."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hst_wfc3ir_ramp_linearity_audit.exceptions import InsufficientDataError
from hst_wfc3ir_ramp_linearity_audit.ima_io import IMAProduct


def assign_quadrant(x: int, y: int, nx: int, ny: int) -> str:
    """Assign a coarse quadrant label from pixel position.

    ASSUMPTION (documented, not independently verified against real WFC3/IR
    amplifier-corner geometry): quadrants are assigned by simple
    array-center splitting (bottom/top x left/right), not the exact physical
    amplifier layout. Sufficient to test whether the linearity signature
    varies across the array, which is the bounded question here.
    """
    horiz = "L" if x < nx / 2 else "R"
    vert = "B" if y < ny / 2 else "T"
    return f"{vert}{horiz}"


@dataclass(frozen=True)
class ExtractedRamp:
    x: int
    y: int
    quadrant: str
    samptimes: np.ndarray
    counts: np.ndarray
    uncertainty: np.ndarray
    dq: np.ndarray  # bitwise-OR of the aperture's DQ per read, shape (n_reads,)


def extract_ramp(product: IMAProduct, x: int, y: int, aperture_radius: int = 0) -> ExtractedRamp:
    """Extract accumulated-counts-vs-time for a pixel or small square aperture.

    Raises InsufficientDataError if the product has no reads or the
    requested pixel is outside the array.
    """
    if not product.reads:
        raise InsufficientDataError("IMA product has no reads")
    ny, nx = product.reads[0].science.shape
    if not (0 <= x < nx and 0 <= y < ny):
        raise InsufficientDataError(f"pixel ({x},{y}) is outside the array ({nx}x{ny})")

    n_reads = len(product.reads)
    samptimes = np.array([r.samptime for r in product.reads])
    counts = np.empty(n_reads)
    uncertainty = np.empty(n_reads)
    dq = np.empty(n_reads, dtype=np.int64)

    y0, y1 = max(0, y - aperture_radius), min(ny, y + aperture_radius + 1)
    x0, x1 = max(0, x - aperture_radius), min(nx, x + aperture_radius + 1)

    for i, r in enumerate(product.reads):
        counts[i] = float(np.sum(r.science[y0:y1, x0:x1]))
        uncertainty[i] = float(np.sqrt(np.sum(r.uncertainty[y0:y1, x0:x1] ** 2)))
        dq[i] = int(np.bitwise_or.reduce(r.dq_mask[y0:y1, x0:x1], axis=None))

    return ExtractedRamp(
        x=x, y=y, quadrant=assign_quadrant(x, y, nx, ny),
        samptimes=samptimes, counts=counts, uncertainty=uncertainty, dq=dq,
    )
