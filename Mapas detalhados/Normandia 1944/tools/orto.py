# -*- coding: utf-8 -*-
"""
orto.py — a placa de ORTOFOTO, no lugar do desenho.

    py -3 tools/orto.py                      todos os quadros que ja tem ficha
    py -3 tools/orto.py entroncamento 4096   um quadro, com a largura em pixels

POR QUE ISTO EXISTE
O mapa desenhado no QGIS chega a 0,063 m/px e ali fica sem O QUE DIZER, nao sem
pixel. O OSM sabe onde esta cada predio e cada rua, e mais nada: nao sabe do muro
do quintal, da horta, do rastro de trator no campo, da sombra que a arvore joga
na estrada. Fechar mais o zoom so faz mancha chapada maior.

A referencia do Operations Room, no enquadramento fechado, nao e desenho: e foto
aerea. A diferenca nao e de escala, e de FONTE. Entao a fonte muda.

DE ONDE VEM
BD ORTHO do IGN frances, servida pela Geoplateforme em WMTS. Licenca aberta
(Etalab) desde 2021, com atribuicao — veja ATRIBUICAO la embaixo. Resolucao
nativa de 20 cm/px, que e o z19 do xadrez de tiles. O z20 NAO existe: devolve
404, medido. Entao 0,195 m/px na latitude de Carentan e o teto do dado, e um
quadro mais fechado que uns 375 m num video de 1920 px esta ampliando pixel.

O QUE NAO MUDA
A ficha .json ao lado da imagem e a MESMA que o carentan.py grava: mesmos
limites, mesma extensao em 3857, mesmos metros por pixel. Por isso a cena, o
grafo de ruas, a mascara de predio e o estudio inteiro continuam funcionando sem
uma linha de diferenca — a placa e so a imagem que fica embaixo.

O RECORTE TEM QUE SER EXATO. O xadrez de tiles nao cai nos limites do quadro; os
tiles cobrem um retangulo maior. Recortar no pixel certo e o que mantem a ficha
valida, e um erro de meio tile aqui poe todo soldado da cena dez metros fora do
lugar sem que nada denuncie.
"""
import io, json, math, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from PIL import Image

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QGIS = os.path.join(AQUI, 'qgis')
SAIDA = os.path.join(AQUI, 'orto')
CACHE = os.path.join(SAIDA, '.tiles')

WMTS = ('https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0'
        '&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&TILEMATRIXSET=PM'
        '&FORMAT=image/jpeg&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}')
AGENTE = 'carentan-map/1.0 (mapa historico; contato via repositorio)'
ATRIBUICAO = 'Ortofoto: BD ORTHO (r) IGN - Geoplateforme, licence ouverte Etalab 2.0'

LADO = 256
MUNDO = 20037508.342789244          # meia largura do Web Mercator, em metros
Z_MAX = 19                          # MEDIDO: o z20 devolve 404 no BD ORTHO
FIOS = 8                            # pedidos ao mesmo tempo


def tiles_do_z(z):
    """Quantos metros de 3857 cabe num tile, neste zoom."""
    return (MUNDO * 2) / (2 ** z)


def escolhe_zoom(ext, larg_px, lat):
    """
    O zoom cujo pixel nativo e pelo menos tao fino quanto o pixel de saida.

    A conta e feita em metros de CHAO, e nao em unidades de 3857: o Mercator
    estica por 1/cos(lat), e comparar a resolucao esticada com a largura em
    metros que a ficha promete daria um zoom a menos nesta latitude.
    """
    chao_por_px = (ext[2] - ext[0]) * math.cos(math.radians(lat)) / larg_px
    for z in range(1, Z_MAX + 1):
        nativo = tiles_do_z(z) / LADO * math.cos(math.radians(lat))
        if nativo <= chao_por_px:
            return z
    return Z_MAX


def baixa(z, x, y, tentativas=4):
    caminho = os.path.join(CACHE, str(z), str(x), '%d.jpg' % y)
    if os.path.exists(caminho) and os.path.getsize(caminho) > 0:
        return caminho
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    url = WMTS.format(z=z, x=x, y=y)
    for n in range(tentativas):
        try:
            req = Request(url, headers={'User-Agent': AGENTE})
            with urlopen(req, timeout=60) as r:
                dados = r.read()
            if not dados:
                raise URLError('vazio')
            with open(caminho, 'wb') as fh:
                fh.write(dados)
            return caminho
        except (URLError, HTTPError, OSError) as e:
            if n == tentativas - 1:
                print('   falhou %d/%d/%d: %s' % (z, x, y, e))
                return None
            time.sleep(0.8 * (n + 1))
    return None


