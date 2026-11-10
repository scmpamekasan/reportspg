import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import pytz

# Import library untuk mendeteksi GPS otomatis dari browser
try:
    from streamlit_js_eval import get_geolocation, streamlit_js_eval
    JS_EVAL_AVAILABLE = True
except ImportError:
    JS_EVAL_AVAILABLE = False

TZ_WIB = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.now(TZ_WIB)
hari_ini = waktu_sekarang.strftime("%Y-%m-%d")

FOLDER_LAPORAN = "bukti_laporan_spg"
os.makedirs(FOLDER_LAPORAN, exist_ok=True)

# ====================================================
# FUNGSI PEMBERSIHAN OTOMATIS FOTO LEWAT 1 HARI
# ====================================================
def bersihkan_foto_lama(hari_ini_str):
    if os.path.exists(FOLDER_LAPORAN):
        format_hari_ini = hari_ini_str.replace("-", "")
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

bersihkan_foto_lama(hari_ini)

st.set_page_config(
    page_title="Report Penjualan SPG Mobile", 
    page_icon="🛍️", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Cek ketersediaan library JS Eval
if not JS_EVAL_AVAILABLE:
    st.error("Library `streamlit-js-eval` belum terinstall. Jalankan `pip install streamlit-js-eval` terlebih dahulu.")
    st.stop()

st.markdown("<h2 style='text-align: center;'>📱 Form Report Lapangan SPG</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align: center; color: #64748b;'>Tim SPG Djarum Black Matcha - Surabaya | Tanggal: {hari_ini}</p>", unsafe_allow_html=True)

if 'notifikasi_sukses' in st.session_state:
    st.balloons()
    st.success(st.session_state.pop('notifikasi_sukses'))

# ====================================================
# INISIALISASI DATABASE & STRUKTUR TABEL
# ====================================================
DB_NAME = "spg_report.db"

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
            path_foto TEXT
        )
    """)
    # Migrasi kolom merek_rokok jika belum ada pada database lama
    cursor.execute("PRAGMA table_info(laporan)")
    kolom = [kol[1] for kol in cursor.fetchall()]
    if "merek_rokok" not in kolom:
        cursor.execute("ALTER TABLE laporan ADD COLUMN merek_rokok TEXT")
    conn.commit()
    conn.close()

inisialisasi_database()

def muat_data_laporan():
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query("""
            SELECT id AS ID, tanggal AS Tanggal, nama_spg AS [Nama SPG], 
                   merek_rokok AS [Merek Rokok], lokasi_kegiatan AS [Kategori Lokasi],
                   nama_tempat AS [Nama Tempat], jumlah_terjual AS [Terjual (Bungkus)], 
                   pendapatan AS [Pendapatan (Rp)], waktu_submit AS [Waktu Submit],
                   latitude AS Latitude, longitude AS Longitude, path_foto AS [Path Foto]
            FROM laporan
            ORDER BY waktu_submit DESC
        """, conn)
    except Exception:
        df = pd.DataFrame(columns=[
            "ID", "Tanggal", "Nama SPG", "Merek Rokok", "Kategori Lokasi",
            "Nama Tempat", "Terjual (Bungkus)", "Pendapatan (Rp)", "Waktu Submit",
            "Latitude", "Longitude", "Path Foto"
        ])
    conn.close()
    return df

# ====================================================
# PENGAMBILAN GPS OTOMATIS
# ====================================================
st.markdown("### 📍 Deteksi Lokasi Lapangan")
st.info("💡 Pastikan GPS HP Anda aktif dan berikan izin akses lokasi (*Allow*) pada browser.")

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
MEREK_ROKOK_OPTIONS = [
    "Djarum Black Matcha Siro",
    "Djarum Black Matcha Kuro",
    "Djarum Black Matcha Kretek"
]

if gps_valid:
    with st.form("form_report_spg_otomatis"):
        nama_spg = st.selectbox("Pilih Nama SPG", SPG_TEAM)
        merek_rokok = st.selectbox("Pilih Merek Rokok", MEREK_ROKOK_OPTIONS)
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
                waktu_sekarang = datetime.now(TZ_WIB)
                waktu_str = waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S")
                
                # Simpan Foto Fisik ke Folder
                bytes_data = foto_bukti.getvalue()
                img = Image.open(BytesIO(bytes_data))
                nama_file = f"{FOLDER_LAPORAN}/{nama_spg.replace(' ', '_')}_{waktu_sekarang.strftime('%Y%m%d_%H%M%S')}.jpg"
                img.save(nama_file, "JPEG")
                
                # Simpan ke Database SQLite
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO laporan (tanggal, nama_spg, merek_rokok, lokasi_kegiatan, nama_tempat, jumlah_terjual, pendapatan, latitude, longitude, waktu_submit, path_foto)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (hari_ini, nama_spg, merek_rokok, lokasi_kegiatan, nama_tempat, jumlah_terjual, pendapatan, user_lat, user_lon, waktu_str, nama_file))
                conn.commit()
                conn.close()
                
                st.session_state['notifikasi_sukses'] = f"🎉 Laporan penjualan **{merek_rokok}** berhasil dikirim beserta titik koordinat GPS!"
                st.rerun()
else:
    st.error("❌ Form terkunci karena sinyal GPS belum terbaca. Harap refresh halaman atau izinkan akses lokasi pada browser HP Anda.")

# ====================================================
# PANEL ADMIN (LOG REPORT, GOOGLE MAPS, GALERI & MANAJEMEN)
# ====================================================
st.markdown("---")
st.markdown("### 📊 Panel Admin & Log Report Penjualan")

df_laporan = muat_data_laporan()

if not df_laporan.empty:
    df_tampil = df_laporan.drop(columns=['Path Foto']).copy()
    df_tampil['Google Maps'] = df_tampil.apply(lambda row: f"https://www.google.com/maps?q={row['Latitude']},{row['Longitude']}", axis=1)
    
    st.dataframe(df_tampil, use_column_width=True)
    
    # --- GALERI FOTO LOKASI LAPANGAN ---
    st.markdown("---")
    st.markdown(f"### 🖼️ Galeri Foto Lapangan Hari Ini ({hari_ini})")
    
    df_hari_ini = df_laporan[df_laporan['Tanggal'] == hari_ini]
    
    if not df_hari_ini.empty:
        cols = st.columns(3)
        for index, row in df_hari_ini.reset_index(drop=True).iterrows():
            col_target = cols[index % 3]
            with col_target:
                st.markdown(f"**{row['Nama SPG']}**")
                st.caption(f"🚬 {row['Merek Rokok']}\n\n📍 {row['Nama Tempat']}\n\n🕒 {row['Waktu Submit']}\n\n🌐 Lat/Lon: `{row['Latitude']:.4f}, {row['Longitude']:.4f}`")
                
                gmaps_link = f"https://www.google.com/maps?q={row['Latitude']},{row['Longitude']}"
                st.markdown(f"🔗 [Buka di Google Maps]({gmaps_link})", unsafe_allow_html=True)
                
                path_foto = row['Path Foto']
                if path_foto and os.path.exists(path_foto):
                    st.image(path_foto, use_column_width=True)
                else:
                    st.info("Foto tidak tersedia")
                st.markdown("---")
    else:
        st.info("📭 Belum ada foto laporan penjualan untuk hari ini.")

    # ====================================================
    # MENU UNDUH & HAPUS DATA (HARIAN, MINGGUAN, SEMUA)
    # ====================================================
    st.markdown("---")
    st.markdown("### 🛠️ Fitur Manajemen Data (Unduh & Hapus)")
    
    col_u, col_h = st.columns(2)
    
    # --- MENU UNDUH DATA ---
    with col_u:
        st.markdown("#### 📥 Unduh Laporan Excel")
        opsi_unduh = st.selectbox("Pilih Rentang Data Unduh:", ["Hari Ini", "7 Hari Terakhir (Mingguan)", "Semua Data"])
        
        if opsi_unduh == "Hari Ini":
            df_unduh = df_laporan[df_laporan['Tanggal'] == hari_ini]
        elif opsi_unduh == "7 Hari Terakhir (Mingguan)":
            tgl_7_hari = (waktu_sekarang - timedelta(days=7)).strftime("%Y-%m-%d")
            df_unduh = df_laporan[df_laporan['Tanggal'] >= tgl_7_hari]
        else:
            df_unduh = df_laporan.copy()
            
        data_excel = BytesIO()
        with pd.ExcelWriter(data_excel, engine='openpyxl') as writer:
            df_unduh.to_excel(writer, index=False, sheet_name='Report SPG')
        
        waktu_unduh_str = waktu_sekarang.strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label=f"💾 Download Excel ({opsi_unduh})",
            data=data_excel.getvalue(),
            file_name=f"report_spg_{opsi_unduh.lower().replace(' ', '_')}_{waktu_unduh_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # --- MENU HAPUS DATA ---
    with col_h:
        st.markdown("#### 🗑️ Hapus Log Data")
        opsi_hapus = st.selectbox("Pilih Rentang Data Hapus:", ["Hari Ini", "7 Hari Terakhir (Mingguan)", "Semua Data"], key="sb_hapus")
        
        if st.button(f"🔥 Hapus Data ({opsi_hapus})", type="secondary", use_container_width=True):
            st.session_state['konfirmasi_hapus'] = True
            st.session_state['target_hapus'] = opsi_hapus

    if st.session_state.get('konfirmasi_hapus', False):
        st.write("")
        st.warning(f"⚠️ **PERINGATAN:** Tindakan ini akan menghapus log data & foto untuk **{st.session_state['target_hapus']}** secara permanen.")
        
        input_pass = st.text_input
