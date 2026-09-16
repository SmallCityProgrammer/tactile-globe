# sinuoso.py — tirar o "tudo em L" do desenho.
#
# A queixa: "muitos angulos sao pouco naturais, sem sinuosidade, todos em L".
# O OSM entrega poligonos de canto reto, e o textura.py corta as lajes do patio
# em linhas paralelas aos eixos da tela. Um mapa desenhado a mao tem um tremor
# em toda linha.
#
# Sao duas frentes, independentes:
#
#   ONDULAR A GEOMETRIA  — densificar cada contorno e deslocar cada vertice por
#                          um campo de ruido SUAVE amostrado na propria posicao
#                          do vertice. Costa, mata e patio ganham um vagar
#                          organico sem sair do lugar.
#
#   ENTORTAR AS JUNTAS   — o corte das lajes deixa de ser reto: as coordenadas
#                          de amostragem sao dobradas por um ruido periodico
#                          antes de decidir a que laje cada pixel pertence.
#
# A ARMADILHA CENTRAL (medida, nao suposta)
# terra e mar PARTILHAM a linha de costa: no pearl.py, mar = retangulo - terra.
# Ondular a terra e nao o mar abre um vazio de 179.106 m2 ao longo de toda a
# costa (a 14 m de amplitude; 252.021 m2 a 18 m) — 1,17 px de largura no render
# de 3000 px, o fundo teal aparecendo por baixo da praia. A base tambem:
# recortada na terra antiga, sobram 30.580 m2 de concreto por cima da agua.
#
# A ordem certa esta em deriva(): ondula a TERRA primeiro e RECALCULA mar e base
# a partir dela. Verificado em 0,000000 m2 de vazio e 0,000000 m2 de
# sobreposicao. Custa 0,003 s.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" sinuoso.py
import os, sys, glob, math, hashlib
import numpy as np
from qgis.core import QgsGeometry, QgsPointXY, QgsRectangle, QgsFeature, QgsVectorLayer

# ============================================================== O CAMPO DE RUIDO
#
# Tem que ser FUNCAO PURA DA POSICAO NO MUNDO, e nao da posicao do vertice
# dentro do anel. E isso, e so isso, que faz a costa da terra e a costa do mar
# andarem juntas: dois vertices na mesma coordenada recebem o mesmo empurrao,
# venham do anel que vierem, na ordem que vierem.
#
# Por isso NAO serve nada que ande ao longo da linha — wave(), wave_randomized(),
# triangular_wave() — nem nada que dependa do indice do vertice. Ver a secao
# EXPRESSOES no fim deste arquivo, onde isso esta medido.
#
# A rede e infinita: o valor de cada no sai de um hash de (i, j), sem tabela.
# Coordenada 3857 no Havai e da ordem de 1,76e7 m, o que estoura qualquer grade
# pre-computada de tamanho razoavel.
_M32 = np.uint64(0xFFFFFFFF)

def _hash01(i, j, s):
    """Valor em [0,1) para o no inteiro (i, j) da rede. Estavel entre rodadas."""
    i = (i.astype(np.int64) & 0xFFFFFFFF).astype(np.uint64)
    j = (j.astype(np.int64) & 0xFFFFFFFF).astype(np.uint64)
    h = (i * np.uint64(374761393) + j * np.uint64(668265263) + np.uint64(s)) & _M32
    h = ((h ^ (h >> np.uint64(13))) * np.uint64(1274126177)) & _M32
    return ((h ^ (h >> np.uint64(16))) & _M32).astype(np.float64) / 4294967296.0

def _valor(x, y, cel, s):
    """Ruido de valor bilinear com hermite — a mesma receita do textura.py."""
    u, v = x / cel, y / cel
    i, j = np.floor(u), np.floor(v)
    fu, fv = u - i, v - j
    i = i.astype(np.int64); j = j.astype(np.int64)
    su = fu * fu * (3 - 2 * fu); sv = fv * fv * (3 - 2 * fv)
    a = _hash01(i,     j,     s); b = _hash01(i + 1, j,     s)
    c = _hash01(i,     j + 1, s); d = _hash01(i + 1, j + 1, s)
    return (a + (b - a) * su) * (1 - sv) + (c + (d - c) * su) * sv

# Ganho: o fBm normalizado por soma-das-amplitudes nao usa [0,1] inteiro, ele se
# aperta em torno de 0,5 — o mesmo problema que o textura.py resolve medindo a
# faixa. Aqui a faixa nao pode ser medida a posteriori (o campo e infinito),
# entao vai medida de uma vez, por amostragem, e gravada como constante. Sem
# isso 'amp' nao quer dizer nada: pedia-se 18 m e o pico era 12,2 m.
_GANHO = {1: 1.10, 2: 1.34, 3: 1.51, 4: 1.61}

