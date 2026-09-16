# exporta.py — o mapa saindo do QGIS para o After Effects.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" exporta.py [larg] [quadro]
#
#   exporta.py                 -> mapa inteiro a 12000 px
#   exporta.py 16000           -> mapa inteiro a 16000 px
#   exporta.py 12000 ford      -> Ford Island a 12000 px
#
# A IDEIA
# No Operations Room o mapa e estatico: so os navios e avioes se mexem. Entao o
# QGIS renderiza a base UMA vez, grande, e o movimento acontece no AE por cima.
# Nao ha motivo para o QGIS renderizar quadro a quadro, e nao ha integracao
# direta entre os dois — a passagem e por arquivo.
#
# O QUE SAI
#   saida/<quadro>-<larg>/00-completo.png   o mapa inteiro, achatado
#   saida/<quadro>-<larg>/NN-<camada>.png   uma camada por arquivo, com alfa
#   saida/<quadro>-<larg>/enquadramento.txt a extensao e a escala, para referencia
#
# As camadas separadas sao registradas pixel a pixel: empilhar todas na ordem do
# numero, com opacidade cheia e modo normal, reproduz o 00-completo. Isso e
# verificado no fim da exportacao, e a diferenca e impressa — se der mais que
# zero por cento, alguma camada tem efeito que nao sobrevive a separacao.
#
# UMA COISA IMPORTANTE SOBRE ESCALA
# As regras de estilo reagem ao DENOMINADOR DE ESCALA, que depende do tamanho de
# saida, e nao do enquadramento. O telhado desenhado entra abaixo de 1:8000:
#
#   mapa inteiro a  3000 px -> 1:15429   nervura
#   mapa inteiro a  6000 px -> 1: 7715   telhado desenhado
#   mapa inteiro a 12000 px -> 1: 3857   telhado desenhado
#
# Ou seja, o cartaz em alta resolucao ganha o desenho dos telhados de graca.
import os, sys, glob, time
for _p in glob.glob(os.path.join(os.environ.get('QGIS_PREFIX_PATH', r'C:/Program Files/QGIS 3.44.12/apps/qgis-ltr'), 'python', 'plugins')) + glob.glob(r'C:/Program Files/QGIS*/apps/qgis*/python/plugins'):
    if _p not in sys.path: sys.path.append(_p)
from qgis.core import (QgsApplication, QgsProject, QgsRectangle, QgsMapSettings,
                       QgsMapRendererParallelJob, QgsCoordinateReferenceSystem)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor, QImage, QPainter

HERE = os.path.dirname(os.path.abspath(__file__))
MERC = QgsCoordinateReferenceSystem('EPSG:3857')

QUADROS = {                       # sul, oeste, norte, leste
    'tudo':  (21.325, -158.030, 21.400, -157.920),
    'ford':  (21.348, -157.978, 21.383, -157.933),
    'base':  (21.3525, -157.9670, 21.3655, -157.9510),
}

qgs = QgsApplication([], False); qgs.initQgis()

# O projeto ja tem tudo montado e na ordem certa; nao ha por que remontar o
# pipeline so para exportar. Se o .qgz nao existir, rode o pearl.py antes.
proj = QgsProject.instance()
qgz = os.path.join(HERE, 'pearl-harbor.qgz')
if not proj.read(qgz):
    sys.exit('nao consegui abrir %s — rode o pearl.py primeiro' % qgz)

# de cima para baixo na arvore do projeto, que e a ordem de desenho invertida
ordem = [n.layer() for n in proj.layerTreeRoot().findLayers() if n.layer()]
print('camadas no projeto:', len(ordem))

LARG = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
quadro = sys.argv[2] if len(sys.argv) > 2 else 'tudo'
S, W, N, E = QUADROS[quadro]

from qgis.core import QgsCoordinateTransform
tr = QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), MERC, proj)
ext = tr.transformBoundingBox(QgsRectangle(W, S, E, N))
ALT = int(LARG * ext.height() / ext.width())

destino = os.path.join(HERE, 'saida', '%s-%d' % (quadro, LARG))
os.makedirs(destino, exist_ok=True)

def monta(camadas, fundo):
    ms = QgsMapSettings()
    ms.setLayers(camadas)
    ms.setBackgroundColor(fundo)
    ms.setOutputSize(QSize(LARG, ALT))
    ms.setOutputDpi(96)                  # o mesmo do pearl.py: as texturas estao em mm
    ms.setExtent(ext)
    ms.setDestinationCrs(MERC)
    return ms

