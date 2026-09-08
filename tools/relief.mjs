/*
 * relief.mjs — global elevation  ->  data/relief.png
 *
 * Source: NASA Visible Earth's GEBCO-derived elevation raster, 21600x10800
 * 8-bit greyscale, equirectangular. Its encoding is convenient: 0 is sea
 * level and everything below it, so the ocean is already flat and no land
 * mask is needed — 67% of the image is a constant, which is also why the
 * output compresses as well as it does.
 *
 * Downsampled 4x by box average to 5400x2700 (~7.4 km/pixel), which is the
 * scale at which continental relief actually reads. The average also
 * recovers sub-step precision from the source's coarse 8-bit quantization.
 *
 * Written back out as a greyscale PNG so the browser decodes it natively,
 * with no JavaScript decoder and no extra dependency here: zlib ships with
 * Node, and the rest is a few hundred lines of chunk plumbing.
 *
 * usage:  node tools/relief.mjs
 */
import fs from 'fs';
import path from 'path';
import zlib from 'zlib';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data');
const SRC_URL = 'https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73934/gebco_08_rev_elev_21600x10800.png';
const SRC = path.join(DATA, 'elev_source.png');
const OUT = path.join(DATA, 'relief.png');
const FACTOR = 4;                     // 21600x10800 -> 5400x2700

fs.mkdirSync(DATA, { recursive: true });

if (!fs.existsSync(SRC)) {
  console.log('downloading global elevation (~18 MB)...');
  const res = await fetch(SRC_URL);
  if (!res.ok) throw new Error('download failed: HTTP ' + res.status);
  fs.writeFileSync(SRC, Buffer.from(await res.arrayBuffer()));
}

/* ---------- minimal PNG reader: 8-bit greyscale, non-interlaced ---------- */
function readPNG(file) {
  const b = fs.readFileSync(file);
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (!b.subarray(0, 8).equals(sig)) throw new Error('not a PNG');

  let p = 8, W = 0, H = 0;
  const idat = [];
  while (p < b.length) {
    const len = b.readUInt32BE(p), type = b.subarray(p + 4, p + 8).toString('ascii');
    if (type === 'IHDR') {
      W = b.readUInt32BE(p + 8); H = b.readUInt32BE(p + 12);
      if (b[p + 16] !== 8 || b[p + 17] !== 0 || b[p + 20] !== 0)
        throw new Error('expected 8-bit greyscale, non-interlaced');
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
      if (f === 1) v += a;
      else if (f === 2) v += up;
      else if (f === 3) v += (a + up) >> 1;
      else if (f === 4) {
        const pa = Math.abs(up - c), pb = Math.abs(a - c), pc = Math.abs(a + up - 2 * c);
        v += (pa <= pb && pa <= pc) ? a : (pb <= pc ? up : c);
      }
      cur[x] = v & 255;
    }
    prev = cur;
  }
  return { W, H, img };
}

/* ---------- minimal PNG writer: 8-bit greyscale ---------- */
const CRC = (() => {
  const t = new Int32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c;
  }
  return t;
})();

function crc32(buf) {
  let r = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) r = CRC[(r ^ buf[i]) & 255] ^ (r >>> 8);
  return (r ^ 0xFFFFFFFF) >>> 0;
}

function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const c = Buffer.alloc(4); c.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, c]);
}

/* per-row filter choice by the usual minimum-sum-of-absolute-differences */
function writePNG(w, h, px) {
  const rows = Buffer.allocUnsafe(h * (w + 1));
  const cand = [0, 1, 2, 3, 4].map(() => Buffer.allocUnsafe(w));
  let prev = Buffer.alloc(w);
  for (let y = 0; y < h; y++) {
    const cur = px.subarray(y * w, y * w + w);
    let bestF = 0, bestS = Infinity;
    for (let f = 0; f < 5; f++) {
      const o = cand[f];
      let s = 0;
      for (let x = 0; x < w; x++) {
        const a = x ? cur[x - 1] : 0, up = prev[x], c = x ? prev[x - 1] : 0;
        let v;
        if (f === 0) v = cur[x];
        else if (f === 1) v = cur[x] - a;
        else if (f === 2) v = cur[x] - up;
        else if (f === 3) v = cur[x] - ((a + up) >> 1);
        else {
          const pa = Math.abs(up - c), pb = Math.abs(a - c), pc = Math.abs(a + up - 2 * c);
          v = cur[x] - ((pa <= pb && pa <= pc) ? a : (pb <= pc ? up : c));
        }
        o[x] = v & 255;
        s += Math.min(o[x], 256 - o[x]);
      }
      if (s < bestS) { bestS = s; bestF = f; }
    }
    rows[y * (w + 1)] = bestF;
    cand[bestF].copy(rows, y * (w + 1) + 1);
    prev = cur;
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; ihdr[9] = 0; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(rows, { level: 9 })),
    chunk('IEND', Buffer.alloc(0))
  ]);
}

/* ---------- run ---------- */
console.log('decoding source...');
const { W, H, img } = readPNG(SRC);

const w = W / FACTOR, h = H / FACTOR;
if (!Number.isInteger(w) || !Number.isInteger(h)) throw new Error('FACTOR must divide the source');

console.log(`downsampling ${W}x${H} -> ${w}x${h}...`);
const out = Buffer.allocUnsafe(w * h);
const n2 = FACTOR * FACTOR;
for (let y = 0; y < h; y++) {
  for (let x = 0; x < w; x++) {
    let s = 0;
    for (let j = 0; j < FACTOR; j++) {
      const row = (y * FACTOR + j) * W;
      for (let i = 0; i < FACTOR; i++) s += img[row + x * FACTOR + i];
    }
    out[y * w + x] = Math.round(s / n2);
  }
}

const png = writePNG(w, h, out);
fs.writeFileSync(OUT, png);

let land = 0;
for (let i = 0; i < out.length; i++) if (out[i] > 0) land++;
console.log([
  ``,
  `relief`,
  `  size                ${w}x${h}   (~${(40075 / w).toFixed(1)} km/pixel at the equator)`,
  `  above sea level     ${(100 * land / out.length).toFixed(1)}%`,
  `  data/relief.png     ${(png.length / 1048576).toFixed(2)} MB`
].join('\n'));
