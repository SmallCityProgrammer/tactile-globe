/*
 * build.mjs — Natural Earth + GEBCO (read from the Tactile Globe repo, never
 * written to)  ->  data/pacific.json + data/fields.png
 *
 *   pacific.json  coastline rings of every land mass in the Pacific window,
 *                 projected to Mercator metres (origin 145°E on the equator),
 *                 tagged with their sovereign.
 *   fields.png    RGB raster of the window (90–200°E, 50°S–62°N at 1/12°,
 *                 ~9.3 km/cell):  R = depth in 50 m steps (0 on land),
 *                 G = distance to the nearest land in 10 km steps,
 *                 B = land elevation in 40 m steps (0 at sea).
 *
 * Longitudes run 0..360 EAST throughout, so the window is a single interval
 * that happens to cross the date line at 180.
 *
 * usage:  node tools/build.mjs            (expects ../../data, or MAPA_DATA=)
 */
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = process.env.MAPA_DATA || [path.resolve(ROOT, '..', '..', 'data'), path.resolve(ROOT, '..', 'Mapa', 'data')].find(p => fs.existsSync(path.join(p, 'ne_10m_admin_0_countries.geojson'))) || path.resolve(ROOT, '..', '..', 'data');
const DATA = path.join(ROOT, 'data');
fs.mkdirSync(DATA, { recursive: true });

/* ---------- projection: Mercator, metres, origin 145°E on the equator ----------
   A sea chart wants Mercator: a constant course is a straight line, which is how
   every track on this map was actually steamed. The price is that a "metre" here
   is a metre only on the equator — at latitude f it is 1/cos f too long — so the
   renderer divides by cosh(y/R) when it prints a distance. */
const R = 6378137, LON0 = 145;
const D2R = Math.PI / 180;
const merc = (lon, lat) => [R * (lon - LON0) * D2R, -R * Math.log(Math.tan(Math.PI / 4 + Math.max(-85, Math.min(85, lat)) * D2R / 2))];
const BB = { w: 78, e: 212, s: -50, n: 62 };      // the window, degrees east / north: Ceylon to Pearl Harbor
const DEG = 12;                                    // raster cells per degree (source is 1/60°)
const Q = 10;                                      // coast quantum, metres
const east = lon => (lon + 360) % 360;             // -180..180  ->  0..360

/* ---------- PNG reader: 8-bit greyscale or identity-palette, non-interlaced ---------- */
function readPNG(file) {
  const b = fs.readFileSync(file);
  let p = 8, W = 0, H = 0;
  const idat = [];
  while (p < b.length) {
    const len = b.readUInt32BE(p), type = b.subarray(p + 4, p + 8).toString('ascii');
    if (type === 'IHDR') {
      W = b.readUInt32BE(p + 8); H = b.readUInt32BE(p + 12);
      const bit = b[p + 16], ct = b[p + 17];
      if (bit !== 8 || (ct !== 0 && ct !== 3) || b[p + 20]) throw new Error('expected 8-bit grey or palette, non-interlaced');
    } else if (type === 'PLTE') {                  // fine as long as it is the identity grey ramp
      const pl = b.subarray(p + 8, p + 8 + len);
      for (let i = 0; i * 3 < pl.length; i++) if (pl[3 * i] !== i || pl[3 * i + 1] !== i || pl[3 * i + 2] !== i) throw new Error('palette is not the identity grey ramp');
    } else if (type === 'IDAT') idat.push(b.subarray(p + 8, p + 8 + len));
    p += 12 + len;
    if (type === 'IEND') break;
  }
  const raw = zlib.inflateSync(Buffer.concat(idat), { maxOutputLength: 4 * W * H + 1e6 });
  const img = Buffer.allocUnsafe(W * H);
  let prev = Buffer.alloc(W);
  for (let y = 0; y < H; y++) {
    const f = raw[y * (W + 1)];
    const src = raw.subarray(y * (W + 1) + 1, y * (W + 1) + 1 + W);
    const cur = img.subarray(y * W, y * W + W);
    for (let x = 0; x < W; x++) {
      const a = x ? cur[x - 1] : 0, up = prev[x], c = x ? prev[x - 1] : 0;
      let v = src[x];
      if (f === 1) v += a; else if (f === 2) v += up; else if (f === 3) v += (a + up) >> 1;
      else if (f === 4) { const pa = Math.abs(up - c), pb = Math.abs(a - c), pc = Math.abs(a + up - 2 * c); v += (pa <= pb && pa <= pc) ? a : (pb <= pc ? up : c); }
      cur[x] = v & 255;
    }
    prev = cur;
  }
  return { W, H, img };
}

