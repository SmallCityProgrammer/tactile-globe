# textura.py — os ladrilhos procedurais do mapa.
#
# Copia do textura.py do Pacifico WW2, com duas receitas a mais: 'bocage' e
# 'pocas'. E copia, e nao import, porque cada mapa detalhado e uma pasta que se
# abre sozinha — o do Japao Feudal tambem tem o seu. O preco e que uma correcao
# aqui nao viaja para la.
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
# existe borda para ver. O 'bocage' faz a mesma coisa com outra matematica: as
# celulas vizinhas sao procuradas modulo a grade, entao o campo que sai pela
# direita entra pela esquerda inteiro.
#
# OPACO OU SOBREPOSTO
# Um ladrilho opaco carrega a cor dentro de si, e so serve para um uso. Um
# ladrilho de SOBREPOR carrega so a modulacao (escurece aqui, clareia ali) em
# canal alfa, e entao pode ir por cima de qualquer base — uma cor chapada, um
# degrade de praia, o que for. Quase tudo aqui e de sobrepor; a agua e a excecao
# historica, e as 'pocas' sao a segunda, por um motivo declarado la embaixo.
import os, math, hashlib
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


# =========================================================== O CAMPO CERCADO
#
# O bocage e a razao pela qual essa batalha durou seis dias: um labirinto de
# talhoes pequenos, cada um fechado por um aterro com arbustos e arvores em
# cima, de onde nem se via o campo seguinte. Um mapa de Carentan com o campo
# aberto chapado conta a historia errada.
#
# E TEXTURA, NAO CADASTRO. O OSM tem duas sebes no recorte inteiro — o campo
# frances nao esta mapeado talhao por talhao, e inventar quais sao os talhoes
# seria mentir com precisao. A textura diz "este chao era dividido assim", que e
# verdade, sem afirmar onde ficava cada divisa.
#
# SAO DOIS LADRILHOS, E ISSO IMPORTA. O tom do talhao e modulacao de sobrepor,
# como todo o resto do mapa; a sebe e ladrilho COM COR, como as pocas. Sebe nao
# e o campo mais escuro, e outra coisa em cima dele — verde-escuro, com sombra
# propria, porque um aterro com arvores tem tres ou quatro metros de altura.
# Feita de modulacao preto-e-branco, a sebe saia cinza-carvao e o mapa inteiro
# lia como vitral.

def _campo_celular(lado, celulas, jitter, semente, quadrado):
    """
    O mosaico de talhoes, em bruto: quem e o dono de cada pixel e quao perto ele
    esta da divisa. Os dois ladrilhos do bocage saem daqui, e por isso a conta
    fica guardada: e a parte cara, e roda uma vez so.

    A METRICA E O QUE DA A FORMA. Distancia euclidiana pura da favo de mel — seis
    lados, tudo do mesmo tamanho, e o olho acha na hora que aquilo e ruido
    celular e nao um campo. O campo normando e de quadrilateros. Chebyshev
    (max(|dx|,|dy|)) da retangulos; a mistura das duas, pesada por 'quadrado', da
    o retangulo de canto arredondado que se ve na foto aerea.

    E OS TALHOES TEM TAMANHOS DIFERENTES. Sem isso todo campo sai com a mesma
    area, o que nenhuma paisagem de verdade tem. O peso aditivo por celula —
    subtrair w_i da distancia — empurra a divisa para longe dos talhoes grandes e
    para perto dos pequenos, exatamente como o vizinho de terra boa que comprou o
    pedaco do lado.

    A busca varre as nove celulas ao redor MODULO a grade, e e isso que fecha a
    emenda: o talhao cortado pela borda direita continua na esquerda.
    """
    n = celulas
    g = _grade(n * n * 4, semente)            # por celula: dx, dy, peso, tom
    pts = []
    for j in range(n):
        for i in range(n):
            k = (j * n + i) * 4
            pts.append((i + 0.5 + (g[k] - 0.5) * 2 * jitter,
                        j + 0.5 + (g[k + 1] - 0.5) * 2 * jitter,
                        (g[k + 2] - 0.5) * 0.38))          # o peso: talhao maior ou menor
    dono = bytearray(lado * lado)
    borda = [0.0] * (lado * lado)
    i = 0
    for y in range(lado):
        cy = (y + 0.5) / lado * n
        jy = int(cy)
        for x in range(lado):
            cx = (x + 0.5) / lado * n
            ix = int(cx)
            d1 = d2 = 9.9
            qual = 0
            for dj in (-1, 0, 1):
                jj = jy + dj
                for di in (-1, 0, 1):
                    ii = ix + di
                    k = (jj % n) * n + (ii % n)
                    px, py, w = pts[k]
                    # o ponto da celula vizinha vem do OUTRO lado da grade,
                    # deslocado de n — e esse deslocamento que emenda
                    ax = abs(px + (ii - (ii % n)) - cx)
                    ay = abs(py + (jj - (jj % n)) - cy)
                    d = (math.sqrt(ax * ax + ay * ay) * (1.0 - quadrado)
                         + (ax if ax > ay else ay) * quadrado) - w
                    if d < d1: d2, d1, qual = d1, d, k
                    elif d < d2: d2 = d
            dono[i] = qual
            borda[i] = d2 - d1
            i += 1
    return dono, borda

