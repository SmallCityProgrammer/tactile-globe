# carentan.py — Carentan, 12 de junho de 1944, no estilo Operations Room.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" carentan.py
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" carentan.py holgate
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" carentan.py carentan 8192
#
# COPIA DO ardenas.py, QUE E O CASO GERAL. Nao do pearl.py: la a terra tinha que
# ser DEDUZIDA da linha de costa, e Carentan nao tem costa dentro do recorte —
# a terra e o quadro inteiro. Fica o telhado em SVG escolhido por classe, a copa
# em PNG com alfa, a ondulacao do talhao e a colcha de tons por tipo.
#
# O QUE ESTE MAPA TEM E BASTOGNE NAO
# O BREJO. Carentan e uma ilha de chao seco entre os vales alagados da Douve e da
# Taute. Isso nao e paisagem de fundo: e a explicacao da batalha inteira, porque
# e o que obrigou os paraquedistas a descer pela calcada exposta, em fila.
#
# E ELE SAI COM A FICHA DE ONDE CAI NO MUNDO. Junto do PNG vai um .json com os
# limites em graus e a extensao em 3857. Sem ele o render e so um desenho
# bonito; com ele o estudio de cena converte lon/lat em pixel, e e isso que
# deixa um soldado andar pela Rue Holgate de verdade em vez de por uma reta
# inventada.
import os, sys, glob, math, random, time, json
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
S, W, N, E = 49.285, -1.283, 49.322, -1.220       # o retangulo que o fetch.mjs baixou

# --------------------------------------------------------------- OS QUADROS
# centro em graus, largura NO CHAO em km. A altura sai da proporcao 16:9, para a
# placa cair inteira num quadro de video sem sobra.
#
# 'carentan' cobre a hora inteira do assalto das 6h: a base de partida em La
# Billonnerie (sudoeste), a estrada de Periers subindo, o entroncamento em T, a
# Rue Holgate entrando na cidade, e a borda norte por onde desceram os que
# vinham do outro lado as 7h.
QUADROS = {
    'carentan': (-1.24500, 49.30295, 3.18),   # o assalto inteiro — o padrao
    'holgate':  (-1.24737, 49.30264, 1.10),   # so o entroncamento em T e a rua
    'periers':  (-1.25142, 49.29788, 1.40),   # a subida desde La Billonnerie
    # Os quadros de PERTO, na escala da referencia: la a estrada ocupa um decimo
    # da largura do quadro, o que da uns 100 m de campo visivel. E dai que veio a
    # queixa de que "a rua e menor que os soldados" — nao era o zoom, era a via
    # medida em milimetro de tela; mas o zoom tambem faltava.
    'entroncamento': (-1.24963, 49.30085, 0.26),   # o T e o Bar du Stade
    'vala':          (-1.25060, 49.29950, 0.22),   # as duas valas e o meio da estrada
    'holgate-perto': (-1.24850, 49.30240, 0.34),   # a subida da rua, dentro da cidade
    # OS QUADROS DE CHAO. A referencia poe a estrada ocupando um decimo da
    # largura do quadro: com pista de 5,5 m isso da uns 55 a 120 m de campo
    # visivel. Abaixo de 120 m ja se conta o homem na fila.
    'rua-200': (-1.24890, 49.30175, 0.20),
    'rua-130': (-1.24905, 49.30155, 0.13),
    'rua-80':  (-1.24930, 49.30120, 0.08),
}
ASPECTO = 16.0 / 9.0

# O quadro e escolhido AQUI, antes de qualquer coisa, e nao la embaixo junto
# do render: a escala do ladrilho do bocage sai da largura do quadro em
# metros por milimetro de tela, e ela precisa estar pronta na hora de vestir.
# O nome vem pelo argumento, e a largura em pixels pode vir junto:
#   carentan.py holgate 8192
# As bandeiras saem da lista antes: '--camadas' pede, alem da placa, as tres
# fatias que o tools/pincel.py precisa (veja o fim do arquivo).
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
CAMADAS = '--camadas' in sys.argv
nome = ARGS[0] if ARGS else 'carentan'
LARG = int(ARGS[1]) if len(ARGS) > 1 else 4096
if nome not in QUADROS:
    raise SystemExit('quadro %r nao existe. Ha: %s' % (nome, ', '.join(QUADROS)))
Q_LON, Q_LAT, Q_KM = QUADROS[nome]

