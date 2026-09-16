# -*- coding: utf-8 -*-
"""
pincel.py — as ruas pintadas POR CIMA do render, em raster.

    py -3 tools/pincel.py                      todas as placas que tem camadas/
    py -3 tools/pincel.py holgate              uma placa
    py -3 tools/pincel.py holgate --prova      so a folha de prova, sem gravar a placa
    py -3 tools/pincel.py --recorte holgate -1.2496 49.3009 140 saida.jpg
                                               um recorte de 140 m de largura, centrado
                                               em lon/lat, da placa ja pintada

POR QUE ISTO EXISTE
A via do QGIS e uma linha: faixa chapada, contorno de espessura uniforme, ponta
redonda. Isso e um simbolo de mapa rodoviario, e num quadro fechado, com
soldados andando por cima, le como desenho animado. O que a referencia do
Operations Room tem no lugar e uma ESTRADA: piso claro com remendos e o
desgaste das rodas, beiral fino e escuro, capim batido no acostamento, calcada
na cidade, sebe com sombra no campo. Nada disso se faz com um simbolo de linha.

E "Photoshop por cima", so que em codigo — o motivo e o mesmo do pos.py: o que
se pinta a mao se perde no proximo render, e o que esta em codigo volta em dois
minutos. A regra da casa continua: no Photoshop, pinte em camadas POR CIMA do
resultado daqui, nunca sobre as camadas do QGIS.

COMO ENTRA NA PILHA
O carentan.py --camadas grava tres fatias registradas ao pixel:

    camadas/<placa>-abaixo.png   o chao SEM a via (terra, campo, brejo, mata,
                                 urbano, agua, rio, cais) — opaco
    camadas/<placa>-via.png      a via sozinha, com alfa — so para CONFERIR o
                                 registro da rasterizacao daqui contra a do QGIS
    camadas/<placa>-acima.png    o que fica por cima da via: predios COM a sua
                                 sombra e o grao do papel — com alfa

A rua pintada entra entre 'abaixo' e 'acima'. E por isso que a sombra do predio
continua caindo na rua e o grao do papel continua cobrindo tudo: nada disso e
refeito aqui. A ferrovia e a fila de arvores do OSM sao as excecoes: ficam
acima da via na pilha do QGIS, mas sairam da fatia de cima e sao pintadas aqui
(lastro e trilhos; sebe com sombra), porque a faixa chapada delas tinha o mesmo
defeito da rua.

TUDO EM METROS DE CHAO. Largura de pista, acostamento, calcada, sebe, escala do
ruido: todos em metros, convertidos pela ficha da placa. A mesma rua sai com a
mesma largura na placa larga e na fechada, e e isso que deixa o estudio trocar
de placa no meio de um movimento de camera sem a rua mudar de tamanho.

Uma medida que vale registrar: a via do estilo.py esta em RenderMetersInMapUnits,
e MEDIDO nas fatias o QGIS desenhava os "5,5 m" com 3,6 m de chao — fator
0,652, que e o cos(49,3 graus). Sem elipsoide no QgsMapSettings, o "metro" e a
unidade de mapa do 3857, esticada por 1/cos(lat) nesta latitude. As larguras
daqui sao metros de chao de verdade, entao a rua sai uns 50% mais larga do que
saia — e do tamanho que tem.

DUAS GEOMETRIAS PARA A MESMA RUA
A borda da pista vem da UNIAO dos poligonos das vias (traco largo de ponta
reta, fechada em 2 m para arredondar o canto de dentro dos cruzamentos): e ela
que decide onde o piso acaba. Por isso um beco termina reto, o toco que entra
numa rua larga morre na borda dela em vez de atravessa-la em bico, e o beiral
so corre pelo contorno de fora. Ja o desgaste das rodas, o acostamento, a
calcada e a sebe vem da distancia ao EIXO, normalizada pela meia-largura do
grupo mais perto: e o que diz "estou a 0,5 da pista" ou "a 2 m para fora do
beiral". As faixas de fora sao recortadas por poligonos mais largos, com a
mesma ponta reta, para a calcada nao dar a volta no fim da rua.

O QUE E DADO E O QUE E INVENTADO
A posicao, a classe e a tag de cada via vem do OSM. O piso (asfalto, macadame,
cascalho, terra) e deduzido da tag — uma nacional era asfaltada em 1944, um
caminho de fazenda era terra — e a textura e ruido. A SEBE ao longo da estrada
rural e o mesmo contrato do bocage: o campo normando tinha sebe na beira de
quase toda estrada, e isso e um fato sobre o lugar; ONDE cada uma tinha um vao
e sorteio. "Era assim", sem "era aqui". SEBES = False desliga.
"""
import os, sys, json, math, time, shutil
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.spatial import cKDTree

