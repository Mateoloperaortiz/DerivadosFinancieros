"""Gráficos interactivos (Plotly) del informe.

Todas las gráficas usan el sistema visual de ``theme.py``: colores de la paleta validada (con su pareja para el modo
oscuro), un solo eje Y por panel y menús que la página convierte en botones.
"""

from __future__ import annotations

import textwrap

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..analysis import DISTS, HEDGE_YEARS, STRATS
from .fmt import NBSP, fecha, mes, num
from .theme import DIST, HEDGE, SCEN, SEQ, C, _layout, _menu, _visible, narrow, rgba, to_div

PCT = f"{NBSP}%"


def _iso(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M")


def _note(x, y, text: str, ax: float = 0, ay: float = -36, yref: str = "y", **kw) -> dict:
    """Etiqueta de un punto con un tallo fino; el texto va en tinta neutra sobre un velo de la superficie."""
    kw.setdefault("align", kw.get("xanchor", "center"))
    return dict(x=_iso(x), y=y, xref="x", yref=yref, text=text, showarrow=True, ax=ax, ay=ay, standoff=5,
                arrowcolor=C.muted, arrowwidth=1, arrowhead=0, bgcolor=rgba(C.surface, 0.85), borderpad=1,
                font=dict(size=11.5, color=C.ink2), **kw)


def _tag(x, y, text: str, yref: str = "y", **kw) -> dict:
    """Valor junto al último punto de una serie, sin tallo."""
    opts = dict(xanchor="right", align="right", yanchor="bottom", xshift=-2, yshift=5)
    opts.update(kw)
    return dict(x=_iso(x), y=y, xref="x", yref=yref, text=text, showarrow=False, font=dict(size=11.5, color=C.ink2),
                **opts)


def _unit(text: str, yref: str = "y") -> dict:
    """Unidad de un panel, encima de su esquina superior izquierda; reemplaza el título vertical del eje."""
    return dict(x=0, xref="paper", y=1, yref=f"{yref} domain", text=text, showarrow=False, xanchor="left",
                yanchor="bottom", yshift=5, font=dict(size=11.5, color=C.muted))


def _span(s: pd.Series, start, pad_lo: float, pad_hi: float) -> list[float]:
    w = s[s.index >= start]
    lo, hi = float(w.min()), float(w.max())
    return [lo - pad_lo * (hi - lo), hi + pad_hi * (hi - lo)]


# ----------------------------------------------------------------------------- A.1
def trm_history(R: dict) -> go.Figure:
    a1, st = R["a1"], R["a1"]["stats"]
    trm, brent = a1["trm_daily"], a1["brent_monthly"]
    end = trm.index[-1]
    # El promedio mensual del Brent se dibuja a mitad de mes para que el cursor lea el mes que le corresponde.
    bm = pd.Series(brent.values, index=brent.index.to_period("M").to_timestamp() + pd.Timedelta(days=14))
    events = dict(
        desplome=("2015-08-24", "Desplome<br>del petróleo"),
        covid=("2020-03-19", "Choque<br>COVID-19"),
        maximo=(st["fecha_max_hist"], f"Máximo histórico {num(st['max_hist'])}"),
        guerra=("2026-03-04", "Guerra en el<br>golfo Pérsico"),
        vuelta=("2026-06-23", "Segunda<br>vuelta"),
        terremoto=("2026-08-10", "Terremoto<br>7,4"),
        valoracion=(end, f"Valoración<br>{num(R['s0'], 2)}"),
    )
    pts = {k: (pd.Timestamp(d), float(trm.asof(pd.Timestamp(d))), t) for k, (d, t) in events.items()}
    # Los rótulos dependen del horizonte, porque los cuatro eventos de 2026 caben en pocos píxeles cuando la ventana
    # es larga. En las vistas largas solo se dibujan los puntos rotulados; en las cortas, los siete (con tooltip).
    wide = dict(desplome=dict(ay=-56, xanchor="left"), covid=dict(ay=-40), maximo=dict(ay=-24),
                guerra=dict(ay=40, xanchor="right"), valoracion=dict(ay=46, xanchor="right"))
    mid = dict(guerra=dict(ay=40, xanchor="right"), vuelta=dict(ay=44, xanchor="right"),
               valoracion=dict(ay=46, xanchor="right"))
    near = dict(guerra=dict(ay=-30), vuelta=dict(ay=40, xanchor="right"), terremoto=dict(ay=44),
                valoracion=dict(ay=-62, xanchor="right"))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trm.index, y=trm.values, name="TRM (COP por USD)", line=dict(color=C.green, width=2),
        hovertemplate="<b>%{y:,.2f}</b>  TRM<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=bm.index, y=bm.values, name="Brent, promedio mensual (USD por barril)", yaxis="y2",
        line=dict(color=C.ocre, width=2), fill="tozeroy", fillcolor=rgba(C.ocre, 0.1),
        customdata=[mes(d) for d in brent.index],
        hovertemplate="<b>USD %{y:,.1f}</b>  Brent, promedio de %{customdata}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[p[0] for p in pts.values()], y=[p[1] for p in pts.values()], mode="markers", name="Eventos",
        showlegend=False, marker=dict(size=8, color=C.ink), customdata=[fecha(p[0]) for p in pts.values()],
        text=[p[2].replace("<br>", " ") for p in pts.values()],
        hovertemplate="<b>%{text}</b>  %{customdata}<extra></extra>",
    ))

    last = float(bm.iloc[-1])
    fixed = [_tag(bm.index[-1], last, f"USD{NBSP}{num(last, 1)} ({mes(brent.index[-1])})", yref="y2", yshift=6),
             _unit("COP por USD"), _unit("USD por barril", "y2")]
    views = [("1 año", end - pd.DateOffset(years=1), near), ("3 años", end - pd.DateOffset(years=3), mid),
             ("5 años", end - pd.DateOffset(years=5), wide), ("Desde 2015", trm.index[0], wide)]
    buttons = []
    for label, start, place in views:
        pad = (end - start) * 0.012
        notes = [_note(pts[k][0], pts[k][1], pts[k][2], **o) for k, o in place.items() if pts[k][0] >= start]
        shown = [1 if k in place or place is not wide else 0 for k in pts]
        # Un valor por traza: la TRM y el Brent no tienen marcadores; los eventos, uno por punto.
        buttons.append(dict(label=label, method="update", args=[{"marker.opacity": [1, 1, shown]}, {
            "xaxis.range": [_iso(start - pad), _iso(end + pad)],
            "yaxis.range": _span(trm, start, 0.1, 0.2),
            "yaxis2.range": [0, float(bm[bm.index >= start - pd.Timedelta(days=15)].max()) * 1.25],
            "annotations": notes + fixed,
        }]))
    menu = _menu(buttons)
    menu[0]["active"] = len(buttons) - 1
    init = buttons[-1]["args"][1]
    fig.data[2].marker.opacity = buttons[-1]["args"][0]["marker.opacity"][2]
    fig.update_layout(
        updatemenus=menu, annotations=init["annotations"], hovermode="x unified", hoversubplots="axis",
        hoverdistance=30, legend=dict(y=1.06),
        xaxis=dict(anchor="y2", range=init["xaxis.range"], showspikes=True, hoverformat="%d %b %Y"),
        yaxis=dict(domain=[0.36, 1], range=init["yaxis.range"], tickformat=",.0f"),
        yaxis2=dict(domain=[0, 0.24], range=init["yaxis2.range"], nticks=4),
    )
    return _layout(fig, 540)


def policy_rates(R: dict) -> go.Figure:
    rates = R["a1"]["rates"]
    # La semana se rotula con su domingo; la última se lleva a la fecha de corte para no pasarse de ella.
    r = rates.resample("W").last()
    r = r.rename(index={r.index[-1]: rates.index[-1]})
    diff = r["banrep"] - r["fed_u"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=r.index, y=r["banrep"], name="BanRep (tasa de política)", line=dict(color=C.green, width=2.5),
        line_shape="hv", hovertemplate="<b>%{y:.2f} %</b>  BanRep<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=r.index, y=r["fed_u"], name="Fed (techo del rango)", line=dict(color=C.gray, width=2),
        line_shape="hv", hovertemplate="<b>%{y:.2f} %</b>  Fed, techo del rango<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=r.index, y=diff, name="Diferencial BanRep − Fed (pp)", yaxis="y2", line=dict(color=C.ocre, width=2),
        fill="tozeroy", fillcolor=rgba(C.ocre, 0.12), line_shape="hv",
        hovertemplate="<b>%{y:.2f} pp</b>  diferencial<extra></extra>",
    ))
    x1 = r.index[-1]
    fig.update_layout(annotations=[
        _tag(x1, r["banrep"].iloc[-1], f"{num(r['banrep'].iloc[-1], 2)}{NBSP}%"),
        _tag(x1, r["fed_u"].iloc[-1], f"{num(r['fed_u'].iloc[-1], 2)}{NBSP}%"),
        _tag(x1, diff.iloc[-1], f"{num(diff.iloc[-1], 2)}{NBSP}pp", yref="y2"),
        _unit("tasa (% anual)"), _unit("diferencial (pp)", "y2"),
    ])
    fig.update_layout(
        hovermode="x unified", hoversubplots="axis", legend=dict(y=1.07),
        xaxis=dict(anchor="y2", showspikes=True, hoverformat="%d %b %Y"),
        yaxis=dict(domain=[0.44, 1], ticksuffix=f"{NBSP}%", range=[0, float(r["banrep"].max()) * 1.14]),
        yaxis2=dict(domain=[0, 0.3], range=[0, float(diff.max()) * 1.32], nticks=4),
    )
    return _layout(fig, 480)


def inflation(R: dict) -> go.Figure:
    col, us = R["a1"]["inflation_col"], R["a1"]["inflation_us"]
    years = sorted(col)
    peak = max(years, key=lambda y: col[y])
    fig = go.Figure()
    fig.add_hrect(y0=2, y1=4, fillcolor=rgba(C.green, 0.16), line_width=0, layer="below")
    # La muestra de la leyenda es pequeña: lleva más opacidad que la franja para que se lea en los dos modos. Nombres
    # cortos (las fuentes van en el pie): así las tres entradas caben en una fila al lado del Gráfico A.1.4.
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", fill="toself", fillcolor=rgba(C.green, 0.3),
                             line=dict(width=0), name=f"Meta BanRep 2–4{NBSP}%", hoverinfo="skip"))
    fig.add_trace(go.Bar(
        x=years, y=[col[y] for y in years], name="Colombia", marker_color=C.green,
        text=[f"{num(col[y], 2)}{NBSP}%" if y in (peak, years[-1]) else "" for y in years],
        textposition="outside", cliponaxis=False, constraintext="none",
        hovertemplate="<b>%{y:.2f} %</b>  Colombia<br>variación anual a sep-%{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=years, y=[us.get(y) for y in years], name=f"EE.{NBSP}UU.", marker_color=C.gray,
        hovertemplate="<b>%{y:.2f} %</b>  Estados Unidos<br>variación anual a sep-%{x}<extra></extra>",
    ))
    # Años en horizontal y abreviados después del primero (2017, 18, 19…): en un celular caben sin girar.
    fig.update_xaxes(type="category", tickangle=0, tickvals=years,
                     ticktext=[str(y) if i == 0 else str(y)[2:] for i, y in enumerate(years)])
    # Rejilla cada 5 puntos y techo en la línea siguiente con holgura: el rótulo del pico queda entre dos líneas (10 % y
    # 15 %) sin que ninguna lo tache, y la línea del techo ancla la unidad como en el Gráfico A.1.4 de al lado.
    fig.update_yaxes(ticksuffix=f"{NBSP}%", range=[0, 5 * np.ceil(max(col.values()) * 1.16 / 5)], dtick=5)
    # x apenas negativa: plotly.js deja que la leyenda use también el margen izquierdo antes de partirla en filas. Con
    # letra de 12 cabe en una fila al lado del A.1.4 y en el celular en dos con holgura (con 12,5 quedaba en el límite).
    return _layout(fig, 400, barmode="group", bargap=0.28, bargroupgap=0.06,
                   legend=dict(y=1.08, x=-0.002, font=dict(size=12)),
                   annotations=[_unit("inflación anual a septiembre")])


