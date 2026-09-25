from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_published_robustness_contract() -> None:
    payload = json.loads((ROOT / "results" / "robustness.json").read_text(encoding="utf-8"))
    assert payload["design_count"] == 18
    assert payload["positive_pooled_designs"] == 0
    assert payload["pooled_median_rate_change_range"][1] < 0
    assert payload["usable_exposures"] == ["ibft16req_ima", "icp910qoq_ima"]
    assert "not a detector nonlinearity calibration" in payload["claim_boundary"]

    with (ROOT / "results" / "robustness_designs.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        designs = list(csv.DictReader(handle))
    assert len(designs) == 18
    assert {int(row["n_pixels_requested_per_exposure"]) for row in designs} == {20, 40}
    assert {int(row["minimum_separation_pixels"]) for row in designs} == {3, 5, 7}
    assert {float(row["early_fraction"]) for row in designs} == {0.4, 0.5, 0.6}


def test_published_summary_records_release_provenance() -> None:
    payload = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
    assert payload["project"] == "HST WFC3/IR Calibrated Ramp-Stability Audit"
    assert payload["data_kind"] == "real public calibrated HST WFC3/IR IMA products"
    assert payload["provenance"]["git_commit"] != "LOCAL_UNCOMMITTED"
    assert payload["provenance"]["package_version"] == "1.0.0"
    assert len(payload["provenance"]["input_receipts"]) == 3


def test_dashboard_serves_exact_generated_result_files() -> None:
    for name in (
        "summary.json",
        "warnings.json",
        "benchmarks.json",
        "measurements.csv",
        "robustness.json",
        "robustness_designs.csv",
    ):
        assert (ROOT / "web-react" / "public" / "results" / name).read_bytes() == (
            ROOT / "results" / name
        ).read_bytes()
