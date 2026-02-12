def pixel_to_latlon_grid(roi, H: int, W: int):
    """Simple bbox georef over ROI bounds (EPSG:4326)."""
    minx, miny, maxx, maxy = roi.polygon.bounds  # x=lon, y=lat
    def pixel_to_latlon(r, c):
        lat = maxy - (r/(H-1))*(maxy-miny)
        lon = minx + (c/(W-1))*(maxx-minx)
        return float(lat), float(lon)

    return {
        "bbox": (miny, minx, maxy, maxx),
        "H": H, "W": W,
        "pixel_to_latlon": pixel_to_latlon,
        "lon_min": float(minx), "lon_max": float(maxx),
        "lat_min": float(miny), "lat_max": float(maxy),
    }
