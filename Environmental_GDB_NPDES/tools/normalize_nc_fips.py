#!/usr/bin/env python3
"""
Normalize FIPS fields in all CSV files under a folder so that:
- FIPS is a string
- For North Carolina, FIPS = '37' + last 3 digits (county code)
  Examples: '00001' -> '37001', '001' -> '37001', '37119' stays '37119'

The script:
- Recursively finds all *.csv in the given folder
- Detects a FIPS-like column: one of {'fips','FIPS','GEOID','GEOID10','COUNTYFP','COUNTY_FIPS'}
- Creates a .bak backup next to each CSV
- Overwrites the CSV with normalized FIPS stored in a 'fips' column (lowercase)
"""

import argparse
import os
from pathlib import Path
import pandas as pd

FIPS_CANDIDATES = ["fips", "FIPS", "GEOID", "GEOID10", "COUNTYFP", "COUNTY_FIPS"]

def normalize_nc_fips(series: pd.Series) -> pd.Series:
    """
    Convert any incoming FIPS-like value to NC 5-digit string '37' + 3-digit county code.
    Logic:
      1) Coerce to string, keep only digits.
      2) If it already starts with '37' and has length >= 5, return first 5 chars (clean).
      3) Else, take the last 3 digits and prefix '37'.
      4) If fewer than 3 digits after cleaning, mark as NaN (cannot normalize).
    """
    s = series.astype(str).fillna("").str.replace(r"\D", "", regex=True)

    def fix_one(x: str) -> str:
        if x.startswith("37") and len(x) >= 5:
            return x[:5]
        # pull last 3 digits as county code
        cc = x[-3:] if len(x) >= 3 else None
        if cc:
            return f"37{cc}"
        return None  # will become NaN

    out = s.apply(fix_one)
    return pd.Series(out, index=series.index, dtype="string")

def process_csv(csv_path: Path, dry_run=False, verbose=True):
    try:
        df = pd.read_csv(csv_path, dtype="string")
    except Exception as e:
        if verbose:
            print(f"[SKIP] {csv_path} (could not read as CSV): {e}")
        return

    # detect a FIPS-like column
    src_col = None
    for c in FIPS_CANDIDATES:
        if c in df.columns:
            src_col = c
            break
    if not src_col:
        if verbose:
            print(f"[SKIP] {csv_path} (no FIPS-like column found)")
        return

    # normalize
    old = df[src_col].copy()
    df["fips"] = normalize_nc_fips(df[src_col])

    # report changes
    changed = (old.fillna("") != df["fips"].fillna("")).sum()
    missing = df["fips"].isna().sum()
    if verbose:
        print(f"[OK]   {csv_path.name}: normalized -> {changed} changed, {missing} missing")

    if dry_run:
        return

    # backup and overwrite
    bak = csv_path.with_suffix(csv_path.suffix + ".bak")
    try:
        if not bak.exists():
            csv_path.replace(bak)
        else:
            # if backup exists, keep it; just overwrite the original
            pass
        df.to_csv(csv_path, index=False)
        if verbose:
            print(f"      wrote: {csv_path} (backup: {bak.name})")
    except Exception as e:
        print(f"[ERR] {csv_path} (write failed): {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True, help="Folder to scan for CSV files (recursively)")
    ap.add_argument("--dry-run", action="store_true", help="Only report; do not write changes")
    ap.add_argument("--quiet", action="store_true", help="Less logging")
    args = ap.parse_args()

    folder = Path(args.folder)
    verbose = not args.quiet

    if not folder.exists():
        print(f"[ERR] Folder not found: {folder}")
        return

    csvs = list(folder.rglob("*.csv"))
    if verbose:
        print(f"Found {len(csvs)} CSV files under {folder}")

    for csv in csvs:
        process_csv(csv, dry_run=args.dry_run, verbose=verbose)

if __name__ == "__main__":
    main()