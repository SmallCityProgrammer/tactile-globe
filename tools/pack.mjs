/*
 * pack.mjs — src/template.html + data/*.bin  ->  globo.html
 *
 * Embeds each binary as base64 inside a <script type="application/octet-
 * stream"> tag. The base64 alphabet has no '<', so the payload cannot close
 * the tag by accident.
 *
 * The result is a single file with no external requests — it opens straight
 * from file:// with no server.
 *
 * usage:  node tools/pack.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TPL = path.join(ROOT, 'src', 'template.html');
const BINS = [
  ['__DATA_B64__',  path.join(ROOT, 'data', 'coastlines.bin')],
  ['__DATA2_B64__', path.join(ROOT, 'data', 'subdivisions.bin')],
  ['__DATA5_B64__', path.join(ROOT, 'data', 'land_borders.bin')],
  ['__RELIEF_B64__', path.join(ROOT, 'data', 'relief.png')]
];
const OUT = path.join(ROOT, 'globo.html');

let out = fs.readFileSync(TPL, 'utf8');
let dados = 0;

for (const [marker, file] of BINS) {
  if (!fs.existsSync(file)) {
    console.error(`${path.relative(ROOT, file)} is missing — run first:  node tools/build.mjs`);
    process.exit(1);
  }
  if (!out.includes(marker)) {
    console.error(`src/template.html has no placeholder ${marker}`);
    process.exit(1);
  }
  const b64 = fs.readFileSync(file).toString('base64');
  dados += b64.length;
  out = out.replace(marker, b64);
}

// sanity check: the embedded JS must parse
new Function(out.match(/<script>\n([\s\S]*)<\/script>/)[1]);

fs.writeFileSync(OUT, out, 'utf8');
console.log(`globo.html  ${(out.length / 1048576).toFixed(2)} MB  (data: ${(dados / 1048576).toFixed(2)} MB base64)`);
