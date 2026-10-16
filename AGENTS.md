# AGENTS.md

## Comandos

- Instalar: `uv sync`
- Generar el informe: `uv run python -m derivados.report.build` (escribe `docs/index.html` y `docs/.nojekyll`; tarda ~15 s)
- Pruebas: `uv run pytest -q`
- Lint: `uv run ruff check src tests scripts`
- Refrescar datos crudos: `uv run python scripts/fetch_data.py` (cambia la fecha de corte; revisar la narrativa después)

## Verificación visual

Chrome headless sirve para revisar el HTML renderizado:
`python3 -m http.server -d docs 8765` y luego
`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --window-size=1440,33000 --virtual-time-budget=25000 --screenshot=/tmp/full.png http://localhost:8765/index.html`.
No usar `Scattergl`: requiere WebGL y no se dibuja en todos los navegadores.

## Convenciones

- Informe en español, con formato numérico colombiano (miles con `.`, decimales con `,`, `%` separado por espacio duro). Los helpers están en `src/derivados/report/fmt.py`.
- Año comercial de 252 días: paso mensual de 21 días, trimestre de 63 días y forwards a 252 días.
- Los insumos manuales viven en `data/manual/market_inputs.yaml` con fuente y fecha. No escribir cifras de mercado en el código.
- Dentro de LaTeX (KaTeX) no insertar valores con `%` ni coma decimal sin proteger: usar el filtro `texnum` o dejar el número fuera de `\( \)`.
- En la narrativa, cuando el texto ya expresa la dirección ("cayó", "cuesta", "reduce"), usar las variantes `*_abs` de `key_numbers` para evitar dobles signos.
- Simulación reproducible: semilla fija (`SEED` en `analysis.py`) y 20.000 trayectorias por escenario y distribución.
