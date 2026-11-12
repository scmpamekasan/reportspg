from datetime import datetime
from io import BytesIO
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

# ====================================================
# INISIALISASI SESSION STATE UNTUK LOGIN & REKAP
# ====================================================
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
if "user_spg" not in st.session_state:
  st.session_state["user_spg"] = ""
if "kota_kab" not in st.session_state:
  st.session_state["kota_kab"] = ""
if "plat_kendaraan" not in st.session_state:
  st.session_state["plat_kendaraan"] = ""
if "laporan_list" not in st.session_state:
  st.session_state["laporan_list"] = []

# ====================================================
# MENU LOGIN PERTAMA
# ====================================================
if not st.session_state["logged_in"]:
  st.markdown(
      "<h2 style='text-align: center;'>🔐 Login Portal Laporan SPG</h2>",
      unsafe_allow_html=True,
  )

  with st.form("form_login"):
    # Pilihan Team SPG 1 sampai 20
    list_spg = [f"Team SPG {i}" for i in range(1, 21)]
    pilihan_user = st.selectbox("Pilih User (Team SPG)", list_spg)

    # Pilihan Kota / Kabupaten
    pilihan_kota = st.selectbox(
        "Pilih Kota / Kabupaten", ["Surabaya", "Gresik"]
    )

    # Input Plat Kendaraan (Bebas)
    plat_input = st.text_input(
        "Plat Nomor Kendaraan", placeholder="Contoh: L 1234 AB"
    )

    # Password berdasarkan user (Contoh: Team SPG 1 passwordnya spg1, atau universal spg123)
    password_input = st.text_input(
        "Password", type="password", placeholder="Masukkan password"
    )

    btn_login = st.form_submit_button("Masuk Aplikasi", type="primary")

    if btn_login:
      spg_num = pilihan_user.replace("Team SPG ", "")
      expected_password = f"spg{spg_num}"

      if password_input == expected_password or password_input == "spg123":
        if not plat_input.strip():
          st.warning("Mohon isi plat nomor kendaraan terlebih dahulu.")
        else:
          st.session_state["logged_in"] = True
          st.session_state["user_spg"] = pilihan_user
          st.session_state["kota_kab"] = pilihan_kota
          st.session_state["plat_kendaraan"] = plat_input.strip().upper()
          st.rerun()
      else:
        st.error(
            f"❌ Password salah untuk {pilihan_user}! (Petunjuk sandi default:"
            f" spg{spg_num} atau spg123)"
        )

  st.stop()  # Hentikan eksekusi sebelum login berhasil

# ====================================================
# APLIKASI UTAMA (SETELAH LOGIN BERHASIL)
# ====================================================
st.markdown(
    "<h2 style='text-align: center;'>📍 Portal Laporan SPG Lapangan</h2>",
    unsafe_allow_html=True,
)

# Tampilkan informasi sesi login di bagian atas
st.success(
    f"👤 **Login sebagai:** {st.session_state['user_spg']} | 🏙️ **Wilayah:**"
    f" {st.session_state['kota_kab']} | 🚗 **Plat:**"
    f" {st.session_state['plat_kendaraan']}"
)

# Tombol Logout kecil
if st.button("🚪 Keluar / Ganti Akun"):
  st.session_state["logged_in"] = False
  st.rerun()

st.markdown("---")


# ====================================================
# 1. AMBIL DATA MASTER WILAYAH DINAMIS (SURABAYA / GRESIK)
# ====================================================
@st.cache_data
def load_master_wilayah(kota):
  # Tentukan nama file geojson berdasarkan pilihan kota saat login
  if kota == "Surabaya":
    filename = "Surabaya Barat.geojson"
  else:
    filename = "Gresik.geojson"

  try:
    with open(filename, "r", encoding="utf-8") as f:
      data = json.load(f)
    gdf_master = gpd.GeoDataFrame.from_features(data)
    return gdf_master
  except Exception as e:
    st.error(f"Gagal memuat file master wilayah '{filename}': {e}")
    return None


# Muat file GeoJSON sesuai wilayah yang dipilih saat login
gdf_wilayah = load_master_wilayah(st.session_state["kota_kab"])

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

user_lat = float(loc["coords"]["latitude"])
user_lon = float(loc["coords"]["longitude"])
akurasi_meter = round(float(loc["coords"].get("accuracy", 0)), 1)

# ====================================================
# 3. DETEKSI POSISI SPG SAAT INI (KECAMATAN & KOORDINAT)
# ====================================================
titik_spg = Point(user_lon, user_lat)
kecamatan_saat_ini = f"Di luar wilayah {st.session_state['kota_kab']}"

