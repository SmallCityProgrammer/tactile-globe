# -*- coding: utf-8 -*-
# carentan.py — Carentan no estilo Operations Room, para servir de palco.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" carentan.py
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" carentan.py holgate
#
# O QUE ESTE MAPA E
# A placa de fundo da cena de 12 de junho de 1944, 6h da manha: a Easy Company
# do 2/506 subindo do sudoeste, o entroncamento em T na ponta da Rue Holgate, e
# a cidade. O render sai com um arquivo .json do lado dizendo exatamente onde
# ele cai no mundo — e por ele que o estudio de cena prega os soldados em cima.
#
# O QUE MUDA EM RELACAO AO pearl.py
# La o OSM nao tinha o porto como poligono e a terra precisava ser deduzida
# poligonizando a linha de costa. Aqui e o contrario: Carentan e cidade de rio,
# a agua vem pronta do OSM, e a TERRA E O RETANGULO INTEIRO. Some o passo mais
# frágil do pipeline do Pacifico.
#
# O estilo mora inteiro em estilo.py.
import os, sys, glob, math, json, time
# o plugin 'processing' nao esta no path do lancador; mora em apps/qgis*/python/plugins
for _p in glob.glob(os.path.join(os.environ.get('QGIS_PREFIX_PATH', r'C:/Program Files/QGIS 3.44.12/apps/qgis-ltr'), 'python', 'plugins')) + glob.glob(r'C:/Program Files/QGIS*/apps/qgis*/python/plugins'):
    if _p not in sys.path: sys.path.append(_p)
import processing
from processing.core.Processing import Processing
from qgis.core import (QgsApplication, QgsVectorLayer, QgsProject, QgsFeature, QgsGeometry,
                       QgsPointXY, QgsField, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsRectangle, QgsMapSettings, QgsMapRendererParallelJob, QgsVectorFileWriter)
from qgis.PyQt.QtCore import QSize, QVariant
from qgis.PyQt.QtGui import QColor

HERE = os.path.dirname(os.path.abspath(__file__))
WGS = QgsCoordinateReferenceSystem('EPSG:4326')
MERC = QgsCoordinateReferenceSystem('EPSG:3857')

# O retangulo que o fetch.mjs baixou. A terra e ele; nada fora disso existe.
S, W, N, E = 49.285, -1.283, 49.322, -1.220

# ---------------------------------------------------------------- OS QUADROS
# centro em graus, largura NO CHAO em km. A altura sai da proporcao — 16:9, para
# a placa cair inteira num quadro de video sem sobra.
#
# 'carentan' cobre a hora inteira do trecho 9:00-11:00 do video: a base de
# partida em La Billonnerie (sudoeste, embaixo a esquerda), a estrada de Periers
# subindo, o entroncamento em T, a Rue Holgate entrando na cidade, o centro, e a
# borda norte por onde desceram os que vinham do outro lado as 7h.
QUADROS = {
    'carentan': (-1.24500, 49.30295, 3.18),   # o assalto das 6h inteiro — o padrao
    'holgate':  (-1.24737, 49.30264, 1.10),   # so o entroncamento em T e a rua
    'periers':  (-1.25142, 49.29788, 1.40),   # a subida desde La Billonnerie
}
PADRAO = 'carentan'
LARG = 4096                  # px. Potencia de dois: a placa vira textura no estudio
DPI = 96                     # as texturas estao em mm — o dpi define a escala delas
ASPECTO = 16.0 / 9.0
MOLDURA_ON = False           # a borda de papel rasgado do Pacifico.

nome = sys.argv[1] if len(sys.argv) > 1 else PADRAO
if nome not in QUADROS:
    raise SystemExit('quadro %r nao existe. Ha: %s' % (nome, ', '.join(QUADROS)))
Q_LON, Q_LAT, Q_KM = QUADROS[nome]

qgs = QgsApplication([], False); qgs.initQgis(); Processing.initialize()
tr = QgsCoordinateTransform(WGS, MERC, QgsProject.instance())
inv = QgsCoordinateTransform(MERC, WGS, QgsProject.instance())

