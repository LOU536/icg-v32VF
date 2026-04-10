from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

PLOT_LAYOUT = dict(
    paper_bgcolor="#08111f",
    plot_bgcolor="#0b1728",
    font=dict(color="#d6e2f0"),
    xaxis=dict(gridcolor="#18314d", zerolinecolor="#18314d"),
    yaxis=dict(gridcolor="#18314d", zerolinecolor="#18314d"),
    legend=dict(bgcolor="#0b1728", bordercolor="#18314d", borderwidth=1),
)


def choropleth(df: pd.DataFrame, metric: str, title: str) -> go.Figure:
    fig = px.choropleth(
        df,
        locations="iso3",
        color=metric,
        hover_name="country",
        hover_data={
            "icg_full": ":.1f",
            "icg_base": ":.1f",
            "strategic_signal": ":.1f",
            "regulatory_friction": ":.1f",
            "capital_confirmation": ":.1f",
            "iso3": False,
        },
        color_continuous_scale="Tealgrn",
        title=title,
    )
    fig.update_layout(
        **PLOT_LAYOUT,
        geo=dict(bgcolor="#08111f", showcountries=True, countrycolor="#17314e",
                 showocean=True, oceancolor="#07101a", showland=True, landcolor="#0b1728"),
        height=500,
        margin=dict(t=60, b=0, l=0, r=0),
    )
    return fig


def ranking_bar(df: pd.DataFrame, metric: str, title: str, n: int = 20) -> go.Figure:
    dd = df.sort_values(metric, ascending=True).tail(n)
    fig = px.bar(dd, x=metric, y="country", orientation="h", color=metric, color_continuous_scale="Tealgrn", title=title)
    fig.update_layout(**PLOT_LAYOUT, height=620, coloraxis_showscale=False)
    fig.update_traces(text=dd[metric].round(1), textposition="outside")
    return fig


def matrix_power_access(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df,
        x="icg_base",
        y="market_access_viability",
        size="gdp_current_usd",
        color="icg_full",
        hover_name="country",
        color_continuous_scale="Tealgrn",
        title="Poder estructural vs viabilidad de acceso al mercado",
    )
    fig.add_vline(x=50, line_dash="dash", line_color="#355d7d")
    fig.add_hline(y=50, line_dash="dash", line_color="#355d7d")
    fig.update_layout(**PLOT_LAYOUT, height=560)
    return fig


def signal_gap_chart(df: pd.DataFrame) -> go.Figure:
    dd = df[["country", "signal_gap"]].sort_values("signal_gap")
    colors = ["#ef4444" if x > 10 else "#f59e0b" if x > 0 else "#19c37d" for x in dd["signal_gap"]]
    fig = go.Figure(go.Bar(x=dd["signal_gap"], y=dd["country"], orientation="h", marker_color=colors))
    fig.update_layout(**PLOT_LAYOUT, height=600, title="Brecha entre señal estratégica y confirmación de capital")
    return fig


def radar_compare(df: pd.DataFrame, a: str, b: str) -> go.Figure:
    dims = ["leverage", "resilience", "autonomy", "strategic_signal", "capital_confirmation", "market_access_viability"]
    labels = ["Apalancamiento", "Resiliencia", "Autonomía", "Señal estratégica", "Capital", "Acceso mercado"]
    colors = ["#19c37d", "#f5b942"]

    def rgba(hex_color: str, alpha: float) -> str:
        h = hex_color.lstrip("#")
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b_ = int(h[4:6], 16)
        return f"rgba({r},{g},{b_},{alpha})"

    fig = go.Figure()
    for country, color in [(a, colors[0]), (b, colors[1])]:
        row = df[df["country"] == country].iloc[0]
        vals = [row[d] for d in dims]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=labels + [labels[0]],
            name=country, line=dict(color=color, width=2.5),
            fill="toself", fillcolor=rgba(color, 0.12)
        ))
    fig.update_layout(
        **PLOT_LAYOUT,
        polar=dict(
            bgcolor="#0b1728",
            radialaxis=dict(range=[0, 100], gridcolor="#18314d", linecolor="#18314d"),
            angularaxis=dict(gridcolor="#18314d", linecolor="#18314d"),
        ),
        height=500,
        title=f"Comparación multicapa: {a} vs {b}",
    )
    return fig
