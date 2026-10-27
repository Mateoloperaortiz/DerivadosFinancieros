"""Gráficos interactivos (Plotly) de la Parte 2."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..parte2.data import yahoo
from .figures import ACCENT, GRAY, GREEN, PRIMARY, PURPLE, RED, _layout, _menu, _visible, to_div

TK_COLORS = {"MSFT": "#1d4e89", "WMT": "#2a9d8f", "XOM": "#c8553d", "S&P 500": "#8d99ae", "Portafolio": "#e3a21a"}
STRAT_COLORS = {"sin": "#64748b", "corto": GREEN, "largo": RED}
STRAT_NAMES = {"sin": "Sin cobertura", "corto": "Cobertura corta (β)", "largo": "Siempre largo"}


def price_12m(R: dict) -> go.Figure:
    cut, t0 = R["cut"], R["t0"]
    start = cut - pd.DateOffset(years=1)
    last = R["expost"]["fecha"]
    fig = go.Figure()
    for t in R["cfg"]["portafolio"]["tickers"]:
        s = yahoo(t)["adjclose"].loc[start:last]
        s = 100 * s / s.iloc[0]
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=t, line=dict(color=TK_COLORS[t], width=2),
                                 hovertemplate=f"{t}<br>%{{x|%d %b %Y}}: %{{y:.1f}}<extra></extra>"))
    s = yahoo("^GSPC")["close"].loc[start:last]
    s = 100 * s / s.iloc[0]
    fig.add_trace(go.Scatter(x=s.index, y=s.values, name="S&P 500 (precio)", line=dict(color=GRAY, width=2, dash="dot"),
                             hovertemplate="S&P 500<br>%{x|%d %b %Y}: %{y:.1f}<extra></extra>"))
    fig.add_vrect(x0=t0, x1=last, fillcolor="#fde68a", opacity=0.3, line_width=0, layer="below",
                  annotation_text="Después de la decisión (solo verificación ex post)", annotation_position="top left",
                  annotation_font_size=11)
    fig.add_vline(x=cut, line_dash="dash", line_color="#334155")
    fig.update_yaxes(title_text="Base 100 = 29-jul-2025 (retorno total)")
    return _layout(fig, 430)


def growth(R: dict) -> go.Figure:
    px = R["rb"]["prices"]
    g = (100 * px / px.iloc[0]).resample("W-FRI").last()
    fig = go.Figure()
    for t in g.columns:
        fig.add_trace(go.Scatter(x=g.index, y=g[t], name=t, line=dict(color=TK_COLORS[t], width=1.7),
                                 hovertemplate=f"{t}<br>%{{x|%d %b %Y}}: %{{y:,.0f}}<extra></extra>"))
    spx = yahoo("^SP500TR")["close"].loc[g.index[0]:g.index[-1]]
    spx = (100 * spx / spx.iloc[0]).resample("W-FRI").last()
    fig.add_trace(go.Scatter(x=spx.index, y=spx.values, name="S&P 500 total return", line=dict(color=GRAY, dash="dot"),
                             hovertemplate="S&P 500 TR<br>%{x|%d %b %Y}: %{y:,.0f}<extra></extra>"))
    fig.update_yaxes(title_text="USD 100 invertidos (log)", type="log")
    fig.update_xaxes(rangeslider_visible=True)
    return _layout(fig, 460)


def by_year(R: dict) -> go.Figure:
    by = R["rb"]["by_year"]
    fig = go.Figure()
    for t in by.columns:
        fig.add_trace(go.Bar(x=by.index.astype(str), y=100 * by[t], name=t, marker_color=TK_COLORS[t],
                             hovertemplate=f"{t} %{{x}}: %{{y:.1f}} %<extra></extra>"))
    fig.update_yaxes(title_text="Retorno total anual", ticksuffix=" %")
    fig.update_xaxes(title_text="2016 desde agosto · 2026 hasta el 29 de julio")
    return _layout(fig, 380, barmode="group")


def correlation(R: dict) -> go.Figure:
    c = R["rb"]["corr"]
    fig = go.Figure(go.Heatmap(z=c.values, x=c.columns, y=c.index, zmin=-1, zmax=1, colorscale="RdBu_r",
                               text=[[f"{v:.2f}".replace(".", ",") for v in row] for row in c.values],
                               texttemplate="%{text}", hovertemplate="%{y}–%{x}: %{z:.4f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return _layout(fig, 360, margin=dict(l=60, r=20, t=20, b=40))


def frontier(R: dict) -> go.Figure:
    o, rf = R["opt"], R["rf_s"]
    cl = o["cloud"]
    st = R["rb"]["stats"]
    fig = go.Figure()
    idx = np.random.default_rng(1).choice(len(cl["ret"]), 4000, replace=False)
    fig.add_trace(go.Scatter(x=100 * cl["vol"][idx], y=100 * cl["ret"][idx], mode="markers", name="Combinaciones factibles",
                             marker=dict(size=4, color=cl["sharpe"][idx], colorscale="Viridis", opacity=0.55,
                                         colorbar=dict(title="Sharpe", thickness=12, len=0.6)),
                             hovertemplate="σ %{x:.2f} % · E(R) %{y:.2f} %<extra></extra>"))
    fr = o["frontier"]
    fig.add_trace(go.Scatter(x=100 * fr[:, 0], y=100 * fr[:, 1], mode="lines", name="Frontera eficiente",
                             line=dict(color=PRIMARY, width=3)))
    xs = np.linspace(0, 100 * o["vol"] * 1.35, 20)
    fig.add_trace(go.Scatter(x=xs, y=100 * rf + xs * o["sharpe"], mode="lines", name="Línea del mercado de capitales",
                             line=dict(color=ACCENT, dash="dash")))
    fig.add_trace(go.Scatter(x=[100 * o["vol"]], y=[100 * o["ret"]], mode="markers", name="Máximo Sharpe",
                             marker=dict(size=16, symbol="star", color=RED, line=dict(color="black", width=1))))
    fig.add_trace(go.Scatter(x=[100 * o["vol_mv"]], y=[100 * o["ret_mv"]], mode="markers", name="Mínima varianza",
                             marker=dict(size=13, symbol="diamond", color=ACCENT, line=dict(color="black", width=1))))
    fig.add_trace(go.Scatter(x=100 * st["vol"], y=100 * st["ret_arit"], mode="markers+text", text=st.index,
                             textposition="top center", name="Acciones individuales",
                             marker=dict(size=11, color=[TK_COLORS[t] for t in st.index])))
    fig.update_xaxes(title_text="Volatilidad anual", ticksuffix=" %", range=[0, 32])
    fig.update_yaxes(title_text="Retorno esperado anual (histórico)", ticksuffix=" %", range=[0, 27])
    return _layout(fig, 500)


def var_hist(R: dict) -> go.Figure:
    v = R["var"]
    r = 100 * v["roll21"]
    fig = go.Figure(go.Histogram(x=r, nbinsx=90, marker_color="#9fb6cc", name="Retornos de 21 días (ventanas móviles)",
                                 hovertemplate="%{x:.1f} %: %{y} ventanas<extra></extra>"))
    tb = v["table"]
    cnt, _ = np.histogram(r, bins=90)
    top = float(cnt.max()) * 1.05
    for _, row in tb.iterrows():
        c = int(round(row["conf"] * 100))
        for val, col, tag in ((row["var_pct"], RED, "paramétrico"), (row["hist_pct"], PRIMARY, "histórico")):
            x = -100 * val
            fig.add_trace(go.Scatter(x=[x, x], y=[0, top], mode="lines", name=f"VaR {tag} {c} %: {x:.2f} %".replace(".", ","),
                                     line=dict(color=col, dash="dash" if c == 95 else "solid", width=2),
                                     hovertemplate=f"VaR {tag} {c} %: %{{x:.2f}} %<extra></extra>"))
    fig.update_xaxes(title_text="Retorno del portafolio en 21 días hábiles", ticksuffix=" %")
    fig.update_yaxes(title_text="Frecuencia")
    return _layout(fig, 420, legend=dict(orientation="h", y=1.12, x=0))


def beta_scatter(R: dict) -> go.Figure:
    df = R["bt"]["sample"]
    tk = R["cfg"]["portafolio"]["tickers"]
    w = R["w"]
    df = df.assign(Portafolio=df[tk] @ w)
    sub = df.sample(1500, random_state=3)
    names = tk + ["Portafolio"]
    fig = go.Figure()
    xs = np.linspace(-0.07, 0.07, 10)
    for j, n in enumerate(names):
        b = R["bt"]["table"][n]
        fig.add_trace(go.Scatter(x=100 * sub["mkt"], y=100 * sub[n], mode="markers", name=f"{n}: retornos diarios",
                                 marker=dict(size=4, color=TK_COLORS[n], opacity=0.45), visible=j == len(names) - 1,
                                 hovertemplate="S&P %{x:.2f} % · " + n + " %{y:.2f} %<extra></extra>"))
        fig.add_trace(go.Scatter(x=100 * xs, y=100 * (b["alpha"] + b["beta"] * xs), mode="lines",
                                 name=f"Recta CAPM: β = {b['beta']:.3f}".replace(".", ","),
                                 line=dict(color="black", width=2), visible=j == len(names) - 1))
    buttons = [dict(label=n, method="update", args=[{"visible": _visible(2 * len(names), [2 * j, 2 * j + 1])}])
               for j, n in enumerate(names)]
    menu = _menu(buttons, y=1.2)
    menu[0]["active"] = len(names) - 1
    fig.update_layout(updatemenus=menu)
    fig.update_xaxes(title_text="Retorno diario del S&P 500", ticksuffix=" %", range=[-7, 7])
    fig.update_yaxes(title_text="Retorno diario del activo", ticksuffix=" %", range=[-10, 10])
    return _layout(fig, 440, legend=dict(orientation="h", y=1.02, x=0.25))


def beta_rolling(R: dict) -> go.Figure:
    fig = go.Figure()
    for n, s in R["bt"]["rolling"].items():
        s = s.resample("W-FRI").last()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=n, line=dict(color=TK_COLORS[n], width=2.6 if n == "Portafolio" else 1.6),
                                 hovertemplate=f"{n}<br>%{{x|%b %Y}}: β = %{{y:.2f}}<extra></extra>"))
    fig.add_hline(y=1, line_dash="dot", line_color="#94a3b8")
    fig.update_yaxes(title_text="Beta móvil (2 años, 504 días)")
    return _layout(fig, 400)


def payoff(R: dict) -> go.Figure:
    v0, bp, n, f0, m = R["v0"], R["beta_p"], R["n"], R["f0"], R["mult"]
    x = np.linspace(-0.30, 0.30, 61)
    port = bp * x * v0
    short = -n * m * f0 * x
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=100 * x, y=port / 1e6, name="Portafolio sin cobertura (β·V·ΔS/S)", line=dict(color=GRAY, width=2.5)))
    fig.add_trace(go.Scatter(x=100 * x, y=short / 1e6, name=f"{n} futuros cortos", line=dict(color=RED, dash="dash")))
    fig.add_trace(go.Scatter(x=100 * x, y=(port + short) / 1e6, name="Portafolio + futuros cortos", line=dict(color=GREEN, width=3)))
    fig.add_trace(go.Scatter(x=100 * x, y=(port - short) / 1e6, name=f"Portafolio + {n} futuros largos",
                             line=dict(color=PURPLE, dash="dot"), visible="legendonly"))
    fig.add_hline(y=0, line_color="#94a3b8")
    fig.update_xaxes(title_text="Variación del S&P 500 en el periodo", ticksuffix=" %")
    fig.update_yaxes(title_text="Ganancia o pérdida (USD millones)")
    return _layout(fig, 420)


def margin(R: dict) -> go.Figure:
    tl, h = R["tl"], R["strat"]["corto"]
    imf, mm = R["imf"], R["mm_s"]
    labels = {"p5": "Mercado bajista (P5 del S&P final)", "p50": "Escenario central (mediana)", "p95": "Mercado alcista (P95)"}
    fig = go.Figure()
    for key in labels:
        k = R["rep"][key]
        vis = key == "p50"
        x = tl["fecha"]
        N = h["N"][k]
        fig.add_trace(go.Scatter(x=x, y=h["bal"][k] / 1e6, name="Saldo después de reposición", line=dict(color=PRIMARY, width=2.4),
                                 visible=vis, hovertemplate="%{x|%b %Y}: USD %{y:.3f} M<extra></extra>"))
        fig.add_trace(go.Scatter(x=x, y=h["pre"][k] / 1e6, name="Saldo antes del llamado", mode="markers",
                                 marker=dict(size=5, color="#9fb6cc"), visible=vis,
                                 hovertemplate="%{x|%b %Y}: USD %{y:.3f} M<extra></extra>"))
        fig.add_trace(go.Scatter(x=x, y=N * mm * imf / 1e6, name="Margen inicial", line=dict(color=ACCENT, dash="dash", shape="hv"),
                                 visible=vis))
        fig.add_trace(go.Scatter(x=x, y=N * mm / 1e6, name="Margen de mantenimiento", line=dict(color=RED, dash="dot", shape="hv"),
                                 visible=vis))
        c = h["call"][k]
        fig.add_trace(go.Bar(x=x[c], y=h["dep"][k][c] / 1e6, name="Reposición por llamado", marker_color=RED, opacity=0.6,
                             visible=vis, hovertemplate="%{x|%b %Y}: USD %{y:.3f} M<extra>Llamado al margen</extra>"))
    n_tr = 5 * len(labels)
    buttons = [dict(label=lab, method="update", args=[{"visible": _visible(n_tr, list(range(5 * j, 5 * j + 5)))}])
               for j, lab in enumerate(labels.values())]
    fig.add_vrect(x0=tl["fecha"].iloc[0], x1=tl["fecha"].iloc[R["last_i"]], fillcolor="#fde68a", opacity=0.35,
                  line_width=0, layer="below", annotation_text="Datos reales", annotation_position="top left")
    menu = _menu(buttons, y=1.22)
    menu[0]["active"] = 1
    fig.update_layout(updatemenus=menu)
    fig.update_yaxes(title_text="USD millones")
    return _layout(fig, 450, legend=dict(orientation="h", y=-0.18, x=0))


def wealth_fan(R: dict) -> go.Figure:
    tl = R["tl"]
    x = tl["fecha"]
    fig = go.Figure()
    fills = {"sin": "rgba(100,116,139,0.18)", "corto": "rgba(42,157,143,0.22)", "largo": "rgba(200,85,61,0.13)"}
    for key in ("largo", "sin", "corto"):
        Wk = R["W"][key] / 1e6
        p5, p50, p95 = (np.percentile(Wk, p, axis=0) for p in (5, 50, 95))
        fig.add_trace(go.Scatter(x=x, y=p95, line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=p5, fill="tonexty", fillcolor=fills[key], line=dict(width=0),
                                 name=f"{STRAT_NAMES[key]}: P5–P95", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=p50, name=f"{STRAT_NAMES[key]}: mediana", line=dict(color=STRAT_COLORS[key], width=2.4),
                                 hovertemplate="%{x|%b %Y}: USD %{y:.2f} M<extra>" + STRAT_NAMES[key] + "</extra>"))
    fig.add_vrect(x0=x.iloc[0], x1=x.iloc[R["last_i"]], fillcolor="#fde68a", opacity=0.35, line_width=0, layer="below")
    fig.update_yaxes(title_text="Riqueza: acciones + resultado de futuros (USD M)")
    return _layout(fig, 470, legend=dict(orientation="h", y=-0.2, x=0))


def terminal_hist(R: dict) -> go.Figure:
    fig = go.Figure()
    for key in ("sin", "corto", "largo"):
        r = 100 * (R["W"][key][:, -1] / R["v0"] - 1)
        cnt, edges = np.histogram(r, bins=np.arange(-100, 305, 5))
        fig.add_trace(go.Bar(x=edges[:-1] + 2.5, y=100 * cnt / len(r), width=5, name=STRAT_NAMES[key],
                             marker_color=STRAT_COLORS[key], opacity=0.55,
                             hovertemplate="%{x:.0f} %: %{y:.1f} % de trayectorias<extra></extra>"))
    fig.add_vline(x=0, line_color="black")
    fig.update_xaxes(title_text="Retorno acumulado a 4 años (30-jul-2030)", ticksuffix=" %", range=[-80, 250])
    fig.update_yaxes(title_text="% de trayectorias")
    return _layout(fig, 400, barmode="overlay")


def quarters(R: dict) -> go.Figure:
    q = R["quarters"]
    lab = [f"{a.strftime('%b-%y')}→{b.strftime('%b-%y')}" for a, b in zip(q["desde"], q["hasta"], strict=True)]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=lab, y=q["pnl_media"] / 1e3, name="Resultado esperado de los futuros cortos (USD miles)",
                         marker_color=[ACCENT if o else RED for o in q["obs"]],
                         error_y=dict(type="data", symmetric=False, array=(q["pnl_p95"] - q["pnl_media"]) / 1e3,
                                      arrayminus=(q["pnl_media"] - q["pnl_p5"]) / 1e3, color="#94a3b8"),
                         hovertemplate="%{x}: USD %{y:,.0f} mil<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=lab, y=q["spread_roll"], name="Spread del roll (F nuevo − F viejo, puntos)", mode="lines+markers",
                             line=dict(color=PRIMARY)), secondary_y=True)
    fig.update_yaxes(title_text="USD miles (P5–P95)", secondary_y=False)
    fig.update_yaxes(title_text="Puntos del índice", secondary_y=True, showgrid=False, tickformat=".0f", range=[0, 100])
    fig.update_xaxes(tickangle=-45, tickfont=dict(size=10))
    return _layout(fig, 430, legend=dict(orientation="h", y=1.08, x=0))


def expected(R: dict) -> go.Figure:
    tl = R["tl"]
    x = tl["fecha"]
    v0 = R["v0"]
    t = np.array([(d - R["t0"]).days / 365.25 for d in x])
    fig = go.Figure()
    for key in ("sin", "corto"):
        m = R["W"][key].mean(axis=0) / 1e6
        fig.add_trace(go.Scatter(x=x, y=m, name=f"{STRAT_NAMES[key]}: media simulada", line=dict(color=STRAT_COLORS[key], width=3)))
    fig.add_trace(go.Scatter(x=x, y=v0 * (1 + R["capm"]["Portafolio"]) ** t / 1e6, name="CAPM: V₀(1 + rf + β·PRM)^t",
                             line=dict(color=GRAY, dash="dash")))
    fig.add_trace(go.Scatter(x=x, y=v0 * (1 + R["rf_h"]) ** t / 1e6, name="Libre de riesgo: V₀(1 + rf)^t",
                             line=dict(color=GREEN, dash="dot")))
    fig.update_yaxes(title_text="Valor esperado (USD M)")
    return _layout(fig, 400, legend=dict(orientation="h", y=-0.2, x=0))


def beta_sens(R: dict) -> go.Figure:
    v0 = R["v0"]
    x = np.linspace(-0.3, 0.3, 61)
    fig = go.Figure()
    colors = {0: GREEN, 1: ACCENT, 2: RED}
    for j, row in R["sens_beta"].reset_index(drop=True).iterrows():
        b = row["beta"]
        lab = f"β = {b:.2f}".replace(".", ",")
        fig.add_trace(go.Scatter(x=100 * x, y=b * x * v0 / 1e6, name=f"{lab} sin cobertura", line=dict(color=colors[j], width=2.5)))
        fig.add_trace(go.Scatter(x=100 * x, y=row["beta_res"] * x * v0 / 1e6, name=f"{lab} con {int(row['n'])} cortos",
                                 line=dict(color=colors[j], dash="dot")))
    fig.add_hline(y=0, line_color="#94a3b8")
    fig.update_xaxes(title_text="Variación del S&P 500", ticksuffix=" %")
    fig.update_yaxes(title_text="Ganancia o pérdida sistemática (USD M)")
    return _layout(fig, 420, legend=dict(orientation="h", y=-0.22, x=0))


def expost(R: dict) -> go.Figure:
    e = R["expost"]
    v = e["series"] / 1e6
    h = (e["series"] + e["fut_cum"]) / 1e6
    spx = yahoo("^GSPC")["close"].loc[v.index]
    spx = R["invested"] * spx / spx.iloc[0] / 1e6
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v.index, y=v.values, name="Portafolio sin cobertura", line=dict(color=GRAY, width=2.4)))
    fig.add_trace(go.Scatter(x=h.index, y=h.values, name="Portafolio + futuros cortos", line=dict(color=GREEN, width=2.8)))
    fig.add_trace(go.Scatter(x=spx.index, y=spx.values, name="USD 20 M en el S&P 500 (precio)", line=dict(color=PRIMARY, dash="dot")))
    fig.add_vline(x=pd.Timestamp("2026-08-31"), line_dash="dash", line_color="#94a3b8",
                  annotation_text="Roll ESU26 → ESZ26", annotation_position="top left", annotation_font_size=10)
    fig.update_yaxes(title_text="USD millones")
    return _layout(fig, 400)


def build_all(R: dict) -> dict[str, str]:
    figs = {
        "p2_price12m": price_12m, "p2_growth": growth, "p2_byyear": by_year, "p2_corr": correlation, "p2_frontier": frontier,
        "p2_var": var_hist, "p2_beta_scatter": beta_scatter, "p2_beta_rolling": beta_rolling, "p2_payoff": payoff,
        "p2_margin": margin, "p2_fan": wealth_fan, "p2_terminal": terminal_hist, "p2_quarters": quarters,
        "p2_expected": expected, "p2_beta_sens": beta_sens, "p2_expost": expost,
    }
    return {k: to_div(f(R), k) for k, f in figs.items()}
