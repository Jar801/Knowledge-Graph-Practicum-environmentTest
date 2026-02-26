#!/usr/bin/env python3
"""
04_normals_to_county_cog.py

Compute county zonal means from NOAA 1991–2020 Gridded Climate Normals
stored as local Cloud-Optimized GeoTIFFs (COGs).

Inputs (local files):
  --counties   Path to county polygons (GeoJSON/SHP/FGDB) with a FIPS/GEOID field
  --temp-tif   Path to annual mean temperature COG (.tif)
  --prcp-tif   Path to annual precipitation COG (.tif)
  --out        Output CSV (default: Environmental_GDB_NPDES/data/processed/_ncei_normals_by_county.csv)

Outputs:
  CSV with columns: fips, avg_temp_f, annual_precip_in, year
"""

import argparse
from pathlib import Path
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import pandas as pd
import sys

DEFAULT_TEMP = "Environmental_GDB_NPDES/data/raw/ncei_normals_temp.tif"
DEFAULT_PRCP = "Environmental_GDB_NPDES/data/raw/ncei_normals_prcp.tif"
DEFAULT_OUT  = "Environmental_GDB_NPDES/data/processed/ncei_normals_by_county.csv"

def _read_counties_with_fips(counties_path: str) -> gpd.GeoDataFrame:
    g = gpd.read_file(counties_path)
    fips_field = next(
        (c for c in g.columns if c.upper() in {"FIPS", "COUNTYFP", "COUNTY_FIPS", "GEOID", "GEOID10"}),
        None
    )
    if fips_field is None:
        raise SystemExit("[ERROR] County layer must contain a FIPS/GEOID field.")
    g["fips"] = g[fips_field].astype(str).str.zfill(5)
    if g.crs is None:
        # GeoJSON default; set if missing
        g = g.set_crs("EPSG:4326")
    return g

def _zonal_mean(c_gdf: gpd.GeoDataFrame, raster_path: str, stat="mean"):
    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise SystemExit(
                f"[ERROR] {raster_path} has no CRS. Ensure this is the true COG/GeoTIFF, not a rendered image."
            )
        c_proj = c_gdf.to_crs(src.crs)
        zs = zonal_stats(
            c_proj,
            raster_path,
            stats=[stat],
            nodata=src.nodata,
        )
        return [z[stat] for z in zs]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--counties", required=True, help="County polygons with FIPS/GEOID (GeoJSON/SHP/FGDB)")
    p.add_argument("--temp-tif", default=DEFAULT_TEMP, help=f"Annual mean temperature COG (default: {DEFAULT_TEMP})")
    p.add_argument("--prcp-tif", default=DEFAULT_PRCP, help=f"Annual precipitation COG (default: {DEFAULT_PRCP})")
    p.add_argument("--out", default=DEFAULT_OUT, help=f"Output CSV (default: {DEFAULT_OUT})")
    args = p.parse_args()

    # Basic existence checks
    for pth in [args.counties, args.temp_tif, args.prcp_tif]:
        if not Path(pth).exists():
            sys.exit(f"[ERROR] File not found: {pth}")

    Path(Path(args.out).parent).mkdir(parents=True, exist_ok=True)

    # Load counties
    counties = _read_counties_with_fips(args.counties)

    # Zonal means
    out = pd.DataFrame({"fips": counties["fips"]})
    out["avg_temp_f"] = _zonal_mean(counties, args.temp_tif, stat="mean")
    out["annual_precip_in"] = _zonal_mean(counties, args.prcp_tif, stat="mean")
    out["year"] = 2020  # 1991–2020 normals period label

    out.to_csv(args.out, index=False)
    print("Wrote", args.out)

if __name__ == "__main__":
    main()