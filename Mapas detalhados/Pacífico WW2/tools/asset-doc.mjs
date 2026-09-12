/*
 * asset-doc.mjs — src/template.html  ->  docs/assets.md
 *
 * The catalogue of asset slots is written once, in the ASSETS table of the
 * template, and the documentation is generated from it. A hand-kept list would
 * be wrong the first time a slot is added.
 *
 * usage:  node tools/asset-doc.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tpl = fs.readFileSync(path.join(ROOT, 'src', 'template.html'), 'utf8');

/* the table is a pure array literal, so it evaluates on its own */
const m = tpl.match(/const ASSETS = (\[[\s\S]*?\n\]);/);
if (!m) { console.error('ASSETS table not found in the template'); process.exit(1); }
const ASSETS = new Function('return ' + m[1])();

/* the per-class slots are generated at run time from the ship database */
const hist = path.join(ROOT, 'data', 'history.json');
const ships = fs.existsSync(hist) ? JSON.parse(fs.readFileSync(hist, 'utf8')).ships : [];
for (const s of ships) ASSETS.push({ id: 'navio_' + s.id, pt: `${s.n} (${s.t}, ${s.l} m)`, g: 'classes', k: 'glyph', m: s.l, rot: 1, cls: s.id });

const KIND = {
  glyph: 'carimbo num ponto',
  tile: 'textura que se repete',
  line: 'carimbo repetido ao longo de uma linha',
};
const groups = [];
for (const a of ASSETS) {
  let gr = groups.find(q => q.g === a.g);
  if (!gr) groups.push(gr = { g: a.g, items: [] });
  gr.items.push(a);
}

const size = a => {
  const v = a.m;
  if (v >= 1000) return (v / 1000).toFixed(v % 1000 ? 1 : 0).replace('.', ',') + ' km';
  if (v >= 1) return String(Math.round(v * 10) / 10).replace('.', ',') + ' m';
  return String(v).replace('.', ',') + ' m';
};
const px = a => {
  // the aspect the exportador uses when you click a slot to download its template
  if (a.k === 'tile') return '256 × 256';
  if (a.k === 'line') return '256 × 102';
  return a.an === 'bottom' ? '256 × 179' : '256 × 256';
};

