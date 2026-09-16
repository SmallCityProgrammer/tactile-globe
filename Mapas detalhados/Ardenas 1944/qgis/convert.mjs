// convert.mjs — osm.json -> uma camada por arquivo
//
//   node convert.mjs
//
// As camadas sao outras que as do Pearl Harbor, porque a paisagem e outra. La o
// mapa era agua e uma base; aqui e TALHAO: o que desenha as Ardenas e a colcha
// de campos, a mata fechada, a sebe entre um campo e outro, e a aldeia no meio.
import fs from 'fs';
const J = JSON.parse(fs.readFileSync('osm.json', 'utf8'));
const LAT = 50.02;                                     // para a conta de area
const ring = g => g.map(p => [p.lon, p.lat]);
const closed = r => r.length > 3 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1];
const area = r => { let a = 0; for (let i = 0, n = r.length - 1; i < n; i++)
    a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
  return Math.abs(a / 2) * (111320 ** 2) * Math.cos(LAT * Math.PI / 180); };

const L = { campo: [], mata: [], urbano: [], via: [], ferro: [],
            predio: [], agua: [], rio: [], sebe: [] };
const push = (k, geom, props) => L[k].push({ type: 'Feature', properties: props, geometry: geom });

// A classe da via vira campo 'c' para o estilo variar a espessura: sem isso a
// aldeia inteira teria a grossura da estrada nacional e viraria um novelo.
const VIAS = { motorway: 1, trunk: 1, primary: 1, secondary: 2, tertiary: 2,
               unclassified: 3, residential: 3, living_street: 3,
               service: 4, track: 4, pedestrian: 4, cycleway: 4 };

// O campo aberto nao e um verde so. Cada uso ganha o seu tom, e dentro do tom
// cada talhao sorteia o seu — e essa colcha que faz a paisagem das Ardenas.
const CAMPO = { meadow: 'prado', farmland: 'lavoura', grass: 'grama',
                grassland: 'prado', orchard: 'pomar', village_green: 'grama',
                recreation_ground: 'grama', greenery: 'grama' };
const MATA = { forest: 'mata', wood: 'mata', scrub: 'moita', heath: 'charneca' };
const URBANO = { residential: 'casario', commercial: 'comercio', retail: 'comercio',
                 industrial: 'industria', farmyard: 'fazenda', cemetery: 'cemiterio',
                 military: 'militar', quarry: 'pedreira', construction: 'obra',
                 brownfield: 'obra', religious: 'casario' };

for (const e of J.elements || []) {
  const t = e.tags || {}; if (!e.geometry) continue;
  const r = ring(e.geometry);
  const poly = g => ({ type: 'Polygon', coordinates: [g] });
  const linha = { type: 'LineString', coordinates: r };

  if (t.highway) { const c = VIAS[t.highway]; if (c) push('via', linha, { h: t.highway, c }); continue; }
  if (t.railway) { push('ferro', linha, { r: t.railway }); continue; }
  if (t.barrier === 'hedge' || t.barrier === 'tree_row' || t.natural === 'tree_row') {
    push('sebe', linha, { b: t.barrier || 'tree_row' }); continue;
  }
  if (t.waterway && t.waterway !== 'riverbank') { push('rio', linha, { w: t.waterway }); continue; }

  if (!closed(r)) continue;
  const a = area(r);
  if (t.building) { if (a > 30) push('predio', poly(r), {}); continue; }
  if (t.natural === 'water' || t.landuse === 'basin' || t.waterway === 'riverbank') {
    push('agua', poly(r), {}); continue;
  }
  const g = t.natural || t.landuse || t.leisure;
  if (MATA[g]) { push('mata', poly(r), { t: MATA[g] }); continue; }
  if (URBANO[g]) { push('urbano', poly(r), { t: URBANO[g] }); continue; }
  if (CAMPO[g] || g === 'park' || g === 'pitch' || g === 'garden') {
    push('campo', poly(r), { t: CAMPO[g] || 'grama' }); continue;
  }
}

for (const k of Object.keys(L))
  fs.writeFileSync(k + '.geojson', JSON.stringify({ type: 'FeatureCollection', features: L[k] }));
console.log(Object.entries(L).map(([k, v]) => k + ':' + v.length).join('  '));
const porTipo = {};
for (const f of L.campo) porTipo[f.properties.t] = (porTipo[f.properties.t] || 0) + 1;
console.log('campo por tipo:', Object.entries(porTipo).map(([k, v]) => k + ':' + v).join(' '));
