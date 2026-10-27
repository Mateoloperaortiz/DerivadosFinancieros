# Instrumentos derivados financieros: forwards COP/USD y futuros sobre el S&P 500

Desarrollo de la **Parte 1** del ejercicio semestral: financiar maquinaria amarilla por COP 400.000.000 con un crédito en dólares (Wells Fargo, Prime + 2,50 pp, 10 años, cuotas trimestrales por sistema francés), medir el riesgo cambiario y evaluar una cobertura con cuatro forwards de divisas (NDF) sobre el 75 % de la exposición de los años 7 a 10.

Incluye también la **Parte 2**: portafolio media-varianza con MSFT, WMT y XOM (USD 20 millones desde el 30-jul-2026), VaR mensual, beta CAPM y cobertura con futuros E-mini S&P 500 (número de contratos, cuenta de margen con liquidación mensual, roll-over trimestral durante 4 años y sensibilidad a la beta).

El entregable es un **informe web interactivo** en dos páginas: `docs/index.html` (Parte 1) y `docs/parte2.html` (Parte 2). Muestra solo resultados y análisis, con gráficos dinámicos en Plotly; no muestra código.

## Ver el informe

- **En GitHub Pages:** [Parte 1](https://mateoloperaortiz.github.io/DerivadosFinancieros/) · [Parte 2](https://mateoloperaortiz.github.io/DerivadosFinancieros/parte2.html). Se publica desde la rama `main`, carpeta `/docs`.
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
uv run python -m derivados.report.build   # regenera docs/index.html y docs/parte2.html (~30 s)
uv run pytest                             # pruebas de los modelos
```

Los datos tienen corte al **15 de octubre de 2026**:

- `data/raw/`: TRM histórica (datos.gov.co) y series de FRED, descargadas y versionadas.
- `data/raw/parte2/`: precios diarios de Yahoo Finance (MSFT, WMT, XOM, ^GSPC, ^SP500TR, ES=F, ESZ26, ESH27, ^IRX, ^FVX, ^TNX; consulta 27-oct-2026) y curva par del Tesoro de EE. UU. 2026.
- `data/manual/parte2_inputs.yaml`: parámetros, especificaciones y márgenes del E-mini S&P 500 (CME), supuestos y fuentes de la Parte 2.
- `data/manual/market_inputs.yaml`: insumos curados a mano (puntos forward, tasas, proyecciones, fundamentales, escenarios), cada uno con su fuente y fecha.

`uv run python scripts/fetch_data.py` vuelve a descargar las series. Si lo hace, cambia la fecha de corte y debe revisar la narrativa.

## Personalizar

- **Integrantes:** edite `meta.integrantes` en `data/manual/market_inputs.yaml` y regenere el informe.
- **Supuestos** (tasa del crédito, escenarios, tasas de largo plazo de los forwards): están en el mismo YAML.
- **Textos del análisis:** en `src/derivados/report/templates/report.html.j2`. Las cifras se insertan automáticamente desde los cálculos.
- **Diseño:** el CSS y el JavaScript compartidos están en `templates/_head.html.j2` y `templates/_scripts.html.j2`; la paleta de las gráficas (modo claro y oscuro, validada para daltonismo) y su plantilla Plotly, en `src/derivados/report/theme.py`. Las gráficas solo usan colores de esa paleta: `uv run pytest` lo verifica sobre el HTML publicado.

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
  report/                 gráficos Plotly, tablas, plantillas y generador del HTML
    theme.py              paleta validada (claro/oscuro), plantilla Plotly y paso de figuras a HTML
    typo.py               pulido tipográfico del HTML final (espacios duros, signo menos, comillas)
  parte2/                 Parte 2: datos, optimización, VaR, beta, simulación, margen y roll-over
docs/index.html           informe publicado, Parte 1 (GitHub Pages)
docs/parte2.html          informe publicado, Parte 2
tests/                    pruebas unitarias
```
