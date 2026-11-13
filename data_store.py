import json

import geopandas as gpd
import pandas as pd
import streamlit as st

from app_config import (
    BASE_DIR,
    DB_FILE,
    DB_SUPERVISI_KONTAK_FILE,
    EXPECTED_COLUMNS,
    EXPECTED_SUPERVISI_COLUMNS,
)


def load_database():
    """Memuat database transaksi SPG."""
    if not DB_FILE.exists():
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    try:
        df = pd.read_csv(DB_FILE)

        # Mendukung nama kolom lama.
        if "Usia" in df.columns and "Range_Umur" not in df.columns:
            df = df.rename(columns={"Usia": "Range_Umur"})

        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = "-"

        return df[EXPECTED_COLUMNS]
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        st.error(f"Gagal membaca database transaksi: {exc}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)


def save_database(df):
    """Menyimpan database transaksi SPG."""
    df.to_csv(DB_FILE, index=False)


def load_supervisi_database():
    """Memuat database kontak supervisi."""
    if not DB_SUPERVISI_KONTAK_FILE.exists():
        return pd.DataFrame(columns=EXPECTED_SUPERVISI_COLUMNS)

    try:
        df = pd.read_csv(DB_SUPERVISI_KONTAK_FILE)

        for col in EXPECTED_SUPERVISI_COLUMNS:
            if col not in df.columns:
                df[col] = "-"

        return df[EXPECTED_SUPERVISI_COLUMNS]
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        st.error(f"Gagal membaca database kontak supervisi: {exc}")
        return pd.DataFrame(columns=EXPECTED_SUPERVISI_COLUMNS)


def save_supervisi_database(df):
    """Menyimpan database kontak supervisi."""
    df.to_csv(DB_SUPERVISI_KONTAK_FILE, index=False)


@st.cache_data
def load_master_wilayah(kota):
    """Memuat GeoJSON batas wilayah berdasarkan nama kota."""
    filename_by_city = {
        "Surabaya": "Surabaya Barat.geojson",
        "Gresik": "Gresik.geojson",
    }
    filename = filename_by_city.get(kota)

    if filename is None:
        return None

    file_path = BASE_DIR / filename

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        gdf_master = gpd.GeoDataFrame.from_features(data)

        if gdf_master.crs is None:
            gdf_master = gdf_master.set_crs("EPSG:4326")

        return gdf_master
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        st.error(f"Gagal memuat file master wilayah '{filename}': {exc}")
        return None