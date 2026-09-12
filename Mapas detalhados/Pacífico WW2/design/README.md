# Como desenhar um navio em planta

`ships.mjs` desenha encouraçados vistos de cima, em SVG, grandes o bastante
para servir de referência e de gabarito.

```
node design/ships.mjs
    -> design/yamato.svg       3.822 × 685 px   Yamato em abril de 1945 (Ten-Go)
    -> design/yamato-1941.svg  3.822 × 685 px   Yamato como completado, o porte da planta
    -> design/iowa.svg         3.926 × 602 px   270,4 × 33,0 m a 14 px/m
    -> design/comparacao.svg   2.984 × 1.160 px (Yamato e Iowa na mesma escala, com régua)
```

`yamato('1941')` e `yamato('1945')` são o mesmo casco e as mesmas estações com
armamento diferente: em 1941 são quatro torres de 15,5 cm (duas delas nas asas,
abreadas com a chaminé), seis reparos duplos de 12,7 cm e oito triplos de
25 mm; em 1945 as torres das asas já foram para terra, os duplos de 12,7 cm
dobraram para doze e os 25 mm cobrem tudo que sobrou de superfície plana.

Não são desenhos: são **geometria**. Tudo está em metros, proa em x = 0, linha
de centro em y = 0, popa em x = LOA. Um reparo não fica onde parece bonito —
fica na caverna em que ele ficava, e o cano que sai dele tem 20,7 m porque um
46 cm/45 tem 20,7 m.

Isso não é preciosismo: é o que impede erro. O tombadilho do Yamato começa em
219,8 m **porque é ali que os canos da torre 3 terminam** quando ela aponta
para a popa (198 de barbeta + 6 de face + 15,8 de cano) — e a planta mostra o
convés quebrando exatamente nesse ponto. Os hidroaviões estavam avante disso na
primeira versão e ficaram enfiados dentro dos canhões. O número diz onde é que
dá.

---

## Os dois navios prontos

| | Yamato | Iowa |
|---|---|---|
| eslora total | 263,0 m | **270,4 m** |
| boca | **38,9 m** | 33,0 m |
| calado | 10,9 m | 11,0 m |
| deslocamento (plena carga) | **72.800 t** | 57.540 t |
| velocidade | 27 nós | **33 nós** |
| guarnição | 2.767 | 2.788 |
| bateria principal | 9 × 46 cm/45, 3 torres triplas | 9 × 40,6 cm/50, 3 torres triplas |
| comprimento do cano | 20,7 m | 20,3 m |
| espaçamento entre canos | 3,05 m | 2,97 m |
| diâmetro da barbeta | 13,3 m | 11,6 m |
| telêmetro da torre | 15,0 m | 13,7 m (torres 2 e 3) |
| secundária (1945) | 2 × 3 de 15,5 cm + 12 × 2 de 12,7 cm | 10 × 2 de 12,7 cm |
| secundária (1941) | 4 × 3 de 15,5 cm + 6 × 2 de 12,7 cm | — |
| antiaérea leve | ~52 triplos de 25 mm (8 em 1941) | 20 quádruplos de 40 mm + ~49 de 20 mm |
| aviação | 7 hidros, 2 catapultas | 3 hidros, 2 catapultas |
| chaminés | **1** (com favo de mel na boca) | **2** |

O Yamato sai nos dois portes; a Iowa, como andava ao largo do Japão em 1945.

A Iowa é sete metros mais comprida e o Yamato é o navio maior. A boca da Iowa
foi decidida pelas eclusas do Panamá, que têm 33,53 m; a do Yamato, por nada —
ele nunca precisou passar por lá. É o que a folha de comparação mostra de cara.

**Cores.** Yamato em cinza-verde de Kure com convés de **madeira natural**;
Iowa em Measure 22 (azul-marinho no casco até a borda, cinza-neblina acima) com
o teca tingido de **Deck Blue 20-B** — que é o que a US Navy passou a fazer a
partir de 1943. Por isso um convés é quente e o outro é azul.

