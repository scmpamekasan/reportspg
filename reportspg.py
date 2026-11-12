from datetime import datetime
import json
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import streamlit as st
from streamlit_js_eval import get_geolocation

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
# 2. AMBIL KOORDINAT GPS OTOMATIS SAAT WEB DIBUKA
# ====================================================
loc = get_geolocation()

if loc is None:
  st.warning(
      "⏳ Sedang mengunci titik GPS lokasi Anda... Pastikan izin lokasi"
      " (**Allow / Izinkan**) aktif pada browser Anda."
  )
  st.stop()

# Ekstrak koordinat asli dari perangkat SPG
user_lat = float(loc["coords"]["latitude"])
user_lon = float(loc["coords"]["longitude"])
akurasi_meter = round(float(loc["coords"].get("accuracy", 0)), 1)

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
    f"- **Koordinat:** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}` (Akurasi: ±{akurasi_meter}m)\n"
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
      " Silakan isi laporan konsumen."
  )

  st.markdown("---")
  with st.form("form_laporan_spg"):
    st.markdown("### 📝 Form Input Laporan Konsumen")

    st.write(f"**Warkop/LKK:** {nama_warkop_manual}")

    # Field Form Sesuai Permintaan
    brand_entry = st.selectbox(
        "Brand Rokok",
        [
            "D.Super 12",
            "D.76 Apel",
            "D.76 Apel Royal",
            "Black Matcha K12",
            "Djarum 76 Aksara",
        ],
    )
    
    nama_konsumen = st.text_input("Nama Konsumen", placeholder="Masukkan nama konsumen")
    
    gender_entry = st.radio("Gender", ["L", "P"], horizontal=True)
    
    usia_entry = st.number_input("Usia", min_value=17, max_value=100, step=1, value=25)
    
    nohp_entry = st.text_input("No HP", placeholder="Contoh: 081234567890")
    
    # Instagram dengan awalan '@' otomatis di entiannya
    instagram_input = st.text_input("Instagram", placeholder="username_ig")
    instagram_entry = f"@{instagram_input.strip().lstrip('@')}" if instagram_input.strip() else ""
    
    jumlah_bungkus = st.number_input("Jumlah Bungkus", min_value=1, step=1, value=1)
    
    rokok_asal_bumo = st.text_input("Rokok Asal (BUMO)", placeholder="Merk rokok yang biasa dikonsumsi sebelumnya")

    btn_kirim = st.form_submit_button(
        "🚀 Kirim Laporan ke Database", type="primary"
    )

    if btn_kirim:
      if not nama_warkop_manual.strip():
        st.warning("Mohon isi nama Warkop/LKK terlebih dahulu.")
      elif not nama_konsumen.strip():
        st.warning("Mohon isi nama konsumen.")
      else:
        st.balloons()
        st.success(
            f"🎉 Laporan konsumen **{nama_konsumen}** di **{nama_warkop_manual}** "
            f"(Kecamatan {kecamatan_pilihan}) oleh **{nama_spg}** berhasil disimpan!\n\n"
            f"**Instagram tercatat:** {instagram_entry}"
        )
else:
  if not lokasi_sah and gdf_wilayah is not None:
    st.error(pesan_validasi)
  elif nama_warkop_manual.strip() == "":
    st.info("ℹ️ Silakan masukkan nama Warkop/LKK terlebih dahulu.")
