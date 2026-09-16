# Mapas detalhados — guia de orientação

Leia isto antes de mexer em qualquer pasta daqui. Ele existe para quem chega sem
contexto conseguir **fazer um mapa novo sem repetir os erros já pagos**.

Há duas famílias de projeto aqui, e elas não se parecem:

| família | o que é | onde |
|---|---|---|
| **zoom contínuo em HTML** | um `.html` único, Canvas 2D, sem dependência, do país inteiro até o telhado | `Japão Feudal/`, `Pacífico WW2/` (o `pacifico.html`) |
| **estático no QGIS** | mapa no estilo *The Operations Room*, renderizado em PNG e projeto `.qgz` | `Pacífico WW2/qgis/`, `Normandia 1944/qgis/`, `Ardenas 1944/qgis/` |

> A pasta `Pacífico WW2/` tem as **duas** coisas: o mapa de zoom contínuo do
> teatro do Pacífico na raiz, e o mapa estático de Pearl Harbor em `qgis/`.

| projeto | assunto | estado |
|---|---|---|
| `Pacífico WW2/qgis` | Pearl Harbor | o mais maduro; é onde quase tudo foi descoberto |
| `Ardenas 1944/qgis` | Bastogne e o Bois Jacques | **banco de provas** — feito para ser quebrado |
| `Normandia 1944/qgis` | Carentan | estúdio de cena e mp4; é onde **as ruas foram resolvidas** (seção 8), pintadas em raster por cima do QGIS |
| `Pacífico WW2/` (raiz) | carta do teatro, zoom contínuo | 194 slots de asset, todos trocáveis por PNG |
| `Japão Feudal/` | Japão Sengoku, zoom contínuo | ilustrado, estilo *chōkanzu* |

---

# 1. Fazer um mapa novo no QGIS

**Copie do `Ardenas 1944/qgis`, não do Pearl Harbor.** O de Pearl carrega uma
dedução de terra que só serve para mapa com linha de costa; o das Ardenas é o
caso geral.

```
fetch.mjs ─► osm.json ─► convert.mjs ─► *.geojson ─► <mapa>.py ─► PNG + .qgz
                                                          ▲
                                     textura.py ─► texturas/*.png ─┤
                          estilo.py, arvores.py, telhado.py ───────┘
```

1. **Copie** `textura.py`, `sinuoso.py`, `arvores.py`, `telhado.py`,
   `exporta.py`, `pos.py`. Esses não mudam de mapa para mapa.
2. **`fetch.mjs`** — troque a *bbox* e os *tags*. A consulta muda com a
   paisagem: costa e molhe num porto, talhão e sebe no campo. Precisa de
   `User-Agent`, senão o Overpass responde **406 sem dizer por quê**.
3. **`convert.mjs`** — uma camada por arquivo. Guarde a *classe* do OSM num
   campo (`c` na via, `t` no talhão): é o que deixa o estilo variar espessura e
   cor sem refazer os dados.
4. **`estilo.py`** — a paleta e os símbolos. **Todo o estilo mora aqui**, e em
   nenhum outro lugar.
5. **`<mapa>.py`** — monta, grava `.gpkg`, salva `.qgz`, renderiza.
6. **`tools/pincel.py`** e o bloco `--camadas` do fim do `carentan.py` — as ruas
   pintadas por cima, em raster. **Copie os dois**; o símbolo de linha do QGIS
   não chega lá (seção 8).

```powershell
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' ardenas.py
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' ardenas.py 50.020 5.700 50.050 5.745 foy
```

### A terra: dois casos, e só um é difícil

**Sem costa** (Bastogne, Carentan): a terra é o retângulo do quadro. Não há o que
deduzir.

**Com costa** (Pearl Harbor): o OSM **não tem o porto como polígono de água** —
só existe `natural=coastline`. A terra sai de poligonizar a costa contra a
moldura e ficar com as faces onde há **densidade** de prédio. *Contar* prédios
não serve: o porto tem três construções sobre estacas e passaria. O que separa é
a **fração** dos candidatos que cai dentro — continente 594 de 600, água 3 de
600, corte em 0,15.

---

# 2. Os princípios que se repetem

**Milímetros de tela, não metros.** Toda textura, praia, copa e espessura de via
está em mm. É o que mantém o desenho com a mesma cara em qualquer zoom, como numa
ilustração. A consequência é que o **dpi do render define a escala das texturas**
— os scripts fixam 96.

