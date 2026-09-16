# textura.py — os ladrilhos procedurais do mapa.
#
# Nada aqui sabe o que e um mapa: sao geradores de PNG emendavel. Quem escolhe
# cor e escala e o estilo.py.
#
# POR QUE RUIDO, E NAO PADRAO
# A textura do Operations Room nao tem direcao nem periodo: e variacao irregular
# de tom, como lona, aguada ou grama de verdade. Padrao de linhas ou de pontos
# denuncia a grade na hora — o olho acha o passo em menos de um segundo. Entao o
# tom vem de ruido.
#
# POR QUE EMENDAVEL
# O ladrilho se repete pela tela inteira. Se a borda direita nao continuar na
# borda esquerda, cada repeticao desenha uma costura visivel, e o resultado vira
# uma grade — exatamente o que estavamos fugindo. Por isso todo ruido daqui e
# ruido de valor sobre uma grade PERIODICA: a oitava de periodo n toma os
# indices modulo n, entao o ultimo pixel interpola de volta para o primeiro. Nao
# existe borda para ver.
#
# OPACO OU SOBREPOSTO
# Um ladrilho opaco carrega a cor dentro de si, e so serve para um uso. Um
# ladrilho de SOBREPOR carrega so a modulacao (escurece aqui, clareia ali) em
# canal alfa, e entao pode ir por cima de qualquer base — uma cor chapada, um
# degrade de praia, o que for. Quase tudo aqui e de sobrepor; a agua e a excecao
# historica, que ja estava pronta.
import os, math, hashlib
import numpy as np
from qgis.PyQt.QtGui import QColor, QImage, qRgba

# =========================================================== O RUIDO
def _grade(n, semente):
    """Uma grade n x n de valores em [0,1), sempre a mesma para a mesma semente."""
    v, s = [], (semente * 2654435761 + 1013904223) & 0x7fffffff
    for _ in range(n * n):
        s = (s * 1103515245 + 12345) & 0x7fffffff
        v.append(s / 2147483647.0)
    return v

def _suave(t):
    return t * t * (3.0 - 2.0 * t)              # hermite: derivada zero nas pontas

def _valor(x, y, n, g):
    xi, yi = int(x) % n, int(y) % n
    xf, yf = x - math.floor(x), y - math.floor(y)
    x1, y1 = (xi + 1) % n, (yi + 1) % n         # o modulo e o que fecha a emenda
    u, v = _suave(xf), _suave(yf)
    a, b = g[yi * n + xi], g[yi * n + x1]
    c, d = g[y1 * n + xi], g[y1 * n + x1]
    return (a + (b - a) * u) * (1 - v) + (c + (d - c) * u) * v

class Fbm:
    """Ruido fracionario emendavel, pre-computado para um ladrilho de lado fixo."""
    def __init__(self, lado, base, oitavas, semente):
        self.lado, self.base, self.oitavas = lado, base, oitavas
        self.grades = [_grade(base << k, semente + k * 977) for k in range(oitavas)]

    def __call__(self, x, y):
        val, amp, soma = 0.0, 1.0, 0.0
        for k in range(self.oitavas):
            n = self.base << k
            val += amp * _valor(x / self.lado * n, y / self.lado * n, n, self.grades[k])
            soma += amp
            amp *= 0.5
        return val / soma                        # em [0,1), media perto de 0.5

def _sal(*partes):
    """Um valor estavel em [0,1) para uma tupla de inteiros. Serve de dado viciado."""
    h = hashlib.md5(repr(partes).encode()).digest()
    return int.from_bytes(h[:4], 'big') / 4294967296.0

# =========================================================== O CACHE
# O nome do arquivo carrega um resumo dos PARAMETROS, nao so a receita. Entao
# mudar o contraste gera outro arquivo em vez de reaproveitar o velho — o erro
# classico de ajustar um numero, nao ver diferenca nenhuma e culpar o numero.
# O codigo deste arquivo tambem entra na chave. Sem isso, mudar o ALGORITMO e
# manter os parametros devolve o PNG velho — e foi o que aconteceu: a
# normalizacao do ruido foi escrita, os numeros foram ajustados, e a medicao
# continuou dando exatamente o mesmo alfa medio de 2,8. O cache estava servindo
# o ladrilho de antes, em silencio. O preco e regerar os ladrilhos sempre que
# este arquivo muda, uns 30 s no total.
with open(__file__, 'rb') as _f:
    _VERSAO = hashlib.md5(_f.read()).hexdigest()[:8]

