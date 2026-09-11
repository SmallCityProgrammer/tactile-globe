# Japão Sengoku — mapa ilustrado

Um mapa do Japão feudal (c. 1580) no estilo dos mapas pictóricos japoneses
(鳥瞰図, *chōkanzu*), que aguenta zoom contínuo do país inteiro até o nível de
uma vila: cabanas de sapê, arrozais, árvores, caminhos, soldados em formação.
Tudo vetorial, desenhado a cada frame, sem perder nitidez em nenhuma escala.

Um único arquivo, `japao.html` (3,5 MB com os sprites embutidos, 1,4 MB sem
eles), sem dependências. Abre por duplo clique.

---

## Uso

| ação | resultado |
|---|---|
| scroll | zoom, ancorado no ponto sob o cursor |
| arrastar | move o mapa |
| duplo clique | aproxima 4× no ponto |
| `ir para…` | voa até castelos, cidades, portos, batalhas ou "uma vila qualquer" |
| botão `clãs` (ou `C`) | liga e desliga os domínios coloridos |
| botão `rótulos` (ou `L`) | liga e desliga os nomes |
| botão `grade` (ou `G`) | paralelos e meridianos |
| botão `montanhas` (ou `M`) | liga e desliga as montanhas em vista lateral das bandas país e região |
| botão `florestas` (ou `F`) | liga e desliga as manchas de floresta e as árvores selvagens (as árvores das vilas e as alamedas das estradas ficam) |
| `Home` | volta ao Japão inteiro |
| botão `imagem` (ou `I`) | alterna entre os glifos em imagem (sprites recortados de uma folha desenhada, `data/sprites.json`) e os glifos em código; sem sprites embutidos o botão some |
| botão `glifos` (ou abrir `glifos.html` / `japao.html#glifos`) | catálogo de todos os glifos do mapa, desenhados grandes e legendados, numa página rolável; `baixar PNG` salva a folha inteira; `Esc` volta ao mapa |
| `+` / `-` | zoom no centro |

O zoom vai de ~2,4 km/pixel (país) a 5 cm/pixel (diorama): 50.000×.

---

## Bandas de zoom

O mapa muda de "gênero" conforme se aproxima. Cada banda desenha coisas
diferentes, e as transições são graduais (alpha por escala).

| m/pixel | banda | o que aparece |
|---|---|---|
| > 800 | país | costa, domínios dos clãs, brasões (*mon*) nas capitais, cadeias de montanhas em vista lateral, estradas principais, navios, Ezo hachurado |
| 100 – 800 | região | + fronteiras internas dos domínios, florestas como manchas, rios, castelos e templos como glifos, batalhas, estações |
| 20 – 100 | distrito | montanhas somem; florestas em manchas, zonas de arrozal, vilas como aglomerados de telhados, vilas-posto (*shukuba*) nas estações |
| 6 – 20 | cidade | tiles procedurais de 2 km: árvores individuais (ralas), caminhos, quarteirões das cidades-castelo, fossos e muralhas |
| 1 – 6 | vila | cabanas individuais (*minka*, *kura*, santuário com *torii*), arrozais célula a célula com diques, bosques de bambu, barcos nas vilas de pesca |
| < 1 | diorama | pessoas nos caminhos, soldados com lanças e *sashimono*, bandeiras *nobori*, textura de sapê nos telhados, copas com lóbulos, fileiras de arroz |

---

## Como funciona

**Renderização.** Canvas 2D, um único `draw()` por frame quando algo muda. A
câmera vive em doubles no JS (`cam.x`, `cam.y` em metros; `cam.s` em
pixels/metro) e cada ponto vira coordenada de tela antes de chegar ao canvas,
então não há *jitter* de float32 mesmo a 50.000× de zoom. Polígonos grandes
(costa, prefeituras) são recortados ao retângulo da vista (Sutherland–Hodgman)
e subdivididos antes de receber o tremor de tinta, para que a costa da Natural
Earth (pontos a ~4 km) não vire linha reta na escala de vila.

