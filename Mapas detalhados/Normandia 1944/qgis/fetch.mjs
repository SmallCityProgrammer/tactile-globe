// fetch.mjs — Carentan OSM -> osm.json, sem dependencia.
//
// O retangulo pega a cidade inteira, a estrada de Periers saindo para sudoeste
// (por onde a Easy subiu) e o comeco da calcada ao norte. Overpass devolve 406
// sem User-Agent.
import fs from 'fs';
const BB = '49.285,-1.283,49.322,-1.220';             // S,W,N,E
const Q = `[out:json][timeout:240];
(
  way["natural"="water"](${BB}); relation["natural"="water"](${BB});
  way["waterway"="riverbank"](${BB}); relation["waterway"="riverbank"](${BB});
  way["landuse"~"^(basin|reservoir)$"](${BB});
  way["waterway"~"^(river|stream|canal|ditch|drain)$"](${BB});
  way["natural"~"^(wood|scrub|grassland|wetland|heath|sand|beach)$"](${BB});
  relation["natural"~"^(wood|scrub|wetland)$"](${BB});
  way["landuse"](${BB}); relation["landuse"](${BB});
  way["leisure"~"^(park|pitch|garden|golf_course)$"](${BB});
  way["highway"~"^(motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|unclassified|living_street|pedestrian|service|track)$"](${BB});
  way["building"](${BB}); relation["building"](${BB});
  way["railway"~"^(rail|light_rail|narrow_gauge|disused|abandoned)$"](${BB});
  way["barrier"="hedge"](${BB});
  way["natural"="tree_row"](${BB});
  way["man_made"~"^(pier|breakwater|quay|dyke)$"](${BB});
);
out geom;`;
// A instancia principal do Overpass vive caindo com 504 ("Dispatcher_Client
// ::request_read_and_idx::timeout"). Entao a lista de espelhos e parte do
// script, nao um detalhe de operacao: tenta um por um ate um responder JSON.
const ESPELHOS = process.env.OVP ? [process.env.OVP] : [
  'https://overpass.private.coffee/api/interpreter',
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
];
(async () => {
  let j = null;
  for (const url of ESPELHOS) {
    try {
      const r = await fetch(url, {
        method: 'POST', body: 'data=' + encodeURIComponent(Q),
        headers: { 'Content-Type': 'application/x-www-form-urlencoded',
                   'User-Agent': 'carentan-map/1.0 (QGIS study)' },
        signal: AbortSignal.timeout(240000) });
      const txt = await r.text();
      console.log('HTTP', r.status, url);
      if (r.status !== 200) { console.log('  ', txt.replace(/\s+/g, ' ').slice(0, 180)); continue; }
      j = JSON.parse(txt);
      break;
    } catch (e) { console.log('ERR', url, e.message); }
  }
  if (!j) { console.error('nenhum espelho respondeu'); process.exit(1); }
  fs.writeFileSync('osm.json', JSON.stringify(j));
  const tally = {};
  for (const e of j.elements || []) {
    const t = e.tags || {};
    const k = t.natural ? 'natural=' + t.natural : t.waterway ? 'waterway=' + t.waterway
      : t.landuse ? 'landuse=' + t.landuse : t.highway ? 'highway=' + t.highway
      : t.building ? 'building' : t.railway ? 'railway' : t.barrier ? 'barrier=' + t.barrier
      : t.leisure ? 'leisure=' + t.leisure : t.man_made ? 'man_made=' + t.man_made : 'outro';
    tally[k] = (tally[k] || 0) + 1;
  }
  console.log('elementos:', (j.elements || []).length);
  console.log(Object.entries(tally).sort((a, b) => b[1] - a[1]).map(([k, v]) => k + ':' + v).join('  '));
})();
