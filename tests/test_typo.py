from derivados.report.fmt import num, pb, pct, texnum
from derivados.report.typo import MINUS, NBSP, polish

NW = '<span class="nw">'


def test_fmt_usa_signo_menos_y_texnum_lo_devuelve_a_guion():
    assert num(-1234.5, 1) == f"{MINUS}1.234,5"
    assert num(-0.0001, 2) == "0,00"
    assert pct(-0.046, 1) == f"{MINUS}4,6{NBSP}%"
    assert pb(-25) == f"{MINUS}25{NBSP}pb"
    assert texnum(num(-1234.5, 2)) == "-1.234{,}50"


def test_espacio_duro_antes_de_unidades_y_despues_de_la_moneda():
    out = polish("<p>servicios: <b>9,2</b> %), 25 pb, 0,5 pp, USD 8.138, COP -5 y (COP M) en EE. UU.</p>")
    assert f"<b>9,2</b>{NBSP}%" in out
    assert f"25{NBSP}pb" in out and f"0,5{NBSP}pp" in out
    assert f"USD{NBSP}8.138" in out and f"COP{NBSP}{MINUS}5" in out and f"(COP{NBSP}M)" in out
    assert f"EE.{NBSP}UU." in out
    assert polish("<td>a las 9:30 a. m. ET</td>") == f"<td>a las 9:30{NBSP}a.{NBSP}m. ET</td>"
    assert NBSP * 2 not in polish(f"<p>9,2{NBSP}% y 9,2&nbsp;%</p>")


def test_signo_menos_sin_falsos_positivos():
    out = polish("<td>-4,6 %</td><td>2026-07-15</td><td>2015-2026</td><td>COVID-19</td><td>t-1</td><td>BB-</td>")
    assert f"<td>{MINUS}4,6{NBSP}%</td>" in out
    for keep in ("2026-07-15", "2015-2026", "COVID-19", "t-1", "BB-"):
        assert f"<td>{keep}</td>" in out


def test_comillas_tipograficas():
    out = polish("<p>vamos \"largos\", 'Cierre de mercado' y Moody&#x27;s &quot;deuda&quot;</p>")
    assert "“largos”" in out and "‘Cierre de mercado’" in out and "Moody’s" in out and "“deuda”" in out


def test_fechas_y_rangos_no_se_parten():
    out = polish("<p>el 14-oct-2026, TRM oct-2027 (cierre 30-jul), años 7–10, P5–P95 y 11,0 %–11,5 %.</p>")
    # la puntuación que cierra pegada a la fecha o al rango va dentro del span (Chrome parte en su borde)
    assert f"{NW}14-oct-2026,</span>" in out and f"{NW}oct-2027</span>" in out and f"{NW}30-jul),</span>" in out
    assert f"{NW}7–10,</span>" in out and f"{NW}P5–P95</span> y" in out
    assert f"{NW}11,0{NBSP}%–11,5{NBSP}%.</span>" in out
    assert polish("<td>earnings (21-may-2026), 10-Q</td>") == (
        f"<td>earnings {NW}(21-may-2026),</span> {NW}10-Q</span></td>")
    assert polish("<td>(<b>21-may-2026</b>);</td>") == f"<td>(<b>{NW}21-may-2026</span></b>);</td>"
    assert "nw" not in polish("<p>2026-07-15 y 2015-2026</p>")
    assert "nw" not in polish("<td>USD 50.001–250.000</td>")  # un rango largo sí puede partirse tras la raya
    assert polish("<td>P5 – P95</td>") == f"<td>P5{NBSP}–{NBSP}P95</td>"
    assert polish("<td>Mercado spot SET-ICAP FX</td>") == f"<td>Mercado spot {NW}SET-ICAP</span> FX</td>"


def test_rango_de_dinero_con_de_lleva_a_y_no_raya():
    # «de USD 50.001–250.000» partía en «50.001–» / «250.000»: con «a» (RAE) el renglón parte antes de la «a»
    out = polish("<td>préstamos de USD 50.001–250.000 (Prime + 6,0 pp)</td>")
    assert out == f"<td>préstamos de USD{NBSP}50.001 a{NBSP}250.000 (Prime +{NBSP}6,0{NBSP}pp)</td>"
    # el rango corto deja de ir envuelto: ya no tiene raya que proteger
    out = polish("<li>ingresos de USD 89.850–90.950 millones y UPA desde USD 2,75–2,85.</li>")
    assert out == (f"<li>ingresos de USD{NBSP}89.850 a{NBSP}90.950{NBSP}millones y UPA desde USD{NBSP}2,75 a{NBSP}"
                   "2,85.</li>")
    # sin moneda el «de» no siempre abre el rango («el totazo de 2014–2016»), y la fórmula no se toca
    assert polish("<p>el totazo de 2014–2016</p>") == f"<p>el totazo de {NW}2014–2016</span></p>"
    assert polish("<p>\\( de USD 1.000–2.000 \\)</p>") == "<p>\\( de USD 1.000–2.000 \\)</p>"


