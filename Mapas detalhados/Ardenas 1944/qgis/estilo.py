# estilo.py — a paleta e os simbolos das Ardenas.
#
# Irmao do estilo.py do Pearl Harbor, e de proposito: as pecas (sombra, sobre,
# dd, sorteia, veste) sao as mesmas, ja provadas. O que muda e a PAISAGEM.
#
# La o mapa era agua com uma base no meio, e o trabalho era a costa. Aqui nao ha
# costa nenhuma: a terra e o quadro inteiro, e o que desenha o mapa e o TALHAO —
# a colcha de campos, a mata fechada, a sebe entre um campo e outro, a aldeia.
#
# TUDO EM MILIMETROS DE TELA, como no outro: e o que mantem o desenho com a
# mesma cara em qualquer zoom. O dpi do render define a escala das texturas.
import os
from qgis.core import (Qgis, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol, QgsSingleSymbolRenderer,
                       QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSimpleMarkerSymbolLayer,
                       QgsLinePatternFillSymbolLayer, QgsPointPatternFillSymbolLayer,
                       QgsMarkerLineSymbolLayer, QgsRasterFillSymbolLayer,
                       QgsShapeburstFillSymbolLayer, QgsDropShadowEffect, QgsEffectStack,
                       QgsDrawSourceEffect, QgsProperty, QgsExpression, QgsSymbolLayer,
                       QgsUnitTypes, QgsSvgMarkerSymbolLayer, QgsSVGFillSymbolLayer,
                       QgsCentroidFillSymbolLayer, QgsRuleBasedRenderer)
from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor
import textura as T

# ============================================================== PALETA
FUNDO      = '#96a259'   # o chao que aparece onde nao ha talhao mapeado
AGUA       = '#5d94a8'
MATA       = '#4e6b31'   # a mata fechada
COPA       = '#3d5725'
COPA_SOMBRA= '#2b3f19'
VIA        = '#a8a298'
VIA_ORLA   = '#867f75'
FERRO      = '#6b655c'
SEBE       = '#3f5a26'   # a sebe: quase mata, em linha
SOMBRA_SEC = '#2a2f24'
PAPEL      = '#f3efe1'

# O campo aberto nao e um verde so. Cada uso ganha a sua familia de tons, e
# dentro da familia cada talhao sorteia o seu. E essa colcha que faz a paisagem —
# sem ela o mapa vira um tapete verde chapado.
CAMPO = {
    'prado':   ['#9fae5e', '#a7b566', '#98a657', '#a2b162', '#9aa85a'],
    'lavoura': ['#c2b077', '#b9a76d', '#c8b881', '#bda971', '#c5b47b'],
    'grama':   ['#93a054', '#9aa65c', '#8d9a4e'],
    'pomar':   ['#7f9448', '#86994f'],
}
MATAS = {
    'mata':     ['#4e6b31', '#496429', '#536f36'],
    'moita':    ['#6a7c3e', '#718443'],
    'charneca': ['#8a8a52', '#93925a'],
}
URBANO = {
    'casario':   ['#c6b79a', '#c1b193'],
    'comercio':  ['#bdb08f'],
    'industria': ['#aaa494'],
    'fazenda':   ['#c9b992'],
    'cemiterio': ['#9aa46e'],
    'militar':   ['#a5a47e'],
    'pedreira':  ['#b9b2a4'],
    'obra':      ['#b5aa93'],
}
# Telhado das Ardenas: ardosia escura na maioria, telha vermelha em alguns.
TELHADOS = ['#565b5f', '#61666a', '#4c5154', '#6b7074',
            '#7d4c3f', '#5a5f63', '#8a5a48', '#52575a']

# --- escalas das texturas, em milimetros de tela -----------------------------
ESC_CAMPO  = 150.0
ESC_MATA   = 140.0
ESC_URBANO = 64.0
ESC_AGUA   = 150.0
ESC_PAPEL  = 60.0

MM = QgsUnitTypes.RenderMillimeters

def _mm(o, *setters):
    for s in setters:
        if hasattr(o, s): getattr(o, s)(MM)
    return o