def oil_correlation(R: dict) -> go.Figure:
    c = R["a1"]["corr24"].dropna()
    y26, x1 = pd.Timestamp("2026-01-01"), c.index[-1] + pd.Timedelta(days=45)
    fig = go.Figure()
    fig.add_vrect(x0=y26, x1=x1, fillcolor=rgba(C.ocre, 0.12), line_width=0, layer="below")
    fig.add_hline(y=0, line=dict(color=C.axis, width=1))
    fig.add_trace(go.Scatter(
        x=c.index, y=c.values, name="Correlación móvil a 24 meses", line=dict(color=C.green, width=2),
        fill="tozeroy", fillcolor=rgba(C.green, 0.1),
        hovertemplate="<b>%{y:.2f}</b>  correlación a 24 meses<extra></extra>",
    ))
    fig.add_trace(go.Scatter(x=[c.index[-1]], y=[c.iloc[-1]], mode="markers", marker=dict(size=8, color=C.green),
                             hoverinfo="skip", showlegend=False, cliponaxis=False))
    # La franja lleva la correlación de solo los meses de 2026 (la cifra del texto), distinta de la ventana móvil.
    only = R["a1"]["stats"]["corr_2026"]
    fig.update_layout(annotations=[
        dict(x=_iso(x1), y=1, xref="x", yref="paper", text=f"2026<br>solo este año: {_signed(only, 2)}",
             showarrow=False, xanchor="right", align="right", yanchor="top", font=dict(size=11.5, color=C.muted)),
        _note(c.index[-1], c.iloc[-1], f"{mes(c.index[-1])}: {_signed(c.iloc[-1], 2)}", ax=-30, ay=-44,
              xanchor="right"),
        _unit("correlación a 24 meses"),
    ])
    fig.update_xaxes(showspikes=True, hoverformat="%b %Y", range=[_iso(c.index[0] - pd.Timedelta(days=30)), _iso(x1)])
    fig.update_yaxes(range=[-0.8, 0.6], tickformat=".1f", dtick=0.2)
    return _layout(fig, 400, showlegend=False, hovermode="x unified", margin=dict(l=8, r=16, t=28, b=8))


def _wrap(text: str, width: int = 40) -> str:
    """Parte en dos líneas una etiqueta larga en su primer separador (dos puntos o punto medio)."""
    if len(text) <= width:
        return text
    for sep, keep in ((": ", ":"), (" · ", "")):
        if sep in text:
            a, b = text.split(sep, 1)
            return f"{a}{keep}<br>{b}"
    return text


def _lines(text: str, width: int = 38) -> str:
    """Parte un texto largo del tooltip en renglones para que quepa en un celular."""
    return "<br>".join(textwrap.wrap(text, width, break_on_hyphens=False))


def _text_px(text: str, size: float = 11.5) -> float:
    """Ancho aproximado (px) de un renglón en IBM Plex Sans; calibrado con los rótulos de A.1.5 (±3 px)."""
    em = 0.0
    for ch in text:
        if ch.isupper():
            em += 0.66
        elif ch.isdigit():
            em += 0.6
        elif ch.isalpha():
            em += 0.5
        elif ch in "()[]":
            em += 0.3
        elif ch in "–—":
            em += 0.5
        else:  # espacio, puntuación y el punto medio
            em += 0.25
    return em * size


def _balance(text: str, size: float = 11.5) -> str:
    """Parte un rótulo en los dos renglones más parejos posibles. Un «·» en el corte se va (el salto ya separa)."""
    words = text.split(" ")
    best, best_w = text, _text_px(text, size)
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        a, b = a.removesuffix(" ·"), b.removeprefix("· ")
        if a in ("", "·") or b in ("", "·"):
            continue
        w = max(_text_px(a, size), _text_px(b, size))
        if w < best_w:
            best, best_w = f"{a}<br>{b}", w
    return best


def projections(R: dict) -> go.Figure:
    proj = pd.DataFrame(R["inp"]["proyecciones_trm"])
    group = {"Dic-2026": 0, "2027": 1, "Dic-2027": 1, "1T-2027": 1, "Equilibrio": 2}
    proj["grupo"] = proj["horizonte"].map(group)
    if proj["grupo"].isna().any():
        raise ValueError(f"horizonte sin grupo: {set(proj.loc[proj['grupo'].isna(), 'horizonte'])}")
    proj = proj.assign(grupo=proj["grupo"].astype(int), tipo=proj["tipo"].str.lower())
    proj = proj.sort_values(["grupo", "valor"], ascending=[True, False])
    # En el cierre de 2026 el tipo ya lo dice el encabezado; en los demás grupos se agrega si la entidad no lo trae.
    proj["etiqueta"] = [e if g == 0 or t in e.lower() else f"{e} · {t}"
                        for e, t, g in zip(proj["entidad"], proj["tipo"], proj["grupo"], strict=True)]
    scen = sorted(R["scenarios"], key=lambda s: -s.trm_12m)
    s0, fwd = R["s0"], R["b1"]["forward_1y_val"]
    heads = {0: "Cierre de 2026", 1: "Para 2027", 2: "Valor de equilibrio", 3: "Escenarios propios · oct-2027"}

    lo = min(proj["valor"].min(), min(s.trm_12m for s in scen), s0)
    hi = max(proj["valor"].max(), max(s.trm_12m for s in scen), fwd)
    # a la izquierda, aire para que el «3.000» del eje quepa dentro del lienzo también en el celular
    x0, x1 = lo - 0.12 * (hi - lo), hi + 0.06 * (hi - lo)
    mid = (x0 + x1) / 2

    # Filas de arriba hacia abajo: un encabezado por grupo y una fila por proyección.
    y, rows, head_y = 0.0, {}, {}
    for g in heads:
        y -= 1.3
        head_y[g] = y
        for i in (list(proj.index[proj["grupo"] == g]) if g < 3 else [s.key for s in scen]):
            y -= 1.0
            rows[i] = y
    bottom = y - 0.8
    veil = rgba(C.surface, 0.88)

    def label(v: float, row: float, text: str, gap: int = 9, side: str | None = None) -> dict:
        """Nombre de la fila junto a su punto, hacia el lado con más aire y sobre un velo que tapa líneas y rejilla."""
        side = side or ("left" if v < mid else "right")
        return dict(x=v, y=row, xref="x", yref="y", text=text, showarrow=False, xanchor=side, align=side,
                    xshift=gap if side == "left" else -gap, bgcolor=veil, borderpad=1,
                    font=dict(size=11.5, color=C.ink2))

    # En el celular (lienzo de menos de 330 px) los rótulos se acomodan al más angosto, el de una pantalla de 320 px:
    # 266 px de lienzo con el trazado entre 12 y 250. Cada uno va en un renglón hacia su lado si cabe; si no, en dos
    # (cortado en su «:» o «·», o en los dos renglones más parejos), y solo si tampoco así cabe, hacia el otro lado.
    # Con más ancho, todo cabe con más holgura.
    W, PL, PR = 266, 12, 16

    def fit(v: float, text: str, gap: int) -> tuple[str, str]:
        x = PL + (v - x0) / (x1 - x0) * (W - PL - PR)
        pref = "left" if v < mid else "right"
        other = "right" if pref == "left" else "left"
        cuts = [_wrap(text, 0), _balance(text)]
        for t, side in [(text, pref), *((c, pref) for c in cuts), (text, other), *((c, other) for c in cuts)]:
            room = W - 2 - x - gap if side == "left" else x - gap - 2
            if max(_text_px(s) for s in t.split("<br>")) + 4 <= room:
                return t, side
        return cuts[-1], pref

    fig = go.Figure()
    notes, small = [], []
    market, model = proj[proj["grupo"] < 2], proj[proj["grupo"] == 2]
    for sub, name, marker in (
        (market, "Mercado", dict(size=10, color=C.ocre)),
        (model, "Equilibrio (modelo)", dict(size=10, color=C.surface, line=dict(color=C.ocre, width=2.5))),
    ):
        fig.add_trace(go.Scatter(
            x=sub["valor"], y=[rows[i] for i in sub.index], mode="markers", name=name, marker=marker,
            cliponaxis=False, customdata=sub[["entidad", "horizonte", "tipo", "fecha", "fuente"]].assign(
                fuente=[_lines(f) for f in sub["fuente"]]),
            hovertemplate="<b>%{x:,.0f}</b>  COP por USD<br>%{customdata[0]}<br>%{customdata[1]} · %{customdata[2]}"
                          "<br>publicada: %{customdata[3]}<br>fuente: %{customdata[4]}<extra></extra>",
        ))
        # (en el celular el valor de equilibrio no repite «· modelo»: lo dicen su encabezado y la leyenda)
        for i, v, t, e in zip(sub.index, sub["valor"], sub["etiqueta"], sub["entidad"], strict=True):
            notes.append(label(v, rows[i], _wrap(t)))
            t2, side = fit(v, e if name.startswith("Equilibrio") else t, 9)
            small.append(label(v, rows[i], t2, side=side))
    for s in scen:
        short = s.nombre.split(" ")[0]
        fig.add_trace(go.Scatter(
            x=[s.trm_12m], y=[rows[s.key]], mode="markers", name=short, cliponaxis=False,
            marker=dict(size=13, symbol="diamond", color=SCEN[s.key]),
            hovertemplate=f"<b>%{{x:,.0f}}</b>  COP por USD<br>Escenario {s.nombre.lower()}<br>"
                          "TRM a 12 meses (oct-2027)<extra></extra>",
        ))
        text = f"{short} · {num(s.trm_12m)}"
        notes.append(label(s.trm_12m, rows[s.key], text, gap=11))
        t2, side = fit(s.trm_12m, text, 11)
        small.append(label(s.trm_12m, rows[s.key], t2, gap=11, side=side))

    top = 0.25
    shapes = [dict(type="line", x0=v, x1=v, y0=bottom, y1=top, layer="below",
                   line=dict(color=C.muted, width=1.2, dash=dash)) for v, dash in ((s0, "dash"), (fwd, "dot"))]
    heads_notes = [dict(x=0, xref="paper", y=head_y[g], text=f"<b>{t}</b>", showarrow=False, xanchor="left",
                        align="left", bgcolor=veil, borderpad=2, font=dict(size=12, color=C.ink))
                   for g, t in heads.items()]

    def lines_notes(spot: str, forward: str) -> list[dict]:
        return [dict(x=v, y=top, text=t, showarrow=False, xanchor=side, align=side, yanchor="bottom", bgcolor=veil,
                     borderpad=1, xshift=4 if side == "left" else -4, font=dict(size=11.5, color=C.ink2))
                for v, t, side in ((s0, spot, "right"), (fwd, forward, "left"))]

    notes += heads_notes + lines_notes(f"Spot {num(s0, 2)}", f"Forward 1 año {num(fwd)}")
    # En el celular el spot no cabía a la izquierda de su línea («pot 3.197,65»): los dos rótulos de arriba van en dos
    # renglones, con aire encima. La leyenda deja solo los dos tipos de punto, porque cada rombo ya lleva su nombre al
    # lado; así no ocupa cinco renglones y la gráfica gana alto para los rótulos partidos.
    small += heads_notes + lines_notes(f"Spot<br>{num(s0, 2)}", f"Forward 1 año<br>{num(fwd)}")
    fig.update_layout(shapes=shapes, annotations=notes)
    fig.update_xaxes(title_text="COP por USD", tickformat=",.0f", range=[x0, x1], showgrid=True)
    fig.update_yaxes(visible=False, range=[bottom, top + 1.1], showgrid=False)
    n = len(fig.data)
    narrow(fig, 330, layout={"annotations": small, "height": 760, "yaxis.range": [bottom, top + 1.5]},
           traces={i: {"showlegend": False} for i in range(n - len(scen), n)})
    return _layout(fig, 680)


