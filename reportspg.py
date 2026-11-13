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
# CUSTOM CSS UNTUK UI MODERN & TOMBOL BESAR LOGIN
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
    "Black Matcha Siro",
    "Black Matcha Kuro",
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
    "Black Matcha Siro": {"target_spg": 40, "target_team": 80},
    "Black Matcha Kuro": {"target_spg": 40, "target_team": 80},
    "D.Super 12": {"target_spg": 40, "target_team": 80},
    "D.76 Apel Royal": {"target_spg": 40, "target_team": 80},
    "D.76 Apel": {"target_spg": 30, "target_team": 60},
    "Djarum 76 Aksara": {"target_spg": 30, "target_team": 60},
}


def get_target_spg(brand):
  if brand in ["Black Matcha Siro", "Black Matcha Kuro"]:
    return 40
  return TARGET_RULES.get(brand, {"target_spg": 25, "target_team": 50})["target_spg"]


def get_target_team(brand):
  if brand in ["Black Matcha Siro", "Black Matcha Kuro"]:
    return 80
  return TARGET_RULES.get(brand, {"target_spg": 25, "target_team": 50})["target_team"]


def cek_status_target_spg_val(brand, omset_spg):
  target_val = get_target_spg(brand)
  return "Achieved" if omset_spg >= target_val else "Not Achieved"


def cek_status_target_team_val(brand, omset_team):
  target_val = get_target_team(brand)
  return "Achieved" if omset_team >= target_val else "Not Achieved"


