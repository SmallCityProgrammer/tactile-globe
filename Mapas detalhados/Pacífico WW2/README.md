# Pacífico 1941–1945 — carta ilustrada da guerra naval

Uma carta náutica do teatro do Pacífico inteiro — de Ceilão a Pearl Harbor, das
Aleutas à Austrália — que aguenta zoom contínuo do teatro até o convés de um
navio: relevo do fundo do mar, isóbatas, rotas das frotas, ordem de batalha
navio a navio, aeronaves, colunas de água, marinheiros no convés. Tudo
vetorial, desenhado a cada frame.

Um único arquivo, `pacifico.html` (3,6 MB sem assets embutidos), sem
dependências. Abre por duplo clique.

**A diferença para o mapa do Japão: aqui *todo* asset aceita um PNG seu.**
Não existe nada desenhado fora da tabela `ASSETS` — nem a água, nem a textura
do convés, nem a linha de data. São 194 slots, e a página `assets` mostra
todos, com o desenho atual, prontos para receber uma imagem arrastada.

---

## Uso

| ação | resultado |
|---|---|
| scroll | zoom, ancorado no ponto sob o cursor |
| arrastar | move a carta |
| duplo clique | aproxima 4× no ponto |
| clique | identifica o que está embaixo (navio, batalha, base) |
| `ir para…` | voa até as quatro ações, as batalhas ou as bases |
| barra de data (ou `←` `→`, `Shift` para pular mês) | move a guerra no tempo: a frente japonesa muda, as batalhas aparecem, as frotas navegam |
| `▶` | roda a guerra inteira, dois dias por frame |
| `frentes` (`F`) | o perímetro japonês na data atual |
| `rotas` (`R`) | as rotas das operações navais |
| `batalhas` (`B`) | os marcos das ações e os naufrágios |
| `bases` (`N`) | portos, ancoradouros, arsenais, estreitos |
| `rótulos` (`L`) | os nomes |
| `grade` (`G`) | paralelos e meridianos |
| `sondas` (`S`) | isóbatas e números de profundidade |
| `assets` (`A`) | a folha de assets |
| `imagem` (`I`) | alterna entre os PNGs e os desenhos em código |
| `Home` | volta ao teatro inteiro |

---

## Bandas de zoom

| m/pixel | banda | o que aparece |
|---|---|---|
| > 2500 | teatro | costa, profundidade em lavagem, perímetro japonês, rotas, marcos de batalha, bases grandes, nomes dos mares, rosa dos ventos |
| 400 – 2500 | mar | isóbatas, sondas, grupos de ilhas, todas as bases, formações como símbolo, setores de busca aérea |
| 55 – 400 | batalha | naufrágios, recifes, relevo das ilhas em vista lateral, forças a caminho como formação |
| 6 – 55 | formação | navios um a um, com esteira, em estação; esquadrilhas aéreas; colunas de água e flak nas ações do dia |
| 0,7 – 6 | navio | o casco em planta: torres com canos, ilha, chaminés, catapulta, escaleres, antiaéreo |
| < 0,7 | convés | chapeamento, convés de voo com marcação e elevadores, aviões estacionados, marinheiros |

O zoom vai de ~16 km/pixel (teatro) a alguns centímetros por pixel: mais de
100.000×.

---

## A tabela de assets

Essa é a diferença de projeto em relação ao mapa do Japão, onde só uns vinte
glifos tinham gancho para sprite e o resto era código intocável.

Aqui existe uma tabela `ASSETS` com 194 entradas, e **toda** marca que a carta
faz passa por `glyph()`, `tile()` ou `stamp()`, que resolvem o slot nesta ordem:

1. o PNG que você soltou (guardado no IndexedDB do navegador, sobrevive a
   recarregar a página, mesmo em `file://`);
2. o PNG embutido no arquivo em `data/assets.json` na hora do `pack`;
3. o desenho em código, que é o fallback e nunca some.

As entradas dizem o tipo:

