from __future__ import annotations

import pytest

from hst_wfc3ir_ramp_linearity_audit.config import load_config
from hst_wfc3ir_ramp_linearity_audit.core import run_pipeline, select_bright_pixels
from hst_wfc3ir_ramp_linearity_audit.exceptions import InsufficientDataError
from hst_wfc3ir_ramp_linearity_audit.ima_io import load_ima
from conftest import SyntheticRampSpec, build_synthetic_ima_hdulist


def test_select_bright_pixels_excludes_edges(synthetic_ima_path):
    path, spec = synthetic_ima_path
    product = load_ima(path)
    pixels = select_bright_pixels(product, n_pixels=5, edge_margin=3)
    for x, y in pixels:
        assert 3 <= x < 20 - 3
        assert 3 <= y < 20 - 3


def test_select_bright_pixels_rejects_tiny_array():
    from hst_wfc3ir_ramp_linearity_audit.ima_io import IMAProduct, RampRead
    import numpy as np

    reads = [
        RampRead(extver=1, samptime=1.0, science=np.ones((4, 4)), uncertainty=np.ones((4, 4)), dq_mask=np.zeros((4, 4), dtype=int))
    ]
    product = IMAProduct(product_id="x", reads=reads, exposure_metadata={}, calibration_reference_ids={})
    with pytest.raises(InsufficientDataError):
        select_bright_pixels(product, n_pixels=1, edge_margin=5)


def test_run_pipeline_end_to_end_on_synthetic_ima(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    config = load_config("config/analysis.yml")

    spec = SyntheticRampSpec(count_rate=20.0, curvature=0.0003, read_noise=5.0)
    hdul = build_synthetic_ima_hdulist(spec=spec, size=30, cosmic_ray_read_index=3, seed=42)
    hdul.writeto(raw_dir / "synth1_ima.fits")

    manifest_rows = [{"product_id": "synth1_ima"}]
    result = run_pipeline(manifest_rows, raw_dir, config, n_pixels_per_file=15, aperture_radius=0)

    assert len(result.measurements) == 15
    assert set(result.quadrant_summary.keys()).issubset({"BL", "BR", "TL", "TR"})
    assert any("minimum_sample_size" in w for w in result.warnings)


def test_run_pipeline_raises_on_empty_manifest(tmp_path):
    config = load_config("config/analysis.yml")
    with pytest.raises(InsufficientDataError):
        run_pipeline([], tmp_path, config)


def test_run_pipeline_warns_not_crashes_on_missing_file(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    config = load_config("config/analysis.yml")
    manifest_rows = [{"product_id": "missing_ima"}]
    with pytest.raises(InsufficientDataError):
        # the only file is missing -> no usable measurements -> raises
        run_pipeline(manifest_rows, raw_dir, config)
