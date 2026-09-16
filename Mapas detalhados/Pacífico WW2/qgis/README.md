# Pearl Harbor, no estilo Operations Room

Um mapa de Pearl Harbor feito inteiro no QGIS, a partir do OpenStreetMap. Sem
navios, sem aviões, sem tropas: é um mapa, não uma ordem de batalha.

```
fetch.mjs  ──►  osm.json  ──►  convert.mjs  ──►  *.geojson  ──►  pearl.py  ──►  .png + .qgz
                                                                      ▲
                                        textura.py ──► texturas/*.png ─┤
                                        estilo.py  ────────────────────┘
```

| arquivo | o que faz |
|---|---|
| `fetch.mjs` | baixa o retângulo do Overpass (precisa de `User-Agent`, senão 406) |
| `convert.mjs` | `osm.json` → `agua costa verde via predio pier aero.geojson` |
| `textura.py` | gera os ladrilhos procedurais emendáveis |
| `estilo.py` | a paleta e todos os símbolos — **o estilo não existe em outro lugar** |
| `pearl.py` | deriva a terra, monta o projeto, grava `.qgz` e renderiza |
| `provas.py` | rende variantes lado a lado, para escolher olhando |

## Rodar

```powershell
cd 'C:\Users\eliez\OneDrive\Desktop\Mapa\Mapas detalhados\Pacífico WW2\qgis'
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' pearl.py
```

Com enquadramento próprio — sul, oeste, norte, leste, nome:

```powershell
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' pearl.py 21.348 -157.978 21.383 -157.933 ford-island
```

Depois é só abrir `pearl-harbor.qgz`. Não precisa repetir `fetch.mjs`/`convert.mjs`:
o `osm.json` já está baixado (fica fora do git, 21 MB).

---

## A terra não vem pronta

O OSM **não tem o porto como polígono de água**. Só existe a linha de costa. A
terra é deduzida assim:

1. junta a linha de costa com o retângulo da moldura;
2. `native:polygonize` fecha isso em faces (14, no recorte atual);
3. fica com as faces onde há **densidade** de prédio.

O terceiro passo é o que custou a acertar. *Contar* prédios não serve: o porto
tem três construções sobre estacas e passaria no teste, e a baía inteira ficava
bege. O que separa é a **fração** dos candidatos que cai dentro da face —
continente 594 de 600, água 3 de 600. Corte em 0,15.

---

## As texturas

O `textura.py` não sabe o que é um mapa; são geradores de PNG. Duas ideias
sustentam tudo:

**Ruído, não padrão.** A textura do Operations Room não tem direção nem período.
Qualquer padrão de linhas ou de pontos entrega a grade em menos de um segundo de
olhar. Então o tom vem de ruído fBm.

**Emendável de verdade.** O ladrilho se repete pela tela inteira; se a borda
direita não continuar na esquerda, cada repetição desenha uma costura e o
resultado vira justamente a grade que se queria evitar. Por isso o ruído é de
valor sobre uma grade **periódica**: a oitava de período *n* toma os índices
módulo *n*, e o último pixel interpola de volta para o primeiro.

| receita | onde entra | o que é |
|---|---|---|
| `mancha` | água, grama, terra batida | variação irregular de tom, sem direção |
| `laje` | pátio de concreto | malha de placas, cada uma com seu tom, com junta |
| `rocada` | campo de pouso | o xadrez de quem cortou a grama em faixas |
| `grao` | o mapa inteiro | granulação de papel, bem fina |

Quase todos saem em **ARGB de sobrepor**: o ladrilho não carrega cor, carrega só
a modulação (escurece aqui, clareia ali). Assim o mesmo arquivo serve sobre
qualquer base — uma cor chapada, o degradê da praia, o que for. A água é a
exceção: o ladrilho dela é opaco, de antes dessa ideia.

### Duas armadilhas que já custaram caro