Image.MAX_IMAGE_PIXELS = None
AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QGIS = os.path.join(AQUI, 'qgis')
CAMADAS = os.path.join(QGIS, 'camadas')
R_TERRA = 6378137.0
SEMENTE = 1944
SEBES = True          # sebe ao longo das estradas rurais, com vaos sorteados

# ============================================================== AS MEDIDAS
# Largura da PISTA por tag do OSM, em metros de chao, e o piso que ela tinha.
# Medidas de estrada normanda: a D971 tem duas maos de 3,5 m mais o acostamento
# pavimentado; uma rua de aldeia tem cinco e meio; num caminho de servico cabe
# um trator. Sao um pouco mais estreitas que as do estilo.py porque a pista e
# so a pista — o acostamento agora e pintado a parte, e some no chao.
VIAS = {
    #  tag             pista  piso
    'trunk':          (8.0, 'asfalto'),
    'primary':        (8.0, 'asfalto'),
    'secondary':      (6.5, 'asfalto'),
    'tertiary':       (6.0, 'macadame'),
    'unclassified':   (5.0, 'macadame'),
    'residential':    (5.5, 'macadame'),
    'living_street':  (5.0, 'macadame'),
    'pedestrian':     (3.5, 'cascalho'),
    'service':        (3.2, 'cascalho'),
    'track':          (3.0, 'terra'),
}
PADRAO = (3.2, 'cascalho')
# os que ganham calcada quando passam pela cidade
COM_CALCADA = {'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
               'residential', 'living_street'}
# os que ganham sebe quando passam pelo campo: o caminho de servico e uma
# entrada de garagem ou uma alameda de patio, e nao tem
COM_SEBE = {'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
            'residential', 'living_street', 'track'}

# O piso, em RGB 0..1, NEUTRO e CLARO. Vista de cima, a estrada e a superficie
# mais clara do terreno: o asfalto reflete o ceu, e na referencia a rua e uma
# fita clara sobre o campo, mais clara que a grama e um pouco mais escura que a
# calcada. A primeira versao daqui era escura, e virava vala entre as casas.
# Neutro, sem puxar para o oliva do campo nem para o bege da cidade, senao a
# rua so se distingue do chao pela saturacao. Quem da a leitura e o BEIRAL.
PISO = {
    'asfalto':  (0.575, 0.57, 0.565),
    'macadame': (0.62, 0.61, 0.59),
    'cascalho': (0.68, 0.65, 0.60),
    'terra':    (0.66, 0.59, 0.47),
}
CAPIM       = (0.72, 0.70, 0.46)    # o capim batido e amarelado da beira
ORLA        = (0.72, 0.70, 0.64)    # a beira clara de cascalho, com falhas
GRAMA_RUT   = (0.50, 0.55, 0.33)    # a faixa de capim no meio da trilha
CALCADA     = (0.75, 0.73, 0.67)    # a calcada
SEBE        = (0.23, 0.29, 0.155)   # a sebe, quase preta vista de cima
LASTRO      = (0.62, 0.595, 0.55)   # a brita da ferrovia
TRILHO      = (0.30, 0.29, 0.28)    # o trilho

BEIRAL_M   = 0.30   # a linha escura no beiral, para dentro da pista
ORLA_M     = 0.35   # a beira clara, para fora, em estrada rural
ACOST_M    = 0.9    # o capim batido, do beiral para fora
CALCADA_M  = 1.8
BORDA_M    = 0.22   # amplitude do tremor do beiral
BORDA_ESC_M = 1.6   # ...e a escala dele: mordidas curtas de mato, nao onda de caneta
JUNTA_M    = 1.2    # duas vias cujas pontas caem a menos disto se emendam
CANTO_M    = 2.0    # o raio do fechamento que arredonda o canto de dentro do cruzamento
SEBE_DE_M  = 1.0    # a sebe comeca aqui, do beiral para fora
SEBE_MIN_M, SEBE_MAX_M = 1.5, 4.5   # a largura dela ondula entre estes
SEBE_SOMBRA_M = 2.4 # quanto a sombra dela cai para sudeste
URB_FOLGA_M = 60.0  # ate onde a cidade se estende: sebe so em estrada de campo mesmo
LASTRO_M   = 4.5    # a largura do lastro de uma via
BITOLA_M   = 1.435

# ============================================================== A PLACA
def ficha_de(nome):
    with open(os.path.join(QGIS, nome + '.json'), encoding='utf-8') as fh:
        return json.load(fh)