if gdf_wilayah is not None:
  for _, row in gdf_wilayah.iterrows():
    geom = row["geometry"]
    if geom and geom.contains(titik_spg):
      kecamatan_saat_ini = row.get("nm_kecamatan", "Tidak diketahui")
      break

st.info(
    f"📍 **Status GPS Anda:**\n\n"
    f"- **Koordinat:** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}` (Akurasi:"
    f" ±{akurasi_meter}m)\n"
    f"- **Posisi Kecamatan Saat Ini:** **{kecamatan_saat_ini}**"
)

# ====================================================
# 4. PILIH KECAMATAN TUJUAN & WARKOP
# ====================================================
st.markdown("### 📋 Lokasi Kunjungan")
kecamatan_pilihan = st.selectbox(
    f"Pilih Kecamatan Tujuan Kunjungan ({st.session_state['kota_kab']})",
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

    nama_konsumen = st.text_input(
        "Nama Konsumen", placeholder="Masukkan nama konsumen"
    )
    gender_entry = st.radio("Gender", ["L", "P"], horizontal=True)
    usia_entry = st.number_input(
        "Usia", min_value=17, max_value=100, step=1, value=25
    )
    nohp_entry = st.text_input("No HP", placeholder="Contoh: 081234567890")

    instagram_input = st.text_input("Instagram", placeholder="username_ig")
    jumlah_bungkus = st.number_input(
        "Jumlah Bungkus", min_value=1, step=1, value=1
    )
    rokok_asal_bumo = st.text_input(
        "Rokok Asal (BUMO)",
        placeholder="Merk rokok yang biasa dikonsumsi sebelumnya",
    )

    btn_kirim = st.form_submit_button(
        "🚀 Kirim Laporan ke Database", type="primary"
    )

    if btn_kirim:
      if not nama_warkop_manual.strip():
        st.warning("Mohon isi nama Warkop/LKK terlebih dahulu.")
      elif not nama_konsumen.strip():
        st.warning("Mohon isi nama konsumen.")
      else:
        # Format Instagram otomatis dengan '@'
        ig_formatted = (
            f"@{instagram_input.strip().lstrip('@')}"
            if instagram_input.strip()
            else "-"
        )

        data_baru = {
            "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Promotor": st.session_state["user_spg"],
            "Kota_Kab": st.session_state["kota_kab"],
            "Plat_Kendaraan": st.session_state["plat_kendaraan"],
            "Kecamatan": kecamatan_pilihan,
            "Warkop_LKK": nama_warkop_manual,
            "Brand_Rokok": brand_entry,
            "Nama_Konsumen": nama_konsumen,
            "Gender": gender_entry,
            "Usia": usia_entry,
            "No_HP": nohp_entry,
            "Instagram": ig_formatted,
            "Jumlah_Bungkus": jumlah_bungkus,
            "Rokok_Asal_BUMO": rokok_asal_bumo,
            "Latitude": user_lat,
            "Longitude": user_lon,
        }

        st.session_state["laporan_list"].append(data_baru)
        st.balloons()
        st.success(
            f"🎉 Laporan konsumen **{nama_konsumen}** di"
            f" **{nama_warkop_manual}** berhasil disimpan!"
        )

else:
  if not lokasi_sah and gdf_wilayah is not None:
    st.error(pesan_validasi)
  elif nama_warkop_manual.strip() == "":
    st.info("ℹ️ Silakan masukkan nama Warkop/LKK terlebih dahulu.")

# ====================================================
# 7. LOG REKAP PENJUALAN & MENU DOWNLOAD EXCEL
# ====================================================
st.markdown("---")
st.markdown("### 📊 Log Rekap Penjualan Lapangan")

if len(st.session_state["laporan_list"]) > 0:
  df_rekap = pd.DataFrame(st.session_state["laporan_list"])
  st.dataframe(df_rekap, use_container_width=True)

  # Menyiapkan file Excel (.xlsx) di memori menggunakan openpyxl
  output = BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_rekap.to_excel(writer, index=False, sheet_name="Rekap Penjualan SPG")
  excel_data = output.getvalue()

  st.download_button(
      label="📥 Download Rekap Excel (.xlsx)",
      data=excel_data,
      file_name=(
          f"rekap_penjualan_{st.session_state['user_spg'].replace(' ', '_')}_"
          f"{st.session_state['kota_kab']}_"
          f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
      ),
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
      type="primary",
  )
else:
  st.info("Belum ada data laporan yang dikirim pada sesi ini.")