**A repetição aparece.** Com ladrilho de 30 mm dava para contar as manchas
marchando pela baía. O que resolve é ladrilho grande com muitas manchas dentro
(150 mm, base 8): repete ~5 vezes num render de 3000 px em vez de 26.

**O cache mordia.** O nome do arquivo carrega um resumo dos **parâmetros**, não
só o da receita. Antes era só a receita, e mudar o contraste reaproveitava o PNG
velho em silêncio — ajustava-se o número, não mudava nada, e a culpa ia para o
número. Agora parâmetro diferente é arquivo diferente, e não há mais o que
apagar à mão.

---

## Medidas em milímetros, não em metros

Toda textura, a praia, as copas e a espessura das vias estão em **milímetros de
tela**. Não é descuido: é o que mantém o desenho com a mesma aparência em
qualquer zoom, como numa ilustração. Em metros, a trama sumiria ao afastar e
viraria mancha gigante ao aproximar.

A consequência é que o `dpi` do render define a escala das texturas. O `pearl.py`
fixa 96; mudar isso muda a aparência de tudo.

---

## O bege não é a terra

No Operations Room o terreno é oliva e o bege é só o **pátio da base** — o chão
batido em volta dos galpões. Foi o erro de fundo da primeira versão, com a terra
inteira bege.

O pátio é deduzido dos prédios: engorda cada um 85 m, funde tudo, encolhe 58 m
(isso fecha os vãos e arredonda os cantos) e corta na costa.

---

## Escolher olhando

```powershell
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' provas.py
```

Rende as receitas de água lado a lado num mesmo recorte e salva
`provas-agua.png`. Não refaz a terra — lê o que o `pearl.py` já gravou em
`.gpkg`, então roda em segundos.

Para trocar, mude `MAR_ESTILO` no topo do `estilo.py`.

---

## O que cada camada ganha

| camada | base | por cima |
|---|---|---|
| mar | shapeburst da água **com a terra como furos** → raso saindo de cada praia | `mancha` |
| terra | areia transbordando a costa + shapeburst areia→oliva | `mancha` (grama) |
| verde | oliva frio | `mancha` + copas com sombrinha própria |
| base | concreto | `laje` |
| aero | terra batida escura | `rocada` |
| pier | concreto | `laje` miúda |
| predio | cor sorteada por prédio + telhado em SVG | sombra dura no conjunto |
| papel | — | `grao` sobre o mapa inteiro |

### O pátio é uma chapa só, não um ladrilho

O concreto **não se repete nenhuma vez**: são 3456 px a 914,4 mm, que a 96 dpi é
maior que o render de 3000 px.

Chegar nisso exigiu medir, porque a intuição errava. A repetição é cópia
literal — diferença média de 0,2 a 1,5 níveis de cinza no deslocamento de um
período, contra 7,4 entre posições sem relação. Mas **o que denuncia não é a
razão ladrilho/tela**: é quantas vezes a maior feição de dentro do ladrilho (a
nódoa escura) aparece dentro de uma peça contínua de pátio. A maior peça da base
tem 9,22 km², ou 1713 × 795 px no render. A 46 mm cabem ~10 cópias e a grade
salta aos olhos; a 90 mm são 5, e fica **pior**, porque a nódoa cresceu junto e
ficou mais reconhecível.

Então aumentar o mesmo ladrilho não resolve. Resolve um ladrilho com **mais
coisa dentro** — e, no limite, um maior que a tela. Custa +0,013 s no render.

Empilhar dois ladrilhos de tamanhos primos entre si também não resolve: o olho
trava na feição do menor, que continua lá no mesmo passo. O que engana é escala
de feição diferente, e é por isso que vai uma `mancha(base=3)` a 290 mm por cima.

> Se o `LARG` do `pearl.py` subir acima de `LADO_PATIO`, a chapa volta a se
> repetir. Os dois números andam juntos.

