"""Phoenix bursting out of a supernova core.

Pure-stdlib procedural drawing (Python 3.13, no third-party modules):
a colossal firebird rises on a strong diagonal out of one huge glowing
core, wings swept back, embers trailing, over a deep indigo starfield
with a thin tilted orbit ring and a tiny silhouetted ridge at the
bottom for scale. Deterministic: two runs write byte-identical PNGs.

Writes $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
"""

import math
import os
import random
import struct
import zlib

W = H = 1024
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

buf = bytearray(W * H * 3)


def _add(i, r, g, b):
    nr = buf[i] + r
    buf[i] = 255 if nr > 255 else nr
    ng = buf[i + 1] + g
    buf[i + 1] = 255 if ng > 255 else ng
    nb = buf[i + 2] + b
    buf[i + 2] = 255 if nb > 255 else nb


def disc(cx, cy, r, color, strength=1.0):
    """Soft additive disc, brightness fading to the edge."""
    r2 = r * r
    x0 = max(0, int(cx - r))
    x1 = min(W - 1, int(cx + r) + 1)
    y0 = max(0, int(cy - r))
    y1 = min(H - 1, int(cy + r) + 1)
    cr, cg, cb = color
    for y in range(y0, y1 + 1):
        dy = y - cy
        base = y * W * 3
        for x in range(x0, x1 + 1):
            dx = x - cx
            d2 = dx * dx + dy * dy
            if d2 < r2:
                f = (1.0 - d2 / r2) * strength
                _add(base + x * 3, int(cr * f), int(cg * f), int(cb * f))


def ellipse_streak(x0, y0, x1, y1, width, c_root, c_tip):
    """One tapered feather: a rotated ellipse, root colour at the base
    fading to tip colour at the far end, soft edges."""
    cx = (x0 + x1) * 0.5
    cy = (y0 + y1) * 0.5
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    a = length * 0.5
    b = width * 0.5
    ca = dx / length
    sa = dy / length
    ia2 = 1.0 / (a * a)
    ib2 = 1.0 / (b * b)
    rx = int(a * abs(ca) + b * abs(sa)) + 2
    ry = int(a * abs(sa) + b * abs(ca)) + 2
    xa = max(0, int(cx - rx))
    xb = min(W - 1, int(cx + rx) + 1)
    ya = max(0, int(cy - ry))
    yb = min(H - 1, int(cy + ry) + 1)
    for y in range(ya, yb + 1):
        dyy = y - cy
        base = y * W * 3
        for x in range(xa, xb + 1):
            dxx = x - cx
            u = dxx * ca + dyy * sa
            v = -dxx * sa + dyy * ca
            q = u * u * ia2 + v * v * ib2
            if q < 1.0:
                t = u / a * 0.5 + 0.5
                f = (1.0 - q) * (1.0 - q)
                r = int((c_root[0] + (c_tip[0] - c_root[0]) * t) * f)
                g = int((c_root[1] + (c_tip[1] - c_root[1]) * t) * f)
                bl = int((c_root[2] + (c_tip[2] - c_root[2]) * t) * f)
                _add(base + x * 3, r, g, bl)


def bezier(p0, p1, p2, steps):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
        y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


# ---------------------------------------------------------------- colours
GOLD = (255, 214, 106)
ORANGE = (255, 122, 26)
MAGENTA = (255, 46, 136)
VIOLET = (123, 47, 255)
WHITE = (255, 246, 220)
CYAN = (125, 249, 255)
EMBER = (255, 170, 60)

rng = random.Random(20261116)

