# estilo.py — a paleta e os simbolos do mapa, num lugar so.
#
# pearl.py e provas.py importam daqui, entao mexer numa cor ou numa medida muda
# o mapa e as provas de uma vez. Nao ha estilo escrito em outro lugar.
#
# Toda medida de textura esta em MILIMETROS, nao em metros: a trama da agua, a
# praia e as copas tem tamanho constante na tela, como num desenho. Se fossem em
# metros elas sumiriam ao afastar e virariam manchas gigantes ao aproximar.
import os, math
from qgis.core import (QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol, QgsSingleSymbolRenderer,
                       QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSimpleMarkerSymbolLayer,
                       QgsLinePatternFillSymbolLayer, QgsPointPatternFillSymbolLayer,
                       QgsRasterFillSymbolLayer, QgsShapeburstFillSymbolLayer,
                       QgsDropShadowEffect, QgsEffectStack, QgsDrawSourceEffect, QgsUnitTypes)
from qgis.PyQt.QtGui import QColor, QImage

# ============================================================== PALETA
MAR        = '#2b8492'   # o corpo da agua
MAR_CLARO  = '#3fa0ad'   # o alto da mancha / a listra
MAR_FUNDO  = '#1f6f7c'   # o baixo da mancha
ESPUMA     = '#7fc6ce'   # os floquinhos de crista
RASO       = '#57aab3'   # o halo de agua rasa encostando na costa
TERRA      = '#8d9a4e'   # o oliva do terreno
AREIA      = '#cdc08d'   # a praia
MATA       = '#6f8340'
COPA       = '#5b6f33'   # as copas salpicadas na mata
BASE       = '#c3b283'   # o bege da area construida (nao e a terra!)
PISTA      = '#6d6146'
CAIS       = '#a89c82'
VIA        = '#9b968c'
VIA_ORLA   = '#7f7a71'
PREDIO     = '#7b7062'
SOMBRA     = '#1b5a63'   # a sombra da terra cai na agua: escura e teal
PAPEL      = '#f3efe1'

MAR_ESTILO = 'mancha'    # liso | lona | mancha | mancha-listra | mancha-espuma
MAR_LADRILHO_MM = 150.0  # o lado do ladrilho na tela: grande, senao a repeticao aparece

MM = QgsUnitTypes.RenderMillimeters

def _mm(o, *setters):
    for s in setters:
        if hasattr(o, s): getattr(o, s)(MM)
    return o

# ==================================================== O RUIDO DA AGUA
# A mancha do Operations Room nao tem direcao: e variacao irregular de tom, como
# lona ou aguada. Nenhum padrao de linhas ou de pontos faz isso — so ruido. Entao
# geramos um ladrilho e o usamos como preenchimento raster.
#
# O ruido precisa EMENDAR consigo mesmo, ou cada repeticao mostra a costura. Por
# isso e ruido de valor sobre uma grade PERIODICA: a oitava de periodo n toma o
# indice modulo n, entao o pixel do fim do ladrilho interpola de volta para o do
# comeco. Nao ha borda. As oitavas dobram de frequencia e caem pela metade em
# amplitude (fBm), que e o que da o aspecto de nuvem em vez de bolha regular.

def _grade(n, semente):
    """Uma grade n x n de valores em [0,1), sempre a mesma para a mesma semente."""
    v, s = [], (semente * 2654435761 + 1013904223) & 0x7fffffff
    for _ in range(n * n):
        s = (s * 1103515245 + 12345) & 0x7fffffff
        v.append(s / 2147483647.0)
    return v

def _suave(t):
    return t * t * (3.0 - 2.0 * t)          # hermite: derivada zero nas bordas

def _valor(x, y, n, g):
    xi, yi = int(x) % n, int(y) % n
    xf, yf = x - math.floor(x), y - math.floor(y)
    x1, y1 = (xi + 1) % n, (yi + 1) % n     # o modulo e o que fecha a emenda
    u, v = _suave(xf), _suave(yf)
    a, b = g[yi * n + xi], g[yi * n + x1]
    c, d = g[y1 * n + xi], g[y1 * n + x1]
    return (a + (b - a) * u) * (1 - v) + (c + (d - c) * u) * v

