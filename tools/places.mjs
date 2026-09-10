/*
 * places.mjs — Natural Earth  ->  data/places.bin
 *
 * Two point sets, for the city dots and for the names:
 *
 *   countries   NAME at LABEL_X / LABEL_Y, ordered by LABELRANK
 *   cities      NAME at the point, ordered by SCALERANK then population
 *
 * Both are stored *in order of importance*, which is what makes the zoom
 * threshold free at draw time: showing everything down to rank k is drawing
 * the first n[k] entries, so it stays one draw call with a smaller count and
 * needs no per-instance test.
 *
 * Natural Earth's populated places file is 18 MB, almost all of it names in
 * dozens of languages. Only the point, the rank and one name survive here.
 *
 * usage:  node tools/places.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data');
const BASE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/';
const Q = 1e5;                        // 1e-5 degree ~= 1.1 m, far finer than a dot needs

fs.mkdirSync(DATA, { recursive: true });

async function source(name, mb) {
  const file = path.join(DATA, name);
  if (!fs.existsSync(file)) {
    console.log(`downloading ${name} (~${mb} MB)...`);
    const res = await fetch(BASE + name);
    if (!res.ok) throw new Error('download failed: HTTP ' + res.status);
    fs.writeFileSync(file, Buffer.from(await res.arrayBuffer()));
  }
  return file;
}

/* ---------- encoder ---------- */
const buf = [];
function pushV(v) {
  let x = ((v << 1) ^ (v >> 31)) >>> 0;
  while (x > 127) { buf.push((x & 127) | 128); x = Math.floor(x / 128); }
  buf.push(x);
}
function pushU(v) {
  let x = v >>> 0;
  while (x > 127) { buf.push((x & 127) | 128); x = Math.floor(x / 128); }
  buf.push(x);
}
function pushName(s) {
  const b = Buffer.from(s, 'utf8');
  pushU(b.length);
  for (const c of b) buf.push(c);
}

/* ranks are 0..15; the renderer needs to know where each tier ends */
function writeSet(list) {
  pushU(list.length);
  const counts = new Array(16).fill(0);
  for (const p of list) counts[Math.min(15, Math.max(0, p.rank | 0))]++;
  let acc = 0;
  for (let i = 0; i < 16; i++) { acc += counts[i]; pushU(acc); }   // cumulative

  let lx = 0, ly = 0;
  for (const p of list) {
    const x = Math.round(p.lon * Q), y = Math.round(p.lat * Q);
    pushV(x - lx); pushV(y - ly);
    lx = x; ly = y;
    pushName(p.name);
  }
  return counts;
}

/* ---------- countries ---------- */
const f0 = await source('ne_10m_admin_0_countries.geojson', 13);
const gj0 = JSON.parse(fs.readFileSync(f0, 'utf8'));
const countries = [];
for (const f of gj0.features) {
  const p = f.properties;
  const lon = p.LABEL_X, lat = p.LABEL_Y;
  if (typeof lon !== 'number' || typeof lat !== 'number') continue;
  const name = p.NAME || p.NAME_EN;
  if (!name) continue;
  countries.push({ lon, lat, name, rank: Math.min(15, Math.max(0, (p.LABELRANK | 0))) });
}
countries.sort((a, b) => a.rank - b.rank || a.name.localeCompare(b.name));

/* ---------- cities ---------- */
const f1 = await source('ne_10m_populated_places.geojson', 18);
const gj1 = JSON.parse(fs.readFileSync(f1, 'utf8'));
const cities = [];
for (const f of gj1.features) {
  const g = f.geometry, p = f.properties;
  if (!g || g.type !== 'Point') continue;
  const name = p.NAME || p.NAMEASCII;
  if (!name) continue;
  cities.push({
    lon: g.coordinates[0], lat: g.coordinates[1], name,
    rank: Math.min(15, Math.max(0, (p.SCALERANK | 0))),
    pop: p.POP_MAX | 0
  });
}
cities.sort((a, b) => a.rank - b.rank || b.pop - a.pop);

/* ---------- write ---------- */
const cCounts = writeSet(countries);
const kCounts = writeSet(cities);
const bin = Buffer.from(buf);
fs.writeFileSync(path.join(DATA, 'places.bin'), bin);

const tiers = c => c.map((n, i) => n ? i + ':' + n : null).filter(Boolean).join('  ');
console.log([
  ``,
  `places`,
  `  countries           ${countries.length}`,
  `    by LABELRANK      ${tiers(cCounts)}`,
  `  cities              ${cities.length}`,
  `    by SCALERANK      ${tiers(kCounts)}`,
  `  data/places.bin     ${(bin.length / 1024).toFixed(0)} KB`
].join('\n'));
