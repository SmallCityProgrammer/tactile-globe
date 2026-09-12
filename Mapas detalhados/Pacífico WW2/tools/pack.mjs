/*
 * pack.mjs — src/template.html + data/  ->  pacifico.html
 *
 * One file, no external requests: opens from file:// by double-click.
 *
 *   data/pacific.json   coast rings + the fields metadata   (tools/build.mjs)
 *   data/history.json   battles, bases, routes, ships, ...  (tools/history.mjs)
 *   data/fields.png     depth / distance to land / elevation
 *   data/assets.json    optional: a PNG per asset id, exported from the
 *                       "assets" page of the map itself
 *
 * usage:  node tools/pack.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TPL = path.join(ROOT, 'src', 'template.html');
const OUT = path.join(ROOT, 'pacifico.html');
const D = f => path.join(ROOT, 'data', f);

let out = fs.readFileSync(TPL, 'utf8');
const json = f => fs.readFileSync(D(f), 'utf8').replace(/<\//g, '<\\/');
const assetsFile = D('assets.json');
const assets = fs.existsSync(assetsFile) ? fs.readFileSync(assetsFile, 'utf8').replace(/<\//g, '<\\/') : '{}';

for (const [marker, value] of [
  ['__PACIFIC_JSON__', json('pacific.json')],
  ['__HISTORY_JSON__', json('history.json')],
  ['__FIELDS_B64__', fs.readFileSync(D('fields.png')).toString('base64')],
  ['__SPRITES_JSON__', assets],
]) {
  if (!out.includes(marker)) { console.error(`template has no ${marker}`); process.exit(1); }
  out = out.replace(marker, () => value);
}
new Function(out.match(/<script>\n([\s\S]*?)<\/script>/)[1]);   // the embedded JS must parse
fs.writeFileSync(OUT, out, 'utf8');
// assets.html: opens the same file straight into the asset sheet
fs.writeFileSync(path.join(ROOT, 'assets.html'), '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=pacifico.html#assets"><title>assets</title><a href="pacifico.html#assets">pacifico.html#assets</a>\n', 'utf8');
const n = Object.keys(JSON.parse(assets)).length;
console.log(`pacifico.html  ${(out.length / 1048576).toFixed(2)} MB  (${n} assets embutidos, + assets.html)`);
