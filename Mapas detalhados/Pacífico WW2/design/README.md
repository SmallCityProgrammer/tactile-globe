# Como desenhar um navio em planta

`ships.mjs` desenha encouraçados vistos de cima, em SVG, grandes o bastante
para servir de referência e de gabarito.

```
node design/ships.mjs
    -> design/yamato.svg       3.822 × 685 px   (263,0 × 38,9 m a 14 px/m)
    -> design/iowa.svg         3.926 × 602 px   (270,4 × 33,0 m a 14 px/m)
    -> design/comparacao.svg   2.984 × 1.160 px (os dois na mesma escala, com régua)
```

Não são desenhos: são **geometria**. Tudo está em metros, proa em x = 0, linha
de centro em y = 0, popa em x = LOA. Um reparo não fica onde parece bonito —
fica na caverna em que ele ficava, e o cano que sai dele tem 20,7 m porque um
46 cm/45 tem 20,7 m.

Isso não é preciosismo: é o que impede erro. O convés de aviação do Yamato
começa em 224,5 m **porque é ali que os canos da torre 3 terminam** quando ela
aponta para a popa (200 de barbeta + 7 de face + 15,5 de cano). Os hidroaviões
estavam em 223 na primeira versão e ficaram enfiados dentro dos canhões. O
número diz onde é que dá.

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
| secundária | 2 × 3 de 15,5 cm + 12 × 2 de 12,7 cm | 10 × 2 de 12,7 cm |
| antiaérea leve | ~52 triplos de 25 mm | 20 quádruplos de 40 mm + ~49 de 20 mm |
| aviação | 7 hidros, 2 catapultas | 3 hidros, 2 catapultas |
| chaminés | **1** (com favo de mel na boca) | **2** |

O porte desenhado é **abril de 1945** nos dois: o Yamato como saiu para Okinawa
na Ten-Gō (as torres de 15,5 cm das asas já tinham ido embora em 1943 para dar
lugar a mais antiaérea), a Iowa como andava ao largo do Japão.

A Iowa é sete metros mais comprida e o Yamato é o navio maior. A boca da Iowa
foi decidida pelas eclusas do Panamá, que têm 33,53 m; a do Yamato, por nada —
ele nunca precisou passar por lá. É o que a folha de comparação mostra de cara.

**Cores.** Yamato em cinza-verde de Kure com convés de **madeira natural**;
Iowa em Measure 22 (azul-marinho no casco até a borda, cinza-neblina acima) com
o teca tingido de **Deck Blue 20-B** — que é o que a US Navy passou a fazer a
partir de 1943. Por isso um convés é quente e o outro é azul.

---

## De onde vêm os números — e o que conferir primeiro

**Não usei imagem de referência.** Não abri planta, foto nem desenho: os
números saíram do que eu sei sobre os dois navios. Isso muda o que dá para
confiar em cada coisa, e vale separar em três níveis.

**Nível 1 — medidas consagradas.** Eslora, boca, calado, deslocamento,
velocidade, guarnição, calibre, número de canos, comprimento e espaçamento dos
canos, diâmetro da barbeta, base do telêmetro. São dados publicados e batidos;
se algum estiver errado é erro de digitação, não de julgamento.

**Nível 2 — o porte de 1945.** Quantas peças de cada tipo, e quando as torres
de 15,5 cm das asas do Yamato saíram. Bem estabelecido, mas as contagens de
antiaérea variam de fonte para fonte (o Yamato aparece com 98, 113, 150 e 162
canos de 25 mm dependendo de quem conta e de quando).

**Nível 3 — as estações, e é aqui que mora o risco.** O objeto `T` de cada
navio — a que distância da proa fica cada torre, o pagode, a chaminé, o mastro
— é **estimativa minha a partir da proporção geral**, não medição. O mesmo vale
para a tabela de cavernas que dá a forma do casco. É a primeira coisa a
conferir contra uma planta de verdade:

| | Yamato | Iowa |
|---|---|---|
| torre 1 | 61 m | 66 m |
| torre 2 | 84 m | 87 m |
| 15,5 cm de proa | 100 m | — |
| pagode / ilha | 116 m | 114 m |
| chaminé (1ª) | 140 m | 130 m |
| chaminé (2ª) | — | 156 m |
| mastro principal | 157 m | 172 m |
| posto de comando de ré | 169 m | 188 m |
| 15,5 cm de popa | 182 m | — |
| torre 3 | 200 m | 206 m |

Corrigir qualquer uma dessas linhas é editar um número; o navio se remonta
sozinho em volta dela.

O que **não** é estimativa, e serve de trava: a torre 3 do Yamato em 200 m com
7 m de face e 15,5 m de cano põe a boca dos canhões em 224,5 m, e o convés de
aviação começa exatamente ali. Se você mover a torre 3, o convés tem que andar
junto — é o tipo de coisa que o gerador deixa evidente e uma ilustração à mão
esconde.

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
const H = hullMaker([
  [0, 0], [3.5, 1.5], [9, 3.6], [16, 6.4], [25, 9.6], [36, 12.8], [48, 15.5],
  [62, 17.6], [78, 18.9], [95, 19.4], [115, 19.45], [135, 19.45], [152, 19.3],
  [170, 18.7], [186, 17.7], [200, 16.4], [214, 14.5], [227, 12.2], [239, 9.4],
  [249, 6.5], [256.5, 3.8], [261, 1.7], [263, 0],
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

A diferença entre os dois cascos é toda aqui: a proa da Iowa sai de 0 e só
chega a 13,6 m de meia-boca lá pelos 102 m, enquanto a do Yamato já tem 15,5 m
aos 48 m. É por isso que uma parece uma lâmina e a outra um charuto.

### 2. As estações — onde fica cada coisa

```js
const T = { n1: 61, n2: 84, sf: 100, br: 116, fn: 140, mm: 157, ap: 169, sa: 182, n3: 200 };
//          torre 1   torre 2   15,5 cm   pagode   chaminé  mastro  posto  15,5 cm  torre 3
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
const G46 = { faceW: 12.6, midW: 15.2, rearW: 13.2, fwd: 7.0, aft_: 14.0,
              barbette: 13.3, guns: 3, spacing: 3.05, cal: 46,
              barrelProj: 15.5, rf: 15.0, rfBack: 3.2 };     // Yamato
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
