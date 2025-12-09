#!/usr/bin/env python3
"""
debug_zoom_levels.py

Check mask coverage of your NDVI COG at various zoom levels.
"""

from rio_tiler.io import COGReader
import mercantile

# Absolute path to your NDVI_2019 COG
TIF_PATH = "/Users/refayetsiam/Documents/vsCode_projects_offline/NOV-geojson-processor/PG_Assets_May4/Output/NDVI_2019.tif"

def main():
    # 1) Open the COG and read its bounds, CRS, and size
    with COGReader(TIF_PATH) as cog:
        west, south, east, north = cog.bounds
        print("COG bounds (lon/lat in EPSG:4326):")
        print(f"  west  = {west}")
        print(f"  south = {south}")
        print(f"  east  = {east}")
        print(f"  north = {north}")
        print(f"CRS: {cog.crs}")
        print(f"Size: {cog.width} × {cog.height} pixels\n")

        # 2) Compute the map center
        center_lon = (west + east) / 2
        center_lat = (south + north) / 2
        print(f"Map center: lon={center_lon}, lat={center_lat}\n")

        # 3) Loop through zoom levels and inspect mask coverage
        for z in [13, 12, 11, 10]:
            x, y, _ = mercantile.tile(center_lon, center_lat, z)
            data, mask = cog.tile(x, y, z, tilesize=256)
            print(
                f"Zoom {z:2d} → tile x={x}, y={y} → "
                f"mask sum = {int(mask.sum())}, "
                f"data min/max = {data.min():.4f}/{data.max():.4f}"
            )

if __name__ == "__main__":
    main()