def campo(x, y, cel, s, oitavas=2):
    """Ruido fBm em ~[-1,1], funcao pura de (x, y) em metros de 3857."""
    val = np.zeros_like(x, dtype=np.float64); amp = 1.0; soma = 0.0
    for k in range(oitavas):
        val += amp * _valor(x, y, cel / (2 ** k), s + k * 977)
        soma += amp; amp *= 0.5
    return np.clip((val / soma - 0.5) * 2.0 * _GANHO.get(oitavas, 1.6), -1.0, 1.0)

def desloca(x, y, amp, cel, semente=1941, oitavas=2, peso=None):
    """(dx, dy) em metros. Duas sementes distantes = dois campos independentes."""
    dx = campo(x, y, cel, semente,        oitavas) * amp
    dy = campo(x, y, cel, semente + 5150, oitavas) * amp
    if peso is not None:
        dx = dx * peso; dy = dy * peso
    return dx, dy

# ============================================================== ONDULAR
def congela(ext, faixa):
    """
    Peso que vai a ZERO junto da moldura do render.

    A terra do pearl.py e poligonizada com o retangulo da moldura junto, entao
    parte do contorno dela E a borda da figura. Ondular ali faria a figura ter a
    aresta serrilhada, e o mar apareceria por fora da terra na quina. O peso cai
    suavemente nos ultimos 'faixa' metros.
    """
    x0, y0 = ext.xMinimum(), ext.yMinimum()
    x1, y1 = ext.xMaximum(), ext.yMaximum()
    def peso(xs, ys):
        d = np.minimum(np.minimum(xs - x0, x1 - xs), np.minimum(ys - y0, y1 - ys))
        t = np.clip(d / faixa, 0.0, 1.0)
        return t * t * (3 - 2 * t)
    return peso

def ondula(g, amp, cel, semente=1941, oitavas=2, interval=25.0, peso_fn=None):
    """
    Densifica o contorno e desloca cada vertice pelo campo.

    'interval' e o passo da densificacao em METROS. Ele nao e cosmetico: e ele
    que decide se dois poligonos que partilham uma aresta continuam partilhando.
    densifyByDistance parte cada segmento em n pedacos iguais com
    n = ceil(comprimento/interval) — deterministico e simetrico —, entao o mesmo
    segmento em duas camadas recebe exatamente os mesmos pontos, bit a bit.
    Medido: 6.167 vertices da terra, TODOS presentes nos 17.101 do mar. Com
    intervalos diferentes (25 e 30) o vazio reaparece.
    """
    if interval:
        g = g.densifyByDistance(interval)
    polys = g.asMultiPolygon() if g.isMultipart() else [g.asPolygon()]
    novo = []
    for poly in polys:
        aneis = []
        for anel in poly:
            n = len(anel)
            if n < 4: aneis.append(anel); continue
            xs = np.fromiter((p.x() for p in anel), np.float64, n)
            ys = np.fromiter((p.y() for p in anel), np.float64, n)
            peso = peso_fn(xs, ys) if peso_fn else None
            dx, dy = desloca(xs, ys, amp, cel, semente, oitavas, peso)
            nx, ny = xs + dx, ys + dy
            nx[-1], ny[-1] = nx[0], ny[0]        # o anel tem que fechar
            aneis.append([QgsPointXY(float(a), float(b)) for a, b in zip(nx, ny)])
        novo.append(aneis)
    ng = QgsGeometry.fromMultiPolygonXY(novo) if g.isMultipart() else QgsGeometry.fromPolygonXY(novo[0])
    if not ng.isGeosValid():
        ng = ng.makeValid()                      # amplitude alta dobra a linha em cabo estreito
    return ng

def ondula_camada(layer, amp, cel, semente=1941, oitavas=2, interval=25.0, peso_fn=None):
    """A camada inteira, em memoria, mantendo os campos."""
    saida = QgsVectorLayer('MultiPolygon?crs=' + layer.crs().authid(), layer.name(), 'memory')
    dp = saida.dataProvider()
    dp.addAttributes(layer.fields()); saida.updateFields()
    lote = []
    for f in layer.getFeatures():
        nf = QgsFeature(saida.fields()); nf.setAttributes(f.attributes())
        nf.setGeometry(ondula(f.geometry(), amp, cel, semente, oitavas, interval, peso_fn))
        lote.append(nf)
    dp.addFeatures(lote); saida.updateExtents()
    return saida

