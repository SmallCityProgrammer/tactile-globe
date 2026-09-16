// convert.mjs — osm.json -> as camadas em GeoJSON.
//
// Difere do Pacifico em duas coisas que mudam tudo:
//
// 1. AQUI A AGUA VEM PRONTA. Carentan fica no rio, nao no mar: a Douve, a Taute,
//    o canal e a bacia do porto sao POLIGONOS no OSM. Nao ha linha de costa para
//    poligonizar, entao a terra e o retangulo menos a agua — o inverso do que o
//    pearl.py faz, e muito mais firme.
//
// 2. AS ESTRADAS GUARDAM A TAG INTEIRA, nao so a classe. A N13 de hoje e uma via
//    expressa de quatro pistas construida depois da guerra, passando justo pelo
//    norte da cidade: num mapa de 1944 ela e um anacronismo gritante. Para poder
//    tirar, e preciso saber qual e — dai o campo 'h'.
import fs from 'fs';
const J = JSON.parse(fs.readFileSync('osm.json', 'utf8'));
const LAT = 49.303;
const ring = g => g.map(p => [p.lon, p.lat]);
const closed = r => r.length > 3 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1];
const area = r => { let a = 0; for (let i = 0, n = r.length - 1; i < n; i++) a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
                    return Math.abs(a / 2) * (111320 ** 2) * Math.cos(LAT * Math.PI / 180); };

const L = { agua: [], rio: [], brejo: [], mata: [], campo: [], via: [], trilho: [], predio: [], cais: [], sebe: [] };
const push = (k, geom, props) => L[k].push({ type: 'Feature', properties: props || {}, geometry: geom });
const poly = g => ({ type: 'Polygon', coordinates: [g] });
const linha = g => ({ type: 'LineString', coordinates: g });

// A classe da via decide a espessura. Sem isso os 292 caminhos de servico ficam
// da grossura da nacional e a cidade vira um novelo.
const VIAS = { motorway: 1, trunk: 1, primary: 1, motorway_link: 1, trunk_link: 1, primary_link: 1,
               secondary: 2, secondary_link: 2, tertiary: 2, tertiary_link: 2,
               unclassified: 3, residential: 3, living_street: 3, road: 3,
               service: 4, track: 4, pedestrian: 4, path: 4 };
// A largura da agua corrente: 1 rio e canal, 2 corrego, 3 vala de drenagem. As
// valas sao o desenho do brejo drenado, entao entram, mas finas.
const AGUAS = { river: 1, canal: 1, stream: 2, ditch: 3, drain: 3 };

const MATA = ['wood', 'forest', 'scrub', 'tree_row'];
const CAMPO = ['meadow', 'grass', 'farmland', 'farmyard', 'village_green', 'recreation_ground',
               'allotments', 'orchard', 'vineyard', 'cemetery', 'park', 'pitch', 'garden',
               'golf_course', 'greenfield'];

// Aneis externos de uma relacao multipoligono, cada um como poligono proprio.
// Simplificacao consciente: o furo de um bosque com clareira some. No recorte de
// Carentan nao ha nenhum que apareca.
const externos = e => (e.members || []).filter(m => m.role !== 'inner' && m.geometry)
                                       .map(m => ring(m.geometry)).filter(closed);

for (const e of J.elements || []) {
  const t = e.tags || {};
  const r = e.geometry ? ring(e.geometry) : null;
  const eh_agua = t.natural === 'water' || t.waterway === 'riverbank' ||
                  t.landuse === 'basin' || t.landuse === 'reservoir';

  if (eh_agua) {
    if (r && closed(r)) push('agua', poly(r), {});
    else for (const rr of externos(e)) push('agua', poly(rr), {});
    continue;
  }
  if (t.natural === 'wetland') {
    if (r && closed(r)) push('brejo', poly(r), {});
    else for (const rr of externos(e)) push('brejo', poly(rr), {});
    continue;
  }
  if (t.waterway && AGUAS[t.waterway] && r) { push('rio', linha(r), { w: t.waterway, c: AGUAS[t.waterway] }); continue; }
  if (t.highway && r) { const c = VIAS[t.highway]; if (c) push('via', linha(r), { h: t.highway, c }); continue; }
  if (t.railway && r) { push('trilho', linha(r), { r: t.railway }); continue; }
  if (t.barrier === 'hedge' && r) { push('sebe', linha(r), {}); continue; }
  if (t.natural === 'tree_row' && r && !closed(r)) { push('sebe', linha(r), {}); continue; }
  if (t.man_made && ['pier', 'quay', 'breakwater', 'dyke'].includes(t.man_made) && r) {
    push('cais', closed(r) ? poly(r) : linha(r), {}); continue;
  }
  if (t.building) {
    if (r && closed(r)) { if (area(r) > 25) push('predio', poly(r), {}); }
    else for (const rr of externos(e)) if (area(rr) > 25) push('predio', poly(rr), {});
    continue;
  }
  const g = t.natural || t.landuse || t.leisure;
  if (!g) continue;
  const alvo = MATA.includes(g) ? 'mata' : CAMPO.includes(g) ? 'campo' : null;
  if (!alvo) continue;
  if (r && closed(r)) push(alvo, poly(r), { g });
  else for (const rr of externos(e)) push(alvo, poly(rr), { g });
}

for (const k of Object.keys(L)) fs.writeFileSync(k + '.geojson', JSON.stringify({ type: 'FeatureCollection', features: L[k] }));
console.log(Object.entries(L).map(([k, v]) => k + ':' + v.length).join('  '));
const km2 = L.agua.reduce((s, f) => s + area(f.geometry.coordinates[0]), 0) / 1e6;
console.log('agua', km2.toFixed(2), 'km2   brejo',
  (L.brejo.reduce((s, f) => s + area(f.geometry.coordinates[0]), 0) / 1e6).toFixed(2), 'km2');
const vias = {};
for (const f of L.via) vias[f.properties.h] = (vias[f.properties.h] || 0) + 1;
console.log('vias:', Object.entries(vias).sort((a, b) => b[1] - a[1]).map(([k, v]) => k + ':' + v).join(' '));
