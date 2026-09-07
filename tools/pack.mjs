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
const BIN = path.join(ROOT, 'data', 'borders.bin');
const OUT = path.join(ROOT, 'globo.html');

if (!fs.existsSync(BIN)) {
  console.error('data/borders.bin nao existe — rode antes:  node tools/build.mjs');
  process.exit(1);
}

const tpl = fs.readFileSync(TPL, 'utf8');
if (!tpl.includes('__DATA_B64__')) {
  console.error('src/template.html nao tem o marcador __DATA_B64__');
  process.exit(1);
}

const b64 = fs.readFileSync(BIN).toString('base64');
const out = tpl.replace('__DATA_B64__', b64);

// checagem: o JS embutido tem que ser sintaticamente valido
new Function(out.match(/<script>\n([\s\S]*)<\/script>/)[1]);

fs.writeFileSync(OUT, out, 'utf8');
console.log(`globo.html  ${(out.length / 1048576).toFixed(2)} MB  (dados: ${(b64.length / 1048576).toFixed(2)} MB base64)`);
