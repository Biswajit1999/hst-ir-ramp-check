# Exposure-aware ramp uncertainty

The 70 published pixel measurements come from only two usable real WFC3/IR IMA exposures. Treating all pixels as independent would overstate the effective replication. This follow-up therefore reports both a conventional pixel bootstrap and an equal-exposure estimator obtained by resampling pixels within each exposure and averaging the two exposure medians.

It also reports each exposure separately, tests the rank association between residual late/early drift and maximum accumulated fluence, and compares robust Theil--Sen ramp rates against weighted least-squares rates. Units remain electrons, electrons per second and fractional rate change.

Neither interval is a population uncertainty: the pixel interval assumes exchangeable pixels, while the balanced interval conditions on the same two fixed exposures. Detector-wide and visit-level systematics remain unconstrained. All inputs are measurements derived from the three provenance-verified public IMA files; the third exposure remains excluded by the original minimum-read gate.

The pooled-pixel median is -1.60% with a percentile interval from -3.46% to -0.57%. Equal exposure weighting shifts the point estimate to -0.76% and its within-exposure interval spans -2.85% to +8.21%. The change is the central scientific result of this audit: the apparent sign stability is sensitive to the dependence structure and cannot be promoted to an exposure-population claim.

Run `python scripts/analyze_clustered_uncertainty.py` from the repository environment.
