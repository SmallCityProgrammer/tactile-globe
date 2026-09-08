# Filling a region on the globe

The globe draws lines. This is how it was taught to fill an area — a set of
countries, painted flat over the sphere — without triangulating anything,
without a tessellation error, and without giving up the zoom range the rest of
the renderer is built around.

The short version: **the region is a bag of closed rings, and the fill is their
even-odd parity, accumulated in the stencil buffer by one XORed triangle per
boundary segment.** Everything else in this document follows from that choice,
including the two places where it bites back.

The example region here is the Napoleonic Empire in 1812, but nothing below
depends on what the rings contain.

---

## 1. What the renderer gives you to work with

Three constraints, all inherited:

- **The sphere is analytic.** There is no mesh — a full-screen triangle solves
  the ray-sphere intersection per pixel. So there is no vertex grid to attach a
  fill to, and no faceting to hide behind.
- **There is no depth buffer.** Everything is painted in order. Lines already
  rely on this: a point `G` on the unit sphere is visible from camera `C` iff
  `dot(G, C) >= 1`, which is exact for anything lying on the sphere and is
  cheaper than depth.
- **Zoom runs from the whole globe to ~13 m of altitude.** Positions reach the
  GPU as an emulated double — a `hi`/`lo` split, subtracted eye-relative in the
  shader — because `float32` visibly shakes below ~600 m.

A fill has to survive all three.

---

## 2. Why not triangulate

The obvious answer is: run the rings through an ear-clipping triangulator and
draw triangles. It is the wrong answer here, for four separate reasons that
compound.

**Holes and count.** The rings are `admin_0` and `admin_1` polygons with holes
— 141 rings, 26,412 points for this region. Ear clipping with hole bridging is
a few hundred lines to get right, and naive ear clipping is O(n²) on the
largest ring.

**A flat triangle sinks through a sphere.** A chord subtending an angle `α`
sits below the surface by `1 - cos(α/2) ≈ α²/8` in radius units. At a 0.15°
edge that is 8.6e-7, or 5.5 m. That does not move the fill's outline — the
boundary vertices are exact either way — but it does move where the horizon
test cuts the fill, by roughly `s / sin θₕ`. At whole-globe zoom that is under
a metre; at 13 m of altitude, where `sin θₕ ≈ √(2h)` is 2e-3, it is 2.7 km, and
the fill visibly peels away from the limb.

So interior edges have to be subdivided, and the tolerance depends on the zoom
— which means a triangulation **per level of detail**, not one.

**Subdivision cracks.** Subdivide adaptively and neighbouring triangles
disagree on their shared edge; the T-junction opens a one-pixel seam of
background colour through the middle of a solid fill. Fixing that means either
red-green refinement, or a global edge-midpoint table, or clipping every
triangle to a fixed lon/lat lattice so the cuts line up by construction. All
three work. All three are more machinery than what follows.

**And it is all for the interior**, which is a flat colour, where no accuracy
was ever needed.

---

## 3. Parity in the stencil buffer

Take a closed ring `P₀…Pₙ₋₁`, pick any apex `A`, and draw the triangles
`(A, Pᵢ, Pᵢ₊₁)` with the stencil op set to `INVERT`. Pixels covered an odd
number of times end up non-zero, and that set is exactly the ring's even-odd
interior.

It works because every interior edge `A→Pᵢ` is shared by exactly two triangles
— the one before and the one after — and two coincident edges rasterize
complementarily under the fill rule, so their contributions cancel. **What the
edge does in space is irrelevant.** It can pass through the sphere, behind it,
anywhere; it cancels.

That is the whole trick, and it buys three things:

1. **No triangulation.** Holes, concavity, self-touching rings, disjoint
   islands — parity handles them all, because parity is what "inside" means.
2. **No tessellation error.** The fill's outline is the boundary polyline
   itself, projected at full precision. There is no interior geometry whose
   accuracy matters, so §2's sagitta problem does not exist.
3. **Set algebra, free.**

### Set algebra

Parity does not care which ring a segment came from, only how many times a ray
crosses. So:

> a country, followed by a ring **inside** it, is that country **minus** that
> ring