# ============================================================== A ORDEM CERTA
#
# Quem partilha contorno com quem:
#
#     mar  = retangulo_grande - terra          (o pearl.py faz assim)
#     base = (buffer dos predios) ∩ terra
#     verde, aero, pier: por cima da terra, sem partilhar aresta
#
# Entao a terra e a unica que pode ser ondulada por conta propria. Mar e base
# tem que ser REFEITOS depois, nunca ondulados em paralelo.
def deriva(terras, mar_ret, base_bruta=None, amp=14.0, cel=220.0, interval=25.0,
           semente=1941, oitavas=2, peso_fn=None, amp_base=0.0, cel_base=120.0):
    """
    Devolve (terra_ondulada, mar_refeito, base_refeita).

    terras     lista de QgsGeometry (as faces de terra)
    mar_ret    o retangulo grande do mar, ANTES da diferenca — ou a geometria do
               mar atual, de onde se tira o boundingBox
    base_bruta o apron ANTES do corte na costa; se vier ja cortado tambem serve,
               porque o recorte na terra ondulada e refeito de qualquer jeito
    amp_base   > 0 ondula tambem a aresta propria do patio (a que nao e costa);
               a aresta que E costa vem da terra e nao se mexe.
    """
    tw = [ondula(g, amp, cel, semente, oitavas, interval, peso_fn) for g in terras]
    t_un = QgsGeometry.unaryUnion(tw)
    ret = mar_ret if isinstance(mar_ret, QgsRectangle) else mar_ret.boundingBox()
    mw = QgsGeometry.fromRect(ret).difference(t_un)
    bw = None
    if base_bruta is not None:
        bw = base_bruta
        if amp_base > 0:
            bw = ondula(bw, amp_base, cel_base, semente + 313, oitavas, interval, peso_fn)
        bw = bw.intersection(t_un)               # o corte na costa, refeito
    return tw, mw, bw

# ============================================================== AS JUNTAS DA LAJE
#
# O apron() do textura.py corta as lajes em ys[] e xs[] retos: toda junta fica a
# 0 ou 90 graus na tela. As duas saidas, medidas:
#
#   GIRAR O LADRILHO  QgsRasterFillSymbolLayer.setAngle() existe, aceita float e
#                     int, e e data-definable por Property.Angle. Gira a MALHA
#                     inteira de lajes: o "tudo em L" some de uma vez.
#
#   DOBRAR OS CORTES  as coordenadas de amostragem passam por um ruido PERIODICO
#                     antes de decidir a laje. A junta deixa de ser de regua,
#                     mas a DIRECAO MEDIA continua 0/90 — sozinho, isto nao
#                     resolve a queixa.
#
# As duas, juntas: e esta funcao (torto) mais sl.setAngle(12).
#
# A COSTURA — a preocupacao legitima, verificada e DESCARTADA
# A chapa do patio NAO e emendavel, e nunca foi: o degrau do wrap esta no
# percentil 100 dos degraus internos (coluna 8,71 contra maximo interno 5,49;
# linha 31,71 contra 33,07). Nunca apareceu porque a 0 grau a borda do ladrilho
# cai EXATAMENTE na borda do quadro — 15.579 px de marca, que e 3 x 3000 + 3 x
# 2196, a moldura inteira e nada por dentro.
#
# Girada 36 graus a borda passa a atravessar o quadro (duas vezes com a chapa de
# 3456, uma vez com 4096 — a conta e L cos a + A sin a contra o lado, e o pior
# caso e a diagonal, 3718 px para 3000 x 2196). E deslocar a imagem de um periodo
# devolve COPIA LITERAL: 0,376 nivel de cinza de diferenca, contra 7,88 entre
# posicoes sem relacao. Ou seja: repete mesmo.
#
# So que NAO SE VE. Medido no render de 3000 px, no lugar exato onde a marca diz
# que a borda passa:
#     degrau atravessando a emenda        0,542 nivel/px
#     degrau tipico do resto da textura   0,870 nivel/px
#     degrau de uma junta de laje         18,76 nivel/px
# A emenda e mais suave que o proprio grao da textura. A razao e que o ladrilho e
# de MODULACAO com forca=0,15: 8,7 de alfa viram meio nivel de cinza sobre o
# bege. Olhando o recorte lado a lado (prova9), nao ha linha nenhuma.
#
# CUIDADO: isso vale para ESTA chapa, que e enorme e fraca. O laje() do cais
# (22 mm, ~36 repeticoes na tela) e o rocada() do campo de pouso (70 mm, ~11
# repeticoes) tambem NAO sao emendaveis — percentil 99,2 e 99,6 — e esses
# repetem de verdade. Girar aqueles e outra conversa.
def _valor_np(w, h, nx, ny, semente):
    """O _valor() vetorizado sobre uma grade PERIODICA — copiado do textura.py."""
    g = np.random.default_rng(semente).random((ny, nx))
    x = np.arange(w, dtype=np.float32) / w * nx
    y = np.arange(h, dtype=np.float32) / h * ny
    xi = np.floor(x).astype(np.int64) % nx; xf = (x - np.floor(x)).astype(np.float32)
    yi = np.floor(y).astype(np.int64) % ny; yf = (y - np.floor(y)).astype(np.float32)
    x1 = (xi + 1) % nx; y1 = (yi + 1) % ny
    u = (xf*xf*(3-2*xf))[None, :]; v = (yf*yf*(3-2*yf))[:, None]
    a = g[np.ix_(yi, xi)]; b = g[np.ix_(yi, x1)]
    c = g[np.ix_(y1, xi)]; d = g[np.ix_(y1, x1)]
    return ((a + (b-a)*u) * (1-v) + (c + (d-c)*u) * v).astype(np.float32)

