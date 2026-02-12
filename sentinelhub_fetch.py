from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
import numpy as np

def _get_secrets():
    try:
        import streamlit as st
        return st.secrets.get("SH_CLIENT_ID", None), st.secrets.get("SH_CLIENT_SECRET", None)
    except Exception:
        return None, None

def have_credentials() -> bool:
    cid, csec = _get_secrets()
    return bool(cid and csec)

def _make_shconfig():
    from sentinelhub import SHConfig
    cid, csec = _get_secrets()
    if not cid or not csec:
        raise RuntimeError("Sentinel Hub secrets yok (SH_CLIENT_ID/SH_CLIENT_SECRET).")
    cfg = SHConfig()
    cfg.sh_client_id = cid
    cfg.sh_client_secret = csec
    return cfg

def _request(collection, evalscript: str, bbox_lonlat: Tuple[float,float,float,float], size: Tuple[int,int], time_interval: Tuple[str,str]):
    from sentinelhub import SentinelHubRequest, BBox, CRS, MimeType
    cfg = _make_shconfig()
    min_lon, min_lat, max_lon, max_lat = bbox_lonlat
    bbox = BBox(bbox=[min_lon, min_lat, max_lon, max_lat], crs=CRS.WGS84)

    req = SentinelHubRequest(
        data_folder=None,
        evalscript=evalscript,
        input_data=[SentinelHubRequest.input_data(data_collection=collection, time_interval=time_interval)],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=cfg,
    )
    return req.get_data()[0].astype(np.float32)  # HxWxC

def fetch_s1_vv_vh(bbox_lonlat, size=(256,256), time_interval=("2024-01-01","2026-12-31")) -> np.ndarray:
    from sentinelhub import DataCollection
    evalscript = """//VERSION=3
function setup() {
  return {input: [{bands: ["VV", "VH"], units: "LINEAR"}], output: {bands: 2, sampleType: "FLOAT32"}};
}
function evaluatePixel(s) { return [s.VV, s.VH]; }
"""
    return _request(DataCollection.SENTINEL1_IW, evalscript, bbox_lonlat, size, time_interval)

def fetch_s2_indices(bbox_lonlat, size=(256,256), time_interval=("2024-01-01","2026-12-31")) -> np.ndarray:
    from sentinelhub import DataCollection
    evalscript = """//VERSION=3
function setup() {
  return {
    input: [{bands: ["B02","B03","B04","B08","B11","SCL"], units: "REFLECTANCE"}],
    output: {bands: 4, sampleType: "FLOAT32"}
  };
}
function evaluatePixel(s) {
  var scl = s.SCL;
  var invalid = (scl==3 || scl==8 || scl==9 || scl==10 || scl==11);
  if (invalid) { return [0,0,0,0]; }
  var ndvi = (s.B08 - s.B04) / (s.B08 + s.B04 + 1e-6);
  var ndwi = (s.B03 - s.B08) / (s.B03 + s.B08 + 1e-6);
  var ndbi = (s.B11 - s.B08) / (s.B11 + s.B08 + 1e-6);
  var bright = (s.B02 + s.B03 + s.B04) / 3.0;
  return [ndvi, ndwi, ndbi, bright];
}
"""
    return _request(DataCollection.SENTINEL2_L2A, evalscript, bbox_lonlat, size, time_interval)

def fetch_landsat_thermal(bbox_lonlat, size=(256,256), time_interval=("2024-01-01","2026-12-31")) -> np.ndarray:
    from sentinelhub import DataCollection
    evalscript = """//VERSION=3
function setup() {
  return {input: [{bands: ["ST_B10"], units: "DN"}], output: {bands: 1, sampleType: "FLOAT32"}};
}
function evaluatePixel(s) { return [s.ST_B10]; }
"""
    try:
        return _request(DataCollection.LANDSAT_OT_L2, evalscript, bbox_lonlat, size, time_interval)
    except Exception:
        return np.zeros((size[1], size[0], 1), dtype=np.float32)