Every partial country is written as its `admin_0` outline followed by the
`admin_1` subdivisions to remove. Nothing is clipped and no polygons are
intersected. Two disjoint rings union; a ring inside another subtracts.

There is a data-quality reason to prefer that direction over listing the
subdivisions to keep. Natural Earth's `admin_0` and `admin_1` are built on the
same topology but agree only to about 99.6%. Writing *(Germany) − (Brandenburg,
Berlin)* leaves every international border on `admin_0` geometry, bit-identical
to the neighbour's, and confines the disagreement to inland cuts where nothing
is lined up against it. Writing *(the German states we want)* would put that
disagreement on the French border instead.

Two coincident rings do not fight, either. A ray crossing the France-Belgium
border crosses one segment from each ring: two crossings, parity unchanged,
which is right, because you are inside the union on both sides.

---

## 4. Five things that have to be exactly right

### 4.1 Shared vertices, to the last bit

The cancellation in §3 needs the two triangles meeting at `Pᵢ` to agree on
where `Pᵢ` is. Not to a tolerance — bit for bit. Off by one ulp and the two
edges no longer coincide, and a hairline opens along every ray from the apex.

The line layer stores each segment as a start point plus a delta, which saves a
quarter of the buffer. Doing that here is the bug: instance `i` would compute
`B = Aᵢ + Δᵢ` while instance `i+1` reads its own stored `Aᵢ₊₁`, and float
arithmetic does not promise those are the same number.

So points are stored **once**, and `B` is read from the same buffer one point
further along. The two attributes alias the same bytes:

```js
var RSTRIDE = 28;                              // 3 hi + 3 lo + 1 flag
//        location, size, byte offset
var at = [[0,3,0], [1,3,12], [2,1,24],         // A: hi, lo, flag
          [3,3,RSTRIDE], [4,3,RSTRIDE+12]];    // B: the next point's hi, lo
for (var i = 0; i < at.length; i++){
  gl.enableVertexAttribArray(at[i][0]);
  gl.vertexAttribPointer(at[i][0], at[i][1], gl.FLOAT, false, RSTRIDE, at[i][2]);
  gl.vertexAttribDivisor(at[i][0], 1);
}
```

`B` of instance `i` and `A` of instance `i+1` are now the same 24 bytes, so the
question of whether they match does not arise. One draw call covers every ring;
`aFlag` is 0 on the point that closes a ring, and the shader collapses that
instance to a degenerate triangle so a ring never joins the next one.

The buffer is built so that the closing point is bit-identical to the first by
construction: densification emits `sph(lon + dlon*t, lat + dlat*t)` at `t = 0`,
and the closing point is `sph(lon, lat)`. `x + y*0` is exactly `x`, so both
calls receive identical arguments.

### 4.2 The horizon, without clipping

Half the region is on the far side of the globe most of the time, and a far-side
point projects to somewhere on the near side — garbage, and the parity with it.
The textbook fix is to clip every ring against the horizon plane each frame and
re-close the pieces along the horizon circle. That is real CPU work, every
frame, on tens of thousands of points.

Instead, a point beyond the horizon is **slid along its meridian from the camera
onto the horizon circle**. Azimuth is preserved, so consecutive points keep
their order around that circle, and the fan goes on tracing the visible part of
the region. The clip falls out of the projection.

The visibility test is the line layer's, rearranged. With `rel = P − C`,
`C = R·u`, and `C2 = R² − 1 = 2h + h²`:

```
dot(P, C) ≥ 1   ⟺   dot(rel, u) + C2/R ≥ 0
```

and the clamped point has a closed form. `Q = u/R + w·sin θₕ` with
`sin θₕ = √C2 / R`, so `Q − C = w·sin θₕ − u·(C2/R)` — no subtraction of large
nearly-equal numbers, and it lands exactly on the silhouette:

```glsl
vec3 clampHorizon(vec3 rel){
  if (dot(rel, uCamDir) + uHorizK >= 0.0) return rel;
  vec3 P = rel + uCamHi + uCamLo;
  vec3 w = P - uCamDir*dot(P, uCamDir);
  float wl = length(w);
  if (wl < 1e-7){                              // exactly antipodal: any azimuth
    vec3 t = abs(uCamDir.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
    w = normalize(cross(uCamDir, t));
  } else w /= wl;
  return w*uSinH - uCamDir*uHorizK;
}
```

