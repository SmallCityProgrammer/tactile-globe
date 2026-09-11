/*
 * pack.mjs — src/template.html + data/japan.json + data/fields.png  ->  japao.html
 *
 * One file, no external requests: opens from file:// by double-click.
 *
 * usage:  node tools/pack.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TPL = path.join(ROOT, 'src', 'template.html');
const OUT = path.join(ROOT, 'japao.html');

let out = fs.readFileSync(TPL, 'utf8');
const json = fs.readFileSync(path.join(ROOT, 'data', 'japan.json'), 'utf8');
const png = fs.readFileSync(path.join(ROOT, 'data', 'fields.png')).toString('base64');
const spritesFile = path.join(ROOT, 'data', 'sprites.json');
const sprites = fs.existsSync(spritesFile) ? fs.readFileSync(spritesFile, 'utf8') : '{}';
for (const [marker, value] of [['__JAPAN_JSON__', json.replace(/<\//g, '<\\/')], ['__FIELDS_B64__', png], ['__SPRITES_JSON__', sprites]]) {
  if (!out.includes(marker)) { console.error(`template has no ${marker}`); process.exit(1); }
  out = out.replace(marker, () => value);
}
new Function(out.match(/<script>\n([\s\S]*?)<\/script>/)[1]);   // the embedded JS must parse
fs.writeFileSync(OUT, out, 'utf8');
// glifos.html: opens the same file straight into the glyph catalogue
fs.writeFileSync(path.join(ROOT, 'glifos.html'), '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=japao.html#glifos"><title>glifos</title><a href="japao.html#glifos">japao.html#glifos</a>\n', 'utf8');
console.log(`japao.html  ${(out.length / 1048576).toFixed(2)} MB  (+ glifos.html)`);
