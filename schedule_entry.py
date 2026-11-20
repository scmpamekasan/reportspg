import json
import re
from datetime import date, timedelta
from io import BytesIO
import os

import openpyxl
import pandas as pd
import streamlit as st


SCHEDULE_FILE = "Jadwal SPG.xlsx"
SCHEDULE_DETAIL_FILE = "jadwal_spg_detail.json"
TEAM_NAMES_FILE = "master_nama_team.json"
TEAM_BRANDS_FILE = "master_team_brand.json"
BRANDS_FILE = "master_brand_rokok.json"
VEHICLES_FILE = "master_plat_kendaraan.json"
CITIES = ["Surabaya", "Gresik"]
WEEKDAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
DEFAULT_VEHICLES = ["L 1234 ABC"]
DEFAULT_BRANDS = [
    "D.Super 12", "D.76 Apel", "D.76 Apel Royal", "Black Matcha K12",
    "Djarum 76 Aksara", "Black Matcha Siro", "Black Matcha Kuro",
]


def load_schedule():
    if not os.path.exists(SCHEDULE_FILE):
        return pd.DataFrame(columns=["Kota", "Kecamatan"])
    try:
        frame = pd.read_excel(SCHEDULE_FILE)
        frame.columns = [str(column).strip() for column in frame.columns]
        return frame
    except Exception as exc:
        st.error(f"Gagal membaca {SCHEDULE_FILE}: {exc}")
        return pd.DataFrame(columns=["Kota", "Kecamatan"])


def save_schedule(frame):
    try:
        frame.to_excel(SCHEDULE_FILE, index=False)
        return True
    except Exception as exc:
        st.error(f"Gagal menyimpan {SCHEDULE_FILE}: {exc}")
        return False


def read_json(path, fallback):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, ValueError, TypeError):
            pass
    return fallback


def load_details():
    details = read_json(SCHEDULE_DETAIL_FILE, {})
    return details if isinstance(details, dict) else {}


def save_details(details):
    try:
        with open(SCHEDULE_DETAIL_FILE, "w", encoding="utf-8") as file:
            json.dump(details, file, ensure_ascii=False, indent=2)
        return True
    except (OSError, TypeError, ValueError) as exc:
        st.error(f"Gagal menyimpan detail kendaraan/brand jadwal: {exc}")
        return False


def team_mapping():
    defaults = {f"Team SPG {number}": f"Team SPG {number}" for number in range(1, 21)}
    if not os.path.exists(TEAM_NAMES_FILE):
        return defaults
    mapping = read_json(TEAM_NAMES_FILE, {})
    if isinstance(mapping, dict):
        defaults.update({key: str(mapping.get(key, key)).strip() for key in defaults})
    return defaults


def team_choices():
    return [team for team in team_mapping().values() if team]


def schedule_team_names(frame, date_cols):
    names = []
    seen = set()
    for _, row in frame.iterrows():
        for date_col in date_cols:
            value = row.get(date_col)
            if not is_active(value):
                continue
            name = str(value).strip()
            normalized = name.casefold()
            if normalized not in seen:
                seen.add(normalized)
                names.append(name)
    return names


def save_team_names_from_schedule(team_names):
    if len(team_names) > 20:
        st.error("Jadwal memuat lebih dari 20 team. Master Nama Team hanya mendukung 20 team.")
        return False
    if not team_names:
        st.error("Jadwal harus memuat minimal satu nama team aktif.")
        return False

    mapping = {
        f"Team SPG {number}": team_names[number - 1] if number <= len(team_names) else ""
        for number in range(1, 21)
    }
    try:
        with open(TEAM_NAMES_FILE, "w", encoding="utf-8") as file:
            json.dump(mapping, file, ensure_ascii=False, indent=2)
        return True
    except (OSError, TypeError, ValueError) as exc:
        st.error(f"Gagal menyimpan master nama team dari jadwal: {exc}")
        return False


def brands_for_team(team):
    all_brands = read_json(BRANDS_FILE, DEFAULT_BRANDS)
    if not isinstance(all_brands, list):
        all_brands = DEFAULT_BRANDS
    allocations = read_json(TEAM_BRANDS_FILE, {})
    if not isinstance(allocations, dict):
        allocations = {}
    selected = allocations.get(team)
    if selected is None:
        for canonical, alias in team_mapping().items():
            if alias == team:
                selected = allocations.get(canonical)
                if selected is not None:
                    break
    if not isinstance(selected, list) or not selected:
        selected = all_brands
    return [str(brand) for brand in selected if str(brand) in all_brands] or all_brands


def vehicle_choices():
    vehicles = read_json(VEHICLES_FILE, DEFAULT_VEHICLES)
    if isinstance(vehicles, dict):
        vehicles = list(vehicles.values())
    if not isinstance(vehicles, list):
        vehicles = DEFAULT_VEHICLES
    cleaned = list(dict.fromkeys(str(vehicle).strip() for vehicle in vehicles if str(vehicle).strip()))
    return cleaned or DEFAULT_VEHICLES


