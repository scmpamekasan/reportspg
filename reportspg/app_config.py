from pathlib import Path


# Lokasi file data relatif terhadap folder aplikasi,
# agar tidak bergantung pada working directory saat aplikasi dijalankan.
BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "rekap_laporan_spg.csv"
DB_SUPERVISI_KONTAK_FILE = BASE_DIR / "rekap_kontak_supervisi.csv"

MASTER_BRAND_FILE = BASE_DIR / "master_brand_rokok.json"
MASTER_LOKASI_FILE = BASE_DIR / "Master WarkopLKK.xlsx"
MASTER_SPG_FILE = BASE_DIR / "master_nama_spg.json"
MASTER_TEAM_BRAND_FILE = BASE_DIR / "master_team_brand.json"
MASTER_PLAT_FILE = BASE_DIR / "master_plat_kendaraan.json"
JADWAL_SPG_FILE = BASE_DIR / "Jadwal SPG.xlsx"

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
