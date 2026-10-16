"""Paridad cubierta de tasas, conversiones de tasas y estrategias de cobertura con forwards (NDF)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

BASE = 252


def ea_from_nominal(rate: float, period_days: int, day_base: int = 360, year_days: int = 365) -> float:
    """Tasa nominal (base 360) a efectiva anual, capitalizando en el plazo del período."""
    return (1 + rate * period_days / day_base) ** (year_days / period_days) - 1


def ea_from_simple(rate: float, days: int = 365, day_base: int = 360) -> float:
    """Tasa simple a un año (p. ej. Act/360) a efectiva anual."""
    return rate * days / day_base


def ea_from_bond_equivalent(y: float) -> float:
    return (1 + y / 2) ** 2 - 1


def cip_forward(spot: float, r_cop: float, r_usd: float, days: float, base: int = BASE) -> float:
    """F = S · [(1 + r_COP) / (1 + r_USD)]^(n/252), con tasas efectivas anuales."""
    return spot * ((1 + r_cop) / (1 + r_usd)) ** (days / base)


def implied_devaluation(forward: float, spot: float, days: float, base: int = BASE) -> float:
    return (forward / spot) ** (base / days) - 1


def calendar_to_business(days: float) -> float:
    return days * BASE / 365


@dataclass
class HedgeResult:
    years: np.ndarray  # años cubiertos (7..10)
    notional_usd: np.ndarray  # nominal por forward
    forward: np.ndarray  # (n, k) tasa pactada
    spot_t: np.ndarray  # (n, k) TRM al vencimiento
    payoff: np.ndarray  # (n, k) liquidación en COP (positivo = recibe la empresa)
    avg_spot: np.ndarray  # (n, k) TRM promedio de las cuatro cuotas del año
    cost_unhedged: np.ndarray  # (n, k) cuotas del año en COP sin cobertura
    cost_hedged: np.ndarray  # (n, k) cuotas del año en COP neto del forward
    budget: np.ndarray  # (n, k) presupuesto del año: 4 cuotas a la tasa forward pactada
    obligation_usd: np.ndarray  # pagos programados por año

    @property
    def budget_dev_unhedged(self) -> np.ndarray:
        return self.cost_unhedged / self.budget - 1

    @property
    def budget_dev_hedged(self) -> np.ndarray:
        return self.cost_hedged / self.budget - 1


def _year_months(year: int, months_per_year: int = 12) -> list[int]:
    start = months_per_year * (year - 1)
    return [start + 3, start + 6, start + 9, start + 12]


def hedge(
    paths: np.ndarray,
    installment: float,
    d: float,
    hedge_ratio: float = 0.75,
    years: tuple[int, ...] = (7, 8, 9, 10),
    style: str = "rolling",
) -> HedgeResult:
    """Cuatro NDF anuales sobre el 75 % de las cuotas de cada año, liquidados contra la TRM.

    style = "rolling": cada forward a 1 año se pacta al cierre del año anterior (F = S_{k-1}·(1+d)).
    style = "strip": los cuatro se pactan al cierre del año 6 con plazos 1–4 años (F = S_6·(1+d)^(k-6)).
    """
    n, k = paths.shape[0], len(years)
    obligation = np.full(k, 4 * installment)
    notional = hedge_ratio * obligation
    out = {name: np.empty((n, k)) for name in ("forward", "spot_t", "avg_spot", "cost_u")}
    for j, year in enumerate(years):
        months = _year_months(year)
        if style == "rolling":
            out["forward"][:, j] = paths[:, 12 * (year - 1)] * (1 + d)
        else:
            out["forward"][:, j] = paths[:, 12 * (years[0] - 1)] * (1 + d) ** (year - years[0] + 1)
        out["spot_t"][:, j] = paths[:, 12 * year]
        out["avg_spot"][:, j] = paths[:, months].mean(axis=1)
        out["cost_u"][:, j] = installment * paths[:, months].sum(axis=1)
    payoff = notional * (out["spot_t"] - out["forward"])
    return HedgeResult(
        years=np.array(years),
        notional_usd=notional,
        forward=out["forward"],
        spot_t=out["spot_t"],
        payoff=payoff,
        avg_spot=out["avg_spot"],
        cost_unhedged=out["cost_u"],
        cost_hedged=out["cost_u"] - payoff,
        budget=obligation * out["forward"],
        obligation_usd=obligation,
    )


def hedge_quarterly_matched(
    paths: np.ndarray, installment: float, d: float, hedge_ratio: float = 0.75, years=(7, 8, 9, 10)
) -> np.ndarray:
    """Variante sin desfase temporal: cuatro forwards por año, cada uno al vencimiento de una cuota.

    Devuelve el costo cubierto por año (n, k) para aislar el riesgo de base de la liquidación anual.
    """
    cost = np.empty((paths.shape[0], len(years)))
    for j, year in enumerate(years):
        s_start = paths[:, 12 * (year - 1)]
        total = np.zeros(paths.shape[0])
        for q, m in enumerate(_year_months(year), start=1):
            f = s_start * (1 + d) ** (q / 4)
            total += installment * paths[:, m] - hedge_ratio * installment * (paths[:, m] - f)
        cost[:, j] = total
    return cost
