"""Sistema visual de las gráficas: paleta validada (modo claro y oscuro), plantilla base y paso a HTML.

La paleta categórica pasó el validador de la skill dataviz (separación con daltonismo protan/deutan, piso de
visión normal y contraste) para cada combinación de series que comparte una gráfica, en los dos modos. El modo
oscuro no es una inversión: cada color tiene su propio paso y el navegador cambia uno por otro con ``dark_map``.

Reglas para quien dibuje una gráfica nueva:
- Todo color sale de ``C``, de ``rgba()``, ``SEQ`` o ``DIV``; nunca un hexadecimal suelto (la prueba lo exige).
- Un solo eje Y por panel: dos magnitudes distintas van en paneles separados (``make_subplots``).
- Los menús de Plotly (``updatemenus``) se convierten en botones HTML encima de la gráfica (ver ``to_div``).
- Lo que no cabe en el celular (rótulos largos, leyendas, marcas del eje) se resuelve con ``narrow``: un juego de
  ajustes que el navegador aplica solo cuando el lienzo es angosto, sin tocar la versión de escritorio.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import plotly.graph_objects as go
import plotly.io as pio
from plotly.utils import PlotlyJSONEncoder

FONT = "IBM Plex Sans, system-ui, -apple-system, Segoe UI, sans-serif"
MONO = "IBM Plex Mono, ui-monospace, SFMono-Regular, Menlo, monospace"

LIGHT = dict(
    surface="#ffffff", ink="#121c19", ink2="#44514c", muted="#6f7b76", grid="#e6ebe8", axis="#b9c3bf",
    green="#0f8a68", blue="#2f6fd1", verm="#d6452c", ocre="#d99f0b", violet="#7a5bd6", magenta="#c94f8c",
    gray="#9aa19d",
)
DARK = dict(
    surface="#151b19", ink="#e7eeea", ink2="#b4c0bb", muted="#87938e", grid="#25302c", axis="#3c4945",
    green="#1f9f78", blue="#4f86ea", verm="#d0453f", ocre="#b28f17", violet="#8e7ceb", magenta="#d6619b",
    gray="#6f7772",
)
C = SimpleNamespace(**LIGHT)

# Escala secuencial (un solo tono, verde) y divergente (azul ↔ gris ↔ bermellón). En oscuro el ancla se invierte:
# el valor bajo queda cerca de la superficie y el alto, brillante.
SEQ_LIGHT = ["#e6f4ee", "#c2e5d6", "#93d0b8", "#5fb597", "#2f9877", "#11795d", "#0b5944"]
SEQ_DARK = ["#18302a", "#1b4a3d", "#1d6651", "#228466", "#3aa37e", "#6cc3a0", "#a6e0c6"]
DIV_LIGHT = ["#1f56a8", "#6f9be0", "#c3d5f2", "#eef0ee", "#f3c7bb", "#e2795c", "#b5361f"]
DIV_DARK = ["#7aa6f2", "#3f69b3", "#273a5c", "#2b3230", "#5c2f28", "#b04c39", "#f08268"]
SEQ = [[i / (len(SEQ_LIGHT) - 1), c] for i, c in enumerate(SEQ_LIGHT)]
DIV = [[i / (len(DIV_LIGHT) - 1), c] for i, c in enumerate(DIV_LIGHT)]

# Significado fijo de cada color en todo el informe (el color sigue a la entidad, nunca al orden).
SCEN = {"base": C.gray, "favorable": C.blue, "central": C.green, "adverso": C.verm, "neutral": C.violet}
# Las distribuciones no repiten los colores de los escenarios, que aparecen en las mismas secciones.
DIST = {"normal": C.ocre, "t": C.magenta}
HEDGE = {"sin": C.gray, "con": C.green}
TICKER = {"MSFT": C.blue, "WMT": C.ocre, "XOM": C.verm, "S&P 500": C.gray, "Portafolio": C.green}
STRAT_P2 = {"sin": C.gray, "corto": C.green, "largo": C.verm}

_MAP: dict[str, str] = {}


def _register(light: str, dark: str) -> None:
    if _MAP.get(light, dark) != dark:
        raise ValueError(f"{light} ya tiene otra pareja oscura ({_MAP[light]} ≠ {dark})")
    _MAP[light] = dark


for _k in LIGHT:
    _register(LIGHT[_k], DARK[_k])
for _a, _b in zip(SEQ_LIGHT + DIV_LIGHT, SEQ_DARK + DIV_DARK, strict=True):
    _register(_a, _b)


def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def rgba(color: str, alpha: float, dark_alpha: float | None = None) -> str:
    """Color de la paleta con transparencia; registra su pareja para el modo oscuro.

    ``dark_alpha`` fija la opacidad del par oscuro cuando el refuerzo de abajo sobra: una franja de fondo que en claro
    es apenas un tinte no debe pesar en oscuro tanto como los datos.
    """
    if color not in _MAP:
        raise ValueError(f"{color} no pertenece a la paleta")
    light = "rgba({},{},{},{:g})".format(*_rgb(color), alpha)
    # Sobre la superficie oscura un relleno tenue casi desaparece: su pareja lleva más opacidad (1 − (1 − α)^1,6, que
    # no repite valores). Los velos del color de la superficie conservan la suya.
    if dark_alpha is None:
        dark_alpha = alpha if color == C.surface else round(1 - (1 - alpha) ** 1.6, 3)
    _register(light, "rgba({},{},{},{:g})".format(*_rgb(_MAP[color]), dark_alpha))
    return light


def dark_map() -> dict[str, str]:
    """Pares color claro → color oscuro que usa el navegador para cambiar de tema."""
    return dict(_MAP)


def dark_map_json() -> str:
    return json.dumps(_MAP, separators=(",", ":"))


TEMPLATE = go.layout.Template(
    layout=dict(
        font=dict(family=FONT, size=13, color=C.ink2),
        colorway=[C.green, C.blue, C.verm, C.ocre, C.violet, C.magenta],
        # El lienzo lleva el color de la tarjeta: con fondo transparente plotly.js pinta sobre blanco el trazo bajo la
        # cruz de lectura y la caja del nombre en el tooltip, y en modo oscuro se ven.
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=C.surface,
        separators=",.",
        hovermode="closest",
        hoverlabel=dict(bgcolor=C.surface, bordercolor=C.axis, font=dict(family=FONT, size=12.5, color=C.ink),
                        align="left", namelength=-1),
        legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom", bgcolor="rgba(0,0,0,0)",
                    font=dict(size=12.5, color=C.ink2), itemwidth=30,
                    tracegroupgap=4),
        xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor=C.axis, linewidth=1, ticks="outside",
                   tickcolor=C.axis, ticklen=4, tickfont=dict(size=12, color=C.muted), automargin=True,
                   title=dict(font=dict(size=12.5, color=C.ink2), standoff=12), gridcolor=C.grid, gridwidth=1,
                   spikecolor=C.axis, spikethickness=1, spikedash="solid", spikemode="across", spikesnap="cursor"),
        yaxis=dict(showgrid=True, gridcolor=C.grid, gridwidth=1, zeroline=False, showline=False, ticks="",
                   tickfont=dict(size=12, color=C.muted), automargin=True, linecolor=C.axis,
                   title=dict(font=dict(size=12.5, color=C.ink2), standoff=14)),
        annotationdefaults=dict(font=dict(size=11.5, color=C.ink2), arrowcolor=C.muted, arrowwidth=1, arrowhead=0,
                                bgcolor="rgba(0,0,0,0)", borderpad=2),
        shapedefaults=dict(line=dict(color=C.axis, width=1)),
        bargap=0.38,
        bargroupgap=0.1,
        barcornerradius=4,
        modebar=dict(bgcolor="rgba(0,0,0,0)", color=C.muted, activecolor=C.ink),
        margin=dict(l=8, r=16, t=16, b=8),
        polar=dict(bgcolor="rgba(0,0,0,0)"),
    ),
    data=dict(
        scatter=[go.Scatter(line=dict(width=2), marker=dict(size=8, line=dict(color=C.surface, width=2)))],
        bar=[go.Bar(marker=dict(line=dict(width=0)), textfont=dict(color=C.ink2, size=11.5),
                    insidetextfont=dict(color=C.surface), outsidetextfont=dict(color=C.ink2))],
        heatmap=[go.Heatmap(colorscale=SEQ, colorbar=dict(outlinewidth=0, thickness=10,
                                                          tickfont=dict(color=C.muted, size=11),
                                                          title=dict(font=dict(color=C.ink2, size=12))))],
        box=[go.Box(line=dict(width=1.5))],
        table=[go.Table(header=dict(line=dict(color=C.grid)), cells=dict(line=dict(color=C.grid)))],
    ),
)

CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "locale": "es",
    "displayModeBar": "hover",
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines", "hoverClosestCartesian",
                               "hoverCompareCartesian"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def _layout(fig: go.Figure, height: int = 430, **kw) -> go.Figure:
    layout = dict(template=TEMPLATE, height=height)
    layout.update(kw)
    fig.update_layout(**layout)
    return fig


def _menu(buttons: list[dict], **_ignored) -> list[dict]:
    """Menú de vistas. ``to_div`` lo convierte en botones HTML, así que la posición dentro del lienzo no importa."""
    return [dict(type="buttons", buttons=buttons, showactive=True, visible=False)]


def _visible(n: int, on: list[int]) -> list[bool]:
    return [i in on for i in range(n)]


def narrow(fig: go.Figure, below: int, layout: dict | None = None, traces: dict[int, dict] | None = None) -> go.Figure:
    """Ajustes para cuando el lienzo es angosto (el celular): por debajo de ``below`` px de ancho, el navegador aplica
    ``layout`` (claves con puntos, como en ``Plotly.relayout``: "xaxis.dtick", "legend.font.size", "annotations") y
    ``traces`` ({índice de la serie: {atributo: valor}}); si el lienzo vuelve a ensancharse, repone lo de la figura.
    Una clave "height" cambia también el alto que la página le reserva. Los colores siguen saliendo de la paleta."""
    fig._dv_narrow = dict(below=below, layout=layout or {}, traces=traces or {})
    return fig


def _path(o, path: str):
    for k in path.split("."):
        if not isinstance(o, dict) or k not in o:
            return None
        o = o[k]
    return o


def _narrow_spec(spec: dict, nar: dict) -> dict:
    """Los dos juegos de valores, el angosto («on») y el de la figura («off»), listos para JSON."""
    def js(o):
        return json.loads(json.dumps(o, cls=PlotlyJSONEncoder))

    on_layout = js(nar["layout"])
    on_traces = {str(i): js(attrs) for i, attrs in nar["traces"].items()}
    off_layout = {k: _path(spec["layout"], k) for k in on_layout}
    off_traces = {i: {k: _path(spec["data"][int(i)], k) for k in attrs} for i, attrs in on_traces.items()}
    return {"below": nar["below"], "on": {"layout": on_layout, "traces": on_traces},
            "off": {"layout": off_layout, "traces": off_traces}}


def _controls(fig: go.Figure) -> list[dict]:
    """Saca los menús de la figura y los describe para pintarlos como botones HTML."""
    menus = []
    for m in fig.layout.updatemenus or ():
        buttons = [dict(label=b.label, method=b.method, args=list(b.args or [])) for b in m.buttons]
        menus.append(dict(buttons=buttons, active=int(m.active or 0)))
    fig.layout.updatemenus = ()
    return menus


def _controls_html(div_id: str, menus: list[dict]) -> str:
    parts = []
    for mi, m in enumerate(menus):
        labels = [b["label"] for b in m["buttons"]]
        split = [lab.split(" · ") for lab in labels]
        dims = len(split[0])
        if dims > 1 and all(len(s) == dims for s in split):
            groups = [list(dict.fromkeys(s[d] for s in split)) for d in range(dims)]
        else:
            groups, split = [labels], [[lab] for lab in labels]
        active = split[m["active"]]
        for d, opts in enumerate(groups):
            if len(opts) > 5:
                options = "".join(f'<option{" selected" if o == active[d] else ""}>{o}</option>' for o in opts)
                parts.append(f'<select class="seg-select" data-menu="{mi}" data-dim="{d}" aria-label="Vista">{options}</select>')
            else:
                btns = "".join(
                    f'<button type="button" data-dim="{d}" aria-pressed="{"true" if o == active[d] else "false"}">{o}</button>'
                    for o in opts
                )
                parts.append(f'<div class="seg" role="group" data-menu="{mi}">{btns}</div>')
    return f'<div class="plot-controls" data-for="{div_id}">{"".join(parts)}</div>' if parts else ""


def to_div(fig: go.Figure, div_id: str) -> str:
    """Contenedor de la gráfica: controles HTML, lienzo con la altura reservada y la especificación en JSON.

    El JavaScript de la página (``_scripts.html.j2``) dibuja la figura cuando se acerca a la pantalla y la vuelve a
    colorear al cambiar entre modo claro y oscuro.
    """
    menus = _controls(fig)
    spec = json.loads(pio.to_json(fig, validate=False))
    spec["config"] = CONFIG
    spec["menus"] = [[{k: b[k] for k in ("label", "method", "args")} for b in m["buttons"]] for m in menus]
    if getattr(fig, "_dv_narrow", None):
        spec["narrow"] = _narrow_spec(spec, fig._dv_narrow)
    height = int(fig.layout.height or 430)
    payload = json.dumps(spec, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return (
        f'<div class="plot-wrap">{_controls_html(div_id, menus)}'
        f'<div class="plot" id="{div_id}" style="height:{height}px"></div>'
        f'<script type="application/json" class="plot-spec" data-for="{div_id}">{payload}</script></div>'
    )