def _guarda(pasta, nome, params, pinta):
    params = dict(params, _claro=CLARO, _versao=_VERSAO)
    chave = hashlib.md5(repr(sorted(params.items())).encode()).hexdigest()[:10]
    destino = os.path.join(pasta, 'texturas')
    os.makedirs(destino, exist_ok=True)
    caminho = os.path.join(destino, '%s-%s.png' % (nome, chave))
    if not os.path.exists(caminho):
        img = pinta()
        if not img.save(caminho):
            raise IOError('nao consegui gravar ' + caminho)
    return caminho

def _lerp_cor(c1, c2, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    a, b = QColor(c1), QColor(c2)
    return QColor(int(a.red()   + (b.red()   - a.red())   * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue()  + (b.blue()  - a.blue())  * t))

CLARO = 0.55    # o quanto o lado claro da sobreposicao vale, contra o escuro

def _sobrepor(t, forca, claro=None):
    """
    Converte um valor de ruido em [0,1) num pixel de modulacao ARGB.

    Abaixo de 0.5 escurece (preto com alfa), acima clareia (branco com alfa).
    Assim o mesmo ladrilho serve para qualquer cor de base: ele nao pinta, ele
    empurra o que ja estava la para cima ou para baixo.

    O lado claro pesa MENOS que o escuro, e nao e capricho. Branco com alfa a
    sobre a cor C entrega C + a(255-C); preto entrega C - aC. Sobre um teal
    escuro isso significa que clarear anda tres vezes mais do que escurecer, e
    um ladrilho simetrico lava a cor do mapa inteiro. Foi exatamente o que
    aconteceu quando a granulacao de papel entrou: tudo virou pastel de uma vez.
    """
    if claro is None: claro = CLARO
    d = (t - 0.5) * 2.0                          # [-1, 1]
    if d > 0:
        return qRgba(255, 255, 255, int(min(255, d * forca * claro * 255)))
    return qRgba(0, 0, 0, int(min(255, -d * forca * 255)))

# =========================================================== RECEITAS
def mancha(pasta, nome, lado=512, base=8, oitavas=5, semente=1941,
           forca=0.22, cor=None, cor2=None, contraste=0.45, grao=0.0, grao_base=96,
           espuma=0.0, espuma_base=192):
    """
    Variacao irregular de tom, sem direcao. A textura de fundo de quase tudo:
    grama, agua, terra batida.

    Sem cor/cor2 sai um ladrilho de SOBREPOR (ARGB), que serve sobre qualquer
    base. Com cor e cor2 sai opaco, interpolando entre as duas.

    grao    soma um ruido bem fino por cima, para o ladrilho nao ficar chapado
            quando ampliado; grao_base e a frequencia desse ruido.
    espuma  fracao de pixels de crista, tirados de uma oitava bem fina. E o que
            faz os floquinhos brancos no mar aberto da referencia.
    """
    params = dict(lado=lado, base=base, oitavas=oitavas, semente=semente, forca=forca,
                  cor=cor, cor2=cor2, contraste=contraste, grao=grao, grao_base=grao_base,
                  espuma=espuma, espuma_base=espuma_base)

    def pinta():
        f = Fbm(lado, base, oitavas, semente)

        # PRIMEIRA PASSADA: so para saber a faixa que este ruido de fato ocupa.
        # Sem isso 'contraste' e 'forca' nao significam nada. O fBm nao usa o
        # intervalo [0,1): somando oitavas de media 0.5 ele se aperta em torno
        # de 0.5 com desvio de uns 0.1. Multiplicar isso por contraste e depois
        # por forca dava alfa medio 3 de 255 — a textura simplesmente nao
        # aparecia, e mexer nos numeros nao mudava nada de visivel.
        cru = [f(x, y) for y in range(lado) for x in range(lado)]
        ord_ = sorted(cru)
        lo, hi = ord_[len(ord_) // 100], ord_[-len(ord_) // 100 - 1]
        faixa = (hi - lo) or 1.0

        gf = _grade(grao_base, semente + 7717) if grao > 0 else None
        ef = _grade(espuma_base, semente + 4242) if espuma > 0 else None
        opaco = cor is not None and cor2 is not None
        img = QImage(lado, lado, QImage.Format_RGB32 if opaco else QImage.Format_ARGB32)
        i = 0
        for y in range(lado):
            for x in range(lado):
                n = (cru[i] - lo) / faixa                 # agora sim, [0,1]
                i += 1
                t = (n - 0.5) * contraste + 0.5
                if gf is not None:
                    t += (_valor(x / lado * grao_base, y / lado * grao_base, grao_base, gf) - 0.5) * grao
                crista = (ef is not None and
                          _valor(x / lado * espuma_base, y / lado * espuma_base, espuma_base, ef) > 1.0 - espuma)
                if opaco:
                    img.setPixel(x, y, QColor('#ffffff').rgb() if crista else _lerp_cor(cor, cor2, t).rgb())
                else:
                    img.setPixel(x, y, qRgba(255, 255, 255, 200) if crista else _sobrepor(t, forca))
        return img

    return _guarda(pasta, nome, params, pinta)


def laje(pasta, nome, lado=512, placas=8, baias=2, semente=7, forca=0.115, junta=0.30,
         junta_px=2, variacao=0.15, baia_var=0.20, mancha_base=3, mancha_forca=0.70,
         grao=0.25, grao_base=128, desalinho=0.5):
    """
    Concreto: placas com junta, agrupadas em baias, sob manchas largas.

    A primeira versao era uma grade regular de placas pequenas, todas com tom
    independente, e lia como piso de banheiro. Na referencia o patio e uma
    superficie continua: as placas sao grandes, o tom anda em BLOCOS de varias
    placas (a concretagem foi feita por baia, num dia so), e por cima disso tudo
    passam manchas largas que atravessam a malha inteira e ignoram as juntas.

    Sao tres escalas empilhadas, e e o empilhamento que mata a leitura de grade:

      mancha_forca   manchas bem maiores que a baia, de ruido fBm
      baia_var       tom por grupo de 'baias' x 'baias' placas
      variacao       tom por placa, pequeno — so tira o chapado de dentro da baia

    placas      quantas placas cabem no lado do ladrilho; inteiro, senao a junta
                da borda nao encontra a da borda oposta
    baias       quantas placas formam o lado de uma baia; tem que dividir 'placas'
    junta       quanto a junta escurece (0..1)
    desalinho   desloca as placas de cada faixa, para nao virar xadrez perfeito;
                fracao da largura da placa
    """
    params = dict(lado=lado, placas=placas, baias=baias, semente=semente, forca=forca,
                  junta=junta, junta_px=junta_px, variacao=variacao, baia_var=baia_var,
                  mancha_base=mancha_base, mancha_forca=mancha_forca,
                  grao=grao, grao_base=grao_base, desalinho=desalinho)

    def pinta():
        p = lado / float(placas)
        gf = _grade(grao_base, semente + 313)
        # a mancha larga tem que ser normalizada como no mancha(): crua, ela
        # ocupa so uns 0,2 de faixa e ficaria fraca demais contra a variacao de
        # baia, que e uniforme e usa a faixa inteira
        _fm = Fbm(lado, mancha_base, 4, semente + 2027)
        cru = [_fm(x, y) for y in range(lado) for x in range(lado)]
        o = sorted(cru)
        lo, hi = o[len(o) // 100], o[-len(o) // 100 - 1]
        faixa = (hi - lo) or 1.0
        img = QImage(lado, lado, QImage.Format_ARGB32)
        for y in range(lado):
            fy = int(y // p)
            # o desalinho e um multiplo exato da placa dividido por placas, entao
            # a coluna que sai pela direita entra pela esquerda no lugar certo
            desl = (desalinho * p * fy) % lado
            for x in range(lado):
                xx = (x + desl) % lado
                fx = int(xx // p)
                dx, dy = xx - fx * p, y - fy * p
                na_junta = dx < junta_px or dy < junta_px
                bx, by = fx // baias, fy // baias
                t = 0.5
                t += ((cru[y * lado + x] - lo) / faixa - 0.5) * mancha_forca   # a mancha larga
                t += (_sal(bx, by, semente + 11) - 0.5) * baia_var
                t += (_sal(fx, fy, semente) - 0.5) * variacao
                t += (_valor(x / lado * grao_base, y / lado * grao_base, grao_base, gf) - 0.5) * grao
                if na_junta:
                    t -= junta
                img.setPixel(x, y, _sobrepor(t, forca))
        return img

    return _guarda(pasta, nome, params, pinta)


def rocada(pasta, nome, lado=512, colunas=3, linhas=7, semente=19, forca=0.10,
           variacao=0.55, grao=0.35, grao_base=110):
    """
    O xadrez de quem cortou a grama em faixas: blocos retangulares de tom
    ligeiramente diferente. E a cara do campo de pouso de Ford Island.

    Blocos mais largos que altos (colunas < linhas) dao a leitura de "passou o
    trator nesta direcao".
    """
    params = dict(lado=lado, colunas=colunas, linhas=linhas, semente=semente,
                  forca=forca, variacao=variacao, grao=grao, grao_base=grao_base)

    def pinta():
        lx, ly = lado / float(colunas), lado / float(linhas)
        gf = _grade(grao_base, semente + 991)
        img = QImage(lado, lado, QImage.Format_ARGB32)
        for y in range(lado):
            by = int(y // ly)
            for x in range(lado):
                bx = int(x // lx)
                t = 0.5 + (_sal(bx, by, semente) - 0.5) * variacao
                t += (_valor(x / lado * grao_base, y / lado * grao_base, grao_base, gf) - 0.5) * grao
                img.setPixel(x, y, _sobrepor(t, forca))
        return img

    return _guarda(pasta, nome, params, pinta)


def grao(pasta, nome, lado=256, base=64, oitavas=2, semente=3, forca=0.09):
    """
    A granulacao do papel, para passar por cima do mapa inteiro no fim e amarrar
    as camadas. Fininha de proposito: se der para ver, esta forte demais.
    """
    return mancha(pasta, nome, lado=lado, base=base, oitavas=oitavas,
                  semente=semente, forca=forca, contraste=1.0)

# ================================================= A CHAPA DO PATIO
# O patio nao pode ser um ladrilho pequeno repetido. A medicao do problema:
# a repeticao e copia literal (diferenca media de 0,2 a 1,5 niveis de cinza no
# deslocamento de um periodo, contra 7,4 entre posicoes sem relacao), e o que
# denuncia nao e a razao ladrilho/tela — e quantas vezes a MAIOR feicao de
# dentro do ladrilho (a nodoa escura) aparece dentro de uma peca continua de
# patio. A maior peca da base tem 9,22 km2, ou 1713 x 795 px no render de 3000.
# A 46 mm cabem ~10 copias da nodoa ali e a grade salta aos olhos; a 90 mm sao
# 5, e fica PIOR, porque a nodoa cresceu junto e ficou mais reconhecivel.
#
# Ou seja: aumentar o MESMO ladrilho nao resolve. O que resolve e um ladrilho
# com MAIS feicoes dentro — e, no limite, um maior que a tela, que entao nao se
# repete nenhuma vez. A 914,4 mm e 96 dpi, 1 px do ladrilho vale 1 px de tela.
#
# Isso nao se escreve com setPixel: 3456 x 3456 sao 11,9 milhoes de pixels, uns
# 78 s no laco de Python contra 2,3 s em numpy, que ja vem no QGIS.
def _valor_np(w, h, nx, ny, semente):
    """O _valor() do arquivo, vetorizado: mesma grade periodica, mesmo hermite."""
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
    lo, hi = np.percentile(val, 1), np.percentile(val, 99)   # a mesma normalizacao do mancha()
    return np.clip((val/soma - lo/soma) / (((hi-lo)/soma) or 1.0), 0, 1)

def _cortes(total, alvo, jitter, rng):
    c = [0.0]
    while c[-1] < total:
        c.append(c[-1] + max(4.0, alvo * (1.0 + rng.uniform(-jitter, jitter))))
    return np.array(c, np.float32)

def apron(pasta, nome, lado=3456, placa=90, jitter=0.35, semente=1941, forca=0.15,
          junta=0.55, junta_px=2.0, variacao=0.32, nodoa=0.55, nodoa_cel=620,
          grao=0.30, grao_cel=9.0):
    """
    O patio inteiro numa chapa so: placas irregulares, nodoa larga que atravessa
    varias placas, grao fino. Grande de proposito — em 914 mm de tela ela e maior
    que o render de 3000 px, entao NAO SE REPETE NENHUMA VEZ.

    Nao da para escrever isto com setPixel: 3456 x 3456 sao 11,9 milhoes de
    pixels, ~78 s no laco de Python contra 2,3 s em numpy (medido). Dai o numpy,
    que ja vem no QGIS.

    placa       lado medio da placa em px do ladrilho (= px de tela)
    jitter      o quanto o corte varia de placa para placa
    nodoa_cel   tamanho da nodoa, em px: 620 px atravessa ~7 placas
    """
    params = dict(lado=lado, placa=placa, jitter=jitter, semente=semente, forca=forca,
                  junta=junta, junta_px=junta_px, variacao=variacao, nodoa=nodoa,
                  nodoa_cel=nodoa_cel, grao=grao, grao_cel=grao_cel)

    def pinta():
        rng = np.random.default_rng(semente)
        w = h = lado
        ys = _cortes(h, placa, jitter, rng)
        yy = np.arange(h, dtype=np.float32); xx = np.arange(w, dtype=np.float32)
        faixa = np.clip(np.searchsorted(ys, yy, side='right') - 1, 0, len(ys) - 2)
        t = np.full((h, w), 0.5, np.float32); na_junta = np.zeros((h, w), bool)
        for i in range(len(ys) - 1):
            lin = np.where(faixa == i)[0]
            if not len(lin): continue
            xs = _cortes(w, placa * (1.0 + rng.uniform(-0.25, 0.25)), jitter, rng)
            xs -= rng.uniform(0, placa)                      # desalinho por faixa
            col = np.clip(np.searchsorted(xs, xx, side='right') - 1, 0, len(xs) - 2)
            tom = 0.5 + (rng.random(len(xs) - 1) - 0.5) * variacao
            t[lin, :] = tom[col][None, :]
            na_junta[lin, :] = ((np.abs(xx - xs[col]) < junta_px)[None, :] |
                                (np.abs(yy[lin] - ys[i]) < junta_px)[:, None])
        if nodoa > 0:
            t += (_fbm_np(w, h, nodoa_cel, 4, semente + 31) - 0.5) * nodoa
        if grao > 0:
            t += (_valor_np(w, h, max(2, int(w/grao_cel)), max(2, int(h/grao_cel)),
                            semente + 7717) - 0.5) * grao
        t = np.clip(np.where(na_junta, t - junta, t), 0, 1)

        # o mesmo criterio do _sobrepor(): escurece abaixo de 0.5, clareia acima,
        # e o lado claro pesa CLARO
        d = (t - 0.5) * 2.0
        alfa = np.where(d > 0, np.clip(d * forca * CLARO * 255.0, 0, 255),
                               np.clip(-d * forca * 255.0, 0, 255)).astype(np.uint8)
        tom = np.where(d > 0, 255, 0).astype(np.uint8)
        buf = np.empty((h, w, 4), np.uint8)          # ARGB32 little-endian: B,G,R,A
        buf[..., 0] = tom; buf[..., 1] = tom; buf[..., 2] = tom; buf[..., 3] = alfa
        buf = np.ascontiguousarray(buf)
        return QImage(buf.data, w, h, 4*w, QImage.Format_ARGB32).copy()

    return _guarda(pasta, nome, params, pinta)

# A escala em que 1 px do ladrilho vale 1 px de tela, a 96 dpi. Se o LARG do
# pearl.py subir acima de LADO_PATIO, a chapa volta a se repetir — os dois
# numeros andam juntos.
LADO_PATIO = 3456
ESC_PATIO  = LADO_PATIO * 25.4 / 96.0        # 914,4 mm


# ================================================= A COPA, EM PNG COM ALFA
# Um disco chapado de cor unica le como bolinha, nao como arvore — foi a queixa.
# O que falta nele nao e resolucao, e as tres coisas que uma copa de verdade tem
# vista de cima: SILHUETA irregular (lobos, nao circulo), VOLUME (a luz bate de
# um lado e a copa escurece para a borda) e BORDA MACIA.
#
# Nada disso precisa de detalhe fino: na tela a arvore tem uns 7 px no quadro
# inteiro, entao o PNG e reduzido de 128 para 7. O que sobrevive a essa reducao e
# exatamente silhueta, volume e borda — e e por isso que funciona.
def _borra_np(a, r):
    """Media movel em cruz, duas passadas. Suficiente para borrar uma sombra."""
    if r < 1: return a
    for _ in range(2):
        for eixo in (0, 1):
            n = a.shape[eixo]; k = 2 * r + 1
            pad = [(0, 0)] * a.ndim; pad[eixo] = (r + 1, r)
            c = np.cumsum(np.pad(a, pad, mode='edge'), axis=eixo, dtype=np.float32)
            i1 = [slice(None)] * a.ndim; i1[eixo] = slice(k, k + n)
            i0 = [slice(None)] * a.ndim; i0[eixo] = slice(0, n)
            a = (c[tuple(i1)] - c[tuple(i0)]) / k
    return a

def copa(pasta, nome, lado=128, lobos=6, cor='#46602c', semente=7,
         luz=0.34, escurece=0.42, sombra=0.40, sombra_off=0.09, sombra_borrao=6,
         borda=2.2):
    """
    Uma copa de arvore em PNG com fundo transparente.

    lobos    quantos circulos se somam para formar a silhueta; 1 daria o disco
    luz      quanto o lado de cima-esquerda clareia
    escurece quanto a borda escurece em relacao ao miolo (e o que da volume)
    sombra   a sombra projetada, ASSADA no proprio PNG — sai mais barato que uma
             segunda camada de marcador e cai sempre do mesmo lado
    """
    params = dict(lado=lado, lobos=lobos, cor=cor, semente=semente, luz=luz,
                  escurece=escurece, sombra=sombra, sombra_off=sombra_off,
                  sombra_borrao=sombra_borrao, borda=borda)

    def pinta():
        rng = np.random.default_rng(semente)
        y, x = np.mgrid[0:lado, 0:lado].astype(np.float32)
        cx = cy = lado * 0.5
        R = lado * 0.30
        # o campo: distancia ate o lobo mais proximo, negativa dentro
        campo = np.full((lado, lado), 1e9, np.float32)
        for i in range(lobos):
            ang = 2 * np.pi * i / lobos + rng.uniform(-0.4, 0.4)
            raio = R * rng.uniform(0.18, 0.46)
            lr = R * rng.uniform(0.58, 0.86)
            lx, ly = cx + np.cos(ang) * raio, cy + np.sin(ang) * raio
            campo = np.minimum(campo, np.sqrt((x - lx) ** 2 + (y - ly) ** 2) - lr)

        alfa = np.clip((-campo + borda * 0.5) / borda, 0, 1)
        fundura = np.clip(-campo / (R * 0.55), 0, 1)          # 0 na borda, 1 no miolo
        # a luz vem de cima e da esquerda
        ul = np.clip(0.5 - ((x - cx) + (y - cy)) / (R * 2.4), 0, 1)
        k = (1.0 - escurece * (1.0 - fundura)) * (1.0 - luz * 0.5 + luz * ul)

        base = QColor(cor)
        rgb = np.empty((lado, lado, 3), np.float32)
        for c, v in enumerate((base.red(), base.green(), base.blue())):
            rgb[..., c] = np.clip(v * k, 0, 255)

        # a sombra, assada: a mesma silhueta deslocada e borrada, por baixo
        d = int(round(lado * sombra_off))
        som = _borra_np(np.roll(np.roll(alfa, d, 0), d, 1), sombra_borrao) * sombra
        som = np.clip(som - alfa, 0, 1)                       # nao escurece a copa

        a_fim = np.clip(alfa + som, 0, 1)
        # onde so ha sombra, a cor e preta; onde ha copa, e a copa
        peso = np.divide(alfa, np.maximum(a_fim, 1e-6))[..., None]
        cor_fim = rgb * peso

        buf = np.empty((lado, lado, 4), np.uint8)             # ARGB32: B, G, R, A
        buf[..., 0] = cor_fim[..., 2]; buf[..., 1] = cor_fim[..., 1]
        buf[..., 2] = cor_fim[..., 0]; buf[..., 3] = np.clip(a_fim * 255, 0, 255)
        buf = np.ascontiguousarray(buf)
        return QImage(buf.data, lado, lado, 4 * lado, QImage.Format_ARGB32).copy()

    return _guarda(pasta, nome, params, pinta)
