"""Gráficos de la Parte 2 (cobertura de un portafolio de acciones con futuros del S&P 500)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ..parte2.data import yahoo
from .fmt import MESES, fecha, num
from .theme import DIV, HEDGE, SEQ, STRAT_P2, TICKER, C, _layout, _menu, _visible, rgba, to_div

LOG_TICKS = [50, 100, 200, 500, 1000]
DIVERSIFICATION_YEARS = (2020, 2022)  # los años que cita el pie del gráfico 2.3
DAY_MS = 24 * 3600 * 1000
# Leyenda apenas a la izquierda del lienzo: así plotly.js le deja usar también el margen izquierdo antes de partirla en
# varias filas (el margen derecho que piden los rótulos finales la partía en la columna de 476 px de la .grid2).
WIDE_LEGEND = dict(x=-0.002)


def _day_month(ts) -> str:
    """'1-ago' a partir de una fecha (fecha() sin el año)."""
    return fecha(ts).rsplit("-", 1)[0]


def _weekly(s: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Último dato real de cada semana, con su fecha verdadera (nunca un viernes posterior al corte), más el primer
    dato, que es la base de la serie."""
    w = s.groupby(pd.Grouper(freq="W-FRI")).tail(1)
    out = pd.concat([s.iloc[:1], w])
    return out[~out.index.duplicated()]


def _seq_from(i: int) -> list:
    """Escala secuencial sin sus pasos más claros, para que los puntos de valor bajo no se pierdan en la superficie."""
    cols = [c for _, c in SEQ[i:]]
    return [[k / (len(cols) - 1), c] for k, c in enumerate(cols)]


def _wide_layout(fig: go.Figure, height: int, **kw) -> go.Figure:
    """``_layout`` con la leyenda ancha."""
    kw["legend"] = WIDE_LEGEND | kw.get("legend", {})
    return _layout(fig, height, **kw)


def _time_axis(fig: go.Figure) -> None:
    """Cruz de lectura en x con la fecha del tooltip como en el texto (29-jul-2026)."""
    fig.update_xaxes(showspikes=True, hoverformat="%-d-%b-%Y")


def _ref_line(fig: go.Figure, xs: list, y: float, color: str = C.muted, dash: str = "dot") -> None:
    """Línea horizontal de referencia como traza: queda sobre la rejilla y debajo de las series."""
    fig.add_trace(go.Scatter(x=xs, y=[y, y], mode="lines", line=dict(color=color, width=1, dash=dash), showlegend=False,
                             hoverinfo="skip"))


def _legend_dot(fig: go.Figure, name: str, group: str, color: str, **kw) -> None:
    """Muestra de leyenda para una nube de puntos: la de la traza hereda su punto pequeño y translúcido, que casi no se
    ve (menos en modo oscuro). La nube va con ``showlegend=False`` en el mismo grupo, así el clic las prende juntas."""
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=name, legendgroup=group, hoverinfo="skip",
                             marker=dict(size=9, color=color, line=dict(width=0)), **kw))


def _end_labels(fig: go.Figure, x, ys: list[float], texts: list[str], colors: list[str]) -> None:
    """Punto y valor al final de cada serie (texto neutro; la identidad la dan el color del punto y la leyenda). Solo el
    valor: con el nombre, el margen derecho dejaba el área de trazado en la mitad del ancho en el celular."""
    fig.add_trace(go.Scatter(x=[x] * len(ys), y=ys, mode="markers+text", text=texts, textposition="middle right",
                             marker=dict(size=8, color=colors), textfont=dict(color=C.ink2, size=12),
                             cliponaxis=False, showlegend=False, hoverinfo="skip"))


# ----------------------------------------------------------------------------- 1.1
def price_12m(R: dict) -> go.Figure:
    cut, t0 = R["cut"], R["t0"]
    start = cut - pd.DateOffset(years=1)
    last = R["expost"]["fecha"]
    series = {t: (t, f"{t} (con dividendos)", yahoo(t)["adjclose"]) for t in R["cfg"]["portafolio"]["tickers"]}
    series["S&P 500"] = ("S&P 500 (precio)", "S&P 500 (solo precio)", yahoo("^GSPC")["close"])
    fig = go.Figure()
    # Velo tenue (el mismo de 2.3): más denso, en modo oscuro la línea gris del S&P 500 se pierde dentro de él.
    fig.add_vrect(x0=t0, x1=last, fillcolor=rgba(C.gray, 0.1), line_width=0, layer="below")
    _ref_line(fig, [start, last], 100, C.axis, "solid")
    fig.add_vline(x=cut, line=dict(color=C.muted, width=1, dash="dot"), layer="below")
    fig.add_annotation(x=t0, y=1, xref="x", yref="paper", text="Ex post", showarrow=False, xanchor="left",
                       yanchor="top", xshift=6, yshift=-2, font=dict(color=C.muted, size=11.5))
    for rank, (key, (legend, name, s)) in enumerate(reversed(series.items())):
        s = s.loc[start:last]
        s = 100 * s / s.iloc[0]
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=legend, line=dict(color=TICKER[key], width=2),
                                 legendrank=10 - rank, hovertemplate=f"<b>%{{y:,.1f}}</b>  {name}<extra></extra>"))
    _time_axis(fig)
    # Formato según el paso entre marcas: horas o días al hacer zoom, meses en la vista completa.
    fig.update_xaxes(tickformatstops=[dict(dtickrange=[None, DAY_MS / 2], value="%H:%M<br>%-d %b %Y"),
                                      dict(dtickrange=[DAY_MS, 14 * DAY_MS], value="%-d %b %Y"),
                                      dict(dtickrange=["M1", "M2"], value="%b %Y"),
                                      dict(dtickrange=["M3", None], value="%b<br>%Y")])
    fig.update_yaxes(title_text=f"índice ({fecha(start)} = 100)")
    return _wide_layout(fig, 430, hovermode="x unified")