def _fbm_np(w, h, cel_px, oitavas, semente):
    val = np.zeros((h, w), np.float32); amp = 1.0; soma = 0.0
    for k in range(oitavas):
        nx = max(2, int(round(w / cel_px * (2**k)))); ny = max(2, int(round(h / cel_px * (2**k))))
        val += amp * _valor_np(w, h, nx, ny, semente + k*977); soma += amp; amp *= 0.5
    lo, hi = np.percentile(val, 1), np.percentile(val, 99)
    return np.clip((val/soma - lo/soma) / (((hi-lo)/soma) or 1.0), 0, 1)

def _cortes(total, alvo, jitter, rng):
    c = [0.0]
    while c[-1] < total:
        c.append(c[-1] + max(4.0, alvo * (1.0 + rng.uniform(-jitter, jitter))))
    return np.array(c, np.float32)

def apron_sinuoso(pasta, nome, lado=3456, placa=90, jitter=0.35, semente=1941, forca=0.15,
                  junta=0.55, junta_px=2.0, variacao=0.32, nodoa=0.55, nodoa_cel=620,
                  grao=0.30, grao_cel=9.0, torto=11.0, torto_cel=430.0, CLARO=0.55,
                  _guarda=None):
    """
    O apron() do textura.py com as JUNTAS DOBRADAS.

    torto      amplitude do entorte, em px do ladrilho (= px de tela a 96 dpi)
    torto_cel  comprimento de onda do entorte, em px. Tem que ser bem maior que
               'placa', senao a laje deixa de parecer laje e vira poca.

    O truque e o mesmo do domain warp: em vez de mexer nos cortes, mexe-se em
    ONDE cada pixel acha que esta. O ruido do entorte e periodico no ladrilho
    (e o _valor_np, de grade modular), entao a emenda nao piora nem um pouco.

    Custa mexer no laco: com o entorte, a faixa a que um pixel pertence deixa de
    ser constante na linha, e o codigo original escrevia a linha inteira de uma
    vez. A solucao que mantem o custo e varrer uma TIRA de linhas por faixa, com
    margem de 'torto' px dos dois lados — so ali e que a faixa pode aparecer.
    """
    from qgis.PyQt.QtGui import QImage
    params = dict(lado=lado, placa=placa, jitter=jitter, semente=semente, forca=forca,
                  junta=junta, junta_px=junta_px, variacao=variacao, nodoa=nodoa,
                  nodoa_cel=nodoa_cel, grao=grao, grao_cel=grao_cel,
                  torto=torto, torto_cel=torto_cel)

    def pinta():
        rng = np.random.default_rng(semente)
        w = h = lado
        ys = _cortes(h, placa, jitter, rng)
        yy = np.arange(h, dtype=np.float32); xx = np.arange(w, dtype=np.float32)

        # O ENTORTE. Dois campos periodicos, um para cada eixo.
        if torto > 0:
            nx = max(2, int(round(w / torto_cel))); ny = max(2, int(round(h / torto_cel)))
            wx = (_valor_np(w, h, nx, ny, semente + 4001) - 0.5) * 2.0 * torto
            wy = (_valor_np(w, h, nx, ny, semente + 8009) - 0.5) * 2.0 * torto
            # uma oitava mais curta da a tremida de mao; sem ela a junta vira arco de compasso
            nx2, ny2 = max(2, int(nx * 3)), max(2, int(ny * 3))
            wx += (_valor_np(w, h, nx2, ny2, semente + 4002) - 0.5) * 2.0 * torto * 0.35
            wy += (_valor_np(w, h, nx2, ny2, semente + 8010) - 0.5) * 2.0 * torto * 0.35
            Xw = xx[None, :] + wx; Yw = yy[:, None] + wy
            marg = int(math.ceil(torto * 1.4)) + 2
        else:
            Xw = np.broadcast_to(xx[None, :], (h, w)).copy()
            Yw = np.broadcast_to(yy[:, None], (h, w)).copy()
            marg = 1

        t = np.full((h, w), 0.5, np.float32)
        na_junta = np.zeros((h, w), bool)
        nb = len(ys) - 1
        for i in range(nb):
            r0 = max(0, int(math.floor(ys[i])) - marg)
            r1 = min(h, int(math.ceil(ys[i + 1])) + marg)
            if r1 <= r0: continue
            sy = Yw[r0:r1]; sx = Xw[r0:r1]
            m = np.ones(sy.shape, bool)
            if i > 0:      m &= (sy >= ys[i])
            if i < nb - 1: m &= (sy < ys[i + 1])
            # os cortes em x sao sorteados SEMPRE, faixa cheia ou vazia, para a
            # sequencia do rng nao depender do entorte
            xs = _cortes(w, placa * (1.0 + rng.uniform(-0.25, 0.25)), jitter, rng)
            xs -= rng.uniform(0, placa)
            tom = 0.5 + (rng.random(len(xs) - 1) - 0.5) * variacao
            if not m.any(): continue
            xv = sx[m]; yv = sy[m]
            col = np.clip(np.searchsorted(xs, xv, side='right') - 1, 0, len(xs) - 2)
            tt = t[r0:r1]; tt[m] = tom[col]
            jj = na_junta[r0:r1]
            jj[m] = (np.abs(xv - xs[col]) < junta_px) | (np.abs(yv - ys[i]) < junta_px)

        if nodoa > 0:
            t += (_fbm_np(w, h, nodoa_cel, 4, semente + 31) - 0.5) * nodoa
        if grao > 0:
            t += (_valor_np(w, h, max(2, int(w/grao_cel)), max(2, int(h/grao_cel)),
                            semente + 7717) - 0.5) * grao
        t = np.clip(np.where(na_junta, t - junta, t), 0, 1)

        d = (t - 0.5) * 2.0
        alfa = np.where(d > 0, np.clip(d * forca * CLARO * 255.0, 0, 255),
                               np.clip(-d * forca * 255.0, 0, 255)).astype(np.uint8)
        tom = np.where(d > 0, 255, 0).astype(np.uint8)
        buf = np.empty((h, w, 4), np.uint8)       # ARGB32 little-endian: B,G,R,A
        buf[..., 0] = tom; buf[..., 1] = tom; buf[..., 2] = tom; buf[..., 3] = alfa
        buf = np.ascontiguousarray(buf)
        return QImage(buf.data, w, h, 4*w, QImage.Format_ARGB32).copy()

    if _guarda is None:
        raise ValueError('passe _guarda=textura._guarda')
    return _guarda(pasta, nome, params, pinta)