WGS = QgsCoordinateReferenceSystem('EPSG:4326')
MERC = QgsCoordinateReferenceSystem('EPSG:3857')
# A moldura de papel rasgado fica DESLIGADA: esta placa e palco de cena, e os
# soldados andam ate a borda. Uma borda desenhada seria parte do mundo.
MOLDURA_ON = False
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
brejo, cais = load('brejo'), load('cais')
print('campo %d | mata %d | urbano %d | via %d | sebe %d | predio %d | brejo %d'
      % (campo.featureCount(), mata.featureCount(), urbano.featureCount(),
         via.featureCount(), sebe.featureCount() if sebe else 0, predios.featureCount(),
         brejo.featureCount() if brejo else 0))

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
# --------------------------------------------- o bege preso aos quarteiroes
# Em Bastogne o `landuse=residential` desenha a aldeia e pronto: o poligono e
# justo, cola no casario. Em Carentan os seis poligonos de residential cobrem a
# comuna inteira, e o mapa saia com uma CHAPA BEGE de canto a canto onde devia
# haver quintal, horta e campo entre os quarteiroes.
#
# A saida e cruzar o que o OSM diz que e urbano com onde ha predio de verdade:
# engorda cada predio 22 m, funde, encolhe 14 (isso fecha os vaos e arredonda os
# cantos) e corta o urbano por dentro disso. Os 85 m do patio de Pearl Harbor
# nao servem aqui — la eram galpoes soltos num campo, aqui o quarteirao normando
# e denso e 85 m juntaria a cidade inteira num borrao redondo.
pred3857 = para3857(predios)
if urbano:
    apron = corre('native:buffer', {'INPUT': pred3857, 'DISTANCE': 22, 'SEGMENTS': 4,
                                    'JOIN_STYLE': 1, 'DISSOLVE': True})
    apron = corre('native:buffer', {'INPUT': apron, 'DISTANCE': -14, 'SEGMENTS': 4,
                                    'JOIN_STYLE': 1, 'DISSOLVE': False})
    antes = urbano.featureCount()
    urbano = corre('native:clip', {'INPUT': para3857(urbano), 'OVERLAY': apron})
    urbano.setName('urbano')
    print('urbano: %d poligonos -> %d, cortados no quarteirao' % (antes, urbano.featureCount()))
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
# metros de chao por milimetro de tela: e disto que sai a escala do bocage, que
# e a unica coisa do mapa medida no chao e nao na tela.
m_por_mm = (Q_KM * 1000.0) / (LARG / 96.0 * 25.4)
malha, esc_bocage = ST.malha_bocage(HERE, m_por_mm)
print('bocage: talhao de %.0f m -> ladrilho de %.0f mm de tela' % (ST.TALHAO_M, esc_bocage))

ST.veste(terra, *ST.chao(HERE, malha, esc_bocage))
ST.veste(campo, *ST.campo(HERE, malha, esc_bocage))
# a lavoura e as sebes, uma vez so, na geometria do quadro inteiro
cerca = QgsVectorLayer(terra.source(), 'cerca', 'ogr')
ST.veste(cerca, *ST.cerca_viva(malha, esc_bocage))
ST.veste(mata, *ST.mata(HERE))
if brejo:  ST.veste(brejo, *ST.brejo(HERE))
if urbano: ST.veste(urbano, *ST.urbano(HERE))
if agua_p: ST.veste(agua_p, *ST.agua(HERE))
if cais:   ST.veste(cais, *ST.cais(HERE))
if via:    ST.via(via)
if rio:    ST.rio(rio)
if ferro:  ST.ferro(ferro)
if sebe:   ST.sebe(sebe)
ST.telhados(predios, HERE)

graozinho = QgsVectorLayer(terra.source(), 'papel', 'ogr')
ST.veste(graozinho, *ST.papel(HERE))

# de cima para baixo. O brejo fica ACIMA do campo e ABAIXO do urbano: ele cobre
# o talhao mapeado (o vale alagado nao era pasto naquele junho) mas nao a cidade.
ordem = [l for l in (graozinho, predios, sebe, ferro, via, cais, rio, agua_p,
                     urbano, mata, brejo, cerca, campo, terra) if l]

proj = QgsProject.instance(); proj.setCrs(MERC)
raiz = proj.layerTreeRoot()
for l in ordem:
    proj.addMapLayer(l, False); raiz.addLayer(l)
c = QColor(ST.FUNDO)
for parte, val in (('Red', c.red()), ('Green', c.green()), ('Blue', c.blue())):
    proj.writeEntry('Gui', '/CanvasColor%sPart' % parte, val)
qgz = os.path.join(HERE, 'carentan.qgz'); proj.write(qgz)
print('projeto ->', qgz)

# ============================================================== RENDER
# O 3857 estica Y por 1/cos(lat) — 1,53 nesta latitude. Entao um metro de chao
# vale 1/cos(lat) unidades de mapa, e e por isso que a largura em km tem que ser
# convertida antes de virar retangulo. Como o Mercator e conforme, o desenho sai
# com a forma certa: o que muda e so a escala, igual nas duas direcoes.
cq = tr.transform(QgsPointXY(Q_LON, Q_LAT))
larg_mapa = Q_KM * 1000.0 / math.cos(math.radians(Q_LAT))
alt_mapa = larg_mapa / ASPECTO
ext = QgsRectangle(cq.x() - larg_mapa / 2, cq.y() - alt_mapa / 2,
                   cq.x() + larg_mapa / 2, cq.y() + alt_mapa / 2)