**Projeção.** Equirretangular local, origem em 137°E 36°N, unidades em metros.

**Dados reais** (`tools/build.mjs` lê o `data/` do repositório do globo, dois níveis acima, só leitura; ou o caminho em `MAPA_DATA=`):

| camada | fonte | observação |
|---|---|---|
| costa | Natural Earth 1:10m `admin_0` (Japão) | 70 anéis, 6.174 pontos |
| domínios | Natural Earth `admin_1` (46 prefeituras) | cada prefeitura recebe um clã de ~1580 (15 clãs, com Ukita em Okayama); é uma aproximação grosseira das 68 províncias |
| lagos | polígonos aproximados no template (`LAKES`) | Biwa, Suwa, Hamana, Kasumigaura, Inawashiro; desenhados de memória |
| elevação | GEBCO 8-bit 21600×10800, janela 128–147°E / 30–46°N | 1140×960 células de ~1,85 km |
| rios | derivados da elevação: preenchimento de depressões, fluxo D8, acumulação, traçado | 674 polilinhas; nas planícies ficam retos |
| castelos, templos, batalhas, portos | tabela `PLACES` no template | coordenadas aproximadas, de memória |
| estradas | tabela `ROADS`: Tōkaidō, Nakasendō, San'yōdō, Hokurikudō, Ōshūdō, Kōshū, e rotas de Kyūshū/Shikoku | pontos de passagem nas estações históricas, suavizados com Catmull-Rom e tremidos com ruído |
| brasões | 14 *mon* desenhados em código, simplificados | |

**Detalhe inventado, mas determinístico.** Abaixo de 100 m/pixel nada é
armazenado: tudo é gerado por *hash* da posição.

- **Distrito (8 km)** → 16 células de 2 km com terra/mar, altitude, distância
  ao mar e ao rio, densidade de floresta, aptidão para arrozal; vilas são
  sorteadas nas células baixas (mais perto de rios e estradas), com tamanho,
  direção (alinhada à estrada mais próxima) e nome gerado
  (*Kami-no-mura* 上野村…). As estações das estradas viram vilas-posto.
- **Vila** → caminho principal ondulado, ramais, cabanas dos dois lados com
  *kura* atrás, santuário com bosque no fim do caminho, bosque de bambu,
  arrozais numa malha irregular (colunas e linhas de largura variável,
  linhas curvas, células alagadas agrupadas), pessoas nos caminhos. Vilas
  costeiras viram vilas de pesca com barcos empurrados até a linha d'água.
- **Micro tile (2 km)** → candidatos a árvore numa malha de 12,8 m, mantidos
  pela densidade local (floresta em manchas de ruído; planícies vazias;
  cinturão de pinheiros a menos de 600 m do mar); clareiras em volta das
  vilas; alamedas de pinheiros ao longo das estradas principais. Perto do
  mar, a máscara de terra é rasterizada do polígono da costa a ~17 m.
- **Cidade-castelo** → fosso e muralha (duplos nos castelos grandes), torre
  de menagem e torretas em planta, quarteirões de *machiya* com frentes
  estreitas nas duas margens de cada rua, quadras de samurai entre o castelo
  e a cidade, templos na borda oposta, uma coluna de soldados na rua
  principal. Kyoto é uma grade de 120 m.
- **Batalhas** → duas formações de três fileiras com bandeiras nas cores dos
  clãs, frente a frente.

O número de árvores por tela é limitado por uma prioridade por árvore, então
ao aproximar as árvores "aparecem" sem que as existentes mudem de lugar.

---

## Build

```
node tools/build.mjs   # ../../data -> data/japan.json + data/fields.png
node tools/pack.mjs    # src/template.html + data -> japao.html
```

`fields.png` guarda três campos no RGB: elevação, distância ao mar (km) e
distância ao rio (km). O navegador decodifica o PNG sozinho.

