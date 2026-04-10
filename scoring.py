from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ThemeWeights:
    leverage: float
    resilience: float
    autonomy: float
    strategic_signal: float
    access_viability: float
    capital_confirmation: float


THEME_WEIGHTS = {
    "General": ThemeWeights(0.23, 0.19, 0.16, 0.16, 0.14, 0.12),
    "Petróleo": ThemeWeights(0.22, 0.23, 0.12, 0.10, 0.12, 0.21),
    "Minerales críticos": ThemeWeights(0.22, 0.15, 0.14, 0.18, 0.12, 0.19),
    "Semiconductores": ThemeWeights(0.17, 0.11, 0.17, 0.22, 0.15, 0.18),
    "Defensa": ThemeWeights(0.18, 0.19, 0.16, 0.18, 0.10, 0.19),
    "IA": ThemeWeights(0.15, 0.09, 0.16, 0.25, 0.15, 0.20),
    "Alimentos": ThemeWeights(0.15, 0.28, 0.17, 0.11, 0.13, 0.16),
    "Shipping": ThemeWeights(0.18, 0.15, 0.18, 0.15, 0.12, 0.22),
    "Barreras no arancelarias": ThemeWeights(0.11, 0.11, 0.16, 0.18, 0.30, 0.14),
}


def _norm(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0)
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series(50.0, index=s.index)
    return ((s - mn) / (mx - mn) * 100).clip(0, 100)


def calc_leverage(df: pd.DataFrame) -> pd.Series:
    exports = _norm(np.log1p(df["critical_exports_proxy"]))
    reserves = _norm(np.log1p(df["fx_reserves_usd"]))
    chain = _norm(df["supply_chain_centrality"])
    sanctions_pen = df["sanctions_score"] * 4
    return (0.40 * exports + 0.28 * reserves + 0.32 * chain - 0.10 * sanctions_pen).clip(0, 100)


def calc_resilience(df: pd.DataFrame) -> pd.Series:
    energy = _norm(-df["energy_import_pct"])
    food = _norm(df["food_self_sufficiency"])
    gdp = _norm(np.log1p(df["gdp_current_usd"]))
    strategic_import_pen = _norm(df["import_dependency_strategic"])
    return (0.34 * energy + 0.34 * food + 0.24 * gdp - 0.12 * strategic_import_pen).clip(0, 100)


def calc_autonomy(df: pd.DataFrame) -> pd.Series:
    us_dep = _norm(df["us_export_pct"])
    strategic_imports = _norm(df["import_dependency_strategic"])
    partner_conc = _norm(df["export_partner_concentration"])
    sanctions = _norm(df["sanctions_score"])
    raw = 100 - (0.35 * us_dep + 0.25 * strategic_imports + 0.20 * partner_conc + 0.20 * sanctions)
    return raw.clip(0, 100)


def calc_strategic_signal(df: pd.DataFrame) -> pd.Series:
    return (
        0.38 * df["institutional_signal_score"] +
        0.30 * df["think_tank_consensus_score"] +
        0.32 * df["multi_alignment_score"]
    ).clip(0, 100)


def calc_regulatory_friction(df: pd.DataFrame) -> pd.Series:
    return (
        0.34 * df["ntm_score"] +
        0.26 * df["sps_tbt_score"] +
        0.22 * df["export_control_score"] +
        0.18 * (df["sanctions_score"] * 10)
    ).clip(0, 100)


def calc_capital_confirmation(df: pd.DataFrame) -> pd.Series:
    return (0.48 * df["fund_flow_score"] + 0.52 * df["strategic_capex_score"]).clip(0, 100)


def calc_market_access_viability(df: pd.DataFrame) -> pd.Series:
    friction = calc_regulatory_friction(df)
    return (0.65 * df["market_access_score"] + 0.35 * (100 - friction)).clip(0, 100)


def compute_scores(
    df: pd.DataFrame,
    theme: str = "General",
    shock_tariff: float = 0,
    shock_export_controls: float = 0,
    shock_shipping: float = 0,
) -> pd.DataFrame:
    out = df.copy()

    out["leverage"] = calc_leverage(out)
    out["resilience"] = calc_resilience(out)
    out["autonomy"] = calc_autonomy(out)
    out["strategic_signal"] = calc_strategic_signal(out)
    out["regulatory_friction"] = calc_regulatory_friction(out)
    out["capital_confirmation"] = calc_capital_confirmation(out)
    out["market_access_viability"] = calc_market_access_viability(out)

    out["icg_base"] = np.cbrt(
        np.maximum(out["leverage"], 1) *
        np.maximum(out["resilience"], 1) *
        np.maximum(out["autonomy"], 1)
    ).clip(0, 100)

    weights = THEME_WEIGHTS[theme]
    theme_component = (
        weights.leverage * out["leverage"] +
        weights.resilience * out["resilience"] +
        weights.autonomy * out["autonomy"] +
        weights.strategic_signal * out["strategic_signal"] +
        weights.access_viability * out["market_access_viability"] +
        weights.capital_confirmation * out["capital_confirmation"]
    )

    tariff_penalty = (out["us_export_pct"] / 100.0) * shock_tariff * 0.22
    export_control_penalty = (out["export_control_score"] / 100.0) * shock_export_controls * 0.18
    shipping_penalty = (out["supply_chain_centrality"] / 100.0) * shock_shipping * 0.16
    news_penalty = out.get("news_shock", pd.Series(0.0, index=out.index)) * 1.8

    out["shock_penalty_raw"] = tariff_penalty + export_control_penalty + shipping_penalty + news_penalty
    out["theme_score_raw"] = theme_component - out["shock_penalty_raw"]

    raw_full = 0.56 * out["icg_base"] + 0.44 * out["theme_score_raw"]
    out["icg_full"] = _norm(raw_full)
    out["shock_penalty"] = _norm(out["shock_penalty_raw"])
    out["signal_gap"] = (out["strategic_signal"] - out["capital_confirmation"]).round(1)
    out["category"] = pd.cut(
        out["icg_full"],
        bins=[-1, 20, 40, 60, 80, 101],
        labels=["Crítico", "Frágil", "Intermedio", "Fuerte", "Dominante"],
    )

    return out.sort_values("icg_full", ascending=False).reset_index(drop=True)
