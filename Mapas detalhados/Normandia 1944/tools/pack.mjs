/*
 * pack.mjs — src/template.html + qgis/*.jpg + data/sprites/*.png + cenas/*.json
 *            ->  carentan.html
 *
 * Um arquivo só, sem nenhuma requisição externa: abre de file://, por duplo
 * clique, offline.
 *
 * As PLACAS vêm da pasta qgis/. Cada uma é um par: o .jpg que o QGIS desenhou
 * e o .json que o carentan.py gravou ao lado dizendo onde aquele retângulo cai
 * no mundo. É esse par que transforma um desenho bonito num mapa — sem o .json
 * não há como converter lon/lat em pixel, e sem isso um soldado não anda pela
 * Rue Holgate, anda por uma reta inventada.
 *
 * Base64 não tem '<' nem '$', então a carga não fecha a tag por acidente nem
 * tropeça na sintaxe de padrão do String.replace. Ainda assim as substituições
 * são feitas por função, que não interpreta nada.
 *
 * uso:  node tools/pack.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TPL = path.join(RAIZ, 'src', 'template.html');
const QGIS = path.join(RAIZ, 'qgis');
const SPRITES = path.join(RAIZ, 'data', 'sprites');
const CENAS = path.join(RAIZ, 'cenas');
const MALHA = path.join(RAIZ, 'data', 'malha.json');
const ORTO = path.join(RAIZ, 'orto');
const SAIDA = path.join(RAIZ, 'carentan.html');

/* A ordem das placas importa: a mais LARGA primeiro. O estúdio abre nela, e a
   validação de "está fora do mapa" usa a união de todas. */
const ORDEM = ['carentan', 'periers', 'holgate', 'holgate-perto', 'vala', 'entroncamento'];

function morre(msg) { console.error('pack: ' + msg); process.exit(1); }

let html = fs.readFileSync(TPL, 'utf8');
let bytes = 0;

/* ---------- as placas ----------
   O DESENHO DO QGIS É O PADRÃO. A ortofoto existe e funciona (`--orto`), mas o
   que faltava nunca foi detalhe de textura: era ZOOM. Espremer dez soldados numa
   faixa de três pixels fazia parecer falta de resolução do mapa, e era falta de
   aproximação da câmera mais a via medida em milímetro de tela. Consertados os
   dois, o desenho dá o que a cena precisa — e é o estilo da casa.

   As duas famílias de ficha .json são idênticas em limites e extensão, então a
   troca não mexe em mais nada: mesma cena, mesmo grafo, mesma máscara. */
const COM_ORTO = process.argv.includes('--orto');
const placas = [];
if (!fs.existsSync(QGIS)) morre('não achei a pasta qgis/');
const deOnde = new Map();          // nome -> {pasta, ficha}
for (const [pasta, rotulo] of [[QGIS, 'desenho'], [ORTO, 'ortofoto']]) {
  if (rotulo === 'ortofoto' && !COM_ORTO) continue;   // quem vem depois sobrepõe
  if (!fs.existsSync(pasta)) continue;
  for (const f of fs.readdirSync(pasta).filter((f) => f.endsWith('.json') && f !== 'osm.json')) {
    const ficha = JSON.parse(fs.readFileSync(path.join(pasta, f), 'utf8'));
    if (!ficha.extensao3857 || !ficha.limites) continue;        // não é ficha de placa
    deOnde.set(ficha.nome, { pasta, rotulo, ficha });           // a ortofoto vem depois e sobrepõe
  }
}
const fichas = [...deOnde.keys()].sort((a, b) => {
  const ia = ORDEM.indexOf(a), ib = ORDEM.indexOf(b);
  return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
});
for (const nome of fichas) {
  const { pasta, rotulo, ficha } = deOnde.get(nome);
  const img = path.join(pasta, ficha.jpg || ficha.png);
  if (!fs.existsSync(img)) {
    console.warn(`  (pulei ${ficha.nome}: falta ${path.basename(img)})`);
    continue;
  }
  /* O template carrega tudo como data:image/png. Um JPEG servido com esse
     rótulo é decodificado do mesmo jeito pelo navegador — ele olha os bytes,
     não o rótulo — mas dizer a verdade custa uma linha, e um dia alguém vai
     ler isto. */
  const b64 = fs.readFileSync(img).toString('base64');
  bytes += b64.length;
  placas.push({
    nome: ficha.nome, px: ficha.px, limites: ficha.limites, extensao3857: ficha.extensao3857,
    larguraKm: ficha.larguraKm, metrosPorPixel: ficha.metrosPorPixel,
    mime: img.toLowerCase().endsWith('.jpg') ? 'image/jpeg' : 'image/png', b64: b64
  });
  console.log(`placa ${ficha.nome} (${rotulo}): ${ficha.px[0]}×${ficha.px[1]}  ` +
              `${ficha.larguraKm} km  ${ficha.metrosPorPixel.toFixed(3)} m/px  ` +
              `${(b64.length / 1048576).toFixed(2)} MB b64`);
}
if (!placas.length) morre('nenhuma placa em qgis/ — rode primeiro o carentan.py');

