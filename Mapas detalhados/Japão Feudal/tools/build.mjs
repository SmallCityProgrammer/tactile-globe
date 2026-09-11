/*
 * build.mjs — Natural Earth + GEBCO (read from the Tactile Globe repo, never
 * written to)  ->  data/japan.json + data/fields.png
 *
 *   japan.json   coastline rings and prefecture rings, projected to a local
 *                equirectangular grid in metres (origin 137°E 36°N), plus
 *                rivers traced by flow accumulation over the elevation raster.
 *   fields.png   RGB raster of the Japan window (128–147°E, 30–46°N at
 *                1/60°, ~1.85 km/px): R = elevation (GEBCO 8-bit units),
 *                G = distance to the sea in km (0 = sea), B = distance to
 *                the nearest traced river in km.
 *
 * usage:  node tools/build.mjs            (expects ../Mapa/data, or MAPA_DATA=)
 */
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
// the Natural Earth / GEBCO sources: the globe repo's data/ two levels up (this folder lives in
// Mapas detalhados/Japão Feudal), a sibling Mapa/ checkout, or MAPA_DATA=
const SRC = process.env.MAPA_DATA || [path.resolve(ROOT, '..', '..', 'data'), path.resolve(ROOT, '..', 'Mapa', 'data')].find(p => fs.existsSync(path.join(p, 'ne_10m_admin_0_countries.geojson'))) || path.resolve(ROOT, '..', '..', 'data');
const DATA = path.join(ROOT, 'data');
fs.mkdirSync(DATA, { recursive: true });

/* ---------- projection ---------- */
const LON0 = 137, LAT0 = 36, M = 111320;
const KX = Math.round(M * Math.cos(LAT0 * Math.PI / 180));   // metres per degree of longitude at 36°N
const BB = { w: 128, e: 147, s: 30, n: 46 };                 // the window, degrees
const DEG = 60;                                              // raster cells per degree (source is 1/60°)
const proj = (lon, lat) => [Math.round((lon - LON0) * KX), Math.round(-(lat - LAT0) * M)];

/* ---------- vectors ---------- */
function ringsOf(geom) {
  const polys = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;
  const out = [], ll = [];
  for (const p of polys) for (const r of p) {
    let inside = false;
    for (const [x, y] of r) if (x >= BB.w && x <= BB.e && y >= BB.s && y <= BB.n) { inside = true; break; }
    if (!inside) continue;
    const flat = [];
    for (const [x, y] of r) { const [X, Y] = proj(x, y); flat.push(X, Y); }
    out.push(flat); ll.push(r);
  }
  return { proj: out, ll };
}

console.log('reading Natural Earth...');
const countries = JSON.parse(fs.readFileSync(path.join(SRC, 'ne_10m_admin_0_countries.geojson'), 'utf8'));
const japan = countries.features.find(f => f.properties.ADMIN === 'Japan');
const coast = ringsOf(japan.geometry);
let coastPts = 0; for (const r of coast.proj) coastPts += r.length / 2;
console.log(`  coast: ${coast.proj.length} rings, ${coastPts} points`);

const admin1 = JSON.parse(fs.readFileSync(path.join(SRC, 'ne_10m_admin_1_states_provinces.geojson'), 'utf8'));
const prefs = admin1.features.filter(f => f.properties.adm0_a3 === 'JPN').map(f => {
  const r = ringsOf(f.geometry);
  return { name: f.properties.name, ja: f.properties.name_local, region: f.properties.region, rings: r.proj };
}).filter(p => p.rings.length);
console.log(`  prefectures: ${prefs.length}`);

