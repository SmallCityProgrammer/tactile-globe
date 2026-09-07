/*
 * build.mjs — Natural Earth 1:10m  ->  data/borders.bin
 *
 * 1. baixa (uma vez) os poligonos de paises do Natural Earth
 * 2. quantiza as coordenadas para 1e-6 grau (~11 cm)
 * 3. remove segmentos duplicados: fronteiras compartilhadas entre dois
 *    paises aparecem duas vezes na fonte e sao desenhadas uma so vez
 * 4. remove arestas artificiais (fecho polar da Antartida e costura
 *    no antimeridiano) — elas nao existem sobre uma esfera
 * 5. reagrupa os segmentos restantes em cadeias e grava tudo como
 *    varint zigzag de deltas
 *
 * uso:  node tools/build.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC_URL = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson';
const GEOJSON = path.join(ROOT, 'data', 'ne_10m_admin_0_countries.geojson');
const OUT = path.join(ROOT, 'data', 'borders.bin');

const Q = 1e6;                        // quantizacao: 1e-6 grau ~= 0.11 m
const POLAR = Math.round(89.9 * Q);   // limiar do fecho polar
const SEAM = Math.round(180 * Q);     // antimeridiano

fs.mkdirSync(path.join(ROOT, 'data'), { recursive: true });

if (!fs.existsSync(GEOJSON)) {
  console.log('baixando Natural Earth 1:10m (~13 MB)...');
  const res = await fetch(SRC_URL);
  if (!res.ok) throw new Error('falha no download: HTTP ' + res.status);
  fs.writeFileSync(GEOJSON, Buffer.from(await res.arrayBuffer()));
}

const gj = JSON.parse(fs.readFileSync(GEOJSON, 'utf8'));

/* ---- 1. extrai todos os aneis dos poligonos ---- */
const rings = [];
for (const f of gj.features) {
  const g = f.geometry;
  if (!g) continue;
  if (g.type === 'Polygon') for (const r of g.coordinates) rings.push(r);
  else if (g.type === 'MultiPolygon') for (const p of g.coordinates) for (const r of p) rings.push(r);
}

/* ---- 2. quantiza, descartando pontos repetidos ---- */
const qrings = rings.map(r => {
  const out = [];
  let px = NaN, py = NaN;
  for (const c of r) {
    const x = Math.round(c[0] * Q), y = Math.round(c[1] * Q);
    if (x === px && y === py) continue;
    out.push(x, y);
    px = x; py = y;
  }
  return out;
});

/* ---- 3+4. dedupe e filtros, preservando a ordem do anel -> cadeias ----
   Percorrer o anel em ordem e cortar a cadeia sempre que um segmento e
   descartado da o mesmo resultado que construir a topologia inteira,
   sem precisar de um indice de vertices. */
const seen = new Set();
const chains = [];
let kept = 0, dupes = 0, artificial = 0;

for (const r of qrings) {
  const n = r.length / 2;
  let cur = null;
  for (let i = 0; i + 1 < n; i++) {
    const ax = r[2 * i], ay = r[2 * i + 1];
    const bx = r[2 * i + 2], by = r[2 * i + 3];
    let ok = true;

    if ((ay <= -POLAR && by <= -POLAR) ||
        (Math.abs(ax) === SEAM && Math.abs(bx) === SEAM)) {
      ok = false; artificial++;
    } else {
      // chave nao-direcional: A->B e B->A sao o mesmo segmento
      const k = (ax < bx || (ax === bx && ay <= by))
        ? `${ax},${ay},${bx},${by}`
        : `${bx},${by},${ax},${ay}`;
      if (seen.has(k)) { ok = false; dupes++; } else { seen.add(k); kept++; }
    }

    if (ok) {
      if (!cur) { cur = [ax, ay]; chains.push(cur); }
      cur.push(bx, by);
    } else {
      cur = null;                     // o corte quebra a cadeia
    }
  }
}
seen.clear();

let pts = 0;
for (const c of chains) pts += c.length / 2;

/* ---- 5. varint zigzag sobre deltas ---- */
const buf = [];
function pushV(v) {
  let x = ((v << 1) ^ (v >> 31)) >>> 0;
  while (x > 127) { buf.push((x & 127) | 128); x = Math.floor(x / 128); }
  buf.push(x);
}

pushV(chains.length);
let lx = 0, ly = 0;
for (const c of chains) {
  pushV(c.length / 2);
  for (let i = 0; i < c.length; i += 2) {
    pushV(c[i] - lx);
    pushV(c[i + 1] - ly);
    lx = c[i]; ly = c[i + 1];
  }
}

fs.writeFileSync(OUT, Buffer.from(buf));

console.log([
  `aneis                 ${rings.length}`,
  `segmentos unicos      ${kept}`,
  `  duplicados          ${dupes}   (fronteiras compartilhadas)`,
  `  artificiais         ${artificial}   (fecho polar + antimeridiano)`,
  `cadeias               ${chains.length}`,
  `pontos                ${pts}`,
  `data/borders.bin      ${(buf.length / 1048576).toFixed(2)} MB  (${(buf.length / pts).toFixed(2)} bytes/ponto)`
].join('\n'));
