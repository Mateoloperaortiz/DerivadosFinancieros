import json
import re

import pytest

from derivados.data import ROOT
from derivados.report import theme

COLOR = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(.*\)|hsla?\(.*\))$")
PAGES = [ROOT / "docs" / "index.html", ROOT / "docs" / "parte2.html"]


def test_dark_map_is_invertible():
    m = theme.dark_map()
    assert len(set(m.values())) == len(m), "dos colores claros comparten pareja oscura"


def test_rgba_registers_dark_pair():
    light = theme.rgba(theme.C.green, 0.15)
    assert theme.dark_map()[light] == "rgba(31,159,120,0.229)"
    veil = theme.rgba(theme.C.surface, 0.85)
    assert theme.dark_map()[veil] == "rgba(21,27,25,0.85)"
    with pytest.raises(ValueError):
        theme.rgba("#123456", 0.5)


def _colors(o, out):
    if isinstance(o, str):
        if COLOR.match(o):
            out.add(o)
    elif isinstance(o, dict):
        for v in o.values():
            _colors(v, out)
    elif isinstance(o, list):
        for v in o:
            _colors(v, out)
    return out


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_published_charts_use_the_palette(page):
    if not page.exists():
        pytest.skip("falta generar el informe")
    html = page.read_text(encoding="utf-8")
    dark = json.loads(re.search(r"window\.DV_DARK = (\{.*?\});", html).group(1))
    specs = re.findall(r'<script type="application/json" class="plot-spec" data-for="([^"]+)">(.*?)</script>', html, re.S)
    assert specs
    for div_id, raw in specs:
        spec = json.loads(raw.replace("<\\/", "</"))
        missing = (_colors([spec["data"], spec["layout"], spec["menus"], spec.get("narrow", {})], set())
                   - set(dark) - {"rgba(0,0,0,0)"})
        assert not missing, f"{div_id}: colores sin pareja oscura {sorted(missing)}"
        overlaid = [k for k, v in spec["layout"].items() if k.startswith("yaxis") and v.get("overlaying")]
        assert not overlaid, f"{div_id}: doble eje Y {overlaid}"