# Las cuatro piezas de la cuota llevan el mismo color en la amortización (A.2.2), la descomposición (A.3.2) y la
# cascada (A.3.3): el capital es el monto de referencia (gris), el interés el costo pactado (ocre) y el efecto
# cambiario, bermellón sobre el capital y violeta sobre los intereses. El color sigue a la pieza, no a su signo.
CAPITAL, INTEREST, FX_CAPITAL, FX_INTEREST = C.gray, C.ocre, C.verm, C.violet



def _signed(v: float, d: int = 1, plus: str = "+") -> str:
    """Número con signo tipográfico (−, no guion), igual al que Plotly pone en los ejes."""
    if round(v, d) == 0:
        return num(0, d)
    return (plus if v > 0 else "−") + num(abs(v), d)


# ----------------------------------------------------------------------------- A.2
def rate_benchmarks(R: dict) -> go.Figure:
    cred = R["inp"]["credito"]
    refs = cred["referencias"]
    r504 = next(r for r in refs if "504" in r["nombre"])
    r7a = next(r for r in refs if "7(a)" in r["nombre"])
    rng = {("Bancos" if "bancarios" in r["nombre"] else "Pesado"): r for r in refs if "tasa_min" in r}
    chosen = cred["prime"] + cred["spread"]
    spread = num(cred["spread"] * 100, 2)
    points = [
        ("Prime Wells Fargo", cred["prime"], C.gray, cred["fuente_prime"].split(":")[0]),
        ("SBA 504 · 10 años (subsidiada)", r504["tasa"], C.blue, r504["fuente"]),
        (f"Elegida: Prime + {spread} pp", chosen, C.green,
         f"Prime {num(cred['prime'] * 100, 2)}{PCT} + spread {spread} pp"),
        ("Techo SBA 7(a) · USD 50k–250k", r7a["tasa"], C.verm, r7a["fuente"]),
    ]
    ranges = [("Bancos: equipo (rango APR)", rng["Bancos"]), ("Equipo pesado (rango APR)", rng["Pesado"])]
    rows = list(range(len(points))) + [len(points) + 0.35 + i for i in range(len(ranges))]
    fig = go.Figure()
    fig.add_shape(type="line", x0=chosen * 100, x1=chosen * 100, y0=-0.62, y1=rows[-1] + 0.45, layer="below",
                  line=dict(color=C.green, width=1.25, dash="dot"))
    for (name, r), y in zip(ranges, rows[len(points):], strict=True):
        lo, hi = r["tasa_min"] * 100, r["tasa_max"] * 100
        label = f"{num(lo, 0)}{PCT}–{num(hi, 0)}{PCT}"
        fig.add_trace(go.Bar(
            y=[y], x=[hi - lo], base=[lo], orientation="h", width=0.3, showlegend=False,
            marker=dict(color=rgba(C.gray, 0.35), cornerradius=0),
            hovertemplate=f"<b>{label}</b>  {name}<br><i>{_lines(r['fuente'], 44)}</i><extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            y=[y, y], x=[lo, hi], mode="markers+text", showlegend=False, hoverinfo="skip",
            marker=dict(color=C.muted, size=9), text=["", label], textposition="middle right", cliponaxis=False,
            textfont=dict(color=C.ink2, size=12),
        ))
    for (name, rate, color, src), y in zip(points, rows[:len(points)], strict=True):
        main = color == C.green
        fig.add_trace(go.Scatter(
            y=[y], x=[rate * 100], mode="markers+text", showlegend=False,
            marker=dict(color=color, size=15 if main else 12),
            text=[f"<b>{num(rate * 100, 2)}{PCT}</b>" if main else f"{num(rate * 100, 2)}{PCT}"],
            textposition="middle right", cliponaxis=False,
            textfont=dict(color=C.ink if main else C.ink2, size=13 if main else 12),
            hovertemplate=f"<b>%{{x:.2f}}{PCT}</b>  {name}<br><i>{_lines(src, 44)}</i><extra></extra>",
        ))
    labels = [p[0] for p in points] + [r[0] for r in ranges]
    for name, y in zip(labels, rows, strict=True):
        main = name.startswith("Elegida")
        fig.add_annotation(xref="paper", x=0, y=y, yshift=11, xanchor="left", yanchor="bottom", showarrow=False,
                           text=f"<b>{name}</b>" if main else name, align="left", bgcolor=C.surface, borderpad=1,
                           font=dict(size=12.5, color=C.ink if main else C.ink2))
    fig.update_xaxes(title_text="tasa nominal anual", range=[5, 19.2], dtick=2, ticksuffix=PCT, showgrid=True,
                     zeroline=False)
    fig.update_yaxes(range=[rows[-1] + 0.5, -0.75], tickvals=rows, showticklabels=False, showgrid=True,
                     fixedrange=True)
    return _layout(fig, 400, showlegend=False, margin=dict(l=8, r=12, t=8, b=8))


def amortization(R: dict) -> go.Figure:
    s = R["a2"]["schedule"]
    x = pd.to_datetime(s["fecha"])
    period = s["periodo"].to_numpy()
    fig = go.Figure()
    gap = dict(color=C.surface, width=1)
    fig.add_trace(go.Bar(
        x=x, y=s["abono_capital"], name="Abono a capital", yaxis="y2", marker=dict(color=CAPITAL, line=gap),
        hovertemplate="<b>USD %{y:,.2f}</b>  abono a capital<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=x, y=s["interes"], name="Intereses", yaxis="y2", marker=dict(color=INTEREST, line=gap),
        hovertemplate="<b>USD %{y:,.2f}</b>  intereses<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=s["saldo_final"], name="Saldo al cierre", mode="lines", line=dict(color=CAPITAL, width=2.5),
        fill="tozeroy", fillcolor=rgba(CAPITAL, 0.14), customdata=period,
        hovertemplate="<b>USD %{y:,.2f}</b>  saldo al cierre (trim. %{customdata})<extra></extra>",
    ))
    y0, y1 = min(HEDGE_YEARS), max(HEDGE_YEARS)
    i6 = int(np.flatnonzero(s["anio"].to_numpy() == y0)[0]) - 1
    step = (x.iloc[i6 + 1] - x.iloc[i6]) / 2
    fig.add_shape(type="rect", xref="x", yref="paper", x0=x.iloc[i6] + step, x1=x.iloc[-1] + step, y0=0, y1=1,
                  fillcolor=rgba(C.green, 0.1), line_width=0, layer="below")
    fig.add_annotation(xref="x", yref="paper", x=x.iloc[i6] + step, y=1, xanchor="left", yanchor="top", xshift=6,
                       yshift=-4, showarrow=False, align="left", text=f"<b>Años {y0} a {y1}</b><br>con forwards",
                       font=dict(size=11.5, color=C.ink2))
    cuota = float(s["cuota"].iloc[0])
    fig.add_annotation(xref="x", yref="y2", x=x.iloc[0], y=cuota, xanchor="left", yanchor="bottom", xshift=-6,
                       yshift=3, showarrow=False, text=f"Cuota fija: USD {num(cuota, 2)}",
                       font=dict(size=11.5, color=C.ink2))
    bal = float(s["saldo_final"].iloc[i6])
    fig.add_trace(go.Scatter(x=[x.iloc[i6]], y=[bal], mode="markers", marker=dict(color=CAPITAL, size=9),
                             showlegend=False, hoverinfo="skip"))
    fig.add_annotation(xref="x", yref="y", x=x.iloc[i6], y=bal, xanchor="right", yanchor="top", showarrow=False,
                       xshift=-8, yshift=-4, align="right", text=f"Saldo al cierre del año {y0 - 1}<br>USD {num(bal, 0)}",
                       font=dict(size=11.5, color=C.ink2))
    fig.update_layout(
        barmode="stack", hovermode="x unified", hoversubplots="axis", bargap=0.3, legend=dict(traceorder="normal"),
        barcornerradius=0,
        xaxis=dict(anchor="y", type="date", tickformat="%Y", hoverformat="%b %Y", dtick="M24", tick0="2028-01-01",
                   showspikes=True, range=[x.iloc[0] - step * 1.4, x.iloc[-1] + step * 1.4]),
        yaxis=dict(domain=[0, 0.29], title_text="saldo (USD)", tickformat=",.0f", range=[0, 128000], dtick=50000),
        yaxis2=dict(domain=[0.39, 1], anchor="x", title=dict(text="cuota (USD)", standoff=28), tickformat=",.0f",
                    range=[0, 5300], dtick=1000, zeroline=True, zerolinecolor=C.axis, zerolinewidth=1),
    )
    return _layout(fig, 480, margin=dict(l=8, r=12, t=8, b=8))


# La tabla de amortización (Tabla A.2.2) es HTML: tables.amortization.


# ----------------------------------------------------------------------------- A.3
def _band_labels(fan: dict, x_end, x_mid, i: int, floor: float, ceil: float) -> list[dict]:
    """Extremos de la banda exterior y nombre de cada banda escrito dentro de ella (reemplaza su muestra de leyenda).

    ``floor`` es la línea más baja que cruza la banda exterior y ``ceil`` la más alta dentro de la interior en el punto
    ``i``: cada nombre va en el hueco libre de líneas.
    """
    return [
        dict(x=x_end, y=fan[95][-1] / 1e6, text=f"P95: {num(fan[95][-1] / 1e6, 1)}", yanchor="bottom", yshift=2),
        dict(x=x_end, y=fan[5][-1] / 1e6, text=f"P5: {num(fan[5][-1] / 1e6, 1)}", yanchor="top", yshift=-2),
        dict(x=x_mid, y=(fan[5][i] / 1e6 + floor) / 2, text="P5–P95", xanchor="center", yanchor="middle"),
        dict(x=x_mid, y=(ceil + fan[75][i] / 1e6) / 2, text="P25–P75", xanchor="center", yanchor="middle"),
    ]


