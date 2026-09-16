/*
 * malha.mjs — qgis/via.geojson + qgis/predio.geojson -> data/malha.json
 *
 *   node tools/malha.mjs
 *
 * POR QUE ISTO EXISTE
 * Uma rota desenhada a mão passa por cima de tudo: o pelotão atravessa o
 * quarteirão em diagonal, entra num prédio e sai do outro lado. Num mapa onde
 * dá para ler cada telhado, isso é a primeira coisa que o olho pega.
 *
 * Duas saídas, e as duas são dado, não código:
 *
 *   A MALHA — o grafo das ruas de verdade, tirado do OSM. Com ele o estúdio
 *   deixa de interpolar entre dois pontos e passa a ANDAR: acha o nó mais perto
 *   de cada ponto da rota e procura o caminho mais curto por ruas. O pelotão
 *   dobra a esquina porque a esquina existe, não porque alguém a desenhou.
 *
 *   O BLOQUEIO — uma máscara de bit por célula dizendo onde há prédio. Serve
 *   para a validação reprovar, em milissegundos, um trecho que corta uma casa;
 *   é o mesmo papel do "está fora do mapa", e vale pelo mesmo motivo: é um erro
 *   que só apareceria no vídeo.
 *
 * A MÁSCARA É DE BIT, E NÃO DE POLÍGONO. Os 3365 prédios em GeoJSON são 1,5 MB
 * e cada teste é um ponto-em-polígono contra todos. A 3,1 m por célula a mesma
 * pergunta vira um índice num array, e o arquivo inteiro cabe em 72 KB de
 * base64 — o que importa aqui é "há parede neste metro quadrado", não qual
 * parede.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const QGIS = path.join(RAIZ, 'qgis');
const SAIDA = path.join(RAIZ, 'data', 'malha.json');

const COLA_M = 4.0;        // dois extremos a menos disto viram o mesmo nó
const GRADE_X = 1024;      // colunas da máscara de bloqueio

function morre(m) { console.error('malha: ' + m); process.exit(1); }

/* a ficha da placa mais larga diz o retângulo que a máscara tem que cobrir */
const fichas = fs.readdirSync(QGIS).filter((f) => f.endsWith('.json') && f !== 'osm.json')
  .map((f) => JSON.parse(fs.readFileSync(path.join(QGIS, f), 'utf8')))
  .filter((j) => j.limites);
if (!fichas.length) morre('nenhuma ficha de placa em qgis/ — rode o carentan.py antes');
const lim = fichas.reduce((a, j) => ({
  oeste: Math.min(a.oeste, j.limites.oeste), leste: Math.max(a.leste, j.limites.leste),
  sul: Math.min(a.sul, j.limites.sul), norte: Math.max(a.norte, j.limites.norte),
}), fichas[0].limites);

const LAT = (lim.sul + lim.norte) / 2;
const MX = 111320 * Math.cos(LAT * Math.PI / 180);   // metros por grau de longitude
const MY = 111132;                                   // metros por grau de latitude
const metros = (a, b) => Math.hypot((a[0] - b[0]) * MX, (a[1] - b[1]) * MY);

/* ------------------------------------------------------------- a malha */
const vias = JSON.parse(fs.readFileSync(path.join(QGIS, 'via.geojson'), 'utf8')).features;

/* As classes que um homem a pé usa. A 4 (serviço, trilha, calçada) entra: é
   justamente por onde se corta um quarteirão em Carentan. A 1 também — a
   estrada de Périers é o eixo do ataque das 6h. */
const nos = [];              // [lon, lat]
const porChave = new Map();
const adj = new Map();       // no -> [[vizinho, metros], ...]

function no(p) {
  /* 1e-6 de grau é 7 cm: dois vértices que o OSM escreveu com o mesmo valor
     caem na mesma chave, e o resto é colado depois por distância */
  const ch = p[0].toFixed(6) + ',' + p[1].toFixed(6);
  let i = porChave.get(ch);
  if (i === undefined) { i = nos.length; nos.push([p[0], p[1]]); porChave.set(ch, i); adj.set(i, []); }
  return i;
}
function liga(a, b) {
  if (a === b) return;
  const d = metros(nos[a], nos[b]);
  if (d <= 0) return;
  if (!adj.get(a).some((e) => e[0] === b)) adj.get(a).push([b, d]);
  if (!adj.get(b).some((e) => e[0] === a)) adj.get(b).push([a, d]);
}

