/*
 * satellite.mjs — NASA Blue Marble  ->  data/satellite.jpg
 *
 * Blue Marble Next Generation, topography and bathymetry, December 2004.
 * Downloaded as published and embedded as published: the browser decodes
 * the JPEG natively, so there is nothing to transcode and no image codec
 * in this repository.
 *
 * NASA publishes this at two sizes and nothing in between: 5400x2700 and
 * 21600x10800. The larger one is 28.5 MB and exceeds the 16384 texture
 * limit most GPUs report, so it cannot be uploaded without downscaling or
 * splitting. This ships the smaller one, at 7.42 km per pixel.
 *
 * That is a whole-globe texture: it is at native resolution only when the
 * globe is small on screen, and the `satellite` style magnifies it from
 * there. Cubic reconstruction in the shader keeps that magnification from
 * ever looking like tiles, but it cannot invent detail the raster does not
 * carry.
 *
 * usage:  node tools/satellite.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data');
const URL_5400 = 'https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/world.topo.bathy.200412.3x5400x2700.jpg';
const OUT = path.join(DATA, 'satellite.jpg');

fs.mkdirSync(DATA, { recursive: true });

if (!fs.existsSync(OUT)) {
  console.log('downloading Blue Marble (~2.5 MB)...');
  const res = await fetch(URL_5400);
  if (!res.ok) throw new Error('download failed: HTTP ' + res.status);
  fs.writeFileSync(OUT, Buffer.from(await res.arrayBuffer()));
}

/* read the SOF marker back, so the report is the file's own word for it */
const b = fs.readFileSync(OUT);
let p = 2, w = 0, h = 0;
while (p < b.length - 1) {
  if (b[p] !== 0xFF) { p++; continue; }
  const m = b[p + 1];
  if (m >= 0xC0 && m <= 0xCF && m !== 0xC4 && m !== 0xC8 && m !== 0xCC) {
    h = b.readUInt16BE(p + 5); w = b.readUInt16BE(p + 7); break;
  }
  if (m === 0xD8 || m === 0x01 || (m >= 0xD0 && m <= 0xD7)) { p += 2; continue; }
  p += 2 + b.readUInt16BE(p + 2);
}

console.log([
  ``,
  `satellite`,
  `  size                ${w}x${h}   (~${(40075 / w).toFixed(2)} km/pixel at the equator)`,
  `  data/satellite.jpg  ${(b.length / 1048576).toFixed(2)} MB`
].join('\n'));