def style_status_target(val):
  if val == "Not Achieved":
    return "color: #d32f2f; font-weight: bold;"
  elif val == "Achieved":
    return "color: #16a34a; font-weight: bold;"
  return ""


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
      if st.button(
          "🏠 Dashboard Utama", use_container_width=True, type="primary"
      ):
        st.session_state["admin_view"] = "Dashboard"
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

  # --- TAMPILAN MASTER PLAT KENDARAAN (TAMBAH & HAPUS FLEKSIBEL) ---
  if st.session_state["admin_view"] == "Master_Plat":
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
    st.markdown("#### 📋 Ringkasan Alokasi Brand Seluruh Team (1 - 20)")
    summary_list = []
    for i in range(1, 21):
      t_name = f"Team SPG {i}"
      b_list = team_brands_dict.get(t_name, [])
      summary_list.append({"Team": t_name, "Brand Diizinkan": ", ".join(b_list) if b_list else "(Belum ada brand)"})
    
    st.dataframe(pd.DataFrame(summary_list), use_container_width=True)

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
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
    st.caption("Kelola daftar merek rokok beserta aturan target omset per SPG dan Team.")

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
            TARGET_RULES[b_clean] = {
                "target_spg": int(t_spg),
                "target_team": int(t_team),
            }
            st.success(f"✅ Merek rokok '{b_clean}' berhasil ditambahkan!")
            st.rerun()
          else:
            st.warning("Merek rokok tersebut sudah ada dalam daftar.")
        else:
          st.warning("Mohon masukkan nama merek rokok.")

    st.markdown("---")
    st.markdown("#### 📋 Daftar Merek Rokok & Aturan Target")
    for idx, b in enumerate(current_brands):
      t_s = get_target_spg(b)
      t_t = get_target_team(b)
      col_b1, col_b2, col_b3 = st.columns([0.5, 0.3, 0.2])
      with col_b1:
        st.write(
            f"**{idx+1}. {b}**\n- Target SPG: `{t_s} bks`\n-"
            f" Target Team: `{t_t} bks`"
        )
      with col_b2:
        st.write("")
      with col_b3:
        if st.button("🗑️ Hapus", key=f"del_brand_{idx}"):
          current_brands.pop(idx)
          save_master_brands(current_brands)
          st.success("Merek rokok berhasil dihapus!")
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
          kec_col_name = next(
              (c for c in df_lokasi_excel.columns if "kec" in c.lower() or "wilayah" in c.lower()),
              "Kecamatan",
          )
          warkop_col_name = next(
              (c for c in df_lokasi_excel.columns if "warkop" in c.lower() or "lkk" in c.lower() or "nama" in c.lower()),
              "Warkop_LKK",
          )
          alamat_col_name = next(
              (c for c in df_lokasi_excel.columns if "alamat" in c.lower() or "address" in c.lower()),
              "Alamat_Warkop",
          )

          new_row = {
              kec_col_name: col_kec_input.strip(),
              warkop_col_name: col_warkop_input.strip(),
              alamat_col_name: col_alamat_input.strip() if col_alamat_input else "-"
          }
          df_lokasi_excel = pd.concat(
              [df_lokasi_excel, pd.DataFrame([new_row])], ignore_index=True
          )
          if save_master_lokasi_excel(df_lokasi_excel):
            st.success(f"✅ Warkop '{col_warkop_input.strip()}' berhasil ditambahkan!")
            st.rerun()
        else:
          st.warning("Mohon isi nama Kecamatan dan Nama Warkop/LKK.")

    st.markdown("---")
    st.markdown("#### 📋 Preview Data Warkop/LKK dari Excel")
    if not df_lokasi_excel.empty:
      edited_df = st.data_editor(
          df_lokasi_excel, use_container_width=True, key="editor_excel_warkop"
      )
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
      df_all_users["Jumlah_Bungkus"] = pd.to_numeric(
          df_all_users["Jumlah_Bungkus"], errors="coerce"
      ).fillna(0)

      c1, c2 = st.columns(2)
      with c1:
        st.markdown("#### 👥 Demografi Konsumen (Gender)")
        gender_count = df_all_users["Gender"].value_counts()
        st.bar_chart(gender_count)
      with c2:
        st.markdown("#### 📊 Sebaran Range Umur Konsumen")
        if "Range_Umur" in df_all_users.columns:
          age_count = df_all_users["Range_Umur"].value_counts()
          st.bar_chart(age_count)
        else:
          st.info("Data Range Umur belum tersedia.")

      st.markdown("---")
      st.markdown("#### 🏙️ Sebaran per Wilayah (Kota/Kab)")
      kota_count = df_all_users["Kota_Kab"].value_counts()
      st.bar_chart(kota_count)

      st.markdown("---")
      st.markdown("#### 🗺️ Sebaran Kunjungan & Omset per Kecamatan")

      list_kota_analitik = ["Semua Wilayah"] + sorted(
          df_all_users["Kota_Kab"].dropna().unique().tolist()
      )
      pilih_kota_kec = st.selectbox(
          "Filter Kota/Kabupaten untuk Sebaran Kecamatan", list_kota_analitik
      )

      df_kec_analitik = df_all_users.copy()
      if pilih_kota_kec != "Semua Wilayah":
        df_kec_analitik = df_kec_analitik[
            df_kec_analitik["Kota_Kab"] == pilih_kota_kec
        ]

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

        chart_kec = df_sebaran_kec.set_index("Kecamatan")[
            "Total_Omset_Bungkus"
        ]
        st.bar_chart(chart_kec)
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
    st.markdown("## 🗺️ Visualisasi Peta Rute Perjalanan (All User)")
    st.caption("Pantau rute dan titik kunjungan lapangan berdasarkan filter Team SPG, Nama SPG, dan Tanggal.")

    df_peta_all = load_database()
    if not df_peta_all.empty and "Latitude" in df_peta_all.columns:
      df_peta_all["Waktu_Dt"] = pd.to_datetime(
          df_peta_all["Waktu"], errors="coerce"
      )
      df_peta_all["Tanggal"] = df_peta_all["Waktu_Dt"].dt.date
      df_peta_all = df_peta_all.dropna(subset=["Latitude", "Longitude"])

      col_p1, col_p2, col_p3 = st.columns(3)
      with col_p1:
        list_team_filter = ["Semua Team"] + sorted(
            df_peta_all["Promotor"].dropna().unique().tolist()
        )
        pilih_team = st.selectbox("Filter Team SPG", list_team_filter)

      with col_p2:
        list_spg_filter = ["Semua SPG"] + sorted(
            df_peta_all["Nama_SPG"].dropna().unique().tolist()
        )
        pilih_spg = st.selectbox("Filter Nama SPG", list_spg_filter)

      with col_p3:
        list_tgl_filter = ["Semua Tanggal"] + sorted(
            df_peta_all["Tanggal"].dropna().unique().tolist(), reverse=True
        )
        pilih_tgl = st.selectbox("Filter Tanggal", list_tgl_filter)

      df_filtered_map = df_peta_all.copy()
      if pilih_team != "Semua Team":
        df_filtered_map = df_filtered_map[
            df_filtered_map["Promotor"] == pilih_team
        ]
      if pilih_spg != "Semua SPG":
        df_filtered_map = df_filtered_map[
            df_filtered_map["Nama_SPG"] == pilih_spg
        ]
      if pilih_tgl != "Semua Tanggal":
        df_filtered_map = df_filtered_map[
            df_filtered_map["Tanggal"] == pilih_tgl
        ]

      if not df_filtered_map.empty:
        df_filtered_map = df_filtered_map.sort_values("Waktu")
        koordinat_rute = df_filtered_map[
            ["Longitude", "Latitude"]
        ].values.tolist()
        center_lat = df_filtered_map["Latitude"].mean()
        center_lon = df_filtered_map["Longitude"].mean()

        path_layer = pdk.Layer(
            "PathLayer",
            data=[{"path": koordinat_rute, "name": "Rute Perjalanan"}],
            get_path="path",
            get_color=[211, 47, 47, 200],
            get_width=6,
            pickable=True,
        )

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_filtered_map,
            get_position=["Longitude", "Latitude"],
            get_color=[0, 128, 255, 200],
            get_radius=60,
            pickable=True,
        )

        view_state = pdk.ViewState(
            latitude=center_lat, longitude=center_lon, zoom=12, pitch=35
        )

        deck_map = pdk.Deck(
            layers=[path_layer, scatter_layer],
            initial_view_state=view_state,
            tooltip={
                "html": (
                    "<b>Team:</b> {Promotor} ({Nama_SPG})<br/><b>Plat Mobil:</b> {Plat_Mobil}<br/><b>Warkop:</b>"
                    " {Warkop_LKK} ({Kecamatan})<br/><b>Brand:</b>"
                    " {Brand_Rokok} ({Jumlah_Bungkus} bks)<br/><b>Waktu:</b>"
                    " {Waktu}"
                ),
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

  st.markdown("#### 📦 Master Data")
  col_m1, col_m2, col_m3 = st.columns(3)
  with col_m1:
    if st.button("👥 Master Team & Brand\nAtur brand rokok per team", use_container_width=True):
      st.session_state["admin_view"] = "Master_Team"
      st.rerun()
    if st.button("👩‍💼 Nama SPG\nKelola daftar SPG", use_container_width=True):
      st.session_state["admin_view"] = "Master_SPG"
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
    df_all_users["Waktu_Dt"] = pd.to_datetime(
        df_all_users["Waktu"], errors="coerce"
    )
    df_all_users["Tanggal"] = df_all_users["Waktu_Dt"].dt.date
    df_all_users["Jumlah_Bungkus"] = pd.to_numeric(
        df_all_users["Jumlah_Bungkus"], errors="coerce"
    ).fillna(0)

    total_omset = int(df_all_users["Jumlah_Bungkus"].sum())
    total_konsumen = len(df_all_users)
    total_warkop = df_all_users["Warkop_LKK"].nunique()
    total_team_aktif = df_all_users["Promotor"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
      st.markdown(
          f'<div class="kpi-card"><div class="kpi-value">{total_omset:,}</div>'
          '<div class="kpi-label">Total Omset</div></div>',
          unsafe_allow_html=True,
      )
    with k2:
      st.markdown(
          f'<div class="kpi-card"><div class="kpi-value">{total_konsumen:,}'
          '</div><div class="kpi-label">Konsumen Beli</div></div>',
          unsafe_allow_html=True,
      )
    with k3:
      st.markdown(
          f'<div class="kpi-card"><div class="kpi-value">{total_warkop:,}</div>'
          '<div class="kpi-label">Titik Warkop</div></div>',
          unsafe_allow_html=True,
      )
    with k4:
      st.markdown(
          f'<div class="kpi-card"><div class="kpi-value">{total_team_aktif}'
          '</div><div class="kpi-label">Team Aktif</div></div>',
          unsafe_allow_html=True,
      )

    st.markdown("#### 🏆 Leaderboard Team SPG (Berdasarkan Target Team)")
    df_team_leaderboard = (
        df_all_users.groupby(["Promotor", "Kota_Kab", "Brand_Rokok"])
        .agg(
            Total_Omset_Team=("Jumlah_Bungkus", "sum"),
            Total_Konsumen_Beli=("Nama_Konsumen", "count"),
        )
        .reset_index()
    )
    df_team_leaderboard["Target_Team"] = df_team_leaderboard[
        "Brand_Rokok"
    ].apply(get_target_team)
    df_team_leaderboard["Status_Target_Team"] = df_team_leaderboard.apply(
        lambda r: cek_status_target_team_val(r["Brand_Rokok"], r["Total_Omset_Team"]),
        axis=1,
    )

    st.dataframe(
        df_team_leaderboard.style.map(
            style_status_target, subset=["Status_Target_Team"]
        ),
        use_container_width=True,
    )
  else:
    st.info("Belum ada data laporan transaksi SPG masuk.")

  # ====================================================
  # REPORT REKAPITULASI COMBINE PER TITIK LKK (ADMIN)
  # ====================================================
  st.markdown("---")
  st.markdown("#### 📊 Rekapitulasi Combine Per Titik LKK (All Team)")
  st.caption("Gabungan data jumlah kontak manual Supervisi dan penjualan konsumen SPG per titik Warkop/LKK.")

  if not df_all_supervisi.empty:
    df_all_supervisi["Waktu_Dt"] = pd.to_datetime(
        df_all_supervisi["Waktu"], errors="coerce"
    )
    df_all_supervisi["Tanggal"] = df_all_supervisi["Waktu_Dt"].dt.date
    df_all_supervisi["Jumlah_Kontak_Manual"] = pd.to_numeric(
        df_all_supervisi["Jumlah_Kontak_Manual"], errors="coerce"
    ).fillna(0).astype(int)

  # Filter Team untuk Rekapitulasi Combine
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
      columns=["Promotor", "Kota_Kab", "Kecamatan", "Warkop_LKK", "Alamat_Warkop", "SPG_Bertugas", "Brand_Rokok", "Konsumen_Beli", "Total_Omset_Bungkus"]
  )
  if not df_spg_lkk_filtered.empty:
    df_rekap_spg_admin = (
        df_spg_lkk_filtered.groupby(["Promotor", "Kota_Kab", "Kecamatan", "Warkop_LKK", "Alamat_Warkop", "Brand_Rokok"])
        .agg(
            SPG_Bertugas=("Nama_SPG", lambda x: ", ".join(x.dropna().unique())),
            Konsumen_Beli=("Nama_Konsumen", "count"),
            Total_Omset_Bungkus=("Jumlah_Bungkus", "sum")
        )
        .reset_index()
    )
    df_rekap_spg_admin["Target_Omset_Team"] = df_rekap_spg_admin["Brand_Rokok"].apply(get_target_team)

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
      df_combine_admin["Brand_Rokok"] = "-"
      df_combine_admin["Target_Omset_Team"] = 0
      df_combine_admin["Konsumen_Beli"] = 0
      df_combine_admin["Total_Omset_Bungkus"] = 0
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
          "Brand_Rokok": "-",
          "Target_Omset_Team": 0,
          "Plat_Mobil_Supervisi": "-",
          "Jumlah_Kontak_Manual": 0,
          "Konsumen_Beli": 0,
          "Total_Omset_Bungkus": 0,
      })

    df_combine_admin["Plat_Mobil_Supervisi"] = df_combine_admin["Plat_Mobil_Supervisi"].replace("", "-")
    df_combine_admin["Jumlah_Kontak_Manual"] = df_combine_admin["Jumlah_Kontak_Manual"].astype(int)
    df_combine_admin["Konsumen_Beli"] = df_combine_admin["Konsumen_Beli"].astype(int)
    df_combine_admin["Total_Omset_Bungkus"] = df_combine_admin["Total_Omset_Bungkus"].astype(int)
    df_combine_admin["Target_Omset_Team"] = df_combine_admin["Target_Omset_Team"].astype(int)

    cols_combine_order = [
        "Promotor",
        "Plat_Mobil_Supervisi",
        "Kota_Kab",
        "Kecamatan",
        "Warkop_LKK",
        "Alamat_Warkop",
        "SPG_Bertugas",
        "Brand_Rokok",
        "Target_Omset_Team",
        "Jumlah_Kontak_Manual",
        "Konsumen_Beli",
        "Total_Omset_Bungkus",
    ]
    df_combine_admin = df_combine_admin[cols_combine_order].sort_values(
        by=["Total_Omset_Bungkus", "Jumlah_Kontak_Manual"], ascending=False
    )

    st.dataframe(df_combine_admin, use_container_width=True)

    # Tombol Export Excel Rekap Combine LKK
    output_lkk = BytesIO()
    with pd.ExcelWriter(output_lkk, engine="openpyxl") as writer:
      df_combine_admin.to_excel(writer, index=False, sheet_name="Rekap Combine LKK")
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

  # ====================================================
  # MENU HAPUS DATA KONTAK SUPERVISI (REKAP LKK)
  # ====================================================
  with st.expander("🗑️ Menu Hapus Data Kontak Supervisi / Rekap LKK (Per Row / Hari / Minggu / All Data)", expanded=False):
    if not df_all_supervisi.empty:
      st.warning("⚠️ Perhatian: Menghapus log kontak Supervisi akan memengaruhi angka 'Jumlah_Kontak_Manual' pada tabel Rekapitulasi Combine Per Titik LKK di atas.")
      tab_sup_row, tab_sup_day, tab_sup_week, tab_sup_all = st.tabs([
          "🔹 Hapus per Row",
          "📅 Hapus per Hari",
          "📆 Hapus per Minggu",
          "🚨 Hapus All Data"
      ])

      with tab_sup_row:
        df_sup_indexed = df_all_supervisi.reset_index()
        opsi_sup_rows = [
            f"ID #{row['index']} | {row['Waktu']} | {row['Promotor']} ({row['Plat_Mobil']}) - {row['Warkop_LKK']} ({row['Kecamatan']}): {int(row['Jumlah_Kontak_Manual'])} kontak"
            for _, row in df_sup_indexed.sort_values(by="Waktu", ascending=False).iterrows()
        ]
        selected_sup_rows = st.multiselect(
            "Pilih baris log kontak Supervisi yang akan dihapus:",
            options=opsi_sup_rows,
            key="ms_del_sup_rows"
        )
        if st.button("🗑️ Hapus Baris Kontak Terpilih", type="primary", key="btn_del_sup_row"):
          if selected_sup_rows:
            indices_sup_drop = [
                int(item.split(" | ")[0].replace("ID #", ""))
                for item in selected_sup_rows
            ]
            df_sup_clean = df_all_supervisi.drop(index=indices_sup_drop).drop(
                columns=["Waktu_Dt", "Tanggal"], errors="ignore"
            )
            save_supervisi_database(df_sup_clean)
            st.success(f"✅ Berhasil menghapus {len(indices_sup_drop)} baris data kontak Supervisi!")
            st.rerun()
          else:
            st.warning("Silakan pilih minimal 1 baris data terlebih dahulu.")

      with tab_sup_day:
        daftar_tgl_sup = sorted(
            df_all_supervisi["Tanggal"].dropna().unique().tolist(), reverse=True
        )
        if daftar_tgl_sup:
          tgl_sup_hapus = st.selectbox(
              "Pilih Tanggal Log Kontak Supervisi yang akan dihapus:",
              options=daftar_tgl_sup,
              key="sb_del_sup_day"
          )
          jml_sup_hari = len(df_all_supervisi[df_all_supervisi["Tanggal"] == tgl_sup_hapus])
          st.info(f"Terdapat **{jml_sup_hari} entri kontak Supervisi** pada tanggal **{tgl_sup_hapus}**.")
          if st.button(f"🗑️ Hapus Data Kontak Tanggal {tgl_sup_hapus}", type="primary", key="btn_del_sup_day"):
            df_sup_clean = df_all_supervisi[df_all_supervisi["Tanggal"] != tgl_sup_hapus].drop(
                columns=["Waktu_Dt", "Tanggal"], errors="ignore"
            )
            save_supervisi_database(df_sup_clean)
            st.success(f"✅ Seluruh data kontak Supervisi ({jml_sup_hari} baris) pada tanggal {tgl_sup_hapus} berhasil dihapus!")
            st.rerun()
        else:
          st.info("Tidak ada data tanggal valid untuk dihapus.")

      with tab_sup_week:
        df_sup_valid_dt = df_all_supervisi.dropna(subset=["Waktu_Dt"]).copy()
        if not df_sup_valid_dt.empty:
          iso_sup_cal = df_sup_valid_dt["Waktu_Dt"].dt.isocalendar()
          df_sup_valid_dt["Year_Week"] = (
              iso_sup_cal["year"].astype(str)
              + "-W"
              + iso_sup_cal["week"].astype(str).str.zfill(2)
          )
          sup_week_options = {}
          for yw, group in df_sup_valid_dt.groupby("Year_Week"):
            min_d = group["Tanggal"].min()
            max_d = group["Tanggal"].max()
            label = f"{yw} ({min_d} s/d {max_d}) — {len(group)} entri kontak"
            sup_week_options[label] = yw

          sorted_sup_week_labels = sorted(sup_week_options.keys(), reverse=True)
          pilih_sup_minggu_label = st.selectbox(
              "Pilih Minggu Log Kontak Supervisi yang akan dihapus:",
              options=sorted_sup_week_labels,
              key="sb_del_sup_week"
          )
          if st.button("🗑️ Hapus Data Kontak Minggu Terpilih", type="primary", key="btn_del_sup_week"):
            target_sup_yw = sup_week_options[pilih_sup_minggu_label]
            iso_sup_all = df_all_supervisi["Waktu_Dt"].dt.isocalendar()
            yw_sup_series = (
                iso_sup_all["year"].astype(str)
                + "-W"
                + iso_sup_all["week"].astype(str).str.zfill(2)
            )
            df_sup_clean = df_all_supervisi[yw_sup_series != target_sup_yw].drop(
                columns=["Waktu_Dt", "Tanggal"], errors="ignore"
            )
            save_supervisi_database(df_sup_clean)
            st.success(f"✅ Data kontak Supervisi pada minggu {target_sup_yw} berhasil dihapus!")
            st.rerun()
        else:
          st.info("Tidak ada data waktu valid untuk pengelompokan mingguan.")

      with tab_sup_all:
        st.error(
            f"🚨 Tindakan ini akan menghapus **SELURUH ({len(df_all_supervisi)} baris)** log kontak Supervisi secara permanen!"
        )
        konfirmasi_hapus_sup_all = st.checkbox(
            "Izin konfirmasi hapus seluruh data kontak Supervisi.",
            key="chk_del_sup_all"
        )
        if st.button("🔥 KOSONGKAN SEMUA DATA KONTAK SUPERVISI", type="primary", key="btn_del_sup_all"):
          if konfirmasi_hapus_sup_all:
            df_sup_empty = pd.DataFrame(columns=EXPECTED_SUPERVISI_COLUMNS)
            save_supervisi_database(df_sup_empty)
            st.success("✅ Seluruh database kontak Supervisi telah dikosongkan!")
            st.rerun()
          else:
            st.warning("Centang kotak konfirmasi terlebih dahulu sebelum menghapus seluruh data.")

      st.markdown("##### 📋 Preview Log Input Kontak Manual Supervisi")
      st.dataframe(
          df_all_supervisi.drop(columns=["Waktu_Dt", "Tanggal"], errors="ignore").sort_values(
              by="Waktu", ascending=False
          ),
          use_container_width=True,
      )
    else:
      st.info("Belum ada data log input kontak manual dari Supervisi.")

  # ====================================================
  # LOG DETAIL TRANSAKSI ALL USER (SPG) & MENU HAPUS
  # ====================================================
  if not df_all_users.empty:
    st.markdown("---")
    st.markdown("#### 📑 Log Detail Transaksi All User (SPG)")

    with st.expander("🗑️ Menu Hapus Log Detail Transaksi SPG (Per Row / Hari / Minggu / All Data)", expanded=False):
      st.warning("⚠️ Perhatian: Data yang sudah dihapus dari database tidak dapat dikembalikan.")
      tab_del_row, tab_del_day, tab_del_week, tab_del_all = st.tabs([
          "🔹 Hapus per Row",
          "📅 Hapus per Hari",
          "📆 Hapus per Minggu",
          "🚨 Hapus All Data"
      ])

      with tab_del_row:
        df_indexed = df_all_users.reset_index()
        opsi_rows = [
            f"ID #{row['index']} | {row['Waktu']} | {row['Promotor']} ({row['Nama_SPG']}) - {row['Nama_Konsumen']} ({row['Brand_Rokok']}: {int(row['Jumlah_Bungkus'])} bks)"
            for _, row in df_indexed.sort_values(by="Waktu", ascending=False).iterrows()
        ]
        selected_rows = st.multiselect(
            "Pilih baris transaksi yang akan dihapus:",
            options=opsi_rows,
            key="ms_del_rows"
        )
        if st.button("🗑️ Hapus Baris Terpilih", type="primary", key="btn_del_row"):
          if selected_rows:
            indices_to_drop = [
                int(item.split(" | ")[0].replace("ID #", ""))
                for item in selected_rows
            ]
            df_clean = df_all_users.drop(index=indices_to_drop).drop(
                columns=["Waktu_Dt", "Tanggal"], errors="ignore"
            )
            save_database(df_clean)
            st.success(f"✅ Berhasil menghapus {len(indices_to_drop)} baris transaksi!")
            st.rerun()
          else:
            st.warning("Silakan pilih minimal 1 baris transaksi terlebih dahulu.")

      with tab_del_day:
        daftar_tanggal = sorted(
            df_all_users["Tanggal"].dropna().unique().tolist(), reverse=True
        )
        if daftar_tanggal:
          tgl_hapus = st.selectbox(
              "Pilih Tanggal Transaksi yang akan dihapus:",
              options=daftar_tanggal,
              key="sb_del_day"
          )
          jml_data_hari = len(df_all_users[df_all_users["Tanggal"] == tgl_hapus])
          st.info(f"Terdapat **{jml_data_hari} transaksi** pada tanggal **{tgl_hapus}**.")
          if st.button(f"🗑️ Hapus Semua Data Tanggal {tgl_hapus}", type="primary", key="btn_del_day"):
            df_clean = df_all_users[df_all_users["Tanggal"] != tgl_hapus].drop(
                columns=["Waktu_Dt", "Tanggal"], errors="ignore"
            )
            save_database(df_clean)
            st.success(f"✅ Seluruh data ({jml_data_hari} baris) pada tanggal {tgl_hapus} berhasil dihapus!")
            st.rerun()
        else:
          st.info("Tidak ada data tanggal valid untuk dihapus.")

      with tab_del_week:
        df_valid_dt = df_all_users.dropna(subset=["Waktu_Dt"]).copy()
        if not df_valid_dt.empty:
          iso_cal = df_valid_dt["Waktu_Dt"].dt.isocalendar()
          df_valid_dt["Year_Week"] = (
              iso_cal["year"].astype(str)
              + "-W"
              + iso_cal["week"].astype(str).str.zfill(2)
          )
          week_options = {}
          for yw, group in df_valid_dt.groupby("Year_Week"):
            min_d = group["Tanggal"].min()
            max_d = group["Tanggal"].max()
            label = f"{yw} ({min_d} s/d {max_d}) — {len(group)} transaksi"
            week_options[label] = yw

          sorted_week_labels = sorted(week_options.keys(), reverse=True)
          pilih_minggu_label = st.selectbox(
              "Pilih Minggu Transaksi yang akan dihapus:",
              options=sorted_week_labels,
              key="sb_del_week"
          )
          if st.button("🗑️ Hapus Semua Data Minggu Terpilih", type="primary", key="btn_del_week"):
            target_yw = week_options[pilih_minggu_label]
            iso_all = df_all_users["Waktu_Dt"].dt.isocalendar()
            yw_series = (
                iso_all["year"].astype(str)
                + "-W"
                + iso_all["week"].astype(str).str.zfill(2)
            )
            df_clean = df_all_users[yw_series != target_yw].drop(
                columns=["Waktu_Dt", "Tanggal"], errors="ignore"
            )
            save_database(df_clean)
            st.success(f"✅ Data pada minggu {target_yw} berhasil dihapus!")
            st.rerun()
        else:
          st.info("Tidak ada data waktu valid untuk pengelompokan mingguan.")

      with tab_del_all:
        st.error(
            f"🚨 Tindakan ini akan menghapus **SELURUH ({len(df_all_users)} baris)** data transaksi dari database secara permanen!"
        )
        konfirmasi_hapus_all = st.checkbox(
            "Izin konfirmasi hapus seluruh data transaksi.",
            key="chk_del_all"
        )
        if st.button("🔥 KOSONGKAN SEMUA DATA TRANSAKSI", type="primary", key="btn_del_all"):
          if konfirmasi_hapus_all:
            df_empty = pd.DataFrame(columns=EXPECTED_COLUMNS)
            save_database(df_empty)
            st.success("✅ Seluruh database transaksi telah dikosongkan!")
            st.rerun()
          else:
            st.warning("Centang kotak konfirmasi terlebih dahulu sebelum menghapus seluruh data.")

    st.dataframe(
        df_all_users.drop(columns=["Waktu_Dt", "Tanggal"], errors="ignore").sort_values(
            by="Waktu", ascending=False
        ),
        use_container_width=True,
    )

  st.stop()

