/*
 * isobaths.mjs — Natural Earth 10m bathymetry  ->  data/isobaths.bin
 *
 * The depth contours, as lines. Natural Earth ships bathymetry as twelve
 * nested polygon bands (0 m down to -10000 m); the boundary of each band is
 * an isobath, and boundaries go straight through the line pipeline the
 * country borders already use. Filling the bands instead would need the
 * even-odd stencil machinery back, and would trade a continuous depth field
 * for twelve flat steps.
 *
 * Three things keep the size down:
 *
 *   - the 0 m band is skipped: that contour is the coastline, and the globe
 *     already draws it from admin_0
 *   - adjacent bands share the contour between them — the deeper band's
 *     outer ring is the shallower band's hole — so the same undirected
 *     segment key that de-duplicates country borders drops one of each pair
 *   - the chains are simplified on the way out. Bathymetry at 1:10m is
 *     already generalized and the sea floor is smooth; carrying vertices
 *     finer than the depth field justifies is paying for nothing
 *
 * Order matters: segments are de-duplicated while still at full precision
 * and only then simplified. The other way round, Douglas-Peucker run on each
 * ring separately would keep a different subset of vertices on each side of
 * a shared contour — the two copies would no longer match, nothing would
 * de-duplicate, and every shared contour would ship twice and draw twice.
 *
 * usage:  node tools/isobaths.mjs [tolerance-in-degrees]
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data');
const BASE = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/';
const OUT = path.join(DATA, 'isobaths.bin');

const Q = 1e6;                                  // 1e-6 degrees, ~11 cm
const SEAM = Math.round(180 * Q);
const NEAR_SEAM = Math.round(0.002 * Q);        // the cut is not always at exactly 180
const COLINEAR = Math.round(0.000002 * Q);
const POLAR = Math.round(89.5 * Q);
const MAXSEG = Math.round(1.0 * Q);             // longest segment a real contour may have
const TOL = Math.round((Number(process.argv[2]) || 0.010) * Q);

/* deepest first, so a shared contour is kept by the deeper of the two */
const BANDS = [10000, 9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000, 1000, 200];
const LETTER = 'ABCDEFGHIJK';
const LAYERS = BANDS.map((d, i) => `ne_10m_bathymetry_${LETTER[i]}_${d}`);

fs.mkdirSync(DATA, { recursive: true });

async function source(name) {
  const file = path.join(DATA, name + '.geojson');
  if (!fs.existsSync(file)) {
    process.stdout.write(`downloading ${name}... `);
    const res = await fetch(BASE + name + '.geojson');
    if (!res.ok) throw new Error(name + ': HTTP ' + res.status);
    const b = Buffer.from(await res.arrayBuffer());
    fs.writeFileSync(file, b);
    console.log(`${(b.length / 1048576).toFixed(2)} MB`);
  }
  return file;
}

/* Douglas-Peucker in quantized degrees, iterative so deep chains cannot
   blow the stack; endpoints are always kept, which is what lets chains be
   simplified independently without pulling apart at their junctions */
function simplify(q, tol) {
  const n = q.length / 2;
  if (n < 3) return q;
  const keep = new Uint8Array(n); keep[0] = 1; keep[n - 1] = 1;
  const st = [0, n - 1], t2 = tol * tol;
  while (st.length) {
    const j = st.pop(), i = st.pop();
    if (j - i < 2) continue;
    const ax = q[2 * i], ay = q[2 * i + 1];
    const dx = q[2 * j] - ax, dy = q[2 * j + 1] - ay;
    const dd = dx * dx + dy * dy;
    let best = -1, bi = -1;
    for (let k = i + 1; k < j; k++) {
      const px = q[2 * k] - ax, py = q[2 * k + 1] - ay;
      let d2;
      if (dd === 0) d2 = px * px + py * py;
      else {
        let t = (px * dx + py * dy) / dd; t = t < 0 ? 0 : t > 1 ? 1 : t;
        const ex = px - t * dx, ey = py - t * dy; d2 = ex * ex + ey * ey;
      }
      if (d2 > best) { best = d2; bi = k; }
    }
    if (best > t2) { keep[bi] = 1; st.push(i, bi, bi, j); }
  }
  const out = [];
  for (let k = 0; k < n; k++) if (keep[k]) out.push(q[2 * k], q[2 * k + 1]);
  return out;
}

const key = (ax, ay, bx, by) =>
  (ax < bx || (ax === bx && ay <= by))
    ? ax + ',' + ay + ',' + bx + ',' + by
    : bx + ',' + by + ',' + ax + ',' + ay;

const seen = new Set();
const chains = [];
let rawPts = 0, shared = 0, artificial = 0;

