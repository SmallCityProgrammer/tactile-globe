# pearl.py — Pearl Harbor no estilo Operations Room.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" pearl.py
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" pearl.py 21.348 -157.978 21.383 -157.933 ford-island
#
# O OSM nao tem o porto como poligono de agua: so ha linha de costa. Entao a
# terra e obtida poligonizando (costa + retangulo da moldura) e ficando com as
# faces onde a DENSIDADE de predio e alta — o mar tem quase nenhum.
#
# O estilo mora inteiro em estilo.py. A ideia da referencia:
#   agua   = teal manchado por ruido fBm emendavel + halo claro de raso
#   terra  = oliva com a borda esmaecendo para areia (shapeburst) e sombra
#   bege   = NAO e a terra, e so a area construida da base (apron dos predios)
#   verde  = mata mais escura salpicada de copas
import os, sys, glob, math, random, time
# o plugin 'processing' nao esta no path do lancador; ele mora em apps/qgis*/python/plugins
for _p in glob.glob(os.path.join(os.environ.get('QGIS_PREFIX_PATH', r'C:/Program Files/QGIS 3.44.12/apps/qgis-ltr'), 'python', 'plugins')) + glob.glob(r'C:/Program Files/QGIS*/apps/qgis*/python/plugins'):
    if _p not in sys.path: sys.path.append(_p)
import processing
from processing.core.Processing import Processing
from qgis.core import (QgsApplication, QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry,
                       QgsPointXY, QgsField, QgsWkbTypes, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsRectangle, QgsMapSettings, QgsMapRendererParallelJob,
                       QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol, QgsSingleSymbolRenderer,
                       QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSimpleMarkerSymbolLayer,
                       QgsLinePatternFillSymbolLayer, QgsPointPatternFillSymbolLayer,
                       QgsShapeburstFillSymbolLayer, QgsDropShadowEffect, QgsEffectStack,
                       QgsDrawSourceEffect, QgsUnitTypes, QgsSpatialIndex, QgsVectorFileWriter)
from qgis.PyQt.QtCore import QSize, QVariant
from qgis.PyQt.QtGui import QColor

HERE = os.path.dirname(os.path.abspath(__file__))
S, W, N, E = 21.325, -158.030, 21.400, -157.920          # a moldura, em graus
WGS = QgsCoordinateReferenceSystem('EPSG:4326')
MERC = QgsCoordinateReferenceSystem('EPSG:3857')
NAVIOS_ON = False        # os navios de 1941; ligue se quiser os marcos de volta
MOLDURA_ON = True        # a borda branca rasgada da referencia
SINUOSO_ON = True        # ondular costa e mata; os molhes ficam retos

qgs = QgsApplication([], False); qgs.initQgis(); Processing.initialize()
tr = QgsCoordinateTransform(WGS, MERC, QgsProject.instance())

from estilo import *   # a paleta e os simbolos moram la, e provas.py usa os mesmos

# ============================================================== DADOS
def load(name):
    v = QgsVectorLayer(os.path.join(HERE, name + '.geojson'), name, 'ogr')
    return v if v.isValid() and v.featureCount() else None

def mem(name, kind, crs='EPSG:3857'):
    return QgsVectorLayer('%s?crs=%s' % (kind, crs), name, 'memory')

def corre(alg, par):
    par = dict(par); par['OUTPUT'] = 'memory:'
    return processing.run(alg, par)['OUTPUT']

# ---------------------------------------------------------------- a terra
costa = load('costa')
moldura = mem('moldura', 'LineString', 'EPSG:4326')
f = QgsFeature()
f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(W, S), QgsPointXY(E, S),
                                          QgsPointXY(E, N), QgsPointXY(W, N), QgsPointXY(W, S)]))
moldura.dataProvider().addFeature(f)

linhas = corre('native:mergevectorlayers', {'LAYERS': [costa, moldura], 'CRS': MERC})
faces = corre('native:polygonize', {'INPUT': linhas, 'KEEP_FIELDS': False})

predios = load('predio')
idx = QgsSpatialIndex(); pts = {}
for b in predios.getFeatures():
    g = b.geometry().centroid(); g.transform(tr)
    ff = QgsFeature(b.id()); ff.setGeometry(g)
    idx.addFeature(ff); pts[b.id()] = g.asPoint()

# Terra e agua se separam pela DENSIDADE de predio, nao pela contagem: o porto
# tem 3 predios (coisas sobre estacas) em 22 km2; o continente tem 594 em 85.
terra = mem('terra', 'Polygon'); tp = terra.dataProvider()
for face in faces.getFeatures():
    g = face.geometry()
    cand = idx.intersects(g.boundingBox())[:600]
    if not cand: continue
    dentro = sum(1 for i in cand if g.contains(QgsGeometry.fromPointXY(pts[i])))
    if dentro / len(cand) >= 0.15:
        ff = QgsFeature(); ff.setGeometry(g); tp.addFeature(ff)
