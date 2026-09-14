// fetch.js — Pearl Harbor OSM -> GeoJSON, sem dependencia
import fs from 'fs';
const BB='21.325,-158.030,21.400,-157.920';           // S,W,N,E
const Q=`[out:json][timeout:180];
(
  way["natural"="coastline"](${BB});
  way["natural"="water"](${BB}); relation["natural"="water"](${BB});
  way["waterway"="riverbank"](${BB});
  way["landuse"](${BB});
  way["natural"~"^(wood|scrub|grassland|beach|sand|wetland)$"](${BB});
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified|service)$"](${BB});
  way["building"](${BB});
  way["aeroway"](${BB});
  way["man_made"~"^(pier|breakwater|storage_tank)$"](${BB});
);
out geom;`;
(async()=>{
  const r=await fetch((process.env.OVP||'https://overpass-api.de/api/interpreter'),{method:'POST',body:'data='+encodeURIComponent(Q),headers:{'Content-Type':'application/x-www-form-urlencoded','User-Agent':'pearl-harbor-map/1.0 (QGIS study)'}});
  console.log('HTTP',r.status);
  const j=await r.json();
  fs.writeFileSync('osm.json',JSON.stringify(j));
  const tally={};
  for(const e of j.elements||[]){
    const t=e.tags||{};
    const k=t.natural?'natural='+t.natural : t.waterway?'waterway='+t.waterway : t.landuse?'landuse='+t.landuse
      : t.highway?'highway' : t.building?'building' : t.aeroway?'aeroway='+t.aeroway : t.man_made?'man_made='+t.man_made : 'outro';
    tally[k]=(tally[k]||0)+1;
  }
  console.log('elementos:',(j.elements||[]).length);
  console.log(Object.entries(tally).sort((a,b)=>b[1]-a[1]).map(([k,v])=>k+':'+v).join('  '));
})();