def _modo_tela():
    """VIEWPORT poe todas as camadas na MESMA malha; em Feature cada feicao
    ancora o ladrilho no proprio retangulo e aparece emenda onde duas se tocam."""
    for dono, nome in ((Qgis, 'SymbolCoordinateReference'), (QgsRasterFillSymbolLayer, None)):
        alvo = getattr(dono, nome) if nome else dono
        if hasattr(alvo, 'Viewport'): return alvo.Viewport
    return 1
MODO_TELA = _modo_tela()

# ============================================================== PECAS
def sombra(dist=0.9, blur=2.4, cor=SOMBRA_SEC, op=0.45, ang=135):
    """Sombra projetada + o proprio desenho. Sem o DrawSource no fim sai so a sombra."""
    e = QgsDropShadowEffect()
    e.setOffsetDistance(dist); _mm(e, 'setOffsetUnit')
    e.setBlurLevel(blur); _mm(e, 'setBlurUnit')
    e.setOffsetAngle(int(round(ang)))        # so aceita int
    e.setColor(QColor(cor)); e.setOpacity(op)
    st = QgsEffectStack(); st.appendEffect(e); st.appendEffect(QgsDrawSourceEffect())
    return st

def simples(cor, borda=None, larg=0.2):
    sl = QgsSimpleFillSymbolLayer(QColor(cor))
    sl.setStrokeStyle(0 if not borda else 1)
    if borda:
        sl.setStrokeColor(QColor(borda)); sl.setStrokeWidth(larg); _mm(sl, 'setStrokeWidthUnit')
    return sl

def sobre(png, escala):
    """Ladrilho de sobrepor. Caminho inexistente pinta PRETO OPACO; vazio nao pinta nada."""
    r = QgsRasterFillSymbolLayer(png if (png and os.path.exists(png)) else '')
    r.setWidth(escala)
    if hasattr(r, 'setOutputUnit'): r.setOutputUnit(MM)
    else: _mm(r, 'setSizeUnit')
    r.setCoordinateMode(MODO_TELA)
    return r

def dd(camada, chave, expr):
    """Valida antes de aplicar: expressao quebrada e aceita em silencio e o QGIS
    desenha o valor estatico, entao o erro so apareceria no mapa."""
    e = QgsExpression(expr)
    if e.hasParserError():
        raise ValueError('expressao invalida %r: %s' % (expr, e.parserErrorString().strip()))
    camada.setDataDefinedProperty(chave, QgsProperty.fromExpression(expr))
    return camada

def sorteia(n, desvio=0):
    """Inteiro 0..n-1 por feicao, estavel entre renders. Tem que ser o rand() de
    TRES argumentos: sem semente ele re-sorteia a cada render e o mapa pisca."""
    return 'rand(0, {m}, ($id) + {d})'.format(m=n - 1, d=desvio)

def _lista(cores):
    return "array('" + "','".join(cores) + "')"

def paleta_por_tipo(familias, campo='t', padrao=None, desvio=0):
    """
    A cor sai do TIPO do talhao, e dentro do tipo sorteia.

    Monta um CASE: cada familia vira um ramo, e o ramo tira uma cor da sua lista
    pelo rand() semeado no id. E o que produz a colcha — dois prados vizinhos
    quase nunca caem no mesmo tom.
    """
    ramos = []
    for tipo, cores in familias.items():
        ramos.append("WHEN \"{c}\" = '{t}' THEN array_get({a}, {s})".format(
            c=campo, t=tipo, a=_lista(cores), s=sorteia(len(cores), desvio)))
    fim = list(familias.values())[0] if padrao is None else padrao
    return 'CASE ' + ' '.join(ramos) + " ELSE array_get({a}, {s}) END".format(
        a=_lista(fim), s=sorteia(len(fim), desvio))

def veste(layer, *camadas, efeito=None, por_feicao=False):
    """
    O efeito vai no RENDERIZADOR, nao na camada de simbolo: na camada ele roda uma
    vez por feicao, e em milhares de predios isso custa uma ordem de grandeza a mais.
    """
    s = QgsFillSymbol(); s.deleteSymbolLayer(0)
    for c in camadas: s.appendSymbolLayer(c)
    r = QgsSingleSymbolRenderer(s)
    if efeito is not None:
        if por_feicao: camadas[0].setPaintEffect(efeito)
        else: r.setPaintEffect(efeito)
    layer.setRenderer(r); return layer

