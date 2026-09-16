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
| predio | cor sorteada por prédio + nervura alinhada ao prédio | sombra dura no conjunto |
| papel | — | `grao` sobre o mapa inteiro |

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
