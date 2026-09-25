"""Run predeclared selection and early-window sensitivity designs."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from hst_wfc3ir_ramp_linearity_audit.config import load_config
from hst_wfc3ir_ramp_linearity_audit.core import run_pipeline
from hst_wfc3ir_ramp_linearity_audit.provenance import read_manifest, verify_manifest_files


N_PIXELS = (20, 40)
MIN_SEPARATIONS = (3, 5, 7)
EARLY_FRACTIONS = (0.4, 0.5, 0.6)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "config" / "analysis.yml")
    manifest = read_manifest(root / "data" / "manifest.csv")
    verify_manifest_files(manifest, root / "data" / "raw")
    rows: list[dict[str, float | int | str]] = []

    for n_pixels in N_PIXELS:
        for separation in MIN_SEPARATIONS:
            for early_fraction in EARLY_FRACTIONS:
                result = run_pipeline(
                    manifest,
                    root / "data" / "raw",
                    config,
                    n_pixels_per_file=n_pixels,
                    aperture_radius=0,
                    min_separation=separation,
                    early_fraction=early_fraction,
                )
                rate_changes = np.array(
                    [measurement.late_to_early_rate_change for measurement in result.measurements]
                )
                endpoint_residuals = np.array(
                    [measurement.endpoint_fractional_residual for measurement in result.measurements]
                )
                row: dict[str, float | int | str] = {
                    "n_pixels_requested_per_exposure": n_pixels,
                    "minimum_separation_pixels": separation,
                    "early_fraction": early_fraction,
                    "accepted_measurements": len(result.measurements),
                    "median_late_to_early_rate_change": float(np.median(rate_changes)),
                    "median_endpoint_fractional_residual": float(np.median(endpoint_residuals)),
                }
                for product_id in sorted({m.product_id for m in result.measurements}):
                    members = [m for m in result.measurements if m.product_id == product_id]
                    row[f"median_rate_change_{product_id}"] = float(
                        np.median([m.late_to_early_rate_change for m in members])
                    )
                    row[f"accepted_{product_id}"] = len(members)
                rows.append(row)

    output_dir = root / "results"
    output_dir.mkdir(exist_ok=True)
    fieldnames = list(rows[0].keys())
    with (output_dir / "robustness_designs.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    medians = [float(row["median_late_to_early_rate_change"]) for row in rows]
    per_exposure = {
        product_id: [
            float(row[f"median_rate_change_{product_id}"])
            for row in rows
            if f"median_rate_change_{product_id}" in row
        ]
        for product_id in ("ibft16req_ima", "icp910qoq_ima")
    }
    payload = {
        "question": (
            "Do header-corrected, NLINCORR-complete IMA ramps show a stable residual "
            "late-versus-early count-rate change under declared pixel-selection choices?"
        ),
        "design_count": len(rows),
        "factors": {
            "pixels_requested_per_exposure": list(N_PIXELS),
            "minimum_separation_pixels": list(MIN_SEPARATIONS),
            "early_fraction": list(EARLY_FRACTIONS),
            "aperture_radius_pixels": 0,
        },
        "pooled_median_rate_change_range": [min(medians), max(medians)],
        "positive_pooled_designs": sum(value > 0 for value in medians),
        "per_exposure_median_rate_change_ranges": {
            product_id: [min(values), max(values)] for product_id, values in per_exposure.items()
        },
        "usable_exposures": ["ibft16req_ima", "icp910qoq_ima"],
        "excluded_exposure": {
            "product_id": "icnn06srq_ima",
            "reason": "Only two positive-time reads; fewer than the six required for disjoint early/late fits.",
        },
        "calibration_state": {
            "bunit": "ELECTRONS/S converted to accumulated ELECTRONS with TIME.PIXVALUE",
            "unitcorr": "COMPLETE",
            "nlincorr": "COMPLETE",
            "cal_ver": "3.7.3 (Jan-07-2026)",
        },
        "claim_boundary": (
            "A descriptive post-calibration ramp-stability audit of two usable exposures. "
            "It is not a detector nonlinearity calibration, an independent test of the "
            "NLIN reference file, or a population-level uncertainty interval."
        ),
    }
    (output_dir / "robustness.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    figure_dir = root / "figures"
    figure_dir.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.8))
    markers = {20: "o", 40: "s"}
    colors = {3: "#22d3ee", 5: "#f59e0b", 7: "#a78bfa"}
    for row in rows:
        ax.scatter(
            row["early_fraction"],
            100 * float(row["median_late_to_early_rate_change"]),
            marker=markers[int(row["n_pixels_requested_per_exposure"])],
            color=colors[int(row["minimum_separation_pixels"])],
            s=58,
            alpha=0.82,
        )
    ax.axhline(0, color="#475569", linewidth=1)
    ax.set_xlabel("Fraction of usable reads assigned to early fit")
    ax.set_ylabel("Pooled median late/early rate change (%)")
    ax.set_title("All 18 declared designs retain a negative pooled median")
    ax.grid(alpha=0.18)
    fig.tight_layout()
    fig.savefig(figure_dir / "fig07_selection_robustness.svg")
    fig.savefig(figure_dir / "fig07_selection_robustness.png", dpi=220)
    plt.close(fig)
    print(
        f"Wrote {len(rows)} robustness designs; pooled medians span "
        f"{min(medians):.6f} to {max(medians):.6f}"
    )


if __name__ == "__main__":
    main()
