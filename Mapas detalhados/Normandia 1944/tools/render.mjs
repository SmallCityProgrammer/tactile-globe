/*
 * render.mjs — uma cena, como arquivo de video.
 *
 * Irmao do render.mjs do Globe Studio, apontado para o carentan.html. A ideia
 * e a mesma e vale repetir: o mapa desenha cada quadro SO a partir do relogio.
 * seek(t) e depois render() poem sempre os mesmos pixels na tela, sem nada
 * carregado do quadro anterior. Entao o video nao e uma gravacao de tela — e a
 * cena amostrada a uma taxa fixa, um quadro por vez, na velocidade que a
 * maquina der. Se um quadro demorar dois segundos, nada escorrega: o decimo
 * segundo continua sendo o decimo segundo.
 *
 * O encanamento, sem nenhuma biblioteca para instalar:
 *
 *   http.createServer   serve a pasta do projeto (o carentan.html tem 7 MB de
 *                       base64, e o file:// recusa parte disso)
 *   Chrome --headless   desenha
 *   CDP por WebSocket   o Node 22+ tem WebSocket embutido, entao falar com o
 *                       Chrome nao custa dependencia nenhuma
 *   ffmpeg              le os PNGs na entrada padrao e escreve o mp4
 *
 * Nada e escrito em disco entre o Chrome e o ffmpeg: os quadros descem por um
 * cano, entao um filme de 52 s nao deixa 2 GB de PNG para tras. --frames=DIR
 * guarda mesmo assim, quando se quer olhar um.
 *
 * uso:
 *   node tools/render.mjs                             a cena padrao
 *   node tools/render.mjs --scene=cenas/x.json --out=x.mp4
 *   node tools/render.mjs --from=8 --secs=2           so o trecho duvidoso
 *   node tools/render.mjs --check                     sem video: diz o que faria
 *
 * bandeiras: --fps=30 --w=1920 --h=1080 --crf=18 --helpers --frames=DIR
 */
import fs from 'fs';
import path from 'path';
import http from 'http';
import { spawn, execFileSync } from 'child_process';
import { fileURLToPath } from 'url';
import os from 'os';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/* ---------- arguments ---------- */
const ARG = {};
for (const a of process.argv.slice(2)) {
  const m = /^--([^=]+)(?:=(.*))?$/.exec(a);
  if (!m) { console.error(`unknown argument: ${a}`); process.exit(2); }
  ARG[m[1]] = m[2] === undefined ? true : m[2];
}
const SCENE   = ARG.scene || 'carentan-0600';  // um nome de cena, ou um caminho para um JSON
const FPS     = +(ARG.fps || 30);
const W       = +(ARG.w || 1920);
const H       = +(ARG.h || 1080);
const CRF     = +(ARG.crf || 18);
const FROM    = ARG.from !== undefined ? +ARG.from : 0;
const SECS    = ARG.secs !== undefined ? +ARG.secs : null;
const HELPERS = !!ARG.helpers;                 // keep routes, tags and the bar in frame
const FRAMEDIR = ARG.frames || null;
const CHECK   = !!ARG.check;
const OUT     = path.resolve(ROOT, ARG.out || `render/${path.basename(String(SCENE), '.json')}.mp4`);

if (!(FPS > 0 && FPS <= 120)) fail('--fps must be between 1 and 120');
if (!(W >= 16 && H >= 16)) fail('--w and --h must be at least 16');
if (W % 2 || H % 2) fail('--w and --h must be even (yuv420p)');   // the docs' rule, enforced in code
if (SECS !== null && !(SECS > 0)) fail('--secs must be positive');
if (FROM < 0) fail('--from cannot be negative');

function fail(msg) { console.error('render: ' + msg); process.exit(1); }
const log = (...a) => console.log(...a);

