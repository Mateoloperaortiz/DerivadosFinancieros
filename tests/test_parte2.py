import numpy as np
import pandas as pd

from derivados.parte2 import model as m


def test_third_friday():
    assert m.third_friday(2026, 9) == pd.Timestamp("2026-09-18")
    assert m.third_friday(2030, 9) == pd.Timestamp("2030-09-20")


def test_roll_calendar():
    tl = m.build_timeline(m.inputs())
    assert tl["fecha"].iloc[0] == pd.Timestamp("2026-07-30")
    assert tl["fecha"].iloc[-1] == pd.Timestamp("2030-07-30")
    assert int(tl["roll"].sum()) == 16
    assert tl.loc[0, "old"] == (2026, 9)
    first_roll = tl[tl["roll"]].iloc[0]
    assert first_roll["fecha"] == pd.Timestamp("2026-08-31") and first_roll["new"] == (2026, 12)
    assert (tl["tau_old"] > 0).all()


def test_hedge_short_offsets_index():
    tl = pd.DataFrame({"roll": [False, False]})
    sim = {"V": np.array([[100.0, 100.0]]), "Fo": np.array([[10.0, 12.0]]), "Fn": np.array([[10.0, 12.0]])}
    h = m.run_hedge(tl, sim, beta=1.0, n0=2, side=-1, mult=50, mm=100.0, im_factor=1.1)
    assert h["pnl"][0, 1] == -2 * 50 * 2.0
    assert h["call"][0, 1] and np.isclose(h["bal"][0, 1], 2 * 110.0)


def test_optimizer_reproduces_weights():
    cfg = m.inputs()
    rb = m.returns_block(cfg)
    o = m.optimize(rb["stats"]["ret_arit"].to_numpy(), rb["cov"].to_numpy(), cfg["tasas"]["rf_sharpe"]["valor"])
    assert np.allclose(o["w"], [0.414134, 0.477183, 0.108683], atol=1e-4)
    assert abs(o["sharpe"] - 0.9255) < 1e-3
