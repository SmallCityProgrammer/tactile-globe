# pearl.py — Pearl Harbor no estilo Operations Room.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" pearl.py
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" pearl.py 21.348 -157.978 21.383 -157.933 ford-island
#
# O OSM nao tem o porto como poligono de agua: so ha linha de costa. Entao a
# terra e obtida poligonizando (costa + retangulo da moldura) e ficando com as
# faces onde a DENSIDADE de predio e alta — o mar tem quase nenhum.
#
# O estilo esta todo na secao ESTILO, em um lugar so. A ideia da referencia:
#   agua   = teal com listra horizontal fina (a "lona") + halo claro de raso
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
                       QgsDrawSourceEffect, QgsUnitTypes, QgsSpatialIndex)
from qgis.PyQt.QtCore import QSize, QVariant
from qgis.PyQt.QtGui import QColor

HERE = os.path.dirname(os.path.abspath(__file__))
S, W, N, E = 21.325, -158.030, 21.400, -157.920          # a moldura, em graus
WGS = QgsCoordinateReferenceSystem('EPSG:4326')
MERC = QgsCoordinateReferenceSystem('EPSG:3857')
NAVIOS_ON = False        # os navios de 1941; ligue se quiser os marcos de volta
MOLDURA_ON = True        # a borda branca rasgada da referencia

qgs = QgsApplication([], False); qgs.initQgis(); Processing.initialize()
tr = QgsCoordinateTransform(WGS, MERC, QgsProject.instance())

# ============================================================== PALETA
MAR        = '#2b8492'   # o corpo da agua
MAR_LISTRA = '#3a95a2'   # a listra clara da "lona"
MAR_TRAMA  = '#24747f'   # a contra-listra, quase invisivel
RASO       = '#57aab3'   # o halo de agua rasa encostando na costa
TERRA      = '#8d9a4e'   # o oliva do terreno
AREIA      = '#cdc08d'   # a borda de areia, para onde o oliva esmaece
MATA       = '#6f8340'   # a mata
COPA       = '#5b6f33'   # as copas salpicadas na mata
BASE       = '#c3b283'   # o bege da area construida (nao e a terra!)
PISTA      = '#6d6146'   # asfalto do campo de aviacao
CAIS       = '#a89c82'
VIA        = '#9b968c'
VIA_ORLA   = '#7f7a71'
PREDIO     = '#7b7062'
SOMBRA     = '#1b5a63'   # a sombra da terra cai na agua, entao e escura e teal
PAPEL      = '#f3efe1'   # a moldura

# ============================================================== ESTILO
MM = QgsUnitTypes.RenderMillimeters

def _mm(o, *setters):
    for s in setters:
        if hasattr(o, s): getattr(o, s)(MM)
    return o

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
    if borda: sl.setStrokeColor(QColor(borda)); sl.setStrokeWidth(larg); _mm(sl, 'setStrokeWidthUnit')
    return sl

def veste(layer, *camadas, efeito=None):
    """Monta um QgsFillSymbol com as camadas dadas, de baixo para cima."""
    s = QgsFillSymbol(); s.deleteSymbolLayer(0)
    for c in camadas: s.appendSymbolLayer(c)
    # o efeito mora na camada de simbolo, nao no simbolo: vai na primeira, que e o corpo
    if efeito is not None: camadas[0].setPaintEffect(efeito)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer

def agua_lona():
    """O teal com a trama. Tres camadas: corpo, listra horizontal, contra-listra."""
    corpo = simples(MAR)
    listra = QgsLinePatternFillSymbolLayer()
    listra.setLineAngle(0); listra.setDistance(1.6); listra.setLineWidth(0.62)
    listra.setColor(QColor(MAR_LISTRA)); _mm(listra, 'setDistanceUnit', 'setLineWidthUnit')
    trama = QgsLinePatternFillSymbolLayer()
    trama.setLineAngle(90); trama.setDistance(3.2); trama.setLineWidth(0.22)
    trama.setColor(QColor(MAR_TRAMA)); _mm(trama, 'setDistanceUnit', 'setLineWidthUnit')
    try: trama.setOpacity(0.35)
    except AttributeError: pass
    return [corpo, listra, trama]