# ============================================================== O CHAO
def chao(pasta):
    """O fundo do quadro: onde nao ha talhao mapeado, ainda ha terra."""
    return [simples(FUNDO),
            sobre(T.mancha(pasta, 'chao', base=5, oitavas=5, contraste=0.85,
                           forca=0.30, grao=0.30), ESC_CAMPO)]

def campo(pasta):
    """A colcha de talhoes: cor por tipo, tom sorteado dentro do tipo, e a mancha
    de textura por cima para nenhum ficar chapado."""
    f = simples(CAMPO['prado'][0])
    dd(f, QgsSymbolLayer.Property.FillColor, paleta_por_tipo(CAMPO, padrao=CAMPO['prado']))
    return [f, sobre(T.mancha(pasta, 'campo', base=5, oitavas=5, contraste=0.85,
                              forca=0.26, grao=0.28, semente=3311), ESC_CAMPO)]

def urbano(pasta):
    """A mancha construida da aldeia: o chao batido em volta das casas."""
    f = simples(URBANO['casario'][0])
    dd(f, QgsSymbolLayer.Property.FillColor,
       paleta_por_tipo(URBANO, padrao=URBANO['casario'], desvio=4177))
    chapa = sobre(T.apron(pasta, 'urbano'), T.ESC_PATIO)
    chapa.setAngle(12.0)                     # tira o alinhamento das juntas com a tela
    return [f, chapa]

# Como a arvore e desenhada. Trocar aqui muda SO a arvore; o chao da mata e o
# mesmo nos tres, para a comparacao ser honesta.
#   nenhuma  so a chapa e a mancha, sem arvore alguma
#   circulo  os discos chapados
#   png      a copa em imagem com alfa: silhueta irregular, volume e giro
ARVORE = 'png'

def mata(pasta, modo=None):
    """
    A mata. As arvores moram em arvores.py; o import e aqui dentro porque
    arvores.py importa a paleta deste modulo, e no topo seria um ciclo.

    A chapa de baixo ganha cor por TIPO depois de montada: mata fechada, moita e
    charneca vem todas no mesmo 'mata.geojson', e sem isso a charneca ficaria
    verde-escura de floresta.
    """
    import arvores
    cams = arvores.mata_modo(pasta, modo or ARVORE)
    dd(cams[0], QgsSymbolLayer.Property.FillColor,
       paleta_por_tipo(MATAS, padrao=MATAS['mata'], desvio=911))
    return cams

def agua(pasta):
    return [simples(AGUA),
            sobre(T.mancha(pasta, 'agua', base=10, oitavas=5, contraste=0.55,
                           forca=0.15), ESC_AGUA)]

def papel(pasta):
    return [sobre(T.grao(pasta, 'papel', forca=0.07), ESC_PAPEL)]

# ============================================================== AS LINHAS
LARG_ORLA   = (0.95, 0.74, 0.54, 0.38)
LARG_NUCLEO = (0.62, 0.48, 0.32, 0.20)

def _por_classe(vals):
    return 'array_get(array({v}), coalesce("c", 4) - 1)'.format(v=', '.join(str(v) for v in vals))

def via(layer):
    """Espessura pela classe do OSM. Numa grossura so, as 1822 vias da aldeia
    viravam um novelo."""
    orla = QgsSimpleLineSymbolLayer(QColor(VIA_ORLA)); orla.setWidth(LARG_ORLA[0])
    nucleo = QgsSimpleLineSymbolLayer(QColor(VIA)); nucleo.setWidth(LARG_NUCLEO[0])
    dd(orla, QgsSymbolLayer.Property.StrokeWidth, _por_classe(LARG_ORLA))
    dd(nucleo, QgsSymbolLayer.Property.StrokeWidth, _por_classe(LARG_NUCLEO))
    s = QgsLineSymbol(); s.deleteSymbolLayer(0)
    for c in (orla, nucleo):
        c.setPenCapStyle(1); c.setPenJoinStyle(1); _mm(c, 'setWidthUnit'); s.appendSymbolLayer(c)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer

def rio(layer):
    c = QgsSimpleLineSymbolLayer(QColor(AGUA)); c.setWidth(0.5)
    c.setPenCapStyle(1); c.setPenJoinStyle(1); _mm(c, 'setWidthUnit')
    s = QgsLineSymbol(); s.changeSymbolLayer(0, c)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer

def ferro(layer):
    base = QgsSimpleLineSymbolLayer(QColor(FERRO)); base.setWidth(0.55)
    _mm(base, 'setWidthUnit')
    s = QgsLineSymbol(); s.changeSymbolLayer(0, base)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer

def sebe(layer):
    """
    A sebe: a linha de arbustos entre um talhao e outro.

    Nao e um traco — e uma fila de copas. Um traco escuro por baixo fecha os vaos
    e uma linha de marcadores por cima faz o volume. E o detalhe que diz "bocage"
    em vez de "divisa administrativa".
    """
    corpo = QgsSimpleLineSymbolLayer(QColor(SEBE)); corpo.setWidth(1.1)
    corpo.setPenCapStyle(1); corpo.setPenJoinStyle(1); _mm(corpo, 'setWidthUnit')
    s = QgsLineSymbol(); s.changeSymbolLayer(0, corpo)

    m = QgsSimpleMarkerSymbolLayer()
    m.setColor(QColor(COPA)); m.setStrokeStyle(0); m.setSize(1.5); _mm(m, 'setSizeUnit')
    ms = QgsMarkerSymbol(); ms.changeSymbolLayer(0, m)
    fila = QgsMarkerLineSymbolLayer()
    fila.setInterval(1.2); _mm(fila, 'setIntervalUnit')
    fila.setSubSymbol(ms)
    s.appendSymbolLayer(fila)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer

# ============================================================== OS TELHADOS
CORTE_TELHADO = 8000     # denominador de escala; acima disso, so a nervura

TELHADO_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="240" height="100" viewBox="0 0 240 100">
  <rect x="0" y="0" width="240" height="100" fill="param(fill) #565b5f"/>
  <rect x="0" y="0"  width="240" height="49" fill="#ffffff" fill-opacity="0.11"/>
  <rect x="0" y="51" width="240" height="49" fill="#000000" fill-opacity="0.15"/>
  <polygon points="0,0 26,50 0,100"      fill="#000000" fill-opacity="0.10"/>
  <polygon points="240,0 214,50 240,100" fill="#000000" fill-opacity="0.10"/>
  <rect x="0" y="48.5" width="240" height="3" fill="param(outline) #23271f" fill-opacity="0.50"/>
  <rect x="0" y="0"  width="240" height="3" fill="#ffffff" fill-opacity="0.22"/>
  <rect x="0" y="93" width="240" height="7" fill="#000000" fill-opacity="0.30"/>
</svg>
'''
NERVURA_SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <rect x="0" y="0"  width="24" height="3"   fill="param(outline) #000000" fill-opacity="0.34"/>
  <rect x="0" y="12" width="24" height="1.5" fill="param(outline) #000000" fill-opacity="0.16"/>
</svg>
'''
# 'rumo' e o azimute do eixo longo, horario a partir do norte. O angulo do
# marcador e do preenchimento SVG e o rumo do TOPO do desenho (-y); o eixo longo
# do desenho e +x, 90 graus adiante. CUIDADO: o QgsLinePatternFillSymbolLayer usa
# a convencao CONTRARIA e quer 90 - "rumo".
ANGULO_SVG = '"rumo" - 90'

def grava_svg(pasta, nome, texto):
    """O SVG tem que ser ARQUIVO: string crua vira URL e o QGIS desenha a
    nuvenzinha de download; caminho inexistente desenha um '?'."""
    destino = os.path.join(pasta, 'svg')
    os.makedirs(destino, exist_ok=True)
    caminho = os.path.join(destino, nome + '.svg')
    if not os.path.exists(caminho) or open(caminho, encoding='utf-8').read() != texto:
        with open(caminho, 'w', encoding='utf-8') as f: f.write(texto)
    return caminho