# ----------------------------------------------------------------------------- 2.1
def growth(R: dict) -> go.Figure:
    px = R["rb"]["prices"]
    g = _weekly(100 * px / px.iloc[0])
    spx = yahoo("^SP500TR")["close"].reindex(px.index).ffill()
    spx = _weekly(100 * spx / spx.iloc[0])
    lines = {"S&P 500": ("S&P 500 (con dividendos)", spx)} | {t: (t, g[t]) for t in g.columns}
    fig = go.Figure()
    for rank, (key, (name, s)) in enumerate(lines.items()):
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=key, line=dict(color=TICKER[key], width=2),
                                 legendrank=rank or len(lines),
                                 hovertemplate=f"<b>USD %{{y:,.0f}}</b>  {name}<extra></extra>"))
    _end_labels(fig, px.index[-1], [s.iloc[-1] for _, s in lines.values()],
                [num(s.iloc[-1]) for _, s in lines.values()], [TICKER[k] for k in lines])
    log = {"yaxis.type": "log", "yaxis.tickmode": "array", "yaxis.tickvals": LOG_TICKS,
           "yaxis.ticktext": [num(v) for v in LOG_TICKS], "yaxis.autorange": True}
    lin = {"yaxis.type": "linear", "yaxis.tickmode": "auto", "yaxis.autorange": True}
    fig.update_layout(updatemenus=_menu([dict(label="Escala logarítmica", method="relayout", args=[log]),
                                         dict(label="Escala lineal", method="relayout", args=[lin])]))
    _time_axis(fig)
    fig.update_xaxes(range=[px.index[0], px.index[-1]])
    fig.update_yaxes(title_text="valor de USD 100 invertidos", type="log", tickmode="array", tickvals=LOG_TICKS,
                     ticktext=[num(v) for v in LOG_TICKS], tickformat=",d")
    return _wide_layout(fig, 400, hovermode="x unified", margin=dict(l=8, r=44, t=16, b=8))


# ----------------------------------------------------------------------------- 2.3
def by_year(R: dict) -> go.Figure:
    by = 100 * R["rb"]["by_year"]
    px = R["rb"]["prices"]
    years = [int(y) for y in by.index]
    first, last = years[0], years[-1]
    since, until = _day_month(px.index[0]), _day_month(px.index[-1])
    hover = {y: str(y) for y in years} | {first: f"{first} (desde el {since})", last: f"{last} (hasta el {until})"}
    tick = [f"’{y % 100:02d}{'*' if y in (first, last) else ''}" for y in years]
    lo, hi = by.stack().idxmin(), by.stack().idxmax()
    fig = go.Figure()
    for y in DIVERSIFICATION_YEARS:
        fig.add_vrect(x0=y - 0.5, x1=y + 0.5, fillcolor=rgba(C.gray, 0.1), line_width=0, layer="below")
    for t in by.columns:
        text = [f"{'+' if v > 0 else ''}{num(v, 0)} %" if (y, t) in (lo, hi) else "" for y, v in by[t].items()]
        fig.add_trace(go.Bar(x=years, y=by[t], name=t, marker_color=TICKER[t], text=text, textposition="outside",
                             constraintext="none", textfont=dict(size=11.5, color=C.ink2), cliponaxis=False,
                             customdata=[[f"{num(v, 1)} %", hover[y]] for y, v in by[t].items()],
                             hovertemplate=f"<b>%{{customdata[0]}}</b><br>{t} en %{{customdata[1]}}<extra></extra>"))
    fig.update_xaxes(tickmode="array", tickvals=years, ticktext=tick, showline=False, ticks="",
                     tickfont=dict(size=11.5), title_text=f"año (* {first} desde el {since}; {last} hasta el {until})")
    fig.update_yaxes(title_text="retorno total del año", ticksuffix=" %", zeroline=True, zerolinecolor=C.axis,
                     zerolinewidth=1)
    return _wide_layout(fig, 400, barmode="group", bargap=0.3, bargroupgap=0.12)


# ----------------------------------------------------------------------------- 2.2
def correlation(R: dict) -> go.Figure:
    c = R["rb"]["corr"]
    names = list(c.columns)
    z = c.values.astype(float).copy()
    np.fill_diagonal(z, np.nan)
    diag = np.where(np.eye(len(names), dtype=bool), 1.0, np.nan)
    fig = go.Figure()
    fig.add_trace(go.Heatmap(z=diag, x=names, y=names, colorscale=[[0, rgba(C.gray, 0.14)], [1, rgba(C.gray, 0.14)]],
                             showscale=False, xgap=3, ygap=3, hoverinfo="skip"))
    # hoverongaps=False: la diagonal (NaN aquí, pintada por la traza de arriba) no muestra un tooltip «NaN».
    fig.add_trace(go.Heatmap(z=z, x=names, y=names, zmin=-1, zmax=1, colorscale=DIV, xgap=3, ygap=3, hoverongaps=False,
                             colorbar=dict(tickvals=[-1, -0.5, 0, 0.5, 1], ticktext=["−1", "−0,5", "0", "0,5", "1"],
                                           len=0.86, title=dict(text="ρ", side="top")),
                             hovertemplate="<b>%{z:.2f}</b><br>%{y} con %{x}<extra></extra>"))
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            v = c.values[i, j]
            fig.add_annotation(x=b, y=a, text="1" if i == j else f"<b>{num(v, 2)}</b>", showarrow=False,
                               font=dict(size=15, color=C.muted if i == j else C.ink))
    fig.update_xaxes(showline=False, ticks="", side="bottom", tickfont=dict(size=12.5, color=C.ink2))
    fig.update_yaxes(autorange="reversed", showgrid=False, ticks="", tickfont=dict(size=12.5, color=C.ink2))
    # 2.1 va a su lado con una fila de botones encima (44 px): con esta altura y el mismo margen inferior, los dos ejes x
    # quedan a la misma altura en la .grid2.
    return _wide_layout(fig, 444, margin=dict(l=8, r=16, t=16, b=30))


