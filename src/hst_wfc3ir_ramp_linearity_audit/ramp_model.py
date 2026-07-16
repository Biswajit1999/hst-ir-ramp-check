"""Up-the-ramp linear and nonlinearity model fitting.

Nonlinearity model: `counts(t) = rate*t - curvature*(rate*t)^2 + offset`,
matching the synthetic injection model in `synthetic.py` (deficit grows with
the square of accumulated fluence) — a simple, self-consistent empirical
model for this bounded audit, not a physical trap-capture simulation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import theilslopes

from hst_wfc3ir_ramp_linearity_audit.exceptions import ConvergenceError, InsufficientDataError
from hst_wfc3ir_ramp_linearity_audit.uncertainty import FitConvergence, check_fit_convergence

_MIN_POINTS_LINEAR = 3
_MIN_POINTS_CURVATURE = 4


@dataclass(frozen=True)
class LinearFitResult:
    rate: float
    offset: float
    method: str  # "weighted" or "robust"


def fit_weighted_linear(t: np.ndarray, counts: np.ndarray, uncertainty: np.ndarray) -> LinearFitResult:
    """Weighted least-squares linear fit (weights = 1/uncertainty^2)."""
    t, counts, uncertainty = np.asarray(t, float), np.asarray(counts, float), np.asarray(uncertainty, float)
    if t.size < _MIN_POINTS_LINEAR:
        raise InsufficientDataError(f"need at least {_MIN_POINTS_LINEAR} points for a linear fit, got {t.size}")
    if np.any(uncertainty <= 0) or not np.all(np.isfinite(uncertainty)):
        raise InsufficientDataError("uncertainty must be finite and positive for a weighted fit")

    weights = 1.0 / uncertainty**2
    design = np.column_stack([t, np.ones_like(t)])
    w_design = design * weights[:, None]
    try:
        params, *_ = np.linalg.lstsq(w_design.T @ design, w_design.T @ counts, rcond=None)
    except np.linalg.LinAlgError as exc:
        raise ConvergenceError(f"weighted linear fit failed: {exc}") from exc
    if not np.all(np.isfinite(params)):
        raise ConvergenceError("weighted linear fit returned non-finite parameters")
    return LinearFitResult(rate=float(params[0]), offset=float(params[1]), method="weighted")


def fit_robust_linear(t: np.ndarray, counts: np.ndarray) -> LinearFitResult:
    """Robust (Theil-Sen) linear fit, insensitive to a small number of outlier reads."""
    t, counts = np.asarray(t, float), np.asarray(counts, float)
    if t.size < _MIN_POINTS_LINEAR:
        raise InsufficientDataError(f"need at least {_MIN_POINTS_LINEAR} points for a robust fit, got {t.size}")
    slope, intercept, _, _ = theilslopes(counts, t)
    if not (np.isfinite(slope) and np.isfinite(intercept)):
        raise ConvergenceError("robust (Theil-Sen) fit returned non-finite parameters")
    return LinearFitResult(rate=float(slope), offset=float(intercept), method="robust")


def linear_residuals(t: np.ndarray, counts: np.ndarray, fit: LinearFitResult) -> np.ndarray:
    predicted = fit.rate * np.asarray(t, float) + fit.offset
    return np.asarray(counts, float) - predicted


def _curvature_model(t, rate, curvature, offset):
    fluence = rate * t
    return fluence - curvature * fluence**2 + offset


@dataclass(frozen=True)
class CurvatureFitResult:
    rate: float
    curvature: float
    offset: float
    convergence: FitConvergence


def fit_ramp_with_curvature(t: np.ndarray, counts: np.ndarray) -> CurvatureFitResult:
    """Fit the nonlinear (rate, curvature, offset) ramp model via curve_fit.

    This is the model used for the synthetic injection-recovery gate: given a
    ramp with a known injected curvature, this function should recover it
    within the documented tolerance.

    `rate` (electrons/second, typically O(1-100)) and `curvature`
    (typically O(1e-4) or smaller) differ by many orders of magnitude, which
    makes the raw covariance matrix from `curve_fit` structurally
    ill-conditioned regardless of fit quality (found empirically: a fit that
    visibly tracked the data well still failed the condition-number gate at
    higher count rates). The fit is therefore performed in a normalized
    (t, counts) scale where all three parameters are O(1), and the result is
    converted back to physical units — the standard fix for this class of
    curve_fit conditioning issue.
    """
    t, counts = np.asarray(t, float), np.asarray(counts, float)
    if t.size < _MIN_POINTS_CURVATURE:
        raise InsufficientDataError(
            f"need at least {_MIN_POINTS_CURVATURE} points to fit a 3-parameter curvature model, got {t.size}"
        )
    if not np.all(np.isfinite(counts)):
        raise ConvergenceError("ramp counts contain non-finite values; refusing to fit")

    t_scale = float(t[-1]) if t[-1] > 0 else 1.0
    c_scale = float(np.max(np.abs(counts))) if np.max(np.abs(counts)) > 0 else 1.0
    t_norm, counts_norm = t / t_scale, counts / c_scale

    rate_norm_guess = float(counts_norm[-1] / t_norm[-1]) if t_norm[-1] > 0 else 1.0
    p0 = [max(rate_norm_guess, 0.1), 0.0, 0.0]
    bounds = ([0.0, -1e6, -np.inf], [np.inf, 1e6, np.inf])
    try:
        popt_norm, pcov_norm = curve_fit(_curvature_model, t_norm, counts_norm, p0=p0, bounds=bounds, maxfev=10000)
    except RuntimeError as exc:
        raise ConvergenceError(f"curvature ramp fit failed to converge: {exc}") from exc

    residuals_norm = counts_norm - _curvature_model(t_norm, *popt_norm)
    dof = t.size - len(popt_norm)
    convergence = check_fit_convergence(pcov_norm, residuals=residuals_norm, dof=dof, max_condition_number=1e10)

    rate_norm, curvature_norm, offset_norm = popt_norm
    rate = rate_norm * c_scale / t_scale
    curvature = curvature_norm / c_scale
    offset = offset_norm * c_scale

    return CurvatureFitResult(rate=float(rate), curvature=float(curvature), offset=float(offset), convergence=convergence)
