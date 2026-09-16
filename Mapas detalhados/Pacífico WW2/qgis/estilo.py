# estilo.py — a paleta e os simbolos do mapa, num lugar so.
#
# pearl.py e provas.py importam daqui, entao mexer numa cor ou numa medida muda
# o mapa e as provas de uma vez. Nao ha estilo escrito em outro lugar.
#
# COMO CADA CAMADA E MONTADA
# Sempre do mesmo jeito: uma base opaca (cor chapada, ou um degrade) e, por
# cima, um ladrilho de SOBREPOR vindo do textura.py. O ladrilho nao pinta — ele
# so empurra o que ja estava ali para mais claro ou mais escuro. E por isso que
# o mesmo arquivo de grama serve sobre o oliva do terreno e sobre a areia da
# praia sem virar duas texturas diferentes.
#
# TUDO EM MILIMETROS DE TELA
# A trama da agua, a praia, as copas e a espessura das vias estao em milimetros,
# nao em metros. E o que mantem o desenho com a mesma cara em qualquer zoom,
# como numa ilustracao. Em metros a trama sumiria ao afastar e viraria mancha
# gigante ao aproximar. A conta disso e que o dpi do render define a escala das
# texturas: o pearl.py fixa 96.
import os
from qgis.core import (Qgis, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol, QgsSingleSymbolRenderer,
                       QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSimpleMarkerSymbolLayer,
                       QgsLinePatternFillSymbolLayer, QgsPointPatternFillSymbolLayer,
                       QgsRasterFillSymbolLayer, QgsShapeburstFillSymbolLayer,
                       QgsDropShadowEffect, QgsEffectStack, QgsDrawSourceEffect,
                       QgsProperty, QgsExpression, QgsSymbolLayer, QgsUnitTypes)
from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor
import textura as T

# ============================================================== PALETA
# Tirada das referencias do Operations Room, nao do gosto do QGIS.
MAR        = '#2b8492'   # o corpo da agua
RASO       = '#57aab3'   # a agua rasa encostando na costa
AREIA      = '#cdc08d'   # a praia
TERRA      = '#93a054'   # o oliva do terreno aberto
MATA       = '#5f7a38'   # a mata, mais escura e mais fria
COPA       = '#46602c'   # as copas salpicadas por cima da mata
COPA_SOMBRA= '#33461f'   # a sombrinha debaixo de cada copa
BASE       = '#c2af93'   # o concreto do patio da base (NAO e a terra)
PISTA      = '#5e5535'   # o campo de pouso, terra batida escura
CAIS       = '#a89c82'
VIA        = '#9b968c'
VIA_ORLA   = '#7f7a71'
SOMBRA     = '#1b5a63'   # a sombra da terra cai na agua: escura e teal
SOMBRA_SEC = '#2a2f24'   # a sombra de predio cai no chao: escura e neutra
PAPEL      = '#f3efe1'   # a moldura de papel rasgado

# Telhados. A referencia nao tem um cinza so: ha telha escura, chapa clara,
# verde militar e uns poucos galpoes de telhado vermelho.
TELHADOS   = ['#5b6154', '#6e7268', '#4d5949', '#646a5c',
              '#565b50', '#727a6c', '#6b4a40', '#5f665a']

MAR_ESTILO = 'mancha'    # liso | lona | mancha | mancha-espuma

# --- escalas das texturas, em milimetros de tela -----------------------------
# Regra de bolso: quanto maior o ladrilho, menos a repeticao se denuncia, mas
# menos textura cabe na tela. A agua precisa do maior porque e a maior area
# continua do mapa.
ESC_AGUA   = 150.0
ESC_GRAMA  = 90.0
ESC_MATA   = 54.0
ESC_LAJE   = 46.0
ESC_ROCADA = 70.0
ESC_CAIS   = 22.0
ESC_PAPEL  = 60.0

MM = QgsUnitTypes.RenderMillimeters

def _mm(o, *setters):
    for s in setters:
        if hasattr(o, s): getattr(o, s)(MM)
    return o

# O modo de coordenada do preenchimento raster. VIEWPORT poe todas as camadas na
# MESMA malha: sem isso cada feicao ancora o ladrilho no seu proprio retangulo, e
# aparece emenda onde dois poligonos se tocam — e o mar, sendo maior que a tela,
# ainda escorrega por baixo do mapa quando se navega.
def _modo_tela():
    for dono, nome in ((Qgis, 'SymbolCoordinateReference'), (QgsRasterFillSymbolLayer, None)):
        alvo = getattr(dono, nome) if nome else dono
        if hasattr(alvo, 'Viewport'):
            return alvo.Viewport
    return 1