class Placa:
    """A ficha .json virada em conversor lon/lat -> pixel, e metros -> pixel."""
    def __init__(self, ficha):
        self.nome = ficha['nome']
        self.W, self.H = ficha['px']
        self.ext = ficha['extensao3857']
        # metros de CHAO por pixel — e a mesma conta do carentan.py, e nao a
        # unidade de 3857, que esta esticada por 1/cos(lat) nesta latitude
        self.mpp = ficha['larguraKm'] * 1000.0 / self.W
        self.ppm = 1.0 / self.mpp
        self.lat = (ficha['limites']['sul'] + ficha['limites']['norte']) / 2

    def px(self, lonlat):
        a = np.asarray(lonlat, dtype=np.float64)
        x = R_TERRA * np.radians(a[:, 0])
        y = R_TERRA * np.log(np.tan(np.pi / 4 + np.radians(a[:, 1]) / 2))
        e = self.ext
        return np.stack([(x - e[0]) / (e[2] - e[0]) * self.W,
                         (e[3] - y) / (e[3] - e[1]) * self.H], 1)

    def dentro(self, pts, folga):
        return ((pts[:, 0] > -folga).any() and (pts[:, 0] < self.W + folga).any() and
                (pts[:, 1] > -folga).any() and (pts[:, 1] < self.H + folga).any())

def geojson(nome):
    cam = os.path.join(QGIS, nome + '.geojson')
    if not os.path.exists(cam): return []
    with open(cam, encoding='utf-8') as fh:
        return json.load(fh)['features']

# ============================================================== O RUIDO
def ruido(W, H, escala_px, semente, oitavas=3):
    """
    Ruido de valor sem direcao nem periodo, em [-1, 1] aproximado.

    Uma grade aleatoria pequena ampliada em bicubico e o mesmo ruido de valor do
    textura.py, so que feito pelo PIL, que e o que deixa isto rodar em segundos
    numa placa de 38 milhoes de pixels. Tres oitavas, cada uma com metade da
    escala e metade do peso.

    A grade nunca fica mais fina que 5 px: abaixo disso o bicubico entrega a
    propria grade — e foi assim que a sebe da placa larga saiu com tracinhos
    periodicos, e a trilha com cara de corda trancada.
    """
    rng = np.random.default_rng(semente)
    soma = np.zeros((H, W), np.float32); peso = 0.0
    for o in range(oitavas):
        esc = max(5.0, escala_px / (2 ** o))
        gw, gh = int(math.ceil(W / esc)) + 2, int(math.ceil(H / esc)) + 2
        g = rng.random((gh, gw), np.float32) * 2 - 1
        im = Image.fromarray(g, 'F').resize((int(gw * esc), int(gh * esc)), Image.BICUBIC)
        a = np.asarray(im, np.float32)[:H, :W]
        w = 0.5 ** o
        soma += a * w; peso += w
    soma /= peso
    # normaliza pela faixa medida, e nao pela teorica: o bicubico aperta o ruido
    return np.clip(soma / (3.0 * soma.std() + 1e-6), -1, 1)

def grao(W, H, semente):
    return np.random.default_rng(semente).random((H, W), np.float32) * 2 - 1

# ============================================================== AS MASCARAS
def _poligonos(feats, P):
    polys = []
    for f in feats:
        g = f['geometry']
        aneis = g['coordinates'] if g['type'] == 'Polygon' else [a for p in g['coordinates'] for a in p]
        for anel in aneis:
            pts = P.px(anel)
            if P.dentro(pts, 50): polys.append(pts)
    return polys

def mascara_poligonos(feats, P):
    im = Image.new('L', (P.W, P.H), 0)
    d = ImageDraw.Draw(im)
    for pts in _poligonos(feats, P):
        d.polygon([tuple(p) for p in pts], fill=255)
    return np.asarray(im) > 0

def mascara_linhas(feats, P, larg_px, filtro=None):
    im = Image.new('L', (P.W, P.H), 0)
    d = ImageDraw.Draw(im)
    for f in feats:
        if filtro and not filtro(f['properties']): continue
        g = f['geometry']
        for l in ([g['coordinates']] if g['type'] == 'LineString' else g['coordinates']):
            if len(l) < 2: continue
            pts = P.px(l)
            if P.dentro(pts, larg_px + 10):
                d.line([tuple(p) for p in pts], fill=255, width=max(1, int(round(larg_px))), joint='curve')
    return np.asarray(im) > 0

def edt(mask):
    """Distancia, em pixels, ate o pixel VERDADEIRO mais perto."""
    return ndimage.distance_transform_edt(~mask).astype(np.float32)

def fecha(mask, r_px):
    """Fechamento morfologico por EDT: engorda r e encolhe r. Une o que esta a
    menos de 2r e arredonda o canto de dentro — a concordancia do cruzamento."""
    if r_px < 1: return mask
    dil = edt(mask) <= r_px
    return edt(~dil) >= r_px

def desloca(a, dx, dy):
    """A imagem empurrada dx, dy pixels (o que sai por um lado nao volta)."""
    out = np.zeros_like(a)
    H, W = a.shape[:2]
    sx0, sx1 = max(0, dx), min(W, W + dx)
    sy0, sy1 = max(0, dy), min(H, H + dy)
    out[sy0:sy1, sx0:sx1] = a[sy0 - dy:sy1 - dy, sx0 - dx:sx1 - dx]
    return out

