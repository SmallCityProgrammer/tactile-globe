// fetch.mjs — Bastogne e o Bois Jacques, OSM cru -> osm.json
//
//   node fetch.mjs
//
// O recorte pega Bastogne, Foy ao norte e o Bois Jacques a leste: cidade com
// quarteirao denso, estrada em todo lugar, campo aberto e mata fechada. E o que
// se queria de um banco de provas — o Pearl Harbor e quase so agua e uma base.
//
// A consulta e OUTRA, e nao por capricho. Aqui nao ha linha de costa: a terra e
// o quadro inteiro, e o que desenha o mapa e o TALHAO — campo, prado, mata,
// sebe, ferrovia. Pedir os mesmos tags do Pearl traria quase nada.
import fs from 'fs';
const BB = '49.980,5.680,50.065,5.795';               // S,W,N,E
const Q = `[out:json][timeout:240];
(
  way["landuse"](${BB}); relation["landuse"](${BB});
  way["natural"~"^(wood|scrub|grassland|heath|water|wetland)$"](${BB});
  relation["natural"~"^(wood|water)$"](${BB});
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
  const r = await fetch(process.env.OVP || 'https://overpass-api.de/api/interpreter', {
    method: 'POST',
    body: 'data=' + encodeURIComponent(Q),
    // sem User-Agent o Overpass responde 406 e nao diz por que
    headers: { 'Content-Type': 'application/x-www-form-urlencoded',
               'User-Agent': 'ardennes-map/1.0 (QGIS study)' },
  });
  console.log('HTTP', r.status);
  const j = await r.json();
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
