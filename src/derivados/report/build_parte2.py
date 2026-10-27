"""Genera docs/parte2.html: portafolio MSFT–WMT–XOM y cobertura con futuros E-mini S&P 500.

Uso: uv run python -m derivados.report.build_parte2
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import plotly.offline as po
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..data import ROOT, manual_inputs
from ..parte2.model import build, code, label
from . import figures_p2
from .fmt import FILTERS, fecha, num, pct, usd
from .tables import html_table

TEMPLATES = Path(__file__).parent / "templates"
OUTPUT = ROOT / "docs" / "parte2.html"


def musd(x: float, d: int = 2) -> str:
    return f"USD {num(x / 1e6, d)} M"


def kusd(x: float) -> str:
    return f"USD {num(x / 1e3, 0)} mil"


# ----------------------------------------------------------------------------- tablas
def t_prices(R: dict) -> str:
    pb = R["prices"]
    rows = []
    for t, r in pb.iterrows():
        dy = pct(r["dy"]) if t != "S&P 500" else pct(R["q_idx"]) + "*"
        close = usd(r["close"]) if t != "S&P 500" else f"{num(r['close'], 2)} pts"
        rows.append([f"<b>{t}</b>", close, pct(r["ytd"], 1, True), pct(r["r12"], 1, True), pct(r["r3"], 1, True),
                     f"{num(r['lo52'], 2)} – {num(r['hi52'], 2)}", pct(r["dist_hi"], 1, True), dy])
    return html_table(["Activo", "Cierre 29-jul-2026", "En 2026", "12 meses", "3 meses", "Rango 52 semanas", "Vs. máximo 52 sem.",
                       "Rend. dividendo 12 m"], rows, "lrrrrrrr",
                      caption="Retornos totales (precios ajustados por dividendos) para las acciones; el S&P 500 es índice de precio. "
                              "*Rendimiento por dividendo del índice estimado con ^SP500TR frente a ^GSPC. Fuente: Yahoo Finance.")


def t_expected_price(R: dict) -> str:
    rows = []
    for t in R["cfg"]["portafolio"]["tickers"]:
        e, p0 = R["exp_price"][t], R["px0"][t]
        rows.append([f"<b>{t}</b>", usd(p0), num(R["bt"]["table"][t]["beta"], 3), pct(R["capm"][t]), usd(R["div_fwd"][t], 3),
                     f"<b>{usd(e['capm'])}</b> ({pct(e['capm'] / p0 - 1, 1, True)})", f"{usd(e['lo'])} – {usd(e['hi'])}",
                     f"{usd(e['hist'])} ({pct(e['hist'] / p0 - 1, 1, True)})"])
    return html_table(["Acción", "P₀ (compra, 30-jul-2026)", "β", "Retorno CAPM", "Dividendo esperado 12 m", "Precio esperado jul-2027 (CAPM)",
                       "Rango ±1σ", "Con el promedio histórico"], rows, "lrrrrrrr",
                      caption="E[P₁] = P₀·(1 + E[R]) − D₁, con D₁ = 4 × el último dividendo trimestral: el retorno total esperado incluye el dividendo, que no se refleja en el precio.")


def t_stats(R: dict) -> str:
    st = R["rb"]["stats"]
    rows = [[f"<b>{t}</b>", pct(r["media_d"], 4), pct(r["ret_arit"]), pct(r["ret_geo"]), pct(r["vol"]), num(r["var_a"], 6),
             pct(r["min"], 2), pct(r["max"], 2), num(r["asim"], 2), num(r["curt"], 2)] for t, r in st.iterrows()]
    return html_table(["Acción", "Retorno diario medio", "Retorno anual aritmético (×252)", "Retorno anual geométrico",
                       "Volatilidad anual (×√252)", "Varianza anual", "Peor día", "Mejor día", "Asimetría", "Exceso de curtosis"],
                      rows, "lrrrrrrrrr", cls="compact")


def t_matrix(df, d: int = 6) -> str:
    rows = [[f"<b>{i}</b>", *[num(v, d) for v in r]] for i, r in df.iterrows()]
    return html_table(["", *df.columns], rows, "l" + "r" * len(df.columns), cls="narrow")


def t_weights(R: dict) -> str:
    o, tk, cap = R["opt"], R["cfg"]["portafolio"]["tickers"], R["cfg"]["portafolio"]["capital_usd"]
    rows = []
    for j, t in enumerate(tk):
        rows.append([f"<b>{R['cfg']['portafolio']['nombres'][t]}</b> ({t})", pct(o["w"][j], 2), usd(o["w"][j] * cap),
                     usd(R["px0"][t]), num(R["shares"][t]), usd(R["shares"][t] * R["px0"][t]), pct(o["w_mv"][j], 2)])
    rows.append(["<b>Total</b>", "100,00 %", usd(cap), "", "", usd(R["invested"]), "100,00 %"])
    return html_table(["Acción", "Peso máximo Sharpe", "Monto objetivo", "Precio de compra (cierre 30-jul)", "Acciones",
                       "Monto ejecutado", "Peso mínima varianza"], rows, "lrrrrrr", highlight={len(rows) - 1},
                      caption=f"Efectivo no invertido por redondeo a acciones enteras: {usd(R['cash'])}.")


def t_var(R: dict) -> str:
    rows = []
    for _, r in R["var"]["table"].iterrows():
        c = int(round(r["conf"] * 100))
        rows.append([f"<b>{c} %</b> (VaR al {100 - c} %)", num(r["z"], 4), pct(r["var_pct"]), usd(r["var_usd"]),
                     usd(R["v0"] - r["var_usd"]), pct(r["var0_pct"]), usd(r["var0_usd"]), pct(r["hist_pct"]), usd(r["hist_usd"])])
    return html_table(["Confianza", "z", "VaR paramétrico", "VaR en USD", "Valor tras la pérdida", "Sin descontar la media",
                       "En USD", "VaR histórico", "En USD"], rows, "lrrrrrrrr", cls="compact")


def t_beta(R: dict) -> str:
    rows = []
    for n, b in R["bt"]["table"].items():
        rows.append([f"<b>{n}</b>", num(b["beta"], 3), num(b["se_beta"], 3), num(b["t_beta"], 1),
                     f"[{num(b['beta'] - 1.96 * b['se_beta'], 3)}; {num(b['beta'] + 1.96 * b['se_beta'], 3)}]",
                     num(b["r2"], 3), num(b["corr"], 3), pct(b["alpha_a"], 2, True), pct(b["resid_vol"]),
                     pct(R["capm"][n])])
    return html_table(["Activo", "β", "Error estándar", "t", "IC 95 %", "R²", "ρ con S&P", "α anual (Jensen)",
                       "Vol. idiosincrática", "E[R] CAPM"], rows, "lrrrrrrrrr", highlight={len(rows) - 1}, cls="compact",
                      caption="Regresión de excesos de retorno diarios (rf diaria = ^IRX/252) sobre el exceso del S&P 500, "
                              f"{fecha(R['cfg']['portafolio']['inicio_muestra'])} a {fecha(R['cut'])}; "
                              f"E[R] = rf + β·PRM con rf = {pct(R['rf_h'])} y PRM = {pct(R['erp'], 1)}.")


def t_specs(R: dict) -> str:
    f = R["cfg"]["futuro"]
    rows = [
        ["Contrato", escape(f["nombre"]) + f", {escape(f['bolsa'])}"],
        ["Activo subyacente", escape(f["subyacente"])],
        ["Multiplicador y tamaño", f"USD {f['multiplicador']} × índice → {usd(R['f0'] * R['mult'], 0)} por contrato al 30-jul-2026"],
        ["Fluctuación mínima", escape(f["tick"])],
        ["Vencimientos disponibles", escape(f["vencimientos"])],
        ["Contrato inicial", f"{label(*R['tl'].loc[0, 'old'])}, vence el {fecha(R['tl_exp0'])}"],
        ["Precio inicial del futuro", f"{num(R['f0'], 2)} puntos (cierre 30-jul-2026) frente a S&P 500 en {num(R['s0'], 2)}"],
        ["Último día de negociación", escape(f["ultimo_dia"])],
        ["Mecanismo de liquidación", escape(f["liquidacion"])],
        ["Ajuste a mercado", escape(f["mark_to_market"]) + "; en este trabajo se evalúa con liquidaciones mensuales"],
        ["Margen de mantenimiento", f"{usd(R['mm_s'], 0)} por contrato corto ({usd(R['mm_l'], 0)} largo)"],
        ["Margen inicial", f"{usd(R['mm_s'] * R['imf'], 0)} por contrato corto ({pct(R['imf'], 0)} del de mantenimiento)"],
        ["Fuente", f"<a href=\"{f['url_specs']}\">CME Group, especificaciones</a> y <a href=\"{f['url_margen']}\">márgenes</a> (consulta 27-oct-2026)"],
    ]
    return html_table(["Característica", "Detalle"], rows, "ll", cls="kv")


def t_contracts(R: dict) -> str:
    rows = []
    for o in R["n_opts"]:
        sel = o["n"] == R["n"]
        rows.append([f"<b>{o['n']}</b>" + (" ✔" if sel else ""), musd(o["cubierto"]), pct(o["h"], 1), num(o["beta_res"], 4),
                     usd(o["exp_res"], 0), "Subcobertura: queda exposición larga" if o["beta_res"] > 0 else "Sobrecobertura: posición neta corta"])
    return html_table(["Contratos", "Nocional cubierto", "% de la exposición β·V", "β residual", "Exposición residual", "Lectura"],
                      rows, "lrrrrl", highlight={i for i, o in enumerate(R["n_opts"]) if o["n"] == R["n"]})


def t_margin_path(R: dict, key: str) -> str:
    tl, h, sim = R["tl"], R["strat"]["corto"], R["sim"]
    k = R["rep"][key]
    rows = []
    for i in range(1, len(tl)):
        r = tl.iloc[i]
        f_ini, f_fin = sim["Fn"][k, i - 1], sim["Fo"][k, i]
        N_prev = h["N"][k, i - 1]
        d_f = f_fin - f_ini
        g_long = N_prev * R["mult"] * d_f
        contr = code(*r["old"])
        if r["roll"]:
            contr += f" → {code(*r['new'])} a {num(sim['Fn'][k, i], 2)}"
        src = "Real" if i <= R["last_i"] else "Simulado"
        rows.append([fecha(r["fecha"]), src, contr, num(N_prev), num(f_ini, 2), num(f_fin, 2), num(d_f, 2),
                     usd(g_long, 0), usd(-g_long, 0), usd(h["pre"][k, i], 0),
                     "<b class='up'>Sí</b>" if h["call"][k, i] else ("Depósito por roll" if h["rdep"][k, i] else "No"),
                     usd(h["dep"][k, i], 0), usd(h["bal"][k, i], 0)])
    return html_table(["Liquidación", "Dato", "Contrato", "N", "Precio inicial", "Precio final", "Variación", "G/P posición larga",
                       "G/P posición corta", "Saldo antes del llamado", "Llamado", "Reposición", "Saldo final"], rows,
                      "lllrrrrrrrcrr", cls="compact")


def t_quarters(R: dict) -> str:
    rows = []
    for _, q in R["quarters"].iterrows():
        rows.append([f"{fecha(q['desde'])} → {fecha(q['hasta'])}", ("Real" if q["obs"] else "Sim."), q["cierra"], q["abre"],
                     usd(q["pnl_central"], 0), usd(q["pnl_media"], 0), f"{usd(q['pnl_p5'], 0)} / {usd(q['pnl_p95'], 0)}",
                     "n. a." if np.isnan(q["spread_roll"]) else num(q["spread_roll"], 1), num(q["base_cierre"], 1),
                     pct(q["r_u"], 2), pct(q["r_h"], 2), pct(q["p_call"], 1)])
    return html_table(["Trimestre", "Dato", "Cierra", "Abre", "G/P realizada (escenario central)", "G/P esperada",
                       "P5 / P95", "Spread del roll (pts)", "Base al cierre (pts)", "Retorno esperado sin cobertura",
                       "Retorno esperado cubierto", "P(llamado)"], rows, "llllrrrrrrrr", cls="compact",
                      caption="G/P realizada: resultado de cerrar la posición del trimestre en la trayectoria central (la misma de la tabla del punto 8); "
                              "el primer trimestre es real en todas las trayectorias.")


def t_strategies(R: dict) -> str:
    names = {"sin": "Sin cobertura", "corto": f"Siempre corto ({R['n']} contratos, rebalanceo en cada roll)",
             "corto_fijo": f"Siempre corto con {R['n']} contratos fijos", "largo": "Siempre largo (mismo número de contratos)"}
    rows = []
    for key in ("sin", "corto", "corto_fijo", "largo"):
        t = R["term"][key]
        rows.append([f"<b>{names[key]}</b>", musd(t["media"]), pct(t["r_media"], 1, True), pct((1 + t["r_media"]) ** (1 / R["years"]) - 1, 2),
                     musd(t["sd"]), musd(t["p5"]), musd(t["p95"]), musd(t["cvar5"]), pct(t["p_loss"], 1)])
    return html_table(["Estrategia", "Riqueza media jul-2030", "Retorno acumulado", "Equivalente anual", "Desviación",
                       "P5", "P95", "CVaR 5 %", "P(perder capital)"], rows, "lrrrrrrrr", highlight={1})


def t_rates(R: dict) -> str:
    tsy = R["tsy"]
    rows = [
        ["Treasury 3 meses (par yield)", pct(tsy["3 Mo"]), "Sharpe del punto 3 (alternativa de liquidez a corto plazo)"],
        ["^IRX (T-bill 13 semanas, tasa de descuento)", pct(R["irx"]), "Tasa diaria del exceso de retorno en la regresión CAPM"],
        ["Treasury 3 años (par yield)", pct(tsy["3 Yr"]), "Referencia del tramo 3–5 años"],
        ["Treasury 5 años (par yield)", pct(tsy["5 Yr"]), "Contraste oficial de ^FVX"],
        ["<b>^FVX (CBOE 5-Year Treasury Yield Index)</b>", f"<b>{pct(R['fvx'], 3)}</b> → {pct(R['rf_h'], 3)} E.A.",
         "<b>Tasa libre de riesgo del horizonte (puntos 10–12, CAPM y acarreo del futuro)</b>"],
        ["^TNX (CBOE 10-Year Treasury Yield Index)", pct(R["tnx"], 3), "Referencia sugerida en el enunciado; sensibilidad"],
        ["Treasury 10 años (par yield)", pct(tsy["10 Yr"]), "Contraste oficial de ^TNX"],
    ]
    return html_table(["Tasa observada el 29-jul-2026", "Valor", "Uso en el trabajo"], rows, "lrl", highlight={4})


def t_expected_q(R: dict) -> str:
    rows = []
    v0 = R["v0"]
    for _, q in R["quarters"].iterrows():
        t = (q["hasta"] - R["t0"]).days / 365.25
        rows.append([fecha(q["hasta"]), musd(v0 * (1 + R["capm"]["Portafolio"]) ** t), musd(q["EV_u"]), musd(q["EV_h"]),
                     musd(v0 * (1 + R["rf_h"]) ** t), usd(q["pnl_media"], 0)])
    return html_table(["Fin del trimestre", "CAPM sin cobertura (analítico)", "Sin cobertura (simulado)",
                       "Cubierto (simulado)", "V₀ a la tasa libre de riesgo", "Resultado esperado de los futuros en el trimestre"],
                      rows, "lrrrrr", cls="compact")


def t_sens_erp(R: dict) -> str:
    rows = [[pct(r["erp"], 0), musd(r["Eu"]), pct(r["ru"]), musd(r["sdu"]), musd(r["Eh"]), pct(r["rh"]), musd(r["sdh"])]
            for _, r in R["sens_erp"].iterrows()]
    return html_table(["Prima de riesgo de mercado", "E[V] sin cobertura", "Anual", "σ", "E[V] cubierto", "Anual", "σ"],
                      rows, "lrrrrrr", highlight={1})


def t_monthly(R: dict) -> str:
    m, v0 = R["monthly"], R["v0"]
    rows = [
        ["<b>Sin cobertura (CAPM)</b>", pct(m["mu_u"], 3), usd(v0 * (1 + m["mu_u"]), 0), pct(m["sd_u"], 2),
         f"rf + β·PRM = {pct(R['capm']['Portafolio'])} anual"],
        ["Sin cobertura (promedio histórico)", pct(m["mu_hist"], 3), usd(v0 * (1 + m["mu_hist"]), 0), pct(m["sd_u"], 2),
         f"Retorno histórico del punto 3 ({pct(R['opt']['ret'])} anual ÷ 12, igual que μ₂₁ del punto 4); incluye la alfa de la muestra"],
        ["<b>Cubierto con futuros</b>", pct(m["mu_h"], 3), usd(v0 * (1 + m["mu_h"]), 0), pct(m["sd_h"], 2),
         f"rf + β residual·PRM; β residual = {num(m['beta_res'], 4)}"],
    ]
    for v in m["var"]:
        c = int(round(v["conf"] * 100))
        rows.append([f"<b>Ajustado por VaR {c} %</b> sin cobertura", pct(-v["u_pct"], 2), usd(v0 * (1 - v["u_pct"]), 0), "",
                     f"Umbral de pérdida mensual que solo se supera en {100 - c} % de los meses"])
        rows.append([f"Ajustado por VaR {c} % cubierto", pct(-v["h_pct"], 2), usd(v0 * (1 - v["h_pct"]), 0), "",
                     f"La cobertura reduce la pérdida en {usd(v0 * (v['u_pct'] - v['h_pct']), 0)}"])
    return html_table(["Enfoque", "Rendimiento del mes", "Valor esperado al cierre del mes", "σ mensual", "Lectura"],
                      rows, "lrrrl", highlight={0, 2})


def t_dividends(R: dict) -> str:
    rows = []
    for t in R["cfg"]["portafolio"]["tickers"]:
        p = R["prices"].loc[t]
        d4 = R["div_fwd"][t]
        rows.append([f"<b>{t}</b>", f"{usd(p['last_div'], 3)} ({fecha(p['last_div_date'])})", usd(d4, 3), pct(d4 / R["px0"][t]),
                     num(R["shares"][t]), usd(d4 * R["shares"][t], 0), usd(d4 * R["shares"][t] / 12, 0)])
    real = R["expost"]["dividends"]
    tot = sum(R["div_fwd"][t] * R["shares"][t] for t in R["cfg"]["portafolio"]["tickers"])
    rows.append(["<b>Portafolio</b>", "", "", pct(R["q_p"]), "", usd(tot, 0), usd(tot / 12, 0)])
    cap = "Dividendos efectivamente cobrados después de la compra: " + "; ".join(
        f"{r.ticker} {usd(r.dps, 3)} el {fecha(r.fecha)} ({usd(r.usd, 0)})" for r in real.itertuples()) + "."
    return html_table(["Acción", "Último dividendo trimestral", "Dividendo anualizado (4×)", "Rendimiento sobre el precio de compra", "Acciones",
                       "Dividendo anual esperado", "Promedio mensual"], rows, "lrrrrrr", highlight={len(rows) - 1}, caption=cap)


def t_beta_sens(R: dict) -> str:
    rows = []
    for _, r in R["sens_beta"].iterrows():
        rows.append([f"<b>{num(r['beta'], 2)}</b>", num(r["n_star"], 2), f"<b>{int(r['n'])}</b>", musd(r["exp_sist"]),
                     usd(r["dv_1pct"], 0), musd(r["dv_m10"]), num(r["beta_res"], 4), pct(r["sd_u"], 1), pct(r["sd_h"], 1),
                     pct(r["red_var"], 1), usd(r["im_total"], 0)])
    return html_table(["β del portafolio", "N*", "Contratos", "Exposición sistemática β·V", "ΔV por 1 % del índice",
                       "ΔV si el índice cae 10 %", "β residual", "σ anual sin cobertura", "σ anual cubierta",
                       "Varianza eliminada", "Margen inicial"], rows, "lrrrrrrrrrr", highlight={1}, cls="compact")


def t_change_beta(R: dict) -> str:
    rows = [[f"β* = {num(c['objetivo'], 1)}", num(c["n"], 2), f"{int(round(abs(c['n'])))} contratos en posición {c['pos']}"]
            for c in R["change_beta"]]
    return html_table(["Beta objetivo", "N = (β* − β)·V / (F·50)", "Operación"], rows, "lrl", cls="narrow")


def t_sources(R: dict) -> str:
    rows = [[escape(s["dato"]), escape(s["fuente"]), f'<a href="{s["url"]}">enlace</a>'] for s in R["cfg"]["fuentes"]]
    return html_table(["Dato", "Fuente", "URL"], rows, "llc", cls="compact")


# ----------------------------------------------------------------------------- cifras clave
def key_numbers(R: dict) -> dict:
    k: dict = {}
    o, st, bt, tl = R["opt"], R["rb"]["stats"], R["bt"]["table"], R["tl"]
    tk = R["cfg"]["portafolio"]["tickers"]
    k["members"] = manual_inputs()["meta"]["integrantes"]
    k["w"] = {t: pct(o["w"][j]) for j, t in enumerate(tk)}
    k["w_mv"] = {t: pct(o["w_mv"][j]) for j, t in enumerate(tk)}
    k["amt"] = {t: usd(o["w"][j] * R["v0"]) for j, t in enumerate(tk)}
    k["ret"], k["vol"], k["sharpe"] = pct(o["ret"]), pct(o["vol"]), num(o["sharpe"], 4)
    k["ret_mv"], k["vol_mv"], k["sharpe_mv"] = pct(o["ret_mv"]), pct(o["vol_mv"]), num(o["sharpe_mv"], 4)
    k["d_ret"] = num(100 * (o["ret"] - o["ret_mv"]), 2)
    k["d_vol"] = num(100 * (o["vol"] - o["vol_mv"]), 2)
    k["exp_usd"] = usd(o["ret"] * R["v0"])
    k["n_obs"] = num(R["rb"]["n"])
    k["n_px"] = num(R["rb"]["n"] + 1)
    for t in tk:
        k[t] = {"ra": pct(st.loc[t, "ret_arit"]), "rg": pct(st.loc[t, "ret_geo"]), "vol": pct(st.loc[t, "vol"]),
                "beta": num(bt[t]["beta"], 3), "r2": num(bt[t]["r2"], 2), "alpha": pct(bt[t]["alpha_a"], 1, True),
                "capm": pct(R["capm"][t]), "ytd": pct(R["prices"].loc[t, "ytd"], 1, True),
                "r12": pct(R["prices"].loc[t, "r12"], 1, True), "r3": pct(R["prices"].loc[t, "r3"], 1, True),
                "dist": pct(R["prices"].loc[t, "dist_hi"], 1, True), "close": usd(R["prices"].loc[t, "close"]),
                "dist_abs": pct(abs(R["prices"].loc[t, "dist_hi"]), 1), "r3_abs": pct(abs(R["prices"].loc[t, "r3"]), 1),
                "px0": usd(R["px0"][t]), "jump": pct(R["px0"][t] / R["prices"].loc[t, "close"] - 1, 1, True),
                "dy": pct(R["prices"].loc[t, "dy"]), "exp": usd(R["exp_price"][t]["capm"]),
                "exp_var": pct(R["exp_price"][t]["capm"] / R["px0"][t] - 1, 1, True),
                "last": usd(R["expost"]["px_last"][t]),
                "post": pct(R["expost"]["px_last"][t] / R["px0"][t] - 1, 1, True)}
    c = R["rb"]["corr"]
    k["c_mw"], k["c_mx"], k["c_wx"] = num(c.loc["MSFT", "WMT"], 4), num(c.loc["MSFT", "XOM"], 4), num(c.loc["WMT", "XOM"], 4)
    vt = R["var"]["table"].set_index("conf")
    for c_, tag in ((0.95, "95"), (0.99, "99")):
        r = vt.loc[c_]
        k[f"var{tag}"] = {"pct": pct(r["var_pct"]), "usd": usd(r["var_usd"]), "h_pct": pct(r["hist_pct"]),
                          "h_usd": usd(r["hist_usd"]), "z_pct": pct(r["var0_pct"]), "z_usd": usd(r["var0_usd"])}
    k["mu21"], k["sd21"] = pct(R["var"]["mu_h"]), pct(R["var"]["sd_h"])
    k["rf_s"] = pct(R["rf_s"])
    k["rf_h"], k["fvx"], k["tnx"], k["irx"] = pct(R["rf_h"], 3), pct(R["fvx"], 3), pct(R["tnx"], 3), pct(R["irx"], 3)
    k["erp"] = pct(R["erp"], 1)
    k["beta_p"] = num(R["beta_p"], 4)
    k["beta_p2"] = num(R["beta_p"], 2)
    k["beta_reg"] = num(R["bt"]["beta_p_reg"], 4)
    k["r2_p"] = pct(bt["Portafolio"]["r2"], 1)
    k["alpha_p"] = pct(bt["Portafolio"]["alpha_a"], 1, True)
    k["resid_p"] = pct(bt["Portafolio"]["resid_vol"])
    k["mkt_vol"] = pct(R["bt"]["mkt_vol"])
    k["mkt_ret"] = pct(R["bt"]["mkt_ret"])
    k["capm_p"] = pct(R["capm"]["Portafolio"])
    k["q_idx"], k["q_p"] = pct(R["q_idx"]), pct(R["q_p"])
    k["s0"], k["f0"] = num(R["s0"], 2), num(R["f0"], 2)
    k["basis0"] = num(R["f0"] - R["s0"], 2)
    k["f0_theo"], k["f0_theo_3m"] = num(R["f0_theo"], 2), num(R["f0_theo_3m"], 2)
    k["tau0_d"] = num(R["tau0"] * 365)
    k["notional1"] = usd(R["f0"] * R["mult"], 0)
    k["n_star"] = num(R["n_star"], 2)
    k["n"] = R["n"]
    k["contract0"] = label(*tl.loc[0, "old"])
    k["hedged_notional"] = musd(R["n"] * R["f0"] * R["mult"])
    k["exp_sist"] = musd(R["beta_p"] * R["v0"])
    sel = next(o_ for o_ in R["n_opts"] if o_["n"] == R["n"])
    oth = next(o_ for o_ in R["n_opts"] if o_["n"] != R["n"])
    k["n_other"] = oth["n"]
    k["res_sel"], k["res_oth"] = num(sel["beta_res"], 4), num(oth["beta_res"], 4)
    k["exp_sel"], k["exp_oth"] = usd(abs(sel["exp_res"]), 0), usd(abs(oth["exp_res"]), 0)
    k["se_beta2"] = num(1.96 * bt["Portafolio"]["se_beta"], 3)
    k["im_tot"] = usd(R["mstats"]["corto"]["im0"], 0)
    k["mm_tot"] = usd(R["mstats"]["corto"]["mm0"], 0)
    k["im_c"], k["mm_c"] = usd(R["mm_s"] * R["imf"], 0), usd(R["mm_s"], 0)
    k["cushion_pts"] = num((R["imf"] - 1) * R["mm_s"] / R["mult"], 1)
    k["cushion_pct"] = pct((R["imf"] - 1) * R["mm_s"] / R["mult"] / R["f0"], 2)
    k["lev"] = num(R["n"] * R["f0"] * R["mult"] / R["mstats"]["corto"]["im0"], 1)
    k["im_pct"] = pct(R["mm_s"] * R["imf"] / (R["f0"] * R["mult"]), 1)
    ms, ml = R["mstats"]["corto"], R["mstats"]["largo"]
    k["m"] = {"p_any": pct(ms["p_any"], 1), "n_calls": num(ms["n_calls"], 1), "n_calls_p95": num(ms["n_calls_p95"]),
              "dep_mean": musd(ms["dep_mean"]), "dep_p95": musd(ms["dep_p95"]), "p_month": pct(ms["p_month_call"], 1),
              "sweep": pct(ms["sweep_share"], 1), "n_rdep": num(ms["n_rdep"], 1)}
    k["ml"] = {"p_any": pct(ml["p_any"], 1), "n_calls": num(ml["n_calls"], 1), "dep_mean": musd(ml["dep_mean"]),
               "dep_p95": musd(ml["dep_p95"])}
    T = {kk: R["term"][kk] for kk in R["term"]}
    for kk, t in T.items():
        k[f"T_{kk}"] = {"media": musd(t["media"]), "sd": musd(t["sd"]), "p5": musd(t["p5"]), "p95": musd(t["p95"]),
                        "r": pct(t["r_media"], 1, True), "ra": pct((1 + t["r_media"]) ** (1 / R["years"]) - 1, 2),
                        "ploss": pct(t["p_loss"], 1), "cvar": musd(t["cvar5"])}
    k["sd_red"] = pct(1 - T["corto"]["sd"] / T["sin"]["sd"], 1)
    k["var_red"] = pct(1 - (T["corto"]["sd"] / T["sin"]["sd"]) ** 2, 1)
    k["sd_reb_gain"] = pct(1 - T["corto"]["sd"] / T["corto_fijo"]["sd"], 1)
    q = R["quarters"]
    k["q_n"] = len(q)
    k["roll1_old"], k["roll1_new"] = num(R["sim"]["Fo"][0, 1], 2), num(R["sim"]["Fn"][0, 1], 2)
    k["roll1_spread"] = num(R["sim"]["Fn"][0, 1] - R["sim"]["Fo"][0, 1], 2)
    k["roll_spread_mean"] = num(q["spread_roll"].dropna().iloc[1:].mean(), 1)
    k["base_final"] = num(q["base_cierre"].iloc[-1], 1)
    k["base_final_usd"] = usd(q["base_cierre"].iloc[-1] * R["mult"] * R["n"], 0)
    k["base_final_sd"] = num(q["base_sd"].iloc[-1], 1)
    k["tau_final_d"] = num(tl["tau_old"].iloc[-1] * 365)
    k["contract_final"] = label(*tl["old"].iloc[-1])
    k["r_u_q"] = pct(q["r_u"].iloc[1:-1].mean(), 2)
    k["r_h_q"] = pct(q["r_h"].iloc[1:-1].mean(), 2)
    k["sd_u_q"] = pct(q["sd_u"].iloc[1:-1].mean(), 2)
    k["sd_h_q"] = pct(q["sd_h"].iloc[1:-1].mean(), 2)
    k["capm_q"], k["rf_q"] = pct(R["capm_q"], 2), pct(R["rf_q"], 2)
    k["pnl_q"] = usd(q["pnl_media"].iloc[1:-1].mean(), 0)
    se = R["sens_erp"].set_index("erp")
    k["erp_lo"], k["erp_hi"] = pct(se.index.min(), 0), pct(se.index.max(), 0)
    k["Eu_lo"], k["Eu_hi"] = musd(se["Eu"].iloc[0]), musd(se["Eu"].iloc[-1])
    k["Eh_lo"], k["Eh_hi"] = musd(se["Eh"].iloc[0]), musd(se["Eh"].iloc[-1])
    m = R["monthly"]
    k["mm_u"], k["mm_h"], k["mm_hist"] = pct(m["mu_u"], 3), pct(m["mu_h"], 3), pct(m["mu_hist"], 3)
    k["msd_u"], k["msd_h"] = pct(m["sd_u"], 2), pct(m["sd_h"], 2)
    k["mv_u"] = usd(R["v0"] * (1 + m["mu_u"]), 0)
    k["mv_h"] = usd(R["v0"] * (1 + m["mu_h"]), 0)
    k["mvar95_u"] = usd(R["v0"] * m["var"][0]["u_pct"], 0)
    k["mvar95_h"] = usd(R["v0"] * m["var"][0]["h_pct"], 0)
    k["mvar99_u"] = usd(R["v0"] * m["var"][1]["u_pct"], 0)
    k["mvar99_h"] = usd(R["v0"] * m["var"][1]["h_pct"], 0)
    k["div_m"] = pct(m["div_m"], 3)
    k["div_year"] = usd(sum(R["div_fwd"][t] * R["shares"][t] for t in tk), 0)
    k["div_real"] = usd(R["expost"]["dividends"]["usd"].sum(), 0)
    sb = R["sens_beta"].reset_index(drop=True)
    k["sb"] = [{"b": num(r["beta"], 2), "n": int(r["n"]), "ns": num(r["n_star"], 2), "exp": musd(r["exp_sist"]),
                "dv": usd(r["dv_1pct"], 0), "m10": musd(abs(r["dv_m10"])), "red": pct(r["red_var"], 1),
                "sdu": pct(r["sd_u"], 1), "sdh": pct(r["sd_h"], 1), "im": usd(r["im_total"], 0), "Eu": pct(r["Eu"]),
                "Eh": pct(r["Eh"])} for _, r in sb.iterrows()]
    cb = {c["objetivo"]: c for c in R["change_beta"]}
    k["cb05"] = int(round(abs(cb[0.5]["n"])))
    k["cb2"] = int(round(abs(cb[2.0]["n"])))
    e = R["expost"]
    k["ep"] = {"fecha": fecha(e["fecha"], largo=True), "v0": musd(e["v0"]), "v": musd(e["v_last"]),
               "r": pct(e["v_last"] / e["v0"] - 1, 1, True), "spx": pct(e["spx_last"] / e["spx0"] - 1, 1, True),
               "fut": usd(e["pnl_fut"], 0), "fut_abs": usd(abs(e["pnl_fut"]), 0), "u6": usd(e["pnl_u6"], 0),
               "z6": usd(e["pnl_z6"], 0), "n_roll": e["n_roll"],
               "h": musd(e["v_last"] + e["pnl_fut"]), "rh": pct((e["v_last"] + e["pnl_fut"]) / e["v0"] - 1, 1, True),
               "alpha": pct(e["v_last"] / e["v0"] - 1 - R["beta_p"] * (e["spx_last"] / e["spx0"] - 1), 1, True),
               "sys": pct(R["beta_p"] * (e["spx_last"] / e["spx0"] - 1), 1, True)}
    k["beta_roll"] = {n: num(float(sr.loc[:R["cut"]].iloc[-1]), 2) for n, sr in R["bt"]["rolling"].items()}
    k["n_roll_beta"] = int(round(float(R["bt"]["rolling"]["Portafolio"].loc[:R["cut"]].iloc[-1]) * R["v0"] / (R["f0"] * R["mult"])))
    from ..parte2.model import ea_from_bey
    k["tnx_ea"] = pct(ea_from_bey(R["tnx"]), 3)
    k["tnx_diff"] = num((ea_from_bey(R["tnx"]) - R["rf_h"]) * 1e4)
    k["years"] = num(R["years"], 2)
    k["fo_u"], k["fo_h"] = pct(R["from_obs"]["sin"], 2), pct(R["from_obs"]["corto"], 2)
    k["obs_gain"] = pct(R["w0_obs"] / R["v0"] - 1, 2, True)
    k["sharpe_rfh"] = num(R["sharpe_rfh"], 4)
    k["last_px"] = fecha(R["expost"]["fecha"])
    k["n_paths"] = num(R["n_paths"])
    k["last_obs"] = fecha(R["tl"]["fecha"].iloc[R["last_i"]])
    k["roll_n"] = int(R["tl"]["roll"].sum())
    k["basis_sd"] = pct(R["mkt"].basis_sd, 2)
    k["p1_call"] = usd(R["strat"]["corto"]["dep"][0, 1], 0)
    k["p1_loss"] = usd(-R["strat"]["corto"]["pnl"][0, 1], 0)
    return k


def tables(R: dict) -> dict:
    corr = R["rb"]["corr"]
    return {
        "prices": t_prices(R), "exp_price": t_expected_price(R), "stats": t_stats(R),
        "cov": t_matrix(R["rb"]["cov"]), "corr": t_matrix(corr, 4), "weights": t_weights(R), "var": t_var(R),
        "beta": t_beta(R), "specs": t_specs(R), "contracts": t_contracts(R),
        "m_p50": t_margin_path(R, "p50"), "m_p5": t_margin_path(R, "p5"), "m_p95": t_margin_path(R, "p95"),
        "quarters": t_quarters(R), "strategies": t_strategies(R), "rates": t_rates(R), "expected_q": t_expected_q(R),
        "sens_erp": t_sens_erp(R), "monthly": t_monthly(R), "dividends": t_dividends(R), "beta_sens": t_beta_sens(R),
        "change_beta": t_change_beta(R), "sources": t_sources(R),
    }


def render(R: dict) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined, autoescape=False,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(FILTERS)
    tpl = env.get_template("parte2.html.j2")
    return tpl.render(R=R, k=key_numbers(R), fig=figures_p2.build_all(R), tab=tables(R),
                      plotly_js=f"https://cdn.plot.ly/plotly-{po.get_plotlyjs_version()}.min.js")


def main() -> None:
    R = build()
    from ..parte2.model import third_friday
    R["tl_exp0"] = third_friday(*R["tl"].loc[0, "old"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(R), encoding="utf-8")
    print(f"Informe generado en {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