# ============================================================== EXPRESSOES
#
# A rota (b) — QgsGeometryGeneratorSymbolLayer com expressao — foi sondada
# funcao por funcao nesta instalacao (3.44.12). O resumo:
#
#   NAO EXISTE     noise(), perlin(), qualquer ruido nomeado. 391 funcoes, zero.
#   EXISTE         smooth, densify_by_distance, densify_by_count, offset_curve,
#                  wave, wave_randomized, triangular_wave[_randomized],
#                  square_wave[_randomized], simplify, simplify_vw,
#                  affine_transform, translate, rotate, extrude, point_n,
#                  num_points, x_at/y_at, array_foreach, generate_series,
#                  make_line, make_polygon, randf(min,max,semente).
#
# RUIDO POR EXPRESSAO: DA, e foi medido funcionando.
# randf(-1, 1, hash_inteiro_de(i,j)) da o valor do no; floor() da o no; o
# hermite e aritmetica. Quatro randf + a bilinear = 1.337 caracteres por eixo.
# Verificado continuo: em x, +1 m muda 0,00004 e +110 m muda 0,36.
# Remontando o poligono com make_polygon(make_line(array_foreach(...))) sai
# geometria valida. EXPR = 2.951 caracteres.
#
# MAS a rota nao serve aqui, por tres motivos MEDIDOS:
#
#   1. exterior_ring() devolve NULL em MULTIpoligono, e terra e mar sao ambos
#      multipart. Daria para varrer as partes com geometry_n(), mas
#      make_polygon(make_line(anel_externo)) DESCARTA OS FUROS — e o mar leva a
#      terra como furos, que e o que alimenta o shapeburst do raso. O raso
#      morreria.
#
#   2. custo por RENDER, nao uma vez: 5,38 ms por feicao nas 656 do verde =
#      3,53 s todo render, contra 0,50 s uma vez so no numpy.
#
#   3. as funcoes prontas de onda NAO respeitam a aresta partilhada, porque
#      andam ao longo da linha e nao pela posicao no mundo. Medido na moldura:
#          wave_randomized(60,240,6,18,3)   478.264 m2 de vazio (2,18 px)
#          wave(150, 10, false)             104.404 m2 de vazio (0,52 px)
#          triangular_wave_randomized       397.495 m2 de vazio (1,85 px)
#      e as tres devolvem geometria NAO VALIDA (isGeosValid() False).
#
# Ou seja: da para escrever ruido por vertice em expressao, e a expressao ate
# preserva a aresta partilhada (porque tambem e funcao da posicao). O que mata e
# o furo perdido e o custo por render. A rota (a) faz o mesmo, uma vez so, e
# escreve em .gpkg.
EXPR_RUIDO_DOC = '''
Para quem quiser a rota (b) num caso simples (poligono sem furo, sem multipart):

def _ruido_expr(cel, s):
    u = '(x(@p) / {c})'.format(c=cel); v = '(y(@p) / {c})'.format(c=cel)
    I = 'floor(%s)' % u; J = 'floor(%s)' % v
    fu = '(%s - %s)' % (u, I); fv = '(%s - %s)' % (v, J)
    su = '({f} * {f} * (3 - 2 * {f}))'.format(f=fu)
    sv = '({f} * {f} * (3 - 2 * {f}))'.format(f=fv)
    R = lambda a, b: ('randf(-1, 1, ((({i}) + {a}) * 73856093 + (({j}) + {b}) '
                      '* 19349663 + {s}) % 2147483647)').format(i=I, j=J, a=a, b=b, s=s)
    return ('((({A} + ({B} - {A}) * {su}) * (1 - {sv})) + '
            '(({C} + ({D} - {C}) * {su}) * {sv}))').format(
                A=R(0,0), B=R(1,0), C=R(0,1), D=R(1,1), su=su, sv=sv)

EXPR = ("make_polygon(make_line(array_foreach(generate_series(1, num_points(R)), "
        "with_variable('p', point_n(R, @element), DESL))))")
  com R    = exterior_ring(densify_by_distance($geometry, 25))
  e   DESL = make_point(x(@p) + 18 * ruido(220, 11), y(@p) + 18 * ruido(220, 5150))
'''