for (const name of LAYERS) {
  const gj = JSON.parse(fs.readFileSync(await source(name), 'utf8'));
  const rings = [];
  const push = r => {
    const q = [];
    let px = NaN, py = NaN;
    for (const c of r) {
      const x = Math.round(c[0] * Q), y = Math.round(c[1] * Q);
      if (x === px && y === py) continue;      // repeated vertex
      q.push(x, y); px = x; py = y;
    }
    rawPts += q.length / 2;
    if (q.length >= 6) rings.push(q);
  };
  for (const f of gj.features) {
    const g = f.geometry;
    if (!g) continue;
    if (g.type === 'Polygon') for (const r of g.coordinates) push(r);
    else if (g.type === 'MultiPolygon') for (const p of g.coordinates) for (const r of p) push(r);
  }

  /* Same treatment the borders get: drop the edges that are an artefact of
     cutting the globe into a rectangle — the antimeridian seam and the run
     along the bottom that closes a polygon round the south pole — then walk
     what is left into chains, breaking wherever a segment is dropped. */
  for (const r of rings) {
    const n = r.length / 2;
    let cur = null;
    for (let i = 0; i + 1 < n; i++) {
      const ax = r[2 * i], ay = r[2 * i + 1], bx = r[2 * i + 2], by = r[2 * i + 3];
      /* A seam edge runs straight up the antimeridian, but the cut is not
         always at exactly 180: these files place it at 179.999156 and at
         -179.999989 as well, so the test has to be a neighbourhood rather
         than an equality. A polar edge is the same thing along the top or
         bottom of the rectangle. */
      let ok = true;
      const onSeam = Math.abs(Math.abs(ax) - SEAM) <= NEAR_SEAM &&
                     Math.abs(Math.abs(bx) - SEAM) <= NEAR_SEAM &&
                     Math.abs(ax - bx) <= COLINEAR;
      if (onSeam || (ay <= -POLAR && by <= -POLAR) ||
          (ay >= POLAR && by >= POLAR)) { ok = false; artificial++; }
      else if (seen.has(key(ax, ay, bx, by))) { ok = false; shared++; }
      else seen.add(key(ax, ay, bx, by));
      if (ok) {
        if (!cur) { cur = [ax, ay]; chains.push(cur); }
        cur.push(bx, by);
      } else cur = null;
    }
  }
}

let before = 0;
for (const c of chains) before += c.length / 2;
for (let i = 0; i < chains.length; i++) chains[i] = simplify(chains[i], TOL);

/* The last artefact, and the one that only shows once the bands are drawn as
   lines. Where a band boundary is a construction edge rather than a measured
   contour — the straight run a clipped polygon closes itself with — Natural
   Earth still densifies it, laying evenly spaced points exactly on the line.
   One of them steps 17.6 degrees across the North Pacific in 36 collinear
   hops. Douglas-Peucker folds those back to the single straight segment they
   always were, which is correct and is what makes them visible: filled, the
   edge is interior to the band and cannot be seen; stroked, it is a ruled
   line across the ocean.
   What gives them away afterwards is their length. Surviving simplification
   at a kilometre means the source ran straight to within a kilometre over
   the whole span, and a 111 km contour segment that straight is not a
   contour. Cut there, and let the chain resume on the other side. */
let cutN = 0;
const split = [];
for (const c of chains) {
  let run = [c[0], c[1]];
  for (let i = 0; i + 3 < c.length; i += 2) {
    let dx = c[i + 2] - c[i];
    if (dx > SEAM) dx -= 2 * SEAM; else if (dx < -SEAM) dx += 2 * SEAM;
    const dy = c[i + 3] - c[i + 1];
    if (dx * dx + dy * dy > MAXSEG * MAXSEG) {
      cutN++;
      if (run.length >= 4) split.push(run);
      run = [c[i + 2], c[i + 3]];
    } else run.push(c[i + 2], c[i + 3]);
  }
  if (run.length >= 4) split.push(run);
}
chains.length = 0;
for (const c of split) chains.push(c);

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
    pushV(c[i] - lx); pushV(c[i + 1] - ly);
    lx = c[i]; ly = c[i + 1];
  }
}
const bin = Buffer.from(buf);
fs.writeFileSync(OUT, bin);

let pts = 0;
for (const c of chains) pts += c.length / 2;
console.log([
  ``,
  `isobaths  (${BANDS.length} bands, ${BANDS[BANDS.length - 1]} m to ${BANDS[0]} m; 0 m is the coastline and is skipped)`,
  `  source points       ${rawPts}`,
  `  shared contours     ${shared}   (segments carried by two bands, kept once)`,
  `  artificial edges    ${artificial}   (antimeridian seam, polar closure)`,
  `  construction edges  ${cutN}   (straight runs longer than ${(MAXSEG / Q).toFixed(1)} deg, cut)`,
  `  chains              ${chains.length}`,
  `  points              ${before} -> ${pts}   (Douglas-Peucker at ${(TOL / Q).toFixed(3)} deg, ~${Math.round(TOL / Q * 111000)} m)`,
  `  data/isobaths.bin   ${(bin.length / 1048576).toFixed(2)} MB   (${(bin.length / pts).toFixed(2)} bytes/point)`
].join('\n'));
