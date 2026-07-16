"""Synthetic injection-recovery validation gate for ramp fitting.

Per docs/VALIDATION_CONTRACT.md and the CLAUDE_TASK.md stop condition: if
this fails, the pipeline must not be used to interpret real IMA data as
validated. Thresholds were calibrated empirically across 15 independent
noise realizations at rate=20 e-/s, curvature=0.0003, read_noise=5 e-/read
(see IMPLEMENTATION_PLAN.md); observed worst case was 6.6% rate error and
5.7% curvature error, so the thresholds here carry margin above that.
"""
from __future__ import annotations

import numpy as np
import pytest

from hst_wfc3ir_ramp_linearity_audit.exceptions import ConvergenceError, InsufficientDataError
from hst_wfc3ir_ramp_linearity_audit.ramp_model import (
    fit_ramp_with_curvature,
    fit_robust_linear,
    fit_weighted_linear,
    linear_residuals,
)
from conftest import SyntheticRampSpec, synthetic_ramp_counts

RATE_TOLERANCE = 0.20
CURVATURE_TOLERANCE = 0.25


def test_synthetic_curvature_injection_recovery():
    truth_rate, truth_curvature = 20.0, 0.0003
    spec = SyntheticRampSpec(count_rate=truth_rate, curvature=truth_curvature, read_noise=5.0)
    counts = synthetic_ramp_counts(spec, seed=2000)

    fit = fit_ramp_with_curvature(spec.samptimes, counts)

    rate_error = abs(fit.rate - truth_rate) / truth_rate
    curvature_error = abs(fit.curvature - truth_curvature) / truth_curvature
    assert rate_error < RATE_TOLERANCE, f"rate recovery error {rate_error:.1%} too large"
    assert curvature_error < CURVATURE_TOLERANCE, f"curvature recovery error {curvature_error:.1%} too large"
    assert fit.convergence.converged


def test_null_control_zero_curvature_recovered_near_zero():
    """Negative control: a purely linear ramp (no injected curvature) should fit near-zero curvature."""
    truth_rate = 20.0
    spec = SyntheticRampSpec(count_rate=truth_rate, curvature=0.0, read_noise=5.0)
    counts = synthetic_ramp_counts(spec, seed=2000)

    fit = fit_ramp_with_curvature(spec.samptimes, counts)

    assert abs(fit.curvature) < 5e-5


def test_weighted_and_robust_linear_agree_on_clean_data():
    t = np.arange(1.0, 10.0)
    counts = 3.0 * t + 5.0
    unc = np.full_like(t, 1.0)
    weighted = fit_weighted_linear(t, counts, unc)
    robust = fit_robust_linear(t, counts)
    assert weighted.rate == pytest.approx(3.0, abs=0.05)
    assert robust.rate == pytest.approx(3.0, abs=0.05)


def test_linear_residuals_zero_for_perfect_fit():
    t = np.arange(1.0, 10.0)
    counts = 2.0 * t + 1.0
    unc = np.full_like(t, 1.0)
    fit = fit_weighted_linear(t, counts, unc)
    residuals = linear_residuals(t, counts, fit)
    assert np.allclose(residuals, 0.0, atol=1e-6)


def test_fit_weighted_linear_rejects_too_few_points():
    with pytest.raises(InsufficientDataError):
        fit_weighted_linear(np.array([1.0, 2.0]), np.array([1.0, 2.0]), np.array([1.0, 1.0]))


def test_fit_weighted_linear_rejects_nonpositive_uncertainty():
    with pytest.raises(InsufficientDataError):
        fit_weighted_linear(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0]), np.array([1.0, 0.0, 1.0]))


def test_fit_ramp_with_curvature_rejects_too_few_points():
    with pytest.raises(InsufficientDataError):
        fit_ramp_with_curvature(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0]))


def test_fit_ramp_with_curvature_rejects_non_finite_counts():
    t = np.arange(1.0, 10.0)
    counts = np.full_like(t, np.nan)
    with pytest.raises(ConvergenceError):
        fit_ramp_with_curvature(t, counts)