def get_geo_districts(city):
    filename = "Gresik.geojson" if city == "Gresik" else "Surabaya Barat.geojson"
    try:
        with open(filename, "r", encoding="utf-8") as file:
            geojson = json.load(file)
        frame = pd.DataFrame(feature.get("properties", {}) for feature in geojson.get("features", []))
        column = next(
            (name for name in ["nm_kecamatan", "KECAMATAN", "kecamatan", "Name", "NAME"] if name in frame.columns),
            None,
        )
        if column:
            return sorted(frame[column].dropna().astype(str).str.strip().unique().tolist())
    except (OSError, ValueError, TypeError):
        pass
    return ["Tegalsari", "Wonokromo", "Rungkut", "Asemrowo", "Benowo"]


def is_active(value):
    if pd.isna(value):
        return False
    return str(value).strip().lower() not in {"", "-", "nan", "none"}


def parse_schedule_date(value):
    if pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def parse_flat_schedule_header(column):
    label = str(column).strip()
    lowered = label.casefold()
    kind = "team"
    if "kendaraan" in lowered or "plat" in lowered:
        kind = "vehicle"
        label = re.sub(r"(kendaraan|plat(?:\s*(?:nomor|nomer))?)", "", label, flags=re.IGNORECASE)
    elif "nama team" in lowered:
        label = re.sub(r"nama\s*team", "", label, flags=re.IGNORECASE)
    label = label.strip(" -|:_/")
    return parse_schedule_date(label), kind


def validate_schedule_upload(uploaded_file):
    try:
        uploaded_file.seek(0)
        raw = pd.read_excel(uploaded_file, header=None)
    except Exception as exc:
        return None, None, None, None, None, f"File Excel tidak dapat dibaca: {exc}"
    if raw.empty or len(raw.index) < 2:
        return None, None, None, None, None, "File tidak memiliki header dan data jadwal."

    header = raw.iloc[0]
    normalized_header = {
        index: str(value).strip().casefold()
        for index, value in header.items()
        if not pd.isna(value)
    }
    city_index = next((i for i, value in normalized_header.items() if "kota" in value), None)
    district_index = next((i for i, value in normalized_header.items() if "kecamatan" in value), None)
    if city_index is None or district_index is None or city_index == district_index:
        return None, None, None, None, None, "File harus memiliki kolom Kota dan Kecamatan."

    subheader = raw.iloc[1]
    subheader_labels = {
        index: str(value).strip().casefold()
        for index, value in subheader.items()
        if not pd.isna(value)
    }
    team_indexes = {}
    vehicle_indexes = {}
    raw_has_two_header_rows = True
    for index, value in header.items():
        work_date = parse_schedule_date(value)
        if work_date is None:
            continue
        date_key = date_column(work_date)
        label = subheader_labels.get(index, "")
        if "kendaraan" in label or "plat" in label:
            return None, None, None, None, None, "Kolom tanggal harus berada di atas kolom Nama Team."
        team_index = index
        vehicle_index = None
        if "nama team" in label:
            vehicle_label = subheader_labels.get(index + 1, "")
            if "kendaraan" in vehicle_label or "plat" in vehicle_label:
                vehicle_index = index + 1
        if date_key in team_indexes:
            return None, None, None, None, None, f"Tanggal {date_key[:10]} muncul lebih dari sekali."
        team_indexes[date_key] = team_index
        if vehicle_index is not None:
            vehicle_indexes[date_key] = vehicle_index

    has_team_subheaders = any("nama team" in label for label in subheader_labels.values())
    if not team_indexes or not has_team_subheaders:
        uploaded_file.seek(0)
        try:
            frame = pd.read_excel(uploaded_file)
        except Exception as exc:
            return None, None, None, None, None, f"File Excel tidak dapat dibaca: {exc}"
        frame.columns = [str(column).strip() for column in frame.columns]
        if not len(frame.columns) or any(not column for column in frame.columns):
            return None, None, None, None, None, "File harus memiliki nama kolom yang valid."
        if len(set(frame.columns)) != len(frame.columns):
            return None, None, None, None, None, "Nama kolom pada file tidak boleh duplikat."
        city_col = next((col for col in frame.columns if "kota" in col.lower()), None)
        district_col = next((col for col in frame.columns if "kecamatan" in col.lower()), None)
        if not city_col or not district_col or city_col == district_col:
            return None, None, None, None, None, "File harus memiliki kolom Kota dan Kecamatan."

        team_columns = {}
        vehicle_indexes = {}
        for col in frame.columns:
            if col in {city_col, district_col}:
                continue
            work_date, column_kind = parse_flat_schedule_header(col)
            if work_date is None:
                return None, None, None, None, None, (
                    f"Kolom '{col}' bukan tanggal jadwal atau kolom kendaraan bertanggal yang valid."
                )
            date_key = date_column(work_date)
            target_columns = vehicle_indexes if column_kind == "vehicle" else team_columns
            if date_key in target_columns:
                column_label = "kendaraan/plat" if column_kind == "vehicle" else "nama team"
                return None, None, None, None, None, (
                    f"Kolom {column_label} untuk tanggal {date_key[:10]} muncul lebih dari sekali."
                )
            target_columns[date_key] = col
        missing_team_dates = sorted(set(vehicle_indexes) - set(team_columns))
        if missing_team_dates:
            return None, None, None, None, None, (
                f"Kolom kendaraan tidak memiliki kolom Nama Team untuk tanggal {missing_team_dates[0][:10]}."
            )
        if not team_columns:
            return None, None, None, None, None, "File harus memiliki kolom tanggal dan Nama Team."

        team_indexes = team_columns
        raw = frame
        raw_city_col, raw_district_col = city_col, district_col
        frame = frame[[city_col, district_col, *team_columns.values()]].rename(
            columns={
                city_col: "Kota",
                district_col: "Kecamatan",
                **{column: date_key for date_key, column in team_columns.items()},
            }
        )
        city_col, district_col = "Kota", "Kecamatan"
        date_cols = [date_key for date_key in team_indexes]
        multi_header = bool(vehicle_indexes)
        raw_has_two_header_rows = False
    else:
        city_col, district_col = "Kota", "Kecamatan"
        date_cols = list(team_indexes)
        raw_city_col, raw_district_col = city_index, district_index
        multi_header = True
        rows = []
        for _, source_row in raw.iloc[2:].iterrows():
            row = {
                city_col: source_row.get(raw_city_col),
                district_col: source_row.get(raw_district_col),
            }
            for date_key, team_index in team_indexes.items():
                row[date_key] = source_row.get(team_index)
            rows.append(row)
        frame = pd.DataFrame(rows, columns=[city_col, district_col, *date_cols])

    seen_locations = set()
    for _, row in frame.iterrows():
        has_assignment = any(is_active(row.get(column)) for column in date_cols)
        city = str(row.get(city_col, "")).strip()
        district = str(row.get(district_col, "")).strip()
        if not has_assignment and not city and not district:
            continue
        if not city or city.casefold() in {"nan", "none"} or not district or district.casefold() in {"nan", "none"}:
            if not has_assignment:
                continue
            return None, None, None, None, None, "Setiap baris jadwal aktif harus memiliki Kota dan Kecamatan."
        location = (city.casefold(), district.casefold())
        if location in seen_locations:
            return None, None, None, None, None, f"Lokasi {city} / {district} muncul lebih dari sekali."
        seen_locations.add(location)

    uploaded_vehicles = {}
    if multi_header:
        source_rows = raw.iloc[2:].iterrows() if raw_has_two_header_rows else raw.iterrows()
        for _, source_row in source_rows:
            city = str(source_row.get(raw_city_col, "")).strip()
            district = str(source_row.get(raw_district_col, "")).strip()
            if not city or not district or city.casefold() == "nan" or district.casefold() == "nan":
                continue
            for date_key, team_column in team_indexes.items():
                if not is_active(source_row.get(team_column)):
                    continue
                vehicle_column = vehicle_indexes.get(date_key)
                if vehicle_column is None:
                    continue
                vehicle = source_row.get(vehicle_column)
                uploaded_vehicles[assignment_key(parse_schedule_date(date_key), city, district)] = (
                    "" if pd.isna(vehicle) else str(vehicle).strip()
                )

    return frame, city_col, district_col, date_cols, uploaded_vehicles, None