A camada raster com `QgsMapClippingRegion` também funciona e recorta direito —
isso foi verificado —, mas custa 7× mais, o `.qgz` não guarda a região de
recorte, e sobretudo põe a textura em **metros**: ela cresceria ao aproximar e o
pátio deixaria de combinar com a água, a grama e o papel, que estão todos em
milímetros.

### O telhado em SVG, em duas rotas

Não é uma ou outra: são as duas, separadas por escala num `QgsRuleBasedRenderer`.

O **marcador** desenha um telhado de verdade por prédio — cumeeira, duas águas,
beiral com sombra — com `Width` e `Height` definidos por feição
**separadamente**, que é o que deixa o galpão 4×1 ser 4×1. Mas ele cobra pelos
prédios **que estão na tela**, não pelo tamanho da camada: 4 s a mais nos 5533 do
mapa inteiro, e praticamente nada em Ford Island (548 na tela) ou no hangar (27).
E no mapa inteiro o prédio tem 10 a 30 px, onde cumeeira e beiral somem de
qualquer jeito. Pagar ali é pagar por nada.

Longe, a **nervura** em `QgsSVGFillSymbolLayer`, que é até mais barata que a
hachura de linha que havia antes (0,109 s contra 0,231 s). O que ela nunca vai
dar é UMA cumeeira no meio e UM beiral na borda — ladrilho se repete, e cumeeira
é singular. Essa é a fronteira entre as duas rotas, e não é de desempenho.

O **raso** funciona porque a água leva a terra como furos: o shapeburst mede a
distância até a borda mais próxima, que dentro da baía é a linha de costa. Só
vale enquanto a distância for menor que 10% da extensão desenhada — o QGIS corta
a geometria de preenchimento na extensão inflada em exatamente 10%, e essa borda
cortada também brilha. No mapa inteiro sobra folga; num recorte bem fechado, não.

A **nervura do telhado** vem do azimute do eixo longo de cada prédio
(`native:orientedminimumboundingbox`), calculado em EPSG:3857 e guardado no campo
`rumo`.

---

## Detalhes que mordem

Quase todos foram descobertos batendo a cabeça, e alguns foram encontrados
sondando a instalação de verdade em vez de confiar na documentação.

### Dados e projeto

**GeoPackage, não GeoJSON, para o que o script grava.** O driver do GeoJSON se
recusa a sobrescrever, e o OneDrive às vezes ainda segura o arquivo da rodada
anterior. Os `.geojson` de entrada continuam como estão.

**Camada de memória não sobrevive dentro de um projeto.** Ao reabrir o `.qgz` o
QGIS acharia a referência e não os dados.

**O plugin `processing` não está no path do lançador.** Mora em
`apps/qgis*/python/plugins`, e os scripts o acrescentam na mão.

**O ângulo da caixa mínima tem que ser calculado em 3857**, não em 4326. Não é
arredondamento: o Web Mercator estica Y em 7,4% na latitude do Havaí, o que gira
o ângulo típico uns 2° e, pior, **vira o eixo longo de 96 dos 5533 prédios em 90°
inteiros** — a nervura correria atravessada neles. O algoritmo preserva a ordem
de entrada mas renumera os `fid`, então o casamento é posicional; juntar por
`fid` daria 4 acertos em 5533.

### Símbolos

**Efeito de pintura não mora no símbolo.** `QgsFillSymbol` não tem
`setPaintEffect`. Vai na camada de símbolo — ou, melhor, no **renderizador**: na
camada ele roda uma vez por feição, e nos 5533 prédios isso mede 3,93 s contra
0,38 s no renderizador. O desenho ainda fica melhor, porque a sombra sai da
silhueta do conjunto em vez de cada prédio jogar sombra no vizinho.

**Sombra com borrão maior que o deslocamento é sombra invisível**: ela fica
quase toda debaixo do próprio desenho e escapa só uma franja. Deslocamento 1,15 mm
com borrão 0,5 mm lê; o contrário não.

