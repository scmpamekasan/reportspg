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
# CUSTOM CSS UNTUK UI MODERN & DASHBOARD ADMIN
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

# File database lokal & master
DB_FILE = "rekap_laporan_spg.csv"
MASTER_BRAND_FILE = "master_brand_rokok.json"
MASTER_LOKASI_FILE = "Master WarkopLKK.xlsx"
MASTER_SPG_FILE = "master_nama_spg.json"
MASTER_TEAM_BRAND_FILE = "master_team_brand.json"
JADWAL_SPG_FILE = "Jadwal SPG.xlsx"

EXPECTED_COLUMNS = [
    "Waktu",
    "Promotor",
    "Nama_SPG",
    "Kota_Kab",
    "Kecamatan",
    "Warkop_LKK",
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


# ====================================================
# MANAJEMEN MASTER DATA & TEAM BRAND
# ====================================================
DEFAULT_BRANDS = [
    "D.Super 12",
    "D.76 Apel",
    "D.76 Apel Royal",
    "Black Matcha K12",
    "Djarum 76 Aksara",
]
DEFAULT_SPGS = ["Nanda", "Dewi", "Aci", "Ayu"]


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


def get_kota_from_schedule(team_name):
  """Mendeteksi kota operasional team berdasarkan Jadwal SPG.xlsx untuk hari ini secara akurat."""
  df_j = load_jadwal_spg()
  if df_j.empty:
    return "Surabaya"  # Fallback default
  
  kota_col = next((c for c in df_j.columns if "kota" in c.lower()), None)
  if not kota_col:
    return "Surabaya"
    
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
    return "Surabaya"
    
  team_clean = team_name.strip().lower()
  team_digit = ''.join(filter(str.isdigit, team_clean))
  
  for _, row in df_j.iterrows():
    val_cell = str(row[today_col]).strip()
    if val_cell and val_cell.lower() != "nan" and val_cell != "-":
      val_lower = val_cell.lower()
      cell_digit = ''.join(filter(str.isdigit, val_lower))
      if team_clean == val_lower or (team_digit and cell_digit and team_digit == cell_digit and len(team_digit) == len(cell_digit)):
        found_kota = str(row[kota_col]).strip()
        if found_kota:
          return found_kota
          
  return "Surabaya"  # Fallback jika tidak ditemukan


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


# ====================================================
# INISIALISASI SESSION STATE
# ====================================================
if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
if "user_spg" not in st.session_state:
  st.session_state["user_spg"] = ""
if "kota_kab" not in st.session_state:
  st.session_state["kota_kab"] = ""
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

  # --- TAMPILAN 0: MASTER TEAM & BRAND ROKOK ---
  if st.session_state["admin_view"] == "Master_Team":
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

  # --- TAMPILAN 1: MASTER DATA NAMA SPG ---
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

  # --- TAMPILAN 2: MASTER DATA MEREK ROKOK ---
  elif st.session_state["admin_view"] == "Master_Brand":
    st.markdown("## 🚬 Master Data: Merek Rokok & Target")
    st.caption(
        "Kelola daftar merek rokok beserta aturan target omset per SPG dan"
        " Team."
    )

    current_brands = load_master_brands()

    with st.form("form_tambah_brand"):
      new_brand_name = st.text_input(
          "Nama Merek Rokok Baru", placeholder="Contoh: Djarum Super Extra"
      )
      t_spg = st.number_input(
          "Target per SPG (Bungkus)", min_value=1, value=30, step=1
      )
      t_team = st.number_input(
          "Target per Team (Bungkus)", min_value=1, value=60, step=1
      )
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
            st.success(
                f"✅ Merek rokok '{b_clean}' berhasil ditambahkan dengan target"
                f" SPG: {t_spg}, Team: {t_team}!"
            )
            st.rerun()
          else:
            st.warning("Merek rokok tersebut sudah ada dalam daftar.")
        else:
          st.warning("Mohon masukkan nama merek rokok.")

    st.markdown("---")
    st.markdown("#### 📋 Daftar Merek Rokok & Aturan Target")
    for idx, b in enumerate(current_brands):
      rule = TARGET_RULES.get(b, {"target_spg": 25, "target_team": 50})
      col_b1, col_b2, col_b3 = st.columns([0.5, 0.3, 0.2])
      with col_b1:
        st.write(
            f"**{idx+1}. {b}**\n- Target SPG: `{rule['target_spg']} bks`\n-"
            f" Target Team: `{rule['target_team']} bks`"
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

  # --- TAMPILAN 3: MASTER DATA LOKASI WARKOP DARI FILE EXCEL ---
  elif st.session_state["admin_view"] == "Master_Lokasi":
    st.markdown("## 📍 Master Data: Lokasi Warkop / LKK (Excel)")
    st.caption(
        "Mengelola data warkop/LKK dari file repository: Master WarkopLKK.xlsx"
    )

    df_lokasi_excel = load_master_lokasi_excel()
    cols_available = df_lokasi_excel.columns.tolist()
    st.info(
        f"📁 Sumber file aktif: `{MASTER_LOKASI_FILE}` | Kolom terdeteksi:"
        f" {cols_available}"
    )

    with st.form("form_tambah_lokasi_excel"):
      st.markdown("#### Tambah Baris Warkop / LKK Baru ke Excel")
      col_kec_input = st.text_input(
          "Kecamatan", placeholder="Contoh: Tegalsari"
      )
      col_warkop_input = st.text_input(
          "Nama Warkop / LKK", placeholder="Contoh: Warkop Barokah"
      )
      btn_add_excel = st.form_submit_button("➕ Tambah & Simpan ke Excel")

      if btn_add_excel:
        if col_kec_input.strip() and col_warkop_input.strip():
          kec_col_name = next(
              (
                  c
                  for c in df_lokasi_excel.columns
                  if "kec" in c.lower() or "wilayah" in c.lower()
              ),
              "Kecamatan",
          )
          warkop_col_name = next(
              (
                  c
                  for c in df_lokasi_excel.columns
                  if "warkop" in c.lower()
                  or "lkk" in c.lower()
                  or "nama" in c.lower()
              ),
              "Warkop_LKK",
          )

          new_row = {
              kec_col_name: col_kec_input.strip(),
              warkop_col_name: col_warkop_input.strip(),
          }
          df_lokasi_excel = pd.concat(
              [df_lokasi_excel, pd.DataFrame([new_row])], ignore_index=True
          )
          if save_master_lokasi_excel(df_lokasi_excel):
            st.success(
                f"✅ Warkop '{col_warkop_input.strip()}' di Kecamatan"
                f" '{col_kec_input.strip()}' berhasil ditambahkan ke"
                f" {MASTER_LOKASI_FILE}!"
            )
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

  # --- TAMPILAN 4: ANALITIK & REKAP ALL ---
  elif st.session_state["admin_view"] == "Analitik":
    st.markdown("## 📊 Analitik & Rekapitulasi All User")
    st.caption(
        "Laporan mendalam performa seluruh tim berdasarkan demografi, wilayah,"
        " dan sebaran kecamatan."
    )

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

  # --- TAMPILAN 5: PETA RUTE ALL USER ---
  elif st.session_state["admin_view"] == "Peta_Rute":
    st.markdown("## 🗺️ Visualisasi Peta Rute Perjalanan (All User)")
    st.caption(
        "Pantau rute dan titik kunjungan lapangan berdasarkan filter Team SPG,"
        " Nama SPG, dan Tanggal."
    )

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
                    "<b>Team:</b> {Promotor} ({Nama_SPG})<br/><b>Warkop:</b>"
                    " {Warkop_LKK} ({Kecamatan})<br/><b>Brand:</b>"
                    " {Brand_Rokok} ({Jumlah_Bungkus} bks)<br/><b>Waktu:</b>"
                    " {Waktu}"
                ),
                "style": {"backgroundColor": "#1e293b", "color": "white"},
            },
        )

        st.pydeck_chart(deck_map)
      else:
        st.warning(
            "Tidak ada data koordinat yang cocok dengan filter yang dipilih."
        )
    else:
      st.info("Belum ada data koordinat GPS yang terekam pada sistem.")

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN UTAMA: DASHBOARD ADMIN BERGAYA KARTU ---
  st.markdown("## 📊 Dashboard Admin & Manajemen Lapangan")
  st.caption(
      "Pilih menu master data atau pantau rekapitulasi tim secara real-time."
  )

  st.markdown("#### 📦 Master Data")
  col_m1, col_m2 = st.columns(2)
  with col_m1:
    if st.button(
        "👥 Master Team & Brand\nAtur brand rokok per team (1-20)",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Master_Team"
      st.rerun()
    if st.button(
        "👩‍💼 Nama SPG\nKelola daftar SPG",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Master_SPG"
      st.rerun()
  with col_m2:
    if st.button(
        "📍 Lokasi Warkop (Excel)\nKelola dari Master WarkopLKK.xlsx",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Master_Lokasi"
      st.rerun()
    if st.button(
        "🚬 Merek Rokok & Target\nKelola daftar merek & target",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Master_Brand"
      st.rerun()

  st.markdown("---")
  st.markdown("#### 📈 Analitik & Pemetaan")
  col_a1, col_a2, col_a3 = st.columns(3)
  with col_a1:
    if st.button(
        "📊 Analitik Lapangan\nDemografi & Kecamatan", use_container_width=True
    ):
      st.session_state["admin_view"] = "Analitik"
      st.rerun()
  with col_a2:
    if st.button(
        "🗺️ Peta Rute All User\nFilter Team/SPG/Tanggal", use_container_width=True
    ):
      st.session_state["admin_view"] = "Peta_Rute"
      st.rerun()
  with col_a3:
    if st.button(
        "⬅️ Keluar Admin",
        use_container_width=True,
    ):
      st.session_state["admin_logged_in"] = False
      st.rerun()

  st.markdown("---")
  st.markdown("#### 🌐 Ringkasan Cepat Data Masuk (All User)")

  df_all_users = load_database()
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
          '</div><div class="kpi-label">Konsumen</div></div>',
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
            Total_Konsumen=("Nama_Konsumen", "count"),
        )
        .reset_index()
    )
    df_team_leaderboard["Target_Team"] = df_team_leaderboard[
        "Brand_Rokok"
    ].apply(
        lambda b: TARGET_RULES.get(b, {"target_team": 50})["target_team"]
    )
    df_team_leaderboard["Status_Target_Team"] = df_team_leaderboard.apply(
        lambda r: cek_status_target_team(r["Brand_Rokok"], r["Total_Omset_Team"]),
        axis=1,
    )

    st.dataframe(
        df_team_leaderboard.style.map(
            style_status_target, subset=["Status_Target_Team"]
        ),
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("#### 📑 Log Detail Transaksi All User")

    # ====================================================
    # MENU HAPUS LOG DETAIL TRANSAKSI ALL USER
    # ====================================================
    with st.expander("🗑️ Menu Hapus Log Detail Transaksi (Per Row / Hari / Minggu / All Data)", expanded=False):
      st.warning("⚠️ Perhatian: Data yang sudah dihapus dari database tidak dapat dikembalikan.")
      tab_del_row, tab_del_day, tab_del_week, tab_del_all = st.tabs([
          "🔹 Hapus per Row",
          "📅 Hapus per Hari",
          "📆 Hapus per Minggu",
          "🚨 Hapus All Data"
      ])

      # 1. HAPUS PER ROW
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

      # 2. HAPUS PER HARI
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

      # 3. HAPUS PER MINGGU
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

      # 4. HAPUS ALL DATA
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
  else:
    st.info("Belum ada data laporan masuk.")

  st.stop()

# ====================================================
# HALAMAN LOGIN UTAMA (DENGAN REFRESH REAL-TIME SELECTBOX)
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

    # Menggunakan st.container / form interaktif di luar form statis murni
    # agar preview kota langsung merefresh saat pilihan team diganti.
    st.markdown("#### 🚀 Masuk ke Akun Operasional")
    st.caption("Pilih tim (1-20). Wilayah operasional akan otomatis terdeteksi sesuai jadwal.")

    list_spg = [f"Team SPG {i}" for i in range(1, 21)]
    
    # Menambahkan key agar state selectbox terpantau langsung
    pilihan_user = st.selectbox("👤 Pilih User (Team SPG)", list_spg, key="selected_team_login")

    # Deteksi otomatis kota berdasarkan jadwal hari ini secara real-time saat selectbox berubah
    auto_detected_kota = get_kota_from_schedule(pilihan_user)
    st.info(f"🏙️ Wilayah Terdeteksi dari Jadwal Hari Ini: **{auto_detected_kota}**")

    if st.button("Masuk Aplikasi", type="primary", use_container_width=True):
      st.session_state["logged_in"] = True
      st.session_state["user_spg"] = pilihan_user
      st.session_state["kota_kab"] = auto_detected_kota
      st.rerun()

    st.markdown(
        """
        <div class="footer-note">
            Gunakan sidebar kiri untuk masuk ke menu <b>Dashboard Admin.<br/>
            © 2026 Tumarso Monitoring System
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
              🏙️ Wilayah Operasional (Otomatis Jadwal): <b>{st.session_state['kota_kab']}</b>
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
      f" {st.session_state['kota_kab']}. Form laporan dikunci sampai Anda"
      " berada di dalam area operasional yang sah."
  )

st.markdown("### 📋 Lokasi Kunjungan")

daftar_master_spg = load_master_spgs()
if daftar_master_spg:
  nama_spg_manual = st.selectbox("Pilih Nama SPG", options=daftar_master_spg)
else:
  nama_spg_manual = st.text_input(
      "Nama SPG (Entry Manual)", placeholder="Contoh: Nanda"
  )

opsi_kecamatan = daftar_kecamatan if daftar_kecamatan else ["Kecamatan Umum"]
default_index_kec = 0
if detected_kecamatan and detected_kecamatan in opsi_kecamatan:
  default_index_kec = opsi_kecamatan.index(detected_kecamatan)

kecamatan_pilihan = st.selectbox(
    f"Pilih Kecamatan Tujuan Kunjungan ({st.session_state['kota_kab']})",
    options=opsi_kecamatan,
    index=default_index_kec,
    help="Otomatis terpilih berdasarkan titik koordinat GPS Anda saat ini",
)

# ====================================================
# VALIDASI JADWAL SPG DARI EXCEL (Jadwal SPG.xlsx)
# ====================================================
df_jadwal_raw = load_jadwal_spg()
is_scheduled_today = True
schedule_check_msg = ""

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
      mask_j = (
          (df_jadwal_raw[kota_col_j].astype(str).str.strip().str.lower() == st.session_state["kota_kab"].strip().lower()) &
          (df_jadwal_raw[kec_col_j].astype(str).str.strip().str.lower() == str(kecamatan_pilihan).strip().lower())
      )
      row_matched = df_jadwal_raw[mask_j]
      
      if not row_matched.empty:
        val_jadwal = str(row_matched.iloc[0][today_col]).strip()
        user_team_str = st.session_state["user_spg"].strip().lower()
        val_jadwal_lower = val_jadwal.lower()
        
        if val_jadwal == "" or val_jadwal.lower() == "nan" or val_jadwal == "-":
          is_scheduled_today = False
          schedule_check_msg = f"❌ Tidak ada jadwal penugasan untuk {st.session_state['user_spg']} di Kecamatan {kecamatan_pilihan} pada tanggal hari ini ({today_date})."
        elif user_team_str not in val_jadwal_lower and "team" in user_team_str and "team" not in val_jadwal_lower:
          team_digit = ''.join(filter(str.isdigit, user_team_str))
          excel_digit = ''.join(filter(str.isdigit, val_jadwal_lower))
          if team_digit and excel_digit and team_digit != excel_digit:
            is_scheduled_today = False
            schedule_check_msg = f"❌ Jadwal di Kecamatan {kecamatan_pilihan} pada tanggal {today_date} ditugaskan untuk **{val_jadwal}**, bukan untuk {st.session_state['user_spg']}."
      else:
        is_scheduled_today = False
        schedule_check_msg = f"❌ Kecamatan {kecamatan_pilihan} tidak terdaftar dalam jadwal operasional untuk wilayah {st.session_state['kota_kab']}."

if not is_scheduled_today:
  st.error(
      f"🚨 **Akses Masuk Form Dikunci (Sesuai Jadwal SPG.xlsx):**\n\n"
      f"{schedule_check_msg}\n\n"
      "⚠️ Anda tidak dapat melakukan entry laporan pada kecamatan atau jadwal ini karena tidak sesuai dengan data penugasan resmi."
  )
else:
  if is_inside_geofence:
    st.success(f"✅ Jadwal terverifikasi! Anda terdaftar bertugas di Kecamatan {kecamatan_pilihan} hari ini.")

# ====================================================
# FILTER WARKOP/LKK SESUAI KECAMATAN DARI EXCEL
# ====================================================
df_master_excel = load_master_lokasi_excel()
filtered_warkop_list = []

if not df_master_excel.empty:
  col_kec_excel = next(
      (
          c
          for c in df_master_excel.columns
          if "kec" in c.lower() or "wilayah" in c.lower()
      ),
      None,
  )
  col_warkop_excel = next(
      (
          c
          for c in df_master_excel.columns
          if "warkop" in c.lower() or "lkk" in c.lower() or "nama" in c.lower()
      ),
      None,
  )

  if col_kec_excel and col_warkop_excel:
    mask = (
        df_master_excel[col_kec_excel].astype(str).str.strip().str.lower()
        == str(kecamatan_pilihan).strip().lower()
    )
    filtered_warkop_list = (
        df_master_excel[mask][col_warkop_excel].dropna().unique().tolist()
    )

    if not filtered_warkop_list:
      filtered_warkop_list = (
          df_master_excel[col_warkop_excel].dropna().unique().tolist()
      )
  else:
    filtered_warkop_list = (
        df_master_excel.iloc[:, -1].dropna().unique().tolist()
    )

if not filtered_warkop_list:
  filtered_warkop_list = ["Warkop Alternatif 1", "Warkop Alternatif 2"]

nama_warkop_manual = st.selectbox(
    f"Pilih Warkop / LKK di Kecamatan {kecamatan_pilihan}",
    options=filtered_warkop_list,
    help=(
        "Daftar warkop difilter otomatis dari file Master WarkopLKK.xlsx sesuai"
        " kecamatan aktif"
    ),
)

if (
    is_inside_geofence
    and is_scheduled_today
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
            "Nama_SPG": str(nama_spg_manual).strip(),
            "Kota_Kab": st.session_state["kota_kab"],
            "Kecamatan": kecamatan_pilihan,
            "Warkop_LKK": str(nama_warkop_manual).strip(),
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
  elif not is_scheduled_today:
    st.warning("🔒 Form input dikunci karena Anda tidak memiliki jadwal tugas di wilayah/tanggal ini.")
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
  df_eval_spg["Target_SPG"] = df_eval_spg["Brand_Rokok"].apply(
      lambda b: TARGET_RULES.get(b, {"target_spg": 25})["target_spg"]
  )
  df_eval_spg["Status_Target_SPG"] = df_eval_spg.apply(
      lambda r: cek_status_target_spg(r["Brand_Rokok"], r["Jumlah_Omset_SPG"]),
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
  st.dataframe(
      df_user_rekap.drop(columns=["Tanggal"], errors="ignore"),
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