/* O PASSO MÁXIMO ENTRE DOIS NÓS, e é ele que faz o grafo servir.

   O OSM guarda uma reta como DOIS pontos. Um trecho reto da estrada de
   Périers tem trezentos metros e dois nós — e o estúdio acha o caminho pelo nó
   MAIS PERTO de onde a unidade está. No meio dessa reta o nó mais perto fica a
   cento e cinquenta metros, e não raro numa RUA DIFERENTE: um caminho de serviço
   paralelo, a entrada de um pátio.

   Medido antes disto: os pontos da estrada de Périers, tirados da própria way do
   OSM, davam 41 e 47 m até o nó mais perto. O A* então partia do lugar errado, e
   um percurso de 244 m saía com 643 — com esporão de ida-e-volta no meio, que no
   vídeo é o pelotão girando no próprio eixo.

   Partir em pedaços de 12 m põe o erro de encaixe em 6 m no pior caso, que é
   menos que a largura da pista. Dobra o número de nós e vinte KB no arquivo. */
const PASSO_M = 12.0;

let descartadas = 0, densificados = 0;
for (const f of vias) {
  const c = f.geometry && f.geometry.coordinates;
  if (!c || f.geometry.type !== 'LineString' || c.length < 2) { descartadas++; continue; }
  const dentro = (p) => !(p[0] < lim.oeste - 0.004 || p[0] > lim.leste + 0.004 ||
                          p[1] < lim.sul - 0.004 || p[1] > lim.norte + 0.004);
  let anterior = null, antP = null;
  for (const p of c) {
    if (!dentro(p)) { anterior = null; antP = null; continue; }
    if (anterior !== null) {
      /* semeia o miolo do trecho antes de fechar a ligação */
      const d = metros(antP, p);
      const n = Math.floor(d / PASSO_M);
      let prev = anterior;
      for (let k = 1; k <= n; k++) {
        const t = k / (n + 1);
        const m = no([antP[0] + (p[0] - antP[0]) * t, antP[1] + (p[1] - antP[1]) * t]);
        liga(prev, m); prev = m; densificados++;
      }
      const i = no(p);
      liga(prev, i);
      anterior = i; antP = p;
    } else {
      anterior = no(p); antP = p;
    }
  }
}

/* A COLAGEM, e é ela que faz o grafo ser um grafo.
   No OSM duas ruas que se cruzam quase sempre partilham o nó — mas "quase". Um
   fim de rua a 30 cm do começo da outra fica sendo duas ilhas, e o caminho mais
   curto entre elas não existe. Sem este passo o grafo de Carentan sai em dezenas
   de pedaços e metade das rotas não fecha. */
const cel = COLA_M / MY;                 // célula de busca, em graus de latitude
const balde = new Map();
for (let i = 0; i < nos.length; i++) {
  const k = Math.floor(nos[i][0] / cel) + ':' + Math.floor(nos[i][1] / cel);
  if (!balde.has(k)) balde.set(k, []);
  balde.get(k).push(i);
}
let colados = 0;
for (let i = 0; i < nos.length; i++) {
  const cx = Math.floor(nos[i][0] / cel), cy = Math.floor(nos[i][1] / cel);
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
    for (const j of balde.get((cx + dx) + ':' + (cy + dy)) || []) {
      if (j <= i) continue;
      if (metros(nos[i], nos[j]) <= COLA_M && !adj.get(i).some((e) => e[0] === j)) {
        liga(i, j); colados++;
      }
    }
  }
}

/* quantos pedaços ficaram — um grafo em cem ilhas é um grafo que não serve */
const visto = new Uint8Array(nos.length);
let ilhas = 0, maior = 0;
for (let i = 0; i < nos.length; i++) {
  if (visto[i]) continue;
  ilhas++;
  let n = 0; const pilha = [i]; visto[i] = 1;
  while (pilha.length) {
    const u = pilha.pop(); n++;
    for (const [v] of adj.get(u)) if (!visto[v]) { visto[v] = 1; pilha.push(v); }
  }
  maior = Math.max(maior, n);
}

/* ---------------------------------------------------- a máscara de prédio */
const predios = JSON.parse(fs.readFileSync(path.join(QGIS, 'predio.geojson'), 'utf8')).features;
const largGrau = lim.leste - lim.oeste, altGrau = lim.norte - lim.sul;
const GRADE_Y = Math.max(1, Math.round(GRADE_X * (altGrau * MY) / (largGrau * MX)));
const bits = new Uint8Array(Math.ceil(GRADE_X * GRADE_Y / 8));
const mPorCel = largGrau * MX / GRADE_X;