from estilo import *   # a paleta e os simbolos moram la

# ============================================================== O ENQUADRAMENTO
# O 3857 estica Y por 1/cos(lat) — 1,53 nesta latitude. Entao um metro de chao
# vale 1/cos(lat) unidades de mapa, e e por isso que a largura em km tem que ser
# convertida antes de virar retangulo. Como o Mercator e conforme, o desenho sai
# com a forma certa: o que muda e so a escala, igual nas duas direcoes.
c = tr.transform(QgsPointXY(Q_LON, Q_LAT))
esticao = 1.0 / math.cos(math.radians(Q_LAT))
larg_mapa = Q_KM * 1000.0 * esticao
alt_mapa = larg_mapa / ASPECTO
ext = QgsRectangle(c.x() - larg_mapa / 2, c.y() - alt_mapa / 2,
                   c.x() + larg_mapa / 2, c.y() + alt_mapa / 2)
ALT = int(round(LARG / ASPECTO))

# metros de chao por milimetro de tela: e disto que sai a escala do bocage
m_por_mm = (Q_KM * 1000.0) / (LARG / DPI * 25.4)
print('quadro %s: %.2f x %.2f km, %d x %d px, %.2f m/px, %.1f m por mm de tela'
      % (nome, Q_KM, Q_KM / ASPECTO, LARG, ALT, Q_KM * 1000.0 / LARG, m_por_mm))

# ============================================================== DADOS
def load(n):
    v = QgsVectorLayer(os.path.join(HERE, n + '.geojson'), n, 'ogr')
    return v if v.isValid() and v.featureCount() else None

def mem(n, kind, crs='EPSG:3857'):
    return QgsVectorLayer('%s?crs=%s' % (kind, crs), n, 'memory')

def corre(alg, par):
    par = dict(par); par['OUTPUT'] = 'memory:'
    return processing.run(alg, par)['OUTPUT']

agua_l, rio_l = load('agua'), load('rio')
brejo_l, mata_l = load('brejo'), load('mata')
via_l, trilho_l, sebe_l = load('via'), load('trilho'), load('sebe')
predio_l, cais_l = load('predio'), load('cais')

# O campo.geojson traz duas coisas diferentes com o mesmo nome, e elas nao podem
# ir na mesma altura da pilha: o prado aberto tem que ficar DEBAIXO das sebes do
# bocage, e o parque e o cemiterio tem que ficar POR CIMA do chao da cidade,
# senao somem no bege. Mesmo arquivo, dois subconjuntos.
ABERTO = "'meadow','farmland','farmyard','grass','orchard','vineyard','greenfield','recreation_ground','golf_course'"
URBANO = "'park','cemetery','pitch','garden','village_green','allotments'"
campo_l, verde_l = load('campo'), load('campo')
if campo_l: campo_l.setSubsetString('"g" IN (%s)' % ABERTO); campo_l.setName('campo')
if verde_l: verde_l.setSubsetString('"g" IN (%s)' % URBANO); verde_l.setName('verde')
if campo_l and not campo_l.featureCount(): campo_l = None
if verde_l and not verde_l.featureCount(): verde_l = None

# ---------------------------------------------------------------- o chao
# A terra e o retangulo do fetch, e pronto. Sem poligonizar, sem contar predios:
# Carentan nao tem linha de costa dentro do recorte, so rio.
chao_l = mem('chao', 'Polygon', 'EPSG:4326')
f = QgsFeature(); f.setGeometry(QgsGeometry.fromRect(QgsRectangle(W, S, E, N)))
chao_l.dataProvider().addFeature(f); chao_l.updateExtents()
chao_l = corre('native:reprojectlayer', {'INPUT': chao_l, 'TARGET_CRS': MERC})
chao_l.setName('chao')