# ----------------------------------------------------------------------------- 3.1
def frontier(R: dict) -> go.Figure:
    o, rf = R["opt"], R["rf_s"]
    cl, st = o["cloud"], R["rb"]["stats"]
    tk = list(st.index)
    idx = np.random.default_rng(1).choice(len(cl["ret"]), 4000, replace=False)
    mix = " · ".join(f"{t} %{{customdata[{i}]:.0f}} %" for i, t in enumerate(tk))
    point = "<b>%{y:.1f} %</b> retorno esperado<br>%{x:.1f} % volatilidad"
    fig = go.Figure()
    f4 = np.float32  # precisión de sobra para dibujar y aligera la página
    fig.add_trace(go.Scatter(
        x=(100 * cl["vol"][idx]).astype(f4), y=(100 * cl["ret"][idx]).astype(f4), mode="markers",
        name="Combinaciones factibles", legendgroup="nube", showlegend=False,
        marker=dict(size=5, color=cl["sharpe"][idx].astype(f4), colorscale=_seq_from(2), opacity=0.5, line=dict(width=0),
                    colorbar=dict(orientation="h", x=1, xanchor="right", y=0.06, yanchor="bottom", lenmode="pixels", len=140,
                                  thickness=8, outlinewidth=0, tickvals=[0.4, 0.6, 0.8], tickformat=".1f",
                                  tickfont=dict(size=11, color=C.muted),
                                  title=dict(text="Sharpe", side="top", font=dict(size=12, color=C.ink2)))),
        customdata=np.rint(100 * np.asarray(cl["w"])[idx]).astype(np.uint8),
        hovertemplate=point + "<br>" + mix + "<br>Sharpe %{marker.color:.2f}<extra></extra>"))
    _legend_dot(fig, "Combinaciones factibles", "nube", SEQ[4][1])
    fr = o["frontier"]
    fig.add_trace(go.Scatter(x=100 * fr[:, 0], y=100 * fr[:, 1], mode="lines", line=dict(color=C.surface, width=6),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=100 * fr[:, 0], y=100 * fr[:, 1], mode="lines", name="Frontera eficiente",
                             line=dict(color=C.ink, width=2.5),
                             hovertemplate=point + "<br>frontera eficiente<extra></extra>"))
    xs = np.array([0, 100 * o["vol"] * 1.4])
    fig.add_trace(go.Scatter(x=xs, y=100 * rf + xs * o["sharpe"], mode="lines", name="Línea del mercado de capitales",
                             line=dict(color=C.muted, width=1.5, dash="dash"), hoverinfo="skip"))
    pts = (("Máximo Sharpe", o["vol"], o["ret"], o["w"], o["sharpe"], "star", 24, C.green),
           ("Mínima varianza", o["vol_mv"], o["ret_mv"], o["w_mv"], o["sharpe_mv"], "diamond", 14, C.ink2))
    for name, vol, ret, w, sh, sym, size, color in pts:
        tag = f"<br>{mix}<br>Sharpe {num(sh, 2)}<br>portafolio de {name[0].lower()}{name[1:]}<extra></extra>"
        # Halo del color de la tarjeta: separa la marca de la nube verde sin dibujarle un borde.
        fig.add_trace(go.Scatter(x=[100 * vol], y=[100 * ret], mode="markers", showlegend=False, hoverinfo="skip",
                                 marker=dict(size=size + 8, symbol=sym, color=C.surface, line=dict(width=0))))
        fig.add_trace(go.Scatter(x=[100 * vol], y=[100 * ret], mode="markers", name=name, customdata=[100 * np.asarray(w)],
                                 showlegend=False, marker=dict(size=size, symbol=sym, color=color, line=dict(width=0)),
                                 hovertemplate=point + tag))
    fig.add_trace(go.Scatter(x=100 * st["vol"], y=100 * st["ret_arit"], mode="markers", showlegend=False,
                             marker=dict(size=10, color=[TICKER[t] for t in tk]), customdata=tk,
                             hovertemplate=point + "<br>%{customdata}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[0], y=[100 * rf], mode="markers", showlegend=False, cliponaxis=False,
                             marker=dict(size=8, color=C.ink2),
                             hovertemplate=f"<b>{num(100 * rf, 2)} %</b><br>Treasury a 3 meses<extra></extra>"))
    label = dict(showarrow=True, arrowcolor=C.muted, arrowwidth=1, standoff=12, font=dict(size=12, color=C.ink),
                 bgcolor=C.surface)
    # Rótulos encima de la estrella y debajo del rombo: esas dos zonas quedan vacías en las dos vistas y, centrados, no
    # se salen del lienzo por la izquierda en el celular. En el celular la línea del mercado pasa por detrás: el fondo
    # opaco la corta limpio. El de mínima varianza baja hasta la franja del 14-15 %, donde la rama inferior de la nube
    # ya se fue a la derecha: más arriba su fondo le mordía el borde a la nube en el celular.
    fig.add_annotation(x=100 * o["vol"], y=100 * o["ret"], text="Máximo Sharpe", ax=0, ay=-40, yanchor="bottom", **label)
    fig.add_annotation(x=100 * o["vol_mv"], y=100 * o["ret_mv"], text="Mínima varianza", ax=0, ay=75, yanchor="top",
                       **label)
    place = {"MSFT": dict(yshift=15), "WMT": dict(xanchor="left", xshift=8), "XOM": dict(yshift=-16)}
    for t in tk:
        fig.add_annotation(x=100 * st.loc[t, "vol"], y=100 * st.loc[t, "ret_arit"], text=t, showarrow=False,
                           font=dict(size=12, color=C.ink2), bgcolor=rgba(C.surface, 0.85), **place.get(t, {}))
    fig.add_annotation(x=0, y=100 * rf, text=f"r<sub>f</sub> = {num(100 * rf, 2)} %", showarrow=False, xanchor="left",
                       yanchor="top", xshift=6, yshift=-4, font=dict(size=11.5, color=C.ink2))
    # Dos vistas. De cerca, la nube, la frontera y los portafolios llenan el lienzo; abajo queda una franja libre para la
    # escala de color. La completa arranca en el origen para mostrar la tasa libre, donde nace la línea del mercado de
    # capitales (r_f y su rótulo quedan fuera de la vista de cerca y plotly.js los esconde).
    vx = 100 * np.r_[cl["vol"][idx], st["vol"]]
    vy = 100 * np.r_[cl["ret"][idx], st["ret_arit"]]
    near = {"xaxis.range": [float(np.floor(vx.min()) - 3), float(np.ceil(vx.max()) + 1.5)],
            "yaxis.range": [float(np.floor(vy.min()) - 5), float(np.ceil(vy.max()) + 1.5)]}
    full = {"xaxis.range": [0, 32], "yaxis.range": [0, 27]}
    fig.update_layout(updatemenus=_menu([dict(label="Zoom a la frontera", method="relayout", args=[near]),
                                         dict(label="Desde la tasa libre", method="relayout", args=[full])]))
    fig.update_xaxes(title_text="volatilidad anual", ticksuffix=" %", range=near["xaxis.range"], showgrid=True)
    fig.update_yaxes(title_text="retorno esperado anual (histórico)", ticksuffix=" %", range=near["yaxis.range"])
    return _wide_layout(fig, 500)