def retain_matching_schedule_details(details, frame, city_col, district_col, date_cols):
    assignments = {}
    for _, row in frame.iterrows():
        city = str(row.get(city_col, "")).strip()
        district = str(row.get(district_col, "")).strip()
        if not city or not district:
            continue
        for date_col in date_cols:
            team = row.get(date_col)
            if not is_active(team):
                continue
            work_date = pd.to_datetime(date_col, errors="coerce")
            if not pd.isna(work_date):
                assignments[assignment_key(work_date.date(), city, district)] = str(team).strip()

    retained = {}
    for key, saved in details.items():
        team = assignments.get(key)
        if team is None:
            continue
        saved_team = saved.get("team") if isinstance(saved, dict) else None
        if saved_team and str(saved_team).strip().casefold() != team.casefold():
            continue
        retained[key] = saved
    return retained


def build_schedule_excel(schedule, details, city_col, district_col):
    date_cols = [
        column
        for column in schedule.columns
        if column not in {city_col, district_col} and parse_schedule_date(column) is not None
    ]
    header = [city_col, district_col]
    subheader = [None, None]
    normalized_date_cols = []
    for column in date_cols:
        work_date = parse_schedule_date(column)
        normalized_date_cols.append((column, work_date))
        header.extend([work_date, None])
        subheader.extend(["Nama Team", "Kendaraan / Plat Nomor"])

    rows = [header, subheader]
    for _, source_row in schedule.iterrows():
        city = source_row.get(city_col, "")
        district = source_row.get(district_col, "")
        row = [city, district]
        for column, work_date in normalized_date_cols:
            row.append(source_row.get(column, ""))
            saved = details.get(assignment_key(work_date, city, district), {})
            vehicle = saved.get("vehicle", "") if isinstance(saved, dict) else ""
            row.append(vehicle)
        rows.append(row)

    buffer = BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, header=False)
    return buffer.getvalue()

