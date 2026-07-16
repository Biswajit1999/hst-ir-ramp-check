"""Shared synthetic-data fixtures for tests.

The synthetic-data model lives in
`hst_wfc3ir_ramp_linearity_audit.synthetic` (shared with
`scripts/make_figures.py --demo`); this module only adds the pytest fixture
layer on top.
"""
from __future__ import annotations

import pytest

from hst_wfc3ir_ramp_linearity_audit.synthetic import (
    DEFAULT_SAMPTIMES,
    SyntheticRampSpec,
    build_synthetic_ima_hdulist,
    synthetic_ramp_counts,
)

__all__ = [
    "DEFAULT_SAMPTIMES",
    "SyntheticRampSpec",
    "build_synthetic_ima_hdulist",
    "synthetic_ramp_counts",
    "synthetic_ima_path",
]


@pytest.fixture
def synthetic_ima_path(tmp_path):
    """A (path, spec) pair: a synthetic IMA file with a known injected ramp + curvature."""
    spec = SyntheticRampSpec(count_rate=5.0, curvature=0.0002, read_noise=15.0)
    hdul = build_synthetic_ima_hdulist(spec=spec, cosmic_ray_read_index=3)
    path = tmp_path / "synthetic_ima.fits"
    hdul.writeto(path)
    return path, spec
