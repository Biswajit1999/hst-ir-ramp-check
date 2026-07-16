# Implementation Plan — HST WFC3/IR Up-the-Ramp Linearity Audit

Status: Phase 1 (audit) complete.

## 1. Environment audit

- Same pinned dependency stack as projects 1 and 2 (numpy 1.26.4, scipy 1.13.1,
  astropy 6.1.0, astroquery 0.4.7, photutils 1.13.0, Python 3.11–3.12). Reused the
  shared `hst-acs-cte-audit` conda env; `pip install -e ".[dev]"` succeeded with all
  dependencies already satisfied.
- Same Node/npm and no-local-LaTeX constraints as prior projects.

## 2. Dataset decision (real data, verified live)

Unlike Euclid (project 2), WFC3/IR is served directly by MAST, same access pattern
as project 1 (`astroquery.mast.Observations`).

- Queried live for real public WFC3/IR galaxy-targeted exposures, filter F160W,
  `calib_level=2`, `target_classification=GALAXY`: 13 results, all confirmed
  `dataRights=PUBLIC` (e.g. NGC-105, NGC1097, 3C-186, CR7, EGS442 — real HST targets).
- Confirmed both `_ima.fits` (all MULTIACCUM non-destructive reads, ~137 MB) and
  `_flt.fits` (final calibrated single-frame product, ~16.5 MB) are available per
  exposure. The ramp-linearity science question needs the **IMA** product — it
  contains every individual read of the up-the-ramp sample sequence.
- **Sample budget:** 3 real IMA files (~410 MB total) — comparable to project 1's
  budget, smaller than a full multi-target survey. Real download requires explicit
  operator authorization before `scripts/fetch_data.py` is run for real.
- Licence: STScI/MAST public HST archive data, same terms as project 1.

## 3. Literature verification (done in Phase 1)

- **Baggett 2019 WFC3 instrument review, DOI:10.1007/s11214-019-0592-1**: could
  **not** be verified. The DOI does not resolve (404 via doi.org, 404 via
  link.springer.com, 404 via the CrossRef API `api.crossref.org/works/...`), and a
  web search did not turn up an independently confirmable primary source (one search
  result made an unsupported claim citing "Spanish Wikipedia" that does not match any
  actual URL returned — not trusted). **Marked `TODO_VERIFY` in `references.bib`**,
  per the explicit instruction not to invent metadata when a citation cannot be
  confirmed.
- **New, directly relevant, independently verified addition**: Huynh, Bajaj,
  Marinelli, Mack, Shenoy & Grogin, "Testing and Validation of the Updated
  Pixel-Based Non-Linearity Calibration File for WFC3/IR", WFC3 Instrument Science
  Report 2025-09, arXiv:2602.12110 (2026) — verified against the arXiv abstract page,
  directly on-topic (WFC3/IR nonlinearity calibration), added to the literature set.
- STScI WFC3 Data Handbook / calwf3 documentation / MAST archive documentation: will
  cite as institutional documentation (stable URL, no invented DOI); marked
  `TODO_VERIFY` only if no stable citation form is found.

## 4. Scientific method (bounded to the stated question)

**Question**: How does count-rate linearity vary with accumulated fluence, quadrant
and data-quality flags in selected WFC3/IR MULTIACCUM exposures?

WFC3/IR reads out non-destructively at increasing sample times within a single
exposure (the MULTIACCUM sequence), producing a "ramp" of accumulated counts per
pixel vs. time. For a source with constant illumination, accumulated counts should
increase linearly with time (constant count rate); real WFC3/IR detectors show
count-rate nonlinearity that grows with accumulated fluence (well documented in the
verified literature above), which the standard calibration partially corrects.

1. **IMA structure**: each real IMA file has one (SCI, ERR, DQ, SAMP, TIME)
   extension quintet per non-destructive read, `EXTVER=1` is the last (deepest,
   final) read and `EXTVER=NSAMP` is the first (shallowest) read — the standard,
   long-documented WFC3 MULTIACCUM convention (not the same brand-new-format
   uncertainty risk as Euclid; still validated defensively — `ima_io.py` raises a
   clear `DataSchemaError` if the expected extension pattern is absent).
2. **Ramp extraction** (`ima_io.py`, `aperture_analysis.py`): for a chosen pixel or
   small aperture, extract accumulated counts vs. `SAMPTIME` across all reads.
3. **Ramp model** (`ramp_model.py`): fit a robust/weighted linear regression
   (accumulated counts vs. time) to the *early* reads (low accumulated fluence,
   where linearity should hold best) and compute residuals of *all* reads from that
   fit — growing residuals at high fluence are the nonlinearity signal. Compare
   early-read-only vs. all-reads fits (the "early/late read comparison" figure).
4. **Fluence bins** (`fluence_bins.py`): bin residuals by accumulated fluence,
   flagging underpopulated bins.
5. **DQ / cosmic rays** (`dq_masks.py`): WFC3/IR DQ flags include per-read
   cosmic-ray hits; report how CR-flagged read fraction depends on accumulated
   fluence (the "CR flags vs fluence" figure) and exclude flagged reads from the
   linearity fit (with the exclusion count reported, not silently applied).
6. **Quadrant splits**: WFC3/IR has 4 readout quadrants (amplifiers); results are
   reported per-quadrant to test the "varies with quadrant" part of the question.
