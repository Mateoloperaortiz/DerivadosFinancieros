"""Tablas HTML del informe (cifras con formato colombiano)."""

from __future__ import annotations

import re
from html import escape, unescape

from ..analysis import DISTS, HEDGE_YEARS, STRATS
from .fmt import NBSP, fecha, mm, num, pct, usd

_ALIGN = {"l": "", "r": "ar", "c": "ac"}


def _plain(h: str) -> str:
    """Texto plano de una cabecera (sin etiquetas), para el rótulo de las tarjetas en el celular."""
    return escape(" ".join(unescape(re.sub(r"<[^>]+>", "", h)).split()), quote=True)


def html_table(headers: list[str], rows: list[list[str] | str], align: str | None = None, cls: str = "",
               highlight: set[int] | None = None, caption: str | None = None, *, minw: int | None = None,
               wide: dict[int, str] | None = None, nowrap: set[int] | None = None, stack: bool = False,
               full: set[int] | None = None, eyebrow: int | None = None, row_cls: dict[int, str] | None = None,
               foot: list[str] | None = None, vscroll: bool = False,
               groups: dict[int, tuple[str, int]] | None = None) -> str:
    """Tabla HTML del informe.

    - groups: cabecera de dos niveles, {columna inicial: (rótulo, n.º de columnas)}. El rótulo va centrado sobre sus
      columnas con una raya propia debajo; las columnas sin grupo ocupan los dos renglones. No va con vscroll.
    - caption: nota al pie (fuente, unidades). Va debajo, fuera de la zona que se desplaza.
    - minw: ancho mínimo en px; en pantallas más angostas la tabla se desplaza de lado (con sombra de pista). En el
      celular se le suma un 10 % (CSS, --tw) para que las cabeceras no pasen de dos o tres renglones.
    - wide: ancho mínimo de columnas de texto ({índice: "16em"}) para que no se aplasten en el celular.
    - nowrap: columnas que no se parten (por defecto, las alineadas a la derecha).
    - stack: en el celular cada fila se vuelve una tarjeta con el nombre de la columna al lado de cada dato;
      full son las columnas que ocupan todo el ancho de la tarjeta y eyebrow la que va como antetítulo.
    - rows: una fila que es un texto (no una lista) es el rótulo de un grupo y ocupa todo el ancho.
    - highlight: filas en dorado (hl); row_cls: clases extra por fila (hg = verde, sep = inicio de grupo).
    - foot: fila de totales. vscroll: caja de 540 px de alto con cabecera y totales fijos.
    """
    align = align or "l" + "r" * (len(headers) - 1)
    highlight, row_cls, wide, full = highlight or set(), row_cls or {}, wide or {}, full or set()
    nowrap = {j for j, a in enumerate(align) if a == "r"} if nowrap is None else nowrap
    title = 1 if eyebrow == 0 else 0
    labels = [_plain(h) for h in headers]

    def th(j: int, h: str, extra: str = "") -> str:
        style = _attr("style", f"min-width:{wide[j]}" if j in wide else "")
        return f"<th{_attr('class', _ALIGN[align[j]])}{extra}{style}>{h}</th>"

    def td(j: int, v: str) -> str:
        c = [_ALIGN[align[j]], "nw" if j in nowrap else ""]
        label = ""
        if stack:
            c.append("eb" if j == eyebrow else "tt" if j == title else "full" if j in full else "")
            label = "" if j in (eyebrow, title) else labels[j]
            v = f"<span>{v}</span>" if v else ""
        return f"<td{_attr('class', ' '.join(x for x in c if x))}{_attr('data-label', label)}>{v}</td>"

    head = f"<tr>{''.join(th(j, h) for j, h in enumerate(headers))}</tr>"
    if groups:
        # La raya del grupo va en el <span> (no en el borde de la celda) para que quede recortada por el relleno y
        # dos grupos vecinos no se lean como una sola raya.
        top, sub, j = [], [], 0
        while j < len(headers):
            if j in groups:
                label, n = groups[j]
                top.append(f'<th class="ac gh" colspan="{n}"><span>{label}</span></th>')
                sub += [th(k, headers[k]) for k in range(j, j + n)]
                j += n
            else:
                top.append(th(j, headers[j], ' rowspan="2"'))
                j += 1
        head = f"<tr>{''.join(top)}</tr><tr>{''.join(sub)}</tr>"
    body = []
    for i, row in enumerate(rows):
        rc = " ".join(x for x in ("hl" if i in highlight else "", row_cls.get(i, "")) if x)
        if isinstance(row, str):  # rótulo de grupo a todo el ancho (p. ej. el escenario de las filas que siguen)
            body.append(f'<tr{_attr("class", f"grp {rc}".strip())}><td colspan="{len(headers)}">{row}</td></tr>')
            continue
        assert len(row) == len(headers), (headers, row)
        body.append(f"<tr{_attr('class', rc)}>{''.join(td(j, v) for j, v in enumerate(row))}</tr>")
    tfoot = f"<tfoot><tr>{''.join(td(j, v) for j, v in enumerate(foot))}</tr></tfoot>" if foot else ""
    note = f'<p class="tnote">{caption}</p>' if caption else ""
    scroller = '<div class="tscroll vs" tabindex="0">' if vscroll else '<div class="tscroll">'
    return (f"<div{_attr('class', 'table-wrap stack' if stack else 'table-wrap')}>{scroller}"
            f"<table{_attr('class', f'data {cls}'.strip())}{_attr('style', f'--tw:{minw}px' if minw else '')}>"
            f"<thead>{head}</thead><tbody>{''.join(body)}</tbody>{tfoot}</table></div>{note}</div>")