MODO_TELA = _modo_tela()

# ============================================================== PECAS
def sombra(dist=0.9, blur=2.4, cor=SOMBRA, op=0.45, ang=135):
    """
    Sombra projetada + o proprio desenho, nessa ordem.

    O angulo e rumo de bussola medido da tela para cima, no sentido horario:
    0 e para cima, 90 para a direita, 135 para BAIXO E A DIREITA. E a pilha
    precisa do QgsDrawSourceEffect no fim, senao sai so a sombra e o desenho
    original some.
    """
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
    """
    Um ladrilho de sobrepor, medido em milimetros de tela.

    Caminho inexistente NAO e inofensivo: o preenchimento raster pinta PRETO
    OPACO por cima de tudo que estiver embaixo. Caminho vazio, sim, e o
    sentinela seguro — nao pinta nada e a base aparece.
    """
    r = QgsRasterFillSymbolLayer(png if (png and os.path.exists(png)) else '')
    r.setWidth(escala)
    if hasattr(r, 'setOutputUnit'): r.setOutputUnit(MM)   # setWidthUnit esta obsoleto
    else: _mm(r, 'setSizeUnit')
    r.setCoordinateMode(MODO_TELA)
    return r

def dd(camada, chave, expr):
    """
    Liga uma propriedade de simbolo a uma expressao, por feicao.

    A expressao e validada antes: o QGIS aceita expressao quebrada em silencio
    absoluto e desenha o valor estatico, entao o erro so apareceria no mapa, se
    aparecesse.
    """
    e = QgsExpression(expr)
    if e.hasParserError():
        raise ValueError('expressao invalida %r: %s' % (expr, e.parserErrorString().strip()))
    camada.setDataDefinedProperty(chave, QgsProperty.fromExpression(expr))
    return camada

def sorteia(n, semente='$id', desvio=0):
    """
    Um inteiro 0..n-1 por feicao, estavel entre renders.

    Tem que ser o rand() de TRES argumentos: sem a semente ele re-sorteia a cada
    render e o mapa pisca. E nao adianta usar hash multiplicativo — ($id*K) % n
    e estritamente periodico e sai listrado no mapa.

    'desvio' descorrelaciona dois usos da mesma feicao (cor e angulo, digamos).
    """
    return 'rand(0, {m}, ($id) + {d})'.format(m=n - 1, d=desvio)

def veste(layer, *camadas, efeito=None, por_feicao=False):
    """
    Monta um QgsFillSymbol com as camadas dadas, de baixo para cima.

    O efeito vai no RENDERIZADOR, nao na camada de simbolo. Nao e detalhe: no
    simbolo ele roda uma vez por feicao, e nos 5533 predios isso mediu 3,93 s
    contra 0,14 s sem efeito. No renderizador a camada inteira e desenhada uma
    vez e o efeito passa por cima — 0,38 s. Cento e duas vezes mais rapido, e o
    desenho fica ate melhor: a sombra sai da silhueta do conjunto em vez de cada
    predio jogar sombra em cima do vizinho.
    """
    s = QgsFillSymbol(); s.deleteSymbolLayer(0)
    for c in camadas: s.appendSymbolLayer(c)
    r = QgsSingleSymbolRenderer(s)
    if efeito is not None:
        if por_feicao: camadas[0].setPaintEffect(efeito)
        else: r.setPaintEffect(efeito)
    layer.setRenderer(r); return layer

# ============================================================== A AGUA
def _listras():
    """A lona: uma listra clara horizontal e uma contra-listra fraca."""
    a = QgsLinePatternFillSymbolLayer()
    a.setLineAngle(0); a.setDistance(1.6); a.setLineWidth(0.62)
    a.setColor(QColor('#3fa0ad')); _mm(a, 'setDistanceUnit', 'setLineWidthUnit')
    b = QgsLinePatternFillSymbolLayer()
    b.setLineAngle(90); b.setDistance(3.2); b.setLineWidth(0.22)
    b.setColor(QColor('#1f6f7c')); _mm(b, 'setDistanceUnit', 'setLineWidthUnit')
    try: b.setOpacity(0.35)
    except AttributeError: pass
    return [a, b]

