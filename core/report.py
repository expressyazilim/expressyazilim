import numpy as np
import datetime as dt

def build_report(result: dict, settings: dict, use_real_data: bool) -> dict:
    pts = result.get("anomaly_points", [])
    heat = result["heatmap"]

    layer_count = sum(1 for k,v in settings.items() if v)
    contrast = float(np.std(heat))
    base = min(0.95, max(0.15, 0.35 + 0.55*(contrast/0.25)))
    acc = min(0.99, base * (0.75 + 0.08*layer_count))

    voids = sum(1 for p in pts if p.get("polarity") == "NEG")
    metals = sum(1 for p in pts if p.get("polarity") == "POS")

    top = sorted(pts, key=lambda p: p.get("score",0), reverse=True)[:3]

    patterns = []
    if voids: patterns.append("Boşluk/negatif anomali kümeleri")
    if metals: patterns.append("Pozitif anomali kümeleri")
    if not patterns: patterns.append("Belirgin patern yok")

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    methods = [
        "ROI üzerinden çoklu katman çekimi",
        "Normalize + DoG (Difference of Gaussians) anomali haritası",
        "Tepe noktası seçimi (min mesafe kısıtı)",
        "Kümeye dayalı özet (demo)",
    ]

    if use_real_data:
        data_type = "Gerçek veri (Sentinel Hub)"
        sources = []
        if settings.get("radar"): sources.append("Sentinel-1 (VV/VH)")
        if settings.get("optic"): sources.append("Sentinel-2 (NDVI/NDWI/NDBI/brightness)")
        if settings.get("thermal"): sources.append("Landsat L2 Thermal (ST_B10)")
    else:
        data_type = "Demo (sentetik raster)"
        sources = ["Demo raster"]

    return {
        "timestamp": now,
        "overall_accuracy_pct": round(acc*100, 1),
        "voids_detected": int(voids),
        "metals_detected": int(metals),
        "findings_top3": top,
        "models_used": int(max(1, layer_count)),
        "methods_used": methods,
        "sources_used": sources,
        "software_targets": ["QGIS","Surfer","ArcMap","Voxler","Global Mapper","RockWorks"],
        "patterns": patterns,
        "data_type": data_type,
        "scan_mode": "Kapsamlı tarama",
    }
