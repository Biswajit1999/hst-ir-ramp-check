"""Synthetic WFC3/IR-MULTIACCUM-like ramp generation, clearly labelled and never real data.

Sample times are a plausible, monotonically-increasing illustrative sequence,
not a reproduction of any specific named real WFC3/IR sample sequence
(SPARS/STEP/etc.) — this is a labelled-synthetic model for validating the
fitting pipeline, not a simulation claiming instrumental fidelity.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from astropy.io import fits

DEFAULT_SAMPTIMES = np.array([0.0, 2.9, 8.6, 16.9, 27.9, 41.6, 58.1, 77.3, 99.3, 124.1])


@dataclass(frozen=True)
class SyntheticRampSpec:
    count_rate: float  # electrons/second, true illumination rate
    curvature: float = 0.0  # nonlinearity coefficient; measured deficit grows as curvature * fluence
    read_noise: float = 15.0  # electrons per read (illustrative)
    samptimes: np.ndarray = field(default_factory=lambda: DEFAULT_SAMPTIMES.copy())


def synthetic_ramp_counts(spec: SyntheticRampSpec, seed: int = 20260713) -> np.ndarray:
    """Accumulated counts (electrons) at each sample time for one synthetic pixel/aperture.

    Nonlinearity model: measured accumulated counts = true linear accumulation
    minus a quadratic deficit growing with accumulated fluence
    (`curvature * (count_rate * t)^2`), matching the qualitative behaviour
    described in the verified WFC3/IR nonlinearity literature (deficit grows
    with accumulated signal), not a specific calibration model.
    """
    rng = np.random.default_rng(seed)
    true_fluence = spec.count_rate * spec.samptimes
    deficit = spec.curvature * true_fluence**2
    mean_counts = np.clip(true_fluence - deficit, 0.0, None)

    shot_noise = rng.normal(0.0, np.sqrt(np.clip(mean_counts, 1.0, None)))
    read_noise = rng.normal(0.0, spec.read_noise, size=spec.samptimes.shape)
    return mean_counts + shot_noise + read_noise


def build_synthetic_ima_hdulist(
    *,
    seed: int = 20260713,
    size: int = 20,
    spec: SyntheticRampSpec = SyntheticRampSpec(count_rate=5.0, curvature=0.0002),
    cosmic_ray_read_index: int | None = None,
) -> fits.HDUList:
    """Build a small, labelled-synthetic WFC3/IR-IMA-like HDUList.

    Mimics the real IMA extension convention (verified against the WFC3
    Data Handbook documentation): one (SCI, ERR, DQ) triplet per
    non-destructive read, EXTVER=1 is the LAST (deepest) read, increasing
    EXTVER moves toward the first (shallowest) read; each SCI header carries
    SAMPTIME for that read.
    """
    rng = np.random.default_rng(seed)
    n_reads = spec.samptimes.size
    hdus: list[fits.hdu.base._BaseHDU] = [fits.PrimaryHDU()]
    hdus[0].header["INSTRUME"] = "WFC3"
    hdus[0].header["DETECTOR"] = "IR"
    hdus[0].header["NSAMP"] = n_reads

    # EXTVER=1 (last read) has the longest SAMPTIME; EXTVER=NSAMP (first read) has SAMPTIME~0.
    order = np.argsort(-spec.samptimes)  # descending: longest exposure first -> EXTVER=1
    for extver, read_idx in enumerate(order, start=1):
        t = spec.samptimes[read_idx]
        true_fluence = spec.count_rate * t
        deficit = spec.curvature * true_fluence**2
        mean_counts = max(true_fluence - deficit, 0.0)
        science = np.full((size, size), mean_counts)
        dq = np.zeros((size, size), dtype=np.int16)
        science += rng.normal(0.0, np.sqrt(max(mean_counts, 1.0)), size=(size, size))
        science += rng.normal(0.0, spec.read_noise, size=(size, size))
        err = np.full((size, size), np.sqrt(max(mean_counts, 1.0) + spec.read_noise**2))

        if cosmic_ray_read_index is not None and read_idx == cosmic_ray_read_index:
            cy, cx = size // 2, size // 2
            science[cy, cx] += 2000.0
            dq[cy, cx] = 1024  # SPIKE: CR spike detected during cridcalc IR (verified spacetelescope/hstcal wf3dq.h)

        sci_header = fits.Header()
        sci_header["EXTNAME"] = "SCI"
        sci_header["EXTVER"] = extver
        sci_header["SAMPTIME"] = float(t)
        sci_header["SAMPNUM"] = int(extver)
        hdus.append(fits.ImageHDU(data=science.astype(np.float32), header=sci_header, name="SCI", ver=extver))

        err_header = sci_header.copy()
        err_header["EXTNAME"] = "ERR"
        hdus.append(fits.ImageHDU(data=err.astype(np.float32), header=err_header, name="ERR", ver=extver))

        dq_header = sci_header.copy()
        dq_header["EXTNAME"] = "DQ"
        hdus.append(fits.ImageHDU(data=dq, header=dq_header, name="DQ", ver=extver))

    return fits.HDUList(hdus)
