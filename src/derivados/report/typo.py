"""Pulido tipográfico del HTML ya renderizado.

Recorre solo el texto visible: nunca toca etiquetas ni atributos, el contenido de <script> (las especificaciones JSON
de las gráficas), <style>, los botones y opciones que el JS compara con las vistas de cada gráfica, ni lo que va entre
delimitadores KaTeX (\\( \\), \\[ \\], $$ $$). Reglas:

- espacio duro antes de %, pp, pb, σ, M y millones, y después de USD, COP y EUR delante de una cifra;
- espacio duro entre % y la unidad de la tasa (9,84 % E.A., 9,50 % N.T.V., 31,1 % a/a);
- espacio duro entre una cifra y años, meses, días, sem., pesos, dólares, cuotas, puntos, pts. o veces (10 años,
  8,3 pesos, 24 cuotas, 4,3 veces), y entre año(s), mes(es) o día(s) y la cifra o el rango que sigue (año 6, años 7–10);
- espacio duro a ambos lados de → entre cifras (8,66 % → 0,13 %), y después de → si sigue una cifra con su moneda
  (USD 10,63 M → USD 6,14 M parte antes de la flecha, nunca después);
- espacio duro tras «vs.» si sigue una cifra o una palabra de una o dos letras (normal vs. t, 7,50 % vs. 3,40 %);
- espacio duro tras un «+» rodeado de espacios (Prime + 6,0 pp, 3 % + tasa real): el renglón parte antes del operador
  y nunca termina en «+»;
- espacio duro entre VaR o CVaR y su nivel (CVaR 5 %), y en «COP por USD»;
- espacio duro a ambos lados de = cuando lo que sigue es corto (año = 252 días, \\(d\\) = 3,97 %, β = 1,
  periódica = nominal/4), así ningún renglón termina en «=» ni empieza con él;
- «a» en vez de raya en un rango de dinero que abre «de» o «desde» (de USD 50.001 a 250.000, como pide la RAE), con
  espacio duro entre la «a» y la cifra: el renglón ya no termina en «50.001–»;
- espacio duro en EE. UU., p. ej., s. d., 9:30 a. m. y S&P 500, y antes de la raya de un rango con espacios
  (352,83 – 542,07), o a ambos lados si los extremos son rótulos cortos (P5 – P95);
- signo menos (−) en vez del guion delante de una cifra, salvo pegado a letras o cifras (COVID-19, 2015-2026,
  2026-07-15);
- comillas tipográficas “ ” y ‘ ’, y apóstrofo ’;
- «vs» como «vs.»;
- fechas (14-oct-2026, oct-2027, 30-jul, 31 de agosto), rangos cortos con raya sin espacios (7–10, P5–P95,
  11,0 %–11,5 %) o con «a» (3 a 5) dentro de <span class="nw">, que no se parten al final del renglón, y lo mismo las
  siglas compuestas con guion (SET-ICAP, 10-K, E-mini). El signo que abre justo antes («(», «“») y el que cierra justo
  después, con su puntuación («),», «.»), entran en el mismo span: Chrome sí parte en el borde de un span nowrap, y sin
  esto el «)» abría renglón;
- el paréntesis, corchete o comilla que abre justo antes de una fórmula en línea va en el mismo <span class="nw"> que
  ella (con el cierre y la puntuación que la siguen): la fórmula no se parte (.katex es nowrap) y, sin esto, el «(»
  quedaba solo al final del renglón. Los delimitadores quedan dentro del span, donde auto-render los sigue hallando.

Las reglas leen el texto corrido de cada bloque, así que «<b>9,2</b> %» también cuenta, y no cruzan de un párrafo,
una celda o un renglón (<br>) al siguiente.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from collections.abc import Callable

NBSP = "\N{NO-BREAK SPACE}"
MINUS = "\N{MINUS SIGN}"
NBHYPHEN = "\N{NON-BREAKING HYPHEN}"
NW_OPEN, NW_CLOSE = '<span class="nw">', "</span>"

# Contenido que no se toca. Los botones y las opciones de las vistas alternativas se comparan, por su texto, con las
# etiquetas del menú guardadas en la especificación JSON de cada gráfica.
_OPAQUE = "script|style|textarea|title|pre|code|kbd|samp|svg|math|button|option|select|template"
# Etiquetas en línea: no cortan el texto corrido.
_INLINE = {"a", "abbr", "b", "bdi", "bdo", "cite", "data", "del", "dfn", "em", "i", "ins", "label", "mark", "q", "s",
           "small", "span", "strong", "sub", "sup", "time", "u", "var", "wbr"}
_TOKEN = re.compile(
    rf"<!--.*?-->"                                  # comentario
    rf"|<({_OPAQUE})\b[^>]*(?<!/)>.*?</\1\s*>"      # bloque opaco completo
    rf"|</?([a-zA-Z][\w-]*)\b[^>]*>"                # etiqueta
    rf"|<![^>]*>",                                  # doctype
    re.S | re.I,
)
_ENTITIES = {"&nbsp;": NBSP, "&#160;": NBSP, "&#xa0;": NBSP, "&quot;": '"', "&#34;": '"', "&#x22;": '"',
             "&#39;": "'", "&#x27;": "'", "&apos;": "'"}
_ENTITY = re.compile("|".join(map(re.escape, _ENTITIES)), re.I)
_BREAK = "\x00"  # marca de borde de bloque en el texto corrido
_MATH = re.compile(r"\$\$.*?\$\$|\\\(.*?\\\)|\\\[.*?\\\]", re.S)

_WS = r"[ \t\r\n]+"
_OPENERS = set(" \t\r\n" + NBSP + _BREAK + "([{¿¡“‘«—–-/")


def _double_quote(text: str, i: int) -> str:
    return "“" if i == 0 or text[i - 1] in _OPENERS else "”"


def _single_quote(text: str, i: int) -> str:
    prev = text[i - 1] if i else _BREAK
    nxt = text[i + 1] if i + 1 < len(text) else _BREAK
    if prev in _OPENERS and not nxt.isspace() and nxt != _BREAK:
        return "‘"
    return "’"  # cierre o apóstrofo (Moody’s, Sam’s Club)


# Lo que va a la derecha de un = que no se separa de él: una palabra o cifra corta, con su moneda si la lleva.
_EQ_RHS = rf"(?:(?:USD|COP|EUR)[ {NBSP}])?[^\s{NBSP}{_BREAK}]{{1,12}}(?=[\s{NBSP}{_BREAK}]|$)"

# (patrón, grupo que se reemplaza, reemplazo); el reemplazo puede depender del texto y de la posición.
_Sub = tuple[re.Pattern[str], int, str | Callable[[str, int], str]]
_SUBS: list[_Sub] = [
    (re.compile(rf"(?<=\d)({_WS})(?=%|‰|(?:pp|pb|σ|M|MM|millones|billones)(?!\w))"), 1, NBSP),
    (re.compile(rf"(?<![\w$])(?:USD|COP|EUR)({_WS})(?=[\d+\-{MINUS}]|(?:M|MM|millones)(?!\w))"), 1, NBSP),
    # la tasa no se separa de su unidad: «9,84 % E.A.», «9,50 % N.T.V.», «+31,1 % a/a»
    (re.compile(rf"(?<=%)({_WS})(?=(?:E\.A\.|N\.[AMTS]\.(?:[AV]\.)?|[AMTS]\.[AV]\.|[am]/[am])(?!\w))"), 1, NBSP),
    # plazos y cantidades contadas: «10 años», «12 meses», «52 sem.», «8,3 pesos», «24 cuotas», «67,75 puntos»,
    # «4,3 veces»; y «año 6», «años 7–10»
    (re.compile(rf"(?<=\d)({_WS})(?=(?:años?|mes(?:es)?|días?|sem\.|pesos|dólares|cuotas|puntos?|pts\.?|veces)(?!\w))"),
     1, NBSP),
    (re.compile(rf"(?<![\w.])(?:años?|mes(?:es)?|días?)({_WS})(?=\d)"), 1, NBSP),
    # «8,66 % → 0,13 %»: el par antes → después va junto
    (re.compile(rf"(?<=[\d%])({_WS})(?=→{_WS}[+\-{MINUS}]?\d)"), 1, NBSP),
    (re.compile(rf"(?<=[\d%])[ \t\r\n{NBSP}]+→({_WS})(?=[+\-{MINUS}]?\d)"), 1, NBSP),
    # «USD 10,63 M → USD 6,14 M»: la flecha va con la cifra que sigue (el renglón parte antes de ella, si hace falta)
    (re.compile(rf"(?<=[\d%M])[ \t\r\n{NBSP}]+→({_WS})(?=(?:USD|COP|EUR)[ \t\r\n{NBSP}]+[+\-{MINUS}]?\d)"), 1, NBSP),
    # «vs.» no cierra el renglón si lo que sigue es una cifra o una palabra de una o dos letras («normal vs. t»,
    # «7,50 % vs. 3,40 %»)
    (re.compile(rf"\bvs\.?({_WS})(?=[+\-{MINUS}]?\d|[^\W\d_]{{1,2}}(?!\w))"), 1, NBSP),
    # un «+» entre espacios no cierra el renglón: va con lo que suma («Prime + 6,0 pp», «3 % + tasa real»)
    (re.compile(rf"(?<=[ \t\r\n{NBSP}]\+)({_WS})(?=[^\s{NBSP}{_BREAK}])"), 1, NBSP),
    # el nivel de confianza va con la medida («CVaR 5 %», «VaR 95 %»; ver _VAR_LEVEL) y la unidad del tipo de cambio,
    # entera
    (_VAR_LEVEL := re.compile(rf"\bC?VaR({_WS})(?=\d)"), 1, NBSP),
    (re.compile(rf"\bCOP({_WS})(?=por[ \t\r\n{NBSP}]+USD\b)"), 1, NBSP),
    (re.compile(rf"(?<=\bCOP[ {NBSP}]por)({_WS})(?=USD\b)"), 1, NBSP),
    # «año = 252 días», «\(d\) = 3,97 %», «periódica = nominal/4», «÷ 3.197,65 = USD 112.582,68»: el = no cierra
    # ni abre renglón cuando lo que sigue es corto (hasta 12 caracteres, o una cifra con su moneda)
    (re.compile(rf"(?<=\S)({_WS})(?==[ \t\r\n{NBSP}]+{_EQ_RHS})"), 1, NBSP),
    (re.compile(rf"(?<=\S[ \t\r\n{NBSP}]=)({_WS})(?={_EQ_RHS})"), 1, NBSP),
    (re.compile(rf"\bEE\.({_WS})UU\."), 1, NBSP),
    (re.compile(rf"\bp\.({_WS})ej\."), 1, NBSP),
    (re.compile(rf"\bs\.({_WS})d\."), 1, NBSP),
    (re.compile(rf"(?<=\d)({_WS})(?=[ap]\.\s?m\.)"), 1, NBSP),
    (re.compile(rf"\b[ap]\.({_WS})m\."), 1, NBSP),
    # «500(?!\d)» y no «500\b»: junto a una etiqueta en línea el texto corrido sigue sin espacio («500Inversión»)
    (re.compile(rf"\bS&(?:amp;)?P({_WS})500(?!\d)"), 1, NBSP),
    # «préstamos de USD 50.001–250.000» → «de USD 50.001 a 250.000»: el rango que abre «de» o «desde» se cierra con
    # «a» (RAE), no con raya, y así el renglón tampoco termina en «50.001–» (una cifra con miles no cabe entera en
    # las columnas angostas del celular). Solo con la moneda delante, donde el «de» siempre abre el rango (en «el
    # totazo de 2014–2016», no). La «a» va con la cifra que sigue.
    (_DE_RANGE := re.compile(rf"\b(?:de|desde)[ \t\r\n{NBSP}]+(?:USD|COP|EUR)[ \t\r\n{NBSP}]+[+\-{MINUS}]?\d[\d.,]*"
                             rf"(–)(?=[+\-{MINUS}]?\d)"), 1, f" a{NBSP}"),
    (re.compile(rf"(?<=[\d%])({_WS})–(?=[ \t\r\n])"), 1, NBSP),
    # entre rótulos cortos («P5 – P95») el rango entero va junto
    (re.compile(rf"(?<![\w.,])[A-Za-z]{{0,2}}\d{{1,3}}[ {NBSP}]–({_WS})[A-Za-z]{{0,2}}\d{{1,3}}(?![\w.,])"), 1, NBSP),
    (re.compile(rf"(?<![\w.,/\-{NBHYPHEN}{MINUS}])(-)(?=\d)"), 1, MINUS),
    (re.compile(r"\bvs()(?![.\w])"), 1, "."),
    (re.compile(r'"'), 0, _double_quote),
    (re.compile(r"'"), 0, _single_quote),
]

# Reglas que no se aplican dentro de un encabezado de tabla: ahí la columna es angosta y «CVaR» sobre «95 %» se lee
# bien; pegados, ensanchaban la columna y partían en tres renglones a sus vecinas.
_NOT_IN_TH = {_VAR_LEVEL}

_MES = r"(?i:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"
_MESES = r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
_SP = rf"[ \t\r\n{NBSP}]+"
_TOK = r"[^\W_](?:[\w.,]*[^\W_])?"  # palabra o cifra, con puntos y comas internos
_UNIT = rf"(?:[ {NBSP}](?:%|pp|pb)(?!\w))?"
# (patrón, largo máximo). Un rango largo con raya («50.001–250.000») sí puede partirse después de ella: pegado
# ensancharía las columnas angostas de las tablas en el celular (el que abre «de USD» ya lleva «a», ver _DE_RANGE).
_WRAPS = [
    (re.compile(rf"(?<![\w\-{MINUS}])(?:\d{{1,2}}-{_MES}(?:-\d{{4}})?|{_MES}-\d{{4}})(?![\w\-])"), 11),
    # «31 de agosto», «17 de septiembre» (el año, si sigue, sí puede pasar al renglón siguiente)
    (re.compile(rf"(?<![\w.,])\d{{1,2}}{_SP}de{_SP}{_MESES}(?!\w)"), 16),
    # rangos cortos con «a»: «3 a 5», «7 a 10» (no «SBA 504 a 10» ni «2016 a 2026»)
    (re.compile(rf"(?<![\w.,\-{MINUS}])\d{{1,2}}{_SP}a{_SP}\d{{1,2}}(?![\w.,])"), 7),
    (re.compile(rf"(?<![\w.,\-{MINUS}]){_TOK}{_UNIT}–{_TOK}{_UNIT}(?!\w)"), 13),
    # siglas compuestas con guion («SET-ICAP»): el renglón no se parte después del guion (ante una cifra, como en
    # «COVID-19», el navegador ya no parte)
    (re.compile(r"(?<![\w\-])[A-Z]{2,6}-[A-Z]{2,6}(?![\w\-])"), 13),
    # y las de cifra o letra suelta con guion: «Form 8-K», «10-K», «E-mini», «T-bills»
    (re.compile(r"(?<![\w\-])(?:\d{1,2}-[A-Z]|[A-Z]-[a-z]{3,})(?![\w\-])"), 7),
]
# Lo que abre pegado antes de un envuelto y lo que lo cierra pegado después (con su puntuación) entra en el span.
_WRAP_OPEN = set("([{“«¿¡\"")
_WRAP_CLOSE = re.compile(r"[)\]}”»\"]*[,.;:!?…]?")


# «(\(\Delta t = 21/252\))», «“\(x\)”,»: lo que abre pegado a una fórmula en línea, la fórmula y lo que la cierra.
_MATH_WRAP = re.compile(rf"[(\[“«\"]\\\((?:(?!\\\))[^{_BREAK}])+\\\)[)\]”»\"]?[,.;:]?")


def _split(html: str) -> list[tuple[bool, str]]:
    """Parte el HTML en trozos (es_texto, contenido)."""
    out, pos = [], 0
    for m in _TOKEN.finditer(html):
        if m.start() > pos:
            out.append((True, html[pos:m.start()]))
        out.append((False, m.group(0)))
        pos = m.end()
    if pos < len(html):
        out.append((True, html[pos:]))
    return out


def _flow_piece(chunk: str) -> str:
    """Lo que aporta una etiqueta al texto corrido: nada si es en línea o un comentario, un borde si no."""
    if chunk.startswith("<!--"):
        return ""
    m = re.match(r"</?([a-zA-Z][\w-]*)", chunk)
    return "" if m and m.group(1).lower() in _INLINE else _BREAK


def polish(html: str) -> str:
    chunks = [(t, _ENTITY.sub(lambda m: _ENTITIES[m.group(0).lower()], c) if t else c) for t, c in _split(html)]
    flow, starts, idx = [], [], []  # texto corrido; inicio en él y posición en chunks de cada trozo de texto
    in_th: set[int] = set()  # trozos de texto dentro de un <th>
    n, th = 0, 0
    for k, (is_text, c) in enumerate(chunks):
        piece = c if is_text else _flow_piece(c)
        if is_text:
            if th:
                in_th.add(len(starts))
            starts.append(n)
            idx.append(k)
        elif re.match(r"<th\b", c, re.I):
            th += 1
        elif re.match(r"</th\s*>", c, re.I):
            th = max(th - 1, 0)
        flow.append(piece)
        n += len(piece)
    text = "".join(flow)
    math = [(m.start(), m.end()) for m in _MATH.finditer(text)]
    math_starts = [a for a, _ in math]

    def in_math(a: int, b: int) -> bool:
        """¿[a, b) toca una fórmula? (una inserción, a = b, cuenta si cae dentro o justo antes)."""
        j = bisect_right(math_starts, max(a, b - 1)) - 1
        return j >= 0 and math[j][1] > a

    def owner(a: int, b: int) -> int | None:
        """Trozo de texto que contiene por completo [a, b), o None."""
        j = bisect_right(starts, a) - 1
        if j < 0 or b > starts[j] + len(chunks[idx[j]][1]):
            return None
        return j

    edits: dict[int, list[tuple[int, int, int, str]]] = {}
    taken: set[int] = set()
    de_range: set[int] = set()  # rayas que pasaron a «a»: ese rango ya no se envuelve entero

    def add(a: int, b: int, rep: str, prio: int = 0, j: int | None = None) -> None:
        j = owner(a, b) if j is None else j
        if j is None:
            return
        edits.setdefault(j, []).append((a - starts[j], b - starts[j], prio, rep))

    for pat, grp, rep in _SUBS:
        for m in pat.finditer(text):
            a, b = m.span(grp)
            # Dueño: el trozo que contiene todo el hallazgo (así el punto de «vs.» queda junto a «vs»), o al menos el
            # que contiene lo que se reemplaza.
            j = owner(*m.span())
            j = owner(a, b) if j is None else j
            if (j is None or in_math(*m.span()) or any(p in taken for p in range(a, b))
                    or (pat in _NOT_IN_TH and j in in_th)):
                continue
            taken.update(range(a, b))
            if pat is _DE_RANGE:
                de_range.add(a)
            add(a, b, rep(text, a) if callable(rep) else rep, j=j)

    wrapped: list[tuple[int, int]] = []
    for m in _MATH_WRAP.finditer(text):
        a, b = m.span()
        j = owner(a, b)
        if j is None or in_math(a, a + 1):
            continue
        wrapped.append((a, b))
        add(a, a, NW_OPEN, 1, j)
        add(b, b, NW_CLOSE, 0, j)
    for pat, longest in _WRAPS:
        for m in pat.finditer(text):
            a, b = m.span()
            if b - a > longest or in_math(a, b) or any(a <= p < b for p in de_range):
                continue
            a2 = a - 1 if a and text[a - 1] in _WRAP_OPEN else a
            b2 = _WRAP_CLOSE.match(text, b).end()
            for x0, y0 in ((a2, b2), (a, b2), (a2, b), (a, b)):
                j = owner(x0, y0)
                if j is not None and not in_math(x0, y0) and not any(x0 < y and x < y0 for x, y in wrapped):
                    break
            else:
                continue
            wrapped.append((x0, y0))
            add(x0, x0, NW_OPEN, 1, j)
            add(y0, y0, NW_CLOSE, 0, j)

    out = [c for _, c in chunks]
    for j, eds in edits.items():
        s = out[idx[j]]
        for a, b, _, rep in sorted(eds, reverse=True):
            s = s[:a] + rep + s[b:]
        out[idx[j]] = s
    return "".join(out)