def cop_installments(R: dict) -> go.Figure:
    a3 = R["a3"]
    dates = pd.to_datetime(a3["base"]["fecha"])
    fig = go.Figure()
    n_fan, band_notes = 0, {}
    edge = dict(color=rgba(C.green, 0.4), width=1)
    x_end = dates.iloc[-1].strftime("%Y-%m-%d")
    # Las bandas se nombran dentro de sí mismas, hacia la mitad del horizonte: sus muestras de leyenda casi no se veían.
    esc = a3["escenarios"]
    i_mid = round(0.55 * (len(dates) - 1))
    x_mid = dates.iloc[i_mid].strftime("%Y-%m-%d")
    lines_low = min(esc[k]["cuota_cop"].iloc[i_mid] for k in ("base", "favorable")) / 1e6
    central_mid = esc["central"]["cuota_cop"].iloc[i_mid] / 1e6
    for dist in DISTS:
        fan = a3["fan"][dist]
        vis = dist == "normal"
        for lo, hi, alpha, label in [(5, 95, 0.08, "P5–P95"), (25, 75, 0.16, "P25–P75")]:
            fig.add_trace(go.Scatter(x=dates, y=fan[hi] / 1e6, line=edge, showlegend=False, hoverinfo="skip",
                                     visible=vis))
            mid = "<br><b>%{customdata[2]:,.2f}</b>  mediana" if lo == 25 else ""
            fig.add_trace(go.Scatter(
                x=dates, y=fan[lo] / 1e6, fill="tonexty", fillcolor=rgba(C.green, alpha), line=edge,
                name=f"Simulación {label}", visible=vis, showlegend=False,
                customdata=np.column_stack([fan[lo], fan[hi], fan[50]]) / 1e6,
                hovertemplate=f"<b>%{{customdata[0]:,.2f}}–%{{customdata[1]:,.2f}}</b>  simulación {label}{mid}"
                "<extra></extra>",
            ))
            n_fan += 2
        floor = min(lines_low, fan[25][i_mid] / 1e6)
        band_notes[dist] = _band_labels(fan, x_end, x_mid, i_mid, floor, central_mid)
    names = {"base": "Spot constante", "favorable": "Favorable", "central": "Central", "adverso": "Adverso"}
    ends = []
    for rank, key in enumerate(("base", "favorable", "central", "adverso")):
        df = a3["escenarios"][key]
        main = key == "central"
        if main:
            fig.add_trace(go.Scatter(x=dates, y=df["cuota_cop"] / 1e6, mode="lines", showlegend=False,
                                     hoverinfo="skip", line=dict(color=C.surface, width=6)))
        fig.add_trace(go.Scatter(
            x=dates, y=df["cuota_cop"] / 1e6, name=names[key], mode="lines", legendrank=100 + rank,
            line=dict(color=SCEN[key], width=2.5 if main else 2, dash="dash" if key == "base" else "solid"),
            customdata=df["trm"],
            hovertemplate="<b>%{y:,.2f}</b>  " + names[key].lower() + " · TRM %{customdata:,.0f}<extra></extra>",
        ))
        if key in ("central", "adverso"):
            v = df["cuota_cop"].iloc[-1] / 1e6
            end = dict(x=x_end, y=v, text=f"{key.capitalize()}: {num(v, 1)}", yanchor="bottom", yshift=4)
            if key == "adverso":
                # En un celular el borde P95 cruza este rótulo: un velo de la superficie lo tapa.
                end.update(bgcolor=rgba(C.surface, 0.85), borderpad=1)
            ends.append(end)
    n = len(fig.data)
    lines = list(range(n_fan, n))

    def notes(dist: str) -> list[dict]:
        base = dict(xref="x", yref="y", xanchor="right", showarrow=False, font=dict(size=11.5, color=C.ink2))
        return [base | a for a in band_notes[dist] + ends]

    buttons = [
        dict(label=f"Innovaciones {'normales' if d == 'normal' else DISTS[d]}", method="update",
             args=[{"visible": _visible(n, list(range(4 * i, 4 * i + 4)) + lines)}, {"annotations": notes(d)}])
        for i, d in enumerate(DISTS)
    ]
    # Las bandas con relleno «tonexty» hacen que Plotly invierta la leyenda por defecto.
    fig.update_layout(updatemenus=_menu(buttons), annotations=notes("normal"), hovermode="x unified",
                      legend=dict(traceorder="normal"))
    fig.update_xaxes(type="date", tickformat="%Y", hoverformat="%b %Y · COP millones", showspikes=True,
                     range=[dates.iloc[0] - pd.Timedelta(days=40), dates.iloc[-1] + pd.Timedelta(days=40)])
    fig.update_yaxes(title_text="cuota trimestral (COP millones)", tickformat=",.0f", range=[7, 37], dtick=5)
    return _layout(fig, 500, margin=dict(l=8, r=12, t=8, b=8))


def decomposition(R: dict) -> go.Figure:
    a3 = R["a3"]["escenarios"]
    # Los mismos botones que la cascada (A.3.3), que va al lado.
    keys = ["base", "favorable", "central", "adverso"]
    labels = {"base": "Spot constante", "favorable": "Favorable", "central": "Central", "adverso": "Adverso"}
    comps = [("capital_s0", "Capital a TRM base"), ("interes_s0", "Interés a TRM base"),
             ("fx_capital", "Efecto cambiario s/ capital"), ("fx_interes", "Efecto cambiario s/ interés")]
    gap = dict(color=C.surface, width=1)
    fig = go.Figure()
    lo, hi = 0.0, 0.0
    for key in keys:
        df = a3[key]
        dates = pd.to_datetime(df["fecha"])
        colors = [CAPITAL, INTEREST, FX_CAPITAL, FX_INTEREST]
        for j, ((col, name), color) in enumerate(zip(comps, colors, strict=True)):
            tail = "<br><b>%{customdata[1]:,.2f}</b>  cuota total" if j == len(comps) - 1 else ""
            fig.add_trace(go.Bar(
                x=dates, y=df[col] / 1e6, name=name, marker=dict(color=color, line=gap), visible=key == "central",
                customdata=[[_signed(v / 1e6, 2, ""), c / 1e6] for v, c in zip(df[col], df["cuota_cop"], strict=True)],
                hovertemplate=f"<b>%{{customdata[0]}}</b>  {name[0].lower() + name[1:]}{tail}<extra></extra>",
            ))
        lo = min(lo, float((df["fx_capital"].clip(upper=0) + df["fx_interes"].clip(upper=0)).min()) / 1e6)
        hi = max(hi, float(df["cuota_cop"].max()) / 1e6)
    n = len(fig.data)
    buttons = [dict(label=labels[k], method="update", args=[{"visible": _visible(n, list(range(4 * i, 4 * i + 4)))}])
               for i, k in enumerate(keys)]
    menu = _menu(buttons)
    menu[0]["active"] = keys.index("central")
    # Sin esquinas redondeadas: en una barra apilada el redondeo solo deforma el último segmento.
    fig.update_layout(updatemenus=menu, barmode="relative", bargap=0.25, hovermode="x unified", barcornerradius=0)
    fig.update_xaxes(type="date", tickformat="%Y", hoverformat="%b %Y · COP millones", showspikes=True, showline=False,
                     ticks="")
    fig.update_yaxes(title_text="COP millones por trimestre", tickformat=",.0f", range=[lo * 1.6, hi * 1.04], dtick=5,
                     zeroline=True, zerolinecolor=C.axis, zerolinewidth=1)
    return _layout(fig, 470, margin=dict(l=8, r=10, t=8, b=8))


def waterfall(R: dict) -> go.Figure:
    summ = R["a3"]["summary"].set_index("key")
    keys = ["base", "favorable", "central", "adverso"]
    labels = {"base": "Spot constante", "favorable": "Favorable", "central": "Central", "adverso": "Adverso"}
    # Mismo orden que la fórmula, el texto y el apilado de la descomposición (A.3.2): capital antes que interés.
    steps = ["Capital desembolsado", "Interés a TRM base", "Efecto cambiario s/ capital",
             "Efecto cambiario s/ interés", "Total pagado en pesos"]
    rows = np.arange(len(steps))
    fin = R["a2"]["financed_cop"]
    fig = go.Figure()
    top = 0.0
    for key in keys:
        r = summ.loc[key]
        deltas = [fin, r["interes_s0"], r["fx_capital"], r["fx_interes"]]
        start = np.concatenate([[0.0], np.cumsum(deltas)[:-1]])
        total = float(sum(deltas))
        top = max(top, total, float(np.max(np.cumsum(deltas))))
        cost = float(r["costo_financiero"])
        share = ["", *(f"<br>{_signed(100 * d / cost)}{PCT} del costo financiero" if cost else "" for d in deltas[1:])]
        share.append(f"<br>costo financiero {num(cost / 1e6, 1)} millones")
        values = deltas + [total]
        text = [num(fin / 1e6, 1)] + [_signed(d / 1e6) for d in deltas[1:]]
        text.append(f"<b>{num(total / 1e6, 1)}</b>")
        fig.add_trace(go.Bar(
            y=rows, x=[d / 1e6 for d in deltas] + [total / 1e6], base=[s / 1e6 for s in start] + [0.0],
            orientation="h", width=0.32, visible=key == "central", name=labels[key], showlegend=False,
            # El total va en un neutro medio: el color del texto (C.ink2) quedaba como una losa clara en modo oscuro.
            marker=dict(color=[CAPITAL, INTEREST, FX_CAPITAL, FX_INTEREST, C.muted], cornerradius=3),
            text=text, textposition="outside", cliponaxis=False, textfont=dict(color=C.ink2, size=12.5),
            customdata=[[f"COP {_signed(v / 1e6) if 0 < i < len(deltas) else num(v / 1e6, 1)} millones", step + sh]
                        for i, (v, step, sh) in enumerate(zip(values, steps, share, strict=True))],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
        ))
        ends = np.cumsum(deltas) / 1e6
        cx, cy = [], []
        for i, e in enumerate(ends):
            cx += [e, e, None]
            cy += [i + 0.16, i + 0.84, None]
        fig.add_trace(go.Scatter(x=cx, y=cy, mode="lines", line=dict(color=C.muted, width=1), hoverinfo="skip",
                                 showlegend=False, visible=key == "central"))
    n = len(fig.data)
    buttons = [dict(label=labels[k], method="update", args=[{"visible": _visible(n, [2 * i, 2 * i + 1])}])
               for i, k in enumerate(keys)]
    menu = _menu(buttons)
    menu[0]["active"] = keys.index("central")
    for i, step in enumerate(steps):
        last = i == len(steps) - 1
        fig.add_annotation(xref="paper", x=0, y=i, yshift=16, xanchor="left", yanchor="bottom", showarrow=False,
                           text=f"<b>{step}</b>" if last else step, bgcolor=C.surface, borderpad=1,
                           font=dict(size=12, color=C.ink if last else C.ink2))
    fig.update_layout(updatemenus=menu, showlegend=False)
    # Sin título en el eje X (la unidad está en el pie): así su eje queda a la altura del de la descomposición.
    fig.update_xaxes(tickformat=",.0f", range=[0, top / 1e6 * 1.2], showgrid=True)
    fig.update_yaxes(range=[len(steps) - 0.5, -0.85], tickvals=rows, showticklabels=False, showgrid=False,
                     fixedrange=True)
    return _layout(fig, 470, margin=dict(l=8, r=12, t=8, b=8))


_TENOR_MONTHS = {"1M": "1", "3M": "3", "6M": "6", "1Y": "12", "3Y": "36"}
_DIST_VIEWS = (("normal", "Innovaciones normales"), ("t", "Innovaciones t de Student"))


def _direct_label(x, y, text, **kw) -> dict:
    """Etiqueta directa en texto neutro (nunca en el color de la serie)."""
    base = dict(x=x, y=y, text=text, showarrow=False, font=dict(size=11.5, color=C.ink2))
    base.update(kw)
    return base