terra.updateExtents()
print('faces:', faces.featureCount(), '-> terra:', terra.featureCount())

# ------------------------------------------------------------ ondular a terra
# Aqui, e nao depois. O mar e a diferenca do retangulo pela terra, e o patio e o
# apron cortado na terra: os dois PARTILHAM contorno com ela. Ondular a terra
# depois de montar os dois abriria fenda em toda a praia. Ondulando antes, os
# dois sao derivados da terra ja ondulada e continuam colados.
#
# Dois pesos multiplicam a ondulacao, e basta um ir a zero para o vertice ficar
# parado: 'congela' segura os 600 m junto a moldura, senao a aresta da figura
# fica serrilhada; 'estreito' segura os molhes.
if SINUOSO_ON:
    import sinuoso as SN
    _ext = tr.transformBoundingBox(QgsRectangle(W, S, E, N))
    _faces = [f.geometry() for f in terra.getFeatures()]
    _peso = SN.junta(SN.congela(_ext, 600.0),
                     SN.estreito(QgsGeometry.unaryUnion(_faces), 45.0, 55.0))
    terra = mem('terra', 'Polygon'); tp = terra.dataProvider()
    for g in _faces:
        ff = QgsFeature(); ff.setGeometry(SN.ondula(g, 14.0, 220.0, 1941, 2, 25.0, _peso))
        tp.addFeature(ff)
    terra.updateExtents()
    print('terra ondulada')

# -------------------------------------------------- o bege da area construida
# No Operations Room o bege nao e "a terra", e o patio da base: o chao batido
# em volta dos galpoes. Entao ele se deduz dos predios — engorda cada um,
# funde tudo, encolhe de volta (isso arredonda e fecha os vaos) e corta na costa.
pred3857 = corre('native:reprojectlayer', {'INPUT': predios, 'TARGET_CRS': MERC})

# ------------------------------------------- o rumo do eixo longo de cada predio
# Para a nervura do telhado seguir o predio, e nao a tela. Tem que ser calculado
# em 3857, que e o que o mapa desenha: em 4326 o esticao de 7,4% em Y na latitude
# do Havai gira o angulo uns 2 graus e, pior, vira o eixo longo de 96 predios
# quase quadrados em 90 graus inteiros — a trama correria ATRAVESSADA neles.
# O algoritmo preserva a ordem de entrada, mas renumera os fid, entao o casamento
# e posicional; juntar por fid daria 4 acertos em 5533.
caixas = corre('native:orientedminimumboundingbox', {'INPUT': pred3857})
telha = mem('predio', 'Polygon')
telha.dataProvider().addAttributes([QgsField('rumo', QVariant.Double),
                                    QgsField('alonga', QVariant.Double),
                                    QgsField('comp', QVariant.Double),
                                    QgsField('larg', QVariant.Double)])
telha.updateFields()
lote = []
for orig, cx in zip(pred3857.getFeatures(), caixas.getFeatures()):
    ft = QgsFeature(telha.fields())
    ft.setGeometry(orig.geometry())
    larg, alt = float(cx['width']), float(cx['height'])
    # 'height' e sempre o lado longo, e 'angle' e o azimute dele, horario a partir
    # do norte, em (0, 180] — nunca 0.
    # comp e larg alimentam o telhado em SVG: sao a largura e a altura do marcador
    ft.setAttributes([float(cx['angle']), (alt / larg) if larg else 1.0, alt, larg])
    lote.append(ft)
telha.dataProvider().addFeatures(lote)
telha.updateExtents()
print('predios com rumo:', telha.featureCount())

base = corre('native:buffer', {'INPUT': pred3857, 'DISTANCE': 85, 'SEGMENTS': 4,
                               'JOIN_STYLE': 1, 'DISSOLVE': True})
base = corre('native:buffer', {'INPUT': base, 'DISTANCE': -58, 'SEGMENTS': 4,
                               'JOIN_STYLE': 1, 'DISSOLVE': False})
base = corre('native:clip', {'INPUT': base, 'OVERLAY': terra})
base.setName('base')

