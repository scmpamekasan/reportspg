from datetime import datetime
from io import BytesIO
import math
import pandas as pd
import streamlit as st
from streamlit_geolocation import streamlit_geolocation

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Laporan SPG Mobile", page_icon="📍", layout="centered"
)

st.markdown(
    "<h2 style='text-align: center;'>📍 Portal Laporan SPG Lapangan</h2>",
    unsafe_allow_html=True,
)


# ====================================================
# 1. AMBIL DATA MASTER WARKOP/LKK DARI GITHUB
# ====================================================
@st.cache_data
def load_master_lokasi():
  # Ganti URL di bawah dengan "Raw URL" file Excel Anda di GitHub
  url_github = "https://raw.githubusercontent.com/username/repo-anda/main/master_warkop.xlsx"
  try:
    df_lokasi = pd.read_excel(url_github)
    return df_lokasi
  except Exception:
    # Data Dummy untuk cadangan/simulasi jika URL belum disesuaikan
    data_dummy = {
        "Nama_Warkop": ["Warkop Cak No", "Warkop Barokah", "LKK Bahagia"],
        "Zona": ["Surabaya Barat", "Surabaya Barat", "Surabaya Barat"],
        "Latitude": [-7.2575, -7.2600, -7.2500],
        "Longitude": [112.7521, 112.7550, 112.7400],
        "Radius_Meter": [150, 150, 150],  # Toleransi radius dalam meter
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


df_master = load_master_lokasi()

# ====================================================
# 2. DETEKSI GPS OTOMATIS (DI BACKGROUND)
# ====================================================
# Komponen berjalan otomatis meminta izin lokasi browser tanpa memunculkan teks/tombol
loc = streamlit_geolocation()

user_lat = None
user_lon = None

if loc and loc.get("latitude") and loc.get("longitude"):
  user_lat = float(loc["latitude"])
  user_lon = float(loc["longitude"])
else:
  # Fallback jika GPS belum diizinkan atau sedang proses memuat
  # Menggunakan nilai default sementara agar tidak error saat pertama render
  user_lat = -7.2575
  user_lon = 112.7521

# ====================================================
# 3. PILIH PROMOTOR & LOKASI WARKOP/LKK
# ====================================================
st.markdown("### 👤 Identifikasi Tugas")
nama_spg = st.selectbox(
    "Pilih Nama Promotor / SPG",
    ["Arif Yuliadi", "Nur Muhammad Khoirul Firmansyah"],
)
pilihan_warkop = st.selectbox(
    "Pilih Lokasi Warkop / LKK Tujuan", df_master["Nama_Warkop"].tolist()
)

# Ambil data koordinat target warkop yang dipilih dari file GitHub
data_terpilih = df_master[df_master["Nama_Warkop"] == pilihan_warkop].iloc[0]
target_lat = float(data
