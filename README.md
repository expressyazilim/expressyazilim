# AnomaliLab Pro v3 (Gerçek Veri + Rapor + Anomaliye Git)

Bu sürüm:
- ✅ ROI seçimi (polygon/rectangle/circle)
- ✅ Haritada anomali marker'ları
- ✅ **Anomaliye Git** butonu (listeden seç → harita o noktaya zoomlar)
- ✅ Rapor sekmesi: kartlar + 3D surface + teknik bilgiler (tarih/saat dahil)
- ✅ Export: GeoTIFF, ESRI ASCII, Surfer GRD, KML, DXF, GeoJSON, CSV/XYZ
- ✅ **Gerçek veri modu (Sentinel Hub)**: Sentinel-1 + Sentinel-2 + Thermal (Landsat L2)

> Not: Sentinel Hub kimlik bilgileri girilmezse otomatik DEMO raster ile çalışır.

---

## Kurulum
```bash
pip install -r requirements.txt
```

## Çalıştırma
```bash
streamlit run app.py
```

---

## Gerçek Veri (Sentinel Hub) Kurulumu

### 1) Sentinel Hub OAuth
Sentinel Hub hesabı → OAuth Client oluştur → `client_id` / `client_secret`.

### 2) Secrets ekle
**.streamlit/secrets.toml**
```toml
SH_CLIENT_ID="BURAYA"
SH_CLIENT_SECRET="BURAYA"
```

### 3) Uygulamada aç
Sağ panelde: **“Gerçek veri kullan (Sentinel Hub)”** toggle’ını aç.

---

## Hangi veriler çekiliyor?
- **Sentinel-1 (SAR):** VV & VH (SENTINEL1_IW)
- **Sentinel-2 (Optik):** NDVI/NDWI/NDBI + parlaklık (SENTINEL2_L2A)
- **Thermal:** Landsat L2 ST_B10 (LANDSAT_OT_L2) (uygun sahne varsa)

Bu katmanlar normalize edilip tek bir “anomali raster” üretilir.