# -------------------------------------------------------- os navios de 1941
NAVIOS = [   # lat, lon, rumo, eslora, boca, nome
    (21.3690, -157.9530, 160, 177, 29, 'Nevada'),
    (21.3670, -157.9512, 160, 185, 30, 'Arizona'),
    (21.3654, -157.9502, 160, 190, 33, 'West Virginia'),
    (21.3638, -157.9504, 160, 177, 32, 'Oklahoma'),
    (21.3622, -157.9513, 160, 190, 33, 'California'),
    (21.3606, -157.9598, 60,  159, 32, 'Utah'),
    (21.3538, -157.9566, 25,  185, 32, 'Pennsylvania'),
]
navios = None
if NAVIOS_ON:
    navios = mem('navios', 'Polygon', 'EPSG:4326')
    navios.dataProvider().addAttributes([QgsField('nome', QVariant.String)]); navios.updateFields()
    MPD = 111320.0
    for lat, lon, rumo, loa, boca, nome in NAVIOS:
        a = math.radians(rumo)
        ux, uy = math.sin(a), math.cos(a)
        vx, vy = math.cos(a), -math.sin(a)
        kx = MPD * math.cos(math.radians(lat))
        casco = []
        for sl, sb in ((.5, .12), (.42, .5), (-.5, .5), (-.5, -.5), (.42, -.5), (.5, -.12)):
            casco.append(QgsPointXY(lon + (ux * loa * sl + vx * boca * sb) / kx,
                                    lat + (uy * loa * sl + vy * boca * sb) / MPD))
        ft = QgsFeature(navios.fields()); ft.setGeometry(QgsGeometry.fromPolygonXY([casco]))
        ft.setAttributes([nome]); navios.dataProvider().addFeature(ft)
    navios.updateExtents()

# ------------------------------------------------------------------- o mar
# A agua e geometria de verdade, nao a cor de fundo: so assim ela aceita textura.
#
# E ela leva a TERRA COMO FUROS, o que nao e capricho: assim o shapeburst mede a
# distancia ate a borda mais proxima, que dentro da baia e a linha de costa, e o
# raso vira um degrade saindo de cada praia em vez de uma faixa de largura fixa.
mar = mem('mar', 'Polygon', 'EPSG:4326')
mg = QgsGeometry.fromRect(QgsRectangle(W - .25, S - .25, E + .25, N + .25))
fm = QgsFeature(); fm.setGeometry(mg); mar.dataProvider().addFeature(fm)
mar.updateExtents()
mar = corre('native:reprojectlayer', {'INPUT': mar, 'TARGET_CRS': MERC})
mar = corre('native:difference', {'INPUT': mar, 'OVERLAY': terra})
mar.setName('mar')

# ---------------------------------------- gravar em disco antes de estilizar
# Camada de memoria nao sobrevive dentro de um projeto: ao reabrir o .qgz o
# QGIS acharia a referencia e nao os dados. Entao vira arquivo.
def grava(layer, nome):
    """
    Grava a camada em GeoPackage, SOBRESCREVENDO no lugar.

    Apagar-e-recriar e fragil aqui: o OneDrive segura o arquivo da rodada
    anterior, o `os.remove` falha, e entao tanto o driver do GeoJSON quanto o do
    GPKG se recusam a criar por cima — a rodada inteira morre no meio. O
    QgsVectorFileWriter com CreateOrOverwriteFile abre o arquivo para escrita em
    vez de desligar e religar, e passa por cima do cadeado. O caminho antigo fica
    de reserva, para o caso de o writer nao existir nesta versao.
    """
    caminho = os.path.join(HERE, nome + '.gpkg')
    op = QgsVectorFileWriter.SaveVectorOptions()
    op.driverName = 'GPKG'
    op.layerName = nome
    op.fileEncoding = 'UTF-8'
    op.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    ret = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, caminho, QgsProject.instance().transformContext(), op)
    erro = ret[0] if isinstance(ret, (tuple, list)) else ret
    if erro != QgsVectorFileWriter.NoError:
        for _ in range(8):                        # plano B: o caminho antigo
            if not os.path.exists(caminho): break
            try: os.remove(caminho); break
            except OSError: time.sleep(0.5)
        processing.run('native:savefeatures', {'INPUT': layer, 'OUTPUT': caminho})
    v = QgsVectorLayer(caminho + '|layername=' + nome, nome, 'ogr')
    if not v.isValid(): v = QgsVectorLayer(caminho, nome, 'ogr')
    if not v.isValid():
        raise IOError('nao consegui reabrir ' + caminho)
    return v

terra = grava(terra, 'terra')
base = grava(base, 'base')
mar = grava(mar, 'mar')
predios = grava(telha, 'predio')                  # a versao com o campo 'rumo'
if navios is not None: navios = grava(navios, 'navios')

# ============================================================== VESTIR TUDO
verde, aero, pier, via, agua_int = load('verde'), load('aero'), load('pier'), load('via'), load('agua')
# A mata nao partilha aresta com ninguem, entao pode ondular sozinha — mas em
# 3857, que e onde o mapa desenha; ela vem do convert.mjs em 4326.
if SINUOSO_ON and verde:
    verde = SN.ondula_camada(corre('native:reprojectlayer', {'INPUT': verde, 'TARGET_CRS': MERC}),
                             11.0, 130.0, 777, 2, 25.0)