# ----------------------------------------------------------------------------- 4.1
def var_hist(R: dict) -> go.Figure:
    v = R["var"]
    r = 100 * v["roll21"]
    step = 0.5
    edges = np.arange(np.floor(r.min() / step) * step, np.ceil(r.max() / step) * step + step / 2, step)
    cnt, _ = np.histogram(r, bins=edges)
    top = 1.04 * float(cnt.max())
    fig = go.Figure()
    fig.add_trace(go.Bar(x=(edges[:-1] + edges[1:]) / 2, y=cnt, width=0.86 * step,
                         name=f"Retornos de 21 días ({num(len(r))} ventanas)", legendgroup="dist",
                         legendrank=1, marker=dict(color=rgba(C.green, 0.42), cornerradius=2),
                         customdata=[[f"{c} ventana{'' if c == 1 else 's'}", f"{num(a, 1)} % y {num(b, 1)} %"]
                                     for c, a, b in zip(cnt, edges[:-1], edges[1:], strict=True)],
                         hovertemplate="<b>%{customdata[0]}</b><br>retorno entre %{customdata[1]}<extra></extra>"))
    # Color según el método y trazo según la confianza (95 % discontinua, 99 % continua); el valor va en la leyenda,
    # agrupada por método: cada grupo es una columna con sus dos niveles.
    methods = {"var_pct": ("VaR paramétrico", C.blue), "hist_pct": ("VaR histórico", C.ocre)}
    ys = np.linspace(0, top, 16)
    for m, (col, (label, color)) in enumerate(methods.items()):
        for _, row in v["table"].iterrows():
            x, c = -100 * row[col], int(round(100 * row["conf"]))
            name = f"{label} {c} %: {num(x, 2)} %"
            fig.add_trace(go.Scatter(x=[x] * len(ys), y=ys, mode="lines", name=name, legendgroup=col,
                                     legendrank=2 + 2 * m + (c == 99),
                                     line=dict(color=color, width=2, dash="dash" if c == 95 else "solid"),
                                     hovertemplate=f"<b>{num(x, 2)} %</b><br>{label} al {c} %<extra></extra>"))
    fig.update_xaxes(title_text="retorno del portafolio en 21 días hábiles", ticksuffix=" %")
    fig.update_yaxes(title_text="número de ventanas", rangemode="tozero")
    return _wide_layout(fig, 450, legend=dict(traceorder="grouped"))


# ----------------------------------------------------------------------------- 5.1
def beta_scatter(R: dict) -> go.Figure:
    df = R["bt"]["sample"]
    tk = R["cfg"]["portafolio"]["tickers"]
    df = df.assign(Portafolio=df[tk] @ R["w"])
    sub = df.sample(1500, random_state=3)
    names = tk + ["Portafolio"]
    # Ejes a ±12 % (x) y ±16 % (y): caben los días extremos de marzo de 2020 (S&P 500 −12,0 %, MSFT −14,7 %), los que
    # más pesan en la recta que se dibuja.
    lim_x, lim_y = 12, 16
    xs = np.array([-lim_x, lim_x]) / 100
    dates = [fecha(d) for d in sub.index]
    fig = go.Figure(go.Scatter(x=[-lim_x, lim_x], y=[-lim_x, lim_x], mode="lines", showlegend=False,
                               line=dict(color=C.muted, width=1, dash="dot"), hoverinfo="skip"))
    for j, n in enumerate(names):
        b = R["bt"]["table"][n]
        vis = j == len(names) - 1
        fig.add_trace(go.Scatter(x=(100 * sub["mkt"]).astype(np.float32), y=(100 * sub[n]).astype(np.float32),
                                 mode="markers", name="Retornos diarios", legendgroup=f"nube{j}", showlegend=False,
                                 marker=dict(size=5, color=TICKER[n], opacity=0.45, line=dict(width=0)), visible=vis,
                                 customdata=dates,
                                 hovertemplate=f"<b>%{{y}}</b> {n}<br>%{{x}} S&P 500<br>%{{customdata}}<extra></extra>"))
        _legend_dot(fig, "Retornos diarios", f"nube{j}", TICKER[n], visible=vis, legendrank=1)
        fig.add_trace(go.Scatter(x=100 * xs, y=100 * (b["alpha"] + b["beta"] * xs), mode="lines", name="Recta del CAPM",
                                 line=dict(color=C.ink, width=2), visible=vis, hoverinfo="skip", legendrank=2))
        fig.add_trace(go.Scatter(x=[-lim_x + 0.6], y=[lim_y - 0.6], mode="text", textposition="bottom right", visible=vis,
                                 text=[f"β = {num(b['beta'], 3)}<br>R² = {num(b['r2'], 3)}"], showlegend=False,
                                 textfont=dict(size=13, color=C.ink), hoverinfo="skip"))
    fig.add_annotation(x=lim_x, y=lim_x, text="β = 1", showarrow=False, xanchor="left", xshift=4,
                       font=dict(color=C.muted, size=11.5))
    per = 4  # nube, muestra de leyenda, recta y rótulo de cada activo
    n_tr = 1 + per * len(names)
    buttons = [dict(label=n, method="update", args=[{"visible": _visible(n_tr, [0, *range(per * j + 1, per * j + 1 + per)])}])
               for j, n in enumerate(names)]
    menu = _menu(buttons)
    menu[0]["active"] = len(names) - 1
    fig.update_layout(updatemenus=menu)
    # %{x} y %{y} sin formato toman el de los ejes (hoverformat y sufijo), con signo menos tipográfico como las marcas.
    # Margen de 0,6 puntos a cada lado del eje X: las rectas, que llegan a ±12 %, no tocan los rótulos del eje Y, y en la
    # esquina «−12 %» del eje X se aparta de «−16 %». Marcas cada 6 puntos en X: con 4 eran siete y a 320 px giraban.
    pad = 0.6
    fig.update_xaxes(title_text="retorno diario del S&P 500", ticksuffix=" %", range=[-lim_x - pad, lim_x + pad],
                     dtick=6, zeroline=True, zerolinecolor=C.axis, zerolinewidth=1, hoverformat=".2f")
    fig.update_yaxes(title_text="retorno diario del activo", ticksuffix=" %", range=[-lim_y, lim_y], dtick=4,
                     zeroline=True, zerolinecolor=C.axis, zerolinewidth=1, hoverformat=".2f")
    return _wide_layout(fig, 420, margin=dict(l=8, r=44, t=16, b=8))


# ----------------------------------------------------------------------------- 5.2
def beta_rolling(R: dict) -> go.Figure:
    roll = {n: _weekly(s.dropna()) for n, s in R["bt"]["rolling"].items()}
    first, last = min(s.index[0] for s in roll.values()), max(s.index[-1] for s in roll.values())
    fig = go.Figure()
    _ref_line(fig, [first, last], 1)
    for n, s in roll.items():
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=n,
                                 line=dict(color=TICKER[n], width=2.5 if n == "Portafolio" else 2),
                                 hovertemplate=f"<b>%{{y:.2f}}</b>  {n}<extra></extra>"))
    _end_labels(fig, last, [s.iloc[-1] for s in roll.values()], [num(s.iloc[-1], 2) for s in roll.values()],
                [TICKER[n] for n in roll])
    fig.add_annotation(x=last, y=1, text="β = 1", showarrow=False, xanchor="left", xshift=4,
                       font=dict(size=11.5, color=C.muted))
    _time_axis(fig)
    fig.update_xaxes(range=[first, last], title_text="último día de la ventana")
    fig.update_yaxes(title_text="beta móvil (ventana de 504 días)", tickformat=".1f")
    # Altura de 5.1 más su fila de botones: los dos ejes x quedan alineados en la .grid2.
    return _wide_layout(fig, 464, hovermode="x unified", margin=dict(l=8, r=50, t=16, b=8))


