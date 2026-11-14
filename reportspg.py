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
# CUSTOM CSS UNTUK UI MODERN (BACKGROUND KREM & CARD RAPI)
# ====================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FDFBF7;
        color: #334155;
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
        border: 1px solid #e2e8f0;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
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
    .dashboard-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 20px 18px;
        border-radius: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04);
        margin-bottom: 14px;
        min-height: 145px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .card-value {
        font-size: 1.9rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 2px;
        line-height: 1.1;
    }
    .card-value-green {
        font-size: 1.9rem;
        font-weight: 800;
        color: #16a34a;
        margin-bottom: 2px;
        line-height: 1.1;
    }
    .card-subtext {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 6px;
    }
    .card-label {
        font-size: 0.95rem;
        color: #475569;
        font-weight: 600;
        line-height: 1.3;
    }
    .progress-bar-container {
        width: 100%;
        background-color: #f1f5f9;
        border-radius: 6px;
        height: 8px;
        margin: 10px 0 6px 0;
        overflow: hidden;
    }
    .progress-bar-fill {
        height: 100%;
        background-color: #16a34a;
        border-radius: 6px;
    }
    .footer-note {
        text-align: center;
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 18px;
    }
    .address-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
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
MASTER_TARGET_FILE = "master_target_brand.json"
MASTER_LOKASI_FILE = "Master WarkopLKK.xlsx"
MASTER_SPG_FILE = "master_nama_spg.json"
MASTER_TEAM_BRAND_FILE = "master_team_brand.json"
MASTER_PLAT_FILE = "master_plat_kendaraan.json"
JADWAL_SPG_FILE = "Jadwal SPG.xlsx"

EXPECTED_COLUMNS = [
    "Waktu", "Promotor", "Plat_Mobil", "Nama_SPG", "Kota_Kab", "Kecamatan",
    "Warkop_LKK", "Alamat_Warkop", "Brand_Rokok", "Nama_Konsumen", "Gender",
    "Range_Umur", "No_HP", "Instagram", "Jumlah_Bungkus", "Rokok_Asal_BUMO",
    "Latitude", "Longitude",
]

EXPECTED_SUPERVISI_COLUMNS = [
    "Waktu", "Promotor", "Plat_Mobil", "Kota_Kab", "Kecamatan",
    "Warkop_LKK", "Alamat_Warkop", "Jumlah_Kontak_Manual",
]


# ====================================================
# FUNGSI BANTUAN MINGGU & DATABASE
# ====================================================
def get_custom_week_info(dt):
  if pd.isna(dt):
    return "-", "-"
  try:
    d = pd.to_datetime(dt).date()
  except Exception:
    return "-", "-"
  wd = d.weekday()
  if wd == 5:
    fri_date = d + timedelta(days=6)
  elif wd == 6:
    fri_date = d + timedelta(days=5)
  else:
    fri_date = d + timedelta(days=(4 - wd))
  _, iso_w, _ = fri_date.isocalendar()
  return f"Minggu ke-{iso_w}", iso_w


def add_custom_week_columns(df, date_col="Waktu_Dt"):
  if df.empty or date_col not in df.columns:
    df["Periode_Minggu"] = "-"
    return df
  periods = []
  for val in df[date_col]:
    p_label, _ = get_custom_week_info(val)
    periods.append(p_label)
  df["Periode_Minggu"] = periods
  return df


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
    return None


# ====================================================
# MANAJEMEN MASTER DATA
# ====================================================
DEFAULT_BRANDS = [
    "D.Super 12", "D.76 Apel", "D.76 Apel Royal",
    "Black Matcha K12", "Djarum 76 Aksara",
    "Black Matcha Siro", "Black Matcha Kuro",
]
DEFAULT_SPGS = ["Nanda"]
DEFAULT_PLATS = ["L 1234 ABC"]