The precision of `P` here does not matter — it is only used for a direction, and
only for points that are being thrown onto the horizon anyway. Visible points
return `rel` untouched, at full `hi`/`lo` precision.

Two cases fall out of this for free, which is the part worth noticing:

- **The camera deep inside the region.** Every boundary point is beyond the
  horizon, so every one is clamped, and together they wind once around the
  circle — parity odd across the whole disc. The screen fills. Correct, with no
  special case.
- **The region entirely on the far side and not surrounding the camera.** The
  clamped points collapse onto an arc and trace back over themselves. Parity
  zero. Nothing drawn. Also correct.

### 4.3 The near plane would break the cancellation

A fan triangle clipped by the near plane comes out as a polygon whose edges no
longer coincide with the neighbour's, and the cancellation fails along the cut.
It has to be impossible, not merely unlikely.

It is. In view space `z = dot(u, rel) = dot(P, u) − R`, and `|P| ≤ 1` for every
point of the sphere **and of its interior**, so `z ≤ 1 − R = −h`. Fan edges run
through the inside of the sphere, which is exactly the region that bound covers.
Writing the clip position directly, with `w = −z`:

```glsl
gl_Position = vec4(v.x/(uTanHF*uAspect), v.y/uTanHF, 0.0, -v.z);
```

`w ≥ h > 0` always, `z_clip = 0` is inside `[-w, w]`, and no near plane is
involved at all. The apex is the point under the camera, `rel = −h·u`, which
gives `w = h` — the tightest case, and still positive.

### 4.4 Colour: run the sphere shader again

The stencil says *where*. For *what colour*, the cheapest good answer is to run
the existing sphere fragment shader a second time with a different albedo and
the stencil test set to `NOTEQUAL 0`:

```js
gl.stencilFunc(gl.NOTEQUAL, 0, 0xff);
gl.stencilOp(gl.KEEP, gl.KEEP, gl.KEEP);
gl.useProgram(pSph);
gl.uniform1f(uSph.uMask, 1.0);
gl.uniform3fv(uSph.uAlbedo, REGION.color);
gl.drawArrays(gl.TRIANGLES, 0, 3);
```

The fill inherits the globe's shading, its limb darkening and — the part that
would otherwise be fiddly — its exact analytic silhouette, antialiased by the
same coverage term the white sphere uses. Two uniforms and one full-screen pass.
In mask mode the shader outputs `vec4(albedo*shade, cov)` and blends, so the
region's edge at the limb is the sphere's edge, to the pixel.

### 4.5 The stencil edge is hard, and MSAA is the wrong fix

A stencil is one bit per pixel. The fill's own outline — where it runs inland,
not along a coastline — comes out stair-stepped.

Multisampling fixes it properly: with 4 samples the stencil is per-sample and
the resolve does the work. It also runs the entire frame at 4 samples for the
sake of one edge.

Measured A/B — two builds differing only in that flag, same machine, same
1280×860 viewport, GPU timer queries — the cost tracks covered area, not
instance count:

| view | 1 sample | 4 samples |
|---|---|---|
| north pole | 0.22 ms | 0.25 ms |
| whole globe | 0.60 ms | 0.56 ms |
| Europe — dense lines, most of them subpixel | 1.61 ms | 1.79 ms |
| max zoom | 0.20 ms | 0.45 ms |
| region — lines and wedges sweeping the screen | 1.48 ms | 3.11 ms |

Free where little is covered, and up to ~1 ms — the heaviest frame roughly
doubles — where a lot is. Not a catastrophe, and worth knowing rather than
assuming: my first estimate of this was off by more than the number itself,
because I compared two different views instead of two builds.

It is still the worse of the two options, because there is a cheaper fix that
also produces something useful.

What is drawn instead is the region's **outline, as a line, in the fill's own
colour**, through the existing line pipeline — which computes its coverage
analytically in the fragment shader and needs no help from the framebuffer. A
1.15 px line centred on the true boundary covers ±0.575 px, which is more than
the stencil's worst error, and where it overlaps the fill it is painting the
same colour on itself.