**Ruído, não padrão.** A textura do Operations Room não tem direção nem período.
Qualquer padrão de linhas ou de pontos entrega a grade em menos de um segundo de
olhar.

**Ladrilho que emenda de verdade.** Ruído de valor sobre grade **periódica**: a
oitava de período *n* toma os índices módulo *n*, e o último pixel interpola de
volta para o primeiro.

**Sobrepor, não pintar.** Quase todo ladrilho é modulação ARGB: não carrega cor,
só empurra o que está embaixo para mais claro ou mais escuro. Assim o mesmo
arquivo de grama serve sobre o oliva e sobre a areia.

**Medir, não olhar.** Metade dos achados deste projeto veio de contar pixels. Ver
a seção 5.

---

# 3. Catálogo de armadilhas do PyQGIS 3.44

Quase todas foram **medidas**, não lidas em documentação.

### Dados e projeto

- **GeoPackage, não GeoJSON**, para o que o script grava. O driver do GeoJSON se
  recusa a sobrescrever.
- **Sobrescreva no lugar**, não apague antes. `QgsVectorFileWriter` com
  `CreateOrOverwriteFile`. O OneDrive segura o arquivo da rodada anterior com
  frequência, `os.remove` falha, e aí os dois drivers se recusam a criar por cima
  e a rodada morre no meio.
- **Camada de memória não sobrevive dentro de um `.qgz`**: ao reabrir, o QGIS
  acha a referência e não os dados.
- **O plugin `processing` não está no path do lançador** — mora em
  `apps/qgis*/python/plugins`, os scripts o acrescentam na mão.
- **O ângulo da caixa mínima orientada tem que ser calculado em EPSG:3857.** Não
  é arredondamento: o Web Mercator estica Y em 7,4% na latitude do Havaí, o que
  **vira o eixo longo de 96 dos 5533 prédios em 90° inteiros**. O algoritmo
  preserva a ordem de entrada mas **renumera os `fid`** — casar por `fid` dá 4
  acertos em 5533; o casamento é posicional.

### Símbolos e efeitos

- **`RenderMetersInMapUnits` sem elipsoide não é metro.** É unidade de mapa do
  3857, que nesta latitude está esticada em 1/cos: **medido** nas fatias, a via
  de "5,5 m" saía com 3,6 m de chão (fator 0,652 = cos 49,3°), em todas as
  classes e em duas placas. Vale para tudo que o `estilo.py` mede em `CHAO` —
  via, rio, trilho, copa — e vale nas Ardenas também (cos 50° = 0,64). O
  `pincel.py` converte metros pela `larguraKm` da ficha, que é chão de verdade.

- **Efeito de pintura não mora no símbolo.** `QgsFillSymbol` não tem
  `setPaintEffect`. Vai na camada de símbolo — ou, melhor, **no renderizador**:
  na camada roda uma vez por feição (3,93 s nos 5533 prédios) contra 0,38 s no
  renderizador. 102×, e o desenho fica melhor.
- **Sombra com borrão maior que o deslocamento é sombra invisível**: fica quase
  toda debaixo do próprio desenho.
- **Pilha de efeitos sem `QgsDrawSourceEffect` no fim desenha só a sombra.**
- **`setMaximumRandomDeviationX`**, e não `setRandomDeviationX` — este não
  existe. Atrás de um `hasattr` some em silêncio.
- **Semente de fábrica 0 = re-sorteia a cada render.** Sem `setSeed` o desenho
  pisca entre repinturas.
- **Modo Viewport** no preenchimento raster. Em Feature cada *feição* ancora o
  ladrilho no próprio retângulo e aparece emenda onde dois polígonos se tocam.
- **Caminho de PNG inexistente pinta PRETO OPACO.** A string vazia é o sentinela
  seguro. (No marcador SVG é o contrário: string vazia desenha um `?`.)
- **Vários `set*Unit` recusam `int`** — passe `QgsUnitTypes.RenderMillimeters`.
  Já `setBlurRadius` e `setOffsetAngle` só aceitam **int**.
- **`setWidthUnit` está obsoleto** no preenchimento raster → `setOutputUnit`.

### Expressões por feição

- **Expressão quebrada é aceita em silêncio absoluto**: a propriedade fica ativa
  e o QGIS desenha o valor estático. Valide com `QgsExpression.hasParserError()`
  antes de aplicar — é o que o `dd()` faz.
- **`rand()` sem semente não é estável.** Só a forma de três argumentos.
- **Hash multiplicativo não embaralha.** `($id * 2654435761) % 4` colapsa
  exatamente em `$id % 4`; o mapa sai listrado.
