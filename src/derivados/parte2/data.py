"""Carga de los datos de la Parte 2 (versionados en data/raw/parte2 y data/manual/parte2_inputs.yaml)."""

from __future__ import annotations

import io
import json
from functools import cache

import pandas as pd
import yaml

from ..data import MANUAL, RAW

RAW2 = RAW / "parte2"


@cache
def inputs() -> dict:
    return yaml.safe_load((MANUAL / "parte2_inputs.yaml").read_text(encoding="utf-8"))


@cache
def _bundle() -> dict:
    return json.loads((RAW2 / "yahoo_parte2.json").read_text(encoding="utf-8"))


@cache
def yahoo(symbol: str) -> pd.DataFrame:
    """Serie diaria de Yahoo Finance: open, close (sin ajustar) y adjclose (ajustado por dividendos y splits)."""
    df = pd.read_csv(io.StringIO(_bundle()["series"][symbol]["csv"]), parse_dates=["date"]).set_index("date")
    return df[~df.index.duplicated(keep="last")].sort_index()


@cache
def dividends(symbol: str) -> pd.Series:
    txt = _bundle()["series"][symbol]["div"]
    if not txt:
        return pd.Series(dtype=float)
    df = pd.read_csv(io.StringIO("date,amount\n" + txt), parse_dates=["date"])
    return df.set_index("date")["amount"].sort_index()


@cache
def treasury() -> pd.DataFrame:
    df = pd.read_csv(RAW2 / "treasury_par_yield_2026.csv")
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
    return df.set_index("Date").sort_index() / 100


def consulta() -> str:
    return _bundle()["consulta"]
