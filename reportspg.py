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

# File database lokal agar data persisten
DB_FILE = "rekap_laporan_spg.csv"
MASTER_BRAND_FILE = "master_brand_rokok.json"
MASTER_LOKASI_FILE = "master_lokasi_warkop.json"
MASTER_PLAT_FILE = "master_plat_kendaraan.json"
MASTER_SPG_FILE = "master_nama_spg.json"

EXPECTED_COLUMNS = [
    "Waktu",
    "Promotor",
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


# ====================================================
# MANAJEMEN MASTER DATA (BRAND, LOKASI, PLAT & SPG)
# ====================================================
DEFAULT_BRANDS = [
    "D.Super 12",
    "D.76 Apel",
    "D.76 Apel Royal",
    "Black Matcha K12",
    "Djarum 76 Aksara",
]
DEFAULT_LOKASI = [
    "Warkop Cak No",
    "Warkop Pitoe",
    "Warkop Giras",
    "Warkop Madura",
    "Warkop 88",
]
DEFAULT_PLATS = [
    "L 1774 BAS",
    "L 1176 BAN",
    "L 1046 BAN",
    "N 1103 ABT",
    "L 1233 BBO",
    "B 2644 UYA",
    "L 1728 BAY",
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


def load_master_lokasi():
  if os.path.exists(MASTER_LOKASI_FILE):
    try:
      with open(MASTER_LOKASI_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return DEFAULT_LOKASI
  return DEFAULT_LOKASI


def save_master_lokasi(lokasi):
  with open(MASTER_LOKASI_FILE, "w", encoding="utf-8") as f:
    json.dump(lokasi, f, ensure_ascii=False, indent=2)


def load_master_plats():
  if os.path.exists(MASTER_PLAT_FILE):
    try:
      with open(MASTER_PLAT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return DEFAULT_PLATS
  return DEFAULT_PLATS


def save_master_plats(plats):
  with open(MASTER_PLAT_FILE, "w", encoding="utf-8") as f:
    json.dump(plats, f, ensure_ascii=False, indent=2)


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
if "admin_view" not in st.session_state:
  st.session_state["admin_view"] = "Dashboard"

# ====================================================
# SIDEBAR: LOGIN ADMIN DI HALAMAN UTAMA
# ====================================================
if not st.session_state["logged_in"]:
  with st.sidebar:
    st.markdown("### 🔐 Menu Admin / Supervisor")
    st.markdown("Akses dashboard terpusat dan pengaturan master data.")

    if not st.session_state["admin_logged_in"]:
      with st.form("form_admin_login"):
        pass_input = st.text_input(
            "Password Admin", type="password", placeholder="admin123"
        )
        btn_pass = st.form_submit_button("Buka Dashboard Admin")

        if btn_pass:
          if pass_input == "admin123":
            st.session_state["admin_logged_in"] = True
            st.session_state["admin_view"] = "Dashboard"
            st.success("✅ Berhasil masuk sebagai Admin!")
            st.rerun()
          else:
            st.error("❌ Password salah! (Gunakan: admin123)")
    else:
      st.success("🟢 Status: Admin Aktif")
      st.markdown("---")
      if st.button(
          "🏠 Dashboard Utama", use_container_width=True, type="primary"
      ):
        st.session_state["admin_view"] = "Dashboard"
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
      if st.button("🚗 Master Plat Kendaraan", use_container_width=True):
        st.session_state["admin_view"] = "Master_Plat"
        st.rerun()
      if st.button("📊 Analitik & Rekap All", use_container_width=True):
        st.session_state["admin_view"] = "Analitik"
        st.rerun()

      st.markdown("---")
      if st.button("🔒 Keluar dari Mode Admin", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()

# ====================================================
# TAMPILAN DASHBOARD ADMIN & MASTER DATA
# ====================================================
if not st.session_state["logged_in"] and st.session_state["admin_logged_in"]:

  # --- TAMPILAN 1: MASTER DATA NAMA SPG ---
  if st.session_state["admin_view"] == "Master_SPG":
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
    st.markdown("## 🚬 Master Data: Merek Rokok")
    st.caption("Tambah, ubah, atau hapus daftar merek rokok aktif.")

    current_brands = load_master_brands()

    with st.form("form_tambah_brand"):
      new_brand_name = st.text_input(
          "Nama Merek Rokok Baru", placeholder="Contoh: Djarum Super Extra"
      )
      btn_add_brand = st.form_submit_button("➕ Tambah Merek Rokok")
      if btn_add_brand:
        if new_brand_name.strip():
          if new_brand_name.strip() not in current_brands:
            current_brands.append(new_brand_name.strip())
            save_master_brands(current_brands)
            st.success(
                f"✅ Merek rokok '{new_brand_name.strip()}' berhasil ditambahkan!"
            )
            st.rerun()
          else:
            st.warning("Merek rokok tersebut sudah ada dalam daftar.")
        else:
          st.warning("Mohon masukkan nama merek rokok.")

    st.markdown("---")
    st.markdown("#### 📋 Daftar Merek Rokok Aktif")
    for idx, b in enumerate(current_brands):
      col_b1, col_b2 = st.columns([0.8, 0.2])
      with col_b1:
        st.write(f"**{idx+1}.** {b}")
      with col_b2:
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

  # --- TAMPILAN 3: MASTER DATA LOKASI WARKOP ---
  elif st.session_state["admin_view"] == "Master_Lokasi":
    st.markdown("## 📍 Master Data: Lokasi Warkop / LKK")
    st.caption(
        "Kelola daftar titik warkop atau lokasi kunjungan standar operasional."
    )

    current_lokasi = load_master_lokasi()

    with st.form("form_tambah_lokasi"):
      new_lokasi_name = st.text_input(
          "Nama Warkop / LKK Baru", placeholder="Contoh: Warkop Barokah"
      )
      btn_add_lokasi = st.form_submit_button("➕ Tambah Lokasi Warkop")
      if btn_add_lokasi:
        if new_lokasi_name.strip():
          if new_lokasi_name.strip() not in current_lokasi:
            current_lokasi.append(new_lokasi_name.strip())
            save_master_lokasi(current_lokasi)
            st.success(
                f"✅ Lokasi '{new_lokasi_name.strip()}' berhasil ditambahkan!"
            )
            st.rerun()
          else:
            st.warning("Lokasi warkop tersebut sudah ada dalam daftar.")
        else:
          st.warning("Mohon masukkan nama lokasi.")

    st.markdown("---")
    st.markdown("#### 📋 Daftar Warkop / LKK Aktif")
    for idx, l in enumerate(current_lokasi):
      col_l1, col_l2 = st.columns([0.8, 0.2])
      with col_l1:
        st.write(f"**{idx+1}.** {l}")
      with col_l2:
        if st.button("🗑️ Hapus", key=f"del_lokasi_{idx}"):
          current_lokasi.pop(idx)
          save_master_lokasi(current_lokasi)
          st.success("Lokasi berhasil dihapus!")
          st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN 4: MASTER DATA PLAT KENDARAAN ---
  elif st.session_state["admin_view"] == "Master_Plat":
    st.markdown("## 🚗 Master Data: Plat Kendaraan Operasional")
    st.caption(
        "Kelola daftar plat kendaraan yang akan muncul pada pilihan login SPG."
    )

    current_plats = load_master_plats()

    with st.form("form_tambah_plat"):
      new_plat_name = st.text_input(
          "Nomor Plat Kendaraan Baru", placeholder="Contoh: L 1234 AB"
      )
      btn_add_plat = st.form_submit_button("➕ Tambah Plat Kendaraan")
      if btn_add_plat:
        plat_clean = new_plat_name.strip().upper()
        if plat_clean:
          if plat_clean not in current_plats:
            current_plats.append(plat_clean)
            save_master_plats(current_plats)
            st.success(f"✅ Plat kendaraan '{plat_clean}' berhasil ditambahkan!")
            st.rerun()
          else:
            st.warning("Plat kendaraan tersebut sudah ada dalam daftar.")
        else:
          st.warning("Mohon masukkan nomor plat kendaraan.")

    st.markdown("---")
    st.markdown("#### 📋 Daftar Plat Kendaraan Terdaftar")
    for idx, p in enumerate(current_plats):
      col_p1, col_p2 = st.columns([0.8, 0.2])
      with col_p1:
        st.write(f"**{idx+1}.** `{p}`")
      with col_p2:
        if st.button("🗑️ Hapus", key=f"del_plat_{idx}"):
          current_plats.pop(idx)
          save_master_plats(current_plats)
          st.success("Plat kendaraan berhasil dihapus!")
          st.rerun()

    st.markdown("---")
    if st.button("⬅️ Kembali ke Dashboard"):
      st.session_state["admin_view"] = "Dashboard"
      st.rerun()
    st.stop()

  # --- TAMPILAN 5: ANALITIK & REKAP ALL (DITAMBAH SEBARAN PER KECAMATAN) ---
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
        st.markdown("#### 🏙️ Sebaran per Wilayah (Kota/Kab)")
        kota_count = df_all_users["Kota_Kab"].value_counts()
        st.bar_chart(kota_count)

      st.markdown("---")
      st.markdown("#### 🗺️ Sebaran Kunjungan & Omset per Kecamatan")

      # Filter wilayah opsional pada analitik kecamatan
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

        # Grafik batang omset per kecamatan
        chart_kec = df_sebaran_kec.set_index("Kecamatan")[
            "Total_Omset_Bungkus"
        ]
        st.bar_chart(chart_kec)

        # Tabel detail sebaran per kecamatan
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

  # --- TAMPILAN UTAMA: DASHBOARD ADMIN BERGAYA KARTU ---
  st.markdown("## 📊 Dashboard Admin & Manajemen Lapangan")
  st.caption(
      "Pilih menu master data atau pantau rekapitulasi tim secara real-time."
  )

  # Grid Kartu Menu Admin
  st.markdown("#### 📦 Master Data")
  col_m1, col_m2 = st.columns(2)
  with col_m1:
    if st.button(
        "👩‍💼 Nama SPG\nKelola daftar SPG",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Master_SPG"
      st.rerun()
    if st.button(
        "📍 Lokasi Warkop\nKelola titik warkop/LKK",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Master_Lokasi"
      st.rerun()
  with col_m2:
    if st.button(
        "🚬 Merek Rokok\nKelola daftar merek",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Master_Brand"
      st.rerun()
    if st.button(
        "🚗 Plat Kendaraan\nKelola nopol tim",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Master_Plat"
      st.rerun()

  st.markdown("---")
  st.markdown("#### 📈 Analitik & Performa")
  col_a1, col_a2 = st.columns(2)
  with col_a1:
    if st.button(
        "📊 Analitik Lapangan\nDemografi, Regional & Kecamatan",
        use_container_width=True,
    ):
      st.session_state["admin_view"] = "Analitik"
      st.rerun()
  with col_a2:
    if st.button(
        "⬅️ Kembali ke Menu Login Utama",
        use_container_width=True,
    ):
      st.session_state["admin_logged_in"] = False
      st.rerun()

  st.markdown("---")
  st.markdown("#### 🌐 Ringkasan Cepat Data Masuk (All User)")

  df_all_users = load_database()
  if not df_all_users.empty:
    df_all_users["Tanggal"] = pd.to_datetime(
        df_all_users["Waktu"], errors="coerce"
    ).dt.date
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

    st.markdown("#### 🏆 Leaderboard Team SPG")
    df_leaderboard = (
        df_all_users.groupby(["Promotor", "Kota_Kab"])
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
        df_all_users.drop(columns=["Tanggal"], errors="ignore").sort_values(
            by="Waktu", ascending=False
        ),
        use_container_width=True,
    )

    # Menu Penghapusan Data Khusus Admin
    with st.expander("⚙️ Menu Pengaturan & Hapus Log (Admin Panel)"):
      tab_row, tab_hari, tab_minggu, tab_all = st.tabs([
          "Hapus per Row",
          "Hapus per Hari",
          "Hapus per Minggu",
          "Hapus Semua (All)",
      ])

      with tab_row:
        options_row = []
        for idx, row in df_all_users.iterrows():
          label = (
              f"[{row['Waktu']}] Team: {row['Promotor']} | SPG:"
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
            df_all_users["Tanggal"].dropna().unique().tolist(), reverse=True
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
  else:
    st.info("Belum ada data laporan masuk.")

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
        daftar_plat_tersedia = load_master_plats()
        if daftar_plat_tersedia:
          plat_input = st.selectbox(
              "🚗 Plat Kendaraan", options=daftar_plat_tersedia
          )
        else:
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
          if not plat_input or not str(plat_input).strip():
            st.warning("⚠️ Mohon pilih plat nomor kendaraan terlebih dahulu.")
          else:
            st.session_state["logged_in"] = True
            st.session_state["user_spg"] = pilihan_user
            st.session_state["kota_kab"] = pilihan_kota
            st.session_state["plat_kendaraan"] = str(plat_input).strip().upper()
            st.rerun()
        else:
          st.error(
              f"❌ Password salah untuk **{pilihan_user}**! (Petunjuk default:"
              f" `spg{spg_num}` atau `spg123`)"
          )

    st.markdown(
        """
        <div class="footer-note">
            Gunakan sidebar kiri untuk masuk ke menu <b>Dashboard Admin</b> (Password: <code>admin123</code>).<br/>
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
      f"- **Wilayah Terpilih:** **{st.session_state['kota_kab']}**\n\n"
      "⚠️ Posisi Anda terdeteksi berada di luar batas zona GeoJSON wilayah"
      f" {st.session_state['kota_kab']}. Form laporan dikunci sampai Anda"
      " berada di dalam area operasional yang sah."
  )

st.markdown("### 📋 Lokasi Kunjungan")

# Pilihan Nama SPG terhubung langsung dengan Master Data Nama SPG
daftar_master_spg = load_master_spgs()
if daftar_master_spg:
  nama_spg_manual = st.selectbox("Pilih Nama SPG", options=daftar_master_spg)
else:
  nama_spg_manual = st.text_input(
      "Nama SPG (Entry Manual)", placeholder="Contoh: Nanda"
  )

# Pilih Kecamatan otomatis terisi sesuai titik GPS saat ini
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

# Pilihan warkop terhubung langsung dengan Master Lokasi Warkop
daftar_master_lokasi = load_master_lokasi()
nama_warkop_manual = st.selectbox(
    "Pilih / Nama Warkop / LKK",
    options=daftar_master_lokasi,
    help="Dikelola melalui Master Data Lokasi Admin",
)

if (
    is_inside_geofence
    and str(nama_spg_manual).strip() != ""
    and str(nama_warkop_manual).strip() != ""
):
  st.success(
      f"✅ Form laporan untuk **{str(nama_spg_manual).strip()}** di"
      f" **Kecamatan {kecamatan_pilihan}** siap diisi."
  )
  st.markdown("---")
  with st.form("form_laporan_spg"):
    st.markdown("### 📝 Form Input Laporan Konsumen")
    st.write(
        f"**Team Login:** {st.session_state['user_spg']} | **Nama SPG:**"
        f" {str(nama_spg_manual).strip()} | **Warkop/LKK:**"
        f" {str(nama_warkop_manual).strip()}"
    )

    # Brand rokok terhubung langsung dengan Master Merek Rokok
    daftar_master_brand = load_master_brands()
    brand_entry = st.selectbox(
        "Brand Rokok",
        options=daftar_master_brand,
        help="Dikelola melalui Master Data Merek Rokok Admin",
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
            "Promotor": st.session_state["user_spg"],
            "Nama_SPG": str(nama_spg_manual).strip(),
            "Kota_Kab": st.session_state["kota_kab"],
            "Plat_Kendaraan": st.session_state["plat_kendaraan"],
            "Kecamatan": kecamatan_pilihan,
            "Warkop_LKK": str(nama_warkop_manual).strip(),
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
        "ℹ️ Silakan pilih **Nama SPG** dan pilih **Warkop/LKK** terlebih"
        " dahulu untuk membuka form."
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

  st.markdown("#### 📋 Tabel Evaluasi Harian Per Team SPG")
  df_eval = (
      df_user_rekap.groupby(["Tanggal", "Promotor", "Brand_Rokok"])
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