ALT = int(round(LARG / ASPECTO))
print('quadro %s: %.2f x %.2f km, %d x %d px, %.3f m/px'
      % (nome, Q_KM, Q_KM / ASPECTO, LARG, ALT, Q_KM * 1000.0 / LARG))

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
img = job.renderedImage()
out = os.path.join(HERE, nome + '.png')
img.save(out)
print('->', out, LARG, 'x', ALT)

# O PNG e copia de arquivo: sem perda, para olhar de perto e imprimir. Mas a
# placa vai embutida em base64 dentro de um HTML de um arquivo so, e o PNG deste
# mapa passa de 30 MB a 8192 px. O JPEG a 92 com croma INTEIRO (4:4:4) da menos
# de um decimo disso com erro medio de 1,4 em 255, medido. O croma nao pode ser
# reduzido: a textura do mapa e justamente o que o JPEG faz pior, e com 4:2:0 a
# sebe verde-escura sangra nos talhoes.
jpg = os.path.join(HERE, nome + '.jpg')
img.save(jpg, 'JPG', 92)
print('->', jpg, '%.1f MB (PNG: %.1f MB)'
      % (os.path.getsize(jpg) / 1048576.0, os.path.getsize(out) / 1048576.0))

# ------------------------------------------- onde a placa cai no mundo
inv = QgsCoordinateTransform(MERC, WGS, QgsProject.instance())
so = inv.transform(QgsPointXY(ext.xMinimum(), ext.yMinimum()))
ne = inv.transform(QgsPointXY(ext.xMaximum(), ext.yMaximum()))
ficha = {
    'nome': nome, 'png': nome + '.png', 'jpg': nome + '.jpg',
    'px': [LARG, ALT], 'centro': [Q_LON, Q_LAT],
    'larguraKm': Q_KM, 'alturaKm': Q_KM / ASPECTO,
    'metrosPorPixel': Q_KM * 1000.0 / LARG,
    'limites': {'oeste': so.x(), 'sul': so.y(), 'leste': ne.x(), 'norte': ne.y()},
    'crs': 'EPSG:3857',
    'extensao3857': [ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum()],
}
cam = os.path.join(HERE, nome + '.json')
with open(cam, 'w', encoding='utf-8') as fh:
    json.dump(ficha, fh, ensure_ascii=False, indent=2)
print('->', cam)
print('   %.6f,%.6f (SO)  ..  %.6f,%.6f (NE)' % (so.x(), so.y(), ne.x(), ne.y()))

# ------------------------------------------------- as fatias, para o pincel
# O tools/pincel.py pinta as ruas POR CIMA do render, em raster. Para isso ele
# precisa de tres coisas separadas, registradas ao pixel: o chao SEM a via (o
# que ha por baixo dela, opaco), a via sozinha (so para conferir o registro da
# propria rasterizacao dele) e o que fica POR CIMA da via — predios com a sua
# sombra e o grao do papel — com alfa. Assim a rua pintada entra
# no lugar certo da pilha, e nao por cima da sombra dos predios.
if CAMADAS:
    pasta_c = os.path.join(HERE, 'camadas'); os.makedirs(pasta_c, exist_ok=True)
    i_via = ordem.index(via)
    fatias = (('abaixo', ordem[i_via + 1:], QColor(ST.FUNDO)),
              ('via',    [via],             QColor(0, 0, 0, 0)),
              # o trilho e a sebe do OSM ficam FORA da fatia de cima: o pincel pinta
              # a ferrovia (lastro e trilhos) e a fila de arvores ele mesmo
              ('acima',  [l for l in ordem[:i_via] if l is not ferro and l is not sebe], QColor(0, 0, 0, 0)))
    for rot, cams, fundo in fatias:
        t0 = time.time()
        ms2 = QgsMapSettings(); ms2.setLayers(cams); ms2.setBackgroundColor(fundo)
        ms2.setOutputSize(QSize(LARG, ALT)); ms2.setOutputDpi(96)
        ms2.setExtent(ext); ms2.setDestinationCrs(MERC)
        job = QgsMapRendererParallelJob(ms2); job.start(); job.waitForFinished()
        alvo = os.path.join(pasta_c, '%s-%s.png' % (nome, rot))
        job.renderedImage().save(alvo)
        print('-> camadas/%s-%s.png  %.0f s' % (nome, rot, time.time() - t0))
qgs.exitQgis()

# ...e o pincel roda em seguida, no Python de fora (PIL, numpy, scipy), para o
# PNG e o JPG desta placa nunca ficarem crus por esquecimento. --so-camadas
# grava as fatias e para ai.
if CAMADAS and '--so-camadas' not in sys.argv:
    import subprocess
    pincel = os.path.join(os.path.dirname(HERE), 'tools', 'pincel.py')
    print('pincel:', nome)
    r = subprocess.run(['py', '-3', pincel, nome], cwd=os.path.dirname(HERE))
    if r.returncode:
        raise SystemExit('o pincel falhou (%d) — a placa %s ficou CRUA' % (r.returncode, nome))