# ----------------------------------------------------------------------------- B.1
def forward_curve(R: dict) -> go.Figure:
    b1 = R["b1"]
    c, t, cip = b1["curve"], b1["theo_curve"], b1["cip"]
    x = c["dias"].to_numpy()
    tenor = [_TENOR_MONTHS.get(p, p) for p in c["plazo"]]
    date = fecha(R["inp"]["forward_mercado"]["fecha_cotizacion"])

    def parity_dev(tag: str) -> np.ndarray:
        return np.full(len(x), float(cip.loc[cip["par"].str.contains(tag), "dev"].iloc[0]) * 100)

    series = [
        ("Paridad BanRep–SOFR", t["banrep_sofr"].to_numpy(), parity_dev("BanRep"), C.blue, "dash", 2),
        ("Paridad IBR–swap SOFR", t["ibr_swap"].to_numpy(), parity_dev("IBR"), C.ocre, "dot", 3),
        (f"Mercado (Itaú, {date})", c["puntos"].to_numpy(), c["dev"].to_numpy() * 100, C.green, "solid", 1),
    ]
    mkt_pts = c["puntos"].to_numpy()
    fig = go.Figure()
    # En puntos las tres curvas van casi una encima de otra (las brechas son de unos pesos en un eje de 0 a 800): la
    # segunda vista muestra la brecha misma, mercado − paridad, con el cero como la paridad. El color y el trazo siguen
    # a cada paridad, como en la vista de devaluación.
    for name, pts, _, color, dash, rank in series[:2]:
        gap = mkt_pts - pts
        fig.add_trace(go.Scatter(
            x=x, y=gap, name="Mercado − " + name[0].lower() + name[1:], mode="lines+markers", legendrank=rank,
            visible=False, customdata=[_signed(v, 2) for v in gap],
            line=dict(color=color, width=2, dash=dash), marker=dict(size=7, color=color),
            hovertemplate="<b>%{customdata}</b> pesos · mercado − " + name[0].lower() + name[1:] + "<extra></extra>",
        ))
    for name, _, dev, color, dash, rank in series:
        market = rank == 1
        fig.add_trace(go.Scatter(
            x=x, y=dev, name=name, mode="lines+markers" if market else "lines", legendrank=rank,
            line=dict(color=color, width=2.5 if market else 2, dash=dash), marker=dict(size=8, color=color),
            hovertemplate=f"<b>%{{y:.2f}}{PCT}</b> · " + name.split(" (")[0] + "<extra></extra>",
        ))
    i1y = int(np.flatnonzero(c["plazo"].to_numpy() == "1Y")[0])
    x1y = float(np.log10(x[i1y]))
    gap1y = float(mkt_pts[i1y] - t["banrep_sofr"].iloc[i1y])
    notes = {
        # a la derecha del punto: a su izquierda pasan las dos rectas que suben hacia los 12 meses
        "diff": [_direct_label(x1y, gap1y, f"{_signed(gap1y, 2)} a 1 año", xanchor="left", yanchor="bottom",
                               xshift=6, yshift=2)],
        "dev": [_direct_label(x1y, float(c["dev"].iloc[i1y] * 100),
                              f"{num(c['dev'].iloc[i1y] * 100, 2)}{PCT} a 1 año", yanchor="bottom", yshift=10)],
    }
    n = len(fig.data)
    fig.update_layout(updatemenus=_menu([
        dict(label="Devaluación implícita", method="update", args=[
            {"visible": _visible(n, [2, 3, 4])},
            {"annotations": notes["dev"], "yaxis.title.text": "devaluación implícita anual", "yaxis.ticksuffix": PCT,
             "yaxis.tickformat": ".1f", "yaxis.autorange": True}]),
        dict(label="Diferencia en pesos", method="update", args=[
            {"visible": _visible(n, [0, 1])},
            {"annotations": notes["diff"], "yaxis.title.text": "mercado − paridad (COP)", "yaxis.ticksuffix": "",
             "yaxis.tickformat": ",.0f", "yaxis.autorange": True}]),
    ]), annotations=notes["dev"])
    fig.update_xaxes(title_text="plazo en meses (escala logarítmica)", type="log", tickvals=list(x), ticktext=tenor,
                     tickangle=0, showspikes=True, unifiedhovertitle=dict(text="Plazo de %{x:,.0f} días calendario"))
    # La línea del cero (mercado = paridad) solo cae dentro del rango en la vista de diferencias. No va como forma:
    # una forma entraría en el rango automático y aplastaría la vista de devaluación.
    fig.update_yaxes(title_text="devaluación implícita anual", ticksuffix=PCT, tickformat=".1f", rangemode="normal",
                     zeroline=True, zerolinecolor=C.muted, zerolinewidth=1)
    return _layout(fig, 420, hovermode="x unified")


def cip_heatmap(R: dict) -> go.Figure:
    b1 = R["b1"]
    h, cip = b1["heat"], b1["cip"]
    rc, ru, z = np.asarray(h["rc"]) * 100, np.asarray(h["ru"]) * 100, np.asarray(h["z"])
    fig = go.Figure(go.Heatmap(
        x=rc, y=ru, z=z, colorscale=SEQ, zsmooth="best",
        colorbar=dict(orientation="h", x=0, xanchor="left", y=1.035, yanchor="bottom", ypad=0, len=0.62, thickness=9,
                      tickformat=",.0f", nticks=4, title=dict(text="forward teórico a 1 año (COP por USD)", side="top")),
        hovertemplate=f"<b>%{{z:,.0f}}</b> forward teórico<br>Tasa COP %{{x:.2f}}{PCT} · tasa USD %{{y:.2f}}{PCT}"
                      "<extra></extra>",
    ))
    inside = cip[cip["r_cop"].between(rc.min() / 100, rc.max() / 100)
                 & cip["r_usd"].between(ru.min() / 100, ru.max() / 100)]
    short = {"BanRep": "BanRep–SOFR", "IBR": "IBR–swap", "TES": "TES–Tesoro"}
    fig.add_trace(go.Scatter(
        x=inside["r_cop"] * 100, y=inside["r_usd"] * 100, mode="markers", showlegend=False,
        marker=dict(size=10, color=C.surface, line=dict(color=C.ink, width=2)),
        customdata=np.c_[inside["forward_val"], inside["par"]],
        hovertemplate="<b>%{customdata[0]:,.0f}</b> forward teórico<br>%{customdata[1]}<extra></extra>",
    ))
    small = []
    for _, row in inside.iterrows():
        label = next((v for k, v in short.items() if k in row["par"]), row["par"])
        note = dict(x=row["r_cop"] * 100, y=row["r_usd"] * 100, showarrow=True, ax=-16, ay=0, xanchor="right",
                    arrowcolor=C.ink2, bgcolor=C.surface, font=dict(size=11, color=C.ink), borderpad=3)
        fig.add_annotation(text=f"{label} {num(row['forward_val'])}", **note)
        small.append(dict(note, text=f"{label}<br>{num(row['forward_val'])}", align="right"))
    # Sin línea de eje, los rótulos se separan del mapa (si no, «3,50 %» y «10 %» se montan en la esquina).
    fig.update_xaxes(title_text="tasa en pesos (E.A.)", ticksuffix=PCT, tickformat=".0f", dtick=1, showline=False,
                     ticks="", ticklabelstandoff=6)
    fig.update_yaxes(title_text="tasa en dólares (E.A.)", ticksuffix=PCT, tickformat=".2f", dtick=0.25, showgrid=False,
                     ticklabelstandoff=6)
    # En el lienzo angosto los rótulos de una línea no cabían a la izquierda de su punto y el autorango del eje x
    # abría una franja vacía a la izquierda del mapa (con una marca de «9 %» sobre nada). En dos renglones caben
    # dentro, el eje queda fijo en la extensión del mapa (10 % a 13 %) y la barra de color se alarga para que sus
    # cifras no se inclinen.
    half = float(rc[1] - rc[0]) / 2 if len(rc) > 1 else 0.0
    narrow(fig, 330, layout={"annotations": small, "xaxis.range": [float(rc.min()) - half, float(rc.max()) + half],
                             "xaxis.autorange": False},
           traces={0: {"colorbar.len": 0.9}})
    # 462 px: su pareja (B.1.1) lleva encima la fila de botones; así los dos ejes x y los dos pies quedan a la par.
    # r = 18: la marca «13 %» cae en el borde derecho del mapa y la mitad del rótulo sale del trazado; con r = 10 Plotly
    # la escondía en los lienzos angostos (celular, y la ficha de 1.181 px a 3 columnas).
    return _layout(fig, 462, margin=dict(autoexpand=False, t=66, l=84, b=46, r=18))


def forwards_valuation(R: dict) -> go.Figure:
    per = R["b2"][("central", "normal")]["per"]
    base = np.arange(len(per), dtype=float)
    contract = [f"Forward {i + 1}, año {y}" for i, y in enumerate(per["anio"])]
    fig = go.Figure()
    # La tasa pactada va a la derecha de cada par: sus extremos se rotulan en el hueco hasta el par siguiente, lejos de
    # las marcas del eje Y.
    w = 0.11
    series = (("spot_t", "TRM al vencimiento", HEDGE["sin"], -0.1), ("forward", "Tasa pactada F", HEDGE["con"], 0.1))
    for col, name, color, off in series:
        lo, mid, hi = per[f"{col}_p5"].to_numpy(), per[f"{col}_media"].to_numpy(), per[f"{col}_p95"].to_numpy()
        # El rango P5–P95 es el mensaje del texto: barra de intervalo con borde, no una sombra.
        fig.add_trace(go.Bar(
            x=base + off, y=hi - lo, base=lo, width=w, name=name, legendgroup=name, showlegend=False,
            marker=dict(color=rgba(color, 0.26), line=dict(color=color, width=1), cornerradius=0),
            customdata=np.c_[mid, lo, hi, contract],
            hovertemplate="<b>%{customdata[0]:,.0f}</b> media · " + name + "<br>%{customdata[3]}"
                          + "<br>P5–P95: %{customdata[1]:,.0f} a %{customdata[2]:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=base + off, y=mid, mode="markers", name=f"{name} (media y rango P5–P95)", legendgroup=name,
            marker=dict(size=10, color=color), hoverinfo="skip",
        ))
    # Extremos del primer forward (las cifras del texto), pegados a la esquina derecha de su barra.
    edge, hi, lo = base[0] + series[1][3] + w / 2, per["forward_p95"].iloc[0], per["forward_p5"].iloc[0]
    side = dict(xanchor="left", align="left", xshift=5)
    notes = [_direct_label(edge, hi, f"P95<br>{num(hi)}", yanchor="top", **side),
             _direct_label(edge, lo, f"P5<br>{num(lo)}", yanchor="bottom", **side)]
    ends = per[["forward_p5", "spot_t_p5", "forward_p95", "spot_t_p95"]].to_numpy()
    span = ends.max() - ends.min()
    fig.update_xaxes(title_text="año de vencimiento de cada forward", tickvals=base,
                     ticktext=[f"Año {y}" for y in per["anio"]], range=[-0.55, len(per) - 0.5], ticks="",
                     tickangle=0)
    fig.update_yaxes(title_text="COP por USD", tickformat=",.0f",
                     range=[ends.min() - 0.06 * span, ends.max() + 0.04 * span])
    return _layout(fig, 420, annotations=notes, barmode="overlay")


