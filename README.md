# HST WFC3/IR Calibrated Ramp-Stability Audit

This repository asks a deliberately narrow question: after reconstructing accumulated electrons from calibrated WFC3/IR IMA count-rate arrays, is the residual late-versus-early ramp drift stable under declared pixel-selection choices?

## Research evidence and downloads


- [Download the machine-readable table profiles](evidence/table-profiles.json) for 3 archived tables. Open `table-evidence.html` from the checkout for the coverage chart.
- Start with [Summary](results/summary.json), [Per exposure summary](results/clustered-uncertainty/per_exposure_summary.csv), [Summary](results/clustered-uncertainty/summary.json).
- [View Fig05 injection recovery](figures/fig05_injection_recovery.png).

To rebuild the table profiles after rebuilding the evidence inventory, run `python scripts/profile_evidence_tables.py` followed by `python scripts/render_table_profiles.py`.

[Open the evidence browser file](evidence.html) for 14 selected files, including [`summary.json`](results/summary.json). Each file has a download link and SHA-256 digest. Serve this checkout with `python -m http.server` to view the static browser.

Rebuild the inventory and browser with `python scripts/evidence_catalog.py` and `python scripts/render_evidence_page.py`.

## Scientific correction

The earlier release interpreted IMA `SCI` arrays as accumulated electrons. The three archived products used here have `BUNIT=ELECTRONS/S` and `UNITCORR=COMPLETE`; fitting those values as charge produced an invalid nonlinearity headline. The repaired loader multiplies `SCI` and `ERR` by the matching `TIME.PIXVALUE` before fitting and fails closed on unknown units.

The same products have `NLINCORR=COMPLETE`. Therefore this analysis is **not a new detector nonlinearity calibration**. It is a bounded audit of residual post-calibration ramp stability. That distinction is enforced in the dashboard, documentation, and machine-readable robustness record.

## Result

The default design compares disjoint early and late weighted slopes for deterministic, separated, DQ-clean single pixels. Two of the three preselected products contain at least six usable positive-time reads; the third is excluded once at exposure level. Across 18 declared designs—20/40 requested pixels, 3/5/7-pixel separation, and 0.4/0.5/0.6 early-read fractions—the pooled median late/early rate change remains negative. The exact values and per-exposure ranges are generated into `results/robustness.json` and displayed without converting this small descriptive sample into a population claim.

The [exposure-aware uncertainty audit](docs/CLUSTERED_UNCERTAINTY.md) contrasts pooled-pixel and equal-exposure bootstrap summaries, publishes per-exposure estimates, tests fluence association, and checks robust-versus-weighted ramp rates without treating 70 pixels as 70 independent exposures.

## Reproduce

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python scripts/fetch_data.py --i-have-authorization
python scripts/run_analysis.py
python scripts/analyze_robustness.py
python scripts/make_figures.py
python scripts/sync_web_assets.py
pytest -q
ruff check src tests scripts
```

`fetch_data.py` retrieves the exact public MAST products in `data/manifest.csv`. The pipeline verifies both file size and SHA-256 before analysis. Raw FITS files remain untracked; result tables, receipts, figures, configuration hash, package version, and Git provenance are published.

For the dashboard:

```powershell
cd web-react
npm ci
npm run lint
npm run build
```

## Evidence map

- `results/summary.json`: primary estimates and provenance.
- `results/measurements.csv`: auditable pixel-level measurements.
- `results/robustness.json`: claim boundary and aggregate sensitivity ranges.
- `results/robustness_designs.csv`: all 18 selection designs.
- `data/manifest.csv`: product URLs, retrieval timestamps, byte counts, and SHA-256 receipts.
- `figures/fig07_selection_robustness.svg`: visual comparison across all declared designs.
- `docs/ASSUMPTIONS_AND_LIMITATIONS.md`: interpretation boundary and threats to validity.
- `CURATION_STATUS.md`: evidence-completeness and release-readiness record.

## Author and licence

Biswajit Jana. Original code is BSD-3-Clause; HST/MAST products retain their archive terms.