def _attr(name: str, value: str) -> str:
    return f' {name}="{value}"' if value else ""


def _nw(s: str) -> str:
    """Trozo de cabecera que no se parte (una condición como «S_T < F» o «> 10 %»)."""
    return f'<span class="nw">{s}</span>'


ARROWS = {1: '<span class="up">▲ deprecia</span>', -1: '<span class="down">▼ aprecia</span>', 0: '<span class="flat">◆ mixto</span>'}


def _fund_value(v: str) -> str:
    """Valor de la Tabla A.1.1. El paréntesis final (rango, contexto) va en letra pequeña y sin partir, y cada tramo
    separado por « / » (una calificación: «Fitch BB») tampoco se parte. En el celular, lo que no cabe baja entero al
    renglón siguiente."""
    m = re.fullmatch(r"(.+?) \((.+)\)", v)
    main, note = (m[1], m[2]) if m else (v, "")
    parts = [escape(p) for p in main.split(" / ")]
    if len(parts) > 1 or note:  # con paréntesis, la cifra («61 % del PIB») tampoco se parte: solo se corta antes de él
        parts = [_nw(p + (f"{NBSP}/" if k < len(parts) - 1 else "")) for k, p in enumerate(parts)]
    return " ".join(parts) + (f' <small class="nw">({escape(note)})</small>' if note else "")


def fundamentals(R: dict) -> str:
    rows, sep, prev = [], {}, None
    for i, f in enumerate(R["inp"]["fundamentales"]):
        new = f["grupo"] != prev
        if new and i:
            sep[i] = "sep"
        prev = f["grupo"]
        rows.append([f"<b>{escape(f['grupo'])}</b>" if new else "", escape(f["indicador"]), _fund_value(f["valor"]),
                     escape(f["fecha"]), ARROWS[f["efecto"]], escape(f["fuente"])])
    # En el celular cada indicador es una tarjeta: bloque arriba, valor a la derecha y fecha, presión y fuente debajo.
    return html_table(["Bloque", "Indicador", "Valor", "Fecha", "Presión sobre el peso", "Fuente"], rows, "llrccl",
                      cls="compact fund", row_cls=sep, nowrap={2, 3, 4}, stack=True, eyebrow=0)


