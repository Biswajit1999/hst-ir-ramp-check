"""Run the WFC3/IR up-the-ramp linearity audit: either the synthetic --demo
smoke path, or the real-data pipeline over data/manifest.csv + data/raw/.

Peak memory is measured with the stdlib `tracemalloc` (Python-level
allocations) rather than a full process-RSS profiler such as psutil, which
is not part of this project's pinned dependency set.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

from hst_wfc3ir_ramp_linearity_audit import __version__
from hst_wfc3ir_ramp_linearity_audit.config import load_config
from hst_wfc3ir_ramp_linearity_audit.core import demo_series, robust_summary, run_pipeline
from hst_wfc3ir_ramp_linearity_audit.exceptions import ProjectError
from hst_wfc3ir_ramp_linearity_audit.logging_utils import get_logger
from hst_wfc3ir_ramp_linearity_audit.provenance import get_git_commit, read_manifest, sha256_config
from hst_wfc3ir_ramp_linearity_audit.results_io import Metric, write_summary

LOGGER = get_logger(__name__)


def _write_benchmark(path: Path, label: str, wall_time_s: float, peak_memory_mib: float, dataset_size: int) -> None:
    payload = {
        "label": label,
        "wall_time_seconds": wall_time_s,
        "peak_memory_mib": peak_memory_mib,
        "peak_memory_method": "tracemalloc (Python-level allocations, not full process RSS)",
        "dataset_size": dataset_size,
        "python_version": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "package_version": __version__,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    existing.append(payload)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def run_demo() -> None:
    tracemalloc.start()
    start = time.perf_counter()

    values = demo_series()
    summary = robust_summary(values)

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    out = Path("results")
    out.mkdir(exist_ok=True)
    metrics = [
        Metric(name="median", estimate=summary.median, units="dimensionless", sample_size=summary.count),
        Metric(name="median_absolute_deviation", estimate=summary.mad, units="dimensionless", sample_size=summary.count),
    ]
    payload = write_summary(
        out / "summary.json",
        project="HST WFC3/IR Up-the-Ramp Linearity Audit (demo smoke test)",
        data_kind="synthetic_smoke_test",
        metrics=metrics,
        provenance={
            "config_sha256": None,
            "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
            "package_version": __version__,
        },
        warnings=[],
    )
    print(json.dumps(payload, indent=2))
    _write_benchmark(out / "benchmarks.json", "demo", elapsed, peak / (1024 * 1024), values.size)


def run_real_data(config_path: Path, manifest_path: Path, raw_dir: Path, results_dir: Path) -> None:
    config = load_config(config_path)
    try:
        manifest_rows = read_manifest(manifest_path)
    except ProjectError as exc:
        raise SystemExit(
            f"Cannot run the real-data pipeline: {exc}. Run scripts/fetch_data.py "
            "(with explicit operator authorization) first."
        ) from exc

    if not manifest_rows:
        raise SystemExit(
            "data/manifest.csv has no rows. Run scripts/fetch_data.py "
            "(with explicit operator authorization) before running the real-data pipeline."
        )

    tracemalloc.start()
    start = time.perf_counter()

    result = run_pipeline(manifest_rows, raw_dir, config)

    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    curvatures = [m.curvature for m in result.measurements]
    metrics = [
        Metric(name="median_curvature", estimate=float(np.median(curvatures)), units="dimensionless", sample_size=len(curvatures)),
        Metric(
            name="median_cr_flagged_fraction",
            estimate=float(np.median([m.cr_flagged_read_fraction for m in result.measurements])),
            units="dimensionless",
            sample_size=len(result.measurements),
        ),
    ]
    for quadrant, stats in sorted(result.quadrant_summary.items()):
        metrics.append(
            Metric(name=f"median_curvature_quadrant_{quadrant}", estimate=stats["median_curvature"], units="dimensionless", sample_size=int(stats["n"]))
        )
    for label, binning in (("residual", result.residual_by_fluence), ("cr_fraction", result.cr_fraction_by_fluence)):
        for i, b in enumerate(binning.bins):
            metrics.append(
                Metric(
                    name=f"{label}_by_fluence_bin_{i}_[{b.bin_low:.4g},{b.bin_high:.4g})",
                    estimate=b.mean, units="electrons" if label == "residual" else "dimensionless", sample_size=b.n_members,
                )
            )

    provenance = {
        "config_sha256": sha256_config(config_path),
        "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
        "package_version": __version__,
        "n_ima_files": len({row["product_id"] for row in manifest_rows}),
        "n_pixel_measurements": len(result.measurements),
    }

    results_dir.mkdir(exist_ok=True)
    write_summary(
        results_dir / "summary.json",
        project=config.project.title,
        data_kind=config.input.data_mode,
        metrics=metrics,
        provenance=provenance,
        warnings=result.warnings,
    )
    (results_dir / "warnings.json").write_text(json.dumps(result.warnings, indent=2), encoding="utf-8")
    _write_benchmark(results_dir / "benchmarks.json", "real_data", elapsed, peak / (1024 * 1024), len(manifest_rows))
    print(f"Wrote {results_dir / 'summary.json'} ({len(metrics)} metrics, {len(result.warnings)} warnings)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Run synthetic smoke data only")
    parser.add_argument("--config", type=Path, default=Path("config/analysis.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    run_real_data(args.config, args.manifest, args.raw_dir, args.results_dir)


if __name__ == "__main__":
    main()