# ====================================================
# HALAMAN LOGIN UTAMA (LOGIN SPG DENGAN NAMA TEAM, LOGIN SUPERVISI DENGAN PILIHAN TEAM & PLAT KENDARAAN)
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

    st.markdown("#### 🚀 Pilih Mode Masuk & Identitas Operasional")
    
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

    with st.container():
      list_team = [f"Team SPG {i}" for i in range(1, 21)]
      
      pilihan_user = st.selectbox(
          "👤 Pilih Nama Team",
          list_team,
          key="selected_team_login",
          on_change=reset_session_on_user_change,
      )

      # Jika mode Supervisi, tampilkan juga opsi pilihan Plat Nomor Kendaraan secara fleksibel
      pilihan_plat_supervisi = ""
      if st.session_state["login_mode"] == "Supervisi":
        daftar_plat_master = load_master_plat_kendaraan()
        if not daftar_plat_master:
          daftar_plat_master = ["L 1234 ABC"]
        pilihan_plat_supervisi = st.selectbox(
            "🚗 Pilih Plat Nomor Kendaraan Operasional",
            daftar_plat_master,
            key="selected_plat_supervisi_login"
        )

      has_schedule, schedule_warning_msg, auto_detected_kota = get_schedule_info_for_team(pilihan_user)

      if not has_schedule:
        st.error(f"⚠️ **Tidak Ada Jadwal Team Tersebut Untuk Hari Ini**")
      else:
        st.info(f"🏙️ Wilayah Terdeteksi dari Jadwal Hari Ini: **{auto_detected_kota}**")

      st.markdown("")
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

    st.markdown(
        """
        <div class="footer-note">
            Gunakan sidebar kiri untuk masuk ke menu <b>Dashboard Admin</b>.<br/>
            © 2026 Tumarso Monitoring System
        </div>
        """,
        unsafe_allow_html=True,
    )

  st.stop()

