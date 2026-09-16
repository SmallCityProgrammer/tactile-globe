# pos.py — o acabamento, o que se faria no Photoshop.
#
#   "C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat" pos.py saida/ford-3000
#
# POR QUE EM CODIGO E NAO NO PHOTOSHOP
# Pintar a mao e melhor para o que e UNICO — escombro, fumaca, cratera, letreiro.
# Mas tudo que se pinta a mao se PERDE no proximo render do QGIS. Estas aqui sao
# as operacoes que valem para a imagem inteira e que ninguem quer refazer a cada
# ajuste de cor: oclusao, suavizacao, brilho, gradacao, vinheta, grao. Em codigo
# elas voltam em cinco segundos.
#
# Ele le a PASTA de camadas do exporta.py, e nao so o achatado, porque com as
# camadas da para fazer o que uma imagem plana nao deixa: a oclusao sai do alfa
# dos predios e das arvores, entao a penumbra cai onde ha coisa EM PE, e nao
# onde a cor por acaso e escura.
import os, sys, time
from qgis.core import QgsApplication
qgs = QgsApplication([], False); qgs.initQgis()
import numpy as np
from qgis.PyQt.QtGui import QImage, QPainter, QColor, QFont

# ============================================================== AS RECEITAS
# Duas intensidades. A primeira tentativa saiu no 'forte' e, olhando, passou do
# ponto: halo escuro em volta de cada moita e verde escurecido demais. A
# referencia do Operations Room e mais clara e mais lavada do que a intuicao de
# "tratar a imagem" sugere — tratar de menos erra menos que tratar de mais.
RECEITAS = {
    'leve': dict(
        suaviza=0.30, suaviza_r=2,
        oclusao=0.16, oclusao_r=16,          # encosta a penumbra, nao desenha halo
        brilho=0.22, brilho_lim=0.74, brilho_r=26,
        sombra_cor=(0.010, 0.045, 0.065),    # a sombra puxa para o azul-esverdeado
        luz_cor=(0.055, 0.045, 0.012),       # a luz puxa para o creme quente
        contraste=0.07, vinheta=0.20, grao=0.014),
    'forte': dict(
        suaviza=0.28, suaviza_r=2,
        oclusao=0.34, oclusao_r=14,
        brilho=0.30, brilho_lim=0.70, brilho_r=26,
        sombra_cor=(0.020, 0.070, 0.100),
        luz_cor=(0.090, 0.070, 0.020),
        contraste=0.16, vinheta=0.30, grao=0.016),
}

# ============================================================== FERRAMENTA
def _le(caminho):
    """PNG -> float32 (h, w, 4) em 0..1, na ordem RGBA."""
    img = QImage(caminho)
    if img.isNull(): raise IOError('nao abriu ' + caminho)
    img = img.convertToFormat(QImage.Format_ARGB32)
    p = img.constBits(); p.setsize(img.sizeInBytes())
    bpl = img.bytesPerLine()
    a = np.frombuffer(p, np.uint8, count=bpl * img.height())
    a = a.reshape(img.height(), bpl // 4, 4)[:, :img.width()]
    # ARGB32 em little-endian esta na memoria como B, G, R, A
    return np.stack([a[..., 2], a[..., 1], a[..., 0], a[..., 3]], -1).astype(np.float32) / 255.0

def _grava(rgb, caminho):
    h, w = rgb.shape[:2]
    q = np.clip(rgb, 0, 1) * 255.0 + 0.5
    b = np.empty((h, w, 4), np.uint8)
    b[..., 2] = q[..., 0]; b[..., 1] = q[..., 1]; b[..., 0] = q[..., 2]; b[..., 3] = 255
    b = np.ascontiguousarray(b)
    QImage(b.data, w, h, 4 * w, QImage.Format_ARGB32).copy().save(caminho)

def _box1(a, r, eixo):
    """Media movel por soma acumulada: custa o mesmo em qualquer raio."""
    n = a.shape[eixo]; k = 2 * r + 1
    pad = [(0, 0)] * a.ndim; pad[eixo] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=eixo, dtype=np.float32)
    i1 = [slice(None)] * a.ndim; i1[eixo] = slice(k, k + n)
    i0 = [slice(None)] * a.ndim; i0[eixo] = slice(0, n)
    return (c[tuple(i1)] - c[tuple(i0)]) / k

def borra(a, r, passes=3):
    """Tres medias moveis aproximam uma gaussiana."""
    if r < 1: return a
    for _ in range(passes):
        a = _box1(_box1(a, r, 0), r, 1)
    return a