/* ---------- PNG writer (8-bit RGB, "Up" filter on every row) ---------- */
const CRC = (() => { const t = new Int32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c; } return t; })();
function crc32(buf) { let r = 0xFFFFFFFF; for (let i = 0; i < buf.length; i++) r = CRC[(r ^ buf[i]) & 255] ^ (r >>> 8); return (r ^ 0xFFFFFFFF) >>> 0; }
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const c = Buffer.alloc(4); c.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, c]);
}
function writeRGB(w, h, px) {
  const stride = w * 3, rows = Buffer.allocUnsafe(h * (stride + 1));
  for (let y = 0; y < h; y++) {
    rows[y * (stride + 1)] = 2;
    for (let x = 0; x < stride; x++) rows[y * (stride + 1) + 1 + x] = (px[y * stride + x] - (y ? px[(y - 1) * stride + x] : 0)) & 255;
  }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(rows, { level: 9 })), chunk('IEND', Buffer.alloc(0))]);
}

/* ---------- vectors: every coastline ring that touches the window ----------
   Douglas-Peucker on a CLOSED ring needs a second anchor: with first == last the
   baseline has zero length, every deviation measures zero, and the whole island
   collapses to two coincident points. So the ring is cut at the vertex farthest
   from its first point and the two halves are simplified separately. */
function dpOpen(pts, a, b, tol, keep) {
  const stack = [[a, b]];
  while (stack.length) {
    const seg = stack.pop(), i0 = seg[0], i1 = seg[1];
    if (i1 - i0 < 2) continue;
    const ax = pts[i0][0], ay = pts[i0][1], bx = pts[i1][0], by = pts[i1][1];
    const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy);
    let worst = -1, wi = -1;
    for (let i = i0 + 1; i < i1; i++) {
      const px = pts[i][0], py = pts[i][1];
      const d = len > 1e-6 ? Math.abs((px - ax) * dy - (py - ay) * dx) / len : Math.hypot(px - ax, py - ay);
      if (d > worst) { worst = d; wi = i; }
    }
    if (worst > tol) { keep[wi] = 1; stack.push([i0, wi], [wi, i1]); }
  }
}
function dp(pts, tol) {
  const n = pts.length;
  if (n < 5) return pts;
  const keep = new Uint8Array(n); keep[0] = keep[n - 1] = 1;
  let far = 1, fd = -1;
  for (let i = 1; i < n - 1; i++) { const d = Math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]); if (d > fd) { fd = d; far = i; } }
  keep[far] = 1;
  dpOpen(pts, 0, far, tol, keep);
  dpOpen(pts, far, n - 1, tol, keep);
  const out = pts.filter((_, i) => keep[i]);
  return out.length < 4 ? pts.filter((_, i) => i % Math.ceil(n / 8) === 0 || i === n - 1) : out;
}

