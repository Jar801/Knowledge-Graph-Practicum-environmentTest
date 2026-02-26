
#!/usr/bin/env python3
import argparse
from pathlib import Path
import geopandas as gpd
import fiona

"""
Impaired waters from FileGDB (polylines) → county intersection → miles per county.
"""

p = argparse.ArgumentParser()
p.add_argument('--impaired-gdb', required=True)
p.add_argument('--counties', required=True)
p.add_argument('--out', default='Environmental_GDB_NPDES/data/processed/impaired_streams_by_county.csv')
args = p.parse_args()

Path('Environmental_GDB_NPDES/data/processed').mkdir(parents=True, exist_ok=True)

layers = fiona.listlayers(args.impaired_gdb)
layer_candidates = [l for l in layers if any(k in l.lower() for k in ['impair','303','assess'])]
layer = layer_candidates[0] if layer_candidates else layers[0]

impaired = gpd.read_file(args.impaired_gdb, layer=layer)
counties = gpd.read_file(args.counties)

# FIPS field
fips_field = next((c for c in counties.columns if c.upper() in {'FIPS','COUNTYFP','COUNTY_FIPS','GEOID','GEOID10'}), None)
if fips_field is None:
    raise SystemExit('County layer: missing FIPS/GEOID field.')
counties['fips'] = counties[fips_field].astype(str).str.zfill(5)

# Project to EPSG:32119 for length (meters)
counties = counties.to_crs('EPSG:32119')
impaired = impaired.to_crs(counties.crs)

# Intersect and sum miles
inter = gpd.overlay(impaired[['geometry']], counties[['fips','geometry']], how='intersection')
inter['miles'] = inter.geometry.length * 0.000621371
miles = inter.groupby('fips')['miles'].sum().reset_index()
miles.rename(columns={'miles':'impaired_stream_miles'}, inplace=True)
miles.to_csv(args.out, index=False)
print('Impaired waters layer:', layer)
print('Wrote', args.out)