# ------------------------------------------------- o chao da cidade, dos predios
# Mesmo truque do bege de Pearl Harbor, com outro numero. La eram 85 m para fora
# e 58 de volta, porque a base tem galpoes soltos num campo. Aqui o quarteirao
# normando e denso: com 85 m a cidade inteira virava um borrao redondo e as ruas
# sumiam. Com 22 para fora e 14 de volta os quarteiroes se fecham, os quintais
# entram junto e as ruas largas continuam abertas.
pred3857 = corre('native:reprojectlayer', {'INPUT': predio_l, 'TARGET_CRS': MERC})
cidade_l = corre('native:buffer', {'INPUT': pred3857, 'DISTANCE': 22, 'SEGMENTS': 4,
                                   'JOIN_STYLE': 1, 'DISSOLVE': True})
cidade_l = corre('native:buffer', {'INPUT': cidade_l, 'DISTANCE': -14, 'SEGMENTS': 4,
                                   'JOIN_STYLE': 1, 'DISSOLVE': False})
cidade_l.setName('cidade')
print('predios:', predio_l.featureCount())

# ---------------------------------------------- gravar antes de estilizar
# Camada de memoria nao sobrevive dentro de um projeto: ao reabrir o .qgz o QGIS
# acharia a referencia e nao os dados. E GeoPackage, nao GeoJSON: o driver do
# GeoJSON se recusa a sobrescrever e o OneDrive as vezes ainda segura o arquivo
# da rodada anterior.
def grava(layer, n):
    caminho = os.path.join(HERE, n + '.gpkg')
    op = QgsVectorFileWriter.SaveVectorOptions()
    op.driverName = 'GPKG'; op.layerName = n; op.fileEncoding = 'UTF-8'
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
    v = QgsVectorLayer(caminho + '|layername=' + n, n, 'ogr')
    if not v.isValid(): v = QgsVectorLayer(caminho, n, 'ogr')
    if not v.isValid(): raise IOError('nao consegui reabrir ' + caminho)
    return v

chao_l = grava(chao_l, 'chao')
cidade_l = grava(cidade_l, 'cidade')

# ============================================================== VESTIR TUDO
malha, esc_bocage = malha_bocage(HERE, m_por_mm)
print('bocage: talhao de %.0f m -> ladrilho de %.1f mm de tela' % (TALHAO_M, esc_bocage))

veste(chao_l, *chao(malha, esc_bocage))
if campo_l:  veste(campo_l, *talhoes(malha, esc_bocage))
# A lavoura e as sebes sao uma camada propria, e usam a geometria do chao: o
# retangulo inteiro, so com os dois ladrilhos. Desenhadas uma vez so — ver
# cerca_viva.
cerca_l = QgsVectorLayer(chao_l.source(), 'cerca', 'ogr')
veste(cerca_l, *cerca_viva(malha, esc_bocage))
if brejo_l:  veste(brejo_l, *brejo(HERE))
veste(cidade_l, *cidade(HERE))
if verde_l:  veste(verde_l, *talhoes(malha, esc_bocage))
if mata_l:   veste(mata_l, *mata(HERE))
# A agua leva sombra INTERNA: aqui ela e o recorte e a terra e o fundo, entao a
# sombra tem que nascer na margem e cair para dentro do rio. Sombra projetada
# faria o canal parecer flutuar acima do campo.
if agua_l:   veste(agua_l, *agua(HERE), efeito=sombra_dentro(1.3, 3, SOMBRA, 0.55, 125))
if rio_l:    rio(rio_l)
if cais_l:   veste(cais_l, *cais(HERE))
if via_l:    via_dupla(via_l)
if trilho_l: ferrovia(trilho_l)
if sebe_l:   sebes(sebe_l)
telhados(predio_l)

# A granulacao de papel e uma camada como outra qualquer: o retangulo do chao
# outra vez, no topo de tudo, so com o ladrilho de grao. E ela que amarra as
# camadas — sem isso cada area parece recortada e colada por cima da outra.
graozinho = QgsVectorLayer(chao_l.source(), 'papel', 'ogr')
veste(graozinho, *papel(HERE))

# de cima para baixo.
ordem = [l for l in (graozinho, predio_l, sebe_l, trilho_l, via_l, cais_l, rio_l, agua_l,
                     mata_l, verde_l, cidade_l, brejo_l, cerca_l, campo_l, chao_l) if l]