| tipo | significado | exemplos |
|---|---|---|
| `glyph` | um carimbo num ponto, opcionalmente girado | navios, aviões, explosões, bases, bandeiras |
| `tile` | uma textura que se repete | água aberta, água rasa, selva, recife, chapeamento do convés, papel |
| `line` | um carimbo repetido ao longo de uma linha | esteira, rebentação, praia, isóbata, torpedo, perímetro, corrente |

Os grupos: **o mar** (8), **a terra** (10), **navios** (22), **convés** (10),
**aeronaves** (11), **combate** (7), **marcadores** (16), **carta** (5) e
**classes** (105 — uma por classe de navio do banco de dados).

### Trocar um asset

- Abra `assets.html`, ou `pacifico.html#assets`, ou aperte `A`.
- **Arraste um PNG** para cima de um quadro. Ou solte vários de uma vez em
  qualquer lugar da página: cada arquivo vai para o slot de mesmo nome
  (`dd.png` → contratorpedeiro, `navio_yamato.png` → o Yamato em particular).
- **Clique no quadro** para baixar o desenho atual em PNG, no tamanho e na
  proporção certos, e pintar por cima.
- `↺` no canto do quadro devolve o desenho em código.
- `exportar assets.json` gera o arquivo que `tools/pack.mjs` embute; a partir
  daí o `pacifico.html` já sai com as suas imagens dentro.

### Âncoras e rotação

Cada slot declara onde fica o ponto de ancoragem (`center`, ou `bottom` para
montanhas e vulcões, que crescem a partir do chão) e se o mapa gira a imagem.
Nas imagens que giram, **a proa/frente aponta para a esquerda**: um navio é
desenhado com a proa em −x, um avião idem. Um PNG com a proa para cima vai
aparecer navegando de lado.

### O catálogo completo

**[docs/assets.md](docs/assets.md)** lista os 194 slots um por um — arquivo,
espécie, tamanho real em metros, se gira, e a proporção do gabarito. É gerado
da própria tabela do template:

```
node tools/asset-doc.mjs
```

### Desenhar os navios

**[design/README.md](design/README.md)** é o guia de como montar uma vista em
planta: sistema de coordenadas, tabela de cavernas, catálogo de peças
(torres, chaminés, catapultas, radar, hidroaviões) e um exemplo de navio novo
do zero. O gerador `design/ships.mjs` já sai com o Yamato e a Iowa prontos, em
SVG, prontos para virar `navio_yamato.png` e `navio_iowa.png`.

```
node design/ships.mjs
```

---

## Como funciona

**Renderização.** Canvas 2D, um `draw()` por frame quando algo muda. A câmera
vive em doubles (`cam.x`, `cam.y` em metros de Mercator; `cam.s` em
pixels/metro), e cada ponto vira coordenada de tela antes de chegar ao canvas,
então não há tremor de float32 nem no zoom mais fundo. Polígonos grandes são
recortados à vista (Sutherland–Hodgman) e ganham tremor de tinta na escala de
ilha.

**Projeção.** Mercator, origem em 145°E sobre o equador. É a projeção da carta
náutica: rumo constante vira linha reta, que é como cada uma dessas rotas foi
efetivamente navegada. O preço é que um "metro" só é um metro no equador — na
latitude φ ele é 1/cos φ grande demais — então tudo que precisa ser distância
real (o comprimento de um casco, a barra de escala, as milhas de uma estação
na formação) é dividido por cos φ no ponto onde é desenhado. Longitudes
correm 0–360 leste, então a janela é um intervalo só e a linha de data não
parte nada ao meio.

**A cor da água.** Longe, a profundidade vem de um raster construído uma vez no
carregamento, já em coordenadas de Mercator, e sai num único `drawImage`. Perto,
ela é amostrada num raster pequeno (uma amostra a cada 18 px) que o canvas
interpola de volta ao tamanho da tela: preencher um retângulo por célula
desenhava a própria grade de amostragem — degraus visíveis em toda borda de
plataforma — e custava quatro vezes mais. A rampa de cor tem 256 degraus
espaçados pela raiz da profundidade, então os cem primeiros metros ganham um
degrau a cada dois metros e a planície abissal, onde nada muda, fica com a
ponta grossa.

