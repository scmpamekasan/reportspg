from datetime import datetime, timedelta
from io import BytesIO
import json
import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import streamlit as st
from streamlit_js_eval import get_geolocation

# ====================================================
# KONFIGURASI HALAMAN STREAMLIT
# ====================================================
st.set_page_config(
    page_title="Laporan SPG Mobile", page_icon="📍", layout="centered"
)

# File database lokal agar data persisten (tidak hilang saat refresh/tutup page)
DB_FILE = "rekap_laporan_spg.csv"


# ====================================================
# FUNGSI MANAJEMEN DATA PERSISTEN (CSV)
# ====================================================
def load_database():
  if os.path.exists(DB_FILE):
    try:
      return pd.read_csv(DB_FILE)
    except Exception:
      return pd.DataFrame()
  return pd.DataFrame(
      columns=[
          "Waktu",
          "Promotor",
          "Kota_Kab",
          "Plat_Kendaraan",
          "Kecamatan",
          "Warkop_LKK",
          "Brand_Rokok",
          "Nama_Konsumen",
          "Gender",
          "Usia",
          "No_HP",
          "Instagram",
          "Jumlah_Bungkus",
          "Rokok_Asal_BUMO",
          "Latitude",
          "Longitude",
      ]
  )


def save_database(df):
  df.to_csv(DB_FILE, index=False)


# ====================================================
# INISIALISASI SESSION STATE UNTUK LOGIN
# ====================================================
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
if "user_spg" not in st.session_state:
  st.session_state["user_spg"] = ""
if "kota_kab" not in st.session_state:
  st.session_state["kota_kab"] = ""
if "plat_kendaraan" not in st.session_state:
  st.session_state["plat_kendaraan"] = ""

# ====================================================
# MENU LOGIN PERTAMA (Team SPG 1 sampai 20)
# ====================================================
if not st.session_state["logged_in"]:
  st.markdown(
      "<h2 style='text-align: center;'>🔐 Login Portal Laporan SPG</h2>",
      unsafe_allow_html=True,
  )

  with st.form("form_login"):
    list_spg = [f"Team SPG {i}" for i in range(1, 21)]
    pilihan_user = st.selectbox("Pilih User (Team SPG)", list_spg)
    pilihan_kota = st.selectbox(
        "Pilih Kota / Kabupaten", ["Surabaya", "Gresik"]
    )
    plat_input = st.text_input(
        "Plat Nomor Kendaraan", placeholder="Contoh: L 1234 AB"
    )
    password_input = st.text_input(
        "Password", type="password", placeholder="Masukkan password"
    )

    btn_login = st.form_submit_button("Masuk Aplikasi", type="primary")

    if btn_login:
      spg_num = pilihan_user.replace("Team SPG ", "")
      expected_password = f"spg{spg_num}"  # Contoh: Team SPG 1 passwordnya 'spg1'

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

  st.stop()

# ====================================================
# APLIKASI UTAMA (SETELAH LOGIN BERHASIL)
# ====================================================
st.markdown(
    "<h2 style='text-align: center;'>📍 Portal Laporan SPG Lapangan</h2>",
    unsafe_allow_html=True,
)

st.success(
    f"👤 **Login sebagai:** {st.session_state['user_spg']} | 🏙️ **Wilayah:**"
    f" {st.session_state['kota_kab']} | 🚗 **Plat:**"
    f" {st.session_state['plat_kendaraan']}"
)

if st.button("🚪 Keluar / Ganti Akun"):
  st.session_state["logged_in"] = False
  st.rerun()

st.markdown("---")


# ====================================================
# 1. AMBIL DATA MASTER WILAYAH DINAMIS (SURABAYA / GRESIK)
# ====================================================
@st.cache_data
def load_master_wilayah(kota):
  if kota == "Surabaya":
    filename = "Surabaya Barat.geojson"
  elif kota == "Gresik":
    filename = "Gresik.geojson"
  else:
    return None

  try:
    with open(filename, "r", encoding="utf-8") as f:
      data = json.load(f)
    gdf_master = gpd.GeoDataFrame.from_features(data)
    return gdf_master
  except Exception as e:
    st.error(f"Gagal memuat file master wilayah '{filename}': {e}")
    return None


gdf_wilayah = load_master_wilayah(st.session_state["kota_kab"])

daftar_kecamatan = []
if gdf_wilayah is not None:
  col_kec = None
  for c in ["nm_kecamatan", "KECAMATAN", "kecamatan", "Name", "NAME"]:
    if c in gdf_wilayah.columns:
      col_kec = c
      break
  if col_kec:
    daftar_kecamatan = sorted(
        gdf_wilayah[col_kec].dropna().unique().tolist()
    )
  else:
    daftar_kecamatan = ["Kecamatan Default"]

