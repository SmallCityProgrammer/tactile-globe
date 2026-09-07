# Globo Tátil

Um globo terrestre branco com as divisas dos países em cinza, e nada mais. Sem
oceanos, sem relevo, sem rótulos. Scroll para zoom, arrastar para girar. Um único
botão acrescenta as divisas de estados e províncias de todos os países.

Arquivo único de 5,6 MB, sem nenhuma dependência externa — abre por `file://`,
com duplo clique, offline.

![O globo](docs/globo.png)

---

## Usar

Abra `globo.html`. É só isso.

| ação | resultado |
|---|---|
| scroll | zoom, ancorado no ponto sob o cursor |
| arrastar | gira o globo, com o ponto agarrado colado no cursor |
| botão `estados e províncias` (ou tecla `d`) | liga/desliga as divisas internas |

A faixa de zoom vai do globo inteiro pequeno na tela até ~13 m de altitude.

---

## O problema

O pedido tinha um requisito que decide todo o resto: **resolução**, para zooms
muito fundos e muito distantes no mesmo objeto. Isso elimina de saída as duas
soluções óbvias.

- **Textura numa esfera** — resolução fixa. Uma textura 8K dá ~2,5 km/pixel no
  equador; qualquer zoom além disso vira borrão.
- **Malha esferificada** — o contorno da esfera vira polígono. Numa esfera de
  10 mil faces o horizonte já mostra facetas em zoom médio.

Então: fronteiras **vetoriais** e esfera **analítica**.

---

## Os dados