def rende(ms, nome):
    t = time.time()
    job = QgsMapRendererParallelJob(ms); job.start(); job.waitForFinished()
    img = job.renderedImage()
    alvo = os.path.join(destino, nome + '.png')
    img.save(alvo)
    mb = os.path.getsize(alvo) / 1048576.0
    print('  %-28s %6.1f s  %6.1f MB' % (nome + '.png', time.time() - t, mb))
    return img

esc = monta(ordem, QColor(0, 0, 0, 0)).scale()
print('%s a %d x %d px  ->  1:%.0f' % (quadro, LARG, ALT, esc))
print('destino:', destino)

# ------------------------------------------------------------- o mapa achatado
inteiro = rende(monta(ordem, QColor(0, 0, 0, 0)), '00-completo')

# ------------------------------------------------- uma camada por arquivo
# Fundo TRANSPARENTE em cada uma. O efeito de sombra de cada camada viaja com
# ela, porque mora no renderizador daquela camada — e por isso que a sombra dos
# predios sai no arquivo dos predios e nao precisa ser refeita no AE.
#
# As camadas sao renderizadas DE BAIXO PARA CIMA e empilhadas numa imagem so na
# hora, em vez de guardadas numa lista. Nao e capricho: a 12000 px cada camada
# ocupa uns 420 MB em ARGB, e segurar as onze junto com o achatado passaria de
# 4 GB. Assim ficam tres imagens vivas por vez.
volta = QImage(LARG, ALT, QImage.Format_ARGB32)
volta.fill(QColor(0, 0, 0, 0))
pintor = QPainter(volta)
for i in range(len(ordem), 0, -1):
    l = ordem[i - 1]
    img = rende(monta([l], QColor(0, 0, 0, 0)), '%02d-%s' % (i, l.name()))
    pintor.drawImage(0, 0, img)
    del img
pintor.end()

# ------------------------------------------------- conferir o registro

# Contar pixels diferentes nao basta: o que separa "antialias" de "efeito
# quebrado" e a MAGNITUDE. Empilhar camadas antialiasadas uma a uma arredonda
# diferente de desenhar tudo numa passada so, e isso rende uns poucos niveis de
# diferenca na beirada de cada contorno. Um efeito que nao sobreviveu a
# separacao renderia dezenas ou centenas.
passo = max(1, LARG // 900)               # comparar 12000^2 pixels seria caro
difs = tot = pior = soma = 0
for y in range(0, ALT, passo):
    for x in range(0, LARG, passo):
        a, b = inteiro.pixel(x, y), volta.pixel(x, y)
        tot += 1
        if a == b: continue
        d = max(abs(((a >> s) & 255) - ((b >> s) & 255)) for s in (0, 8, 16, 24))
        difs += 1; soma += d; pior = max(pior, d)
print('registro: %d de %d amostras diferentes (%.3f%%)' % (difs, tot, 100.0 * difs / tot))
if difs:
    print('           desvio medio %.1f de 255, pior %d' % (soma / difs, pior))
    print('           %s' % ('so antialias de borda — empilhar no AE reproduz o achatado'
                             if pior <= 24 else
                             'ATENCAO: grande demais para antialias; alguma camada tem '
                             'efeito que nao sobrevive a separacao'))

with open(os.path.join(destino, 'enquadramento.txt'), 'w', encoding='utf-8') as f:
    f.write('quadro      %s\n' % quadro)
    f.write('tamanho     %d x %d px, 96 dpi\n' % (LARG, ALT))
    f.write('escala      1:%.0f\n' % esc)
    f.write('CRS         EPSG:3857\n')
    f.write('extensao    %.2f %.2f %.2f %.2f\n' % (ext.xMinimum(), ext.yMinimum(),
                                                   ext.xMaximum(), ext.yMaximum()))
    f.write('graus       S %.6f  W %.6f  N %.6f  E %.6f\n' % (S, W, N, E))
    f.write('m por px    %.4f\n' % (ext.width() / LARG))
    f.write('\ncamadas, de cima para baixo:\n')
    for i, l in enumerate(ordem, 1):
        f.write('  %02d  %s\n' % (i, l.name()))
print('->', destino)
qgs.exitQgis()