def scenarios(R: dict) -> str:
    rows = []
    for s in R["scenarios"]:
        e = R["exp_paths"][s.key]
        rows.append([f"<b>{s.nombre}</b>", num(s.trm_12m), pct(s.trm_12m / R["s0"] - 1, 1, True),
                     pct(s.deriva_lp, 1), num(e[-1]), pct(s.probabilidad, 0), escape(s.narrativa)])
    rows.append(["<b>Esperanza ponderada</b>", num(R["a1"]["expected_12m"]), pct(R["a1"]["expected_12m"] / R["s0"] - 1, 1, True),
                 "", "", "100 %", "Promedio de los tres escenarios ponderado por su probabilidad subjetiva."])
    return html_table(["Escenario", "TRM oct-2027", "Var. vs. spot", "Deriva anual años 2–10", "TRM esperada oct-2036",
                       "Prob.", "Narrativa"], rows, "lrrrrcl", highlight={len(rows) - 1}, cls="compact",
                      wide={0: "10.5em", 2: "5.5em", 3: "6.5em", 4: "6.5em", 6: "17em"}, stack=True, full={6})


def loan_params(R: dict) -> str:
    a2, cred = R["a2"], R["inp"]["credito"]
    loan = a2["loan"]
    rows = [
        ["Entidad financiera", escape(cred["entidad"])],
        ["Producto de referencia", escape(cred["producto"])],
        ["Tasa base", f"Prime de Wells Fargo {pct(cred['prime'])} (vigente desde {fecha(cred['prime_vigencia'])})"],
        ["Spread", f"{num(cred['spread'] * 1e4)} pb"],
        ["Forma de cotización", escape(cred["forma_cotizacion"])],
        ["Tasa nominal / periódica", f"{pct(loan.nominal_rate)} N.T.V. → {pct(loan.periodic_rate, 3)} por trimestre {_nw('(63 de 252 días)')}"],
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
                     mm(r["interes_s0"]), mm(r["fx_capital"]), mm(r["fx_interes"]), mm(r["costo_financiero"]),
                     pct(r["tir_cop"]), pct(r["dev_implicita"], 2, True)])
    # Las unidades (COP millones) van en el pie de la tabla; así las cabeceras caben en dos renglones. Los efectos
    # cambiarios van bajo un solo rótulo y en el orden de la fórmula y de los Gráficos A.3.2 y A.3.3: capital, intereses.
    return html_table(["Trayectoria", "TRM oct-2036", "Última cuota", "Total pagado", "Intereses a TRM base",
                       "Capital", "Intereses", "Costo financiero", "Costo efectivo (E.A.)", "Devaluación implícita"], rows,
                      "lrrrrrrrrr", cls="compact", nowrap=set(range(10)), minw=860, groups={5: ("Efecto cambiario", 2)})


def _tenor(p: str) -> str:
    """Plazo del YAML ('1M', '1Y') en meses ('1 mes', '12 meses'), como el eje del Gráfico B.1.1."""
    n = int(p[:-1]) * {"M": 1, "Y": 12}[p[-1]]
    return f"{n}{NBSP}{'mes' if n == 1 else 'meses'}"


def market_quote(R: dict) -> str:
    mk = R["inp"]["forward_mercado"]
    rows = []
    for _, c in R["b1"]["curve"].iterrows():
        rows.append([_tenor(c["plazo"]), num(c["dias"]), num(c["dias_habiles"], 1), num(mk["spot_referencia"], 2),
                     num(c["puntos"]), num(c["forward"], 2), pct(c["dev"])])
    return html_table(["Plazo", "Días calendario", "Días hábiles", "Spot ref.", "Puntos forward", "Forward outright",
                       "Dev. implícita anual"], rows, "crrrrrr", cls="compact", highlight={3}, minw=620,
                      caption=f"Días hábiles en base 252; en dorado, el plazo de un año. Fuente: {escape(mk['fuente'])}. "
                              "Spot: cierre SET-ICAP FX del 13-oct-2026. Consulta: 15-oct-2026.")


def tradition(R: dict) -> str:
    tr = R["inp"]["forward_mercado"]["tradition"]
    rows = [[k.replace("-", "–"), num(v[0], 2) if v[0] else "Sin operaciones", num(v[1])] for k, v in tr["cierres"].items()]
    return html_table(["Tramo", "Precio de cierre", "N.º de operaciones"], rows, "crr", cls="compact narrow",
                      caption=f"Fuente: {escape(tr['fuente'])}.")


