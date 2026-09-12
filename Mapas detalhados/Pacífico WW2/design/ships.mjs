/*
 * ships.mjs — plan views of a battleship, drawn from her general arrangement
 *
 *   node design/ships.mjs        ->  design/yamato.svg       (porte de 1945)
 *                                    design/yamato-1941.svg  (porte da planta)
 *                                    design/iowa.svg
 *                                    design/comparacao.svg
 *
 * WHY A GENERATOR AND NOT A DRAWING
 * Everything here is in metres, bow at x = 0, centreline at y = 0, stern at
 * x = LOA. So a mount is not placed where it looks right — it is placed at the
 * frame it actually sat on, and the barrel that comes out of it is 20.7 m long
 * because a 46 cm/45 is 20.7 m long. Change LOA and the whole ship re-lays
 * itself. That is the part an image generator cannot do.
 *
 * The two ships are drawn to the same scale and the same conventions:
 *   - bow to the LEFT (the map's sprites point their bow at -x)
 *   - no background: the page is transparent, so it exports straight to a PNG
 *     with alpha
 *   - every colour is a CSS custom property at the top of the file, so the
 *     whole thing can be re-skinned without touching a single path
 *   - layers are named groups (casco, conves, torres, ...): hide one and the
 *     ship keeps working
 *
 * Yamato is measured off two drawings: the builders' plan NH 111711 (Naval
 * History & Heritage Command, public domain) for the hull and the stations,
 * and Alexpl's colour plan of 7 April 1945 (Wikimedia, CC BY-SA 3.0) for the
 * fit she died in. Nothing is traced — these are measurements read off the
 * sheets, and the geometry is rebuilt from the numbers.
 *
 * IOWA IS NOT MEASURED. Her stations are estimated from general proportion, the
 * same standing Yamato's had before the plan was read. The US Navy's Booklets
 * of General Plans are public domain and would settle them the same way.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)));
const PX_PER_M = 14;                  // only sets the width= attribute; the viewBox is metres
const MARGIN = 5;

/* ---------------------------------------------------------------- plumbing */
const f = n => {
  const v = Math.round(n * 100) / 100;
  return Object.is(v, -0) ? '0' : String(v);
};
function el(tag, attrs, kids) {
  let s = '<' + tag;
  for (const k of Object.keys(attrs || {})) {
    const v = attrs[k];
    if (v === null || v === undefined || v === false) continue;
    s += ' ' + k + '="' + (typeof v === 'number' ? f(v) : v) + '"';
  }
  if (kids === undefined || kids === null || kids === '') return s + '/>';
  return s + '>' + (Array.isArray(kids) ? kids.join('') : kids) + '</' + tag + '>';
}
const g = (id, kids, attrs) => el('g', Object.assign({ id }, attrs || {}), kids);
const pts = a => a.map(p => f(p[0]) + ',' + f(p[1])).join(' ');

/* a closed Catmull-Rom through the points, as cubic beziers: hulls are fair
   curves and a polyline through 20 stations reads as a polygon */
function smooth(p, closed) {
  const n = p.length, at = i => p[closed ? (i + n) % n : Math.max(0, Math.min(n - 1, i))];
  let d = 'M' + f(p[0][0]) + ' ' + f(p[0][1]);
  const last = closed ? n : n - 1;
  for (let i = 0; i < last; i++) {
    const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
    d += 'C' + f(p1[0] + (p2[0] - p0[0]) / 6) + ' ' + f(p1[1] + (p2[1] - p0[1]) / 6)
      + ' ' + f(p2[0] - (p3[0] - p1[0]) / 6) + ' ' + f(p2[1] - (p3[1] - p1[1]) / 6)
      + ' ' + f(p2[0]) + ' ' + f(p2[1]);
  }
  return d + (closed ? 'Z' : '');
}

/* ------------------------------------------------------------------- hulls
   Each ship is a table of stations: [distance from the bow, half-breadth at
   the weather deck]. Everything else on deck is placed against halfAt(). */
function hullMaker(st) {
  const halfAt = x => {
    if (x <= st[0][0]) return st[0][1];
    for (let i = 1; i < st.length; i++) if (x <= st[i][0]) {
      const t = (x - st[i - 1][0]) / (st[i][0] - st[i - 1][0]);
      return st[i - 1][1] + (st[i][1] - st[i - 1][1]) * t;
    }
    return st[st.length - 1][1];
  };
  const outline = () => {
    const top = st.map(s => [s[0], -s[1]]);
    const bot = st.slice(1, -1).reverse().map(s => [s[0], s[1]]);
    return smooth(top.concat(bot), true);
  };
  // the same shape pulled in by `d` metres all round: deck edges, planking limits
  const inset = d => {
    const top = st.map(s => [s[0] + (s[1] < 0.6 ? d * 3 : 0), -Math.max(0, s[1] - d)]);
    const bot = st.slice(1, -1).reverse().map(s => [s[0] + (s[1] < 0.6 ? d * 3 : 0), Math.max(0, s[1] - d)]);
    return smooth(top.concat(bot), true);
  };
  return { halfAt, outline, inset, L: st[st.length - 1][0], B: 2 * Math.max(...st.map(s => s[1])) };
}

/* --------------------------------------------------------------- the parts
   d = +1 means the mount trains toward the bow, -1 toward the stern. Every
   part is drawn around its own centre and then translated, so `train` is just
   a rotation and a trained turret costs nothing extra. */