proj = QgsProject.instance(); proj.setCrs(MERC)
raiz = proj.layerTreeRoot()
for l in ordem:
    proj.addMapLayer(l, False); raiz.addLayer(l)
cor = QColor(CAMPO)
for parte, val in (('Red', cor.red()), ('Green', cor.green()), ('Blue', cor.blue())):
    proj.writeEntry('Gui', '/CanvasColor%sPart' % parte, val)
qgz = os.path.join(HERE, 'carentan.qgz')
proj.write(qgz)
print('projeto ->', qgz)

# ============================================================== RENDER
camadas = list(ordem)
if MOLDURA_ON:
    import random
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
    mold = mem('moldura', 'Polygon')
    fp = QgsFeature(); fp.setGeometry(QgsGeometry.fromPolygonXY([fora, dentro]))
    mold.dataProvider().addFeature(fp); mold.updateExtents()
    veste(mold, simples(PAPEL), efeito=sombra(1.1, 3.0, '#14343a', 0.40, 315))
    camadas.insert(0, mold)

ms = QgsMapSettings()
ms.setLayers(camadas)
ms.setBackgroundColor(QColor(CAMPO))
ms.setOutputSize(QSize(LARG, ALT))
ms.setOutputDpi(DPI)
ms.setExtent(ext)
ms.setDestinationCrs(MERC)
job = QgsMapRendererParallelJob(ms); job.start(); job.waitForFinished()
img = job.renderedImage()
out = os.path.join(HERE, nome + '.png')
img.save(out)
print('->', out, LARG, 'x', ALT)

# O PNG e o arquivo de arquivo: sem perda, para olhar de perto e para
# imprimir. Mas ele tem 13 MB, e a placa vai embutida em base64 dentro de um
# HTML de um arquivo so — dois PNGs desses viram 35 MB de pagina.
#
# O JPEG a 92 com croma inteiro (4:4:4) da 2,9 MB com erro medio de 1,4 em 255,
# medido, nao chutado. A textura do mapa e justamente o que o JPEG faz pior, por
# isso o croma nao pode ser reduzido; com 4:2:0 a sebe verde escura sangraria nos
# talhoes. A placa e fundo de cena, com soldados por cima: 1,4 de erro nao
# aparece em video nenhum.
jpg = os.path.join(HERE, nome + '.jpg')
img.save(jpg, 'JPG', 92)
print('->', jpg, '%.2f MB (PNG: %.2f MB)'
      % (os.path.getsize(jpg) / 1048576.0, os.path.getsize(out) / 1048576.0))

# ------------------------------------------------- onde a placa cai no mundo
# Sem isto o PNG e so um desenho bonito. Com isto ele e um mapa: o estudio de
# cena le estes numeros e sabe converter lon/lat em pixel, que e o que deixa um
# soldado andar pela Rue Holgate de verdade em vez de por uma reta inventada.
sw = inv.transform(QgsPointXY(ext.xMinimum(), ext.yMinimum()))
ne = inv.transform(QgsPointXY(ext.xMaximum(), ext.yMaximum()))
ficha = {
    'nome': nome,
    'png': nome + '.png',
    'jpg': nome + '.jpg',
    'px': [LARG, ALT],
    'centro': [Q_LON, Q_LAT],
    'larguraKm': Q_KM,
    'alturaKm': Q_KM / ASPECTO,
    'metrosPorPixel': Q_KM * 1000.0 / LARG,
    'limites': {'oeste': sw.x(), 'sul': sw.y(), 'leste': ne.x(), 'norte': ne.y()},
    'crs': 'EPSG:3857',
    'extensao3857': [ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum()],
}
cam = os.path.join(HERE, nome + '.json')
with open(cam, 'w', encoding='utf-8') as fh:
    json.dump(ficha, fh, ensure_ascii=False, indent=2)
print('->', cam)
print('   %.6f,%.6f (SO)  ..  %.6f,%.6f (NE)' % (sw.x(), sw.y(), ne.x(), ne.y()))
qgs.exitQgis()
