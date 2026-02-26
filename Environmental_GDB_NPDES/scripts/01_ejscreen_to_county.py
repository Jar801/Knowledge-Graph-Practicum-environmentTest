
#!/usr/bin/env python3
import argparse
import pandas as pd
from pathlib import Path

"""
EJScreen (national, block-group) → filter to NC → aggregate to county.
Extract raw indicators only: PM25, OZONE, RSEI_AIR.
"""

p = argparse.ArgumentParser()
p.add_argument('--ejscreen', required=True)
p.add_argument('--out', default='Environmental_GDB_NPDES/data/processed/ejscreen_county.csv')
args = p.parse_args()

Path('Environmental_GDB_NPDES/data/processed').mkdir(parents=True, exist_ok=True)

df = pd.read_csv(args.ejscreen, dtype=str)

# Find a BG id column
bg_id_col = None
for c in df.columns:
    if c.strip().lower() in {'bg_fips','id','geoid','blockgroup','block_group_geoid','blockgroupgeoid'}:
        bg_id_col = c
        break
if bg_id_col is None:
    raise SystemExit('EJScreen: could not find a block-group FIPS/ID column.')

# Filter to NC
if 'STATEFP' in df.columns:
    df['STATEFP'] = df['STATEFP'].astype(str).str.zfill(2)
    df = df[df['STATEFP']=='37'].copy()
else:
    df = df[df[bg_id_col].str[:2]=='37'].copy()

# Select raw indicator columns
candidates = {
    'PM25':['PM25','pm25','PM2_5'],
    'OZONE':['OZONE','ozone'],
    'RSEI_AIR':['RSEI_AIR','rsei_air','RSEI']
}
sel = {}
for k, opts in candidates.items():
    for o in opts:
        if o in df.columns:
            sel[k] = o
            break
if len(sel) < 3:
    missing = set(candidates.keys()) - set(sel.keys())
    raise SystemExit(f'EJScreen: missing columns {missing}; please verify field names.')

# County FIPS
df['county_fips'] = df[bg_id_col].str[:5]
# numeric coercion
for k, col in sel.items():
    df[col] = pd.to_numeric(df[col], errors='coerce')

out = (df.groupby('county_fips')[[sel['PM25'], sel['OZONE'], sel['RSEI_AIR']]]
         .mean()
         .rename(columns={sel['PM25']:'pm25_mean', sel['OZONE']:'ozone_8hr_avg', sel['RSEI_AIR']:'rsei_tox_air'})
         .reset_index())
out['year'] = 2024
out.to_csv(args.out, index=False)
print('Wrote', args.out)
