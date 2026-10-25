# Instrumentos derivados financieros: Forward de divisas COP/USD

Desarrollo de la **Parte 1** del ejercicio semestral: financiar maquinaria amarilla por COP 400.000.000 con un crédito en dólares (Wells Fargo, Prime + 2,50 pp, 10 años, cuotas trimestrales por sistema francés), medir el riesgo cambiario y evaluar una cobertura con cuatro forwards de divisas (NDF) sobre el 75 % de la exposición de los años 7 a 10.

El entregable es un **informe web interactivo** (`docs/index.html`). Muestra solo resultados y análisis, con gráficos dinámicos en Plotly; no muestra código.

## Ver el informe

- **En GitHub Pages:** [abrir el informe](https://mateoloperaortiz.github.io/DerivadosFinancieros/). Se publica desde la rama `main`, carpeta `/docs`.
- **En local:** abra `docs/index.html` en el navegador, o sirva la carpeta con `python3 -m http.server -d docs 8000`.

## Contenido

| Sección | Qué responde |
| --- | --- |
| A.1 | Análisis fundamental de la TRM (tasas, inflación, petróleo, balanza de pagos, riesgo fiscal y político, proyecciones) y escenarios a 12 meses |
| A.2 | Crédito en USD: entidad, tasa verificable, forma de cotización y tabla de amortización |
| A.3 | Conversión de las cuotas a COP (spot constante, trayectorias y simulación) y descomposición intereses vs. tasa de cambio |
| B.1 | Cotización forward de mercado (> 6 meses), paridad cubierta y valoración de los cuatro forwards |
| B.2 | Protección, costo de oportunidad, pérdidas extremas y fracaso de la cobertura con innovaciones normales y t de Student |
| B.3 | Flujo consolidado, escenarios favorable, central y adverso, volatilidad, estabilidad presupuestal, riesgo residual, sensibilidad a tasas y conclusión |

## Reproducir los resultados

Requiere [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                   # instala dependencias
uv run python -m derivados.report.build   # regenera docs/index.html (~15 s)
uv run pytest                             # pruebas de los modelos
```

Los datos tienen corte al **15 de octubre de 2026**:

- `data/raw/`: TRM histórica (datos.gov.co) y series de FRED, descargadas y versionadas.
- `data/manual/market_inputs.yaml`: insumos curados a mano (puntos forward, tasas, proyecciones, fundamentales, escenarios), cada uno con su fuente y fecha.

`uv run python scripts/fetch_data.py` vuelve a descargar las series. Si lo hace, cambia la fecha de corte y debe revisar la narrativa.

## Personalizar

- **Integrantes:** edite `meta.integrantes` en `data/manual/market_inputs.yaml` y regenere el informe.
- **Supuestos** (tasa del crédito, escenarios, tasas de largo plazo de los forwards): están en el mismo YAML.
- **Textos del análisis:** en `src/derivados/report/templates/report.html.j2`. Las cifras se insertan automáticamente desde los cálculos.

## Estructura

```
data/raw/                 series descargadas (TRM, FRED)
data/manual/              insumos documentados (YAML)
src/derivados/
  credit.py               sistema francés
  fx_model.py             calibración y simulación de la TRM (normal / t de Student)
  forwards.py             paridad cubierta, conversiones de tasas y estrategias NDF
  cashflows.py            flujo consolidado, TIR y valor presente
  analysis.py             orquestación de las partes A y B
  report/                 gráficos Plotly, tablas, plantilla y generador del HTML
docs/index.html           informe publicado (GitHub Pages)
tests/                    pruebas unitarias
```
