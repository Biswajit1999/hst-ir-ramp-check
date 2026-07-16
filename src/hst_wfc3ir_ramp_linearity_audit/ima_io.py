"""FITS ingestion for WFC3/IR MULTIACCUM IMA products.

Maps archive-specific FITS structure onto the logical fields documented in
data/INPUT_SCHEMA.md. An IMA file has one (SCI, ERR, DQ) extension triplet
per non-destructive read, EXTVER=1 being the last (deepest) read; this is
the long-documented WFC3 MULTIACCUM convention, still validated defensively
here rather than assumed silently.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits

from hst_wfc3ir_ramp_linearity_audit.exceptions import DataSchemaError


@dataclass(frozen=True)
class RampRead:
    extver: int
    samptime: float
    science: np.ndarray
    uncertainty: np.ndarray
    dq_mask: np.ndarray


@dataclass(frozen=True)
class IMAProduct:
    product_id: str
    reads: list[RampRead]  # ordered by increasing SAMPTIME (first read -> last read)
    exposure_metadata: dict[str, Any]
    calibration_reference_ids: dict[str, str]


def load_ima(path: str | Path) -> IMAProduct:
    """Load a WFC3/IR IMA file's per-read SCI/ERR/DQ triplets, ordered by SAMPTIME.

    Raises DataSchemaError for a missing file, missing NSAMP keyword, missing
    or mismatched SCI/ERR/DQ extensions, or fewer than 2 usable reads.
    """
    fits_path = Path(path)
    if not fits_path.is_file():
        raise DataSchemaError(f"FITS product not found: {fits_path}")

    with fits.open(fits_path) as hdul:
        primary_header = hdul[0].header
        if "NSAMP" not in primary_header:
            raise DataSchemaError(f"{fits_path.name} missing required NSAMP header keyword")
        nsamp = int(primary_header["NSAMP"])

        extvers = sorted({int(hdu.header["EXTVER"]) for hdu in hdul if hdu.name == "SCI"})
        if not extvers:
            raise DataSchemaError(f"{fits_path.name} has no SCI extensions")

        reads: list[RampRead] = []
        for extver in extvers:
            try:
                sci_hdu = hdul["SCI", extver]
                err_hdu = hdul["ERR", extver]
                dq_hdu = hdul["DQ", extver]
            except KeyError as exc:
                raise DataSchemaError(
                    f"{fits_path.name} missing SCI/ERR/DQ triplet for EXTVER={extver}"
                ) from exc

            if "SAMPTIME" not in sci_hdu.header:
                raise DataSchemaError(f"{fits_path.name} EXTVER={extver} missing SAMPTIME keyword")

            science = np.asarray(sci_hdu.data, dtype=float)
            uncertainty = np.asarray(err_hdu.data, dtype=float)
            dq = np.asarray(dq_hdu.data, dtype=int)
            if science.shape != uncertainty.shape or science.shape != dq.shape:
                raise DataSchemaError(
                    f"{fits_path.name} EXTVER={extver}: SCI/ERR/DQ array shapes disagree: "
                    f"{science.shape} vs {uncertainty.shape} vs {dq.shape}"
                )

            reads.append(
                RampRead(
                    extver=extver,
                    samptime=float(sci_hdu.header["SAMPTIME"]),
                    science=science,
                    uncertainty=uncertainty,
                    dq_mask=dq,
                )
            )

        reads.sort(key=lambda r: r.samptime)
        if len(reads) < 2:
            raise DataSchemaError(f"{fits_path.name} has fewer than 2 usable reads (found {len(reads)})")

        exposure_metadata: dict[str, Any] = {
            "instrument": str(primary_header.get("INSTRUME", "")),
            "detector": str(primary_header.get("DETECTOR", "")),
            "nsamp": nsamp,
            "n_reads_loaded": len(reads),
        }
        calibration_reference_ids = {
            key: str(primary_header[key]) for key in ("DARKFILE", "NLINFILE", "BPIXTAB") if key in primary_header
        }
        product_id = str(primary_header.get("ROOTNAME", fits_path.stem))

    return IMAProduct(
        product_id=product_id,
        reads=reads,
        exposure_metadata=exposure_metadata,
        calibration_reference_ids=calibration_reference_ids,
    )
