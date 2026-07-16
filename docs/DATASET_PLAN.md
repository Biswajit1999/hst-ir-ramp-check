# Dataset Plan

## Mode

**real public HST WFC3/IR IMA/FLT products**

## Official sources and literature seeds

- Baggett 2019 WFC3 instrument review, DOI:10.1007/s11214-019-0592-1
- STScI WFC3 Data Handbook
- STScI calwf3 documentation
- Recent WFC3/IR nonlinearity calibration literature
- MAST official archive documentation

## Acquisition rules

- Prefer official mission/archive endpoints and author-maintained catalogue deposits.
- Record product identifier, query, retrieval UTC, source URL, file size, checksum and licence/terms.
- Do not commit large raw FITS, HDF5 or catalogue files.
- Store a deterministic manifest under `data/manifest.csv`.
- Store only a tiny, clearly labelled synthetic/example dataset in `data/example/`.
- Never replace inaccessible real data with fabricated values while presenting them as observations.

## Required manifest columns

`product_id, source, source_url, retrieved_utc, sha256, file_size_bytes, selection_reason, licence_or_terms`

## FAIR contract

Every derived product must point to the raw product ID, software commit, configuration hash and transformation script.
