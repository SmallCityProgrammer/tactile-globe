# -*- coding: utf-8 -*-
# estilo.py — a paleta e os simbolos do mapa de Carentan, num lugar so.
#
# Mesma gramatica do mapa do Pacifico: cada camada e uma base opaca (cor chapada
# ou degrade) e, por cima, um ladrilho de SOBREPOR vindo do textura.py. O
# ladrilho nao pinta — so empurra o que ja estava ali para mais claro ou mais
# escuro. Por isso o mesmo arquivo de mancha serve sobre o oliva do campo e
# sobre o verde do brejo sem virar duas texturas.
#
# O QUE MUDA EM RELACAO A PEARL HARBOR
# La o problema era separar terra de agua sem poligono de agua. Aqui a agua vem
# pronta do OSM e o problema e outro: o chao de Carentan nao e liso. E bocage —
# um mosaico de talhoes pequenos, cada um fechado por um aterro com arvores em
# cima. Foi ele que segurou uma divisao inteira por seis dias. Um mapa com o
# campo aberto chapado conta a historia errada, entao o bocage e uma textura,
# nao um enfeite.
#
# TUDO EM MILIMETROS DE TELA, MENOS UMA COISA
# A trama, o grao e a espessura das vias estao em milimetros: e o que mantem o
# desenho com a mesma cara em qualquer enquadramento. O bocage e a excecao
# declarada — veja TALHAO_M la embaixo.
import os
from qgis.core import (Qgis, QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol, QgsSingleSymbolRenderer,
                       QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSimpleMarkerSymbolLayer,
                       QgsLinePatternFillSymbolLayer, QgsPointPatternFillSymbolLayer,
                       QgsRasterFillSymbolLayer, QgsShapeburstFillSymbolLayer,
                       QgsDropShadowEffect, QgsInnerShadowEffect, QgsEffectStack, QgsDrawSourceEffect,
                       QgsProperty, QgsExpression, QgsSymbolLayer, QgsUnitTypes)
from qgis.PyQt.QtCore import QPointF
from qgis.PyQt.QtGui import QColor
import textura as T

# ============================================================== PALETA
# A familia do Operations Room, puxada para a Normandia de junho: menos areia,
# mais verde, e o teal do mar virando o teal de rio parado.
AGUA       = '#2b8492'   # a Douve, a Taute, o canal, a bacia do porto
RASO       = '#57aab3'   # a beirada da agua
BREJO      = '#7c8f66'   # o pantano: pasto alagado, mais frio e mais cinza que o campo
POCA       = '#4a8b91'   # a agua parada em cima do brejo
CAMPO      = '#93a054'   # o oliva do campo aberto
PASTO      = '#9aa65c'   # os talhoes que o OSM tem mapeados, um tom acima
MATA       = '#5f7a38'   # a mata
COPA       = '#46602c'   # as copas salpicadas por cima
COPA_SOMBRA= '#33461f'
SEBE       = '#4a6129'   # a sebe do bocage, onde o OSM a tem de verdade
# Os talhoes que em junho nao estavam verdes: feno de corte, cereal em pe
# amarelando, e o que ja tinha sido arado.
LAVOURA    = ('#c0b071', '#a9a05e', '#9c8e63')
CIDADE     = '#c4b49a'   # o chao da cidade: rua, patio e quintal entre as casas
CAIS       = '#a89c82'
# A via precisa de mais contraste aqui do que em Pearl Harbor. La ela corria
# sobre bege de patio e cinza de concreto; aqui corre sobre campo verde, e com o
# cinza de la a estrada de Periers — que e o eixo do ataque das 6h — sumia no
# oliva. O nucleo clareia, a orla escurece: a estrada le no campo e continua
# discreta dentro da cidade.
VIA        = '#b3ada1'
VIA_ORLA   = '#6f6a61'
TRILHO     = '#4c4941'
DORMENTE   = '#cfc7b4'
SOMBRA     = '#1b5a63'   # a sombra da terra caindo DENTRO da agua
SOMBRA_SEC = '#2a2f24'   # a sombra dos predios, caindo no chao
PAPEL      = '#f3efe1'

