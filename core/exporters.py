import os
import json
import numpy as np
import rasterio
from rasterio.transform import from_bounds
import simplekml
import ezdxf

def _ensure_dir(d): os.makedirs(d, exist_ok=True)

def export_geotiff(heatmap: np.ndarray, georef: dict, out_path: str):
    H, W = heatmap.shape
    transform = from_bounds(georef["lon_min"], georef["lat_min"], georef["lon_max"], georef["lat_max"], W, H)
    profile = {
        "driver": "GTiff",
        "height": H, "width": W,
        "count": 1,
        "dtype": rasterio.float32,
        "crs": "EPSG:4326",
        "transform": transform,
        "compress": "LZW",
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(heatmap.astype(np.float32), 1)
    return out_path

def export_esri_ascii_grid(heatmap: np.ndarray, georef: dict, out_path: str):
    H, W = heatmap.shape
    cellsize_x = (georef["lon_max"] - georef["lon_min"]) / (W-1)
    cellsize_y = (georef["lat_max"] - georef["lat_min"]) / (H-1)
    cellsize = float((cellsize_x + cellsize_y) / 2.0)
    data = np.flipud(heatmap)  # origin lower-left

    header = [
        f"ncols         {W}",
        f"nrows         {H}",
        f"xllcorner     {georef['lon_min']}",
        f"yllcorner     {georef['lat_min']}",
        f"cellsize      {cellsize}",
        f"NODATA_value  -9999",
    ]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(header) + "\n")
        for r in range(H):
            f.write(" ".join(f"{v:.6f}" for v in data[r]) + "\n")
    return out_path

def export_surfer_dsaa_grid(heatmap: np.ndarray, georef: dict, out_path: str):
    H, W = heatmap.shape
    zmin, zmax = float(np.min(heatmap)), float(np.max(heatmap))
    xlo, xhi = georef["lon_min"], georef["lon_max"]
    ylo, yhi = georef["lat_min"], georef["lat_max"]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("DSAA\n")
        f.write(f"{W} {H}\n")
        f.write(f"{xlo} {xhi}\n")
        f.write(f"{ylo} {yhi}\n")
        f.write(f"{zmin} {zmax}\n")
        data = np.flipud(heatmap)
        for r in range(H):
            for c0 in range(0, W, 10):
                chunk = data[r, c0:c0+10]
                f.write(" ".join(f"{v:.6f}" for v in chunk) + "\n")
    return out_path

def export_xyz_csv(points: list, out_path: str):
    import csv
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["x_lon", "y_lat", "z_score", "polarity", "z_rel", "depth_m", "volume_m3"])
        for p in points:
            w.writerow([p["lon"], p["lat"], p["score"], p["polarity"], p["z_rel"], p.get("depth_m",""), p.get("volume_m3","")])
    return out_path

def export_kml(roi, points: list, out_path: str):
    kml = simplekml.Kml()
    pol = kml.newpolygon(name="ROI")
    pol.outerboundaryis = [(x,y) for x,y in list(roi.polygon.exterior.coords)]
    pol.style.polystyle.color = simplekml.Color.changealphaint(60, simplekml.Color.blue)

    for i, p in enumerate(points, 1):
        pt = kml.newpoint(name=f"A{i} {p['polarity']}", coords=[(p["lon"], p["lat"])])
        pt.description = f"score={p['score']}\nz_rel={p['z_rel']}"
        pt.style.iconstyle.color = simplekml.Color.red if p["polarity"] == "POS" else simplekml.Color.green
    kml.save(out_path)
    return out_path

def export_geojson(roi, points: list, out_path: str):
    feat_roi = {
        "type": "Feature",
        "properties": {"name": "ROI"},
        "geometry": {"type": "Polygon","coordinates": [[ [x,y] for x,y in list(roi.polygon.exterior.coords) ]]},
    }
    feat_pts = []
    for i,p in enumerate(points,1):
        feat_pts.append({
            "type":"Feature",
            "properties":{"name": f"A{i}","polarity": p["polarity"],"score": p["score"],"z_rel": p["z_rel"]},
            "geometry":{"type":"Point","coordinates":[p["lon"], p["lat"]]},
        })
    fc = {"type":"FeatureCollection","features":[feat_roi]+feat_pts}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
    return out_path

def export_dxf(roi, points: list, out_path: str):
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    coords = list(roi.polygon.exterior.coords)
    msp.add_lwpolyline([(x,y) for x,y in coords], close=True, dxfattribs={"layer":"ROI"})
    for p in points:
        msp.add_point((p["lon"], p["lat"]), dxfattribs={"layer": f"ANOM_{p['polarity']}"})
    doc.saveas(out_path)
    return out_path

def export_all(result: dict, exports_dir: str):
    _ensure_dir(exports_dir)
    heatmap = result["heatmap"]
    georef = result["georef"]
    roi = result["roi"]
    points = result["anomaly_points"]

    out = {}
    out["GeoTIFF"] = export_geotiff(heatmap, georef, os.path.join(exports_dir, "heatmap.tif"))
    out["ESRI_ASCII"] = export_esri_ascii_grid(heatmap, georef, os.path.join(exports_dir, "heatmap.asc"))
    out["Surfer_GRD"] = export_surfer_dsaa_grid(heatmap, georef, os.path.join(exports_dir, "heatmap.grd"))
    out["XYZ_CSV"] = export_xyz_csv(points, os.path.join(exports_dir, "anomalies_xyz.csv"))
    out["KML"] = export_kml(roi, points, os.path.join(exports_dir, "roi_and_anomalies.kml"))
    out["GeoJSON"] = export_geojson(roi, points, os.path.join(exports_dir, "roi_and_anomalies.geojson"))
    out["DXF"] = export_dxf(roi, points, os.path.join(exports_dir, "roi_and_anomalies.dxf"))
    return out
