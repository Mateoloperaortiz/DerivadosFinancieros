"""Calibración y simulación de la TRM con innovaciones normales y t de Student.

Modelo: movimiento browniano geométrico discretizado mensualmente (21 días hábiles,
dt = 21/252) con deriva anual por tramos (año 1 anclado a la TRM esperada a 12 meses,
años 2–10 con deriva de largo plazo). La t de Student se estandariza a varianza 1, de modo
que ambas distribuciones comparten volatilidad y solo difieren en la forma (colas).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .data import trm_business_days, trm_month_end

DT = 21 / 252


@dataclass(frozen=True)
class Calibration:
    sigma: float
    nu: float
    mean: float
    skew: float
    ex_kurt: float
    n_obs: int
    start: str
    end: str
    sigma_daily: float
    nu_daily: float
    ex_kurt_daily: float


@dataclass(frozen=True)
class Scenario:
    key: str
    nombre: str
    trm_12m: float
    deriva_lp: float
    probabilidad: float
    narrativa: str


def monthly_log_returns(start: str, end: str) -> pd.Series:
    r = np.log(trm_month_end()).diff().dropna()
    return r[(r.index >= start) & (r.index <= end)]


def calibrate(start: str = "2000-01-01", end: str = "2026-09-30") -> Calibration:
    r = monthly_log_returns(start, end)
    nu, _, _ = stats.t.fit(r)
    d = np.log(trm_business_days()).diff().dropna()
    d = d[(d.index >= start) & (d.index <= end)]
    nu_d, _, _ = stats.t.fit(d)
    return Calibration(
        sigma=float(r.std(ddof=1) * np.sqrt(12)),
        nu=float(nu),
        mean=float(r.mean() * 12),
        skew=float(stats.skew(r)),
        ex_kurt=float(stats.kurtosis(r)),
        n_obs=len(r),
        start=r.index[0].strftime("%Y-%m"),
        end=r.index[-1].strftime("%Y-%m"),
        sigma_daily=float(d.std(ddof=1) * np.sqrt(252)),
        nu_daily=float(nu_d),
        ex_kurt_daily=float(stats.kurtosis(d)),
    )


def drift_schedule(s0: float, trm_12m: float, deriva_lp: float, months: int = 120) -> np.ndarray:
    """Deriva logarítmica anual por mes: E[S_12] = trm_12m y luego E[S] crece a (1 + deriva_lp) por año."""
    mu = np.full(months, np.log1p(deriva_lp))
    mu[:12] = np.log(trm_12m / s0)
    return mu


def innovations(n_paths: int, months: int, dist: str, nu: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if dist == "normal":
        return rng.standard_normal((n_paths, months))
    return rng.standard_t(nu, (n_paths, months)) * np.sqrt((nu - 2) / nu)


def simulate(s0: float, sigma: float, mu: np.ndarray, eps: np.ndarray, dt: float = DT) -> np.ndarray:
    """Trayectorias (n_paths, months + 1) con S0 en la columna 0."""
    steps = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * eps
    log_paths = np.concatenate([np.zeros((eps.shape[0], 1)), np.cumsum(steps, axis=1)], axis=1)
    return s0 * np.exp(log_paths)


def expected_path(s0: float, mu: np.ndarray, dt: float = DT) -> np.ndarray:
    return s0 * np.exp(np.concatenate([[0.0], np.cumsum(mu * dt)]))
