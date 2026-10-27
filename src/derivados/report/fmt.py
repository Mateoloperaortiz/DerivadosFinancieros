"""Formato numérico colombiano: miles con punto y decimales con coma."""

from __future__ import annotations

import math

import pandas as pd

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def num(x: float, d: int = 0) -> str:
    """Cifra con miles en punto, decimales en coma y signo menos tipográfico (−), igual que en los ejes de Plotly."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "s. d."
    if round(x, d) == 0:
        x = 0.0
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", MINUS)


def pct(x: float, d: int = 2, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "s. d."
    sign = "+" if signed and round(100 * x, d) > 0 else ""
    return f"{sign}{num(100 * x, d)}{NBSP}%"


NBSP = "\u00a0"  # espacio que no se parte: evita que "%" o "COP" queden solos al final de una línea
MINUS = "\N{MINUS SIGN}"  # signo menos tipográfico, el mismo de los ejes; texnum lo devuelve a "-" para KaTeX


def cop(x: float, d: int = 0) -> str:
    return f"COP{NBSP}{num(x, d)}"


def mcop(x: float, d: int = 1) -> str:
    return f"COP{NBSP}{num(x / 1e6, d)}{NBSP}millones"


def mm(x: float, d: int = 1) -> str:
    return num(x / 1e6, d)


def usd(x: float, d: int = 2) -> str:
    return f"USD{NBSP}{num(x, d)}"


def pb(x: float, d: int = 0) -> str:
    return f"{num(x, d)}{NBSP}pb"


def fecha(ts, largo: bool = False) -> str:
    ts = pd.Timestamp(ts)
    if largo:
        return f"{ts.day} de {MESES_LARGOS[ts.month - 1]} de {ts.year}"
    return f"{ts.day}-{MESES[ts.month - 1]}-{ts.year}"


def mes(ts) -> str:
    ts = pd.Timestamp(ts)
    return f"{MESES[ts.month - 1]}-{ts.year}"


def texnum(s: str) -> str:
    """Protege la coma decimal en LaTeX (KaTeX añade espacio tras una coma en modo matemático) y entrega el signo
    menos como "-", que KaTeX ya dibuja como −."""
    return s.replace(",", "{,}").replace(MINUS, "-")


FILTERS = {"num": num, "pct": pct, "cop": cop, "mcop": mcop, "mm": mm, "usd": usd, "pb": pb, "fecha": fecha,
           "mes": mes, "texnum": texnum}