def cip(R: dict) -> str:
    rows = []
    for _, c in R["b1"]["cip"].iterrows():
        rows.append([f"<b>{escape(c['par'])}</b><br><small>{escape(c['nota'])}</small>", pct(c["r_cop"]), pct(c["r_usd"]),
                     pct(c["dev"]), num(c["forward_13oct"], 2), num(c["dif_cop"], 2), num(c["dif_pb"], 0),
                     num(c["forward_val"], 2)])
    mkt = R["b1"]
    pts = num(R["inp"]["forward_mercado"]["puntos"]["1Y"])
    rows.append([f"<b>Mercado (Itaú, {pts} puntos)</b>", "", "", pct(mkt["dev_1y"]), num(mkt["forward_1y_mkt"], 2), "n. a.", "n. a.",
                 num(mkt["forward_1y_val"], 2)])
    return html_table(["Par de tasas (E.A.)", "r COP", "r USD", "Devaluación teórica", "F teórico (spot 13-oct)",
                       "Mercado − teórico (COP)", "Mercado − teórico (pb)", f"F al spot de valoración ({num(R['s0'], 2)})"],
                      rows, "lrrrrrrr", highlight={len(rows) - 1}, cls="compact", wide={0: "15em"}, minw=880)


def valuation(R: dict) -> str:
    per_n = R["b2"][("central", "normal")]["per"]
    per_t = R["b2"][("central", "t")]["per"]
    coh = R["coherence"]
    rows = []
    for i, y in enumerate(per_n["anio"]):
        pv = per_n["payoff_media"][i] / (1 + R["disc_rate"]) ** y
        rows.append([f"<b>Forward{NBSP}{i + 1}</b>", f"Año{NBSP}{y - 1} → año{NBSP}{y}", usd(coh["cubierto_usd"][i]),
                     f"{num(per_n['forward_media'][i])} <small>({num(per_n['forward_p5'][i])}–{num(per_n['forward_p95'][i])})</small>",
                     num(per_n["spot_t_media"][i]), mm(per_n["payoff_media"][i], 2), mm(per_t["payoff_media"][i], 2),
                     mm(pv, 2), pct(per_n["proteccion"][i], 1)])
    # Un renglón por contrato: la vigencia va corta y sin partir («Año 6 → año 7»); el «fin de año» va en la cabecera.
    return html_table(["Contrato", f"Pacto → vencimiento {_nw('(fin de año)')}", "Nominal", "F pactado medio (P5–P95)",
                       "TRM al vencimiento (media)", "Liquidación esperada, normal", "Liquidación esperada, t",
                       "Valor presente hoy", "P(protección)"],
                      rows, "lcrrrrrrr", cls="compact", nowrap=set(range(9)), minw=860)


def coherence(R: dict) -> str:
    c = R["coherence"]
    rows = [[f"Año{NBSP}{int(r['anio'])}", usd(r["obligacion_usd"]), usd(r["capital_usd"]), usd(r["interes_usd"]),
             usd(r["cubierto_usd"]), usd(r["abierto_usd"]), usd(r["saldo_inicio_usd"]),
             pct(r["cubierto_usd"] / r["obligacion_usd"], 0)] for _, r in c.iterrows()]
    rows.append(["<b>Total años 7–10</b>", usd(c["obligacion_usd"].sum()), usd(c["capital_usd"].sum()),
                 usd(c["interes_usd"].sum()), usd(c["cubierto_usd"].sum()), usd(c["abierto_usd"].sum()),
                 usd(R["a2"]["balance_end_y6"]), pct(c["cubierto_usd"].sum() / c["obligacion_usd"].sum(), 0)])
    return html_table(["Año", "Pagos programados", "de los cuales capital", "de los cuales interés", "Nominal forward (75 %)",
                       "Abierto (25 %)", "Saldo de capital al inicio", "Cubierto / obligación"], rows, "lrrrrrrr",
                      highlight={len(rows) - 1}, cls="compact", nowrap=set(range(8)), minw=860)


