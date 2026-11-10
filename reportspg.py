import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, time, timedelta
from io import BytesIO
from PIL import Image
import math
import pytz

# Proteksi impor untuk streamlit-js-eval
try:
    from streamlit_js_eval import get_geolocation, streamlit_js_eval
    JS_EVAL_AVAILABLE = True
except ImportError:
    JS_EVAL_AVAILABLE = False

# Definisi Zona Waktu Asia/Jakarta (WIB)
TZ_WIB = pytz.timezone('Asia/Jakarta')

# Folder Penyimpanan Bukti Foto Laporan
FOLDER_LAPORAN = "bukti_laporan_spg"
os.makedirs(FOLDER_LAPORAN, exist_ok=True)

# ====================================================
# FUNGSI PEMBERSIHAN OTOMATIS FOTO LEWAT 1 HARI
# ====================================================
def bersihkan_foto_lama(hari_ini_str):
    """Menghapus file foto di folder jika tanggalnya bukan hari ini"""
    if os.path.exists(FOLDER_LAPORAN):
        format_hari_ini = hari_ini_str.replace("-", "") # Format YYYYMMDD
        for filename in os.listdir(FOLDER_LAPORAN):
            if "_" in filename:
                parts = filename.split("_")
                if len(parts) >= 2:
                    tanggal_file = parts[1][:8]
                    if tanggal_file != format_hari_ini:
                        try:
                            os.remove(os.path.join(FOLDER_LAPORAN, filename))
                        except Exception:
                            pass

waktu_sekarang_wib = datetime.now(TZ_WIB)
hari_ini = waktu_sekarang_wib.strftime("%Y-%m-%d")
bersihkan_foto_lama(hari_ini)

# ====================================================
# 1. KONFIGURASI HALAMAN & STYLING CSS
# ====================================================
st.set_page_config(
    page_title="Report SPG - Djarum Black Matcha",
    page_icon="🚬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    h1, h2, h3 {
        color: #0f172a;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
        width: 100%;
    }
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    </style>
""", unsafe_allow_html=True)

# ====================================================
# 2. KONFIGURASI KANTOR & PILIHAN PRODUK
# ====================================================
KANTOR_LATITUDE = -6.983120          
KANTOR_LONGITUDE = 112.489525
RADIUS_MAKSIMAL_METER = 150
BATAS_JAM_MASUK = time(8, 0, 0)

SPG_TEAM = ["SPG 1: Siska", "SPG 2: Rina"]

# Merek Rokok Khusus Djarum Black Matcha
MEREK_ROKOK = [
    "Djarum Black Matcha Siro",
    "Djarum Black Matcha Kuro",
    "Djarum Black Matcha Kretek"
]

DB_NAME = "spg_report.db"

# ====================================================
# 3. SISTEM DATABASE (SQLITE)
# ====================================================
def inisialisasi_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS laporan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            nama_spg TEXT,
            merek_rokok TEXT,
            lokasi_kegiatan TEXT,
            nama_tempat TEXT,
            jumlah_terjual INTEGER,
            pendapatan REAL,
            latitude REAL,
            longitude REAL,
            waktu_submit TEXT,
            path_foto TEXT,
            device_info TEXT
        )
    """)
    
    # Cek migrasi kolom merek_rokok & device_info jika DB sudah ada sebelumnya
    cursor.execute("PRAGMA table_info(laporan)")
    kolom = [kol[1] for kol in cursor.fetchall()]
    if "merek_rokok" not in kolom:
        cursor.execute("ALTER TABLE laporan ADD COLUMN merek_rokok TEXT")
    if "device_info" not in kolom:
        cursor.execute("ALTER TABLE laporan ADD COLUMN device_info TEXT")
    conn.commit()
    conn.close()

inisialisasi_database()