def build_schedule_template_excel(week_anchor):
    week_start = week_anchor - timedelta(days=week_anchor.weekday())
    workdays = [week_start + timedelta(days=offset) for offset in range(5)]
    locations = [
        (city, district)
        for city in CITIES
        for district in get_geo_districts(city)
    ]

    header = ["Kota", "Kecamatan"]
    subheader = ["", ""]
    for workday in workdays:
        header.extend([workday, None])
        subheader.extend(["Nama Team", "Kendaraan / Plat Nomor"])

    rows = [header, subheader]
    rows.extend([[city, district, *("" for _ in range(len(workdays) * 2))] for city, district in locations])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(
            writer, sheet_name="Jadwal SPG", index=False, header=False
        )
        workbook = writer.book
        master_sheet = workbook.create_sheet("Master")
        master_sheet["A1"] = "Nama Team"
        master_sheet["B1"] = "Plat Kendaraan"
        teams = team_choices()
        vehicles = vehicle_choices()
        for row_number, team in enumerate(teams, start=2):
            master_sheet.cell(row=row_number, column=1, value=team)
        for row_number, vehicle in enumerate(vehicles, start=2):
            master_sheet.cell(row=row_number, column=2, value=vehicle)
        master_sheet.sheet_state = "hidden"

        worksheet = writer.sheets["Jadwal SPG"]
        worksheet.freeze_panes = "C3"
        worksheet.column_dimensions["A"].width = 18
        worksheet.column_dimensions["B"].width = 24
        for column_number in range(3, len(header) + 1):
            worksheet.column_dimensions[
                openpyxl.utils.get_column_letter(column_number)
            ].width = 22

        if locations:
            last_row = len(rows)
            team_last_row = max(2, len(teams) + 1)
            vehicle_last_row = max(2, len(vehicles) + 1)
            team_validation = openpyxl.worksheet.datavalidation.DataValidation(
                type="list",
                formula1=f'=INDIRECT("\'Master\'!$A$2:$A${team_last_row}")',
                allow_blank=True,
            )
            vehicle_validation = openpyxl.worksheet.datavalidation.DataValidation(
                type="list",
                formula1=f'=INDIRECT("\'Master\'!$B$2:$B${vehicle_last_row}")',
                allow_blank=True,
            )
            worksheet.add_data_validation(team_validation)
            worksheet.add_data_validation(vehicle_validation)
            for column_number in range(3, len(header) + 1, 2):
                team_validation.add(
                    f"{openpyxl.utils.get_column_letter(column_number)}3:"
                    f"{openpyxl.utils.get_column_letter(column_number)}{last_row}"
                )
                vehicle_validation.add(
                    f"{openpyxl.utils.get_column_letter(column_number + 1)}3:"
                    f"{openpyxl.utils.get_column_letter(column_number + 1)}{last_row}"
                )

    return output.getvalue()

def build_schedule_preview(frame, details, city_col, district_col, date_cols, uploaded_vehicles):
    preview_rows = []
    preview_columns = [city_col, district_col]
    for date_col in date_cols:
        work_date = parse_schedule_date(date_col)
        date_label = work_date.strftime("%Y-%m-%d") if work_date else str(date_col)
        preview_columns.extend(
            [f"{date_label} - Nama Team", f"{date_label} - Kendaraan / Plat Nomor"]
        )

    for _, source_row in frame.iterrows():
        city = source_row.get(city_col, "")
        district = source_row.get(district_col, "")
        preview_row = {city_col: city, district_col: district}
        for date_col in date_cols:
            work_date = parse_schedule_date(date_col)
            team = source_row.get(date_col, "")
            key = assignment_key(work_date, city, district) if work_date else None
            saved = details.get(key, {}) if key else {}
            vehicle = uploaded_vehicles.get(key) if key in uploaded_vehicles else (
                saved.get("vehicle", "") if isinstance(saved, dict) else ""
            )
            date_label = work_date.strftime("%Y-%m-%d") if work_date else str(date_col)
            preview_row[f"{date_label} - Nama Team"] = team
            preview_row[f"{date_label} - Kendaraan / Plat Nomor"] = vehicle
        preview_rows.append(preview_row)

    return pd.DataFrame(preview_rows, columns=preview_columns)


def date_column(value):
    return pd.Timestamp(value).strftime("%Y-%m-%d 00:00:00")


def assignment_key(work_date, city, district):
    normalized_city = str(city).strip().casefold()
    normalized_district = str(district).strip().casefold()
    return f"{date_column(work_date)}|{normalized_city}|{normalized_district}"


def assignment_details(details, work_date, city, district, team):
    saved = details.get(assignment_key(work_date, city, district), {})
    saved = saved if isinstance(saved, dict) else {}
    return {
        "team": team,
        "vehicle": str(saved.get("vehicle", "")),
        "brands": saved.get("brands", []) if isinstance(saved.get("brands", []), list) else [],
    }