def _marcador(caminho_svg, cor, folga=1.05, escolha=None):
    """
    Width e Height por feicao, SEPARADOS: e o que deixa um celeiro 4x1 ser 4x1.

    'escolha' e uma expressao que devolve o CAMINHO do SVG, e e ela que faz a
    biblioteca funcionar: cada predio recebe o telhado da sua classe em vez de um
    telhado so esticado para todas as formas. Tem que ir em Property.Name —
    Property.File existe, aparece como "Symbol file path", e e um no-op silencioso.

    setClipPoints e obrigatorio, senao o retangulo do telhado vaza por cima do
    vizinho; e pointOnSurface, porque o centroide de um L cai fora do L.
    """
    m = QgsSvgMarkerSymbolLayer(caminho_svg)
    m.setSizeUnit(QgsUnitTypes.RenderMapUnits); m.setSize(30); m.setStrokeWidth(0)
    P = QgsSymbolLayer.Property
    dd(m, P.Width,  '"comp" * {0:g}'.format(folga))
    dd(m, P.Height, '"larg" * {0:g}'.format(folga))
    dd(m, P.Angle,  ANGULO_SVG)
    dd(m, P.FillColor, cor)
    if escolha: dd(m, P.Name, escolha)
    ms = QgsMarkerSymbol(); ms.deleteSymbolLayer(0); ms.appendSymbolLayer(m)
    cf = QgsCentroidFillSymbolLayer(); cf.setSubSymbol(ms)
    cf.setPointOnSurface(True); cf.setPointOnAllParts(False); cf.setClipPoints(True)
    return cf

def _nervura(caminho_svg, larg_mm=1.1):
    sl = QgsSVGFillSymbolLayer(caminho_svg)
    sl.setPatternWidth(larg_mm); _mm(sl, 'setPatternWidthUnit')
    dd(sl, QgsSymbolLayer.Property.Angle, ANGULO_SVG)
    return sl

def telhados(layer, pasta, corte=CORTE_TELHADO):
    """
    Telhado desenhado de perto, nervura de longe, cor propria por predio nos dois.

    A divisao nao e hesitacao: o marcador cobra pelos predios QUE ESTAO NA TELA, e
    no quadro inteiro o predio tem uns poucos pixels, onde cumeeira e beiral somem
    de qualquer jeito.
    """
    import telhado as TL
    cor = "array_get({a}, {s})".format(a=_lista(TELHADOS), s=sorteia(len(TELHADOS)))
    biblio = TL.grava(pasta, grava_svg)          # casa, celeiro, galpao, anexo, bloco
    escolha = TL.escolhe(biblio)                 # a expressao que decide qual
    svg_t = biblio['casa']                       # o de fabrica, se a expressao falhar
    svg_n = grava_svg(pasta, 'nervura', NERVURA_SVG)

    def monta(*camadas):
        s = QgsFillSymbol(); s.deleteSymbolLayer(0)
        chapado = simples(TELHADOS[0])
        dd(chapado, QgsSymbolLayer.Property.FillColor, cor)
        s.appendSymbolLayer(chapado)
        for c in camadas: s.appendSymbolLayer(c)
        return s

    # Os nomes sao ao contrario do que parecem, porque o numero e o DENOMINADOR:
    # 'minimumScale' e o limite mais afastado. E nao existe setScaleMinDenom na Rule.
    raiz = QgsRuleBasedRenderer.Rule(None)
    for sim, aproximado, afastado, nome in (
            (monta(_marcador(svg_t, cor, escolha=escolha)), 0, corte, 'perto'),
            (monta(_nervura(svg_n)), corte, 0, 'longe')):
        r = QgsRuleBasedRenderer.Rule(sim)
        r.setLabel(nome); r.setMaximumScale(aproximado); r.setMinimumScale(afastado)
        raiz.appendChild(r)
    rend = QgsRuleBasedRenderer(raiz)
    rend.setPaintEffect(sombra(1.15, 0.5, SOMBRA_SEC, 0.6, 135))
    layer.setRenderer(rend)
    return layer
