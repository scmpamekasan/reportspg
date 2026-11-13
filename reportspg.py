from datetime import datetime, timedelta
from io import BytesIO
import json
import os
import geopandas as gpd
import pandas as pd
import pydeck as pdk
from shapely.geometry import Point
import streamlit as st
from streamlit_js_eval import get_geolocation

# ====================================================
# KONFIGURASI HALAMAN STREAMLIT
# ====================================================
st.set_page_config(
    page_title="Laporan SPG Mobile",
    page_icon="📍",
    layout="centered",
    initial_sidebar_state="auto",
)

# ====================================================
# CUSTOM CSS UNTUK UI MODERN
# ====================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4f6f9;
    }
    .login-header {
        background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%);
        padding: 28px 20px;
        border-radius: 16px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 20px rgba(211, 47, 47, 0.25);
        margin-bottom: 24px;
    }
    .login-header h1 {
        margin: 0;
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .login-header p {
        margin: 8px 0 0 0;
        font-size: 0.92rem;
        opacity: 0.9;
    }
    [data-testid="stForm"] {
        background-color: #ffffff;
        padding: 26px 24px;
        border-radius: 16px;
        border: 1px solid #e6e9ef;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
    }
    [data-testid="stFormSubmitButton"] > button {
        width: 100%;
        background: linear-gradient(135deg, #d32f2f 0%, #9a0007 100%);
        color: white;
        font-weight: 600;
        font-size: 1rem;
        padding: 0.65rem 1rem;
        border-radius: 10px;
        border: none;
        transition: all 0.25s ease;
        margin-top: 10px;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(211, 47, 47, 0.35);
    }
    .user-banner {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: #f8fafc;
        padding: 16px 20px;
        border-radius: 14px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
    }
    .user-banner-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .user-banner-sub {
        font-size: 0.88rem;
        color: #cbd5e1;
    }
    .kpi-card {
        background-color: #ffffff;
        padding: 16px;
        border-radius: 12px;
        border-left: 5px solid #d32f2f;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 10px;
    }
    .kpi-value {
        font-size: 1.5rem;
        font-weight: 800;
        color: #1e293b;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
    }
    .footer-note {
        text-align: center;
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# File database lokal agar data persisten
DB_FILE = "rekap_laporan_spg.csv"

EXPECTED_COLUMNS = [
    "Waktu",
    "Nama_Team",
    "Nama_SPG",
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


def load_database():
  if os.path.exists(DB_FILE):
    try:
      df = pd.read_csv(DB_FILE)
      for col in EXPECTED_COLUMNS:
        if col not in df.columns:
          df[col] = "-"
      return df[EXPECTED_COLUMNS]
    except Exception:
      return pd.DataFrame(columns=EXPECTED_COLUMNS)
  return pd.DataFrame(columns=EXPECTED_COLUMNS)


def save_database(df):
  df.to_csv(DB_FILE, index=False)


def tentukan_status_target(row):
  brand = row["Brand_Rokok"]
  omset = row["Jumlah_Omset"]
  if brand == "Black Matcha K12":
    return "Achieved" if omset >= 100 else "Not Achieved"
  elif brand in ["D.Super 12", "D.76 Apel Royal"]:
    return "Achieved" if omset >= 80 else "Not Achieved"
  else:
    return "Achieved"


def style_status_target(val):
  if val == "Not Achieved":
    return "color: #d32f2f; font-weight: bold;"
  elif val == "Achieved":
    return "color: #16a34a; font-weight: bold;"
  return ""


# ====================================================
# INISIALISASI SESSION STATE
# ====================================================
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
if "user_spg" not in st.session_state:
  st.session_state["user_spg"] = ""
if "kota_kab" not in st.session_state:
  st.session_state["kota_kab"] = ""
if "plat_kendaraan" not in st.session_state:
  st.session_state["plat_kendaraan"] = ""
if "admin_logged_in" not in st.session_state:
  st.session_state["admin_logged_in"] = False

# ====================================================
# SIDEBAR: MENU REKAP ALL USER & ADMIN CONTROLS
# ====================================================
if not st.session_state["logged_in"]:
  with st.sidebar:
    st.markdown("### 🔐 Menu Admin / Supervisor")
    st.markdown(
        "Akses khusus laporan rekapitulasi seluruh team SPG dari halaman login."
    )

    if not st.session_state["admin_logged_in"]:
      with st.form("form_admin_login"):
        pass_input = st.text_input(
            "Password Admin", type="password"
        )
        btn_pass = st.form_submit_button("Buka Rekap All User")

        if btn_pass:
          if pass_input == "admin123":
            st.session_state["admin_logged_in"] = True
            st.success("✅ Berhasil masuk sebagai Admin!")
            st.rerun()
          else:
            st.error("❌ Password salah! (Gunakan: admin123)")
    else:
      st.success("🟢 Status: Admin Aktif")
      if st.button("🔒 Keluar dari Mode Admin"):
        st.session_state["admin_logged_in"] = False
        st.rerun()

# ====================================================
# TAMPILAN JIKA ADMIN MASUK DARI SIDEBAR (ALL USER)
# ====================================================
if not st.session_state["logged_in"] and st.session_state["admin_logged_in"]:
  st.markdown(
      "## 🌐 Dashboard Report Rekap All User (Mode Supervisor/Admin)"
  )
  st.info(
      "Anda sedang melihat rekapitulasi data seluruh Team SPG (1 - 20) secara"
      " terpusat."
  )

  if st.button("⬅️ Kembali ke Menu Utama Login"):
    st.session_state["admin_logged_in"] = False
    st.rerun()

  st.markdown("---")

  df_all_users = load_database()
  if df_all_users.empty:
    st.warning("📭 Belum ada data laporan yang tersimpan di sistem.")
  else:
    df_all_users["Tanggal"] = pd.to_datetime(
        df_all_users["Waktu"], errors="coerce"
    ).dt.date
    df_all_users["Jumlah_Bungkus"] = pd.to_numeric(
        df_all_users["Jumlah_Bungkus"], errors="coerce"
    ).fillna(0)

    with st.expander("🔍 Filter Data Rekap All User", expanded=True):
      col_f1, col_f2, col_f3 = st.columns(3)
      with col_f1:
        list_kota_all = ["Semua Wilayah"] + sorted(
            df_all_users["Kota_Kab"].dropna().unique().tolist()
        )
        filter_kota = st.selectbox("Filter Wilayah", list_kota_all)
      with col_f2:
        list_tgl_all = ["Semua Tanggal"] + sorted(
            df_all_users["Tanggal"].dropna().unique().tolist(), reverse=True
        )
        filter_tanggal = st.selectbox("Filter Tanggal", list_tgl_all)
      with col_f3:
        list_brand_all = ["Semua Brand"] + sorted(
            df_all_users["Brand_Rokok"].dropna().unique().tolist()
        )
        filter_brand = st.selectbox("Filter Brand", list_brand_all)

    df_filtered = df_all_users.copy()
    if filter_kota != "Semua Wilayah":
      df_filtered = df_filtered[df_filtered["Kota_Kab"] == filter_kota]
    if filter_tanggal != "Semua Tanggal":
      df_filtered = df_filtered[df_filtered["Tanggal"] == filter_tanggal]
    if filter_brand != "Semua Brand":
      df_filtered = df_filtered[df_filtered["Brand_Rokok"] == filter_brand]

    total_omset = int(df_filtered["Jumlah_Bungkus"].sum())
    total_konsumen = len(df_filtered)
    total_warkop = df_filtered["Warkop_LKK"].nunique()
    total_team_aktif = df_filtered["Nama_Team"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
      st.markdown(
          f'<div class="kpi-card"><div class="kpi-value">{total_omset:,}</div>'
          '<div class="kpi-label">Total Omset (Bks)</div></div>',
          unsafe_allow_html=True,
      )
    with k2:
      st.markdown(
          f'<div class="kpi-card"><div class="kpi-value">{total_konsumen:,}'
          '</div><div class="kpi-label">Total Konsumen</div></div>',
          unsafe_allow_html=True,
      )
    with k3:
      st.markdown(
          f'<div class="kpi-card"><div class="kpi-value">{total_warkop:,}</div>'
          '<div class="kpi-label">Titik Warkop/LKK</div></div>',
          unsafe_allow_html=True,
      )
    with k4:
      st.markdown(
          f'<div class="kpi-card"><div class="kpi-value">{total_team_aktif}'
          '</div><div class="kpi-label">Team Aktif</div></div>',
          unsafe_allow_html=True,
      )

    st.markdown("---")
    st.markdown("#### 🏆 Tabel Evaluasi Performa All Team SPG")

    if not df_filtered.empty:
      df_eval_all = (
          df_filtered.groupby(
              ["Tanggal", "Kota_Kab", "Nama_Team", "Brand_Rokok"]
          )
          .agg(
              Jumlah_Titik_Warkop=("Warkop_LKK", lambda x: x.nunique()),
              Konsumen_Beli=("Nama_Konsumen", "count"),
              Jumlah_Omset=("Jumlah_Bungkus", "sum"),
          )
          .reset_index()
          .sort_values(
              by=["Tanggal", "Jumlah_Omset"], ascending=[False, False]
          )
      )

      df_eval_all["Status_Target"] = df_eval_all.apply(
          tentukan_status_target, axis=1
      )

      st.dataframe(
          df_eval_all.style.map(style_status_target, subset=["Status_Target"]),
          use_container_width=True,
      )

      st.markdown("#### 📊 Leaderboard Total Omset Per Team SPG")
      df_leaderboard = (
          df_filtered.groupby(["Nama_Team", "Kota_Kab"])
          .agg(
              Total_Hari_Aktif=("Tanggal", lambda x: x.nunique()),
              Total_Warkop=("Warkop_LKK", lambda x: x.nunique()),
              Total_Konsumen=("Nama_Konsumen", "count"),
              Total_Omset_Bungkus=("Jumlah_Bungkus", "sum"),
          )
          .reset_index()
          .sort_values(by="Total_Omset_Bungkus", ascending=False)
      )
      st.dataframe(df_leaderboard, use_container_width=True)

      st.markdown("---")
      st.markdown("#### 📑 Log Detail Transaksi All User")
      st.dataframe(
          df_filtered.drop(columns=["Tanggal"], errors="ignore").sort_values(
              by="Waktu", ascending=False
          ),
          use_container_width=True,
      )

      # ==========================================
      # MENU PENGATURAN / HAPUS LOG (HANYA UNTUK ADMIN)
      # ==========================================
      with st.expander("⚙️ Menu Pengaturan & Hapus Log (Admin Panel)"):
        tab_row, tab_hari, tab_minggu, tab_all = st.tabs([
            "Hapus per Row",
            "Hapus per Hari",
            "Hapus per Minggu",
            "Hapus Semua (All)",
        ])

        with tab_row:
          options_row = []
          for idx, row in df_filtered.iterrows():
            label = (
                f"[{row['Waktu']}] Team: {row['Nama_Team']} | SPG:"
                f" {row['Nama_SPG']} | Konsumen: {row['Nama_Konsumen']} -"
                f" {row['Warkop_LKK']} ({row['Brand_Rokok']})"
            )
            options_row.append((idx, label))

          selected_row_to_delete = st.selectbox(
              "Pilih Data Baris",
              options=options_row,
              format_func=lambda x: x[1],
              key="sel_row_admin",
          )

          if st.button("🗑️ Hapus Baris Terpilih (Admin)", type="secondary"):
            if selected_row_to_delete:
              original_idx = selected_row_to_delete[0]
              df_master_all = load_database()
              df_master_all = df_master_all.drop(original_idx).reset_index(
                  drop=True
              )
              save_database(df_master_all)
              st.success(
                  "✅ Berhasil menghapus baris data terpilih oleh Admin!"
              )
              st.rerun()

        with tab_hari:
          unique_dates = sorted(
              df_filtered["Tanggal"].dropna().unique().tolist(), reverse=True
          )
          if unique_dates:
            selected_date = st.selectbox(
                "Pilih Tanggal", options=unique_dates, key="sel_date_admin"
            )
            if st.button(
                "🗑️ Hapus Log Tanggal Ini (Admin)", type="secondary"
            ):
              df_master_all = load_database()
              df_master_all["Tgl_Cek"] = pd.to_datetime(
                  df_master_all["Waktu"], errors="coerce"
              ).dt.date
              mask_keep = df_master_all["Tgl_Cek"] != selected_date
              df_master_all = df_master_all[mask_keep].drop(
                  columns=["Tgl_Cek"], errors="ignore"
              )
              save_database(df_master_all)
              st.success(
                  f"✅ Berhasil menghapus semua log tanggal {selected_date}!"
              )
              st.rerun()
          else:
            st.info("Tidak ada data tanggal yang tersedia.")

        with tab_minggu:
          if st.button(
              "🗑️ Hapus Log 7 Hari Terakhir (Admin)", type="secondary"
          ):
            cutoff_date = datetime.now() - timedelta(days=7)
            df_master_all = load_database()
            df_master_all["Dt_Cek"] = pd.to_datetime(
                df_master_all["Waktu"], errors="coerce"
            )
            mask_keep = df_master_all["Dt_Cek"] < cutoff_date
            df_master_all = df_master_all[mask_keep].drop(
                columns=["Dt_Cek"], errors="ignore"
            )
            save_database(df_master_all)
            st.success("✅ Berhasil menghapus log 7 hari terakhir!")
            st.rerun()

        with tab_all:
          st.warning(
              "⚠️ Perhatian: Tindakan ini akan menghapus **SELURUH** riwayat"
              " laporan dari semua Team SPG secara permanen!"
          )
          confirm_delete_all = st.checkbox(
              "Saya yakin ingin menghapus seluruh data sistem",
              key="chk_all_admin",
          )
          if st.button(
              "🗑️ Hapus Semua Data Sistem (All)",
              type="primary",
              disabled=not confirm_delete_all,
          ):
            empty_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
            save_database(empty_df)
            st.success(
                "✅ Seluruh database laporan berhasil dikosongkan oleh Admin!"
            )
            st.rerun()

      output_all = BytesIO()
      with pd.ExcelWriter(output_all, engine="openpyxl") as writer:
        df_leaderboard.to_excel(
            writer, index=False, sheet_name="Leaderboard Team"
        )
        df_eval_all.to_excel(
            writer, index=False, sheet_name="Evaluasi Harian All"
        )
        df_filtered.drop(columns=["Tanggal"], errors="ignore").to_excel(
            writer, index=False, sheet_name="Detail All Transaksi"
        )

      st.download_button(
          label="📥 Download Rekap All User (.xlsx)",
          data=output_all.getvalue(),
          file_name=(
              "rekap_ALL_USER_SPG_"
              f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
          ),
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
          type="primary",
      )
    else:
      st.warning("Tidak ada data yang cocok dengan filter yang dipilih.")

  st.stop()

# ====================================================
# HALAMAN LOGIN UTAMA
# ====================================================
if not st.session_state["logged_in"]:
  _, col_center, _ = st.columns([0.05, 0.9, 0.05])

  with col_center:
    st.markdown(
        """
        <div class="login-header">
            <div style="font-size: 2.5rem; margin-bottom: 6px;">📍</div>
            <h1>PORTAL LAPORAN SPG</h1>
            <p>Sistem Pelaporan Lapangan &amp; Monitoring Geofencing</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("form_login"):
      st.markdown("#### 🔐 Masuk ke Akun Operasional")
      st.caption("Silakan lengkapi identitas team dan kendaraan sebelum mulai.")

      list_spg = [f"Team SPG {i}" for i in range(1, 21)]
      pilihan_user = st.selectbox("👤 Pilih User (Team SPG)", list_spg)

      col_k1, col_k2 = st.columns(2)
      with col_k1:
        pilihan_kota = st.selectbox(
            "🏙️ Wilayah Operasional", ["Surabaya", "Gresik"]
        )
      with col_k2:
        plat_input = st.text_input(
            "🚗 Plat Kendaraan", placeholder="Contoh: L 1234 AB"
        )

      password_input = st.text_input(
          "🔑 Kata Sandi (Password)",
          type="password",
          placeholder="Masukkan password akun Anda",
      )

      btn_login = st.form_submit_button("🚀 Masuk Aplikasi")

      if btn_login:
        spg_num = pilihan_user.replace("Team SPG ", "")
        expected_password = f"spg{spg_num}"

        if password_input == expected_password or password_input == "spg123":
          if not plat_input.strip():
            st.warning("⚠️ Mohon isi plat nomor kendaraan terlebih dahulu.")
          else:
            st.session_state["logged_in"] = True
            st.session_state["user_spg"] = pilihan_user
            st.session_state["kota_kab"] = pilihan_kota
            st.session_state["plat_kendaraan"] = plat_input.strip().upper()
            st.rerun()
        else:
          st.error(
              f"❌ Password salah untuk **{pilihan_user}**! (Petunjuk default:"
              f" `spg{spg_num}` atau `spg123`)"
          )

    st.markdown(
        """
        <div class="footer-note">
            Gunakan sidebar kiri untuk masuk ke menu <b>Report Rekap All User</b> (Password Admin: <code>admin123</code>).<br/>
            © 2026 Field Force Monitoring System
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.stop()

# ====================================================
# APLIKASI UTAMA SETELAH LOGIN SPG BERHASIL
# ====================================================
col_banner, col_logout = st.columns([0.78, 0.22])

with col_banner:
  st.markdown(
      f"""
      <div class="user-banner">
          <div class="user-banner-title">👤 {st.session_state['user_spg']}</div>
          <div class="user-banner-sub">
              🏙️ Wilayah: <b>{st.session_state['kota_kab']}</b> &nbsp;|&nbsp;
              🚗 Plat: <b>{st.session_state['plat_kendaraan']}</b>
          </div>
      </div>
      """,
      unsafe_allow_html=True,
  )

with col_logout:
  st.write("")
  if st.button("🚪 Keluar", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

st.markdown("---")


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
    if gdf_master.crs is None:
      gdf_master.set_crs("EPSG:4326", inplace=True)
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

# GPS & Geofencing
loc = get_geolocation()

if loc is None:
  st.warning(
      "⏳ Sedang mengunci titik GPS lokasi Anda... Pastikan izin lokasi"
      " (**Allow / Izinkan**) aktif pada browser Anda."
  )
  user_lat = -7.2575
  user_lon = 112.7521
  akurasi_meter = 0.0
  is_inside_geofence = False
else:
  user_lat = float(loc["coords"]["latitude"])
  user_lon = float(loc["coords"]["longitude"])
  akurasi_meter = round(float(loc["coords"].get("accuracy", 0)), 1)

  point_user = Point(user_lon, user_lat)
  is_inside_geofence = False

  if gdf_wilayah is not None:
    for geom in gdf_wilayah.geometry:
      if geom.contains(point_user) or geom.intersects(point_user):
        is_inside_geofence = True
        break
  else:
    is_inside_geofence = True

if is_inside_geofence:
  st.success(
      f"📍 **Status GPS (Valid & Terkunci di Wilayah):**\n\n"
      f"- **Koordinat:** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}` (Akurasi:"
      f" ±{akurasi_meter}m)\n"
      f"- **Wilayah Sesi:** **{st.session_state['kota_kab']}** (✅ Dalam Area"
      " Operasional)"
  )
else:
  st.error(
      f"🚨 **Peringatan Lock GPS (Diluar Wilayah Operasional):**\n\n"
      f"- **Koordinat Anda:** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}`\n"
      f"- **Wilayah Terpilih:** **{st.session_state['kota_kab']}**\n\n"
      "⚠️ Posisi Anda terdeteksi berada di luar batas zona GeoJSON wilayah"
      f" {st.session_state['kota_kab']}. Form laporan dikunci sampai Anda"
      " berada di dalam area operasional yang sah."
  )

st.markdown("### 📋 Lokasi Kunjungan")
nama_spg_manual = st.text_input("Nama SPG (Entry Manual)", placeholder="Contoh: Nanda")
kecamatan_pilihan = st.selectbox(
    f"Pilih Kecamatan Tujuan Kunjungan ({st.session_state['kota_kab']})",
    daftar_kecamatan if daftar_kecamatan else ["Kecamatan Umum"],
)
nama_warkop_manual = st.text_input(
    "Nama Warkop / LKK (Entry Manual)", placeholder="Contoh: Warkop Cak No"
)

if (
    is_inside_geofence
    and nama_spg_manual.strip() != ""
    and nama_warkop_manual.strip() != ""
):
  st.success(
      f"✅ Form laporan untuk **{nama_spg_manual.strip()}** di **Kecamatan"
      f" {kecamatan_pilihan}** siap diisi."
  )
  st.markdown("---")
  with st.form("form_laporan_spg"):
    st.markdown("### 📝 Form Input Laporan Konsumen")
    st.write(
        f"**Team Login:** {st.session_state['user_spg']} | **Nama SPG:**"
        f" {nama_spg_manual.strip()} | **Warkop/LKK:**"
        f" {nama_warkop_manual.strip()}"
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

    btn_kirim = st.form_submit_button("🚀 Kirim Laporan ke Database")

    if btn_kirim:
      if not nama_konsumen.strip():
        st.warning("Mohon isi nama konsumen.")
      else:
        ig_formatted = (
            f"@{instagram_input.strip().lstrip('@')}"
            if instagram_input.strip()
            else "-"
        )
        data_baru = {
            "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Nama_Team": st.session_state["user_spg"],
            "Nama_SPG": nama_spg_manual.strip(),
            "Kota_Kab": st.session_state["kota_kab"],
            "Plat_Kendaraan": st.session_state["plat_kendaraan"],
            "Kecamatan": kecamatan_pilihan,
            "Warkop_LKK": nama_warkop_manual.strip(),
            "Brand_Rokok": brand_entry,
            "Nama_Konsumen": nama_konsumen.strip(),
            "Gender": gender_entry,
            "Usia": usia_entry,
            "No_HP": nohp_entry.strip(),
            "Instagram": ig_formatted,
            "Jumlah_Bungkus": jumlah_bungkus,
            "Rokok_Asal_BUMO": rokok_asal_bumo.strip(),
            "Latitude": user_lat,
            "Longitude": user_lon,
        }
        df_all = load_database()
        df_new_row = pd.DataFrame([data_baru])
        df_all = pd.concat([df_all, df_new_row], ignore_index=True)
        save_database(df_all)
        st.balloons()
        st.success(
            f"🎉 Laporan konsumen **{nama_konsumen}** oleh SPG"
            f" **{nama_spg_manual.strip()}** berhasil disimpan!"
        )
else:
  if not is_inside_geofence:
    st.warning(
        "🔒 Form input terkunci karena posisi GPS Anda berada di luar wilayah"
        f" {st.session_state['kota_kab']}."
    )
  else:
    st.info(
        "ℹ️ Silakan masukkan **Nama SPG** dan **Nama Warkop/LKK** terlebih"
        " dahulu untuk membuka form."
    )

st.markdown("---")
st.markdown(
    f"### 📈 Evaluasi Harian & Log Rekap: {st.session_state['user_spg']} ("
    f"{st.session_state['kota_kab']})"
)

df_master_all = load_database()
if not df_master_all.empty and "Nama_Team" in df_master_all.columns:
  df_user_rekap = df_master_all[
      df_master_all["Nama_Team"] == st.session_state["user_spg"]
  ].copy()
else:
  df_user_rekap = pd.DataFrame()

if not df_user_rekap.empty:
  df_user_rekap["Tanggal"] = pd.to_datetime(
      df_user_rekap["Waktu"], errors="coerce"
  ).dt.date
  df_user_rekap["Nama_SPG"] = df_user_rekap["Nama_SPG"].fillna("-")

  st.markdown("#### 📋 Tabel Evaluasi Harian Per Team SPG")
  df_eval = (
      df_user_rekap.groupby(["Tanggal", "Nama_Team", "Brand_Rokok"])
      .agg(
          Jumlah_Titik_Warkop=("Warkop_LKK", lambda x: x.nunique()),
          Konsumen_Beli=("Nama_Konsumen", "count"),
          Jumlah_Omset=("Jumlah_Bungkus", "sum"),
      )
      .reset_index()
  )
  df_eval["Status_Target"] = df_eval.apply(tentukan_status_target, axis=1)

  st.dataframe(
      df_eval.style.map(style_status_target, subset=["Status_Target"]),
      use_container_width=True,
  )

  st.markdown("---")
  st.markdown("#### 📑 Log Detail Transaksi & Pengaturan")
  st.dataframe(
      df_user_rekap.drop(columns=["Tanggal"], errors="ignore"),
      use_container_width=True,
  )

  # Visualisasi Rute
  st.markdown("---")
  st.markdown(
      f"### 🗺️ Visualisasi Rute Perjalanan Lapangan -"
      f" {st.session_state['user_spg']}"
  )
  daftar_tanggal = sorted(
      df_user_rekap["Tanggal"].dropna().unique(), reverse=True
  )
  if daftar_tanggal:
    pilihan_tgl_rute = st.selectbox(
        "Pilih Tanggal Rute Perjalanan", options=daftar_tanggal
    )
    df_rute_harian = df_user_rekap[
        df_user_rekap["Tanggal"] == pilihan_tgl_rute
    ].sort_values("Waktu")

    if not df_rute_harian.empty and "Latitude" in df_rute_harian.columns:
      koordinat_list = df_rute_harian[["Longitude", "Latitude"]].values.tolist()
      center_lat = df_rute_harian["Latitude"].mean()
      center_lon = df_rute_harian["Longitude"].mean()

      path_layer = pdk.Layer(
          "PathLayer",
          data=[{"path": koordinat_list, "name": "Rute SPG"}],
          get_path="path",
          get_color=[255, 0, 0, 200],
          get_width=5,
          pickable=True,
      )
      scatter_layer = pdk.Layer(
          "ScatterplotLayer",
          data=df_rute_harian,
          get_position=["Longitude", "Latitude"],
          get_color=[0, 128, 255, 200],
          get_radius=50,
          pickable=True,
      )
      view_state = pdk.ViewState(
          latitude=center_lat, longitude=center_lon, zoom=13, pitch=40
      )
      r = pdk.Deck(
          layers=[path_layer, scatter_layer],
          initial_view_state=view_state,
          tooltip={
              "html": "<b>Warkop/LKK:</b> {Warkop_LKK}<br/><b>Waktu:</b>"
              " {Waktu}<br/><b>Brand:</b> {Brand_Rokok} ({Jumlah_Bungkus} bks)",
              "style": {"backgroundColor": "steelblue", "color": "white"},
          },
      )
      st.pydeck_chart(r)

  # Tombol Download Excel User
  output = BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_eval.to_excel(writer, index=False, sheet_name="Evaluasi Harian")
    df_user_rekap.drop(columns=["Tanggal"], errors="ignore").to_excel(
        writer, index=False, sheet_name="Detail Transaksi"
    )

  st.download_button(
      label=f"📥 Download Rekap Excel (.xlsx) - {st.session_state['user_spg']}",
      data=output.getvalue(),
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