STRAT_NAMES = {"sin": "Sin cobertura", "corto": "Siempre corto (cubierto)", "largo": "Siempre largo"}
_STRAT_SHORT = {"sin": "sin cobertura", "corto": "cubierto", "largo": "siempre largo"}


def _usd_m(fmt: str = ",.2f") -> str:
    return f"<b>USD %{{y:{fmt}}} M</b>"


def _time_axes(fig: go.Figure, hoverformat: str = "%b %Y", **kw) -> None:
    fig.update_xaxes(showspikes=True, hoverformat=hoverformat, **kw)


def _real_band(fig: go.Figure, x0, x1, label: str | None = "← datos reales") -> None:
    """Franja ocre de los meses con datos reales; la etiqueta va a su derecha y señala la franja con la flecha."""
    # En oscuro, sin el refuerzo de opacidad de rgba(): con él la franja pesaba tanto como las bandas de datos.
    fig.add_vrect(x0=x0, x1=x1, fillcolor=rgba(C.ocre, 0.13, dark_alpha=0.09), line_width=0, layer="below")
    if label:
        fig.add_annotation(x=x1, y=1, xref="x", yref="paper", text=label, showarrow=False, xanchor="left",
                           yanchor="top", xshift=4, yshift=-2, font=dict(size=11, color=C.ink2))


def _label(fig: go.Figure, x, y, text: str, above: bool = True, xanchor: str = "right", **kw) -> None:
    fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor=xanchor, yanchor="bottom" if above else "top",
                       yshift=4 if above else -4, font=dict(size=11.5, color=C.ink2), **kw)


# ----------------------------------------------------------------------------- 7.1
def payoff(R: dict) -> go.Figure:
    v0, bp, n, f0, m = R["v0"], R["beta_p"], R["n"], R["f0"], R["mult"]
    x = np.linspace(-0.30, 0.30, 61)
    port = bp * x * v0
    short = -n * m * f0 * x
    lines = [
        ("Portafolio sin cobertura", port, dict(color=C.gray, width=2), True),
        (f"{n} futuros cortos", short, dict(color=C.blue, width=2, dash="dash"), True),
        (f"Portafolio + {n} futuros cortos", port + short, dict(color=C.green, width=2.5), True),
        (f"Portafolio + {n} futuros largos", port - short, dict(color=C.verm, width=2), "legendonly"),
    ]
    fig = go.Figure()
    for name, y, line, vis in lines:
        fig.add_trace(go.Scatter(x=100 * x, y=y / 1e6, name=name, line=line, visible=vis,
                                 hovertemplate=f"{_usd_m('+,.2f')}  {name}<extra></extra>"))
    xe = 100 * x[-3]
    # Velo bajo cada rótulo: la recta de los futuros largos (que se prende desde la leyenda) y la gris los cruzaban.
    veil = dict(bgcolor=rgba(C.surface, 0.85), borderpad=2)
    _label(fig, xe, port[-3] / 1e6, "sin cobertura", above=True, **veil)
    _label(fig, xe, short[-3] / 1e6, f"{n} futuros cortos", above=False, **veil)
    _label(fig, xe, (port + short)[-3] / 1e6, "cubierto: casi plano", above=True, **veil)
    fig.add_hline(y=0, line=dict(color=C.axis, width=1), layer="below")
    fig.update_xaxes(title_text="variación del S&P 500 en el periodo (%)", ticksuffix=" %", showspikes=True,
                     hoverformat="+.0f", unifiedhovertitle=dict(text="S&P 500 %{x:+.0f} %"))
    fig.update_yaxes(title_text="ganancia o pérdida (USD millones)", tickformat=",.0f")
    return _layout(fig, 430, hovermode="x unified")


# ----------------------------------------------------------------------------- 8.1
def _millions(v: float) -> str:
    return num(v / 1e6, 2)  # num() ya entrega el signo menos tipográfico


def _margin_notes(h: dict, k: int) -> list[str]:
    """Texto del tooltip del saldo: el llamado (o el depósito por roll) de ese mes."""
    notes = []
    for call, rdep, pre, dep in zip(h["call"][k], h["rdep"][k], h["pre"][k], h["dep"][k], strict=True):
        if call:
            notes.append(f"<br>llamado: reponemos <b>USD {_millions(dep)} M</b>"
                         f"<br>(el saldo había caído a {_millions(pre)} M)")
        elif rdep:
            notes.append(f"<br>depósito por roll: USD {_millions(dep)} M")
        else:
            notes.append("")
    return notes


def margin(R: dict) -> go.Figure:
    tl, h = R["tl"], R["strat"]["corto"]
    imf, mm = R["imf"], R["mm_s"]
    x = tl["fecha"]
    views = {"p5": "Bajista (P5)", "p50": "Central (mediana)", "p95": "Alcista (P95)"}
    fig = go.Figure()
    for key in views:
        k = R["rep"][key]
        vis = key == "p50"
        n = h["N"][k]
        c = h["call"][k]
        fig.add_trace(go.Scatter(x=x, y=h["bal"][k] / 1e6, name="Saldo de la cuenta", legendrank=1, visible=vis,
                                 line=dict(color=C.green, width=2.5), customdata=_margin_notes(h, k),
                                 hovertemplate=f"{_usd_m()}  saldo%{{customdata}}<extra></extra>"))
        fig.add_trace(go.Bar(x=x[c], y=h["dep"][k][c] / 1e6, base=h["pre"][k][c] / 1e6, width=15 * DAY_MS,
                             name="Reposición por llamado", legendrank=3, visible=vis,
                             marker=dict(color=rgba(C.verm, 0.85)),
                             hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x[c], y=h["pre"][k][c] / 1e6, mode="markers", name="Saldo antes del llamado",
                                 legendrank=2, visible=vis, hoverinfo="skip",
                                 marker=dict(size=8, color=C.surface, line=dict(color=C.verm, width=2))))
        fig.add_trace(go.Scatter(x=x, y=n * round(mm * imf) / 1e6, name="Margen inicial", legendrank=4, visible=vis,
                                 line=dict(color=C.ink2, width=1.5, dash="dash", shape="hv"),
                                 customdata=n, hovertemplate=f"{_usd_m()}  margen inicial (%{{customdata:.0f}} contratos)"
                                                             "<extra></extra>"))
        fig.add_trace(go.Scatter(x=x, y=n * mm / 1e6, name="Margen de mantenimiento", legendrank=5, visible=vis,
                                 line=dict(color=C.verm, width=1.5, dash="dot", shape="hv"),
                                 hovertemplate=f"{_usd_m()}  mantenimiento<extra></extra>"))
    buttons = [dict(label=lab, method="update", args=[{"visible": _visible(5 * len(views), list(range(5 * j, 5 * j + 5)))}])
               for j, lab in enumerate(views.values())]
    menu = _menu(buttons)
    menu[0]["active"] = 1
    _real_band(fig, x.iloc[0], x.iloc[R["last_i"]])
    pad = pd.Timedelta(days=12)
    _time_axes(fig, range=[x.iloc[0] - pad, x.iloc[-1] + pad])
    # Enteros como en las demás gráficas en millones; si el paso fuera de medio millón, sale el decimal (0,5).
    fig.update_yaxes(title_text="cuenta de margen (USD millones)", tickformat=",.1~f", zeroline=True,
                     zerolinecolor=C.axis, zerolinewidth=1)
    return _layout(fig, 470, updatemenus=menu, hovermode="x unified", barmode="overlay")