- **Nunca monte expressão com `%` do Python** — o `%` é o módulo do QGIS e a
  formatação come o operador. Use `.format()`.
- **Cuidado com `import *`**: se a camada se chama `agua` e a função de estilo
  também, a variável tapa a função e o erro só aparece na chamada. Mordeu duas
  vezes no Pearl; nas Ardenas usa-se `import estilo as ST`.

### SVG

- **Os dois ângulos têm sinais opostos.** Marcador SVG e preenchimento SVG querem
  `"rumo" - 90`; o `QgsLinePatternFillSymbolLayer` quer `90 - "rumo"`. Trocado, o
  erro bate 90° certinhos e a nervura corre **atravessada** no prédio.
- **Tudo que é fino tem que ser horizontal no desenho.** O esticão em x é maior,
  então traço vertical vira barra gorda. Se precisar de traço de verdade,
  `vector-effect="non-scaling-stroke"` é respeitado pelo Qt.
- **`setClipPoints(True)` não é enfeite**: sem ele o telhado vaza 30% da área por
  cima do vizinho. E **`setPointOnSurface(True)`**, porque o centroide de um L cai
  fora do L.
- **`Property.Name` troca o arquivo por feição no marcador.** `Property.File`
  existe, se anuncia como *Symbol file path*, e é **ignorado em silêncio**. (No
  `QgsSVGFillSymbolLayer` é o contrário: `File` é a certa.)
- **String crua de SVG não funciona** — o QGIS acha que é URL e desenha a
  nuvenzinha de download.
- **`fixedAspectRatio=0` não é "travado"**: 0 quer dizer "use a proporção do
  viewBox". `Width` e `Height` por feição passam por cima de qualquer jeito.
- **Na `Rule` não existe `setScaleMinDenom`** — é `setMinimumScale` /
  `setMaximumScale`, e os nomes são ao contrário do que parecem, porque o número
  é o **denominador**: `minimumScale` é o limite mais *afastado*.

### Marcador raster (PNG)

- `QgsRasterMarkerSymbolLayer` existe, tem `setPath`, e aceita **`name`** definido
  por dados — então dá para trocar o PNG por feição.
- **Não existe `param(fill)` num raster.** Para variar cor, gere **um PNG por
  tom** e troque o arquivo.

### 2.5D e 3D — pesquisados, não aplicados

- `Qgs25DRenderer` **existe** e roda headless, mas custa **14,8 s** nos 5533
  prédios e **substitui o renderizador inteiro** — a cor por telhado e a nervura
  desaparecem.
- `QgsVectorLayer3DRenderer` **não serve**: `QgsOffscreen3DEngine` e `Qgs3DUtils`
  não existem nas bindings Python desta instalação. **Sem PNG headless.**
- A rota viável, se um dia se quiser volume: extrusão à mão com
  `QgsGeometryGeneratorSymbolLayer` — **2,83 s**, mantendo cor, nervura e sombra.

---

# 4. As texturas

`textura.py` não sabe o que é um mapa; são geradores de PNG emendável.

| receita | onde entra |
|---|---|
| `mancha` | água, grama, terra batida — variação irregular sem direção |
| `laje` / `apron` | concreto: placas, baias e nódoa larga |
| `rocada` | campo de pouso: o xadrez de quem cortou a grama em faixas |
| `copa` | a árvore, em PNG com alfa |
| `grao` | granulação de papel sobre o mapa inteiro |

### Três coisas que custaram caro

**O lado claro pesa menos que o escuro.** Branco com alfa *a* sobre a cor *C*
entrega `C + a(255−C)`; preto entrega `C − aC`. Sobre um teal escuro, clarear
anda três vezes mais, e um ladrilho simétrico **lava a cor do mapa inteiro**. Daí
`CLARO = 0,55`.

**O ruído precisa ser normalizado antes dos controles.** O fBm não usa [0,1): ele
se aperta em torno de 0,5 com desvio de ~0,1. Multiplicar por `contraste` e
depois por `forca` dava **alfa médio de 2,8 em 255** — a textura não existia, e
mexer nos números não mudava nada de visível.

**O cache tem que hashear o código também.** Primeiro era só a receita; depois os
parâmetros — e ainda mordeu, porque o *algoritmo* mudou e os parâmetros não. A
medição continuou dando exatamente o mesmo 2,8.

### A repetição do ladrilho

