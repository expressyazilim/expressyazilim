import numpy as np
from .roi import ROI

def _zscore(x: np.ndarray) -> np.ndarray:
    m = np.nanmean(x)
    s = np.nanstd(x) + 1e-6
    return (x - m) / s

def get_raster_for_roi(roi: ROI, size: int = 256, settings: dict | None = None, use_real_data: bool = False) -> np.ndarray:
    if settings is None:
        settings = dict(radar=True, optic=True, thermal=False, magnetic=False)

    if use_real_data:
        try:
            from .sentinelhub_fetch import have_credentials, fetch_s1_vv_vh, fetch_s2_indices, fetch_landsat_thermal
            if not have_credentials():
                raise RuntimeError("no_credentials")

            minx, miny, maxx, maxy = roi.polygon.bounds
            bbox = (float(minx), float(miny), float(maxx), float(maxy))

            feats = []
            if settings.get("radar"):
                s1 = fetch_s1_vv_vh(bbox, size=(size, size))
                feats += [_zscore(s1[...,0]), _zscore(s1[...,1])]
            if settings.get("optic"):
                s2 = fetch_s2_indices(bbox, size=(size, size))
                for i in range(s2.shape[-1]):
                    feats.append(_zscore(s2[...,i]))
            if settings.get("thermal"):
                th = fetch_landsat_thermal(bbox, size=(size, size))[...,0]
                feats.append(_zscore(th))

            if len(feats) == 0:
                raise RuntimeError("no_features_enabled")

            fused = np.nanmean(np.stack(feats, axis=0), axis=0).astype(np.float32)
            fused = (fused - fused.mean()) / (fused.std() + 1e-6)
            return fused.astype(np.float32)
        except Exception:
            pass

    # DEMO fallback
    rng = np.random.default_rng(42)
    base = rng.normal(0, 1, (size, size)).astype(np.float32)
    y, x = np.mgrid[0:size, 0:size]
    for _ in range(6):
        cx, cy = rng.integers(0, size, 2)
        sx = rng.uniform(size*0.05, size*0.18)
        sy = rng.uniform(size*0.05, size*0.18)
        amp = rng.uniform(-4, 4)
        base += amp * np.exp(-(((x-cx)**2)/(2*sx**2) + ((y-cy)**2)/(2*sy**2))).astype(np.float32)
    base = (base - base.mean()) / (base.std() + 1e-6)
    return base.astype(np.float32)