function barrel(len, calM, x0, y) {
  // breech end thick, a step down at the chase, a muzzle swell at the tip
  const rB = calM * 2.4, rM = calM * 1.5, step = len * 0.42;
  return [
    el('path', { class: 'cano', d: `M${f(x0)} ${f(y - rB)}L${f(x0 - step)} ${f(y - rB)}L${f(x0 - step - 0.4)} ${f(y - rM)}L${f(x0 - len + 0.5)} ${f(y - rM)}L${f(x0 - len)} ${f(y - rM * 1.25)}L${f(x0 - len)} ${f(y + rM * 1.25)}L${f(x0 - len + 0.5)} ${f(y + rM)}L${f(x0 - step - 0.4)} ${f(y + rM)}L${f(x0 - step)} ${f(y + rB)}L${f(x0)} ${f(y + rB)}Z` }),
    el('line', { class: 'cano-luz', x1: x0 - step, y1: y - rM * 0.45, x2: x0 - len + 0.6, y2: y - rM * 0.45 }),
  ].join('');
}
function mainTurret(o) {
  /* d = +1 trains toward the bow, -1 toward the stern. The face sits at -d*fwd
     and the rear at +d*aft_, so an after turret is the same drawing mirrored —
     getting this wrong puts the sloped face on the wrong end of the house. */
  const d = o.aft ? -1 : 1;
  const fw = o.faceW, mw = o.midW, rw = o.rearW, fx = -d * o.fwd, rx = d * o.aft_;
  // gun house: narrow sloped face, widest a third of the way back, square rear
  const house = `M${f(fx)} ${f(-fw / 2)}` +
    `L${f(fx + d * 3.2)} ${f(-mw / 2)}` +
    `L${f(rx - d * 2.2)} ${f(-rw / 2)}` +
    `L${f(rx)} ${f(-rw / 2 + 1.1)}` +
    `L${f(rx)} ${f(rw / 2 - 1.1)}` +
    `L${f(rx - d * 2.2)} ${f(rw / 2)}` +
    `L${f(fx + d * 3.2)} ${f(mw / 2)}` +
    `L${f(fx)} ${f(fw / 2)}Z`;
  const out = [];
  out.push(el('circle', { class: 'barbeta', cx: 0, cy: 0, r: o.barbette / 2 }));
  out.push(el('path', { class: 'torre', d: house }));
  out.push(el('path', { class: 'torre-topo', d: house, transform: `translate(${f(-d * 0.5)} -0.5) scale(0.955)` }));
  /* Barrels are drawn once, pointing at -x, and mirrored for an after turret.
     In that mirrored frame the face is always at -fwd, whichever way the
     turret trains. */
  for (let i = 0; i < o.guns; i++) {
    const y = (i - (o.guns - 1) / 2) * o.spacing;
    out.push(el('g', { transform: d < 0 ? 'scale(-1,1)' : null }, barrel(o.barrelProj, o.cal / 100, -o.fwd, y)));
    out.push(el('ellipse', { class: 'lona', cx: fx + d * 0.45, cy: y, rx: 1.0, ry: o.spacing * 0.33 }));
  }
  if (o.rf) {                                     // the base-length rangefinder across the rear
    const ry = rx - d * o.rfBack;
    out.push(el('rect', { class: 'telemetro', x: ry - 0.8, y: -o.rf / 2, width: 1.6, height: o.rf, rx: 0.55 }));
    for (const s of [-1, 1]) out.push(el('rect', { class: 'telemetro-cabeca', x: ry - 1.3, y: s * o.rf / 2 - 0.9, width: 2.6, height: 1.8, rx: 0.5 }));
  }
  // roof clutter: hatches and the captain's cupola
  out.push(el('circle', { class: 'escotilha', cx: rx - d * 4.5, cy: -rw * 0.22, r: 0.55 }));
  out.push(el('circle', { class: 'escotilha', cx: rx - d * 4.5, cy: rw * 0.22, r: 0.55 }));
  out.push(el('circle', { class: 'cupula', cx: fx + d * 5.5, cy: 0, r: 1.0 }));
  return g(o.id, out, { transform: `translate(${f(o.x)} 0)` + (o.train ? ` rotate(${f(o.train)})` : '') });
}
function secTurret(o) {                            // a light triple: 15.5 cm or a 20 cm
  const d = o.aft ? -1 : 1, L = o.len, Wd = o.w;
  const fx = -d * L * 0.36, rx = d * L * 0.64;
  const house = `M${f(fx)} ${f(-Wd / 2 * 0.86)}L${f(fx + d * 1.8)} ${f(-Wd / 2)}L${f(rx - d * 1.2)} ${f(-Wd / 2)}L${f(rx)} ${f(-Wd / 2 + 0.8)}L${f(rx)} ${f(Wd / 2 - 0.8)}L${f(rx - d * 1.2)} ${f(Wd / 2)}L${f(fx + d * 1.8)} ${f(Wd / 2)}L${f(fx)} ${f(Wd / 2 * 0.86)}Z`;
  const out = [el('circle', { class: 'barbeta', cx: 0, cy: 0, r: o.barbette / 2 }), el('path', { class: 'torre', d: house }), el('path', { class: 'torre-topo', d: house, transform: 'scale(0.94)' })];
  for (let i = 0; i < o.guns; i++) {
    const y = (i - (o.guns - 1) / 2) * o.spacing;
    out.push(el('g', { transform: d < 0 ? 'scale(-1,1)' : null }, barrel(o.barrelProj, o.cal / 100, -L * 0.36, y)));
  }
  return g(o.id, out, { transform: `translate(${f(o.x)} ${f(o.y || 0)})` + (o.rot ? ` rotate(${f(o.rot)})` : '') });
}
/* a twin 12.7 cm / 5 in in its shield: the workhorse mount of both navies */
function twinDP(x, y, rot, cal) {
  const w = cal > 12 ? 4.6 : 4.2, l = cal > 12 ? 4.4 : 4.0, bl = cal * 0.40;
  const shield = `M${f(-l * 0.45)} ${f(-w / 2 * 0.74)}L${f(-l * 0.2)} ${f(-w / 2)}L${f(l * 0.42)} ${f(-w / 2)}L${f(l * 0.55)} ${f(-w / 2 + 0.7)}L${f(l * 0.55)} ${f(w / 2 - 0.7)}L${f(l * 0.42)} ${f(w / 2)}L${f(-l * 0.2)} ${f(w / 2)}L${f(-l * 0.45)} ${f(w / 2 * 0.74)}Z`;
  const out = [el('circle', { class: 'aa-tina', cx: 0, cy: 0, r: w * 0.78 }), el('circle', { class: 'reparo-base', cx: 0, cy: 0, r: w * 0.56 }), el('path', { class: 'reparo', d: shield })];
  for (const s of [-1, 1]) out.push(el('rect', { class: 'cano', x: -l * 0.45 - bl, y: s * 0.75 - 0.16, width: bl, height: 0.32, rx: 0.14 }));
  return g(null, out, { transform: `translate(${f(x)} ${f(y)}) rotate(${f(rot || 0)})`, class: 'dp' });
}
/* a 25 mm triple (IJN) — the mount that covered Yamato from end to end in 1945 */
function aa25(x, y, rot) {
  const out = [
    el('circle', { class: 'aa-tina', cx: 0, cy: 0, r: 2.3 }),
    el('circle', { class: 'aa-base', cx: 0, cy: 0, r: 1.45 }),
    el('path', { class: 'aa', d: `M-1.0 -1.15L0.75 -1.15L1.25 -0.5L1.25 0.5L0.75 1.15L-1.0 1.15Z` }),
  ];
  for (const s of [-1, 0, 1]) out.push(el('rect', { class: 'cano', x: -2.7, y: s * 0.42 - 0.11, width: 1.9, height: 0.22, rx: 0.1 }));
  return g(null, out, { transform: `translate(${f(x)} ${f(y)}) rotate(${f(rot || 0)})`, class: 'aa25' });
}
/* a quad 40 mm Bofors (USN), with its own director tub alongside */
function bofors(x, y, rot) {
  const out = [
    el('circle', { class: 'aa-base', cx: 0, cy: 0, r: 1.9 }),
    el('rect', { class: 'aa', x: -1.3, y: -1.5, width: 2.7, height: 3.0, rx: 0.45 }),
  ];
  for (const s of [-1.5, -0.5, 0.5, 1.5]) out.push(el('rect', { class: 'cano', x: -3.9, y: s * 0.52 - 0.11, width: 2.7, height: 0.22, rx: 0.1 }));
  return g(null, out, { transform: `translate(${f(x)} ${f(y)}) rotate(${f(rot || 0)})`, class: 'bofors' });
}
function oerlikon(x, y, rot) {
  return g(null, [el('circle', { class: 'aa-base', cx: 0, cy: 0, r: 0.85 }), el('rect', { class: 'cano', x: -2.0, y: -0.1, width: 1.5, height: 0.2, rx: 0.09 })],
    { transform: `translate(${f(x)} ${f(y)}) rotate(${f(rot || 0)})`, class: 'oerlikon' });
}
/* a stack of platforms seen from straight above: each level is smaller than the
   one under it, and the shadow between them is what makes it read as height */