# ----------------------------------------------------------------------------- 9.2
def wealth_fan(R: dict) -> go.Figure:
    x = R["tl"]["fecha"]
    alpha = {"largo": 0.12, "sin": 0.2, "corto": 0.2}
    pct = {k: [np.percentile(R["W"][k] / 1e6, p, axis=0) for p in (5, 50, 95)] for k in alpha}
    fig = go.Figure()
    # Bandas P5–P95 anidadas: cada borde rellena hasta el anterior, así cada color pinta solo su anillo.
    edges = [("largo", 2, None), ("sin", 2, "largo"), ("corto", 2, "sin"), ("corto", 0, "corto"), ("sin", 0, "sin"),
             ("largo", 0, "largo")]
    for k, j, fill in edges:
        fig.add_trace(go.Scatter(x=x, y=pct[k][j], line=dict(color=rgba(STRAT_P2[k], 0.55), width=1), showlegend=False,
                                 hoverinfo="skip", fill="tonexty" if fill else None,
                                 fillcolor=rgba(STRAT_P2[fill], alpha[fill]) if fill else None))
    for rank, k in ((3, "largo"), (2, "sin"), (1, "corto")):
        p5, p50, p95 = pct[k]
        fig.add_trace(go.Scatter(x=x, y=p50, name=STRAT_NAMES[k], legendrank=rank,
                                 line=dict(color=STRAT_P2[k], width=2.5 if k == "corto" else 2), customdata=np.c_[p5, p95],
                                 hovertemplate=f"<b>%{{y:,.1f}}</b>  mediana {_STRAT_SHORT[k]}<br>"
                                               "P5–P95: %{customdata[0]:,.1f} a %{customdata[1]:,.1f}<extra></extra>"))
    v0 = R["v0"] / 1e6
    fig.add_hline(y=v0, line=dict(color=C.muted, width=1, dash="dot"))
    fig.add_annotation(x=x.iloc[-1], y=v0, text=f"USD {num(v0, 0)} M invertidos", showarrow=False, xanchor="right",
                       yanchor="top", yshift=-3, font=dict(size=11, color=C.ink2))
    _real_band(fig, x.iloc[0], x.iloc[R["last_i"]])
    _time_axes(fig, unifiedhovertitle=dict(text="%{x|%b %Y} · USD millones"))
    fig.update_yaxes(title_text="riqueza (USD millones)", tickformat=",.0f")
    legend = dict(title=dict(text="Mediana (línea) y P5–P95 (banda):", side="top", font=dict(size=12, color=C.ink2)),
                  traceorder="normal", itemclick=False, itemdoubleclick=False)
    return _layout(fig, 440, hovermode="x unified", legend=legend)


