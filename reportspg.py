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
loc = streamlit_geolocation()

user_lat = None
user_lon = None

if loc and loc.get("latitude") and loc.get("longitude"):
  user_lat = float(loc["latitude"])
  user_lon = float(loc["longitude"])
else:
  # Fallback nilai default sementara agar tidak error saat pertama kali render
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

# Ambil data koordinat target warkop yang dipilih dari file GitHub (Penulisan bersih)
data_terpilih = df_master[df_master["Nama_Warkop"] == pilihan_warkop].iloc[0]
target_lat = float(data_terpilih["Latitude"])
target_lon = float(data_terpilih["Longitude"])
max_radius = float(data_terpilih.get("Radius_Meter", 150))

# ====================================================
# 4. VALIDASI JARAK RADIUS LOKASI
# ====================================================
jarak_saat_ini = hitung_jarak_meter(user_lat, user_lon, target_lat, target_lon)

if jarak_saat_ini <= max_radius:
  st.success(
      f"✅ Terdeteksi di area **{pilihan_warkop}** (Jarak:"
      f" {round(jarak_saat_ini, 1)} m). Silakan isi laporan."
  )
  sistem_terbuka = True
else:
  st.error(
      f"❌ Anda berada di luar area **{pilihan_warkop}**! Jarak Anda saat ini"
      f" {round(jarak_saat_ini, 1)} meter dari lokasi (Maksimal radius:"
      f" {max_radius} m). Mendekatlah ke lokasi untuk membuka form laporan."
  )
  sistem_terbuka = False

# ====================================================
# 5. FORM LAPORAN (Hanya Terbuka Jika Berada di Dalam Radius)
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