function tower(x, levels) {
  /* Seen from straight above a tower is just concentric outlines, and outlines
     alone read as a target. What makes it read as height is tone: every level
     is a step lighter than the one it stands on, and each drops a hard shadow
     on the deck below it. */
  const out = [];
  levels.forEach((lv, i) => {
    const n = Math.min(5, Math.round(1 + i * 4 / Math.max(1, levels.length - 1)));
    const r = lv.r === undefined ? Math.min(lv.l, lv.w) * 0.28 : lv.r;
    const box = { x: lv.x - lv.l / 2, y: -lv.w / 2, width: lv.l, height: lv.w, rx: r };
    if (i) out.push(el('rect', Object.assign({ class: 'nivel-sombra' }, box, { x: box.x + 0.55, y: box.y + 0.7 })));
    out.push(el('rect', Object.assign({ class: 'nivel n' + n }, box)));
  });
  return g(null, out, { transform: `translate(${f(x)} 0)`, class: 'torre-comando' });
}
function funnel(x, o) {
  const out = [
    el('ellipse', { class: 'chamine', cx: 0, cy: 0, rx: o.l / 2, ry: o.w / 2, transform: o.rot ? `rotate(${f(o.rot)})` : null }),
    el('ellipse', { class: 'chamine-boca', cx: o.cap || 0, cy: 0, rx: o.l / 2 - 1.0, ry: o.w / 2 - 1.0 }),
  ];
  if (o.grid) {                                   // Yamato's honeycomb cap, against a bomb going down the stack
    const r = o.w / 2 - 1.2;
    for (let j = -3; j <= 3; j++) for (let i = -4; i <= 4; i++) {
      const cx = (o.cap || 0) + i * 1.35 + (j % 2 ? 0.67 : 0), cy = j * 1.18;
      if ((cx - (o.cap || 0)) ** 2 / ((o.l / 2 - 1.2) ** 2) + cy * cy / (r * r) > 1) continue;
      out.push(el('circle', { class: 'favo', cx, cy, r: 0.5 }));
    }
  }
  return g(null, out, { transform: `translate(${f(x)} 0)`, class: 'chamines' });
}
function mast(x, o) {                              // a tripod or lattice, from above: legs + a platform
  const out = [];
  for (const leg of o.legs) out.push(el('circle', { class: 'mastro-pe', cx: leg[0], cy: leg[1], r: 0.55 }));
  out.push(el('path', { class: 'mastro-trelica', d: 'M' + pts(o.legs) + 'Z' }));
  if (o.top) out.push(el('rect', { class: 'plataforma', x: -o.top.l / 2, y: -o.top.w / 2, width: o.top.l, height: o.top.w, rx: 0.8 }));
  return g(null, out, { transform: `translate(${f(x)} 0)`, class: 'mastro' });
}
function crane(x, y, o) {                          // a boat/aircraft derrick, slewed outboard
  const s = Math.sign(y) || 1, a = (o.angle || 60) * s;
  return g(null, [
    el('circle', { class: 'guindaste-base', cx: 0, cy: 0, r: 1.5 }),
    el('path', { class: 'lanca', d: `M-0.9 -0.55L${f(o.len)} ${f(-0.30)}L${f(o.len)} ${f(0.30)}L-0.9 0.55Z`, transform: `rotate(${f(a)})` }),
    el('circle', { class: 'gancho', cx: Math.cos(a * Math.PI / 180) * o.len, cy: Math.sin(a * Math.PI / 180) * o.len, r: 0.45 }),
  ], { transform: `translate(${f(x)} ${f(y)})`, class: 'guindaste' });
}
function catapult(x, y, rot, len) {
  const out = [
    el('rect', { class: 'catapulta', x: -len * 0.5, y: -1.05, width: len, height: 2.1, rx: 0.3 }),
    el('rect', { class: 'catapulta-trilho', x: -len * 0.5 + 0.5, y: -0.55, width: len - 1.4, height: 1.1, rx: 0.2 }),
    el('rect', { class: 'catapulta-carro', x: len * 0.28, y: -1.3, width: 2.6, height: 2.6, rx: 0.35 }),
    el('circle', { class: 'catapulta-pivo', cx: -len * 0.5 + 1.2, cy: 0, r: 1.5 }),
  ];
  return g(null, out, { transform: `translate(${f(x)} ${f(y)}) rotate(${f(rot)})`, class: 'catapultas' });
}
/* a floatplane in plan. IJN = twin float (E13A "Jake"), USN = single central
   float with wingtip floats (OS2U Kingfisher) */
function floatplane(x, y, rot, o) {
  const span = o.span, len = o.len, c = len * 0.23, out = [];
  // the floats hang below everything, so they go down first
  if (o.twinFloat) for (const s of [-1, 1]) out.push(el('ellipse', { class: 'flutuador', cx: -len * 0.04, cy: s * span * 0.155, rx: len * 0.34, ry: len * 0.042 }));
  else {
    out.push(el('ellipse', { class: 'flutuador', cx: -len * 0.02, cy: 0, rx: len * 0.44, ry: len * 0.048 }));
    for (const s of [-1, 1]) out.push(el('ellipse', { class: 'flutuador', cx: 0, cy: s * span * 0.42, rx: len * 0.1, ry: len * 0.026 }));
  }
  // one wing panel, root chord c, tapering and swept back a little at the tip
  out.push(el('path', {
    class: 'aviao-asa',
    d: `M${f(-c * 0.5)} ${f(-span / 2)}L${f(c * 0.12)} ${f(-span / 2)}L${f(c * 0.5)} ${f(-span * 0.09)}` +
      `L${f(c * 0.5)} ${f(span * 0.09)}L${f(c * 0.12)} ${f(span / 2)}L${f(-c * 0.5)} ${f(span / 2)}Z`,
  }));
  out.push(el('ellipse', { class: 'aviao-fus', cx: 0, cy: 0, rx: len / 2, ry: len * 0.075 }));
  out.push(el('circle', { class: 'aviao-cowl', cx: -len * 0.42, cy: 0, r: len * 0.075 }));
  out.push(el('ellipse', { class: 'aviao-cabine', cx: len * 0.04, cy: 0, rx: len * 0.14, ry: len * 0.045 }));
  out.push(el('path', { class: 'aviao-asa', d: `M${f(len * 0.34)} ${f(-span * 0.19)}L${f(len * 0.46)} ${f(-span * 0.19)}L${f(len * 0.48)} 0L${f(len * 0.46)} ${f(span * 0.19)}L${f(len * 0.34)} ${f(span * 0.19)}Z` }));
  if (o.mark === 'hinomaru') for (const s of [-1, 1]) out.push(el('circle', { class: 'hinomaru', cx: len * 0.02, cy: s * span * 0.33, r: span * 0.055 }));
  if (o.mark === 'star') for (const s of [-1, 1]) out.push(el('circle', { class: 'estrela-us', cx: len * 0.02, cy: s * span * 0.33, r: span * 0.055 }));
  return g(null, out, { transform: `translate(${f(x)} ${f(y)}) rotate(${f(rot)})`, class: 'aviao' });
}
function boat(x, y, rot, len, bw, kind) {
  const half = [[-len / 2, 0], [-len * 0.36, -bw * 0.34], [-len * 0.1, -bw / 2], [len * 0.28, -bw / 2], [len * 0.46, -bw * 0.36], [len / 2, -bw * 0.13]];
  const full = half.concat(half.slice().reverse().map(p => [p[0], -p[1]]));
  const out = [el('path', { class: 'barco', d: smooth(full, true) })];
  if (kind !== 'raft') out.push(el('rect', { class: 'barco-cabine', x: -len * 0.04, y: -bw * 0.26, width: len * 0.3, height: bw * 0.52, rx: 0.3 }));
  return g(null, out, { transform: `translate(${f(x)} ${f(y)}) rotate(${f(rot || 0)})`, class: 'barcos' });
}
/* The breakwater: a chevron with its apex FORWARD, which is the whole point of
   it — it throws green water coming over the bow out to the sides before it
   reaches the turrets. Drawn as a stroked polyline so the arms keep an even
   thickness however wide the deck is. */
function breakwater(x, halfAt) {
  const arm = 5.0, y = halfAt(x + arm) - 2.0;
  return el('path', {
    class: 'quebra-mar', fill: 'none', 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
    d: `M${f(x + arm)} ${f(-y)}L${f(x)} 0L${f(x + arm)} ${f(y)}`,
  });
}
const vent = (x, y, r) => el('circle', { class: 'ventilador', cx: x, cy: y, r });
const hatch = (x, y, w, h) => el('rect', { class: 'escotilha', x: x - w / 2, y: y - h / 2, width: w, height: h, rx: 0.2 });
const bollard = (x, y) => el('circle', { class: 'cabeco', cx: x, cy: y, r: 0.42 });
const searchlight = (x, y, r) => g(null, [el('circle', { class: 'holofote-base', cx: 0, cy: 0, r: r * 1.25 }), el('circle', { class: 'holofote', cx: 0, cy: 0, r })], { transform: `translate(${f(x)} ${f(y)})` });
function raftRow(x0, x1, y, n) {
  const out = [];
  for (let i = 0; i < n; i++) out.push(el('rect', { class: 'balsa', x: x0 + (x1 - x0) * i / (n - 1) - 1.1, y: y - 0.45, width: 2.2, height: 0.9, rx: 0.42 }));
  return out.join('');
}
/* the mattress and the paddle: 1945 US radar is the most recognisable thing on
   an American ship from directly above */
