"""Tablas HTML del informe (cifras con formato colombiano)."""

from __future__ import annotations

from html import escape

from ..analysis import DISTS, STRATS
from .fmt import fecha, mm, num, pct, usd


def html_table(headers: list[str], rows: list[list[str]], align: str | None = None, cls: str = "",
               highlight: set[int] | None = None, caption: str | None = None) -> str:
    align = align or "l" + "r" * (len(headers) - 1)
    css = {"l": "left", "r": "right", "c": "center"}
    highlight = highlight or set()
    head = "".join(f'<th style="text-align:{css[a]}">{h}</th>' for h, a in zip(headers, align, strict=True))
    body = []
    for i, row in enumerate(rows):
        cells = "".join(
            f'<td style="text-align:{css[a]}{";white-space:nowrap" if a == "r" else ""}">{c}</td>'
            for c, a in zip(row, align, strict=True)
        )
        cls_row = ' class="hl"' if i in highlight else ""
        body.append(f"<tr{cls_row}>{cells}</tr>")
    cap = f"<caption>{caption}</caption>" if caption else ""
    return (f'<div class="table-wrap"><table class="data {cls}">{cap}<thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


ARROWS = {1: '<span class="up">▲ deprecia</span>', -1: '<span class="down">▼ aprecia</span>', 0: '<span class="flat">◆ mixto</span>'}


def fundamentals(R: dict) -> str:
    rows = [[f"<b>{escape(f['grupo'])}</b>", escape(f["indicador"]), escape(f["valor"]), escape(f["fecha"]),
             ARROWS[f["efecto"]], escape(f["fuente"])] for f in R["inp"]["fundamentales"]]
    return html_table(["Bloque", "Indicador", "Valor", "Fecha", "Presión sobre el peso", "Fuente"], rows, "llrccl",
                      cls="compact")


def scenarios(R: dict) -> str:
    rows = []
    for s in R["scenarios"]:
        e = R["exp_paths"][s.key]
        rows.append([f"<b>{s.nombre}</b>", num(s.trm_12m), pct(s.trm_12m / R["s0"] - 1, 1, True),
                     pct(s.deriva_lp, 1), num(e[-1]), pct(s.probabilidad, 0), escape(s.narrativa)])
    rows.append(["<b>Esperanza ponderada</b>", num(R["a1"]["expected_12m"]), pct(R["a1"]["expected_12m"] / R["s0"] - 1, 1, True),
                 "", "", "100 %", "Promedio de los tres escenarios ponderado por su probabilidad subjetiva."])
    return html_table(["Escenario", "TRM oct-2027", "Var. vs. spot", "Deriva anual años 2–10", "TRM esperada oct-2036",
                       "Prob.", "Narrativa"], rows, "lrrrrcl", highlight={len(rows) - 1}, cls="compact")


def loan_params(R: dict) -> str:
    a2, cred = R["a2"], R["inp"]["credito"]
    loan = a2["loan"]
    rows = [
        ["Entidad financiera", escape(cred["entidad"])],
        ["Producto de referencia", escape(cred["producto"])],
        ["Tasa base", f"Prime de Wells Fargo {pct(cred['prime'])} (vigente desde {fecha(cred['prime_vigencia'])})"],
        ["Spread", f"{num(cred['spread'] * 1e4)} pb"],
        ["Forma de cotización", escape(cred["forma_cotizacion"])],
        ["Tasa nominal / periódica", f"{pct(loan.nominal_rate)} N.T.V. → {pct(loan.periodic_rate, 3)} por trimestre (63 de 252 días)"],
        ["Tasa efectiva anual", pct(loan.effective_annual_rate)],
        ["Valor maquinaria / aporte propio", f"COP {num(a2['machine'])} / COP {num(a2['equity'])} (10 %)"],
        ["Monto financiado", f"COP {num(a2['financed_cop'])} ÷ {num(R['s0'], 2)} = <b>{usd(loan.principal_usd)}</b>"],
        ["Plazo y amortización", "10 años, 40 cuotas trimestrales constantes (sistema francés)"],
        ["Cuota trimestral", f"<b>{usd(loan.installment)}</b>"],
        ["Total pagado / intereses", f"{usd(a2['total_paid_usd'])} / {usd(a2['total_interest_usd'])}"],
        ["Fecha de consulta", fecha(R["inp"]["meta"]["fecha_consulta"], largo=True)],
    ]
    return html_table(["Parámetro", "Valor"], rows, "ll", cls="kv")


def a3_summary(R: dict) -> str:
    rows = []
    for _, r in R["a3"]["summary"].iterrows():
        rows.append([f"<b>{r['escenario']}</b>", num(r["trm_final"]), mm(r["cuota_ultima"], 2), mm(r["total_cop"]),
                     mm(r["interes_s0"]), mm(r["fx_interes"]), mm(r["fx_capital"]), mm(r["costo_financiero"]),
                     pct(r["tir_cop"]), pct(r["dev_implicita"], 2, True)])
    return html_table(["Trayectoria", "TRM oct-2036", "Última cuota (COP M)", "Total pagado (COP M)",
                       "Intereses a TRM base", "Efecto cambiario s/ intereses", "Efecto cambiario s/ capital",
                       "Costo financiero (COP M)", "Costo efectivo COP (E.A.)", "Devaluación implícita anual"],
                      rows, "lrrrrrrrrr", cls="compact")


def market_quote(R: dict) -> str:
    mk = R["inp"]["forward_mercado"]
    rows = []
    for _, c in R["b1"]["curve"].iterrows():
        rows.append([c["plazo"], num(c["dias"]), num(c["dias_habiles"], 1), num(mk["spot_referencia"], 2),
                     num(c["puntos"]), num(c["forward"], 2), pct(c["dev"])])
    return html_table(["Plazo", "Días calendario", "Días hábiles (base 252)", "Spot de referencia", "Puntos forward",
                       "Forward outright", "Devaluación implícita anual"], rows, "crrrrrr",
                      highlight={3}, caption=f"Fuente: {escape(mk['fuente'])}. Spot: cierre SET-ICAP FX del 13-oct-2026. "
                      "Consulta: 15-oct-2026.")


def tradition(R: dict) -> str:
    tr = R["inp"]["forward_mercado"]["tradition"]
    rows = [[k, num(v[0], 2) if v[0] else "Sin operaciones", num(v[1])] for k, v in tr["cierres"].items()]
    return html_table(["Tramo", "Precio de cierre", "N.º de operaciones"], rows, "crr", cls="compact narrow",
                      caption=f"Fuente: {escape(tr['fuente'])}.")


def cip(R: dict) -> str:
    rows = []
    for _, c in R["b1"]["cip"].iterrows():
        rows.append([f"<b>{escape(c['par'])}</b><br><small>{escape(c['nota'])}</small>", pct(c["r_cop"]), pct(c["r_usd"]),
                     pct(c["dev"]), num(c["forward_13oct"], 2), num(c["dif_cop"], 2), num(c["dif_pb"], 0),
                     num(c["forward_val"], 2)])
    mkt = R["b1"]
    rows.append(["<b>Mercado (Itaú, 257 puntos)</b>", "", "", pct(mkt["dev_1y"]), num(mkt["forward_1y_mkt"], 2), "n. a.", "n. a.",
                 num(mkt["forward_1y_val"], 2)])
    return html_table(["Par de tasas (E.A.)", "r COP", "r USD", "Devaluación teórica", "F teórico (spot 13-oct)",
                       "Mercado − teórico (COP)", "Mercado − teórico (pb)", "F al spot de valoración (3.197,65)"],
                      rows, "lrrrrrrr", highlight={len(rows) - 1})


def valuation(R: dict) -> str:
    per_n = R["b2"][("central", "normal")]["per"]
    per_t = R["b2"][("central", "t")]["per"]
    coh = R["coherence"]
    rows = []
    for i, y in enumerate(per_n["anio"]):
        pv = per_n["payoff_media"][i] / (1 + R["disc_rate"]) ** y
        rows.append([f"Forward {i + 1}", f"Fin año {y - 1} → fin año {y}", usd(coh["cubierto_usd"][i]),
                     f"{num(per_n['forward_media'][i])} <small>({num(per_n['forward_p5'][i])}–{num(per_n['forward_p95'][i])})</small>",
                     num(per_n["spot_t_media"][i]), mm(per_n["payoff_media"][i], 2), mm(per_t["payoff_media"][i], 2),
                     mm(pv, 2), pct(per_n["proteccion"][i], 1)])
    return html_table(["Contrato", "Pacto → vencimiento", "Nominal", "F pactado medio (P5–P95)", "TRM vencimiento media",
                       "Liquidación esperada normal (COP M)", "Liquidación esperada t (COP M)", "Valor presente hoy (COP M)",
                       "P(protección)"], rows, "lcrrrrrrr", cls="compact")


def coherence(R: dict) -> str:
    c = R["coherence"]
    rows = [[f"Año {int(r['anio'])}", usd(r["obligacion_usd"]), usd(r["capital_usd"]), usd(r["interes_usd"]),
             usd(r["cubierto_usd"]), usd(r["abierto_usd"]), usd(r["saldo_inicio_usd"]),
             pct(r["cubierto_usd"] / r["obligacion_usd"], 0)] for _, r in c.iterrows()]
    rows.append(["<b>Total años 7–10</b>", usd(c["obligacion_usd"].sum()), usd(c["capital_usd"].sum()),
                 usd(c["interes_usd"].sum()), usd(c["cubierto_usd"].sum()), usd(c["abierto_usd"].sum()),
                 usd(R["a2"]["balance_end_y6"]), pct(c["cubierto_usd"].sum() / c["obligacion_usd"].sum(), 0)])
    return html_table(["Año", "Pagos programados", "de los cuales capital", "de los cuales interés", "Nominal forward (75 %)",
                       "Abierto (25 %)", "Saldo de capital al inicio", "Cubierto / obligación"], rows, "lrrrrrrr",
                      highlight={len(rows) - 1}, cls="compact")


def proportions(R: dict) -> str:
    names = {s.key: s.nombre for s in R["scenarios"]} | {"neutral": "Neutral al riesgo (referencia)"}
    rows, hl = [], set()
    for key in ("favorable", "central", "adverso", "neutral"):
        for dist in DISTS:
            p = R["b2"][(key, dist)]["pooled"]
            if key == "central":
                hl.add(len(rows))
            rows.append([f"<b>{names[key]}</b>", DISTS[dist], pct(p["proteccion"], 1), pct(p["costo_oportunidad"], 1),
                         pct(p["extrema_exposicion"], 1), pct(p["extrema_derivado"], 1), pct(p["fracaso"], 1),
                         mm(p["payoff_media"], 2), mm(p["payoff_cvar"], 1), pct(p["prob_total_negativo"], 1)])
    return html_table(["Escenario", "Innovación", "Protección (S_T > F)", "Costo de oportunidad (S_T < F)",
                       "Pérdida cambiaria extrema (S_T > 1,2F)", "Pérdida extrema del derivado (S_T < 0,8F)",
                       "Fracaso por desfase", "Liquidación media por forward (COP M)", "CVaR 5 % de la liquidación (COP M)",
                       "P(resultado de los 4 forwards < 0)"], rows, "llrrrrrrrr", highlight=hl, cls="compact")


def quadrants(R: dict) -> str:
    labels = [("proteccion_efectiva", "Protección efectiva", "Forward gana y las cuotas del año superaron el presupuesto: compensó la depreciación."),
              ("costo_op_puro", "Costo de oportunidad (cobertura exitosa)", "Forward pierde, pero las cuotas costaron menos que el presupuesto: el costo quedó fijado; es pérdida del derivado, no fracaso."),
              ("sobrecompensacion", "Sobrecompensación", "Forward gana aunque las cuotas costaron menos: la TRM subió al cierre del año tras pagos baratos."),
              ("fracaso", "Fracaso por desfase temporal", "Forward pierde y las cuotas superaron el presupuesto: la TRM subió durante el año y cayó bajo F al vencimiento.")]
    rows = []
    for key, name, desc in labels:
        rows.append([f"<b>{name}</b>", desc] + [pct(R["b2"][("central", d)]["pooled"][key], 1) for d in DISTS])
    return html_table(["Resultado", "Interpretación", "Normal", "t de Student"], rows, "llrr", cls="compact")


def combined_cost(R: dict) -> str:
    rows = []
    for dist in DISTS:
        per = R["b2"][("central", dist)]["per"]
        for i, y in enumerate(per["anio"]):
            rows.append([f"Año {y}", DISTS[dist], num(per["forward_media"][i]), num(per["tasa_u_media"][i]),
                         num(per["tasa_h_media"][i]), num(per["tasa_u_p95"][i]), num(per["tasa_h_p95"][i]),
                         pct(per["dev_u_sd"][i], 1), pct(per["dev_h_sd"][i], 1), pct(per["dev_u_10"][i], 1),
                         pct(per["dev_h_10"][i], 2)])
    return html_table(["Año", "Innovación", "F medio", "Tasa efectiva sin cobertura (media)", "Tasa efectiva 75/25 (media)",
                       "Sin cobertura P95", "75/25 P95", "σ desviación vs. presupuesto sin cob.", "σ desviación 75/25",
                       "P(sobrecosto > 10 %) sin cob.", "P(sobrecosto > 10 %) 75/25"], rows, "lcrrrrrrrrr", cls="compact")


def tails(R: dict) -> str:
    rows = [[r["dist"], f"{r['horizonte']} mes" + ("" if r["horizonte"] == 1 else "es"), num(r["curtosis"], 2),
             pct(r["p_2sd"], 2), pct(r["p_3sd"], 3), num(r["q999"], 2)] for _, r in R["tails"].iterrows()]
    return html_table(["Innovación", "Horizonte", "Exceso de curtosis", "P(choque > 2σ)", "P(choque > 3σ)",
                       "Cuantil 99,9 % (σ)"], rows, "lcrrrr", cls="compact narrow")


def b3_summary(R: dict) -> str:
    names = {s.key: s.nombre for s in R["scenarios"]} | {"neutral": "Neutral al riesgo"}
    rows, hl = [], set()
    for key in ("favorable", "central", "adverso", "neutral"):
        for dist in DISTS:
            for strat in STRATS:
                m = R["b3"][(key, dist, strat)]
                if strat == "con":
                    hl.add(len(rows))
                rows.append([f"<b>{names[key]}</b>", DISTS[dist], STRATS[strat], mm(m["total_media"]), mm(m["total_sd"]),
                             mm(m["total_p95"]), mm(m["total_cvar95"]),
                             f"{pct(m['tir_media'])} <small>({pct(m['tir_p5'], 1)} – {pct(m['tir_p95'], 1)})</small>",
                             mm(m["vp_media"]), mm(m["forward_neto"], 2) if strat == "con" else "n. a."])
    return html_table(["Escenario", "Innovación", "Estrategia", "Total pagado medio (COP M)", "σ total (COP M)",
                       "P95 total (COP M)", "CVaR 95 % (COP M)", "TIR en COP media (P5 – P95)",
                       "VP a TES 10A (COP M)", "Resultado forwards (COP M)"], rows, "lllrrrrrrr", highlight=hl,
                      cls="compact")


def b3_years710(R: dict) -> str:
    names = {s.key: s.nombre for s in R["scenarios"]} | {"neutral": "Neutral al riesgo"}
    rows, hl = [], set()
    for key in ("favorable", "central", "adverso"):
        for dist in DISTS:
            u, h = R["b3"][(key, dist, "sin")], R["b3"][(key, dist, "con")]
            if key == "central":
                hl.add(len(rows))
            rows.append([f"<b>{names[key]}</b>", DISTS[dist], mm(u["y710_media"]), mm(h["y710_media"]),
                         f"{mm(u['y710_sd'])} → {mm(h['y710_sd'])}", pct(h["y710_sd"] / u["y710_sd"] - 1, 1),
                         f"{mm(u['y710_sd_cond'])} → {mm(h['y710_sd_cond'])}", pct(h["y710_sd_cond"] / u["y710_sd_cond"] - 1, 1),
                         f"{mm(u['y710_cvar95'])} → {mm(h['y710_cvar95'])}",
                         f"{pct(u['dev_sd'], 1)} → {pct(h['dev_sd'], 1)}", f"{pct(u['dev_10'], 1)} → {pct(h['dev_10'], 2)}"])
    return html_table(["Escenario", "Innovación", "Costo años 7–10 sin cob. (COP M)", "Con cob. (COP M)",
                       "σ incondicional (COP M)", "Cambio", "σ condicional a TRM año 6", "Cambio", "CVaR 95 % (COP M)",
                       "σ desviación presupuestal", "P(sobrecosto anual > 10 %)"], rows, "llrrrrrrrrr", highlight=hl,
                      cls="compact")


def strategies(R: dict) -> str:
    s = R["sens"]["strategies"]
    rows = [[f"<b>{escape(r['estrategia'])}</b>", mm(r["media"]), mm(r["costo_esperado"], 2), mm(r["sd"]), mm(r["sd_cond"]),
             mm(r["cvar95"]), pct(r["dev_sd"], 2)] for _, r in s.iterrows()]
    return html_table(["Estrategia (75 % de los años 7–10, escenario central normal)", "Costo años 7–10 (COP M)",
                       "Costo esperado de cubrir (COP M)", "σ incondicional", "σ condicional a TRM año 6", "CVaR 95 %",
                       "σ desviación presupuestal"], rows, "lrrrrrr", highlight={1}, cls="compact")


def sens_rate(R: dict) -> str:
    r = R["sens"]["rate"]
    base = R["a2"]["loan"].nominal_rate
    rows, hl = [], set()
    for _, x in r.iterrows():
        if abs(x["tasa"] - base) < 1e-9:
            hl.add(len(rows))
        rows.append([pct(x["tasa"]), pct(x["ea"]), usd(x["cuota_usd"]), usd(x["total_usd"]), mm(x["total_cop_sin"]),
                     mm(x["total_cop_con"]), pct(x["tir_sin"]), pct(x["tir_con"])])
    return html_table(["Tasa nominal T.V.", "E.A.", "Cuota trimestral", "Total pagado USD", "Total COP sin cob. (M)",
                       "Total COP con cob. (M)", "TIR COP sin cob.", "TIR COP con cob."], rows, "rrrrrrrr", highlight=hl,
                      cls="compact")


def sens_d(R: dict) -> str:
    d = R["sens"]["d"]
    rows, hl = [], set()
    for _, x in d.iterrows():
        label = pct(x["d"])
        if abs(x["d"] - R["d_lr"]) < 1e-9:
            label += " <small>(base: 7,50 % vs 3,40 %)</small>"
            hl.add(len(rows))
        elif abs(x["d"] - R["dev_lt"]) < 1e-9:
            label += " <small>(TES 10A vs UST 10A)</small>"
        elif abs(x["d"] - R["b1"]["dev_1y"]) < 1e-9:
            label += " <small>(forward 1A de hoy)</small>"
        rows.append([label, mm(x["forward_neto"], 2), pct(x["proteccion"], 1), mm(x["y710_media"]), pct(x["tir_media"])])
    return html_table(["Prima forward anual (años 7–10)", "Resultado esperado 4 forwards (COP M)", "P(protección)",
                       "Costo años 7–10 con cobertura (COP M)", "TIR en COP con cobertura"], rows, "lrrrr", highlight=hl,
                      cls="compact")


RATE_LABELS = {
    "banrep": "Tasa de política del Banco de la República",
    "ibr_overnight": "IBR overnight",
    "ibr_1m": "IBR a 1 mes",
    "dtf_90": "DTF a 90 días",
    "tes_nov2027": "TES tasa fija nov-2027",
    "tes_jun2032": "TES tasa fija jun-2032 (10 años)",
    "tes_oct2034": "TES tasa fija oct-2034",
    "tes_oct2050": "TES tasa fija oct-2050",
    "sofr": "SOFR overnight",
    "sofr_swap_1y": "Swap SOFR a 1 año",
    "ust_1y": "Tesoro de EE. UU. a 1 año",
    "ust_10y": "Tesoro de EE. UU. a 10 años",
    "fed_rango": "Rango de los fondos federales (Fed)",
}


def sources(R: dict) -> str:
    inp = R["inp"]
    items = [
        ("TRM histórica y spot de valoración", inp["spot"]["fuente"], inp["spot"]["url"]),
        ("Mercado spot SET-ICAP FX", inp["spot"]["fuente_setfx"], None),
        ("Prime de Wells Fargo", inp["credito"]["fuente_prime"], inp["credito"]["url_prime"]),
        *[(r["nombre"], r["fuente"], r.get("url")) for r in inp["credito"]["referencias"]],
        ("Puntos forward COP", inp["forward_mercado"]["fuente"], inp["forward_mercado"]["url"]),
        ("Operaciones forward por tramo", inp["forward_mercado"]["tradition"]["fuente"], inp["forward_mercado"]["tradition"]["url"]),
        ("Curva de devaluaciones implícitas", inp["forward_mercado"]["banco_agrario"]["fuente"], inp["forward_mercado"]["banco_agrario"]["url"]),
        *[(RATE_LABELS.get(k, k), v["fuente"], v.get("url"))
          for k, v in inp["tasas"].items() if isinstance(v, dict) and "fuente" in v and k not in ("fed_sep_2026_09",)],
        ("Proyecciones de la Fed", inp["tasas"]["fed_sep_2026_09"]["fuente"], "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),
        ("Decisiones de política monetaria", inp["banrep_decisiones"]["fuente"], None),
        ("Inflación Colombia", inp["inflacion"]["colombia_septiembre"]["fuente"],
         "https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc"),
        ("Calificaciones soberanas", inp["calificaciones"]["fuente"], inp["calificaciones"]["url"]),
        ("Series de EE. UU. (Prime, SOFR, Fed, Tesoros, Brent, IPC)", "FRED: Federal Reserve Bank of St. Louis (descarga del 15-oct-2026)",
         "https://fred.stlouisfed.org"),
    ]
    rows = []
    for name, src, url in items:
        link = f'<a href="{escape(url)}" target="_blank" rel="noopener">enlace</a>' if url else ""
        rows.append([escape(name), escape(src), link])
    return html_table(["Dato", "Fuente", "URL"], rows, "llc", cls="compact sources")


def build_all(R: dict) -> dict[str, str]:
    fns = [fundamentals, scenarios, loan_params, a3_summary, market_quote, tradition, cip, valuation, coherence,
           proportions, quadrants, combined_cost, tails, b3_summary, b3_years710, strategies, sens_rate, sens_d, sources]
    return {fn.__name__: fn(R) for fn in fns}