veste(mar, *agua(HERE, raso_mm=7.0))
veste(terra, *terreno(HERE), efeito=sombra(1.4, 3.4, SOMBRA, 0.45, 125))
veste(base, *patio(HERE))
if verde: veste(verde, *mata(HERE))
if aero:  veste(aero, *campo(HERE))
if pier:  veste(pier, *cais(HERE))
if agua_int: veste(agua_int, simples(RASO))
if via:   via_dupla(via)
telhados(predios, HERE)
if navios is not None: veste(navios, simples('#43433f', '#1b1b1a', 0.3))

# A granulacao de papel e uma camada como outra qualquer: o retangulo do mar
# outra vez, no topo de tudo, so com o ladrilho de grao. E ela que amarra as
# camadas — sem isso cada area parece recortada e colada por cima da outra.
graozinho = QgsVectorLayer(mar.source(), 'papel', 'ogr')
veste(graozinho, *papel(HERE))

ordem = [l for l in (graozinho, navios, predios, via, pier, aero, agua_int,
                     verde, base, terra, mar) if l]

proj = QgsProject.instance(); proj.setCrs(MERC)
raiz = proj.layerTreeRoot()
for l in ordem:                                   # 'ordem' vem de cima para baixo
    proj.addMapLayer(l, False); raiz.addLayer(l)
c = QColor(MAR)
for parte, val in (('Red', c.red()), ('Green', c.green()), ('Blue', c.blue())):
    proj.writeEntry('Gui', '/CanvasColor%sPart' % parte, val)
qgz = os.path.join(HERE, 'pearl-harbor.qgz')
proj.write(qgz)
print('projeto ->', qgz)

# ============================================================== RENDER
rS, rW, rN, rE, nome = (float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]),
                        float(sys.argv[4]), sys.argv[5]) if len(sys.argv) > 5 else (S, W, N, E, 'pearl-harbor')
ext = tr.transformBoundingBox(QgsRectangle(rW, rS, rE, rN))
LARG = 3000
ALT = int(LARG * ext.height() / ext.width())

camadas = list(ordem)
if MOLDURA_ON:
    # A borda de papel: um anel branco cuja aresta interna treme um pouco.
    random.seed(7)
    esp = ext.width() * 0.030
    ix0, iy0 = ext.xMinimum() + esp, ext.yMinimum() + esp
    ix1, iy1 = ext.xMaximum() - esp, ext.yMaximum() - esp
    jit, passo = esp * 0.16, esp * 0.55
    dentro = []
    def borda(x0, y0, x1, y1):
        d = math.hypot(x1 - x0, y1 - y0); n = max(2, int(d / passo))
        for k in range(n):
            t = k / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            nx, ny = (y1 - y0) / d, -(x1 - x0) / d          # normal, apontando para fora
            r = random.uniform(-jit, jit)
            dentro.append(QgsPointXY(x + nx * r, y + ny * r))
    borda(ix0, iy0, ix1, iy0); borda(ix1, iy0, ix1, iy1)
    borda(ix1, iy1, ix0, iy1); borda(ix0, iy1, ix0, iy0)
    dentro.append(dentro[0])
    fora = [QgsPointXY(ext.xMinimum(), ext.yMinimum()), QgsPointXY(ext.xMaximum(), ext.yMinimum()),
            QgsPointXY(ext.xMaximum(), ext.yMaximum()), QgsPointXY(ext.xMinimum(), ext.yMaximum()),
            QgsPointXY(ext.xMinimum(), ext.yMinimum())]
    mold = mem('papel', 'Polygon')
    fp = QgsFeature(); fp.setGeometry(QgsGeometry.fromPolygonXY([fora, dentro]))
    mold.dataProvider().addFeature(fp); mold.updateExtents()
    veste(mold, simples(PAPEL), efeito=sombra(1.1, 3.0, '#14343a', 0.40, 315))
    camadas.insert(0, mold)

ms = QgsMapSettings()
ms.setLayers(camadas)
ms.setBackgroundColor(QColor(MAR))
ms.setOutputSize(QSize(LARG, ALT))
ms.setOutputDpi(96)                               # as texturas estao em mm: o dpi define a escala delas
ms.setExtent(ext)
ms.setDestinationCrs(MERC)
job = QgsMapRendererParallelJob(ms); job.start(); job.waitForFinished()
out = os.path.join(HERE, nome + '.png')
job.renderedImage().save(out)
print('->', out, LARG, 'x', ALT)
qgs.exitQgis()