# ====================================================
# APLIKASI UTAMA SETELAH LOGIN BERHASIL (SPG / SUPERVISI)
# ====================================================
col_banner, col_logout = st.columns([0.78, 0.22])

with col_banner:
  mode_badge = "👀 Mode Supervisi" if st.session_state['login_mode'] == "Supervisi" else "📝 Mode SPG"
  st.markdown(
      f"""
      <div class="user-banner">
          <div class="user-banner-title">👤 {st.session_state['user_spg']} &nbsp;|&nbsp; <span style="font-size: 0.9rem; color: #38bdf8;">{mode_badge}</span></div>
          <div class="user-banner-sub">
              🚗 Plat Mobil: <b>{st.session_state['plat_mobil']}</b> &nbsp;|&nbsp; 🏙️ Wilayah: <b>{st.session_state['kota_kab']}</b>
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

col_kec = None
daftar_kecamatan = []
if gdf_wilayah is not None:
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
# GPS & DETEKSI OTOMATIS KECAMATAN (REVERSE GEOFENCE)
# ====================================================
loc = get_geolocation()
detected_kecamatan = None

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
    for idx_geom, row_geom in gdf_wilayah.iterrows():
      geom = row_geom.geometry
      if geom is not None and (
          geom.contains(point_user) or geom.intersects(point_user)
      ):
        is_inside_geofence = True
        if col_kec and pd.notna(row_geom[col_kec]):
          detected_kecamatan = str(row_geom[col_kec]).strip()
        break
  else:
    is_inside_geofence = True

if is_inside_geofence:
  info_kec_gps = (
      f"Kecamatan **{detected_kecamatan}**"
      if detected_kecamatan
      else "Wilayah Terdeteksi"
  )
  st.success(
      f"📍 **Status GPS (Valid & Terkunci di Wilayah):**\n\n"
      f"- **Koordinat:** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}` (Akurasi:"
      f" ±{akurasi_meter}m)\n"
      f"- **Lokasi Terdeteksi:** {info_kec_gps} —"
      f" **{st.session_state['kota_kab']}** (✅ Dalam Area Operasional)"
  )
else:
  st.error(
      f"🚨 **Peringatan Lock GPS (Diluar Wilayah Operasional):**\n\n"
      f"- **Koordinat Anda:** Lat: `{user_lat:.6f}`, Lon: `{user_lon:.6f}`\n"
      f"- **Wilayah Terpilih (Jadwal):** **{st.session_state['kota_kab']}**\n\n"
      "⚠️ Posisi Anda terdeteksi berada di luar batas zona GeoJSON wilayah"
      f" {st.session_state['kota_kab']}."
  )

# ====================================================
# VALIDASI JADWAL SPG DARI EXCEL (Jadwal SPG.xlsx)
# ====================================================
df_jadwal_raw = load_jadwal_spg()
daftar_kecamatan_terjadwal = []
if not df_jadwal_raw.empty:
  kota_col_j = next((c for c in df_jadwal_raw.columns if "kota" in c.lower()), None)
  kec_col_j = next((c for c in df_jadwal_raw.columns if "kecamatan" in c.lower()), None)
  
  if kota_col_j and kec_col_j:
    today_date = datetime.now().date()
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
      team_digit = ''.join(filter(str.isdigit, team_clean))
      
      for _, row in df_jadwal_raw.iterrows():
        val_cell = str(row[today_col]).strip()
        if val_cell and val_cell.lower() != "nan" and val_cell != "-":
          val_lower = val_cell.lower()
          cell_digit = ''.join(filter(str.isdigit, val_lower))
          if team_clean == val_lower or (team_digit and cell_digit and team_digit == cell_digit and len(team_digit) == len(cell_digit)):
            k_val = str(row[kec_col_j]).strip()
            if k_val and k_val not in daftar_kecamatan_terjadwal:
              daftar_kecamatan_terjadwal.append(k_val)

if not daftar_kecamatan_terjadwal:
  daftar_kecamatan_terjadwal = daftar_kecamatan if daftar_kecamatan else ["Kecamatan Umum"]

st.markdown("### 📋 Lokasi Kunjungan Lapangan")

kecamatan_pilihan = st.selectbox(
    f"Pilih Kecamatan Tujuan Kunjungan Berdasarkan Jadwal ({st.session_state['kota_kab']})",
    options=daftar_kecamatan_terjadwal,
    help="Kecamatan difilter otomatis sesuai penugasan jadwal hari ini"
)

# Filter warkop/LKK
df_master_excel = load_master_lokasi_excel()
filtered_df_warkop = pd.DataFrame()

if not df_master_excel.empty:
  col_kec_excel = next((c for c in df_master_excel.columns if "kec" in c.lower() or "wilayah" in c.lower()), None)
  col_warkop_excel = next((c for c in df_master_excel.columns if "warkop" in c.lower() or "lkk" in c.lower() or "nama" in c.lower()), None)
  col_alamat_excel = next((c for c in df_master_excel.columns if "alamat" in c.lower() or "address" in c.lower()), None)

  if col_kec_excel and col_warkop_excel:
    mask = (
        df_master_excel[col_kec_excel].astype(str).str.strip().str.lower()
        == str(kecamatan_pilihan).strip().lower()
    )
    filtered_df_warkop = df_master_excel[mask]
    if filtered_df_warkop.empty:
      filtered_df_warkop = df_master_excel.copy()

  if not filtered_df_warkop.empty and col_warkop_excel:
    filtered_warkop_list = filtered_df_warkop[col_warkop_excel].dropna().unique().tolist()
  else:
    filtered_warkop_list = ["Warkop Alternatif 1", "Warkop Alternatif 2"]
else:
  filtered_warkop_list = ["Warkop Alternatif 1", "Warkop Alternatif 2"]

if not filtered_warkop_list:
  filtered_warkop_list = ["Warkop Alternatif 1", "Warkop Alternatif 2"]

nama_warkop_manual = st.selectbox(
    f"Pilih Warkop / LKK (Titik Wajib Kunjung) di {kecamatan_pilihan}",
    options=filtered_warkop_list,
    help="Daftar warkop difilter otomatis dari Master WarkopLKK.xlsx",
)

# Alamat warkop otomatis di bawahnya
alamat_warkop_terpilih = "-"
if not df_master_excel.empty and col_warkop_excel and col_alamat_excel:
  match_row = df_master_excel[df_master_excel[col_warkop_excel].astype(str).str.strip() == str(nama_warkop_manual).strip()]
  if not match_row.empty:
    alamat_warkop_terpilih = str(match_row.iloc[0][col_alamat_excel])

st.markdown(
    f"""
    <div class="address-box">
        📍 <b>Alamat Warkop / LKK Wajib Kunjung:</b> {alamat_warkop_terpilih}
    </div>
    """,
    unsafe_allow_html=True,
)

# ====================================================
# JIKA KONDISI LOGIN SUPERVISI: TAMPILKAN MENU MONITORING & ENTRY KONTAK
# ====================================================
if st.session_state["login_mode"] == "Supervisi":
  st.markdown("---")
  st.markdown(f"### 👀 Dashboard Monitoring & Entry Supervisi: {st.session_state['user_spg']} (Plat Mobil: `{st.session_state['plat_mobil']}`)")
  st.caption("Supervisor menginput jumlah kontak konsumen di warkop ini secara manual.")

  # Form Supervisi untuk Entry Manual Jumlah Kontak Konsumen
  with st.form("form_entry_kontak_supervisi"):
    st.markdown("#### 📝 Input Manual Jumlah Kontak Konsumen (Oleh Supervisi)")
    jumlah_kontak_input = st.number_input(
        f"Jumlah Kontak Konsumen di {nama_warkop_manual}",
        min_value=0,
        step=1,
        value=0,
        help="Masukkan jumlah total orang/konsumen yang berhasil dikontak di warkop ini"
    )
    btn_simpan_kontak = st.form_submit_button("💾 Simpan Jumlah Kontak Warkop Ini", type="primary")

    if btn_simpan_kontak:
      df_sup_db = load_supervisi_database()
      new_sup_row = {
          "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
      st.success(f"✅ Berhasil mencatat **{jumlah_kontak_input} kontak konsumen** untuk warkop **{nama_warkop_manual}**!")

  st.markdown("---")

  # Ambil data dari database transaksi SPG & database kontak supervisi
  df_all_db = load_database()
  df_sup_db = load_supervisi_database()

  df_current_team_spg = pd.DataFrame()
  if not df_all_db.empty and "Promotor" in df_all_db.columns:
    df_current_team_spg = df_all_db[df_all_db["Promotor"] == st.session_state["user_spg"]].copy()

  df_current_team_sup = pd.DataFrame()
  if not df_sup_db.empty and "Promotor" in df_sup_db.columns:
    df_current_team_sup = df_sup_db[df_sup_db["Promotor"] == st.session_state["user_spg"]].copy()

  # Filter transaksi SPG per LKK aktif
  df_lkk_active_spg = pd.DataFrame()
  if not df_current_team_spg.empty:
    df_current_team_spg["Jumlah_Bungkus"] = pd.to_numeric(df_current_team_spg["Jumlah_Bungkus"], errors="coerce").fillna(0)
    df_lkk_active_spg = df_current_team_spg[df_current_team_spg["Warkop_LKK"].astype(str).str.strip() == str(nama_warkop_manual).strip()]

  # Ambil total kontak manual supervisi terbaru untuk LKK aktif ini
  kontak_manual_lkk_ini = 0
  if not df_current_team_sup.empty:
    df_lkk_active_sup = df_current_team_sup[df_current_team_sup["Warkop_LKK"].astype(str).str.strip() == str(nama_warkop_manual).strip()]
    if not df_lkk_active_sup.empty:
      kontak_manual_lkk_ini = int(df_lkk_active_sup["Jumlah_Kontak_Manual"].astype(int).sum())

  col_mon1, col_mon2, col_mon3, col_mon4 = st.columns(4)
  with col_mon1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-value">{kontak_manual_lkk_ini}</div>'
        '<div class="kpi-label">Kontak (Input Supervisi)</div></div>',
        unsafe_allow_html=True,
    )
  with col_mon2:
    total_konsumen_beli = len(df_lkk_active_spg)
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-value">{total_konsumen_beli}</div>'
        '<div class="kpi-label">Konsumen Beli (SPG)</div></div>',
        unsafe_allow_html=True,
    )
  with col_mon3:
    total_omset_lkk = int(df_lkk_active_spg["Jumlah_Bungkus"].sum()) if not df_lkk_active_spg.empty else 0
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-value">{total_omset_lkk:,} bks</div>'
        '<div class="kpi-label">Omset LKK Ini</div></div>',
        unsafe_allow_html=True,
    )
  with col_mon4:
    spg_list_str = ", ".join(df_lkk_active_spg["Nama_SPG"].dropna().unique().tolist()) if not df_lkk_active_spg.empty else "Belum ada SPG"
    st.markdown(
        f'<div class="kpi-card" style="border-left-color: #3b82f6;"><div class="kpi-value" style="font-size: 1.0rem; padding-top: 6px;">{spg_list_str}</div>'
        '<div class="kpi-label">SPG Bertugas</div></div>',
        unsafe_allow_html=True,
    )

  st.markdown("---")
  st.markdown(f"#### 📊 Rekapitulasi Combine Per Titik LKK ({st.session_state['user_spg']})")
  
  df_rekap_spg = pd.DataFrame(columns=["Kecamatan", "Warkop_LKK", "Alamat_Warkop", "Jumlah_SPG_Bertugas", "Brand_Rokok", "Konsumen_Beli", "Total_Omset_Bungkus"])
  if not df_current_team_spg.empty:
    df_rekap_spg = (
        df_current_team_spg.groupby(["Kecamatan", "Warkop_LKK", "Alamat_Warkop", "Brand_Rokok"])
        .agg(
            Jumlah_SPG_Bertugas=("Nama_SPG", lambda x: ", ".join(x.dropna().unique())),
            Konsumen_Beli=("Nama_Konsumen", "count"),
            Total_Omset_Bungkus=("Jumlah_Bungkus", "sum")
        )
        .reset_index()
    )
    df_rekap_spg["Target_Omset_Team"] = df_rekap_spg["Brand_Rokok"].apply(get_target_team)

  df_rekap_sup = pd.DataFrame(columns=["Kecamatan", "Warkop_LKK", "Jumlah_Kontak_Manual"])
  if not df_current_team_sup.empty:
    df_rekap_sup = (
        df_current_team_sup.groupby(["Kecamatan", "Warkop_LKK"])
        .agg(Jumlah_Kontak_Manual=("Jumlah_Kontak_Manual", "sum"))
        .reset_index()
    )

  if not df_rekap_spg.empty or not df_rekap_sup.empty:
    if df_rekap_spg.empty:
      df_combine_rekap = df_rekap_sup.copy()
      df_combine_rekap["Jumlah_SPG_Bertugas"] = "-"
      df_combine_rekap["Brand_Rokok"] = "-"
      df_combine_rekap["Target_Omset_Team"] = 0
      df_combine_rekap["Konsumen_Beli"] = 0
      df_combine_rekap["Total_Omset_Bungkus"] = 0
      df_combine_rekap["Alamat_Warkop"] = "-"
    elif df_rekap_sup.empty:
      df_combine_rekap = df_rekap_spg.copy()
      df_combine_rekap["Jumlah_Kontak_Manual"] = 0
    else:
      df_combine_rekap = pd.merge(
          df_rekap_spg,
          df_rekap_sup,
          on=["Kecamatan", "Warkop_LKK"],
          how="outer"
      ).fillna({"Jumlah_Kontak_Manual": 0, "Konsumen_Beli": 0, "Total_Omset_Bungkus": 0, "Jumlah_SPG_Bertugas": "-", "Brand_Rokok": "-", "Target_Omset_Team": 0, "Alamat_Warkop": "-"})

    df_combine_rekap = df_combine_rekap[
        ["Kecamatan", "Warkop_LKK", "Alamat_Warkop", "Jumlah_SPG_Bertugas", "Brand_Rokok", "Target_Omset_Team", "Jumlah_Kontak_Manual", "Konsumen_Beli", "Total_Omset_Bungkus"]
    ].sort_values(by="Total_Omset_Bungkus", ascending=False)

    st.dataframe(df_combine_rekap, use_container_width=True)
  else:
    st.info("Belum ada data rekapitulasi gabungan untuk team ini.")

  st.markdown("#### 📑 Log Detail Konsumen Beli (SPG) di Warkop Ini")
  if not df_lkk_active_spg.empty:
    st.dataframe(df_lkk_active_spg.drop(columns=["Waktu", "Promotor", "Plat_Mobil"], errors="ignore"), use_container_width=True)
  else:
    st.info(f"Belum ada data konsumen beli masuk untuk titik Warkop / LKK '{nama_warkop_manual}'.")

  st.stop()

# ====================================================
# JIKA KONDISI LOGIN SPG: TAMPILKAN FORM INPUT LAPORAN
# ====================================================
daftar_master_spg = load_master_spgs()
if daftar_master_spg:
  nama_spg_manual = st.selectbox("Pilih Nama SPG yang Bertugas", options=daftar_master_spg)
else:
  nama_spg_manual = st.text_input("Nama SPG (Entry Manual)", placeholder="Contoh: Nanda")

if (
    is_inside_geofence
    and str(nama_spg_manual).strip() != ""
    and str(nama_warkop_manual).strip() != ""
):
  st.success(
      f"✅ Form laporan untuk **{str(nama_spg_manual).strip()}** di"
      f" **Kecamatan {kecamatan_pilihan}** ({nama_warkop_manual}) siap diisi."
  )
  st.markdown("---")

  with st.form("form_laporan_spg"):
    st.markdown(
        "### 📝 Form Input Laporan Konsumen &nbsp; `💾 Dilengkapi Auto-Draft`"
    )
    st.write(
        f"**Team Login:** {st.session_state['user_spg']} | **Nama SPG:**"
        f" {str(nama_spg_manual).strip()} | **Warkop/LKK:**"
        f" {str(nama_warkop_manual).strip()}"
    )

    team_brands_map = load_master_team_brands()
    allowed_brands_for_team = team_brands_map.get(
        st.session_state["user_spg"], load_master_brands()
    )
    if not allowed_brands_for_team:
      allowed_brands_for_team = load_master_brands()

    brand_entry = st.selectbox(
        f"Brand Rokok (Dikhususkan untuk {st.session_state['user_spg']})",
        options=allowed_brands_for_team,
        help="Daftar merek rokok disesuaikan dengan alokasi Master Team Admin",
    )

    nama_konsumen = st.text_input(
        "Nama Konsumen",
        value=st.session_state["draft_konsumen"],
        placeholder="Masukkan nama konsumen",
    )
    gender_entry = st.radio("Gender", ["L", "P"], horizontal=True)
    
    range_umur_entry = st.selectbox(
        "Range Umur",
        options=["18-24", "25-30", "31-35", "36-44", "45+"],
        help="Pilih rentang usia konsumen"
    )

    nohp_entry = st.text_input(
        "No HP",
        value=st.session_state["draft_nohp"],
        placeholder="Contoh: 081234567890",
    )
    instagram_input = st.text_input(
        "Instagram",
        value=st.session_state["draft_ig"],
        placeholder="username_ig",
    )
    jumlah_bungkus = st.number_input(
        "Jumlah Bungkus",
        min_value=1,
        step=1,
        value=st.session_state["draft_bungkus"],
    )
    rokok_asal_bumo = st.text_input(
        "Rokok Asal (BUMO)",
        value=st.session_state["draft_bumo"],
        placeholder="Merk rokok yang biasa dikonsumsi sebelumnya",
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
      btn_save_draft = st.form_submit_button(
          "💾 Simpan Draft Saja", type="secondary"
      )
    with col_btn2:
      btn_kirim = st.form_submit_button(
          "🚀 Kirim Laporan ke Database", type="primary"
      )

    if btn_save_draft:
      st.session_state["draft_konsumen"] = nama_konsumen
      st.session_state["draft_nohp"] = nohp_entry
      st.session_state["draft_ig"] = instagram_input
      st.session_state["draft_bungkus"] = jumlah_bungkus
      st.session_state["draft_bumo"] = rokok_asal_bumo
      st.info(
          "💾 Draft laporan berhasil diamankan ke memori sesi sementara!"
          " (Aman jika HP sempat tidur sejenak)."
      )

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
        df_new_row = pd.DataFrame([data_baru])
        df_all = pd.concat([df_all, df_new_row], ignore_index=True)
        save_database(df_all)

        st.session_state["draft_konsumen"] = ""
        st.session_state["draft_nohp"] = ""
        st.session_state["draft_ig"] = ""
        st.session_state["draft_bungkus"] = 1
        st.session_state["draft_bumo"] = ""

        st.balloons()
        st.success(
            f"🎉 Laporan konsumen **{nama_konsumen}** oleh SPG"
            f" **{str(nama_spg_manual).strip()}** berhasil disimpan!"
        )
else:
  if not is_inside_geofence:
    st.warning(
        "🔒 Form input terkunci karena posisi GPS Anda berada di luar wilayah"
        f" {st.session_state['kota_kab']}."
    )
  else:
    st.info(
        "ℹ️ Silakan pilih **Nama SPG** dan pastikan **Warkop/LKK** terpilih untuk"
        " membuka form."
    )

st.markdown("---")
st.markdown(
    f"### 📈 Evaluasi Harian & Log Rekap: {st.session_state['user_spg']} ("
    f"{st.session_state['kota_kab']})"
)

df_master_all = load_database()
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
  df_user_rekap["Nama_SPG"] = df_user_rekap["Nama_SPG"].fillna("-")

  st.markdown("#### 📋 Tabel Evaluasi Harian Per SPG (Berdasarkan Target SPG)")
  df_eval_spg = (
      df_user_rekap.groupby(["Tanggal", "Nama_SPG", "Brand_Rokok"])
      .agg(
          Jumlah_Titik_Warkop=("Warkop_LKK", lambda x: x.nunique()),
          Konsumen_Beli=("Nama_Konsumen", "count"),
          Jumlah_Omset_SPG=("Jumlah_Bungkus", "sum"),
      )
      .reset_index()
  )
  df_eval_spg["Target_SPG"] = df_eval_spg["Brand_Rokok"].apply(get_target_spg)
  df_eval_spg["Status_Target_SPG"] = df_eval_spg.apply(
      lambda r: cek_status_target_spg_val(r["Brand_Rokok"], r["Jumlah_Omset_SPG"]),
      axis=1,
  )

  st.dataframe(
      df_eval_spg.style.map(
          style_status_target, subset=["Status_Target_SPG"]
      ),
      use_container_width=True,
  )

  st.markdown("---")
  st.markdown("#### 📑 Log Detail Transaksi & Pengaturan")
  
  # Kolom Plat_Mobil dihapus dari tampilan log detail transaksi SPG
  cols_to_drop_spg = ["Tanggal", "Plat_Mobil"] if "Plat_Mobil" in df_user_rekap.columns else ["Tanggal"]
  st.dataframe(
      df_user_rekap.drop(columns=cols_to_drop_spg, errors="ignore"),
      use_container_width=True,
  )

  output = BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_eval_spg.to_excel(
        writer, index=False, sheet_name="Evaluasi Harian SPG"
    )
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
