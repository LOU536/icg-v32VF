from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from data_sources import (
    compute_news_shock,
    enrich_with_world_bank,
    fetch_newsapi_articles,
    load_regulatory_signals,
)
from scoring import THEME_WEIGHTS, compute_scores
from visuals import choropleth, matrix_power_access, radar_compare, ranking_bar, signal_gap_chart

st.set_page_config(
    page_title="ICG v3.2 · Real Data Hybrid",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.1rem; padding-bottom: 1.1rem;}
    html, body, [class*="css"] {background-color:#08111f; color:#d6e2f0;}
    [data-testid="stSidebar"] {background-color:#06101c; border-right:1px solid #16314d;}
    .hero {background: linear-gradient(135deg,#0b1a2d 0%,#0c2138 55%,#091423 100%); border:1px solid #1d3e62; border-radius:18px; padding:22px 26px; margin-bottom:18px;}
    .hero h1 {margin:0; font-size:2rem; color:#eef6ff;}
    .hero p {color:#8da8c4; margin:8px 0 0 0;}
    .tag {display:inline-block; padding:4px 8px; border-radius:999px; border:1px solid #2c567f; color:#6ec1ff; font-size:.75rem; margin-bottom:10px;}
    </style>
    """,
    unsafe_allow_html=True,
)

THEMES = list(THEME_WEIGHTS.keys())


@st.cache_data(ttl=60 * 60, show_spinner=False)
def load_base(year: int) -> pd.DataFrame:
    base = load_regulatory_signals("data/regulatory_signals.csv")
    return enrich_with_world_bank(base, wb_year=year)


def main() -> None:
    with st.sidebar:
        st.title("ICG v3.2")
        st.caption("Hybrid: real World Bank data + curated strategic/regulatory layer")
        wb_year = st.selectbox("World Bank year", [2023, 2022, 2021], index=0)
        theme = st.selectbox("Motor temático", THEMES)

        st.markdown("### Shocks")
        shock_tariff = st.slider("Arancel EE.UU. (%)", 0, 100, 10, 5)
        shock_export_controls = st.slider("Escalada export controls", 0, 100, 20, 5)
        shock_shipping = st.slider("Disrupción shipping/logística", 0, 100, 15, 5)

        st.markdown("### News overlay")
        default_key = st.secrets.get("NEWS_API_KEY", "") if hasattr(st, "secrets") else ""
        news_api_key = st.text_input("NewsAPI key", type="password", value=default_key)
        news_query = st.text_input("Query", value="sanctions OR \"export controls\" OR tariff OR shipping")
        use_news = st.checkbox("Activar overlay de noticias", value=False)

    base_df = load_base(wb_year)

    if use_news and news_api_key:
        with st.spinner("Leyendo noticias..."):
            articles = fetch_newsapi_articles(news_query, news_api_key, page_size=20)
            news_df = compute_news_shock(articles, base_df["country"].tolist())
            model_df = base_df.merge(news_df, on="country", how="left")
            model_df["news_shock"] = model_df["news_shock"].fillna(0)
    else:
        model_df = base_df.copy()
        model_df["news_shock"] = 0.0
        articles = []

    df = compute_scores(
        model_df,
        theme=theme,
        shock_tariff=shock_tariff,
        shock_export_controls=shock_export_controls,
        shock_shipping=shock_shipping,
    )

    top = df.iloc[0]
    avg = df["icg_full"].mean()
    fragile = int((df["icg_full"] < 40).sum())

    st.markdown(
        f"""
        <div class="hero">
            <div class="tag">REAL DATA HYBRID · WORLD BANK + CURATED STRATEGIC LAYER</div>
            <h1>ICG v3.2 — Geoeconomic Power, Friction & Signal Engine</h1>
            <p>
                Combina datos reales del Banco Mundial para PIB, reservas y dependencia energética con una capa curada
                de fricción regulatoria, señal estratégica, capital y alineamiento geopolítico. Tema activo: <b>{theme}</b>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Líder global", top["country"], f"ICG Full {top['icg_full']:.1f}")
    c2.metric("Promedio", f"{avg:.1f}", f"{len(df)} países")
    c3.metric("Estados frágiles", fragile, "ICG < 40")
    c4.metric("Año WB", str(wb_year), "Datos macro reales")

    tabs = st.tabs([
        "🌍 Mapa & ranking",
        "🧠 Señal estratégica",
        "🚧 Fricción & acceso",
        "🎯 Comparación",
        "📰 News overlay",
        "📋 Datos",
    ])

    with tabs[0]:
        left, right = st.columns([1.7, 1.3])
        with left:
            metric = st.selectbox(
                "Métrica del mapa",
                ["icg_full", "icg_base", "strategic_signal", "regulatory_friction", "capital_confirmation", "market_access_viability"],
                index=0,
            )
            st.plotly_chart(choropleth(df, metric, f"Mapa global — {metric}"), use_container_width=True)
        with right:
            st.plotly_chart(ranking_bar(df, "icg_full", "Ranking ICG Full"), use_container_width=True)

    with tabs[1]:
        left, right = st.columns([1.2, 1.8])
        with left:
            st.plotly_chart(ranking_bar(df, "strategic_signal", "Señal estratégica"), use_container_width=True)
        with right:
            st.plotly_chart(signal_gap_chart(df), use_container_width=True)
        st.info("La señal estratégica mezcla narrativa institucional, consenso de think tanks y capacidad de multi-alignment.")

    with tabs[2]:
        left, right = st.columns([1.2, 1.8])
        with left:
            st.plotly_chart(ranking_bar(df, "regulatory_friction", "Fricción regulatoria"), use_container_width=True)
        with right:
            st.plotly_chart(matrix_power_access(df), use_container_width=True)
        st.warning("Esta capa intenta capturar tu punto clave: el acceso real al mercado depende más de fricciones regulatorias que del arancel nominal por sí solo.")

    with tabs[3]:
        countries = df["country"].tolist()
        a, b = st.columns(2)
        country_a = a.selectbox("País A", countries, index=0)
        country_b = b.selectbox("País B", countries, index=1)
        st.plotly_chart(radar_compare(df, country_a, country_b), use_container_width=True)
        st.dataframe(
            df[df["country"].isin([country_a, country_b])][[
                "country", "icg_full", "icg_base", "leverage", "resilience", "autonomy",
                "strategic_signal", "regulatory_friction", "capital_confirmation", "market_access_viability", "shock_penalty"
            ]],
            use_container_width=True,
            hide_index=True,
        )

    with tabs[4]:
        if not articles:
            st.info("Activa el overlay de noticias y añade tu NewsAPI key para sumar un shock narrativo/event-driven.")
        else:
            st.success(f"{len(articles)} artículos procesados.")
            show = pd.DataFrame([
                {
                    "title": a.get("title"),
                    "source": a.get("source", {}).get("name"),
                    "publishedAt": a.get("publishedAt"),
                    "url": a.get("url"),
                }
                for a in articles
            ])
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.dataframe(df[["country", "news_shock", "shock_penalty"]].sort_values("news_shock", ascending=False), use_container_width=True, hide_index=True)

    with tabs[5]:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown(
            """
            ### Cómo leer esta v3.2
            - **Real data**: PIB, reservas y energía vienen del API v2 del Banco Mundial.
            - **Curated layer**: NTM, SPS/TBT, export controls, industrial policy, señal institucional y capital siguen en CSV curado.
            - **Por qué híbrido**: hoy no todas estas variables tienen una API oficial limpia, homogénea y abierta con la misma cobertura para un dashboard estable.
            - **Siguiente salto**: reemplazar partes del CSV con pipelines por fuente: WTO/ePing, OECD docs, G20 communiqués, think tanks y flujos temáticos.
            """
        )


if __name__ == "__main__":
    main()
