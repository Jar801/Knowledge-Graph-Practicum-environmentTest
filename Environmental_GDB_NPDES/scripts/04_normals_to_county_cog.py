#!/usr/bin/env python3
"""
04_normals_to_county_cog.py

Compute county zonal means from NOAA 1991 to 2020 Gridded Climate Normals
served as Cloud-Optimized GeoTIFFs (COGs) on Microsoft Planetary Computer.

Inputs:
  --counties   Path to NC counties (GeoJSON/SHP/FGDB) with a FIPS/GEOID field
  --temp-cog   HTTPS signed URL (or local .tif) for annual mean temperature COG
  --prcp-cog   HTTPS signed URL (or local .tif) for annual precipitation COG
  --out        Output CSV path (default: Environmental_GDB_NPDES/data/processed/_ncei_normals_by_county.csv)

Output columns:
  fips, avg_temp_f, annual_precip_in, year
"""
import argparse
from pathlib import Path
import os
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import pandas as pd

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
        # GeoJSON default is WGS84; set it if missing
        g = g.set_crs("EPSG:4326")
    return g

def _zonal_mean(c_gdf: gpd.GeoDataFrame, raster_path: str):
    # Helpful GDAL tunings when reading remote COGs (optional)
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")

    with rasterio.Env():
        with rasterio.open(raster_path) as src:
            if src.crs is None:
                raise SystemExit(
                    f"[ERROR] {raster_path} has no CRS. Make sure you are using the "
                    "Planetary Computer COG (not a rendered image)."
                )
            c_proj = c_gdf.to_crs(src.crs)
            zs = zonal_stats(
                c_proj,
                raster_path,             # COG URL or local .tif
                stats=["mean"],
                nodata=src.nodata,
            )
            return [z["mean"] for z in zs]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--counties", required=True, help="County polygons with FIPS/GEOID")
    p.add_argument("--temp-cog", required=True, help="Signed COG URL (or local .tif) for annual mean temperature")
    p.add_argument("--prcp-cog", required=True, help="Signed COG URL (or local .tif) for annual precipitation")
    p.add