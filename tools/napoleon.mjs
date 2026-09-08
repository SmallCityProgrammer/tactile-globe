/*
 * napoleon.mjs — Natural Earth  ->  data/napoleon.bin
 *
 * The Napoleonic Empire at its greatest extent (1812): the French Empire
 * proper plus the client states ruled by Napoleon or his family. Defeated
 * but formally independent allies — Prussia, Austria, Denmark — are not in
 * it, and neither is anything taken and lost again (Egypt 1798, Portugal
 * 1807, Moscow 1812).
 *
 * 1812 borders do not survive in any modern dataset, so the region is
 * approximated with present-day boundaries: whole countries where the fit
 * is good, admin_1 subdivisions where it is not.
 *
 * The renderer fills the region by even-odd parity, which means the layer
 * is just a bag of closed rings and set operations come for free:
 *
 *   country + a subdivision inside it  =  country minus that subdivision
 *
 * So a partial country is written as its admin_0 outline followed by the
 * subdivisions to remove. That keeps every international border on the
 * admin_0 geometry, bit-identical to the neighbour's, and confines any
 * topology mismatch between the two datasets to the inland cuts.
 *
 * Output is the varint format of borders.bin — rings instead of chains,
 * stored open (the renderer closes them).
 *
 * usage:  node tools/napoleon.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data');
const Q = 1e6;                          // 1e-6 degree, as in build.mjs

/* ---- what is in the empire ----------------------------------------- */

/* Whole countries. `keep` filters the polygons of a MultiPolygon by the
   centre of their bounding box — that is how the overseas départements and
   the islands that stayed out of the empire are dropped. */
const box = (lo0, la0, lo1, la1) => (x, y) => x >= lo0 && x <= lo1 && y >= la0 && y <= la1;
const SICILY   = box(11.8, 35.4, 15.8, 38.9);   // Bourbon, under British protection
const SARDINIA = box( 7.8, 38.5, 10.0, 41.6);   // where the House of Savoy took refuge
const BALEARIC = box( 1.1, 38.5,  4.4, 40.2);   // held for the Cortes, never occupied
const EUROPE   = box(-12.0, 34.0, 32.0, 60.0);

const COUNTRIES = [
  /* French Empire — departments annexed outright */
  ['FRA', box(-6, 41, 10, 52)],                           // metropolitan France + Corsica
  ['BEL', EUROPE],
  ['NLD', box(3, 50, 8, 54)],                             // annexed 1810
  ['LUX', EUROPE],
  ['MCO', EUROPE],
  ['AND', EUROPE],                                        // dép. de Sègre, 1812
  /* client states */
  ['CHE', EUROPE],                                        // Swiss Confederation
  ['LIE', EUROPE],                                        // Confederation of the Rhine
  ['ITA', (x, y) => EUROPE(x, y) && !SICILY(x, y) && !SARDINIA(x, y)],
  ['SVN', EUROPE],                                        // Illyrian Provinces
  ['ESP', (x, y) => box(-10, 36, 4, 44)(x, y) && !BALEARIC(x, y)],
  /* partial countries — outline here, cuts below */
  ['DEU', EUROPE],
  ['POL', EUROPE],
  ['AUT', EUROPE],
  ['HRV', EUROPE]
];

/* subdivisions removed from the country above, by ISO 3166-2 code */
const CUTS = [
  // Prussia's core, and the Danish duchies (Denmark was an ally, not a conquest)
  'DE-BB', 'DE-BE', 'DE-SH',
  // Prussian Silesia, Pomerania and East Prussia; Bialystok went to Russia in 1807
  'PL-DS', 'PL-OP', 'PL-ZP', 'PL-LB', 'PL-WN', 'PL-PD',
  // Austria proper — Tirol, Vorarlberg and Salzburg went to Bavaria, Karnten to Illyria
  'AT-1', 'AT-3', 'AT-4', 'AT-6', 'AT-9',
  // Croatia north and east of the Sava stayed Austrian and Hungarian
  'HR-01', 'HR-21', 'HR-02', 'HR-05', 'HR-20', 'HR-06',
  'HR-07', 'HR-10', 'HR-12', 'HR-14', 'HR-16'
];

/* subdivisions added on their own, where the country as a whole is out */
const ADDS = ['ME-08', 'ME-10', 'ME-19', 'ME-05'];        // Bocche di Cattaro, Illyrian Provinces
const ADD_NAMES = [['GRC', 'Ionioi Nisoi']];              // Ionian Islands, French 1807-1814

/* -------------------------------------------------------------------- */