It costs one more line layer, and line layers are view-culled, so at high zoom
it draws almost nothing.

---

## 5. The outline is not the union of the rings' edges

Drawing every ring as a line puts navy strokes through empty countryside. The
rings are not the frontier: where two of them run along the same line, the
parity is the same on both sides, so that stretch is **interior**.

Two cases, one rule:

- France and Belgium share a border and both are in. Crossing it does not leave
  the region.
- Germany and Brandenburg share the piece of the Polish border where one ring
  adds and the other takes away. Crossing it does not enter the region.

In both, the segment is carried by an **even** number of rings. That is the
whole test — it is the deduplication the border builder already does for shared
national borders, counted rather than flagged:

```js
const count = new Map();
for (const r of rings)
  for (let i = 0; i < r.length / 2; i++) {
    const k = key(...seg(r, i));               // undirected: A→B and B→A are one
    count.set(k, (count.get(k) || 0) + 1);
  }
// keep the odd ones, re-chain by walking each ring and cutting where one dropped
```

For this region: 25,768 segments in, 13,494 interior and dropped, 12,274 kept,
re-chained into 133 chains and 12,407 points — 62 KB. Roughly half, which is
what you would expect from a blob of adjacent countries.

The dissolved frontier is also the honest thing to call this layer. It is the
empire's border, not a pile of country outlines.

---

## 6. Making it fast

### The cost model, which is upside down

The line layers are culled by a spatial grid, which at maximum zoom throws away
almost all of their instances. **The fan cannot be culled that way.** Drop one
segment and the parity is wrong *everywhere*, not just where that segment was.

Worse, an off-screen segment is not free the way an off-screen line is. Its two
points clamp to the horizon circle, which at high zoom is far outside the
viewport, so its wedge runs clear across the screen. The cost is roughly

```
instances × screen radius in pixels
```

which is the opposite of the lines: **the fan is cheap when the region fills the
screen and dear when it does not.** Zoomed in over Paris with the boundary
hundreds of kilometres away, the first working version spent 41,443 wedges
sweeping the whole viewport to paint it a single flat colour, for 1.5–2 ms.

### A dead end worth recording

The tempting fix is to clamp far points onto a circle just outside the viewport
instead of onto the horizon. The winding number of every on-screen pixel is
preserved — radial clamping to a circle is homotopic to the identity on the disc
inside it, and the homotopy never sweeps a point across anything inside — so it
is *correct*. It is also **useless**: the wedge's on-screen length is the screen
radius either way. Shortening the part of the wedge that is off screen saves
nothing. The only lever is the instance count.

### Levels of detail chosen by clearance, not by pixels

The line layers pick a level from angular resolution per pixel. For the fan that
is the wrong question, because the expensive case — a boundary far from the view
— is also the case whose detail nobody can see.

So the region picks its level by **clearance**. The cells its boundary occupies
are precomputed, which bounds from below how far the nearest piece of boundary
is; if a level's simplification tolerance cannot move the boundary that far, it
is indistinguishable from the exact one:

```js
function pickRegionLOD(viewRho){
  var best = pixelLOD(), clear = Infinity, i, d, a;
  for (i = 0; i < regN; i++){                     // occupied cells only
    d = regDir[3*i]*camU[0] + regDir[3*i+1]*camU[1] + regDir[3*i+2]*camU[2];
    a = Math.acos(Math.max(-1, Math.min(1, d))) - regRad[i];
    if (a < clear) clear = a;
  }
  var slack = clear - viewRho;                    // empty sphere around the view
  if (slack > 0){
    for (i = LODS.length - 1; i > best; i--){
      if (LODS[i].tol*DEG*1.5 < slack){ best = i; break; }
    }
  }
  return lodAt(REGION, best);
}
```

The cell caps are conservative supersets, so `clear` is a lower bound and the
choice is always safe. Over Paris, where the pixel rule asks for the full
41,443 instances at every altitude below a kilometre, clearance gives:

| altitude | fan |
|---|---|
| 127 km | 41,443 |
| 12.7 km | 41,443 |
| 1.27 km | 13,744 |
| 127 m | 13,744 |
| 12.7 m | 3,350 |