def get_scheduled_vehicles(schedule_rows, work_date):
    if schedule_rows is None or schedule_rows.empty:
        return []

    details = load_details()
    vehicles = {}
    for _, row in schedule_rows.iterrows():
        saved = details.get(
            assignment_key(work_date, row.get("Kota", ""), row.get("Kecamatan", "")),
            {},
        )
        if not isinstance(saved, dict):
            continue
        assigned = saved.get("vehicle", "")
        if not isinstance(assigned, str):
            continue
        assigned = assigned.strip()
        if assigned.casefold() not in {"", "-", "nan", "none"}:
            vehicles.setdefault(assigned.casefold(), assigned)

    return sorted(vehicles.values(), key=str.casefold)


def week_info(value):
    iso = pd.Timestamp(value).isocalendar()
    return f"Minggu ke-{iso.week} · {iso.year}", (iso.year, iso.week)


def find_meta_columns(frame):
    city = next((col for col in frame.columns if "kota" in str(col).strip().lower()), "Kota")
    district = next((col for col in frame.columns if "kecamatan" in str(col).strip().lower()), "Kecamatan")
    if city not in frame.columns:
        frame[city] = ""
    if district not in frame.columns:
        frame[district] = ""
    return city, district


def add_assignments(frame, city_col, district_col, dates, city, districts, team):
    date_cols = [col for col in frame.columns if col not in {city_col, district_col}]
    conflicts = []
    for district in districts:
        matching = frame[
            frame[city_col].astype(str).str.strip().str.casefold().eq(city.strip().casefold())
            & frame[district_col].astype(str).str.strip().str.casefold().eq(district.strip().casefold())
        ]
        for workday in dates:
            column = date_column(workday)
            if not matching.empty and column in date_cols and is_active(frame.at[matching.index[0], column]):
                conflicts.append(f"{district} — {workday.strftime('%d-%m-%Y')}")
    if conflicts:
        return frame, conflicts

    for district in districts:
        for workday in dates:
            column = date_column(workday)
            if column not in frame.columns:
                frame[column] = "-"
            matching = frame[
                frame[city_col].astype(str).str.strip().str.casefold().eq(city.strip().casefold())
                & frame[district_col].astype(str).str.strip().str.casefold().eq(district.strip().casefold())
            ]
            if matching.empty:
                new_row = {col: "-" for col in frame.columns}
                new_row[city_col] = city
                new_row[district_col] = district
                new_row[column] = team
                frame = pd.concat([frame, pd.DataFrame([new_row])], ignore_index=True)
            else:
                frame.at[matching.index[0], column] = team
    return frame, []


def store_assignment_details(details, dates, city, districts, team, vehicle, brands):
    for workday in dates:
        for district in districts:
            details[assignment_key(workday, city, district)] = {
                "team": team,
                "vehicle": vehicle,
                "brands": list(brands),
            }
    return details