---

## De onde vêm os números

**O Yamato foi medido em cima de uma planta.** A folha é a
[NH 111711](https://commons.wikimedia.org/wiki/File:Builders_plans_for_the_Japanese_battleship_Yamato_(NH_111711).png)
do Naval History & Heritage Command — domínio público nos EUA e no Japão — uma
prancha japonesa (第18図 戦艦大和の外見見取図, "esboço do aspecto externo do
encouraçado Yamato") que traz **perfil e planta** na mesma escala mais a tabela
de características. É o porte como completado, em 1941.

Como foi medido:

1. Achei a banda horizontal da planta contando pixels escuros por linha.
2. A corrida contínua de tinta dá o casco: **4.584 px para 263 m = 17,43 px/m**.
3. Conferi a escala pelo outro eixo: a boca mede 689 px, que a 17,43 px/m dá
   39,5 m contra os 38,9 m declarados — 1,5% a mais, que é a espessura do
   traço. Todas as meias-bocas saíram escaladas por 0,983.
4. Tracei o contorno (primeiro pixel escuro de cima e de baixo, com filtro de
   mediana para descartar rótulo encostado) e amostrei a meia-boca de 5 em 5 m.
5. O perfil está na mesma escala e alinhado com a planta (17,49 px/m, proas a
   12 px uma da outra), então chaminé e mastro — ilegíveis na planta, que é
   densa demais ali — foram lidos no perfil.

**O que mudou.** O grupo de vante inteiro estava uns 18 m avante demais:

| | antes | medido | Δ |
|---|---|---|---|
| torre 1 | 61 m | **81 m** | +20 |
| torre 2 | 84 m | **102 m** | +18 |
| 15,5 cm de vante | 100 m | **118 m** | +18 |
| pagode | 116 m | **133 m** | +17 |
| chaminé | 140 m | **153 m** | +13 |
| mastro principal | 157 m | **165 m** | +8 |
| 15,5 cm de ré | 182 m | **181 m** | −1 |
| torre 3 | 200 m | **198 m** | −2 |
| catapultas | 240 m | **243 m** | +3 |
| quebra do convés | — | **219 m** | novo |

A metade de ré já estava certa; o erro era todo à frente do pagode. E o casco
mudou mais ainda: ele carrega a **boca cheia de 130 até 210 m** (eu afinava a
partir de 135) e a proa é muito mais fina do que parece — **11 m de meia-boca
aos 50 m do talha-mar**, onde eu tinha 16.

A casamata das torres também encolheu: a planta dá 16 m de comprimento com o
centro da barbeta 6 m atrás da face, e não os 21 m que eu tinha suposto.

**A Iowa continua por medir.** As estações dela ainda são estimativa pela
proporção geral, mesmo nível de confiança que o Yamato tinha antes desta
passagem. Os *Booklets of General Plans* da US Navy estão em domínio público e
resolveriam do mesmo jeito.

**Trava útil, independente de qualquer planta:** a torre 3 do Yamato em 198 m,
com 6 m de face e 15,8 m de cano, põe a boca dos canhões em 219,8 m — e é
exatamente ali que a planta mostra o convés quebrar para o tombadilho. Se você
mover a torre 3, o convés tem que andar junto.

---

## O sistema de coordenadas

```
        y = -B/2   ┌──────────────────────────────┐
                   │                              │
  proa  x = 0   ◄──┤            y = 0             ├──►  popa  x = LOA
                   │                              │
        y = +B/2   └──────────────────────────────┘
```

- **metros**, sempre. O `viewBox` do SVG é em metros; só o atributo `width`
  usa pixels, e é `PX_PER_M` quem decide.
- **proa à esquerda** (−x), que é como os sprites do mapa apontam.
- as espessuras de traço também são em metros: `stroke-width: .3` é uma linha
  de 30 cm. É estranho no começo e depois fica natural.

---

## Anatomia de uma função de navio

Cada navio é uma função que devolve `{ id, L, B, H, layers }`. Tem três partes.

### 1. A tabela de cavernas — a forma do casco

```js
const H = hullMaker([          // Yamato, traçada da planta de 5 em 5 m
  [0, 0], [4, 1.4], [10, 3.2], [18, 5.9], [26, 7.3], [34, 8.6], [42, 9.9],
  [50, 11.1], [58, 12.5], [66, 13.9], [74, 15.2], [82, 16.1], [90, 17.0],
  [98, 17.7], [106, 18.2], [114, 18.7], [124, 19.1], [136, 19.35],
  [150, 19.42], [170, 19.45], [190, 19.45], [204, 19.3], [214, 18.9],
  [220, 17.0], [228, 16.6], [236, 15.8], [243, 14.2], [249, 10.8],
  [254, 7.9], [258, 5.4], [261, 2.8], [263, 0],
]);
```

Cada par é `[distância da proa, meia-boca no convés]`. Uma Catmull-Rom passa
por todos e fecha o contorno espelhado. Vinte e poucas estações bastam; menos
que isso e o casco vira polígono.

`hullMaker` devolve:

| | |
|---|---|
| `H.halfAt(x)` | meia-boca em qualquer x — **é com isto que se encosta coisa na borda** |
| `H.outline()` | o `d` do contorno fechado |
| `H.inset(d)` | o mesmo contorno puxado `d` metros para dentro (borda do convés) |
| `H.L`, `H.B` | eslora e boca, deduzidas da tabela |

A diferença entre os dois cascos é toda aqui: a proa da Iowa só chega a 13,6 m
de meia-boca lá pelos 102 m; a do Yamato chega a 15,2 m aos 74 m e depois
segura a boca cheia por oitenta metros. É por isso que uma parece uma lâmina e
a outra um charuto.

### 2. As estações — onde fica cada coisa

```js
const T = { n1: 81, n2: 102, sf: 118, br: 133, fn: 153, mm: 165, ap: 173, sa: 181, n3: 198, wing: 148 };
//          torre 1   torre 2   15,5 cm  pagode  chaminé  mastro  posto  15,5 cm  torre 3  asas
```

Um objeto e nada mais. Mexer numa estação move a peça e tudo que foi
posicionado em relação a ela.

### 3. As camadas

```js
return { id: 'yamato', L, B, H, layers: { conves, proa, torres, sup, deck, aa, av, misc } };
```

Viram grupos nomeados no SVG, nesta ordem de pintura:

| grupo | o que tem | sombra |
|---|---|---|
| `sombra-casco` | o contorno deslocado, sob tudo | — |
| `casco` | o costado | — |
| `conves` | tabuado, chapas de aço, quarteirão de popa | — |
| `proa` | correntes, âncoras, cabeços, quebra-mar, ventiladores | — |
| `miudezas` | balsas, escotilhas, ventiladores de meia-nau | — |
| `barcos` | escaleres e guindastes | leve |
| `aviacao` | catapultas, trilhos, hidroaviões, guindaste de popa | leve |
| `superestrutura` | pagode/ilha, chaminés, mastros, diretores, radar | leve |
| `artilharia` | torres e canos | forte |
| `antiaerea` | 12,7 cm, 25 mm, Bofors, Oerlikon | leve |

Esconder qualquer uma e o navio continua de pé.

---

## O catálogo de peças

Todas desenham em torno do próprio centro e depois são transladadas, então
girar é só passar um ângulo. Ângulos em **graus**.

### Artilharia principal

```js
mainTurret({ id, x, aft, train,
  faceW, midW, rearW,   // largura da face, do meio e da traseira da casamata
  fwd, aft_,            // quanto a casamata avança e recua do centro da barbeta
  barbette,             // diâmetro da barbeta
  guns, spacing, cal,   // número de canos, distância entre eixos, calibre em cm
  barrelProj,           // quanto de cano fica para fora da face
  rf, rfBack })         // base do telêmetro e quanto ele recua da traseira
```

`aft: true` vira a torre para a popa — a casamata é espelhada, não só os canos.
`train:` em graus gira a torre inteira; deixei em 0 porque é o que serve de
sprite, mas é aí que se põe a torre apontando para o inimigo.

As duas fichas prontas:

```js
const G46 = { faceW: 12.6, midW: 15.2, rearW: 13.2, fwd: 6.0, aft_: 10.5,
              barbette: 13.3, guns: 3, spacing: 3.05, cal: 46,
              barrelProj: 15.8, rf: 15.0, rfBack: 2.8 };     // Yamato, da planta
const G16 = { faceW: 12.2, midW: 13.1, rearW: 11.8, fwd: 6.2, aft_: 12.1,
              barbette: 11.6, guns: 3, spacing: 2.97, cal: 40.6,
              barrelProj: 15.0, rfBack: 2.6 };               // Iowa
```

### Resto do armamento

| chamada | o quê |
|---|---|
| `secTurret({ id, x, y, rot, aft, len, w, barbette, guns, spacing, cal, barrelProj })` | torre leve (15,5 cm, 20 cm) |
| `twinDP(x, y, rot, cal)` | reparo duplo de 12,7 cm / 5 in, com escudo |
| `aa25(x, y, rot)` | triplo de 25 mm (japonês) |
| `bofors(x, y, rot)` | quádruplo de 40 mm (americano) |
| `oerlikon(x, y, rot)` | 20 mm simples |
| `director(x, y, { r, rf, radar, rot })` | diretor de tiro; `rf` = base do telêmetro, `radar` = largura da antena |

### Estrutura

| chamada | o quê |
|---|---|
| `tower(x, [{ x, l, w, r }, …])` | pilha de plataformas, da base para o topo |
| `funnel(x, { l, w, cap, grid, rot })` | chaminé; `grid: true` põe o favo de mel do Yamato |
| `mast(x, { legs: [[x,y],…], top: { l, w } })` | tripé ou treliça vista de cima |
| `crane(x, y, { len, angle })` | pau de carga girado para fora |
| `catapult(x, y, rot, len)` | catapulta com carro e pivô |
| `breakwater(x, halfAt)` | quebra-mar em V, ápice para a proa |
| `radarSK(x, y)` / `radarBar(x, y, w, h, rot)` | o "colchão" de busca aérea e as antenas de barra |

### Miudezas

`boat(x, y, rot, len, bw, kind)` · `floatplane(x, y, rot, { span, len, twinFloat, mark })` ·
`vent(x, y, r)` · `hatch(x, y, w, h)` · `bollard(x, y)` ·
`searchlight(x, y, r)` · `raftRow(x0, x1, y, n)`

`mark: 'hinomaru'` ou `'star'` põe as insígnias. `twinFloat: true` dá o
flutuador duplo do Jake; sem ele sai o flutuador central do Kingfisher.

---

## Duas regras que custaram caro

**1. Uma peça que gira precisa de tom, não só de forma.** Os hidroaviões
saíram na primeira versão com asa, fuselagem e flutuadores todos no mesmo
cinza, e viraram um monte de lascas. Asa escura, fuselagem clara com capota e
cabine, flutuadores mais escuros por baixo: aí vira avião.

**2. Uma torre vista de cima é uma silhueta chapada.** O pagode do Yamato, em
retângulos concêntricos do mesmo tom, virou um alvo de tiro. O que dá altura é
**valor**: cada nível um passo mais claro que o de baixo (classes `.n1` a
`.n5`) e cada um com a sua sombra dura no convés.

Mesma coisa vale para as texturas do mapa: um ladrilho que pinta a própria
célula desenha a grade em que foi ladrilhado.

---

## Montar um terceiro navio

Copie `iowa()`, troque três coisas e pronto.

```js
function fletcher() {
  const L = 114.8, B = 12.0;
  const H = hullMaker([ /* [x, meia-boca] — umas 15 estações chegam num destróier */ ]);
  const edge = x => H.halfAt(x);
  const T = { n1: 26, n2: 38, br: 48, f1: 56, f2: 74, n3: 88, n4: 100 };

  const conves = [el('path', { class: 'conves', d: H.inset(0.4) })];
  const torres = [/* cinco simples de 12,7 cm: secTurret com guns: 1 */];
  const sup = [tower(T.br, [{ x: 0, l: 9, w: 6, r: 1.6 }, { x: 0, l: 5, w: 4, r: 1.4 }]),
               funnel(T.f1, { l: 3.4, w: 3.0 }), funnel(T.f2, { l: 3.4, w: 3.0 })];
  const aa = [], av = [], deck = [], proa = [], misc = [];
  return { id: 'fletcher', L, B, H, layers: { conves, proa, torres, sup, deck, aa, av, misc } };
}
```

Depois acrescente a paleta:

```js
PALETTE.fletcher = `--casco:#5a6572; --conves:#49515c; /* … */`;
```

e mande gerar:

```js
const F = fletcher();
fs.writeFileSync(path.join(ROOT, 'fletcher.svg'), svgFor(F));
```

O `svgFor()` monta sozinho o `viewBox`, as sombras, o tabuado e a ordem das
camadas.

---

## A paleta

Toda cor do desenho é uma variável CSS, todas juntas no bloco `PALETTE`.
Trocar a pele do navio é editar esse bloco e mais nada — nenhum `path` tem cor
escrita dentro.

| variável | onde aparece |
|---|---|
| `--casco`, `--casco-borda`, `--casco-baixo` | costado e contorno |
| `--conves`, `--conves-veio`, `--conves-junta` | tabuado: tábua, veio e junta de topo |
| `--aco`, `--aco-alto`, `--aco-baixo` | chapa em geral |
| `--aco-1` … `--aco-5` | os cinco degraus de valor das plataformas |
| `--torre`, `--torre-topo`, `--barbeta`, `--cano` | artilharia |
| `--reparo`, `--aa`, `--diretor`, `--telemetro` | armamento leve e direção de tiro |
| `--lona` | escaleres, balsas, capas de lona |
| `--sombra`, `--linha`, `--luz` | sombra projetada, traço e realce |
| `--hinomaru`, `--ouro`, `--vidro` | insígnia, o crisântemo da proa, holofotes |

---

## Levar para o mapa

Os SVG individuais são **só o navio, fundo transparente, proa à esquerda** — o
formato que os slots `navio_*` esperam. Para virar sprite:

1. abra o SVG num editor ou no navegador e exporte PNG na largura que quiser
   (300–600 px de eslora cobre qualquer zoom que o mapa desenha);
2. renomeie para o id da classe: `navio_yamato.png`, `navio_iowa.png`;
3. solte na página `assets` do mapa, ou junte num `assets.json`.

O catálogo completo dos slots está em **[../docs/assets.md](../docs/assets.md)**.

**Cuidado com o tabuado em escala pequena.** A tábua tem 22 cm. Abaixo de uns
10 px/m isso vira sub-pixel e a média com a linha escura deixa o convés
lamacento. Para sprite pequeno, suba a opacidade do veio ou desligue o tabuado
(`.conves{fill:var(--conves)}`).

---

## O que ficou de fora, e por quê

- **Ondas, esteira e sombra na água.** O mapa põe as dele, e um sprite precisa
  de fundo limpo.
- **Cabos, antenas e mastaréus finos.** De cima eles somem; desenhá-los só
  sujaria a silhueta.
- **Camuflagem disruptiva.** A Iowa usou Measure 22, que é lisa. Uma Measure 32
  com manchas é um `<clipPath>` do casco e mais alguns polígonos.
- **O interior das torres.** Se um dia quiser um corte, é outra vista.
