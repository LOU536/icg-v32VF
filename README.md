# ICG v3.2 — Real Data Hybrid

Dashboard en Streamlit para análisis geoeconómico multicapa.

## Qué hace

- Usa datos reales del Banco Mundial para:
  - PIB nominal (`NY.GDP.MKTP.CD`)
  - reservas internacionales (`FI.RES.TOTL.CD`)
  - importación neta de energía (`EG.IMP.CONS.ZS`)
- Combina esos datos con una capa curada de:
  - fricción regulatoria
  - SPS/TBT y NTM
  - export controls
  - capital confirmation
  - strategic signal
  - multi-alignment
- Añade simulación de shocks y overlay opcional de noticias con NewsAPI.

## Estructura

```text
icg_v32/
├── app.py
├── data_sources.py
├── scoring.py
├── visuals.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── secrets.toml.example
└── data/
    └── regulatory_signals.csv
```

## Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secrets opcionales

Crea `.streamlit/secrets.toml` a partir del ejemplo si quieres activar noticias.

## Nota metodológica

Esta versión es **híbrida** a propósito. No fuerza una falsa precisión para variables estratégicas donde no hay todavía una API oficial única, limpia y homogénea.
## Roadmap v3.3

- [ ] Añadir arquitectura hot / warm / cold
- [ ] Mostrar fecha/frescura de cada fuente
- [ ] Integrar NewsAPI real
- [ ] Añadir score de shocks recientes
- [ ] Preparar integración de comercio reciente
- [ ] Mejorar diseño visual