def monta(ficha, larg_px=None, zoom=None):
    nome = ficha['nome']
    ext = ficha['extensao3857']
    larg_px = larg_px or ficha['px'][0]
    alt_px = int(round(larg_px * (ext[3] - ext[1]) / (ext[2] - ext[0])))
    lat = (ficha['limites']['sul'] + ficha['limites']['norte']) / 2
    z = zoom or escolhe_zoom(ext, larg_px, lat)

    passo = tiles_do_z(z)
    x0 = int(math.floor((ext[0] + MUNDO) / passo))
    x1 = int(math.floor((ext[2] + MUNDO) / passo))
    y0 = int(math.floor((MUNDO - ext[3]) / passo))
    y1 = int(math.floor((MUNDO - ext[1]) / passo))
    nx, ny = x1 - x0 + 1, y1 - y0 + 1
    nativo = passo / LADO * math.cos(math.radians(lat))
    print('%s: z%d, %d x %d tiles (%d), nativo %.3f m/px -> saida %d x %d px (%.3f m/px)'
          % (nome, z, nx, ny, nx * ny, nativo, larg_px, alt_px,
             (ext[2] - ext[0]) * math.cos(math.radians(lat)) / larg_px))

    pedidos = [(z, x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
    with ThreadPoolExecutor(max_workers=FIOS) as pool:
        caminhos = list(pool.map(lambda t: baixa(*t), pedidos))
    faltou = sum(1 for c in caminhos if not c)
    if faltou:
        print('   %d tiles nao vieram; ficam cinza' % faltou)

    folha = Image.new('RGB', (nx * LADO, ny * LADO), (128, 132, 126))
    for (zz, x, y), caminho in zip(pedidos, caminhos):
        if not caminho:
            continue
        try:
            with Image.open(caminho) as t:
                folha.paste(t.convert('RGB'), ((x - x0) * LADO, (y - y0) * LADO))
        except Exception as e:
            print('   tile ruim %d/%d/%d: %s' % (zz, x, y, e))

    # O RECORTE EXATO. A folha comeca no canto do tile x0/y0, que nao e o canto
    # do quadro; a conta abaixo passa de 3857 para pixel da folha e corta ali.
    fx0 = (ext[0] + MUNDO) / passo - x0
    fy0 = (MUNDO - ext[3]) / passo - y0
    fx1 = (ext[2] + MUNDO) / passo - x0
    fy1 = (MUNDO - ext[1]) / passo - y0
    caixa = (fx0 * LADO, fy0 * LADO, fx1 * LADO, fy1 * LADO)
    recorte = folha.resize((larg_px, alt_px), Image.LANCZOS, box=caixa)

    os.makedirs(SAIDA, exist_ok=True)
    jpg = os.path.join(SAIDA, nome + '.jpg')
    # 92 com croma inteiro, como as placas desenhadas: a foto aerea tem detalhe
    # fino em toda parte, e 4:2:0 borraria o telhado contra a grama
    recorte.save(jpg, 'JPEG', quality=92, subsampling=0, optimize=True)

    nova = dict(ficha)
    nova['px'] = [larg_px, alt_px]
    nova['metrosPorPixel'] = ficha['larguraKm'] * 1000.0 / larg_px
    nova['jpg'] = nome + '.jpg'
    nova.pop('png', None)
    nova['fonte'] = ATRIBUICAO
    nova['zoomTile'] = z
    with open(os.path.join(SAIDA, nome + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(nova, fh, ensure_ascii=False, indent=2)
    print('   -> orto/%s.jpg  %.1f MB' % (nome, os.path.getsize(jpg) / 1048576.0))
    return nova


def main():
    if not os.path.isdir(QGIS):
        raise SystemExit('nao achei a pasta qgis/ — rode o carentan.py antes')
    fichas = {}
    for f in sorted(os.listdir(QGIS)):
        if not f.endswith('.json') or f == 'osm.json':
            continue
        with open(os.path.join(QGIS, f), encoding='utf-8') as fh:
            j = json.load(fh)
        if 'extensao3857' in j and 'limites' in j:
            fichas[j['nome']] = j
    if not fichas:
        raise SystemExit('nenhuma ficha de placa em qgis/')

    alvo = sys.argv[1] if len(sys.argv) > 1 else None
    larg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if alvo:
        if alvo not in fichas:
            raise SystemExit('quadro %r nao tem ficha. Ha: %s' % (alvo, ', '.join(fichas)))
        monta(fichas[alvo], larg)
    else:
        for j in fichas.values():
            monta(j, larg)
    print('\n' + ATRIBUICAO)


if __name__ == '__main__':
    main()