# ----------------------------------------------------------------------------- B.2
def ratio_hist(R: dict) -> go.Figure:
    bins = np.linspace(-0.6, 0.8, 71)
    centers = (bins[:-1] + bins[1:]) / 2 * 100
    fig = go.Figure()
    peak = 0.0
    dots = []
    for dist in DISTS:
        x = np.asarray(R["ratio_hist"][dist])
        h, _ = np.histogram(np.clip(x, bins[0], bins[-1] - 1e-9), bins=bins)
        y = h / len(x) * 100
        peak = max(peak, y.max())
        # Los tramos aislados solo se ven con un punto; en escala lineal parecen ruido sobre el cero, así que el
        # punto aparece únicamente en la escala logarítmica (tamaños por traza en los botones).
        alone = (h > 0) & (np.r_[0, h[:-1]] == 0) & (np.r_[h[1:], 0] == 0)
        dots.append(np.where(alone, 6, 0).tolist())
        # El recorte amontona en los tramos extremos lo que cae fuera de la escala: el tooltip lo avisa.
        clip = [""] * len(h)
        if (x >= bins[-1]).any():
            clip[-1] = f"<br>incluye lo que pasa de {_signed(bins[-1] * 100, 0, '')}{PCT}"
        if (x < bins[0]).any():
            clip[0] = f"<br>incluye lo que baja de {_signed(bins[0] * 100, 0, '')}{PCT}"
        fig.add_trace(go.Scatter(
            x=centers, y=np.where(h > 0, y, np.nan), name=DISTS[dist], mode="lines+markers",
            line=dict(color=DIST[dist], width=2, shape="hvh"),
            marker=dict(size=[0] * len(h), color=DIST[dist], line=dict(width=0)), customdata=clip,
            # cifras significativas: en las colas de la vista logarítmica (0,0025 %) dos decimales darían «0,00 %»
            hovertemplate=f"<b>%{{y:.2r}}{PCT}</b> de los escenarios · {DISTS[dist]}%{{customdata}}<extra></extra>",
        ))
    # El pico llega al 66 % del alto en las dos escalas. Las líneas de ±20 % y 0 terminan justo encima y los rótulos de
    # en medio van debajo de los de las bandas (que ocupan tres renglones desde arriba): en el celular la zona central
    # mide unos 75 px y esos rótulos se salen hacia las bandas, pero en otra altura y sin que ninguna línea los cruce.
    head, y_mid = 0.66, 0.81
    for xv, dash, color in ((-20, "dash", C.muted), (0, "solid", C.ink2), (20, "dash", C.muted)):
        fig.add_shape(type="line", x0=xv, x1=xv, y0=0, y1=head + 0.02, yref="paper",
                      line=dict(color=color, width=1, dash=dash), layer="below")
    fig.add_vrect(x0=bins[0] * 100, x1=-20, fillcolor=rgba(C.gray, 0.1), line_width=0, layer="below")
    fig.add_vrect(x0=20, x1=bins[-1] * 100, fillcolor=rgba(C.gray, 0.1), line_width=0, layer="below")
    lab = dict(yref="paper", yanchor="top")
    fig.update_layout(annotations=[
        _direct_label(bins[0] * 100, 0.99, "Pérdida<br>extrema del<br>derivado", xanchor="left", align="left",
                      xshift=4, **lab),
        _direct_label(20, 0.99, "Pérdida<br>cambiaria<br>extrema evitada", xanchor="left", align="left", xshift=4,
                      **lab),
        _direct_label(-1.5, y_mid, "← Costo de<br>oportunidad", xanchor="right", align="right", **lab),
        _direct_label(1.5, y_mid, "Protección →", xanchor="left", **lab),
    ])
    top = float(peak / head)
    lo = np.log10(100 / len(R["ratio_hist"]["normal"])) - 0.3
    lo, hi = float(lo), float(lo + (np.log10(peak) - lo) / head)
    # En la escala lineal la rejilla llega solo hasta el pico: encima van los rótulos y la línea siguiente los tachaba.
    # (En la logarítmica la del 10 % queda debajo de ellos.)
    step = next(s for s in (1, 2, 5, 10, 20) if top / s <= 6)
    lin_ticks = [float(v) for v in np.arange(0, peak + 1e-9, step)]
    linear = {"yaxis.type": "linear", "yaxis.range": [0, top], "yaxis.tickmode": "array", "yaxis.tickvals": lin_ticks,
              "yaxis.ticktext": [f"{num(v, 0)}{PCT}" for v in lin_ticks]}
    fig.update_layout(updatemenus=_menu([
        dict(label="Escala lineal", method="update", args=[{"marker.size": [[0] * len(d) for d in dots]}, linear]),
        dict(label="Escala logarítmica", method="update", args=[
            {"marker.size": dots},
            {"yaxis.type": "log", "yaxis.range": [lo, hi], "yaxis.tickmode": "array",
             "yaxis.tickvals": [0.001, 0.01, 0.1, 1, 10],
             "yaxis.ticktext": [f"{num(v, d)}{PCT}" for v, d in ((0.001, 3), (0.01, 2), (0.1, 1), (1, 0), (10, 0))]}]),
    ]))
    fig.update_xaxes(title_text="TRM al vencimiento frente a<br>la tasa pactada (S<sub>T</sub>/F − 1)", ticksuffix=PCT,
                     range=[bins[0] * 100, bins[-1] * 100], tickangle=0, showspikes=True,
                     unifiedhovertitle=dict(text=f"S<sub>T</sub>/F − 1 ≈ %{{x:.0f}}{PCT}"))
    fig.update_yaxes(title_text="% de escenarios", ticksuffix=PCT, range=[0, top], exponentformat="none",
                     tickmode="array", tickvals=lin_ticks, ticktext=linear["yaxis.ticktext"])
    return _layout(fig, 460, hovermode="x unified")


def proportions(R: dict) -> go.Figure:
    metrics = [("proteccion", "Protección (S<sub>T</sub> > F)"),
               ("costo_oportunidad", "Costo de oportunidad (S<sub>T</sub> &lt; F)"),
               ("extrema_exposicion", "Pérdida cambiaria extrema (S<sub>T</sub> > 1,2F)"),
               ("extrema_derivado", "Pérdida extrema del derivado (S<sub>T</sub> &lt; 0,8F)"),
               ("fracaso", "Fracaso por desfase")]
    keys = ["favorable", "central", "adverso", "neutral"]
    names = {s.key: s.nombre for s in R["scenarios"]} | {"neutral": "Neutral al riesgo"}
    step = len(keys) + 1.7
    fig = go.Figure()
    top = 0.0
    for dist, _ in _DIST_VIEWS:
        for j, key in enumerate(keys):
            pooled = R["b2"][(key, dist)]["pooled"]
            v = np.array([pooled[m] * 100 for m, _ in metrics])
            top = max(top, v.max())
            fig.add_trace(go.Bar(
                y=[i * step + j for i in range(len(metrics))], x=v, orientation="h", name=names[key],
                marker_color=SCEN[key], visible=dist == "normal", width=0.74, customdata=[lbl for _, lbl in metrics],
                text=[f"{num(x, 1)} %" for x in v] if key == "central" else None, textposition="outside",
                constraintext="none", cliponaxis=False,
                hovertemplate="<b>%{x:.1f} %</b> de los escenarios<br>" + names[key] + " · %{customdata}<extra></extra>",
            ))
    n = len(fig.data)
    fig.update_layout(updatemenus=_menu([
        dict(label=lab, method="update", args=[{"visible": _visible(n, list(range(k * 4, k * 4 + 4)))}])
        for k, (_, lab) in enumerate(_DIST_VIEWS)
    ]), annotations=[
        _direct_label(0, i * step - 0.65, lbl, xref="paper", xanchor="left", yanchor="bottom",
                      font=dict(size=12.5, color=C.ink))
        for i, (_, lbl) in enumerate(metrics)
    ])
    fig.update_yaxes(showticklabels=False, showgrid=False, showline=True, linecolor=C.axis,
                     range=[(len(metrics) - 1) * step + len(keys) - 0.4, -2.1])
    fig.update_xaxes(title_text="% de escenarios (promedio de los cuatro forwards)", ticksuffix=" %", showgrid=True,
                     showline=False, range=[0, top * 1.12], dtick=10)
    return _layout(fig, 560, margin=dict(l=22))


def budget_scatter(R: dict) -> go.Figure:
    s = R["scatter"]
    gain, above = s["payoff"] > 0, s["above"]
    # Un color por desenlace que no signifique otra cosa en B.2 (el bermellón y el violeta ya son los escenarios adverso
    # y neutral del Gráfico B.2.2; el ocre y el magenta, las distribuciones de B.2.1 y B.2.5). Los dos desenlaces en
    # que la cobertura cumple van en dos verdes de la escala secuencial, el verde de «con forward» en B.2.3; los dos del
    # desfase, en tinta: punto lleno para el fracaso y aro para la sobrecompensación. La tinta queda en el extremo de
    # luminosidad en los dos modos (casi negra en claro, casi blanca en oscuro), así que se separa de los dos verdes
    # también con daltonismo. Entre sí se distinguen por el relleno: el aro va opaco y relleno de papel, así que en la
    # cuña angosta del celular, donde se apilan cientos, cada aro tapa el centro del anterior y el montón se sigue
    # leyendo como burbujas, no como una mancha igual a la de los puntos llenos (que van encima, de último). Un aro
    # hueco y translúcido se volvía ahí una mancha de tinta indistinguible del fracaso.
    groups = [
        ("Protección efectiva", gain & above, SEQ[5][1], "circle"),
        ("Costo de oportunidad", ~gain & ~above, SEQ[3][1], "circle"),
        ("Sobrecompensación", gain & ~above, C.ink, "ring"),
        ("Fracaso por desfase", ~gain & above, C.ink, "circle"),
    ]
    xr, yr = (-30, 35), (-20, 20)
    fig = go.Figure()
    fig.add_hline(y=0, line=dict(color=C.axis, width=1), layer="below")
    fig.add_vline(x=0, line=dict(color=C.axis, width=1), layer="below")
    for name, mask, color, symbol in groups:
        if symbol == "ring":
            mk = dict(size=6, color=C.surface, opacity=1, line=dict(width=1, color=color))
            key = dict(size=9, color=C.surface, line=dict(width=1.6, color=color))
        else:
            mk = dict(size=5, color=color, opacity=0.85 if color == C.ink else 0.5, line=dict(width=0))
            key = dict(size=9, color=color, line=dict(width=0))
        u, h = s["u"][mask] * 100, s["h"][mask] * 100
        fig.add_trace(go.Scatter(
            x=u, y=h, mode="markers", name=name, legendgroup=name, showlegend=False,
            marker=dict(symbol="circle", **mk), customdata=np.c_[_pcts(h), _pcts(u)],
            hovertemplate="<b>%{customdata[0]}</b> con cobertura · %{customdata[1]} sin cobertura<br>" + name
                          + "<extra></extra>",
        ))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=name, legendgroup=name, hoverinfo="skip",
                                 marker=dict(symbol="circle", **key)))
    # Las dos rectas de referencia llevan rótulo directo y no entran en la leyenda: en el celular la partían en seis
    # renglones y le quitaban un tercio de alto a la nube.
    for k, dash, color, tag in ((1.0, "dash", C.muted, "sin cobertura · y = x"),
                                (0.25, "dot", C.ink2, "cobertura ideal<br>y = 0,25x")):
        xx = np.array([max(xr[0], yr[0] / k), min(xr[1], yr[1] / k)])
        fig.add_trace(go.Scatter(x=xx, y=k * xx, mode="lines", showlegend=False, hoverinfo="skip",
                                 line=dict(color=color, width=1.5, dash=dash)))
        # El de la recta ideal va pegado al borde derecho: en el celular así no toca la diagonal.
        at = xx[1] if k < 1 else 0.7 * xx[1]
        fig.add_annotation(_direct_label(at, k * at, tag, xanchor="right", align="right", yanchor="bottom", yshift=4,
                                         xshift=-6 if k == 1 else -1, bgcolor=rgba(C.surface, 0.85), borderpad=1))
    fig.update_xaxes(title_text="desviación presupuestal sin cobertura", range=xr, ticksuffix=PCT, showgrid=True)
    fig.update_yaxes(title_text="desviación con cobertura", range=yr, ticksuffix=PCT, dtick=10)
    # x apenas negativa y letra de 11,5 (la de los rótulos): la leyenda usa también el margen izquierdo y en el celular
    # queda en dos renglones con holgura (con 12,5 quedaba justo en el límite y a veces se partía en cuatro).
    return _layout(fig, 500, legend=dict(x=-0.002, font=dict(size=11.5)))


def _loose_segments(x0, x1, y0, y1) -> tuple[list, list]:
    """Segmentos sueltos en una sola traza, separados por None."""
    xs, ys = [], []
    for a, b, c, d in zip(x0, x1, y0, y1, strict=True):
        xs += [float(a), float(b), None]
        ys += [float(c), float(d), None]
    return xs, ys


def _pcts(values, d: int = 1) -> list[str]:
    """Porcentajes ya escritos, con signo menos tipográfico: el tooltip de un solo punto es una caja que Plotly mide
    con el texto que le llega y no se ensancha después, así que el «−» no puede cambiarse en el navegador."""
    return [num(v, d) + PCT for v in np.asarray(values, dtype=float)]


def _box_marks(fig: go.Figure, x: np.ndarray, st: dict, name: str, color: str, visible: bool, w: float = 0.22) -> None:
    """Caja P25–P75 con bigotes P5–P95, mediana gruesa y media punteada; un solo tooltip por caja."""
    p5, q1, med, q3, p95, mean = (np.asarray(st[k]) * 100 for k in (5, 25, 50, 75, 95, "mean"))
    cap, half = w * 0.22, w / 2
    wx, wy = _loose_segments(np.r_[x, x, x - cap, x - cap], np.r_[x, x, x + cap, x + cap], np.r_[p5, q3, p5, p95],
                       np.r_[q1, p95, p5, p95])
    common = dict(visible=visible, legendgroup=name, showlegend=False, hoverinfo="skip")
    fig.add_trace(go.Scatter(x=wx, y=wy, mode="lines", line=dict(color=color, width=1.5), **common))
    fig.add_trace(go.Bar(x=x, y=q3 - q1, base=q1, width=w, name=name, visible=visible, legendgroup=name,
                         hoverinfo="skip",
                         marker=dict(color=rgba(color, 0.18), line=dict(color=color, width=1.5), cornerradius=0)))
    for y, width, dash in ((med, 2.5, "solid"), (mean, 1.2, "dot")):
        sx, sy = _loose_segments(x - half, x + half, y, y)
        fig.add_trace(go.Scatter(x=sx, y=sy, mode="lines", line=dict(color=color, width=width, dash=dash), **common))
    fig.add_trace(go.Bar(
        x=x, y=p95 - p5, base=p5, width=w, visible=visible, legendgroup=name, showlegend=False,
        marker=dict(color="rgba(0,0,0,0)"),
        customdata=np.c_[_pcts(med), _pcts(q1), _pcts(q3), _pcts(p5), _pcts(p95), _pcts(mean)],
        hovertemplate="<b>%{customdata[0]}</b> mediana · " + name + "<br>P25–P75: %{customdata[1]} a "
                      "%{customdata[2]}<br>P5–P95: %{customdata[3]} a %{customdata[4]}<br>Media: "
                      "%{customdata[5]}<extra></extra>",
    ))


