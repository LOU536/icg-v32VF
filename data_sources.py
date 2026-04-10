import requests
import pandas as pd
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent
DATA_DIR = BASE_PATH / "data"

WORLD_BANK_INDICATORS = {
    "gdp_usd": "NY.GDP.MKTP.CD",
    "reserves_usd": "FI.RES.TOTL.CD",
    "energy_import_pct": "EG.IMP.CONS.ZS",
}

COUNTRIES = {
    "USA": "United States",
    "CHN": "China",
    "DEU": "Germany",
    "FRA": "France",
    "JPN": "Japan",
    "IND": "India",
    "BRA": "Brazil",
    "RUS": "Russia",
    "SAU": "Saudi Arabia",
    "ARE": "UAE",
    "KOR": "South Korea",
    "IDN": "Indonesia",
    "TUR": "Turkey",
    "ZAF": "South Africa",
    "MEX": "Mexico",
    "CAN": "Canada",
    "AUS": "Australia",
    "POL": "Poland",
    "KAZ": "Kazakhstan",
    "IRN": "Iran",
    "PRK": "North Korea",
    "VEN": "Venezuela",
}


def fetch_world_bank_indicator(indicator: str, year: int = 2023, timeout: int = 12) -> pd.DataFrame:
    url = (
        f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
        f"?format=json&date={year}&per_page=400"
    )

    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    payload = r.json()

    if len(payload) < 2 or not payload[1]:
        return pd.DataFrame(columns=["iso3", "value"])

    rows = []
    for row in payload[1]:
        iso3 = row.get("countryiso3code")
        value = row.get("value")
        if iso3 in COUNTRIES and value is not None:
            rows.append({"iso3": iso3, "value": value})

    return pd.DataFrame(rows)


def fetch_world_bank_bundle(year: int = 2023) -> pd.DataFrame:
    base = pd.DataFrame({
        "iso3": list(COUNTRIES.keys()),
        "country": list(COUNTRIES.values()),
    })

    for col_name, indicator in WORLD_BANK_INDICATORS.items():
        df_i = fetch_world_bank_indicator(indicator, year=year).rename(columns={"value": col_name})
        base = base.merge(df_i, on="iso3", how="left")

    return base


def load_local_fallback() -> pd.DataFrame:
    fallback_path = DATA_DIR / "world_bank_fallback.csv"

    if not fallback_path.exists():
        return pd.DataFrame({
            "iso3": list(COUNTRIES.keys()),
            "country": list(COUNTRIES.values()),
            "gdp_usd": [None] * len(COUNTRIES),
            "reserves_usd": [None] * len(COUNTRIES),
            "energy_import_pct": [None] * len(COUNTRIES),
        })

    return pd.read_csv(fallback_path)


def enrich_with_world_bank(base_df: pd.DataFrame, wb_year: int = 2023) -> pd.DataFrame:
    try:
        wb_df = fetch_world_bank_bundle(year=wb_year)
    except Exception:
        wb_df = load_local_fallback()

    df = base_df.merge(wb_df, on=["iso3", "country"], how="left")
    return df


def load_regulatory_signals() -> pd.DataFrame:
    path = DATA_DIR / "regulatory_signals.csv"
    return pd.read_csv(path)


def load_base(wb_year: int = 2023) -> pd.DataFrame:
    base_df = load_regulatory_signals()
    return enrich_with_world_bank(base_df, wb_year=wb_year)
