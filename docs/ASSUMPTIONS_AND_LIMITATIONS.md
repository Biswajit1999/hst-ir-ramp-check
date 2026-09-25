# Assumptions and limitations

## Assumptions enforced in code

- Each IMA read exposes a matched `SCI`, `ERR`, `DQ`, `SAMP`, and `TIME` extension at the same `EXTVER`.
- `ELECTRONS/S` arrays become accumulated electrons only after multiplication by the read-specific `TIME.PIXVALUE`; `ELECTRONS` arrays need no conversion. Unknown units raise an error.
- A usable exposure contains at least six finite, positive-time reads after quality masking.
- Selected pixels are finite and DQ-clean in the deepest read and are separated by the configured minimum distance.
- Early and late slope windows are disjoint and each contains enough samples for weighted fitting.

## Interpretive limitations

- `NLINCORR=COMPLETE` for every input. Residual drift is not an independent measurement of raw detector nonlinearity.
- Only two of three preselected exposures pass the read-count gate. Exposure-level replication is too small for a population interval.
- Bright selected pixels are deterministic descriptive samples, not independent draws from the detector population.
- Pixel measurements within an exposure share observing conditions and calibration history; treating them as independent would overstate precision.
- Residual trends may combine detector response, source or scene evolution, pointing, persistence, background estimation, and other pipeline effects.
- Sensitivity checks cover three declared analysis choices, not every plausible model or target-selection decision.
- Synthetic recovery validates implementation behavior under its own generative assumptions; it does not validate the real-data causal interpretation.

The public dashboard intentionally presents ranges, exclusions, and a claim boundary instead of a detector-wide confidence interval.