The closer in, the less of the boundary can possibly be seen, and the coarser
the fan is allowed to get — which is exactly backwards from how the line layers
choose, and exactly right for this one.

### The grid resolution trap

The first version reused the renderer's existing 4° culling grid, and the
heuristic never fired. A 4° cell is about 440 km across, and its bounding cap
has a ~3° radius — so from Paris, the cell holding the Belgian border is
"zero away", and every cell that matters overlaps every view. The clearance was
always 0.

The region gets its own **1° grid**, built once, with caps computed only for the
cells the boundary actually occupies — a few hundred of them, cheap enough to
scan in full every frame. Below about 1° the heuristic stops paying for itself;
above it, it stops working.

### Measured

RTX 3050 Laptop, 1280×860, GPU timer queries, best of 5 runs of 30 frames,
line layers on:

| view | camera | without | with | added | fan |
|---|---|---|---|---|---|
| north pole | 2 230 km | 0.22 ms | 0.22 ms | 0.00 ms | 256 |
| whole globe | 13 379 km | 0.58 ms | 0.60 ms | 0.02 ms | 3,350 |
| max zoom | 12.7 m | 0.05 ms | 0.20 ms | 0.15 ms | 3,350 |
| Europe | 3 504 km | 1.42 ms | 1.61 ms | 0.19 ms | 13,744 |
| region | 127 km | 0.06 ms | 1.48 ms | 1.42 ms | 41,443 |

The last row is what is left, and it is the honest middle distance: the boundary
is just off screen, so clearance cannot coarsen it, and full detail is genuinely
needed for the part that is on screen. It is also the least stable number here,
drifting between about 1.5 and 2.2 ms run to run. Either way it is the worst
case, not the common one, and still ~500 fps.

### What would fix that row

The parity contributed by segments that stay off screen is **constant across the
whole screen** — the boundary does not pass through the viewport, so the winding
number is the same for every pixel in it. That means the far half could be
collapsed to a single constant and never drawn, leaving only the handful of
segments near the view to rasterize.

The obstacle is bookkeeping, not theory: something has to compute that constant,
and the cheap ways to get it are circular (you need the parity to know the
parity). A point-in-region test on the CPU would settle it — 26,412 points, a
plain even-odd ray cast, on the order of 0.3 ms — which is most of what it would
save. It was not worth building for one view. It is the right next step if it
ever is.

---

## 7. The pipeline, in order

Per frame:

1. Sphere pass, white, opaque, no stencil.
2. `clearStencil(0)`, `colorMask(false…)`, `stencilOp(KEEP, KEEP, INVERT)`.
3. One instanced draw: 3 vertices, one instance per boundary point, apex under
   the camera, far points clamped to the horizon.
4. `colorMask(true…)`, `stencilFunc(NOTEQUAL, 0)`, sphere pass again with the
   region's albedo and blending on.
5. Lines: the region's frontier, then subdivisions, then countries — heaviest
   last, so it wins wherever two nearly touch.

Offline, once:

1. Select the rings — whole countries where the fit is good, subdivisions where
   it is not, ordered so that each partial country is its outline followed by
   the pieces to remove.
2. Quantize to 1e-6°, drop repeated points, store rings open.
3. Dissolve to the frontier by dropping even-count segments; re-chain.
4. Zigzag varints over consecutive deltas, base64 into the single HTML file.
   141 rings and 26,412 points come to 130 KB; the frontier adds 62 KB.

---

## 8. When this is the wrong technique

Parity-in-stencil is a good fit here because the fill is one flat colour over an
analytic sphere with no depth buffer. It stops being the obvious choice if:

- **you need per-pixel data inside the region** — a texture, a gradient keyed to
  geometry, anything that needs interpolated attributes. The stencil gives you a
  mask, not a surface. You would be back to triangles.
- **you have many regions with different colours.** Each one costs its own
  stencil clear and full-screen pass. A handful is fine; a choropleth of 200
  countries is not.
- **the boundary is enormous and always mostly off screen.** §6's cost model is
  the ceiling, and there is no culling under it.

For one region, one colour, on a sphere you can intersect analytically, it is
hard to beat: no triangulation, no tessellation error, set algebra for free, and
the silhouette handled by the shader that was already drawing the globe.