function dentro(x, y, anel) {
  let d = false;
  for (let i = 0, j = anel.length - 1; i < anel.length; j = i++) {
    const xi = anel[i][0], yi = anel[i][1], xj = anel[j][0], yj = anel[j][1];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) d = !d;
  }
  return d;
}
let marcadas = 0;
for (const f of predios) {
  const anel = f.geometry && f.geometry.coordinates && f.geometry.coordinates[0];
  if (!anel || anel.length < 4) continue;
  /* só as células da caixa do prédio são testadas: a conta inteira contra
     todos os polígonos seria 3365 x 590 mil */
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of anel) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
  const cx0 = Math.max(0, Math.floor((x0 - lim.oeste) / largGrau * GRADE_X));
  const cx1 = Math.min(GRADE_X - 1, Math.ceil((x1 - lim.oeste) / largGrau * GRADE_X));
  const cy0 = Math.max(0, Math.floor((y0 - lim.sul) / altGrau * GRADE_Y));
  const cy1 = Math.min(GRADE_Y - 1, Math.ceil((y1 - lim.sul) / altGrau * GRADE_Y));
  const marca = (cx, cy) => {
    if (cx < 0 || cy < 0 || cx >= GRADE_X || cy >= GRADE_Y) return;
    const k = cy * GRADE_X + cx;
    if (!(bits[k >> 3] & (1 << (k & 7)))) { bits[k >> 3] |= 1 << (k & 7); marcadas++; }
  };
  for (let cy = cy0; cy <= cy1; cy++) {
    const lat = lim.sul + (cy + 0.5) / GRADE_Y * altGrau;
    for (let cx = cx0; cx <= cx1; cx++) {
      const lon = lim.oeste + (cx + 0.5) / GRADE_X * largGrau;
      if (dentro(lon, lat, anel)) marca(cx, cy);
    }
  }
  /* A PAREDE TAMBÉM, e não só o miolo.
     Testar o centro da célula perde todo prédio mais estreito que 3,1 m — e
     perde, pior, o anexo de fundo de quintal e o muro. Medido: dos centroides
     de 400 prédios, 90 caíam fora da máscara só por isso. Andar pelas arestas
     custa o comprimento do perímetro em células e fecha o contorno. */
  for (let i = 0, j = anel.length - 1; i < anel.length; j = i++) {
    const ax = (anel[j][0] - lim.oeste) / largGrau * GRADE_X;
    const ay = (anel[j][1] - lim.sul) / altGrau * GRADE_Y;
    const bx = (anel[i][0] - lim.oeste) / largGrau * GRADE_X;
    const by = (anel[i][1] - lim.sul) / altGrau * GRADE_Y;
    const passos = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay)));
    for (let k = 0; k <= passos; k++) {
      const t = k / passos;
      marca(Math.floor(ax + (bx - ax) * t), Math.floor(ay + (by - ay) * t));
    }
  }
}

/* --------------------------------------------------------------- gravar */
const saida = {
  limites: lim,
  nos: nos.flat().map((v) => +v.toFixed(6)),
  arestas: [].concat(...[...adj.entries()].map(([a, vs]) =>
    [].concat(...vs.filter(([b]) => b > a).map(([b, d]) => [a, b, +d.toFixed(1)])))),
  bloqueio: { largura: GRADE_X, altura: GRADE_Y, metrosPorCelula: +mPorCel.toFixed(2),
              bits: Buffer.from(bits).toString('base64') },
};
fs.mkdirSync(path.dirname(SAIDA), { recursive: true });
fs.writeFileSync(SAIDA, JSON.stringify(saida));
const kb = (n) => (n / 1024).toFixed(0) + ' KB';
console.log(`malha: ${nos.length} nós (${densificados} semeados a ${PASSO_M} m), ` +
            `${saida.arestas.length / 3} arestas ` +
            `(${colados} colados a ${COLA_M} m, ${descartadas} vias descartadas)`);
console.log(`       ${ilhas} pedaços; o maior tem ${maior} nós (${(maior / nos.length * 100).toFixed(0)}%)`);
console.log(`bloqueio: ${GRADE_X}x${GRADE_Y} a ${mPorCel.toFixed(2)} m/célula, ` +
            `${marcadas} células com prédio (${(marcadas / (GRADE_X * GRADE_Y) * 100).toFixed(1)}%)`);
console.log(`data/malha.json  ${kb(fs.statSync(SAIDA).size)}`);
if (maior / nos.length < 0.7)
  console.warn('AVISO: o maior pedaço tem menos de 70% dos nós — suba o COLA_M ou confira o via.geojson');