**Uma pilha de efeitos sem `QgsDrawSourceEffect` no fim desenha só a sombra** e
some com o original.

**`setMaximumRandomDeviationX`**, e não `setRandomDeviationX` — este não existe.
Como estava atrás de um `hasattr`, as copas vinham numa grade perfeita e ninguém
percebia. E a semente de fábrica é 0, que significa "re-sorteia a cada render":
sem `setSeed` a mata muda de desenho a cada repintura.

**Modo Viewport no preenchimento raster.** Em Feature cada *feição* ancora o
ladrilho no próprio retângulo, e aparece emenda onde dois polígonos se tocam; o
mar, sendo maior que a tela, ainda escorrega por baixo do mapa ao navegar.

**Caminho de PNG inexistente pinta PRETO OPACO** por cima de tudo. O sentinela
seguro é a string vazia, que não pinta nada.

**Vários `set*Unit` recusam `int`** — tem que ser `QgsUnitTypes.RenderMillimeters`.
`setBlurRadius` e `setOffsetAngle`, ao contrário, só aceitam `int`.

### Expressões por feição

**Expressão quebrada é aceita em silêncio absoluto**: a propriedade fica ativa e
o QGIS desenha o valor estático. O erro só apareceria no mapa, se aparecesse. O
`dd()` valida com `QgsExpression.hasParserError()` antes de aplicar.

**`rand()` sem semente não é estável** — pisca entre renders. Só a forma de três
argumentos, `rand(min, max, $id)`, é.

**Hash multiplicativo não embaralha.** `($id * 2654435761) % 4` colapsa
exatamente em `$id % 4`, porque a constante é ≡1 módulo 4; o mapa sai listrado.

**Nunca monte expressão com `%` do Python** — o `%` é o operador módulo do QGIS e
a formatação come o operador. Use `.format()`.

### SVG

**Os dois ângulos têm sinais opostos.** `QgsSvgMarkerSymbolLayer.Angle` e
`QgsSVGFillSymbolLayer.Angle` querem `"rumo" - 90`; o
`QgsLinePatternFillSymbolLayer.LineAngle` quer `90 - "rumo"`. Com o sinal trocado
o erro bate 90° certinhos e a nervura corre **atravessada** no prédio — erro que
só aparece olhando o mapa.

**Tudo que é fino tem que ser horizontal no desenho.** O QGIS estica o SVG em x e
em y por fatores diferentes; um traço vertical vira barra gorda, um círculo vira
elipse. Retângulo deitado guarda a espessura, que é medida em y. Se precisar de
um traço de verdade, `vector-effect="non-scaling-stroke"` é respeitado pelo Qt.

**`setClipPoints(True)` não é enfeite**: sem ele o retângulo do telhado vaza 30%
da área de prédio por cima do vizinho e do chão. E `setPointOnSurface(True)`,
porque o centroide de um L cai fora do L. Os padrões de fábrica do
`QgsCentroidFillSymbolLayer` erram dois dos quatro.

**`Property.File` no marcador é um no-op silencioso** — quem troca o arquivo por
feição é `Property.Name`. (No `QgsSVGFillSymbolLayer`, `File` é a certa.)

**String crua de SVG não funciona**: o QGIS acha que é URL e desenha a nuvenzinha
de download. Caminho inexistente desenha um `?` — e string vazia também, ao
contrário do preenchimento raster, onde a string vazia é o sentinela seguro.

**`fixedAspectRatio=0` não é "travado"**: 0 quer dizer "use a proporção do
viewBox". `Width` e `Height` por feição passam por cima dele de qualquer jeito.

**A folga do telhado fica em 1,03–1,08.** Acima de ~1,10 a faixa do beiral é
empurrada para fora do recorte e o telhado volta a parecer chapado. O que não é
coberto não é buraco: é o chapado de baixo, na mesma cor sorteada.