# ====================================================
# 2. AMBIL KOORDINAT GPS OTOMATIS SAAT WEB DIBUKA
# ====================================================
loc = get_geolocation()

if loc is None:
  st.warning(
      "⏳ Sedang mengunci titik GPS lokasi Anda... Pastikan izin lokasi"
      " (**Allow / Izinkan**) aktif pada browser Anda."
  )
  user_lat = -7.2575
  user_lon = 112.7521
  akurasi_meter = 0.0
else:
  user_lat = float(loc["coords"]["latitude"])
  user_lon = float(loc["coords"]["longitude"])
  akurasi_meter = round(float(loc["coords"].get("accuracy", 0)), 1)

st.info(
    f"📍 **Status GPS Anda:**\n\n"
    f"- **Koordinat:** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}` (Akurasi:"
    f" ±{akurasi_meter}m)\n"
    f"- **Wilayah Sesi:** **{st.session_state['kota_kab']}**"
)

# ====================================================
# 3. PILIH KECAMATAN TUJUAN & WARKOP
# ====================================================
st.markdown("### 📋 Lokasi Kunjungan")

nama_SPG = st.text_input(
    "Nama SPG (Entry Manual)",
    placeholder="Contoh: Luna Maya",
)

kecamatan_pilihan = st.selectbox(
    f"Pilih Kecamatan Tujuan Kunjungan ({st.session_state['kota_kab']})",
    daftar_kecamatan if daftar_kecamatan else ["Kecamatan Umum"],
)

nama_warkop_manual = st.text_input(
    "Nama Warkop / LKK (Entry Manual)",
    placeholder="Contoh: Warkop Cak No",
)

# ====================================================
# 4. FORM LAPORAN KONSUMEN
# ====================================================
if nama_warkop_manual.strip() != "":
  st.success(
      f"✅ Form laporan di **Kecamatan {kecamatan_pilihan}** siap diisi."
  )

  st.markdown("---")
  with st.form("form_laporan_spg"):
    st.markdown("### 📝 Form Input Laporan Konsumen")

    st.write(
        f"**User:** {st.session_state['user_spg']} |"
        f" **Warkop/LKK:** {nama_warkop_manual}"
    )

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

        df_all = load_database()
        df_new_row = pd.DataFrame([data_baru])
        df_all = pd.concat([df_all, df_new_row], ignore_index=True)
        save_database(df_all)

        st.balloons()
        st.success(
            f"🎉 Laporan konsumen **{nama_konsumen}** oleh"
            f" **{st.session_state['user_spg']}** berhasil disimpan!"
        )
else:
  st.info("ℹ️ Silakan masukkan nama Warkop/LKK terlebih dahulu untuk membuka form.")

# ====================================================
# 5. EVALUASI HARIAN & LOG REKAP (KHUSUS USER AKTIF)
# ====================================================
st.markdown("---")
st.markdown(
    f"### 📈 Evaluasi Harian & Log Rekap: {st.session_state['user_spg']} ("
    f"{st.session_state['kota_kab']})"
)

df_master_all = load_database()

# Filter data HANYA untuk user yang sedang login
if not df_master_all.empty and "Promotor" in df_master_all.columns:
  df_user_rekap = df_master_all[
      df_master_all["Promotor"] == st.session_state["user_spg"]
  ].copy()
else:
  df_user_rekap = pd.DataFrame()