def proportions(R: dict) -> str:
    names = {s.key: s.nombre for s in R["scenarios"]} | {"neutral": "Neutral al riesgo (referencia)"}
    rows, hl = [], set()
    for key in ("favorable", "central", "adverso", "neutral"):
        for dist in ("", *DISTS):
            if key == "central":
                hl.add(len(rows))
            if not dist:
                rows.append(names[key])
                continue
            p = R["b2"][(key, dist)]["pooled"]
            rows.append([_dist(dist), pct(p["proteccion"], 1), pct(p["costo_oportunidad"], 1),
                         pct(p["extrema_exposicion"], 1), pct(p["extrema_derivado"], 1), pct(p["fracaso"], 1),
                         mm(p["payoff_media"], 2), mm(p["payoff_cvar"], 1), pct(p["prob_total_negativo"], 1)])
    def cond(op: str, rhs: str) -> str:  # la condición que define la columna no se parte
        return _nw(f"(S<sub>T</sub>{NBSP}{op}{NBSP}{rhs})")

    return html_table(["Innovación", f"Protección {cond('&gt;', 'F')}", f"Costo de oportunidad {cond('&lt;', 'F')}",
                       f"Pérdida cambiaria extrema {cond('&gt;', '1,2F')}",
                       f"Pérdida extrema del derivado {cond('&lt;', '0,8F')}", "Fracaso por desfase",
                       "Liquidación media por forward", f"CVaR 5 % de la{NBSP}liquidación",
                       f"P(resultado de los 4 {_nw(f'forwards{NBSP}&lt;{NBSP}0)')}"], rows, "lrrrrrrrr", highlight=hl,
                      cls="compact grouped", nowrap=set(range(9)), minw=820)


def quadrants(R: dict) -> str:
    labels = [("proteccion_efectiva", "Protección efectiva", "Forward gana y las cuotas del año superaron el presupuesto: compensó la depreciación."),
              ("costo_op_puro", "Costo de oportunidad (cobertura exitosa)", "Forward pierde, pero las cuotas costaron menos que el presupuesto: el costo quedó fijado; es pérdida del derivado, no fracaso."),
              ("sobrecompensacion", "Sobrecompensación", "Forward gana aunque las cuotas costaron menos: la TRM subió al cierre del año tras pagos baratos."),
              ("fracaso", "Fracaso por desfase temporal", "Forward pierde y las cuotas superaron el presupuesto: la TRM subió durante el año y cayó bajo F al vencimiento.")]
    rows = []
    for key, name, desc in labels:
        rows.append([f"<b>{name}</b>", desc] + [pct(R["b2"][("central", d)]["pooled"][key], 1) for d in DISTS])
    return html_table(["Resultado", "Interpretación", *(_dist(d) for d in DISTS)], rows, "llrr", cls="compact",
                      wide={0: "11em"}, stack=True, full={1})


def combined_cost(R: dict) -> str:
    rows = []
    for dist in DISTS:
        per = R["b2"][("central", dist)]["per"]
        rows.append(DISTS[dist])
        for i, y in enumerate(per["anio"]):
            rows.append([f"Año{NBSP}{y}", num(per["forward_media"][i]), num(per["tasa_u_media"][i]),
                         num(per["tasa_h_media"][i]), num(per["tasa_u_p95"][i]), num(per["tasa_h_p95"][i]),
                         pct(per["dev_u_sd"][i], 2), pct(per["dev_h_sd"][i], 2), pct(per["dev_u_10"][i], 2),
                         pct(per["dev_h_10"][i], 2)])
    # Cabecera de dos niveles: cada medida agrupa su par sin cobertura / 75/25, así la condición «> 10 %» sale una vez.
    pair = ["Sin cob.", "75/25"]
    return html_table(["Año", "F medio", *pair * 4], rows, "lrrrrrrrrr", cls="compact grouped", nowrap=set(range(10)),
                      minw=820, groups={2: ("Tasa efectiva media", 2), 4: ("Tasa efectiva P95", 2),
                                        6: ("σ desviación vs. presupuesto", 2),
                                        8: (_nw(f"P(sobrecosto{NBSP}&gt;{NBSP}10{NBSP}%)"), 2)})