**Na `Rule` não existe `setScaleMinDenom`** — é `setMinimumScale` /
`setMaximumScale`, e os nomes são ao contrário do que parecem, porque o número é
o denominador: `minimumScale` é o limite mais **afastado**.

### 2.5D e 3D, pesquisados e não aplicados

`Qgs25DRenderer` **existe** e roda headless, com parede clara/escura por azimute.
Mas custa 14,8 s nos 5533 prédios (0,98 s desligando a sombra dele, que não é
sombra projetada e sim um brilho simétrico em unidades de mapa), e **substitui o
renderizador inteiro** — a cor sorteada por telhado e a nervura desaparecem.

`QgsVectorLayer3DRenderer` / `QgsPolygon3DSymbol` **não servem aqui**: montam,
mas `QgsOffscreen3DEngine` e `Qgs3DUtils` não existem nas bindings Python desta
instalação, então não há como sair PNG headless. Esse caminho está fechado.

A rota que funcionaria, se um dia se quiser volume, é montar a extrusão à mão com
`QgsGeometryGeneratorSymbolLayer` (parede com `extrude(segments_to_lines(...))`,
telhado com `translate(...)`), que mede 2,83 s e **mantém** a cor por prédio, a
nervura e a sombra no renderizador. Fica registrado, não aplicado — extrusão
briga com a leitura de planta que o mapa tem hoje.

---

## O truque das texturas de sobrepor

Quase todo ladrilho é **ARGB de modulação**: não carrega cor, só empurra o que
está embaixo para mais claro ou mais escuro. Duas correções foram necessárias
para isso funcionar, e as duas custaram uma medição para aparecer.

**O lado claro pesa menos que o escuro.** Branco com alfa *a* sobre a cor *C*
entrega `C + a(255−C)`; preto entrega `C − aC`. Sobre um teal escuro, clarear
anda três vezes mais do que escurecer, e um ladrilho simétrico lava a cor do mapa
inteiro — foi o que aconteceu quando o grão de papel entrou e tudo virou pastel
de uma vez. Daí `CLARO = 0,55`.

**O ruído precisa ser normalizado antes dos controles.** O fBm não usa o
intervalo [0,1): somando oitavas de média 0,5 ele se aperta em torno de 0,5 com
desvio de uns 0,1. Multiplicar isso por `contraste` e depois por `forca` dava
alfa médio de **2,8 em 255** — a textura simplesmente não existia, e mexer nos
números não mudava nada de visível. Agora a primeira passada mede a faixa que o
ruído de fato ocupa e estica para [0,1]; só então `contraste` e `forca` querem
dizer alguma coisa.

**O cache hasheia o código também.** Antes era só a receita, depois passou a ser
os parâmetros — e ainda assim mordeu: a normalização foi escrita, os números
foram ajustados, e a medição continuou dando exatamente o mesmo 2,8. O cache
estava servindo o ladrilho de antes, em silêncio. Agora o conteúdo do
`textura.py` entra na chave, ao preço de regerar tudo (~30 s) quando o arquivo
muda.

---

## Levar para o After Effects

```powershell
& 'C:\Program Files\QGIS 3.44.12\bin\python-qgis-ltr.bat' exporta.py 12000 tudo
```

`exporta.py [largura] [tudo|ford|base]` escreve em `saida/<quadro>-<largura>/`:
o mapa achatado, **uma camada por arquivo com alfa**, e um `enquadramento.txt`
com extensão, escala e metros por pixel.

Não existe integração QGIS↔After Effects; a passagem é por arquivo. Mas o ponto
que importa é outro: no Operations Room **o mapa é estático** e só os navios e
aviões se mexem. Então o QGIS renderiza a base uma vez e o movimento acontece no
AE por cima — não há motivo para renderizar quadro a quadro.

### O registro é conferido, não prometido

