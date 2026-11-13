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
    page_title="Laporan SPG & Supervisi Mobile",
    page_icon="📍",
    layout="centered",
    initial_sidebar_state="auto",
)

# ====================================================
# CUSTOM CSS UNTUK UI MODERN & ADMIN PANEL GRID
# ====================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4f6f9;
        margin-bottom: 40px;
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
    .address-box {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 0.9rem;
        color: #334155;
        margin-top: 6px;
        margin-bottom: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# File database lokal & master
DB_FILE = "rekap_laporan_spg.csv"
DB_SUPERVISI_KONTAK_FILE = "rekap_kontak_supervisi.csv"
MASTER_BRAND_FILE = "master_brand_rokok.json"
MASTER_LOKASI_FILE = "Master WarkopLKK.xlsx"
MASTER_SPG_FILE = "master_nama_spg.json"
MASTER_TEAM_BRAND_FILE = "master_team_brand.json"
MASTER_PLAT_FILE = "master_plat_kendaraan.json"
JADWAL_SPG_FILE = "Jadwal SPG.xlsx"

EXPECTED_COLUMNS = [
    "Waktu",
    "Promotor",
    "Plat_Mobil",
    "Nama_SPG",
    "Kota_Kab",
    "Kecamatan",
    "Warkop_LKK",
    "Alamat_Warkop",
    "Brand_Rokok",
    "Nama_Konsumen",
    "Gender",
    "Range_Umur",
    "No_HP",
    "Instagram",
    "Jumlah_Bungkus",
    "Rokok_Asal_BUMO",
    "Latitude",
    "Longitude",
]

EXPECTED_SUPERVISI_COLUMNS = [
    "Waktu",
    "Promotor",
    "Plat_Mobil",
    "Kota_Kab",
    "Kecamatan",
    "Warkop_LKK",
    "Alamat_Warkop",
    "Jumlah_Kontak_Manual",
]


def load_database():
  if os.path.exists(DB_FILE):
    try:
      df = pd.read_csv(DB_FILE)
      if "Usia" in df.columns and "Range_Umur" not in df.columns:
        df = df.rename(columns={"Usia": "Range_Umur"})
      for col in EXPECTED_COLUMNS:
        if col not in df.columns:
          df[col] = "-"
      return df[EXPECTED_COLUMNS]
    except Exception:
      return pd.DataFrame(columns=EXPECTED_COLUMNS)
  return pd.DataFrame(columns=EXPECTED_COLUMNS)


def save_database(df):
  df.to_csv(DB_FILE, index=False)


def load_supervisi_database():
  if os.path.exists(DB_SUPERVISI_KONTAK_FILE):
    try:
      df = pd.read_csv(DB_SUPERVISI_KONTAK_FILE)
      for col in EXPECTED_SUPERVISI_COLUMNS:
        if col not in df.columns:
          df[col] = "-"
      return df[EXPECTED_SUPERVISI_COLUMNS]
    except Exception:
      return pd.DataFrame(columns=EXPECTED_SUPERVISI_COLUMNS)
  return pd.DataFrame(columns=EXPECTED_SUPERVISI_COLUMNS)


def save_supervisi_database(df):
  df.to_csv(DB_SUPERVISI_KONTAK_FILE, index=False)


# ====================================================
# MANAJEMEN MASTER DATA & PLAT KENDARAAN
# ====================================================
DEFAULT_BRANDS = [
    "D.Super 12",
    "D.76 Apel",
    "D.76 Apel Royal",
    "Black Matcha K12",
    "Djarum 76 Aksara",
]
DEFAULT_SPGS = ["Nanda", "Dewi", "Aci", "Ayu"]
DEFAULT_PLATS = ["L 1234 ABC", "L 5678 XYZ"]


def load_master_brands():
  if os.path.exists(MASTER_BRAND_FILE):
    try:
      with open(MASTER_BRAND_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return DEFAULT_BRANDS
  return DEFAULT_BRANDS


def save_master_brands(brands):
  with open(MASTER_BRAND_FILE, "w", encoding="utf-8") as f:
    json.dump(brands, f, ensure_ascii=False, indent=2)


def load_master_team_brands():
  default_teams = {f"Team SPG {i}": DEFAULT_BRANDS.copy() for i in range(1, 21)}
  if os.path.exists(MASTER_TEAM_BRAND_FILE):
    try:
      with open(MASTER_TEAM_BRAND_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        for i in range(1, 21):
          t_name = f"Team SPG {i}"
          if t_name not in data:
            data[t_name] = DEFAULT_BRANDS.copy()
        return data
    except Exception:
      return default_teams
  return default_teams


def save_master_team_brands(team_brands):
  with open(MASTER_TEAM_BRAND_FILE, "w", encoding="utf-8") as f:
    json.dump(team_brands, f, ensure_ascii=False, indent=2)


def load_master_plat_kendaraan():
  if os.path.exists(MASTER_PLAT_FILE):
    try:
      with open(MASTER_PLAT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
          return data
        elif isinstance(data, dict):
          return list(data.values())
    except Exception:
      return DEFAULT_PLATS
  return DEFAULT_PLATS


def save_master_plat_kendaraan(plat_list):
  with open(MASTER_PLAT_FILE, "w", encoding="utf-8") as f:
    json.dump(plat_list, f, ensure_ascii=False, indent=2)


def load_master_lokasi_excel():
  if os.path.exists(MASTER_LOKASI_FILE):
    try:
      df_excel = pd.read_excel(MASTER_LOKASI_FILE)
      df_excel.columns = [str(c).strip() for c in df_excel.columns]
      return df_excel
    except Exception as e:
      st.error(f"Gagal membaca file Excel {MASTER_LOKASI_FILE}: {e}")
      return pd.DataFrame(columns=["Kecamatan", "Warkop_LKK"])
  else:
    return pd.DataFrame(
        columns=["Kecamatan", "Warkop_LKK"],
        data=[
            ["Kecamatan Default", "Warkop Cak No"],
            ["Kecamatan Default", "Warkop Pitoe"],
        ],
    )


def save_master_lokasi_excel(df_excel):
  try:
    df_excel.to_excel(MASTER_LOKASI_FILE, index=False)
    return True
  except Exception as e:
    st.error(f"Gagal menyimpan file Excel: {e}")
    return False


def load_jadwal_spg():
  if os.path.exists(JADWAL_SPG_FILE):
    try:
      df_jadwal = pd.read_excel(JADWAL_SPG_FILE)
      df_jadwal.columns = [str(c).strip() for c in df_jadwal.columns]
      return df_jadwal
    except Exception as e:
      st.error(f"Gagal membaca file Jadwal SPG {JADWAL_SPG_FILE}: {e}")
      return pd.DataFrame()
  return pd.DataFrame()


def load_master_spgs():
  if os.path.exists(MASTER_SPG_FILE):
    try:
      with open(MASTER_SPG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return DEFAULT_SPGS
  return DEFAULT_SPGS


def save_master_spgs(spgs):
  with open(MASTER_SPG_FILE, "w", encoding="utf-8") as f:
    json.dump(spgs, f, ensure_ascii=False, indent=2)


def get_schedule_info_for_team(team_name):
  df_j = load_jadwal_spg()
  if df_j.empty:
    return False, "Tidak Ada Jadwal Team Tersebut Untuk Hari Ini", "Surabaya"
  
  kota_col = next((c for c in df_j.columns if "kota" in c.lower()), None)
  if not kota_col:
    return False, "Tidak Ada Jadwal Team Tersebut Untuk Hari Ini", "Surabaya"
    
  today_date = datetime.now().date()
  today_col = None
  for c in df_j.columns:
    try:
      parsed_dt = pd.to_datetime(c).date()
      if parsed_dt == today_date:
        today_col = c
        break
    except Exception:
      continue
      
  if not today_col:
    return False, "Tidak Ada Jadwal Team Tersebut Untuk Hari Ini", "Surabaya"
    
  team_clean = team_name.strip().lower()
  team_digit = ''.join(filter(str.isdigit, team_clean))
  
  found_kota = None
  for _, row in df_j.iterrows():
    val_cell = str(row[today_col]).strip()
    if val_cell and val_cell.lower() != "nan" and val_cell != "-":
      val_lower = val_cell.lower()
      cell_digit = ''.join(filter(str.isdigit, val_lower))
      if team_clean == val_lower or (team_digit and cell_digit and team_digit == cell_digit and len(team_digit) == len(cell_digit)):
        temp_kota = str(row[kota_col]).strip()
        if temp_kota:
          found_kota = temp_kota
          break
          
  if found_kota:
    return True, "", found_kota
  else:
    return False, "Tidak Ada Jadwal Team Tersebut Untuk Hari Ini", "Surabaya"


# ====================================================
# ATURAN TARGET PER BRAND
# ====================================================
TARGET_RULES = {
    "Black Matcha K12": {"target_spg": 50, "target_team": 100},
    "D.Super 12": {"target_spg": 40, "target_team": 80},
    "D.76 Apel Royal": {"target_spg": 40, "target_team": 80},
    "D.76 Apel": {"target_spg": 30, "target_team": 60},
    "Djarum 76 Aksara": {"target_spg": 30, "target_team": 60},
}


def cek_status_target_spg(brand, omset_spg):
  rule = TARGET_RULES.get(brand, {"target_spg": 25, "target_team": 50})
  return "Achieved" if omset_spg >= rule["target_spg"] else "Not Achieved"


def cek_status_target_team(brand, omset_team):
  rule = TARGET_RULES.get(brand, {"target_spg": 25, "target_team": 50})
  return "Achieved" if omset_team >= rule["target_team"] else "Not Achieved"


def style_status_target(val):
  if val == "Not Achieved":
    return "color: #d32f2f; font-weight: bold;"
  elif val == "Achieved":
    return "color: #16a34a; font-weight: bold;"
  return ""


# Fungsi Indikator Visual Prosentase Pencapaian Target yang Menarik
def format_pencapaian_visual(pct):
  if pd.isna(pct):
    return "⏳ 0% (Belum Ada Target)"
  if pct >= 100:
    return f"🟢 **{pct:.1f}%** (Target Tercapai)"
  elif pct >= 75:
    return f"🟡 **{pct:.1f}%** (Mendekati Target)"
  else:
    return f"🔴 **{pct:.1f}%** (Belum Tercapai)"


# ====================================================
# INISIALISASI SESSION STATE & CALLBACK USER CHANGE
# ====================================================
def reset_session_on_user_change():
  st.session_state["logged_in"] = False
  st.session_state["user_spg"] = st.session_state.get("selected_team_login", "")
  st.session_state["draft_konsumen"] = ""
  st.session_state["draft_nohp"] = ""
  st.session_state["draft_ig"] = ""
  st.session_state["draft_bungkus"] = 1
  st.session_state["draft_bumo"] = ""


if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
if "user_spg" not in st.session_state:
  st.session_state["user_spg"] = ""
if "plat_mobil" not in st.session_state:
  st.session_state["plat_mobil"] = ""
if "kota_kab" not in st.session_state:
  st.session_state["kota_kab"] = ""
if "login_mode" not in st.session_state:
  st.session_state["login_mode"] = "SPG"
if "admin_logged_in" not in st.session_state:
  st.session_state["admin_logged_in"] = False
if "admin_view" not in st.session_state:
  st.session_state["admin_view"] = "Dashboard"

if "draft_konsumen" not in st.session_state:
  st.session_state["draft_konsumen"] = ""
if "draft_nohp" not in st.session_state:
  st.session_state["draft_nohp"] = ""
if "draft_ig" not in st.session_state:
  st.session_state["draft_ig"] = ""
if "draft_bungkus" not in st.session_state:
  st.session_state["draft_bungkus"] = 1
if "draft_bumo" not in st.session_state:
  st.session_state["draft_bumo"] = ""

# ====================================================
# SIDEBAR: LOGIN ADMIN DI HALAMAN UTAMA
# ====================================================
if not st.session_state["logged_in"]:
  with st.sidebar:
    st.markdown("### 🔐 Menu Admin / Supervisor")
    st.markdown("Akses dashboard terpusat, analitik, rekap, shift, absensi, dan pengaturan master data.")

    if not st.session_state["admin_logged_in"]:
      with st.form("form_admin_login"):
        pass_input = st.text_input("Password Admin", type="password")
        btn_pass = st.form_submit_button("Buka Dashboard Admin")

        if btn_pass:
          if pass_input == "admin123":
            st.session_state["admin_logged_in"] = True
            st.session_state["admin_view"] = "Dashboard"
            st.success("✅ Berhasil masuk sebagai Admin!")
            st.rerun()
          else:
            st.error("❌ Password salah!")
    else:
      st.success("🟢 Status: Admin Aktif")
      st.markdown("---")
      if st.button("🏠 Dashboard Utama Admin", use_container_width=True, type="primary"):
        st.session_state["admin_view"] = "Dashboard"
        st.rerun()
      if st.button("⏱️ Aktivitas & Harian", use_container_width=True):
        st.session_state["admin_view"] = "Hari_Ini"
        st.rerun()
      if st.button("👥 Shift & Jadwal Team", use_container_width=True):
        st.session_state["admin_view"] = "Shift"
        st.rerun()
      if st.button("📊 Rekapitulasi & Unduh", use_container_width=True):
        st.session_state["admin_view"] = "Rekap"
        st.rerun()
      if st.button("📋 Absensi Lapangan", use_container_width=True):
        st.session_state["admin_view"] = "Absensi"
        st.rerun()
      if st.button("📈 Analitik All User", use_container_width=True):
        st.session_state["admin_view"] = "Analitik"
        st.rerun()
      if st.button("🗺️ Peta Rute All User", use_container_width=True):
        st.session_state["admin_view"] = "Peta_Rute"
        st.rerun()

      st.markdown("---")
      st.markdown("#### 📦 Master Data")
      if st.button("👥 Master Team & Brand", use_container_width=True):
        st.session_state["admin_view"] = "Master_Team"
        st.rerun()
      if st.button("🚗 Master Plat Kendaraan", use_container_width=True):
        st.session_state["admin_view"] = "Master_Plat"
        st.rerun()
      if st.button("👩‍💼 Master Nama SPG", use_container_width=True):
        st.session_state["admin_view"] = "Master_SPG"
        st.rerun()
      if st.button("🚬 Master Merek Rokok", use_container_width=True):
        st.session_state["admin_view"] = "Master_Brand"
        st.rerun()
      if st.button("📍 Master Lokasi Warkop", use_container_width=True):
        st.session_state["admin_view"] = "Master_Lokasi"
        st.rerun()

      st.markdown("---")
      if st.button("🔒 Keluar dari Mode Admin", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()

# ====================================================
# TAMPILAN PANEL ADMIN / SUPERVISOR
# ====================================================
if not st.session_state["logged_in"] and st.session_state["admin_logged_in"]:

  # --- MENU: HARI INI (AKTIVITAS & KUNJUNGAN) ---
  if st.session_state["admin_view"] == "Hari_Ini":
    st.markdown("## ⏱️ Aktivitas & Kunjungan Lapangan Hari Ini")
    st.caption("Pantau aktivitas harian seluruh team dan status kunjungan secara real-time.")
    df_today_all = load_database()
    if not df_today_all.empty:
      df_today_all["Waktu_Dt"] = pd.to_datetime(df_today_all["Waktu"], errors="coerce")
      df_today_all["Tanggal"] = df_today_all["Waktu_Dt"].dt.date
      tgl_hari_ini = datetime.now().date()
      df_hini = df_today_all[df_today_all["Tanggal"] == tgl_hari_ini]
      if not df_hini.empty:
        st.dataframe(df_hini.drop(columns=["Waktu_Dt", "Tanggal"], errors="ignore"), use_container_width=True)
      else:
        st.info(f"Belum ada transaksi tercatat pada hari ini ({tgl_hari_ini}). Menampilkan seluruh data:")
        st.dataframe(df_today_all.drop(columns=["Waktu_Dt", "Tanggal"], errors="ignore"), use_container_width=True)
    else:
      st.info("Belum ada data transaksi tersimpan di sistem.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- MENU: SHIFT & JADWAL TEAM ---
  elif st.session_state["admin_view"] == "Shift":
    st.markdown("## 👥 Informasi Shift & Penugasan Team")
    st.caption("Kelola dan tinjau jadwal penugasan master seluruh team SPG.")
    df_jadwal_info = load_jadwal_spg()
    if not df_jadwal_info.empty:
      st.markdown("#### 📅 Jadwal Penugasan Master (Jadwal SPG.xlsx)")
      st.dataframe(df_jadwal_info, use_container_width=True)
    else:
      st.warning("File master Jadwal SPG.xlsx belum tersedia atau kosong.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- MENU: REKAPITULASI & UNDUH LAPORAN ---
  elif st.session_state["admin_view"] == "Rekap":
    st.markdown("## 📊 Rekapitulasi & Unduh Laporan Lapangan")
    st.caption("Pusat unduh rekapitulasi data dan laporan performa seluruh team.")
    df_rekap_all = load_database()
    if not df_rekap_all.empty:
      st.dataframe(df_rekap_all, use_container_width=True)
      output_rk = BytesIO()
      with pd.ExcelWriter(output_rk, engine="openpyxl") as writer:
        df_rekap_all.to_excel(writer, index=False, sheet_name="Rekap Semua User")
      st.download_button(
          label="📥 Download Rekap Semua Data Excel (.xlsx)",
          data=output_rk.getvalue(),
          file_name=f"rekap_all_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          type="primary"
      )
    else:
      st.info("Belum ada data tersimpan untuk diunduh.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- MENU: ABSENSI LAPANGAN ---
  elif st.session_state["admin_view"] == "Absensi":
    st.markdown("## 📋 Rekap Kehadiran & Absensi Lapangan")
    st.caption("Pantau laporan kehadiran operasional harian seluruh team di titik lokasi tugas.")
    df_abs_all = load_database()
    if not df_abs_all.empty:
      df_abs_summary = df_abs_all.groupby(["Promotor", "Kota_Kab"]).agg(
          Total_Laporan=("Nama_Konsumen", "count"),
          Warkop_Dikunjungi=("Warkop_LKK", "nunique")
      ).reset_index()
      st.dataframe(df_abs_summary, use_container_width=True)
    else:
      st.info("Belum ada data kehadiran/laporan tercatat.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER PLAT KENDARAAN ---
  elif st.session_state["admin_view"] == "Master_Plat":
    st.markdown("## 🚗 Master Data: Plat Nomor Kendaraan Operasional")
    plat_list = load_master_plat_kendaraan()

    with st.form("form_tambah_plat"):
      st.markdown("#### Tambah Plat Nomor Kendaraan Baru")
      new_plat_input = st.text_input("Plat Nomor Kendaraan", placeholder="Contoh: L 1234 ABC")
      btn_add_plat = st.form_submit_button("➕ Tambah Plat Kendaraan")

      if btn_add_plat:
        p_clean = new_plat_input.strip().upper()
        if p_clean:
          if p_clean not in plat_list:
            plat_list.append(p_clean)
            save_master_plat_kendaraan(plat_list)
            st.success(f"✅ Plat kendaraan '{p_clean}' berhasil ditambahkan!")
            st.rerun()
          else:
            st.warning("Plat nomor kendaraan tersebut sudah ada dalam daftar.")
        else:
            st.warning("Mohon masukkan nomor plat kendaraan.")

    st.markdown("---")
    for idx, p in enumerate(plat_list):
      col_p1, col_p2 = st.columns([0.8, 0.2])
      with col_p1:
        st.write(f"**{idx+1}.** `{p}`")
      with col_p2:
        if st.button("🗑️ Hapus", key=f"del_plat_{idx}"):
          plat_list.pop(idx)
          save_master_plat_kendaraan(plat_list)
          st.success("Plat kendaraan berhasil dihapus!")
          st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER TEAM & BRAND ROKOK ---
  elif st.session_state["admin_view"] == "Master_Team":
    st.markdown("## 👥 Master Data: Team 1 - 20 & Alokasi Brand Rokok")
    team_brands_dict = load_master_team_brands()
    all_available_brands = load_master_brands()

    selected_team_config = st.selectbox(
        "Pilih Team SPG untuk Konfigurasi Brand",
        options=[f"Team SPG {i}" for i in range(1, 21)]
    )

    current_assigned_brands = team_brands_dict.get(selected_team_config, all_available_brands)

    with st.form("form_config_team_brand"):
      st.markdown(f"#### Alokasi Merek untuk `{selected_team_config}`")
      selected_brands_input = st.multiselect(
          "Pilih Brand Rokok yang Diizinkan",
          options=all_available_brands,
          default=[b for b in current_assigned_brands if b in all_available_brands]
      )
      btn_save_team_brand = st.form_submit_button("💾 Simpan Alokasi Brand Team")

      if btn_save_team_brand:
        team_brands_dict[selected_team_config] = selected_brands_input
        save_master_team_brands(team_brands_dict)
        st.success(f"✅ Alokasi brand rokok untuk **{selected_team_config}** berhasil disimpan!")
        st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER NAMA SPG ---
  elif st.session_state["admin_view"] == "Master_SPG":
    st.markdown("## 👩‍💼 Master Data: Nama SPG")
    current_spgs = load_master_spgs()

    with st.form("form_tambah_spg"):
      new_spg_name = st.text_input("Nama SPG Baru", placeholder="Contoh: Siska")
      btn_add_spg = st.form_submit_button("➕ Tambah Nama SPG")
      if btn_add_spg:
        spg_clean = new_spg_name.strip()
        if spg_clean:
          if spg_clean not in current_spgs:
            current_spgs.append(spg_clean)
            save_master_spgs(current_spgs)
            st.success(f"✅ Nama SPG '{spg_clean}' berhasil ditambahkan!")
            st.rerun()

    st.markdown("---")
    for idx, s in enumerate(current_spgs):
      col_s1, col_s2 = st.columns([0.8, 0.2])
      with col_s1:
        st.write(f"**{idx+1}.** {s}")
      with col_s2:
        if st.button("🗑️ Hapus", key=f"del_spg_{idx}"):
          current_spgs.pop(idx)
          save_master_spgs(current_spgs)
          st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER MEREK ROKOK ---
  elif st.session_state["admin_view"] == "Master_Brand":
    st.markdown("## 🚬 Master Data: Merek Rokok & Target")
    current_brands = load_master_brands()

    with st.form("form_tambah_brand"):
      new_brand_name = st.text_input("Nama Merek Rokok Baru", placeholder="Contoh: Djarum Super Extra")
      t_spg = st.number_input("Target per SPG (Bungkus)", min_value=1, value=30, step=1)
      t_team = st.number_input("Target per Team (Bungkus)", min_value=1, value=60, step=1)
      btn_add_brand = st.form_submit_button("➕ Tambah Merek Rokok")
      if btn_add_brand:
        b_clean = new_brand_name.strip()
        if b_clean:
          if b_clean not in current_brands:
            current_brands.append(b_clean)
            save_master_brands(current_brands)
            TARGET_RULES[b_clean] = {"target_spg": int(t_spg), "target_team": int(t_team)}
            st.success(f"✅ Merek rokok '{b_clean}' berhasil ditambahkan!")
            st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER LOKASI WARKOP ---
  elif st.session_state["admin_view"] == "Master_Lokasi":
    st.markdown("## 📍 Master Data: Lokasi Warkop / LKK (Excel)")
    df_lokasi_excel = load_master_lokasi_excel()

    with st.form("form_tambah_lokasi_excel"):
      col_kec_input = st.text_input("Kecamatan", placeholder="Contoh: Tegalsari")
      col_warkop_input = st.text_input("Nama Warkop / LKK", placeholder="Contoh: Warkop Barokah")
      col_alamat_input = st.text_input("Alamat Warkop", placeholder="Contoh: Jl. Ngagel Tirto No. 10")
      btn_add_excel = st.form_submit_button("➕ Tambah & Simpan ke Excel")

      if btn_add_excel:
        if col_kec_input.strip() and col_warkop_input.strip():
          new_row = {"Kecamatan": col_kec_input.strip(), "Warkop_LKK": col_warkop_input.strip(), "Alamat_Warkop": col_alamat_input.strip() if col_alamat_input else "-"}
          df_lokasi_excel = pd.concat([df_lokasi_excel, pd.DataFrame([new_row])], ignore_index=True)
          if save_master_lokasi_excel(df_lokasi_excel):
            st.success("✅ Warkop berhasil ditambahkan!")
            st.rerun()

    st.markdown("---")
    if not df_lokasi_excel.empty:
      edited_df = st.data_editor(df_lokasi_excel, use_container_width=True, key="editor_excel_warkop")
      if st.button("💾 Simpan Perubahan Edit Tabel"):
        if save_master_lokasi_excel(edited_df):
          st.success("✅ Perubahan berhasil disimpan!")
          st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN ANALITIK ---
  elif st.session_state["admin_view"] == "Analitik":
    st.markdown("## 📊 Analitik & Rekapitulasi All User")
    df_all_users = load_database()
    if not df_all_users.empty:
      df_all_users["Jumlah_Bungkus"] = pd.to_numeric(df_all_users["Jumlah_Bungkus"], errors="coerce").fillna(0)
      c1, c2 = st.columns(2)
      with c1:
        st.markdown("#### 👥 Demografi Konsumen (Gender)")
        st.bar_chart(df_all_users["Gender"].value_counts())
      with c2:
        st.markdown("#### 📊 Sebaran Range Umur")
        if "Range_Umur" in df_all_users.columns:
          st.bar_chart(df_all_users["Range_Umur"].value_counts())
    else:
      st.info("Belum ada data analitik.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN PETA RUTE ---
  elif st.session_state["admin_view"] == "Peta_Rute":
    st.markdown("## 🗺️ Visualisasi Peta Rute Perjalanan (All User)")
    df_peta_all = load_database()
    if not df_peta_all.empty and "Latitude" in df_peta_all.columns:
      df_peta_all = df_peta_all.dropna(subset=["Latitude", "Longitude"])
      if not df_peta_all.empty:
        center_lat = df_peta_all["Latitude"].mean()
        center_lon = df_peta_all["Longitude"].mean()
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_peta_all,
            get_position=["Longitude", "Latitude"],
            get_color=[0, 128, 255, 200],
            get_radius=60,
            pickable=True,
        )
        st.pydeck_chart(pdk.Deck(layers=[scatter_layer], initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=12, pitch=35)))
    else:
      st.info("Belum ada data koordinat GPS.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard Admin"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # ====================================================
  # DASHBOARD UTAMA ADMIN
  # ====================================================
  st.markdown("## 📊 Panel Menu Admin & Supervisor")
  st.caption("Pusat kendali operasional, pemantauan, dan manajemen data lapangan.")

  st.markdown("#### 🧭 Menu Utama Monitoring & Operasional")
  col_mn1, col_mn2, col_mn3, col_mn4 = st.columns(4)
  with col_mn1:
    if st.button("⏱️ Hari Ini\n(Aktivitas)", use_container_width=True):
      st.session_state["admin_view"] = "Hari_Ini"
      st.rerun()
  with col_mn2:
    if st.button("👥 Shift\n(Jadwal)", use_container_width=True):
      st.session_state["admin_view"] = "Shift"
      st.rerun()
  with col_mn3:
    if st.button("📊 Rekap\n(Unduh Laporan)", use_container_width=True):
      st.session_state["admin_view"] = "Rekap"
      st.rerun()
  with col_mn4:
    if st.button("📋 Absensi\n(Kehadiran)", use_container_width=True):
      st.session_state["admin_view"] = "Absensi"
      st.rerun()

  st.markdown("---")
  st.markdown("#### 📦 Master Data & Pengaturan")
  col_m1, col_m2 = st.columns(2)
  with col_m1:
    if st.button("👥 Master Team & Brand", use_container_width=True):
      st.session_state["admin_view"] = "Master_Team"
      st.rerun()
    if st.button("👩‍💼 Master Nama SPG", use_container_width=True):
      st.session_state["admin_view"] = "Master_SPG"
      st.rerun()
    if st.button("📍 Master Lokasi Warkop", use_container_width=True):
      st.session_state["admin_view"] = "Master_Lokasi"
      st.rerun()
  with col_m2:
    if st.button("🚗 Master Plat Kendaraan", use_container_width=True):
      st.session_state["admin_view"] = "Master_Plat"
      st.rerun()
    if st.button("🚬 Master Merek Rokok & Target", use_container_width=True):
      st.session_state["admin_view"] = "Master_Brand"
      st.rerun()
    if st.button("🚪 Keluar dari Mode Admin", use_container_width=True):
      st.session_state["admin_logged_in"] = False
      st.rerun()

  st.markdown("---")
  st.markdown("#### 📈 Analitik & Pemetaan")
  col_a1, col_a2 = st.columns(2)
  with col_a1:
    if st.button("📊 Analitik & Rekap All", use_container_width=True):
      st.session_state["admin_view"] = "Analitik"
      st.rerun()
  with col_a2:
    if st.button("🗺️ Peta Rute All User", use_container_width=True):
      st.session_state["admin_view"] = "Peta_Rute"
      st.rerun()

  st.markdown("---")
  st.markdown("#### 🌐 Ringkasan Cepat Data Masuk (All User)")

  df_all_users = load_database()
  df_all_supervisi = load_supervisi_database()

  if not df_all_users.empty:
    df_all_users["Waktu_Dt"] = pd.to_datetime(df_all_users["Waktu"], errors="coerce")
    df_all_users["Tanggal"] = df_all_users["Waktu_Dt"].dt.date
    df_all_users["Jumlah_Bungkus"] = pd.to_numeric(df_all_users["Jumlah_Bungkus"], errors="coerce").fillna(0)

    total_omset = int(df_all_users["Jumlah_Bungkus"].sum())
    total_konsumen = len(df_all_users)
    total_warkop = df_all_users["Warkop_LKK"].nunique()
    total_team_aktif = df_all_users["Promotor"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
      st.markdown(f'<div class="kpi-card"><div class="kpi-value">{total_omset:,}</div><div class="kpi-label">Total Omset</div></div>', unsafe_allow_html=True)
    with k2:
      st.markdown(f'<div class="kpi-card"><div class="kpi-value">{total_konsumen:,}</div><div class="kpi-label">Konsumen Beli</div></div>', unsafe_allow_html=True)
    with k3:
      st.markdown(f'<div class="kpi-card"><div class="kpi-value">{total_warkop:,}</div><div class="kpi-label">Titik Warkop</div></div>', unsafe_allow_html=True)
    with k4:
      st.markdown(f'<div class="kpi-card"><div class="kpi-value">{total_team_aktif}</div><div class="kpi-label">Team Aktif</div></div>', unsafe_allow_html=True)
  else:
    st.info("Belum ada data laporan masuk.")

  # ====================================================
  # REPORT REKAPITULASI COMBINE PER TITIK LKK (DENGAN TARGET & % PENCAPAIAN VISUAL)
  # ====================================================
  st.markdown("---")
  st.markdown("#### 📊 Rekapitulasi Combine Per Titik LKK (All Team)")
  st.caption("Gabungan data jumlah kontak manual Supervisi, penjualan SPG, Target Penjualan, serta Indikator % Pencapaian per Titik Warkop/LKK.")

  if not df_all_supervisi.empty:
    df_all_supervisi["Waktu_Dt"] = pd.to_datetime(df_all_supervisi["Waktu"], errors="coerce")
    df_all_supervisi["Tanggal"] = df_all_supervisi["Waktu_Dt"].dt.date
    df_all_supervisi["Jumlah_Kontak_Manual"] = pd.to_numeric(df_all_supervisi["Jumlah_Kontak_Manual"], errors="coerce").fillna(0).astype(int)

  teams_spg = df_all_users["Promotor"].dropna().unique().tolist() if not df_all_users.empty else []
  teams_sup = df_all_supervisi["Promotor"].dropna().unique().tolist() if not df_all_supervisi.empty else []
  all_teams_lkk = ["Semua Team"] + sorted(list(set(teams_spg + teams_sup)))

  filter_team_lkk = st.selectbox(
      "Filter Team pada Rekapitulasi Combine LKK:",
      options=all_teams_lkk,
      key="admin_filter_team_lkk"
  )

  df_spg_lkk_filtered = df_all_users.copy()
  df_sup_lkk_filtered = df_all_supervisi.copy()

  if filter_team_lkk != "Semua Team":
    if not df_spg_lkk_filtered.empty:
      df_spg_lkk_filtered = df_spg_lkk_filtered[df_spg_lkk_filtered["Promotor"] == filter_team_lkk]
    if not df_sup_lkk_filtered.empty:
      df_sup_lkk_filtered = df_sup_lkk_filtered[df_sup_lkk_filtered["Promotor"] == filter_team_lkk]

  df_rekap_spg_admin = pd.DataFrame(
      columns=["Promotor", "Kota_Kab", "Kecamatan", "Warkop_LKK", "Alamat_Warkop", "SPG_Bertugas", "Konsumen_Beli", "Total_Omset_Bungkus", "Brand_Rokok"]
  )
  if not df_spg_lkk_filtered.empty:
    df_rekap_spg_admin = (
        df_spg_lkk_filtered.groupby(["Promotor", "Kota_Kab", "Kecamatan", "Warkop_LKK", "Alamat_Warkop"])
        .agg(
            SPG_Bertugas=("Nama_SPG", lambda x: ", ".join(x.dropna().unique())),
            Konsumen_Beli=("Nama_Konsumen", "count"),
            Total_Omset_Bungkus=("Jumlah_Bungkus", "sum"),
            Brand_Rokok=("Brand_Rokok", lambda x: x.iloc[0] if not x.empty else "D.Super 12")
        )
        .reset_index()
    )

  df_rekap_sup_admin = pd.DataFrame(
      columns=["Promotor", "Kota_Kab", "Kecamatan", "Warkop_LKK", "Plat_Mobil_Supervisi", "Jumlah_Kontak_Manual"]
  )
  if not df_sup_lkk_filtered.empty:
    df_rekap_sup_admin = (
        df_sup_lkk_filtered.groupby(["Promotor", "Kota_Kab", "Kecamatan", "Warkop_LKK"])
        .agg(
            Plat_Mobil_Supervisi=("Plat_Mobil", lambda x: ", ".join([str(v) for v in x.dropna().unique() if str(v) != "-"])),
            Jumlah_Kontak_Manual=("Jumlah_Kontak_Manual", "sum")
        )
        .reset_index()
    )

  if not df_rekap_spg_admin.empty or not df_rekap_sup_admin.empty:
    if df_rekap_spg_admin.empty:
      df_combine_admin = df_rekap_sup_admin.copy()
      df_combine_admin["Alamat_Warkop"] = "-"
      df_combine_admin["SPG_Bertugas"] = "-"
      df_combine_admin["Konsumen_Beli"] = 0
      df_combine_admin["Total_Omset_Bungkus"] = 0
      df_combine_admin["Brand_Rokok"] = "D.Super 12"
    elif df_rekap_sup_admin.empty:
      df_combine_admin = df_rekap_spg_admin.copy()
      df_combine_admin["Plat_Mobil_Supervisi"] = "-"
      df_combine_admin["Jumlah_Kontak_Manual"] = 0
    else:
      df_combine_admin = pd.merge(
          df_rekap_spg_admin,
          df_rekap_sup_admin,
          on=["Promotor", "Kota_Kab", "Kecamatan", "Warkop_LKK"],
          how="outer"
      ).fillna({
          "Alamat_Warkop": "-",
          "SPG_Bertugas": "-",
          "Plat_Mobil_Supervisi": "-",
          "Jumlah_Kontak_Manual": 0,
          "Konsumen_Beli": 0,
          "Total_Omset_Bungkus": 0,
          "Brand_Rokok": "D.Super 12"
      })

    df_combine_admin["Plat_Mobil_Supervisi"] = df_combine_admin["Plat_Mobil_Supervisi"].replace("", "-")
    df_combine_admin["Jumlah_Kontak_Manual"] = df_combine_admin["Jumlah_Kontak_Manual"].astype(int)
    df_combine_admin["Konsumen_Beli"] = df_combine_admin["Konsumen_Beli"].astype(int)
    df_combine_admin["Total_Omset_Bungkus"] = df_combine_admin["Total_Omset_Bungkus"].astype(int)

    # Menghitung Target Penjualan per Titik berdasarkan Aturan Brand (Target Team)
    def get_target_titik(row):
      brand = row.get("Brand_Rokok", "D.Super 12")
      rule = TARGET_RULES.get(brand, {"target_team": 50})
      return rule["target_team"]

    df_combine_admin["Target_Penjualan"] = df_combine_admin.apply(get_target_titik, axis=1)

    # Menghitung Persentase Pencapaian Target (% Achievement)
    df_combine_admin["Persentase_Pencapaian_Num"] = (
        (df_combine_admin["Total_Omset_Bungkus"] / df_combine_admin["Target_Penjualan"]) * 100
    ).round(1)

    # Menggunakan Indikator Visual Prosentase yang Menarik
    df_combine_admin["Status_%_Pencapaian"] = df_combine_admin["Persentase_Pencapaian_Num"].apply(format_pencapaian_visual)

    cols_combine_order = [
        "Promotor",
        "Plat_Mobil_Supervisi",
        "Kota_Kab",
        "Kecamatan",
        "Warkop_LKK",
        "Alamat_Warkop",
        "SPG_Bertugas",
        "Jumlah_Kontak_Manual",
        "Konsumen_Beli",
        "Target_Penjualan",
        "Total_Omset_Bungkus",
        "Status_%_Pencapaian",
    ]
    df_combine_admin = df_combine_admin[cols_combine_order].sort_values(
        by=["Total_Omset_Bungkus", "Jumlah_Kontak_Manual"], ascending=False
    )

    st.dataframe(df_combine_admin.drop(columns=["Persentase_Pencapaian_Num"], errors="ignore"), use_container_width=True)

    output_lkk = BytesIO()
    with pd.ExcelWriter(output_lkk, engine="openpyxl") as writer:
      df_combine_admin.drop(columns=["Persentase_Pencapaian_Num"], errors="ignore").to_excel(
          writer, index=False, sheet_name="Rekap Combine LKK"
      )
      if not df_all_supervisi.empty:
        df_all_supervisi.drop(columns=["Waktu_Dt", "Tanggal"], errors="ignore").to_excel(
            writer, index=False, sheet_name="Log Kontak Supervisi"
        )

    st.download_button(
        label="📥 Download Rekapitulasi Combine Per Titik LKK (.xlsx)",
        data=output_lkk.getvalue(),
        file_name=f"rekap_combine_lkk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_dl_combine_lkk_admin",
    )
  else:
    st.info("Belum ada data rekapitulasi gabungan LKK yang tersedia.")

  st.stop()
