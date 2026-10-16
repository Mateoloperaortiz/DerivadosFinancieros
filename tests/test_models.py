import numpy as np
import pandas as pd
import pytest

from derivados import cashflows as cf
from derivados import forwards as fw
from derivados import fx_model as fx
from derivados.credit import Loan


def test_french_schedule_amortizes_fully():
    loan = Loan(112_582.68, 0.095)
    s = loan.schedule(pd.Timestamp("2026-10-15"))
    assert len(s) == 40
    assert s["abono_capital"].sum() == pytest.approx(loan.principal_usd)
    assert s["saldo_final"].iloc[-1] == 0
    pv = (s["cuota"] / (1 + loan.periodic_rate) ** s["periodo"]).sum()
    assert pv == pytest.approx(loan.principal_usd)


def test_cip_and_implied_devaluation_are_inverse():
    f = fw.cip_forward(3197.65, 0.1225, 0.04, 252)
    assert fw.implied_devaluation(f, 3197.65, 252) == pytest.approx(1.1225 / 1.04 - 1)
    assert fw.cip_forward(100, 0.1, 0.1, 126) == pytest.approx(100)


def test_rate_conversions():
    assert fw.ea_from_bond_equivalent(0.04) == pytest.approx(0.0404)
    assert fw.ea_from_nominal(0.1141, 1) == pytest.approx(0.1226, abs=5e-4)
    assert fw.calendar_to_business(365) == pytest.approx(252)


def test_t_innovations_have_unit_variance():
    e = fx.innovations(400_000, 1, "t", 6.0, 1)
    assert e.std() == pytest.approx(1, abs=0.02)


def test_simulation_matches_expected_path_on_average():
    mu = fx.drift_schedule(3197.65, 3400, 0.03)
    eps = fx.innovations(100_000, 120, "normal", 6, 3)
    p = fx.simulate(3197.65, 0.128, mu, eps)
    e = fx.expected_path(3197.65, mu)
    assert p[:, 12].mean() == pytest.approx(3400, rel=0.005)
    assert p[:, 120].mean() == pytest.approx(e[120], rel=0.02)


def test_hedge_payoff_and_budget_identity():
    paths = np.tile(np.linspace(3000, 4200, 121), (3, 1))
    h = fw.hedge(paths, 1000.0, 0.04)
    assert np.allclose(h.payoff, h.notional_usd * (h.spot_t - h.forward))
    assert np.allclose(h.cost_hedged, h.cost_unhedged - h.payoff)
    assert np.all(h.notional_usd <= h.obligation_usd)
    strip = fw.hedge(paths, 1000.0, 0.04, style="strip")
    assert np.allclose(strip.forward[:, 3], paths[:, 72] * 1.04**4)


def test_irr_with_constant_spot_equals_loan_rate():
    loan = Loan(100_000, 0.095)
    pay = np.full((1, 40), loan.installment * 3000)
    assert cf.irr_ea(100_000 * 3000, pay)[0] == pytest.approx(loan.effective_annual_rate, abs=1e-9)