def lum(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114

# ============================================================== O ACABAMENTO
def acaba(pasta, n):
    t0 = time.time()
    base = _le(os.path.join(pasta, '00-completo.png'))
    rgb = base[..., :3].copy()
    h, w = rgb.shape[:2]

    # --- 1. oclusao -----------------------------------------------------------
    # O alfa do que esta EM PE. Borrado e multiplicado por baixo, poe penumbra em
    # volta de cada coisa — que e o que a sombra dura sozinha nao da, porque ela
    # so cai de um lado. O termo que subtrai o proprio alfa impede que o objeto
    # escureca a si mesmo.
    emPe = np.zeros((h, w), np.float32)
    for nome in ('02-predio', '07-verde', '04-pier'):
        p = os.path.join(pasta, nome + '.png')
        if os.path.exists(p): emPe = np.maximum(emPe, _le(p)[..., 3])
    if emPe.max() > 0:
        oc = np.clip(borra(emPe, n['oclusao_r']) - emPe * 0.55, 0, 1)
        rgb *= (1.0 - n['oclusao'] * oc)[..., None]

    # --- 2. suavizar ----------------------------------------------------------
    # Aresta de vetor e dura demais. Um pouco do desfoque de volta tira o
    # recortado sem comer a estrutura.
    rgb = rgb * (1 - n['suaviza']) + borra(rgb, n['suaviza_r']) * n['suaviza']

    # --- 3. brilho ------------------------------------------------------------
    alto = np.clip((lum(rgb) - n['brilho_lim']) / (1 - n['brilho_lim']), 0, 1)
    rgb += borra(alto, n['brilho_r'])[..., None] * n['brilho'] * rgb.mean(axis=2, keepdims=True)

    # --- 4. gradacao ----------------------------------------------------------
    # Tonalizacao dividida: sombra para um lado, luz para o outro. E o unico
    # passo que, sozinho, ja faz a imagem parecer tratada.
    l = np.clip(lum(rgb), 0, 1)[..., None]
    rgb = rgb + np.float32(n['sombra_cor']) * (1 - l) ** 2 + np.float32(n['luz_cor']) * l ** 2
    # o S da curva: mexe nas pontas e quase nao toca o meio-tom
    rgb = rgb + n['contraste'] * (rgb - 0.5) * (1 - np.abs(rgb - 0.5) * 2) ** 1.5

    # --- 5. vinheta -----------------------------------------------------------
    yy = (np.arange(h, dtype=np.float32) / h - 0.5)[:, None]
    xx = (np.arange(w, dtype=np.float32) / w - 0.5)[None, :]
    d = np.sqrt(xx * xx + yy * yy) / 0.707
    rgb *= (1.0 - n['vinheta'] * np.clip(d - 0.42, 0, 1) ** 2 / 0.34)[..., None]

    # --- 6. grao --------------------------------------------------------------
    # Mais no meio-tom, quase nada no branco e no preto: e onde o filme granula.
    rnd = np.random.default_rng(1941)
    g = (1 - (2 * lum(rgb) - 1) ** 2)[..., None]
    rgb += (rnd.random((h, w), np.float32) - 0.5)[..., None] * n['grao'] * g

    print('  %5.1f s' % (time.time() - t0))
    return base[..., :3], np.clip(rgb, 0, 1)

if __name__ == '__main__':
    pasta = sys.argv[1] if len(sys.argv) > 1 else 'saida/ford-3000'
    if not os.path.isabs(pasta):
        pasta = os.path.join(os.path.dirname(os.path.abspath(__file__)), pasta)
    antes = None; feitas = []
    for nome in ('leve', 'forte'):
        print(nome)
        antes, depois = acaba(pasta, RECEITAS[nome])
        _grava(depois, os.path.join(pasta, 'pos-' + nome + '.png'))
        feitas.append((nome.upper(), depois))

    # o painel: o original e as duas, no mesmo recorte 1:1
    h, w = antes.shape[:2]
    cw, ch = min(900, w), min(900, h)
    x, y = (w - cw) // 2, (h - ch) // 2
    tiras = [('QGIS, sem nada', antes)] + feitas
    folha = QImage(cw * 3 + 24, ch + 40, QImage.Format_ARGB32); folha.fill(QColor('#23303a'))
    p = QPainter(folha); p.setFont(QFont('Segoe UI', 16, QFont.Bold)); p.setPen(QColor('#e9e4d2'))
    tmp = os.path.join(pasta, '_t.png')
    for i, (rot, arr) in enumerate(tiras):
        _grava(arr[y:y + ch, x:x + cw], tmp)
        p.drawImage(6 + i * (cw + 6), 34, QImage(tmp))
        p.drawText(8 + i * (cw + 6), 24, rot)
    p.end(); os.remove(tmp)
    folha.save(os.path.join(pasta, 'pos-lado.png'))
    print('->', os.path.join(pasta, 'pos-lado.png'))