# Telhados normandos: ardosia azulada na maioria, telha em alguns, e o cinza
# claro dos galpoes. Nada de verde militar — isto e uma cidade, nao uma base.
TELHADOS   = ['#5d646b', '#6b727a', '#535a61', '#7c5245',
              '#646b66', '#8a5f4c', '#4f565c', '#70776e', '#5a6169']

# --- escalas das texturas, em milimetros de tela -----------------------------
ESC_BREJO  = 110.0
ESC_POCA   = 130.0
ESC_CAMPO  = 90.0
ESC_MATA   = 54.0
ESC_CIDADE = 64.0
ESC_CAIS   = 22.0
ESC_AGUA   = 150.0
ESC_PAPEL  = 60.0

# O BOCAGE E MEDIDO NO CHAO, NAO NA TELA — a unica coisa do mapa que e.
#
# A regra da casa e milimetro de tela, e ela existe por um bom motivo: uma trama
# de material tem que ter a mesma cara em qualquer zoom. Mas o bocage nao e
# material, e FEICAO: o talhao normando tinha uns 140 m, e isso e um fato sobre
# o lugar. Em milimetro fixo, o mesmo campo sairia com 300 m num enquadramento e
# 80 m no outro, e duas cenas do mesmo filme mostrariam campos de tamanhos
# diferentes. Entao aqui a escala vem do render: quem chama passa quantos metros
# cabem num milimetro de tela, e o ladrilho se ajusta.
TALHAO_M   = 140.0       # o lado de um talhao tipico, em metros
# Quantos talhoes cabem no lado do ladrilho. Vale a mesma regra de bolso da agua
# de Pearl Harbor: quanto mais cabe dentro, menos a repeticao se denuncia. Com 4
# o ladrilho media 560 m e se repetia quase seis vezes na largura do quadro, e da
# para achar o mesmo talhao marchando pelo campo; com 6 sao 840 m e menos de
# quatro repeticoes.
BOCAGE_CEL = 6

MM = QgsUnitTypes.RenderMillimeters

def _mm(o, *setters):
    for s in setters:
        if hasattr(o, s): getattr(o, s)(MM)
    return o

# VIEWPORT poe todas as camadas na MESMA malha. Sem isso cada feicao ancora o
# ladrilho no proprio retangulo e aparece emenda onde dois poligonos se tocam.
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

    O angulo e rumo de bussola medido da tela para cima, no sentido horario: 0
    para cima, 90 para a direita, 135 para baixo e a direita. A pilha precisa do
    QgsDrawSourceEffect no fim, senao sai so a sombra e o desenho some.

    E sombra com borrao MAIOR que o deslocamento e sombra invisivel: ela fica
    quase toda debaixo do proprio desenho.
    """
    e = QgsDropShadowEffect()
    e.setOffsetDistance(dist); _mm(e, 'setOffsetUnit')
    e.setBlurLevel(blur); _mm(e, 'setBlurUnit')
    e.setOffsetAngle(int(round(ang)))        # so aceita int
    e.setColor(QColor(cor)); e.setOpacity(op)
    st = QgsEffectStack(); st.appendEffect(e); st.appendEffect(QgsDrawSourceEffect())
    return st

def sombra_dentro(dist=1.3, blur=3, cor=SOMBRA, op=0.55, ang=125):
    """
    A sombra do barranco caindo DENTRO da agua.

    Em Pearl Harbor a terra era um poligono no meio do mar, entao bastava dar
    sombra projetada nela. Aqui e o contrario: a terra e o fundo do mapa inteiro
    e a agua e o recorte. Sombra projetada na agua faria o rio parecer flutuar
    ACIMA do campo. A sombra interna resolve — ela nasce na margem e cai para
    dentro do rio, que e o que a margem faz de verdade.
    """
    e = QgsInnerShadowEffect()
    e.setOffsetDistance(dist); _mm(e, 'setOffsetUnit')
    e.setBlurLevel(int(round(blur))); _mm(e, 'setBlurUnit')
    e.setOffsetAngle(int(round(ang)))
    e.setColor(QColor(cor)); e.setOpacity(op)
    st = QgsEffectStack(); st.appendEffect(QgsDrawSourceEffect()); st.appendEffect(e)
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
    OPACO por cima de tudo. String vazia, sim, e o sentinela seguro.
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

    Validada antes: o QGIS aceita expressao quebrada em silencio absoluto e
    desenha o valor estatico, entao o erro so apareceria no mapa, se aparecesse.
    """
    e = QgsExpression(expr)
    if e.hasParserError():
        raise ValueError('expressao invalida %r: %s' % (expr, e.parserErrorString().strip()))
    camada.setDataDefinedProperty(chave, QgsProperty.fromExpression(expr))
    return camada