# ----------------------------------------------------------------------------- 9.3
def terminal_hist(R: dict) -> go.Figure:
    edges = np.arange(-100, 305, 5)
    mid = edges[:-1] + 2.5
    lo, hi = -100, 250
    ret = {k: 100 * (R["W"][k][:, -1] / R["v0"] - 1) for k in STRAT_P2}
    share = {k: 100 * np.histogram(r, bins=edges)[0] / len(r) for k, r in ret.items()}
    fig = go.Figure()
    for rank, key in ((2, "sin"), (3, "largo"), (1, "corto")):
        prot = key == "corto"
        fig.add_trace(go.Scatter(x=mid, y=share[key], name=STRAT_NAMES[key], legendrank=rank, mode="lines",
                                 line=dict(color=STRAT_P2[key], width=2.5 if prot else 2, shape="hvh"),
                                 fill="tozeroy" if prot else None, fillcolor=rgba(STRAT_P2[key], 0.14) if prot else None,
                                 hovertemplate=f"<b>%{{y:.1f}} %</b>  {STRAT_NAMES[key]}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=C.ink2, width=1, dash="dot"))
    for text, anchor in (("← pierde capital", "right"), ("gana →", "left")):
        fig.add_annotation(x=0, y=1, yref="paper", text=text, showarrow=False, xanchor=anchor, yanchor="top",
                           xshift=-6 if anchor == "right" else 6, font=dict(size=11, color=C.muted))
    # La cola de siempre largo que pasa del borde derecho: la nota va encima de las curvas desde el 75 %, porque en el
    # celular el texto llega por la izquierda hasta cerca del 90 % (a la altura de las curvas desde el 100 % se montaba
    # sobre los escalones rojo y gris). El velo la deja legible si en una pantalla más angosta alcanza alguno.
    tail = 100 * np.mean(ret["largo"] > hi)
    y_tail = max(s[mid >= 75].max() for s in share.values())
    fig.add_annotation(x=hi, y=y_tail, text=f"{num(tail, 1)} % de siempre largo<br>pasa de {hi} % →", showarrow=False,
                       xanchor="right", yanchor="bottom", yshift=6, align="right", font=dict(size=11, color=C.muted),
                       bgcolor=rgba(C.surface, 0.85), borderpad=2)
    # Marcas cada 2 puntos y la más alta lejos del borde: las notas «pierde capital» y «gana» van en esa franja y, en el
    # celular, la de la izquierda llega hasta la columna de las marcas del eje (se pegaba al «8 %»).
    ymax = max(s.max() for s in share.values())
    top = 1.18 * ymax
    top = max(top, 2 * np.floor(top / 2) / 0.86)
    fig.update_xaxes(title_text="retorno acumulado a 4 años, al 30-jul-2030 (%)", ticksuffix=" %", range=[lo, hi],
                     showspikes=True, unifiedhovertitle=dict(text="Retorno de %{x:.1f} % ± 2,5 puntos · % de trayectorias"))
    fig.update_yaxes(title_text="trayectorias (%)", ticksuffix=" %", tickformat=",.0f", dtick=2, range=[0, top])
    return _layout(fig, 440, hovermode="x unified")


# ----------------------------------------------------------------------------- 9.1
def quarters(R: dict) -> go.Figure:
    q = R["quarters"].reset_index(drop=True)
    x = pd.to_datetime(q["hasta"])
    obs = q["obs"].to_numpy(bool)
    sim = ~obs
    since = [f"{d.day} {MESES[d.month - 1]} {d.year}" for d in pd.to_datetime(q["desde"])]
    cd = np.c_[q["cierra"], q["abre"], q["pnl_p5"] / 1e3, q["pnl_p95"] / 1e3, since]
    w = 0.6 * x.diff().min().days * DAY_MS
    fig = go.Figure()
    # Relleno tenue con contorno: el rango se lee en los dos modos y su muestra en la leyenda no queda vacía.
    fig.add_trace(go.Bar(x=x[sim], base=q["pnl_p5"][sim] / 1e3, y=(q["pnl_p95"] - q["pnl_p5"])[sim] / 1e3, width=w,
                         name="Rango P5–P95", customdata=cd[sim],
                         marker=dict(color=rgba(C.green, 0.2), line=dict(color=rgba(C.green, 0.5), width=1)),
                         hovertemplate="<b>%{customdata[2]:,.0f} a %{customdata[3]:,.0f}</b>  rango P5–P95<extra></extra>"))
    fig.add_trace(go.Scatter(x=x[sim], y=q["pnl_media"][sim] / 1e3, mode="markers", name="Resultado esperado (media)",
                             marker=dict(size=9, color=C.green), customdata=cd[sim],
                             hovertemplate="<b>%{y:,.0f}</b>  resultado esperado del %{customdata[0]}"
                                           "<br>desde el %{customdata[4]}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x[obs], y=q["pnl_media"][obs] / 1e3, mode="markers",
                             name=f"Dato real ({', '.join(q['cierra'][obs])})",
                             legendgroup="obs", marker=dict(size=11, color=C.ocre), customdata=cd[obs],
                             hovertemplate="<b>%{y:,.0f}</b>  resultado real del %{customdata[0]}"
                                           "<br>desde el %{customdata[4]}<extra></extra>"))
    sp = q["spread_roll"].notna().to_numpy()
    fig.add_trace(go.Bar(x=x[sim & sp], y=q["spread_roll"][sim & sp], width=0.7 * w, yaxis="y2", name="Spread del roll",
                         marker=dict(color=C.blue), customdata=cd[sim & sp],
                         hovertemplate="<b>%{y:,.1f} puntos</b>  spread del roll a %{customdata[1]}<extra></extra>"))
    fig.add_trace(go.Bar(x=x[obs & sp], y=q["spread_roll"][obs & sp], width=0.7 * w, yaxis="y2", name="Dato real",
                         legendgroup="obs", showlegend=False, marker=dict(color=C.ocre), customdata=cd[obs & sp],
                         hovertemplate="<b>%{y:,.1f} puntos</b>  spread real del roll a %{customdata[1]}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=C.axis, width=1), layer="below")
    fig.update_layout(
        yaxis=dict(domain=[0.36, 1], title_text="resultado de los futuros cortos<br>(USD miles)", tickformat=",.0f"),
        yaxis2=dict(domain=[0, 0.24], title_text="spread del roll<br>(puntos)", tickformat=",.0f", rangemode="tozero"),
        xaxis=dict(anchor="y2", showspikes=True, spikemode="across",
                   unifiedhovertitle=dict(text="Cierre del %{x|%d %b %Y} · USD miles")),
        hoversubplots="axis",
    )
    return _layout(fig, 500, hovermode="x unified", barmode="overlay")


# ----------------------------------------------------------------------------- 10.1
def expected(R: dict) -> go.Figure:
    x = R["tl"]["fecha"]
    v0 = R["v0"]
    t = np.array([(d - R["t0"]).days / 365.25 for d in x])
    m = {key: R["W"][key].mean(axis=0) / 1e6 for key in ("sin", "corto")}
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=m["sin"], name="Sin cobertura (media simulada)", line=dict(color=C.gray, width=2),
                             hovertemplate=f"{_usd_m()}  sin cobertura<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=v0 * (1 + R["capm"]["Portafolio"]) ** t / 1e6,
                             name="CAPM: V₀(1 + rf + β·PRM)<sup>t</sup>",
                             line=dict(color=C.gray, width=1.5, dash="dash"),
                             hovertemplate=f"{_usd_m()}  CAPM<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=m["corto"], name="Con cobertura (media simulada)", line=dict(color=C.green, width=2.5),
                             hovertemplate=f"{_usd_m()}  con cobertura<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=v0 * (1 + R["rf_h"]) ** t / 1e6, name="Libre de riesgo: V₀(1 + rf)<sup>t</sup>",
                             line=dict(color=C.green, width=1.5, dash="dot"),
                             hovertemplate=f"{_usd_m()}  libre de riesgo<extra></extra>"))
    xe, hi, lo = x.iloc[-1], m["sin"][-1], m["corto"][-1]
    fig.add_annotation(x=xe, y=hi, ax=xe, ay=lo, xref="x", yref="y", axref="x", ayref="y", text="", showarrow=True,
                       arrowside="end+start", arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor=C.muted,
                       standoff=3, startstandoff=3)
    fig.add_annotation(x=xe, y=(hi + lo) / 2, text=f"−USD {num(hi - lo, 1)} M", showarrow=False, xanchor="right",
                       xshift=-8, yshift=-46, font=dict(size=11.5, color=C.ink2))
    _real_band(fig, x.iloc[0], x.iloc[R["last_i"]])
    _time_axes(fig)
    fig.update_yaxes(title_text="valor esperado (USD millones)", tickformat=",.0f")
    return _layout(fig, 430, hovermode="x unified")


# ----------------------------------------------------------------------------- 12.1
def _signed_m(values, d: int) -> list[str]:
    """«+1,80», «−0,023» y «0,00» (el cero sin signo), ya escritos para el tooltip."""
    return [("+" if round(v, d) > 0 else "") + num(v, d) for v in np.asarray(values, dtype=float)]


def beta_sens(R: dict) -> go.Figure:
    v0 = R["v0"]
    x = np.linspace(-0.3, 0.3, 61)
    # Las rectas sin cubrir no usan el verde, que en todo el informe es «con cobertura» (7.1, 10.1, E.1). Las dos más
    # cercanas (0,50 y 0,80) van en ocre y azul, que se separan también con daltonismo.
    colors = [C.ocre, C.blue, C.verm]
    fig = go.Figure()
    rows = list(R["sens_beta"].reset_index(drop=True).iterrows())
    for j, row in rows:
        b = row["beta"]
        lab = f"β = {num(b, 2)}"
        col = colors[j]
        y = b * x * v0 / 1e6 + 0.0
        fig.add_trace(go.Scatter(x=100 * x, y=y, name=lab + (" (nuestra)" if j == 1 else "") + " sin cobertura",
                                 legendrank=1 + j, line=dict(color=col, width=2.5 if j == 1 else 2),
                                 customdata=_signed_m(y, 2),
                                 hovertemplate=f"<b>USD %{{customdata}} M</b>  {lab} sin cubrir<extra></extra>"))
    # Las tres coberturas quedan una encima de otra en cero: van las tres en el verde punteado (el color de «con
    # cobertura») de su única entrada de leyenda, que las prende o apaga juntas. En el tooltip solo va la nuestra (lo
    # que queda sin cubrir, unos miles de dólares): seis filas largas tapaban toda la gráfica en el celular.
    for j, row in (rows[0], rows[2], rows[1]):
        y = row["beta_res"] * x * v0 / 1e6 + 0.0  # + 0.0: sin «−0,000» en el cero
        # (con plantilla de tooltip, plotly.js no respeta hoverinfo="skip" en la caja unificada: las otras dos no llevan)
        hover = (dict(customdata=_signed_m(y, 3), hovertemplate=f"<b>USD %{{customdata}} M</b>  con {int(row['n'])} "
                                                                "cortos<extra></extra>")
                 if j == 1 else dict(hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=100 * x, y=y, name=f"β = {num(row['beta'], 2)} con {int(row['n'])} cortos",
                                 legendgroup="con", showlegend=False, line=dict(color=HEDGE["con"], width=2, dash="dot"),
                                 **hover))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name="Con cobertura (las tres, ≈ 0)", legendgroup="con",
                             legendrank=4, line=dict(color=HEDGE["con"], width=2, dash="dot"), hoverinfo="skip"))
    # Rótulos al final de cada recta: dentro del lienzo, en el celular la recta de β = 0,50 cruzaba su propio rótulo.
    _end_labels(fig, 100 * x[-1], [row["beta"] * x[-1] * v0 / 1e6 for _, row in rows],
                [f"β = {num(row['beta'], 2)}" for _, row in rows], colors)
    _label(fig, 100 * x[-1], 0, "con cobertura ≈ 0", above=False)
    fig.add_hline(y=0, line=dict(color=C.axis, width=1), layer="below")
    # Rango fijo: sin él, el autorango abre espacio a la derecha para el texto de los rótulos finales.
    fig.update_xaxes(title_text="variación del S&P 500 (%)", ticksuffix=" %", showspikes=True, range=[-30, 30],
                     unifiedhovertitle=dict(text="S&P 500 %{x:+.0f} %"))
    fig.update_yaxes(title_text="ganancia o pérdida sistemática (USD millones)", tickformat=",.0f")
    return _layout(fig, 470, hovermode="x unified", margin=dict(l=8, r=64, t=16, b=8))


