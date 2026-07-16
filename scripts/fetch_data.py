"""Deterministic, provenance-recording fetch of real public WFC3/IR IMA data.

Queries MAST directly (no fabricated metadata) via astroquery.mast.Observations,
same access pattern verified in project 1 (hst-acs-two-axis-cte-audit). IMA
products (~137 MB each) contain the full MULTIACCUM ramp needed for the
linearity analysis; FLT (final calibrated single-frame, ~16.5 MB) is not
downloaded since it discards the individual reads.

This script performs real network downloads and must only be invoked with
explicit user authorization for the session, per docs/DATASET_PLAN.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from hst_wfc3ir_ramp_linearity_audit.exceptions import ArchiveAccessError
from hst_wfc3ir_ramp_linearity_audit.logging_utils import get_logger
from hst_wfc3ir_ramp_linearity_audit.provenance import ManifestRow, append_manifest_row, sha256_file

LOGGER = get_logger(__name__)

INSTRUMENT = "WFC3/IR"
FILTER_NAME = "F160W"
TARGET_CLASSIFICATION = "GALAXY"
LICENCE_TERMS = (
    "STScI/MAST public HST archive data (dataRights=PUBLIC), no proprietary period; "
    "standard STScI archive usage terms apply, https://archive.stsci.edu/copyright.html"
)
SOURCE_URL = "https://mast.stsci.edu"


def _select_observations(n_exposures: int):
    """Query MAST for a deterministic sample of real public WFC3/IR galaxy exposures.

    Raises ArchiveAccessError if the query fails, returns no rows, or any
    selected observation is not confirmed PUBLIC.
    """
    try:
        from astroquery.mast import Observations
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ArchiveAccessError("astroquery is not installed in this environment") from exc

    try:
        obs = Observations.query_criteria(
            obs_collection="HST",
            instrument_name=INSTRUMENT,
            dataproduct_type="image",
            calib_level=[2],
            filters=FILTER_NAME,
            target_classification=TARGET_CLASSIFICATION,
        )
    except Exception as exc:  # noqa: BLE001
        raise ArchiveAccessError(f"MAST query failed: {exc}") from exc

    if len(obs) == 0:
        raise ArchiveAccessError(
            f"MAST query for {INSTRUMENT} {FILTER_NAME} galaxy targets returned zero observations"
        )

    obs.sort("obs_id")
    selected = obs[:n_exposures]
    for row in selected:
        if str(row["dataRights"]) != "PUBLIC":
            raise ArchiveAccessError(
                f"observation {row['obs_id']} is not PUBLIC (dataRights={row['dataRights']!r}); refusing to download"
            )
    return selected


def _download_ima(observations, out_dir: Path) -> list[Path]:
    from astroquery.mast import Observations

    out_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    for row in observations:
        try:
            products = Observations.get_product_list(observations[observations["obs_id"] == row["obs_id"]])
        except Exception as exc:  # noqa: BLE001
            raise ArchiveAccessError(f"failed to list products for {row['obs_id']}: {exc}") from exc

        subset = products[products["productSubGroupDescription"] == "IMA"]
        if len(subset) == 0:
            raise ArchiveAccessError(f"no IMA product found for {row['obs_id']}")

        download_manifest = Observations.download_products(subset, download_dir=str(out_dir))
        for local_path_str in download_manifest["Local Path"]:
            downloaded.append(Path(local_path_str))
    return downloaded


def _flatten(paths: list[Path], out_dir: Path) -> list[Path]:
    import shutil

    flat_paths = []
    for path in paths:
        flat_path = out_dir / path.name
        if path != flat_path:
            shutil.move(str(path), str(flat_path))
        flat_paths.append(flat_path)
    mast_download_dir = out_dir / "mastDownload"
    if mast_download_dir.is_dir():
        shutil.rmtree(mast_download_dir, ignore_errors=True)
    return flat_paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-exposures", type=int, default=3)
    parser.add_argument("--out-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.csv"))
    parser.add_argument(
        "--i-have-authorization",
        action="store_true",
        help=(
            "Required flag confirming the operator has explicitly authorized this "
            "real network download in the current session."
        ),
    )
    args = parser.parse_args()

    if not args.i_have_authorization:
        raise SystemExit(
            "Refusing to download real archive data without --i-have-authorization. "
            "This flag exists so the download only runs after the operator has "
            "explicitly confirmed it in the current session (see docs/DATASET_PLAN.md)."
        )

    selected = _select_observations(args.n_exposures)
    LOGGER.info("Selected %d observations", len(selected))

    downloaded = _download_ima(selected, args.out_dir)
    downloaded = _flatten(downloaded, args.out_dir)
    retrieved_utc = datetime.now(timezone.utc).isoformat()

    for local_path in downloaded:
        if not local_path.is_file():
            raise ArchiveAccessError(f"expected downloaded file missing: {local_path}")
        digest = sha256_file(local_path)
        size = local_path.stat().st_size
        row = ManifestRow(
            product_id=local_path.stem,
            source="MAST/HST",
            source_url=SOURCE_URL,
            retrieved_utc=retrieved_utc,
            sha256=digest,
            file_size_bytes=size,
            selection_reason=(
                f"deterministic first-{args.n_exposures} public {INSTRUMENT} {FILTER_NAME} "
                f"{TARGET_CLASSIFICATION} exposure sample, sorted by obs_id, for MULTIACCUM "
                "ramp linearity audit"
            ),
            licence_or_terms=LICENCE_TERMS,
        )
        append_manifest_row(args.manifest, row)
        LOGGER.info("Recorded manifest row for %s (%d bytes)", local_path.name, size)

    print(f"Downloaded and recorded {len(downloaded)} IMA files under {args.out_dir}")


if __name__ == "__main__":
    main()