**O que denuncia não é a razão ladrilho/tela.** É quantas vezes a maior feição de
dentro do ladrilho aparece dentro de uma peça contínua. A 46 mm cabem ~10 cópias
da nódoa na maior peça do pátio e a grade salta; a 90 mm são 5 e fica **pior**,
porque a nódoa cresceu junto.

Aumentar o mesmo ladrilho **não resolve**. Resolve um ladrilho com *mais coisa
dentro* — e, no limite, **maior que a tela** (a chapa do pátio tem 3456 px a
914 mm e não se repete nenhuma vez).

Empilhar dois ladrilhos de tamanhos primos entre si também não resolve: o olho
trava na feição do menor. O que engana é **escala de feição diferente**.

> Esse defeito reapareceu nas Ardenas porque os arquivos foram copiados antes da
> correção. Ao copiar de um mapa para outro, **confira as escalas de ladrilho**.

---

# 5. O que quebrou, e como se descobriu

O padrão é sempre o mesmo: **olhar não bastou, medir resolveu.**

| sintoma | causa real |
|---|---|
| mapa desbotou ao entrar o grão | viés do lado claro na sobreposição |
| ajustar os números não mudava nada | cache servindo o ladrilho velho, em silêncio |
| textura "não aparecia" | alfa médio 2,8 de 255 — medido, não estimado |
| baía inteira bege | classificador de terra contava prédios em vez de densidade |
| copas numa grade perfeita | `setRandomDeviationX` não existe, e o `hasattr` engolia |
| sombra invisível | borrão maior que o deslocamento |
| molhes ondulados | no OSM eles são **linha de costa**, não `pier` |
| `.qgz` não existia | o script só renderizava PNG |

**Ferramentas que funcionaram**: renderizar a mesma coisa com e sem o efeito e
diferenciar; contar tons distintos numa região; medir o alfa médio de um
ladrilho; imprimir o histograma do peso antes de aplicar.

---

# 6. Levar para fora do QGIS

`exporta.py` escreve o mapa achatado **mais uma camada por arquivo com alfa**,
registradas ao pixel, e um `enquadramento.txt` com extensão, escala e metros por
pixel.

- Registro **conferido**, não prometido: a 12000 px, 150 de 624.624 amostras
  diferem, desvio médio **1,0 de 255**. É arredondamento de antialias.
- **12000 px em 128 s, 16000 px em 225 s.** Não empurrei além disso.
- As regras de estilo reagem ao **denominador de escala**, que segue o *tamanho
  de saída*: o mapa inteiro cruza o corte de 1:8000 já a 6000 px, então o cartaz
  em alta resolução ganha os telhados desenhados de graça.
- A **moldura não vai** nas camadas exportadas — ela só existe no render.
- Saída em **8 bits**: para gradar pesado à mão, converta para 16 antes.

`pos.py` faz o acabamento global em código — oclusão (tirada do alfa dos prédios
e das árvores, o que uma imagem plana não permite), suavização da aresta de
vetor, brilho, tonalização dividida, vinheta e grão. Duas receitas, `leve` e
`forte`; **a leve é a certa** — a referência é mais lavada do que a intuição de
"tratar a imagem" sugere.

> **Por que em código e não no Photoshop:** pintar à mão é melhor para o que é
> *único* (escombro, fumaça, cratera, letreiro), mas **se perde no próximo
> render**. O que vale para a imagem inteira fica em código e volta em segundos.
> A regra prática: no Photoshop, pinte em camadas **por cima**, nunca sobre as
> camadas do QGIS.

Para animar: o mapa é **estático**, só os assets se mexem. Renderize a base uma
vez, grande, e monte o movimento por cima no After Effects. Não há integração
entre os dois — a passagem é por arquivo, e não precisa haver.

---

# 7. O que não está feito

**Árvore individual no zoom fechado.** A copa é medida em mm de tela, então
aproximar não a aumenta: de perto vira tapete denso. A solução é a mesma forma
dos telhados — regra por escala com o tamanho em unidades de mapa.

**Prédios.** As ruas foram (seção 8); o telhado e a sombra continuam do jeito
que o QGIS os desenha, e são a próxima coisa que denuncia "vetor" no zoom
fechado.

**Volume nos prédios.** A extrusão por `QgsGeometryGeneratorSymbolLayer` está
pesquisada e medida (2,83 s) e **não aplicada**: briga com a leitura de planta.

**`laje()` e `rocada()` não são emendáveis** e repetem 36× e 11× na tela. Nunca
apareceu porque a borda cai fora do quadro, mas está lá.