Fonte: [Natural Earth](https://www.naturalearthdata.com/) 1:10m, `admin_0_countries`
— a base pública mais detalhada de contornos de países. 13 MB de GeoJSON,
548.471 pontos.

`tools/build.mjs` reduz isso a 2,38 MB:

**1. Quantização** para 1e-6 grau (~11 cm). A precisão cartográfica real da base
é da ordem de 1 km, então isso é 10.000× mais fino que o dado — não se perde nada.

**2. Dedupe de fronteiras compartilhadas.** No GeoJSON, a divisa Brasil–Paraguai
existe duas vezes: uma no polígono de cada país. Desenhar as duas engrossa a linha
e dobra o custo. Com os vértices já quantizados, os segmentos compartilhados ficam
bit a bit idênticos, então basta uma chave não-direcional (`A→B` e `B→A` são o mesmo
segmento) num `Set`. **68.617 segmentos duplicados** removidos — 12,6% do total,
que é exatamente a proporção de fronteira terrestre contra litoral.

**3. Remoção de arestas artificiais.** Duas categorias existem só porque o GeoJSON
é plano e o globo não é:

- O polígono da Antártida cobre o polo sul. Em lon/lat isso é impossível sem uma
  aresta postiça descendo o antimeridiano até a latitude −90.
- Polígonos que cruzam o antimeridiano (Rússia, Fiji) são cortados ali, e o corte
  vira uma aresta vertical em ±180°.

São **777 segmentos** que não existem sobre uma esfera. Sem esse filtro aparece uma
linha reta saindo da costa antártica em direção ao polo — visível abaixo do centro:

![Aresta artificial da Antártida](docs/antartida-artefato.png)

**4. Recadeamento.** Os segmentos que sobraram são reagrupados em cadeias
percorrendo o anel original e cortando onde um segmento foi descartado — dá o mesmo
resultado que construir a topologia inteira, sem precisar indexar vértices.
Guardar cadeias em vez de segmentos soltos economiza metade dos pontos.

**5. Varint zigzag** sobre deltas consecutivos. Como os pontos vizinhos são
próximos, os deltas cabem quase sempre em 1–2 bytes: **5,21 bytes por ponto**.

> Testei gzip por cima: só 11% a mais. O fluxo de varints já está perto da entropia,
> e não valia a dependência de `DecompressionStream`. Ficou base64 puro.

Resultado: 4.324 cadeias, 479.106 pontos, 474.782 segmentos únicos.

### A segunda camada: estados e províncias

Vem do `admin_1_states_provinces` do Natural Earth — 4.596 subdivisões em 253
países, 1,3 milhão de pontos.

O problema é que esses polígonos **também** contêm o litoral e as fronteiras
nacionais: cada estado costeiro carrega seu pedaço de costa. Desenhar a base
inteira por cima da primeira camada dobraria todo o contorno dos países.

A saída depende de um fato que precisou ser verificado antes de valer a pena:
as duas bases são construídas sobre a **mesma topologia**. Medindo com os
vértices quantizados, **99,6% dos segmentos do admin_0 aparecem bit a bit
idênticos no admin_1**. Isso permite subtrair por chave exata, sem tolerância
nem heurística de proximidade:

| segmentos do admin_1 | |
|---|---|
| já presentes na camada de países | 540.864 → descartados |
| duplicados entre estados vizinhos | 371.157 → descartados |
| artificiais (polo, antimeridiano) | 775 → descartados |
| **divisas internas restantes** | **373.827** |

Sobram 5.967 cadeias e 379.794 pontos — 1,78 MB. É essa camada que o botão liga,
desenhada num cinza mais claro e mais fina que a dos países, para a hierarquia
ficar legível: divisa nacional pesa mais que divisa estadual.

![Estados brasileiros e departamentos vizinhos](docs/estados.png)

---

## A renderização

Dois passes de WebGL2, sem depth buffer.

### Passe 1 — a esfera, por interseção analítica

Um triângulo de tela cheia; cada pixel resolve a interseção raio–esfera em forma
fechada. Não há malha, então **não existe facetamento em nenhum zoom** e a silhueta
é exata. O antialiasing da borda sai do próprio discriminante, via derivadas de tela.

A forma ingênua `t = b − √(b²−c)` cancela catastroficamente quando a câmera está
rente à superfície (`b ≈ √(b²−c)`). A versão racionalizada `t = c/(b + √(b²−c))` é
estável em toda a faixa, com `c = 2h + h²` calculado em dupla na CPU.

### Passe 2 — as linhas, instanciadas

Um quad por segmento, expandido em espaço de tela para dar largura constante em
pixels. 941 mil instâncias num único `drawArraysInstanced`.

**Oclusão pelo horizonte sem depth buffer.** Um ponto `G` da esfera unitária é
visível da câmera `C` se `dot(G, C) ≥ 1`. Como todas as linhas estão exatamente
sobre a esfera, esse teste é exato — e resolve de graça o z-fighting que apareceria
ao desenhar linhas coplanares com uma superfície. O teste roda por fragmento
(recorte suave no horizonte) e também por vértice, descartando cedo os segmentos
inteiramente do lado escondido.

### O problema da precisão

`float32` tem ~7 dígitos. Numa esfera de raio 1, isso é um ulp de ~6e-8. Quando a
câmera desce a 600 m de altitude, a tela cobre ~1e-4 em unidades de raio e o erro
já é 0,3 px; a 60 m a imagem treme visivelmente.

A solução é aritmética de dupla emulada, só na parte que importa. Cada posição vai
para a GPU em duas metades:

```js
hi = Math.fround(v);
lo = Math.fround(v - hi);   // resíduo, calculado em dupla
```

e o shader faz a subtração relativa ao olho antes de qualquer outra coisa:

```glsl
vec3 rel = (aHi - uCamHi) + (aLo - uCamLo);
```

`aHi - uCamHi` é exato quando os dois são próximos (lema de Sterbenz), e o termo
`lo` devolve o resto. O erro final fica na casa de 1e-13 — irrelevante mesmo no
zoom máximo.

Verificado centrando num vértice real da base, a 12,7 m de altitude (tela cobrindo
~10 m): a linha passa exata pelo centro, sem tremor.

![Zoom extremo](docs/zoom-extremo.png)

O ponto final de cada segmento é guardado como **delta** em vez de posição absoluta.
O delta é pequeno (≤ 0,02°), então `float32` sozinho já dá 1e-11 de precisão nele —
economiza 25% do buffer sem custo nenhum.

### O problema da curvatura

Um segmento reto em lon/lat **não** é reto sobre a esfera. Traçar a corda 3D entre
dois vértices distantes afunda a linha para dentro do globo. Cada segmento é
subdividido até a flecha ficar abaixo de 10 cm (passo de 0,02°).

A interpolação é linear em lon/lat, não em grande círculo — é o que preserva
fronteiras definidas por paralelo, como o 49ᵒ entre EUA e Canadá, que num grande
círculo arquearia para o norte.

### Níveis de detalhe

Cinco níveis, simplificados com Douglas–Peucker no carregamento e escolhidos pela
resolução angular por pixel. Sem isso, o globo visto de longe vira um borrão escuro
de tanta linha sobreposta.

| nível | tolerância | passo | países | subdivisões |
|---|---|---|---|---|
| 0 | — (integral) | 0,02° | 940.899 | 642.121 |
| 1 | 0,008° | 0,06° | 328.199 | 194.809 |
| 2 | 0,04° | 0,25° | 83.912 | 51.858 |
| 3 | 0,15° | 0,90° | 23.614 | 16.895 |
| 4 | 0,45° | 2,50° | 9.545 | 8.628 |

Só o nível 3 dos países é construído antes do primeiro quadro. O resto entra em
segundo plano, intercalando as duas camadas, para o botão nunca abrir vazio.

As duas camadas passam pelo mesmo shader, em duas chamadas de desenho — as
subdivisões primeiro, os países por cima, para a linha mais forte vencer onde as
duas quase se encostam.

![Europa](docs/europa.png)

### Câmera

Estado em precisão dupla na CPU: `lon`, `lat`, altitude. Norte sempre para cima.

Arrastar e dar zoom usam a mesma primitiva: **colocar um ponto do mundo `G` num
pixel `(x,y)`**. Isso são 2 restrições, e a câmera norte-para-cima tem exatamente
2 graus de liberdade, então há solução fechada.

Convertendo o pixel num vetor `g = (a,b,c)` nas coordenadas da câmera, a componente
vertical do mundo depende só da latitude:

```
G_y = b·cos(φ) + c·sen(φ)
```

que resolve direto em `φ`; a longitude sai de um sistema 2×2 nas componentes `x,z`.

A primeira versão era iterativa: girar a câmera pela rotação mínima que leva o ponto
ao lugar certo, re-derivar o norte, repetir. Funciona, mas converge por aproximação
— cada passo descarta o roll e reintroduz um erro — e não dá para afirmar que fecha
exato. A forma fechada resolve em uma passada e é exata por construção: **erro de
0 m** em todos os casos medidos, inclusive 40 notches de scroll do globo inteiro até
o zoom máximo, e no arrasto ponto-a-ponto.

---

## Desempenho

Medido em RTX 3050 Laptop, 1038×986:

| vista | só países | com subdivisões |
|---|---|---|
| zoom máximo (13 m) | 7,5 ms | 4,9 ms |
| região (127 km) | 2,7 ms | 4,2 ms |
| continente | 0,9 ms | 1,5 ms |
| globo inteiro | 0,3 ms | 0,5 ms |

Primeira pintura em ~196 ms. 79 MB de VRAM com as duas camadas e todos os níveis
(2,3 milhões de segmentos).

> O zoom máximo sair mais rápido com as subdivisões ligadas é ruído de medição —
> nessa vista quase toda a geometria cai no descarte por horizonte, e a diferença
> está dentro da variação de clock da GPU entre as duas medidas.

A renderização é sob demanda: sem input, nenhum quadro é desenhado.

---

## Reproduzir

```bash
node tools/build.mjs    # baixa o Natural Earth -> data/borders.bin
node tools/pack.mjs     # src/template.html + dados -> globo.html
```

Só precisa de Node (sem dependências). `build.mjs` é determinístico: gera
`borders.bin` byte a byte idêntico a cada execução.

```
src/template.html      renderizador (WebGL2 + controles), com os marcadores de dados
tools/build.mjs        Natural Earth -> binários quantizados
tools/pack.mjs         empacota tudo num HTML
data/borders.bin       países: litoral + fronteiras nacionais (2,38 MB)
data/subdivisions.bin  divisas internas de estados/províncias (1,78 MB)
globo.html             o resultado
```

---

## Limitações

- A precisão **cartográfica** do Natural Earth 1:10m é de ~1 km. Abaixo de uns 2 km
  de altitude o zoom continua nítido, mas não revela informação nova — você está
  vendo a geometria do dado, não mais detalhe do mundo.
- As linhas de costa estão desenhadas. Não há oceano colorido nem sombreado — terra
  e mar são o mesmo branco — mas o contorno costeiro faz parte do desenho de cada
  país; sem ele sobrariam só as divisas terrestres soltas.
- A cobertura do `admin_1` varia bastante por país: alguns têm subdivisões
  detalhadas, outros têm poucas ou nenhuma. O que aparece é o que a base traz.
- Sem inércia, sem animação de rotação, sem rótulos.
- Precisa de WebGL2 (universal em navegadores atuais; a página avisa se faltar).

---

## Créditos

Fronteiras: [Natural Earth](https://www.naturalearthdata.com/), domínio público.
