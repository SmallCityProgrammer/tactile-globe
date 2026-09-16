# arvores.py — a mata, com arvore que parece arvore.
#
# Substitui a mata() do estilo.py. Em pearl.py basta:
#
#     import arvores
#     if verde: veste(verde, *arvores.mata(HERE))
#
# ou, no proprio estilo.py, trocar o corpo de mata() por um  return
# arvores.mata(pasta).  O resto do arquivo nao muda: a paleta, o sobre(), o dd()
# e o _mm() daqui vem todos de la.
#
# ============================================================================
# O QUE ESTAVA ERRADO, E O QUE CADA COISA CONSERTA
#
# A mata antiga era um QgsPointPatternFillSymbolLayer: uma grade jitterada de
# circulos. Tres coisas a denunciavam, e cada uma tem uma resposta aqui.
#
#   1. A GRADE.  Jitter de 0,7 mm num passo de 2,3 mm nao desmancha a grade —
#      desloca cada ponto no maximo 30% da celula, entao as fileiras continuam
#      la e o olho as acha em um segundo. Resposta: espalhamento aleatorio de
#      verdade (QgsRandomMarkerFillSymbolLayer), que faz grumo e faz claro.
#
#   2. A ARVORE IGUAL.  Dentro do point pattern o tamanho ja variava, preso a
#      @symbol_marker_row/@symbol_marker_column. No sorteio essas duas nao
#      existem — mas @geometry_point_num existe, e e o indice do ponto sorteado
#      dentro da feicao. Serve de semente por arvore, e serve para tamanho, cor
#      e o que mais se quiser.
#
#   3. A BORDA RETA.  Essa e a maior. Um bosque cuja beirada e a linha reta do
#      OSM nunca vai parecer bosque. Resposta em dois tempos: as arvores se
#      espalham num poligono ENGORDADO 1,25 mm, e um anel mais denso costura a
#      beirada — a silhueta do bosque passa a ser a das copas, nao a do dado.
#
# TUDO CONTINUA EM MILIMETROS DE TELA, como o resto do mapa: a densidade e por
# mm2 de tela, a arvore mede mm, e ate o engorda da borda mede mm — veja a nota
# sobre setUnits() no gerador().
import os
from qgis.core import (Qgis, QgsFillSymbol, QgsMarkerSymbol, QgsSimpleMarkerSymbolLayer,
                       QgsRandomMarkerFillSymbolLayer, QgsGeometryGeneratorSymbolLayer,
                       QgsSvgMarkerSymbolLayer, QgsSymbolLayer, QgsExpression, QgsUnitTypes)
from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor
import textura as T
from estilo import MATA, ESC_MATA, sobre, simples, MM, _mm, dd, grava_svg

P = QgsSymbolLayer.Property

# ============================================================== NUMEROS
# A copa nao tem uma cor so: a referencia tem verde quente e verde frio na mesma
# mata. Cinco tons da mesma familia bastam — mais que isso vira confete.
COPAS   = ['#3e5526', '#46602c', '#4e6a33', '#55743b', '#405a28']
SOMBRA_COPA = '#2c3d1a'

TAM_MIN, TAM_MAX = 1.05, 2.05     # mm de tela, diametro da copa
SOMBRA_OFF  = 0.55                # mm, para baixo e para a direita
SOMBRA_MAIS = 0.12                # a sombra e um tico maior que a copa
DENS        = 88                  # arvores por DENS_AREA
DENS_AREA   = 250.0               # mm2 de tela
SEMENTE     = 1941

ENGORDA     = 1.25                # mm que as arvores transbordam o poligono
ANEL_DENS   = 48                  # a costura da beirada, por DENS_AREA
ANEL_SEM    = 6161

# Cada arvore sorteia pelo seu indice dentro da feicao. randf de TRES argumentos:
# sem semente ele re-sorteia a cada repintura e a mata pisca.
TAMANHO = 'randf({0:g}, {1:g}, @geometry_point_num)'.format(TAM_MIN, TAM_MAX)

def cor_copa(desvio=777):
    """Uma das COPAS por arvore. 'desvio' descorrelaciona cor de tamanho."""
    return "array_get(array('{p}'), rand(0, {n}, @geometry_point_num + {d}))".format(
        p="','".join(COPAS), n=len(COPAS) - 1, d=desvio)

# ============================================================== A ARVORE
def copa(expr_cor=None):
    """
    Uma arvore: disco de sombra embaixo, disco de copa em cima.

    A sombra e uma CAMADA DE MARCADOR deslocada, e nao um QgsDropShadowEffect —
    efeito por marcador sairia caro em centenas de milhares de arvores. E ela
    precisa de deslocamento de verdade: a mata antiga usava 0,28 mm com a sombra
    so 0,10 mm maior que a copa, o que deixava escapar uma franja de 0,05 mm.
    Dava para provar que existia, nao para ver. Com 0,55 mm a foice aparece.

    A sombra NAO sorteia cor. Ela e a mesma para todas: sombra colorida por
    arvore vira ruido, e o que amarra a mata e a luz vir toda do mesmo lado.
    """
    som = QgsSimpleMarkerSymbolLayer()
    som.setColor(QColor(SOMBRA_COPA)); som.setStrokeStyle(0)
    som.setSize(TAM_MIN + SOMBRA_MAIS); som.setSizeUnit(MM)
    som.setOffset(QPointF(SOMBRA_OFF, SOMBRA_OFF)); _mm(som, 'setOffsetUnit')
    dd(som, P.Size, '({0}) + {1:g}'.format(TAMANHO, SOMBRA_MAIS))

    cop = QgsSimpleMarkerSymbolLayer()
    cop.setColor(QColor(COPAS[1])); cop.setStrokeStyle(0)
    cop.setSize(TAM_MIN); cop.setSizeUnit(MM)
    dd(cop, P.Size, TAMANHO)
    dd(cop, P.FillColor, expr_cor or cor_copa())

    ms = QgsMarkerSymbol(); ms.deleteSymbolLayer(0)
    ms.appendSymbolLayer(som); ms.appendSymbolLayer(cop)
    return ms

# ============================================================== O ESPALHAMENTO
def sorteio(sub, por=DENS, area=DENS_AREA, semente=SEMENTE, clip=False, por_feicao=True):
    """
    QgsRandomMarkerFillSymbolLayer, o espalhador.

    DensityBasedCount + densityArea em MILIMETROS prende a densidade a tela, e
    nao ao terreno — que e o que o resto do mapa faz. Com AbsoluteCount cada
    poligono ganharia o mesmo numero de arvores, e um bosque de 20 m ficaria tao
    cheio quanto um de 600 m.

    A semente de fabrica e 0, que quer dizer 're-sorteia a cada render' — a
    mesma armadilha do point pattern. Medido: com setSeed(1941) dois renders
    saem com o MESMO md5; com 0, diferentes.

    clipPoints fica DESLIGADO, que ja e o de fabrica. Ligado, a copa e cortada
    rente a reta do poligono e a beirada fica serrada com uma regua — e o
    contrario do que se quer.

    A semente por feicao existe porque o sorteio parte da MESMA sequencia em
    toda feicao: dois poligonos de formato parecido ganhariam o mesmo desenho de
    arvores. rand(...,$id) resolve e continua estavel entre renders.
    """
    sl = QgsRandomMarkerFillSymbolLayer(por)
    sl.setCountMethod(QgsRandomMarkerFillSymbolLayer.DensityBasedCount)
    sl.setDensityArea(area); sl.setDensityAreaUnit(MM)
    sl.setSeed(semente); sl.setClipPoints(clip)
    sl.setSubSymbol(sub)
    if por_feicao:
        dd(sl, P.RandomSeed, 'rand(1, 99999, $id + {0:d})'.format(semente))
    return sl

def gerador(expr, sub_fill, unidade=QgsUnitTypes.RenderMillimeters):
    """
    Preenchimento com a geometria derivada na hora.

    O setUnits() e o detalhe que faz isso servir aqui, e foi medido: com
    RenderMillimeters, 'buffer($geometry, 4)' desenha um anel de 15 px em
    QUALQUER escala (3,97 mm a 96 dpi), enquanto com RenderMapUnits o mesmo 4 da
    4 metros de chao — 4 px longe e 10 px perto. Como a arvore, a textura e a
    via estao todas em milimetros, a borda tambem tem que estar.
    """
    if QgsExpression(expr).hasParserError():
        raise ValueError('expressao invalida: ' + expr)
    gg = QgsGeometryGeneratorSymbolLayer.create({'geometryModifier': expr})
    gg.setSymbolType(Qgis.SymbolType.Fill)
    gg.setUnits(unidade)
    gg.setSubSymbol(sub_fill)
    return gg

def _fill(*cams):
    s = QgsFillSymbol(); s.deleteSymbolLayer(0)
    for c in cams: s.appendSymbolLayer(c)
    return s

# ============================================================== A MATA
def mata(pasta):
    """
    A mata inteira, de baixo para cima:

      1. a chapa oliva fria, com a mancha de ruido por cima — igual a de antes;
      2. as arvores, espalhadas num poligono ENGORDADO, entao elas transbordam
         a reta do OSM em vez de parar nela;
      3. o anel: uma faixa que abraca a beirada, com o seu proprio sorteio, para
         a borda ficar costurada de copa.

    A chapa de baixo NAO encolhe, e isso foi decidido contando: um encolhimento
    de 0,9 mm vale 13,9 m de chao no enquadramento do mapa inteiro, e 315 dos
    656 bosques do verde.geojson tem raio equivalente menor que isso — quase
    metade perderia o fundo, e perderia SO no zoom afastado, que e o pior tipo
    de bug: some e volta conforme se navega. E, olhando lado a lado, encolher
    nao melhorava nada que o anel ja nao resolvesse.

    O anel usa difference(engorda, encolhe). Em bosque pequeno o encolhe volta
    vazio e a diferenca vira o engorda inteiro — ou seja, bosque pequeno fica
    todo ele beirada, com as duas densidades somadas. Isso e o certo: um bosque
    de 20 m E todo beirada.
    """
    chao = [simples(MATA),
            sobre(T.mancha(pasta, 'mata', base=6, oitavas=5, contraste=0.70,
                           forca=0.28, grao=0.25, semente=5150), ESC_MATA)]
    dentro = gerador('buffer($geometry, {0:g})'.format(ENGORDA),
                     _fill(sorteio(copa())))
    anel = gerador('difference(buffer($geometry, {0:g}), buffer($geometry, -{0:g}))'.format(ENGORDA),
                   _fill(sorteio(copa(cor_copa(311)), por=ANEL_DENS, semente=ANEL_SEM)))
    return chao + [dentro, anel]

# ============================================================================
# A ROTA DA COPA EM SVG — funciona, e ate mais barata, e mesmo assim nao e a
# recomendada. A diferenca e de gosto, e o gosto esta explicado abaixo.
#
# A ideia e desenhar a copa como os telhados sao desenhados: silhueta bolorenta,
# foice escura embaixo-a-direita, foice de luz em cima-a-esquerda e sombra
# caida — tudo dentro do arquivo, entao uma camada de marcador so.
#
# O CUSTO, medido na camada verde sozinha a 3000 px, mediana de tres renders:
#
#              mapa inteiro   ford island   hangar
#   circulo        1,14 s        0,86 s      2,34 s
#   copa SVG       0,86 s        0,48 s      1,52 s
#
# A copa em SVG e MAIS BARATA, e por um motivo bobo: ela e um raster ja pronto
# no cache, que o Qt so estampa, enquanto o circulo desenha duas elipses
# antialiasadas por arvore. Custo nao decide isto.
#
# O QUE DECIDE E O DESENHO. Lado a lado no mesmo recorte, o circulo tem mais
# contraste (desvio de luminancia 30,3 contra 29,0; decil inferior 52 contra 57)
# e cada arvore fica DESTACADA da vizinha. A copa em SVG e mais organica e mais
# macia — as copas se fundem numa massa. A referencia do Operations Room e
# grafica e separada: "blobs arredondados distintos". Por isso o circulo.
#
# TRES ARMADILHAS, e a terceira e um despenhadeiro:
#
#   A. ALFA SE COMPOE. A primeira versao fazia luz e sombra com um circulo POR
#      LOBO a fill-opacity 0,17. Onde cinco lobos se cruzavam o alfa efetivo
#      virava 1 - 0,83^5 = 0,61, e a 6 px isso sai como respingo BRANCO: a mata
#      virou liquen. Um caminho so, um alfa so.
#
#   B. A LUZ TEM QUE SER PEQUENA. Varrendo escala e opacidade da foice de luz e
#      olhando a 11 px: 0,74 de escala lava a arvore e ela fica mais CLARA que o
#      fundo; 0,42 a 0,45 com opacidade 0,09 a 0,11 e onde ainda se ve volume e
#      a arvore continua escura.
#
#   C. TAMANHO CONTINUO NUM MARCADOR SVG E UM DESPENHADEIRO. O cache de SVG do
#      QGIS guarda um raster por combinacao de arquivo, cor e TAMANHO. Um
#      randf() de tamanho da um float diferente por arvore, entao toda arvore e
#      um cache miss e uma rasterizacao nova. Medido no hangar, onde um bosque
#      so cobre a tela inteira e recebe milhares de pontos:
#
#          tamanho fixo               0,91 s
#          5 tamanhos discretos       1,50 s
#          randf() continuo         204,08 s     <- 224 vezes
#
#      E nao e uma curiosidade de bancada: com randf() o render do recorte do
#      hangar com todas as camadas passou de 4 s para 255 s. Por isso o tamanho
#      aqui e um array_get de cinco degraus, e nao um randf. A mesma regra vale
#      para a COR — cinco tons discretos, nao um gradiente sorteado.
#
#      O circulo nao tem esse penhasco: QgsSimpleMarkerSymbolLayer desenha
#      direto, sem cache de raster, e randf() nele custa o mesmo que um valor
#      fixo (1,14 s contra 1,05 s).
#
#   D. Property.Name TROCA O ARQUIVO POR ARVORE — e Property.File no marcador e
#      no-op silencioso, como o README ja registra. So que trocar de arquivo por
#      instancia tambem estoura o cache: 4,66 s contra 0,26 s com um arquivo so,
#      no mesmo recorte. Tres silhuetas diferentes nao valem 18 vezes o tempo, e
#      a 6 px ninguem ve que a silhueta se repete. Um arquivo so.
TAM_SVG = [1.6, 1.95, 2.3, 2.7, 3.05]    # DEGRAUS, nunca um randf — ver a nota C

def _copa_svg(lobos=5, semente_forma=4100):
    """
    A copa desenhada, em quatro caminhos. viewBox QUADRADO de proposito: so o
    Size e definido, a proporcao vem do viewBox, e assim a copa nao vira elipse.

    O raio ondula com o angulo — contorno bolorento em vez do circulo perfeito.
    Amplitude entre 7 e 11%: acima disso vira estrela, nao copa.
    """
    import math, random
    r = random.Random(semente_forma)
    cx, cy, R = 40.0, 38.0, 34.0
    k1, k2 = lobos, lobos + r.choice((3, 4))
    a1, a2 = r.uniform(0.07, 0.11), r.uniform(0.03, 0.06)
    p1, p2 = r.uniform(0, 6.28), r.uniform(0, 6.28)
    def contorno(esc, dx, dy, n=56):
        pts = []
        for i in range(n):
            t = 2 * math.pi * i / n
            rr = R * esc * (1 + a1 * math.sin(k1 * t + p1) + a2 * math.sin(k2 * t + p2))
            pts.append('%.1f,%.1f' % (cx + dx + math.cos(t) * rr, cy + dy + math.sin(t) * rr))
        return 'M' + ' L'.join(pts) + ' Z'
    return chr(10).join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">',
        '  <!-- a sombra caida -->',
        '  <path d="%s" fill="param(outline) #2c3d1a" fill-opacity="0.95"/>' % contorno(0.95, R*0.50, R*0.52),
        '  <!-- a foice escura: vai inteira, o corpo cobre quase tudo -->',
        '  <path d="%s" fill="#12200a" fill-opacity="0.40"/>' % contorno(1.0, R*0.11, R*0.13),
        '  <!-- o corpo, na cor sorteada por arvore -->',
        '  <path d="%s" fill="param(fill) #46602c"/>' % contorno(0.96, -R*0.04, -R*0.05),
        '  <!-- a luz, pequena, senao a arvore fica mais clara que o fundo -->',
        '  <path d="%s" fill="#ffffff" fill-opacity="0.09"/>' % contorno(0.42, -R*0.42, -R*0.46),
        '</svg>'])

def copa_svg(pasta):
    """Um arquivo so, cinco tamanhos discretos, cinco cores discretas."""
    arq = grava_svg(pasta, 'copa', _copa_svg())
    m = QgsSvgMarkerSymbolLayer(arq)
    m.setSize(TAM_SVG[0]); m.setSizeUnit(MM); m.setStrokeWidth(0)
    dd(m, P.Size, "array_get(array({v}), rand(0, {n}, @geometry_point_num))".format(
        v=', '.join('%g' % x for x in TAM_SVG), n=len(TAM_SVG) - 1))
    dd(m, P.FillColor, cor_copa())
    ms = QgsMarkerSymbol(); ms.deleteSymbolLayer(0); ms.appendSymbolLayer(m)
    return ms

def mata_svg(pasta):
    """A mesma mata, com a copa desenhada. Registrada, e nao a recomendada."""
    chao = [simples(MATA),
            sobre(T.mancha(pasta, 'mata', base=6, oitavas=5, contraste=0.70,
                           forca=0.28, grao=0.25, semente=5150), ESC_MATA)]
    dentro = gerador('buffer($geometry, {0:g})'.format(ENGORDA),
                     _fill(sorteio(copa_svg(pasta))))
    anel = gerador('difference(buffer($geometry, {0:g}), buffer($geometry, -{0:g}))'.format(ENGORDA),
                   _fill(sorteio(copa_svg(pasta), por=ANEL_DENS, semente=ANEL_SEM)))
    return chao + [dentro, anel]


# ============================================================== A COPA EM PNG
# O disco chapado lia como bolinha, e o que falta nele nao e resolucao: e
# silhueta irregular, volume e borda macia. Um PNG com alfa da as tres.
#
# O que se PERDE no caminho: num raster nao existe param(fill), entao nao da para
# recolorir uma copa so por feicao como se faz no SVG. A saida e gerar uma copa
# POR TOM e trocar o ARQUIVO por arvore — Property.Name, a mesma que troca o
# telhado no telhado.py. E de graca, porque os PNG ficam no cache de disco.
from qgis.core import QgsRasterMarkerSymbolLayer

TAM_PNG_MIN, TAM_PNG_MAX = 1.5, 2.9   # a copa em PNG carrega a propria sombra,
TAMANHO_PNG = 'randf({0:g}, {1:g}, @geometry_point_num)'.format(TAM_PNG_MIN, TAM_PNG_MAX)
GIRO_PNG = 'rand(0, 359, @geometry_point_num + 31)'   # o disco nao podia girar

def copas_png(pasta):
    """Uma copa por tom da familia. Devolve a lista de caminhos."""
    return [T.copa(pasta, 'copa%d' % i, cor=c, semente=7 + i * 13, lobos=5 + (i % 3))
            for i, c in enumerate(COPAS)]

def copa_png(pasta, desvio=0):
    """
    A arvore como imagem: sem camada de sombra separada, porque a sombra ja vem
    assada no PNG, e com GIRO por arvore — que o disco nao tinha como ter e que e
    metade do motivo de duas arvores vizinhas nao parecerem a mesma.
    """
    caminhos = copas_png(pasta)
    m = QgsRasterMarkerSymbolLayer()
    m.setPath(caminhos[0]); m.setSize(TAM_PNG_MIN); m.setSizeUnit(MM)
    dd(m, P.Size, TAMANHO_PNG)
    dd(m, P.Angle, GIRO_PNG)
    dd(m, P.Name, "array_get(array('{p}'), rand(0, {n}, @geometry_point_num + {d}))".format(
        p="','".join(c.replace(chr(92), '/') for c in caminhos),
        n=len(caminhos) - 1, d=desvio + 505))
    ms = QgsMarkerSymbol(); ms.deleteSymbolLayer(0); ms.appendSymbolLayer(m)
    return ms

def mata_modo(pasta, modo='circulo'):
    """
    A mata inteira, com a arvore escolhida por 'modo'.

      nenhuma  so a chapa e a mancha — sem arvore alguma
      circulo  os discos de sempre
      png      a copa em imagem, com silhueta, volume e giro

    O chao NAO muda entre os modos: e a mesma chapa e a mesma mancha. O que muda
    e so o que vai por cima, para a comparacao ser honesta.
    """
    chao = [simples(MATA),
            sobre(T.mancha(pasta, 'mata', base=6, oitavas=5, contraste=0.70,
                           forca=0.28, grao=0.25, semente=5150), ESC_MATA)]
    if modo == 'nenhuma':
        return chao
    faz = (lambda d=0: copa_png(pasta, d)) if modo == 'png' else (lambda d=0: copa(cor_copa(311 + d)))
    dentro = gerador('buffer($geometry, {0:g})'.format(ENGORDA), _fill(sorteio(faz())))
    anel = gerador('difference(buffer($geometry, {0:g}), buffer($geometry, -{0:g}))'.format(ENGORDA),
                   _fill(sorteio(faz(700), por=ANEL_DENS, semente=ANEL_SEM)))
    return chao + [dentro, anel]