**Sprites (teste de 2026-09-11).** A folha `glifos.png` do catálogo foi
redesenhada por IA em estilo tradicional (`Downloads/glifos 2.jpeg`) e
fatiada por `tools/sheet.mjs`: converte-se o JPEG em PNG (System.Drawing no
PowerShell), detectam-se as linhas da grade por contagem de pixels escuros,
recorta-se o miolo de cada célula (sem a legenda), o papel sai por distância
de cor com desmistura das bordas, e cada sprite vira um PNG RGBA de até
192 px em `data/sprites.json` (61 sprites, 1,7 MB em base64; o Ukita ficou
fora porque a IA desenhou um disco). O mapa das células está em
`tools/sheet-map.json`. No template, cada função de glifo tenta primeiro o
sprite (`sp('nome')`) e cai no desenho em código se não houver; o botão
`imagem` alterna os dois. Árvores em sprite só aparecem com raio ≥ 5 px,
personagens só acima de 8 px/m, e as ondas em sprite são mais esparsas.
As árvores e as pessoas da folha são vistas de lado ou de cima conforme a
IA decidiu, então o diorama mistura perspectivas; é um teste.

A vegetação veio de uma segunda folha (`Downloads/Vegetação.jpeg`, sete
copas vistas de cima: folhosa, folhosa diorama, conífera, conífera diorama,
bambu, bambu diorama, pinheiro costeiro), fatiada com
`tools/sheet-map-vegetacao.json` por cima do mesmo `data/sprites.json`
(o `cut` mescla: a mesma chave sobrescreve). As copas são ancoradas pelo
centro, giradas por hash, e dispensam a sombra em código porque já trazem a
sua pintada. A grade dessa folha tem bordas claras demais para o detector,
por isso o mapa usa retângulos explícitos.

```
node tools/sheet.mjs grid  <folha.png>              # mostra a grade detectada
node tools/sheet.mjs cut   <folha.png> tools/sheet-map.json 192            # glifos gerais
node tools/sheet.mjs cut   <folha.png> tools/sheet-map-vegetacao.json 192  # vegetação, mesclando
node tools/pack.mjs                                 # embute
```

---

## Por que Canvas, e não SVG

SVG no DOM foi a primeira ideia e daria os filtros de tinta de graça, mas
esbarra em dois limites nesse projeto: coordenadas em float32 no rasterizador
(a 50.000× de zoom um translate de 1e7 px tremeria em pixels inteiros) e o
custo de manter dezenas de milhares de nós vivos enquanto se faz pan e zoom.
O Canvas resolve os dois: coordenadas calculadas em double e redesenho só do
que está na tela. Todo o desenho continua vetorial, então exportar a vista
atual como SVG é uma extensão natural.

---

## O que melhorar (em ordem de impacto)

1. **Lagos.** Em 2026-09-11 entraram Biwa, Suwa, Hamana, Kasumigaura e
   Inawashiro como polígonos aproximados desenhados de memória (Biwa com 20
   vértices, os outros como elipses). Falta trocar por contornos reais
   (Natural Earth `ne_10m_lakes`).
2. **Províncias reais (令制国).** As prefeituras não separam Owari de Mikawa,
   nem Suruga de Tōtōmi; os domínios de Oda, Tokugawa e Takeda ficam errados
   nas bordas. Um GeoJSON das 68 províncias corrige o mapa político.
3. **Costa em alta resolução** (GSI 国土地理院 ou OSM). Na escala de vila a
   costa da Natural Earth é um segmento reto de 4 km com tremor por cima.
   (Vilas na água: corrigido em 2026-09-11; cabanas, santuário, bambuzal e
   arrozais agora passam pela máscara fina de 12,5 m, e uma vila que caia
   inteira na água não desenha nada nem ganha rótulo.)