function radarSK(x, y) {
  const out = [el('rect', { class: 'radar-tela', x: -2.6, y: -2.6, width: 5.2, height: 5.2, rx: 0.3 })];
  for (let i = -2; i <= 2; i++) {
    out.push(el('line', { class: 'radar-grade', x1: -2.6, y1: i * 1.05, x2: 2.6, y2: i * 1.05 }));
    out.push(el('line', { class: 'radar-grade', x1: i * 1.05, y1: -2.6, x2: i * 1.05, y2: 2.6 }));
  }
  return g(null, out, { transform: `translate(${f(x)} ${f(y)}) rotate(28)`, class: 'radar' });
}
const radarBar = (x, y, w, h, rot) => el('rect', { class: 'radar-tela', x: -w / 2, y: -h / 2, width: w, height: h, rx: 0.25, transform: `translate(${f(x)} ${f(y)}) rotate(${f(rot || 0)})` });
function director(x, y, o) {                       // a gun director with its radar on top
  const out = [el('circle', { class: 'diretor', cx: 0, cy: 0, r: o.r })];
  if (o.rf) out.push(el('rect', { class: 'telemetro', x: -0.7, y: -o.rf / 2, width: 1.4, height: o.rf, rx: 0.45 }));
  if (o.radar) out.push(radarBar(o.r * 0.2, 0, 1.1, o.radar, 0));
  return g(null, out, { transform: `translate(${f(x)} ${f(y)}) rotate(${f(o.rot || 0)})`, class: 'diretores' });
}

/* ------------------------------------------------------------- the palette
   Every colour the drawing uses, once, at the top. Re-skinning the ship is
   editing this block and nothing else. */
const PALETTE = {
  
  yamato: `
    --casco:#5d6660; --casco-borda:#2e3531; --casco-baixo:#495049;
    --conves:#a08a62; --conves-veio:#6d5a3c; --conves-junta:#7d6a48;
    --aco:#697370; --aco-alto:#7b8481; --aco-baixo:#4b5350;
    --aco-1:#4f5855; --aco-2:#5a6360; --aco-3:#67716d; --aco-4:#757f7a; --aco-5:#838d87;
    --torre:#646e69; --torre-topo:#727c76; --barbeta:#4e5652; --cano:#3b423e;
    --lona:#8e8877; --reparo:#5f6965; --aa:#59625e; --diretor:#6d7773;
    --linoleo:#6b563d; --latao:#b08b4a; --vidro:#93a6a4;
    --sombra:rgba(6,10,9,.55); --linha:rgba(18,24,22,.55); --luz:rgba(255,252,240,.20);
    --hinomaru:#b9302a; --ouro:#c9a24a; --agua:#0d2231;`,
  iowa: `
    --casco:#5a6572; --casco-borda:#242b33; --casco-baixo:#464f5a;
    --conves:#49515c; --conves-veio:#333b45; --conves-junta:#3c444e;
    --aco:#7c8794; --aco-alto:#8d97a3; --aco-baixo:#5a6570;
    --aco-1:#5e6873; --aco-2:#6b7581; --aco-3:#78838f; --aco-4:#86909d; --aco-5:#939dab;
    --torre:#77828e; --torre-topo:#848f9b; --barbeta:#5b6570; --cano:#484f58;
    --lona:#8c8f92; --reparo:#6e7985; --aa:#68727e; --diretor:#7f8a96;
    --linoleo:#4a525c; --latao:#9b8a5e; --vidro:#9fb0bd;
    --sombra:rgba(6,9,13,.55); --linha:rgba(16,20,26,.55); --luz:rgba(255,255,255,.16);
    --hinomaru:#b9302a; --ouro:#b6903f; --agua:#0d2231;`,
};

/* The deck. Planks run fore and aft, about 20 cm wide, with the butt joints of
   one row staggered against the next — which is what a wooden deck actually
   looks like from a mast top, and what makes the scale of everything else
   readable. Two plank rows per tile so the stagger comes for free. */
const PLANKS = el('pattern', { id: 'tabuado', width: 7.2, height: 0.44, patternUnits: 'userSpaceOnUse' }, [
  el('rect', { width: 7.2, height: 0.44, fill: 'var(--conves)' }),
  el('line', { x1: 0, y1: 0.22, x2: 7.2, y2: 0.22, stroke: 'var(--conves-veio)', 'stroke-width': 0.05, opacity: 0.85 }),
  el('line', { x1: 0, y1: 0.44, x2: 7.2, y2: 0.44, stroke: 'var(--conves-veio)', 'stroke-width': 0.05, opacity: 0.85 }),
  el('line', { x1: 0.2, y1: 0, x2: 0.2, y2: 0.22, stroke: 'var(--conves-junta)', 'stroke-width': 0.07 }),
  el('line', { x1: 3.8, y1: 0.22, x2: 3.8, y2: 0.44, stroke: 'var(--conves-junta)', 'stroke-width': 0.07 }),
].join(''));