# ----------------------------------------------------------------------------- E.1
def expost(R: dict) -> go.Figure:
    e = R["expost"]
    v = e["series"] / 1e6
    h = (e["series"] + e["fut_cum"]) / 1e6
    spx = yahoo("^GSPC")["close"].loc[v.index]
    spx = R["invested"] * spx / spx.iloc[0] / 1e6
    lines = [
        (spx, f"USD {num(R['invested'] / 1e6, 0)} M en el S&P 500 (precio)", dict(color=C.muted, width=1.5, dash="dot"),
         "en el S&P 500"),
        (v, "Portafolio sin cobertura", dict(color=C.gray, width=2), "sin cobertura"),
        (h, "Portafolio + futuros cortos", dict(color=C.green, width=2.5), "con cobertura"),
    ]
    fig = go.Figure()
    for rank, (s, name, line, tag) in zip((3, 2, 1), lines, strict=True):
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=name, line=line, legendrank=rank,
                                 hovertemplate=f"{_usd_m()}  {tag}<extra></extra>"))
    for s, _, line, _ in lines:
        fig.add_trace(go.Scatter(x=[s.index[-1]], y=[s.iloc[-1]], mode="markers", marker=dict(color=line["color"]),
                                 showlegend=False, hoverinfo="skip", cliponaxis=False))
        fig.add_annotation(x=s.index[-1], y=s.iloc[-1], text=num(s.iloc[-1], 2), showarrow=False, xanchor="left",
                           xshift=8, font=dict(size=11.5, color=C.ink2))
    q = R["quarters"].iloc[0]
    fig.add_vline(x=q["hasta"], line=dict(color=C.muted, width=1, dash="dash"))
    fig.add_annotation(x=q["hasta"], y=1, yref="paper", text=f"roll {q['cierra']} → {q['abre']}", showarrow=False,
                       xanchor="left", yanchor="top", xshift=4, font=dict(size=11, color=C.ink2))
    _time_axes(fig, "%d %b %Y", dtick="M1", tickformat="%b %Y", range=[v.index[0], v.index[-1]])
    fig.update_yaxes(title_text="valor (USD millones)", tickformat=",.1f")
    return _layout(fig, 420, hovermode="x unified", margin=dict(l=8, r=52, t=16, b=8))


def build_all(R: dict) -> dict[str, str]:
    figs = {
        "p2_price12m": price_12m, "p2_growth": growth, "p2_byyear": by_year, "p2_corr": correlation, "p2_frontier": frontier,
        "p2_var": var_hist, "p2_beta_scatter": beta_scatter, "p2_beta_rolling": beta_rolling, "p2_payoff": payoff,
        "p2_margin": margin, "p2_fan": wealth_fan, "p2_terminal": terminal_hist, "p2_quarters": quarters,
        "p2_expected": expected, "p2_beta_sens": beta_sens, "p2_expost": expost,
    }
    return {k: to_div(f(R), k) for k, f in figs.items()}