**Escala dos cascos.** Um porta-aviões tem 261 m por 30 m. Na banda de formação
isso dá um risco de dois pixels. Então o comprimento é comprimido por uma raiz
abaixo de 26 px (um porta-aviões continua visivelmente maior que um
contratorpedeiro, e os dois ficam legíveis) e a boca tem piso de 7 px. As duas
correções se anulam sozinhas: acima de 26 px de casco a escala é verdadeira.

**Dados reais** (`tools/build.mjs` lê o `data/` do repositório do globo, dois
níveis acima, só leitura; ou o caminho em `MAPA_DATA=`):

| camada | fonte | observação |
|---|---|---|
| costa | Natural Earth 1:10m `admin_0` | 1.435 anéis, 125 mil pontos, quantizados a 10 m e delta-codificados |
| profundidade | GEBCO 8-bit 21600×10800 (raster de batimetria da NASA) | janela 78–212°E / 50°S–62°N a 1/12°, ~9,3 km/célula; calibrada contra as fossas das Marianas, das Filipinas e do Japão → 43,6 m por unidade |
| distância à terra | transformada de distância sobre a máscara de costa | usada para a rebentação, o recife e a densidade de ondulação |
| altitude das ilhas | mesma família de rasters | para o relevo em vista lateral e a linha de palmeiras |

**Dados históricos** (`tools/history.mjs` normaliza `data/history-raw.json`):

| tabela | quantidade | conteúdo |
|---|---|---|
| batalhas | 60 | de Pearl Harbor à baía de Tóquio, com data, posição, forças, vencedor e perdas por tipo |
| bases | 126 | portos, ancoradouros, campos de aviação, arsenais, estreitos, com quem os detinha e desde quando |
| mares | 32 | os nomes das águas, para os rótulos em itálico |
| rotas | 37 | as rotas efetivamente navegadas: a ida e a volta do Kidō Butai, a incursão no Índico, Doolittle, Midway dos dois lados, o Expresso de Tóquio, as quatro forças de Leyte, Ten-Gō |
| classes de navio | 105 | comprimento, boca, calado, deslocamento, velocidade, tripulação, disposição das torres em planta, convés de voo |
| frentes | 5 | o perímetro japonês em dez/1941, ago/1942, nov/1943, out/1944 e ago/1945 |
| cronologia | 44 | eventos datados para a barra de tempo |
| ordens de batalha | 4 | Midway, Surigao, Samar e Ten-Gō — 162 navios com nome, classe, posição e rumo |

As posições vieram de conhecimento histórico e trazem um campo `conf`
(`exact` / `approx` / `guess`). São boas o bastante para a carta e não servem
de fonte primária.

**Detalhe gerado, mas determinístico.** Abaixo do nível dos dados tudo sai de
hash da posição: a ondulação (rumo pelos alísios nos trópicos, pelos ventos de
oeste acima de 35°), os carneiros, o recife dentro da isóbata de 20 m, as
palmeiras na faixa costeira, a mata no interior, as pistas e os povoados nas
bases, a formação que cada força em movimento mantém (anteparo de
contratorpedeiros a 3 milhas dos pesados), e o combate nas quatro ações:
colunas de água enquadrando os navios, flak sobre a formação, clarão de salva
nas torres, esteiras de torpedo saindo dos contratorpedeiros e holofotes nas
ações noturnas.

---

## Build

```
node tools/build.mjs     # ../../data  -> data/pacific.json + data/fields.png
node tools/history.mjs   # data/history-raw.json -> data/history.json
node tools/pack.mjs      # src/template.html + data -> pacifico.html

node tools/asset-doc.mjs # src/template.html -> docs/assets.md (catálogo dos slots)
node design/ships.mjs    # -> design/*.svg (vistas em planta do Yamato e da Iowa)
```

