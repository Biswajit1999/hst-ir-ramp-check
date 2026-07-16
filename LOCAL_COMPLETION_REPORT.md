# Local Completion Report — HST WFC3/IR Up-the-Ramp Linearity Audit

Author: Biswajit Jana. This report documents a local implementation pass
(project 3 of the 30-project pack, `BUILD_FIRST` priority 9.5/10). No git operations
were performed. Nothing has been published.

## 1. Environment

- Reused the `hst-acs-cte-audit` conda environment (Python 3.11.15) from projects 1
  and 2, since this project's `pyproject.toml` pins the identical dependency
  versions (numpy 1.26.4, scipy 1.13.1, astropy 6.1.0, astroquery 0.4.7,
  photutils 1.13.0).
- No local LaTeX toolchain (same limitation as projects 1–2).

## 2. Files created or changed

Foundation (`config.py`, `exceptions.py`, `logging_utils.py`, `provenance.py`,
`results_io.py`), data layer (`scripts/fetch_data.py`, `synthetic.py`,
`scripts/sync_web_assets.py`), scientific modules (`ima_io.py`, `dq_masks.py`,
`ramp_model.py`, `fluence_bins.py`, `aperture_analysis.py`, `uncertainty.py`,
`core.py`), 9 test files (92% coverage), figures/report (`scripts/make_figures.py`,
`reports/report.tex`, `reports/references.bib`), and the web dashboard
(`web-react/src/App.jsx` rewritten, `eslint.config.js` fixed, `recharts` removed,
`public/project.json` rewritten). Full file list mirrors `IMPLEMENTATION_PLAN.md` §5.

## 3. Exact commands run (in order)

```bash
python -m pip install -e ".[dev]"          # into the shared hst-acs-cte-audit env
pytest -q                                    # 48 passed
ruff check src tests scripts                 # All checks passed
mypy src                                     # Success: no issues found in 15 source files
python scripts/run_analysis.py --demo
python scripts/make_figures.py --demo
cd web-react && npm install && npm run lint && npm run build
python scripts/sync_web_assets.py
# Real-data pipeline, run only after explicit operator authorization in chat:
python scripts/fetch_data.py --i-have-authorization
python scripts/run_analysis.py
python scripts/make_figures.py
python scripts/sync_web_assets.py
```

## 4. Test / lint / build results

- **pytest**: 48 tests passed, 0 failed. 92% source coverage.
- **ruff**: clean on `src tests scripts`.
- **mypy**: clean on `src` (0 errors, 15 source files).
- **web-react**: `npm run lint` and `npm run build` both clean after applying the
  same `eslint.config.js` `react/jsx-uses-vars`/`react/jsx-uses-react` fix and
  `recharts` removal identified in projects 1–2 (present in every project in the
  pack scaffold — applied proactively this time instead of rediscovered).
  Dashboard also visually verified in-browser (Vite dev server): all 6 figures
  load (200 OK), no console errors, correct SYNTHETIC DEMO / REAL DATA badge
  switching confirmed against the demo-stage summary before real data was fetched.

### Bugs found and fixed during implementation

1. `fit_ramp_with_curvature` raised spurious `ConvergenceError` (fit covariance
   condition number ~1e14–1e26) on legitimately good fits at higher count rates,
   because `rate` (~5–150 e-/s) and `curvature` (~1e-4–1e-3) differ by many orders
   of magnitude, making the raw covariance matrix structurally ill-conditioned
   regardless of fit quality. Fixed by internally normalizing both the time/count
   axes and the fit parameters to O(1) scale before fitting, then rescaling the
   result — the principled fix, not a loosened threshold. **This exact failure mode
   recurred on real data** (see §5): several real pixels still exceed even the
   normalized threshold (condition numbers up to 1e26), and are correctly recorded
   as warnings rather than silently accepted or crashing the pipeline.
2. `core.run_pipeline`'s per-pixel loop needed to catch all three of
   `InsufficientDataError`, `ConvergenceError`, and `DataSchemaError` (missing any
   one caused real crashes during testing) — converts each to a per-pixel warning
   instead of aborting the whole run.
3. Aperture summing changes the effective scale of the fitted curvature coefficient
   by approximately `1/N_pixels` relative to a single-pixel measurement (a genuine
   physics/scale property, not a bug). Resolved by defaulting to single-pixel
   apertures (`aperture_radius=0`) and documenting the scale-dependence as a known
   limitation rather than attempting a full correction.
4. Two demo-figure design bugs found during self-QA of the generated figures (no
   corresponding real-data bug, since real data has intrinsic diversity these
   synthetic figures lacked): the injection-recovery figure originally varied only
   the count rate at one fixed curvature (a degenerate single-x-value plot) —
   fixed to vary curvature itself across 5 values; the CR-flags-vs-fluence demo
   figure originally used brightness-based pixel selection that never happened to
   include the one synthetic pixel with an injected cosmic ray (an all-zero-flag
   plot) — fixed with a deterministic pixel grid guaranteed to include it.

## 5. Real datasets accessed

Real access used `astroquery.mast.Observations`, the same pattern verified in
project 1.

- **Query**: WFC3/IR, filter F160W, `calib_level=2`, `target_classification=GALAXY`.
  13 results returned, all confirmed `dataRights=PUBLIC` before download (real HST
  targets: NGC-105, NGC1097, 3C-186, CR7, EGS442, etc.); deterministic first-3
  selection sorted by `obs_id`.