def budget_box(R: dict) -> go.Figure:
    fig = go.Figure()
    x = np.arange(len(HEDGE_YEARS), dtype=float)
    for dist, _ in _DIST_VIEWS:
        bd = R["budget_box"][dist]
        for strat, label, key, off in (("u", "Sin cobertura", "sin", -0.17), ("h", "Con forward 75 %", "con", 0.17)):
            _box_marks(fig, x + off, bd[strat], label, HEDGE[key], dist == "normal")
    n, k = len(fig.data), len(fig.data) // len(_DIST_VIEWS)
    fig.update_layout(updatemenus=_menu([
        dict(label=lab, method="update", args=[{"visible": _visible(n, list(range(i * k, (i + 1) * k)))}])
        for i, (_, lab) in enumerate(_DIST_VIEWS)
    ]), barmode="overlay")
    fig.add_hline(y=0, line=dict(color=C.ink2, width=1), layer="below")
    fig.update_xaxes(tickvals=x, ticktext=[f"Año {y}" for y in HEDGE_YEARS], range=[-0.6, len(x) - 0.4], ticks="")
    fig.update_yaxes(title_text="desviación frente al presupuesto", ticksuffix=" %", dtick=5)
    return _layout(fig, 430)


def tails(R: dict) -> go.Figure:
    t = R["tails"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.2)
    horizons = sorted(t["horizonte"].unique())
    for dist, key in (("Normal", "normal"), ("t de Student", "t")):
        sub = t[t["dist"] == dist]
        for row, col, tip in ((1, "p_3sd", "<b>%{y:.3f} %</b> · "), (2, "q999", "<b>%{y:.2f} σ</b> · ")):
            y = sub[col].to_numpy() * (100 if col == "p_3sd" else 1)
            fig.add_trace(go.Scatter(
                x=sub["horizonte"], y=y, name=dist, legendgroup=dist, showlegend=row == 1, mode="lines+markers",
                line=dict(color=DIST[key], width=2), marker=dict(size=9, color=DIST[key]),
                hovertemplate=tip + dist + "<extra></extra>",
            ), row=row, col=1)
    t1 = t[t["dist"] == "t de Student"].sort_values("horizonte").iloc[0]
    x1 = float(np.log10(t1["horizonte"]))
    labels = ((1, t1["p_3sd"] * 100, f"{num(t1['p_3sd'] * 100, 3)} %"), (2, t1["q999"], f"{num(t1['q999'], 2)} σ"))
    for row, y, text in labels:
        fig.add_annotation(_direct_label(x1, y, text, xanchor="left", yanchor="bottom", xshift=5, yshift=5), row=row, col=1)
    for row, text in ((1, "Probabilidad de un choque mayor a 3σ"), (2, "Cuantil 99,9 % (en desviaciones estándar)")):
        ax = "" if row == 1 else row
        fig.add_annotation(_direct_label(0, 1, text, xref=f"x{ax} domain", yref=f"y{ax} domain", xanchor="left",
                                         yanchor="bottom", yshift=8, font=dict(size=12, color=C.ink)))
    p3, q = t["p_3sd"] * 100, t["q999"]
    fig.update_yaxes(ticksuffix=" %", tickformat=".1f", range=[0, p3.max() * 1.25], row=1, col=1)
    fig.update_yaxes(ticksuffix=" σ", tickformat=".1f", range=[q.min() - 0.12, q.max() + 0.28], row=2, col=1)
    fig.update_xaxes(type="log", tickvals=horizons, ticktext=[f"{h} mes" + ("" if h == 1 else "es") for h in horizons],
                     range=[np.log10(0.7), np.log10(16)], showspikes=True)
    fig.update_xaxes(title_text="horizonte de agregación (escala logarítmica)", row=2, col=1)
    return _layout(fig, 480, hovermode="x unified", legend=dict(y=1.1), margin=dict(t=24))


_SCEN3 = ("favorable", "central", "adverso")


def _scen_label(R: dict, key: str) -> str:
    return {s.key: s.nombre for s in R["scenarios"]}.get(key, "Neutral al riesgo")


def _two_lines(label: str) -> str:
    head, _, tail = label.partition(" ")
    return f"{head}<br>{tail}" if tail else head


def _active(labels: list[str], wanted: str) -> int:
    return labels.index(wanted) if wanted in labels else 0


# El flujo consolidado (Tabla B.3.1) es HTML con pestañas: tables.consolidated.


def annual_service(R: dict) -> go.Figure:
    fig = go.Figure()
    combos = [(k, d) for k in _SCEN3 for d in DISTS]
    years = np.arange(1, 11)
    short = {"sin": "sin cobertura", "con": "con forwards"}
    for key, dist in combos:
        for strat in STRATS:
            f = R["flows"][(key, dist, strat)]
            mean, lo, hi = f["anual_media"] / 1e6, f["anual_p5"] / 1e6, f["anual_p95"] / 1e6
            fig.add_trace(go.Scatter(
                x=years, y=mean, mode="markers", name=STRATS[strat], visible=False, offsetgroup=strat,
                marker=dict(size=9, color=HEDGE[strat]), customdata=np.c_[lo, hi],
                error_y=dict(type="data", symmetric=False, array=hi - mean, arrayminus=mean - lo, color=HEDGE[strat],
                             thickness=2, width=0),
                hovertemplate="<b>COP %{y:,.1f} M</b> media " + short[strat]
                              + "<br>P5–P95: %{customdata[0]:,.1f} – %{customdata[1]:,.1f} M<extra></extra>",
            ))
    n = len(fig.data)
    labels = [f"{_scen_label(R, k)} · {DISTS[d]}" for k, d in combos]
    buttons = [dict(label=lab, method="update", args=[{"visible": _visible(n, [2 * i, 2 * i + 1])}])
               for i, lab in enumerate(labels)]
    start = _active(labels, f"{_scen_label(R, 'central')} · {DISTS['normal']}")
    fig.data[2 * start].visible = fig.data[2 * start + 1].visible = True
    menu = _menu(buttons)
    menu[0]["active"] = start
    x0, x1 = min(HEDGE_YEARS) - 0.5, max(HEDGE_YEARS) + 0.5
    fig.add_vrect(x0=x0, x1=x1, fillcolor=rgba(C.green, 0.07), line_width=0, layer="below")
    fig.add_annotation(x=(x0 + x1) / 2, y=0, yref="paper", yanchor="bottom", yshift=6, text="años con forwards",
                       showarrow=False, font=dict(color=C.muted, size=11.5))
    # Solo la cifra del año: el título del eje ya lo dice, y un «Año 1» más ancho que las demás marcas las apretaba
    # (a 320 px hacía girar todo el eje).
    fig.update_xaxes(title_text="año del crédito", tickmode="linear", tick0=1, dtick=1, range=[0.5, 10.5],
                     showspikes=True, unifiedhovertitle=dict(text="Año %{x}"))
    fig.update_yaxes(title_text="servicio de la deuda (COP millones por año)", tickformat=",.0f", rangemode="tozero")
    return _layout(fig, 440, updatemenus=menu, scattermode="group", scattergap=0.45, hovermode="x unified",
                   margin=dict(l=8, r=16, t=16, b=8))


def irr_box(R: dict) -> go.Figure:
    keys = ["favorable", "central", "adverso", "neutral"]
    off = {"sin": -0.19, "con": 0.19}
    fig = go.Figure()
    for dist in DISTS:
        for strat in STRATS:
            st = R["irr_box"][dist][strat]
            stat = {p: np.array([st[k][p] for k in keys]) * 100 for p in (5, 25, 50, 75, 95, "mean")}
            pos = np.arange(len(keys)) + off[strat]
            fig.add_trace(go.Box(
                x=pos, q1=stat[25], median=stat[50], q3=stat[75], lowerfence=stat[5], upperfence=stat[95],
                mean=stat["mean"], boxmean=True, width=0.32, whiskerwidth=0.45, name=STRATS[strat],
                legendgroup=strat, line=dict(color=HEDGE[strat], width=1.5), fillcolor=rgba(HEDGE[strat], 0.16),
                hoverinfo="skip", visible=dist == "normal",
            ))
            names = [f"{_scen_label(R, k)}, {STRATS[strat][0].lower()}{STRATS[strat][1:]}" for k in keys]
            info = np.c_[stat[50], stat["mean"], stat[25], stat[75], stat[5], stat[95]]
            levels = (5, 25, 50, 75, 95)
            fig.add_trace(go.Scatter(
                x=np.repeat(pos, len(levels)), y=np.ravel([[stat[p][i] for p in levels] for i in range(len(keys))]),
                mode="markers", marker=dict(size=24, color=C.surface, opacity=0), showlegend=False, legendgroup=strat,
                customdata=np.repeat(info, len(levels), axis=0), text=np.repeat(names, len(levels)),
                hovertemplate="<b>%{customdata[0]:.1f}" + PCT + "</b> mediana · media %{customdata[1]:.1f}" + PCT
                              + "<br>%{text}<br>P25–P75: %{customdata[2]:.1f} – %{customdata[3]:.1f}" + PCT
                              + "<br>P5–P95: %{customdata[4]:.1f} – %{customdata[5]:.1f}" + PCT + "<extra></extra>",
                visible=dist == "normal",
            ))
    loan_ea = R["a2"]["loan"].effective_annual_rate * 100
    synth = R["synthetic"]["3Y"] * 100
    refs = [
        (synth, f"Cobertura total hoy (forward 3A): {num(synth, 2)}{PCT}", C.verm, "dash"),
        (loan_ea, f"Tasa del crédito en USD: {num(loan_ea, 2)}{PCT} E.A.", C.muted, "dot"),
    ]
    for y, name, color, dash in refs:
        fig.add_trace(go.Scatter(x=[-0.5, len(keys) - 0.5], y=[y, y], mode="lines", name=name, hoverinfo="skip",
                                 line=dict(color=color, width=1.5, dash=dash)))
    n = len(fig.data)
    # En el celular (lienzo de menos de 330 px) la entrada larga de la leyenda va en dos renglones (se salía por la
    # derecha) y bajo cada caja va solo el nombre corto del escenario: los dos renglones («para el peso»,
    # «(depreciación)») no caben en una cuarta parte del ancho y se montaban con el vecino. El tooltip lo dice entero.
    narrow(fig, 330, layout={"xaxis.ticktext": [_scen_label(R, k).split(" ")[0] for k in keys],
                             "xaxis.tickfont.size": 11},
           traces={n - 2: {"name": f"Cobertura total hoy<br>(forward 3A): {num(synth, 2)}{PCT}"}})
    fig.update_layout(updatemenus=_menu([
        dict(label=DISTS[d], method="update", args=[{"visible": _visible(n, [4 * j + i for i in range(4)] + [8, 9])}])
        for j, d in enumerate(DISTS)
    ]))
    top = max(R["irr_box"][d][s][k][95] for d in DISTS for s in STRATS for k in keys) * 100
    fig.update_xaxes(tickvals=list(range(len(keys))), ticktext=[_two_lines(_scen_label(R, k)) for k in keys],
                     range=[-0.5, len(keys) - 0.5], ticks="", tickangle=0, tickfont=dict(size=11.5))
    fig.update_yaxes(title_text="TIR del crédito en pesos (% E.A.)", ticksuffix=PCT, range=[-2, top + 2], dtick=5)
    return _layout(fig, 480, hovermode="closest", hoverdistance=30, margin=dict(l=8, r=16, t=16, b=8))


