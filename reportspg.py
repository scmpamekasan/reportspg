import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from io import BytesIO
from PIL import Image
import pytz

# Import library untuk mendeteksi GPS otomatis dari browser
try:
    from streamlit_js_eval import get_geolocation
    JS_EVAL_AVAILABLE = True
except ImportError:
    JS_EVAL_AVAILABLE = False

TZ_WIB = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.now(TZ_WIB)
hari_ini = waktu_sekarang.strftime("%Y-%m-%d")

FOLDER_LAPORAN = "bukti_laporan_spg"
os.makedirs(FOLDER_LAPORAN, exist_ok=True)

st.set_page_config(page_title="Report Penjualan SPG Mobile", page_icon="🛍️", layout="centered")

# Cek ketersediaan library JS Eval
if not JS_EVAL_AVAILABLE:
    st.error("Library `streamlit-js-eval` belum terinstall. Jalankan `pip install streamlit-js-eval` terlebih dahulu.")
    st.stop()

st.markdown("<h2 style='text-align: center;'>📱 Form Report Lapangan SPG</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: #64748b;'>Tanggal: {hari_ini}</p>", unsafe_allow_html=True)

# ====================================================
# PENGAMBILAN GPS OTOMATIS
# ====================================================
st.markdown("### 📍 Deteksi Lokasi Lapangan")
st.info("💡 Pastikan GPS HP Anda aktif dan berikan izin akses lokasi (*Allow*) pada browser.")

# Fungsi dari streamlit-js-eval untuk menarik koordinat real-time
loc = get_geolocation()

gps_valid = False
user_lat = 0.0
user_lon = 0.0

if loc and isinstance(loc, dict) and loc.get("coords"):
    user_lat = loc["coords"]["latitude"]
    user_lon = loc["coords"]["longitude"]
    gps_valid = True
    
    st.success(f"✅ **GPS Terdeteksi Otomatis!**\n- Latitude: `{user_lat:.6f}`\n- Longitude: `{user_lon:.6f}`")
else:
    st.warning("⏳ Menunggu sinyal GPS dari perangkat... (Pastikan izin lokasi di-browser sudah diaktifkan)")

# ====================================================
# FORM LAPORAN (Hanya aktif jika GPS berhasil didapat)
# ====================================================
SPG_TEAM = ["SPG 1: Siska", "SPG 2: Rina"]

if gps_valid:
    with st.form("form_report_spg_otomatis"):
        nama_spg = st.selectbox("Pilih Nama SPG", SPG_TEAM)
        lokasi_kegiatan = st.selectbox("Kategori Lokasi", ["Warung Kopi (Warkop)", "Kafe", "Pasar Tradisional", "Alun-alun / Keramaian Umum"])
        nama_tempat = st.text_input("Nama Tempat / Titik Spesifik (Contoh: Warkop Cak Anam - Gubeng)")
        
        col1, col2 = st.columns(2)
        with col1:
            jumlah_terjual = st.number_input("Jumlah Rokok Terjual (Bungkus)", min_value=0, step=1)
        with col2:
            pendapatan = st.number_input("Total Pendapatan Tunai (Rp)", min_value=0.0, step=5000.0)
        
        st.markdown("---")
        st.markdown("### 📸 Bukti Foto Kondisi Lapangan (Wajib Live)")
        foto_bukti = st.camera_input("Ambil Foto Lapangan Saat Ini")
        
        submit_report = st.form_submit_button("📤 Kirim Laporan Sekarang", type="primary")

        if submit_report:
            if not nama_tempat or foto_bukti is None:
                st.error("❌ Mohon isi Nama Tempat dan ambil Foto Bukti Lapangan secara langsung!")
            else:
                waktu_str = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
                
                # Simpan Foto Fisik ke Folder
                bytes_data = foto_bukti.getvalue()
                img = Image.open(BytesIO(bytes_data))
                nama_file = f"{FOLDER_LAPORAN}/{nama_spg.replace(' ', '_')}_{waktu_sekarang.strftime('%Y%m%d_%H%M%S')}.jpg"
                img.save(nama_file, "JPEG")
                
                # Simpan ke Database SQLite otomatis dengan koordinat GPS yang ditarik tadi
                conn = sqlite3.connect("spg_report.db")
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS laporan (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tanggal TEXT, nama_spg TEXT, lokasi_kegiatan TEXT, 
                        nama_tempat TEXT, jumlah_terjual INTEGER, pendapatan REAL, 
                        latitude REAL, longitude REAL, waktu_submit TEXT, path_foto TEXT
                    )
                """)
                cursor.execute("""
                    INSERT INTO laporan (tanggal, nama_spg, lokasi_kegiatan, nama_tempat, jumlah_terjual, pendapatan, latitude, longitude, waktu_submit, path_foto)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (hari_ini, nama_spg, lokasi_kegiatan, nama_tempat, jumlah_terjual, pendapatan, user_lat, user_lon, waktu_str, nama_file))
                conn.commit()
                conn.close()
                
                st.success("🎉 Laporan berhasil dikirim beserta titik koordinat GPS otomatis!")
                st.balloons()
else:
    st.error("❌ Form terkunci karena sinyal GPS belum terbaca. Harap refresh halaman atau izinkan akses lokasi pada browser HP Anda.")
