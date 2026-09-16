"""
feldgrau.py — repaint a khaki sprite grey-green, to stand for the other side.

usage:
  py -3 tools/feldgrau.py <outdir> name=path [name=path ...] [options]

  A job may carry its own settings after a '?':  de-rifle=al-rifle.png?sat=0.45

options (defaults in brackets):
  --hue 96       target hue in degrees for the uniform (feldgrau is a green
                 around 90-110; khaki sits near 30-45)
  --sat 0.50     multiply the uniform's saturation by this
  --h0 24        below this hue (degrees) nothing is repainted: skin, leather
                 boots and the rifle's walnut stock live at 5-25 degrees
  --h1 34        at and above this hue the repaint is at full strength; between
                 h0 and h1 it fades in, so no seam appears in the shadows
  --s0 80        saturation (0-255) up to which the repaint is at full strength
  --s1 115       and above which it is off — skin is the reddest, most saturated
                 thing on a soldier, and this is the second guard around it

This is a SIGNBOARD, not a reconstruction.  There is no German asset here; the
same Commonwealth figure is recoloured so the viewer can tell the sides apart.
At map scale — a man is 16 m of ground, under 200 px on screen — what reads is
the colour, never the helmet's shape, so a Brodie in feldgrau does the job that
a Stahlhelm would.  Say so in the credits.

Hue and saturation move; VALUE and ALPHA are untouched.  Keeping the value is
what preserves the photograph: every fold, seam and shadow of the original
lighting stays exactly where it was, and only the pigment changes.  Keeping
the alpha means the cutout's soft outline survives the repaint.
"""
import os
import sys

import numpy as np
from PIL import Image

DEFAULTS = dict(hue=96.0, sat=0.50, h0=24.0, h1=34.0, s0=80.0, s1=115.0)


def parse(argv):
    opts = dict(DEFAULTS)
    outdir = None
    jobs = []
    i = 0
    while i < len(argv):
        a = argv[i]
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
    return outdir, jobs, opts


def ramp(x, a, b):
    """0 below a, 1 above b, smooth in between."""
    t = np.clip((x - a) / max(b - a, 1e-6), 0, 1)
    return t * t * (3 - 2 * t)


def repaint(path, o):
    im = Image.open(path).convert('RGBA')
    a = np.asarray(im)
    alpha = a[:, :, 3]
    hsv = np.asarray(Image.fromarray(a[:, :, :3], 'RGB').convert('HSV')).astype(np.float32)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    u = 256.0 / 360.0                                  # degrees -> PIL's 8-bit hue
    w = ramp(h, o['h0'] * u, o['h1'] * u)              # khaki in, skin and leather out
    w *= 1 - ramp(s, o['s0'], o['s1'])                 # the reddest pixels are skin
    w *= alpha > 0                                     # nothing to repaint in the void

    target = (o['hue'] * u) % 256.0
    h = h + w * (target - h)                           # both ends of the lerp are warm-to-green,
    s = s * (1 - w * (1 - o['sat']))                   # no wrap-around to worry about
    out = np.dstack([h, s, v]).round().clip(0, 255).astype(np.uint8)
    rgb = np.asarray(Image.fromarray(out, 'HSV').convert('RGB'))
    res = np.dstack([rgb, alpha])
    res[alpha == 0, :3] = 0
    moved = float((w > 0.5).sum()) / max(int((alpha > 200).sum()), 1)
    return Image.fromarray(res, 'RGBA'), moved


def main():
    outdir, jobs, opts = parse(sys.argv[1:])
    os.makedirs(outdir, exist_ok=True)
    for name, path, local in jobs:
        o = dict(opts)
        o.update(local)
        img, moved = repaint(path, o)
        dest = os.path.join(outdir, name + '.png')
        img.save(dest, optimize=True)
        kb = os.path.getsize(dest) / 1024
        print(f'{name:10s} {img.size[0]}x{img.size[1]}  {kb:6.0f} KB  '
              f'repainted={moved * 100:4.1f}% of the body  <- {os.path.basename(path)}')


if __name__ == '__main__':
    main()
