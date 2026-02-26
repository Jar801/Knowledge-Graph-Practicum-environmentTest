
#!/usr/bin/env python3
import argparse
from pathlib import Path
import geopandas as gpd
import fiona

"""
NPDES permits from FileGDB (points) → filter ACTIVE → point-in-polygon count per county.
"""

p = argparse.ArgumentParser()
p.add_argument('--npdes-gdb', required=True)
p.add_argument('--counties', required=True)
p.add_argument('--out', default='Environmental_GDB_NPDES/data/processed/npdes_active_by_county.csv')
args = p.parse_args()

Path('Environmental_GDB_NPDES/data/processed').mkdir(parents=True, exist_ok=True)

layers = fiona.listlayers(args.npdes_gdb)
layer_candidates = [l for l in layers if any(k in l.lower() for k in ['npdes','permit','waste','wastewater'])]
layer = layer_candidates[0] if layer_candidates else layers[0]

npdes = gpd.read_file(args.npdes_gdb, layer=layer)
counties = gpd.read_file(args.counties)

# Find status field
status_field = None
for c in npdes.columns:
    lc = c.lower()
    if lc in {'status','permit_status','permitstatus','facility_status','fac_status'}:
        status_field = c
        break
if status_field is None:
    # Try to infer from typical attribute samples
    for c in npdes.columns:
        if 'status' in c.lower():
            status_field = c
            break
if status_field is None:
    raise SystemExit('NPDES GDB: could not find a status field. Please inspect attributes and edit the script.')

npdes['__status__'] = npdes[status_field].astype(str).str.upper()
active = npdes[npdes['__status__'].str.contains('ACTIVE')].copy()

# Counties FIPS
fips_field = next((c for c in counties.columns if c.upper() in {'FIPS','COUNTYFP','COUNTY_FIPS','GEOID','GEOID10'}), None)
if fips_field is None:
    raise SystemExit('County layer: missing FIPS/GEOID field.')
counties['fips'] = counties[fips_field].astype(str).str.zfill(5)

active = active.to_crs(counties.crs)
joined = gpd.sjoin(active[['geometry']], counties[['fips','geometry']], predicate='within', how='left')
counts = joined.groupby('fips').size().reset_index(name='npdes_permits_count')
counts.to_csv(args.out, index=False)
print('NPDES layer:', layer)
print('Status field:', status_field)
print('Wrote', args.out)