_CACHE_CAMPO = {}
def _campo(lado, celulas, jitter, semente, quadrado):
    ch = (lado, celulas, jitter, semente, quadrado)
    if ch not in _CACHE_CAMPO:
        _CACHE_CAMPO[ch] = _campo_celular(*ch)
    return _CACHE_CAMPO[ch]


def bocage(pasta, nome, lado=640, celulas=6, jitter=0.42, semente=1944, quadrado=0.62,
           forca=0.26, variacao=0.60, grao=0.22, grao_base=112):
    """
    O TOM dos talhoes: cada campo com o seu verde, sem a sebe.

    Ladrilho de sobrepor comum. Quem desenha a sebe e o bocage_sebe(), com o
    mesmo lado, celulas, jitter, semente e quadrado — e so assim os dois casam.
    """
    params = dict(lado=lado, celulas=celulas, jitter=jitter, semente=semente, quadrado=quadrado,
                  forca=forca, variacao=variacao, grao=grao, grao_base=grao_base)

    def pinta():
        dono, _ = _campo(lado, celulas, jitter, semente, quadrado)
        gf = _grade(grao_base, semente + 601)
        img = QImage(lado, lado, QImage.Format_ARGB32)
        i = 0
        for y in range(lado):
            for x in range(lado):
                t = 0.5 + (_sal(dono[i], semente) - 0.5) * variacao
                t += (_valor(x / lado * grao_base, y / lado * grao_base, grao_base, gf) - 0.5) * grao
                img.setPixel(x, y, _sobrepor(t, forca))
                i += 1
        return img

    return _guarda(pasta, nome, params, pinta)


def bocage_cultura(pasta, nome, lado=640, celulas=6, jitter=0.42, semente=1944, quadrado=0.62,
                   cores=('#c0b071', '#a9a05e', '#9c8e63'), fracao=0.32,
                   alfa=(80, 140), semente_cor=77):
    """
    A LAVOURA: os talhoes que em junho nao estavam verdes.

    O ladrilho de tom so escurece e clareia, porque e modulacao em preto e
    branco — e com ele sozinho o campo inteiro sai da mesma cor, variando so de
    claro. Nenhuma paisagem e assim, e a Normandia de 12 de junho de 1944 menos
    ainda: parte era pasto verde, parte era feno de corte, parte era cereal em
    pe ja amarelando e parte estava arada. Sem isso o mapa e um lencol de oliva
    de canto a canto, que e justamente a leitura que o bocage deveria desmentir.

    E o terceiro ladrilho com COR do arquivo, pelo mesmo motivo dos outros dois:
    matiz nao se consegue empurrando o que esta embaixo para mais claro.

    A sorte e por TALHAO, tirada do dono do pixel, entao o campo inteiro muda de
    cor de uma vez e a divisa cai exatamente na sebe.

    fracao  quanto do campo nao e pasto verde
    alfa    faixa de opacidade; sorteada por talhao, para nem toda lavoura pesar
            igual e o tom de baixo continuar aparecendo
    """
    params = dict(lado=lado, celulas=celulas, jitter=jitter, semente=semente, quadrado=quadrado,
                  cores=cores, fracao=fracao, alfa=alfa, semente_cor=semente_cor)

    def pinta():
        dono, _ = _campo(lado, celulas, jitter, semente, quadrado)
        # uma decisao por talhao, resolvida antes: dentro do laco de pixel isto
        # custaria 410 mil hashes para responder 36 perguntas
        paleta = [QColor(c) for c in cores]
        mesa = {}
        for k in set(dono):
            if _sal(k, semente_cor) >= fracao:
                mesa[k] = None
                continue
            c = paleta[int(_sal(k, semente_cor + 3) * len(paleta)) % len(paleta)]
            a = int(alfa[0] + _sal(k, semente_cor + 9) * (alfa[1] - alfa[0]))
            mesa[k] = qRgba(c.red(), c.green(), c.blue(), a)
        vazio = qRgba(0, 0, 0, 0)
        img = QImage(lado, lado, QImage.Format_ARGB32)
        i = 0
        for y in range(lado):
            for x in range(lado):
                v = mesa[dono[i]]
                img.setPixel(x, y, vazio if v is None else v)
                i += 1
        return img

    return _guarda(pasta, nome, params, pinta)