# ============================================================== OS NUMEROS
#
# Tudo em METROS de terreno (a geometria e 3857), nao em milimetros de tela: o
# tremor pertence ao desenho, nao ao papel — ele tem que crescer ao aproximar,
# como cresce a costa. O render do pearl.py e 3000 px sobre 12.245 m, ou
# 4,08 m/px; em ford-island da 1,67 m/px e no hangar 0,44 m/px.
#
#            amp    cel   dens  oitavas   por que
# terra/mar   14    220    25      2      ver abaixo
# verde       11    130    25      2      mata e mais miuda que a costa
# base        --    ---    --      -      so RECORTADA na terra ondulada
# predio      --    ---    --      -      nao ondula (ver abaixo)
#
# AMPLITUDE. Varrida em 8 / 14 / 20 / 30 m, olhando o render de 3000 px:
#   8 m  timido demais, quase nao se distingue do original (2 px)
#   14 m e o ponto: 3,4 px no mapa inteiro, 32 px no hangar. As retas longas
#        somem, a peninsula continua a mesma peninsula
#   20 m ja come detalhe de costa — as reentrancias pequenas viram bojos
#   30 m DESTROI as valas dos diques secos de Ford Island, que tem 20-30 m de
#        largura: as quatro fendas fecham e viram uma mancha
#   O teto nao e estetico, e geometrico: a amplitude tem que ficar bem abaixo da
#   METADE da feicao mais estreita que se quer manter.
#
# INTERVALO DE DENSIFICACAO. Varrido em 10 / 25 / 60 / 150 m:
#   10 e 25 sao indistinguiveis; 10 custa o dobro dos vertices
#   60  a curva volta a ler como poligono, com lados retos entre vertices
#   150 desiste: sao as MESMAS retas de antes, so deslocadas
#   A regra que sai disso: intervalo <= cel/8. Com cel 220, 25 m.
#
# COMPRIMENTO DE ONDA E OITAVAS. cel 90 vira penugem (22 px no mapa inteiro,
# le como ruido e nao como mao); cel 220 com 1 oitava fica regular demais, todas
# as curvas do mesmo tamanho; cel 500 com 3 oitavas e bonito mas ARRASTA a costa
# para longe do lugar. cel 220 com 2 oitavas (220 e 110 m) e a que parece
# desenhada: uma curva larga com uma ondinha por cima.
#
# CUSTO, medido:
#   terra 2 feicoes  2.882 ->  6.169 vertices   0,04 s
#   base  1 feicao   5.056 -> 12.048 vertices   0,09 s
#   mar   1 feicao   2.887 -> 17.104 vertices   0,07 s  (nao precisa: e refeito)
#   verde 656 feicoes 12.570 vertices           0,82 s
#   predio 5533 feicoes 70.567 vertices         6,16 s
#   refazer o mar por diferenca                 0,003 s
#   O render nao muda: 2,2 a 3,2 s nos dois casos.
#
# O QUE NAO ONDULA, E POR QUE
#   O PATIO DE CONCRETO. Na referencia do Operations Room o concreto e reto —
#   e o contraste entre a costa organica e a chapa reta e justamente o que faz o
#   desenho ler como desenho. Ondulado a 9 m a aresta do patio nao melhora nada
#   e estraga o contraste. A aresta que E costa vem da terra de qualquer jeito.
#
#   OS PREDIOS. A 4,08 m/px um predio tem 10 a 30 px; 2,2 m de tremor sao 0,5 px
#   e so borram o contorno. Pior: 'comp', 'larg' e 'rumo' saem da caixa minima
#   orientada do predio ORIGINAL, e o telhado em SVG e desenhado com eles — um
#   contorno ondulado debaixo de um telhado reto descola os dois. E custa 6,16 s.
#   Se um dia quiser, tem que recalcular a caixa depois de ondular.
#
#   O CAIS E O CAMPO DE POUSO. Man-made, pela mesma razao do patio.
#
RECEITA = dict(terra=dict(amp=14.0, cel=220.0, interval=25.0, oitavas=2, semente=1941),
               verde=dict(amp=11.0, cel=130.0, interval=25.0, oitavas=2, semente=777),
               patio=dict(torto=12.0, torto_cel=430.0, angulo=12.0),
               congela_m=600.0)

