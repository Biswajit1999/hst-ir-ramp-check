from __future__ import annotations

import numpy as np
import pytest

from hst_wfc3ir_ramp_linearity_audit.dq_masks import (
    DEFAULT_EXCLUSION_MASK,
    SATPIXEL,
    SPIKE,
    cosmic_ray_fraction,
    exclusion_mask,
    is_flagged,
)
from hst_wfc3ir_ramp_linearity_audit.exceptions import DataSchemaError, InsufficientDataError


def test_is_flagged_detects_set_bit():
    values = np.array([0, 16, 1024, 1040])
    assert list(is_flagged(values, SPIKE)) == [False, False, True, True]


def test_cosmic_ray_fraction_counts_correctly():
    dq_stack = np.zeros((10, 5, 5), dtype=np.int64)
    dq_stack[3, 2, 2] = SPIKE
    dq_stack[7, 0, 0] = SPIKE
    result = cosmic_ray_fraction(dq_stack)
    assert result.n_flagged == 2
    assert result.n_total == 10 * 5 * 5
    assert result.fraction == pytest.approx(2 / 250)


def test_cosmic_ray_fraction_rejects_empty_array():
    with pytest.raises(InsufficientDataError):
        cosmic_ray_fraction(np.array([]))


def test_cosmic_ray_fraction_rejects_scalar():
    with pytest.raises(DataSchemaError):
        cosmic_ray_fraction(np.array(5))


def test_exclusion_mask_flags_saturation_and_spike():
    dq = np.array([0, SATPIXEL, SPIKE, SATPIXEL | SPIKE, 16])
    mask = exclusion_mask(dq, DEFAULT_EXCLUSION_MASK)
    assert list(mask) == [False, True, True, True, False]