def costa_areia():
    """
    A praia. Duas camadas: um fundo de areia que transborda a costa por um traco
    largo (entao a areia aparece dos dois lados da linha d'agua), e por cima o
    shapeburst, que leva a areia ao oliva no primeiro tanto de metros de terra.
    Medidas em mm: a praia tem largura constante na tela, como no desenho.
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
    for s, v in (('setRandomDeviationX', 0.5), ('setRandomDeviationY', 0.5)):
        if hasattr(pp, s):
            getattr(pp, s)(v)
            _mm(pp, s.replace('set', 'set').replace('Deviation', 'Deviation') + 'Unit')
    pp.setSubSymbol(ms)
    return pp

def via_dupla(layer):
    orla = QgsSimpleLineSymbolLayer(QColor(VIA_ORLA)); orla.setWidth(0.62)
    nucleo = QgsSimpleLineSymbolLayer(QColor(VIA)); nucleo.setWidth(0.38)
    s = QgsLineSymbol(); s.deleteSymbolLayer(0)
    for c in (orla, nucleo):
        c.setPenCapStyle(1); c.setPenJoinStyle(1); _mm(c, 'setWidthUnit'); s.appendSymbolLayer(c)
    layer.setRenderer(QgsSingleSymbolRenderer(s)); return layer

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

# -------------------------------------------------- o bege da area construida
# No Operations Room o bege nao e "a terra", e o patio da base: o chao batido
# em volta dos galpoes. Entao ele se deduz dos predios — engorda cada um,
# funde tudo, encolhe de volta (isso arredonda e fecha os vaos) e corta na costa.
pred3857 = corre('native:reprojectlayer', {'INPUT': predios, 'TARGET_CRS': MERC})
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
mar = mem('mar', 'Polygon', 'EPSG:4326')
mg = QgsGeometry.fromRect(QgsRectangle(W - .25, S - .25, E + .25, N + .25))
fm = QgsFeature(); fm.setGeometry(mg); mar.dataProvider().addFeature(fm)
mar.updateExtents()

# O halo de raso: e a propria terra, desenhada so como traco largo e macio,
# por baixo dela mesma. Sai de graca e da o contorno claro da referencia.
raso = QgsVectorLayer(terra.source(), 'raso', terra.providerType()) if terra.providerType() == 'ogr' else None

# ---------------------------------------- gravar em disco antes de estilizar
# Camada de memoria nao sobrevive dentro de um projeto: ao reabrir o .qgz o
# QGIS acharia a referencia e nao os dados. Entao vira arquivo.
def grava(layer, nome):
    # GeoPackage, e nao GeoJSON: o driver do GeoJSON se recusa a sobrescrever, e
    # o OneDrive as vezes ainda segura o arquivo da rodada anterior.
    caminho = os.path.join(HERE, nome + '.gpkg')
    for _ in range(6):
        if not os.path.exists(caminho): break
        try: os.remove(caminho); break
        except OSError: time.sleep(0.4)
    processing.run('native:savefeatures', {'INPUT': layer, 'OUTPUT': caminho})
    v = QgsVectorLayer(caminho + '|layername=' + nome, nome, 'ogr')
    if not v.isValid(): v = QgsVectorLayer(caminho, nome, 'ogr')
    return v if v.isValid() else layer

terra = grava(terra, 'terra')
base = grava(base, 'base')
mar = grava(mar, 'mar')
if navios is not None: navios = grava(navios, 'navios')
raso = QgsVectorLayer(terra.source(), 'raso', 'ogr')

# ============================================================== VESTIR TUDO
verde, aero, pier, via, agua = load('verde'), load('aero'), load('pier'), load('via'), load('agua')

veste(mar, *agua_lona())
veste(raso, halo_raso())
veste(terra, *costa_areia(), efeito=sombra(1.4, 3.4, SOMBRA, 0.45, 125))
veste(base, simples(BASE))
if verde: veste(verde, simples(MATA), copas())
if aero:  veste(aero, simples(PISTA))
if pier:  veste(pier, simples(CAIS, '#8a7f68', 0.12))
if agua:  veste(agua, simples(MAR_LISTRA))
if via:   via_dupla(via)
veste(predios, simples(PREDIO))
if navios is not None: veste(navios, simples('#43433f', '#1b1b1a', 0.3))

ordem = [l for l in (navios, predios, via, pier, aero, agua, verde, base, terra, raso, mar) if l]

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