/* ---------- the tools this machine has ---------- */
function findExe(name, candidates) {
  for (const c of candidates) if (c && fs.existsSync(c)) return c;
  try {                                          // fall back to PATH
    const out = execFileSync(process.platform === 'win32' ? 'where' : 'which', [name],
                             { encoding: 'utf8' }).split(/\r?\n/)[0].trim();
    if (out && fs.existsSync(out)) return out;
  } catch (_) {}
  return null;
}
const LOCAL = process.env.LOCALAPPDATA || '';
const CHROME = findExe('chrome', [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  LOCAL && path.join(LOCAL, 'Google/Chrome/Application/chrome.exe'),
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome', '/usr/bin/chromium',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
]);
const FFMPEG = findExe('ffmpeg', [process.env.FFMPEG_PATH, 'C:/Program Files/ffmpeg/bin/ffmpeg.exe']);
const FFPROBE = FFMPEG ? FFMPEG.replace(/ffmpeg(\.exe)?$/i, (m) => m.replace('ffmpeg', 'ffprobe')) : null;
if (!CHROME) fail('no Chrome or Edge found — set CHROME_PATH');
if (!FFMPEG && !CHECK) fail('no ffmpeg found — set FFMPEG_PATH');
if (!fs.existsSync(path.join(ROOT, 'carentan.html'))) fail('falta o carentan.html — rode: node tools/pack.mjs');

/* ---------- a scene from disk, if that is what was asked for ---------- */
let sceneJson = null;
if (/[\\/.]/.test(String(SCENE))) {
  const p = path.resolve(ROOT, String(SCENE));
  if (!fs.existsSync(p)) fail(`no scene file at ${p}`);
  try { sceneJson = JSON.parse(fs.readFileSync(p, 'utf8')); }
  catch (e) { fail(`${SCENE} is not valid JSON: ${e.message}`); }
}

/* ---------- serve the folder ---------- */
const MIME = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.js': 'text/javascript',
               '.png': 'image/png', '.jpg': 'image/jpeg', '.bin': 'application/octet-stream' };
const server = http.createServer((req, res) => {
  const rel = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'carentan.html';
  const file = path.resolve(ROOT, rel);
  if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end('not found');
    return;
  }
  res.writeHead(200, { 'content-type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

/* ---------- a minimal CDP client ---------- */
let cdp = null, msgId = 0;
const pending = new Map();
function send(method, params = {}) {
  const id = ++msgId;
  cdp.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    setTimeout(() => {
      if (pending.has(id)) { pending.delete(id); reject(new Error(`${method} timed out`)); }
    }, 120000);
  });
}
/* Runtime.evaluate, with the page's exception turned into ours — a scene
   that throws in the browser must stop the render, not produce a black film */
async function evaluate(expression, awaitPromise = true) {
  const r = await send('Runtime.evaluate', { expression, awaitPromise, returnByValue: true });
  if (r.exceptionDetails) {
    const e = r.exceptionDetails;
    throw new Error('page: ' + (e.exception?.description || e.text));
  }
  return r.result?.value;
}

const userDir = fs.mkdtempSync(path.join(os.tmpdir(), 'carentan-render-'));
let chrome = null;
async function launch() {
  const args = [
    '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${userDir}`,
    '--no-first-run', '--no-default-browser-check', '--disable-extensions',
    '--hide-scrollbars', '--mute-audio', `--window-size=${W},${H}`,
    '--enable-unsafe-swiftshader',        // software WebGL if this box has no usable GPU
    `http://127.0.0.1:${PORT}/carentan.html`,
  ];
  chrome = spawn(CHROME, args, { stdio: ['ignore', 'ignore', 'pipe'] });
  chrome.stderr.on('data', () => {});    // Chrome is chatty on stderr; the port file is the signal
  const portFile = path.join(userDir, 'DevToolsActivePort');
  const started = Date.now();
  while (Date.now() - started < 30000) {
    if (fs.existsSync(portFile)) {
      const txt = fs.readFileSync(portFile, 'utf8').split('\n');
      if (txt.length >= 2) return +txt[0];
    }
    if (chrome.exitCode !== null) fail(`Chrome exited early (code ${chrome.exitCode})`);
    await new Promise((r) => setTimeout(r, 100));
  }
  fail('Chrome did not open a debugging port in 30 s');
}
async function connect(devPort) {
  const started = Date.now();
  while (Date.now() - started < 30000) {
    try {
      const list = await fetch(`http://127.0.0.1:${devPort}/json/list`).then((r) => r.json());
      const page = list.find((t) => t.type === 'page' && t.webSocketDebuggerUrl);
      if (page) {
        cdp = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((res, rej) => { cdp.onopen = res; cdp.onerror = () => rej(new Error('cdp socket failed')); });
        cdp.onmessage = (ev) => {
          const m = JSON.parse(ev.data);
          if (m.id && pending.has(m.id)) {
            const { resolve, reject } = pending.get(m.id);
            pending.delete(m.id);
            m.error ? reject(new Error(m.error.message)) : resolve(m.result);
          }
        };
        return;
      }
    } catch (_) {}
    await new Promise((r) => setTimeout(r, 150));
  }
  fail('could not attach to Chrome');
}

function cleanup() {
  try { cdp && cdp.close(); } catch (_) {}
  try { chrome && chrome.kill(); } catch (_) {}
  try { server.close(); } catch (_) {}
  try { fs.rmSync(userDir, { recursive: true, force: true }); } catch (_) {}
}
process.on('exit', cleanup);
process.on('SIGINT', () => { cleanup(); process.exit(130); });

/* ================= the render ================= */
const devPort = await launch();
await connect(devPort);
await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride',
           { width: W, height: H, deviceScaleFactor: 1, mobile: false });

