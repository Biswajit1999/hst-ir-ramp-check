from __future__ import annotations

import numpy as np
import pytest

from hst_wfc3ir_ramp_linearity_audit.exceptions import InsufficientDataError
from hst_wfc3ir_ramp_linearity_audit.fluence_bins import bin_scalar_statistic


def test_bin_scalar_statistic_computes_mean_per_bin():
    keys = np.array([1.0, 1.5, 5.0, 5.5])
    values = np.array([10.0, 12.0, 100.0, 104.0])
    result = bin_scalar_statistic(keys, values, edges=np.array([0.0, 3.0, 6.0]), minimum_sample_size=1)
    assert len(result.bins) == 2
    assert result.bins[0].mean == pytest.approx(11.0)
    assert result.bins[1].mean == pytest.approx(102.0)
    assert not result.bins[0].underpopulated


def test_bin_scalar_statistic_flags_underpopulated_bins():
    keys = np.array([1.0, 2.0, 3.0])
    values = np.array([1.0, 2.0, 3.0])
    result = bin_scalar_statistic(keys, values, edges=np.array([0.0, 5.0]), minimum_sample_size=10)
    assert result.bins[0].underpopulated
    assert len(result.warnings) == 1


def test_bin_scalar_statistic_rejects_mismatched_shapes():
    with pytest.raises(InsufficientDataError):
        bin_scalar_statistic(np.array([1.0, 2.0]), np.array([1.0]), edges=np.array([0.0, 3.0]), minimum_sample_size=1)


def test_bin_scalar_statistic_rejects_bad_edges():
    with pytest.raises(InsufficientDataError):
        bin_scalar_statistic(np.array([1.0]), np.array([1.0]), edges=np.array([0.0]), minimum_sample_size=1)