const CSS = `
  .casco{fill:var(--casco);stroke:var(--casco-borda);stroke-width:.30}
  .casco-sombra{fill:var(--sombra)}
  .conves{fill:url(#tabuado)}
  .conves-aco{fill:var(--aco-1)}
  .conves-aviacao{fill:var(--aco-2);stroke:var(--linha);stroke-width:.18}
  .linoleo{fill:var(--linoleo)}
  .borda-conves{fill:none;stroke:var(--casco-borda);stroke-width:.22;opacity:.75}
  .quebra-mar{stroke:var(--aco-2);stroke-width:.85}
  .corrente{fill:none;stroke:var(--linha);stroke-width:.55;stroke-dasharray:.55 .34;opacity:.85}
  .trilho{stroke:var(--aco-baixo);stroke-width:.22;opacity:.9}
  .ancora{fill:var(--aco-baixo);stroke:var(--linha);stroke-width:.16}
  .cabeco{fill:var(--aco-baixo)}
  .ventilador{fill:var(--aco);stroke:var(--linha);stroke-width:.14}
  .escotilha{fill:var(--aco-baixo);stroke:var(--linha);stroke-width:.12}
  .balsa{fill:var(--lona);stroke:var(--linha);stroke-width:.12;opacity:.9}
  .barbeta{fill:var(--barbeta);stroke:var(--linha);stroke-width:.25}
  .torre{fill:var(--torre);stroke:var(--linha);stroke-width:.26}
  .torre-topo{fill:var(--torre-topo);stroke:none;opacity:.55}
  .cano{fill:var(--cano)}
  .cano-luz{stroke:var(--luz);stroke-width:.16}
  .lona{fill:var(--lona);opacity:.85}
  .telemetro{fill:var(--diretor);stroke:var(--linha);stroke-width:.14}
  .telemetro-cabeca{fill:var(--aco-baixo);stroke:var(--linha);stroke-width:.12}
  .cupula{fill:var(--aco-alto);stroke:var(--linha);stroke-width:.14}
  .nivel{fill:var(--aco);stroke:var(--linha);stroke-width:.2}
  .n1{fill:var(--aco-1)} .n2{fill:var(--aco-2)} .n3{fill:var(--aco-3)} .n4{fill:var(--aco-4)} .n5{fill:var(--aco-5)}
  .nivel-sombra{fill:var(--sombra);stroke:none}
  .chamine{fill:var(--aco-baixo);stroke:var(--linha);stroke-width:.3}
  .chamine-boca{fill:#20262a}
  .favo{fill:var(--aco-baixo);opacity:.85}
  .mastro-trelica{fill:var(--aco);opacity:.5;stroke:var(--linha);stroke-width:.14}
  .mastro-pe{fill:var(--aco-baixo)}
  .plataforma{fill:var(--aco);stroke:var(--linha);stroke-width:.16}
  .reparo-base{fill:var(--aco-baixo)}
  .reparo{fill:var(--reparo);stroke:var(--linha);stroke-width:.16}
  .aa-base{fill:var(--aco-baixo)}
  .aa-tina{fill:var(--aco-2);stroke:var(--linha);stroke-width:.2}
  .aa{fill:var(--aa);stroke:var(--linha);stroke-width:.12}
  .diretor{fill:var(--diretor);stroke:var(--linha);stroke-width:.18}
  .radar-tela{fill:var(--aco-alto);stroke:var(--linha);stroke-width:.14;opacity:.92}
  .radar-grade{stroke:var(--aco-baixo);stroke-width:.16}
  .guindaste-base{fill:var(--aco-baixo)}
  .lanca{fill:var(--aco);stroke:var(--linha);stroke-width:.14}
  .gancho{fill:var(--aco-baixo)}
  .catapulta{fill:var(--aco-baixo);stroke:var(--linha);stroke-width:.18}
  .catapulta-trilho{fill:var(--aco);opacity:.75}
  .catapulta-carro{fill:var(--aco-alto);stroke:var(--linha);stroke-width:.14}
  .catapulta-pivo{fill:var(--aco-baixo);stroke:var(--linha);stroke-width:.14}
  .barco{fill:var(--lona);stroke:var(--linha);stroke-width:.14;opacity:.55}
  .paiol-botes{fill:var(--aco-1);stroke:var(--linha);stroke-width:.25}
  .paiol-abertura{fill:#1d2225}
  .paiol-porta{fill:var(--aco-3);stroke:var(--linha);stroke-width:.16}
  .barco-cabine{fill:var(--aco-baixo);opacity:.8}
  .aviao-fus{fill:var(--aco-5);stroke:var(--linha);stroke-width:.14}
  .aviao-asa{fill:var(--aco-2);stroke:var(--linha);stroke-width:.14}
  .aviao-cowl{fill:var(--aco-1)}
  .aviao-cabine{fill:var(--vidro);opacity:.7}
  .flutuador{fill:var(--aco-1);stroke:var(--linha);stroke-width:.1}
  .hinomaru{fill:var(--hinomaru)}
  .estrela-us{fill:#20356b}
  .holofote{fill:var(--vidro)}
  .holofote-base{fill:var(--aco-baixo)}
  .kikumon{fill:var(--ouro)}
  .rotulo{font:1.6px Georgia,serif;fill:var(--aco-alto)}
`;

/* --------------------------------------------------------------- the ships */

/* Yamato, measured off the builders' plan NH 111711 (Naval History & Heritage
   Command, public domain) — the Japanese sheet that carries a profile and a
   plan of the ship as completed, with her characteristics tabulated.
   The hull run on that sheet is 4.584 px for 263 m, which is 17,43 px/m; the
   beam measures 689 px, which at that scale is 39,5 m against a stated 38,9 —
   a 1,5% overshoot that is the thickness of the ink. Everything below was read
   off the sheet with a metre rule laid over it and then scaled by 0,983 so the
   maximum breadth comes out at the stated figure.
      fit: '1941' is the sheet's own fit — four 15.5 cm triples, six twin
      12.7 cm, eight triple 25 mm.  '1945' is the ship that sailed for Okinawa:
      the beam 15.5 cm turrets landed in 1943 and the light AA multiplied. */
