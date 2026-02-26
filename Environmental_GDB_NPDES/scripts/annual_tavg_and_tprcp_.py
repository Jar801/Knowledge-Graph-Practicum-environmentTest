# Get signed (time-limited) HTTPS links to the 1991–2020 annual COGs
# for annual temperature (tavg/temperature) and annual precipitation (prcp/precip)
# from the Planetary Computer collection: noaa-climate-normals-gridded.

import planetary_computer
from pystac_client import Client

# Hints to match asset key/title in the COG collection
TEMP_HINTS = ["tavg", "tas", "temp", "temperature"]
PRCP_HINTS = ["prcp", "ppt", "precip", "precipitation"]

def first_signed_asset(items, hints):
    """Return the first signed asset href whose key/title contains any hint."""
    hints = [h.lower() for h in hints]
    for it in items:
        # Optional: screen items by custom fields if present on Item properties
        #   e.g., 'noaa_climate_normals:period' == '1991-2020'
        #         'noaa_climate_normals:frequency' == 'annual'
        props = it.properties or {}
        if props.get("noaa_climate_normals:period") != "1991-2020":
            continue
        if props.get("noaa_climate_normals:frequency") != "annual":
            continue

        for key, asset in it.assets.items():
            title = (asset.title or key or "").lower()
            # Prefer COGs (GeoTIFF)
            if asset.media_type and "geotiff" not in asset.media_type.lower():
                continue
            if any(h in title or h in key.lower() for h in hints):
                return asset.href  # already signed by the client modifier
    return None

# 1) Open the Planetary Computer STAC API with auto-signing enabled.
#    This makes every asset.href we read a signed, time-limited HTTPS URL.
catalog = Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,  # auto-signing hook
)

# 2) Search the COG collection (Cloud-Optimized GeoTIFFs)
#    Collection id is documented on the dataset page: "noaa-climate-normals-gridded"
search = catalog.search(collections=["noaa-climate-normals-gridded"])

items = list(search.get_items())
print(f"Found {len(items)} items in 'noaa-climate-normals-gridded'.")

# 3) Pick annual 1991–2020 temperature & precipitation assets and print their signed URLs.
temp_href = first_signed_asset(items, TEMP_HINTS)
prcp_href = first_signed_asset(items, PRCP_HINTS)

print("Annual temperature (COG):", temp_href)
print("Annual precipitation (COG):", prcp_href)

# Helpful fallback: if either is None, dump one candidate item’s assets so you can see available keys/titles.
if temp_href is None or prcp_href is None:
    print("\nNo direct match found with current hints.")
    print("Showing asset keys/titles from one annual 1991–2020 item for inspection:\n")
    for it in items:
        props = it.properties or {}
        if props.get("noaa_climate_normals:period") == "1991-2020" and props.get("noaa_climate_normals:frequency") == "annual":
            print(f"ITEM id: {it.id}")
            for key, asset in it.assets.items():
                print(f"  - asset key: {key:25s} | title: {asset.title} | media_type: {asset.media_type}")
            break