def sorteia(n, desvio=0):
    """
    Um inteiro 0..n-1 por feicao, estavel entre renders.

    Tem que ser o rand() de TRES argumentos: sem semente ele re-sorteia a cada
    render e o mapa pisca. E nao adianta hash multiplicativo — ($id*K) % n e
    estritamente periodico e sai listrado.
    """
    return 'rand(0, {m}, ($id) + {d})'.format(m=n - 1, d=desvio)

def veste(layer, *camadas, efeito=None, por_feicao=False):
    """
    Monta um QgsFillSymbol com as camadas dadas, de baixo para cima.

    O efeito vai no RENDERIZADOR, nao na camada de simbolo: na camada ele roda
    uma vez por feicao, e nos 3510 predios isso custa muito mais. No
    renderizador a camada inteira e desenhada uma vez e o efeito passa por cima
    — e o desenho fica melhor, porque a sombra sai da silhueta do quarteirao em
    vez de cada casa jogar sombra na vizinha.
    """
    s = QgsFillSymbol(); s.deleteSymbolLayer(0)
    for c in camadas: s.appendSymbolLayer(c)
    r = QgsSingleSymbolRenderer(s)
    if efeito is not None:
        if por_feicao: camadas[0].setPaintEffect(efeito)
        else: r.setPaintEffect(efeito)
    layer.setRenderer(r); return layer

def veste_linha(layer, *camadas, efeito=None):
    s = QgsLineSymbol(); s.deleteSymbolLayer(0)
    for c in camadas: s.appendSymbolLayer(c)
    r = QgsSingleSymbolRenderer(s)
    if efeito is not None: r.setPaintEffect(efeito)
    layer.setRenderer(r); return layer

# ============================================================== O CHAO
def malha_bocage(pasta, m_por_mm):
    """
    Os dois ladrilhos do bocage e a escala deles em milimetros de tela.

    'm_por_mm' e quantos metros do chao cabem num milimetro de tela NESTE
    enquadramento. E dele que sai a escala, para o talhao sair com os seus 140 m
    em qualquer recorte.

    Sao dois porque o tom do talhao e modulacao e a sebe e cor — e porque assim a
    sebe pode ser desenhada UMA VEZ SO, numa camada propria por cima dos campos.
    Se cada camada de campo carregasse a sebe junto, onde duas se sobrepusessem a
    sebe sairia com alfa dobrado e o mapa ficaria manchado de escuro.
    """
    esc = (TALHAO_M * BOCAGE_CEL) / float(m_por_mm)       # o lado do ladrilho, em mm de tela
    tom = T.bocage(pasta, 'bocage', celulas=BOCAGE_CEL, semente=1944,
                   quadrado=0.62, forca=0.26, variacao=0.60)
    cult = T.bocage_cultura(pasta, 'bocagecultura', celulas=BOCAGE_CEL, semente=1944,
                            quadrado=0.62, cores=LAVOURA, fracao=0.32, alfa=(80, 140))
    sb = T.bocage_sebe(pasta, 'bocagesebe', celulas=BOCAGE_CEL, semente=1944,
                       quadrado=0.62, largura=0.030, cor=SEBE, alfa=205,
                       sombra=SOMBRA_SEC, sombra_alfa=115, desloca=3)
    return (tom, cult, sb), esc