def tails(R: dict) -> str:
    rows, prev = [], None
    for _, r in R["tails"].iterrows():
        if r["dist"] != prev:
            rows.append(r["dist"])
            prev = r["dist"]
        rows.append([f"{r['horizonte']}{NBSP}mes" + ("" if r["horizonte"] == 1 else "es"), num(r["curtosis"], 2),
                     pct(r["p_2sd"], 2), pct(r["p_3sd"], 3), num(r["q999"], 2)])
    return html_table(["Horizonte", "Exceso de curtosis", f"P(choque {_nw(f'&gt;{NBSP}2σ)')}",
                       f"P(choque {_nw(f'&gt;{NBSP}3σ)')}", "Cuantil 99,9 % (σ)"],
                      rows, "lrrrr", cls="compact grouped", nowrap=set(range(5)))


def b3_summary(R: dict) -> str:
    names = {s.key: s.nombre for s in R["scenarios"]} | {"neutral": "Neutral al riesgo"}
    short = {"sin": "Sin cobertura", "con": "Con forwards"}  # el 75 % de los años 7–10 ya está en el texto y el pie
    rows, hl, sep = [], set(), {}
    for key in ("favorable", "central", "adverso", "neutral"):
        if key == "central":
            hl.add(len(rows))
        rows.append(names[key])
        for j, dist in enumerate(DISTS):
            for k, strat in enumerate(STRATS):
                m = R["b3"][(key, dist, strat)]
                if key == "central":
                    hl.add(len(rows))
                if j and not k:
                    sep[len(rows)] = "sub"
                rows.append([_dist(dist) if k == 0 else "", short[strat], mm(m["total_media"]), mm(m["total_sd"]),
                             mm(m["total_p95"]), mm(m["total_cvar95"]),
                             f"{pct(m['tir_media'])} <small>({pct(m['tir_p5'], 1)}{NBSP}–{NBSP}{pct(m['tir_p95'], 1)})</small>",
                             mm(m["vp_media"]), mm(m["forward_neto"], 2) if strat == "con" else "n. a."])
    return html_table(["Innovación", "Estrategia", "Total pagado (media)", "σ total", "P95 total", "CVaR 95 %",
                       "TIR en COP: media (P5–P95)", "VP a TES 10A", "Resultado forwards"], rows, "llrrrrrrr",
                      highlight=hl, row_cls=sep, cls="compact grouped", nowrap=set(range(9)), minw=820)


def b3_years710(R: dict) -> str:
    names = {s.key: s.nombre for s in R["scenarios"]} | {"neutral": "Neutral al riesgo"}
    rows, hl = [], set()
    for key in ("favorable", "central", "adverso"):
        if key == "central":
            hl.add(len(rows))
        rows.append(names[key])
        for dist in DISTS:
            u, h = R["b3"][(key, dist, "sin")], R["b3"][(key, dist, "con")]
            if key == "central":
                hl.add(len(rows))
            rows.append([_dist(dist), mm(u["y710_media"]), mm(h["y710_media"]),
                         f"{mm(u['y710_sd'])} → {mm(h['y710_sd'])}", pct(h["y710_sd"] / u["y710_sd"] - 1, 1),
                         f"{mm(u['y710_sd_cond'])} → {mm(h['y710_sd_cond'])}", pct(h["y710_sd_cond"] / u["y710_sd_cond"] - 1, 1),
                         f"{mm(u['y710_cvar95'])} → {mm(h['y710_cvar95'])}",
                         f"{pct(u['dev_sd'], 2)} → {pct(h['dev_sd'], 2)}", f"{pct(u['dev_10'], 2)} → {pct(h['dev_10'], 2)}"])
    # Cabecera de dos niveles: el costo y las dos σ agrupan sus columnas (sin / con cobertura, sin → con y Δ). Las
    # cabeceras sueltas van en dos renglones fijos para que el ancho sobrante vaya a los grupos. Unidades y lectura de
    # las flechas (sin → con cobertura) en el pie.
    sc = f"Sin{NBSP}→{NBSP}con"
    return html_table(["Innovación", "Sin", "Con", sc, "Δ σ", sc, "Δ σ", "CVaR 95 %", "σ desviación<br>presupuestal",
                       f"P(sobrecosto<br>anual {_nw(f'&gt;{NBSP}10{NBSP}%)')}"],
                      rows, "lrrrrrrrrr", highlight=hl, cls="compact grouped", nowrap=set(range(10)), minw=860,
                      groups={1: (f"Costo años{NBSP}7–10", 2), 3: ("σ incondicional", 2),
                              5: (f"σ condicional a{NBSP}TRM{NBSP}año{NBSP}6", 2)})


