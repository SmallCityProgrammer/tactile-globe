import fs from 'fs';
const J=JSON.parse(fs.readFileSync('osm.json','utf8'));
const ring=g=>g.map(p=>[p.lon,p.lat]);
const closed=r=>r.length>3 && r[0][0]===r[r.length-1][0] && r[0][1]===r[r.length-1][1];
const area=r=>{let a=0;for(let i=0,n=r.length-1;i<n;i++)a+=r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1];return Math.abs(a/2)*(111320**2)*Math.cos(21.36*Math.PI/180);};
const L={agua:[],costa:[],verde:[],via:[],predio:[],pier:[],aero:[]};
const VIAS={motorway:1,trunk:1,primary:1,secondary:2,tertiary:2,
            unclassified:3,residential:3,road:3,living_street:3,
            service:4,track:4,pedestrian:4};
const push=(k,geom,props)=>L[k].push({type:'Feature',properties:props,geometry:geom});
let wArea=0,wMax=0;
for(const e of J.elements||[]){
  const t=e.tags||{}; if(!e.geometry&&!e.members) continue;
  const r=e.geometry?ring(e.geometry):null;
  if(t.natural==='coastline'&&r){ push('costa',{type:'LineString',coordinates:r},{}); continue; }
  const poly=g=>({type:'Polygon',coordinates:[g]});
  if((t.natural==='water'||t.waterway==='riverbank'||t.landuse==='basin')){
    if(r&&closed(r)){ const a=area(r); wArea+=a; wMax=Math.max(wMax,a); push('agua',poly(r),{}); }
    else if(e.members){ for(const m of e.members) if(m.role==='outer'&&m.geometry){ const rr=ring(m.geometry); if(closed(rr)){const a=area(rr);wArea+=a;wMax=Math.max(wMax,a);push('agua',poly(rr),{});} } }
    continue;
  }
  if(!r) continue;
  // A classe vai junto como 'c', para o estilo variar a espessura. Ficar so nas
  // cinco classes maiores tirava do mapa toda a circulacao interna da base: as
  // vias de Ford Island sao service e unclassified, e sem elas a ilha aparece
  // sem nenhum dos caminhos por onde se andava nela.
  if(t.highway){ const c=VIAS[t.highway]; if(c) push('via',{type:'LineString',coordinates:r},{h:t.highway,c}); continue; }
  if(t.man_made==='pier'||t.man_made==='breakwater'){ push('pier',closed(r)?poly(r):{type:'LineString',coordinates:r},{}); continue; }
  if(!closed(r)) continue;
  if(t.building){ if(area(r)>300) push('predio',poly(r),{}); continue; }
  if(t.aeroway){ push('aero',poly(r),{a:t.aeroway}); continue; }
  const g=t.natural||t.landuse;
  if(['wood','scrub','grassland','forest','grass','recreation_ground','cemetery','orchard','farmland','farmyard'].includes(g)) push('verde',poly(r),{g});
  else if(['sand','beach','wetland','dirt'].includes(g)) push('verde',poly(r),{g:'areia'});
}
for(const k of Object.keys(L)) fs.writeFileSync(k+'.geojson',JSON.stringify({type:'FeatureCollection',features:L[k]}));
console.log(Object.entries(L).map(([k,v])=>k+':'+v.length).join('  '));
console.log('area de agua total', (wArea/1e6).toFixed(2),'km2; maior poligono', (wMax/1e6).toFixed(2),'km2');