# ---------------------------------------------------------------- background
# Deep indigo sky, darker at the corners, a violet wash near the core.
for y in range(H):
    ty = y / (H - 1)
    # top -> bottom gradient
    br = int(10 + 26 * ty)
    bg = int(5 + 12 * ty)
    bb = int(36 + 34 * ty)
    base = y * W * 3
    dy = (y - 470) / 512.0
    for x in range(W):
        dx = (x - 600) / 512.0
        d2 = dx * dx + dy * dy
        # violet wash close to the core, darkness far away
        wash = 1.0 / (1.0 + d2 * 2.2)
        vig = 1.0 - 0.45 * min(d2, 1.6)
        i = base + x * 3
        buf[i] = int((br + 52 * wash) * vig)
        buf[i + 1] = int((bg + 18 * wash) * vig)
        buf[i + 2] = int((bb + 58 * wash) * vig)

# ---------------------------------------------------------------- starfield
for _ in range(260):
    x = rng.randint(0, W - 1)
    y = rng.randint(0, H - 1)
    m = rng.random()
    if m < 0.55:
        s = 1
    elif m < 0.9:
        s = 2
    else:
        s = 3
    v = int(90 + 165 * rng.random())
    col = (v, v, min(255, v + 40)) if rng.random() < 0.7 else (v, int(v * 0.8), int(v * 0.6))
    disc(x, y, s, col, 0.9)
    if s == 3:  # bright stars get a little cross sparkle
        for dx, dy in ((5, 0), (-5, 0), (0, 5), (0, -5)):
            disc(x + dx, y + dy, 1, col, 0.7)

# ---------------------------------------------------------------- ridge
# Tiny silhouetted mountain ridge along the bottom, for scale.
peaks = [(0, 985), (90, 948), (170, 972), (260, 930), (350, 968),
         (470, 940), (560, 972), (660, 928), (760, 966), (860, 942),
         (950, 970), (1024, 950)]
for x in range(W):
    for k in range(len(peaks) - 1):
        ax, ay = peaks[k]
        bx, by = peaks[k + 1]
        if ax <= x <= bx:
            t = (x - ax) / max(1, bx - ax)
            ry = int(ay + (by - ay) * t)
            break
    for y in range(ry, H):
        i = (y * W + x) * 3
        buf[i] = 4
        buf[i + 1] = 3
        buf[i + 2] = 14

# ---------------------------------------------------------------- supernova core
# Wide magenta halo + tight white-gold heart, additive.
CX, CY = 600, 470
for y in range(0, H):
    dy = y - CY
    base = y * W * 3
    for x in range(0, W):
        dx = x - CX
        d2 = dx * dx + dy * dy
        halo = 1.0 / (1.0 + d2 / 9000.0)
        heart = 1.0 / (1.0 + d2 / 1400.0)
        r = int(255 * heart + 200 * halo)
        g = int(190 * heart + 40 * halo)
        b = int(90 * heart + 130 * halo)
        i = base + x * 3
        nr = buf[i] + r
        buf[i] = 255 if nr > 255 else nr
        ng = buf[i + 1] + g
        buf[i + 1] = 255 if ng > 255 else ng
        nb = buf[i + 2] + b
        buf[i + 2] = 255 if nb > 255 else nb
# Blinding white heart
disc(CX, CY, 70, WHITE, 1.0)
disc(CX, CY, 34, (255, 255, 255), 1.0)

# ---------------------------------------------------------------- wings
# Upper wing: fan of feathers sweeping up-left from the body.
upper_tips = [(140, 285), (168, 348), (200, 408), (238, 462),
              (282, 505), (330, 535), (382, 552)]
for tx, ty in upper_tips:
    ellipse_streak(560, 505, tx, ty, 30, GOLD, MAGENTA)
# Lower wing: fan sweeping down-left, hotter at the root.
lower_tips = [(150, 648), (192, 706), (244, 752), (300, 788),
              (358, 808), (414, 814)]
for tx, ty in lower_tips:
    ellipse_streak(520, 592, tx, ty, 28, ORANGE, VIOLET)
# Wing undersides: a second, deeper violet layer behind each fan.
for tx, ty in [(170, 330), (230, 440), (300, 520)]:
    ellipse_streak(545, 530, tx + 40, ty + 55, 22, MAGENTA, VIOLET)
