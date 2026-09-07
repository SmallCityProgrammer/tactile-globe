# Tactile Globe

A white globe with country borders in grey, and nothing else. No oceans, no
relief, no labels. Scroll to zoom, drag to spin. One button adds the state and
province borders of every country.

A single 5.6 MB file with no external dependencies — it opens from `file://`,
by double-click, offline.

![The globe](docs/globo.png)

---

## Use

Open `globo.html`. That's it.

| action | result |
|---|---|
| scroll | zoom, anchored on the point under the cursor |
| drag | spins the globe, the grabbed point stays under the cursor |
| `states & provinces` button (or the `d` key) | toggles the internal borders |

Zoom runs from the whole globe small on screen down to ~13 m of altitude.

---

## The problem

The brief had one requirement that decides everything else: **resolution**, for
both very deep and very distant zoom on the same object. That rules out the two
obvious approaches.

- **Texture on a sphere** — fixed resolution. An 8K texture gives ~2.5 km per
  pixel at the equator; anything closer is a blur.
- **Tessellated mesh** — the silhouette becomes a polygon. On a 10k-face sphere
  the horizon already shows facets at moderate zoom.

So: **vector** borders and an **analytic** sphere.

---

## The data

Source: [Natural Earth](https://www.naturalearthdata.com/) 1:10m,
`admin_0_countries` — the most detailed public country-outline dataset. 13 MB of
GeoJSON, 548,471 points.

`tools/build.mjs` reduces that to 2.38 MB:

**1. Quantization** to 1e-6 degree (~11 cm). The real cartographic accuracy of
the source is on the order of 1 km, so this is 10,000× finer than the data —
nothing is lost.

**2. Deduplicating shared borders.** In the GeoJSON, the Brazil–Paraguay border
exists twice, once in each country's polygon. Drawing both thickens the line and
doubles the cost. With vertices already quantized, shared segments are
bit-for-bit identical, so an undirected key (`A→B` and `B→A` are the same
segment) in a `Set` is enough. **68,617 duplicate segments** removed — 12.6% of
the total, which is exactly the share of land border versus coastline.

**3. Removing artificial edges.** Two kinds exist only because GeoJSON is flat
and a globe is not:

- The Antarctica polygon covers the south pole. In lon/lat that is impossible
  without a fake edge running down the antimeridian to latitude −90.
- Polygons crossing the antimeridian (Russia, Fiji) are cut there, and the cut
  becomes a vertical edge at ±180°.

That is **777 segments** that do not exist on a sphere. Without the filter, a
straight line runs from the Antarctic coast toward the pole — visible below
centre here:

![Antarctica's artificial edge](docs/antartida-artefato.png)

**4. Re-chaining.** The surviving segments are regrouped into chains by walking
the original ring and cutting where a segment was dropped — same result as
building the full topology, without indexing vertices. Storing chains instead of
loose segments halves the point count.

**5. Zigzag varints** over consecutive deltas. Since neighbouring points are
close, deltas almost always fit in 1–2 bytes: **5.21 bytes per point**.

> I tried gzip on top: only 11% smaller. The varint stream is already near
> entropy, and it was not worth a `DecompressionStream` dependency. Plain base64
> it is.

Result: 4,324 chains, 479,106 points, 474,782 unique segments.

### The second layer: states and provinces

This comes from Natural Earth's `admin_1_states_provinces` — 4,596 subdivisions
across 253 countries, 1.3 million points.

The catch is that those polygons **also** contain the coastline and the national
borders: every coastal state carries its slice of coast. Drawing the whole set on
top of the first layer would double every country outline.

The way out depends on a fact worth verifying before committing to it: both
datasets are built on the **same topology**. Measured with quantized vertices,
**99.6% of admin_0 segments appear bit-for-bit identical in admin_1**. That
allows subtraction by exact key — no tolerance, no proximity heuristic:

| admin_1 segments | |
|---|---|
| already in the country layer | 540,864 → dropped |
| duplicated between neighbouring states | 371,157 → dropped |
| artificial (pole, antimeridian) | 775 → dropped |
| **internal borders remaining** | **373,827** |

What is left is 5,967 chains and 379,794 points — 1.78 MB. That is the layer the
button toggles, drawn in a lighter grey and thinner than the country layer so the
hierarchy stays readable: a national border outweighs a state border.

![Brazilian states and neighbouring departments](docs/estados.png)

---

## The rendering

Two WebGL2 passes, no depth buffer.

### Pass 1 — the sphere, by analytic intersection

A full-screen triangle; every pixel solves the ray–sphere intersection in closed
form. There is no mesh, so **there is no faceting at any zoom** and the
silhouette is exact. Edge antialiasing falls out of the discriminant via
screen-space derivatives.

The naive form `t = b − √(b²−c)` cancels catastrophically when the camera is
grazing the surface (`b ≈ √(b²−c)`). The rationalized version
`t = c/(b + √(b²−c))` is stable across the whole range, with `c = 2h + h²`
computed in double on the CPU.

### Pass 2 — the lines, instanced

One quad per segment, expanded in screen space for constant pixel width.

**Horizon occlusion without a depth buffer.** A point `G` on the unit sphere is
visible from camera `C` iff `dot(G, C) ≥ 1`. Since every line lies exactly on the
sphere, that test is exact — and it removes for free the z-fighting that drawing
lines coplanar with a surface would cause. The test runs per fragment (soft
cutoff at the horizon) and also per vertex, discarding whole segments on the far
side early.

### The precision problem

`float32` has ~7 digits. On a unit-radius sphere that is an ulp of ~6e-8. By the
time the camera drops to 600 m of altitude the screen covers ~1e-4 in radius
units and the error is already 0.3 px; at 60 m the image visibly shakes.

The fix is emulated double arithmetic, only where it matters. Each position
reaches the GPU in two halves:

```js
hi = Math.fround(v);
lo = Math.fround(v - hi);   // residue, computed in double
```

and the shader does the eye-relative subtraction before anything else:

```glsl
vec3 rel = (aHi - uCamHi) + (aLo - uCamLo);
```

`aHi - uCamHi` is exact when the two are close (Sterbenz lemma), and the `lo`
term returns the remainder. The final error lands around 1e-13 — irrelevant even
at maximum zoom.

Verified by centring on a real vertex of the dataset at 12.7 m of altitude
(screen covering ~10 m): the line passes exactly through the centre, no shake.

![Extreme zoom](docs/zoom-extremo.png)

Each segment's end point is stored as a **delta** rather than an absolute
position. The delta is small (≤ 0.02°), so `float32` alone already gives 1e-11 of
precision on it — 25% off the buffer at no cost.

### The curvature problem

A straight segment in lon/lat is **not** straight on a sphere. Drawing the 3D
chord between two distant vertices sinks the line into the globe. Every segment
is subdivided until the sagitta drops below 10 cm (a 0.02° step).

Interpolation is linear in lon/lat, not along a great circle — that is what
preserves borders defined by a parallel, like the 49th between the US and Canada,
which a great circle would bow northward.

### Levels of detail

Five levels, simplified with Douglas–Peucker at load time and chosen by angular
resolution per pixel. Without this, the globe seen from far away turns into a
dark smear of overlapping lines.

| level | tolerance | step | countries | subdivisions |
|---|---|---|---|---|
| 0 | — (full) | 0.02° | 940,899 | 642,121 |
| 1 | 0.008° | 0.06° | 328,199 | 194,809 |
| 2 | 0.04° | 0.25° | 83,912 | 51,858 |
| 3 | 0.15° | 0.90° | 23,614 | 16,895 |
| 4 | 0.45° | 2.50° | 9,545 | 8,628 |

Only level 3 of the country layer is built before the first frame. The rest
builds in the background, interleaving the two layers, so the button never opens
onto an empty globe.

Both layers go through the same shader in two draw calls — subdivisions first,
countries on top, so the heavier line wins wherever the two nearly touch.

![Europe](docs/europa.png)

### View culling

The horizon test hides far-side lines, but it does not make them free: every
instance still runs its vertex shader. At maximum zoom that meant 1.58 million
instances processed to show a handful of visible ones.

So segments are bucketed into a 4° lon/lat grid and the instance buffer is laid
out **in cell order**, band-major. Each cell carries a bounding cap (centre
direction plus angular radius, sampled along its boundary). Per frame:

1. Compute one cap containing everything on screen, by intersecting the screen
   corners and edge midpoints with the sphere, clamped to the horizon.
2. Reject cells whose cap misses that cap — a dot product against a precomputed
   `cos`/`sin` pair.
3. Because the layout is cell-ordered, the surviving cells collapse into a few
   contiguous ranges. Gaps under 1024 instances are bridged rather than split.

WebGL2 has no `baseInstance`, so each range is drawn by re-pointing the three
instance attributes at its byte offset — three `vertexAttribPointer` calls plus a
draw. When the visible cap grows past ~0.55 rad the whole thing is skipped and
the buffer is drawn in one call, since there would be nothing to cull.

At maximum zoom this draws **2,364 instances instead of 1,584,000**:

| view | before | after |
|---|---|---|
| max zoom (13 m) | 4.11 ms | 0.11 ms |
| region (127 km) | 4.16 ms | 0.10 ms |
| Europe | 1.48 ms | 0.34 ms |
| continent | 1.44 ms | 0.25 ms |
| whole globe | 0.46 ms | 0.46 ms |

Culling is **pixel-exact**: rendering with and without it and comparing the
framebuffers across 20 view/layer combinations — including both poles, the
antimeridian, the limb and maximum zoom — gives zero differing pixels out of
1.1 million each.

### Camera

State in double precision on the CPU: `lon`, `lat`, altitude. North always up.

Dragging and zooming use the same primitive: **place a world point `G` at a pixel
`(x,y)`**. That is 2 constraints, and a north-up camera has exactly 2 degrees of
freedom, so there is a closed-form solution.

Converting the pixel to a vector `g = (a,b,c)` in camera coordinates, the world's
vertical component depends on latitude alone:

```
G_y = b·cos(φ) + c·sin(φ)
```

which solves directly for `φ`; longitude comes out of a 2×2 system in the `x,z`
components.

The first version was iterative: rotate the camera by the minimal rotation that
takes the point where it belongs, re-derive north, repeat. It works, but it
converges by approximation — each step discards roll and reintroduces error — and
there is no way to claim it closes exactly. The closed form solves in one pass
and is exact by construction: **0 m error** in every case measured, including 40
scroll notches from the whole globe down to maximum zoom, and point-to-point
dragging.

---

## Performance

Measured on an RTX 3050 Laptop at 1280×860, best of 5 runs of 30 frames:

| view | countries | + subdivisions | penalty | instances drawn |
|---|---|---|---|---|
| max zoom (13 m) | 0.09 ms | 0.11 ms | 0.02 ms | 2,364 |
| region (127 km) | 0.08 ms | 0.10 ms | 0.02 ms | 1,398 |
| continent | 0.18 ms | 0.25 ms | 0.07 ms | 40,904 |
| Europe | 0.20 ms | 0.34 ms | 0.14 ms | 75,506 |
| whole globe | 0.30 ms | 0.46 ms | 0.16 ms | 135,770 |
| far out | 0.10 ms | 0.13 ms | 0.04 ms | 18,173 |
| north pole | 1.15 ms | 1.70 ms | 0.55 ms | 523,008 |

First paint at ~196 ms. 79 MB of VRAM for both layers across all levels
(2.3 million segments).

The north pole view is the remaining worst case, and it is inherent: at that
altitude the visible cap fills the screen, so there is nothing to cull and the
whole level has to be drawn. 1.7 ms is still ~590 fps.

Rendering is on demand — with no input, no frame is drawn.

---

## Reproduce

```bash
node tools/build.mjs    # fetches Natural Earth -> data/*.bin
node tools/pack.mjs     # src/template.html + data -> globo.html
```

Node only, no dependencies. `build.mjs` is deterministic: it produces
byte-identical `.bin` files on every run.

```
src/template.html      renderer (WebGL2 + controls), with the data placeholders
tools/build.mjs        Natural Earth -> quantized binaries
tools/pack.mjs         packs everything into one HTML file
data/borders.bin       countries: coastline + national borders (2.38 MB)
data/subdivisions.bin  internal state/province borders (1.78 MB)
globo.html             the result
```

---

## Limitations

- The **cartographic** accuracy of Natural Earth 1:10m is ~1 km. Below roughly
  2 km of altitude the zoom stays sharp but stops revealing anything new — you
  are looking at the geometry of the data, not more detail of the world.
- Coastlines are drawn. There is no coloured or shaded ocean — land and sea are
  the same white — but the coastal outline is part of each country's shape;
  without it only the loose land borders would remain.
- `admin_1` coverage varies a lot by country: some have detailed subdivisions,
  others have few or none. What shows up is what the dataset carries.
- No inertia, no spin animation, no labels.
- Requires WebGL2 (universal in current browsers; the page says so if it is
  missing).

---

## Credits

Borders: [Natural Earth](https://www.naturalearthdata.com/), public domain.