7. **Synthetic validation gate**: inject a known linear ramp (given count rate) plus
   a known injected curvature (nonlinearity) into synthetic MULTIACCUM-like data,
   and confirm the fitting pipeline recovers both the linear rate and the injected
   curvature within a documented tolerance, before touching real IMA data.

## 5. File-level task list

### Phase 2 — Foundation
Port `config.py`, `exceptions.py` (+ `ArchiveAccessError`, `ConvergenceError`,
`InsufficientDataError`), `logging_utils.py`, `provenance.py`, `results_io.py` from
the established pattern, adapted to package name `hst_wfc3ir_ramp_linearity_audit`.

### Phase 3 — Data layer
- `scripts/fetch_data.py`: real MAST query (galaxy targets, F160W, calib_level=2,
  PUBLIC only), deterministic first-N selection, IMA download, SHA-256, manifest.
  Gated behind `--i-have-authorization`.
- `src/hst_wfc3ir_ramp_linearity_audit/synthetic.py`: synthetic MULTIACCUM ramp
  generator (linear rate + optional injected curvature + optional CR hits), shared
  by tests and `--demo` scripts.

### Phase 4 — Scientific modules (`src/hst_wfc3ir_ramp_linearity_audit/`)
- `ima_io.py`: load an IMA file's per-read SCI/ERR/DQ/SAMPTIME quintets.
- `dq_masks.py`: WFC3/IR DQ bit interpretation (verify bit meanings against real
  calwf3/CRDS documentation before asserting specific bit numbers, mirroring the
  project-1 HOTPIX-verification approach — do not assume without checking).
- `ramp_model.py`: robust/weighted linear ramp fit + residual computation.
- `fluence_bins.py`: fluence-binned residual statistics, flagging underpopulated
  bins (same `bin_scalar_statistic` pattern as prior projects).
- `aperture_analysis.py`: per-pixel/aperture ramp extraction from a loaded IMA.
- `uncertainty.py`, `provenance.py`, `results_io.py`: same bootstrap /
  fit-convergence-separation pattern as projects 1–2.
- `core.py`: `run_pipeline()` orchestrator; keep starter `demo_series`/
  `robust_summary`.

### Phase 5 — Validation and QA
- Synthetic linear-ramp + injected-curvature recovery test (the required gate).
- Robust vs. weighted regression comparison test.
- Bootstrap-by-pixel/aperture test.
- Quadrant/fluence split tests.
- Null control (zero injected curvature ⇒ recovered curvature consistent with zero).
- Failure tests: missing/malformed IMA extensions, too-few-reads, non-finite input.
- Benchmarks per the established tracemalloc + perf_counter pattern.

### Phase 6 — Figures and report
Six figures per `docs/FIGURE_AND_UI_SPEC.md`: example ramp, residual vs fluence,
quadrant distributions, early/late read comparison, injection recovery, CR flags vs
fluence. `reports/report.tex`/`references.bib` completed from real
`results/summary.json`; Baggett 2019 entry marked `TODO_VERIFY`.

### Phase 7 — React dashboard
Same established pattern (fetch generated JSON, figure gallery, provenance,
methodology/validation/limitations, no fake live-data language); proactively apply
the `eslint.config.js` `react/jsx-uses-vars` fix and remove unused `recharts` from
the start, rather than rediscovering the scaffold bug a third time.

### Phase 8 — Verification
Same command sequence as projects 1–2; write `LOCAL_COMPLETION_REPORT.md`.

## 6. Validation thresholds (from `docs/VALIDATION_CONTRACT.md`, made concrete)

| Check | Threshold |
|---|---|
| Synthetic linear rate recovery | within 10% of injected count rate |
| Synthetic injected curvature recovery | within 20% of injected curvature coefficient |
| Minimum sample size per bin | ≥30 (config), underpopulated bins flagged not dropped |
| Bootstrap resamples | 1000, seed 20260713 |
| Finite-value check | 100% of reported metric arrays finite after documented masking |
| Null control | zero injected curvature ⇒ recovered curvature consistent with 0 at 95% CI |

## 7. Unresolved risks / stop-condition watchlist

- **WFC3/IR DQ bit meanings must be verified against real CALWF3/CRDS documentation**
  before being asserted as fact in `dq_masks.py` (mirrors the project-1 approach of
  checking HOTPIX=16 against the real hstcal source rather than assuming).
- **Baggett 2019 citation is unverifiable** — kept as `TODO_VERIFY`, not removed
  (it may still be a real paper with an incorrect DOI in the pack), with a real,
  independently-verified replacement/supplement already identified (arXiv:2602.12110).
- IMA file structure is a long-standated, well-documented WFC3 convention (lower risk
  than Euclid's brand-new 2025 format), but `ima_io.py` still validates defensively
  and raises `DataSchemaError` rather than assuming silently.
- Per `docs/VALIDATION_CONTRACT.md` stop conditions: if synthetic injection-recovery fails, stop
  and document rather than proceeding to real IMA data.

## 8. Non-negotiables carried forward

No `git commit`/`push`/remote creation. Biswajit
Jana remains sole author in `CITATION.cff`. No fabricated data, benchmarks, or
citation metadata. Real-data download requires explicit operator authorization in
chat before execution.