def receita_pearl():
    """
    O que mudar no pearl.py. Nao ha nada a mudar no estilo.py alem do angulo.

    1) depois de montar 'terra' e ANTES de montar 'mar' e 'base':

        import sinuoso as SN
        ext_render = tr.transformBoundingBox(QgsRectangle(W, S, E, N))
        peso = SN.congela(ext_render, 600.0)
        tw = [SN.ondula(f.geometry(), 14.0, 220.0, 1941, 2, 25.0, peso)
              for f in terra.getFeatures()]
        terra = mem('terra', 'Polygon'); terra.dataProvider().addFeatures(...)

       e so entao o `mar = difference(retangulo, terra)` e o
       `base = clip(base, terra)` que ja existem. A ORDEM e o ponto: os dois
       dependem da terra, entao a terra tem que estar ondulada primeiro.

    2) o verde, que nao partilha aresta com ninguem, pode ondular sozinho —
       mas em 3857. Ele vem em 4326:

        verde = SN.ondula_camada(corre('native:reprojectlayer',
                    {'INPUT': verde, 'TARGET_CRS': MERC}),
                    11.0, 130.0, 777, 2, 25.0, peso)

    3) no estilo.py, patio():

        chapa = sobre(SN.apron_sinuoso(pasta, 'patio', torto=12.0,
                                       torto_cel=430.0, _guarda=T._guarda),
                      T.ESC_PATIO)
        chapa.setAngle(12.0)
    """
    return RECEITA