def frontier(R: dict) -> go.Figure:
    s = R["sens"]
    hr, strat = s["hedge_ratio"], s["strategies"]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13)
    fig.add_trace(go.Scatter(
        x=hr["ratio"] * 100, y=hr["dev_sd"] * 100, mode="lines+markers", name="Desviación presupuestal",
        line=dict(color=C.green, width=2.5), marker=dict(size=9, color=C.green), showlegend=False,
        hovertemplate="<b>%{y:.2f}" + PCT + "</b> σ de la desviación presupuestal<br>cubriendo %{x:.1f}"
                      + PCT + " de los pagos del año<extra></extra>",
    ), row=1, col=1)
    minvar = s["beta_minvar"] * 100
    for x, label, anchor, shift in ((minvar, f"mínima varianza {num(minvar, 1)}{PCT}", "right", -6),
                                    (75, f"exigido 75{PCT}", "left", 6)):
        fig.add_vline(x=x, line=dict(color=C.muted, width=1, dash="dot"), row=1, col=1)
        fig.add_annotation(x=x, y=1, xref="x", yref="y domain", text=label, showarrow=False, xanchor=anchor,
                           yanchor="top", xshift=shift, font=dict(color=C.ink2, size=11.5))
    colors = {"Sin cobertura": C.gray, "Rolling anual (diseño exigido)": C.green,
              "Rolling con 4 vencimientos trimestrales": C.blue, "Strip pactado al cierre del año 6": C.ocre}
    place = {"Sin cobertura": ("left", "bottom", -4, 9), "Rolling anual (diseño exigido)": ("left", "top", 8, -6),
             "Rolling con 4 vencimientos trimestrales": ("left", "bottom", 8, 6),
             "Strip pactado al cierre del año 6": ("right", "middle", -10, 0)}
    breaks = {"Rolling anual (diseño exigido)": "Rolling anual<br>(diseño exigido)",
              "Rolling con 4 vencimientos trimestrales": "Rolling con 4 vencimientos<br>trimestrales",
              "Strip pactado al cierre del año 6": "Strip pactado al cierre<br>del año 6"}
    x, y = strat["costo_esperado"] / 1e6, strat["sd_cond"] / 1e6
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers", showlegend=False, text=strat["estrategia"],
        marker=dict(size=13, color=[colors.get(e, C.gray) for e in strat["estrategia"]]),
        customdata=np.c_[strat["sd"] / 1e6, strat["dev_sd"] * 100],
        hovertemplate="<b>COP %{y:,.1f} M</b> σ años 7–10 dada la TRM del año 6<br>%{text}<br>costo esperado: COP "
                      "%{x:,.2f} M<br>σ incondicional: COP %{customdata[0]:,.1f} M<br>σ presupuestal: "
                      "%{customdata[1]:.2f}" + PCT + "<extra></extra>",
    ), row=2, col=1)
    for name, xv, yv in zip(strat["estrategia"], x, y, strict=True):
        xa, ya, dx, dy = place.get(name, ("left", "middle", 10, 0))
        fig.add_annotation(x=xv, y=yv, xref="x2", yref="y2", text=breaks.get(name, name), showarrow=False,
                           xanchor=xa, yanchor=ya, xshift=dx, yshift=dy, align=xa, font=dict(color=C.ink2, size=11.5))
    fig.update_xaxes(title_text="porcentaje de los pagos del año cubierto con el NDF", ticksuffix=PCT, row=1, col=1,
                     range=[-4, 104])
    dev = hr["dev_sd"] * 100
    fig.update_yaxes(title_text="σ de la desviación presupuestal", ticksuffix=PCT, row=1, col=1,
                     range=[dev.min() - 0.7, dev.max() + 0.7])
    lo, hi = min(x.min(), 0), max(x.max(), 0)
    span = (hi - lo) or 1
    fig.update_xaxes(title_text="costo esperado de la cobertura (COP millones)", row=2, col=1,
                     range=[lo - 0.08 * span, hi + 0.2 * span])
    fig.update_yaxes(title_text="σ años 7–10 dada la TRM<br>del año 6 (COP M)", range=[0, y.max() * 1.15], row=2, col=1)
    return _layout(fig, 660, showlegend=False, margin=dict(l=8, r=16, t=16, b=8))



def sens_d(R: dict) -> go.Figure:
    d = R["sens"]["d"]
    dx, res, prot = d["d"].to_numpy() * 100, d["forward_neto"].to_numpy() / 1e6, d["proteccion"].to_numpy() * 100
    notes = {R["d_lr"]: "supuesto base", R["dev_lt"]: "TES 10A vs. UST 10A", R["b1"]["dev_1y"]: "forward 1A de hoy"}
    note = [next((f" ({v})" for k, v in notes.items() if abs(k - di) < 1e-9), "") for di in d["d"]]
    keep = {int(np.argmax(res)), int(np.argmin(res))} | {i for i, t in enumerate(note) if "base" in t}
    lo, hi = min(float(res.min()), 0), max(float(res.max()), 0)
    pad = (hi - lo) * 0.16
    xlo, xhi = dx.min() - 0.6, dx.max() + 0.6
    width = min(0.04 * (xhi - xlo), 0.8 * np.diff(np.sort(dx)).min())
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dx, y=res, width=width, name="Resultado esperado de los 4 forwards", showlegend=False,
        marker_color=[C.blue if v > 0 else C.verm for v in res], customdata=note,
        text=[_signed(v, 2) if i in keep else "" for i, v in enumerate(res)], textposition="outside",
        constraintext="none", cliponaxis=False, textfont=dict(color=C.ink2, size=11.5),
        hovertemplate="<b>COP %{y:,.2f} M</b> resultado esperado de los forwards%{customdata}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dx, y=prot, yaxis="y2", mode="lines+markers+text", name="Probabilidad de protección", showlegend=False,
        line=dict(color=C.green, width=2.5), marker=dict(size=8, color=C.green),
        text=[f"{num(v, 1)}{PCT}" if i in (0, len(prot) - 1) else "" for i, v in enumerate(prot)],
        textposition=["top right"] + ["top center"] * (len(prot) - 2) + ["bottom left"],
        textfont=dict(color=C.ink2, size=11.5), cliponaxis=False,
        hovertemplate="<b>%{y:.1f}" + PCT + "</b> probabilidad de protección<extra></extra>",
    ))
    for di, label, anchor in ((R["d_lr"], "supuesto base", "center"), (R["b1"]["dev_1y"], "prima de hoy", "right")):
        line = dict(type="line", x0=di * 100, x1=di * 100, xref="x", line=dict(color=C.muted, width=1, dash="dot"),
                    layer="below")
        fig.add_shape(**line, y0=0, y1=hi + pad, yref="y")
        fig.add_shape(**line, y0=0, y1=1, yref="y2 domain")
        fig.add_annotation(x=di * 100, y=1, xref="x", yref="paper", yanchor="bottom", xanchor=anchor, text=label,
                           showarrow=False, font=dict(color=C.ink2, size=11.5))
    return _layout(
        fig, 470, hovermode="x unified", hoversubplots="axis",
        xaxis=dict(anchor="y2", title_text="prima forward anual de los años 7–10", ticksuffix=PCT, dtick=1,
                   range=[xlo, xhi], showspikes=True, hoverformat=".2f"),
        yaxis=dict(domain=[0.44, 1], title_text="resultado esperado<br>(COP millones)", zeroline=True,
                   zerolinecolor=C.axis, zerolinewidth=1, range=[lo - pad, hi + pad]),
        yaxis2=dict(domain=[0, 0.3], anchor="x", title_text="probabilidad<br>de protección", ticksuffix=PCT,
                    range=[np.floor(prot.min() / 5) * 5 - 2, np.ceil(prot.max() / 5) * 5 + 3], nticks=4),
        margin=dict(l=8, r=16, t=26, b=8),
    )


def sens_rate(R: dict) -> go.Figure:
    r = R["sens"]["rate"]
    x = r["tasa"].to_numpy() * 100
    fig = go.Figure()
    series = (("tir_con", "TIR en pesos con forwards", C.green, 3, dict(size=10)),
              ("tir_sin", "TIR en pesos sin cobertura", C.gray, 1.5, dict(size=5, line=dict(width=0))),
              ("ea", "Tasa del crédito en USD (E.A.)", C.ocre, 2, dict(size=8)))
    for col, name, color, width, marker in series:
        y = r[col].to_numpy() * 100
        fig.add_trace(go.Scatter(
            x=x, y=y, name=name, mode="lines+markers", line=dict(color=color, width=width),
            marker=dict(color=color, **marker), cliponaxis=False,
            hovertemplate="<b>%{y:.2f}" + PCT + "</b> " + name + "<extra></extra>",
        ))
    # Rótulos directos en vez de leyenda (la gris va escondida bajo la verde); el velo tapa la rejilla que cruzan.
    end = {col: r[col].iloc[-1] * 100 for col in ("tir_con", "tir_sin", "ea")}
    for y, text in ((max(end["tir_con"], end["tir_sin"]), f"con forwards: {num(end['tir_con'], 2)}{PCT}<br>"
                                                          f"sin cobertura: {num(end['tir_sin'], 2)}{PCT}"),
                    (end["ea"], f"tasa en USD: {num(end['ea'], 2)}{PCT}")):
        fig.add_annotation(x=x[-1], y=y, text=text, showarrow=False, xanchor="right", yanchor="bottom", xshift=-4,
                           yshift=9, align="right", bgcolor=rgba(C.surface, 0.85), borderpad=1,
                           font=dict(color=C.ink2, size=11.5))
    # La tasa base se marca como en el Gráfico B.3.4: línea punteada con su rótulo arriba.
    base = R["a2"]["loan"].nominal_rate * 100
    fig.add_shape(type="line", x0=base, x1=base, y0=0, y1=1, xref="x", yref="paper", layer="below",
                  line=dict(color=C.muted, width=1, dash="dot"))
    fig.add_annotation(x=base, y=1, xref="x", yref="paper", yanchor="bottom", text="tasa base", showarrow=False,
                       font=dict(color=C.ink2, size=11.5))
    lo, hi = r["ea"].min() * 100, r[["tir_con", "tir_sin"]].to_numpy().max() * 100
    fig.update_xaxes(title_text="tasa nominal anual del crédito (Prime + spread)", tickvals=x,
                     ticktext=[f"{num(v, 1)}{PCT}" for v in x], range=[x[0] - 0.3, x[-1] + 0.3], showspikes=True,
                     hoverformat=".1f")
    fig.update_yaxes(title_text="costo efectivo anual (% E.A.)", ticksuffix=PCT,
                     range=[lo - 0.08 * (hi - lo), hi + 0.2 * (hi - lo)])
    # Misma altura y margen superior que el Gráfico B.3.4, que va al lado: los dos ejes X quedan a la misma altura.
    return _layout(fig, 470, hovermode="x unified", showlegend=False, margin=dict(l=8, r=16, t=26, b=8))


def build_all(R: dict) -> dict[str, str]:
    figs = {
        "trm_history": trm_history, "policy_rates": policy_rates, "inflation": inflation,
        "oil_correlation": oil_correlation, "projections": projections, "rate_benchmarks": rate_benchmarks,
        "amortization": amortization, "cop_installments": cop_installments,
        "decomposition": decomposition, "waterfall": waterfall, "forward_curve": forward_curve,
        "cip_heatmap": cip_heatmap, "forwards_valuation": forwards_valuation, "ratio_hist": ratio_hist,
        "proportions": proportions, "budget_scatter": budget_scatter, "budget_box": budget_box, "tails": tails,
        "annual_service": annual_service, "irr_box": irr_box,
        "frontier": frontier, "sens_d": sens_d, "sens_rate": sens_rate,
    }
    return {name: to_div(fn(R), f"fig-{name.replace('_', '-')}") for name, fn in figs.items()}
