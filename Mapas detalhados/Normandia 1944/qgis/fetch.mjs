// fetch.mjs — Carentan, OSM cru -> osm.json
//
//   node fetch.mjs
//
// Copia da consulta das Ardenas, que e o caso geral: terra firme, sem linha de
// costa, onde quem desenha o mapa e o TALHAO. Tres coisas mudam.
//
// O BREJO. Carentan fica numa ilha de chao seco entre os vales alagados da Douve
// e da Taute, e em maio de 44 os alemaes abriram as comportas. E por isso que os
// paraquedistas so tinham a calcada exposta para descer. O pantano nao e
// cenario: e a explicacao da batalha. Vem como natural=wetland, e boa parte dele
// como RELACAO — sem a linha de relation o vale inteiro some do mapa.
//
// O CAIS. Ha um porto e um canal no meio da cidade, com molhe e muro de cais que
// o OSM guarda em man_made.
//
// OS ESPELHOS. A instancia principal do Overpass responde 504 com frequencia.
// A lista esta no codigo, nao na cabeca de quem roda.
import fs from 'fs';
const BB = '49.285,-1.283,49.322,-1.220';             // S,W,N,E
const Q = `[out:json][timeout:240];
(
  way["landuse"](${BB}); relation["landuse"](${BB});
  way["natural"~"^(wood|scrub|grassland|heath|water|wetland)$"](${BB});
  relation["natural"~"^(wood|water|wetland)$"](${BB});
  way["man_made"~"^(pier|quay|breakwater|dyke)$"](${BB});
  way["waterway"~"^(stream|river|ditch|riverbank)$"](${BB});
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified|service|track|living_street|pedestrian)$"](${BB});
  way["railway"~"^(rail|abandoned|disused|narrow_gauge)$"](${BB});
  way["building"](${BB});
  way["barrier"~"^(hedge|tree_row)$"](${BB});
  way["natural"="tree_row"](${BB});
  way["leisure"~"^(park|pitch|garden)$"](${BB});
);
out geom;`;

(async () => {
  const ESPELHOS = process.env.OVP ? [process.env.OVP] : [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.private.coffee/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
  ];
  let j = null;
  for (const url of ESPELHOS) {
    try {
      const r = await fetch(url, {
        method: 'POST',
        body: 'data=' + encodeURIComponent(Q),
        // sem User-Agent o Overpass responde 406 e nao diz por que
        headers: { 'Content-Type': 'application/x-www-form-urlencoded',
                   'User-Agent': 'carentan-map/1.0 (QGIS study)' },
        signal: AbortSignal.timeout(240000),
      });
      const txt = await r.text();
      console.log('HTTP', r.status, url);
      if (r.status !== 200) { console.log('  ', txt.replace(/\s+/g, ' ').slice(0, 150)); continue; }
      j = JSON.parse(txt); break;
    } catch (e) { console.log('ERR', url, e.message); }
  }
  if (!j) { console.error('nenhum espelho respondeu'); process.exit(1); }
  fs.writeFileSync('osm.json', JSON.stringify(j));
  const tally = {};
  for (const e of j.elements || []) {
    const t = e.tags || {};
    const k = t.building ? 'building'
      : t.highway ? 'highway=' + t.highway
      : t.landuse ? 'landuse=' + t.landuse
      : t.natural ? 'natural=' + t.natural
      : t.waterway ? 'waterway=' + t.waterway
      : t.railway ? 'railway'
      : t.barrier ? 'barrier=' + t.barrier
      : t.leisure ? 'leisure=' + t.leisure : 'outro';
    tally[k] = (tally[k] || 0) + 1;
  }
  console.log('elementos:', (j.elements || []).length,
              ' osm.json', (fs.statSync('osm.json').size / 1048576).toFixed(1), 'MB');
  console.log(Object.entries(tally).sort((a, b) => b[1] - a[1])
              .map(([k, v]) => k + ':' + v).join('  '));
})();