def agua(pasta, estilo=None, raso_mm=0.0):
    """
    O mar.

    Se raso_mm > 0 a base deixa de ser cor chapada e vira um shapeburst: a agua
    tem a terra como furos, e o shapeburst mede a distancia ate a borda MAIS
    PROXIMA — que ali e a linha de costa. Sai um degrade de raso saindo de cada
    praia, em vez da faixa de largura fixa que havia antes.

    So vale enquanto raso_mm for menor que 10% da extensao desenhada: o QGIS
    corta a geometria de preenchimento na extensao inflada em exatamente 10%, e
    essa borda cortada tambem brilha. No mapa inteiro sobra folga; num recorte
    bem fechado, nao.
    """
    if raso_mm > 0:
        sb = QgsShapeburstFillSymbolLayer()
        sb.setColor(QColor(RASO)); sb.setColor2(QColor(MAR))
        sb.setUseWholeShape(False); sb.setMaxDistance(raso_mm); _mm(sb, 'setDistanceUnit')
        sb.setBlurRadius(3)
        sb.setIgnoreRings(False)             # ligado, as ilhas somem do calculo
        corpo = [sb]
    else:
        corpo = [simples(MAR)]
    estilo = estilo or MAR_ESTILO
    if estilo == 'liso':
        return corpo
    if estilo == 'lona':
        return corpo + _listras()
    png = T.mancha(pasta, 'agua', base=10, oitavas=5, contraste=0.55, forca=0.15,
                   espuma=(0.005 if estilo == 'mancha-espuma' else 0.0))
    return corpo + [sobre(png, ESC_AGUA)]

def halo_raso():
    """A agua rasa como faixa de largura fixa. So para quem nao usa o shapeburst."""
    sl = QgsSimpleFillSymbolLayer(QColor(RASO))
    sl.setStrokeStyle(1); sl.setStrokeColor(QColor(RASO))
    sl.setStrokeWidth(5.0); _mm(sl, 'setStrokeWidthUnit')
    return sl

# ============================================================== O CHAO
def terreno(pasta):
    """
    A terra, em tres camadas.

    1. a praia: areia que transborda a costa por um traco largo, entao aparece
       dos dois lados da linha da agua;
    2. o shapeburst, que leva a areia ao oliva no primeiro tanto de tela adentro;
    3. a mancha da grama por cima, que e o que tira o chapado.
    """
    praia = QgsSimpleFillSymbolLayer(QColor(AREIA))
    praia.setStrokeStyle(1); praia.setStrokeColor(QColor(AREIA))
    praia.setStrokeWidth(2.0); _mm(praia, 'setStrokeWidthUnit')
    sb = QgsShapeburstFillSymbolLayer()
    sb.setColor(QColor(AREIA)); sb.setColor2(QColor(TERRA))
    sb.setUseWholeShape(False); sb.setMaxDistance(4.5); _mm(sb, 'setDistanceUnit')
    sb.setBlurRadius(4)                      # so aceita int
    grama = sobre(T.mancha(pasta, 'grama', base=5, oitavas=5, contraste=0.85,
                           forca=0.34, grao=0.30), ESC_GRAMA)
    return [praia, sb, grama]

def patio(pasta):
    """O concreto do patio: placas com junta, cada uma com o seu tom."""
    return [simples(BASE), sobre(T.laje(pasta, 'laje'), ESC_LAJE)]

def campo(pasta):
    """O campo de pouso: o xadrez de quem cortou a grama em faixas."""
    return [simples(PISTA), sobre(T.rocada(pasta, 'rocada'), ESC_ROCADA)]

def cais(pasta):
    """Pier e doca: concreto tambem, mas em placa miuda e com a borda marcada."""
    return [simples(CAIS, '#8a7f68', 0.12),
            sobre(T.laje(pasta, 'cais', placas=4, variacao=0.26, junta=0.30), ESC_CAIS)]

