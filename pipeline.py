from .datasources import get_raster_for_roi
from .analysis import compute_anomaly_heatmap, pick_anomaly_points
from .geo import pixel_to_latlon_grid

def run_scan_pipeline(roi, settings: dict, use_real_data: bool = False):
    size = 256
    raster = get_raster_for_roi(roi, size=size, settings=settings, use_real_data=use_real_data)
    heatmap = compute_anomaly_heatmap(raster, settings=settings)
    georef = pixel_to_latlon_grid(roi, H=size, W=size)

    pts_px = pick_anomaly_points(heatmap)
    pts_ll = []
    for p in pts_px:
        lat, lon = georef["pixel_to_latlon"](p["row"], p["col"])
        depth_m = round(abs(p["z_rel"])*2.0 + 1.0, 2)
        volume_m3 = round(depth_m * (3.5 + p["score"]*20.0), 2)

        pts_ll.append({
            "lat": round(lat, 8),
            "lon": round(lon, 8),
            "score": p["score"],
            "polarity": p["polarity"],
            "z_rel": p["z_rel"],
            "depth_m": depth_m,
            "volume_m3": volume_m3,
        })

    return {
        "roi": roi,
        "roi_area_m2": roi.area_m2,
        "heatmap": heatmap,
        "raster": raster,
        "anomaly_points": pts_ll,
        "georef": georef,
    }
