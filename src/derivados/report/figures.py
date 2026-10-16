"""Gráficos interactivos (Plotly) del informe."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..analysis import DISTS, HEDGE_YEARS, STRATS
from .fmt import mes, num

PRIMARY, ACCENT, GREEN, RED, GRAY, PURPLE = "#0f3d5e", "#e3a21a", "#2a9d8f", "#c8553d", "#8d99ae", "#7b6d8d"
SCEN_COLORS = {"base": GRAY, "favorable": GREEN, "central": PRIMARY, "adverso": RED, "neutral": PURPLE}
DIST_COLORS = {"normal": "#1d4e89", "t": "#e07a1f"}
STRAT_COLORS = {"sin": "#9aa5b1", "con": GREEN}
CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "locale": "es",
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def _layout(fig: go.Figure, height: int = 430, **kw) -> go.Figure:
    layout = dict(
        template="plotly_white",
        height=height,
        separators=",.",
        font=dict(family="Inter, system-ui, -apple-system, Segoe UI, sans-serif", size=13, color="#1f2937"),
        margin=dict(l=64, r=28, t=40, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=12)),
        hoverlabel=dict(font_family="Inter, system-ui, sans-serif"),
    )
    layout.update(kw)
    fig.update_layout(**layout)
    return fig


def _menu(buttons: list[dict], x: float = 0.0, y: float = 1.18) -> list[dict]:
    return [
        dict(
            type="dropdown",
            x=x,
            y=y,
            xanchor="left",
            yanchor="top",
            showactive=True,
            bgcolor="#ffffff",
            bordercolor="#cbd5e1",
            font=dict(size=12),
            buttons=buttons,
        )
    ]


def to_div(fig: go.Figure, div_id: str) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, div_id=div_id, config=CONFIG)


def _visible(n: int, on: list[int]) -> list[bool]:
    return [i in on for i in range(n)]


# ----------------------------------------------------------------------------- A.1
def trm_history(R: dict) -> go.Figure:
    a1 = R["a1"]
    trm, brent = a1["trm_daily"], a1["brent_monthly"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=trm.index, y=trm.values, name="TRM (COP por USD)", line=dict(color=PRIMARY, width=1.6),
            hovertemplate="%{x|%d %b %Y}<br>TRM: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=brent.index, y=brent.values, name="Brent, promedio mensual (USD/barril, eje der.)",
            line=dict(color=ACCENT, width=1.5, dash="dot"),
            hovertemplate="%{x|%b %Y}<br>Brent: USD %{y:,.1f}<extra></extra>",
        ),
        secondary_y=True,
    )
    events = [
        ("2015-08-24", "Desplome del petróleo", -45),
        ("2020-03-19", "Choque COVID-19", -40),
        ("2022-11-05", "Máximo histórico 5.061", -30),
        ("2026-03-04", "Guerra en el golfo Pérsico", -40),
        ("2026-06-23", "Segunda vuelta", 40),
        ("2026-08-10", "Terremoto 7,4", -70),
        ("2026-10-15", "Valoración 3.197,65", 55),
    ]
    for date, label, ay in events:
        y = float(trm.asof(pd.Timestamp(date)))
        fig.add_annotation(
            x=date, y=y, text=label, showarrow=True, arrowhead=2, arrowsize=0.8, arrowcolor="#64748b",
            ax=0, ay=ay, font=dict(size=10, color="#334155"), bgcolor="rgba(255,255,255,0.85)",
        )
    fig.update_xaxes(
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1 año", step="year", stepmode="backward"),
                dict(count=3, label="3 años", step="year", stepmode="backward"),
                dict(count=5, label="5 años", step="year", stepmode="backward"),
                dict(step="all", label="Desde 2015"),
            ],
            x=0, y=1.12, font=dict(size=11),
        )
    )
    fig.update_yaxes(title_text="COP por USD", secondary_y=False, tickformat=",.0f")
    fig.update_yaxes(title_text="USD por barril", secondary_y=True, showgrid=False, range=[20, 140], dtick=20)
    _layout(fig, 470, legend=dict(orientation="h", y=-0.15, x=0))
    return fig


def policy_rates(R: dict) -> go.Figure:
    r = R["a1"]["rates"].resample("W").last()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.66, 0.34], vertical_spacing=0.07)
    fig.add_trace(
        go.Scatter(x=r.index, y=r["banrep"], name="BanRep (tasa de política)", line=dict(color=PRIMARY, width=2.2),
                   line_shape="hv", hovertemplate="%{x|%d %b %Y}<br>BanRep: %{y:.2f} %<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=r.index, y=r["fed_u"], name="Fed (techo del rango)", line=dict(color=RED, width=2.2),
                   line_shape="hv", hovertemplate="%{x|%d %b %Y}<br>Fed techo: %{y:.2f} %<extra></extra>"),
        row=1, col=1,
    )
    diff = r["banrep"] - r["fed_u"]
    fig.add_trace(
        go.Scatter(x=r.index, y=diff, name="Diferencial (pp)", fill="tozeroy", line=dict(color=ACCENT, width=1.5),
                   line_shape="hv", hovertemplate="%{x|%d %b %Y}<br>Diferencial: %{y:.2f} pp<extra></extra>"),
        row=2, col=1,
    )
    fig.update_yaxes(title_text="% anual", row=1, col=1, ticksuffix=" %")
    fig.update_yaxes(title_text="pp", row=2, col=1)
    return _layout(fig, 470)


def inflation(R: dict) -> go.Figure:
    col, us = R["a1"]["inflation_col"], R["a1"]["inflation_us"]
    years = sorted(col)
    fig = go.Figure()
    fig.add_hrect(y0=2, y1=4, fillcolor="#bbf7d0", opacity=0.45, line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="Rango meta BanRep (2 %–4 %)",
                             marker=dict(symbol="square", size=13, color="#bbf7d0"), hoverinfo="skip"))
    fig.add_trace(go.Bar(x=years, y=[col[y] for y in years], name="Colombia (DANE)", marker_color=PRIMARY,
                         hovertemplate="Sep-%{x}: %{y:.2f} %<extra>Colombia</extra>"))
    fig.add_trace(go.Bar(x=years, y=[us.get(y) for y in years], name="Estados Unidos (BLS)", marker_color=RED,
                         hovertemplate="Sep-%{x}: %{y:.2f} %<extra>EE. UU.</extra>"))
    fig.update_yaxes(title_text="Variación anual a septiembre", ticksuffix=" %")
    return _layout(fig, 390, barmode="group")


def oil_correlation(R: dict) -> go.Figure:
    c = R["a1"]["corr24"]
    fig = go.Figure()
    fig.add_hline(y=0, line_color="#94a3b8", line_width=1)
    fig.add_vrect(x0=pd.Timestamp("2026-01-01"), x1=c.index[-1], fillcolor="#fde68a", opacity=0.35, line_width=0,
                  annotation_text="2026", annotation_position="top left")
    fig.add_trace(go.Scatter(x=c.index, y=c.values, name="Correlación móvil 24 meses", line=dict(color=PRIMARY, width=2),
                             hovertemplate="%{x|%b %Y}<br>ρ = %{y:.2f}<extra></extra>"))
    fig.update_yaxes(title_text="Correlación (24 meses)", range=[-0.8, 0.6])
    return _layout(fig, 360, showlegend=False)


def projections(R: dict) -> go.Figure:
    proj = pd.DataFrame(R["inp"]["proyecciones_trm"])
    order = {"Dic-2026": 0, "2027": 1, "Dic-2027": 1, "1T-2027": 1, "Equilibrio": 2}
    proj["grupo"] = proj["horizonte"].map(order)
    proj = proj.sort_values(["grupo", "valor"], ascending=[False, True])
    proj["etiqueta"] = proj["entidad"] + " · " + proj["horizonte"] + " (" + proj["tipo"].str.lower() + ")"
    colors = {0: "#64748b", 1: PRIMARY, 2: PURPLE}
    names = {0: "Cierre 2026", 1: "2027", 2: "Valor de equilibrio (modelo)"}
    fig = go.Figure()
    for g in (0, 1, 2):
        sub = proj[proj["grupo"] == g]
        fig.add_trace(go.Scatter(
            x=sub["valor"], y=sub["etiqueta"], mode="markers", name=names[g],
            marker=dict(size=11, color=colors[g], line=dict(color="white", width=1)),
            customdata=sub[["fecha", "fuente"]],
            hovertemplate="%{y}<br>TRM: %{x:,.0f}<br>Fecha: %{customdata[0]}<br>Fuente: %{customdata[1]}<extra></extra>",
        ))
    scen = R["scenarios"]
    label = "Escenarios propios · oct-2027"
    fig.add_trace(go.Scatter(
        x=[s.trm_12m for s in scen], y=[label] * len(scen), mode="markers+text", name="Escenarios propios (12 meses)",
        text=[s.nombre.split(" ")[0] for s in scen], textposition="top center",
        marker=dict(size=14, symbol="diamond", color=[SCEN_COLORS[s.key] for s in scen]),
        hovertemplate="%{text}: %{x:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=R["s0"], line_dash="dash", line_color="#334155",
                  annotation_text=f"Spot {num(R['s0'], 2)}", annotation_position="bottom right")
    fig.add_vline(x=R["b1"]["forward_1y_val"], line_dash="dot", line_color=ACCENT,
                  annotation_text=f"Forward 1 año {num(R['b1']['forward_1y_val'], 0)}", annotation_position="top right")
    fig.update_xaxes(title_text="COP por USD", tickformat=",.0f")
    fig.update_yaxes(automargin=True)
    return _layout(fig, 560, legend=dict(orientation="h", y=-0.14, x=0), margin=dict(l=20, r=28, t=30, b=60))


# ----------------------------------------------------------------------------- A.2
def rate_benchmarks(R: dict) -> go.Figure:
    cred = R["inp"]["credito"]
    refs = cred["referencias"]
    rate_504 = next(r["tasa"] for r in refs if "504" in r["nombre"])
    rate_7a = next(r["tasa"] for r in refs if "7(a)" in r["nombre"])
    rng = {("Bancos" if "bancarios" in r["nombre"] else "Pesado"): r for r in refs if "tasa_min" in r}
    rows = [
        ("Prime Wells Fargo", cred["prime"], GRAY),
        ("SBA 504 · 10 años (subsidiada)", rate_504, GRAY),
        ("Elegida: Prime + 2,50 pp", cred["prime"] + cred["spread"], ACCENT),
        ("Techo SBA 7(a) · USD 50k–250k", rate_7a, RED),
    ]
    ranges = [("Bancos: equipo (rango APR)", rng["Bancos"]), ("Equipo pesado (rango APR)", rng["Pesado"])]
    fig = go.Figure()
    for name, rate, color in rows:
        fig.add_trace(go.Bar(y=[name], x=[rate * 100], orientation="h", marker_color=color, showlegend=False,
                             text=[f"{num(rate * 100, 2)} %"], textposition="outside",
                             hovertemplate=f"{name}: %{{x:.2f}} %<extra></extra>"))
    for name, r in ranges:
        lo, hi = r["tasa_min"] * 100, r["tasa_max"] * 100
        fig.add_trace(go.Bar(y=[name], x=[hi - lo], base=[lo], orientation="h", marker_color="#bcd4e6", showlegend=False,
                             text=[f"{num(lo, 0)}–{num(hi, 0)} %"], textposition="inside",
                             hovertemplate=f"{name}: {num(lo, 0)}–{num(hi, 0)} %<br>{r['fuente']}<extra></extra>"))
    fig.add_vline(x=(cred["prime"] + cred["spread"]) * 100, line_dash="dot", line_color=ACCENT)
    fig.update_xaxes(title_text="% nominal anual", range=[0, 18], ticksuffix=" %")
    fig.update_yaxes(automargin=True, categoryorder="array",
                     categoryarray=[n for n, _ in ranges][::-1] + [r[0] for r in rows][::-1])
    return _layout(fig, 340, margin=dict(l=20, r=40, t=20, b=48))


def amortization(R: dict) -> go.Figure:
    s = R["a2"]["schedule"]
    labels = [f"T{p} · {mes(f)}" for p, f in zip(s["periodo"], s["fecha"], strict=True)]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=labels, y=s["abono_capital"], name="Abono a capital", marker_color=PRIMARY,
                         hovertemplate="%{x}<br>Capital: USD %{y:,.2f}<extra></extra>"))
    fig.add_trace(go.Bar(x=labels, y=s["interes"], name="Intereses", marker_color=ACCENT,
                         hovertemplate="%{x}<br>Interés: USD %{y:,.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=labels, y=s["saldo_final"], name="Saldo al cierre (eje der.)", mode="lines",
                             line=dict(color=RED, width=2.2),
                             hovertemplate="%{x}<br>Saldo: USD %{y:,.2f}<extra></extra>"), secondary_y=True)
    fig.add_vrect(x0=labels[24], x1=labels[-1], fillcolor="#d1fae5", opacity=0.5, line_width=0, layer="below",
                  annotation_text="Años 7–10: tramo cubierto con forwards", annotation_position="top left",
                  annotation_font_size=11)
    p = R["a2"]["loan"].principal_usd
    fig.update_yaxes(title_text="USD por trimestre", secondary_y=False, tickformat=",.0f", range=[0, 5500], dtick=1000)
    fig.update_yaxes(title_text="Saldo USD", secondary_y=True, showgrid=False, tickformat=",.0f",
                     range=[0, p * 5500 / 4800], dtick=20000)
    fig.update_xaxes(tickangle=-60, tickfont=dict(size=9))
    return _layout(fig, 450, barmode="stack")


def amortization_table(R: dict) -> go.Figure:
    s = R["a2"]["schedule"]
    vals = [
        s["periodo"].astype(str),
        [f.strftime("%d/%m/%Y") for f in s["fecha"]],
        s["anio"].astype(str),
        [num(v, 2) for v in s["saldo_inicial"]],
        [num(v, 2) for v in s["interes"]],
        [num(v, 2) for v in s["abono_capital"]],
        [num(v, 2) for v in s["cuota"]],
        [num(v, 2) for v in s["saldo_final"]],
    ]
    fill = [["#f8fafc" if (i // 4) % 2 == 0 else "#eef2f7" for i in range(len(s))]] * len(vals)
    fig = go.Figure(go.Table(
        columnwidth=[50, 80, 45, 100, 90, 100, 90, 100],
        header=dict(values=["<b>Trim.</b>", "<b>Fecha</b>", "<b>Año</b>", "<b>Saldo inicial</b>", "<b>Interés</b>",
                            "<b>Abono capital</b>", "<b>Cuota</b>", "<b>Saldo final</b>"],
                    fill_color=PRIMARY, font=dict(color="white", size=12), align="center", height=30),
        cells=dict(values=vals, align=["center", "center", "center", "right", "right", "right", "right", "right"],
                   fill_color=fill, font=dict(size=12), height=26),
    ))
    return _layout(fig, 520, margin=dict(l=0, r=0, t=6, b=0))


# ----------------------------------------------------------------------------- A.3
def cop_installments(R: dict) -> go.Figure:
    a3 = R["a3"]
    dates = a3["base"]["fecha"]
    fig = go.Figure()
    n_fan = 0
    for dist in DISTS:
        fan = a3["fan"][dist]
        vis = dist == "normal"
        for lo, hi, alpha, label in [(5, 95, 0.13, "P5–P95"), (25, 75, 0.25, "P25–P75")]:
            fig.add_trace(go.Scatter(x=dates, y=fan[hi], line=dict(width=0), showlegend=False, hoverinfo="skip", visible=vis))
            fig.add_trace(go.Scatter(
                x=dates, y=fan[lo], fill="tonexty", fillcolor=f"rgba(15,61,94,{alpha})", line=dict(width=0),
                name=f"Simulación central {label} ({DISTS[dist]})", visible=vis,
                hovertemplate=f"%{{x|%b %Y}}<br>{label}: COP %{{y:,.0f}}<extra></extra>",
            ))
            n_fan += 2
    for key in ("base", "favorable", "central", "adverso"):
        df = a3["escenarios"][key]
        name = "Spot constante (base)" if key == "base" else f"Esperado {key}"
        fig.add_trace(go.Scatter(
            x=dates, y=df["cuota_cop"], name=name, mode="lines",
            line=dict(color=SCEN_COLORS[key], width=2.4, dash="dash" if key == "base" else "solid"),
            customdata=df["trm"], hovertemplate="%{x|%b %Y}<br>Cuota: COP %{y:,.0f}<br>TRM: %{customdata:,.0f}<extra>"
            + name + "</extra>",
        ))
    n = len(fig.data)
    lines = list(range(n_fan, n))
    fig.update_layout(updatemenus=_menu([
        dict(label="Banda: innovaciones normales", method="update", args=[{"visible": _visible(n, list(range(0, 4)) + lines)}]),
        dict(label="Banda: t de Student", method="update", args=[{"visible": _visible(n, list(range(4, 8)) + lines)}]),
    ], y=1.22))
    fig.update_yaxes(title_text="Cuota trimestral en COP", tickformat=",.0f")
    return _layout(fig, 480, legend=dict(orientation="h", y=-0.18, x=0), margin=dict(l=70, r=28, t=60, b=60))


def decomposition(R: dict) -> go.Figure:
    a3 = R["a3"]["escenarios"]
    keys = ["central", "favorable", "adverso"]
    comps = [("capital_s0", "Capital a TRM base", PRIMARY), ("interes_s0", "Interés a TRM base", ACCENT),
             ("fx_capital", "Efecto cambiario sobre capital", RED), ("fx_interes", "Efecto cambiario sobre intereses", "#f4a261")]
    fig = go.Figure()
    for i, key in enumerate(keys):
        df = a3[key]
        labels = [mes(f) for f in df["fecha"]]
        for col, name, color in comps:
            fig.add_trace(go.Bar(x=labels, y=df[col], name=name, marker_color=color, visible=i == 0, legendgroup=col,
                                 hovertemplate=f"%{{x}}<br>{name}: COP %{{y:,.0f}}<extra></extra>"))
    n = len(fig.data)
    buttons = [dict(label=f"Escenario {k}", method="update", args=[{"visible": _visible(n, list(range(4 * i, 4 * i + 4)))}])
               for i, k in enumerate(keys)]
    fig.update_layout(updatemenus=_menu(buttons, y=1.22), barmode="relative")
    fig.update_yaxes(title_text="COP por trimestre", tickformat=",.0f")
    fig.update_xaxes(tickangle=-60, tickfont=dict(size=9))
    return _layout(fig, 470, legend=dict(orientation="h", y=-0.28, x=0), margin=dict(l=70, r=28, t=60, b=80))


def waterfall(R: dict) -> go.Figure:
    summ = R["a3"]["summary"].set_index("key")
    keys = ["central", "favorable", "adverso", "base"]
    fig = go.Figure()
    for i, key in enumerate(keys):
        r = summ.loc[key]
        y = [R["a2"]["financed_cop"], r["interes_s0"], r["fx_interes"], r["fx_capital"], r["total_cop"]]
        fig.add_trace(go.Waterfall(
            x=["Capital desembolsado", "Intereses a TRM base", "Efecto cambiario s/ intereses",
               "Efecto cambiario s/ capital", "Total pagado en COP"],
            y=[v / 1e6 for v in y], measure=["absolute", "relative", "relative", "relative", "total"],
            text=[num(v / 1e6, 1) for v in y], textposition="outside", visible=i == 0,
            connector=dict(line=dict(color="#94a3b8")),
            increasing=dict(marker_color=RED), decreasing=dict(marker_color=GREEN), totals=dict(marker_color=PRIMARY),
            hovertemplate="%{x}: COP %{y:,.1f} millones<extra></extra>", name=r["escenario"],
        ))
    buttons = [dict(label=summ.loc[k, "escenario"], method="update", args=[{"visible": _visible(len(keys), [i])}])
               for i, k in enumerate(keys)]
    fig.update_layout(updatemenus=_menu(buttons, y=1.2), showlegend=False)
    fig.update_yaxes(title_text="COP millones", tickformat=",.0f")
    return _layout(fig, 430, margin=dict(l=70, r=28, t=60, b=48))


# ----------------------------------------------------------------------------- B.1
def forward_curve(R: dict) -> go.Figure:
    b1 = R["b1"]
    c, t = b1["curve"], b1["theo_curve"]
    x = c["dias"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=c["puntos"], name="Mercado (Itaú, 13-oct-2026)", mode="lines+markers+text",
                             text=[num(v) for v in c["puntos"]], textposition="top left",
                             line=dict(color=ACCENT, width=3), marker=dict(size=10),
                             customdata=np.c_[c["forward"], c["dev"] * 100, c["plazo"]],
                             hovertemplate="%{customdata[2]}: %{y} puntos<br>Forward: %{customdata[0]:,.2f}"
                             "<br>Devaluación implícita: %{customdata[1]:.2f} %<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=t["banrep_sofr"], name="Teórico: BanRep vs. SOFR", mode="lines+markers",
                             line=dict(color=PRIMARY, dash="dash"), hovertemplate="%{y:,.1f} puntos<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=t["ibr_swap"], name="Teórico: IBR 1M vs. swap SOFR 1A", mode="lines+markers",
                             line=dict(color=GREEN, dash="dot"), hovertemplate="%{y:,.1f} puntos<extra></extra>"))
    fig.update_yaxes(title_text="Puntos forward (COP)", tickformat=",.0f")
    fig.update_xaxes(title_text="Plazo (escala logarítmica de días)", type="log", tickvals=list(x), ticktext=list(c["plazo"]))
    return _layout(fig, 400, legend=dict(orientation="h", y=-0.25, x=0), margin=dict(l=64, r=28, t=20, b=70))


def cip_heatmap(R: dict) -> go.Figure:
    h = R["b1"]["heat"]
    fig = go.Figure(go.Heatmap(
        z=h["z"], x=[f"{num(v * 100, 2)} %" for v in h["rc"]], y=[f"{num(v * 100, 2)} %" for v in h["ru"]],
        colorscale=[[0, "#e0f2f1"], [0.5, "#5fa8d3"], [1, "#0f3d5e"]],
        text=[[num(v, 0) for v in row] for row in h["z"]], texttemplate="%{text}", textfont=dict(size=10),
        colorbar=dict(title=dict(text="F 1 año"), tickformat=",.0f"),
        hovertemplate="r COP: %{x}<br>r USD: %{y}<br>Forward teórico: %{z:,.2f}<extra></extra>",
    ))
    fig.update_xaxes(title_text="Tasa COP (E.A.)")
    fig.update_yaxes(title_text="Tasa USD (E.A.)")
    return _layout(fig, 430, margin=dict(l=70, r=20, t=20, b=60))


def forwards_valuation(R: dict) -> go.Figure:
    per = R["b2"][("central", "normal")]["per"]
    base = np.arange(len(per))
    labels = [f"Forward {i + 1} · año {y}" for i, y in enumerate(per["anio"])]
    fig = go.Figure()
    for off, col, name, color, symbol in ((-0.12, "forward", "Tasa pactada F (media, P5–P95)", PRIMARY, "circle"),
                                          (0.12, "spot_t", "TRM al vencimiento (media, P5–P95)", ACCENT, "diamond")):
        fig.add_trace(go.Scatter(
            x=base + off, y=per[f"{col}_media"], mode="markers", name=name, marker=dict(size=12, color=color, symbol=symbol),
            error_y=dict(type="data", symmetric=False, array=per[f"{col}_p95"] - per[f"{col}_media"],
                         arrayminus=per[f"{col}_media"] - per[f"{col}_p5"], color=color, thickness=1.5),
            customdata=np.c_[per[f"{col}_p5"], per[f"{col}_p95"]],
            hovertemplate="Media: %{y:,.0f}<br>P5: %{customdata[0]:,.0f} · P95: %{customdata[1]:,.0f}<extra>" + name + "</extra>",
        ))
    fig.update_xaxes(tickvals=base, ticktext=labels)
    fig.update_yaxes(title_text="COP por USD", tickformat=",.0f")
    return _layout(fig, 380)


# ----------------------------------------------------------------------------- B.2
def ratio_hist(R: dict) -> go.Figure:
    bins = np.linspace(-0.6, 0.8, 71)
    centers = (bins[:-1] + bins[1:]) / 2
    fig = go.Figure()
    for dist in DISTS:
        x = R["ratio_hist"][dist]
        h, _ = np.histogram(np.clip(x, bins[0], bins[-1] - 1e-9), bins=bins)
        fig.add_trace(go.Bar(x=centers * 100, y=h / len(x) * 100, name=DISTS[dist], marker_color=DIST_COLORS[dist],
                             opacity=0.6, hovertemplate="S_T/F − 1 ≈ %{x:.0f} %<br>Frecuencia: %{y:.2f} %<extra>"
                             + DISTS[dist] + "</extra>"))
    for x in (-20, 0, 20):
        fig.add_vline(x=x, line_dash="dash" if x else "solid", line_color="#334155")
    for x, txt, anchor in [(-21, "Pérdida extrema<br>del derivado", "right"), (-1, "← Costo de<br>oportunidad", "right"),
                           (1, "Protección →", "left"), (21, "Pérdida cambiaria<br>extrema evitada", "left")]:
        fig.add_annotation(x=x, y=1.0, yref="paper", text=txt, showarrow=False, xanchor=anchor, yanchor="top",
                           font=dict(size=10, color="#334155"), bgcolor="rgba(255,255,255,0.8)")
    fig.update_layout(barmode="overlay", updatemenus=[dict(
        type="buttons", direction="right", x=1, xanchor="right", y=1.2, showactive=True, font=dict(size=11),
        buttons=[dict(label="Escala lineal", method="relayout", args=[{"yaxis.type": "linear"}]),
                 dict(label="Escala log (colas)", method="relayout", args=[{"yaxis.type": "log"}])])])
    fig.update_xaxes(title_text="TRM al vencimiento frente a la tasa pactada (S_T / F − 1, %)", ticksuffix=" %")
    fig.update_yaxes(title_text="% de escenarios")
    return _layout(fig, 430, margin=dict(l=64, r=28, t=80, b=56))


def proportions(R: dict) -> go.Figure:
    metrics = [("proteccion", "Protección<br>(S_T > F)"), ("costo_oportunidad", "Costo de oportunidad<br>(S_T < F)"),
               ("extrema_exposicion", "Pérdida cambiaria<br>extrema (S_T > 1,2F)"),
               ("extrema_derivado", "Pérdida extrema del<br>derivado (S_T < 0,8F)"), ("fracaso", "Fracaso por<br>desfase")]
    keys = ["favorable", "central", "adverso", "neutral"]
    names = {s.key: s.nombre for s in R["scenarios"]} | {"neutral": "Neutral al riesgo"}
    fig = go.Figure()
    for dist in DISTS:
        for key in keys:
            pooled = R["b2"][(key, dist)]["pooled"]
            y = [pooled[m] * 100 for m, _ in metrics]
            fig.add_trace(go.Bar(x=[lbl for _, lbl in metrics], y=y, name=names[key], marker_color=SCEN_COLORS[key],
                                 visible=dist == "normal", text=[num(v, 1) for v in y], textposition="outside",
                                 textfont=dict(size=10),
                                 hovertemplate="%{x}<br>%{y:.2f} % de los escenarios<extra>" + names[key] + "</extra>"))
    n = len(fig.data)
    fig.update_layout(updatemenus=_menu([
        dict(label="Innovaciones normales", method="update", args=[{"visible": _visible(n, list(range(0, 4)))}]),
        dict(label="Innovaciones t de Student", method="update", args=[{"visible": _visible(n, list(range(4, 8)))}]),
    ], y=1.14), barmode="group")
    fig.update_yaxes(title_text="% de escenarios", ticksuffix=" %")
    fig.update_xaxes(tickangle=0)
    return _layout(fig, 470, legend=dict(orientation="h", y=-0.22, x=0), margin=dict(l=64, r=28, t=60, b=90))


def budget_scatter(R: dict) -> go.Figure:
    s = R["scatter"]
    gain, above = s["payoff"] > 0, s["above"]
    groups = [
        ("Protección efectiva", gain & above, GREEN),
        ("Costo de oportunidad", ~gain & ~above, "#5b8fb9"),
        ("Sobrecompensación", gain & ~above, ACCENT),
        ("Fracaso por desfase", ~gain & above, RED),
    ]
    fig = go.Figure()
    for name, mask, color in groups:
        fig.add_trace(go.Scatter(x=s["u"][mask] * 100, y=s["h"][mask] * 100, mode="markers", name=name,
                                   marker=dict(size=5, color=color, opacity=0.65),
                                   hovertemplate="Sin cobertura: %{x:.1f} %<br>Con cobertura: %{y:.1f} %<extra>" + name + "</extra>"))
    lim = 40
    fig.add_trace(go.Scatter(x=[-lim, lim], y=[-lim, lim], mode="lines", name="Sin cobertura (y = x)",
                             line=dict(color="#475569", dash="dash")))
    fig.add_trace(go.Scatter(x=[-lim, lim], y=[-0.25 * lim, 0.25 * lim], mode="lines",
                             name="Cobertura perfecta del 75 % (y = 0,25x)", line=dict(color="#475569", dash="dot")))
    fig.update_xaxes(title_text="Desviación presupuestal sin cobertura (%)", range=[-lim, lim], ticksuffix=" %")
    fig.update_yaxes(title_text="Desviación presupuestal con cobertura (%)", range=[-lim * 0.6, lim * 0.6], ticksuffix=" %")
    return _layout(fig, 470, legend=dict(orientation="h", y=-0.2, x=0), margin=dict(l=64, r=28, t=30, b=70))


def budget_box(R: dict) -> go.Figure:
    fig = go.Figure()
    for dist in DISTS:
        bd = R["budget_box"][dist]
        for strat, label in (("u", "Sin cobertura"), ("h", "Con forward 75 %")):
            st = bd[strat]
            fig.add_trace(go.Box(
                x=[f"Año {y}" for y in HEDGE_YEARS], q1=st[25] * 100, median=st[50] * 100, q3=st[75] * 100,
                lowerfence=st[5] * 100, upperfence=st[95] * 100, mean=st["mean"] * 100, name=label,
                marker_color=STRAT_COLORS["sin" if strat == "u" else "con"], visible=dist == "normal",
                offsetgroup=strat, boxmean=True,
            ))
    n = len(fig.data)
    fig.update_layout(updatemenus=_menu([
        dict(label="Innovaciones normales", method="update", args=[{"visible": _visible(n, [0, 1])}]),
        dict(label="Innovaciones t de Student", method="update", args=[{"visible": _visible(n, [2, 3])}]),
    ], y=1.22), boxmode="group")
    fig.add_hline(y=0, line_color="#94a3b8")
    fig.update_yaxes(title_text="Desviación vs. presupuesto", ticksuffix=" %")
    return _layout(fig, 420, legend=dict(orientation="h", y=1.02, x=0.35), margin=dict(l=64, r=28, t=70, b=48))


def tails(R: dict) -> go.Figure:
    t = R["tails"]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Probabilidad de un choque > 3σ", "Cuantil 99,9 % (en σ)"))
    for dist, color in (("Normal", DIST_COLORS["normal"]), ("t de Student", DIST_COLORS["t"])):
        sub = t[t["dist"] == dist]
        x = [f"{h} mes" if h == 1 else f"{h} meses" for h in sub["horizonte"]]
        fig.add_trace(go.Bar(x=x, y=sub["p_3sd"] * 100, name=dist, marker_color=color,
                             hovertemplate="%{x}: %{y:.3f} %<extra>" + dist + "</extra>"), row=1, col=1)
        fig.add_trace(go.Bar(x=x, y=sub["q999"], name=dist, marker_color=color, showlegend=False,
                             hovertemplate="%{x}: %{y:.2f} σ<extra>" + dist + "</extra>"), row=1, col=2)
    fig.update_yaxes(ticksuffix=" %", row=1, col=1)
    fig.update_yaxes(range=[2.5, 4.3], row=1, col=2)
    return _layout(fig, 380, barmode="group", legend=dict(orientation="h", y=-0.15, x=0),
                   margin=dict(l=56, r=20, t=40, b=60))


# ----------------------------------------------------------------------------- B.3
def _scen_label(R: dict, key: str) -> str:
    return {s.key: s.nombre for s in R["scenarios"]}.get(key, "Neutral al riesgo")


def consolidated_table(R: dict) -> go.Figure:
    s0, a2 = R["s0"], R["a2"]
    sched = a2["schedule"]
    fig = go.Figure()
    combos = [(k, d, st) for k in ("central", "favorable", "adverso") for d in DISTS for st in STRATS]
    for i, (key, dist, strat) in enumerate(combos):
        f = R["flows"][(key, dist, strat)]
        t0 = [
            ("t0", "15/10/2026", "Compra de maquinaria amarilla", "", "", "", "", num(-a2["machine"])),
            ("t0", "15/10/2026", "Aporte propio (10 %)", "", "", "", "", num(a2["equity"])),
            ("t0", "15/10/2026", "Desembolso del crédito", num(a2["loan"].principal_usd, 2), num(s0, 2),
             "", "", num(a2["financed_cop"])),
        ]
        rows = list(t0)
        for q in range(40):
            fwd = f["forward_media"][q]
            rows.append((
                str(q + 1), sched["fecha"].iloc[q].strftime("%d/%m/%Y"), f"Cuota {q + 1} (año {sched['anio'].iloc[q]})",
                num(-sched["cuota"].iloc[q], 2), num(f["trm_media"][q], 2), num(-f["cuota_media"][q]),
                num(fwd) if abs(fwd) > 0 else "", num(-f["neto_media"][q]),
            ))
        rows.append(("Σ", "", "Total 40 cuotas", num(-sched["cuota"].sum(), 2), "", num(-f["cuota_media"].sum()),
                     num(f["forward_media"].sum()), num(-f["neto_media"].sum())))
        cols = list(map(list, zip(*rows, strict=True)))
        fill = ["#fff7e6" if r[0] in ("t0", "Σ") else ("#e8f5f3" if r[6] else "#f8fafc") for r in rows]
        fig.add_trace(go.Table(
            columnwidth=[38, 78, 170, 90, 80, 110, 100, 110],
            header=dict(values=["<b>Trim.</b>", "<b>Fecha</b>", "<b>Concepto</b>", "<b>USD</b>", "<b>TRM esperada</b>",
                                "<b>Cuota en COP</b>", "<b>Liquidación forward</b>", "<b>Flujo neto COP</b>"],
                        fill_color=PRIMARY, font=dict(color="white", size=12), align="center", height=30),
            cells=dict(values=cols, align=["center", "center", "left", "right", "right", "right", "right", "right"],
                       fill_color=[fill] * 8, font=dict(size=11.5), height=24),
            visible=i == 0,
        ))
    buttons = [dict(label=f"{_scen_label(R, k)} · {DISTS[d]} · {STRATS[st]}", method="update",
                    args=[{"visible": _visible(len(combos), [i])}]) for i, (k, d, st) in enumerate(combos)]
    fig.update_layout(updatemenus=_menu(buttons, y=1.09))
    return _layout(fig, 640, margin=dict(l=0, r=0, t=56, b=0))


def annual_service(R: dict) -> go.Figure:
    fig = go.Figure()
    combos = [(k, d) for k in ("central", "favorable", "adverso") for d in DISTS]
    years = [f"Año {y}" for y in range(1, 11)]
    for i, (key, dist) in enumerate(combos):
        for strat in STRATS:
            f = R["flows"][(key, dist, strat)]
            fig.add_trace(go.Bar(
                x=years, y=f["anual_media"] / 1e6, name=STRATS[strat], marker_color=STRAT_COLORS[strat],
                visible=i == 0,
                error_y=dict(type="data", symmetric=False, array=(f["anual_p95"] - f["anual_media"]) / 1e6,
                             arrayminus=(f["anual_media"] - f["anual_p5"]) / 1e6, thickness=1.2, color="#475569"),
                hovertemplate="%{x}<br>Media: COP %{y:,.1f} M<extra>" + STRATS[strat] + "</extra>",
            ))
    n = len(fig.data)
    buttons = [dict(label=f"{_scen_label(R, k)} · {DISTS[d]}", method="update",
                    args=[{"visible": _visible(n, [2 * i, 2 * i + 1])}]) for i, (k, d) in enumerate(combos)]
    fig.update_layout(updatemenus=_menu(buttons, y=1.22), barmode="group")
    fig.update_yaxes(title_text="COP millones por año", tickformat=",.0f")
    return _layout(fig, 440, legend=dict(orientation="h", y=1.02, x=0.42), margin=dict(l=64, r=28, t=70, b=48))


def irr_box(R: dict) -> go.Figure:
    fig = go.Figure()
    keys = ["favorable", "central", "adverso", "neutral"]
    for dist in DISTS:
        for strat in STRATS:
            st = R["irr_box"][dist][strat]
            fig.add_trace(go.Box(
                x=[_scen_label(R, k) for k in keys], q1=[st[k][25] * 100 for k in keys],
                median=[st[k][50] * 100 for k in keys], q3=[st[k][75] * 100 for k in keys],
                lowerfence=[st[k][5] * 100 for k in keys], upperfence=[st[k][95] * 100 for k in keys],
                mean=[st[k]["mean"] * 100 for k in keys], name=STRATS[strat], marker_color=STRAT_COLORS[strat],
                offsetgroup=strat, visible=dist == "normal", boxmean=True,
            ))
    loan_ea = R["a2"]["loan"].effective_annual_rate * 100
    fig.add_hline(y=loan_ea, line_dash="dot", line_color=ACCENT, annotation_text=f"Tasa USD {num(loan_ea, 2)} % E.A.",
                  annotation_position="bottom right", annotation_font_size=11)
    synth = R["synthetic"]["3Y"] * 100
    fig.add_hline(y=synth, line_dash="dash", line_color=RED,
                  annotation_text=f"Cobertura total en pesos (forward 3A): {num(synth, 2)} %",
                  annotation_position="top right", annotation_font_size=11)
    n = len(fig.data)
    fig.update_layout(updatemenus=_menu([
        dict(label="Innovaciones normales", method="update", args=[{"visible": _visible(n, [0, 1])}]),
        dict(label="Innovaciones t de Student", method="update", args=[{"visible": _visible(n, [2, 3])}]),
    ], y=1.22), boxmode="group")
    top = max(R["irr_box"][d][s][key][95] for d in DISTS for s in STRATS for key in keys) * 100
    fig.update_yaxes(title_text="TIR en COP (% E.A.)", ticksuffix=" %", range=[-2, top + 3])
    return _layout(fig, 460, legend=dict(orientation="h", y=1.02, x=0.35), margin=dict(l=64, r=28, t=70, b=48))


def frontier(R: dict) -> go.Figure:
    s = R["sens"]
    hr, strat = s["hedge_ratio"], s["strategies"]
    fig = make_subplots(rows=1, cols=2, subplot_titles=(
        "Desviación presupuestal vs. razón de cobertura", "Costo esperado vs. riesgo (años 7–10)"))
    fig.add_trace(go.Scatter(x=hr["ratio"] * 100, y=hr["dev_sd"] * 100, mode="lines+markers", name="Desv. estándar presupuestal",
                             line=dict(color=PRIMARY, width=2.4), marker=dict(size=9),
                             hovertemplate="Cobertura %{x:.1f} %<br>σ desviación: %{y:.2f} %<extra></extra>"), row=1, col=1)
    for x, label, color, pos in ((62.5, "Mín. varianza 62,5 %", GREEN, "bottom left"),
                                 (75, "Exigido 75 %", ACCENT, "bottom right")):
        fig.add_vline(x=x, line_dash="dot", line_color=color, row=1, col=1, annotation_text=label,
                      annotation_font_size=10, annotation_position=pos)
    colors = [GRAY, ACCENT, GREEN, PURPLE]
    fig.add_trace(go.Scatter(
        x=strat["costo_esperado"] / 1e6, y=strat["sd_cond"] / 1e6, mode="markers+text", text=strat["estrategia"],
        textposition=["top right", "bottom center", "top center", "top left"], textfont=dict(size=10),
        marker=dict(size=14, color=colors), showlegend=False,
        customdata=np.c_[strat["sd"] / 1e6, strat["dev_sd"] * 100],
        hovertemplate="%{text}<br>Costo esperado: COP %{x:,.2f} M<br>σ condicional: COP %{y:,.1f} M"
        "<br>σ incondicional: COP %{customdata[0]:,.1f} M<br>σ presupuestal: %{customdata[1]:.2f} %<extra></extra>",
    ), row=1, col=2)
    fig.update_xaxes(title_text="% de los pagos del año cubierto", row=1, col=1, ticksuffix=" %")
    fig.update_yaxes(title_text="σ (%)", row=1, col=1, ticksuffix=" %")
    fig.update_xaxes(title_text="Costo esperado de la cobertura (COP M)", row=1, col=2, range=[-0.8, 6.5])
    fig.update_yaxes(title_text="σ condicional a la TRM del año 6 (COP M)", row=1, col=2)
    return _layout(fig, 430, showlegend=False, margin=dict(l=64, r=28, t=50, b=56))


def sens_d(R: dict) -> go.Figure:
    d = R["sens"]["d"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x = [f"{num(v * 100, 2)} %" for v in d["d"]]
    fig.add_trace(go.Bar(x=x, y=d["forward_neto"] / 1e6, name="Resultado esperado de los 4 forwards (COP M)",
                         marker_color=[GREEN if v > 0 else RED for v in d["forward_neto"]],
                         hovertemplate="Prima forward %{x}<br>Resultado: COP %{y:,.2f} M<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=d["proteccion"] * 100, name="Probabilidad de protección (eje der.)",
                             mode="lines+markers", line=dict(color=PRIMARY, width=2.4),
                             hovertemplate="Prima %{x}<br>Protección: %{y:.1f} %<extra></extra>"), secondary_y=True)
    fig.update_xaxes(title_text="Prima forward anual (años 7–10)")
    fig.update_yaxes(title_text="COP millones", secondary_y=False)
    fig.update_yaxes(title_text="% de escenarios", secondary_y=True, ticksuffix=" %", showgrid=False, tickformat=".0f")
    return _layout(fig, 420, legend=dict(orientation="h", y=-0.3, x=0), margin=dict(l=64, r=56, t=20, b=90))


def sens_rate(R: dict) -> go.Figure:
    r = R["sens"]["rate"]
    fig = go.Figure()
    for col, name, color in (("tir_sin", "TIR en COP sin cobertura", GRAY), ("tir_con", "TIR en COP con forwards", GREEN),
                             ("ea", "Tasa del crédito en USD (E.A.)", ACCENT)):
        fig.add_trace(go.Scatter(x=r["tasa"] * 100, y=r[col] * 100, name=name, mode="lines+markers",
                                 line=dict(color=color, width=2.4),
                                 hovertemplate="Tasa nominal %{x:.2f} %<br>%{y:.2f} %<extra>" + name + "</extra>"))
    fig.update_xaxes(title_text="Tasa nominal anual del crédito (Prime + spread)", ticksuffix=" %")
    fig.update_yaxes(title_text="% E.A.", ticksuffix=" %")
    return _layout(fig, 380)


def build_all(R: dict) -> dict[str, str]:
    figs = {
        "trm_history": trm_history, "policy_rates": policy_rates, "inflation": inflation,
        "oil_correlation": oil_correlation, "projections": projections, "rate_benchmarks": rate_benchmarks,
        "amortization": amortization, "amortization_table": amortization_table, "cop_installments": cop_installments,
        "decomposition": decomposition, "waterfall": waterfall, "forward_curve": forward_curve,
        "cip_heatmap": cip_heatmap, "forwards_valuation": forwards_valuation, "ratio_hist": ratio_hist,
        "proportions": proportions, "budget_scatter": budget_scatter, "budget_box": budget_box, "tails": tails,
        "consolidated_table": consolidated_table, "annual_service": annual_service, "irr_box": irr_box,
        "frontier": frontier, "sens_d": sens_d, "sens_rate": sens_rate,
    }
    return {name: to_div(fn(R), f"fig-{name.replace('_', '-')}") for name, fn in figs.items()}