function yamato(fit) {
  fit = fit || '1945';
  const L = 263.0, B = 38.9;
  /* Half-breadths traced off the plan every 5 m and scaled. The correction
     that matters: she carries her full beam from 130 m all the way aft to
     210 m, and the bow is far finer than it looks — 11 m of breadth at 50 m
     from the stem, not 16. */
  const H = hullMaker([
    [0, 0], [4, 1.4], [10, 3.2], [18, 5.9], [26, 7.3], [34, 8.6], [42, 9.9],
    [50, 11.1], [58, 12.5], [66, 13.9], [74, 15.2], [82, 16.1], [90, 17.0],
    [98, 17.7], [106, 18.2], [114, 18.7], [124, 19.1], [136, 19.35],
    [150, 19.42], [170, 19.45], [190, 19.45], [204, 19.3], [214, 18.9],
    [220, 17.0], [228, 16.6], [236, 15.8], [243, 14.2], [249, 10.8],
    [254, 7.9], [258, 5.4], [261, 2.8], [263, 0],
  ]);
  const edge = x => H.halfAt(x);
  /* Stations read off the sheet. The whole forward group sat some 18 m too far
     forward before this: turret 1 is at 81 m, not 61, and her guns trained
     ahead reach only to 59 m from the stem. */
  const T = { n1: 81, n2: 102, sf: 118, br: 133, fn: 153, mm: 165, ap: 173, sa: 181, n3: 198, wing: 148 };
  const QD = 219;                                     // where the deck steps down to the quarterdeck

  /* --- deck --- */
  const conves = [];
  conves.push(el('path', { class: 'conves', d: H.inset(0.55) }));
  conves.push(el('rect', { class: 'conves-aco', x: T.sf + 2, y: -12.5, width: 70, height: 25, rx: 3 }));   // the steel amidships deck
  {                                                       // the quarterdeck, cut to the deck edge so it cannot run outside the hull
    const qs = [];
    for (let x = QD; x <= L - 5; x += 3) qs.push([x, -(edge(x) - 1.1)]);
    for (let x = L - 5; x >= QD; x -= 3) qs.push([x, edge(x) - 1.1]);
    conves.push(el('path', { class: 'conves-aco', d: smooth(qs, true) }));
  }
  conves.push(el('path', { class: 'borda-conves', d: H.inset(0.55) }));

  /* --- forecastle --- */
  const proa = [];
  proa.push(el('path', { class: 'kikumon', d: `M2.2 0m-1.6 0a1.6 1.6 0 1 0 3.2 0a1.6 1.6 0 1 0 -3.2 0` }));
  for (const s of [-1, 1]) {
    proa.push(el('path', { class: 'corrente', d: `M${f(7)} ${f(s * 1.9)}Q${f(20)} ${f(s * 4.0)} ${f(34)} ${f(s * 3.6)}` }));
    proa.push(el('rect', { class: 'ancora', x: 5.4, y: s * 1.9 - 1.0, width: 3.0, height: 2.0, rx: 0.4 }));
    proa.push(el('circle', { class: 'ventilador', cx: 35, cy: s * 3.6, r: 1.5 }));      // windlass
    for (let i = 0; i < 7; i++) proa.push(bollard(14 + i * 7, s * (edge(14 + i * 7) - 1.4)));
  }
  proa.push(breakwater(T.n1 - 15, edge));
  for (let i = 0; i < 9; i++) { const x = 22 + i * 4.6; proa.push(vent(x, 0, 0.7)); }
  proa.push(hatch(66, 0, 2.6, 3.4));

  /* --- main battery: three triple 46 cm. 45 calibres makes a 20.7 m gun, of
     which 15.5 m stands out ahead of the face. --- */
  /* The gun house measures 16 m on the plan, with the barbette centre 6 m back
     from the face, and the guns stand 15,8 m proud of it. That puts turret 1's
     muzzles at 59 m from the stem, which is exactly where the sheet has them. */
  const G46 = { faceW: 12.6, midW: 15.2, rearW: 13.2, fwd: 6.0, aft_: 10.5, barbette: 13.3, guns: 3, spacing: 3.05, cal: 46, barrelProj: 15.8, rf: 15.0, rfBack: 2.8 };
  const torres = [
    mainTurret(Object.assign({ id: 'torre-1', x: T.n1 }, G46)),
    mainTurret(Object.assign({ id: 'torre-2', x: T.n2 }, G46)),
    mainTurret(Object.assign({ id: 'torre-3', x: T.n3, aft: true }, G46)),
  ];
  /* One 15.5 cm triple superfiring forward and one aft. In 1941 there were two
     more on the beam, abreast the funnel; they went ashore in 1943 so their
     barbettes could carry 12.7 cm and 25 mm instead. */
  const S155 = { len: 9.2, w: 7.6, barbette: 6.6, guns: 3, spacing: 1.55, cal: 15.5, barrelProj: 7.2 };
  torres.push(secTurret(Object.assign({ id: 'sec-proa', x: T.sf }, S155)));
  torres.push(secTurret(Object.assign({ id: 'sec-popa', x: T.sa, aft: true }, S155)));
  if (fit === '1941') for (const s of [-1, 1])
    torres.push(secTurret(Object.assign({ id: 'sec-asa' + (s < 0 ? 'b' : 'e'), x: T.wing, y: s * 11.5, rot: s * 90 }, S155)));

  /* --- the pagoda: the tower seen from above is a stack of shrinking rings --- */
  const sup = [];
  sup.push(tower(T.br, [
    { x: 0, l: 22, w: 15.5, r: 3.2 },
    { x: 0.8, l: 16.5, w: 12.4, r: 3.0 },
    { x: 1.4, l: 12, w: 9.8, r: 2.8 },
    { x: 1.9, l: 8.4, w: 7.6, r: 2.6 },
    { x: 2.3, l: 5.8, w: 5.6, r: 2.4 },
  ]));
  sup.push(el('rect', { class: 'telemetro', x: T.br + 0.5, y: -7.5, width: 1.8, height: 15, rx: 0.6 }));  // the 15 m rangefinder on the top
  sup.push(director(T.br + 2.5, 0, { r: 2.4, rf: 0 }));
  for (const s of [-1, 1]) {
    sup.push(director(T.br - 7, s * 8.5, { r: 1.9, rf: 4.5, rot: 90 }));                      // 12.7 cm directors
    sup.push(director(T.br + 9.5, s * 8.0, { r: 1.7 }));                                      // 25 mm directors
    sup.push(searchlight(T.fn - 9, s * 9.5, 0.9));
    sup.push(searchlight(T.fn + 7, s * 9.5, 0.9));
  }
  // the single raked funnel, with the honeycomb grating over its mouth
  sup.push(funnel(T.fn, { l: 15.5, w: 10.5, grid: true, cap: 0.6 }));
  sup.push(mast(T.mm, { legs: [[-3.2, -3.6], [-3.2, 3.6], [4.0, 0]], top: { l: 5.0, w: 5.0 } }));
  // the after command post, between the mainmast and the after 15.5 cm turret
  sup.push(tower(T.ap, [{ x: 0, l: 15, w: 12.5, r: 3.4 }, { x: 0.8, l: 10, w: 8.6, r: 3 }, { x: 1.2, l: 6.4, w: 6.0, r: 2.6 }]));
  sup.push(el('rect', { class: 'telemetro', x: T.ap + 0.6, y: -5.2, width: 1.6, height: 10.4, rx: 0.5 }));
  sup.push(director(T.ap + 2, 0, { r: 1.9 }));
  /* The boats. Every other battleship of the war stowed hers on the upper deck
     amidships, in plain sight from above — and that is where I had put them,
     which was wrong twice over.
     Yamato's 46 cm guns threw a blast that wrecked anything left standing on
     deck, so she was given something no other battleship had: an enclosed
     stowage aft that the boats were hauled back into.
       呉市海事歴史科学館: 「つんである短艇をしまうための倉庫をつくり、
       引き込んで格納することにした」
     So from directly above there are no boats to see. What there is, is the
     stowage itself, on the centreline right aft, and the derrick that worked
     them. */
  const deck = [];
  deck.push(el('rect', { class: 'paiol-botes', x: 238, y: -4.6, width: 19, height: 9.2, rx: 1.4 }));
  deck.push(el('rect', { class: 'paiol-abertura', x: 239.5, y: -3.4, width: 16, height: 6.8, rx: 1.0 }));
  for (const s of [-1, 1]) {                          // the boats, inside, barely showing
    deck.push(boat(246, s * 1.9, 0, 11.5, 2.6));
    deck.push(boat(240.5, s * 1.9, 0, 8.0, 2.2));
  }
  deck.push(el('rect', { class: 'paiol-porta', x: 255.6, y: -3.4, width: 1.6, height: 6.8, rx: 0.4 }));
  deck.push(crane(231, 10.5, { len: 13, angle: 128 }));  // the derrick that worked them, starboard quarter

  /* --- 1945 anti-aircraft: twelve twin 12.7 cm and fifty-two triple 25 mm.
     The twins ride the superstructure deck edge, the 25s fill every flat
     surface that was left, which is exactly what happened in refit. --- */
  const aa = [];
  const dpX = fit === '1941' ? [137, 151, 165] : [124, 136, 148, 160, 172, 184];
  for (const x of dpX) for (const s of [-1, 1]) aa.push(twinDP(x, s * (edge(x) - 5.0), s > 0 ? 90 : -90, 12.7));
  const aaSpots = [];
  if (fit === '1941') {                               // eight triple 25 mm, all of them grouped about the funnel
    for (const x of [143, 159]) for (const s of [-1, 1]) aaSpots.push([x, s * 7.6]);
    for (const x of [128, 172]) for (const s of [-1, 1]) aaSpots.push([x, s * 9.2]);
  } else {
    for (const x of [68, 74, 90, 96, 112, 118]) for (const s of [-1, 1]) aaSpots.push([x, s * (edge(x) - 3.0)]);  // forecastle, around turrets 1 and 2
    for (let i = 0; i < 11; i++) { const x = 120 + i * 7.4; for (const s of [-1, 1]) aaSpots.push([x, s * (edge(x) - 1.6)]); }   // the long sponson rows
    for (const x of [128, 142, 156, 170, 184]) for (const s of [-1, 1]) aaSpots.push([x, s * 10.4]);              // inboard of the boat deck
    for (const x of [192, 206, 212]) for (const s of [-1, 1]) aaSpots.push([x, s * (edge(x) - 3.2)]);             // abreast turret 3
    for (const x of [T.br - 11, T.br + 13]) for (const s of [-1, 1]) aaSpots.push([x, s * 12.5]);
    aaSpots.push([T.n2 + 8, 0], [T.n1 - 12, 0]);
  }
  for (const p of aaSpots) aa.push(aa25(p[0], p[1], p[1] < 0 ? -90 : p[1] > 0 ? 90 : 0));

  /* --- aviation: the quarterdeck. Two 19 m catapults trained outboard, the
     handling crane on the centreline, rails to the hangar lift. --- */
  /* The quarterdeck begins where turret 3's guns end when they are trained
     aft — 202 + 7 + 15.5 = 224.5 m — which is exactly why the aircraft deck
     starts there and not a metre further forward. */
  const av = [];
  for (const s of [-1, 1]) {
    av.push(catapult(243, s * 9.0, s * 12, 19.2));
    // the handling rails the trolleys ran on, from the hangar lift out to each catapult
    for (const off of [-0.55, 0.55]) av.push(el('path', {
      class: 'trilho', fill: 'none',
      d: `M${f(226)} ${f(s * 2.6 + off)}Q${f(234)} ${f(s * 7.4 + off)} ${f(249)} ${f(s * 8.6 + off)}`,
    }));
  }
  av.push(el('circle', { class: 'escotilha', cx: 226, cy: 0, r: 2.4 }));          // the lift to the hangar
  if (fit === '1941') {                               // on the Ten-Go sortie she carried none
    av.push(floatplane(232, -6.6, 16, { span: 14.5, len: 11.3, twinFloat: true, mark: 'hinomaru' }));
    av.push(floatplane(232, 6.6, -16, { span: 14.5, len: 11.3, twinFloat: true, mark: 'hinomaru' }));
  }
  for (const s of [-1, 1]) { av.push(bollard(L - 8, s * 2.6)); av.push(bollard(L - 4.5, s * 1.8)); }
  av.push(el('rect', { class: 'ancora', x: L - 7.5, y: -1.0, width: 2.6, height: 2.0, rx: 0.4 }));

  /* --- odds and ends that sell the scale: vents, hatches, life rafts --- */
  const misc = [];
  for (const s of [-1, 1]) {
    misc.push(raftRow(116, 206, s * 17.2, 13));
    for (let i = 0; i < 9; i++) misc.push(vent(124 + i * 8, s * 6.4, 0.75));
    for (let i = 0; i < 4; i++) misc.push(hatch(170 + i * 10, s * 3.2, 1.8, 2.4));
  }
  return { id: fit === '1941' ? 'yamato-1941' : 'yamato', L, B, H, layers: { conves, proa, torres, sup, deck, aa, av, misc } };
}

function iowa() {
  const L = 270.4, B = 33.0;
  /* The long fine clipper bow is the whole shape of this ship: she carries a
     third less beam than Yamato over seven more metres of length, because the
     Panama locks were 33.53 m wide. */
  const H = hullMaker([
    [0, 0], [6, 0.7], [14, 1.7], [24, 3.0], [36, 4.9], [50, 7.0], [66, 9.4],
    [84, 11.7], [102, 13.6], [120, 15.1], [140, 16.2], [158, 16.5], [176, 16.4],
    [193, 16.0], [208, 15.2], [222, 14.0], [235, 12.3], [247, 10.2], [257, 7.7],
    [264, 5.2], [268.5, 2.6], [270.4, 0],
  ]);
  const edge = x => H.halfAt(x);
  const T = { n1: 66, n2: 87, br: 114, f1: 130, f2: 156, mm: 172, ct: 188, n3: 206 };

  const conves = [];
  conves.push(el('path', { class: 'conves', d: H.inset(0.5) }));
  conves.push(el('rect', { class: 'conves-aco', x: 98, y: -13, width: 92, height: 26, rx: 3 }));
  conves.push(el('path', { class: 'borda-conves', d: H.inset(0.5) }));

  const proa = [];
  for (const s of [-1, 1]) {
    proa.push(el('path', { class: 'corrente', d: `M${f(10)} ${f(s * 1.3)}Q${f(26)} ${f(s * 3.0)} ${f(44)} ${f(s * 2.6)}` }));
    proa.push(el('rect', { class: 'ancora', x: 8.0, y: s * 1.3 - 0.9, width: 2.8, height: 1.8, rx: 0.4 }));
    proa.push(el('circle', { class: 'ventilador', cx: 45, cy: s * 2.6, r: 1.4 }));
    for (let i = 0; i < 6; i++) proa.push(bollard(16 + i * 6, s * (edge(16 + i * 6) - 1.4)));
  }
  proa.push(breakwater(T.n1 - 23, edge));
  for (let i = 0; i < 7; i++) proa.push(vent(24 + i * 5, 0, 0.65));

  /* the 16"/50 Mk 7: fifty calibres of 40.6 cm is 20.3 m of gun, within a
     couple of decimetres of Yamato's shorter, fatter 46 cm/45 */
  const G16 = { faceW: 12.2, midW: 13.1, rearW: 11.8, fwd: 6.2, aft_: 12.1, barbette: 11.6, guns: 3, spacing: 2.97, cal: 40.6, barrelProj: 15.0, rfBack: 2.6 };
  const torres = [
    mainTurret(Object.assign({ id: 'torre-1', x: T.n1 }, G16)),
    mainTurret(Object.assign({ id: 'torre-2', x: T.n2, rf: 13.7 }, G16)),
    mainTurret(Object.assign({ id: 'torre-3', x: T.n3, aft: true, rf: 13.7 }, G16)),
  ];

  const sup = [];
  // the armoured conning tower and the bridge levels around it
  sup.push(tower(T.br, [
    { x: 0, l: 21, w: 14, r: 2.6 },
    { x: -0.8, l: 15.5, w: 11, r: 2.4 },
    { x: -1.6, l: 10.5, w: 8.6, r: 2.4 },
    { x: -2.4, l: 6.8, w: 6.4, r: 2.8 },
  ]));
  sup.push(el('circle', { class: 'nivel', cx: T.br - 5, cy: 0, r: 2.6 }));                    // conning tower
  sup.push(director(T.br + 6, 0, { r: 3.0, radar: 4.6 }));                                    // Mk 37 with Mk 12/22
  sup.push(director(T.n2 + 16, 0, { r: 2.6, radar: 5.0 }));                                   // forward Mk 38 with Mk 8
  sup.push(director(T.ct + 6, 0, { r: 2.6, radar: 5.0 }));                                    // after Mk 38
  sup.push(radarSK(T.br + 8.5, 0));                                                            // SK air search, the bedspring
  sup.push(radarBar(T.br + 12.5, 0, 3.4, 1.0, 62));                                             // SG surface search
  sup.push(funnel(T.f1, { l: 9.0, w: 8.2, cap: 0 }));
  sup.push(funnel(T.f2, { l: 9.0, w: 8.2, cap: 0 }));
  sup.push(mast(T.mm, { legs: [[-3.6, -3.2], [3.6, -2.2], [3.6, 2.2], [-3.6, 3.2]], top: { l: 4.2, w: 4.6 } }));
  sup.push(radarBar(T.mm, 0, 3.0, 0.9, 18));
  sup.push(tower(T.ct, [{ x: 0, l: 17, w: 13, r: 3.0 }, { x: 0, l: 11, w: 9, r: 2.8 }]));
  for (const s of [-1, 1]) {
    sup.push(director(T.f1 + 8, s * 7.8, { r: 2.4, radar: 4.0, rot: 90 * s }));                // wing Mk 37s
    sup.push(director(T.ct - 4, s * 7.4, { r: 2.4, radar: 4.0, rot: 90 * s }));
    sup.push(searchlight(T.f2 - 6, s * 8.4, 0.9));
  }

  const deck = [];
  for (const s of [-1, 1]) {
    deck.push(crane(T.mm + 10, s * 8.6, { len: 11, angle: 60 }));
    for (let i = 0; i < 4; i++) deck.push(boat(T.f1 + 6 + i * 9, s * 11.6, 0, 8 + (i % 2) * 2, 2.3));
  }

  /* ten twin 5"/38 — five a side, the tightest secondary battery of the war —
     twenty quad Bofors and a rank of Oerlikons along both deck edges */
  const aa = [];
  for (const x of [104, 120, 140, 160, 178]) for (const s of [-1, 1]) aa.push(twinDP(x, s * 12.6, s > 0 ? 90 : -90, 12.7));
  const bof = [];
  for (const x of [T.n2 + 10, T.n2 + 10]) void x;
  for (const s of [-1, 1]) {
    bof.push([56, s * 6.0], [T.n2 + 12, s * 9.0]);
    for (let i = 0; i < 6; i++) bof.push([110 + i * 13, s * 15.4]);
    bof.push([T.ct - 12, s * 12.0], [T.n3 + 16, s * 9.6]);
  }
  bof.push([236, 0], [T.n1 - 26, 0]);
  for (const p of bof) aa.push(bofors(p[0], p[1], p[1] < 0 ? -90 : p[1] > 0 ? 90 : 0));
  for (const s of [-1, 1]) {
    for (let i = 0; i < 14; i++) {
      const x = 52 + i * 12.5;
      aa.push(oerlikon(x, s * (edge(x) - 1.9), s > 0 ? 90 : -90));
    }
  }

  /* aviation on the fantail: two catapults over the transom, the crane between
     them, and the Kingfishers that spotted for the 16 inch guns */
  const av = [];
  for (const s of [-1, 1]) av.push(catapult(L - 15, s * 6.2, s * 14, 21.0));
  av.push(crane(L - 37, 0, { len: 11, angle: 158 }));
  av.push(el('circle', { class: 'escotilha', cx: L - 40, cy: 0, r: 2.4 }));
  av.push(floatplane(L - 29, -5.8, 14, { span: 10.9, len: 10.3, mark: 'star' }));
  av.push(floatplane(L - 29, 5.8, -14, { span: 10.9, len: 10.3, mark: 'star' }));
  for (const s of [-1, 1]) { av.push(bollard(L - 9, s * 2.2)); av.push(bollard(L - 5, s * 1.5)); }

  const misc = [];
  for (const s of [-1, 1]) {
    misc.push(raftRow(100, 196, s * 13.8, 12));
    for (let i = 0; i < 8; i++) misc.push(vent(108 + i * 9, s * 5.4, 0.7));
    for (let i = 0; i < 4; i++) misc.push(hatch(150 + i * 11, s * 2.6, 1.6, 2.2));
  }
  return { id: 'iowa', L, B, H, layers: { conves, proa, torres, sup, deck, aa, av, misc } };
}