No fim da exportação o script empilha as camadas de volta e compara com o
achatado. Medido a 12000 px: **150 de 624.624 amostras diferem, desvio médio 1,0
de 255, pior caso 1** — puro arredondamento de antialias. Empilhar os PNG no AE,
na ordem do número, com modo normal e opacidade cheia, reproduz o achatado.

Se um dia esse número subir muito, é sinal de que alguma camada ganhou um efeito
que não sobrevive à separação — daí a verificação ficar no script.

### Tamanhos medidos

| largura | escala do mapa inteiro | telhado | tempo total |
|---|---|---|---|
| 3000 | 1:15429 | nervura | ~30 s |
| 6000 | 1:7715 | **desenhado** | — |
| 12000 | 1:3857 | **desenhado** | 128 s |
| 16000 | 1:2893 | **desenhado** | 225 s |

As regras de estilo reagem ao **denominador de escala**, que depende do tamanho
de saída e não do enquadramento. O corte dos telhados está em 1:8000, então o
mapa inteiro já cruza o limiar a 6000 px: **o cartaz em alta resolução ganha o
desenho dos telhados de graça**, e o custo de 4 s que motivou a divisão em duas
rotas é irrelevante num render único.

16000 px foi verificado e funciona. Não empurrei mais que isso.

> As camadas são renderizadas de baixo para cima e empilhadas na hora, em vez de
> guardadas numa lista. A 12000 px cada uma ocupa uns 420 MB em ARGB, e segurar
> as onze junto com o achatado passaria de 4 GB.

---

## A sinuosidade, e os molhes que não ondulam

`SINUOSO_ON` no topo do `pearl.py` liga a ondulação: cada contorno é densificado
a 25 m e cada vértice deslocado por um campo de ruído suave (terra 14 m /
célula 220 m, mata 11 m / 130 m). Custa 0,45 s uma vez; **o render não muda**.

### A ordem é o ponto, não o parâmetro

O mar é a diferença do retângulo pela terra, e o pátio é o apron cortado na
terra: os dois **partilham contorno** com ela. Ondular a terra depois de montar
os dois abriria fenda em toda a praia. Por isso a ondulação entra logo depois da
terra e antes de tudo que dela deriva.

O intervalo de densificação também não é cosmético: `densifyByDistance` parte
cada segmento em `ceil(comprimento/intervalo)` pedaços iguais, determinístico e
simétrico, então o mesmo segmento em duas camadas recebe exatamente os mesmos
pontos. Com intervalos diferentes nas duas, o vazio reaparece.

### Dois pesos, e basta um zerar

| peso | o que segura | por quê |
|---|---|---|
| `congela` | 600 m junto à moldura | parte do contorno da terra **é** a borda da figura; ondular ali serrilharia o quadro |
| `estreito` | os molhes | concreto ondulado lê como obra torta, não como desenho à mão |

Os dedos compridos do estaleiro são molhes, mas no OSM entram na **linha de
costa** — são `terra`, e ondulavam junto. Como achá-los sem etiqueta: pela
**largura**. O núcleo é a terra encolhida de 45 m, então tudo mais estreito que
90 m desaparece dele; um vértice na costa larga fica a ~45 m do núcleo, um
vértice no meio de um molhe fica muito mais longe. O peso cai a zero ao longo de
55 m, para a ondulação se apagar entrando no molhe em vez de dar degrau.

Medido nos 6169 vértices da terra: `estreito` zera 2,7% (os molhes), `congela`
zera 26,8% (a borda do quadro, que é reta de propósito), e 61,5% ondulam cheio.

### As juntas do concreto

As duas coisas, e não uma. Dobrar os cortes tira a régua mas a **direção média**
das juntas continua 0/90 — sozinho não resolve o "tudo em L". Girar 12° tira o
alinhamento com a tela mas mantém a régua. Juntas, viram concreto despejado.

A chapa do pátio não é emendável, e nunca foi — mas ela é maior que a tela, então
a emenda nunca entra no quadro.