def muat_data_laporan():
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query("""
            SELECT id AS ID, tanggal AS Tanggal, nama_spg AS [Nama SPG], 
                   merek_rokok AS [Merek Rokok], lokasi_kegiatan AS [Kategori Tempat],
                   nama_tempat AS [Nama Tempat], jumlah_terjual AS [Terjual (Bungkus)], 
                   pendapatan AS [Pendapatan (Rp)], waktu_submit AS [Waktu Submit],
                   latitude AS Latitude, longitude AS Longitude,
                   device_info AS [Perangkat], path_foto AS [Path Foto]
            FROM laporan
            ORDER BY waktu_submit DESC
        """, conn)
    except Exception:
        df = pd.DataFrame(columns=[
            "ID", "Tanggal", "Nama SPG", "Merek Rokok", "Kategori Tempat",
            "Nama Tempat", "Terjual (Bungkus)", "Pendapatan (Rp)", "Waktu Submit",
            "Latitude", "Longitude", "Perangkat", "Path Foto"
        ])
    conn.close()
    return df

def simpan_laporan(tanggal, nama_spg, merek_rokok, lokasi_kegiatan, nama_tempat, jumlah_terjual, pendapatan, lat, lon, waktu_str, path_foto, device_info):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO laporan 
        (tanggal, nama_spg, merek_rokok, lokasi_kegiatan, nama_tempat, jumlah_terjual, pendapatan, latitude, longitude, waktu_submit, path_foto, device_info)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (tanggal, nama_spg, merek_rokok, lokasi_kegiatan, nama_tempat, jumlah_terjual, pendapatan, lat, lon, waktu_str, path_foto, device_info))
    conn.commit()
    conn.close()

# ====================================================
# 4. FUNGSI BANTU
# ====================================================
def hitung_jarak_meter(lat1, lon1, lat2, lon2):
    R = 6371000  
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def parsing_device_info(ua_string):
    if not ua_string: return "Unknown Device"
    ua_lower = ua_string.lower()
    os_name, browser_name = "Desktop / PC", "Browser Lain"

    if "iphone" in ua_lower: os_name = "iOS (iPhone)"
    elif "ipad" in ua_lower: os_name = "iOS (iPad)"
    elif "android" in ua_lower: os_name = "Android"
    elif "windows" in ua_lower: os_name = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower: os_name = "MacOS"
    elif "linux" in ua_lower: os_name = "Linux"

    if "edg" in ua_lower: browser_name = "Edge"
    elif "chrome" in ua_lower and "chromium" not in ua_lower: browser_name = "Chrome"
    elif "safari" in ua_lower and "chrome" not in ua_lower: browser_name = "Safari"
    elif "firefox" in ua_lower: browser_name = "Firefox"
    elif "whatsapp" in ua_lower: browser_name = "WhatsApp In-App Browser"

    return f"{os_name} - {browser_name}"

# ====================================================
# 5. TAMPILAN UTAMA (FORM SPG)
# ====================================================
st.markdown("<h2 style='text-align: center; margin-bottom: 5px;'>📱 Report Penjualan SPG Mobile</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 25px;'>Tim SPG Djarum Black Matcha - Surabaya</p>", unsafe_allow_html=True)

if 'notifikasi_sukses' in st.session_state:
    st.balloons()
    st.success(st.session_state.pop('notifikasi_sukses'))

if not JS_EVAL_AVAILABLE:
    st.error("Library `streamlit-js-eval` belum terinstall di requirements.txt!")
    st.stop()

user_agent_header = ""
try:
    if hasattr(st, "context") and hasattr(st.context, "headers"):
        user_agent_header = st.context.headers.get("User-Agent", "")
except Exception:
    pass

# Cek Pembatasan 1 HP 1x Laporan/Absen per Hari via localStorage
key_ls = f"sudah_absen_perangkat_{hari_ini}"
device_sudah_absen = streamlit_js_eval(js_expressions=f"localStorage.getItem('{key_ls}')", key=f"check_ls_{hari_ini}")

if device_sudah_absen == "true":
    st.error(f"❌ **Akses Ditolak!** Perangkat ini sudah digunakan untuk kirim laporan hari ini ({hari_ini}). Setiap perangkat diizinkan 1 kali pelaporan per hari.")
