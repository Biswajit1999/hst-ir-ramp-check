"""Pipeline orchestration composing the reusable scientific modules.

`run_pipeline` is the single non-notebook entry point for the real-data
analysis; scripts/run_analysis.py and notebooks/ both call into it rather
than reimplementing logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from hst_wfc3ir_ramp_linearity_audit.aperture_analysis import ExtractedRamp, extract_ramp
from hst_wfc3ir_ramp_linearity_audit.config import AnalysisConfig
from hst_wfc3ir_ramp_linearity_audit.dq_masks import DEFAULT_EXCLUSION_MASK, cosmic_ray_fraction, exclusion_mask
from hst_wfc3ir_ramp_linearity_audit.exceptions import ConvergenceError, DataSchemaError, InsufficientDataError
from hst_wfc3ir_ramp_linearity_audit.fluence_bins import ScalarBinningResult, bin_scalar_statistic
from hst_wfc3ir_ramp_linearity_audit.ima_io import IMAProduct, load_ima
from hst_wfc3ir_ramp_linearity_audit.logging_utils import get_logger
from hst_wfc3ir_ramp_linearity_audit.ramp_model import (
    fit_ramp_with_curvature,
    fit_robust_linear,
    fit_weighted_linear,
    linear_residuals,
)

LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class Summary:
    count: int
    median: float
    mad: float


def validate_numeric(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError("values must be one-dimensional")
    if arr.size == 0:
        raise ValueError("values must not be empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError("values contain non-finite entries")
    return arr


def robust_summary(values: np.ndarray) -> Summary:
    arr = validate_numeric(values)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    return Summary(count=int(arr.size), median=median, mad=mad)


def demo_series(seed: int = 20260713, size: int = 128) -> np.ndarray:
    """Return deterministic synthetic data labelled only for smoke testing."""
    if size < 8:
        raise ValueError("size must be at least 8")
    rng = np.random.default_rng(seed)
    return rng.normal(loc=0.0, scale=1.0, size=size)


def select_bright_pixels(product: IMAProduct, n_pixels: int, edge_margin: int = 5) -> list[tuple[int, int]]:
    """Deterministically select the brightest interior pixels from the deepest read.

    "Bright" pixels give a usable signal-to-noise ramp to fit; edge pixels are
    excluded by `edge_margin` to keep the extraction aperture in-bounds.
    """
    deepest_read = product.reads[-1]  # sorted by increasing samptime; last = deepest
    science = deepest_read.science
    ny, nx = science.shape
    if ny <= 2 * edge_margin or nx <= 2 * edge_margin:
        raise InsufficientDataError(f"array too small ({nx}x{ny}) for edge_margin={edge_margin}")

    interior = science[edge_margin : ny - edge_margin, edge_margin : nx - edge_margin]
    flat_indices = np.argsort(interior.ravel())[::-1][:n_pixels]
    coords = np.column_stack(np.unravel_index(flat_indices, interior.shape))
    return [(int(x) + edge_margin, int(y) + edge_margin) for y, x in coords]


@dataclass(frozen=True)
class PixelMeasurement:
    x: int
    y: int
    quadrant: str
    weighted_rate: float
    robust_rate: float
    curvature: float
    curvature_rate: float
    max_fluence: float
    residual_at_max_fluence: float
    cr_flagged_read_fraction: float
    n_excluded_reads: int


def _measure_pixel(ramp: ExtractedRamp, early_fraction: float = 0.5) -> PixelMeasurement:
    excluded = exclusion_mask(ramp.dq, DEFAULT_EXCLUSION_MASK)
    n_excluded = int(np.sum(excluded))
    keep = ~excluded
    if np.sum(keep) < 4:
        raise InsufficientDataError(
            f"pixel ({ramp.x},{ramp.y}): only {np.sum(keep)} reads survive DQ exclusion, need >=4"
        )

    t, counts, unc = ramp.samptimes[keep], ramp.counts[keep], ramp.uncertainty[keep]
    n_early = max(3, int(len(t) * early_fraction))
    t_early, counts_early, unc_early = t[:n_early], counts[:n_early], unc[:n_early]

    weighted = fit_weighted_linear(t_early, counts_early, unc_early)
    robust = fit_robust_linear(t_early, counts_early)
    curvature_fit = fit_ramp_with_curvature(t, counts)

    residuals = linear_residuals(t, counts, weighted)
    cr_fraction = cosmic_ray_fraction(ramp.dq).fraction

    return PixelMeasurement(
        x=ramp.x, y=ramp.y, quadrant=ramp.quadrant,
        weighted_rate=weighted.rate, robust_rate=robust.rate,
        curvature=curvature_fit.curvature, curvature_rate=curvature_fit.rate,
        max_fluence=float(weighted.rate * t[-1]), residual_at_max_fluence=float(residuals[-1]),
        cr_flagged_read_fraction=cr_fraction, n_excluded_reads=n_excluded,
    )


@dataclass(frozen=True)
class PipelineResult:
    measurements: list[PixelMeasurement]
    residual_by_fluence: ScalarBinningResult
    cr_fraction_by_fluence: ScalarBinningResult
    quadrant_summary: dict[str, dict[str, float]]
    warnings: list[str] = field(default_factory=list)


def run_pipeline(
    manifest_rows: list[dict],
    raw_dir: str | Path,
    config: AnalysisConfig,
    n_pixels_per_file: int = 40,
    aperture_radius: int = 1,
    n_fluence_bins: int = 3,
) -> PipelineResult:
    """Run the full up-the-ramp linearity audit over real (or synthetic-test) IMA files."""
    raw_dir = Path(raw_dir)
    all_warnings: list[str] = []
    measurements: list[PixelMeasurement] = []

    product_ids = sorted({row["product_id"] for row in manifest_rows if row["product_id"].endswith("_ima")})
    if not product_ids:
        raise InsufficientDataError("no *_ima manifest rows found")

    for product_id in product_ids:
        path = raw_dir / f"{product_id}.fits"
        try:
            product = load_ima(path)
        except DataSchemaError as exc:
            all_warnings.append(f"{product_id}: skipped: {exc}")
            continue

        try:
            pixels = select_bright_pixels(product, n_pixels_per_file)
        except InsufficientDataError as exc:
            all_warnings.append(f"{product_id}: skipped: {exc}")
            continue

        for x, y in pixels:
            try:
                ramp = extract_ramp(product, x, y, aperture_radius=aperture_radius)
                measurements.append(_measure_pixel(ramp))
            except (InsufficientDataError, ConvergenceError) as exc:
                all_warnings.append(f"{product_id} pixel ({x},{y}): skipped: {exc}")

    if not measurements:
        raise InsufficientDataError("no usable pixel ramp measurements across any IMA file")

    fluence = np.array([m.max_fluence for m in measurements])
    residual = np.array([m.residual_at_max_fluence for m in measurements])
    cr_fraction = np.array([m.cr_flagged_read_fraction for m in measurements])

    fluence_edges = np.quantile(fluence, np.linspace(0, 1, n_fluence_bins + 1))
    fluence_edges[-1] += 1e-6
    residual_binning = bin_scalar_statistic(fluence, residual, fluence_edges, config.validation.minimum_sample_size)
    cr_binning = bin_scalar_statistic(fluence, cr_fraction, fluence_edges, config.validation.minimum_sample_size)
    all_warnings.extend(residual_binning.warnings)
    all_warnings.extend(cr_binning.warnings)

    quadrant_summary: dict[str, dict[str, float]] = {}
    for quadrant in sorted({m.quadrant for m in measurements}):
        members = [m for m in measurements if m.quadrant == quadrant]
        quadrant_summary[quadrant] = {
            "n": len(members),
            "median_curvature": float(np.median([m.curvature for m in members])),
            "median_residual_at_max_fluence": float(np.median([m.residual_at_max_fluence for m in members])),
        }

    return PipelineResult(
        measurements=measurements,
        residual_by_fluence=residual_binning,
        cr_fraction_by_fluence=cr_binning,
        quadrant_summary=quadrant_summary,
        warnings=all_warnings,
    )