4. **Rios reais** (`ne_10m_rivers_lake_centerlines` ou GSI) no lugar dos
   derivados do relevo de 1,85 km, que ficam retos e às vezes deslocados.
   (Rios e lagos já saem da geração desde 2026-09-11: a máscara fina de cada
   tile e de cada vila recorta o polígono da costa, os lagos e os rios com
   a mesma geometria deslocada que o renderizador desenha, mais uma margem;
   os caminhos das vilas também são recortados pela máscara, e os rios param
   na borda dos lagos.) Falta: **o azul da água deve aparecer saindo dos
   rios, e nunca rio dentro da água**: foz alargando num estuário que se
   funde com o mar ou o lago, rio cortado na linha da costa (hoje o traçado
   vai até o centro da célula de mar do relevo, ~1 km além), a saída do
   Biwa pelo rio Seta, e as margens em si (areia, vegetação ribeirinha,
   vaus e pontes nas estradas).
5. **Coordenadas e nomes.** Uma revisão (`docs/revisao-2026-09-10.txt`) foi
   aplicada em 2026-09-11: pontos de estrada corrigidos (Fukuchiyama, Shinjō,
   Ōtoyo/Ikeda, Takeo/Ōmura, Izumi, Itakura), nomes de 1580 no lugar dos
   de Edo (Kannabe por Fukuyama, Shōzui por Tokushima, Akamagaseki, Chiyo,
   Kozukata, Gokamura, Tonda, Sekino, Nohara, Utazu, Matsugashima,
   Suginome, Fuchū e Kitanoshō na Hokurikudō), castelos com o nome da
   época (Uchi, Muranaka, Oyama; Funai e Sunpu como cidades), Ukita como
   clã em Okayama, Ehime sem clã, Gunma com os Takeda, Utsunomiya e Yuzuki
   sem clã, Hirado sem navio nanban, Hieizan em ruína, navios de volta ao
   mar. Ficaram em aberto, por serem discutíveis: Toyama (Uesugi ou Oda em
   1580), Fukushima (Date é uma antecipação de 1589; o poder era Ashina),
   Tochigi (Hōjō só no sul), Une em vez de Akō, e Sekigahara (1600) mantida
   como marco.
6. **Cidades feitas à mão** para os lugares que importam: Azuchi no monte à
   beira do lago, Kyoto com o Gosho e Kamigyō/Shimogyō, Sakai com fosso e
   grade, Odawara com a muralha externa, Ishiyama Honganji como
   templo-fortaleza.
7. **Castelos de montanha (山城)** com terraços nos cumes, posicionados pelo
   relevo; e o relevo influenciando arrozais (terraços em encosta, células
   seguindo curvas de nível).
8. **Desempenho.** Feito em 2026-09-11: tiles gerados aos poucos (4 por
   frame) com cache LRU, amostragem de floresta local, arrays tipados,
   árvores pequenas e sombras em um path por cor, arrozais em um fill por
   cor, lotes das cidades em `Path2D` por cor de telhado (Kyoto: de 877 ms
   para 94 ms na primeira aparição, 3–5 ms depois). A maioria das bandas
   ficou em 1–7 ms a 1280×720. Falta: cache de tiles rasterizados para
   telas 4K e o preenchimento progressivo dos tiles ficar invisível
   (hoje os tiles "aparecem" ao longo de meio segundo ao entrar na banda
   de 24 m/px).
9. **Montanhas mais bonitas** no nível regional: cadeias contínuas, hachuras,
   sombra projetada, no estilo Yoshida Hatsusaburō.
10. **Mais gente e movimento:** viajantes na estrada, camponeses nos
    arrozais, colunas marchando entre castelos, barcos animados.
11. **Linha do tempo** (1560 / 1570 / 1582 / 1590 / 1600) com domínios por
    ano.
12. **Brasões reais** (kamon do Wikimedia Commons) e uma fonte japonesa
    embutida (subset) para os rótulos em vez da fonte do sistema.
13. **Vegetação por região** (laurissilva no sul, faia no norte, pinheiro na
    costa, cedro nas serras); hoje só a altitude muda a árvore.
14. **Mais topônimos**: províncias, montanhas, rios, baías.
15. **Exportar SVG** da vista atual.