def _dist(d: str) -> str:
    return DISTS[d].replace(" ", NBSP)


def amortization(R: dict) -> str:
    """Tabla A.2.2: las 40 cuotas en USD; los años 7 a 10 (los que cubren los forwards) en verde."""
    s = R["a2"]["schedule"]
    rows, rc = [], {}
    for i, r in s.reset_index(drop=True).iterrows():
        rc[i] = " ".join(x for x in ("hg" if r["anio"] in HEDGE_YEARS else "",
                                     "sep" if i and r["anio"] != s["anio"].iloc[i - 1] else "") if x)
        rows.append([str(int(r["periodo"])), fecha(r["fecha"]), str(int(r["anio"])),
                     *(num(r[c], 2) for c in ("saldo_inicial", "interes", "abono_capital", "cuota", "saldo_final"))])
    foot = ["Σ", "", "", "", *(num(s[c].sum(), 2) for c in ("interes", "abono_capital", "cuota")), ""]
    return html_table(["Trim.", "Fecha", "Año", "Saldo inicial", "Interés", "Abono a capital", "Cuota", "Saldo final"],
                      rows, "cccrrrrr", cls="compact amort", row_cls=rc, foot=foot, nowrap=set(range(8)), minw=660,
                      vscroll=True)


def consolidated(R: dict) -> str:
    """Tabla B.3.1: flujo consolidado esperado en COP para cada escenario, innovación y estrategia.

    Las 12 combinaciones van como tablas en paneles; tres grupos de pestañas (.tabs, el componente de la página)
    prenden un marcador por dimensión y el CSS (.combo) deja visible el panel que coincide con los tres.
    """
    a2, sched = R["a2"], R["a2"]["schedule"]
    t0 = fecha(R["inp"]["meta"]["fecha_valoracion"])
    names = {s.key: s.nombre for s in R["scenarios"]}
    dims = [("Escenario", [(k, names[k]) for k in ("favorable", "central", "adverso")]),
            ("Innovación", list(DISTS.items())),
            ("Estrategia", list(STRATS.items()))]
    start = ("central", "normal", "con")
    heads = ["Trim.", "Fecha", "Concepto", "USD", "TRM esperada", "Cuota en COP", "Liquidación forward", "Flujo neto COP"]
    usd_q = [num(-c, 2) for c in sched["cuota"]]
    base = [["t0", t0, "Compra de maquinaria amarilla", "", "", "", "", num(-a2["machine"])],
            ["t0", t0, f"Aporte propio (10{NBSP}%)", "", "", "", "", num(a2["equity"])],
            ["t0", t0, "Desembolso del crédito", num(a2["loan"].principal_usd, 2), num(R["s0"], 2), "", "",
             num(a2["financed_cop"])]]
    panes = []
    for key in dims[0][1]:
        for dist in dims[1][1]:
            for strat in dims[2][1]:
                combo = (key[0], dist[0], strat[0])
                f = R["flows"][combo]
                rows, rc = [r[:] for r in base], {0: "t0", 1: "t0", 2: "t0"}
                for q in range(len(sched)):
                    fwd = f["forward_media"][q]
                    if abs(fwd) > 0:
                        rc[len(rows)] = "hg"
                    rows.append([str(q + 1), fecha(sched["fecha"].iloc[q]), f"Cuota {q + 1} (año{NBSP}{sched['anio'].iloc[q]})",
                                 usd_q[q], num(f["trm_media"][q], 2), num(-f["cuota_media"][q]),
                                 num(fwd) if abs(fwd) > 0 else "", num(-f["neto_media"][q])])
                rc[3] = "sep"
                # Sin cobertura la columna del forward va en blanco en todas las filas; el total también.
                fwd_sum = num(f["forward_media"].sum()) if any(abs(x) > 0 for x in f["forward_media"]) else ""
                foot = ["Σ", "", "Total 40 cuotas", num(-sched["cuota"].sum(), 2), "", num(-f["cuota_media"].sum()),
                        fwd_sum, num(-f["neto_media"].sum())]
                table = html_table(heads, rows, "cclrrrrr", cls="compact", row_cls=rc, foot=foot, nowrap=set(range(8)),
                                   minw=780, vscroll=True)
                idx = " ".join(f'data-{d}="{[v[0] for v in dims[n][1]].index(combo[n])}"' for n, d in enumerate("abc"))
                panes.append(f'<div class="cpane{" on" if combo == start else ""}" {idx}>{table}</div>')
    tabs, marks = [], []
    for n, (title, opts) in enumerate(dims):
        d = "abc"[n]
        on = [_attr("class", "on" if k == start[n] else "") for k, _ in opts]
        btns = "".join(f'<button{on[j]} data-target="b31-{d}{j}">{escape(lab).replace(" %", NBSP + "%")}</button>'
                       for j, (_, lab) in enumerate(opts))
        tabs.append(f'<div class="tabs" data-group="b31-{d}" role="group" aria-label="{title}">{btns}</div>')
        marks += [f'<i hidden id="b31-{d}{j}" data-{d}="{j}"{on[j]}></i>' for j in range(len(opts))]
    return f'<div class="combo">{"".join(tabs)}{"".join(marks)}{"".join(panes)}</div>'