/* Esperar a PLACA chegar, e nao so a pagina existir. A placa e 3 MB de base64
   que o navegador ainda precisa decodificar; se o primeiro quadro sair antes
   disso, ele sai com o fundo verde chapado — e um quadro sem o mapa e
   igualzinho a um quadro onde o mapa nunca existiu. */
log(`chrome pronto, esperando o mapa (${W}×${H})`);
const ready = await evaluate(`(async () => {
  const t0 = Date.now();
  while (Date.now() - t0 < 60000) {
    if (window.__mapa && __mapa.info) {
      const i = __mapa.info();
      if (i.images && i.placas && i.placas.length && i.images.length >= i.placas.length)
        return { ok: true, images: i.images.length, placas: i.placas };
    }
    const m = document.getElementById('aviso');
    if (m && m.style.display === 'flex' && m.textContent) return { ok: false, msg: m.textContent };
    await new Promise(r => setTimeout(r, 100));
  }
  return { ok: false, msg: 'o __mapa nao apareceu em 60 s' };
})()`);
if (!ready || !ready.ok) fail(`a pagina nao subiu: ${ready ? ready.msg : 'sem resposta'}`);
log(`placas: ${ready.placas.join(', ')}`);

/* a cena, e entao o quadro: sem trajetos, sem barra — so o mapa */
const loader = sceneJson
  ? `__mapa.loadCena(${JSON.stringify(sceneJson)}); return true;`
  : `return __mapa.demo(${JSON.stringify(String(SCENE))});`;
const loaded = await evaluate(`(() => {
  const ok = (function(){ ${loader} })();
  __mapa.pause();
  ${HELPERS ? '' : `__mapa.set({ helpers: false });
  document.querySelectorAll('.painel').forEach(p => p.style.display = 'none');`}
  const chk = __mapa.validaCena(__mapa.cena());
  const i = __mapa.info();
  return { ok: !!ok, sprites: i.sprites, end: i.end, shots: i.shots, kills: i.kills,
           errors: chk.errors, warnings: chk.warnings };
})()`);
if (!loaded.ok) fail(`nao existe cena "${SCENE}" — use um nome de __mapa.demos() ou um caminho para um JSON`);
if (!loaded.sprites) fail('a cena nao tem nenhuma unidade');
/* o portao: nada que custe GPU roda antes de o dado passar na validacao */
if (loaded.errors.length) fail('a cena nao e valida:\n  - ' + loaded.errors.join('\n  - '));
if (loaded.warnings.length) log('avisos:\n  - ' + loaded.warnings.join('\n  - '));