def _fbm(px, py, lado, base, oitavas, grades):
    val, amp, soma = 0.0, 1.0, 0.0
    for k in range(oitavas):
        n = base << k
        val += amp * _valor(px / lado * n, py / lado * n, n, grades[k])
        soma += amp
        amp *= 0.5
    return val / soma

def _cor(c1, c2, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    a, b = QColor(c1), QColor(c2)
    return QColor(int(a.red()   + (b.red()   - a.red())   * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue()  + (b.blue()  - a.blue())  * t))

def ladrilho(pasta, receita, lado=512, base=8, oitavas=5, semente=1941,
             contraste=1.0, listra=0.0, espuma=0.0):
    """
    Escreve (e guarda) um PNG emendavel com a mancha da agua.

    contraste  quanto a mancha se afasta do tom medio
    listra     amplitude de uma ondulacao horizontal somada por cima; o periodo
               divide o lado do ladrilho, senao a listra nao emenda
    espuma     fracao de pixels de crista, tirada de uma oitava bem fina
    """
    destino = os.path.join(pasta, 'texturas')
    os.makedirs(destino, exist_ok=True)
    caminho = os.path.join(destino, receita + '.png')
    if os.path.exists(caminho):
        return caminho

    grades = [_grade(base << k, semente + k * 977) for k in range(oitavas)]
    fina = _grade(base << (oitavas + 1), semente + 7717)
    nf = base << (oitavas + 1)
    img = QImage(lado, lado, QImage.Format_RGB32)
    ciclos = 16                               # listras por ladrilho: inteiro, senao a emenda aparece
    for y in range(lado):
        onda = listra * math.sin(2.0 * math.pi * ciclos * y / lado)
        for x in range(lado):
            t = (_fbm(x, y, lado, base, oitavas, grades) - 0.5) * contraste + 0.5 + onda
            c = _cor(MAR_FUNDO, MAR_CLARO, t)
            if espuma > 0.0 and _valor(x / lado * nf, y / lado * nf, nf, fina) > 1.0 - espuma:
                c = QColor(ESPUMA)
            img.setPixel(x, y, c.rgb())
    img.save(caminho)
    return caminho

# ============================================================== SIMBOLOS
def sombra(dist=0.9, blur=2.4, cor=SOMBRA, op=0.45, ang=135):
    """Sombra projetada + o proprio desenho, nessa ordem."""
    e = QgsDropShadowEffect()
    e.setOffsetDistance(dist); _mm(e, 'setOffsetUnit')
    try: e.setBlurLevel(blur)
    except TypeError: e.setBlurLevel(int(round(blur)))
    _mm(e, 'setBlurUnit')
    e.setOffsetAngle(ang); e.setColor(QColor(cor)); e.setOpacity(op)
    st = QgsEffectStack(); st.appendEffect(e); st.appendEffect(QgsDrawSourceEffect())
    return st

def simples(cor, borda=None, larg=0.2):
    sl = QgsSimpleFillSymbolLayer(QColor(cor))
    sl.setStrokeStyle(0 if not borda else 1)
    if borda:
        sl.setStrokeColor(QColor(borda)); sl.setStrokeWidth(larg); _mm(sl, 'setStrokeWidthUnit')
    return sl

def veste(layer, *camadas, efeito=None):
    """Monta um QgsFillSymbol com as camadas dadas, de baixo para cima."""
    s = QgsFillSymbol(); s.deleteSymbolLayer(0)
    for c in camadas: s.appendSymbolLayer(c)
    # o efeito mora na camada de simbolo, nao no simbolo: vai na primeira, o corpo
    if efeito is not None: camadas[0].setPaintEffect(efeito)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer

def _listras():
    """A lona: uma listra clara horizontal e uma contra-listra fraca."""
    a = QgsLinePatternFillSymbolLayer()
    a.setLineAngle(0); a.setDistance(1.6); a.setLineWidth(0.62)
    a.setColor(QColor(MAR_CLARO)); _mm(a, 'setDistanceUnit', 'setLineWidthUnit')
    b = QgsLinePatternFillSymbolLayer()
    b.setLineAngle(90); b.setDistance(3.2); b.setLineWidth(0.22)
    b.setColor(QColor(MAR_FUNDO)); _mm(b, 'setDistanceUnit', 'setLineWidthUnit')
    try: b.setOpacity(0.35)
    except AttributeError: pass
    return [a, b]

RECEITAS = {                       # contraste, listra, espuma
    'mancha':        (0.45, 0.00, 0.000),
    'mancha-listra': (0.34, 0.09, 0.000),
    'mancha-espuma': (0.45, 0.00, 0.005),
}

def agua(pasta, estilo=None):
    """As camadas de simbolo do mar, conforme a receita escolhida."""
    estilo = estilo or MAR_ESTILO
    cam = [simples(MAR)]                       # o corpo, que aparece se o PNG faltar
    if estilo == 'liso':
        return cam
    if estilo == 'lona':
        return cam + _listras()
    contraste, listra, espuma = RECEITAS[estilo]
    png = ladrilho(pasta, estilo, contraste=contraste, listra=listra, espuma=espuma)
    r = QgsRasterFillSymbolLayer(png)
    r.setWidth(MAR_LADRILHO_MM); _mm(r, 'setWidthUnit')
    return cam + [r]

def costa_areia():
    """
    A praia. Duas camadas: um fundo de areia que transborda a costa por um traco
    largo (entao a areia aparece dos dois lados da linha d'agua), e por cima o
    shapeburst, que leva a areia ao oliva no primeiro tanto de tela adentro.
    """
    praia = QgsSimpleFillSymbolLayer(QColor(AREIA))
    praia.setStrokeStyle(1); praia.setStrokeColor(QColor(AREIA))
    praia.setStrokeWidth(2.0); _mm(praia, 'setStrokeWidthUnit')
    sb = QgsShapeburstFillSymbolLayer()
    sb.setColor(QColor(AREIA)); sb.setColor2(QColor(TERRA))
    sb.setUseWholeShape(False); sb.setMaxDistance(4.5); _mm(sb, 'setDistanceUnit')
    sb.setBlurRadius(4)
    return [praia, sb]

def halo_raso():
    """A agua rasa encostando na costa: a propria terra, engordada por um traco."""
    sl = QgsSimpleFillSymbolLayer(QColor(RASO))
    sl.setStrokeStyle(1); sl.setStrokeColor(QColor(RASO))
    sl.setStrokeWidth(5.0); _mm(sl, 'setStrokeWidthUnit')
    return sl

def copas():
    """As copas salpicadas: um padrao de pontos, desencontrado linha a linha."""
    m = QgsSimpleMarkerSymbolLayer()
    m.setColor(QColor(COPA)); m.setStrokeStyle(0); m.setSize(1.05); _mm(m, 'setSizeUnit')
    ms = QgsMarkerSymbol(); ms.changeSymbolLayer(0, m)
    pp = QgsPointPatternFillSymbolLayer()
    pp.setDistanceX(1.9); pp.setDistanceY(1.9); pp.setDisplacementX(0.95)
    _mm(pp, 'setDistanceXUnit', 'setDistanceYUnit', 'setDisplacementXUnit')
    for s in ('setRandomDeviationX', 'setRandomDeviationY'):
        if hasattr(pp, s):
            getattr(pp, s)(0.5); _mm(pp, s + 'Unit')
    pp.setSubSymbol(ms)
    return pp

def via_dupla(layer):
    orla = QgsSimpleLineSymbolLayer(QColor(VIA_ORLA)); orla.setWidth(0.62)
    nucleo = QgsSimpleLineSymbolLayer(QColor(VIA)); nucleo.setWidth(0.38)
    s = QgsLineSymbol(); s.deleteSymbolLayer(0)
    for c in (orla, nucleo):
        c.setPenCapStyle(1); c.setPenJoinStyle(1); _mm(c, 'setWidthUnit'); s.appendSymbolLayer(c)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer
