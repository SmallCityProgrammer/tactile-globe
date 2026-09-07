/*
 * pack.mjs — src/template.html + data/borders.bin  ->  globo.html
 *
 * Embute o binario como base64 dentro de uma tag <script type="application/
 * octet-stream">. O alfabeto base64 nao contem '<', entao nao ha como o
 * conteudo fechar a tag por acidente.
 *
 * O resultado e um unico arquivo, sem nenhuma requisicao externa — abre
 * direto por file:// sem servidor.
 *
 * uso:  node tools/pack.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TPL = path.join(ROOT, 'src', 'template.html');
const BINS = [
  ['__DATA_B64__',  path.join(ROOT, 'data', 'borders.bin')],
  ['__DATA2_B64__', path.join(ROOT, 'data', 'subdivisions.bin')]
];
const OUT = path.join(ROOT, 'globo.html');

let out = fs.readFileSync(TPL, 'utf8');
let dados = 0;

for (const [marker, file] of BINS) {
  if (!fs.existsSync(file)) {
    console.error(`${path.relative(ROOT, file)} nao existe — rode antes:  node tools/build.mjs`);
    process.exit(1);
  }
  if (!out.includes(marker)) {
    console.error(`src/template.html nao tem o marcador ${marker}`);
    process.exit(1);
  }
  const b64 = fs.readFileSync(file).toString('base64');
  dados += b64.length;
  out = out.replace(marker, b64);
}

// checagem: o JS embutido tem que ser sintaticamente valido
new Function(out.match(/<script>\n([\s\S]*)<\/script>/)[1]);

fs.writeFileSync(OUT, out, 'utf8');
console.log(`globo.html  ${(out.length / 1048576).toFixed(2)} MB  (dados: ${(dados / 1048576).toFixed(2)} MB base64)`);
