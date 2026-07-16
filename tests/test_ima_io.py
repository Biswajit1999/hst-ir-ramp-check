from __future__ import annotations

import numpy as np
import pytest
from astropy.io import fits

from hst_wfc3ir_ramp_linearity_audit.exceptions import DataSchemaError
from hst_wfc3ir_ramp_linearity_audit.ima_io import load_ima
from conftest import SyntheticRampSpec, build_synthetic_ima_hdulist


def test_load_ima_reads_synthetic_fixture(synthetic_ima_path):
    path, spec = synthetic_ima_path
    product = load_ima(path)
    assert len(product.reads) == spec.samptimes.size
    # sorted by increasing samptime
    samptimes = [r.samptime for r in product.reads]
    assert samptimes == sorted(samptimes)
    assert product.exposure_metadata["instrument"] == "WFC3"
    assert product.exposure_metadata["detector"] == "IR"


def test_load_ima_missing_file_raises():
    with pytest.raises(DataSchemaError):
        load_ima("does_not_exist.fits")


def test_load_ima_missing_nsamp_raises(tmp_path):
    hdul = fits.HDUList([fits.PrimaryHDU()])
    path = tmp_path / "no_nsamp.fits"
    hdul.writeto(path)
    with pytest.raises(DataSchemaError):
        load_ima(path)


def test_load_ima_no_sci_extensions_raises(tmp_path):
    primary = fits.PrimaryHDU(header=fits.Header({"NSAMP": 2}))
    hdul = fits.HDUList([primary])
    path = tmp_path / "no_sci.fits"
    hdul.writeto(path)
    with pytest.raises(DataSchemaError):
        load_ima(path)


def test_load_ima_missing_samptime_raises(tmp_path):
    primary = fits.PrimaryHDU(header=fits.Header({"NSAMP": 1}))
    sci_header = fits.Header({"EXTNAME": "SCI", "EXTVER": 1})  # no SAMPTIME
    sci = fits.ImageHDU(data=np.ones((5, 5)), header=sci_header, name="SCI", ver=1)
    err = fits.ImageHDU(data=np.ones((5, 5)), header=sci_header.copy(), name="ERR", ver=1)
    dq = fits.ImageHDU(data=np.zeros((5, 5), dtype=np.int16), header=sci_header.copy(), name="DQ", ver=1)
    hdul = fits.HDUList([primary, sci, err, dq])
    path = tmp_path / "no_samptime.fits"
    hdul.writeto(path)
    with pytest.raises(DataSchemaError):
        load_ima(path)


def test_load_ima_single_read_raises(tmp_path):
    spec = SyntheticRampSpec(count_rate=5.0, samptimes=np.array([0.0, 10.0]))
    hdul = build_synthetic_ima_hdulist(spec=spec)
    # Truncate to a single read's extensions plus primary
    truncated = fits.HDUList([hdul[0], hdul[1], hdul[2], hdul[3]])
    truncated[0].header["NSAMP"] = 1
    path = tmp_path / "single_read.fits"
    truncated.writeto(path)
    with pytest.raises(DataSchemaError):
        load_ima(path)
