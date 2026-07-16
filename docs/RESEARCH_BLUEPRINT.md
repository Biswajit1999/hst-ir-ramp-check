# Research Blueprint

## Technical title

HST WFC3/IR Up-the-Ramp Linearity Audit

## Category

Infrared detector instrumentation

## Bounded scientific question

How does count-rate linearity vary with accumulated fluence, quadrant and data-quality flags in selected WFC3/IR MULTIACCUM exposures?

## Gap statement

An archive-level verification; not a replacement for calwf3 or a new calibration reference file.

## First-release scope

The first release must be completable as a focused 4–6 hour implementation pass after data access is working. It must deliver one reproducible analysis pipeline, one deterministic example/smoke dataset, tests, 4–6 figures, a concise TeX report and a deployable research webpage.

## Validation and uncertainty

- synthetic linear ramp
- injected curvature recovery
- robust/weighted regression
- bootstrap by pixel/aperture
- quadrant/fluence splits

## Required figures

1. example ramp
2. residual vs fluence
3. quadrant distributions
4. early/late read comparison
5. injection recovery
6. CR flags vs fluence

## Reusable scientific modules

- `ima_io.py`
- `dq_masks.py`
- `ramp_model.py`
- `fluence_bins.py`
- `aperture_analysis.py`
- `uncertainty.py`
- `provenance.py`

## Explicit exclusions

- No novelty claim beyond the bounded dataset/question/method combination.
- No causal claim from descriptive catalogue correlations.
- No hidden manual data editing.
- No unsupported precision beyond the input uncertainties.
- No production-pipeline replacement claim.