**Conversor lat/lon → pixel** para posicionar assets no AE sem chutar. Os números
já estão no `enquadramento.txt`; falta a conta.

**Variante de neve.** As referências das Ardenas são de dezembro de 1944. A
paleta é um dicionário no topo do `estilo.py` — é troca de cores mais uma textura
de neve, não mudança de máquina.

**Assets de terceiros.** Nada foi baixado. Os telhados e as copas são desenhados
proceduralmente, no estilo do mapa. Se um dia se quiser testar pacotes prontos
(Kenney é **CC0**), a máquina de escolher por classe já está montada em
`telhado.py` — basta apontar os caminhos para outros arquivos. O aviso: sprite
pronto tem proporção fixa e **só funciona se for escolhido por classe**, nunca
esticado para todas as formas.

---

# 8. As ruas: pintadas por cima, em raster

O símbolo de linha do QGIS tem um teto, e ele aparece no quadro fechado: faixa
chapada, contorno de espessura uniforme, ponta em semicírculo. É símbolo de mapa
rodoviário; com um pelotão andando em cima, é desenho animado. O que a
referência tem é uma **estrada** — piso claro com remendos e desgaste de roda,
beiral fino e escuro, capim batido no acostamento, calçada na cidade, sebe com
sombra no campo — e nada disso cabe num símbolo de linha. Não vale a pena
forçar: a rua sai do QGIS e é pintada em raster, por cima, em código.

Tudo está em `Normandia 1944/tools/pincel.py` (o pincel) e no bloco `--camadas`
do fim de `Normandia 1944/qgis/carentan.py` (as fatias). O README daquela pasta
tem a explicação de cada peça; aqui é o caminho curto e o que mordeu.

![Antes e depois: o toco do estacionamento, 110 m](Normandia%201944/docs/ruas-antes-depois-toco.jpg)

![Antes e depois: a Rue Holgate, a rotatória e a ferrovia, 260 m](Normandia%201944/docs/ruas-antes-depois-holgate.jpg)

## O caminho curto

1. **Copie os dois arquivos** para o mapa novo: `tools/pincel.py` inteiro e o
   bloco `--camadas` do fim do `carentan.py` (é a mesma função de render do
   próprio script, três vezes: as camadas abaixo da via com fundo opaco, a via
   sozinha e as de cima com alfa — menos trilho e sebe, que o pincel pinta).
   O pincel roda no Python de fora (`py -3`, com PIL, numpy e scipy), não no do
   QGIS.
2. O pincel lê o que já existe: a ficha `<placa>.json` (extensão em 3857, px,
   `larguraKm`, limites), o `via.geojson` com a tag do OSM no campo `h`, e —
   se houver — `predio`, `urbano`, `agua`, `brejo`, `rio`, `ferro`, `sebe`.
   O que não existe ele pula.
3. Rode `carentan.py <placa> <px> --camadas`. Ele grava as fatias e **chama o
   pincel no fim**; `--so-camadas` para antes. Leia a linha
   `registro: 100% do eixo cai dentro da via do QGIS` — abaixo de 90% a ficha
   ou a conversão lon/lat está errada, e nada do resto vale.
4. As medidas moram no topo do `pincel.py`, **todas em metros de chão**: pista
   por tag, beiral, orla, capim, calçada, sebe, lastro. Mude ali, e só ali.
5. Julgue com **recortes**, nunca com a placa inteira: o mesmo lon/lat nas três
   versões — cru, pintado, ortofoto — em 100 a 400 m de largura
   (`pincel.py --recorte`). Foi assim que se viu que o tom estava invertido, e
   olhando a placa inteira não se via.

Tempos medidos: 7 a 11 s por fatia a 8192 px, 100 s de pincel na mesma placa,
20 s nas de 4096. A nota de "~90 s por placa" nos READMEs antigos está velha.

## O que mordeu no caminho

Na ordem em que apareceu. Quase tudo foi **visto num recorte e medido**, não
suposto.

- **"5,5 m" que eram 3,6.** A primeira medição: o eixo rasterizado pelo
  pincel contra a borda da via do QGIS deu meia-largura de 2,35 m onde o
  estilo dizia 3,75. Fator 0,652 em todas as classes: `cos(lat)`. Está no
  catálogo da seção 3. O pincel usa metros de chão, então a rua saiu uns 50%
  mais larga do que saía — e do tamanho que tem.
- **A ponta redonda.** É o cap do símbolo, e não vale brigar com ele. Em
  raster: a **união** dos polígonos das vias, cada uma com ponta reta, e
  círculo só onde a ponta cai em cima de outra via (a esquina, ou a via partida
  em duas — cKDTree a 1,2 m). O beco termina reto; a esquina, redonda.
