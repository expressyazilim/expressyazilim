import numpy as np
from scipy.ndimage import gaussian_filter

def compute_anomaly_heatmap(raster: np.ndarray, settings: dict) -> np.ndarray:
    """Return 0..1 anomaly heatmap (demo)."""
    w = 1.0
    if settings.get("radar"): w += 0.6
    if settings.get("optic"): w += 0.4
    if settings.get("thermal"): w += 0.8
    if settings.get("magnetic"): w += 0.5

    sm1 = gaussian_filter(raster, sigma=1.2)
    sm2 = gaussian_filter(raster, sigma=6.0)
    dog = (sm1 - sm2) * w
    dog = (dog - dog.min()) / (dog.max() - dog.min() + 1e-6)
    return dog.astype(np.float32)

def pick_anomaly_points(heatmap: np.ndarray, top_k: int = 35, min_dist_px: int = 10):
    H, W = heatmap.shape
    hm = heatmap.copy()
    points = []
    for _ in range(top_k):
        idx = int(np.argmax(hm))
        r = idx // W
        c = idx % W
        score = float(heatmap[r, c])
        if score <= 0:
            break
        polarity = "POS" if score >= 0.5 else "NEG"
        z_rel = float((score - 0.5) * 4.0)  # demo relative depth indicator
        points.append({"row": int(r), "col": int(c), "score": round(score, 5), "polarity": polarity, "z_rel": round(z_rel, 3)})
        r0, r1 = max(0, r-min_dist_px), min(H, r+min_dist_px)
        c0, c1 = max(0, c-min_dist_px), min(W, c+min_dist_px)
        hm[r0:r1, c0:c1] = -1
    return points
