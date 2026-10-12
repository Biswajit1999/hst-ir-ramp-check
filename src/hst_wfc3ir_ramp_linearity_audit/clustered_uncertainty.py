"""Exposure-aware uncertainty checks for real WFC3/IR ramp measurements."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def pixel_bootstrap(values, *, draws=20000, seed=20261012) -> dict:
    """Bootstrap a median while explicitly treating pixels as exchangeable."""
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    medians = np.median(rng.choice(values, (draws, len(values)), replace=True), axis=1)
    return {
        "median": float(np.median(values)),
        "ci95_low": float(np.quantile(medians, 0.025)),
        "ci95_high": float(np.quantile(medians, 0.975)),
        "draws": draws,
        "seed": seed,
    }


def exposure_balanced_bootstrap(df: pd.DataFrame, *, draws=20000, seed=20261012) -> dict:
    """Resample within exposures and weight each exposure equally per draw."""
    groups = [group.late_to_early_rate_change.to_numpy() for _, group in df.groupby("product_id")]
    if len(groups) < 2:
        raise ValueError("at least two exposures are required")
    rng = np.random.default_rng(seed)
    estimates = np.empty(draws)
    for index in range(draws):
        medians = [np.median(rng.choice(group, len(group), replace=True)) for group in groups]
        estimates[index] = np.mean(medians)
    point = np.mean([np.median(group) for group in groups])
    return {
        "n_exposures": len(groups),
        "equal_exposure_point": float(point),
        "ci95_low": float(np.quantile(estimates, 0.025)),
        "ci95_high": float(np.quantile(estimates, 0.975)),
        "draws": draws,
        "seed": seed,
    }


def diagnostic_associations(df: pd.DataFrame) -> dict:
    """Relate drift to fluence and compare weighted versus robust ramp rates."""
    rho, pvalue = stats.spearmanr(df.max_fluence, df.late_to_early_rate_change)
    difference = (df.robust_rate - df.weighted_rate) / df.weighted_rate
    return {
        "spearman_drift_vs_fluence": float(rho),
        "spearman_drift_vs_fluence_p": float(pvalue),
        "median_robust_vs_weighted_rate_fraction": float(np.median(difference)),
        "p95_absolute_robust_vs_weighted_rate_fraction": float(
            np.quantile(np.abs(difference), 0.95)
        ),
    }


def per_exposure_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Keep exposure-level estimates visible instead of pooling silently."""
    return (
        df.groupby("product_id")
        .agg(
            n=("late_to_early_rate_change", "size"),
            median_rate_change=("late_to_early_rate_change", "median"),
            median_endpoint_residual=("endpoint_fractional_residual", "median"),
            median_max_fluence_e=("max_fluence", "median"),
        )
        .reset_index()
    )
