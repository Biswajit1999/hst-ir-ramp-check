from __future__ import annotations

import json

import pytest

from hst_wfc3ir_ramp_linearity_audit.exceptions import DataSchemaError
from hst_wfc3ir_ramp_linearity_audit.results_io import Metric, validate_summary, write_summary


def test_write_summary_roundtrip(tmp_path):
    metrics = [Metric(name="median_curvature", estimate=0.0003, units="dimensionless", sample_size=40, uncertainty_low=0.0002, uncertainty_high=0.0004)]
    path = tmp_path / "summary.json"
    payload = write_summary(path, "test-project", "synthetic_demo", metrics, {"git_commit": "abc"}, [])

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == payload
    assert loaded["metrics"][0]["name"] == "median_curvature"


def test_validate_summary_rejects_missing_top_key():
    with pytest.raises(DataSchemaError):
        validate_summary({"project": "x", "data_kind": "y", "metrics": [], "warnings": []})


def test_validate_summary_rejects_metric_missing_required_field():
    payload = {
        "project": "x",
        "data_kind": "y",
        "metrics": [{"name": "m", "estimate": 1.0}],
        "provenance": {},
        "warnings": [],
    }
    with pytest.raises(DataSchemaError):
        validate_summary(payload)