# ============================================================== AUTOTESTE
# Roda sozinho contra os .gpkg que o pearl.py ja gravou e prova, com numeros, o
# que este arquivo afirma. Nao escreve nada na pasta do projeto.
#
#   set MAPA=...\Pacifico WW2
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" sinuoso.py
def _autoteste(pasta_qgis, pasta_saida):
    from qgis.core import (QgsVectorLayer, QgsCoordinateReferenceSystem,
                           QgsCoordinateTransform, QgsProject)
    import time
    MERC = QgsCoordinateReferenceSystem('EPSG:3857')
    WGS = QgsCoordinateReferenceSystem('EPSG:4326')
    tr = QgsCoordinateTransform(WGS, MERC, QgsProject.instance())
    S, W, N, E = 21.325, -158.030, 21.400, -157.920
    ext = tr.transformBoundingBox(QgsRectangle(W, S, E, N))
    def gp(n):
        v = QgsVectorLayer(os.path.join(pasta_qgis, n + '.gpkg') + '|layername=' + n, n, 'ogr')
        assert v.isValid(), n
        return v
    terra, mar, base = gp('terra'), gp('mar'), gp('base')
    terras = [f.geometry() for f in terra.getFeatures()]
    mar_g = next(mar.getFeatures()).geometry()
    base_g = next(base.getFeatures()).geometry()
    k = RECEITA['terra']
    peso = congela(ext, RECEITA['congela_m'])

    t0 = time.time()
    tw, mw, bw = deriva(terras, mar_g, base_g, amp=k['amp'], cel=k['cel'],
                        interval=k['interval'], semente=k['semente'],
                        oitavas=k['oitavas'], peso_fn=peso)
    dt = time.time() - t0
    t_un = QgsGeometry.unaryUnion(tw)
    quadro = QgsGeometry.fromRect(ext)
    vazio = quadro.difference(t_un.combine(mw))
    print('deriva(): %.3f s' % dt)
    print('  vazio terra/mar na moldura ....... %.6f m2   (esperado 0)' % vazio.area())
    print('  sobreposicao terra/mar ........... %.6f m2   (esperado 0)' % t_un.intersection(mw).area())
    print('  base fora da terra ondulada ...... %.6f m2   (esperado 0)' % bw.difference(t_un).area())
    a0 = QgsGeometry.unaryUnion(terras).area()
    print('  area de terra .................... %.0f -> %.0f m2 (%+.3f%%)'
          % (a0, t_un.area(), 100 * (t_un.area() - a0) / a0))
    b0, b1 = terra.extent(), t_un.boundingBox()
    print('  moldura congelada: canto SO anda %.2f m em x, %.2f m em y'
          % (abs(b1.xMinimum() - b0.xMinimum()), abs(b1.yMinimum() - b0.yMinimum())))
    # e o controle NEGATIVO: sem refazer o mar, o vazio tem que aparecer
    ruim = quadro.difference(t_un.combine(mar_g))
    print('  CONTROLE (mar NAO refeito) ....... %.1f m2 de vazio, %.2f px de largura'
          % (ruim.area(), (ruim.area() / max(1e-9, ruim.length() / 2)) / (ext.width() / 3000.0)))
    return tw, mw, bw

if __name__ == '__main__':
    from qgis.core import QgsApplication
    _qgs = QgsApplication([], False); _qgs.initQgis()
    _q = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get('MAPA', '.'), 'qgis')
    _autoteste(_q, os.path.dirname(os.path.abspath(__file__)))
    _qgs.exitQgis()


# ============================================================== OS MOLHES
def estreito(geom, meia_larg=45.0, transicao=55.0):
    """
    Peso que vai a ZERO nas partes ESTREITAS da terra: os molhes.

    Os dedos compridos do estaleiro sao concreto, mas no OSM eles entram na
    LINHA DE COSTA — entao sao 'terra', e ondulavam junto com ela. Molhe
    ondulado nao le como desenho a mao, le como obra torta, e come justamente o
    contraste que sustenta a ideia toda: costa organica contra obra reta.

    Como achar um molhe que nao tem etiqueta: pela LARGURA. 'nucleo' e a terra
    encolhida de meia_larg, entao tudo mais estreito que 2*meia_larg desaparece
    dele. Um vertice na costa larga fica a uns meia_larg do nucleo; um vertice no
    meio de um molhe fica muito mais longe, porque o molhe inteiro sumiu. O peso
    cai de 1 a 0 ao longo de 'transicao' metros, entao a ondulacao se APAGA
    entrando no molhe, em vez de dar um degrau na juncao.

    A distancia e medida ate o vertice mais proximo do nucleo densificado, e nao
    com QgsGeometry.distance ponto a ponto: densificado a meia_larg/2 o erro e
    menor que o passo da densificacao, e a conta vetorizada e ordens de grandeza
    mais rapida que milhares de chamadas ao GEOS.
    """
    nucleo = geom.buffer(-meia_larg, 8)
    if nucleo is None or nucleo.isEmpty():
        return lambda xs, ys: np.zeros(len(xs), np.float64)
    amostra = nucleo.densifyByDistance(meia_larg * 0.5)
    pts = np.array([[v.x(), v.y()] for v in amostra.vertices()], np.float64)
    if not len(pts):
        return lambda xs, ys: np.zeros(len(xs), np.float64)

    def peso(xs, ys):
        d = np.empty(len(xs), np.float64)
        for i in range(0, len(xs), 256):         # em blocos: 256 x len(pts) por vez
            a = xs[i:i + 256, None] - pts[None, :, 0]
            b = ys[i:i + 256, None] - pts[None, :, 1]
            d[i:i + 256] = np.sqrt(a * a + b * b).min(axis=1)
        t = np.clip(1.0 - (d - meia_larg) / transicao, 0.0, 1.0)
        return t * t * (3 - 2 * t)
    return peso

def junta(*pesos):
    """Multiplica pesos: basta um ir a zero para o vertice ficar parado."""
    def peso(xs, ys):
        r = np.ones(len(xs), np.float64)
        for p in pesos:
            if p is not None: r = r * p(xs, ys)
        return r
    return peso