if not df_user_rekap.empty:
  df_user_rekap["Tanggal"] = pd.to_datetime(
      df_user_rekap["Waktu"], errors="coerce"
  ).dt.date

  # ----------------------------------------------------
  # TABEL EVALUASI HARIAN
  # ----------------------------------------------------
  st.markdown("#### 📋 Tabel Evaluasi Harian")

  df_eval = (
      df_user_rekap.groupby(["Tanggal", "Promotor", "Brand_Rokok"])
      .agg(
          Jumlah_Titik_Warkop=(
              "Warkop_LKK",
              lambda x: x.nunique(),
          ),  # Single count titik warkop
          Konsumen_Beli=(
              "Nama_Konsumen",
              "count",
          ),  # Jumlah dari konsumen yang beli
          Jumlah_Omset=(
              "Jumlah_Bungkus",
              "sum",
          ),  # Jumlah rokok yang terjual
      )
      .reset_index()
  )


  def tentukan_status(row):
    if row["Brand_Rokok"] == "Black Matcha K12":
      if row["Jumlah_Omset"] >= 50:
        return "Achieved"
      else:
        return "Not Achieved"
    else:
      return "Achieved"


  df_eval["Status_Target"] = df_eval.apply(tentukan_status, axis=1)


  def style_eval(val):
    if val == "Not Achieved":
      return "color: red; font-weight: bold;"
    elif val == "Achieved":
      return "color: green; font-weight: bold;"
    return ""


  st.dataframe(
      df_eval.style.map(style_eval, subset=["Status_Target"]),
      use_container_width=True,
  )

  st.markdown("---")
  st.markdown("#### 📑 Log Detail Transaksi & Pengaturan")

  st.dataframe(
      df_user_rekap.drop(columns=["Tanggal"], errors="ignore"),
      use_container_width=True,
  )

  # ==========================================
  # MENU PENGATURAN / HAPUS LOG
  # ==========================================
  with st.expander("⚙️ Menu Pengaturan & Hapus Log"):
    tab_row, tab_hari, tab_minggu, tab_all = st.tabs([
        "Hapus per Row",
        "Hapus per Hari",
        "Hapus per Minggu",
        "Hapus Semua (All)",
    ])

    with tab_row:
      options_row = []
      for idx, row in df_user_rekap.iterrows():
        label = (
            f"[{row['Waktu']}] {row['Nama_Konsumen']} - {row['Warkop_LKK']}"
            f" ({row['Brand_Rokok']})"
        )
        options_row.append((idx, label))

      selected_row_to_delete = st.selectbox(
          "Pilih Data Baris",
          options=options_row,
          format_func=lambda x: x[1],
          key="sel_row",
      )

      if st.button("🗑️ Hapus Baris Terpilih", type="secondary"):
        if selected_row_to_delete:
          original_idx = selected_row_to_delete[0]
          df_master_all = df_master_all.drop(original_idx).reset_index(
              drop=True
          )
          save_database(df_master_all)
          st.success("✅ Berhasil menghapus baris data terpilih!")
          st.rerun()

    with tab_hari:
      unique_dates = df_user_rekap["Tanggal"].dropna().unique().tolist()
      unique_dates = sorted(unique_dates, reverse=True)

      if unique_dates:
        selected_date = st.selectbox("Pilih Tanggal", options=unique_dates)
        if st.button("🗑️ Hapus Log Tanggal Ini", type="secondary"):
          mask_user_other_date = ~(
              (df_master_all["Promotor"] == st.session_state["user_spg"])
              & (
                  pd.to_datetime(
                      df_master_all["Waktu"], errors="coerce"
                  ).dt.date
                  == selected_date
              )
          )
          df_master_all = df_master_all[mask_user_other_date].reset_index(
              drop=True
          )
          save_database(df_master_all)
          st.success(
              f"✅ Berhasil menghapus semua log untuk tanggal {selected_date}!"
          )
          st.rerun()
      else:
        st.info("Tidak ada data tanggal yang tersedia.")

    with tab_minggu:
      if st.button("🗑️ Hapus Log 7 Hari Terakhir", type="secondary"):
        cutoff_date = datetime.now() - timedelta(days=7)
        mask_user_keep = ~(
            (df_master_all["Promotor"] == st.session_state["user_spg"])
            & (
                pd.to_datetime(df_master_all["Waktu"], errors="coerce")
                >= cutoff_date
            )
        )
        df_master_all = df_master_all[mask_user_keep].reset_index(drop=True)
        save_database(df_master_all)
        st.success("✅ Berhasil menghapus log dalam 7 hari terakhir!")
        st.rerun()

    with tab_all:
      st.warning(
          "⚠️ Perhatian: Tindakan ini akan menghapus **seluruh** riwayat log"
          f" rekap penjualan atas nama {st.session_state['user_spg']} secara"
          " permanen!"
      )
      confirm_delete_all = st.checkbox(
          "Saya yakin ingin menghapus semua data saya"
      )
      if st.button(
          "🗑️ Hapus Semua Data Saya (All)",
          type="primary",
          disabled=not confirm_delete_all,
      ):
        df_master_all = df_master_all[
            df_master_all["Promotor"] != st.session_state["user_spg"]
        ].reset_index(drop=True)
        save_database(df_master_all)
        st.success(
            "✅ Seluruh data rekap penjualan Anda berhasil dihapus dari sistem!"
        )
        st.rerun()

  # ==========================================
  # TOMBOL DOWNLOAD EXCEL
  # ==========================================
  output = BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_eval.to_excel(writer, index=False, sheet_name="Evaluasi Harian")
    df_user_rekap.drop(columns=["Tanggal"], errors="ignore").to_excel(
        writer, index=False, sheet_name="Detail Transaksi"
    )
  excel_data = output.getvalue()

  st.download_button(
      label=f"📥 Download Rekap Excel (.xlsx) - {st.session_state['user_spg']}",
      data=excel_data,
      file_name=(
          f"rekap_evaluasi_{st.session_state['user_spg'].replace(' ', '_')}_"
          f"{st.session_state['kota_kab']}_"
          f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
      ),
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
      type="primary",
  )
else:
  st.info(
      f"Belum ada data laporan tersimpan untuk {st.session_state['user_spg']}."
  )
