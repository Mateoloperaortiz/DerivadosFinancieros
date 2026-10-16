"""Flujo consolidado del crédito en COP, TIR (costo efectivo) y valor presente."""

from __future__ import annotations

import numpy as np


def quarterly_spots(paths: np.ndarray) -> np.ndarray:
    """TRM en t0 y en cada fecha de cuota (meses 0, 3, ..., 120)."""
    return paths[:, ::3]


def debt_service(installment: float, q_spots: np.ndarray, payoff: np.ndarray | None = None) -> np.ndarray:
    """Servicio de deuda trimestral en COP (n, 40); los forwards se liquidan en los trimestres 28, 32, 36, 40."""
    cost = installment * q_spots[:, 1:]
    if payoff is not None:
        cost = cost.copy()
        cost[:, [27, 31, 35, 39]] -= payoff
    return cost


def irr_ea(disbursement: float, payments: np.ndarray, periods_per_year: int = 4, iters: int = 60) -> np.ndarray:
    """TIR efectiva anual de [+desembolso, -pagos] por trayectoria (Newton vectorizado)."""
    payments = np.atleast_2d(payments)
    t = np.arange(1, payments.shape[1] + 1)
    r = np.full(payments.shape[0], 0.025)
    for _ in range(iters):
        disc = (1 + r)[:, None] ** -t
        f = disbursement - (payments * disc).sum(axis=1)
        df = (payments * t * disc / (1 + r)[:, None]).sum(axis=1)
        r = r - f / df
    return (1 + r) ** periods_per_year - 1


def present_value(payments: np.ndarray, rate_ea: float, periods_per_year: int = 4) -> np.ndarray:
    payments = np.atleast_2d(payments)
    t = np.arange(1, payments.shape[1] + 1)
    return (payments * (1 + rate_ea) ** (-t / periods_per_year)).sum(axis=1)
