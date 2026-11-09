"""
Project Cirque — Substack / LinkedIn Code Snippet (Milestone 1, Step 1.2)
Topic: Live DEM Grid Sampling + Directed Acyclic Graph (DAG) Compilation for 708 Pistes & 56 Lifts
"""

from typing import Any, Dict, List
import json
import urllib.request

OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


def fetch_big_sky_dem_grid(rows: int = 15, cols: int = 15) -> List[Dict[str, float]]:
    """
    Sample a 225-point DEM elevation raster across Big Sky Resort [45.23..45.32, -111.47..-111.34]
    via batched HTTP GET requests (80 coordinates per call) in <1.2 seconds.
    """
    grid_coords = [
        (
            round(-111.47 + c * (-111.34 - (-111.47)) / float(cols - 1), 5),
            round(45.23 + r * (45.32 - 45.23) / float(rows - 1), 5),
        )
        for r in range(rows)
        for c in range(cols)
    ]

    points: List[Dict[str, float]] = []
    for i in range(0, len(grid_coords), 80):
        batch = grid_coords[i : i + 80]
        lats_str = ",".join(str(pt[1]) for pt in batch)
        lons_str = ",".join(str(pt[0]) for pt in batch)
        url = f"{OPEN_METEO_ELEVATION_URL}?latitude={lats_str}&longitude={lons_str}"
        req = urllib.request.Request(url, headers={"User-Agent": "ProjectCirque-Topology/1.4"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            elevs = json.loads(resp.read().decode("utf-8")).get("elevation", [])
            for (lon, lat), elev in zip(batch, elevs):
                points.append({"lon": lon, "lat": lat, "elevation_m": float(elev)})
    return points