`fields.png` guarda três campos no RGB: profundidade em passos de 50 m,
distância à terra em passos de 10 km, altitude em passos de 40 m. O navegador
decodifica o PNG sozinho. O `build.mjs` guarda em `data/.*.f32` a janela já
amostrada dos dois rasters de 21600×10800, porque inflar os dois leva um
minuto e eles nunca mudam.

---

## O que melhorar (em ordem de impacto)

1. **Os assets desenhados de verdade.** Os 194 fallbacks em código são
   esquemáticos de propósito: eles existem para que a carta nunca fique com
   buraco e para servirem de gabarito. Uma folha desenhada à mão (ou por IA,
   como a do Japão) trocaria a carta inteira — começando pelos 17 tipos de
   navio, pelos 9 aviões e pela água.
2. **Costa em alta resolução.** A Natural Earth 1:10m tem vértice a cada
   ~150 m; na banda de vila isso é uma reta com tremor por cima. Para as ilhas
   que importam (Guadalcanal, Iwo Jima, Okinawa, Leyte, Truk, Ulithi) vale um
   GeoJSON dedicado.
3. **Batimetria fina nas áreas de batalha.** 9,3 km/célula é bom no oceano
   aberto e grosso demais no Ironbottom Sound, no estreito de Surigao e nas
   lagoas dos atóis, que são justamente onde a profundidade conta.
4. **As posições horárias.** Hoje cada ordem de batalha é um instante só. As
   quatro ações têm `phases` na tabela (3 a 6 horários com o que aconteceu),
   mas o mapa ainda não move os navios entre elas: falta interpolar as
   posições por hora e deixar a barra de tempo descer ao nível do relógio
   dentro do dia da batalha.
5. **Mais ordens de batalha.** Só quatro ações têm navio a navio. Savo, Mar de
   Coral, Guadalcanal (as duas noites), Mar das Filipinas e Bismarck mereciam
   o mesmo tratamento.
6. **Ilhas feitas à mão** para os lugares que importam: Pearl Harbor com a
   Battleship Row e o dique seco, Truk com o anel de recife e os passes,
   Ulithi com a frota inteira fundeada, Rabaul com Simpson Harbour, Henderson
   Field, Iwo Jima com o Suribachi.
7. **Aeronaves com trajetória.** Hoje as esquadrilhas estão paradas na posição
   da tabela. Faltam as rotas de ataque (ida, ataque, volta), o alcance de
   cada tipo como círculo, e a diferença entre quem voltou e quem não voltou.
8. **Submarinos.** As áreas de patrulha e os pontos de afundamento de comboio
   são a metade menos visível e mais decisiva da guerra; hoje só existem duas
   rotas de trânsito.
9. **Perdas acumuladas.** A tabela `losses` (porta-aviões, encouraçados e
   cruzadores de pé em cinco datas) está nos dados e ainda não aparece na
   tela; daria um gráfico pequeno no canto que se move com a barra de tempo.
10. **Clima e luz.** Chuva de monção, as rajadas que esconderam Taffy 3 ao
    largo de Samar, e um modo noturno de verdade para Savo, Tassafaronga e
    Surigao — que foram quase todas batalhas noturnas.
11. **Desempenho em 4K.** A ~1040×980 as bandas medem 1,2 a 8,8 ms por frame
    (mediana, um `draw()` por `requestAnimationFrame`): teatro 5,2 · mar 4,1 ·
    isóbatas 5,7 · Salomões 3,9 · Surigao 8,8 · formação 1,7 · navio 1,2 ·
    convés 0,7. Falta cache de tiles rasterizados e o raster base em duas
    resoluções para telas 4K.
12. **Exportar SVG** da vista atual.
13. **Uma fonte embutida** (subset) para os nomes em japonês, em vez de
    depender da fonte do sistema.
