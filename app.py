import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_sources import load_base

st.set_page_config(
    page_title="ICG v3.2",
    st.info(
    "Fuentes activas: Banco Mundial + fallback local + señales regulatorias. "
    "Los datos estructurales usan el último dato disponible; los shocks pueden actualizarse en tiempo real."
)
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def minmax(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.isna().all():
        return pd.Series([50.0] * len(series), index=series.index)
    mn = s.min()
    mx = s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series([50.0] * len(series), index=series.index)
    return ((s - mn) / (mx - mn) * 100).clip(0, 100)


def build_scores(df: pd.DataFrame, tariff: float, export_controls_shock: float, logistics_shock: float, theme: str) -> pd.DataFrame:
    out = df.copy()

    # Base hard variables
    out["gdp_score"] = minmax(out["gdp_usd"])
    out["reserves_score"] = minmax(out["reserves_usd"])
    out["energy_resilience_score"] = minmax(-pd.to_numeric(out["energy_import_pct"], errors="coerce"))

    # Structural base
    out["icg_base"] = (
        out["gdp_score"] * 0.45 +
        out["reserves_score"] * 0.30 +
        out["energy_resilience_score"] * 0.25
    ).round(2)

    # Regulatory friction
    out["friction_score"] = (
        out["ntm"] * 0.35 +
        out["regulation"] * 0.25 +
        out["export_controls"] * 0.25 +
        out["industrial_policy"] * 0.15
    ).round(2)

    # Strategic signal
    out["signal_score"] = (
        out["strategic_signal"] * 0.50 +
        out["think_tank"] * 0.25 +
        out["capital_confirmation"] * 0.25
    ).round(2)

    # Theme adjustment
    theme_boost = pd.Series([1.0] * len(out), index=out.index)

    if theme == "Energy":
        theme_boost = 1 + (100 - out["energy_resilience_score"]) / 250
    elif theme == "Regulatory":
        theme_boost = 1 + out["friction_score"] / 400
    elif theme == "Capital":
        theme_boost = 1 + out["capital_confirmation"] / 350
    elif theme == "Strategy":
        theme_boost = 1 + out["signal_score"] / 350

    # Shock penalty
    # Ojo: aquí el shock se trata como penalidad simple y transparente
    shock_penalty = (
        tariff * 0.18 +
        export_controls_shock * 0.22 +
        logistics_shock * 0.15
    )

    out["icg_full_raw"] = (
        out["icg_base"] * 0.55 +
        out["signal_score"] * 0.30 -
        out["friction_score"] * 0.15 -
        shock_penalty
    ) * theme_boost

    out["icg_full"] = minmax(out["icg_full_raw"]).round(2)

    out["category"] = pd.cut(
        out["icg_full"],
        bins=[-1, 20, 40, 60, 80, 101],
        labels=["Crítico", "Vulnerable", "Intermedio", "Fuerte", "Dominante"]
    )

    out = out.sort_values("icg_full", ascending=False).reset_index(drop=True)
    return out


def plot_map(df: pd.DataFrame) -> go.Figure:
    fig = px.choropleth(
        df,
        locations="iso3",
        color="icg_full",
        hover_name="country",
        hover_data={
            "icg_full": True,
            "icg_base": True,
            "signal_score": True,
            "friction_score": True,
            "iso3": False,
        },
        color_continuous_scale="RdYlGn",
        title="ICG v3.2 — Global Map",
    )
    fig.update_layout(margin=dict(t=60, l=0, r=0, b=0), height=520)
    return fig


def plot_ranking(df: pd.DataFrame) -> go.Figure:
    dd = df.head(15).sort_values("icg_full", ascending=True)
    fig = px.bar(
        dd,
        x="icg_full",
        y="country",
        orientation="h",
        color="icg_full",
        color_continuous_scale="RdYlGn",
        title="Top 15 Ranking",
    )
    fig.update_layout(height=560, coloraxis_showscale=False)
    return fig


def plot_radar(df: pd.DataFrame, country_a: str, country_b: str) -> go.Figure:
    dims = ["icg_base", "signal_score", "friction_score", "capital_confirmation"]
    labels = ["Base", "Signal", "Friction", "Capital"]

    da = df[df["country"] == country_a].iloc[0]
    db = df[df["country"] == country_b].iloc[0]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[da[d] for d in dims] + [da[dims[0]]],
        theta=labels + [labels[0]],
        fill="toself",
        name=country_a
    ))
    fig.add_trace(go.Scatterpolar(
        r=[db[d] for d in dims] + [db[dims[0]]],
        theta=labels + [labels[0]],
        fill="toself",
        name=country_b
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=500,
        title=f"Comparación: {country_a} vs {country_b}",
    )
    return fig


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    st.title("🌍 ICG v3.2")
    st.caption("Hybrid model with World Bank live data + local fallback + regulatory signals")

    # Sidebar
    st.sidebar.header("Configuración")

    wb_year = st.sidebar.selectbox(
        "World Bank year",
        options=[2023, 2022, 2021, 2020],
        index=0,
    )

    theme = st.sidebar.selectbox(
        "Motor temático",
        options=["General", "Energy", "Regulatory", "Capital", "Strategy"],
        index=0,
    )

    st.sidebar.markdown("### Shocks")
    tariff = st.sidebar.slider("Arancel EE.UU. (%)", 0, 100, 10)
    export_controls_shock = st.sidebar.slider("Escalada export controls", 0, 100, 20)
    logistics_shock = st.sidebar.slider("Disrupción shipping/logística", 0, 100, 15)

    st.sidebar.markdown("### News overlay")
    st.sidebar.text_input("NewsAPI key", type="password", disabled=True)
    st.sidebar.text_input("Query", value='sanctions OR "export controls"', disabled=True)
    st.sidebar.checkbox("Activar overlay de noticias", value=False, disabled=True)

    # Data load with graceful fallback
    with st.spinner("Cargando datos base..."):
        try:
            base_df = load_base(wb_year)
            st.sidebar.success("Datos cargados")
        except Exception as e:
            st.error(f"No se pudieron cargar los datos base: {e}")
            st.stop()

    df = build_scores(
        base_df,
        tariff=tariff,
        export_controls_shock=export_controls_shock,
        logistics_shock=logistics_shock,
        theme=theme,
    )

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Líder", df.iloc[0]["country"])
    c2.metric("ICG medio", f"{df['icg_full'].mean():.1f}")
    c3.metric("Estados vulnerables", int((df["icg_full"] < 40).sum()))
    c4.metric("Tema activo", theme)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🌍 Mapa", "📊 Ranking", "🎯 Comparación", "📋 Tabla"])

    with tab1:
        st.plotly_chart(plot_map(df), use_container_width=True)

    with tab2:
        st.plotly_chart(plot_ranking(df), use_container_width=True)

    with tab3:
        countries = df["country"].tolist()
        col_a, col_b = st.columns(2)
        with col_a:
            country_a = st.selectbox("País A", countries, index=0)
        with col_b:
            country_b = st.selectbox("País B", countries, index=1 if len(countries) > 1 else 0)

        if country_a == country_b:
            st.warning("Selecciona dos países distintos.")
        else:
            st.plotly_chart(plot_radar(df, country_a, country_b), use_container_width=True)

            compare_cols = [
                "country", "icg_full", "icg_base", "signal_score",
                "friction_score", "capital_confirmation", "category"
            ]
            st.dataframe(
                df[df["country"].isin([country_a, country_b])][compare_cols],
                use_container_width=True,
                hide_index=True,
            )

    with tab4:
        show_cols = [
            "country", "iso3", "gdp_usd", "reserves_usd", "energy_import_pct",
            "ntm", "regulation", "export_controls", "industrial_policy",
            "strategic_signal", "think_tank", "capital_confirmation",
            "icg_base", "signal_score", "friction_score", "icg_full", "category"
        ]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("Si el Banco Mundial falla por timeout, la app usa world_bank_fallback.csv para no romperse.")


if __name__ == "__main__":
    main()
