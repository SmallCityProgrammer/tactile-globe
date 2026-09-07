/*
 * build.mjs — Natural Earth 1:10m  ->  data/*.bin
 *
 * Gera duas camadas:
 *
 *   borders.bin        paises: litoral + fronteiras nacionais  (admin_0)
 *   subdivisions.bin   apenas as divisas internas              (admin_1)
 *
 * Os poligonos de estados do admin_1 tambem contem litoral e fronteiras
 * nacionais. As duas bases compartilham a mesma topologia — 99,6% dos
 * segmentos do admin_0 aparecem bit a bit identicos no admin_1 — entao da
 * para subtrair por chave exata e ficar so com o que e realmente interno.
 *
 * Em ambas as camadas:
 *   1. quantiza para 1e-6 grau (~11 cm)
 *   2. remove segmentos duplicados (divisa compartilhada aparece em cada lado)
 *   3. remove arestas artificiais (fecho polar, costura no antimeridiano)
 *   4. reagrupa em cadeias e grava como varint zigzag de deltas
 *
 * uso:  node tools/build.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data');
const BASE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/';

const Q = 1e6;                        // quantizacao: 1e-6 grau ~= 0.11 m
const POLAR = Math.round(89.9 * Q);
const SEAM = Math.round(180 * Q);

fs.mkdirSync(DATA, { recursive: true });

async function source(name, mb) {
  const file = path.join(DATA, name);
  if (!fs.existsSync(file)) {
    console.log(`baixando ${name} (~${mb} MB)...`);
    const res = await fetch(BASE + name);
    if (!res.ok) throw new Error('falha no download: HTTP ' + res.status);
    fs.writeFileSync(file, Buffer.from(await res.arrayBuffer()));
  }
  return file;
}

/* aneis de todos os poligonos, quantizados, sem pontos repetidos */
function rings(file) {
  const gj = JSON.parse(fs.readFileSync(file, 'utf8'));
  const out = [];
  const push = r => {
    const q = [];
    let px = NaN, py = NaN;
    for (const c of r) {
      const x = Math.round(c[0] * Q), y = Math.round(c[1] * Q);
      if (x === px && y === py) continue;
      q.push(x, y);
      px = x; py = y;
    }
    if (q.length >= 4) out.push(q);
  };
  for (const f of gj.features) {
    const g = f.geometry;
    if (!g) continue;
    if (g.type === 'Polygon') for (const r of g.coordinates) push(r);
    else if (g.type === 'MultiPolygon') for (const p of g.coordinates) for (const r of p) push(r);
  }
  return out;
}

/* chave nao-direcional: A->B e B->A sao o mesmo segmento */
const key = (ax, ay, bx, by) =>
  (ax < bx || (ax === bx && ay <= by))
    ? ax + ',' + ay + ',' + bx + ',' + by
    : bx + ',' + by + ',' + ax + ',' + ay;

/* Percorre cada anel em ordem e corta a cadeia sempre que um segmento e
   descartado — mesmo resultado de construir a topologia inteira, sem
   precisar indexar vertices. `exclude` remove segmentos de outra camada. */
function chainsOf(qrings, exclude) {
  const seen = new Set();
  const chains = [];
  let kept = 0, dupes = 0, artificial = 0, shared = 0;

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
        const k = key(ax, ay, bx, by);
        if (exclude && exclude.has(k)) { ok = false; shared++; }
        else if (seen.has(k)) { ok = false; dupes++; }
        else { seen.add(k); kept++; }
      }

      if (ok) {
        if (!cur) { cur = [ax, ay]; chains.push(cur); }
        cur.push(bx, by);
      } else {
        cur = null;
      }
    }
  }
  return { chains, seen, kept, dupes, artificial, shared };
}

/* varint zigzag sobre deltas consecutivos */
function encode(chains) {
  const buf = [];
  const pushV = v => {
    let x = ((v << 1) ^ (v >> 31)) >>> 0;
    while (x > 127) { buf.push((x & 127) | 128); x = Math.floor(x / 128); }
    buf.push(x);
  };
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
  return Buffer.from(buf);
}

function report(label, out, r, bytes) {
  let pts = 0;
  for (const c of r.chains) pts += c.length / 2;
  console.log([
    ``,
    `${label}`,
    `  segmentos unicos    ${r.kept}`,
    `    duplicados        ${r.dupes}`,
    `    artificiais       ${r.artificial}`,
    r.shared ? `    ja em borders.bin ${r.shared}` : null,
    `  cadeias             ${r.chains.length}`,
    `  pontos              ${pts}`,
    `  ${out.padEnd(18)}${(bytes / 1048576).toFixed(2)} MB  (${(bytes / pts).toFixed(2)} bytes/ponto)`
  ].filter(Boolean).join('\n'));
}

/* ---- camada 1: paises ---- */
const f0 = await source('ne_10m_admin_0_countries.geojson', 13);
const r0 = chainsOf(rings(f0), null);
const b0 = encode(r0.chains);
fs.writeFileSync(path.join(DATA, 'borders.bin'), b0);
report('paises (admin_0)', 'data/borders.bin', r0, b0.length);

/* ---- camada 2: subdivisoes, subtraindo o que ja esta na camada 1 ---- */
const f1 = await source('ne_10m_admin_1_states_provinces.geojson', 40);
const r1 = chainsOf(rings(f1), r0.seen);
const b1 = encode(r1.chains);
fs.writeFileSync(path.join(DATA, 'subdivisions.bin'), b1);
report('subdivisoes (admin_1)', 'data/subdivisions.bin', r1, b1.length);
