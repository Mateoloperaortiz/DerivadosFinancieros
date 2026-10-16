"""Descarga, cacheo y carga de datos de mercado.

Los datos descargados se guardan en ``data/raw`` para que el informe sea reproducible
con la misma fecha de corte aunque las fuentes se actualicen después.
"""

from __future__ import annotations

import io
from functools import cache
from pathlib import Path

import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MANUAL = ROOT / "data" / "manual"

TRM_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = {
    "DPRIME": "Bank prime loan rate (H.15)",
    "SOFR": "Secured Overnight Financing Rate",
    "DFEDTARU": "Federal funds target range - upper limit",
    "DFEDTARL": "Federal funds target range - lower limit",
    "DGS1": "Market yield on U.S. Treasury, 1-year constant maturity",
    "DGS10": "Market yield on U.S. Treasury, 10-year constant maturity",
    "DCOILBRENTEU": "Crude oil prices: Brent - Europe (EIA)",
    "CPIAUCNS": "CPI all urban consumers, not seasonally adjusted",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (proyecto academico derivados financieros)"}


def download_trm(path: Path = RAW / "trm.csv") -> pd.DataFrame:
    """TRM certificada por la Superintendencia Financiera (datos.gov.co, conjunto 32sa-8pi3)."""
    params = {"$limit": 50000, "$order": "vigenciadesde ASC"}
    resp = requests.get(TRM_URL, params=params, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df = pd.DataFrame(
        {
            "vigencia_desde": pd.to_datetime(df["vigenciadesde"]).dt.date,
            "vigencia_hasta": pd.to_datetime(df["vigenciahasta"]).dt.date,
            "trm": df["valor"].astype(float),
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def download_fred(series_id: str, start: str = "2000-01-01") -> pd.DataFrame:
    resp = requests.get(
        FRED_URL, params={"id": series_id, "cosd": start}, headers={"User-Agent": "curl/8.7.1"}, timeout=60
    )
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = ["fecha", series_id]
    (RAW / f"fred_{series_id}.csv").write_text(df.to_csv(index=False))
    return df


def download_all() -> None:
    download_trm()
    for sid in FRED_SERIES:
        download_fred(sid)


@cache
def manual_inputs() -> dict:
    """Insumos documentados manualmente (fuente, fecha de consulta y forma de cotización)."""
    return yaml.safe_load((MANUAL / "market_inputs.yaml").read_text(encoding="utf-8"))


@cache
def trm_business_days() -> pd.Series:
    """Serie de TRM por día hábil de vigencia (un registro por certificación)."""
    df = pd.read_csv(RAW / "trm.csv", parse_dates=["vigencia_desde", "vigencia_hasta"])
    return df.set_index("vigencia_desde")["trm"].sort_index()


@cache
def trm_calendar() -> pd.Series:
    """TRM vigente para cada día calendario (fines de semana y festivos incluidos)."""
    df = pd.read_csv(RAW / "trm.csv", parse_dates=["vigencia_desde", "vigencia_hasta"])
    days = pd.date_range(df["vigencia_desde"].min(), df["vigencia_hasta"].max(), freq="D")
    s = df.set_index("vigencia_desde")["trm"].sort_index()
    return s.reindex(days, method="ffill")


@cache
def trm_month_end() -> pd.Series:
    """TRM vigente el último día calendario de cada mes."""
    return trm_calendar().resample("ME").last()


@cache
def fred(series_id: str) -> pd.Series:
    df = pd.read_csv(RAW / f"fred_{series_id}.csv", parse_dates=["fecha"])
    s = pd.to_numeric(df[series_id], errors="coerce")
    return pd.Series(s.to_numpy(), index=df["fecha"], name=series_id).dropna()