def urbano_de(P, predio_mask):
    """
    Onde a rua e de cidade: a mesma regra do carentan.py — o urbano do OSM
    cruzado com onde ha predio de verdade (engorda 22 m, encolhe 14). Com EDT
    isso e duas comparacoes. E' o que decide calcada contra capim e sebe.
    """
    u_osm = mascara_poligonos(geojson('urbano'), P)
    dil = edt(predio_mask) <= 22.0 * P.ppm
    ero = edt(~dil) >= 14.0 * P.ppm
    return u_osm & ero

# ============================================================== AS VIAS
def carrega_vias(P):
    vias = []
    for f in geojson('via'):
        tag = f['properties'].get('h') or ''
        larg, piso = VIAS.get(tag, PADRAO)
        g = f['geometry']
        linhas = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
        for l in linhas:
            if len(l) < 2: continue
            pts = P.px(l)
            if P.dentro(pts, 30 * P.ppm):
                vias.append((pts, tag, larg, piso))
    return vias

def chave(v):
    return (v[2], v[3], v[1] in COM_CALCADA, v[1] in COM_SEBE)

def grupos_de(vias):
    """As combinacoes (largura, piso, calcada, sebe) que existem, numeradas."""
    chaves = sorted({chave(v) for v in vias})
    return {k: i for i, k in enumerate(chaves)}

def desenha_eixos(vias, grupos, P):
    """Um eixo de 1 px por grupo: e dele que sai a distancia lateral."""
    ims = [Image.new('L', (P.W, P.H), 0) for _ in grupos]
    ds = [ImageDraw.Draw(im) for im in ims]
    for v in vias:
        ds[grupos[chave(v)]].line([tuple(p) for p in v[0]], fill=255, width=1)
    return [np.asarray(im) > 0 for im in ims]

def desenha_pista(vias, P, extra_m=0.0, folga_px=3):
    """
    A uniao dos poligonos das vias, com PONTA RETA, engordada extra_m para cada
    lado.

    O simbolo do QGIS terminava em semicirculo, e e isso que dava o ar de linha
    grossa de caneta: uma rua acaba numa cerca, num portao, num patio — reta.
    So se emenda em circulo onde a ponta cai em cima de outra via (a esquina, ou
    a via partida em duas). A folga de 3 px deixa a borda ser decidida pelo
    campo de distancia deste mesmo poligono, ja com o tremor, e nao pelo
    serrilhado do traco.
    """
    im = Image.new('L', (P.W, P.H), 0)
    d = ImageDraw.Draw(im)
    todos = []; dono = []
    for i, v in enumerate(vias):
        todos.append(v[0]); dono.append(np.full(len(v[0]), i))
    arvore = cKDTree(np.concatenate(todos)); dono = np.concatenate(dono)
    r = JUNTA_M * P.ppm
    for i, (pts, tag, larg, piso) in enumerate(vias):
        hw = (larg / 2 + extra_m) * P.ppm
        d.line([tuple(p) for p in pts], fill=255, width=int(round(2 * hw + folga_px)), joint='curve')
        for p in (pts[0], pts[-1]):
            viz = arvore.query_ball_point(p, r)
            if any(dono[j] != i for j in viz):
                rr = hw + folga_px / 2
                d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=255)
    return np.asarray(im) > 0

# ============================================================== A PINTURA
def _lerp(a, b, t):
    return a + (b - a) * t

def _cor(c, H, W):
    return np.broadcast_to(np.asarray(c, np.float32), (H, W, 3))

def _sobre(saida, cor, alfa):
    """cor por cima de saida, com alfa (H, W)."""
    return _lerp(saida, cor, alfa[..., None])

def pinta_sebe(saida, a_sebe, P, n_lobo, n_fino, g_px):
    """
    Uma fila de arbustos e arvores pequenas, dada a mascara suave a_sebe.

    Vista de cima a sebe e quase preta, com a copa pegando luz do lado noroeste
    e a sombra caindo comprida para sudeste — o mesmo rumo da sombra dos predios.
    E' a sombra caindo na estrada que faz a estrada parecer afundada entre as
    sebes, que e o que o bocage era para quem estava embaixo. Os lobos claros
    sao as copas individuais: sem eles a sebe e um traco de largura constante.
    """
    H, W = a_sebe.shape
    s = max(1, int(round(SEBE_SOMBRA_M * P.ppm)))
    sombra = desloca(a_sebe, s, s) * (1 - a_sebe)          # a sombra, fora da propria sebe
    sombra = ndimage.uniform_filter(sombra, max(1, int(0.5 * P.ppm)) | 1)
    saida *= (1 - 0.36 * sombra)[..., None]
    k = max(1, int(round(0.7 * P.ppm)))
    luz = np.clip(a_sebe - desloca(a_sebe, k, k), 0, 1)
    esc = np.clip(a_sebe - desloca(a_sebe, -k, -k), 0, 1)
    copas = np.clip((n_lobo - 0.25) / 0.35, 0, 1)          # os lobos que pegam luz
    cor = _cor(SEBE, H, W) * (1 + 0.18 * n_lobo + 0.30 * copas + 0.06 * n_fino + 0.04 * g_px
                              + 0.35 * luz - 0.30 * esc)[..., None]
    return _sobre(saida, cor, a_sebe)

