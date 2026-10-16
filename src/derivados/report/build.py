"""Genera docs/index.html: informe interactivo con resultados (sin código) para GitHub Pages.

Uso: uv run python -m derivados.report.build
"""

from __future__ import annotations

from pathlib import Path

import plotly.offline as po
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .. import forwards as fw
from ..analysis import build
from ..data import ROOT
from . import figures, tables
from .fmt import FILTERS, fecha, mcop, num, pct, usd

TEMPLATES = Path(__file__).parent / "templates"
OUTPUT = ROOT / "docs" / "index.html"


def key_numbers(R: dict) -> dict:
    inp, a1, a2, a3, b1 = R["inp"], R["a1"], R["a2"], R["a3"], R["b1"]
    loan, sched, st = a2["loan"], a2["schedule"], a1["stats"]
    summ = a3["summary"].set_index("key")
    coh = R["coherence"]
    k: dict = {}

    k["s0"] = num(R["s0"], 2)
    k["fecha_val"] = fecha(R["val_date"], largo=True)
    k["machine"] = f"COP {num(a2['machine'])}"
    k["equity"] = f"COP {num(a2['equity'])}"
    k["financed"] = f"COP {num(a2['financed_cop'])}"
    k["p_usd"] = usd(loan.principal_usd)
    k["prime"] = pct(inp["credito"]["prime"])
    k["spread_pb"] = num(inp["credito"]["spread"] * 1e4)
    k["rate"] = pct(loan.nominal_rate)
    k["iq"] = pct(loan.periodic_rate, 3)
    k["ea"] = pct(loan.effective_annual_rate)
    k["cuota_usd"] = usd(loan.installment)
    k["p_usd_num"] = num(loan.principal_usd, 2)
    k["cuota_num"] = num(loan.installment, 2)
    k["total_usd"] = usd(a2["total_paid_usd"])
    k["int_usd"] = usd(a2["total_interest_usd"])
    k["int_over_p"] = pct(a2["total_interest_usd"] / loan.principal_usd, 1)
    k["int_share_q1"] = pct(sched["interes"].iloc[0] / loan.installment, 1)
    k["int_share_q40"] = pct(sched["interes"].iloc[-1] / loan.installment, 1)
    k["balance_y6"] = usd(a2["balance_end_y6"])
    k["balance_y6_share"] = pct(a2["balance_end_y6"] / loan.principal_usd, 1)
    k["remaining_y6"] = usd(16 * loan.installment)
    k["hedged_total"] = usd(coh["cubierto_usd"].sum())
    k["per_forward"] = usd(coh["cubierto_usd"].iloc[0])
    k["obligation_year"] = usd(coh["obligacion_usd"].iloc[0])
    k["open_year"] = usd(coh["abierto_usd"].iloc[0])
    k["sba504"] = pct(next(r["tasa"] for r in inp["credito"]["referencias"] if "504" in r["nombre"]))
    k["sba7a"] = pct(next(r["tasa"] for r in inp["credito"]["referencias"] if "7(a)" in r["nombre"]))
    k["prime_plus_hike"] = pct(loan.nominal_rate + 0.0025)

    # A.1
    k["var_anio"] = pct(st["var_anio"], 1, True)
    k["var_12m"] = pct(st["var_12m"], 1, True)
    k["var_anio_abs"] = pct(abs(st["var_anio"]), 1)
    k["var_12m_abs"] = pct(abs(st["var_12m"]), 1)
    for name in ("inicio_2026", "hace_1_anio", "max_2026", "min_2026", "posesion", "segunda_vuelta",
                 "post_segunda_vuelta", "max_hist"):
        k[name] = num(st[name], 2)
    k["var_posesion"] = pct(R["s0"] / st["posesion"] - 1, 1, True)
    k["fecha_max_2026"] = fecha(st["fecha_max_2026"])
    k["fecha_min_2026"] = fecha(st["fecha_min_2026"])
    k["fecha_max_hist"] = fecha(st["fecha_max_hist"])
    for name in ("corr_2010", "corr_2014_16", "corr_2026", "corr24_ult"):
        k[name] = ("+" if st[name] > 0 else "") + num(st[name], 2)
    k["brent"] = f"USD {num(st['brent_ult'], 2)}"
    k["brent_fecha"] = fecha(st["brent_fecha"])
    t = inp["tasas"]
    k["banrep"] = pct(t["banrep"]["valor"])
    k["fed"] = f"{pct(t['fed_rango']['inferior'])}–{pct(t['fed_rango']['superior'])}"
    k["diff_policy"] = num((t["banrep"]["valor"] - t["fed_rango"]["superior"]) * 100, 2) + " pp"
    k["expected_12m"] = num(a1["expected_12m"])
    k["expected_12m_var"] = pct(a1["expected_12m"] / R["s0"] - 1, 1, True)
    k["exp_vs_fwd"] = pct(abs(a1["expected_12m"] / b1["forward_1y_val"] - 1), 1)
    for p, v in a1["rolling9"].items():
        k[f"roll9_{p}"] = pct(v, 1, True)
    k["infl_col"] = num(a1["inflation_col"]["2026"], 2) + " %"
    k["infl_us"] = num(a1["inflation_us"]["2026"], 2) + " %"
    k["scen"] = {s.key: {"trm": num(s.trm_12m), "var": pct(s.trm_12m / R["s0"] - 1, 1, True),
                         "drift": pct(s.deriva_lp, 1), "prob": pct(s.probabilidad, 0), "nombre": s.nombre,
                         "trm_2036": num(R["exp_paths"][s.key][-1])} for s in R["scenarios"]}

    # A.3
    for key in ("base", "favorable", "central", "adverso"):
        r = summ.loc[key]
        k[f"a3_{key}"] = {
            "total": mcop(r["total_cop"]), "costo": mcop(r["costo_financiero"]), "int": mcop(r["interes_s0"]),
            "fxi": mcop(r["fx_interes"]), "fxk": mcop(r["fx_capital"]), "tir": pct(r["tir_cop"]),
            "dev": pct(r["dev_implicita"], 2, True), "ultima": mcop(r["cuota_ultima"], 2),
            "trm_final": num(r["trm_final"]),
            "var_total": pct(r["total_cop"] / summ.loc["base", "total_cop"] - 1, 1, True),
            "fx_total": mcop(r["fx_interes"] + r["fx_capital"]),
            "share_int": pct(r["interes_s0"] / r["costo_financiero"], 1) if r["costo_financiero"] else "—",
            "share_fx": pct((r["fx_interes"] + r["fx_capital"]) / r["costo_financiero"], 1) if r["costo_financiero"] else "—",
            "share_fxk_of_fx": pct(r["fx_capital"] / (r["fx_interes"] + r["fx_capital"]), 1)
            if abs(r["fx_interes"] + r["fx_capital"]) > 1 else "—",
            "cuota_var": pct(r["cuota_ultima"] / summ.loc["base", "cuota_ultima"] - 1, 1, True),
            "cuota_var_abs": pct(abs(r["cuota_ultima"] / summ.loc["base", "cuota_ultima"] - 1), 1),
        }
    k["base_cuota"] = f"COP {num(a3['base']['cuota_cop'].iloc[0])}"
    fan = a3["fan"]["normal"]
    k["fan_last_p5"] = mcop(fan[5][-1], 1)
    k["fan_last_p95"] = mcop(fan[95][-1], 1)
    k["fan_last_p50"] = mcop(fan[50][-1], 1)
    k["fan_y1_p95"] = mcop(fan[95][3], 1)
    k["fan_y1_p5"] = mcop(fan[5][3], 1)

    # B.1
    mk = inp["forward_mercado"]
    k["spot_ref"] = num(mk["spot_referencia"], 2)
    k["pts_1y"] = num(mk["puntos"]["1Y"])
    k["pts_3y"] = num(mk["puntos"]["3Y"])
    k["f_1y_mkt"] = num(b1["forward_1y_mkt"], 2)
    k["f_1y_val"] = num(b1["forward_1y_val"], 2)
    k["dev_1y"] = pct(b1["dev_1y"])
    curve = b1["curve"].set_index("plazo")
    k["dev_3y"] = pct(curve.loc["3Y", "dev"])
    k["dev_6m"] = pct(curve.loc["6M", "dev"])
    k["dev_1m"] = pct(curve.loc["1M", "dev"])
    h1 = mk["historia_1y"]
    k["pts_hist"] = {kk: num(v) for kk, v in h1.items()}
    cip = b1["cip"]
    k["cip"] = [{"dev": pct(r["dev"]), "f": num(r["forward_13oct"], 2), "dif": num(r["dif_cop"], 2),
                 "pb": num(r["dif_pb"]), "rc": pct(r["r_cop"]), "ru": pct(r["r_usd"]), "fval": num(r["forward_val"], 2)}
                for _, r in cip.iterrows()]
    base_f = fw.cip_forward(R["s0"], cip.loc[0, "r_cop"], cip.loc[0, "r_usd"], 252)
    k["dF_rcop"] = num(fw.cip_forward(R["s0"], cip.loc[0, "r_cop"] + 0.0025, cip.loc[0, "r_usd"], 252) - base_f, 1)
    k["dF_rusd"] = num(base_f - fw.cip_forward(R["s0"], cip.loc[0, "r_cop"], cip.loc[0, "r_usd"] + 0.0025, 252), 1)
    lr = t["largo_plazo"]
    k["r_cop_lr"] = pct(lr["r_cop"])
    k["r_usd_lr"] = pct(lr["r_usd"])
    k["d_lr"] = pct(R["d_lr"])
    k["dev_lt"] = pct(R["dev_lt"])
    k["tes10"] = pct(t["tes_jun2032"]["valor"])
    k["ust10"] = pct(t["ust_10y"]["valor"])
    k["disc"] = pct(R["disc_rate"])
    per = R["b2"][("central", "normal")]["per"]
    k["f7_mean"] = num(per["forward_media"].iloc[0])
    k["f10_mean"] = num(per["forward_media"].iloc[-1])
    k["f7_p5"] = num(per["forward_p5"].iloc[0])
    k["f7_p95"] = num(per["forward_p95"].iloc[0])
    k["f10_p5"] = num(per["forward_p5"].iloc[-1])
    k["f10_p95"] = num(per["forward_p95"].iloc[-1])

    # B.2
    cal = R["cal"]
    k["sigma"] = pct(cal.sigma)
    k["nu"] = num(cal.nu, 2)
    k["n_obs"] = num(cal.n_obs)
    k["cal_start"], k["cal_end"] = cal.start, cal.end
    k["exkurt_m"] = num(cal.ex_kurt, 2)
    k["skew_m"] = num(cal.skew, 2)
    k["sigma_d"] = pct(cal.sigma_daily)
    k["nu_d"] = num(cal.nu_daily, 2)
    k["exkurt_d"] = num(cal.ex_kurt_daily, 2)
    k["n_paths"] = num(R["n_paths"])
    k["minvar"] = pct(R["sens"]["beta_minvar"], 1)
    for key in ("favorable", "central", "adverso", "neutral"):
        for dist in ("normal", "t"):
            p = R["b2"][(key, dist)]["pooled"]
            k[f"b2_{key}_{dist}"] = {
                "prot": pct(p["proteccion"], 1), "opp": pct(p["costo_oportunidad"], 1),
                "ext_up": pct(p["extrema_exposicion"], 1), "ext_dn": pct(p["extrema_derivado"], 1),
                "fail": pct(p["fracaso"], 1), "over": pct(p["sobrecompensacion"], 1),
                "eff": pct(p["proteccion_efectiva"], 1), "opp_pure": pct(p["costo_op_puro"], 1),
                "payoff": mcop(p["payoff_media"], 2), "payoff_total": mcop(p["payoff_total_media"], 1),
                "p_neg": pct(p["prob_total_negativo"], 1), "cvar": mcop(p["payoff_cvar"], 1),
                "dev_u": pct(p["dev_u_sd"], 1), "dev_h": pct(p["dev_h_sd"], 1),
                "dev_u10": pct(p["dev_u_10"], 1), "dev_h10": pct(p["dev_h_10"], 2),
            }
    tl = R["tails"].set_index(["dist", "horizonte"])
    for dist, tag in (("Normal", "n"), ("t de Student", "t")):
        for hzn in (1, 3, 12):
            k[f"tail_{tag}{hzn}"] = {"kurt": num(tl.loc[(dist, hzn), "curtosis"], 2),
                                     "p3": pct(tl.loc[(dist, hzn), "p_3sd"], 2),
                                     "q": num(tl.loc[(dist, hzn), "q999"], 2)}

    # B.3
    for key in ("favorable", "central", "adverso", "neutral"):
        for dist in ("normal", "t"):
            u, h = R["b3"][(key, dist, "sin")], R["b3"][(key, dist, "con")]
            k[f"b3_{key}_{dist}"] = {
                "tot_u": mcop(u["total_media"]), "tot_h": mcop(h["total_media"]),
                "sd_u": mcop(u["total_sd"]), "sd_h": mcop(h["total_sd"]),
                "sd_chg": pct(h["total_sd"] / u["total_sd"] - 1, 1, True),
                "sd_chg_abs": pct(abs(h["total_sd"] / u["total_sd"] - 1), 1),
                "y710_sd_chg_abs": pct(abs(h["y710_sd"] / u["y710_sd"] - 1), 1),
                "y710_cond_chg_abs": pct(abs(h["y710_sd_cond"] / u["y710_sd_cond"] - 1), 1),
                "fwd_abs": mcop(abs(h["forward_neto"]), 1),
                "fwd_share_abs": pct(abs(h["forward_neto"] / u["total_media"]), 2),
                "tir_u": pct(u["tir_media"]), "tir_h": pct(h["tir_media"]),
                "tir_u_p5": pct(u["tir_p5"], 1), "tir_u_p95": pct(u["tir_p95"], 1),
                "tir_h_p5": pct(h["tir_p5"], 1), "tir_h_p95": pct(h["tir_p95"], 1),
                "vp_u": mcop(u["vp_media"]), "vp_h": mcop(h["vp_media"]),
                "y710_u": mcop(u["y710_media"]), "y710_h": mcop(h["y710_media"]),
                "y710_sd_u": mcop(u["y710_sd"]), "y710_sd_h": mcop(h["y710_sd"]),
                "y710_sd_chg": pct(h["y710_sd"] / u["y710_sd"] - 1, 1, True),
                "y710_cond_u": mcop(u["y710_sd_cond"]), "y710_cond_h": mcop(h["y710_sd_cond"]),
                "y710_cond_chg": pct(h["y710_sd_cond"] / u["y710_sd_cond"] - 1, 1, True),
                "y710_cvar_u": mcop(u["y710_cvar95"]), "y710_cvar_h": mcop(h["y710_cvar95"]),
                "cvar_u": mcop(u["total_cvar95"]), "cvar_h": mcop(h["total_cvar95"]),
                "dev_u": pct(u["dev_sd"], 1), "dev_h": pct(h["dev_sd"], 2),
                "dev10_u": pct(u["dev_10"], 1), "dev10_h": pct(h["dev_10"], 2),
                "fwd": mcop(h["forward_neto"], 1), "fwd_share": pct(h["forward_neto"] / u["total_media"], 2, True),
                "y16_sd": mcop(u["y16_sd"]),
                "p95_u": mcop(u["total_p95"]), "p95_h": mcop(h["total_p95"]),
            }
    s = R["sens"]
    strat = s["strategies"].set_index("estrategia")
    k["strip_cond"] = mcop(strat.iloc[3]["sd_cond"])
    k["strip_cost"] = mcop(strat.iloc[3]["costo_esperado"], 1)
    k["strip_cond_chg"] = pct(abs(strat.iloc[3]["sd_cond"] / strat.iloc[0]["sd_cond"] - 1), 0)
    k["strip_sd"] = mcop(strat.iloc[3]["sd"])
    k["strip_dev"] = pct(strat.iloc[3]["dev_sd"], 2)
    k["qm_dev"] = pct(strat.iloc[2]["dev_sd"], 2)
    k["qm_cost"] = mcop(strat.iloc[2]["costo_esperado"], 1)
    k["qm_cond"] = mcop(strat.iloc[2]["sd_cond"])
    k["roll_dev"] = pct(strat.iloc[1]["dev_sd"], 2)
    k["roll_cond"] = mcop(strat.iloc[1]["sd_cond"])
    hr = s["hedge_ratio"].set_index("ratio")
    k["dev_hr100"] = pct(hr.loc[1.0, "dev_sd"], 1)
    k["dev_hr625"] = pct(hr.loc[0.625, "dev_sd"], 2)
    k["dev_hr50"] = pct(hr.loc[0.5, "dev_sd"], 2)
    d = s["d"]
    k["sens_d_min"] = pct(d["d"].min())
    k["sens_d_max"] = pct(d["d"].max())
    k["sens_fwd_min_d"] = mcop(d["forward_neto"].iloc[0], 1)
    k["sens_fwd_max_d"] = mcop(d["forward_neto"].iloc[-1], 1)
    k["sens_prot_min_d"] = pct(d["proteccion"].iloc[0], 1)
    k["sens_prot_max_d"] = pct(d["proteccion"].iloc[-1], 1)
    k["sens_fwd_dlt"] = mcop(d.loc[(d["d"] - R["dev_lt"]).abs() < 1e-9, "forward_neto"].iloc[0], 1)
    k["sens_fwd_d1y"] = mcop(d.loc[(d["d"] - b1["dev_1y"]).abs() < 1e-9, "forward_neto"].iloc[0], 1)
    k["sens_fwd_d1y_abs"] = mcop(abs(d.loc[(d["d"] - b1["dev_1y"]).abs() < 1e-9, "forward_neto"].iloc[0]), 1)
    k["sens_fwd_max_d_abs"] = mcop(abs(d["forward_neto"].iloc[-1]), 1)
    rt = s["rate"]
    k["tir_r85"] = pct(rt["tir_sin"].iloc[0])
    k["tir_r13"] = pct(rt["tir_sin"].iloc[-1])
    slope = (rt["tir_sin"].iloc[3] - rt["tir_sin"].iloc[1]) / 2
    k["tir_slope_pb"] = num(slope * 1e4)
    k["cuota_slope"] = usd((rt["cuota_usd"].iloc[3] - rt["cuota_usd"].iloc[1]) / 2)
    k["synth_1y"] = pct(R["synthetic"]["1Y"])
    k["synth_3y"] = pct(R["synthetic"]["3Y"])
    k["synth_lt"] = pct(R["synthetic"]["LT"])
    k["members"] = inp["meta"]["integrantes"]
    return k


def render(R: dict) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined, autoescape=False,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(FILTERS)
    tpl = env.get_template("report.html.j2")
    return tpl.render(
        R=R, k=key_numbers(R), fig=figures.build_all(R), tab=tables.build_all(R),
        plotly_js=f"https://cdn.plot.ly/plotly-{po.get_plotlyjs_version()}.min.js",
    )


def main() -> None:
    R = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(R), encoding="utf-8")
    (OUTPUT.parent / ".nojekyll").write_text("")
    print(f"Informe generado en {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
