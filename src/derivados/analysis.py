"""Orquesta los cálculos del informe (partes A y B) y entrega un diccionario de resultados."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import cashflows as cf
from . import forwards as fw
from . import fx_model as fx
from .credit import Loan
from .data import fred, manual_inputs, trm_business_days, trm_calendar, trm_month_end

N_PATHS = 20_000
SEED = 20261015
EXTREME = 0.20  # umbral de pérdida extrema: TRM al vencimiento ±20 % frente a la tasa pactada
BUDGET_TOL = 0.10  # desviación presupuestal tolerada
DISTS = {"normal": "Normal", "t": "t de Student"}
STRATS = {"sin": "Sin cobertura", "con": "Con forwards 75 % (años 7–10)"}
HEDGE_YEARS = (7, 8, 9, 10)
QUARTERS = np.arange(1, 41)


def _q(x: np.ndarray, p: float, axis: int = 0) -> np.ndarray:
    return np.percentile(x, p, axis=axis)


def _cvar(x: np.ndarray, level: float = 0.95) -> float:
    """Promedio del peor (1 - level) de los resultados (costos altos)."""
    cut = np.quantile(x, level)
    return float(x[x >= cut].mean())


def _policy_rate_series(inp: dict, end: pd.Timestamp) -> pd.Series:
    dec = inp["banrep_decisiones"]
    changes = {pd.Timestamp(dec["inicio"]["fecha"]): dec["inicio"]["tasa"]}
    for date, rate in dec["cambios"]:
        changes[pd.Timestamp(date) + pd.Timedelta(days=1)] = rate
    idx = pd.date_range(dec["inicio"]["fecha"], end, freq="D")
    return pd.Series(changes).reindex(idx).ffill()


def part_a1(inp: dict, s0: float, val_date: pd.Timestamp) -> dict:
    trm = trm_business_days()
    cal_trm = trm_calendar()
    brent_m = fred("DCOILBRENTEU").resample("ME").mean()
    m = trm_month_end()
    rets = pd.concat([np.log(m).diff(), np.log(brent_m).diff()], axis=1, join="inner").dropna()
    rets.columns = ["trm", "brent"]
    corr24 = rets["trm"].rolling(24).corr(rets["brent"]).dropna()

    cpi = fred("CPIAUCNS")
    us_yoy = ((cpi / cpi.shift(12, freq="MS") - 1).dropna() * 100)
    us_sep = {str(k.year): float(v) for k, v in us_yoy[us_yoy.index.month == 9].items() if k.year >= 2017}

    banrep = _policy_rate_series(inp, val_date)
    fed_u, fed_l = fred("DFEDTARU"), fred("DFEDTARL")
    rates = pd.DataFrame({"banrep": banrep}).join(fed_u.rename("fed_u")).join(fed_l.rename("fed_l")).ffill()
    rates = rates[rates.index >= "2021-01-01"]

    roll = {}
    for yrs in (9,):
        g = (np.log(m).diff(12 * yrs) / yrs).dropna()
        g = g[g.index >= "2005-01-01"]
        roll = {f"P{p}": float(np.expm1(g.quantile(p / 100))) for p in (10, 25, 50, 75, 90)}

    def at(date: str) -> float:
        return float(cal_trm.loc[date])

    y26 = trm.loc["2026"]
    stats_trm = {
        "inicio_2026": at("2026-01-01"),
        "hace_1_anio": at("2025-10-15"),
        "posesion": at("2026-08-07"),
        "segunda_vuelta": at("2026-06-19"),
        "post_segunda_vuelta": at("2026-06-24"),
        "max_2026": float(y26.max()),
        "fecha_max_2026": y26.idxmax(),
        "min_2026": float(y26.min()),
        "fecha_min_2026": y26.idxmin(),
        "max_hist": float(trm.max()),
        "fecha_max_hist": trm.idxmax(),
        "corr_2010": float(rets.loc["2010":].corr().iloc[0, 1]),
        "corr_2014_16": float(rets.loc["2014":"2016"].corr().iloc[0, 1]),
        "corr_2026": float(rets.loc["2026"].corr().iloc[0, 1]),
        "corr24_ult": float(corr24.iloc[-1]),
        "brent_ult": float(fred("DCOILBRENTEU").iloc[-1]),
        "brent_fecha": fred("DCOILBRENTEU").index[-1],
    }
    stats_trm["var_anio"] = s0 / stats_trm["inicio_2026"] - 1
    stats_trm["var_12m"] = s0 / stats_trm["hace_1_anio"] - 1

    scen = inp["escenarios"]["lista"]
    expected_12m = sum(s["trm_12m"] * s["probabilidad"] for s in scen)
    return {
        "trm_daily": trm[trm.index >= "2015-01-01"],
        "brent_monthly": brent_m[brent_m.index >= "2015-01-01"],
        "corr24": corr24[corr24.index >= "2012-01-01"],
        "rates": rates,
        "inflation_col": inp["inflacion"]["colombia_septiembre"]["valores"],
        "inflation_us": us_sep,
        "rolling9": roll,
        "stats": stats_trm,
        "expected_12m": expected_12m,
    }


def part_a2(inp: dict, s0: float, val_date: pd.Timestamp) -> dict:
    proj, cred = inp["proyecto"], inp["credito"]
    machine = proj["valor_maquinaria_cop"]
    equity = machine * proj["aporte_propio"]
    financed = machine - equity
    loan = Loan(financed / s0, cred["prime"] + cred["spread"], proj["plazo_anios"], proj["pagos_por_anio"])
    sched = loan.schedule(val_date)
    return {
        "loan": loan,
        "schedule": sched,
        "machine": machine,
        "equity": equity,
        "financed_cop": financed,
        "total_paid_usd": float(sched["cuota"].sum()),
        "total_interest_usd": float(sched["interes"].sum()),
        "balance_end_y6": float(sched.loc[sched["periodo"] == 24, "saldo_final"].iloc[0]),
        "q_rate_252": cred["prime"] + cred["spread"],
    }


def _decompose(sched: pd.DataFrame, s_q: np.ndarray, s0: float) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "periodo": sched["periodo"],
            "fecha": sched["fecha"],
            "trm": s_q,
            "cuota_usd": sched["cuota"],
            "interes_s0": sched["interes"] * s0,
            "capital_s0": sched["abono_capital"] * s0,
            "fx_interes": sched["interes"] * (s_q - s0),
            "fx_capital": sched["abono_capital"] * (s_q - s0),
        }
    )
    df["cuota_cop"] = df["cuota_usd"] * df["trm"]
    return df


def part_a3(a2: dict, s0: float, exp_paths: dict, sims: dict, scenarios: list) -> dict:
    sched, loan = a2["schedule"], a2["loan"]
    base = _decompose(sched, np.full(40, s0), s0)
    out = {"base": base, "escenarios": {}}
    summary = []
    rows = [("base", "Spot constante (base)", base)]
    for s in scenarios:
        q = exp_paths[s.key][3::3]
        rows.append((s.key, s.nombre, _decompose(sched, q, s0)))
    for key, name, df in rows:
        out["escenarios"][key] = df
        payments = df["cuota_cop"].to_numpy()
        irr = float(cf.irr_ea(a2["financed_cop"], payments[None, :])[0])
        summary.append(
            {
                "key": key,
                "escenario": name,
                "total_cop": payments.sum(),
                "costo_financiero": payments.sum() - a2["financed_cop"],
                "interes_s0": df["interes_s0"].sum(),
                "fx_interes": df["fx_interes"].sum(),
                "fx_capital": df["fx_capital"].sum(),
                "cuota_max": payments.max(),
                "cuota_ultima": payments[-1],
                "trm_final": df["trm"].iloc[-1],
                "tir_cop": irr,
                "dev_implicita": (1 + irr) / (1 + loan.effective_annual_rate) - 1,
            }
        )
    out["summary"] = pd.DataFrame(summary)
    fan = {}
    for dist in DISTS:
        pay = loan.installment * cf.quarterly_spots(sims[("central", dist)])[:, 1:]
        fan[dist] = {p: _q(pay, p) for p in (5, 25, 50, 75, 95)}
    out["fan"] = fan
    return out


def part_b1(inp: dict, s0: float, d_lr: float) -> dict:
    t, mk = inp["tasas"], inp["forward_mercado"]
    spot_ref = mk["spot_referencia"]
    curve = []
    for tenor, pts in mk["puntos"].items():
        days = mk["dias_calendario"][tenor]
        nb = fw.calendar_to_business(days)
        fwd = spot_ref + pts
        curve.append(
            {
                "plazo": tenor,
                "dias": days,
                "dias_habiles": nb,
                "puntos": pts,
                "forward": fwd,
                "dev": fw.implied_devaluation(fwd, spot_ref, nb),
            }
        )
    curve = pd.DataFrame(curve)
    dev_1y = float(curve.loc[curve["plazo"] == "1Y", "dev"].iloc[0])

    pairs = [
        ("Tasa BanRep vs. SOFR overnight", t["banrep"]["valor"], fw.ea_from_nominal(t["sofr"]["valor"], 1),
         "12,25 % E.A. / SOFR 3,88 % Act/360 capitalizada diariamente"),
        ("IBR 1 mes vs. swap SOFR 1 año", fw.ea_from_nominal(t["ibr_1m"]["valor"], 30),
         fw.ea_from_simple(t["sofr_swap_1y"]["valor"]), "IBR 11,50 % N.A. (30 días) / swap SOFR 4,3067 % Act/360"),
        ("TES nov-2027 vs. Tesoro EE. UU. 1 año", t["tes_nov2027"]["valor"],
         fw.ea_from_bond_equivalent(t["ust_1y"]["valor"]), "TES 11,70 % E.A. / UST 4,53 % semestral"),
        ("Tasas de largo plazo supuestas (años 7–10)", t["largo_plazo"]["r_cop"], t["largo_plazo"]["r_usd"],
         "7,50 % E.A. / 3,40 % E.A. — insumo para pactar los forwards futuros"),
    ]
    cip = []
    for name, rc, ru, note in pairs:
        f_ref = fw.cip_forward(spot_ref, rc, ru, 252)
        cip.append(
            {
                "par": name,
                "r_cop": rc,
                "r_usd": ru,
                "nota": note,
                "dev": (1 + rc) / (1 + ru) - 1,
                "forward_13oct": f_ref,
                "forward_val": fw.cip_forward(s0, rc, ru, 252),
                "dif_cop": spot_ref + mk["puntos"]["1Y"] - f_ref,
                "dif_pb": (dev_1y - ((1 + rc) / (1 + ru) - 1)) * 1e4,
            }
        )
    cip = pd.DataFrame(cip)
    rc_grid = np.round(np.arange(0.10, 0.1301, 0.005), 4)
    ru_grid = np.round(np.arange(0.035, 0.0501, 0.0025), 4)
    heat = np.array([[fw.cip_forward(s0, rc, ru, 252) for rc in rc_grid] for ru in ru_grid])

    theo_curve = []
    for tenor, days in mk["dias_calendario"].items():
        nb = fw.calendar_to_business(days)
        theo_curve.append(
            {
                "plazo": tenor,
                "banrep_sofr": fw.cip_forward(spot_ref, cip.loc[0, "r_cop"], cip.loc[0, "r_usd"], nb) - spot_ref,
                "ibr_swap": fw.cip_forward(spot_ref, cip.loc[1, "r_cop"], cip.loc[1, "r_usd"], nb) - spot_ref,
            }
        )
    return {
        "curve": curve,
        "theo_curve": pd.DataFrame(theo_curve),
        "dev_1y": dev_1y,
        "forward_1y_mkt": spot_ref + mk["puntos"]["1Y"],
        "forward_1y_val": s0 * (1 + dev_1y),
        "cip": cip,
        "heat": {"rc": rc_grid, "ru": ru_grid, "z": heat},
        "d_lr": d_lr,
    }


def _hedge_metrics(h: fw.HedgeResult) -> dict:
    ratio = h.spot_t / h.forward - 1
    gain, above = h.payoff > 0, h.avg_spot > h.forward
    per = pd.DataFrame(
        {
            "anio": h.years,
            "proteccion": (h.payoff > 0).mean(axis=0),
            "costo_oportunidad": (h.payoff < 0).mean(axis=0),
            "extrema_exposicion": (ratio > EXTREME).mean(axis=0),
            "extrema_derivado": (ratio < -EXTREME).mean(axis=0),
            "fracaso": (~gain & above).mean(axis=0),
            "sobrecompensacion": (gain & ~above).mean(axis=0),
            "proteccion_efectiva": (gain & above).mean(axis=0),
            "costo_op_puro": (~gain & ~above).mean(axis=0),
            "payoff_media": h.payoff.mean(axis=0),
            "payoff_p5": _q(h.payoff, 5),
            "payoff_p95": _q(h.payoff, 95),
            "forward_media": h.forward.mean(axis=0),
            "forward_p5": _q(h.forward, 5),
            "forward_p95": _q(h.forward, 95),
            "spot_t_media": h.spot_t.mean(axis=0),
            "spot_t_p5": _q(h.spot_t, 5),
            "spot_t_p95": _q(h.spot_t, 95),
            "tasa_u_media": (h.cost_unhedged / h.obligation_usd).mean(axis=0),
            "tasa_h_media": (h.cost_hedged / h.obligation_usd).mean(axis=0),
            "tasa_u_p95": _q(h.cost_unhedged / h.obligation_usd, 95),
            "tasa_h_p95": _q(h.cost_hedged / h.obligation_usd, 95),
            "dev_u_sd": h.budget_dev_unhedged.std(axis=0),
            "dev_h_sd": h.budget_dev_hedged.std(axis=0),
            "dev_u_10": (h.budget_dev_unhedged > BUDGET_TOL).mean(axis=0),
            "dev_h_10": (h.budget_dev_hedged > BUDGET_TOL).mean(axis=0),
        }
    )
    pooled = {
        c: float(per[c].mean())
        for c in per.columns
        if c not in ("anio",) and not c.startswith(("forward_", "spot_", "tasa_", "payoff_p"))
    }
    pooled["payoff_cvar"] = float(-_cvar(-h.payoff.ravel(), 0.95))
    pooled["payoff_total_media"] = float(h.payoff.sum(axis=1).mean())
    pooled["prob_total_negativo"] = float((h.payoff.sum(axis=1) < 0).mean())
    return {"per": per, "pooled": pooled}


def _conditional_sd(y: np.ndarray, x: np.ndarray) -> float:
    b = np.polyfit(x, y, 1)
    return float((y - np.polyval(b, x)).std())


def part_b2_b3(a2: dict, sims: dict, scen_keys: list, d_lr: float, disc_rate: float) -> dict:
    loan = a2["loan"]
    a = loan.installment
    b2, b3, flows = {}, {}, {}
    for key in scen_keys:
        for dist in DISTS:
            p = sims[(key, dist)]
            h = fw.hedge(p, a, d_lr)
            b2[(key, dist)] = _hedge_metrics(h)
            qs = cf.quarterly_spots(p)
            ds = {"sin": cf.debt_service(a, qs), "con": cf.debt_service(a, qs, h.payoff)}
            for strat, pay in ds.items():
                irr = cf.irr_ea(a2["financed_cop"], pay)
                total = pay.sum(axis=1)
                annual = pay.reshape(len(pay), 10, 4).sum(axis=2)
                y710 = annual[:, 6:].sum(axis=1)
                dev = h.budget_dev_unhedged if strat == "sin" else h.budget_dev_hedged
                b3[(key, dist, strat)] = {
                    "total_media": float(total.mean()),
                    "total_sd": float(total.std()),
                    "total_p5": float(_q(total, 5)),
                    "total_p95": float(_q(total, 95)),
                    "total_cvar95": _cvar(total),
                    "tir_media": float(irr.mean()),
                    "tir_p5": float(_q(irr, 5)),
                    "tir_p50": float(_q(irr, 50)),
                    "tir_p95": float(_q(irr, 95)),
                    "vp_media": float(cf.present_value(pay, disc_rate).mean()),
                    "y710_media": float(y710.mean()),
                    "y710_sd": float(y710.std()),
                    "y710_p95": float(_q(y710, 95)),
                    "y710_cvar95": _cvar(y710),
                    "y710_sd_cond": _conditional_sd(y710, p[:, 72]),
                    "dev_sd": float(dev.std()),
                    "dev_10": float((dev > BUDGET_TOL).mean()),
                    "forward_neto": float(h.payoff.sum(axis=1).mean()) if strat == "con" else 0.0,
                    "y16_sd": float(annual[:, :6].sum(axis=1).std()),
                }
                flows[(key, dist, strat)] = {
                    "tir": irr,
                    "trm_media": qs[:, 1:].mean(axis=0),
                    "cuota_media": (a * qs[:, 1:]).mean(axis=0),
                    "forward_media": (pay - a * qs[:, 1:]).mean(axis=0) * -1,
                    "neto_media": pay.mean(axis=0),
                    "anual_media": annual.mean(axis=0),
                    "anual_p5": _q(annual, 5),
                    "anual_p95": _q(annual, 95),
                }
    return {"b2": b2, "b3": b3, "flows": flows}


def sensitivities(a2: dict, paths: np.ndarray, d_lr: float, dev_1y: float, dev_lt: float) -> dict:
    loan = a2["loan"]
    a = loan.installment
    qs = cf.quarterly_spots(paths)
    d_grid = sorted({0.02, 0.03, d_lr, 0.05, 0.06, dev_lt, dev_1y})
    sens_d = []
    for d in d_grid:
        h = fw.hedge(paths, a, d)
        pay = cf.debt_service(a, qs, h.payoff)
        sens_d.append(
            {
                "d": d,
                "forward_neto": float(h.payoff.sum(axis=1).mean()),
                "proteccion": float((h.payoff > 0).mean()),
                "y710_media": float(h.cost_hedged.sum(axis=1).mean()),
                "tir_media": float(cf.irr_ea(a2["financed_cop"], pay).mean()),
            }
        )
    sens_rate = []
    for r in (0.085, 0.095, 0.105, 0.115, 0.13):
        ln = Loan(loan.principal_usd, r, loan.years, loan.periods_per_year)
        h = fw.hedge(paths, ln.installment, d_lr)
        pay_u = cf.debt_service(ln.installment, qs)
        pay_h = cf.debt_service(ln.installment, qs, h.payoff)
        sens_rate.append(
            {
                "tasa": r,
                "ea": ln.effective_annual_rate,
                "cuota_usd": ln.installment,
                "total_usd": ln.installment * ln.n_periods,
                "total_cop_sin": float(pay_u.sum(axis=1).mean()),
                "total_cop_con": float(pay_h.sum(axis=1).mean()),
                "tir_sin": float(cf.irr_ea(a2["financed_cop"], pay_u).mean()),
                "tir_con": float(cf.irr_ea(a2["financed_cop"], pay_h).mean()),
            }
        )
    sens_hr = []
    for hr in (0.0, 0.25, 0.5, 0.625, 0.75, 1.0):
        h = fw.hedge(paths, a, d_lr, hedge_ratio=hr)
        y = h.cost_hedged.sum(axis=1)
        sens_hr.append(
            {
                "ratio": hr,
                "media": float(y.mean()),
                "sd": float(y.std()),
                "sd_cond": _conditional_sd(y, paths[:, 72]),
                "cvar95": _cvar(y),
                "dev_sd": float(h.budget_dev_hedged.std()),
            }
        )
    strategies = []
    h_roll = fw.hedge(paths, a, d_lr)
    h_strip = fw.hedge(paths, a, d_lr, style="strip")
    qm = fw.hedge_quarterly_matched(paths, a, d_lr)
    for name, cost, budget_dev in [
        ("Sin cobertura", h_roll.cost_unhedged, h_roll.budget_dev_unhedged),
        ("Rolling anual (diseño exigido)", h_roll.cost_hedged, h_roll.budget_dev_hedged),
        ("Rolling con 4 vencimientos trimestrales", qm, qm / h_roll.budget - 1),
        ("Strip pactado al cierre del año 6", h_strip.cost_hedged, h_strip.budget_dev_hedged),
    ]:
        y = cost.sum(axis=1)
        strategies.append(
            {
                "estrategia": name,
                "media": float(y.mean()),
                "sd": float(y.std()),
                "sd_cond": _conditional_sd(y, paths[:, 72]),
                "cvar95": _cvar(y),
                "dev_sd": float(budget_dev.std()),
                "costo_esperado": float(y.mean() - h_roll.cost_unhedged.sum(axis=1).mean()),
            }
        )
    beta = (3 + 6 + 9 + 12) / 12 / 4
    return {
        "d": pd.DataFrame(sens_d),
        "rate": pd.DataFrame(sens_rate),
        "hedge_ratio": pd.DataFrame(sens_hr),
        "strategies": pd.DataFrame(strategies),
        "beta_minvar": beta,
        "strip_prot": (h_strip.payoff > 0).mean(axis=0),
    }


def tails_by_horizon(eps: dict) -> pd.DataFrame:
    rows = []
    for dist, e in eps.items():
        for h in (1, 3, 12):
            x = e[:, :h].sum(axis=1) / np.sqrt(h)
            rows.append(
                {
                    "dist": DISTS[dist],
                    "horizonte": h,
                    "curtosis": float(stats.kurtosis(x)),
                    "p_2sd": float((x > 2).mean()),
                    "p_3sd": float((x > 3).mean()),
                    "q999": float(np.quantile(x, 0.999)),
                }
            )
    return pd.DataFrame(rows)


def build(n_paths: int = N_PATHS) -> dict:
    inp = manual_inputs()
    s0 = float(inp["spot"]["trm"])
    val_date = pd.Timestamp(inp["meta"]["fecha_valoracion"])
    lr = inp["tasas"]["largo_plazo"]
    d_lr = (1 + lr["r_cop"]) / (1 + lr["r_usd"]) - 1
    disc_rate = inp["tasas"]["tes_jun2032"]["valor"]

    a1 = part_a1(inp, s0, val_date)
    a2 = part_a2(inp, s0, val_date)
    b1 = part_b1(inp, s0, d_lr)
    cal = fx.calibrate()

    scenarios = [
        fx.Scenario(s["key"], s["nombre"], s["trm_12m"], s["deriva_lp"], s["probabilidad"], s["narrativa"])
        for s in inp["escenarios"]["lista"]
    ]
    neutral = fx.Scenario(
        "neutral",
        "Neutral al riesgo (referencia)",
        s0 * (1 + b1["dev_1y"]),
        d_lr,
        0.0,
        "La TRM crece en promedio al ritmo de los puntos forward: año 1 con la devaluación implícita de mercado y luego con el diferencial de largo plazo.",
    )
    all_scen = scenarios + [neutral]
    eps = {dist: fx.innovations(n_paths, 120, dist, cal.nu, SEED + i) for i, dist in enumerate(DISTS)}
    mus = {s.key: fx.drift_schedule(s0, s.trm_12m, s.deriva_lp) for s in all_scen}
    exp_paths = {k: fx.expected_path(s0, mu) for k, mu in mus.items()}
    sims = {(s.key, dist): fx.simulate(s0, cal.sigma, mus[s.key], eps[dist]) for s in all_scen for dist in DISTS}
    sim_pct = {
        key: {p: _q(sims[key], p) for p in (5, 25, 50, 75, 95)} | {"mean": sims[key].mean(axis=0)}
        for key in sims
    }

    a3 = part_a3(a2, s0, exp_paths, sims, scenarios)
    res = part_b2_b3(a2, sims, [s.key for s in all_scen], d_lr, disc_rate)
    t = inp["tasas"]
    dev_lt = (1 + t["tes_jun2032"]["valor"]) / (1 + fw.ea_from_bond_equivalent(t["ust_10y"]["valor"])) - 1
    sens = sensitivities(a2, sims[("central", "normal")], d_lr, b1["dev_1y"], dev_lt)

    loan = a2["loan"]
    sched = a2["schedule"]
    coherence = pd.DataFrame(
        {
            "anio": list(HEDGE_YEARS),
            "obligacion_usd": [sched.loc[sched["anio"] == y, "cuota"].sum() for y in HEDGE_YEARS],
            "capital_usd": [sched.loc[sched["anio"] == y, "abono_capital"].sum() for y in HEDGE_YEARS],
            "interes_usd": [sched.loc[sched["anio"] == y, "interes"].sum() for y in HEDGE_YEARS],
            "saldo_inicio_usd": [sched.loc[sched["anio"] == y, "saldo_inicial"].iloc[0] for y in HEDGE_YEARS],
        }
    )
    hr = inp["proyecto"]["cobertura"]
    coherence["cubierto_usd"] = hr * coherence["obligacion_usd"]
    coherence["abierto_usd"] = coherence["obligacion_usd"] - coherence["cubierto_usd"]
    synthetic = {
        name: (1 + loan.effective_annual_rate) * (1 + dev) - 1
        for name, dev in [("1Y", b1["dev_1y"]), ("3Y", float(b1["curve"].loc[4, "dev"])), ("LT", dev_lt)]
    }

    def box_stats(x: np.ndarray) -> dict:
        return {p: _q(x, p) for p in (5, 25, 50, 75, 95)} | {"mean": x.mean(axis=0)}

    central = sims[("central", "normal")]
    h_c = fw.hedge(central, a2["loan"].installment, d_lr)
    h_ct = fw.hedge(sims[("central", "t")], a2["loan"].installment, d_lr)
    budget_box = {
        dist: {"u": box_stats(h.budget_dev_unhedged), "h": box_stats(h.budget_dev_hedged)}
        for dist, h in (("normal", h_c), ("t", h_ct))
    }
    irr_box = {
        dist: {
            strat: {key: box_stats(res["flows"][(key, dist, strat)]["tir"]) for key in [s.key for s in all_scen]}
            for strat in STRATS
        }
        for dist in DISTS
    }
    rng = np.random.default_rng(7)
    sample = rng.choice(n_paths, 2500, replace=False)

    return {
        "inp": inp,
        "s0": s0,
        "val_date": val_date,
        "d_lr": d_lr,
        "disc_rate": disc_rate,
        "cal": cal,
        "scenarios": scenarios,
        "neutral": neutral,
        "exp_paths": exp_paths,
        "sim_pct": sim_pct,
        "a1": a1,
        "a2": a2,
        "a3": a3,
        "b1": b1,
        **res,
        "sens": sens,
        "dev_lt": dev_lt,
        "coherence": coherence,
        "synthetic": synthetic,
        "tails": tails_by_horizon(eps),
        "ratio_hist": {
            "normal": (h_c.spot_t / h_c.forward - 1).ravel(),
            "t": (h_ct.spot_t / h_ct.forward - 1).ravel(),
        },
        "scatter": {
            "u": h_c.budget_dev_unhedged[sample, 0],
            "h": h_c.budget_dev_hedged[sample, 0],
            "payoff": h_c.payoff[sample, 0],
            "above": (h_c.avg_spot > h_c.forward)[sample, 0],
        },
        "budget_box": budget_box,
        "irr_box": irr_box,
        "n_paths": n_paths,
    }
