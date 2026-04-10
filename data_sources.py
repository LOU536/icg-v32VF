from __future__ import annotations

import os
from io import StringIO
from typing import Dict, Iterable, Optional

import pandas as pd
import requests

WB_API = "https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&date={year}&per_page=400&mrv=1"

WB_INDICATORS = {
    "gdp_current_usd": "NY.GDP.MKTP.CD",
    "fx_reserves_usd": "FI.RES.TOTL.CD",
    "energy_import_pct": "EG.IMP.CONS.ZS",
}


def _country_fixups() -> Dict[str, str]:
    return {
        "United States": "USA",
        "China": "CHN",
        "Germany": "DEU",
        "India": "IND",
        "Brazil": "BRA",
        "Russia": "RUS",
        "Saudi Arabia": "SAU",
        "Japan": "JPN",
        "Canada": "CAN",
        "Mexico": "MEX",
        "Australia": "AUS",
        "South Korea": "KOR",
        "France": "FRA",
        "UAE": "ARE",
        "Turkey": "TUR",
        "Indonesia": "IDN",
        "South Africa": "ZAF",
        "Poland": "POL",
        "Kazakhstan": "KAZ",
        "Iran": "IRN",
        "Venezuela": "VEN",
        "North Korea": "PRK",
    }


def fetch_world_bank_indicator(indicator: str, year: int = 2023, timeout: int = 20) -> pd.DataFrame:
    url = WB_API.format(indicator=indicator, year=year)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["iso3", "value"])
    rows = []
    for item in payload[1]:
        iso3 = item.get("countryiso3code")
        value = item.get("value")
        if iso3 and value is not None:
            rows.append({"iso3": iso3, "value": float(value)})
    return pd.DataFrame(rows)


def fetch_world_bank_bundle(year: int = 2023) -> pd.DataFrame:
    merged: Optional[pd.DataFrame] = None
    for col_name, indicator in WB_INDICATORS.items():
        df = fetch_world_bank_indicator(indicator, year=year).rename(columns={"value": col_name})
        merged = df if merged is None else merged.merge(df, on="iso3", how="outer")
    return merged if merged is not None else pd.DataFrame(columns=["iso3", *WB_INDICATORS.keys()])


def load_regulatory_signals(csv_path: str = "data/regulatory_signals.csv") -> pd.DataFrame:
    return pd.read_csv(csv_path)


def enrich_with_world_bank(base_df: pd.DataFrame, wb_year: int = 2023) -> pd.DataFrame:
    wb_df = fetch_world_bank_bundle(year=wb_year)
    out = base_df.merge(wb_df, on="iso3", how="left")

    # Fallbacks keep app usable if World Bank has missing values for a country.
    if "gdp_current_usd" not in out.columns:
        out["gdp_current_usd"] = pd.NA
    if "fx_reserves_usd" not in out.columns:
        out["fx_reserves_usd"] = pd.NA
    if "energy_import_pct" not in out.columns:
        out["energy_import_pct"] = pd.NA

    # Conservative proxy fallbacks.
    out["gdp_current_usd"] = out["gdp_current_usd"].fillna(0)
    out["fx_reserves_usd"] = out["fx_reserves_usd"].fillna(0)
    out["energy_import_pct"] = out["energy_import_pct"].fillna(0)
    return out


def fetch_newsapi_articles(query: str, api_key: str, page_size: int = 20, timeout: int = 20) -> list[dict]:
    if not api_key:
        return []
    url = "https://newsapi.org/v2/everything"
    response = requests.get(
        url,
        params={
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": api_key,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("articles", [])


def compute_news_shock(articles: Iterable[dict], countries: Iterable[str]) -> pd.DataFrame:
    keywords = ["sanction", "sanctions", "export control", "embargo", "shipping", "tariff", "sps", "tbt"]
    rows = []
    names = list(countries)
    for country in names:
        score = 0.0
        country_lower = country.lower()
        for article in articles:
            text = f"{article.get('title','')} {article.get('description','')}".lower()
            if country_lower in text:
                hits = sum(1 for keyword in keywords if keyword in text)
                score += min(2.5, hits * 0.35)
        rows.append({"country": country, "news_shock": min(5.0, score)})
    return pd.DataFrame(rows)
