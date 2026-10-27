"""Cálculos de la Parte 2.

Puntos 2–4: retornos, optimización media-varianza (máximo Sharpe) y VaR mensual (convención de 252 días).
Puntos 5–12: beta CAPM, número óptimo de contratos E-mini S&P 500, cuenta de margen con liquidaciones
mensuales, roll-over trimestral, valor esperado de la cobertura, rendimiento esperado y sensibilidad a la beta.

El horizonte (30-jul-2026 a 30-jul-2030) se evalúa con precios reales hasta el último cierre de mes disponible
(30-sep-2026) y con simulación Monte Carlo desde ahí. El futuro se valora por costo de acarreo,
F = S·exp((r − q)·τ), más un error de base calibrado con los contratos ESZ26 y ESH27.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm

from .data import dividends, inputs, treasury, yahoo

MONTH_CODES = {3: "H", 6: "M", 9: "U", 12: "Z"}
MONTH_NAMES = {3: "mar", 6: "jun", 9: "sep", 12: "dic"}


# ----------------------------------------------------------------------------- calendario de futuros
def third_friday(year: int, month: int) -> pd.Timestamp:
    first = pd.Timestamp(year, month, 1)
    offset = (4 - first.weekday()) % 7
    return first + pd.Timedelta(days=offset + 14)


def contract_after_roll(date: pd.Timestamp) -> tuple[int, int]:
    """Contrato trimestral que se mantiene después de `date` con roll al cierre de feb, may, ago y nov."""
    y, m = date.year, date.month
    # El contrato vigente es el del siguiente mes trimestral; en el mes del roll se pasa al siguiente.
    q = (m // 3 + 1) * 3  # ene–feb: mar; mar–may: jun; jun–ago: sep; sep–nov: dic; dic: mar siguiente
    if m in (2, 5, 8, 11) and date >= pd.Timestamp(y, m, 1) + pd.offsets.BMonthEnd(0):
        q += 3
    if q > 12:
        q -= 12
        y += 1
    return y, q


def code(y: int, m: int) -> str:
    return f"ES{MONTH_CODES[m]}{str(y)[-2:]}"


def label(y: int, m: int) -> str:
    return f"{code(y, m)} ({MONTH_NAMES[m]}-{y})"


def liquidation_dates(start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    """Entrada, último día hábil de cada mes y cierre en la fecha final del horizonte."""
    months = pd.date_range(start + pd.offsets.BMonthEnd(0), end, freq="BME")
    out = [start] + [d for d in months if start < d < end - pd.Timedelta(days=3)
                     and (d.year, d.month) != (start.year, start.month)]
    return out + [end]


# ----------------------------------------------------------------------------- utilidades
def ea_from_bey(y: float) -> float:
    return (1 + y / 2) ** 2 - 1


def per_period(rate_ea: float, dt: float) -> float:
    return (1 + rate_ea) ** dt - 1


def _ols(y: np.ndarray, x: np.ndarray) -> dict:
    X = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    n = len(y)
    s2 = resid @ resid / (n - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - resid.var() / y.var()
    return {"alpha": coef[0], "beta": coef[1], "se_beta": se[1], "t_beta": coef[1] / se[1], "se_alpha": se[0],
            "r2": r2, "resid_sd": float(resid.std(ddof=2)), "n": n}


# ----------------------------------------------------------------------------- puntos 2–4
def returns_block(cfg: dict) -> dict:
    p = cfg["portafolio"]
    tk = p["tickers"]
    prices = pd.concat({t: yahoo(t)["adjclose"] for t in tk}, axis=1).loc[p["inicio_muestra"]:p["fin_muestra"]].dropna()
    rets = prices.pct_change(fill_method=None).dropna()
    n = len(rets)
    D = p["dias_anio"]
    st = pd.DataFrame({
        "media_d": rets.mean(),
        "ret_arit": rets.mean() * D,
        "ret_geo": (1 + rets).prod() ** (D / n) - 1,
        "acum": (1 + rets).prod() - 1,
        "sd_d": rets.std(ddof=1),
        "vol": rets.std(ddof=1) * np.sqrt(D),
        "var_a": rets.var(ddof=1) * D,
        "asim": rets.skew(),
        "curt": rets.kurt(),
        "min": rets.min(),
        "max": rets.max(),
    })
    by_year = (1 + rets).groupby(rets.index.year).prod() - 1
    return {"prices": prices, "rets": rets, "stats": st, "cov": rets.cov() * D, "corr": rets.corr(),
            "by_year": by_year, "n": n}


def optimize(mu: np.ndarray, cov: np.ndarray, rf: float) -> dict:
    k = len(mu)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    bnds = [(0.0, 1.0)] * k
    x0 = np.full(k, 1 / k)
    opts = {"ftol": 1e-14, "maxiter": 10_000}

    def vol(w):
        return float(np.sqrt(w @ cov @ w))

    s = minimize(lambda w: -(w @ mu - rf) / vol(w), x0, method="SLSQP", bounds=bnds, constraints=cons, options=opts)
    m = minimize(lambda w: w @ cov @ w, x0, method="SLSQP", bounds=bnds, constraints=cons, options=opts)
    w_s, w_m = s.x / s.x.sum(), m.x / m.x.sum()
    frontier = []
    for target in np.linspace(float(w_m @ mu), float(mu.max()), 40):
        c = cons + [{"type": "eq", "fun": lambda w, t=target: w @ mu - t}]
        f = minimize(lambda w: w @ cov @ w, w_m, method="SLSQP", bounds=bnds, constraints=c, options=opts)
        if f.success:
            frontier.append((vol(f.x), target))
    rng = np.random.default_rng(42)
    W = rng.dirichlet(np.ones(k), 20_000)
    sim_ret = W @ mu
    sim_vol = np.sqrt(np.einsum("ij,jk,ik->i", W, cov, W))
    return {
        "w": w_s, "ret": float(w_s @ mu), "vol": vol(w_s), "sharpe": float((w_s @ mu - rf) / vol(w_s)),
        "w_mv": w_m, "ret_mv": float(w_m @ mu), "vol_mv": vol(w_m), "sharpe_mv": float((w_m @ mu - rf) / vol(w_m)),
        "frontier": np.array(frontier), "cloud": {"w": W, "ret": sim_ret, "vol": sim_vol, "sharpe": (sim_ret - rf) / sim_vol},
    }


def var_block(rets: pd.DataFrame, w: np.ndarray, capital: float, days: int = 21) -> dict:
    port = rets @ w
    mu_d, sd_d = float(port.mean()), float(port.std(ddof=1))
    mu_h, sd_h = mu_d * days, sd_d * np.sqrt(days)
    roll = (1 + port).rolling(days).apply(np.prod, raw=True).dropna() - 1
    rows = []
    for c in (0.95, 0.99):
        z = norm.ppf(c)
        v = max(z * sd_h - mu_h, 0.0)
        h = max(-float(roll.quantile(1 - c)), 0.0)
        rows.append({"conf": c, "z": z, "var_pct": v, "var_usd": v * capital, "var0_pct": z * sd_h,
                     "var0_usd": z * sd_h * capital, "hist_pct": h, "hist_usd": h * capital})
    return {"port": port, "mu_h": mu_h, "sd_h": sd_h, "table": pd.DataFrame(rows), "roll21": roll}


# ----------------------------------------------------------------------------- punto 5
def betas(cfg: dict, rets: pd.DataFrame, w: np.ndarray) -> dict:
    p = cfg["portafolio"]
    mkt = yahoo(p["mercado"])["close"].loc[p["inicio_muestra"]:p["fin_muestra"]].pct_change(fill_method=None)
    irx = yahoo("^IRX")["close"].reindex(rets.index).ffill() / 100
    rf_d = irx.shift(1).bfill() / p["dias_anio"]
    m = mkt.reindex(rets.index)
    df = rets.join(m.rename("mkt")).join(rf_d.rename("rf")).dropna()
    port = df[p["tickers"]] @ w
    out, rolling = {}, {}
    for name, series in [*[(t, df[t]) for t in p["tickers"]], ("Portafolio", port)]:
        ex = _ols((series - df["rf"]).to_numpy(), (df["mkt"] - df["rf"]).to_numpy())
        raw = _ols(series.to_numpy(), df["mkt"].to_numpy())
        ex["beta_raw"] = raw["beta"]
        ex["alpha_a"] = ex["alpha"] * p["dias_anio"]
        ex["resid_vol"] = ex["resid_sd"] * np.sqrt(p["dias_anio"])
        ex["corr"] = float(np.corrcoef(series, df["mkt"])[0, 1])
        out[name] = ex
        win = 504
        cov = series.rolling(win).cov(df["mkt"])
        rolling[name] = (cov / df["mkt"].rolling(win).var()).dropna()
    bw = float(np.dot(w, [out[t]["beta"] for t in p["tickers"]]))
    mk = df["mkt"]
    return {"table": out, "beta_p": bw, "beta_p_reg": out["Portafolio"]["beta"], "rolling": rolling,
            "mkt_vol": float(mk.std(ddof=1) * np.sqrt(p["dias_anio"])), "mkt_ret": float(mk.mean() * p["dias_anio"]),
            "sample": df}


# ----------------------------------------------------------------------------- punto 1: precios
def price_block(cfg: dict) -> dict:
    p = cfg["portafolio"]
    cut = pd.Timestamp(p["fin_muestra"])
    rows = {}
    for t in p["tickers"]:
        px = yahoo(t)
        c, adj = px["close"].loc[:cut], px["adjclose"].loc[:cut]
        last = float(c.iloc[-1])
        y12 = c.loc[cut - pd.DateOffset(years=1):]
        dv = dividends(t)
        ttm = float(dv.loc[cut - pd.DateOffset(years=1) + pd.Timedelta(days=1):cut].sum())

        def tr(start, adj=adj):
            return float(adj.iloc[-1] / adj.loc[:start].iloc[-1] - 1)

        rows[t] = {
            "close": last, "ytd": tr(pd.Timestamp("2025-12-31")), "r12": tr(cut - pd.DateOffset(years=1)),
            "r3": tr(cut - pd.DateOffset(months=3)), "hi52": float(y12.max()), "lo52": float(y12.min()),
            "dist_hi": last / float(y12.max()) - 1, "dd12": float((adj.loc[y12.index[0]:] / adj.loc[y12.index[0]:].cummax() - 1).min()),
            "div_ttm": ttm, "dy": ttm / last, "last_div": float(dv.loc[:cut].iloc[-1]), "last_div_date": dv.loc[:cut].index[-1],
        }
    spx = yahoo(p["mercado"])["close"].loc[:cut]
    rows["S&P 500"] = {"close": float(spx.iloc[-1]),
                       "ytd": float(spx.iloc[-1] / spx.loc[:"2025-12-31"].iloc[-1] - 1),
                       "r12": float(spx.iloc[-1] / spx.loc[:cut - pd.DateOffset(years=1)].iloc[-1] - 1),
                       "r3": float(spx.iloc[-1] / spx.loc[:cut - pd.DateOffset(months=3)].iloc[-1] - 1),
                       "hi52": float(spx.loc[cut - pd.DateOffset(years=1):].max()),
                       "lo52": float(spx.loc[cut - pd.DateOffset(years=1):].min())}
    rows["S&P 500"]["dist_hi"] = rows["S&P 500"]["close"] / rows["S&P 500"]["hi52"] - 1
    return pd.DataFrame(rows).T


def index_dividend_yield(cut: pd.Timestamp) -> float:
    pr, tr = yahoo("^GSPC")["close"], yahoo("^SP500TR")["close"]
    a = cut - pd.DateOffset(years=1)
    return float(np.expm1(np.log(tr.loc[:cut].iloc[-1] / tr.loc[:a].iloc[-1]) - np.log(pr.loc[:cut].iloc[-1] / pr.loc[:a].iloc[-1])))


# ----------------------------------------------------------------------------- simulación y cobertura
@dataclass
class Market:
    rf: float           # tasa libre de riesgo E.A. del horizonte (^FVX convertido)
    erp: float          # prima de riesgo de mercado
    q: float            # rendimiento por dividendo del índice
    sigma: float        # volatilidad anual del índice
    beta: float         # beta del portafolio
    resid_vol: float    # volatilidad idiosincrática anual del portafolio
    basis_sd: float     # error de base

    @property
    def mu(self) -> float:
        return self.rf + self.erp


def fut_price(S, tau, rf: float, q: float, noise=0.0):
    return S * np.exp((np.log1p(rf) - np.log1p(q)) * tau) * (1 + noise)


def build_timeline(cfg: dict) -> pd.DataFrame:
    p = cfg["portafolio"]
    start, end = pd.Timestamp(p["fecha_inversion"]), pd.Timestamp(p["fin_horizonte"])
    dates = liquidation_dates(start, end)
    rows = []
    held = contract_after_roll(start - pd.Timedelta(days=1))
    for i, d in enumerate(dates):
        new = contract_after_roll(d) if i < len(dates) - 1 else held
        roll = i > 0 and new != held
        rows.append({"i": i, "fecha": d, "old": held, "new": new, "roll": roll,
                     "tau_old": (third_friday(*held) - d).days / 365, "tau_new": (third_friday(*new) - d).days / 365})
        held = new
    tl = pd.DataFrame(rows)
    tl.loc[0, "roll"] = False
    return tl


def observed_futures(tl: pd.DataFrame, last_obs: pd.Timestamp) -> dict:
    """Precios reales del contrato mantenido (old) y del siguiente (new) en las fechas observadas."""
    get = {(2026, 9): yahoo("ES=F")["close"], (2026, 12): yahoo("ESZ26.CME")["close"], (2027, 3): yahoo("ESH27.CME")["close"]}
    out = {}
    for _, r in tl.iterrows():
        if r["fecha"] > last_obs:
            break
        out[r["i"]] = (float(get[r["old"]].loc[r["fecha"]]), float(get[r["new"]].loc[r["fecha"]]))
    return out


def simulate(cfg: dict, tl: pd.DataFrame, mk: Market, n: int, seed: int, s_obs: dict, last_i: int):
    """Trayectorias del índice, del portafolio (retorno total) y de los futuros en las fechas de liquidación."""
    rng = np.random.default_rng(seed)
    T = len(tl)
    dt = 21 / 252
    S = np.empty((n, T))
    V = np.empty((n, T))
    Fo = np.empty((n, T))
    Fn = np.empty((n, T))
    for i in range(last_i + 1):
        S[:, i], V[:, i] = s_obs["S"][i], s_obs["V"][i]
        Fo[:, i], Fn[:, i] = s_obs["F"][i]
    m = np.log1p(mk.mu)
    rf_dt = per_period(mk.rf, dt)
    for i in range(last_i + 1, T):
        eps_m = rng.standard_normal(n)
        eps_e = rng.standard_normal(n)
        x = (m - 0.5 * mk.sigma**2) * dt + mk.sigma * np.sqrt(dt) * eps_m       # log-retorno total del mercado
        S[:, i] = S[:, i - 1] * np.exp(x - np.log1p(mk.q) * dt)
        Rm = np.expm1(x)
        Rp = rf_dt + mk.beta * (Rm - rf_dt) + mk.resid_vol * np.sqrt(dt) * eps_e
        V[:, i] = V[:, i - 1] * (1 + Rp)
        r = tl.iloc[i]
        Fo[:, i] = fut_price(S[:, i], r["tau_old"], mk.rf, mk.q, mk.basis_sd * rng.standard_normal(n))
        Fn[:, i] = (fut_price(S[:, i], r["tau_new"], mk.rf, mk.q, mk.basis_sd * rng.standard_normal(n))
                    if r["roll"] else Fo[:, i])
    return {"S": S, "V": V, "Fo": Fo, "Fn": Fn}


def run_hedge(tl: pd.DataFrame, sim: dict, beta: float, n0: int, side: int, mult: float, mm: float, im_factor: float,
              rebalance: bool = True) -> dict:
    """Cuenta de margen con liquidación mensual. side = -1 corto, +1 largo, 0 sin cobertura."""
    V, Fo, Fn = sim["V"], sim["Fo"], sim["Fn"]
    npaths, T = V.shape
    im = mm * im_factor
    N = np.full(npaths, n0, dtype=float)
    Ns = np.zeros((npaths, T))
    Ns[:, 0] = N
    bal = np.zeros((npaths, T))
    pre = np.zeros((npaths, T))
    dep = np.zeros((npaths, T))
    pnl = np.zeros((npaths, T))
    call = np.zeros((npaths, T), dtype=bool)
    rdep = np.zeros((npaths, T), dtype=bool)
    if side == 0:
        return {"pnl": pnl, "bal": bal, "dep": dep, "call": call, "rdep": rdep, "N": Ns, "pre": pre}
    bal[:, 0] = im * N
    dep[:, 0] = im * N
    for i in range(1, T):
        pnl[:, i] = side * N * mult * (Fo[:, i] - Fn[:, i - 1])
        b = bal[:, i - 1] + pnl[:, i]
        pre[:, i] = b
        if tl.iloc[i]["roll"] and rebalance:
            N = np.round(beta * V[:, i] / (Fn[:, i] * mult))
        need = im * N
        c = b < mm * N                                   # llamado al margen
        r_dep = (~c) & (b < need) & bool(tl.iloc[i]["roll"])  # depósito para abrir el nuevo contrato
        d = np.where(c | r_dep, need - b, 0.0)
        call[:, i] = c
        rdep[:, i] = r_dep
        dep[:, i] = d
        bal[:, i] = b + d
        Ns[:, i] = N
    return {"pnl": pnl, "bal": bal, "dep": dep, "call": call, "rdep": rdep, "N": Ns, "pre": pre}


def wealth(sim: dict, h: dict, rf_dt: float = 0.0) -> np.ndarray:
    """Riqueza: acciones (retorno total) + cuenta de efectivo con el resultado acumulado de los futuros.

    Las pérdidas de los futuros se financian (y las ganancias se invierten) a la tasa libre de riesgo.
    """
    pnl = h["pnl"]
    cash = np.zeros_like(pnl)
    for i in range(1, pnl.shape[1]):
        cash[:, i] = cash[:, i - 1] * (1 + rf_dt) + pnl[:, i]
    return sim["V"] + cash


def summarize(x: np.ndarray, v0: float) -> dict:
    r = x / v0 - 1
    return {"media": float(x.mean()), "sd": float(x.std()), "p5": float(np.percentile(x, 5)),
            "p50": float(np.percentile(x, 50)), "p95": float(np.percentile(x, 95)),
            "r_media": float(r.mean()), "r_sd": float(r.std()), "p_loss": float((r < 0).mean()),
            "cvar5": float(x[x <= np.percentile(x, 5)].mean())}


# ----------------------------------------------------------------------------- orquestación
def build(n_paths: int | None = None) -> dict:
    cfg = inputs()
    p, fu, sup = cfg["portafolio"], cfg["futuro"], cfg["supuestos"]
    n_paths = n_paths or sup["n_trayectorias"]
    tk, cap = p["tickers"], p["capital_usd"]
    cut, t0 = pd.Timestamp(p["fin_muestra"]), pd.Timestamp(p["fecha_inversion"])
    # --- 2–4
    rb = returns_block(cfg)
    rf_s = cfg["tasas"]["rf_sharpe"]["valor"]
    mu, cov = rb["stats"]["ret_arit"].to_numpy(), rb["cov"].to_numpy()
    opt = optimize(mu, cov, rf_s)
    w = opt["w"]
    vb = var_block(rb["rets"], w, cap, p["dias_mes"])

    # --- tasas observadas
    fvx = float(yahoo("^FVX")["close"].loc[:cut].iloc[-1]) / 100
    tnx = float(yahoo("^TNX")["close"].loc[:cut].iloc[-1]) / 100
    irx = float(yahoo("^IRX")["close"].loc[:cut].iloc[-1]) / 100
    tsy = treasury().loc[cut]
    rf_h = ea_from_bey(fvx)

    # --- 5
    bt = betas(cfg, rb["rets"], w)
    beta_p = bt["beta_p"]
    q_idx = index_dividend_yield(cut)
    erp = sup["prima_riesgo_mercado"]
    capm = {t: rf_h + bt["table"][t]["beta"] * erp for t in tk}
    capm["Portafolio"] = rf_h + beta_p * erp

    # --- 1: precios, dividendos y precio esperado
    pb = price_block(cfg)
    px0 = {t: float(yahoo(t)["close"].loc[t0]) for t in tk}
    div_fwd = {t: 4 * float(pb.loc[t, "last_div"]) for t in tk}   # último dividendo trimestral anualizado
    exp_price = {}
    for t in tk:
        p0 = px0[t]
        dv = div_fwd[t]
        exp_price[t] = {"capm": p0 * (1 + capm[t]) - dv, "hist": p0 * (1 + rb["stats"].loc[t, "ret_arit"]) - dv,
                        "lo": p0 * (1 + capm[t] - rb["stats"].loc[t, "vol"]) - dv,
                        "hi": p0 * (1 + capm[t] + rb["stats"].loc[t, "vol"]) - dv}
    q_p = float(np.dot(w, [div_fwd[t] / px0[t] for t in tk]))

    # --- ejecución al cierre del 30-jul-2026
    shares = {t: int(np.floor(w[j] * cap / px0[t])) for j, t in enumerate(tk)}
    invested = sum(shares[t] * px0[t] for t in tk)
    cash = cap - invested
    s0 = float(yahoo("^GSPC")["close"].loc[t0])
    f0 = float(yahoo("ES=F")["close"].loc[t0])
    tl = build_timeline(cfg)
    tau0 = tl.loc[0, "tau_old"]
    f0_theo = fut_price(s0, tau0, rf_h, q_idx)
    f0_theo_3m = fut_price(s0, tau0, ea_from_bey(irx), q_idx)
    mult = fu["multiplicador"]

    # --- 6: número de contratos
    v0 = cap
    n_star = beta_p * v0 / (f0 * mult)
    opts_n = []
    for nn in (int(np.floor(n_star)), int(np.ceil(n_star))):
        resid = beta_p - nn * f0 * mult / v0
        opts_n.append({"n": nn, "cubierto": nn * f0 * mult, "beta_res": resid, "exp_res": resid * v0,
                       "h": nn * f0 * mult / (beta_p * v0)})
    n_cont = min(opts_n, key=lambda r: abs(r["beta_res"]))["n"]
    mm_s, mm_l, imf = fu["margen_mant_corto"], fu["margen_mant_largo"], fu["factor_margen_inicial"]

    # --- observados y simulación
    last_obs = yahoo("ESZ26.CME")["close"].index.max()
    tl_obs = tl[tl["fecha"] <= last_obs - pd.Timedelta(days=0)]
    last_i = int(tl_obs["i"].max())
    fobs = observed_futures(tl, last_obs)
    adj0 = {t: float(yahoo(t)["adjclose"].loc[t0]) for t in tk}

    def v_obs(d):
        return sum(shares[t] * px0[t] * float(yahoo(t)["adjclose"].loc[d]) / adj0[t] for t in tk)

    s_obs = {"S": {i: float(yahoo("^GSPC")["close"].loc[tl.loc[i, "fecha"]]) for i in range(last_i + 1)},
             "V": {i: v_obs(tl.loc[i, "fecha"]) for i in range(last_i + 1)},
             "F": {i: (f0, f0) if i == 0 else fobs[i] for i in range(last_i + 1)}}
    mkt = Market(rf=rf_h, erp=erp, q=q_idx, sigma=bt["mkt_vol"], beta=beta_p,
                 resid_vol=bt["table"]["Portafolio"]["resid_vol"], basis_sd=sup["ruido_base"])
    sim = simulate(cfg, tl, mkt, n_paths, sup["semilla"], s_obs, last_i)

    strategies = {
        "sin": run_hedge(tl, sim, beta_p, n_cont, 0, mult, mm_s, imf),
        "corto": run_hedge(tl, sim, beta_p, n_cont, -1, mult, mm_s, imf),
        "largo": run_hedge(tl, sim, beta_p, n_cont, +1, mult, mm_l, imf),
        "corto_fijo": run_hedge(tl, sim, beta_p, n_cont, -1, mult, mm_s, imf, rebalance=False),
    }
    rf_dt = per_period(rf_h, 21 / 252)
    W = {k: wealth(sim, h, rf_dt) for k, h in strategies.items()}
    term = {k: summarize(W[k][:, -1], v0) for k in W}

    # trayectorias representativas por nivel final del índice
    order = np.argsort(sim["S"][:, -1])
    rep = {lab: int(order[int(q * (n_paths - 1))]) for lab, q in (("p5", 0.05), ("p50", 0.50), ("p95", 0.95))}

    # trimestres: fechas de roll y cierre
    q_idx_rows = [0] + [int(i) for i in tl.index[tl["roll"]]] + [len(tl) - 1]
    quarters = []
    for a, b in zip(q_idx_rows[:-1], q_idx_rows[1:], strict=True):
        h = strategies["corto"]
        pnl_q = h["pnl"][:, a + 1:b + 1].sum(axis=1)
        vu = sim["V"][:, b] / sim["V"][:, a] - 1
        wh = W["corto"][:, b] / W["corto"][:, a] - 1
        basis_close = sim["Fo"][:, b] - sim["S"][:, b]
        roll_spread = sim["Fn"][:, b] - sim["Fo"][:, b]
        quarters.append({
            "desde": tl.loc[a, "fecha"], "hasta": tl.loc[b, "fecha"], "cierra": code(*tl.loc[b, "old"]),
            "abre": code(*tl.loc[b, "new"]) if tl.loc[b, "roll"] else "Cierre final",
            "pnl_media": float(pnl_q.mean()), "pnl_p5": float(np.percentile(pnl_q, 5)), "pnl_p95": float(np.percentile(pnl_q, 95)),
            "r_u": float(vu.mean()), "r_h": float(wh.mean()), "sd_u": float(vu.std()), "sd_h": float(wh.std()),
            "base_cierre": float(basis_close.mean()), "base_sd": float(basis_close.std()),
            "spread_roll": float(roll_spread.mean()) if tl.loc[b, "roll"] else float("nan"),
            "dep_media": float(h["dep"][:, a + 1:b + 1].sum(axis=1).mean()),
            "pnl_central": float(pnl_q[rep["p50"]]),
            "p_call": float(h["call"][:, a + 1:b + 1].any(axis=1).mean()),
            "obs": b <= last_i,
            "EV_u": float(sim["V"][:, b].mean()), "EV_h": float(W["corto"][:, b].mean()),
        })
    quarters = pd.DataFrame(quarters)

    # --- 10: valor esperado analítico y sensibilidad a la prima de riesgo
    years = (tl["fecha"].iloc[-1] - t0).days / 365.25
    sens_erp = []
    for e in sup["prima_sensibilidad"]:
        mk_e = Market(rf=rf_h, erp=e, q=q_idx, sigma=mkt.sigma, beta=beta_p, resid_vol=mkt.resid_vol,
                      basis_sd=mkt.basis_sd)
        sim_e = simulate(cfg, tl, mk_e, n_paths, sup["semilla"], s_obs, last_i)
        hu = run_hedge(tl, sim_e, beta_p, n_cont, 0, mult, mm_s, imf)
        hs = run_hedge(tl, sim_e, beta_p, n_cont, -1, mult, mm_s, imf)
        wu, ws = wealth(sim_e, hu, rf_dt)[:, -1], wealth(sim_e, hs, rf_dt)[:, -1]
        sens_erp.append({"erp": e, "Eu": float(wu.mean()), "Eh": float(ws.mean()), "sdu": float(wu.std()),
                         "sdh": float(ws.std()), "ru": (wu.mean() / v0) ** (1 / years) - 1,
                         "rh": (ws.mean() / v0) ** (1 / years) - 1})
    sens_erp = pd.DataFrame(sens_erp)

    # --- 11: rendimiento mensual esperado bajo tres enfoques
    dt = 1 / 12
    sd_m_u = np.sqrt(beta_p**2 * mkt.sigma**2 + mkt.resid_vol**2) * np.sqrt(dt)
    beta_res = beta_p - n_cont * f0 * mult / v0
    h_ratio = n_cont * f0 * mult / v0
    sd_m_h = np.sqrt((beta_res**2 * mkt.sigma**2 + mkt.resid_vol**2) * dt + 2 * (h_ratio * mkt.basis_sd) ** 2)
    mu_m_u = per_period(capm["Portafolio"], dt)
    mu_m_h = per_period(rf_h + beta_res * erp, dt)
    r_sim_u = sim["V"][:, last_i + 1] / sim["V"][:, last_i] - 1
    r_sim_h = W["corto"][:, last_i + 1] / W["corto"][:, last_i] - 1
    monthly = {
        "mu_u": mu_m_u, "mu_h": mu_m_h, "mu_hist": opt["ret"] / 12,
        "sd_u": sd_m_u, "sd_h": sd_m_h, "beta_res": beta_res,
        "sim_mu_u": float(r_sim_u.mean()), "sim_sd_u": float(r_sim_u.std()),
        "sim_mu_h": float(r_sim_h.mean()), "sim_sd_h": float(r_sim_h.std()),
        "var": [{"conf": c, "z": norm.ppf(c),
                 "u_pct": norm.ppf(c) * sd_m_u - mu_m_u, "h_pct": norm.ppf(c) * sd_m_h - mu_m_h} for c in (0.95, 0.99)],
        "q_p": q_p, "q_idx": q_idx, "div_m": q_p / 12,
    }

    # --- 12: betas hipotéticas
    sens_beta = []
    for b in (0.5, beta_p, 2.0):
        ns = b * v0 / (f0 * mult)
        nr = int(round(ns))
        res = b - nr * f0 * mult / v0
        sd_u = np.sqrt(b**2 * mkt.sigma**2 + mkt.resid_vol**2)
        sd_h = np.sqrt(res**2 * mkt.sigma**2 + mkt.resid_vol**2)
        sens_beta.append({"beta": b, "n_star": ns, "n": nr, "exp_sist": b * v0, "dv_1pct": b * v0 * 0.01,
                          "dv_m10": -b * v0 * 0.10, "beta_res": res, "sd_u": sd_u, "sd_h": sd_h,
                          "red_var": 1 - sd_h**2 / sd_u**2, "mm_total": nr * mm_s, "im_total": nr * mm_s * imf,
                          "Eu": rf_h + b * erp, "Eh": rf_h + res * erp})
    sens_beta = pd.DataFrame(sens_beta)
    change_beta = [{"objetivo": b_t, "n": (b_t - beta_p) * v0 / (f0 * mult),
                    "pos": "corta" if b_t < beta_p else "larga"} for b_t in (0.0, 0.5, 2.0)]

    # --- ex post real 30-jul a último dato
    last_px = yahoo("^GSPC")["close"].index.max()
    dates_real = yahoo("^GSPC")["close"].loc[t0:last_px].index
    v_real = pd.Series([v_obs(d) for d in dates_real], index=dates_real)
    div_real = []
    for t in tk:
        for d, a in dividends(t).loc[t0 + pd.Timedelta(days=1):].items():
            div_real.append({"ticker": t, "fecha": d, "dps": a, "acciones": shares[t], "usd": a * shares[t]})
    es = pd.concat([yahoo("ES=F")["close"].loc[t0:"2026-08-31"], yahoo("ESZ26.CME")["close"].loc["2026-09-01":]])
    # resultado corto real: ESU6 hasta 31-ago y ESZ6 desde ahí, con N = n_cont y luego N rebalanceado
    n_roll = int(round(beta_p * v_obs(pd.Timestamp("2026-08-31")) / (fobs[1][1] * mult)))
    pnl_u6 = -n_cont * mult * (fobs[1][0] - f0)
    z_last = float(yahoo("ESZ26.CME")["close"].loc[last_px])
    pnl_z6 = -n_roll * mult * (z_last - fobs[1][1])
    es_daily = pd.Series(index=dates_real, dtype=float)
    u6 = yahoo("ES=F")["close"]
    z6 = yahoo("ESZ26.CME")["close"]
    roll_d = pd.Timestamp("2026-08-31")
    for d in dates_real:
        if d <= roll_d:
            es_daily[d] = -n_cont * mult * (float(u6.loc[d]) - f0)
        else:
            es_daily[d] = pnl_u6 - n_roll * mult * (float(z6.loc[d]) - fobs[1][1])
    expost = {
        "fut_cum": es_daily,
        "fecha": last_px, "v0": invested, "v_last": float(v_real.iloc[-1]), "spx0": s0,
        "spx_last": float(yahoo("^GSPC")["close"].loc[last_px]), "pnl_fut": pnl_u6 + pnl_z6,
        "pnl_u6": pnl_u6, "pnl_z6": pnl_z6, "n_roll": n_roll, "z_last": z_last, "series": v_real,
        "dividends": pd.DataFrame(div_real), "es": es,
        "px_last": {t: float(yahoo(t)["close"].loc[last_px]) for t in tk},
    }

    def margin_stats(h: dict, mm: float) -> dict:
        calls = h["call"][:, 1:]
        dep = h["dep"][:, 1:].sum(axis=1)
        cushion = (imf - 1) * mm
        sweep = (h["pnl"][:, 1:] < -cushion * h["N"][:, :-1]).mean()
        return {"p_any": float(calls.any(axis=1).mean()), "n_calls": float(calls.sum(axis=1).mean()),
                "n_rdep": float(h["rdep"][:, 1:].sum(axis=1).mean()),
                "n_calls_p95": float(np.percentile(calls.sum(axis=1), 95)), "dep_mean": float(dep.mean()),
                "dep_p50": float(np.percentile(dep, 50)), "dep_p95": float(np.percentile(dep, 95)),
                "p_month_call": float(calls.mean()), "sweep_share": float(sweep),
                "im0": n_cont * mm * imf, "mm0": n_cont * mm}

    mstats = {"corto": margin_stats(strategies["corto"], mm_s), "largo": margin_stats(strategies["largo"], mm_l)}
    yrs_sim = (tl["fecha"].iloc[-1] - tl["fecha"].iloc[last_i]).days / 365.25
    from_obs = {kk: float((W[kk][:, -1].mean() / W[kk][0, last_i]) ** (1 / yrs_sim) - 1) for kk in ("sin", "corto")}
    sharpe_rfh = (opt["ret"] - rf_h) / opt["vol"]
    capm_q = per_period(capm["Portafolio"], 0.25)
    rf_q = per_period(rf_h, 0.25)

    return {
        "mstats": mstats, "capm_q": capm_q, "rf_q": rf_q, "from_obs": from_obs, "sharpe_rfh": sharpe_rfh,
        "div_fwd": div_fwd, "w0_obs": float(W["corto"][0, last_i]), "v_obs_last": float(sim["V"][0, last_i]),
        "cfg": cfg, "rb": rb, "opt": opt, "var": vb, "w": w, "rf_s": rf_s, "fvx": fvx, "tnx": tnx, "irx": irx,
        "tsy": tsy, "rf_h": rf_h, "bt": bt, "beta_p": beta_p, "q_idx": q_idx, "erp": erp, "capm": capm,
        "prices": pb, "exp_price": exp_price, "q_p": q_p, "px0": px0, "shares": shares, "invested": invested,
        "cash": cash, "s0": s0, "f0": f0, "f0_theo": f0_theo, "f0_theo_3m": f0_theo_3m, "tau0": tau0, "tl": tl,
        "n_star": n_star, "n_opts": opts_n, "n": n_cont, "mult": mult, "mm_s": mm_s, "mm_l": mm_l, "imf": imf,
        "last_i": last_i, "last_obs": last_obs, "mkt": mkt, "sim": sim, "strat": strategies, "W": W, "term": term,
        "rep": rep, "quarters": quarters, "sens_erp": sens_erp, "monthly": monthly, "sens_beta": sens_beta,
        "change_beta": change_beta, "expost": expost, "years": years, "v0": v0, "n_paths": n_paths, "t0": t0,
        "cut": cut,
    }
