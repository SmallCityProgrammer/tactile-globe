# ardenas.py — Bastogne e o Bois Jacques, no estilo Operations Room.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" ardenas.py
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" ardenas.py 50.020 5.700 50.050 5.745 foy
#
# IRMAO DO pearl.py, E DIFERENTE ONDE IMPORTA
# La a terra tinha que ser DEDUZIDA: o OSM nao tem o porto como poligono de agua,
# so ha linha de costa, e a terra saia de poligonizar a costa contra a moldura e
# ficar com as faces onde havia densidade de predio. Aqui nao ha costa nenhuma —
# a terra e o quadro inteiro. Some o passo mais delicado do outro mapa, e no
# lugar dele entra o que aquele nao tinha: 2340 talhoes de campo, 168 sebes, uma
# aldeia de 6681 predios.
#
# A ONDULACAO MUDA DE DONO, tambem. No Pearl era a TERRA que ondulava, e o mar e
# o patio se refaziam a partir dela. Aqui a terra E a moldura: ondula-la
# serrilharia a aresta do quadro. Quem ondula e o campo e a mata, que nao
# partilham contorno com ninguem e podem ondular por conta propria.
import os, sys, glob, math, random, time
for _p in glob.glob(os.path.join(os.environ.get('QGIS_PREFIX_PATH', r'C:/Program Files/QGIS 3.44.12/apps/qgis-ltr'), 'python', 'plugins')) + glob.glob(r'C:/Program Files/QGIS*/apps/qgis*/python/plugins'):
    if _p not in sys.path: sys.path.append(_p)
import processing
from processing.core.Processing import Processing
from qgis.core import (QgsApplication, QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry,
                       QgsPointXY, QgsField, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsRectangle, QgsMapSettings, QgsMapRendererParallelJob,
                       QgsVectorFileWriter, QgsUnitTypes)
from qgis.PyQt.QtCore import QSize, QVariant
from qgis.PyQt.QtGui import QColor

HERE = os.path.dirname(os.path.abspath(__file__))
S, W, N, E = 49.980, 5.680, 50.065, 5.795         # Bastogne, Foy, Bois Jacques
WGS = QgsCoordinateReferenceSystem('EPSG:4326')
MERC = QgsCoordinateReferenceSystem('EPSG:3857')
MOLDURA_ON = True
SINUOSO_ON = True

qgs = QgsApplication([], False); qgs.initQgis(); Processing.initialize()
tr = QgsCoordinateTransform(WGS, MERC, QgsProject.instance())

# Como ST, e nao 'from estilo import *'. Aqui as camadas se chamam campo, mata,
# via, sebe — exatamente os nomes das funcoes de estilo. Com o import estrelado a
# variavel tapa a funcao, e o erro so aparece na hora da chamada. Ja aconteceu
# duas vezes no mapa irmao, com 'agua' e com 'predios'.
import estilo as ST

# ============================================================== DADOS
def load(name):
    v = QgsVectorLayer(os.path.join(HERE, name + '.geojson'), name, 'ogr')
    return v if v.isValid() and v.featureCount() else None

def mem(name, kind, crs='EPSG:3857'):
    return QgsVectorLayer('%s?crs=%s' % (kind, crs), name, 'memory')

def corre(alg, par):
    par = dict(par); par['OUTPUT'] = 'memory:'
    return processing.run(alg, par)['OUTPUT']

def para3857(layer):
    return corre('native:reprojectlayer', {'INPUT': layer, 'TARGET_CRS': MERC})

# --------------------------------------------------------------- o quadro
# A terra e o retangulo, e so. Sem poligonizar, sem contar predio: em terra
# firme nao ha o que deduzir.
quadro = QgsGeometry.fromRect(tr.transformBoundingBox(QgsRectangle(W, S, E, N)))
terra = mem('terra', 'Polygon')
ff = QgsFeature(); ff.setGeometry(quadro); terra.dataProvider().addFeature(ff)
terra.updateExtents()

campo, mata, urbano = load('campo'), load('mata'), load('urbano')
via, ferro, rio, sebe = load('via'), load('ferro'), load('rio'), load('sebe')
agua_p, predios = load('agua'), load('predio')
print('campo %d | mata %d | urbano %d | via %d | sebe %d | predio %d'
      % (campo.featureCount(), mata.featureCount(), urbano.featureCount(),
         via.featureCount(), sebe.featureCount() if sebe else 0, predios.featureCount()))

# ------------------------------------------------- ondular campo e mata
# Eles nao partilham aresta com ninguem: o talhao vizinho e outro poligono, e um
# vao de um metro entre dois campos nao aparece. Entao podem ondular sozinhos —
# e sao justamente eles que trazem o "tudo em L" do OSM.
if SINUOSO_ON:
    import sinuoso as SN
    t0 = time.time()
    campo = SN.ondula_camada(para3857(campo), 9.0, 140.0, 1944, 2, 20.0)
    mata = SN.ondula_camada(para3857(mata), 11.0, 130.0, 777, 2, 20.0)
    print('ondulados em %.1f s' % (time.time() - t0))
else:
    campo, mata = para3857(campo), para3857(mata)