/* ---------- os sprites ---------- */
const imagens = {};
if (fs.existsSync(SPRITES)) {
  for (const f of fs.readdirSync(SPRITES).filter((f) => /\.(png|jpg|jpeg)$/i.test(f)).sort()) {
    const b64 = fs.readFileSync(path.join(SPRITES, f)).toString('base64');
    imagens[path.basename(f, path.extname(f))] = b64;
    bytes += b64.length;
  }
}
const nomes = Object.keys(imagens);
console.log(`sprites: ${nomes.length ? nomes.join(', ') : '(nenhum — as unidades vão de ficha desenhada)'}`);

/* ---------- as cenas prontas ---------- */
const cenas = {};
if (fs.existsSync(CENAS)) {
  for (const f of fs.readdirSync(CENAS).filter((f) => f.endsWith('.json')).sort()) {
    const txt = fs.readFileSync(path.join(CENAS, f), 'utf8');
    try { cenas[path.basename(f, '.json')] = JSON.parse(txt); }
    catch (e) { morre(`cenas/${f} não é JSON válido: ${e.message}`); }
  }
}
console.log(`cenas: ${Object.keys(cenas).join(', ') || '(nenhuma)'}`);

/* ---------- a malha das ruas ---------- */
// Sem ela o estúdio ainda abre, mas um passo com naRua:true volta a ser uma reta
// e a validação para de reprovar quem atravessa prédio. Melhor gritar do que
// deixar passar em silêncio: é justamente o tipo de erro que só aparece no vídeo.
let malha = 'null';
if (fs.existsSync(MALHA)) {
  malha = fs.readFileSync(MALHA, 'utf8');
  const j = JSON.parse(malha);
  console.log(`malha: ${j.nos.length / 2} nós, ${j.arestas.length / 3} arestas, ` +
              `bloqueio ${j.bloqueio.largura}×${j.bloqueio.altura} a ` +
              `${j.bloqueio.metrosPorCelula} m (${(malha.length / 1024).toFixed(0)} KB)`);
  bytes += malha.length;
} else {
  console.warn('malha: FALTA data/malha.json — rode primeiro:  node tools/malha.mjs');
}

/* ---------- montar ---------- */
/* '<' vira <: uma cena com um '<' dentro de uma string fecharia a tag
   <script> e a página inteira morreria numa vírgula. */
const seguro = (o) => JSON.stringify(o).replace(/</g, '\\u003c');
for (const [marca, valor] of [['__PLACAS_JSON__', seguro(placas)],
                              ['__SPRITES_JSON__', seguro(imagens)],
                              ['__CENAS_JSON__', seguro(cenas)],
                              ['__MALHA_JSON__', malha.replace(/</g, '\\u003c')]]) {
  if (!html.includes(marca)) morre(`src/template.html não tem o marcador ${marca}`);
  html = html.replace(marca, () => valor);
}

/* o portão: o script embutido tem que compilar. Se houver erro de sintaxe, ele
   estoura AQUI e não na cara de quem abrir o arquivo. */
const script = html.match(/<script>\n([\s\S]*?)<\/script>/);
if (!script) morre('não achei o <script> do template');
new Function(script[1]);

fs.writeFileSync(SAIDA, html, 'utf8');
console.log(`\ncarentan.html  ${(html.length / 1048576).toFixed(2)} MB  ` +
            `(dados: ${(bytes / 1048576).toFixed(2)} MB em base64)`);
