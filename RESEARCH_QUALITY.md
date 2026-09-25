# Research Quality Upgrade

This release changes the project from a plausible-looking exploratory notebook into a falsifiable, receipt-backed calibration audit. The most important upgrade is scientific self-correction: the original headline was withdrawn after the FITS units and calibration state were checked.

## Before and after

The maturity score is a repository-maintenance rubric, not peer review and not a measure of scientific truth. Each dimension is scored from 0 to 20 using visible repository evidence.

| Dimension | Before | After | Evidence added |
|---|---:|---:|---|
| Measurement validity | 4 | 19 | Unit-aware `SCI`/`ERR` conversion, positive-time gating, `NLINCORR` boundary |
| Data provenance | 11 | 20 | Exact MAST URLs, retrieval time, file size, SHA-256 hard gate |
| Robustness | 7 | 18 | 18 predeclared selection designs and per-exposure ranges |
| Reproducibility | 13 | 19 | Pinned Python package set, deterministic selection, machine-readable outputs, CI |
| Communication | 12 | 18 | Correction notice, limitations, accessible evidence dashboard, downloadable tables |
| **Total** | **47/100** | **94/100** | See `assets/research-maturity-before-after.svg` |

## Validation layers

1. The loader tests both `ELECTRONS/S` conversion and already-accumulated `ELECTRONS` handling.
2. Manifest verification rejects a missing, wrong-sized, or wrong-hash input before analysis.
3. Synthetic injection/recovery and null controls test the numerical model independently of archive interpretation.
4. Real-data analysis excludes zero-time reads, flagged samples, non-positive slope segments, and under-sampled exposures.
5. Sensitivity analysis varies pixel count, minimum separation, and early-window fraction without hiding unfavorable designs.
6. The web build serves generated artifacts rather than hand-entered headline values.

## Claim boundary

The result describes two usable calibrated exposures and deterministically selected bright pixels. It does not establish a detector-wide effect, infer a new nonlinearity correction, or separate detector behavior from scene, background, pointing, persistence, and pipeline-calibration residuals. Those questions require a larger observation design with independent exposure-level replication.
