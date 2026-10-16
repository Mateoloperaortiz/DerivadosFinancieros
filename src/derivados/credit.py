"""Crédito en USD amortizado por sistema francés (cuota constante)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Loan:
    principal_usd: float
    nominal_rate: float  # nominal anual pagadera por período (T.V. si periods_per_year = 4)
    years: int = 10
    periods_per_year: int = 4

    @property
    def n_periods(self) -> int:
        return self.years * self.periods_per_year

    @property
    def periodic_rate(self) -> float:
        return self.nominal_rate / self.periods_per_year

    @property
    def effective_annual_rate(self) -> float:
        return (1 + self.periodic_rate) ** self.periods_per_year - 1

    @property
    def installment(self) -> float:
        i = self.periodic_rate
        return self.principal_usd * i / (1 - (1 + i) ** -self.n_periods)

    def schedule(self, start: pd.Timestamp) -> pd.DataFrame:
        i, a = self.periodic_rate, self.installment
        months = 12 // self.periods_per_year
        rows, balance = [], self.principal_usd
        for k in range(1, self.n_periods + 1):
            interest = balance * i
            principal = a - interest
            rows.append(
                {
                    "periodo": k,
                    "fecha": start + pd.DateOffset(months=months * k),
                    "anio": (k - 1) // self.periods_per_year + 1,
                    "saldo_inicial": balance,
                    "interes": interest,
                    "abono_capital": principal,
                    "cuota": a,
                    "saldo_final": balance - principal,
                }
            )
            balance -= principal
        df = pd.DataFrame(rows)
        df.loc[df.index[-1], "saldo_final"] = 0.0
        return df
