/*
 * build.mjs — Natural Earth 1:10m  ->  data/*.bin
 *
 * Produces two layers:
 *
 *   coastlines.bin     coastlines only                          (admin_0)
 *   land_borders.bin   country-to-country land borders only     (admin_0)
 *   subdivisions.bin   internal state/province borders only     (admin_1)
 *
 * The first split is free and exact. A segment carried by two different
 * country polygons is a land border between them; one carried by a single
 * polygon is coastline. The tally is already needed for deduplication.
 *
 * Carrying the country code alongside the tally also buys the MERGE table
 * below: a segment carried twice by what we call the same country is an
 * internal seam, and is dropped entirely.
 *
 * The admin_1 polygons also carry coastline and national borders. Both
 * datasets are built on the same topology — 99.6% of admin_0 segments appear
 * bit-for-bit identical in admin_1 — so the overlap can be subtracted by
 * exact key, with no tolerance and no proximity heuristic.
 *
 * For both layers:
 *   1. quantize to 1e-6 degree (~11 cm)
 *   2. drop duplicate segments (a shared border appears once per side)
 *   3. drop artificial edges (polar closure, antimeridian seam)
 *   4. re-chain and encode as zigzag varints over deltas
 *
 * usage:  node tools/build.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data');
const BASE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/';

/* Natural Earth keeps Western Sahara as its own admin_0. Drawn that way it
   is a lone box outlined in the middle of the Sahara, which reads as an
   error rather than as a position on a disputed territory. Most modern maps
   draw it inside Morocco; so does this one. The seam between them is
   dropped, and the pair is bounded by the coast, Algeria and Mauritania. */
const MERGE = { SAH: 'MAR' };

const Q = 1e6;                        // quantization: 1e-6 degree ~= 0.11 m
const POLAR = Math.round(89.9 * Q);
const SEAM = Math.round(180 * Q);

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

/* rings of every polygon, quantized, with repeated points dropped; each
   ring remembers the country it came from, after MERGE is applied */
function rings(file) {
  const gj = JSON.parse(fs.readFileSync(file, 'utf8'));
  const out = [];
  for (const f of gj.features) {
    const g = f.geometry;
    if (!g) continue;
    const raw = f.properties && (f.properties.ADM0_A3 || f.properties.adm0_a3);
    const code = MERGE[raw] || raw || '?';
    const push = r => {
      const q = [];
      let px = NaN, py = NaN;
      for (const c of r) {
        const x = Math.round(c[0] * Q), y = Math.round(c[1] * Q);
        if (x === px && y === py) continue;
        q.push(x, y);
        px = x; py = y;
      }
      if (q.length >= 4) out.push({ q, code });
    };
    if (g.type === 'Polygon') for (const r of g.coordinates) push(r);
    else if (g.type === 'MultiPolygon') for (const p of g.coordinates) for (const r of p) push(r);
  }
  return out;
}

/* undirected key: A->B and B->A are the same segment */
const key = (ax, ay, bx, by) =>
  (ax < bx || (ax === bx && ay <= by))
    ? ax + ',' + ay + ',' + bx + ',' + by
    : bx + ',' + by + ',' + ax + ',' + ay;

/* Walks each ring in order and cuts the chain wherever a segment is
   dropped — same result as building the full topology, without indexing
   vertices. `exclude` removes segments belonging to another layer. */
/* For each segment: how many rings carry it, and which countries. One ring
   means coastline; two countries mean a land border between them; twice by
   one country means an internal seam, which nobody should see. */
function tally(qrings) {
  const m = new Map();
  for (const { q, code } of qrings) {
    const n = q.length / 2;
    for (let i = 0; i + 1 < n; i++) {
      const k = key(q[2 * i], q[2 * i + 1], q[2 * i + 2], q[2 * i + 3]);
      let e = m.get(k);
      if (!e) { e = { n: 0, codes: new Set() }; m.set(k, e); }
      e.n++;
      e.codes.add(code);
    }
  }
  return m;
}

function chainsOf(qrings, exclude, accept) {
  const seen = new Set();
  const chains = [];
  let kept = 0, dupes = 0, artificial = 0, shared = 0, rejected = 0;

  for (const ring of qrings) {
    const r = ring.q || ring;
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
        else if (accept && !accept(k)) { ok = false; rejected++; }
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
  return { chains, seen, kept, dupes, artificial, shared, rejected };
}

/* zigzag varints over consecutive deltas */
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
    `  unique segments     ${r.kept}`,
    `    duplicates        ${r.dupes}`,
    `    artificial        ${r.artificial}`,
    r.shared ? `    already drawn       ${r.shared}` : null,
    r.rejected ? `    other layer         ${r.rejected}` : null,
    `  chains              ${r.chains.length}`,
    `  points              ${pts}`,
    `  ${out.padEnd(24)}${(bytes / 1048576).toFixed(2)} MB  (${(bytes / pts).toFixed(2)} bytes/point)`
  ].filter(Boolean).join('\n'));
}

/* ---- coastlines and land borders, split by occurrence count ---- */
const f0 = await source('ne_10m_admin_0_countries.geojson', 13);
const q0 = rings(f0);
const tal = tally(q0);

const rc = chainsOf(q0, null, k => tal.get(k).n === 1);
const bc = encode(rc.chains);
fs.writeFileSync(path.join(DATA, 'coastlines.bin'), bc);
report('coastlines (admin_0)', 'data/coastlines.bin', rc, bc.length);

const rb = chainsOf(q0, null, k => { const e = tal.get(k); return e.n > 1 && e.codes.size > 1; });
const bb = encode(rb.chains);
fs.writeFileSync(path.join(DATA, 'land_borders.bin'), bb);
report('land borders (admin_0)', 'data/land_borders.bin', rb, bb.length);

/* ---- subdivisions, subtracting every admin_0 segment ----
   Every segment admin_0 knows about, including the seams MERGE dropped and
   the artificial edges. What the country layer deliberately does not draw,
   the subdivision layer must not resurrect: otherwise merging Western
   Sahara into Morocco at admin_0 would just move its outline down a level. */
const drawn0 = new Set(tal.keys());

const f1 = await source('ne_10m_admin_1_states_provinces.geojson', 40);
const r1 = chainsOf(rings(f1), drawn0, null);
const b1 = encode(r1.chains);
fs.writeFileSync(path.join(DATA, 'subdivisions.bin'), b1);
report('subdivisions (admin_1)', 'data/subdivisions.bin', r1, b1.length);