/* ---------- PNG reader (8-bit grey, non-interlaced) — same as the globe's ---------- */
function readPNG(file) {
  const b = fs.readFileSync(file);
  let p = 8, W = 0, H = 0;
  const idat = [];
  while (p < b.length) {
    const len = b.readUInt32BE(p), type = b.subarray(p + 4, p + 8).toString('ascii');
    if (type === 'IHDR') { W = b.readUInt32BE(p + 8); H = b.readUInt32BE(p + 12); }
    else if (type === 'IDAT') idat.push(b.subarray(p + 8, p + 8 + len));
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

/* ---------- elevation window ---------- */
console.log('decoding elevation (21600x10800, takes a moment)...');
const src = readPNG(path.join(SRC, 'elev_source.png'));
const X0 = Math.round((BB.w + 180) * DEG), X1 = Math.round((BB.e + 180) * DEG);
const Y0 = Math.round((90 - BB.n) * DEG), Y1 = Math.round((90 - BB.s) * DEG);
const W = X1 - X0, H = Y1 - Y0;
const elev = new Uint8Array(W * H);
let emax = 0;
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const v = src.img[(Y0 + y) * src.W + X0 + x]; elev[y * W + x] = v; if (v > emax) emax = v; }
console.log(`  window ${W}x${H}, max elevation unit ${emax}`);

/* ---------- land mask on the same grid, from the coast rings (even-odd scanline) ---------- */
const land = new Uint8Array(W * H);
{
  const cellLat = y => BB.n - (y + 0.5) / DEG;
  for (let y = 0; y < H; y++) {
    const lat = cellLat(y), xs = [];
    for (const r of coast.ll) for (let i = 0, n = r.length - 1; i < n; i++) {
      const [ax, ay] = r[i], [bx, by] = r[i + 1];
      if ((ay <= lat) !== (by <= lat)) xs.push(ax + (lat - ay) / (by - ay) * (bx - ax));
    }
    xs.sort((a, b) => a - b);
    for (let k = 0; k + 1 < xs.length; k += 2) {
      const xa = Math.max(0, Math.ceil((xs[k] - BB.w) * DEG - 0.5)), xb = Math.min(W - 1, Math.floor((xs[k + 1] - BB.w) * DEG - 0.5));
      for (let x = xa; x <= xb; x++) land[y * W + x] = 1;
    }
  }
}

/* ---------- distance transform (two-pass chamfer, in cells) ---------- */
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
const KM = (111.32 * Math.cos(38 * Math.PI / 180) + 111.32) / 2 / DEG;   // ~1.66 km per cell, mean of both axes
const dSea = chamfer(i => !land[i]);

/* ---------- rivers: priority-flood fill, D8 flow, accumulation, tracing ---------- */
console.log('tracing rivers...');
const filled = new Float32Array(W * H);
{
  const hk = [], hi = [];
  const push = (k, i) => { hk.push(k); hi.push(i); let c = hk.length - 1; while (c) { const p = (c - 1) >> 1; if (hk[p] <= hk[c]) break; [hk[p], hk[c]] = [hk[c], hk[p]]; [hi[p], hi[c]] = [hi[c], hi[p]]; c = p; } };
  const pop = () => {
    const k = hk[0], i = hi[0]; const lk = hk.pop(), li = hi.pop();
    if (hk.length) { hk[0] = lk; hi[0] = li; let c = 0; for (;;) { const l = 2 * c + 1, r = l + 1; let m = c; if (l < hk.length && hk[l] < hk[m]) m = l; if (r < hk.length && hk[r] < hk[m]) m = r; if (m === c) break; [hk[m], hk[c]] = [hk[c], hk[m]]; [hi[m], hi[c]] = [hi[c], hi[m]]; c = m; } }
    return [k, i];
  };
  const seen = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) if (!land[i]) { filled[i] = 0; seen[i] = 1; push(0, i); }
  while (hk.length) {
    const [k, i] = pop(); const x = i % W, y = (i / W) | 0;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      if (!dx && !dy) continue; const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
      const j = ny * W + nx; if (seen[j]) continue; seen[j] = 1;
      filled[j] = Math.max(elev[j], k + 1e-3); push(filled[j], j);
    }
  }
}
const flow = new Int32Array(W * H).fill(-1);
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
  const i = y * W + x; if (!land[i]) continue; let best = -1, bd = 0;
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
    if (!dx && !dy) continue; const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
    const j = ny * W + nx, drop = (filled[i] - filled[j]) / (dx && dy ? Math.SQRT2 : 1);
    if (drop > bd) { bd = drop; best = j; }
  }
  flow[i] = best;
}
const order = []; for (let i = 0; i < W * H; i++) if (land[i]) order.push(i);
order.sort((a, b) => filled[b] - filled[a]);
const acc = new Float32Array(W * H).fill(1);
for (const i of order) if (flow[i] >= 0) acc[flow[i]] += acc[i];
const T = 45;                                                 // cells ≈ 125 km² of catchment
const isRiver = new Uint8Array(W * H); let nr = 0;
for (let i = 0; i < W * H; i++) if (land[i] && acc[i] >= T) { isRiver[i] = 1; nr++; }
const inflow = new Uint8Array(W * H);
for (let i = 0; i < W * H; i++) if (isRiver[i] && flow[i] >= 0) inflow[flow[i]] = 1;
const rivers = []; const taken = new Uint8Array(W * H);
const cellXY = i => proj(BB.w + (i % W + 0.5) / DEG, BB.n - (((i / W) | 0) + 0.5) / DEG);
for (let s = 0; s < W * H; s++) {
  if (!isRiver[s] || inflow[s]) continue;
  const pts = []; let i = s, maxAcc = acc[s];
  while (i >= 0 && land[i]) { pts.push(cellXY(i)); maxAcc = Math.max(maxAcc, acc[i]); if (taken[i]) break; taken[i] = 1; i = flow[i]; }
  if (i >= 0 && !land[i]) pts.push(cellXY(i));
  if (pts.length < 4) continue;
  let q = pts;
  for (let it = 0; it < 2; it++) {
    const o = [q[0]];
    for (let k = 0; k + 1 < q.length; k++) { const [ax, ay] = q[k], [bx, by] = q[k + 1]; o.push([ax * 0.75 + bx * 0.25, ay * 0.75 + by * 0.25], [ax * 0.25 + bx * 0.75, ay * 0.25 + by * 0.75]); }
    o.push(q[q.length - 1]); q = o;
  }
  const flat = []; for (const [x, y] of q) flat.push(Math.round(x), Math.round(y));
  rivers.push({ w: Math.round(Math.log2(maxAcc / T) * 10) / 10, pts: flat });
}
console.log(`  ${nr} river cells, ${rivers.length} polylines`);
const dRiver = chamfer(i => isRiver[i]);

/* ---------- write ---------- */
const px = Buffer.allocUnsafe(W * H * 3);
for (let i = 0; i < W * H; i++) {
  px[3 * i] = elev[i];
  px[3 * i + 1] = land[i] ? Math.min(255, Math.max(1, Math.round(dSea[i] * KM))) : 0;
  px[3 * i + 2] = Math.min(255, Math.round(dRiver[i] * KM));
}
fs.writeFileSync(path.join(DATA, 'fields.png'), writeRGB(W, H, px));
const out = {
  proj: { LON0, LAT0, M, KX }, bbox: BB,
  fields: { w: W, h: H, lon0: BB.w, lat0: BB.n, deg: DEG, emax },
  coast: coast.proj, prefs, rivers
};
fs.writeFileSync(path.join(DATA, 'japan.json'), JSON.stringify(out));
console.log(`  data/japan.json ${(fs.statSync(path.join(DATA, 'japan.json')).size / 1024).toFixed(0)} KB, data/fields.png ${(fs.statSync(path.join(DATA, 'fields.png')).size / 1024).toFixed(0)} KB`);