for tx, ty in [(200, 690), (280, 770), (360, 800)]:
    ellipse_streak(520, 610, tx + 30, ty + 30, 20, MAGENTA, VIOLET)

# ---------------------------------------------------------------- tail ribbons
# Three curved ribbons streaming down-left from the body base.
tails = [((370, 790), (180, 880), (110, 965), MAGENTA),
         ((380, 800), (260, 905), (200, 985), ORANGE),
         ((390, 795), (330, 895), (300, 970), VIOLET)]
for p0, p1, p2, col in tails:
    pts = bezier(p0, p1, p2, 60)
    for n, (x, y) in enumerate(pts):
        t = n / len(pts)
        disc(x, y, 15 - 11 * t, col, 0.85)
        disc(x, y, 6 - 4 * t, GOLD, 0.7)

# ---------------------------------------------------------------- body + head
# Body: overlapping discs along a gently curving rising path,
# white-hot spine over a gold-orange body.
body_pts = bezier((360, 800), (540, 600), (705, 295), 40)
for n, (x, y) in enumerate(body_pts):
    t = n / 40.0
    disc(x, y, 48 - 30 * t, (255, 150, 40), 0.55)
for n, (x, y) in enumerate(body_pts):
    t = n / 40.0
    disc(x, y, 26 - 14 * t, GOLD, 0.8)
for n, (x, y) in enumerate(body_pts):
    t = n / 40.0
    disc(x, y, 11 - 5 * t, WHITE, 0.8)
# Head + beak + crest flames, pointing up-right.
disc(708, 292, 30, GOLD, 1.0)
disc(708, 292, 16, WHITE, 1.0)
ellipse_streak(720, 285, 775, 245, 14, GOLD, ORANGE)   # beak
for tx, ty in [(745, 225), (720, 215), (690, 220)]:
    ellipse_streak(700, 275, tx, ty, 12, ORANGE, MAGENTA)  # crest
# Eye: dark dot with a white glint.
disc(712, 288, 5, (20, 8, 30), 1.0)
disc(714, 286, 2, WHITE, 1.0)

# ---------------------------------------------------------------- orbit ring
# Thin glowing ring tilted across the core, cyan-white.
for deg in range(0, 360):
    th = math.radians(deg)
    rx, ry = 345, 118
    px = rx * math.cos(th)
    py = ry * math.sin(th)
    ca, sa = math.cos(-0.49), math.sin(-0.49)
    x = CX + px * ca - py * sa
    y = CY + px * sa + py * ca
    disc(x, y, 4, CYAN, 0.55)
    disc(x, y, 2, WHITE, 0.9)
# Fainter outer ring.
for deg in range(0, 360, 2):
    th = math.radians(deg)
    rx, ry = 400, 140
    px = rx * math.cos(th)
    py = ry * math.sin(th)
    ca, sa = math.cos(-0.49), math.sin(-0.49)
    x = CX + px * ca - py * sa
    y = CY + px * sa + py * ca
    disc(x, y, 2, (90, 160, 255), 0.4)

# ---------------------------------------------------------------- embers
# Glowing embers trailing the bird's diagonal path.
for _ in range(110):
    t = rng.random()
    x = 300 + 560 * t + rng.randint(-90, 90)
    y = 850 - 640 * t + rng.randint(-90, 90)
    s = rng.choice([1, 2, 2, 3])
    col = rng.choice([GOLD, EMBER, ORANGE, MAGENTA])
    disc(x, y, s + 2, col, 0.5)
    disc(x, y, s, WHITE, 0.8)

# ---------------------------------------------------------------- PNG encode
def chunk(tag, data):
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
raw = bytearray()
for y in range(H):
    raw.append(0)  # filter: none
    raw += buf[y * W * 3:(y + 1) * W * 3]
png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
       + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
       + chunk(b"IEND", b""))

os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "entry.png"), "wb") as f:
    f.write(png)
print(f"wrote {os.path.join(OUT_DIR, 'entry.png')} ({len(png)} bytes)")
