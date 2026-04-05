"""
fetch_ppd.py — Download HM Land Registry Price Paid Data for the last N years.

HM Land Registry publishes annual CSV files at:
  https://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com/
  pp-{year}.csv          — full year
  pp-complete.csv        — entire history (4GB+, skip this)
  pp-monthly-update.csv  — current month delta

Usage:
    python fetch_ppd.py [--years 3] [--outdir ./raw]
"""
import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

BASE_URL = "https://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com/"

# PPD column names (no header row in the CSV)
PPD_COLUMNS = [
    "transaction_id",
    "price",
    "date",
    "postcode",
    "property_type",   # D=detached, S=semi, T=terraced, F=flat, O=other
    "new_build",       # Y/N
    "duration",        # F=freehold, L=leasehold, U=unknown
    "paon",            # primary addressable object name
    "saon",            # secondary
    "street",
    "locality",
    "town",
    "district",
    "county",
    "ppd_category",    # A=standard, B=additional (repossessions etc.)
    "record_status",   # A=addition, C=change, D=delete
]


def fetch_year(year: int, outdir: Path, overwrite: bool = False) -> Path:
    filename = f"pp-{year}.csv"
    outpath = outdir / filename

    if outpath.exists() and not overwrite:
        print(f"  {filename} already exists, skipping.")
        return outpath

    url = BASE_URL + filename
    print(f"  Downloading {url} …")

    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0))
    outdir.mkdir(parents=True, exist_ok=True)

    with open(outpath, "wb") as f, tqdm(
        total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=filename
    ) as bar:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
            bar.update(len(chunk))

    return outpath


def fetch_current_month(outdir: Path) -> Path:
    filename = "pp-monthly-update.csv"
    outpath = outdir / filename
    url = BASE_URL + filename
    print(f"  Downloading {url} …")

    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0))
    outdir.mkdir(parents=True, exist_ok=True)

    with open(outpath, "wb") as f, tqdm(
        total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=filename
    ) as bar:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
            bar.update(len(chunk))

    return outpath


def main():
    parser = argparse.ArgumentParser(description="Download HM Land Registry PPD data")
    parser.add_argument("--years", type=int, default=3, help="Number of past years to download (default: 3)")
    parser.add_argument("--outdir", type=str, default="./raw", help="Output directory for CSVs")
    parser.add_argument("--overwrite", action="store_true", help="Re-download even if file exists")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    current_year = datetime.now().year

    print(f"Downloading PPD data for {args.years} year(s) into {outdir}/")

    files = []
    for year in range(current_year - args.years, current_year):
        try:
            f = fetch_year(year, outdir, overwrite=args.overwrite)
            files.append(f)
        except requests.HTTPError as e:
            print(f"  Warning: could not download {year}: {e}", file=sys.stderr)
        time.sleep(0.5)

    # Also grab the current year's monthly update
    try:
        f = fetch_current_month(outdir)
        files.append(f)
    except requests.HTTPError as e:
        print(f"  Warning: could not download monthly update: {e}", file=sys.stderr)

    print(f"\nDownloaded {len(files)} file(s):")
    for f in files:
        size_mb = f.stat().st_size / 1e6
        print(f"  {f.name}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