- **Rua escura vira vala.** A primeira versão tinha asfalto escuro, "como
  asfalto". Entre as casas virou trincheira, e na placa larga, veia preta.
  Vista de cima a rua é a superfície **mais clara** do terreno (mede na
  ortofoto: asfalto L≈155, grama 111). Piso claro e neutro (0,58 a 0,62), e
  quem dá a leitura é o **beiral**: uma linha de 0,3 m, escura, nítida.
- **Halo escuro simétrico é sombra de software.** Capim + vala + sombra da
  sebe, dos dois lados de toda rua, lia como *outer glow*. Em volta da rua só
  fica coisa clara (orla de cascalho com falhas, capim amarelado); o escuro
  vem **só** da sombra da sebe, para sudeste, o mesmo lado da sombra dos
  prédios.
- **Gradiente no beiral deixa a rua fora de foco.** Ao lado de um telhado de
  vetor nítido, 1,5 m de degradê parece desfoque. Linha fina, um pixel de
  antialias, e o tremor com amplitude de 22 cm em 1,6 m — mordida de mato, não
  onda de caneta.
- **O ruído do PIL mostra a grade abaixo de 5 px.** O ruído é uma grade
  aleatória pequena ampliada em bicúbico. Quando a escala pedida cai abaixo
  de 5 px (2,2 m na placa de 0,78 m/px), o que aparece é a própria grade:
  tracinhos periódicos ao longo da sebe e a trilha com cara de corda trançada.
  A oitava nunca fica mais fina que 5 px.
- **O tremor da borda tem que caber no polígono.** Somar ruído à distância
  para dentro do polígono empurrava a borda para fora dele — e onde o ruído
  era positivo aparecia **pista solta no campo**, manchas cinza a 50 m de
  qualquer rua. A folga do polígono é 3 px mais duas amplitudes, e fora dele a
  pista é zero.
- **Bico no entroncamento.** Com um polígono por via, o toco estreito que
  entra na rua larga atravessava o asfalto dela em ponta de seta, e a rotatória
  ganhava cunhas bege nos cantos. União antes de pintar; beiral só no contorno
  de fora da união; fechamento de 2 m para o canto de dentro sair arredondado.
- **A calçada dava a volta no beco.** As faixas de fora vêm da distância ao
  eixo, que em volta da ponta é um semicírculo. Cada faixa é recortada por um
  polígono mais largo com a mesma ponta reta.
- **Sebe em minhoca.** O vão da sebe sorteado com ruído de 16 m e três oitavas
  saía em pedaços de 5 m, e de perto eram lagartas verdes ao lado da rua. Ruído
  de 45 m e **uma** oitava. E só a mais de 60 m da cidade: com 25 m, sobrava
  janela entre dois trechos urbanos e a sebe saía em fragmentos.
- **A sebe do ladrilho do bocage era um dedo sujo.** `largura=0.030` de talhão
  (4 m) mais sombra de 3 px (4 m) davam uma faixa escura de 8 m, que no quadro
  fechado não lia como fila de árvores. `0.020` e `2` no `estilo.py`.
- **Ferrovia sem lastro no brejo.** O lastro era mascarado por "nem água nem
  brejo", e o aterro atravessa o brejo: sobravam 40 m de trilho no capim. Só a
  água interrompe o lastro.
- **O render cru cobre o pintado.** `carentan.py` grava `<placa>.png` cru, e
  uma rodada sem `--camadas` devolve a placa crua ao estúdio sem avisar. Por
  isso o `--camadas` chama o pincel no fim e falha alto se o pincel falhar.
- **Três olhares acham mais que um.** Um painel de três juízes com lentes
  diferentes (foto aérea, estilo Operations Room, artefatos), sobre os mesmos
  recortes, achou o que uma pessoa olhando não viu: o tom invertido, o halo
  simétrico, o bico. O que ficou de cada um está no README do Carentan. O
  revisor de código não rodou (limite da sessão) — o `pincel.py` foi revisado
  só por quem o escreveu.

## O que ficou de fora, de propósito

Dormentes na ferrovia (padrão periódico de 0,7 m: a 0,134 m/px aliasa),
pintura de faixa (não havia em 1944), sombra de árvore de quintal na rua (não
há posição de árvore no OSM). E os **prédios**, que são a próxima coisa a
denunciar vetor no zoom fechado — mas isso é outra conversa.