console.log('reading Natural Earth...');
const countries = JSON.parse(fs.readFileSync(path.join(SRC, 'ne_10m_admin_0_countries.geojson'), 'utf8'));
// who held each coast, roughly, for the political wash; anything unlisted is scenery
const SIDE = {
  Japan: 'jp', Taiwan: 'jp', 'South Korea': 'jp', 'North Korea': 'jp',
  Palau: 'jp', 'Marshall Islands': 'jp', 'Federated States of Micronesia': 'jp',
  'Northern Mariana Islands': 'jp', Vietnam: 'jp', Laos: 'jp', Cambodia: 'jp',
  'United States of America': 'us', Philippines: 'us', Guam: 'us',
  'American Samoa': 'us', 'United States Minor Outlying Islands': 'us',
  Australia: 'allied', 'New Zealand': 'allied', 'Papua New Guinea': 'allied',
  'Solomon Is.': 'allied', Vanuatu: 'allied', 'New Caledonia': 'allied', Fiji: 'allied',
  Indonesia: 'allied', Malaysia: 'allied', Singapore: 'allied', Brunei: 'allied',
  'Timor-Leste': 'allied', Myanmar: 'allied', India: 'allied', 'Sri Lanka': 'allied',
  Bangladesh: 'allied', 'Hong Kong': 'allied', Nauru: 'allied', Kiribati: 'allied',
  Tuvalu: 'allied', Tonga: 'allied', Samoa: 'allied', 'Wallis and Futuna Is.': 'allied',
  China: 'china', Thailand: 'neutral', Russia: 'neutral', Mongolia: 'neutral', Macao: 'neutral',
};
const rings = [];
let rawPts = 0, keptPts = 0;
for (const f of countries.features) {
  const adm = f.properties.ADMIN || f.properties.NAME;
  const side = SIDE[adm] || 'other';
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  for (const poly of polys) for (let ri = 0; ri < poly.length; ri++) {
    const r = poly[ri];
    let inside = false, minLon = 1e9, maxLon = -1e9, minLat = 1e9, maxLat = -1e9;
    const ll = [];
    for (const pt of r) {
      const E = east(pt[0]), la = pt[1];
      ll.push([E, la]);
      if (E < minLon) minLon = E;
      if (E > maxLon) maxLon = E;
      if (la < minLat) minLat = la;
      if (la > maxLat) maxLat = la;
      if (E >= BB.w && E <= BB.e && la >= BB.s && la <= BB.n) inside = true;
    }
    if (!inside) continue;
    if (maxLon - minLon > 180) continue;            // a ring the shift tore in half
    rawPts += ll.length;
    const xy = ll.map(q => merc(q[0], q[1]));
    const span = Math.max(maxLon - minLon, maxLat - minLat);
    // small islands keep every point: an atoll is four vertices wide to begin with.
    // No ring is ever dropped — the land mask below is an even-odd scanline over all
    // of them at once, and a missing ring flips the parity of everything east of it.
    const simp = span < 0.25 ? xy : dp(xy, span < 1 ? 40 : span < 6 ? 120 : 400);
    keptPts += simp.length;
    /* quantized to Q metres and delta-encoded: a coast is a walk of short steps, so
       the deltas are one or two digits where the absolutes are seven. Halves the file. */
    const flat = []; let px = 0, py = 0;
    for (const q of simp) {
      const X = Math.round(q[0] / Q), Y = Math.round(q[1] / Q);
      flat.push(X - px, Y - py); px = X; py = Y;
    }
    rings.push({ s: side, h: ri ? 1 : 0, ll, p: flat });   // h = hole (a lake inside the land)
  }
}
console.log(`  coast: ${rings.length} rings, ${rawPts} -> ${keptPts} points`);

/* ---------- rasters ---------- */
const W = Math.round((BB.e - BB.w) * DEG), H = Math.round((BB.n - BB.s) * DEG);
console.log(`window ${W}x${H} cells (1/${DEG} deg, ~${(111.32 / DEG).toFixed(1)} km)`);

const S = 60;                                       // source cells per degree
// box-average the source down to the map grid; the source x index wraps at the date line
function sample(src, invert) {
  const out = new Float32Array(W * H);
  const step = Math.round(S / DEG);                 // 5 source cells per map cell
  for (let y = 0; y < H; y++) {
    const sy0 = Math.round((90 - (BB.n - y / DEG)) * S);
    for (let x = 0; x < W; x++) {
      const sx0 = Math.round(((BB.w + x / DEG) + 180) * S);   // east longitudes: +180 then wrap
      let sum = 0, n = 0;
      for (let j = 0; j < step; j++) for (let i = 0; i < step; i++) {
        const sy = sy0 + j; if (sy < 0 || sy >= src.H) continue;
        const sx = (sx0 + i) % src.W;
        const v = src.img[sy * src.W + sx];
        sum += invert ? 255 - v : v; n++;
      }
      out[y * W + x] = n ? sum / n : 0;
    }
  }
  return out;
}
/* the two 21600x10800 sources take a minute to inflate, and nothing about them
   changes between runs, so the sampled windows are cached as raw Float32 */
function window(file, invert, label) {
  const cache = path.join(DATA, `.${label}-${W}x${H}.f32`);
  if (fs.existsSync(cache)) { console.log(`  ${label}: cached`); return new Float32Array(fs.readFileSync(cache).buffer.slice(0)); }
  console.log(`decoding ${label} (21600x10800)...`);
  const a = sample(readPNG(path.join(SRC, file)), invert);
  fs.writeFileSync(cache, Buffer.from(a.buffer));
  return a;
}
const elevU = window('elev_source.png', false, 'elevation');
const depthU = window('bath_source.png', true, 'bathymetry');   // shallow-high; inverted into a depth

/* the two NASA rasters carry no absolute scale, so calibrate against soundings
   that are not in dispute: Fuji, and the deeps of the western Pacific */
