# provas.py — as receitas de agua lado a lado, no mesmo recorte.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" provas.py
#
# Nao refaz a terra: le o que pearl.py ja gravou (terra.gpkg, base.gpkg, mar.gpkg
# e os geojson do convert.mjs). Entao roda em segundos e serve so para escolher.
import os, sys, glob
for _p in glob.glob(os.path.join(os.environ.get('QGIS_PREFIX_PATH', r'C:/Program Files/QGIS 3.44.12/apps/qgis-ltr'), 'python', 'plugins')) + glob.glob(r'C:/Program Files/QGIS*/apps/qgis*/python/plugins'):
    if _p not in sys.path: sys.path.append(_p)
from qgis.core import (QgsApplication, QgsVectorLayer, QgsProject, QgsRectangle,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsMapSettings, QgsMapRendererParallelJob)
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QColor, QImage, QPainter, QFont

HERE = os.path.dirname(os.path.abspath(__file__))
WGS = QgsCoordinateReferenceSystem('EPSG:4326')
MERC = QgsCoordinateReferenceSystem('EPSG:3857')

qgs = QgsApplication([], False); qgs.initQgis()
from estilo import *

tr = QgsCoordinateTransform(WGS, MERC, QgsProject.instance())

def gpkg(nome):
    v = QgsVectorLayer(os.path.join(HERE, nome + '.gpkg') + '|layername=' + nome, nome, 'ogr')
    return v if v.isValid() else None

def geo(nome):
    v = QgsVectorLayer(os.path.join(HERE, nome + '.geojson'), nome, 'ogr')
    return v if v.isValid() and v.featureCount() else None

terra, base, mar = gpkg('terra'), gpkg('base'), gpkg('mar')
raso = QgsVectorLayer(terra.source(), 'raso', 'ogr')
verde, aero, pier, via, agua_int, predio = geo('verde'), geo('aero'), geo('pier'), geo('via'), geo('agua'), geo('predio')

veste(raso, halo_raso())
veste(terra, *costa_areia(), efeito=sombra(1.4, 3.4, SOMBRA, 0.45, 125))
veste(base, simples(BASE))
if verde: veste(verde, simples(MATA), copas())
if aero:  veste(aero, simples(PISTA))
if pier:  veste(pier, simples(CAIS, '#8a7f68', 0.12))
if agua_int: veste(agua_int, simples(MAR_CLARO))
if via:   via_dupla(via)
veste(predio, simples(PREDIO))

ordem = [l for l in (predio, via, pier, aero, agua_int, verde, base, terra, raso, mar) if l]

# Um recorte com bastante agua aberta e costa: a boca do canal e Ford Island.
REC = QgsRectangle(-157.9800, 21.3480, -157.9330, 21.3830)
ext = tr.transformBoundingBox(REC)
LARG = 1000
ALT = int(LARG * ext.height() / ext.width())

RECEITAS = ['liso', 'lona', 'mancha', 'mancha-espuma']
quadros = []
for e in RECEITAS:
    veste(mar, *agua(HERE, e))
    ms = QgsMapSettings()
    ms.setLayers(ordem); ms.setBackgroundColor(QColor(MAR))
    ms.setOutputSize(QSize(LARG, ALT)); ms.setOutputDpi(96)
    ms.setExtent(ext); ms.setDestinationCrs(MERC)
    job = QgsMapRendererParallelJob(ms); job.start(); job.waitForFinished()
    quadros.append(job.renderedImage())
    print('ok', e)

# monta 2 x 2 com o nome de cada receita
G = 8
folha = QImage(LARG * 2 + G * 3, (ALT + 34) * 2 + G * 3, QImage.Format_RGB32)
folha.fill(QColor('#23303a'))
p = QPainter(folha)
p.setFont(QFont('Segoe UI', 15, QFont.Bold))
for i, (e, q) in enumerate(zip(RECEITAS, quadros)):
    x = G + (i % 2) * (LARG + G)
    y = G + (i // 2) * (ALT + 34 + G)
    p.setPen(QColor('#e9e4d2')); p.drawText(x + 4, y + 24, e)
    p.drawImage(x, y + 34, q)
p.end()
out = os.path.join(HERE, 'provas-agua.png')
folha.save(out)
print('->', out, folha.width(), 'x', folha.height())
qgs.exitQgis()