def chao(malha, esc):
    """O campo aberto: o fundo do mapa inteiro, com o tom dos talhoes por cima."""
    return [simples(CAMPO), sobre(malha[0], esc)]

def talhoes(malha, esc):
    """
    Os campos que o OSM tem mapeados: MESMO ladrilho de tom, so outra base.

    Nao e preguica, e o que o modo Viewport compra. Como todas as camadas ancoram
    o ladrilho na tela, e nao cada uma no proprio retangulo, a malha de talhoes
    atravessa a divisa do poligono sem emenda: o prado mapeado aparece como um
    verde um pouco diferente POR CIMA do mesmo mosaico, em vez de virar uma chapa
    lisa apagando o bocage embaixo. E o maior prado do recorte tem 3,7 x 6,3 km —
    chapado, ele sozinho apagaria metade do mapa.
    """
    return [simples(PASTO), sobre(malha[0], esc)]

def cerca_viva(malha, esc):
    """
    A lavoura e as sebes, numa camada propria, por cima de todos os campos.

    Vai ABAIXO do brejo e da cidade de proposito: o pantano nao era dividido em
    talhoes, era pasto alagado aberto, e a cidade tem quarteirao no lugar de
    cerca. Deixar a malha passar por cima dos dois poria cerca viva dentro do
    canal e no meio da Rue Holgate.

    A ordem aqui e o que faz a sebe fechar o talhao: a lavoura pinta o campo
    inteiro ate a divisa, e a sebe passa por cima dela.
    """
    return [sobre(malha[1], esc), sobre(malha[2], esc)]

def brejo(pasta):
    """
    O pantano do vale da Douve, que e metade da razao desta batalha.

    Os alemaes abriram as comportas em maio de 44 e deixaram o vale inteiro
    assim. Por isso os paraquedistas tiveram que descer pela calcada exposta, em
    fila, e por isso a estrada ganhou o apelido de Purple Heart Lane.

    A BORDA TEM QUE DESMANCHAR. O poligono de pantano do OSM e uma linha firme, e
    desenhado com cor chapada ele corta o mapa numa diagonal dura que le como
    erro de recorte — brejo nao termina numa reta, ele vai ficando seco. O
    shapeburst resolve: transparente na divisa, cheio la dentro. E a mesma
    ferramenta do raso de Pearl Harbor, usada ao contrario — la para clarear a
    agua junto da praia, aqui para sumir com a propria camada na borda.

    E A POCA E MEDIDA. Com limiar alto o vale inteiro virava lago e o mapa
    mentia: aquilo era pasto alagado com agua parada nas partes baixas, do tipo
    que se atravessa com agua pela canela, nao uma lamina navegavel.
    """
    borda = QColor(BREJO); borda.setAlpha(0)
    sb = QgsShapeburstFillSymbolLayer()
    sb.setColor(borda); sb.setColor2(QColor(BREJO))
    sb.setUseWholeShape(False); sb.setMaxDistance(4.0); _mm(sb, 'setDistanceUnit')
    sb.setBlurRadius(4)                      # so aceita int
    return [sb,
            sobre(T.mancha(pasta, 'brejo', base=6, oitavas=5, contraste=0.75,
                           forca=0.26, grao=0.22, semente=644), ESC_BREJO),
            sobre(T.pocas(pasta, 'pocas', cor=POCA, limiar=0.26, alfa=128,
                          suave=0.16, semente=644), ESC_POCA)]

