"""
recorte.py — lift a top-down SOLDIER off a plain (white studio) background and
write him as a transparent PNG for this map's sprite layer.

Same engine as the globe's tools/cutout.py, but this folder's subject is a man
with a rifle, not an aircraft — which changes one setting, see --mirror below.

usage:
  py -3 tools/recorte.py <outdir> name=path [name=path ...] [options]

  A job may carry its own settings after a '?':  us-para=x.jpeg?rot=180&hi=110

options (defaults in brackets):
  --hi 90        RGB distance from the background colour above which a pixel
                 is surely object.  Raise it when a soft studio shadow on white
                 survives as a grey smear beside the boots.
  --lo 18        distance below which a pixel is surely background; between
                 the two the coverage is interpolated (edge anti-aliasing)
  --close 24     radius (px) of the closing that bridges light features that
                 reach the outline.  Keep this SMALL for a soldier (6-10): a
                 wide closing welds the rifle to the chest and the arm to the
                 torso, and whatever it encloses is then hole-filled with
                 opaque background — a white web between rifle and body.
  --unfill 45    a hole enclosed by the silhouette whose median colour distance
                 from the background is below this stays TRANSPARENT.  An arm
                 curled around a rifle encloses a triangle of backdrop; hole
                 filling would hand it back as an opaque white wedge.  Coloured
                 holes (the helmet's dished crown, a mess tin) are above the
                 threshold and still get filled.  0 restores the old behaviour.
  --keep 0.02    drop connected pieces smaller than this fraction of the largest
  --max 1024     long side of the output, in pixels.  512 is plenty here: a man
                 is 16 m of ground and never gets near 200 px on screen.
  --pad 8        transparent margin around the object, in pixels
  --preview DIR  also write name.preview.png: the result over a teal backdrop
  --mirror 1     use the object's left-right symmetry (see below); 0 turns it off
  --dark 220     distance above which a pixel is object regardless of symmetry
  --sym 3        tolerance (px) for the mirror test: how far off the object the
                 mirrored pixel may land and still count
  --rot 0        turn the source by 90, 180 or 270 degrees counter-clockwise
                 first, so the soldier's FRONT points up — heading 0 is north,
                 and the scene engine spins the sprite from there.

Why --mirror stays off here.  The mirror test is an aircraft trick: a plane
seen from above is the same to the left and to the right of its spine, its cast
shadow is not, so a middling-grey pixel can be kept only if its reflection also
lands on the object and the shadow is dropped.  A soldier is NOT bilaterally
symmetric: the rifle is on one side, the sling crosses one shoulder, one arm
reaches out.  Run the mirror test on him and every pixel of the rifle, of the
outstretched arm and of the slung strap reflects onto empty background and is
erased — the man comes out disarmed.  So these jobs run with --mirror 0, and
the default below is 0 for that reason.  Without the mirror, the only defence
against the studio shadow is colour: keep the background white and push --hi up
until the shadow goes.

How it works. The background colour is the median of the image border. The
silhouette is the "surely object" mask, closed, hole-filled (anything enclosed,
e.g. the dished crown of the helmet) except for holes that are still the colour
of the backdrop (see --unfill), and pruned of small pieces — soft shadows and
JPEG specks fall away with them.

Pixels on the outline keep the coverage their colour implies, so the source's
own anti-aliasing survives; where that coverage is reliable (>= 0.5) the
background is divided back out, so no pale fringe is left when the sprite sits
on the darker green of the map. The result is cropped, downscaled premultiplied
(so transparent pixels cannot bleed into the edge), and written as RGBA PNG.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

DEFAULTS = dict(hi=90.0, lo=18.0, close=24, keep=0.02, max=1024, pad=8, mirror=0, dark=220.0, sym=3, rot=0,
                unfill=45.0)


def parse(argv):
    opts = dict(DEFAULTS)
    preview = None
    outdir = None
    jobs = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--preview':
            preview = argv[i + 1]
            i += 2
            continue
        if a.startswith('--'):
            k = a[2:]
            if k not in opts:
                sys.exit(f'unknown option --{k}')
            opts[k] = type(opts[k])(argv[i + 1])
            i += 2
            continue
        if outdir is None:
            outdir = a
        else:
            local = dict()
            if '=' in a:
                name, path = a.split('=', 1)
            else:
                name, path = os.path.splitext(os.path.basename(a))[0], a
            if '?' in path:
                path, q = path.split('?', 1)
                for kv in q.split('&'):
                    k, v = kv.split('=', 1)
                    if k not in opts:
                        sys.exit(f'unknown setting {k} in {a}')
                    local[k] = type(opts[k])(v)
            jobs.append((name, path, local))
        i += 1
    if outdir is None or not jobs:
        print(__doc__)
        sys.exit(1)
    return outdir, jobs, opts, preview


def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r


def cutout(path, o):
    im = Image.open(path).convert('RGB')
    rot = int(o['rot']) % 360
    if rot == 90:
        im = im.transpose(Image.ROTATE_90)
    elif rot == 180:
        im = im.transpose(Image.ROTATE_180)
    elif rot == 270:
        im = im.transpose(Image.ROTATE_270)
    elif rot:
        sys.exit(f'rot must be 0, 90, 180 or 270, not {rot}')
    rgb = np.asarray(im).astype(np.float32)
    H, W = rgb.shape[:2]

    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    cov = np.clip((dist - o['lo']) / (o['hi'] - o['lo']), 0, 1)   # colour-implied coverage

    strong = dist > o['hi']
    axis = None
    if o['mirror']:
        dark = dist > o['dark']
        if dark.any():
            axis = float(np.nonzero(dark)[1].mean())
            near = ndi.binary_dilation(strong, structure=disk(int(o['sym'])))
            mx = np.clip(np.round(2 * axis - np.arange(W)).astype(int), 0, W - 1)
            strong = dark | (strong & near[:, mx])
    sil = ndi.binary_closing(strong, structure=disk(int(o['close'])), border_value=0) | strong
    shut = sil
    sil = ndi.binary_fill_holes(sil)
    kept_holes = 0
    if o['unfill'] > 0:
        # a hole the arms close around the rifle is background, not soldier:
        # if its colour is still the backdrop's, leave it transparent
        holes = sil & ~shut
        hl, hn = ndi.label(holes)
        if hn:
            idx = np.arange(1, hn + 1)
            area = np.asarray(ndi.sum(holes, hl, idx))
            med = np.asarray(ndi.median(dist, hl, idx))
            open_it = np.zeros(hn + 1, bool)
            open_it[1:] = (med < o['unfill']) & (area >= 64)
            kept_holes = int(open_it.sum())
            sil &= ~open_it[hl]
    lab, n = ndi.label(sil)
    dropped = 0
    if n > 1:
        sizes = np.asarray(ndi.sum(sil, lab, range(1, n + 1)))
        keep = np.zeros(n + 1, bool)
        keep[1:] = sizes >= o['keep'] * sizes.max()
        dropped = int((~keep[1:]).sum())
        sil = keep[lab]

    # outline band: two pixels inward from the silhouette's edge
    inner = ndi.binary_erosion(sil, iterations=2, border_value=0)
    band = sil & ~inner
    alpha = np.where(inner, 1.0, np.where(band, np.maximum(cov, 0.35), 0.0)).astype(np.float32)

    # un-mix the background out of edge pixels whose coverage we trust
    fix = band & (cov >= 0.5) & (cov < 1)
    c = cov[fix][:, None]
    rgb[fix] = np.clip((rgb[fix] - (1 - c) * bg) / c, 0, 255)

    # crop to the object plus a margin
    ys, xs = np.nonzero(alpha > 0)
    if not len(ys):
        raise SystemExit(f'{path}: nothing found — is the background plain?')
    pad = int(o['pad'])
    y0, y1 = max(0, ys.min() - pad), min(H, ys.max() + 1 + pad)
    x0, x1 = max(0, xs.min() - pad), min(W, xs.max() + 1 + pad)
    rgb, alpha = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]

    # downscale premultiplied, then divide the alpha back out
    h, w = alpha.shape
    scale = min(1.0, o['max'] / max(h, w))
    if scale < 1:
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        pm = rgb * alpha[:, :, None]
        chans = [Image.fromarray(pm[:, :, k]).resize((nw, nh), Image.LANCZOS) for k in range(3)]
        a = np.asarray(Image.fromarray(alpha).resize((nw, nh), Image.LANCZOS), dtype=np.float32)
        a = np.clip(a, 0, 1)
        pm = np.stack([np.asarray(ch, dtype=np.float32) for ch in chans], axis=2)
        rgb = np.clip(pm / np.maximum(a, 1e-4)[:, :, None], 0, 255)
        alpha = a

    out = np.dstack([rgb, alpha * 255]).round().astype(np.uint8)
    out[alpha <= 0, :3] = 0                       # tidy fully transparent pixels
    info = dict(bg=tuple(int(v) for v in bg), size=(W, H), crop=(x0, y0, x1, y1),
                out=(out.shape[1], out.shape[0]), pieces=n, dropped=dropped,
                filled=int((sil & ~strong)[y0:y1, x0:x1].sum()), axis=axis, holes=kept_holes)
    return Image.fromarray(out, 'RGBA'), info


def main():
    outdir, jobs, opts, preview = parse(sys.argv[1:])
    os.makedirs(outdir, exist_ok=True)
    if preview:
        os.makedirs(preview, exist_ok=True)
    for name, path, local in jobs:
        o = dict(opts)
        o.update(local)
        img, info = cutout(path, o)
        dest = os.path.join(outdir, name + '.png')
        img.save(dest, optimize=True)
        kb = os.path.getsize(dest) / 1024
        print(f'{name:10s} {info["out"][0]}x{info["out"][1]}  {kb:6.0f} KB  '
              f'bg={info["bg"]}  pieces={info["pieces"]} dropped={info["dropped"]}  '
              f'filled={info["filled"]} px  open holes={info["holes"]}  '
              f'<- {os.path.basename(path)}')
        if preview:
            back = Image.new('RGBA', img.size, (42, 106, 114, 255))
            back.alpha_composite(img)
            back.convert('RGB').save(os.path.join(preview, name + '.preview.png'))


if __name__ == '__main__':
    main()