const L = [];
L.push(`# Os assets do mapa

Tudo o que a carta desenha passa por um **slot**, e todo slot aceita um PNG seu.
São **${ASSETS.length}** deles. Não existe nada desenhado fora desta tabela — nem
a água, nem a textura do convés, nem a linha internacional de data.

> Esta página é gerada por \`node tools/asset-doc.mjs\` a partir da tabela
> \`ASSETS\` do \`src/template.html\`. Não edite à mão.

---

## Como um slot vira imagem

Toda marca do mapa chama \`glyph()\`, \`tile()\` ou \`stamp()\`, e essas três
resolvem o slot **nesta ordem**:

1. **o PNG que você soltou** — guardado no IndexedDB do navegador, sobrevive a
   recarregar a página, funciona até em \`file://\`;
2. **o PNG embutido no arquivo** — o que estava em \`data/assets.json\` na hora
   do \`node tools/pack.mjs\`;
3. **o desenho em código** — o fallback em \`DRAW[id]\`, que nunca some.

O botão \`imagem\` (tecla \`I\`) desliga 1 e 2 de uma vez, então dá para comparar
a sua arte com o desenho em código a qualquer momento.

---

## Trocar um asset

Abra \`assets.html\`, ou \`pacifico.html#assets\`, ou aperte \`A\` no mapa.

| ação | efeito |
|---|---|
| arrastar um PNG **para cima de um quadro** | troca aquele slot |
| soltar **vários PNG** em qualquer lugar da página | cada arquivo vai para o slot de mesmo nome (\`dd.png\` → contratorpedeiro) |
| **clicar no quadro** | baixa o desenho atual em PNG, no tamanho e na proporção certos, para pintar por cima |
| \`↺\` no canto do quadro | devolve aquele slot ao desenho em código |
| \`exportar assets.json\` | gera o arquivo que o \`pack.mjs\` embute |
| \`importar assets.json\` | carrega um conjunto inteiro de uma vez |
| \`restaurar tudo\` | limpa o IndexedDB |

Para que a troca entre no arquivo final:

\`\`\`
# exporte assets.json pela página, salve em data/, e:
node tools/pack.mjs
\`\`\`

---

## As três espécies de slot

| espécie | o que é | como o mapa usa |
|---|---|---|
| **glyph** | um carimbo num ponto | desenha centrado em (x, y), na largura pedida, girado se o slot girar |
| **tile** | uma textura | vira \`createPattern(..., 'repeat')\`; **tem que ladrilhar sem costura** |
| **line** | um carimbo repetido | plantado ao longo de uma polilinha, girado para a tangente |

### Convenções que a sua arte tem que respeitar

- **Proa/frente para a ESQUERDA.** Tudo que gira é desenhado apontando para −x:
  um navio com a proa em −x, um avião com o nariz em −x, uma seta apontando
  para −x. Um PNG com a proa para cima vai aparecer navegando de lado.
- **Âncora.** Quase tudo é ancorado pelo centro. Os slots marcados *base* na
  tabela (monte, vulcão) crescem a partir do chão: o ponto de ancoragem é o
  meio da borda de baixo.
- **Fundo transparente.** O mapa desenha o mar debaixo.
- **A coluna \`tamanho\`** é o tamanho real que aquilo tem no mundo, em metros.
  O mapa divide pelo metros-por-pixel da vista para saber de quantos pixels
  precisa. Num *tile* é o lado de uma repetição.
- **Resolução.** O gabarito que o botão baixa tem 256 px de largura; qualquer
  coisa entre 128 e 512 px serve. Acima disso só engorda o arquivo — o mapa
  raramente desenha um glifo com mais de 300 px.

---

## O catálogo

`);

for (const gr of groups) {
  L.push(`### ${gr.g} — ${gr.items.length} ${gr.items.length === 1 ? 'slot' : 'slots'}\n`);
  L.push('| arquivo | o que é | espécie | tamanho | gira | gabarito |');
  L.push('|---|---|---|---|---|---|');
  for (const a of gr.items) {
    L.push(`| \`${a.id}.png\` | ${a.pt} | ${KIND[a.k]} | ${size(a)}${a.an === 'bottom' ? ' *(base)*' : ''} | ${a.rot ? 'sim' : '—'} | ${px(a)} |`);
  }
  L.push('');
}

L.push(`---

## O grupo \`classes\`

Os ${ships.length} slots \`navio_*\` são gerados do banco de classes
(\`data/history.json\`): um por classe de navio. Eles têm **precedência sobre o
slot de tipo**, então:

- \`navio_yamato.png\` desenha só o Yamato;
- \`bb.png\` desenha qualquer encouraçado que não tenha ficha própria;
- sem nenhum dos dois, o código monta o casco em planta a partir das medidas da
  classe (comprimento, boca, disposição das torres, convés de voo).

É por isso que dá para trocar um navio de cada vez sem tocar nos outros.

Para desenhar um casco novo do zero, veja **[design/README.md](../design/README.md)**:
tem um gerador de vistas em planta em SVG, com o Yamato e a Iowa prontos.
`);

fs.mkdirSync(path.join(ROOT, 'docs'), { recursive: true });
const out = path.join(ROOT, 'docs', 'assets.md');
fs.writeFileSync(out, L.join('\n'));
console.log(`docs/assets.md  ${ASSETS.length} slots em ${groups.length} grupos, ${(fs.statSync(out).size / 1024).toFixed(0)} KB`);
for (const gr of groups) console.log(`  ${gr.g.padEnd(14)} ${gr.items.length}`);