def mata(pasta):
    """
    A mata: verde mais frio, manchado, e as copas salpicadas por cima.

    O setter do jitter chama-se setMaximumRandomDeviationX — setRandomDeviationX
    nao existe, e atras de um hasattr as copas sairiam numa grade perfeita sem
    ninguem notar. E a semente de fabrica e 0, que significa "re-sorteia a cada
    render": sem setSeed a mata muda de desenho a cada repintura.
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
    dd(copa, QgsSymbolLayer.Property.Size,
       'randf(1.15, 1.85, @symbol_marker_row * 1000 + @symbol_marker_column)')
    dd(sombrinha, QgsSymbolLayer.Property.Size,
       'randf(1.25, 1.95, @symbol_marker_row * 1000 + @symbol_marker_column)')

    pp = QgsPointPatternFillSymbolLayer()
    pp.setDistanceX(2.3); pp.setDistanceY(2.3); pp.setDisplacementX(1.15)
    _mm(pp, 'setDistanceXUnit', 'setDistanceYUnit', 'setDisplacementXUnit')
    pp.setMaximumRandomDeviationX(0.7); pp.setMaximumRandomDeviationY(0.7)
    _mm(pp, 'setRandomDeviationXUnit', 'setRandomDeviationYUnit')
    pp.setSeed(1944)                         # 0 significa re-sortear a cada render
    pp.setSubSymbol(ms)

    manchado = sobre(T.mancha(pasta, 'mata', base=6, oitavas=5, contraste=0.70,
                              forca=0.28, grao=0.25, semente=5150), ESC_MATA)
    return [simples(MATA), manchado, pp]

def cidade(pasta):
    """
    O chao da cidade: rua, patio, quintal — tudo que nao e telhado dentro do
    perimetro construido.

    E o mesmo truque do bege de Pearl Harbor, com outro numero. La o patio da
    base saia engordando cada predio 85 m; aqui 85 m juntaria a cidade inteira
    num borrao redondo, porque o quarteirao normando e denso. Com 22 m para fora
    e 14 de volta, os quarteiroes se fecham e as ruas largas continuam abertas.

    E COM OUTRA TEXTURA. Em Pearl Harbor o bege e patio de base militar, e a
    'laje' esta certa: aquilo e concreto lancado por baia. Aqui o bege e quintal,
    horta, calcada e pateo de pedra de uma cidade de mil anos — a malha de placas
    aparecia como piso de garagem por cima da cidade inteira. 'mancha' e o que
    esse chao e: irregular, sem direcao e sem periodo.
    """
    return [simples(CIDADE), sobre(T.mancha(pasta, 'chaocidade', base=7, oitavas=5,
                                            contraste=0.80, forca=0.16, grao=0.30,
                                            semente=612), ESC_CIDADE)]

def cais(pasta):
    """O cais do porto: concreto em placa miuda, com a borda marcada."""
    return [simples(CAIS, '#8a7f68', 0.12),
            sobre(T.laje(pasta, 'cais', placas=4, variacao=0.26, junta=0.30), ESC_CAIS)]

def agua(pasta, raso_mm=3.0):
    """
    A agua: o canal, a bacia do porto e o que o OSM traz de rio como poligono.

    O shapeburst faz a beirada clarear para dentro, como em Pearl Harbor, mas
    aqui as laminas sao estreitas — dai o raso menor. So vale enquanto raso_mm
    for menor que 10% da extensao desenhada: o QGIS corta a geometria de
    preenchimento na extensao inflada em exatamente 10%, e essa borda cortada
    tambem brilha.
    """
    sb = QgsShapeburstFillSymbolLayer()
    sb.setColor(QColor(RASO)); sb.setColor2(QColor(AGUA))
    sb.setUseWholeShape(False); sb.setMaxDistance(raso_mm); _mm(sb, 'setDistanceUnit')
    sb.setBlurRadius(3)                      # so aceita int
    sb.setIgnoreRings(False)
    return [sb, sobre(T.mancha(pasta, 'agua', base=10, oitavas=5, contraste=0.55,
                               forca=0.15), ESC_AGUA)]

def papel(pasta):
    """A granulacao que passa por cima do mapa inteiro e amarra as camadas."""
    return [sobre(T.grao(pasta, 'papel', forca=0.07), ESC_PAPEL)]

# ============================================================== AS LINHAS
# A largura da agua corrente sai da classe que o convert.mjs gravou em 'c':
# 1 rio e canal, 2 corrego, 3 vala. Sem isso as valas de drenagem do brejo
# ficariam da grossura da Douve.
LARG_RIO = (2.6, 1.15, 0.45)

def rio(layer):
    corpo = QgsSimpleLineSymbolLayer(QColor(AGUA)); corpo.setWidth(LARG_RIO[0])
    dd(corpo, QgsSymbolLayer.Property.StrokeWidth,
       'array_get(array({v}), coalesce("c", 3) - 1)'.format(v=', '.join(str(v) for v in LARG_RIO)))
    corpo.setPenCapStyle(1); corpo.setPenJoinStyle(1); _mm(corpo, 'setWidthUnit')
    return veste_linha(layer, corpo)

# 1 grandes, 2 arteriais, 3 locais, 4 servico e trilha. Sem isso os 292 caminhos
# de servico ficariam da mesma grossura da estrada de Periers.
LARG_ORLA   = (1.15, 0.88, 0.62, 0.40)
LARG_NUCLEO = (0.76, 0.58, 0.38, 0.22)

def _por_classe(vals):
    return 'array_get(array({v}), coalesce("c", 4) - 1)'.format(v=', '.join(str(v) for v in vals))

def via_dupla(layer):
    orla = QgsSimpleLineSymbolLayer(QColor(VIA_ORLA)); orla.setWidth(LARG_ORLA[0])
    nucleo = QgsSimpleLineSymbolLayer(QColor(VIA)); nucleo.setWidth(LARG_NUCLEO[0])
    dd(orla, QgsSymbolLayer.Property.StrokeWidth, _por_classe(LARG_ORLA))
    dd(nucleo, QgsSymbolLayer.Property.StrokeWidth, _por_classe(LARG_NUCLEO))
    s = QgsLineSymbol(); s.deleteSymbolLayer(0)
    for c in (orla, nucleo):
        c.setPenCapStyle(1); c.setPenJoinStyle(1); _mm(c, 'setWidthUnit'); s.appendSymbolLayer(c)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer

def ferrovia(layer):
    """
    O trilho: a barra escura e os dormentes claros por cima, em tracejado.

    Fino de proposito. Com 0,85 mm e traco de 0,7 o simbolo virava um cordao
    preto e branco grosso atravessando o mapa, com a cara de fronteira de atlas —
    o olho ia primeiro nele, e nao na cidade. Meio milimetro e traco curto diz
    ferrovia sem gritar.
    """
    barra = QgsSimpleLineSymbolLayer(QColor(TRILHO)); barra.setWidth(0.52)
    barra.setPenCapStyle(0); _mm(barra, 'setWidthUnit')
    dorm = QgsSimpleLineSymbolLayer(QColor(DORMENTE)); dorm.setWidth(0.52)
    dorm.setPenCapStyle(0); _mm(dorm, 'setWidthUnit')
    dorm.setCustomDashVector([0.35, 0.75]); dorm.setUseCustomDashPattern(True)
    _mm(dorm, 'setCustomDashPatternUnit')
    return veste_linha(layer, barra, dorm)

def sebes(layer):
    """As poucas sebes que o OSM tem de verdade, com a sombrinha delas."""
    l = QgsSimpleLineSymbolLayer(QColor(SEBE)); l.setWidth(1.05)
    l.setPenCapStyle(1); l.setPenJoinStyle(1); _mm(l, 'setWidthUnit')
    return veste_linha(layer, l, efeito=sombra(0.5, 0.4, SOMBRA_SEC, 0.5, 135))

def telhados(layer):
    """
    Os predios: cor propria por telhado e sombra dura por baixo do conjunto.

    A cor sai de rand() semeado no id da feicao, e e a sombra que da o volume —
    sem ela as casas sao manchas coladas no chao.
    """
    fundo = simples(TELHADOS[0])
    dd(fundo, QgsSymbolLayer.Property.FillColor,
       "array_get(array('{p}'), {s})".format(p="','".join(TELHADOS), s=sorteia(len(TELHADOS))))
    return veste(layer, fundo, efeito=sombra(0.9, 0.4, SOMBRA_SEC, 0.62, 135))