def strategies(R: dict) -> str:
    s = R["sens"]["strategies"]
    rows = [[f"<b>{escape(r['estrategia'])}</b>", mm(r["media"]), mm(r["costo_esperado"], 2), mm(r["sd"]), mm(r["sd_cond"]),
             mm(r["cvar95"]), pct(r["dev_sd"], 2)] for _, r in s.iterrows()]
    return html_table(["Estrategia", "Costo años 7–10", "Costo esperado de cubrir", "σ incondicional",
                       "σ condicional a TRM año 6", "CVaR 95 %", "σ desviación presupuestal"], rows, "lrrrrrr",
                      highlight={1}, cls="compact", wide={0: "14em"}, minw=780)


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
                      cls="compact", minw=760)


def sens_d(R: dict) -> str:
    d = R["sens"]["d"]
    lp = R["inp"]["tasas"]["largo_plazo"]
    rows, hl = [], set()
    for _, x in d.iterrows():
        label = pct(x["d"])
        if abs(x["d"] - R["d_lr"]) < 1e-9:
            # la fila base va entera en un renglón (en el celular la nota partida dejaba «vs.» colgando)
            label = f'<span class="nw">{label} <small>(base: {pct(lp["r_cop"])} vs. {pct(lp["r_usd"])})</small></span>'
            hl.add(len(rows))
        elif abs(x["d"] - R["dev_lt"]) < 1e-9:
            label += " <small>(TES 10A vs UST 10A)</small>"
        elif abs(x["d"] - R["b1"]["dev_1y"]) < 1e-9:
            label += " <small>(forward 1A de hoy)</small>"
        rows.append([label, mm(x["forward_neto"], 2), pct(x["proteccion"], 1), mm(x["y710_media"]), pct(x["tir_media"])])
    return html_table(["Prima forward anual (años 7–10)", "Resultado esperado 4 forwards (COP M)", "P(protección)",
                       "Costo años 7–10 con cobertura (COP M)", "TIR en COP con cobertura"], rows, "lrrrr", highlight=hl,
                      cls="compact", wide={0: "13em"}, minw=640)


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
    fns = [fundamentals, scenarios, loan_params, amortization, a3_summary, market_quote, tradition, cip, valuation,
           coherence, proportions, quadrants, combined_cost, tails, consolidated, b3_summary, b3_years710, strategies,
           sens_rate, sens_d, sources]
    return {fn.__name__: fn(R) for fn in fns}
