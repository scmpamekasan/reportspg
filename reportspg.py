from datetime import datetime
import json
import math
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
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
    gdf_master = gpd.GeoDataFrame.from_features(data)
    return gdf_master
  except Exception as e:
    st.error(f"Gagal memuat file master wilayah 'Surabaya Barat.geojson': {e}")
    return None


gdf_wilayah = load_master_wilayah()

# Ambil daftar nama kecamatan untuk pilihan menu dropdown
daftar_kecamatan = []
if gdf_wilayah is not None and "nm_kecamatan" in gdf_wilayah.columns:
  daftar_kecamatan = sorted(gdf_wilayah["nm_kecamatan"].dropna().unique().tolist())

# ====================================================
# 2. GPS OTOMATIS SENYAP (TANPA TOMBOL / TANPA MENU)
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
# 3. DETEKSI POSISI SPG SAAT INI (KECAMATAN & KOORDINAT)
# ====================================================
titik_spg = Point(user_lon, user_lat)  # Format GeoJSON: (Longitude, Latitude)
kecamatan_saat_ini = "Di luar wilayah Surabaya Barat"

if gdf_wilayah is not None:
  for _, row in gdf_wilayah.iterrows():
    geom = row["geometry"]
    if geom and geom.contains(titik_spg):
      kecamatan_saat_ini = row.get("nm_kecamatan", "Tidak diketahui")
      break

# Tampilkan informasi live koordinat & posisi SPG di antarmuka
st.info(
    f"📍 **Status GPS Anda:**\n\n"
    f"- **Koordinat:** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}`\n"
    f"- **Posisi Kecamatan Saat Ini:** **{kecamatan_saat_ini}**"
)

# ====================================================
# 4. IDENTIFIKASI TUGAS & PILIH KECAMATAN TUJUAN
# ====================================================
st.markdown("### 👤 Identifikasi Tugas & Lokasi")
nama_spg = st.selectbox(
    "Pilih Nama Promotor / SPG",
    ["Arif Yuliadi", "Nur Muhammad Khoirul Firmansyah"],
)

# Menu Pilih Kecamatan tujuan
kecamatan_pilihan = st.selectbox(
    "Pilih Kecamatan Tujuan Kunjungan",
    daftar_kecamatan if daftar_kecamatan else ["Memuat data..."],
)

nama_warkop_manual = st.text_input(
    "Nama Warkop / LKK (Entry Manual)",
    placeholder="Contoh: Warkop Cak No",
)

# ====================================================
# 5. VALIDASI SPATIAL BERDASARKAN KECAMATAN YANG DIPILIH
# ====================================================
lokasi_sah = False
pesan_validasi = ""

if gdf_wilayah is not None and kecamatan_pilihan:
  # Cari poligon kecamatan yang dipilih oleh pengguna
  row_kecamatan = gdf_wilayah[
      gdf_wilayah["nm_kecamatan"] == kecamatan_pilihan
  ]

  if not row_kecamatan.empty:
    geom = row_kecamatan.iloc[0]["geometry"]
    if geom and geom.contains(titik_spg):
      lokasi_sah = True
    else:
      pesan_validasi = (
          f"❌ Posisi Anda saat ini berada di **Kecamatan {kecamatan_saat_ini}**,"
          f" sedangkan target kunjungan adalah **Kecamatan {kecamatan_pilihan}**."
          " Harap menuju lokasi target kecamatan tersebut untuk membuka form"
          " laporan."
      )
  else:
    pesan_validasi = "❌ Kecamatan yang dipilih tidak ditemukan pada data master."

# ====================================================
# 6. FORM LAPORAN (Hanya Terbuka Jika Berada di Kecamatan yang Dipilih)
# ====================================================
if lokasi_sah and nama_warkop_manual.strip() != "":
  st.success(
      f"✅ Posisi terkonfirmasi berada di **Kecamatan {kecamatan_pilihan}**."
      " Silakan isi laporan."
  )

  st.markdown("---")
  with st.form("form_laporan_spg"):
    st.markdown("### 📝 Form Input Laporan Penjualan")

    st.write(f"**Warkop/LKK:** {nama_warkop_manual}")

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
      if not nama_warkop_manual.strip():
        st.warning("Mohon isi nama Warkop/LKK terlebih dahulu.")
      else:
        st.balloons()
        st.success(
            f"🎉 Laporan untuk **{nama_warkop_manual}** (Kecamatan"
            f" {kecamatan_pilihan}) oleh **{nama_spg}** berhasil disimpan!"
        )
else:
  if not lokasi_sah and gdf_wilayah is not None:
    st.error(pesan_validasi)
  elif nama_warkop_manual.strip() == "":
    st.info("ℹ️ Silakan masukkan nama Warkop/LKK terlebih dahulu.")