def mata(pasta):
    """
    A mata: verde mais frio, manchado, e as copas salpicadas por cima.

    Duas correcoes importantes aqui. O setter do jitter chama-se
    setMaximumRandomDeviationX — setRandomDeviationX nao existe, e como estava
    atras de um hasattr as copas vinham numa grade perfeita sem ninguem notar. E
    a semente de fabrica e 0, que significa "re-sorteia a cada render": sem
    setSeed a mata muda de desenho a cada repintura.

    A sombrinha de cada copa e outra camada de marcador deslocada, e nao um
    efeito de sombra: efeito por marcador sairia caro em centenas de milhares de
    arvores.
    """
    sombrinha = QgsSimpleMarkerSymbolLayer()
    sombrinha.setColor(QColor(COPA_SOMBRA)); sombrinha.setStrokeStyle(0)
    sombrinha.setSize(1.6); _mm(sombrinha, 'setSizeUnit')
    sombrinha.setOffset(QPointF(0.28, 0.28)); _mm(sombrinha, 'setOffsetUnit')
    copa = QgsSimpleMarkerSymbolLayer()
    copa.setColor(QColor(COPA)); copa.setStrokeStyle(0)
    copa.setSize(1.5); _mm(copa, 'setSizeUnit')

    ms = QgsMarkerSymbol(); ms.deleteSymbolLayer(0)
    ms.appendSymbolLayer(sombrinha); ms.appendSymbolLayer(copa)
    # tamanho proprio por copa, preso a celula da grade para nao piscar
    dd(copa, QgsSymbolLayer.Property.Size,
       'randf(1.15, 1.85, @symbol_marker_row * 1000 + @symbol_marker_column)')
    dd(sombrinha, QgsSymbolLayer.Property.Size,
       'randf(1.25, 1.95, @symbol_marker_row * 1000 + @symbol_marker_column)')

    pp = QgsPointPatternFillSymbolLayer()
    pp.setDistanceX(2.3); pp.setDistanceY(2.3); pp.setDisplacementX(1.15)
    _mm(pp, 'setDistanceXUnit', 'setDistanceYUnit', 'setDisplacementXUnit')
    pp.setMaximumRandomDeviationX(0.7); pp.setMaximumRandomDeviationY(0.7)
    _mm(pp, 'setRandomDeviationXUnit', 'setRandomDeviationYUnit')
    pp.setSeed(1941)                         # 0 significa re-sortear a cada render
    pp.setSubSymbol(ms)

    manchado = sobre(T.mancha(pasta, 'mata', base=6, oitavas=5, contraste=0.70,
                              forca=0.28, grao=0.25, semente=5150), ESC_MATA)
    return [simples(MATA), manchado, pp]

def papel(pasta):
    """A granulacao que passa por cima do mapa inteiro e amarra as camadas."""
    return [sobre(T.grao(pasta, 'papel', forca=0.07), ESC_PAPEL)]

def telhados(layer, hachura=False):
    """
    Os predios: cor propria por telhado e sombra dura por baixo do conjunto.

    A cor sai de rand() semeado no id da feicao. E a sombra que da o volume —
    sem ela os predios sao manchas coladas no chao.

    'hachura' liga a nervura do telhado, alinhada ao proprio predio; so funciona
    se a camada tiver o campo 'rumo' (veja telhado.py).
    """
    fundo = simples(TELHADOS[0])
    dd(fundo, QgsSymbolLayer.Property.FillColor,
       "array_get(array('{p}'), {s})".format(p="','".join(TELHADOS), s=sorteia(len(TELHADOS))))
    camadas = [fundo]
    if hachura:
        h = QgsLinePatternFillSymbolLayer()
        h.setColor(QColor(0, 0, 0, 78)); h.setLineWidth(0.30); h.setDistance(0.85)
        _mm(h, 'setDistanceUnit', 'setLineWidthUnit')
        # 'rumo' e o azimute do eixo longo, horario a partir do norte; o angulo da
        # trama do QGIS conta de outro jeito, dai o 90 -.
        dd(h, QgsSymbolLayer.Property.LineAngle, '90 - "rumo"')
        camadas.append(h)
    return veste(layer, *camadas, efeito=sombra(1.15, 0.5, SOMBRA_SEC, 0.6, 135))

def via_dupla(layer):
    orla = QgsSimpleLineSymbolLayer(QColor(VIA_ORLA)); orla.setWidth(0.62)
    nucleo = QgsSimpleLineSymbolLayer(QColor(VIA)); nucleo.setWidth(0.38)
    s = QgsLineSymbol(); s.deleteSymbolLayer(0)
    for c in (orla, nucleo):
        c.setPenCapStyle(1); c.setPenJoinStyle(1); _mm(c, 'setWidthUnit'); s.appendSymbolLayer(c)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer
