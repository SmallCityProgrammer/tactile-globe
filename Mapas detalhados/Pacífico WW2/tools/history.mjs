/*
 * history.mjs — normalise the authored history tables into data/history.json
 *
 * The tables are written by hand (or by an authoring pass) as one object with
 * six keys; this script is the only place that knows their shape, so the
 * template can assume clean, projected, deduplicated data:
 *
 *   battles   the naval actions, with a projected x/y and a day number
 *   bases     ports, anchorages, airfields, straits and named seas
 *   tracks    the fleet routes, projected and resampled
 *   ships     the class database used to draw a hull in plan view
 *   fronts    the perimeter of Japanese control at five dates
 *   actions   the four set-piece orders of battle, ship by ship
 *
 * usage:  node tools/history.mjs <raw.json>        (default: data/history-raw.json)
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'data');
const IN = process.argv[2] || path.join(DATA, 'history-raw.json');

const R = 6378137, LON0 = 145, D2R = Math.PI / 180;
const east = lon => ((lon % 360) + 360) % 360;
const merc = (lon, lat) => [
  Math.round(R * (east(lon) - LON0) * D2R),
  Math.round(-R * Math.log(Math.tan(Math.PI / 4 + Math.max(-85, Math.min(85, lat)) * D2R / 2))),
];
const D0 = Date.UTC(1941, 11, 7);                      // day 0 is the Pearl Harbor morning
const day = s => {
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const p = s.split('-').map(Number);
  return Math.round((Date.UTC(p[0], p[1] - 1, p[2]) - D0) / 86400000);
};

let raw = JSON.parse(fs.readFileSync(IN, 'utf8'));
if (raw.result) raw = raw.result;                      // a workflow envelope
const src = {
  battles: (raw.battles && raw.battles.battles) || raw.battles || [],
  bases: (raw.bases && raw.bases.bases) || [],
  seas: (raw.bases && raw.bases.seas) || [],
  tracks: (raw.tracks && raw.tracks.tracks) || raw.tracks || [],
  ships: (raw.ships && raw.ships.ships) || raw.ships || [],
  fronts: (raw.front && raw.front.fronts) || raw.fronts || [],
  timeline: (raw.front && raw.front.timeline) || raw.timeline || [],
  losses: (raw.front && raw.front.losses) || raw.losses || [],
  actions: (raw.midway && raw.midway.actions) || raw.actions || [],
};

const BB = { w: 78, e: 212, s: -50, n: 62 };
const inBox = (lon, lat) => { const E = east(lon); return E >= BB.w - 2 && E <= BB.e + 2 && lat >= BB.s - 2 && lat <= BB.n + 2; };
const warn = [];
const slug = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

/* ---------- battles ---------- */
const seenB = new Set();
const battles = [];
for (const b of src.battles) {
  const id = slug(b.id || b.name);
  if (!id || seenB.has(id)) continue;
  if (!Number.isFinite(b.lat) || !Number.isFinite(b.lon)) { warn.push(`batalha sem coordenada: ${b.name}`); continue; }
  if (!inBox(b.lon, b.lat)) { warn.push(`batalha fora da janela: ${b.name} ${b.lat} ${b.lon}`); continue; }
  seenB.add(id);
  const xy = merc(b.lon, b.lat);
  battles.push({
    id, n: b.name, ja: b.ja || '', pt: b.pt || b.name,
    x: xy[0], y: xy[1], lat: +b.lat.toFixed(3), lon: +east(b.lon).toFixed(3),
    d0: day(b.d0), d1: day(b.d1 || b.d0),
    k: b.kind || 'fleet', v: b.victor || 'draw', sc: Math.max(1, Math.min(4, b.scale | 0)) || 2,
    nj: (b.ships && b.ships.jp) | 0, na: (b.ships && b.ships.allied) | 0,
    lj: (b.lost && b.lost.jp) || '', la: (b.lost && b.lost.allied) || '',
    c: b.conf || 'approx', t: b.note || '',
  });
}
battles.sort((a, b) => (a.d0 || 0) - (b.d0 || 0));

/* ---------- bases ---------- */
const seenP = new Set();
const bases = [];
for (const p of src.bases) {
  const id = slug(p.id || p.name);
  if (!id || seenP.has(id)) continue;
  if (!Number.isFinite(p.lat) || !Number.isFinite(p.lon) || !inBox(p.lon, p.lat)) { warn.push(`base fora da janela: ${p.name}`); continue; }
  seenP.add(id);
  const xy = merc(p.lon, p.lat);
  bases.push({
    id, n: p.name, ja: p.ja || '', pt: p.pt || p.name,
    x: xy[0], y: xy[1], lat: +p.lat.toFixed(3), lon: +east(p.lon).toFixed(3),
    k: p.kind || 'port', s: p.side || 'neutral',
    a: day(p.since), b: day(p.until),
    z: Math.max(1, Math.min(4, p.size | 0)) || 2, t: p.note || '',
  });
}

/* ---------- named seas ---------- */
const seas = src.seas.filter(s => Number.isFinite(s.lat) && Number.isFinite(s.lon) && inBox(s.lon, s.lat)).map(s => {
  const xy = merc(s.lon, s.lat);
  return { n: s.name, pt: s.pt || s.name, x: xy[0], y: xy[1], w: Math.abs(s.w) || 10 };
});

/* ---------- tracks ---------- */
const tracks = [];
for (const t of src.tracks) {
  const p = t.pts || [];
  if (p.length < 4) { warn.push(`rota curta demais: ${t.name}`); continue; }
  const flat = [];
  for (let i = 0; i + 1 < p.length; i += 2) {
    if (!Number.isFinite(p[i]) || !Number.isFinite(p[i + 1])) continue;
    const xy = merc(p[i], p[i + 1]);
    // a track that jumps more than a third of the window is a lon/lat swap
    if (flat.length && Math.abs(xy[0] - flat[flat.length - 2]) > 1.2e7) { warn.push(`salto na rota ${t.name}`); continue; }
    flat.push(xy[0], xy[1]);
  }
  if (flat.length < 4) continue;
  tracks.push({
    id: slug(t.id || t.name), n: t.name, pt: t.pt || t.name, s: t.side || 'jp',
    d0: day(t.d0), d1: day(t.d1 || t.d0), k: t.kind || 'surface',
    f: t.force || '', t: t.note || '', p: flat,
  });
}

/* ---------- ships ----------
   The orders of battle name classes by their common short form; the database
   spells some of them out. Anything an order of battle needs and the database
   does not carry is written in here by hand. */
const ALIAS = {
  neworleans: 'new-orleans', newmexico: 'new-mexico', pt80: 'pt-elco80', pt: 'pt-elco80',
  northcarolina: 'north-carolina', southdakota: 'south-dakota', deruyter: 'de-ruyter',
  princeofwales: 'prince-of-wales', isehybrid: 'ise-hybrid', chitose: 'chitose-cvl',
  yugumo: 'yugumo', clevelandclass: 'cleveland', atlantaclass: 'atlanta',
};
const EXTRA = [
  { id: 'mahan', name: 'Mahan', navy: 'usn', type: 'DD', loa: 104.1, beam: 10.7, draft: 5.2, disp: 2103, speed: 36.5, crew: 158, built: 18, guns: '5x1 12.7cm', air: 0, note: 'A Cassin e a Downes ardem no dique seco em Pearl Harbor; a classe serve do inicio ao fim.' },
  { id: 'benham', name: 'Benham', navy: 'usn', type: 'DD', loa: 104.0, beam: 10.9, draft: 5.2, disp: 2250, speed: 38.5, crew: 184, built: 10, guns: '4x1 12.7cm', air: 0, note: 'A Benham foi afundada pelos proprios apos avarias na segunda noite de Guadalcanal.' },
  { id: 'sims', name: 'Sims', navy: 'usn', type: 'DD', loa: 106.1, beam: 11.0, draft: 5.3, disp: 2350, speed: 35, crew: 192, built: 12, guns: '4x1 12.7cm', air: 0, note: 'A propria Sims partiu-se ao meio sob os bombardeiros de mergulho no Mar de Coral.' },
  { id: 'johncbutler', name: 'John C. Butler', navy: 'usn', type: 'DE', loa: 93.3, beam: 11.3, draft: 4.1, disp: 1745, speed: 24, crew: 222, built: 83, guns: '2x1 12.7cm', air: 0, note: 'A Samuel B. Roberts atacou cruzadores pesados ao largo de Samar e afundou por isso.' },
  { id: 'shiratsuyu', name: 'Shiratsuyu', ja: '白露型', navy: 'ijn', type: 'DD', loa: 107.5, beam: 9.9, draft: 3.5, disp: 1980, speed: 34, crew: 180, built: 10, guns: '2x2 + 1x1 12.7cm', air: 0, note: 'O Shigure saiu sozinho e intacto do estreito de Surigao, unico sobrevivente da linha de Nishimura.' },
  { id: 'hatsuharu', name: 'Hatsuharu', ja: '初春型', navy: 'ijn', type: 'DD', loa: 109.5, beam: 10.0, draft: 3.5, disp: 1802, speed: 36.5, crew: 212, built: 6, guns: '2x2 + 1x1 12.7cm', air: 0, note: 'Classe pesada demais em cima: reconstruida antes de entrar em servico.' },
  { id: 'county', name: 'County', navy: 'ran', type: 'CA', loa: 192.0, beam: 20.8, draft: 6.4, disp: 13450, speed: 31.5, crew: 710, built: 13, guns: '4x2 20.3cm', air: 1, note: 'O HMAS Canberra afundou em Savo; o Australia levou o primeiro kamikaze da guerra.' },
  { id: 'tribal', name: 'Tribal', navy: 'ran', type: 'DD', loa: 115.0, beam: 11.1, draft: 4.0, disp: 2519, speed: 36, crew: 190, built: 27, guns: '3x2 12cm', air: 0, note: 'Os australianos Arunta e Warramunga escoltaram de Nova Guine a baia de Toquio.' },
];
// a plan-view mount layout for the hand-written classes: destroyers carry their
// guns evenly fore and aft, a treaty cruiser two mounts at each end
for (const e of EXTRA) {
  const n = e.type === 'CA' ? 4 : e.guns.startsWith('4x1') ? 4 : e.guns.startsWith('2x1') ? 2 : 5;
  const cal = e.navy === 'ijn' ? 12.7 : e.type === 'CA' ? 20.3 : e.type === 'DD' && e.navy === 'ran' ? 12 : 12.7;
  const barrels = e.type === 'CA' || (e.navy === 'ijn' || e.navy === 'ran') ? 2 : 1;
  e.turrets = [];
  for (let i = 0; i < n; i++) {
    const fwd = i < Math.ceil(n / 2);
    const k = fwd ? i / Math.max(1, Math.ceil(n / 2)) : (i - Math.ceil(n / 2)) / Math.max(1, Math.floor(n / 2));
    e.turrets.push({ x: fwd ? 0.13 + k * 0.16 : 0.62 + k * 0.22, barrels: i === n - 1 && barrels === 2 && e.type !== 'CA' ? 1 : barrels, cal, aft: !fwd });
  }
  e.flight = [];
}
src.ships = src.ships.concat(EXTRA);

const seenS = new Set();
const ships = [];
for (const s of src.ships) {
  const id = slug(s.id || s.name);
  if (!id || seenS.has(id) || !(s.loa > 0)) continue;
  seenS.add(id);
  const fl = Array.isArray(s.flight) ? s.flight : [];
  ships.push({
    id, n: s.name, ja: s.ja || '', nv: s.navy || 'ijn', t: s.type || 'DD',
    l: Math.round(s.loa), b: +(s.beam || s.loa / 9).toFixed(1), dr: +(s.draft || 6).toFixed(1),
    dp: Math.round(s.disp || 0), sp: +(s.speed || 25).toFixed(1), cr: s.crew | 0, bu: s.built | 0,
    g: s.guns || '',
    tu: (s.turrets || []).filter(t => Number.isFinite(t.x)).map(t => ({ x: +Math.max(0.02, Math.min(0.98, t.x)).toFixed(3), b: Math.max(1, t.barrels | 0), c: +(t.cal || 12.7), a: t.aft ? 1 : 0 })),
    ai: s.air | 0,
    fd: fl.length >= 4 ? { l: +fl[0] || Math.round(s.loa * 0.95), w: +fl[1] || 30, i: fl[2] || 's', lf: +fl[3] || 2 } : null,
    tx: s.note || '',
  });
}

/* ---------- fronts ---------- */
const fronts = [];
for (const f of src.fronts) {
  const p = f.pts || [];
  const flat = [];
  for (let i = 0; i + 1 < p.length; i += 2) {
    if (!Number.isFinite(p[i]) || !Number.isFinite(p[i + 1])) continue;
    const xy = merc(p[i], p[i + 1]);
    flat.push(xy[0], xy[1]);
  }
  if (flat.length < 8) { warn.push(`frente curta: ${f.date}`); continue; }
  fronts.push({ d: day(f.date), date: f.date, pt: f.pt || '', p: flat });
}
fronts.sort((a, b) => a.d - b.d);

/* ---------- timeline ---------- */
const timeline = src.timeline.filter(e => Number.isFinite(e.lat) && Number.isFinite(e.lon) && day(e.d) !== null).map(e => {
  const xy = merc(e.lon, e.lat);
  return { d: day(e.d), date: e.d, pt: e.pt || '', k: e.kind || 'battle', x: xy[0], y: xy[1] };
}).sort((a, b) => a.d - b.d);

const losses = src.losses.map(l => ({ d: day(l.d), date: l.d, jCV: l.jpCV | 0, jBB: l.jpBB | 0, jCA: l.jpCA | 0, uCV: l.usCV | 0, uBB: l.usBB | 0, uCA: l.usCA | 0 })).sort((a, b) => a.d - b.d);

/* ---------- set-piece orders of battle ---------- */
const NM = 1852;
const cls = s => { const k = slug(s); return ALIAS[k] || ALIAS[k.replace(/-/g, '')] || k; };
const actions = [];
for (const a of src.actions) {
  if (!Number.isFinite(a.lat) || !Number.isFinite(a.lon)) continue;
  const c = merc(a.lon, a.lat);
  // the local frame is nautical miles east/north; Mercator stretches both by 1/cos(lat)
  const k = NM / Math.cos(a.lat * D2R);
  const units = (a.units || []).filter(u => Number.isFinite(u.bx) && Number.isFinite(u.by)).map(u => ({
    n: u.name, ja: u.ja || '', c: cls(u.cls), s: u.side === 'jp' ? 'jp' : 'us',
    x: Math.round(c[0] + u.bx * k), y: Math.round(c[1] - u.by * k),
    h: ((u.hdg | 0) % 360 + 360) % 360, f: u.fate || '', r: u.role || 'destroyer',
  }));
  const air = (a.air || []).filter(u => Number.isFinite(u.bx) && Number.isFinite(u.by)).map(u => ({
    s: u.side === 'jp' ? 'jp' : 'us', k: u.kind || 'fighter',
    x: Math.round(c[0] + u.bx * k), y: Math.round(c[1] - u.by * k),
    h: ((u.hdg | 0) % 360 + 360) % 360, n: Math.max(1, u.n | 0), pt: u.pt || '',
  }));
  actions.push({
    id: slug(a.id || a.name), n: a.name, pt: a.pt || a.name, d: day(a.d), date: a.d,
    x: c[0], y: c[1], lat: +a.lat.toFixed(3), lon: +east(a.lon).toFixed(3),
    u: units, a: air, ph: (a.phases || []).map(p => ({ t: p.t, pt: p.pt })),
  });
}

/* ---------- a ship class for every hull named in an order of battle ---------- */
const have = new Set(ships.map(s => s.id));
const missing = new Map();
for (const a of actions) for (const u of a.u) if (!have.has(u.c)) missing.set(u.c, (missing.get(u.c) || 0) + 1);
if (missing.size) warn.push(`classes sem ficha: ${[...missing.entries()].map(e => e[0] + '×' + e[1]).join(', ')}`);

const out = { battles, bases, seas, tracks, ships, fronts, timeline, losses, actions };
fs.writeFileSync(path.join(DATA, 'history.json'), JSON.stringify(out));
console.log(`history.json  ${(fs.statSync(path.join(DATA, 'history.json')).size / 1024).toFixed(0)} KB`);
for (const k of Object.keys(out)) console.log(`  ${k.padEnd(10)} ${out[k].length}`);
if (warn.length) { console.log('\navisos:'); for (const w of warn) console.log('  ' + w); }
