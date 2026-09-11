// sheet.mjs — slice a hand-drawn glyph sheet (PNG) into sprites for the map.
//   node tools/sheet.mjs grid <sheet.png>                      -> prints the detected rows/cells
//   node tools/sheet.mjs cut  <sheet.png> <map.json> [maxSide] -> writes data/sprites.json
// map.json: { name: [x0, x1, y0, y1, captionFrac?] } (explicit cell rect) or { name: [row, cell, captionFrac?] }
import fs from 'node:fs';
import zlib from 'node:zlib';
const SRC = process.argv[3];
if (!SRC) { console.error('usage: node tools/sheet.mjs grid|cut <sheet.png> [map.json] [maxSide]'); process.exit(1); }

function readPNG(file) {
  const b = fs.readFileSync(file); let p = 8, W, H, ct; const idat = [];
  while (p < b.length) { const len = b.readUInt32BE(p), type = b.toString('ascii', p + 4, p + 8); if (type === 'IHDR') { W = b.readUInt32BE(p + 8); H = b.readUInt32BE(p + 12); ct = b[p + 17]; if (b[p + 16] !== 8) throw new Error('bit depth'); } else if (type === 'IDAT') idat.push(b.subarray(p + 8, p + 8 + len)); p += 12 + len; if (type === 'IEND') break; }
  const bpp = ct === 6 ? 4 : ct === 2 ? 3 : ct === 0 ? 1 : null; if (!bpp) throw new Error('colour type ' + ct);
  const raw = zlib.inflateSync(Buffer.concat(idat)), stride = W * bpp, img = Buffer.alloc(W * H * bpp); let prev = Buffer.alloc(stride);
  for (let y = 0; y < H; y++) { const f = raw[y * (stride + 1)], src = raw.subarray(y * (stride + 1) + 1, y * (stride + 1) + 1 + stride), cur = img.subarray(y * stride, y * stride + stride);
    for (let x = 0; x < stride; x++) { const a = x >= bpp ? cur[x - bpp] : 0, up = prev[x], c = x >= bpp ? prev[x - bpp] : 0; let v = src[x]; if (f === 1) v += a; else if (f === 2) v += up; else if (f === 3) v += (a + up) >> 1; else if (f === 4) { const pa = Math.abs(up - c), pb = Math.abs(a - c), pc = Math.abs(a + up - 2 * c); v += (pa <= pb && pa <= pc) ? a : (pb <= pc ? up : c); } cur[x] = v & 255; }
    prev = cur; }
  return { W, H, bpp, img };
}
const CRC = (() => { const t = new Int32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c; } return t; })();
const crc32 = buf => { let r = 0xFFFFFFFF; for (let i = 0; i < buf.length; i++) r = CRC[(r ^ buf[i]) & 255] ^ (r >>> 8); return (r ^ 0xFFFFFFFF) >>> 0; };
const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type, 'ascii'), data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc32(td)); return Buffer.concat([len, td, c]); };
function writeRGBA(w, h, px) { const stride = w * 4, rows = Buffer.alloc(h * (stride + 1)); for (let y = 0; y < h; y++) { rows[y * (stride + 1)] = 2; for (let x = 0; x < stride; x++) rows[y * (stride + 1) + 1 + x] = (px[y * stride + x] - (y ? px[(y - 1) * stride + x] : 0)) & 255; } const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6; return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(rows, { level: 9 })), chunk('IEND', Buffer.alloc(0))]); }

const S = readPNG(SRC); const { W, H, bpp, img } = S;
const px = (x, y) => { const i = (y * W + x) * bpp; return [img[i], img[i + 1], img[i + 2]]; };
const isInk = (x, y) => { const [r, g, b] = px(x, y); const mn = Math.min(r, g, b), mx = Math.max(r, g, b); return mn < 200 || mx - mn > 45; };

/* grid: rows from long horizontal ink runs, cells from vertical runs inside each row band */
const mask = new Uint8Array(W * H); for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) mask[y * W + x] = isInk(x, y) ? 1 : 0;
const dark = (x, y) => { const q = px(x, y); return Math.min(q[0], q[1], q[2]) < 190; };
const rowDark = new Uint32Array(H); for (let y = 0; y < H; y++) { let n = 0; for (let x = 0; x < W; x++) if (dark(x, y)) n++; rowDark[y] = n; }
const groups = []; for (let y = 0; y < H; y++) if (rowDark[y] > 700) { if (groups.length && y - groups[groups.length - 1].y1 <= 2) groups[groups.length - 1].y1 = y; else groups.push({ y0: y, y1: y }); }
const lines = groups.filter(g => g.y1 - g.y0 <= 8);
const bands = []; for (let i = 0; i + 1 < lines.length; i++) { const a = (lines[i].y0 + lines[i].y1) / 2, b = (lines[i + 1].y0 + lines[i + 1].y1) / 2; if (b - a > 160 && b - a < 360) bands.push({ y0: Math.round(a), y1: Math.round(b) }); }
const rows = [];
for (const band of bands) {
  const hgt = band.y1 - band.y0, colDark = new Uint32Array(W);
  for (let x = 0; x < W; x++) { let n = 0; for (let y = band.y0 + 4; y <= band.y1 - 4; y++) if (dark(x, y)) n++; colDark[x] = n; }
  const g2 = []; for (let x = 0; x < W; x++) if (colDark[x] >= (hgt - 8) * 0.8) { if (g2.length && x - g2[g2.length - 1].x1 <= 2) g2[g2.length - 1].x1 = x; else g2.push({ x0: x, x1: x }); }
  const seps = g2.filter(g => g.x1 - g.x0 <= 8);
  const cells = []; for (let i = 0; i + 1 < seps.length; i++) { const a = seps[i].x1, b = seps[i + 1].x0; if (b - a > 140 && b - a < 1200) cells.push({ x0: a + 1, x1: b - 1, y0: band.y0 + 1, y1: band.y1 - 1 }); }
  rows.push({ band, cells });
}
if (process.argv[2] === 'grid') { rows.forEach((r, i) => console.log(`row ${i}: y ${r.band.y0}-${r.band.y1}  ${r.cells.length} cells: ` + r.cells.map(c => `${c.x0}-${c.x1}(${c.x1 - c.x0})`).join(' '))); process.exit(0); }

