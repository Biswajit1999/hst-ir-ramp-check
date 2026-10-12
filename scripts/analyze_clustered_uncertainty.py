"""Generate exposure-aware uncertainty products from real ramp measurements."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import scienceplots  # noqa: F401

from hst_wfc3ir_ramp_linearity_audit.clustered_uncertainty import (
    diagnostic_associations,
    exposure_balanced_bootstrap,
    per_exposure_summary,
    pixel_bootstrap,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    data = pd.read_csv(ROOT / "results/measurements.csv")
    pixel = pixel_bootstrap(data.late_to_early_rate_change)
    balanced = exposure_balanced_bootstrap(data)
    associations = diagnostic_associations(data)
    exposures = per_exposure_summary(data)
    out = ROOT / "results/clustered-uncertainty"
    out.mkdir(parents=True, exist_ok=True)
    exposures.to_csv(out / "per_exposure_summary.csv", index=False)
    (out / "summary.json").write_text(
        json.dumps(
            {
                "data_kind": "real public calibrated HST WFC3/IR IMA-derived measurements",
                "pixel_bootstrap": pixel,
                "exposure_balanced_bootstrap": balanced,
                "diagnostic_associations": associations,
                "limitations": (
                    "Only two exposures pass the predeclared read-count gate. Pixel bootstrap "
                    "intervals assume exchangeable pixels and can understate correlated detector "
                    "or exposure systematics. The exposure-balanced interval resamples within, "
                    "not across, the two fixed exposures and is not a population uncertainty."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with plt.style.context(["science", "no-latex", "bright"]):
        fig, axes = plt.subplots(1, 2, figsize=(9.3, 3.9), constrained_layout=True)
        for product, group in data.groupby("product_id"):
            axes[0].scatter(
                group.max_fluence,
                100 * group.late_to_early_rate_change,
                s=35,
                alpha=0.75,
                label=product,
            )
        axes[0].axhline(0, color="0.35", lw=1)
        axes[0].set(
            xlabel="Maximum accumulated fluence [electron]",
            ylabel="Late/early rate change [%]",
            title="(a) Pixel diagnostics",
        )
        axes[0].set_yscale("symlog", linthresh=5)
        axes[0].legend(frameon=False)
        points = [100 * pixel["median"], 100 * balanced["equal_exposure_point"]]
        low = [
            100 * (pixel["median"] - pixel["ci95_low"]),
            100 * (balanced["equal_exposure_point"] - balanced["ci95_low"]),
        ]
        high = [
            100 * (pixel["ci95_high"] - pixel["median"]),
            100 * (balanced["ci95_high"] - balanced["equal_exposure_point"]),
        ]
        axes[1].errorbar(
            ["Pixel pooled", "Exposure balanced"],
            points,
            yerr=[low, high],
            fmt="o",
            capsize=4,
        )
        axes[1].axhline(0, color="0.35", lw=1)
        axes[1].set(
            ylabel="Rate-change estimate [%]",
            title="(b) Dependence-aware summaries",
        )
        fig.suptitle("HST WFC3/IR calibrated ramp: clustered uncertainty audit")
        fig.savefig(out / "clustered_uncertainty.png", dpi=240)
        fig.savefig(out / "clustered_uncertainty.pdf")
        plt.close(fig)


if __name__ == "__main__":
    main()