def test_no_toca_codigo_atributos_botones_ni_katex():
    src = ('<script type="application/json">{"t": "5 % -3 14-oct-2026 \\"x\\""}</script>'
           '<style>.a::after{content:"5 %"}</style>'
           '<a href="/x-1" title="P5–P95 5 %">enlace</a>'
           '<button data-dim="0">Tasa -1 pp</button><select><option>5 %</option></select>'
           '<p>\\( x = -1 \\) y $$ a - 2 "q" 14-oct-2026 $$ y \\[ 5 % \\]</p>')
    assert polish(src) == src


def test_vs_con_punto():
    assert polish("<small>TES 10A vs UST 10A, vs. otro</small>") == "<small>TES 10A vs. UST 10A, vs. otro</small>"


def test_unidad_de_la_tasa_pegada_al_porcentaje():
    out = polish("<p>idéntico al de dólares (9,84 % E.A.), <b>13,93 %</b> E.A., 9,50 % N.T.V., 7,5 % N.A.V., "
                 "2 % T.V. y +31,1 % a/a.</p>")
    for s in ("9,84{0}%{0}E.A.", "<b>13,93{0}%</b>{0}E.A.", "9,50{0}%{0}N.T.V.", "7,5{0}%{0}N.A.V.", "2{0}%{0}T.V.",
              "31,1{0}%{0}a/a."):
        assert s.format(NBSP) in out
    # solo tras %: ni después de una palabra ni ante otra sigla
    assert polish("<p>en efectivo anual (E.A.) y 5 % EE. UU.</p>") == f"<p>en efectivo anual (E.A.) y 5{NBSP}% EE.{NBSP}UU.</p>"
    assert polish("<p>el 9 % Ea. y 9 % E.Ab</p>") == f"<p>el 9{NBSP}% Ea. y 9{NBSP}% E.Ab</p>"


def test_plazos_no_se_separan_de_su_cifra():
    out = polish("<td>TES nov-2027 vs. Tesoro EE. UU. 1 año</td><td>(años 7–10) y años 2 a 10</td>"
                 "<p>a 10 años, 12 meses, 1 mes, 252 días, 52 sem. y el cierre del año 6</p>")
    assert f"1{NBSP}año</td>" in out
    assert f"(años{NBSP}{NW}7–10)</span>" in out and f"años{NBSP}{NW}2 a 10</span>" in out
    for s in ("10{0}años", "12{0}meses", "1{0}mes", "252{0}días", "52{0}sem.", "año{0}6"):
        assert s.format(NBSP) in out
    # no une palabras que solo empiezan igual, ni cifras que no son plazos
    out = polish("<p>3 mesas, 5 añoso, 2 díasx, 4 semanas, mesa 3, el 7 de agosto y añosa 4</p>")
    assert NBSP not in out


def test_flecha_entre_cifras_y_vs_ante_palabra_corta():
    out = polish("<div>sobrecosto &gt; 10 %: 8,66 % → 0,13 %</div><td>77,1 → −75,6</td>")
    assert f"8,66{NBSP}%{NBSP}→{NBSP}0,13{NBSP}%" in out
    assert f"77,1{NBSP}→{NBSP}{MINUS}75,6" in out
    # la flecha entre palabras sigue partiendo donde haga falta
    assert polish("<td>Fin año 6 → fin año 7</td><th>Pacto → vencimiento</th>") == (
        f"<td>Fin año{NBSP}6 → fin año{NBSP}7</td><th>Pacto → vencimiento</th>")
    out = polish("<p>¿Y normal vs. t? Normal vs t de Student, vs. EE. UU., vs. UST 10A y vs. 3,40 %</p>")
    assert f"normal vs.{NBSP}t?" in out and f"Normal vs.{NBSP}t de" in out and f"vs.{NBSP}EE.{NBSP}UU." in out
    assert "vs. UST" in out and f"vs.{NBSP}3,40" in out


def test_reglas_nuevas_no_dejan_espacios_duros_dobles():
    src = (f"<p>9,84{NBSP}% E.A., 9,84&nbsp;%&nbsp;E.A., años&nbsp;7–10, 8,66{NBSP}%{NBSP}→ 0,13 %, "
           f"vs.{NBSP}t y 10{NBSP}años</p>")
    out = polish(src)
    assert NBSP * 2 not in out and "&nbsp;" not in out
    assert NBSP * 2 not in polish(out)  # pasar dos veces tampoco los duplica


def test_igual_ante_cifra_no_cierra_ni_abre_renglon():
    out = polish("<p>mes = 21 días, año = 252 días, con \\(d\\) = 3,97 %, β = 1 y β residual = -0,0065</p>"
                 "<td>3.197,65 = <b>USD 112.582,68</b></td>")
    for s in ("mes{0}={0}21{0}días", "año{0}={0}252{0}días", "\\(d\\){0}={0}3,97{0}%", "β{0}={0}1 y",
              "residual{0}={0}" + MINUS + "0,0065", "3.197,65{0}={0}<b>USD{0}112.582,68</b>"):
        assert s.format(NBSP) in out
    # también ante una palabra corta; ante una larga sí puede partir, y dentro de una fórmula no se toca
    out = polish("<td>tasa periódica = nominal/4</td><p>petróleo caro = peso fuerte (y = x) y X = Superintendencia</p>")
    for s in ("periódica{0}={0}nominal/4</td>", "caro{0}={0}peso fuerte", "(y{0}={0}x)", "X = Superintendencia"):
        assert s.format(NBSP) in out
    assert polish("<p>a \\(n = 252\\) días</p>") == "<p>a \\(n = 252\\) días</p>"