def bocage_sebe(pasta, nome, lado=640, celulas=6, jitter=0.42, semente=1944, quadrado=0.62,
                largura=0.030, cor='#4a6129', alfa=205, sombra='#2f3d22', sombra_alfa=120,
                desloca=3, macio=0.35):
    """
    A SEBE: o aterro com arvores que fecha cada talhao.

    Ladrilho transparente que so pinta a crista entre dois talhoes — onde
    F2 - F1 e pequeno. Leva a sombra junto, deslocada para baixo e para a
    direita, no mesmo rumo das outras sombras do mapa (135 graus). Sem a sombra a
    sebe fica achatada no chao; com ela o campo ganha relevo e se le que aquilo
    tem altura — que e justamente o que importava para quem estava embaixo.

    A sombra sai da PROPRIA mascara, deslocada modulo o ladrilho. Deslocar modulo
    e o que mantem a emenda: a sombra que sai por baixo entra por cima.

    largura  largura da sebe em fracao de talhao. 0.030 de um talhao de 140 m da
             uns 4 m, que e a sebe com o aterro
    desloca  o deslocamento da sombra, em pixels do ladrilho. Como o ladrilho e
             ancorado no CHAO (veja TALHAO_M no estilo.py), um pixel dele vale
             sempre os mesmos ~1,3 m, entao este numero nao depende do recorte
    macio    fracao da largura que e degrade, para a sebe nao ter recorte de
             tesoura
    """
    params = dict(lado=lado, celulas=celulas, jitter=jitter, semente=semente, quadrado=quadrado,
                  largura=largura, cor=cor, alfa=alfa, sombra=sombra, sombra_alfa=sombra_alfa,
                  desloca=desloca, macio=macio)

    def pinta():
        _, borda = _campo(lado, celulas, jitter, semente, quadrado)
        dentro = largura * (1.0 - macio)
        mask = [0.0] * (lado * lado)
        for i in range(lado * lado):
            b = borda[i]
            if b >= largura: continue
            mask[i] = 1.0 if b <= dentro else (largura - b) / (largura - dentro)
        c, cs = QColor(cor), QColor(sombra)
        img = QImage(lado, lado, QImage.Format_ARGB32)
        i = 0
        for y in range(lado):
            ys = ((y - desloca) % lado) * lado
            for x in range(lado):
                a = mask[i]
                s = mask[ys + ((x - desloca) % lado)]
                if a <= 0.0 and s <= 0.0:
                    img.setPixel(x, y, 0)
                elif a >= s:
                    img.setPixel(x, y, qRgba(c.red(), c.green(), c.blue(), int(a * alfa)))
                else:
                    # so a franja da sombra que a sebe nao cobre aparece
                    e = s * (1.0 - a)
                    img.setPixel(x, y, qRgba(cs.red(), cs.green(), cs.blue(), int(e * sombra_alfa)))
                i += 1
        return img

    return _guarda(pasta, nome, params, pinta)


def pocas(pasta, nome, lado=512, base=6, oitavas=4, semente=1944, limiar=0.40,
          suave=0.12, alfa=165, cor='#4a8b91'):
    """
    A agua parada do brejo: um ladrilho TRANSPARENTE onde so as partes mais
    baixas do ruido recebem cor.

    E a segunda excecao a regra do ladrilho de sobrepor, e por um motivo: uma
    poca nao e o chao mais escuro, e outra COISA em cima do chao — mais azul,
    nao so mais baixa. Modulacao em preto e branco nao muda matiz, entao aqui o
    ladrilho carrega cor mesmo, com alfa.

    Os alemaes abriram as comportas da Douve em maio de 44 e deixaram o vale
    todo assim. E por isso que os paraquedistas nao tinham por onde ir a nao ser
    pela calcada.

    limiar  fracao do terreno que alaga (quanto maior, mais agua)
    suave   largura da margem, em unidades do ruido; sem ela a poca tem recorte
            de tesoura
    """
    params = dict(lado=lado, base=base, oitavas=oitavas, semente=semente,
                  limiar=limiar, suave=suave, alfa=alfa, cor=cor)

    def pinta():
        f = Fbm(lado, base, oitavas, semente)
        cru = [f(x, y) for y in range(lado) for x in range(lado)]
        o = sorted(cru)
        lo, hi = o[len(o) // 100], o[-len(o) // 100 - 1]
        faixa = (hi - lo) or 1.0
        c = QColor(cor)
        img = QImage(lado, lado, QImage.Format_ARGB32)
        i = 0
        for y in range(lado):
            for x in range(lado):
                t = (cru[i] - lo) / faixa
                i += 1
                a = (limiar - t) / suave
                a = 0.0 if a <= 0 else (1.0 if a >= 1 else a)
                img.setPixel(x, y, qRgba(c.red(), c.green(), c.blue(), int(a * alfa)))
        return img

    return _guarda(pasta, nome, params, pinta)
