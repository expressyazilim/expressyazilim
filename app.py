import os
import time
import streamlit as st
import folium
from streamlit_folium import st_folium

import numpy as np
import plotly.graph_objects as go

from core.roi import roi_from_drawn_feature
from core.pipeline import run_scan_pipeline
from core.exporters import export_all
from core.report import build_report
from core.sentinelhub_fetch import have_credentials

st.set_page_config(page_title="AnomaliLab Pro", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 0.6rem; padding-bottom: 2rem;}
.al-title {font-size: 1.25rem; font-weight: 700;}
.al-status {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            background:#0b1220; border:1px solid #243b55; padding:6px 10px; border-radius:10px;}
.al-card {background:#0b1220; border:1px solid #243b55; border-radius:16px; padding:12px; margin-bottom:12px;}
.al-btn button {width: 100%; border-radius: 12px; height: 44px;}
.small-note {opacity:0.8; font-size:0.9rem;}
.metric {font-size: 2.1rem; font-weight: 800;}
.metric-sub {opacity:0.85;}
.finding {background:#0b1220; border:1px solid #243b55; border-radius:14px; padding:12px;}
.finding .pct {font-size:1.4rem; font-weight:800;}
.finding .ttl {font-weight:700; margin-top:4px;}
.badge {display:inline-block; padding:4px 10px; border-radius:999px; border:1px solid #243b55; background:#0b1220; font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

st.session_state.setdefault("status", "Hazır")
st.session_state.setdefault("last_result", None)
st.session_state.setdefault("last_settings", None)
st.session_state.setdefault("last_report", None)
st.session_state.setdefault("exports_dir", os.path.join(os.getcwd(), "exports"))
st.session_state.setdefault("map_center", None)
st.session_state.setdefault("map_zoom", None)

os.makedirs(st.session_state.exports_dir, exist_ok=True)

c1, c2 = st.columns([0.75, 0.25])
with c1:
    st.markdown('<div class="al-title">🛰️ AnomaliLab Pro — ROI seç • Tarama yap • Raporla • Export et</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="al-status">Durum: {st.session_state.status}</div>', unsafe_allow_html=True)

tab_map, tab_report = st.tabs(["🗺️ Harita & Tarama", "📄 Analiz Raporu"])

with tab_map:
    col_map, col_panel = st.columns([0.68, 0.32], gap="large")

    with col_panel:
        st.markdown('<div class="al-card">', unsafe_allow_html=True)
        st.markdown("#### ⚙️ Tarama Ayarları")

        use_real = st.toggle("🌍 Gerçek veri kullan (Sentinel Hub)", value=False)
        if use_real and not have_credentials():
            st.warning("Sentinel Hub secrets bulunamadı. `.streamlit/secrets.toml` ekleyin. Şimdilik DEMO çalışır.")

        a_radar = st.checkbox("📡 Radar (Sentinel-1)", value=True)
        a_optic = st.checkbox("🛰️ Optik (Sentinel-2 indeks)", value=True)
        a_thermal = st.checkbox("🔥 Termal (Landsat L2)", value=False)

        st.divider()
        st.markdown("#### 📍 Konum")
        lat = st.number_input("Enlem (lat)", value=39.000000, format="%.6f")
        lon = st.number_input("Boylam (lon)", value=35.000000, format="%.6f")
        zoom_preset = st.selectbox("Hızlı zoom", ["Yakın", "Orta", "Uzak"], index=0)

        st.markdown('<div class="small-note">ROI çizimi: Haritada sol üstte çizim aracıyla dikdörtgen/çokgen/daire seç.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="al-card al-btn">', unsafe_allow_html=True)
        start_scan = st.button("🔎 Taramayı Başlat", type="primary")
        export_btn = st.button("⬇️ Sonuçları Export Et", type="secondary")
        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.last_result is not None:
            st.markdown('<div class="al-card">', unsafe_allow_html=True)
            st.markdown("#### 📌 Anomali Listesi (Anomaliye Git)")
            pts = st.session_state.last_result["anomaly_points"]
            if not pts:
                st.write("Anomali yok.")
            else:
                for i, p in enumerate(pts[:25], start=1):
                    a, b = st.columns([0.72, 0.28])
                    with a:
                        st.write(f"#{i} **{p['polarity']}** | score={p['score']} | depth={p['depth_m']}m | vol={p['volume_m3']}m³")
                        st.caption(f"{p['lat']}, {p['lon']}")
                    with b:
                        if st.button("📍 Git", key=f"goto_{i}"):
                            st.session_state.map_center = (p["lat"], p["lon"])
                            st.session_state.map_zoom = 19
                            st.toast("Harita anomaliye odaklandı.", icon="📍")
            st.markdown("</div>", unsafe_allow_html=True)

    with col_map:
        zoom = {"Yakın": 17, "Orta": 14, "Uzak": 11}[zoom_preset]
        center = st.session_state.map_center or (lat, lon)
        zoom_use = st.session_state.map_zoom or zoom

        m = folium.Map(location=[center[0], center[1]], zoom_start=zoom_use, control_scale=True)
        folium.TileLayer("OpenStreetMap", name="OSM", control=True).add_to(m)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="ESRI Satellite",
            control=True,
            overlay=False,
        ).add_to(m)

        if st.session_state.last_result is not None:
            r = st.session_state.last_result
            roi = r["roi"]
            pts = r["anomaly_points"]

            coords = [(y, x) for x, y in list(roi.polygon.exterior.coords)]
            folium.Polygon(coords, color="#7c3aed", weight=2, fill=True, fill_opacity=0.08).add_to(m)

            for p in pts:
                color = "#ef4444" if p["polarity"] == "POS" else "#22c55e"
                folium.CircleMarker(
                    location=[p["lat"], p["lon"]],
                    radius=8,
                    color=color,
                    fill=True,
                    fill_opacity=0.85,
                    popup=f"score={p['score']} | depth={p['depth_m']}m | vol={p['volume_m3']}m³ | {p['polarity']}",
                ).add_to(m)

        from folium.plugins import Draw
        Draw(
            export=False,
            position="topleft",
            draw_options={"polyline": False, "marker": False, "circlemarker": False, "polygon": True, "rectangle": True, "circle": True},
            edit_options={"edit": True, "remove": True},
        ).add_to(m)

        folium.LayerControl(collapsed=True).add_to(m)
        out = st_folium(m, height=640, width=None, returned_objects=["last_active_drawing", "all_drawings"])

    roi = None
    try:
        feat = out.get("last_active_drawing") or None
        if feat:
            roi = roi_from_drawn_feature(feat)
    except Exception:
        roi = None

    if start_scan:
        st.session_state.status = "Tarama çalışıyor..."
        prog = st.progress(0, text="Hazırlanıyor...")
        for i in range(10):
            time.sleep(0.06)
            prog.progress((i+1)*6, text="Veri hazırlanıyor...")

        if roi is None:
            st.warning("ROI seçilmedi. Haritada bir alan çiz.")
            st.session_state.status = "Hazır"
        else:
            prog.progress(70, text="Analiz çalışıyor...")
            settings = dict(radar=a_radar, optic=a_optic, thermal=a_thermal, magnetic=False)
            result = run_scan_pipeline(roi, settings=settings, use_real_data=use_real)

            st.session_state.last_result = result
            st.session_state.last_settings = settings
            st.session_state.last_report = build_report(result, settings, use_real_data=use_real)

            prog.progress(100, text="Bitti ✅")
            st.session_state.status = "Tarama tamamlandı"
            st.success(f"Tarama tamamlandı. Anomali sayısı: {len(result['anomaly_points'])}")
            st.info("📄 Rapor sekmesine geçip kartları ve 3D modeli görebilirsin.")

    if export_btn:
        if st.session_state.last_result is None:
            st.warning("Önce tarama yap.")
        else:
            st.session_state.status = "Export ediliyor..."
            exported = export_all(st.session_state.last_result, exports_dir=st.session_state.exports_dir)
            st.session_state.status = "Export hazır"
            st.success("Export tamamlandı. Dosyalar 'exports/' klasörüne kaydedildi.")
            for label, path in exported.items():
                with open(path, "rb") as f:
                    st.download_button(f"İndir: {os.path.basename(path)}", f, file_name=os.path.basename(path), mime="application/octet-stream")

with tab_report:
    if st.session_state.last_result is None or st.session_state.last_report is None:
        st.info("Önce Harita & Tarama sekmesinden tarama çalıştır.")
    else:
        rep = st.session_state.last_report
        res = st.session_state.last_result
        settings = st.session_state.last_settings or {}

        st.markdown("#### ✅ Kapsamlı Analiz Sonucu")
        cA, cB, cC = st.columns(3)
        with cA:
            st.markdown(f'<div class="al-card"><div class="metric">{rep["overall_accuracy_pct"]}%</div><div class="metric-sub">Genel güven seviyesi</div></div>', unsafe_allow_html=True)
        with cB:
            st.markdown(f'<div class="al-card"><div class="metric">{rep["metals_detected"]}</div><div class="metric-sub">Pozitif (POS)</div></div>', unsafe_allow_html=True)
        with cC:
            st.markdown(f'<div class="al-card"><div class="metric">{rep["voids_detected"]}</div><div class="metric-sub">Negatif (NEG)</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="al-card">', unsafe_allow_html=True)
        st.markdown("#### 🧊 3D Görselleştirme (Heatmap Surface)")
        heat = res["heatmap"]
        X = np.linspace(0, 1, heat.shape[1])
        Y = np.linspace(0, 1, heat.shape[0])
        fig = go.Figure(data=[go.Surface(z=heat, x=X, y=Y)])
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=420)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("#### 📍 Bulgu Kartları (Top 3)")
        top = rep["findings_top3"]
        cols = st.columns(3)
        for i in range(3):
            with cols[i]:
                if i < len(top):
                    p = top[i]
                    pct = round(float(p["score"])*100, 1)
                    title = "Pozitif Anomali" if p["polarity"] == "POS" else "Negatif/Boşluk Anomali"
                    st.markdown(f"""
<div class="finding">
  <div class="pct">{pct}%</div>
  <div class="ttl">{title} #{i+1}</div>
  <div class="small-note">Zaman: {rep["timestamp"]}</div>
  <div style="margin-top:8px">
    <b>Koordinat:</b> {p["lat"]}, {p["lon"]}<br/>
    <b>Derinlik:</b> {p["depth_m"]} m<br/>
    <b>Hacim:</b> {p["volume_m3"]} m³<br/>
    <b>z_rel:</b> {p["z_rel"]}<br/>
    <span class="badge">{p["polarity"]}</span>
  </div>
</div>
""", unsafe_allow_html=True)
                else:
                    st.markdown('<div class="finding">Bulgu yok</div>', unsafe_allow_html=True)

        st.markdown('<div class="al-card">', unsafe_allow_html=True)
        st.markdown("#### 🧾 Teknik Bilgiler (Hepsi)")
        st.write({
            "Tarih/Saat": rep["timestamp"],
            "Tarama modu": rep["scan_mode"],
            "Veri tipi": rep["data_type"],
            "Kaynaklar": rep["sources_used"],
            "Kullanılan katmanlar": [k for k,v in settings.items() if v],
            "Kullanılan modeller": rep["models_used"],
            "Yöntemler": rep["methods_used"],
            "Anomali paternleri": rep["patterns"],
            "Uyumlu yazılımlar": rep["software_targets"],
        })
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="al-card">', unsafe_allow_html=True)
        st.markdown("#### 📌 Not")
        st.write("Derinlik/hacim şu an **model tabanlı gösterim**. Gerçek kalibrasyon için saha ölçümü/jeofizik referans gerekir.")
        st.markdown("</div>", unsafe_allow_html=True)