function load(name) {
  const file = path.join(DATA, name);
  if (!fs.existsSync(file)) {
    console.error(`${path.relative(ROOT, file)} is missing — run first:  node tools/build.mjs`);
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

const polysOf = g =>
  !g ? [] : g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];

/* quantized ring, repeated points dropped, closing point not stored */
function ring(r) {
  const q = [];
  let px = NaN, py = NaN;
  for (const c of r) {
    const x = Math.round(c[0] * Q), y = Math.round(c[1] * Q);
    if (x === px && y === py) continue;
    q.push(x, y);
    px = x; py = y;
  }
  if (q.length >= 4 && q[0] === q[q.length - 2] && q[1] === q[q.length - 1]) q.length -= 2;
  return q.length >= 6 ? q : null;
}

function collect(feature, keep, out) {
  for (const p of polysOf(feature.geometry)) {
    if (keep) {
      let lo0 = Infinity, la0 = Infinity, lo1 = -Infinity, la1 = -Infinity;
      for (const c of p[0]) {
        if (c[0] < lo0) lo0 = c[0];
        if (c[0] > lo1) lo1 = c[0];
        if (c[1] < la0) la0 = c[1];
        if (c[1] > la1) la1 = c[1];
      }
      if (!keep((lo0 + lo1) / 2, (la0 + la1) / 2)) continue;
    }
    for (const r of p) { const q = ring(r); if (q) out.push(q); }
  }
}

const a0 = load('ne_10m_admin_0_countries.geojson');
const a1 = load('ne_10m_admin_1_states_provinces.geojson');

const rings = [];
const tally = [];

for (const [code, keep] of COUNTRIES) {
  const f = a0.features.find(x => x.properties.ADM0_A3 === code);
  if (!f) { console.error(`admin_0 has no ${code}`); process.exit(1); }
  const before = rings.length;
  collect(f, keep, rings);
  tally.push([code, rings.length - before]);
}

for (const iso of CUTS.concat(ADDS)) {
  const sel = a1.features.filter(x => x.properties.iso_3166_2 === iso);
  if (!sel.length) { console.error(`admin_1 has no ${iso}`); process.exit(1); }
  const before = rings.length;
  for (const f of sel) collect(f, null, rings);
  tally.push([iso, rings.length - before]);
}

for (const [a3, name] of ADD_NAMES) {
  const sel = a1.features.filter(x => x.properties.adm0_a3 === a3 && x.properties.name === name);
  if (!sel.length) { console.error(`admin_1 has no ${a3}/${name}`); process.exit(1); }
  const before = rings.length;
  for (const f of sel) collect(f, null, rings);
  tally.push([name, rings.length - before]);
}

/* ---- the frontier ----
 * The rings above are the fill. Its outline is not their union of edges:
 * where two of them run along the same line the parity is the same on both
 * sides, so that stretch is interior, not frontier. France and Belgium share
 * a border and both are in; Germany and Brandenburg share the stretch of the
 * Polish border where one adds and the other takes away.
 *
 * Both cases are the same rule — a segment carried by an even number of rings
 * is not an edge — which is the dedup of build.mjs counted rather than
 * flagged. What survives is re-chained by walking each ring and cutting where
 * a segment was dropped.
 */
const key = (ax, ay, bx, by) =>
  (ax < bx || (ax === bx && ay <= by))
    ? ax + ',' + ay + ',' + bx + ',' + by
    : bx + ',' + by + ',' + ax + ',' + ay;

function frontier(rings) {
  const count = new Map();
  const seg = (r, i) => {
    const n = r.length / 2, j = (i + 1) % n;
    return [r[2 * i], r[2 * i + 1], r[2 * j], r[2 * j + 1]];
  };
  for (const r of rings)
    for (let i = 0; i < r.length / 2; i++) {
      const k = key(...seg(r, i));
      count.set(k, (count.get(k) || 0) + 1);
    }

  const done = new Set(), chains = [];
  let kept = 0, dropped = 0;
  for (const r of rings) {
    let cur = null;
    for (let i = 0; i < r.length / 2; i++) {
      const [ax, ay, bx, by] = seg(r, i);
      const k = key(ax, ay, bx, by);
      if (count.get(k) % 2 === 1 && !done.has(k)) {
        done.add(k); kept++;
        if (!cur) { cur = [ax, ay]; chains.push(cur); }
        cur.push(bx, by);
      } else {
        if (count.get(k) % 2 === 0) dropped++;
        cur = null;
      }
    }
  }
  return { chains, kept, dropped };
}

/* zigzag varints over consecutive deltas — same encoder as build.mjs */
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

const bin = encode(rings);
fs.writeFileSync(path.join(DATA, 'napoleon.bin'), bin);

const fr = frontier(rings);
const binE = encode(fr.chains);
fs.writeFileSync(path.join(DATA, 'napoleon_edge.bin'), binE);

let pts = 0, ptsE = 0;
for (const r of rings) pts += r.length / 2;
for (const c of fr.chains) ptsE += c.length / 2;
console.log(tally.map(([k, n]) => `${k}:${n}`).join(' '));
console.log([
  ``,
  `napoleonic empire (1812)`,
  `  rings                     ${rings.length}`,
  `  points                    ${pts}`,
  `  data/napoleon.bin         ${(bin.length / 1048576).toFixed(2)} MB  (${(bin.length / pts).toFixed(2)} bytes/point)`,
  ``,
  `frontier`,
  `  segments kept             ${fr.kept}`,
  `    interior, dropped       ${fr.dropped}`,
  `  chains                    ${fr.chains.length}`,
  `  points                    ${ptsE}`,
  `  data/napoleon_edge.bin    ${(binE.length / 1048576).toFixed(2)} MB  (${(binE.length / ptsE).toFixed(2)} bytes/point)`
].join('\n'));
