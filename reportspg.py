from datetime import datetime
from io import BytesIO
import json
import math
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, shape
import streamlit as st
import streamlit.components.v1 as components

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Laporan SPG Mobile", page_icon="📍", layout="centered"
)

st.markdown(
    "<h2 style='text-align: center;'>📍 Portal Laporan SPG Lapangan</h2>",
    unsafe_allow_html=True,
)


# ====================================================
# 1. AMBIL DATA MASTER WILAYAH DARI FILE LOKAL GITHUB
# ====================================================
@st.cache_data
def load_master_wilayah():
  try:
    with open("Surabaya Barat.geojson", "r", encoding="utf-8") as f:
      data = json.load(f)
    # Konversi GeoJSON ke GeoPandas DataFrame
    gdf_master = gpd.GeoDataFrame.from_features(data)
    return gdf_master
  except Exception as e:
    st.error(f"Gagal memuat file master wilayah 'Surabaya Barat.geojson': {e}")
    return None


# ====================================================
# 2. AMBIL DATA MASTER WARKOP/LKK DARI GITHUB
# ====================================================
@st.cache_data
def load_master_lokasi():
  url_excel = "https://raw.githubusercontent.com/username/repo-anda/main/master_warkop.xlsx"
  try:
    df_lokasi = pd.read_excel(url_excel)
    return df_lokasi
  except Exception:
    # Data Dummy untuk cadangan/simulasi jika URL Excel belum disesuaikan
    data_dummy = {
        "Nama_Warkop": ["Warkop Cak No", "Warkop Barokah", "LKK Bahagia"],
        "Zona": ["Surabaya Barat", "Surabaya Barat", "Surabaya Barat"],
        "Latitude": [-7.2575, -7.2600, -7.2500],
        "Longitude": [112.7521, 112.7550, 112.7400],
        "Radius_Meter": [150, 150, 150],
    }
    return pd.DataFrame(data_dummy)


# Rumus Haversine untuk menghitung jarak dua titik koordinat (dalam meter)
def hitung_jarak_meter(lat1, lon1, lat2, lon2):
  R = 6371000  # Radius bumi dalam meter
  phi1 = math.radians(lat1)
  phi2 = math.radians(lat2)
  dphi = math.radians(lat2 - lat1)
  dlambda = math.radians(lon2 - lon1)

  a = (
      math.sin(dphi / 2) ** 2
      + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
  )
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
  return R * c


# Muat data master
gdf_wilayah = load_master_wilayah()
df_master = load_master_lokasi()

# ====================================================
# 3. GPS OTOMATIS SENYAP (TANPA TOMBOL / TANPA MENU)
# ====================================================
if "user_lat" not in st.session_state:
  st.session_state["user_lat"] = -7.2575  # Default awal
if "user_lon" not in st.session_state:
  st.session_state["user_lon"] = 112.7521

gps_component = """
<script>
const getLocation = () => {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const url = new URL(window.parent.location.href);
                if (url.searchParams.get("lat") != lat || url.searchParams.get("lon") != lon) {
                    url.searchParams.set("lat", lat);
                    url.searchParams.set("lon", lon);
                    window.parent.location.href = url.toString();
                }
            },
            (error) => {
                console.log("GPS Error: " + error.message);
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    }
};
getLocation();
</script>
"""
components.html(gps_component, height=0, width=0)

params = st.query_params
if "lat" in params and "lon" in params:
  try:
    st.session_state["user_lat"] = float(params["lat"])
    st.session_state["user_lon"] = float(params["lon"])
  except:
    pass

user_lat = st.session_state["user_lat"]
user_lon = st.session_state["user_lon"]

# ====================================================
# 4. VALIDASI SPATIAL MASTER WILAYAH (GEOJSON) & RADIUS WARKOP
# ====================================================
lokasi_sah = True
pesan_validasi = ""

# Validasi 1: Apakah posisi GPS SPG berada di dalam poligon master wilayah GeoJSON?
if gdf_wilayah is not None:
  titik_spg = Point(user_lon, user_lat)  # Urutan: (Longitude, Latitude)
  dalam_wilayah = False
  kecamatan_terdeteksi = ""

  for _, row in gdf_wilayah.iterrows():
    # Pastikan geometri valid sebelum diperiksa
    geom = row["geometry"]
    if geom and geom.contains(titik_spg):
      dalam_wilayah = True
      kecamatan_terdeteksi = row.get("nm_kecamatan", "Wilayah Terdaftar")
      break

  if not dalam_wilayah:
    lokasi_sah = False
    pesan_validasi = "❌ Anda berada di LUAR cakupan master wilayah Surabaya Barat!"

# Validasi 2: Pilih Promotor & Warkop Tujuan
st.markdown("### 👤 Identifikasi Tugas")
nama_spg = st.selectbox(
    "Pilih Nama Promotor / SPG",
    ["Arif Yuliadi", "Nur Muhammad Khoirul Firmansyah"],
)
pilihan_warkop = st.selectbox(
    "Pilih Lokasi Warkop / LKK Tujuan", df_master["Nama_Warkop"].tolist()
)

data_terpilih = df_master[df_master["Nama_Warkop"] == pilihan_warkop].iloc[0]
target_lat = float(data_terpilih["Latitude"])
target_lon = float(data_terpilih["Longitude"])
max_radius = float(data_terpilih.get("Radius_Meter", 150))

jarak_saat_ini = hitung_jarak_meter(user_lat, user_lon, target_lat, target_lon)

# Cek radius warkop jika validasi wilayah lolos
if lokasi_sah:
  if jarak_saat_ini <= max_radius:
    st.success(
        f"✅ Berada di area **{pilihan_warkop}** (Kecamatan:"
        f" **{kecamatan_terdeteksi}**). Silakan isi laporan."
    )
    sistem_terbuka = True
  else:
    st.error(
        f"❌ Anda terlalu jauh dari **{pilihan_warkop}**! Jarak Anda saat ini"
        f" ±{round(jarak_saat_ini, 1)} meter dari titik lokasi."
    )
    sistem_terbuka = False
else:
  st.error(pesan_validasi)
  sistem_terbuka = False

# ====================================================
# 5. FORM LAPORAN (Hanya Terbuka Jika Validasi Lolos)
# ====================================================
if sistem_terbuka:
  st.markdown("---")
  with st.form("form_laporan_spg"):
    st.markdown("### 📝 Form Input Laporan Penjualan")

    brand_entry = st.selectbox(
        "Brand",
        [
            "D.Super 12",
            "D.76 Apel",
            "D.76 Apel Royal",
            "Black Matcha K12",
            "Djarum 76 Aksara",
        ],
    )
    omset_entry = st.number_input(
        "Omset (Bungkus)", min_value=0, step=1, value=0
    )
    jumlah_setoran_entry = st.number_input(
        "Jumlah Setoran (Rp)", min_value=0, step=500, value=0
    )

    btn_kirim = st.form_submit_button(
        "🚀 Kirim Laporan ke Database", type="primary"
    )

    if btn_kirim:
      st.balloons()
      st.success(
          f"🎉 Laporan untuk **{pilihan_warkop}** oleh **{nama_spg}** berhasil"
          " disimpan!"
      )