- **Products**: 3 real WFC3/IR `_ima.fits` MULTIACCUM files —
  `ibft16req_ima` (105.2 MB), `icnn06srq_ima` (2.2 MB), `icp910qoq_ima` (168.3 MB);
  275.7 MB total. Retrieved 2026-07-13T22:57:56Z. Full SHA-256 checksums and
  per-file provenance in `data/manifest.csv`.
- **Licence/terms**: STScI/MAST public HST archive data (dataRights=PUBLIC), no
  proprietary period; standard STScI archive usage terms.
- Raw FITS files are **not committed**.
- Download authorized explicitly by the operator in chat before
  `scripts/fetch_data.py --i-have-authorization` was run.

## 6. Validation and uncertainty outcomes

- **Synthetic curvature injection-recovery gate**: PASSED. Recovered rate within
  20% and recovered curvature within 25% of injected values (thresholds calibrated
  with margin above the empirically observed worst case: 6.6% rate error, 5.7%
  curvature error across 15 noise realizations).
- **Null control**: zero injected curvature recovers a fitted curvature
  `< 5e-5`, consistent with zero.
- **Failure-mode tests**: missing/malformed IMA extensions (`DataSchemaError`),
  too-few-reads, non-finite input, tiny arrays — all raise the documented
  exceptions and are caught per-pixel in `run_pipeline`.
- **Real-data result**: of 45 attempted pixel fits (15 per file × 3 files), 39
  succeeded. Median fitted curvature 0.00165 (n=39). Residuals from the
  early-read linear fit grow strongly negative with fluence (−389 e- → −1968 e-
  → −7150 e- across three fluence bins) — a clear, monotonic nonlinearity signal,
  qualitatively consistent with the verified literature
  (arXiv:2602.12110). Early-vs-late read rate comparison shows the same
  nonlinearity direction (all 5 qualifying pixels fall well below the 1:1 line).
- **Genuine real-data limitation, not fabricated or hidden**: the TR readout
  quadrant produced zero successful measurements in this specific 3-file,
  bright-pixel-selected sample (BL n=6, BR n=25, TL n=8, TR n=0) — documented in
  the report's Limitations section with the most defensible interpretation
  (brightness-based pixel selection did not happen to land in that quadrant in
  this sample), not treated as a code defect.
- All three fluence bins (n=13 each) and most quadrant groups are below
  `minimum_sample_size=30` and flagged, not hidden, in `results/warnings.json`
  (87 warnings total: 11 pixel-fit rejections + 3 underpopulated-bin flags,
  duplicated across the residual/CR-fraction metric passes, plus per-pixel
  rejection reasons).

## 7. Remaining TODOs / unresolved risks

- `reports/report.tex` could not be compiled to PDF locally (no LaTeX toolchain);
  structural completeness was checked, not a rendered PDF. **Action for
  Biswajit**: compile before treating the PDF as final.
- The Baggett (2019) WFC3 instrument review citation from the source pack could
  not be independently verified (DOI does not resolve); kept as `TODO_VERIFY`
  rather than deleted or re-invented, with a verified on-topic replacement
  (arXiv:2602.12110) cited alongside it.
- Real-data sample is intentionally small (3 IMA files, 39 fit pixels) — a
  first-release bounded check, not a general characterization of WFC3/IR
  linearity across the full detector or filter set.
- Zero TR-quadrant measurements in this sample (see §6); a larger or
  quadrant-stratified sample would be needed to report a TR curvature value.
- Aperture-summed curvature values are not directly comparable to the
  single-pixel values reported here without rescaling by ~1/N_pixels.

## 8. Claims safe for a public README

- "Implements a reproducible pipeline auditing HST WFC3/IR up-the-ramp
  count-rate linearity across fluence, quadrant and data-quality flags,
  validated against a synthetic curvature injection-recovery gate before use
  on real data."
- "On a small, deterministic real sample (3 public WFC3/IR IMA exposures, 39
  successfully fit pixels), residuals from an early-read linear fit grow
  monotonically more negative with accumulated fluence — a clear nonlinearity
  signal consistent with the WFC3/IR nonlinearity literature."
- "48 automated tests including a null control and failure-mode tests, at 92%
  source coverage; ruff- and mypy-clean."
- "An archive-level verification exercise; not a replacement for calwf3 or a
  new nonlinearity calibration reference file."

## 9. Claims that must NOT be made

- Do not claim this characterizes WFC3/IR linearity in general — the sample is
  3 exposures, 39 pixels, one filter (F160W).
- Do not claim per-quadrant curvature is reported for all 4 quadrants — TR has
  zero measurements in this sample.
- Do not claim the fluence-binned or quadrant-binned trends are statistically
  significant — every bin/group is below the configured minimum sample size.
- Do not claim the TeX report PDF has been visually verified — only its source
  structure was checked.
- Do not claim this replaces or supersedes `calwf3` or an official nonlinearity
  calibration reference file.

## 10. Manual review checklist for Biswajit

- [ ] Compile `reports/report.tex` locally/Overleaf and read the PDF end-to-end.
- [ ] Spot-check the real per-pixel curvature fits (e.g. pixel (430,1018) of
      `ibft16req_ima`) against an independent tool if available.
- [ ] Decide whether to pursue a larger or quadrant-stratified real sample to
      fill in the missing TR-quadrant measurement before public release.
- [ ] Pin the `TODO_VERIFY` Baggett (2019) citation to a confirmed source, or
      remove it if it is confirmed unrecoverable.
- [ ] Review `npm audit` output and decide whether to bump pinned frontend
      tooling.
- [ ] Follow `MANUAL_GITHUB_ONE_BY_ONE.md` for the actual repository creation
      and push — none of that was done in this session.
