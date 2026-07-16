"""Generate the 6 required figures (docs/FIGURE_AND_UI_SPEC.md) as SVG + 300 dpi PNG,
each with a sidecar JSON recording git commit, config hash, sample size and units.

--demo builds figures from the synthetic, clearly-labelled data model in
`hst_wfc3ir_ramp_linearity_audit.synthetic`. The real-data path reads
data/manifest.csv + data/raw/ and must only be run after
scripts/run_analysis.py (real mode) has produced validated results.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from hst_wfc3ir_ramp_linearity_audit import __version__
from hst_wfc3ir_ramp_linearity_audit.aperture_analysis import extract_ramp
from hst_wfc3ir_ramp_linearity_audit.config import load_config
from hst_wfc3ir_ramp_linearity_audit.core import run_pipeline, select_bright_pixels
from hst_wfc3ir_ramp_linearity_audit.dq_masks import DEFAULT_EXCLUSION_MASK, exclusion_mask
from hst_wfc3ir_ramp_linearity_audit.exceptions import ConvergenceError, InsufficientDataError
from hst_wfc3ir_ramp_linearity_audit.ima_io import load_ima
from hst_wfc3ir_ramp_linearity_audit.plotting import plot_demo
from hst_wfc3ir_ramp_linearity_audit.provenance import get_git_commit, read_manifest, sha256_config
from hst_wfc3ir_ramp_linearity_audit.ramp_model import fit_ramp_with_curvature, fit_weighted_linear, linear_residuals
from hst_wfc3ir_ramp_linearity_audit.synthetic import SyntheticRampSpec, build_synthetic_ima_hdulist, synthetic_ramp_counts


def _sidecar(path: Path, *, data_kind: str, sample_size: int, units: str, config_path: Path, extra: dict | None = None) -> None:
    payload = {
        "figure": path.stem,
        "data_kind": data_kind,
        "sample_size": sample_size,
        "units": units,
        "git_commit": get_git_commit(Path(__file__).resolve().parents[1]),
        "config_sha256": sha256_config(config_path) if config_path.is_file() else None,
        "package_version": __version__,
    }
    if extra:
        payload.update(extra)
    path.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _save(fig, out_dir: Path, name: str) -> Path:
    svg_path = out_dir / f"{name}.svg"
    png_path = out_dir / f"{name}.png"
    fig.savefig(svg_path)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)
    return png_path


def make_demo_figures(out_dir: Path, config_path: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data_kind = "synthetic_demo"
    spec = SyntheticRampSpec(count_rate=20.0, curvature=0.0003, read_noise=5.0)
    counts = synthetic_ramp_counts(spec, seed=2000)
    t = spec.samptimes

    weighted = fit_weighted_linear(t[: len(t) // 2], counts[: len(t) // 2], np.full(len(t) // 2, spec.read_noise))
    curvature_fit = fit_ramp_with_curvature(t, counts)

    # 1. example ramp
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(t, counts, "o", label="accumulated counts (synthetic)")
    ax.plot(t, weighted.rate * t + weighted.offset, "--", label="linear fit (early reads)")
    ax.plot(t, curvature_fit.rate * t - curvature_fit.curvature * (curvature_fit.rate * t) ** 2 + curvature_fit.offset, "-", label="nonlinear fit (all reads)")
    ax.set_xlabel("Sample time (s)")
    ax.set_ylabel("Accumulated counts (electrons)")
    ax.set_title(f"Example up-the-ramp — SYNTHETIC DEMO (rate={spec.count_rate} e-/s, curvature={spec.curvature})")
    ax.legend()
    path = _save(fig, out_dir, "fig01_example_ramp")
    _sidecar(path, data_kind=data_kind, sample_size=t.size, units="electrons vs seconds", config_path=config_path)

    # 2. residual vs fluence (multi-pixel synthetic sample, fixed curvature)
    rng = np.random.default_rng(20260713)
    fluences, residuals = [], []
    for i in range(30):
        rate_i = rng.uniform(5, 40)
        spec_i = SyntheticRampSpec(count_rate=rate_i, curvature=0.0003, read_noise=5.0)
        counts_i = synthetic_ramp_counts(spec_i, seed=3000 + i)
        w = fit_weighted_linear(spec_i.samptimes[:3], counts_i[:3], np.full(3, spec_i.read_noise))
        resid = linear_residuals(spec_i.samptimes, counts_i, w)
        fluences.append(w.rate * spec_i.samptimes[-1])
        residuals.append(resid[-1])

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(fluences, residuals, "o", color="tab:red")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xlabel("Accumulated fluence at final read (electrons)")
    ax.set_ylabel("Residual from early-read linear fit (electrons)")
    ax.set_title(f"Residual vs fluence — SYNTHETIC DEMO (n={len(fluences)})")
    path = _save(fig, out_dir, "fig02_residual_vs_fluence")
    _sidecar(path, data_kind=data_kind, sample_size=len(fluences), units="electrons", config_path=config_path)

    # 3. quadrant distributions (synthetic per-quadrant curvature samples)
    quadrants = ["BL", "BR", "TL", "TR"]
    quadrant_data = {q: rng.normal(0.0003, 0.00015, size=15) for q in quadrants}
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([quadrant_data[q] for q in quadrants], tick_labels=quadrants)
    ax.set_ylabel("Fitted curvature coefficient")
    ax.set_title("Curvature by quadrant — SYNTHETIC DEMO (n=15/quadrant)")
    path = _save(fig, out_dir, "fig03_quadrant_distributions")
    _sidecar(path, data_kind=data_kind, sample_size=60, units="dimensionless", config_path=config_path)

    # 4. early/late read comparison
    early_rates, late_rates = [], []
    for i in range(20):
        rate_i = rng.uniform(5, 40)
        spec_i = SyntheticRampSpec(count_rate=rate_i, curvature=0.0003, read_noise=5.0)
        counts_i = synthetic_ramp_counts(spec_i, seed=4000 + i)
        early = fit_weighted_linear(spec_i.samptimes[:3], counts_i[:3], np.full(3, spec_i.read_noise))
        late = fit_weighted_linear(spec_i.samptimes[-3:], counts_i[-3:], np.full(3, spec_i.read_noise))
        early_rates.append(early.rate)
        late_rates.append(late.rate)
    fig, ax = plt.subplots(figsize=(6, 6))
    lims = [0, max(max(early_rates), max(late_rates)) * 1.1]
    ax.plot(lims, lims, "k--", label="1:1")
    ax.plot(early_rates, late_rates, "o", color="tab:purple")
    ax.set_xlabel("Rate from early reads (e-/s)")
    ax.set_ylabel("Rate from late reads (e-/s)")
    ax.set_title(f"Early vs late read rate comparison — SYNTHETIC DEMO (n={len(early_rates)})")
    ax.legend()
    path = _save(fig, out_dir, "fig04_early_late_comparison")
    _sidecar(path, data_kind=data_kind, sample_size=len(early_rates), units="electrons/second", config_path=config_path)

    # 5. injection recovery: vary the injected curvature itself across a real range
    truth_curvatures = np.array([0.0001, 0.0002, 0.0003, 0.0004, 0.0005])
    recovered_curvatures = []
    for i, curv in enumerate(truth_curvatures):
        spec_i = SyntheticRampSpec(count_rate=20.0, curvature=float(curv), read_noise=5.0)
        counts_i = synthetic_ramp_counts(spec_i, seed=5000 + i)
        cf = fit_ramp_with_curvature(spec_i.samptimes, counts_i)
        recovered_curvatures.append(cf.curvature)
    fig, ax = plt.subplots(figsize=(6, 6))
    lims = [0, float(truth_curvatures.max()) * 1.2]
    ax.plot(lims, lims, "k--", label="1:1")
    ax.plot(truth_curvatures, recovered_curvatures, "o", color="tab:green", label="recovered vs injected")
    ax.set_xlabel("Injected curvature")
    ax.set_ylabel("Recovered curvature")
    ax.set_title(f"Injection-recovery validation — SYNTHETIC DEMO (n={len(truth_curvatures)})")
    ax.legend()
    path = _save(fig, out_dir, "fig05_injection_recovery")
    _sidecar(path, data_kind=data_kind, sample_size=len(truth_curvatures), units="dimensionless", config_path=config_path)

    # 6. CR flags vs fluence
    # select_bright_pixels picks the brightest pixels in the deepest read; a
    # single CR injected at one specific pixel/read is very unlikely to land
    # on one of those (found empirically: the resulting figure was all-zero
    # CR flags, since the CR-affected pixel is a plain background pixel, not
    # a bright one). This figure instead directly samples a deterministic
    # pixel grid that is guaranteed to include the known CR-injected pixel,
    # so the figure actually demonstrates the CR-flag/fluence relationship.
    cr_read_index = 4
    array_size = 25
    cr_pixel = (array_size // 2, array_size // 2)
    hdul = build_synthetic_ima_hdulist(spec=SyntheticRampSpec(count_rate=15.0, curvature=0.0003, read_noise=5.0), size=array_size, cosmic_ray_read_index=cr_read_index, seed=99)
    tmp_path = Path(tempfile.mktemp(suffix=".fits"))
    hdul.writeto(tmp_path)
    product = load_ima(tmp_path)
    grid_pixels = {cr_pixel} | {(x, y) for x in range(3, array_size - 3, 4) for y in range(3, array_size - 3, 4)}
    fluence_vals, cr_flag_vals = [], []
    for x, y in grid_pixels:
        ramp = extract_ramp(product, x, y, aperture_radius=0)
        excluded = exclusion_mask(ramp.dq, DEFAULT_EXCLUSION_MASK)
        for t_j, c_j, ex_j in zip(ramp.samptimes, ramp.counts, excluded):
            fluence_vals.append(max(c_j, 0))
            cr_flag_vals.append(1 if ex_j else 0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(fluence_vals, cr_flag_vals, alpha=0.5, color="tab:orange")
    ax.set_xlabel("Accumulated counts at this read (electrons)")
    ax.set_ylabel("CR/exclusion flag (0 or 1)")
    ax.set_title(f"CR flags vs fluence — SYNTHETIC DEMO (n={len(fluence_vals)} pixel-reads)")
    ax.set_yticks([0, 1])
    path = _save(fig, out_dir, "fig06_cr_flags_vs_fluence")
    _sidecar(path, data_kind=data_kind, sample_size=len(fluence_vals), units="electrons vs boolean", config_path=config_path)

    print(f"Wrote 6 demo figures (SVG+PNG+JSON) to {out_dir}")


def make_real_figures(out_dir: Path, config_path: Path, manifest_path: Path, raw_dir: Path) -> None:
    config = load_config(config_path)
    manifest_rows = read_manifest(manifest_path)
    if not manifest_rows:
        raise SystemExit(
            "data/manifest.csv has no rows. Run scripts/fetch_data.py (with explicit "
            "operator authorization) and scripts/run_analysis.py before generating real figures."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    data_kind = config.input.data_mode

    result = run_pipeline(manifest_rows, raw_dir, config)
    product_ids = sorted({row["product_id"] for row in manifest_rows if row["product_id"].endswith("_ima")})
    first_product = load_ima(raw_dir / f"{product_ids[0]}.fits")
    example_pixel = select_bright_pixels(first_product, n_pixels=1)[0]
    example_ramp = extract_ramp(first_product, *example_pixel, aperture_radius=1)

    excluded = exclusion_mask(example_ramp.dq, DEFAULT_EXCLUSION_MASK)
    keep = ~excluded
    t_keep, c_keep, u_keep = example_ramp.samptimes[keep], example_ramp.counts[keep], example_ramp.uncertainty[keep]
    n_early = max(3, len(t_keep) // 2)
    weighted = fit_weighted_linear(t_keep[:n_early], c_keep[:n_early], u_keep[:n_early])
    curvature_fit = fit_ramp_with_curvature(t_keep, c_keep)

    # 1. example ramp
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(example_ramp.samptimes, example_ramp.counts, "o", label="accumulated counts")
    ax.plot(t_keep, weighted.rate * t_keep + weighted.offset, "--", label="linear fit (early reads)")
    t_grid = np.linspace(t_keep.min(), t_keep.max(), 50)
    ax.plot(t_grid, curvature_fit.rate * t_grid - curvature_fit.curvature * (curvature_fit.rate * t_grid) ** 2 + curvature_fit.offset, "-", label="nonlinear fit")
    ax.set_xlabel("Sample time (s)")
    ax.set_ylabel("Accumulated counts (electrons)")
    ax.set_title(f"Example up-the-ramp: {product_ids[0]} pixel {example_pixel}")
    ax.legend()
    path = _save(fig, out_dir, "fig01_example_ramp")
    _sidecar(path, data_kind=data_kind, sample_size=example_ramp.samptimes.size, units="electrons vs seconds", config_path=config_path)

    # 2. residual vs fluence
    fluence = np.array([m.max_fluence for m in result.measurements])
    residual = np.array([m.residual_at_max_fluence for m in result.measurements])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(fluence, residual, "o", color="tab:red")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xlabel("Accumulated fluence at final read (electrons)")
    ax.set_ylabel("Residual from early-read linear fit (electrons)")
    ax.set_title(f"Residual vs fluence (n={len(fluence)} pixels)")
    path = _save(fig, out_dir, "fig02_residual_vs_fluence")
    _sidecar(path, data_kind=data_kind, sample_size=len(fluence), units="electrons", config_path=config_path)

    # 3. quadrant distributions
    quadrants = sorted(result.quadrant_summary.keys())
    quadrant_curv = {q: [m.curvature for m in result.measurements if m.quadrant == q] for q in quadrants}
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.boxplot([quadrant_curv[q] for q in quadrants], tick_labels=quadrants)
    ax.set_ylabel("Fitted curvature coefficient")
    ax.set_title(f"Curvature by quadrant (n={len(result.measurements)} total)")
    path = _save(fig, out_dir, "fig03_quadrant_distributions")
    _sidecar(path, data_kind=data_kind, sample_size=len(result.measurements), units="dimensionless", config_path=config_path)

    # 4. early/late read comparison
    early_rates, late_rates = [], []
    for product_id in product_ids:
        product = load_ima(raw_dir / f"{product_id}.fits")
        for x, y in select_bright_pixels(product, n_pixels=10):
            ramp = extract_ramp(product, x, y, aperture_radius=1)
            excl = exclusion_mask(ramp.dq, DEFAULT_EXCLUSION_MASK)
            keep_i = ~excl
            t_i, c_i, u_i = ramp.samptimes[keep_i], ramp.counts[keep_i], ramp.uncertainty[keep_i]
            if len(t_i) < 6:
                continue
            n_e = max(3, len(t_i) // 2)
            try:
                early_fit = fit_weighted_linear(t_i[:n_e], c_i[:n_e], u_i[:n_e])
                late_fit = fit_weighted_linear(t_i[-n_e:], c_i[-n_e:], u_i[-n_e:])
            except (InsufficientDataError, ConvergenceError):
                continue
            early_rates.append(early_fit.rate)
            late_rates.append(late_fit.rate)
    fig, ax = plt.subplots(figsize=(6, 6))
    if early_rates:
        lims = [0, max(max(early_rates), max(late_rates)) * 1.1]
        ax.plot(lims, lims, "k--", label="1:1")
        ax.plot(early_rates, late_rates, "o", color="tab:purple")
    ax.set_xlabel("Rate from early reads (e-/s)")
    ax.set_ylabel("Rate from late reads (e-/s)")
    ax.set_title(f"Early vs late read rate comparison (n={len(early_rates)})")
    ax.legend()
    path = _save(fig, out_dir, "fig04_early_late_comparison")
    _sidecar(path, data_kind=data_kind, sample_size=len(early_rates), units="electrons/second", config_path=config_path)

    # 5. injection recovery (synthetic gate, run alongside real data): vary
    # the injected curvature itself across a real range, not just noise realizations
    truth_curvatures = np.array([0.0001, 0.0002, 0.0003, 0.0004, 0.0005])
    recovered_curvatures = []
    for i, curv in enumerate(truth_curvatures):
        spec_i = SyntheticRampSpec(count_rate=20.0, curvature=float(curv), read_noise=5.0)
        counts_i = synthetic_ramp_counts(spec_i, seed=5000 + i)
        cf = fit_ramp_with_curvature(spec_i.samptimes, counts_i)
        recovered_curvatures.append(cf.curvature)
    fig, ax = plt.subplots(figsize=(6, 6))
    lims = [0, float(truth_curvatures.max()) * 1.2]
    ax.plot(lims, lims, "k--", label="1:1")
    ax.plot(truth_curvatures, recovered_curvatures, "o", color="tab:green", label="recovered vs injected")
    ax.set_xlabel("Injected curvature")
    ax.set_ylabel("Recovered curvature")
    ax.set_title(f"Injection-recovery validation gate (n={len(truth_curvatures)}, run alongside real data)")
    ax.legend()
    path = _save(fig, out_dir, "fig05_injection_recovery")
    _sidecar(path, data_kind="synthetic_validation_gate", sample_size=len(truth_curvatures), units="dimensionless", config_path=config_path)

    # 6. CR flags vs fluence
    fluence_vals, cr_flag_vals = [], []
    for product_id in product_ids:
        product = load_ima(raw_dir / f"{product_id}.fits")
        for x, y in select_bright_pixels(product, n_pixels=15):
            ramp = extract_ramp(product, x, y, aperture_radius=0)
            excl = exclusion_mask(ramp.dq, DEFAULT_EXCLUSION_MASK)
            for c_j, ex_j in zip(ramp.counts, excl):
                fluence_vals.append(max(c_j, 0))
                cr_flag_vals.append(1 if ex_j else 0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(fluence_vals, cr_flag_vals, alpha=0.5, color="tab:orange")
    ax.set_xlabel("Accumulated counts at this read (electrons)")
    ax.set_ylabel("CR/exclusion flag (0 or 1)")
    ax.set_title(f"CR flags vs fluence (n={len(fluence_vals)} pixel-reads)")
    ax.set_yticks([0, 1])
    path = _save(fig, out_dir, "fig06_cr_flags_vs_fluence")
    _sidecar(path, data_kind=data_kind, sample_size=len(fluence_vals), units="electrons vs boolean", config_path=config_path)

    print(f"Wrote 6 real-data figures (SVG+PNG+JSON) to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=Path("figures"))
    parser.add_argument("--config", type=Path, default=Path("config/analysis.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    if args.demo:
        from hst_wfc3ir_ramp_linearity_audit.core import demo_series

        plot_demo(demo_series(), args.out_dir / "fig00_smoke_test.png")
        make_demo_figures(args.out_dir, args.config)
        return

    make_real_figures(args.out_dir, args.config, args.manifest, args.raw_dir)


if __name__ == "__main__":
    main()