const end = SECS !== null ? FROM + SECS : loaded.end;
const total = Math.max(1, Math.round((end - FROM) * FPS));
log(`cena "${SCENE}": ${loaded.sprites} unidades, ${loaded.shots} tiros, ${loaded.kills} baixas, ${loaded.end.toFixed(2)} s`);
log(`${total} quadros a ${FPS} fps (${FROM.toFixed(2)} s → ${end.toFixed(2)} s) para ${path.relative(ROOT, OUT)}`);
if (CHECK) { log('--check: paro antes do primeiro quadro'); cleanup(); process.exit(0); }

fs.mkdirSync(path.dirname(OUT), { recursive: true });
if (FRAMEDIR) fs.mkdirSync(path.resolve(ROOT, FRAMEDIR), { recursive: true });

const ff = spawn(FFMPEG, [
  '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', String(CRF), '-preset', 'medium',
  '-movflags', '+faststart', OUT,
], { stdio: ['pipe', 'ignore', 'pipe'] });
let ffErr = '';
ff.stderr.on('data', (d) => { ffErr += d.toString(); if (ffErr.length > 8000) ffErr = ffErr.slice(-8000); });
const ffDone = new Promise((resolve) => ff.on('close', resolve));
ff.stdin.on('error', () => {});          // ffmpeg dying is reported by its exit code, not here

const t0 = Date.now();
let written = 0;
for (let i = 0; i < total; i++) {
  const t = FROM + i / FPS;
  await evaluate(`(__mapa.seek(${t}), __mapa.render(), 1)`, false);
  const shot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
  const buf = Buffer.from(shot.data, 'base64');
  if (FRAMEDIR) fs.writeFileSync(path.join(path.resolve(ROOT, FRAMEDIR), `f${String(i).padStart(5, '0')}.png`), buf);
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  written++;
  if (i % Math.max(1, Math.round(FPS)) === 0 || i === total - 1) {
    const done = (i + 1) / total, el = (Date.now() - t0) / 1000;
    process.stdout.write(`\r  ${String(i + 1).padStart(5)}/${total} quadros  ${(done * 100).toFixed(0)}%  ` +
                         `${el.toFixed(0)} s corridos, faltam ~${(el / done - el).toFixed(0)} s   `);
  }
}
process.stdout.write('\n');
ff.stdin.end();
const code = await ffDone;
cleanup();
if (code !== 0) { console.error(ffErr.split('\n').slice(-12).join('\n')); fail(`ffmpeg exited with ${code}`); }
if (written !== total) fail(`escrevi ${written} de ${total} quadros`);

/* ---------- measure it; do not estimate it ---------- */
let probe = null;
if (FFPROBE && fs.existsSync(FFPROBE)) {
  try {
    probe = JSON.parse(execFileSync(FFPROBE, ['-v', 'error', '-show_format', '-show_streams',
                                              '-of', 'json', OUT], { encoding: 'utf8' }));
  } catch (_) {}
}
const size = fs.statSync(OUT).size;
const want = total / FPS;
log(`\n${path.relative(ROOT, OUT)}  ${(size / 1048576).toFixed(1)} MB`);
if (probe) {
  const v = probe.streams.find((s) => s.codec_type === 'video');
  const got = +probe.format.duration;
  log(`${v.width}×${v.height}  ${v.nb_frames || total} frames  ${got.toFixed(2)} s  (${Math.round(+probe.format.bit_rate / 1000)} kbps)`);
  /* medir, nao estimar: o filme tem que ter o comprimento que a cena pediu */
  if (Math.abs(got - want) > 1) fail(`o video tem ${got.toFixed(2)} s mas a cena pediu ${want.toFixed(2)} s`);
  log(`a duracao bate com a cena (${want.toFixed(2)} s, erro de ${Math.abs(got - want).toFixed(3)} s)`);
}
log(`${((Date.now() - t0) / 1000).toFixed(0)} s de render para ${want.toFixed(1)} s de filme`);
process.exit(0);
