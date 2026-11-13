from datetime import timedelta
from zoneinfo import ZoneInfo

import pandas as pd


WIB = ZoneInfo("Asia/Jakarta")


def now_wib():
    """Mengembalikan waktu sekarang dalam zona waktu Asia/Jakarta."""
    return pd.Timestamp.now(tz=WIB).to_pydatetime()


def get_custom_week_info(value):
    """
    Mengembalikan label dan nomor minggu ISO.

    Jumat digunakan sebagai hari acuan:
    - Senin sampai Jumat masuk ke minggu Jumat pada minggu itu.
    - Sabtu dan Minggu masuk ke minggu Jumat berikutnya.
    """
    if pd.isna(value):
        return "-", "-"

    date_value = pd.to_datetime(value).date()
    weekday = date_value.weekday()

    if weekday == 5:  # Sabtu
        friday_date = date_value + timedelta(days=6)
    elif weekday == 6:  # Minggu
        friday_date = date_value + timedelta(days=5)
    else:
        friday_date = date_value + timedelta(days=4 - weekday)

    iso_year, iso_week, _ = friday_date.isocalendar()

    label = f"Minggu ke-{iso_week} ({iso_year})"
    return label, iso_week


def add_custom_week_columns(df, date_col="Waktu_Dt"):
    """Menambahkan kolom Periode_Minggu ke DataFrame."""
    if df.empty or date_col not in df.columns:
        df["Periode_Minggu"] = "-"
        return df

    df["Periode_Minggu"] = df[date_col].apply(
        lambda value: get_custom_week_info(value)[0]
    )
    return df