function at(lon, lat, a) {
  const x = Math.round((east(lon) - BB.w) * DEG), y = Math.round((BB.n - lat) * DEG);
  return a[Math.max(0, Math.min(H - 1, y)) * W + Math.max(0, Math.min(W - 1, x))];
}
const CAL = [[142.59, 11.37, 10920], [126.7, 10.4, 10540], [142.5, 36.1, 8000], [151.9, 6.1, 8000]];
let num = 0, den = 0;
for (const c of CAL) { const u = at(c[0], c[1], depthU); if (u > 4) { num += c[2] * u; den += u * u; } }
const M_PER_DEPTH = den ? num / den : 42;
const M_PER_ELEV = 3776 / Math.max(1, at(138.73, 35.36, elevU));
console.log(`  scales: ${M_PER_DEPTH.toFixed(1)} m per depth unit, ${M_PER_ELEV.toFixed(1)} m per elevation unit`);
for (const c of CAL) console.log(`    ${c[0]}E ${c[1]}N: ${(at(c[0], c[1], depthU) * M_PER_DEPTH).toFixed(0)} m vs ${c[2]} m`);

/* ---------- land mask on the map grid, scanline over the coast rings ---------- */
const land = new Uint8Array(W * H);
{
  const segs = [];   // DEBUG
  for (const r of rings) for (let i = 0, n = r.ll.length - 1; i < n; i++) segs.push([r.ll[i][0], r.ll[i][1], r.ll[i + 1][0], r.ll[i + 1][1]]);
  for (let y = 0; y < H; y++) {
    const lat = BB.n - (y + 0.5) / DEG, xs = [];
    for (const s of segs) if ((s[1] <= lat) !== (s[3] <= lat)) xs.push(s[0] + (lat - s[1]) / (s[3] - s[1]) * (s[2] - s[0]));
    xs.sort((a, b) => a - b);
    for (let k = 0; k + 1 < xs.length; k += 2) {
      const xa = Math.max(0, Math.ceil((xs[k] - BB.w) * DEG - 0.5)), xb = Math.min(W - 1, Math.floor((xs[k + 1] - BB.w) * DEG - 0.5));
      for (let x = xa; x <= xb; x++) land[y * W + x] = 1;       // even-odd: a lake ring falls between its coast crossings, so holes stay unfilled
    }
  }
}
let nl = 0; for (let i = 0; i < W * H; i++) if (land[i]) nl++;
console.log(`  land: ${(100 * nl / (W * H)).toFixed(1)}% of the window`);

/* ---------- distance to land (two-pass chamfer, cells) ---------- */
function chamfer(isZero) {
  const INF = 1e9, d = new Float32Array(W * H).fill(INF);
  for (let i = 0; i < W * H; i++) if (isZero(i)) d[i] = 0;
  const a = 1, b = Math.SQRT2;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x; let v = d[i];
    if (x) v = Math.min(v, d[i - 1] + a);
    if (y) { v = Math.min(v, d[i - W] + a); if (x) v = Math.min(v, d[i - W - 1] + b); if (x < W - 1) v = Math.min(v, d[i - W + 1] + b); }
    d[i] = v;
  }
  for (let y = H - 1; y >= 0; y--) for (let x = W - 1; x >= 0; x--) {
    const i = y * W + x; let v = d[i];
    if (x < W - 1) v = Math.min(v, d[i + 1] + a);
    if (y < H - 1) { v = Math.min(v, d[i + W] + a); if (x < W - 1) v = Math.min(v, d[i + W + 1] + b); if (x) v = Math.min(v, d[i + W - 1] + b); }
    d[i] = v;
  }
  return d;
}
const KM_CELL = 111.32 / DEG;                        // ~9.3 km, taken on the meridian
const dLand = chamfer(i => land[i]);

/* ---------- write ---------- */
const px = Buffer.allocUnsafe(W * H * 3);
for (let i = 0; i < W * H; i++) {
  px[3 * i] = land[i] ? 0 : Math.min(255, Math.round(depthU[i] * M_PER_DEPTH / 50));
  px[3 * i + 1] = Math.min(255, Math.round(dLand[i] * KM_CELL / 10));
  px[3 * i + 2] = land[i] ? Math.min(255, Math.max(1, Math.round(elevU[i] * M_PER_ELEV / 40))) : 0;
}
fs.writeFileSync(path.join(DATA, 'fields.png'), writeRGB(W, H, px));

const out = {
  proj: { R, LON0, BB },
  fields: { w: W, h: H, lon0: BB.w, lat0: BB.n, deg: DEG, depthStep: 50, landStep: 10, elevStep: 40 },
  q: Q,
  coast: rings.map(r => ({ s: r.s, h: r.h, p: r.p })),
};
fs.writeFileSync(path.join(DATA, 'pacific.json'), JSON.stringify(out));
console.log(`  data/pacific.json ${(fs.statSync(path.join(DATA, 'pacific.json')).size / 1048576).toFixed(2)} MB, data/fields.png ${(fs.statSync(path.join(DATA, 'fields.png')).size / 1024).toFixed(0)} KB`);