/* cut: map.json = { name: [row, cell], ... } ; optional 4th/5th entries: capFrac (caption cut) */
const MAP = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
const MAXSIDE = +(process.argv[5] || 192);
const out = {};
for (const name in MAP) {
  const m = MAP[name]; let c, capFrac;
  if (m.length >= 4) { c = { x0: m[0], x1: m[1], y0: m[2], y1: m[3] }; capFrac = m[4]; } else { c = rows[m[0]].cells[m[1]]; capFrac = m[2]; }
  if (!c) { console.error('no cell', name, m); continue; }
  const inset = 6, gx0 = c.x0 + inset, gx1 = c.x1 - inset, gy0 = c.y0 + inset, gy1 = Math.round(c.y0 + (c.y1 - c.y0) * (1 - (capFrac == null ? 0.2 : capFrac)));
  // paper colour: mean of light, unsaturated pixels in the zone
  let pr = 0, pg = 0, pb = 0, pn = 0;
  for (let y = gy0; y < gy1; y += 2) for (let x = gx0; x < gx1; x += 2) { const [r, g, b] = px(x, y); if (Math.min(r, g, b) > 205 && Math.max(r, g, b) - Math.min(r, g, b) < 30) { pr += r; pg += g; pb += b; pn++; } }
  if (!pn) { console.error('no paper in', name); continue; } pr /= pn; pg /= pn; pb /= pn;
  const w = gx1 - gx0, h = gy1 - gy0, rgba = Buffer.alloc(w * h * 4);
  let bx0 = w, by0 = h, bx1 = -1, by1 = -1;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const [r, g, b] = px(gx0 + x, gy0 + y); const d = Math.max(Math.abs(r - pr), Math.abs(g - pg), Math.abs(b - pb));
    let a = Math.min(1, Math.max(0, (d - 16) / 70)); if (a <= 0) continue;
    // un-mix the paper out of the edge pixels
    const rr = a > 0.999 ? r : Math.min(255, Math.max(0, (r - (1 - a) * pr) / a)), gg = a > 0.999 ? g : Math.min(255, Math.max(0, (g - (1 - a) * pg) / a)), bb = a > 0.999 ? b : Math.min(255, Math.max(0, (b - (1 - a) * pb) / a));
    const i = (y * w + x) * 4; rgba[i] = rr; rgba[i + 1] = gg; rgba[i + 2] = bb; rgba[i + 3] = Math.round(a * 255);
    if (a > 0.12) { if (x < bx0) bx0 = x; if (x > bx1) bx1 = x; if (y < by0) by0 = y; if (y > by1) by1 = y; }
  }
  if (bx1 < 0) { console.error('empty', name); continue; }
  // crop (2 px margin) and downscale with box filter to MAXSIDE
  bx0 = Math.max(0, bx0 - 2); by0 = Math.max(0, by0 - 2); bx1 = Math.min(w - 1, bx1 + 2); by1 = Math.min(h - 1, by1 + 2);
  const cw = bx1 - bx0 + 1, ch = by1 - by0 + 1, k = Math.max(1, Math.ceil(Math.max(cw, ch) / MAXSIDE)), ow = Math.ceil(cw / k), oh = Math.ceil(ch / k), o = Buffer.alloc(ow * oh * 4);
  for (let y = 0; y < oh; y++) for (let x = 0; x < ow; x++) { let r = 0, g = 0, b = 0, a = 0, n = 0; for (let j = 0; j < k; j++) for (let i = 0; i < k; i++) { const sx = bx0 + x * k + i, sy = by0 + y * k + j; if (sx > bx1 || sy > by1) continue; const q = (sy * w + sx) * 4, al = rgba[q + 3]; r += rgba[q] * al; g += rgba[q + 1] * al; b += rgba[q + 2] * al; a += al; n++; } const t = (y * ow + x) * 4; if (a) { o[t] = r / a; o[t + 1] = g / a; o[t + 2] = b / a; o[t + 3] = a / n; } }
  out[name] = { w: ow, h: oh, b64: writeRGBA(ow, oh, o).toString('base64') };
  console.log(name.padEnd(18), `${c.x0}-${c.x1} ${c.y0}-${c.y1} -> ${ow}x${oh}`);
}
// merge into the existing set: sprites from several sheets live together, the same key overwrites
const outFile = new URL('../data/sprites.json', import.meta.url);
let prev = {}; try { prev = JSON.parse(fs.readFileSync(outFile, 'utf8')); } catch (e) { prev = {}; }
const all = Object.assign(prev, out);
fs.writeFileSync(outFile, JSON.stringify(all));
let total = 0; for (const n in all) total += all[n].b64.length; console.log(`data/sprites.json: ${Object.keys(out).length} written, ${Object.keys(all).length} total, ${(total / 1024).toFixed(0)} KB base64`);