def pinta(nome, prova=False):
    t0 = time.time()
    f = ficha_de(nome); P = Placa(f); W, H = P.W, P.H
    print('%s: %d x %d px, %.3f m/px' % (nome, W, H, P.mpp))

    def le(rot, modo):
        cam = os.path.join(CAMADAS, '%s-%s.png' % (nome, rot))
        if not os.path.exists(cam):
            raise SystemExit('falta %s — rode: carentan.py %s %d --camadas' % (cam, nome, W))
        return np.asarray(Image.open(cam).convert(modo)).astype(np.float32) / 255
    abaixo = le('abaixo', 'RGB'); via_q = le('via', 'RGBA')[..., 3] > 0.5

    # --- a geometria ------------------------------------------------------
    vias = carrega_vias(P)
    grupos = grupos_de(vias)
    ordem_g = sorted(grupos, key=grupos.get)
    larg_g = np.array([k[0] for k in ordem_g], np.float32)
    piso_g = np.array([list(PISO).index(k[1]) for k in ordem_g], np.int8)
    calcada_g = np.array([k[2] for k in ordem_g], bool)
    sebe_g = np.array([k[3] for k in ordem_g], bool)
    print('  %d vias em %d grupos: %s' % (len(vias), len(grupos),
          ', '.join(sorted({'%g m %s' % (k[0], k[1]) for k in ordem_g}))))

    eixos = desenha_eixos(vias, grupos, P)
    # u: distancia lateral NORMALIZADA — 0 no eixo, 1 no beiral da pista do
    # grupo mais perto. grp: qual grupo e esse. E o par que descreve a rua.
    u = np.full((H, W), 8.0, np.float32); grp = np.full((H, W), -1, np.int8)
    d_min = np.full((H, W), 1e9, np.float32)
    for gi, eixo in enumerate(eixos):
        d = edt(eixo)
        ug = d / (larg_g[gi] / 2 * P.ppm)
        melhor = ug < u
        u[melhor] = ug[melhor]; grp[melhor] = gi
        d_min = np.minimum(d_min, d)
        del d, ug, melhor
    perto = grp >= 0
    g0 = np.maximum(grp, 0)

    # --- conferir o registro contra a via do QGIS ---------------------------
    eixo_todos = np.zeros((H, W), bool)
    for e in eixos: eixo_todos |= e
    cobre = via_q[eixo_todos].mean() if eixo_todos.any() else 0
    borda_q = via_q & ~ndimage.binary_erosion(via_q)
    hw_q = np.median(d_min[borda_q]) * P.mpp if borda_q.any() else 0
    print('  registro: %.1f%% do eixo cai dentro da via do QGIS; meia-largura '
          'mediana da via do QGIS %.2f m' % (100 * cobre, hw_q))
    if cobre < 0.9:
        print('  ATENCAO: registro ruim — confira a ficha e a conversao lon/lat')
    del via_q, borda_q, eixo_todos, eixos, d_min

    # --- as mascaras de contexto ----------------------------------------------
    predios = mascara_poligonos(geojson('predio'), P)
    urb = urbano_de(P, predios)
    urb_longe = edt(urb) <= URB_FOLGA_M * P.ppm       # a cidade e arredores
    urb = ndimage.uniform_filter(urb.astype(np.float32), int(6 * P.ppm) | 1)   # 3 m de fusao
    del predios
    agua = mascara_poligonos(geojson('agua'), P) | mascara_linhas(geojson('rio'), P, 8 * P.ppm)
    seco = ~(agua | mascara_poligonos(geojson('brejo'), P))   # nem agua nem brejo
    sem_agua = ~agua                                          # so nao-agua: o aterro cruza o brejo
    del agua
    # os tres poligonos de ponta reta: a pista (fechada em CANTO_M, para o canto
    # de dentro do cruzamento sair arredondado), a faixa de fora (capim, orla,
    # calcada) e a faixa da sebe
    # o tremor do beiral cabe DENTRO do poligono: a folga e de 2x a amplitude mais
    # 3 px, e a borda nominal fica no meio dela. Sem isso o ruido positivo pintava
    # pista solta no campo, longe de qualquer rua.
    borda_px = BORDA_M * P.ppm
    folga = 3.0 + 2.0 * borda_px
    pista_p = fecha(desenha_pista(vias, P, 0.0, folga), CANTO_M * P.ppm)
    fora_p = desenha_pista(vias, P, ACOST_M + CALCADA_M + 0.6)
    sebe_p = desenha_pista(vias, P, SEBE_DE_M + SEBE_MAX_M + 1.4)
    d_in = edt(~pista_p)                                   # px para DENTRO da pista
    del pista_p

    # --- o ruido --------------------------------------------------------------
    n_borda = ruido(W, H, BORDA_ESC_M * P.ppm, SEMENTE + 1, 2)   # o tremor do beiral
    n_largo = ruido(W, H, 16.0 * P.ppm, SEMENTE + 7, 2)    # remendos: manchas de 8 a 20 m
    n_medio = ruido(W, H, 6.0 * P.ppm, SEMENTE + 2)        # desgaste e variacao ao longo
    n_fino = ruido(W, H, 0.9 * P.ppm, SEMENTE + 3, 2)      # a granulacao do piso
    g_px = grao(W, H, SEMENTE + 4)

    hw_m = larg_g[g0] / 2                                  # meia-largura em m, por pixel
    u2 = u + n_borda * (BORDA_M / hw_m)                    # o beiral treme em METROS
    dm = (u2 - 1.0) * hw_m                                 # metros para FORA do beiral
    # a pista: a borda e a distancia para dentro do poligono, tremida, com um
    # pixel de antialias. E' o que da ponta reta e beiral nitido.
    d_b = d_in - folga / 2 + n_borda * borda_px            # px para dentro do beiral
    a_pista = np.clip(d_b + 0.5, 0, 1) * perto * (d_in > 0.5)
    saida = abaixo
    del abaixo, d_in

    # --- 1. a beira: capim e orla clara no campo, calcada na cidade -------------
    # rural: uma orla clara e fina de cascalho, com falhas, e o capim batido
    # amarelado por fora dela. Nada escuro e simetrico: o escuro so vem da sombra
    # da sebe, de um lado so.
    t = dm / ACOST_M                                       # 0 no beiral, 1 no fim
    falha = np.clip((n_medio + 0.45) / 0.25, 0, 1)         # a orla falha em uns 25%
    a_orla = np.where(perto & fora_p & (dm > 0) & (dm < ORLA_M), 0.45 * falha, 0)
    a_capim = np.where(perto & (t > 0) & (t < 1) & seco & fora_p,
                       0.38 * np.clip(1 - t, 0, 1) ** 1.3 * (0.7 + 0.3 * n_medio), 0)
    a_rural = np.maximum(a_orla, a_capim)
    cor_rural = _lerp(_cor(CAPIM, H, W), _cor(ORLA, H, W), (a_orla > 0)[..., None].astype(np.float32))
    cor_rural = cor_rural * (1 + 0.08 * n_fino + 0.04 * g_px)[..., None]
    del t, falha, a_orla, a_capim

    # urbana: a calcada, do beiral para fora, so nas ruas que tem calcada. O
    # meio-fio e a propria linha escura do beiral, que e como ele se ve de cima.
    tem_calc = calcada_g[g0] & perto & fora_p
    a_calc = np.where(tem_calc & (dm >= 0) & (dm < CALCADA_M), 0.70 * (0.9 + 0.1 * n_medio), 0)
    borda_calc = np.clip((dm - (CALCADA_M - 0.25)) / 0.25, 0, 1)
    cor_urb = _cor(CALCADA, H, W) * (1 + 0.05 * n_fino + 0.03 * g_px)[..., None] * (1 - 0.08 * borda_calc)[..., None]
    a_urb = ndimage.uniform_filter(a_calc, 3)              # meio pixel de antialias
    del a_calc, borda_calc, tem_calc, fora_p

    a_fora = _lerp(a_rural, a_urb, urb) * (1 - a_pista)
    cor_fora = _lerp(cor_rural, cor_urb, urb[..., None])
    saida = _sobre(saida, cor_fora, a_fora)
    del a_rural, a_urb, cor_rural, cor_urb, a_fora, cor_fora

    # --- 2. a sebe: ao longo da estrada rural, e a fila de arvores do OSM ------
    n_lobo = ruido(W, H, 2.5 * P.ppm, SEMENTE + 6, 2)       # o recorte da copa
    n_gordo = ruido(W, H, 9.0 * P.ppm, SEMENTE + 8, 1)      # copa gorda e vao fino, a cada 6-12 m
    a_sebe = np.zeros((H, W), np.float32)
    larg_sebe = SEBE_MIN_M + (SEBE_MAX_M - SEBE_MIN_M) * (0.5 + 0.5 * n_gordo)
    larg_sebe = np.maximum(larg_sebe, 3.0 * P.mpp)          # nunca menos de 3 px
    if SEBES:
        # o vao e de baixa frequencia e uma oitava so: com 16 m e tres oitavas a
        # sebe saia em pedacos de cinco metros, que de perto pareciam minhocas
        n_vao = ruido(W, H, 45.0 * P.ppm, SEMENTE + 5, 1)   # onde ha sebe e onde ha vao
        de = SEBE_DE_M + 0.25 * n_lobo
        ate = de + larg_sebe + 0.5 * n_lobo
        a_sebe = (np.clip((dm - de) / 0.3, 0, 1) * np.clip((ate - dm) / 0.3, 0, 1)
                  * np.clip((n_vao + 0.15) / 0.20, 0, 1)         # uns 60% de sebe, 40% de vao
                  * perto * sebe_g[g0] * (~urb_longe) * seco * sebe_p)
        del n_vao, de, ate
    # a fila de arvores que o OSM mapeou (barrier=hedge, natural=tree_row): dado,
    # sem vao sorteado, com o mesmo pincel
    linhas_osm = mascara_linhas(geojson('sebe'), P, 1)
    if linhas_osm.any():
        d_s = edt(linhas_osm) * P.mpp
        meia = larg_sebe / 2 + 0.25 * n_lobo
        a_osm = np.clip((meia - d_s) / 0.3, 0, 1) * sem_agua
        a_sebe = np.maximum(a_sebe, a_osm)
        del d_s, meia, a_osm
    del linhas_osm, sebe_p, urb_longe, larg_sebe, n_gordo
    a_sebe *= (1 - a_pista)                                # nunca em cima da pista
    if a_sebe.any():
        saida = pinta_sebe(saida, a_sebe, P, n_lobo, n_fino, g_px)
    del a_sebe, n_lobo, dm

    # --- 3. a pista -------------------------------------------------------------
    piso_px = piso_g[g0]
    tab = np.asarray([PISO[k] for k in PISO], np.float32)
    cor = tab[piso_px]                                     # (H, W, 3)
    # a emenda entre dois pisos num cruzamento e uma curva dura no meio do
    # asfalto; 3 m de borrao na COR (nao na mascara) a desmancham
    cor = ndimage.uniform_filter(cor, (int(3.0 * P.ppm) | 1, int(3.0 * P.ppm) | 1, 1))

    uu = np.clip(u, 0, 1.2)
    lum = np.ones((H, W), np.float32)
    # o desgaste das rodas: duas faixas mais claras, uma por mao, nas de duas maos;
    # uma so, no meio, nas de mao unica — e interrompidas ao longo, pelo ruido
    duas = (piso_px <= 1)                                  # asfalto e macadame
    desg_2 = np.exp(-((uu - 0.52) / 0.20) ** 2)
    desg_1 = np.exp(-(uu / 0.38) ** 2)
    lum += np.where(duas, 0.09 * desg_2, 0.06 * desg_1) * np.clip(0.55 + 0.6 * n_medio, 0, 1)
    # o beiral: uma linha fina e escura rente a borda (e onde a agua fica e o
    # piso esfarela), e um escurecimento leve para dentro. A linha e nitida de
    # proposito: um gradiente largo deixava a rua fora de foco ao lado dos
    # telhados de vetor. Na cidade ela e o meio-fio.
    beiral_px = BEIRAL_M * P.ppm
    linha = np.clip(d_b + 0.5, 0, 1) * np.clip((beiral_px - d_b) / max(1.0, beiral_px * 0.35), 0, 1)
    lum -= 0.17 * linha * (0.8 + 0.2 * n_medio)
    lum -= 0.04 * np.clip((uu - 0.70) / 0.30, 0, 1)
    # remendos largos, manchas ao longo, granulacao, e o grao do pixel
    lum += 0.05 * n_largo + 0.045 * n_medio + 0.035 * n_fino + 0.02 * g_px
    cor = cor * lum[..., None]
    # a trilha de terra: dois sulcos e capim no meio — so onde da para ver
    terra = (piso_px == 3)
    if terra.any() and P.mpp < 0.4:
        sulco = np.exp(-((uu - 0.55) / 0.11) ** 2)
        capim = np.clip((0.30 - uu) / 0.18, 0, 1) * 0.5
        cor = np.where(terra[..., None], _lerp(cor * (1 - 0.09 * sulco)[..., None], _cor(GRAMA_RUT, H, W), capim[..., None]), cor)
        del sulco, capim
    saida = _sobre(saida, cor, a_pista)
    del cor, lum, desg_2, desg_1, uu, u2, n_borda, n_largo, hw_m, piso_px, u, grp, g0, linha, d_b

    # --- 4. a ferrovia ----------------------------------------------------------
    # Lastro de brita com os dois trilhos em cima, por via — o lastro e a
    # superficie mais clara do terreno, e o trilho um fio escuro mal visivel. Na
    # passagem de nivel o lastro some (o piso da rua atravessa) e so o trilho
    # continua. O aterro atravessa o brejo, entao so a agua o interrompe. A
    # linha abandonada e lastro tomado de capim, sem trilho.
    ferro = geojson('ferro')
    for tipo, com_trilho in (('rail', True), ('abandoned', False)):
        eixo = mascara_linhas(ferro, P, 1, lambda pr, t=tipo: pr.get('r') == t)
        if not eixo.any(): continue
        d = edt(eixo) * P.mpp                                # metros ate o eixo
        a_lastro = np.clip((LASTRO_M / 2 + 0.3 * n_fino - d) / 0.35, 0, 1)
        if com_trilho:
            a_lastro *= (1 - a_pista)                        # a rua passa por cima
            cor_l = _cor(LASTRO, H, W) * (1 + 0.10 * n_fino + 0.05 * g_px
                                          - 0.10 * np.exp(-(d / 0.5) ** 2)
                                          - 0.10 * np.clip((d - LASTRO_M / 2 + 0.6) / 0.6, 0, 1))[..., None]
        else:
            cor_l = _lerp(_cor(LASTRO, H, W), _cor(CAPIM, H, W), 0.55) * (1 + 0.10 * n_fino)[..., None]
        saida = _sobre(saida, cor_l, a_lastro * sem_agua)
        if com_trilho and P.mpp <= 0.3:
            meia = BITOLA_M / 2
            a_trilho = np.clip(np.exp(-((np.abs(d - meia)) / (0.10 + 0.5 * P.mpp)) ** 2) * 0.6, 0, 1)
            saida = _sobre(saida, _cor(TRILHO, H, W), a_trilho)
            del a_trilho
        del eixo, d, a_lastro, cor_l
    del a_pista, n_medio, n_fino, g_px, seco, sem_agua, urb

    # --- 5. o que fica por cima: predios com sombra, grao ---------------------
    acima = le('acima', 'RGBA')
    A = acima[..., 3:4]
    saida = saida * (1 - A) + acima[..., :3] * A
    del acima, A
    saida = np.clip(saida, 0, 1)
    print('  pintado em %.0f s' % (time.time() - t0))

    out8 = (saida * 255 + 0.5).astype(np.uint8)
    im = Image.fromarray(out8, 'RGB')
    if prova:
        prova_de(nome, P, im)
        return
    # o render cru do carentan.py, guardado antes de ser coberto: se o PNG for
    # mais velho que as fatias, e cru (o carentan.py grava o PNG antes delas)
    png = os.path.join(QGIS, nome + '.png'); jpg = os.path.join(QGIS, nome + '.jpg')
    cru = os.path.join(CAMADAS, nome + '-cru.png')
    if os.path.exists(png) and os.path.getmtime(png) < os.path.getmtime(os.path.join(CAMADAS, nome + '-abaixo.png')):
        shutil.copyfile(png, cru)
    im.save(png)
    # 92 com croma inteiro, como o carentan.py: a textura e o que o JPEG faz pior
    im.save(jpg, 'JPEG', quality=92, subsampling=0, optimize=True)
    print('  -> %s.png, %s.jpg (%.1f MB)  %.0f s' % (nome, nome, os.path.getsize(jpg) / 1048576.0, time.time() - t0))
    prova_de(nome, P, im)