/* ------------------------------------------------------------ assembly */
function shipGroup(s, showLegend) {
  const Ly = s.layers;
  const body = [
    g('sombra-casco', el('path', { class: 'casco-sombra', d: s.H.outline(), transform: 'translate(0.9 1.1)' })),
    g('casco', el('path', { class: 'casco', d: s.H.outline() })),
    g('conves', Ly.conves),
    g('proa', Ly.proa),
    g('miudezas', Ly.misc),
    g('barcos', Ly.deck, { filter: 'url(#relevo)' }),
    g('aviacao', Ly.av, { filter: 'url(#relevo)' }),
    g('superestrutura', Ly.sup, { filter: 'url(#relevo)' }),
    g('artilharia', Ly.torres, { filter: 'url(#relevo-grande)' }),
    g('antiaerea', Ly.aa, { filter: 'url(#relevo)' }),
  ];
  return g(s.id, body);
}
function svgFor(s) {
  const M = MARGIN, w = s.L + 2 * M, h = s.B + 2 * M;
  const defs = el('defs', {}, [
    el('style', {}, `svg{${PALETTE[s.id] || PALETTE[s.id.split('-')[0]]}}` + CSS),
    PLANKS,
    el('filter', { id: 'relevo', x: '-20%', y: '-40%', width: '140%', height: '180%' },
      el('feDropShadow', { dx: 0.5, dy: 0.7, stdDeviation: 0.35, 'flood-color': 'var(--sombra)', 'flood-opacity': 0.85 })),
    el('filter', { id: 'relevo-grande', x: '-20%', y: '-40%', width: '140%', height: '180%' },
      el('feDropShadow', { dx: 0.8, dy: 1.1, stdDeviation: 0.5, 'flood-color': 'var(--sombra)', 'flood-opacity': 0.85 })),
  ]);
  return el('svg', {
    xmlns: 'http://www.w3.org/2000/svg', viewBox: `${f(-M)} ${f(-h / 2)} ${f(w)} ${f(h)}`,
    width: Math.round(w * PX_PER_M), height: Math.round(h * PX_PER_M),
  }, defs + shipGroup(s));
}

/* the comparison sheet: both hulls on one page, to the same scale, which is the
   only honest way to show that Iowa is the longer ship and Yamato the bigger one */
function comparison(a, b) {
  const M = 14, w = Math.max(a.L, b.L) + 2 * M, gap = 26;
  const h = a.B / 2 + gap + b.B / 2 + 2 * M + 26;
  const defs = el('defs', {}, [
    el('style', {}, `svg{${PALETTE.yamato}} #iowa{${PALETTE.iowa}}` + CSS + `
      .nome{font:6px Georgia,serif;fill:#e8dfc8}
      .sub{font:3.1px Georgia,serif;fill:#9db6c6;font-style:italic}
      .cota{font:2.7px Georgia,serif;fill:#9db6c6}
      .regua{stroke:#9db6c6;stroke-width:.35;fill:none}
      .fundo{fill:var(--agua)}`),
    el('filter', { id: 'relevo', x: '-20%', y: '-40%', width: '140%', height: '180%' },
      el('feDropShadow', { dx: 0.5, dy: 0.7, stdDeviation: 0.35, 'flood-color': 'rgba(4,8,12,.6)' })),
    el('filter', { id: 'relevo-grande', x: '-20%', y: '-40%', width: '140%', height: '180%' },
      el('feDropShadow', { dx: 0.8, dy: 1.1, stdDeviation: 0.5, 'flood-color': 'rgba(4,8,12,.6)' })),
  ]);
  const yTop = M + a.B / 2, yBot = yTop + gap + b.B / 2;
  const lbl = (s, y, name, ja, stats) => [
    el('text', { class: 'nome', x: 2, y: y - s.B / 2 - 7.5 }, name + (ja ? ` <tspan class="sub">${ja}</tspan>` : '')),
    el('text', { class: 'sub', x: 2, y: y - s.B / 2 - 3.2 }, stats),
  ].join('');
  const rule = y => {
    const out = [el('line', { class: 'regua', x1: 0, y1: y, x2: 300, y2: y })];
    for (let m = 0; m <= 300; m += 10) out.push(el('line', { class: 'regua', x1: m, y1: y, x2: m, y2: y + (m % 50 ? 1.4 : 3) }));
    for (let m = 0; m <= 300; m += 50) out.push(el('text', { class: 'cota', x: m, y: y + 6.5, 'text-anchor': 'middle' }, m + ' m'));
    return out.join('');
  };
  return el('svg', {
    xmlns: 'http://www.w3.org/2000/svg', viewBox: `${f(-M)} 0 ${f(w)} ${f(h)}`,
    width: Math.round(w * 10), height: Math.round(h * 10),
  }, defs
    + el('rect', { class: 'fundo', x: -M, y: 0, width: w, height: h })
    + lbl(a, yTop, 'Yamato', '大和', `1941 · 263,0 × 38,9 m · 72.800 t · 27 nós · 9 × 46 cm · 2.767 homens`)
    + el('g', { transform: `translate(0 ${f(yTop)})` }, shipGroup(a))
    + lbl(b, yBot, 'Iowa', '', `1943 · 270,4 × 33,0 m · 57.540 t · 33 nós · 9 × 40,6 cm · 2.788 homens`)
    + el('g', { transform: `translate(0 ${f(yBot)})`, id: 'iowa' }, shipGroup(b))
    + el('g', { transform: `translate(0 ${f(h - 12)})` }, rule(0)));
}

/* -------------------------------------------------------------------- run */
const Y = yamato('1945'), Y41 = yamato('1941'), I = iowa();
fs.writeFileSync(path.join(ROOT, 'yamato.svg'), svgFor(Y));
fs.writeFileSync(path.join(ROOT, 'yamato-1941.svg'), svgFor(Y41));
fs.writeFileSync(path.join(ROOT, 'iowa.svg'), svgFor(I));
fs.writeFileSync(path.join(ROOT, 'comparacao.svg'), comparison(Y, I));
for (const n of ['yamato.svg', 'yamato-1941.svg', 'iowa.svg', 'comparacao.svg']) {
  const p = path.join(ROOT, n);
  console.log(`  ${n.padEnd(16)} ${(fs.statSync(p).size / 1024).toFixed(0)} KB`);
}
console.log(`  Yamato ${Y.L} x ${Y.B} m   Iowa ${I.L} x ${I.B} m   (${PX_PER_M} px/m)`);
