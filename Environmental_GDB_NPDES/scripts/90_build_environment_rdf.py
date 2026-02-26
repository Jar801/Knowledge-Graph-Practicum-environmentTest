
#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, XSD


"""
Merge all environmental indicators and emit RDF (SOSA + PROV-O).
"""

PROC = Path('Environmental_GDB_NPDES/data/processed'); PROC.mkdir(parents=True, exist_ok=True)

ejs = pd.read_csv(PROC / 'ejscreen_county.csv', dtype={'county_fips':str}).rename(columns={'county_fips':'fips'})
imp = pd.read_csv(PROC / 'impaired_streams_by_county.csv', dtype={'fips':str})
npd = pd.read_csv(PROC / 'npdes_active_by_county.csv', dtype={'fips':str})
nrm = pd.read_csv(PROC / 'ncei_normals_by_county.csv', dtype={'fips':str})

df = ejs.merge(imp, on='fips', how='left').merge(npd, on='fips', how='left').merge(nrm, on='fips', how='left')

df['county'] = None
# Use EJScreen year as label
if 'year' in df.columns:
    df['year'] = 2024
else:
    df['year'] = 2024

cols = ['fips','county','year','pm25_mean','ozone_8hr_avg','rsei_tox_air',
        'impaired_stream_miles','npdes_permits_count','avg_temp_f','annual_precip_in']
out = df[cols]
out.to_csv(PROC / 'county_environment_2024.csv', index=False)

# RDF
BASE = Namespace('http://example.org/nc-exposome/')
SOSA = Namespace('http://www.w3.org/ns/sosa#')
PROV = Namespace('http://www.w3.org/ns/prov#')
QB = Namespace("http://purl.org/linked-data/cube#")
SCHEMA = Namespace("http://schema.org/")


g = Graph(); g.bind('ex', BASE); g.bind('sosa', SOSA); g.bind('prov', PROV); g.bind('qb', QB); g.bind('schema', SCHEMA)

IND = {
  'pm25_mean': BASE['indicator/pm25_mean'],
  'ozone_8hr_avg': BASE['indicator/ozone_8hr_avg'],
  'rsei_tox_air': BASE['indicator/rsei_tox_air'],
  'impaired_stream_miles': BASE['indicator/impaired_stream_miles'],
  'npdes_permits_count': BASE['indicator/npdes_permits_count'],
  'avg_temp_f': BASE['indicator/avg_temp_f'],
  'annual_precip_in': BASE['indicator/annual_precip_in']
}
SRC = {
  'pm25_mean': BASE['dataset/EJScreen_v23'],
  'ozone_8hr_avg': BASE['dataset/EJScreen_v23'],
  'rsei_tox_air': BASE['dataset/EJScreen_v23'],
  'impaired_stream_miles': BASE['dataset/NCDEQ_ImpairedWaters'],
  'npdes_permits_count': BASE['dataset/NCDEQ_NPDES_ActiveOnly'],
  'avg_temp_f': BASE['dataset/NOAA_NCEI_GriddedNormals_1991_2020'],
  'annual_precip_in': BASE['dataset/NOAA_NCEI_GriddedNormals_1991_2020']
}

for _, r in out.iterrows():
    county = BASE[f"county/{r['fips']}"]
    for k, ind in IND.items():
        val = r.get(k)
        if pd.notna(val):
            obs = BASE[f"obs/{k}/{r['fips']}/{int(r['year'])}"]
            g.add((obs, RDF.type, SOSA.Observation))
            g.add((obs, SOSA.hasFeatureOfInterest, county))
            g.add((obs, SOSA.observedProperty, ind))
            g.add((obs, SOSA.resultTime, Literal(f"{int(r['year'])}-12-31", datatype=XSD.date)))
            try:
                g.add((obs, SOSA.hasSimpleResult, Literal(float(val))))
            except Exception:
                pass
            g.add((obs, PROV.wasDerivedFrom, SRC[k]))

g.serialize((PROC / 'county_environment_2024.ttl').as_posix(), format='turtle')
print('Wrote', (PROC / 'county_environment_2024.ttl').as_posix())


# PATCH to make it compatible with SPARQL_EXAMPLES in 91_sparql_examples.py; add schema.org properties and QB dataset/indicator links

# ALSO add the project's QB + schema.org model so SPARQL_EXAMPLES work
g.add((obs, QB.Observation))                               # qb:Observation
g.add((obs, QB.dataSet, BASE['nc_exposome_dataset']))      # link to dataset
g.add((obs, SCHEMA.location, county))                      # schema:location county
g.add((obs, BASE['measuredIndicator'], ind))               # ex:measuredIndicator indicator

# write value both ways (schema:value is what examples query)
# 'val' is your numeric; ensure it's a float literal
g.add((obs, SCHEMA.value, Literal(float(val))))            # schema:value

# optional: unitText (recommended for impaired miles, temp, precip)
unit_map = {
  'impaired_stream_miles': 'miles',
  'avg_temp_f': 'degree Fahrenheit',
  'annual_precip_in': 'inch',
}
u = unit_map.get(k)
if u:
    g.add((obs, SCHEMA.unitText, Literal(u)))

# project time representation
year = int(r['year'])
g.add((obs, SCHEMA.temporal, Literal(str(year), datatype=XSD.gYear)))  # schema:temporal gYear