from dataclasses import dataclass
from typing import Tuple
from shapely.geometry import Polygon
import math

@dataclass
class ROI:
    kind: str  # polygon | circle
    polygon: Polygon  # lon/lat coords
    center: Tuple[float, float]  # (lat, lon)
    area_m2: float

def _approx_meters_per_deg(lat: float):
    lat_rad = math.radians(lat)
    m_per_deg_lat = 111132.92 - 559.82 * math.cos(2*lat_rad) + 1.175 * math.cos(4*lat_rad)
    m_per_deg_lon = 111412.84 * math.cos(lat_rad) - 93.5 * math.cos(3*lat_rad)
    return m_per_deg_lat, m_per_deg_lon

def _polygon_area_m2(poly: Polygon) -> float:
    cy, cx = poly.centroid.y, poly.centroid.x
    mlat, mlon = _approx_meters_per_deg(cy)
    coords = [((x-cx)*mlon, (y-cy)*mlat) for x, y in poly.exterior.coords]
    area = 0.0
    for i in range(len(coords)-1):
        x1, y1 = coords[i]
        x2, y2 = coords[i+1]
        area += x1*y2 - x2*y1
    return abs(area) * 0.5

def roi_from_drawn_feature(feature: dict) -> ROI:
    geom = feature.get("geometry", {})
    props = feature.get("properties", {}) or {}
    gtype = geom.get("type")

    if gtype == "Polygon":
        coords = geom["coordinates"][0]  # [[lon,lat],...]
        poly = Polygon([(c[0], c[1]) for c in coords])
        cy, cx = poly.centroid.y, poly.centroid.x
        area = _polygon_area_m2(poly)
        return ROI(kind="polygon", polygon=poly, center=(cy, cx), area_m2=area)

    if gtype == "Point" and props.get("radius") is not None:
        lon, lat = geom["coordinates"]
        radius_m = float(props["radius"])
        mlat, mlon = _approx_meters_per_deg(lat)
        r_lat = radius_m / mlat
        r_lon = radius_m / mlon
        pts = []
        for i in range(72):
            a = math.radians(i*5)
            pts.append((lon + r_lon*math.cos(a), lat + r_lat*math.sin(a)))
        poly = Polygon(pts)
        area = math.pi * (radius_m**2)
        return ROI(kind="circle", polygon=poly, center=(lat, lon), area_m2=area)

    raise ValueError("Desteklenmeyen ROI tipi (Polygon veya Circle olmalı).")