def render_schedule_entry():
    schedule = load_schedule()
    city_col, district_col = find_meta_columns(schedule)
    details = load_details()
    teams = team_choices()
    vehicles = vehicle_choices()

    # Scheduling, management, and Excel import/export share the same schedule data.
    tab_day, tab_week, tab_manage, tab_excel = st.tabs(
        [
            "➕ Tambah Hari Kerja",
            "🗓️ Tambah Minggu Kerja",
            "✏️ Kelola Jadwal Aktif",
            "📥 Download / Upload Excel",
        ]
    )

    with tab_day:
        st.markdown("#### Buat jadwal untuk satu hari")
        st.caption("Data team, merek rokok, dan kendaraan diambil dari master data.")
        with st.form("form_add_schedule_day"):
            col_date, col_city, col_team = st.columns(3)
            with col_date:
                work_date = st.date_input("Tanggal kerja", value=date.today(), key="new_workday_date")
            with col_city:
                city = st.selectbox("Kota / Kabupaten", CITIES, key="new_workday_city")
            with col_team:
                team = st.selectbox("Master Team SPG", teams, key="new_workday_team")
            districts = st.multiselect("Kecamatan yang dijadwalkan", get_geo_districts(city), key="new_workday_districts")
            col_vehicle, col_brands = st.columns(2)
            with col_vehicle:
                vehicle = st.selectbox("Kendaraan / Plat Nomor", vehicles, key="new_workday_vehicle")
            with col_brands:
                brands = st.multiselect(
                    "Rokok yang dibawa",
                    brands_for_team(team),
                    default=brands_for_team(team),
                    key="new_workday_brands",
                    help="Pilihan merek mengikuti alokasi pada Master Team & Brand.",
                )
            submit_day = st.form_submit_button("💾 Simpan Jadwal Hari Ini", type="primary")
        if submit_day:
            if not districts:
                st.warning("Pilih minimal satu kecamatan terlebih dahulu.")
            elif not brands:
                st.warning("Pilih minimal satu merek rokok yang dibawa.")
            else:
                updated, conflicts = add_assignments(schedule.copy(), city_col, district_col, [work_date], city, districts, team)
                if conflicts:
                    st.error("Sudah ada jadwal pada lokasi dan tanggal berikut: " + ", ".join(conflicts))
                elif save_schedule(updated):
                    details = store_assignment_details(details, [work_date], city, districts, team, vehicle, brands)
                    if save_details(details):
                        st.success(f"Jadwal {team} tersimpan untuk {len(districts)} kecamatan, termasuk kendaraan dan brand.")
                    st.rerun()

    with tab_week:
        st.markdown("#### Buat jadwal satu minggu")
        st.caption("Pilih hari kerja, kecamatan, team, merek yang dibawa, dan kendaraan. Jadwal yang bentrok tidak akan ditimpa.")
        with st.form("form_add_schedule_week"):
            col_anchor, col_city, col_team = st.columns(3)
            with col_anchor:
                week_anchor = st.date_input("Tanggal dalam minggu tujuan", value=date.today(), key="new_week_anchor")
            week_start = week_anchor - timedelta(days=week_anchor.weekday())
            week_end = week_start + timedelta(days=6)
            with col_city:
                week_city = st.selectbox("Kota / Kabupaten", CITIES, key="new_week_city")
            with col_team:
                week_team = st.selectbox("Master Team SPG", teams, key="new_week_team")
            st.info(f"Periode minggu: {week_start.strftime('%d %b %Y')} – {week_end.strftime('%d %b %Y')}")
            workdays = st.multiselect("Hari kerja", WEEKDAYS, default=WEEKDAYS[:5], key="new_week_days")
            week_districts = st.multiselect("Kecamatan yang dijadwalkan", get_geo_districts(week_city), key="new_week_districts")
            col_vehicle_week, col_brands_week = st.columns(2)
            with col_vehicle_week:
                week_vehicle = st.selectbox("Kendaraan / Plat Nomor", vehicles, key="new_week_vehicle")
            with col_brands_week:
                week_brands = st.multiselect(
                    "Rokok yang dibawa", brands_for_team(week_team), default=brands_for_team(week_team),
                    key="new_week_brands", help="Pilihan merek mengikuti alokasi pada Master Team & Brand.",
                )
            submit_week = st.form_submit_button("🗓️ Buat Jadwal Mingguan", type="primary")
        if submit_week:
            if not workdays or not week_districts:
                st.warning("Pilih minimal satu hari kerja dan satu kecamatan.")
            elif not week_brands:
                st.warning("Pilih minimal satu merek rokok yang dibawa.")
            else:
                day_index = {label: index for index, label in enumerate(WEEKDAYS)}
                selected_dates = [week_start + timedelta(days=day_index[label]) for label in workdays]
                updated, conflicts = add_assignments(
                    schedule.copy(), city_col, district_col, selected_dates, week_city, week_districts, week_team
                )
                if conflicts:
                    st.error("Ada jadwal yang sudah terisi. Tidak ada perubahan yang disimpan: " + ", ".join(conflicts))
                elif save_schedule(updated):
                    details = store_assignment_details(
                        details, selected_dates, week_city, week_districts, week_team, week_vehicle, week_brands
                    )
                    if save_details(details):
                        st.success(f"Berhasil membuat {len(selected_dates) * len(week_districts)} penugasan untuk {week_team}.")
                    st.rerun()

    with tab_manage:
        st.markdown("#### Jadwal aktif")
        st.caption("Master team, alokasi merek, dan data kendaraan ditampilkan pada setiap penugasan.")
        date_cols = [col for col in schedule.columns if col not in {city_col, district_col}]
        entries = []
        for row_index, row in schedule.iterrows():
            for date_col in date_cols:
                parsed_date = pd.to_datetime(date_col, errors="coerce")
                if pd.isna(parsed_date) or not is_active(row.get(date_col, "")):
                    continue
                label, sort_key = week_info(parsed_date)
                city_value = str(row.get(city_col, "") if pd.notna(row.get(city_col, "")) else "").strip()
                district_value = str(row.get(district_col, "") if pd.notna(row.get(district_col, "")) else "").strip()
                team_value = str(row.get(date_col, "")).strip()
                saved = assignment_details(details, parsed_date.date(), city_value, district_value, team_value)
                entries.append({
                    "row": row_index, "date_col": date_col, "date": parsed_date.date(),
                    "week": label, "week_sort": sort_key, "city": city_value,
                    "district": district_value, "team": team_value,
                    "vehicle": saved["vehicle"], "brands": saved["brands"],
                })

        if not entries:
            st.info("Belum ada jadwal aktif. Gunakan tab **Tambah Hari Kerja** atau **Tambah Minggu Kerja** untuk mulai.")
        else:
            weeks_by_sort = {entry["week_sort"]: entry["week"] for entry in entries}
            week_labels = [weeks_by_sort[key] for key in sorted(weeks_by_sort, reverse=True)]
            selected_weeks = st.multiselect(
                "Filter periode", week_labels, default=[week_labels[0]], key="schedule_entry_weeks"
            )
            visible_entries = sorted(
                [entry for entry in entries if entry["week"] in selected_weeks],
                key=lambda entry: (entry["date"], entry["city"], entry["district"], entry["team"]),
            )
            st.markdown(f"**{len(visible_entries)} jadwal aktif**")

            for entry in visible_entries:
                entry_id = f"{entry['row']}_{entry['date_col']}"
                team_widget_key = f"team_{entry_id}_{entry['team']}"
                vehicle_widget_key = f"vehicle_{entry_id}_{entry['vehicle']}"
                heading = (
                    f"{entry['date'].strftime('%d-%m-%Y')} · "
                    f"{entry['district'] or 'Kecamatan belum diisi'} · {entry['team']} · "
                    f"Plat: {entry['vehicle'] or 'Belum diatur'}"
                )
                with st.expander(f"📍 {heading}", expanded=False):
                    brands_allowed = brands_for_team(entry["team"])
                    default_brands = [brand for brand in entry["brands"] if brand in brands_allowed]
                    entry_teams = teams if entry["team"] in teams else [entry["team"], *teams]
                    entry_vehicles = vehicles if entry["vehicle"] in vehicles else [entry["vehicle"], *vehicles]
                    saved_vehicle = entry["vehicle"] or vehicles[0]
                    st.caption(f"{entry['week']} · Kendaraan: {entry['vehicle'] or 'Belum diatur'} · Brand: {', '.join(entry['brands']) or 'Belum diatur'}")
                    with st.form(f"edit_schedule_{entry_id}"):
                        col_date_edit, col_city_edit = st.columns(2)
                        with col_date_edit:
                            edited_date = st.date_input("Tanggal kerja", value=entry["date"], key=f"date_{entry_id}")
                        with col_city_edit:
                            city_index = CITIES.index(entry["city"]) if entry["city"] in CITIES else 0
                            edited_city = st.selectbox("Kota / Kabupaten", CITIES, index=city_index, key=f"city_{entry_id}")
                        col_district_edit, col_team_edit = st.columns(2)
                        with col_district_edit:
                            district_options = get_geo_districts(edited_city)
                            district_index = district_options.index(entry["district"]) if entry["district"] in district_options else None
                            if district_index is None:
                                edited_district = st.text_input("Kecamatan", value=entry["district"], key=f"district_{entry_id}")
                            else:
                                edited_district = st.selectbox("Kecamatan", district_options, index=district_index, key=f"district_{entry_id}")
                        with col_team_edit:
                            edited_team = st.selectbox(
                                "Master Team SPG", entry_teams,
                                index=entry_teams.index(entry["team"]), key=team_widget_key,
                            )
                        col_vehicle_edit, col_brands_edit = st.columns(2)
                        with col_vehicle_edit:
                            edited_vehicle = st.selectbox(
                                "Kendaraan / Plat Nomor", entry_vehicles,
                                index=entry_vehicles.index(saved_vehicle), key=vehicle_widget_key,
                            )
                        with col_brands_edit:
                            edited_brands = st.multiselect(
                                "Rokok yang dibawa", brands_for_team(edited_team), default=default_brands,
                                key=f"brands_{entry_id}", help="Pilihan merek mengikuti alokasi Master Team & Brand.",
                            )
                        save_col, delete_col = st.columns(2)
                        with save_col:
                            save_clicked = st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True)
                        with delete_col:
                            delete_clicked = st.form_submit_button("🗑️ Hapus Jadwal Ini", use_container_width=True)

                    if save_clicked:
                        if not str(edited_district).strip():
                            st.warning("Kecamatan wajib diisi.")
                        elif not edited_brands:
                            st.warning("Pilih minimal satu merek rokok.")
                        else:
                            destination_col = date_column(edited_date)
                            destination_rows = schedule[
                                schedule[city_col].astype(str).str.strip().str.casefold().eq(edited_city.strip().casefold())
                                & schedule[district_col].astype(str).str.strip().str.casefold().eq(edited_district.strip().casefold())
                            ].index
                            destination_row = destination_rows[0] if len(destination_rows) else entry["row"]
                            destination_value = schedule.at[destination_row, destination_col] if destination_col in schedule.columns else "-"
                            same_assignment = (
                                destination_col == entry["date_col"]
                                and destination_row == entry["row"]
                            )
                            if not same_assignment and is_active(destination_value):
                                st.error("Tanggal dan kecamatan tujuan sudah memiliki jadwal aktif. Pilih tujuan lain.")
                            else:
                                if destination_col not in schedule.columns:
                                    schedule[destination_col] = "-"
                                old_key = assignment_key(entry["date"], entry["city"], entry["district"])
                                new_key = assignment_key(edited_date, edited_city, edited_district)
                                if not same_assignment:
                                    schedule.at[entry["row"], entry["date_col"]] = "-"
                                    if len(destination_rows) == 0:
                                        new_row = {col: "-" for col in schedule.columns}
                                        new_row[city_col] = edited_city
                                        new_row[district_col] = edited_district.strip()
                                        schedule = pd.concat([schedule, pd.DataFrame([new_row])], ignore_index=True)
                                        destination_row = schedule.index[-1]
                                schedule.at[destination_row, city_col] = edited_city
                                schedule.at[destination_row, district_col] = edited_district.strip()
                                schedule.at[destination_row, destination_col] = edited_team
                                if old_key != new_key:
                                    details.pop(old_key, None)
                                details[new_key] = {
                                    "team": edited_team,
                                    "vehicle": edited_vehicle,
                                    "brands": list(edited_brands),
                                }
                                if save_schedule(schedule) and save_details(details):
                                    st.success("Jadwal, team, kendaraan, dan brand berhasil diperbarui.")
                                    st.rerun()

                    if delete_clicked:
                        schedule.at[entry["row"], entry["date_col"]] = "-"
                        details.pop(assignment_key(entry["date"], entry["city"], entry["district"]), None)
                        if save_schedule(schedule) and save_details(details):
                            st.success("Jadwal dan detail kendaraan/brand berhasil dihapus.")
                            st.rerun()

    if st.button("🔄 Muat Ulang Jadwal", key="reload_schedule"):
        st.rerun()

    with tab_excel:
        st.markdown("#### Unduh dan unggah jadwal melalui Excel")
        st.caption(
            "Unggah jadwal dengan kolom Kota dan Kecamatan serta kolom tanggal untuk Nama Team dan "
            "Kendaraan / Plat Nomor. Nilai team dan plat akan otomatis mengisi Jadwal Aktif. "
            "Unggah akan mengganti seluruh jadwal aktif setelah Anda memeriksa pratinjau. "
            "Detail kendaraan/brand dipertahankan untuk penugasan yang tetap sama."
        )

        template_anchor = st.date_input(
            "Tanggal acuan minggu template",
            value=date.today(),
            key="schedule_template_week",
        )
        st.caption(
            "Template berisi seluruh kecamatan Surabaya dan Gresik untuk Senin–Jumat "
            "pada minggu terpilih. Nama team dan plat kendaraan tersedia sebagai pilihan."
        )
        st.download_button(
            "📄 Download Template Jadwal SPG",
            data=build_schedule_template_excel(template_anchor),
            file_name="Template Jadwal SPG.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_schedule_template",
        )

        st.download_button(
            "⬇️ Download Jadwal SPG Saat Ini",
            data=build_schedule_excel(schedule, details, city_col, district_col),
            file_name="Jadwal SPG.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_current_schedule",
        )

        uploaded_file = st.file_uploader(
            "Pilih file Excel jadwal untuk diunggah",
            type=["xlsx"],
            key="upload_schedule_excel",
        )
        if uploaded_file is not None:
            (
                upload_frame,
                upload_city_col,
                upload_district_col,
                upload_date_cols,
                uploaded_vehicles,
                upload_error,
            ) = validate_schedule_upload(uploaded_file)
            if upload_error:
                st.error(upload_error)
            else:
                st.markdown("##### Pratinjau jadwal yang akan diunggah")
                st.dataframe(
                    build_schedule_preview(
                        upload_frame,
                        load_details(),
                        upload_city_col,
                        upload_district_col,
                        upload_date_cols,
                        uploaded_vehicles,
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                st.warning("Tindakan ini mengganti seluruh jadwal aktif dengan isi file di atas.")
                uploaded_team_names = schedule_team_names(upload_frame, upload_date_cols)
                if len(uploaded_team_names) > 20:
                    st.error("File jadwal berisi lebih dari 20 team; jumlah maksimum yang didukung adalah 20.")
                elif not uploaded_team_names:
                    st.error("File jadwal harus berisi minimal satu nama team aktif.")
                if st.button(
                    "Ganti Jadwal Aktif dengan File Excel Ini",
                    type="primary",
                    key="confirm_schedule_excel_upload",
                ) and 0 < len(uploaded_team_names) <= 20:
                    updated_details = retain_matching_schedule_details(
                        load_details(),
                        upload_frame,
                        upload_city_col,
                        upload_district_col,
                        upload_date_cols,
                    )
                    if uploaded_vehicles:
                        for _, row in upload_frame.iterrows():
                            city = str(row.get(upload_city_col, "")).strip()
                            district = str(row.get(upload_district_col, "")).strip()
                            if not city or not district:
                                continue
                            for date_col in upload_date_cols:
                                team = row.get(date_col)
                                if not is_active(team):
                                    continue
                                work_date = parse_schedule_date(date_col)
                                key = assignment_key(work_date, city, district)
                                if key not in uploaded_vehicles:
                                    continue
                                saved = updated_details.get(key, {})
                                saved = saved.copy() if isinstance(saved, dict) else {}
                                saved["team"] = str(team).strip()
                                saved["vehicle"] = uploaded_vehicles[key]
                                saved.setdefault("brands", [])
                                updated_details[key] = saved
                    if save_schedule(upload_frame):
                        if save_details(updated_details):
                            if save_team_names_from_schedule(uploaded_team_names):
                                st.success(
                                    f"Jadwal berhasil diperbarui. {len(uploaded_team_names)} nama team "
                                    "diisi berurutan pada Master Data: Nama Team."
                                )
                                st.rerun()
                            st.error(
                                "Jadwal berhasil diperbarui, tetapi Master Nama Team gagal disinkronkan."
                            )
                        else:
                            st.error(
                                "Jadwal berhasil diperbarui, tetapi sinkronisasi detail kendaraan/brand gagal. "
                                "Periksa kembali detail jadwal."
                            )