# ============================================================== A PROVA
def prova_de(nome, P, im):
    """Cru e pintado lado a lado, no mesmo recorte 1:1 do meio da placa."""
    cru = os.path.join(CAMADAS, nome + '-cru.png')
    if not os.path.exists(cru): cru = os.path.join(QGIS, nome + '.png')
    cw, ch = min(1100, P.W // 2), min(700, P.H // 2)
    x, y = (P.W - cw) // 2, (P.H - ch) // 2
    folha = Image.new('RGB', (cw * 2 + 12, ch), (35, 48, 58))
    a = Image.open(cru).convert('RGB').crop((x, y, x + cw, y + ch))
    folha.paste(a, (0, 0)); folha.paste(im.crop((x, y, x + cw, y + ch)), (cw + 12, 0))
    alvo = os.path.join(CAMADAS, nome + '-prova.jpg')
    folha.save(alvo, quality=90)
    print('  prova ->', alvo)

def recorte(nome, lon, lat, larg_m, alvo, larg_px=1600):
    """Um recorte da placa pintada, centrado em lon/lat, com larg_m de chao."""
    P = Placa(ficha_de(nome))
    cx, cy = P.px([[lon, lat]])[0]
    w = larg_m * P.ppm; h = w * 9 / 16
    im = Image.open(os.path.join(QGIS, nome + '.png')).convert('RGB')
    caixa = (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))
    im.crop(caixa).resize((larg_px, int(larg_px * 9 / 16)), Image.LANCZOS).save(alvo, quality=90)
    print('->', alvo)

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--recorte' in sys.argv:
        recorte(args[0], float(args[1]), float(args[2]), float(args[3]), args[4])
        sys.exit()
    nomes = args or sorted({f.rsplit('-', 1)[0] for f in os.listdir(CAMADAS) if f.endswith('-abaixo.png')})
    for n in nomes:
        pinta(n, prova='--prova' in sys.argv)
