from __future__ import annotations

import pytest

from hst_wfc3ir_ramp_linearity_audit.aperture_analysis import assign_quadrant, extract_ramp
from hst_wfc3ir_ramp_linearity_audit.exceptions import InsufficientDataError
from hst_wfc3ir_ramp_linearity_audit.ima_io import load_ima


def test_assign_quadrant_four_corners():
    assert assign_quadrant(2, 2, 10, 10) == "BL"
    assert assign_quadrant(8, 2, 10, 10) == "BR"
    assert assign_quadrant(2, 8, 10, 10) == "TL"
    assert assign_quadrant(8, 8, 10, 10) == "TR"


def test_extract_ramp_matches_known_source(synthetic_ima_path):
    path, spec = synthetic_ima_path
    product = load_ima(path)
    ramp = extract_ramp(product, x=10, y=10, aperture_radius=0)
    assert ramp.samptimes.size == spec.samptimes.size
    assert ramp.counts.size == spec.samptimes.size
    # counts should generally increase with time (allowing for noise)
    assert ramp.counts[-1] > ramp.counts[0]


def test_extract_ramp_flags_cosmic_ray_read(synthetic_ima_path):
    path, spec = synthetic_ima_path
    product = load_ima(path)
    ramp = extract_ramp(product, x=10, y=10, aperture_radius=0)
    assert (ramp.dq != 0).any()


def test_extract_ramp_rejects_pixel_outside_array(synthetic_ima_path):
    path, spec = synthetic_ima_path
    product = load_ima(path)
    with pytest.raises(InsufficientDataError):
        extract_ramp(product, x=1000, y=1000)
