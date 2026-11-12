from datetime import datetime
from io import BytesIO
import math
import pandas as pd
import streamlit as st

# Konfigurasi Halaman
st.set_page_config(
    page_title="Laporan Kanvas SPG Mobile", page_icon="📍", layout="centered"
)

st.markdown(
    "<h2 style='text-align: center;'>📍 Portal Laporan SPG Lapangan</h2>",
    unsafe_allow_html=True,
)


# ====================================================
# 1. AMBIL DATA MASTER WARKOP/LKK DARI GITHUB (EXCEL/CSV)
# ====================================================
@st.cache_data
def load_master_lokasi():
  # Ganti URL di bawah dengan "Raw URL" file Excel atau CSV Anda di GitHub
  # Contoh URL CSV/Excel mentah di GitHub:
  url_github = "https://raw.githubusercontent.com/username/repo-anda/main/master_warkop.xlsx"
  try:
    # Jika menggunakan file Excel (.xlsx)
    df_lokasi = pd.read_excel(url_github)
    return df_lokasi
  except Exception as e:
    # Data Dummy untuk simulasi jika file belum ada
    data_dummy = {
        "Nama_Warkop": ["Warkop Cak No", "Warkop Barokah", "LKK Bahagia"],
        "Zona": ["Surabaya Barat", "Surabaya Barat", "Surabaya Barat"],
        "Latitude": [-7.2575, -7.2600, -7.2500],
        "Longitude": [112.7521, 112.7550, 112.7400],
        "Radius_Meter": [100, 100, 150],  # Toleransi jarak dalam meter
    }
    return pd.DataFrame(data_dummy)


# Hitung Jarak Menggunakan Rumus Haversine (GPS Distance)
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
# 2. PILIH PROMOTOR & LOKASI TUGAS
# ====================================================
st.markdown("### 👤 Identifikasi & Lokasi Tugas")
nama_spg = st.selectbox(
    "Pilih Nama Promotor / SPG",
    ["Arif Yuliadi", "Nur Muhammad Khoirul Firmansyah"],
)
pilihan_warkop = st.selectbox(
    "Pilih Lokasi Warkop / LKK", df_master["Nama_Warkop"].tolist()
)

# Ambil data koordinat target warkop yang dipilih
data_terpilih = df_master[df_master["Nama_Warkop"] == pilihan_warkop].iloc[0]
target_lat = float(data_terpilih["Latitude"])
target_lon = float(data_terpilih["Longitude"])
max_radius = float(data_terpilih.get("Radius_Meter", 100))

st.info(
    f"📌 Lokasi Tujuan: **{pilihan_warkop}** (Zona:"
    f" {data_terpilih.get('Zona', 'Bawean')})"
)

# ====================================================
# 3. CEK GEOLOKASI GPS PERANGKAT SPG
# ====================================================
st.markdown("---")
st.markdown("### 🛰️ Verifikasi Kehadiran via GPS")

# Menggunakan komponen Streamlit JavaScript untuk mengambil koordinat HP/Laptop SPG
lokasi_gps_js = st.components.v1.html(
    """
    <div style="font-family: sans-serif; text-align: center;">
        <button onclick="getLocation()" style="background-color:#2563eb; color:white; padding:10px 20px; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">
            📍 Klik Disini untuk Deteksi Posisi GPS Saya
        </button>
        <p id="status" style="margin-top: 10px; color: #64748b; font-size: 14px;">Menunggu izin GPS...</p>
    </div>
    <script>
    function getLocation() {
        const status = document.getElementById("status");
        if (!navigator.geolocation) {
            status.innerHTML = "GPS tidak didukung oleh browser ini.";
        } else {
            status.innerHTML = "Mencari lokasi satelit...";
            navigator.geolocation.getCurrentPosition(success, error, {enableHighAccuracy: true});
        }
    }
    function success(position) {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        status.innerHTML = "GPS Terdeteksi! Latitude: " + latitude.toFixed(5) + ", Longitude: " + longitude.toFixed(5);
        // Kirim data kembali ke Streamlit (bisa via query params atau session state jika terintegrasi komponen custom)
    }
    function error() {
        status.innerHTML = "Gagal mendeteksi lokasi. Pastikan izin GPS aktif.";
    }
    </script>
    """,
    height=90,
)

# Simulasi Input Koordinat GPS Manual / Otomatis untuk testing di Streamlit Cloud
col_gps1, col_gps2 = st.columns(2)
with col_gps1:
  user_lat = st.number_input(
      "Latitude HP SPG (Simulasi/GPS)", value=target_lat, format="%.5f"
  )
with col_gps2:
  user_lon = st.number_input(
      "Longitude HP SPG (Simulasi/GPS)", value=target_lon, format="%.5f"
  )

# Hitung jarak real-time
jarak_saat_ini = hitung_jarak_meter(user_lat, user_lon, target_lat, target_lon)

if jarak_saat_ini <= max_radius:
  st.success(
      f"✅ Anda berada di dalam area warkop! (Jarak: {round(jarak_saat_ini, 1)}"
      f" meter dari titik pusat)."
  )
  sistem_terbuka = True
else:
  st.error(
      f"❌ Anda berada di luar area warkop! Jarak Anda"
      f" {round(jarak_saat_ini, 1)} meter (Maksimal radius yang diizinkan:"
      f" {max_radius} meter). Mendekatlah ke lokasi untuk mengisi laporan."
  )
  sistem_terbuka = False

# ====================================================
# 4. FORM LAPORAN PENJUALAN (Hanya Buka Jika di Dalam Radius)
# ====================================================
if sistem_terbuka:
  st.markdown("---")
  with st.form("form_laporan_spg_lokasi"):
    st.markdown("### 📝 Form Input Laporan Penjualan")

    omset_laporan = st.number_input(
        "Omset (Bungkus)", min_value=0, step=1, value=0
    )
    jumlah_setoran_rp = st.number_input(
        "Jumlah Setoran (Rp)", min_value=0, step=500, value=0
    )
    catatan_kegiatan = st.text_area("Catatan Aktivitas / Kendala di Lapangan")

    btn_kirim_laporan = st.form_submit_button(
        "🚀 Kirim Laporan ke Server", type="primary"
    )

    if btn_kirim_laporan:
      st.balloons()
      st.success(
          f"🎉 Laporan untuk **{pilihan_warkop}** oleh **{nama_spg}** berhasil"
          " disimpan!"
      )
      # Di sini Anda bisa menyimpannya ke database SQLite / Google Sheets seperti biasa