# -------------------------------------- o rumo do eixo longo de cada predio
# Em 3857, que e o que o mapa desenha. Em 4326 o esticao em Y vira o eixo longo
# dos predios quase quadrados e a nervura corre atravessada neles. O algoritmo
# preserva a ordem de entrada mas renumera os fid, entao o casamento e posicional.
pred3857 = para3857(predios)
caixas = corre('native:orientedminimumboundingbox', {'INPUT': pred3857})
telha = mem('predio', 'Polygon')
telha.dataProvider().addAttributes([QgsField('rumo', QVariant.Double),
                                    QgsField('alonga', QVariant.Double),
                                    QgsField('comp', QVariant.Double),
                                    QgsField('larg', QVariant.Double)])
telha.updateFields()
lote = []
for orig, cx in zip(pred3857.getFeatures(), caixas.getFeatures()):
    ft = QgsFeature(telha.fields()); ft.setGeometry(orig.geometry())
    larg, alt = float(cx['width']), float(cx['height'])   # 'height' e sempre o lado longo
    # alonga decide QUAL telhado a feicao recebe, e nao so o tamanho dele
    ft.setAttributes([float(cx['angle']), (alt / larg) if larg else 1.0, alt, larg])
    lote.append(ft)
telha.dataProvider().addFeatures(lote); telha.updateExtents()
print('predios com rumo:', telha.featureCount())

# ---------------------------------------- gravar antes de estilizar
# Camada de memoria nao sobrevive dentro de um projeto: ao reabrir o .qgz o QGIS
# acharia a referencia e nao os dados. E sobrescreve no lugar, sem apagar antes:
# o OneDrive segura o arquivo da rodada anterior com frequencia, e ai tanto o
# GeoJSON quanto o GPKG se recusam a criar por cima.
def grava(layer, nome):
    caminho = os.path.join(HERE, nome + '.gpkg')
    op = QgsVectorFileWriter.SaveVectorOptions()
    op.driverName = 'GPKG'; op.layerName = nome; op.fileEncoding = 'UTF-8'
    op.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    ret = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, caminho, QgsProject.instance().transformContext(), op)
    erro = ret[0] if isinstance(ret, (tuple, list)) else ret
    if erro != QgsVectorFileWriter.NoError:
        for _ in range(8):
            if not os.path.exists(caminho): break
            try: os.remove(caminho); break
            except OSError: time.sleep(0.5)
        processing.run('native:savefeatures', {'INPUT': layer, 'OUTPUT': caminho})
    v = QgsVectorLayer(caminho + '|layername=' + nome, nome, 'ogr')
    if not v.isValid(): v = QgsVectorLayer(caminho, nome, 'ogr')
    if not v.isValid(): raise IOError('nao consegui reabrir ' + caminho)
    return v

terra = grava(terra, 'terra')
campo = grava(campo, 'campo')
mata = grava(mata, 'mata')
predios = grava(telha, 'predio')

# ============================================================== VESTIR
ST.veste(terra, *ST.chao(HERE))
ST.veste(campo, *ST.campo(HERE))
ST.veste(mata, *ST.mata(HERE))
if urbano: ST.veste(urbano, *ST.urbano(HERE))
if agua_p: ST.veste(agua_p, *ST.agua(HERE))
if via:    ST.via(via)
if rio:    ST.rio(rio)
if ferro:  ST.ferro(ferro)
if sebe:   ST.sebe(sebe)
ST.telhados(predios, HERE)

graozinho = QgsVectorLayer(terra.source(), 'papel', 'ogr')
ST.veste(graozinho, *ST.papel(HERE))

ordem = [l for l in (graozinho, predios, sebe, ferro, via, rio, agua_p,
                     urbano, mata, campo, terra) if l]

proj = QgsProject.instance(); proj.setCrs(MERC)
raiz = proj.layerTreeRoot()
for l in ordem:
    proj.addMapLayer(l, False); raiz.addLayer(l)
c = QColor(ST.FUNDO)
for parte, val in (('Red', c.red()), ('Green', c.green()), ('Blue', c.blue())):
    proj.writeEntry('Gui', '/CanvasColor%sPart' % parte, val)
qgz = os.path.join(HERE, 'bastogne.qgz'); proj.write(qgz)
print('projeto ->', qgz)

# ============================================================== RENDER
rS, rW, rN, rE, nome = (float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]),
                        float(sys.argv[4]), sys.argv[5]) if len(sys.argv) > 5 else (S, W, N, E, 'bastogne')
ext = tr.transformBoundingBox(QgsRectangle(rW, rS, rE, rN))
LARG = 3000
ALT = int(LARG * ext.height() / ext.width())

camadas = list(ordem)
if MOLDURA_ON:
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
            nx, ny = (y1 - y0) / d, -(x1 - x0) / d
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
    ST.veste(mold, ST.simples(ST.PAPEL), efeito=ST.sombra(1.1, 3.0, '#2a2f24', 0.35, 315))
    camadas.insert(0, mold)

ms = QgsMapSettings()
ms.setLayers(camadas)
ms.setBackgroundColor(QColor(ST.FUNDO))
ms.setOutputSize(QSize(LARG, ALT)); ms.setOutputDpi(96)
ms.setExtent(ext); ms.setDestinationCrs(MERC)
job = QgsMapRendererParallelJob(ms); job.start(); job.waitForFinished()
out = os.path.join(HERE, nome + '.png')
job.renderedImage().save(out)
print('->', out, LARG, 'x', ALT)
qgs.exitQgis()