else:
    st.markdown("### 📍 Deteksi Lokasi GPS Lapangan")
    st.info("💡 Pastikan GPS HP aktif dan izinkan akses lokasi (*Allow*) di browser.")

    loc = get_geolocation()

    if not loc or not isinstance(loc, dict) or not loc.get("coords"):
        st.warning("⏳ Menunggu sinyal koordinat GPS dari HP Anda...")
    else:
        user_lat = loc["coords"]["latitude"]
        user_lon = loc["coords"]["longitude"]
        jarak = hitung_jarak_meter(user_lat, user_lon, KANTOR_LATITUDE, KANTOR_LONGITUDE)
        dalam_radius = jarak <= RADIUS_MAKSIMAL_METER

        m1, m2 = st.columns(2)
        with m1:
            st.metric(label="📍 Jarak dari Titik Kantor", value=f"{jarak:.1f} m")
        with m2:
            st.metric(label="🎯 Batas Maksimal", value=f"{RADIUS_MAKSIMAL_METER} m")

        if dalam_radius:
            st.success("✅ **Lokasi Valid!** Anda berada di dalam radius area operasional.")
            st.markdown("---")
            st.markdown("### 📝 Form Input Penjualan SPG")
            
            with st.form(key="form_report_spg"):
                nama_spg = st.selectbox("Pilih Nama SPG", SPG_TEAM)
                
                # Pilihan Merek Rokok Khusus
                merek_rokok = st.selectbox("Pilih Merek Rokok Djarum", MEREK_ROKOK)
                
                lokasi_kegiatan = st.selectbox("Kategori Tempat", ["Warung Kopi (Warkop)", "Kafe", "Pasar Tradisional", "Alun-alun / Tempat Keramaian"])
                nama_tempat = st.text_input("Nama Tempat / Titik Lokasi (Contoh: Warkop Cak Anam - Gubeng)")
                
                c1, c2 = st.columns(2)
                with c1:
                    jumlah_terjual = st.number_input("Jumlah Terjual (Bungkus)", min_value=1, value=1, step=1)
                with c2:
                    pendapatan = st.number_input("Total Pendapatan Tunai (Rp)", min_value=0.0, value=25000.0, step=5000.0)
                
                st.markdown("---")
                st.markdown("### 📸 Bukti Foto Kondisi Lapangan (Wajib Live)")
                picture = st.camera_input("Ambil Foto Lapak / Kondisi Penjualan Saat Ini")
                
                submit_button = st.form_submit_button("🚀 Kirim Laporan Penjualan", type="primary")
                
                if submit_button:
                    if not nama_tempat:
                        st.error("❌ Nama tempat/lokasi wajib diisi!")
                    elif picture is None:
                        st.error("❌ Anda wajib memotret bukti lapangan secara langsung!")
                    else:
                        waktu_sekarang = datetime.now(TZ_WIB)
                        waktu_str = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
                        info_perangkat = parsing_device_info(user_agent_header)

                        bytes_data = picture.getvalue()
                        img = Image.open(BytesIO(bytes_data))
                        
                        nama_file_foto = f"{FOLDER_LAPORAN}/{nama_spg.replace(' ', '_')}_{waktu_sekarang.strftime('%Y%m%d_%H%M%S')}.jpg"
                        img.save(nama_file_foto, "JPEG")

                        # Simpan Laporan ke Database
                        simpan_laporan(
                            hari_ini, nama_spg, merek_rokok, lokasi_kegiatan, 
                            nama_tempat, jumlah_terjual, pendapatan, user_lat, user_lon, 
                            waktu_str, nama_file_foto, info_perangkat
                        )

                        # Kunci LocalStorage Browser
                        streamlit_js_eval(js_expressions=f"localStorage.setItem('{key_ls}', 'true')", key=f"set_ls_{hari_ini}")

                        st.session_state['notifikasi_sukses'] = f"🎉 **Laporan Berhasil Terkirim!**\nTerima kasih **{nama_spg}**, laporan produk **{merek_rokok}** di {nama_tempat} telah tersimpan."
                        st.rerun()
        else:
            st.error(f"❌ **Lokasi Ditolak!** Jarak Anda ({jarak:.1f} m) berada di luar batas operasional ({RADIUS_MAKSIMAL_METER} m). Mohon mendekat ke lokasi kantor/titik yang ditentukan.")

# ====================================================
# 6. PANEL ADMIN (LOG REPORT, EXPORT & HAPUS DATA)
#
