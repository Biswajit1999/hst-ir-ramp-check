from __future__ import annotations

from hst_wfc3ir_ramp_linearity_audit.config import load_config
from hst_wfc3ir_ramp_linearity_audit.provenance import (
    ManifestRow,
    append_manifest_row,
    get_git_commit,
    read_manifest,
    sha256_file,
)


def test_load_config_reads_real_project_config():
    cfg = load_config("config/analysis.yml")
    assert cfg.project.repository == "hst-wfc3ir-ramp-linearity-audit"
    assert cfg.execution.seed == 20260713
    assert cfg.validation.bootstrap_resamples == 1000


def test_manifest_roundtrip(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    row = ManifestRow(
        product_id="iedh16kqq_ima",
        source="MAST/HST",
        source_url="https://mast.stsci.edu",
        retrieved_utc="2026-07-13T00:00:00+00:00",
        sha256="0" * 64,
        file_size_bytes=136716480,
        selection_reason="unit test",
        licence_or_terms="STScI/MAST public HST archive data",
    )
    append_manifest_row(manifest_path, row)
    rows = read_manifest(manifest_path)
    assert len(rows) == 1
    assert rows[0]["product_id"] == "iedh16kqq_ima"


def test_sha256_file_matches_known_content(tmp_path):
    path = tmp_path / "sample.bin"
    path.write_bytes(b"hst-wfc3ir-ramp-linearity-audit")
    digest = sha256_file(path)
    assert len(digest) == 64
    assert digest == sha256_file(path)


def test_get_git_commit_never_raises(tmp_path):
    result = get_git_commit(tmp_path)
    assert isinstance(result, str)
    assert result != ""