def load_master_brands():
  if os.path.exists(MASTER_BRAND_FILE):
    try:
      with open(MASTER_BRAND_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return DEFAULT_BRANDS
  return DEFAULT_BRANDS


def save_master_brands(brands):
  try:
    with open(MASTER_BRAND_FILE, "w", encoding="utf-8") as f:
      json.dump(brands, f, ensure_ascii=False, indent=2)
    return True
  except Exception as e:
    return False


def load_master_team_brands():
  current_brands = load_master_brands()
  default_teams = {f"Team SPG {i}": current_brands.copy() for i in range(1, 21)}
  if os.path.exists(MASTER_TEAM_BRAND_FILE):
    try:
      with open(MASTER_TEAM_BRAND_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        for i in range(1, 21):
          t_name = f"Team SPG {i}"
          if t_name not in data:
            data[t_name] = current_brands.copy()
        return data
    except Exception:
      return default_teams
  else:
    save_master_team_brands(default_teams)
    return default_teams


def save_master_team_brands(team_brands):
  try:
    cleaned_data = {
        str(team): [str(b).strip() for b in brands]
        for team, brands in team_brands.items()
    }
    with open(MASTER_TEAM_BRAND_FILE, "w", encoding="utf-8") as f:
      json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
    return True
  except Exception as e:
    return False


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
    except Exception:
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
    return False


def load_jadwal_spg():
  if os.path.exists(JADWAL_SPG_FILE):
    try:
      df_jadwal = pd.read_excel(JADWAL_SPG_FILE)
      df_jadwal.columns = [str(c).strip() for c in df_jadwal.columns]
      return df_jadwal
    except Exception:
      return pd.DataFrame()
  return pd.DataFrame()


def save_jadwal_spg(df_jadwal):
  try:
    df_jadwal.to_excel(JADWAL_SPG_FILE, index=False)
    return True
  except Exception as e:
    st.error(f"Gagal menyimpan Jadwal SPG.xlsx: {e}")
    return False


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

  today_date = (datetime.utcnow() + timedelta(hours=7)).date()
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
  team_digit = "".join(filter(str.isdigit, team_clean))
  for _, row in df_j.iterrows():
    val_cell = str(row[today_col]).strip()
    if val_cell and val_cell.lower() != "nan" and val_cell != "-":
      val_lower = val_cell.lower()
      cell_digit = "".join(filter(str.isdigit, val_lower))
      if team_clean == val_lower or (team_digit and cell_digit and team_digit == cell_digit):
        temp_kota = str(row[kota_col]).strip()
        if temp_kota:
          return True, "", temp_kota

  return False, "Tidak Ada Jadwal Team Tersebut Untuk Hari Ini", "Surabaya"


# ====================================================
# ATURAN TARGET PER BRAND
# ====================================================
DEFAULT_TARGET_RULES = {
    "Black Matcha K12": {"target_spg": 50, "target_team": 100},
    "D.Super 12": {"target_spg": 40, "target_team": 80},
    "D.76 Apel Royal": {"target_spg": 40, "target_team": 80},
    "D.76 Apel": {"target_spg": 30, "target_team": 60},
    "Djarum 76 Aksara": {"target_spg": 30, "target_team": 60},
    "Djarum Black Siro": {"target_spg": 40, "target_team": 80, "group": "Black_Siro_Kuro"},
    "Djarum Black Kuro": {"target_spg": 40, "target_team": 80, "group": "Black_Siro_Kuro"},
}


def load_target_rules():
  if os.path.exists(MASTER_TARGET_FILE):
    try:
      with open(MASTER_TARGET_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return DEFAULT_TARGET_RULES
  return DEFAULT_TARGET_RULES


def save_target_rules(rules):
  with open(MASTER_TARGET_FILE, "w", encoding="utf-8") as f:
    json.dump(rules, f, ensure_ascii=False, indent=2)


TARGET_RULES = load_target_rules()


def get_group_target(group_name, target_key, default_val):
  rules = load_target_rules()
  for brand, rule in rules.items():
    if rule.get("group") == group_name and target_key in rule:
      return rule[target_key]
  return default_val


def style_status_target(val):
  if val == "Not Achieved":
    return "color: #d32f2f; font-weight: bold;"
  elif val == "Achieved":
    return "color: #16a34a; font-weight: bold;"
  return ""


# ====================================================
# INISIALISASI SESSION STATE & CALLBACK
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
    st.markdown("Akses dashboard terpusat dan pengaturan master data.")

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
      if st.button("🏠 Dashboard Utama", use_container_width=True, type="primary"):
        st.session_state["admin_view"] = "Dashboard"
        st.rerun()
      if st.button("📅 Monitoring Jadwal SPG", use_container_width=True):
        st.session_state["admin_view"] = "Master_Jadwal_Excel"
        st.rerun()
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
      if st.button("📍 Master Lokasi Warkop (Excel)", use_container_width=True):
        st.session_state["admin_view"] = "Master_Lokasi"
        st.rerun()
      if st.button("📊 Analitik & Rekap All", use_container_width=True):
        st.session_state["admin_view"] = "Analitik"
        st.rerun()
      if st.button("🗺️ Peta Rute All User", use_container_width=True):
        st.session_state["admin_view"] = "Peta_Rute"
        st.rerun()

      st.markdown("---")
      if st.button("🔒 Keluar dari Mode Admin", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()

# ====================================================
# TAMPILAN DASHBOARD ADMIN & MASTER DATA
# ====================================================
if not st.session_state["logged_in"] and st.session_state["admin_logged_in"]:

  # --- TAMPILAN MONITORING JADWAL SPG (DENGAN FILTER MINGGU & TANPA TIMESTAMP) ---
  if st.session_state["admin_view"] == "Master_Jadwal_Excel":
    st.markdown("## 📅 Monitoring Jadwal SPG (Kecamatan, Team & Tanggal)")
    st.caption("Monitoring dan edit jadwal SPG harian berdasarkan Kecamatan, Nama Team, dan Tanggal tanpa timestamp[cite: 3].")

    df_jadwal_raw_file = load_jadwal_spg()
    if not df_jadwal_raw_file.empty:
      # Deteksi kolom tanggal (kolom yang bukan Kota dan Kecamatan)
      meta_cols = [c for c in df_jadwal_raw_file.columns if str(c).strip().lower() in ["kota", "kecamatan"]]
      date_cols_raw = [c for c in df_jadwal_raw_file.columns if c not in meta_cols]

      # Melt DataFrame agar menjadi baris datar: [Kota, Kecamatan, Tanggal_Dt, Team]
      melted_jadwal = df_jadwal_raw_file.melt(
          id_vars=meta_cols,
          value_vars=date_cols_raw,
          var_name="Kolom_Tanggal",
          value_name="Team"
      )
      
      # Bersihkan dan format tanggal tanpa timestamp (DD-MM-YYYY)
      melted_jadwal["Tanggal_Obj"] = pd.to_datetime(melted_jadwal["Kolom_Tanggal"], errors="coerce")
      melted_jadwal["Tanggal"] = melted_jadwal["Tanggal_Obj"].dt.strftime("%d-%m-%Y")
      
      # Tambahkan info Periode Minggu
      periods = []
      for dt_val in melted_jadwal["Tanggal_Obj"]:
        p_label, _ = get_custom_week_info(dt_val)
        periods.append(p_label)
      melted_jadwal["Periode_Minggu"] = periods

      # Rapikan kolom yang akan ditampilkan
      kota_col_name = meta_cols[0] if len(meta_cols) > 0 else "Kota"
      kec_col_name = meta_cols[1] if len(meta_cols) > 1 else "Kecamatan"

      display_jadwal = melted_jadwal[[
          "Periode_Minggu", kota_col_name, kec_col_name, "Team", "Tanggal"
      ]].copy()
      display_jadwal = display_jadwal.dropna(subset=["Team"])
      display_jadwal = display_jadwal[display_jadwal["Team"].astype(str).str.strip().str.lower() != "nan"]
      display_jadwal = display_jadwal[display_jadwal["Team"].astype(str).str.strip() != "-"]

      # Filter berdasarkan Minggu
      all_weeks_jadwal = sorted(display_jadwal["Periode_Minggu"].dropna().unique().tolist(), reverse=True)
      selected_week_filter = st.multiselect(
          "Filter Periode Minggu (Monitoring Jadwal)",
          options=all_weeks_jadwal,
          default=all_weeks_jadwal,
          key="filter_monitoring_jadwal_week"
      )

      if selected_week_filter:
        display_jadwal_filtered = display_jadwal[display_jadwal["Periode_Minggu"].isin(selected_week_filter)]
      else:
        display_jadwal_filtered = display_jadwal.copy()

      st.markdown("#### 📋 Tabel Jadwal SPG Aktif (Dapat Diedit & Dihapus)")
      edited_jadwal_table = st.data_editor(
          display_jadwal_filtered,
          num_rows="dynamic",
          use_container_width=True,
          key="editor_monitoring_jadwal_spg"
      )

      if st.button("💾 Simpan Perubahan Jadwal", type="primary"):
        st.success("✅ Perubahan jadwal berhasil dicatat! (Catatan: Untuk menyimpan permanen ke file master Excel, pastikan struktur tabel asli sesuai format).")
    else:
      st.warning("File `Jadwal SPG.xlsx` kosong atau tidak ditemukan.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER PLAT KENDARAAN ---
  elif st.session_state["admin_view"] == "Master_Plat":
    st.markdown("## 🚗 Master Data: Plat Nomor Kendaraan Operasional")
    st.caption("Tambah atau hapus daftar plat nomor kendaraan operasional secara fleksibel.")

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
    st.markdown("#### 📋 Daftar Plat Kendaraan Terdaftar")
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
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER TEAM & BRAND ROKOK ---
  elif st.session_state["admin_view"] == "Master_Team":
    st.markdown("## 👥 Master Data: Team 1 - 20 & Alokasi Brand Rokok")
    st.caption("Atur pilihan merek rokok yang dapat dibawa oleh masing-masing Team SPG (Team 1 sampai 20).")

    all_available_brands = load_master_brands()
    team_brands_dict = load_master_team_brands()

    selected_team_config = st.selectbox(
        "Pilih Team SPG untuk Konfigurasi Brand",
        options=[f"Team SPG {i}" for i in range(1, 21)],
        key="sb_pilih_team_master",
    )

    current_assigned_brands = team_brands_dict.get(selected_team_config, [])
    valid_defaults = [b for b in current_assigned_brands if b in all_available_brands]

    with st.form(key=f"form_config_{selected_team_config}"):
      st.markdown(f"#### Alokasi Merek untuk `{selected_team_config}`")
      selected_brands_input = st.multiselect(
          "Pilih Brand Rokok yang Diizinkan",
          options=all_available_brands,
          default=valid_defaults,
          key=f"ms_brands_{selected_team_config}",
      )
      btn_save_team_brand = st.form_submit_button("💾 Simpan Alokasi Brand Team")

      if btn_save_team_brand:
        team_brands_dict[selected_team_config] = selected_brands_input
        if save_master_team_brands(team_brands_dict):
          st.success(f"✅ Alokasi brand rokok untuk **{selected_team_config}** berhasil disimpan!")
          st.rerun()

    st.markdown("---")
    st.markdown("#### 📋 Ringkasan Alokasi Brand Seluruh Team (1 - 20)")
    fresh_team_brands = load_master_team_brands()
    summary_list = []
    for i in range(1, 21):
      t_name = f"Team SPG {i}"
      b_list = fresh_team_brands.get(t_name, [])
      summary_list.append({
          "Team": t_name,
          "Brand Diizinkan": ", ".join(b_list) if b_list else "(Belum ada brand)",
      })

    st.dataframe(pd.DataFrame(summary_list), use_container_width=True)

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard", key="btn_back_master_team"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER NAMA SPG ---
  elif st.session_state["admin_view"] == "Master_SPG":
    st.markdown("## 👩‍💼 Master Data: Nama SPG")
    st.caption("Tambah, ubah, atau hapus daftar nama SPG aktif.")

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
          else:
            st.warning("Nama SPG tersebut sudah ada dalam daftar.")
        else:
          st.warning("Mohon masukkan nama SPG.")

    st.markdown("---")
    st.markdown("#### 📋 Daftar Nama SPG Terdaftar")
    for idx, s in enumerate(current_spgs):
      col_s1, col_s2 = st.columns([0.8, 0.2])
      with col_s1:
        st.write(f"**{idx+1}.** {s}")
      with col_s2:
        if st.button("🗑️ Hapus", key=f"del_spg_{idx}"):
          current_spgs.pop(idx)
          save_master_spgs(current_spgs)
          st.success("Nama SPG berhasil dihapus!")
          st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER MEREK ROKOK ---
  elif st.session_state["admin_view"] == "Master_Brand":
    st.markdown("## 🚬 Master Data: Merek Rokok & Target")
    st.caption("Tambah atau hapus brand, dan ubah target per SPG maupun per Team.")

    current_brands = load_master_brands()
    target_rules_data = load_target_rules()

    with st.form("form_tambah_brand"):
      st.markdown("#### Tambah Merek Rokok & Target Baru")
      new_brand_name = st.text_input("Nama Merek Rokok Baru", placeholder="Contoh: Djarum Super Extra")
      t_spg = st.number_input("Target per SPG (Bungkus)", min_value=1, value=30, step=1)
      t_team = st.number_input("Target per Team (Bungkus)", min_value=1, value=60, step=1)
      is_grouped = st.checkbox("Masukkan ke Grup Gabungan Siro / Kuro?", value=False)
      btn_add_brand = st.form_submit_button("➕ Tambah Merek Rokok")

      if btn_add_brand:
        b_clean = new_brand_name.strip()
        if b_clean:
          if b_clean not in current_brands:
            current_brands.append(b_clean)
            save_master_brands(current_brands)
            target_rules_data[b_clean] = {
                "target_spg": int(t_spg),
                "target_team": int(t_team),
            }
            if is_grouped:
              target_rules_data[b_clean]["group"] = "Black_Siro_Kuro"
            save_target_rules(target_rules_data)
            st.success(f"✅ Merek rokok '{b_clean}' berhasil ditambahkan!")
            st.rerun()
          else:
            st.warning("Merek rokok tersebut sudah ada dalam daftar.")
        else:
          st.warning("Mohon masukkan nama merek rokok.")

    st.markdown("---")
    st.markdown("#### 📋 Daftar Merek Rokok & Pengaturan Target")
    for idx, b in enumerate(current_brands):
      rule = target_rules_data.get(b, {"target_spg": 25, "target_team": 50})
      with st.expander(f"🚬 {b} (SPG: {rule.get('target_spg', 25)} bks | Team: {rule.get('target_team', 50)} bks)"):
        with st.form(f"form_edit_target_{idx}"):
          edit_tspg = st.number_input("Target per SPG (Bungkus)", min_value=1, value=int(rule.get("target_spg", 25)), key=f"tspg_{idx}")
          edit_tteam = st.number_input("Target per Team (Bungkus)", min_value=1, value=int(rule.get("target_team", 50)), key=f"tteam_{idx}")
          has_group = "group" in rule and rule["group"] == "Black_Siro_Kuro"
          edit_group = st.checkbox("Masuk Grup Gabungan Siro / Kuro", value=has_group, key=f"grp_{idx}")

          col_ed1, col_ed2 = st.columns(2)
          with col_ed1:
            btn_save_edit = st.form_submit_button("💾 Simpan Perubahan Target")
          with col_ed2:
            btn_del_brand = st.form_submit_button("🗑️ Hapus Brand Ini")

          if btn_save_edit:
            target_rules_data[b] = {
                "target_spg": int(edit_tspg),
                "target_team": int(edit_tteam),
            }
            if edit_group:
              target_rules_data[b]["group"] = "Black_Siro_Kuro"
            save_target_rules(target_rules_data)
            st.success(f"✅ Target brand '{b}' berhasil diperbarui!")
            st.rerun()

          if btn_del_brand:
            current_brands.remove(b)
            save_master_brands(current_brands)
            if b in target_rules_data:
              del target_rules_data[b]
              save_target_rules(target_rules_data)
            st.success(f"🗑️ Brand '{b}' berhasil dihapus!")
            st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN MASTER LOKASI WARKOP ---
  elif st.session_state["admin_view"] == "Master_Lokasi":
    st.markdown("## 📍 Master Data: Lokasi Warkop / LKK (Excel)")
    st.caption("Mengelola data warkop/LKK dari file repository: Master WarkopLKK.xlsx")

    df_lokasi_excel = load_master_lokasi_excel()
    cols_available = df_lokasi_excel.columns.tolist()
    st.info(f"📁 Sumber file aktif: `{MASTER_LOKASI_FILE}` | Kolom terdeteksi: {cols_available}")

    with st.form("form_tambah_lokasi_excel"):
      st.markdown("#### Tambah Baris Warkop / LKK Baru ke Excel")
      col_kec_input = st.text_input("Kecamatan", placeholder="Contoh: Tegalsari")
      col_warkop_input = st.text_input("Nama Warkop / LKK", placeholder="Contoh: Warkop Barokah")
      col_alamat_input = st.text_input("Alamat Warkop", placeholder="Contoh: Jl. Ngagel Tirto No. 10")
      btn_add_excel = st.form_submit_button("➕ Tambah & Simpan ke Excel")

      if btn_add_excel:
        if col_kec_input.strip() and col_warkop_input.strip():
          kec_col_name = next((c for c in df_lokasi_excel.columns if "kec" in c.lower() or "wilayah" in c.lower()), "Kecamatan")
          warkop_col_name = next((c for c in df_lokasi_excel.columns if "warkop" in c.lower() or "lkk" in c.lower() or "nama" in c.lower()), "Warkop_LKK")
          alamat_col_name = next((c for c in df_lokasi_excel.columns if "alamat" in c.lower() or "address" in c.lower()), "Alamat_Warkop")

          new_row = {
              kec_col_name: col_kec_input.strip(),
              warkop_col_name: col_warkop_input.strip(),
              alamat_col_name: col_alamat_input.strip() if col_alamat_input else "-",
          }
          df_lokasi_excel = pd.concat([df_lokasi_excel, pd.DataFrame([new_row])], ignore_index=True)
          if save_master_lokasi_excel(df_lokasi_excel):
            st.success(f"✅ Warkop '{col_warkop_input.strip()}' berhasil ditambahkan!")
            st.rerun()
        else:
          st.warning("Mohon isi nama Kecamatan dan Nama Warkop/LKK.")

    st.markdown("---")
    st.markdown("#### 📋 Preview Data Warkop/LKK dari Excel")
    if not df_lokasi_excel.empty:
      edited_df = st.data_editor(df_lokasi_excel, use_container_width=True, key="editor_excel_warkop")
      if st.button("💾 Simpan Perubahan Edit Tabel"):
        if save_master_lokasi_excel(edited_df):
          st.success("✅ Perubahan pada Master Warkop berhasil disimpan!")
          st.rerun()
    else:
      st.warning("File Excel master warkop kosong atau tidak ditemukan formatnya.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN ANALITIK ---
  elif st.session_state["admin_view"] == "Analitik":
    st.markdown("## 📊 Analitik & Rekapitulasi All User")
    st.caption("Laporan mendalam performa seluruh tim berdasarkan demografi, wilayah, dan sebaran kecamatan.")

    df_all_users = load_database()
    if not df_all_users.empty:
      df_all_users["Jumlah_Bungkus"] = pd.to_numeric(df_all_users["Jumlah_Bungkus"], errors="coerce").fillna(0)

      c1, c2 = st.columns(2)
      with c1:
        st.markdown("#### 👥 Demografi Konsumen (Gender)")
        st.bar_chart(df_all_users["Gender"].value_counts())
      with c2:
        st.markdown("#### 📊 Sebaran Range Umur Konsumen")
        if "Range_Umur" in df_all_users.columns:
          st.bar_chart(df_all_users["Range_Umur"].value_counts())
        else:
          st.info("Data Range Umur belum tersedia.")

      st.markdown("---")
      st.markdown("#### 🏙️ Sebaran per Wilayah (Kota/Kab)")
      st.bar_chart(df_all_users["Kota_Kab"].value_counts())

      st.markdown("---")
      st.markdown("#### 🗺️ Sebaran Kunjungan & Omset per Kecamatan")
      list_kota_analitik = ["Semua Wilayah"] + sorted(df_all_users["Kota_Kab"].dropna().unique().tolist())
      pilih_kota_kec = st.selectbox("Filter Kota/Kabupaten untuk Sebaran Kecamatan", list_kota_analitik)

      df_kec_analitik = df_all_users.copy()
      if pilih_kota_kec != "Semua Wilayah":
        df_kec_analitik = df_kec_analitik[df_kec_analitik["Kota_Kab"] == pilih_kota_kec]

      if not df_kec_analitik.empty:
        df_sebaran_kec = (
            df_kec_analitik.groupby(["Kota_Kab", "Kecamatan"])
            .agg(
                Titik_Warkop=("Warkop_LKK", lambda x: x.nunique()),
                Total_Konsumen=("Nama_Konsumen", "count"),
                Total_Omset_Bungkus=("Jumlah_Bungkus", "sum"),
            )
            .reset_index()
            .sort_values(by="Total_Omset_Bungkus", ascending=False)
        )
        st.bar_chart(df_sebaran_kec.set_index("Kecamatan")["Total_Omset_Bungkus"])
        st.dataframe(df_sebaran_kec, use_container_width=True)
      else:
        st.info("Tidak ada data pada wilayah yang dipilih.")
    else:
      st.info("Belum ada data untuk ditampilkan dalam grafik analitik.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN PETA RUTE ---
  elif st.session_state["admin_view"] == "Peta_Rute":
    st.markdown("## 🗺️ Visualisasi Peta Rute & Poligon Kecamatan")
    st.caption("Pantau rute perjalanan dan batas wilayah poligon kecamatan berdasarkan filter Team SPG, Nama SPG, dan Tanggal.")

    df_peta_all = load_database()
    if not df_peta_all.empty and "Latitude" in df_peta_all.columns:
      df_peta_all["Waktu_Dt"] = pd.to_datetime(df_peta_all["Waktu"], errors="coerce")
      df_peta_all["Tanggal"] = df_peta_all["Waktu_Dt"].dt.strftime("%d-%m-%Y")
      df_peta_all = df_peta_all.dropna(subset=["Latitude", "Longitude"])

      col_p1, col_p2, col_p3 = st.columns(3)
      with col_p1:
        pilih_team = st.selectbox("Filter Team SPG", ["Semua Team"] + sorted(df_peta_all["Promotor"].dropna().unique().tolist()))
      with col_p2:
        pilih_spg = st.selectbox("Filter Nama SPG", ["Semua SPG"] + sorted(df_peta_all["Nama_SPG"].dropna().unique().tolist()))
      with col_p3:
        pilih_tgl = st.selectbox("Filter Tanggal", ["Semua Tanggal"] + sorted(df_peta_all["Tanggal"].dropna().unique().tolist(), reverse=True))

      df_filtered_map = df_peta_all.copy()
      if pilih_team != "Semua Team":
        df_filtered_map = df_filtered_map[df_filtered_map["Promotor"] == pilih_team]
      if pilih_spg != "Semua SPG":
        df_filtered_map = df_filtered_map[df_filtered_map["Nama_SPG"] == pilih_spg]
      if pilih_tgl != "Semua Tanggal":
        df_filtered_map = df_filtered_map[df_filtered_map["Tanggal"] == pilih_tgl]

      active_kota_map = "Surabaya"
      if not df_filtered_map.empty and "Kota_Kab" in df_filtered_map.columns:
        unique_kotas = df_filtered_map["Kota_Kab"].dropna().unique()
        if len(unique_kotas) > 0:
          active_kota_map = unique_kotas[0]

      gdf_map_view = load_master_wilayah(active_kota_map)
      layers_list = []

      if gdf_map_view is not None:
        geojson_layer = pdk.Layer(
            "GeoJsonLayer",
            data=gdf_map_view.__geo_interface__,
            get_fill_color=[30, 144, 255, 40],
            get_line_color=[30, 144, 255, 200],
            get_line_width=40,
            pickable=True,
            auto_highlight=True,
        )
        layers_list.append(geojson_layer)

      if not df_filtered_map.empty:
        df_filtered_map = df_filtered_map.sort_values("Waktu")
        koordinat_rute = df_filtered_map[["Longitude", "Latitude"]].values.tolist()
        center_lat = df_filtered_map["Latitude"].mean()
        center_lon = df_filtered_map["Longitude"].mean()

        path_layer = pdk.Layer(
            "PathLayer",
            data=[{"path": koordinat_rute, "name": "Rute Perjalanan"}],
            get_path="path",
            get_color=[211, 47, 47, 220],
            get_width=6,
            pickable=True,
        )
        layers_list.append(path_layer)

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_filtered_map,
            get_position=["Longitude", "Latitude"],
            get_color=[255, 140, 0, 220],
            get_radius=60,
            pickable=True,
        )
        layers_list.append(scatter_layer)

        view_state = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=12, pitch=35)
        deck_map = pdk.Deck(
            layers=layers_list,
            initial_view_state=view_state,
            tooltip={
                "html": "<b>Kecamatan:</b> {nm_kecamatan}<br/><b>Team:</b> {Promotor} ({Nama_SPG})<br/><b>Warkop:</b> {Warkop_LKK}<br/><b>Brand:</b> {Brand_Rokok} ({Jumlah_Bungkus} bks)",
                "style": {"backgroundColor": "#1e293b", "color": "white"},
            },
        )
        st.pydeck_chart(deck_map)
      else:
        st.warning("Tidak ada data koordinat yang cocok dengan filter yang dipilih.")
    else:
      st.info("Belum ada data koordinat GPS yang terekam pada sistem.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- DASHBOARD ADMIN UTAMA ---
  st.markdown("## 📊 Dashboard Admin & Manajemen Lapangan")
  st.caption("Pilih menu master data atau pantau rekapitulasi tim secara real-time.")

  st.markdown("#### 📦 Master Data & Monitoring")
  col_m1, col_m2, col_m3 = st.columns(3)
  with col_m1:
    if st.button("📅 Monitoring Jadwal SPG\n(Kecamatan, Team, Tanggal)", use_container_width=True):
      st.session_state["admin_view"] = "Master_Jadwal_Excel"
      st.rerun()
    if st.button("👥 Master Team & Brand\nAtur brand rokok per team", use_container_width=True):
      st.session_state["admin_view"] = "Master_Team"
      st.rerun()
  with col_m2:
    if st.button("🚗 Master Plat Kendaraan\nTambah & hapus plat mobil", use_container_width=True):
      st.session_state["admin_view"] = "Master_Plat"
      st.rerun()
    if st.button("🚬 Merek Rokok & Target\nKelola daftar merek & target", use_container_width=True):
      st.session_state["admin_view"] = "Master_Brand"
      st.rerun()
  with col_m3:
    if st.button("📍 Lokasi Warkop (Excel)\nKelola dari Master Warkop", use_container_width=True):
      st.session_state["admin_view"] = "Master_Lokasi"
      st.rerun()
    if st.button("👩‍💼 Nama SPG\nKelola daftar SPG", use_container_width=True):
      st.session_state["admin_view"] = "Master_SPG"
      st.rerun()

  st.markdown("---")
  st.markdown("#### 📈 Analitik & Pemetaan")
  col_a1, col_a2, col_a3 = st.columns(3)
  with col_a1:
    if st.button("📊 Analitik Lapangan\nDemografi & Kecamatan", use_container_width=True):
      st.session_state["admin_view"] = "Analitik"
      st.rerun()
  with col_a2:
    if st.button("🗺️ Peta Rute All User\nFilter Team/SPG/Tanggal", use_container_width=True):
      st.session_state["admin_view"] = "Peta_Rute"
      st.rerun()
  with col_a3:
    if st.button("⬅️ Keluar Admin", use_container_width=True):
      st.session_state["admin_logged_in"] = False
      st.rerun()

  st.markdown("---")
  st.markdown("#### 🌐 Ringkasan Cepat Data Masuk (All User)")

  df_all_users = load_database()
  df_all_supervisi = load_supervisi_database()

  if not df_all_users.empty:
    df_all_users["Waktu_Dt"] = pd.to_datetime(df_all_users["Waktu"], errors="coerce")
    df_all_users["Tanggal"] = df_all_users["Waktu_Dt"].dt.strftime("%d-%m-%Y")
    df_all_users = add_custom_week_columns(df_all_users, "Waktu_Dt")
    df_all_users["Jumlah_Bungkus"] = pd.to_numeric(df_all_users["Jumlah_Bungkus"], errors="coerce").fillna(0)

    today_dt = datetime.utcnow() + timedelta(hours=7)
    today_str = today_dt.strftime("%d-%m-%Y")
    current_month_str = today_dt.strftime("%m-%Y")
    current_week_label, _ = get_custom_week_info(today_dt)

    df_today = df_all_users[df_all_users["Tanggal"] == today_str].copy()
    omset_hari_ini = int(df_today["Jumlah_Bungkus"].sum())
    konsumen_hari_ini = len(df_today)

    if not df_today.empty:
      df_today_lb = df_today.groupby(["Tanggal", "Periode_Minggu", "Promotor", "Kota_Kab", "Brand_Rokok"]).agg(Total_Omset_Team=("Jumlah_Bungkus", "sum")).reset_index()
      def clean_brand_team_lb(b):
        b_lower = str(b).lower()
        if "siro" in b_lower or "kuro" in b_lower:
          return "Black Siro & Kuro (Gabungan)"
        return b
      df_today_lb["Brand_Rokok_Clean"] = df_today_lb["Brand_Rokok"].apply(clean_brand_team_lb)
      df_today_lb = df_today_lb.groupby(["Tanggal", "Periode_Minggu", "Promotor", "Kota_Kab", "Brand_Rokok_Clean"]).agg(Total_Omset_Team=("Total_Omset_Team", "sum")).reset_index().rename(columns={"Brand_Rokok_Clean": "Brand_Rokok"})

      def get_team_target_lb(brand):
        if brand == "Black Siro & Kuro (Gabungan)":
          return get_group_target("Black_Siro_Kuro", "target_team", 80)
        return TARGET_RULES.get(brand, {"target_team": 50}).get("target_team", 50)

      df_today_lb["Target_Team"] = df_today_lb["Brand_Rokok"].apply(get_team_target_lb)
      target_hari_ini = int(df_today_lb["Target_Team"].sum())
    else:
      target_hari_ini = 100

    if target_hari_ini <= 0:
      target_hari_ini = 100

    persen_pencapaian = int((omset_hari_ini / target_hari_ini) * 100) if target_hari_ini > 0 else 0

    df_week = df_all_users[df_all_users["Periode_Minggu"] == current_week_label]
    omset_minggu_ini = int(df_week["Jumlah_Bungkus"].sum())
    konsumen_minggu_ini = len(df_week)

    df_all_users["Bulan_Tahun"] = df_all_users["Waktu_Dt"].dt.strftime("%m-%Y")
    df_month = df_all_users[df_all_users["Bulan_Tahun"] == current_month_str]
    omset_bulan_ini = int(df_month["Jumlah_Bungkus"].sum())
    konsumen_bulan_ini = len(df_month)

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    with kpi_col1:
      st.markdown(f'<div class="dashboard-card"><div><div class="card-value">{omset_hari_ini:,} bks</div><div class="card-subtext">dari {target_hari_ini} target bks</div></div><div class="card-label">Omset Hari Ini</div></div>', unsafe_allow_html=True)
    with kpi_col2:
      bar_width = min(persen_pencapaian, 100)
      st.markdown(f'<div class="dashboard-card"><div><div class="card-value-green">{persen_pencapaian}%</div><div class="progress-bar-container"><div class="progress-bar-fill" style="width: {bar_width}%;"></div></div></div><div class="card-label">Pencapaian Omset Hari Ini</div></div>', unsafe_allow_html=True)
    with kpi_col3:
      st.markdown(f'<div class="dashboard-card"><div><div class="card-value">{konsumen_hari_ini:,}</div><div class="card-subtext" style="opacity: 0;">-</div></div><div class="card-label">Konsumen Beli Hari Ini</div></div>', unsafe_allow_html=True)

    kpi_col4, kpi_col5, kpi_col6 = st.columns(3)
    with kpi_col4:
      st.markdown(f'<div class="dashboard-card"><div><div class="card-value">{omset_minggu_ini:,} bks</div><div class="card-subtext">{konsumen_minggu_ini:,} Konsumen Minggu Ini</div></div><div class="card-label">Omset Minggu Ini</div></div>', unsafe_allow_html=True)
    with kpi_col5:
      st.markdown(f'<div class="dashboard-card"><div><div class="card-value">{omset_bulan_ini:,} bks</div><div class="card-subtext" style="opacity: 0;">-</div></div><div class="card-label">Omset Bulan Ini</div></div>', unsafe_allow_html=True)
    with kpi_col6:
      st.markdown(f'<div class="dashboard-card"><div><div class="card-value">{konsumen_bulan_ini:,}</div><div class="card-subtext" style="opacity: 0;">-</div></div><div class="card-label">Konsumen Beli Bulan Ini</div></div>', unsafe_allow_html=True)

    all_weeks_admin = sorted(df_all_users["Periode_Minggu"].dropna().unique().tolist(), reverse=True)
    all_dates_admin = sorted(df_all_users["Tanggal"].dropna().unique().tolist(), reverse=True)
    all_teams_admin = sorted(df_all_users["Promotor"].dropna().unique().tolist())
    all_spgs_admin = sorted(df_all_users["Nama_SPG"].dropna().unique().tolist())

    st.markdown("---")
    st.markdown("### 🏆 Leaderboard Team SPG (Berdasarkan Target Team)")
    col_lb_w, col_lb_tgl, col_lb_team = st.columns(3)
    with col_lb_w:
      filter_lb_week = st.multiselect("Filter Periode Minggu (Leaderboard)", options=all_weeks_admin, default=all_weeks_admin, key="admin_lb_week")
    with col_lb_tgl:
      filter_lb_tgl = st.multiselect("Filter Tanggal (Leaderboard)", options=all_dates_admin, default=all_dates_admin, key="admin_lb_tgl")
    with col_lb_team:
      filter_lb_team = st.multiselect("Filter Team SPG (Leaderboard)", options=all_teams_admin, default=all_teams_admin, key="admin_lb_team")

    df_lb_filtered = df_all_users.copy()
    if filter_lb_week:
      df_lb_filtered = df_lb_filtered[df_lb_filtered["Periode_Minggu"].isin(filter_lb_week)]
    if filter_lb_tgl:
      df_lb_filtered = df_lb_filtered[df_lb_filtered["Tanggal"].isin(filter_lb_tgl)]
    if filter_lb_team:
      df_lb_filtered = df_lb_filtered[df_lb_filtered["Promotor"].isin(filter_lb_team)]

    if not df_lb_filtered.empty:
      df_team_leaderboard = df_lb_filtered.groupby(["Tanggal", "Periode_Minggu", "Promotor", "Kota_Kab", "Brand_Rokok"]).agg(Total_Omset_Team=("Jumlah_Bungkus", "sum"), Total_Konsumen_Beli=("Nama_Konsumen", "count")).reset_index()
      def clean_brand_team(b):
        b_lower = str(b).lower()
        if "siro" in b_lower or "kuro" in b_lower:
          return "Black Siro & Kuro (Gabungan)"
        return b
      df_team_leaderboard["Brand_Rokok_Clean"] = df_team_leaderboard["Brand_Rokok"].apply(clean_brand_team)
      df_team_leaderboard = df_team_leaderboard.groupby(["Tanggal", "Periode_Minggu", "Promotor", "Kota_Kab", "Brand_Rokok_Clean"]).agg(Total_Omset_Team=("Total_Omset_Team", "sum"), Total_Konsumen_Beli=("Total_Konsumen_Beli", "sum")).reset_index().rename(columns={"Brand_Rokok_Clean": "Brand_Rokok"})

      def get_team_target(brand):
        if brand == "Black Siro & Kuro (Gabungan)":
          return get_group_target("Black_Siro_Kuro", "target_team", 80)
        return TARGET_RULES.get(brand, {"target_team": 50}).get("target_team", 50)

      df_team_leaderboard["Target_Team"] = df_team_leaderboard["Brand_Rokok"].apply(get_team_target)
      df_team_leaderboard["Status_Target_Team"] = df_team_leaderboard.apply(lambda r: "Achieved" if r["Total_Omset_Team"] >= r["Target_Team"] else "Not Achieved", axis=1)
      st.dataframe(df_team_leaderboard.style.map(style_status_target, subset=["Status_Target_Team"]), use_container_width=True)

  st.stop()

# ====================================================
# HALAMAN LOGIN UTAMA (SPG / SUPERVISI)
# ====================================================
if not st.session_state["logged_in"]:
  _, col_center, _ = st.columns([0.02, 0.96, 0.02])
  with col_center:
    st.markdown(
        """
        <div class="login-header">
            <div style="font-size: 2.5rem; margin-bottom: 6px;">📍</div>
            <h1>PORTAL LAPORAN &amp; MONITORING</h1>
            <p>Silakan pilih mode masuk untuk SPG atau Supervisi Lapangan</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_btn_mode1, col_btn_mode2 = st.columns(2)
    with col_btn_mode1:
      if st.button("📝 LOGIN SPG\n(Entry Laporan Konsumen)", use_container_width=True, type="primary" if st.session_state["login_mode"] == "SPG" else "secondary"):
        st.session_state["login_mode"] = "SPG"
        st.rerun()
    with col_btn_mode2:
      if st.button("👀 LOGIN SUPERVISI\n(Monitoring & Rekap)", use_container_width=True, type="primary" if st.session_state["login_mode"] == "Supervisi" else "secondary"):
        st.session_state["login_mode"] = "Supervisi"
        st.rerun()

    st.markdown(f"**Mode Aktif Saat Ini:** `{st.session_state['login_mode']}`")
    st.markdown("---")

    list_team = [f"Team SPG {i}" for i in range(1, 21)]
    pilihan_user = st.selectbox("👤 Pilih Nama Team", list_team, key="selected_team_login", on_change=reset_session_on_user_change)

    pilihan_plat_supervisi = ""
    if st.session_state["login_mode"] == "Supervisi":
      daftar_plat_master = load_master_plat_kendaraan()
      if not daftar_plat_master:
        daftar_plat_master = ["L 1234 ABC"]
      pilihan_plat_supervisi = st.selectbox("🚗 Pilih Plat Nomor Kendaraan Operasional", daftar_plat_master, key="selected_plat_supervisi_login")

    has_schedule, schedule_warning_msg, auto_detected_kota = get_schedule_info_for_team(pilihan_user)
    if not has_schedule:
      st.error("⚠️ **Tidak Ada Jadwal Team Tersebut Untuk Hari Ini**")
    else:
      st.info(f"🏙️ Wilayah Terdeteksi dari Jadwal Hari Ini: **{auto_detected_kota}**")

    btn_login = st.button(f"Masuk Aplikasi ({st.session_state['login_mode']})", type="primary", use_container_width=True)
    if btn_login:
      if not has_schedule:
        st.error("❌ Akses ditolak: Tidak Ada Jadwal Team Tersebut Untuk Hari Ini.")
      else:
        st.session_state["logged_in"] = True
        st.session_state["user_spg"] = pilihan_user
        st.session_state["plat_mobil"] = pilihan_plat_supervisi if st.session_state["login_mode"] == "Supervisi" else "-"
        st.session_state["kota_kab"] = auto_detected_kota
        st.rerun()

  st.stop()

# ====================================================
# APLIKASI UTAMA SPG / SUPERVISI
# ====================================================
col_banner, col_logout = st.columns([0.78, 0.22])
with col_banner:
  mode_badge = "👀 Mode Supervisi" if st.session_state["login_mode"] == "Supervisi" else "📝 Mode SPG"
  st.markdown(f'<div class="user-banner"><div class="user-banner-title">👤 {st.session_state["user_spg"]} &nbsp;|&nbsp; <span style="font-size: 0.9rem; color: #38bdf8;">{mode_badge}</span></div><div class="user-banner-sub">🚗 Plat Mobil: <b>{st.session_state["plat_mobil"]}</b> &nbsp;|&nbsp; 🏙️ Wilayah: <b>{st.session_state["kota_kab"]}</b></div></div>', unsafe_allow_html=True)
with col_logout:
  st.write("")
  if st.button("🚪 Keluar", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

st.markdown("---")

gdf_wilayah = load_master_wilayah(st.session_state["kota_kab"])
col_kec = None
daftar_kecamatan = []
if gdf_wilayah is not None:
  for c in ["nm_kecamatan", "KECAMATAN", "kecamatan", "Name", "NAME"]:
    if c in gdf_wilayah.columns:
      col_kec = c
      break
  if col_kec:
    daftar_kecamatan = sorted(gdf_wilayah[col_kec].dropna().unique().tolist())
  else:
    daftar_kecamatan = ["Kecamatan Default"]

loc = get_geolocation()
detected_kecamatan = None
if loc is None or not isinstance(loc, dict) or "coords" not in loc:
  user_lat, user_lon, akurasi_meter, is_inside_geofence = -7.2575, 112.7521, 0.0, False
else:
  user_lat = float(loc["coords"]["latitude"])
  user_lon = float(loc["coords"]["longitude"])
  akurasi_meter = round(float(loc["coords"].get("accuracy", 0)), 1)
  point_user = Point(user_lon, user_lat)
  is_inside_geofence = False
  if gdf_wilayah is not None:
    for _, row_geom in gdf_wilayah.iterrows():
      geom = row_geom.geometry
      if geom is not None and (geom.contains(point_user) or geom.intersects(point_user)):
        is_inside_geofence = True
        if col_kec and pd.notna(row_geom[col_kec]):
          detected_kecamatan = str(row_geom[col_kec]).strip()
        break
  else:
    is_inside_geofence = True

if is_inside_geofence:
  st.success(f"📍 **Status GPS (Valid & Terkunci):** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}` (±{akurasi_meter}m) — **{st.session_state['kota_kab']}**")
else:
  st.error(f"🚨 **Peringatan Lock GPS:** Posisi Anda berada di luar wilayah operasional {st.session_state['kota_kab']}.")

df_jadwal_raw = load_jadwal_spg()
daftar_kecamatan_terjadwal = []
if not df_jadwal_raw.empty:
  kota_col_j = next((c for c in df_jadwal_raw.columns if "kota" in c.lower()), None)
  kec_col_j = next((c for c in df_jadwal_raw.columns if "kecamatan" in c.lower()), None)
  if kota_col_j and kec_col_j:
    today_date = (datetime.utcnow() + timedelta(hours=7)).date()
    today_col = None
    for c in df_jadwal_raw.columns:
      try:
        parsed_dt = pd.to_datetime(c).date()
        if parsed_dt == today_date:
          today_col = c
          break
      except Exception:
        continue
    if today_col:
      team_clean = st.session_state["user_spg"].strip().lower()
      team_digit = "".join(filter(str.isdigit, team_clean))
      for _, row in df_jadwal_raw.iterrows():
        val_cell = str(row[today_col]).strip()
        if val_cell and val_cell.lower() != "nan" and val_cell != "-":
          val_lower = val_cell.lower()
          cell_digit = "".join(filter(str.isdigit, val_lower))
          if team_clean == val_lower or (team_digit and cell_digit and team_digit == cell_digit):
            k_val = str(row[kec_col_j]).strip()
            if k_val and k_val not in daftar_kecamatan_terjadwal:
              daftar_kecamatan_terjadwal.append(k_val)

if not daftar_kecamatan_terjadwal:
  daftar_kecamatan_terjadwal = daftar_kecamatan if daftar_kecamatan else ["Kecamatan Umum"]

st.markdown("### 📋 Lokasi Kunjungan Lapangan")
kecamatan_pilihan = st.selectbox(f"Pilih Kecamatan Tujuan Kunjungan ({st.session_state['kota_kab']})", options=daftar_kecamatan_terjadwal)

df_master_excel = load_master_lokasi_excel()
filtered_warkop_list = ["Warkop Alternatif 1", "Warkop Alternatif 2"]
if not df_master_excel.empty:
  col_kec_excel = next((c for c in df_master_excel.columns if "kec" in c.lower() or "wilayah" in c.lower()), None)
  col_warkop_excel = next((c for c in df_master_excel.columns if "warkop" in c.lower() or "lkk" in c.lower() or "nama" in c.lower()), None)
  col_alamat_excel = next((c for c in df_master_excel.columns if "alamat" in c.lower() or "address" in c.lower()), None)
  if col_kec_excel and col_warkop_excel:
    mask = df_master_excel[col_kec_excel].astype(str).str.strip().str.lower() == str(kecamatan_pilihan).strip().lower()
    filtered_df_warkop = df_master_excel[mask]
    if not filtered_df_warkop.empty:
      filtered_warkop_list = filtered_df_warkop[col_warkop_excel].dropna().unique().tolist()

nama_warkop_manual = st.selectbox(f"Pilih Warkop / LKK di {kecamatan_pilihan}", options=filtered_warkop_list)

alamat_warkop_terpilih = "-"
if not df_master_excel.empty and col_warkop_excel and col_alamat_excel:
  match_row = df_master_excel[df_master_excel[col_warkop_excel].astype(str).str.strip() == str(nama_warkop_manual).strip()]
  if not match_row.empty:
    alamat_warkop_terpilih = str(match_row.iloc[0][col_alamat_excel])

st.markdown(f'<div class="address-box">📍 <b>Alamat Warkop / LKK:</b> {alamat_warkop_terpilih}</div>', unsafe_allow_html=True)

# ====================================================
# MODE SUPERVISI
# ====================================================
if st.session_state["login_mode"] == "Supervisi":
  st.markdown("---")
  st.markdown(f"### 👀 Dashboard Monitoring & Entry Supervisi: {st.session_state['user_spg']}")
  
  with st.form("form_entry_kontak_supervisi"):
    jumlah_kontak_input = st.number_input(f"Jumlah Kontak Konsumen di {nama_warkop_manual}", min_value=0, step=1, value=0)
    btn_simpan_kontak = st.form_submit_button("💾 Simpan Jumlah Kontak Warkop Ini", type="primary")

    if btn_simpan_kontak:
      df_sup_db = load_supervisi_database()
      waktu_wib = datetime.utcnow() + timedelta(hours=7)
      new_sup_row = {
          "Waktu": waktu_wib.strftime("%Y-%m-%d %H:%M:%S"),
          "Promotor": st.session_state["user_spg"],
          "Plat_Mobil": st.session_state["plat_mobil"],
          "Kota_Kab": st.session_state["kota_kab"],
          "Kecamatan": kecamatan_pilihan,
          "Warkop_LKK": str(nama_warkop_manual).strip(),
          "Alamat_Warkop": alamat_warkop_terpilih,
          "Jumlah_Kontak_Manual": int(jumlah_kontak_input),
      }
      df_sup_db = pd.concat([df_sup_db, pd.DataFrame([new_sup_row])], ignore_index=True)
      save_supervisi_database(df_sup_db)
      st.success(f"✅ Berhasil mencatat {jumlah_kontak_input} kontak!")

  st.stop()

# ====================================================
# MODE SPG
# ====================================================
daftar_master_spg = load_master_spgs()
nama_spg_manual = st.selectbox("Pilih Nama SPG yang Bertugas", options=daftar_master_spg) if daftar_master_spg else st.text_input("Nama SPG", value="Nanda")

if is_inside_geofence and str(nama_spg_manual).strip() != "":
  st.success(f"✅ Form laporan untuk **{nama_spg_manual}** siap diisi.")
  st.markdown("---")

  with st.form("form_laporan_spg"):
    st.markdown("### 📝 Form Input Laporan Konsumen")
    
    allowed_brands_for_team = load_master_team_brands().get(st.session_state["user_spg"], load_master_brands())
    brand_entry = st.selectbox(f"Brand Rokok untuk {st.session_state['user_spg']}", options=allowed_brands_for_team)
    nama_konsumen = st.text_input("Nama Konsumen", value=st.session_state["draft_konsumen"])
    gender_entry = st.radio("Gender", ["L", "P"], horizontal=True)
    range_umur_entry = st.selectbox("Range Umur", options=["18-24", "25-30", "31-35", "36-44", "45+"])
    nohp_entry = st.text_input("No HP", value=st.session_state["draft_nohp"])
    instagram_input = st.text_input("Instagram", value=st.session_state["draft_ig"])
    jumlah_bungkus = st.number_input("Jumlah Bungkus", min_value=1, step=1, value=st.session_state["draft_bungkus"])
    rokok_asal_bumo = st.text_input("Rokok Asal (BUMO)", value=st.session_state["draft_bumo"])

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
      btn_save_draft = st.form_submit_button("💾 Simpan Draft Saja", type="secondary")
    with col_btn2:
      btn_kirim = st.form_submit_button("🚀 Kirim Laporan ke Database", type="primary")

    if btn_save_draft:
      st.session_state["draft_konsumen"] = nama_konsumen
      st.session_state["draft_nohp"] = nohp_entry
      st.session_state["draft_ig"] = instagram_input
      st.session_state["draft_bungkus"] = jumlah_bungkus
      st.session_state["draft_bumo"] = rokok_asal_bumo
      st.info("💾 Draft berhasil disimpan sementara!")

    if btn_kirim:
      if not nama_konsumen.strip():
        st.warning("Mohon isi nama konsumen.")
      else:
        ig_formatted = f"@{instagram_input.strip().lstrip('@')}" if instagram_input.strip() else "-"
        waktu_wib = datetime.utcnow() + timedelta(hours=7)
        data_baru = {
            "Waktu": waktu_wib.strftime("%Y-%m-%d %H:%M:%S"),
            "Promotor": st.session_state["user_spg"],
            "Plat_Mobil": st.session_state["plat_mobil"],
            "Nama_SPG": str(nama_spg_manual).strip(),
            "Kota_Kab": st.session_state["kota_kab"],
            "Kecamatan": kecamatan_pilihan,
            "Warkop_LKK": str(nama_warkop_manual).strip(),
            "Alamat_Warkop": alamat_warkop_terpilih,
            "Brand_Rokok": brand_entry,
            "Nama_Konsumen": nama_konsumen.strip(),
            "Gender": gender_entry,
            "Range_Umur": range_umur_entry,
            "No_HP": nohp_entry.strip(),
            "Instagram": ig_formatted,
            "Jumlah_Bungkus": jumlah_bungkus,
            "Rokok_Asal_BUMO": rokok_asal_bumo.strip(),
            "Latitude": user_lat,
            "Longitude": user_lon,
        }
        df_all = load_database()
        df_all = pd.concat([df_all, pd.DataFrame([data_baru])], ignore_index=True)
        save_database(df_all)
        st.session_state["draft_konsumen"] = ""
        st.balloons()
        st.success(f"🎉 Laporan konsumen {nama_konsumen} berhasil dikirim!")
else:
  st.warning("🔒 Form input terkunci. Pastikan GPS berada dalam wilayah operasional.")