def test_parentesis_pegado_a_la_formula_en_linea():
    out = polish("<p>mes = 21 días (\\(\\Delta t = 21/252\\)), trimestre y (\\(\\nu\\) = 2,09) o “\\(x\\)”.</p>")
    assert f"{NW}(\\(\\Delta t = 21/252\\)),</span> trimestre" in out
    assert f"{NW}(\\(\\nu\\)</span>{NBSP}={NBSP}2,09)" in out
    assert f"{NW}“\\(x\\)”.</span>" in out
    # sin nada que abra justo antes, la fórmula queda como estaba; dentro de $$ $$ tampoco se envuelve
    assert polish("<p>con \\(n = 40\\): y $$ f(\\(x\\)) $$</p>") == "<p>con \\(n = 40\\): y $$ f(\\(x\\)) $$</p>"


def test_cantidades_contadas_y_medidas_no_se_separan_de_su_cifra():
    out = polish("<p>se abarata 8,3 pesos, (24 cuotas), 16 cuotas por USD, USD 5 dólares, 67,75 puntos, 7.316,15 pts. "
                 "y 4,3 veces; el CVaR 5 % y el VaR 95 % van en COP por USD.</p>")
    for s in ("8,3{0}pesos,", "(24{0}cuotas)", "16{0}cuotas por", "5{0}dólares", "67,75{0}puntos", "7.316,15{0}pts.",
              "4,3{0}veces", "CVaR{0}5{0}%", "VaR{0}95{0}%", "COP{0}por{0}USD."):
        assert s.format(NBSP) in out
    # en un encabezado de tabla «CVaR» puede ir sobre «95 %» (la columna es angosta)
    assert polish("<th>CVaR 95 %</th><td>CVaR 95 %</td>") == f"<th>CVaR 95{NBSP}%</th><td>CVaR{NBSP}95{NBSP}%</td>"
    # sin cifra delante, o dentro de una fórmula, nada cambia
    assert polish("<p>los pesos, las cuotas y \\(\\text{VaR} 5\\)</p>") == "<p>los pesos, las cuotas y \\(\\text{VaR} 5\\)</p>"
    assert polish("<p>pesos colombianos (COP) por cada USD</p>") == "<p>pesos colombianos (COP) por cada USD</p>"


def test_operador_suma_y_flecha_ante_moneda_no_cierran_renglon():
    out = polish("<td>USD 50.001–250.000 (Prime + 6,0 pp)</td><p>(meta de 3 % + tasa real de ~2,5 % + unos 2 pp)</p>")
    for s in ("(Prime +{0}6,0{0}pp)", "3{0}% +{0}tasa", "2,5{0}% +{0}unos"):
        assert s.format(NBSP) in out
    assert polish("<p>+5 y a+b</p>") == "<p>+5 y a+b</p>"  # sin espacios alrededor no es la suma del texto
    out = polish("<div>USD 10,63 M → USD 6,14 M</div><td>Pacto → USD 5</td>")
    assert f"USD{NBSP}10,63{NBSP}M →{NBSP}USD{NBSP}6,14{NBSP}M" in out  # parte antes de la flecha, no después
    assert "Pacto → USD" in out


def test_fechas_en_palabras_rangos_con_a_y_siglas_con_guion():
    out = polish("<p>el roll del 31 de agosto. La descripción de \"3 a 5 años\", años 7 a 10 y SBA 504 a 10 años; "
                 "2016 a 2026, 1,5 a 2 y el 26 de octubre de 2026.</p>")
    assert f"del {NW}31 de agosto.</span> La" in out
    assert f"de {NW}“3 a 5</span>{NBSP}años”" in out and f"años{NBSP}{NW}7 a 10</span> y" in out
    assert f"{NW}26 de octubre</span> de 2026." in out
    assert "504 a 10" in out and "2016 a 2026" in out and "1,5 a 2" in out
    out = polish("<td>(Form 8-K), segment (10-K) y futuros E-mini: T-bills, COVID-19 y SET-ICAP</td>")
    for s in ("(Form {0}8-K),</span>", "segment {0}(10-K)</span>", "futuros {0}E-mini:</span>", "{0}T-bills,</span>",
              "y {0}SET-ICAP</span></td>"):
        assert s.format(NW) in out
    assert "COVID-19" in out and f"{NW}COVID" not in out


def test_sp500_junto_a_una_etiqueta():
    out = polish("<span>Ficha · <b>E-mini S&amp;P 500</b></span><span>Inversión</span>")
    assert f"S&amp;P{NBSP}500</b>" in out
