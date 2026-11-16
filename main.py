#!/usr/bin/env python3
"""ai-excited-01 -- a colossal phoenix bursting out of a supernova core.

Pure-stdlib procedural renderer (Python 3.13, no third-party imports).
Draws a 1024x1024 PNG and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output/entry.png).

The image: one huge phoenix-firebird tearing upward out of a dying star.
Layered flame wings sweep the whole frame on a diagonal, a blinding
white-gold core burns at its heart, a thin tilted ring of starlight cuts
across the blast, embers stream upward, and a tiny black mountain ridge
along the bottom gives the scale. Hot orange/gold/cyan on deep indigo.

Deterministic: fixed seeds, no clock, no network, no hash-order
dependence. Two runs produce byte-identical files.

How it works (fast on purpose -- the grader allows 60 s):
  1. Paint a smooth "heat" field at 256x256 with distance-field math
     (radial core glow, vertical flame body, two swept sine-ripple
     flame wings, a tail, a tilted ring, a jagged mountain silhouette).
  2. Bilinear-upscale the field to 1024x1024 and map it through a
     256-entry colour palette (indigo -> violet -> red -> orange ->
     gold -> white-hot) with C-speed bytes.translate.
  3. Stamp full-resolution detail straight into the pixel buffer:
     stars, rising embers, cyan streaks at the wing tips.
  4. Encode a standard PNG with zlib + struct (filter 0 scanlines).
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
FW = 256
FH = 256

# Phoenix heart, in field coordinates (1 cell = 4 px).
CX = 128.0
CY = 165.0


# ---------------------------------------------------------------- palette
def _build_palette():
    """256-entry gradient: deep indigo -> violet -> red -> orange ->
    gold -> white-hot. Returns (tabR, tabG, tabB) translation tables."""
    stops = [
        (0.00, (5, 8, 31)),
        (0.10, (13, 18, 56)),
        (0.20, (26, 20, 70)),
        (0.32, (58, 28, 92)),
        (0.45, (110, 31, 46)),
        (0.58, (179, 39, 30)),
        (0.70, (232, 78, 26)),
        (0.80, (255, 122, 26)),
        (0.88, (255, 157, 46)),
        (0.94, (255, 201, 60)),
        (0.98, (255, 233, 138)),
        (1.00, (255, 250, 220)),
    ]
    pal = []
    for i in range(256):
        t = i / 255.0
        for s in range(len(stops) - 1):
            t0, c0 = stops[s]
            t1, c1 = stops[s + 1]
            if t0 <= t <= t1:
                f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                pal.append(tuple(
                    int(c0[k] + (c1[k] - c0[k]) * f + 0.5) for k in range(3)
                ))
                break
        else:
            pal.append(stops[-1][1])
    return (
        bytes(p[0] for p in pal),
        bytes(p[1] for p in pal),
        bytes(p[2] for p in pal),
    )


PAL_R, PAL_G, PAL_B = _build_palette()


# ------------------------------------------------------------- heat field
def _wing(dx, dy, dirx, diry, perpx, perpy, ulen=138.0, wscale=1.0,
          boost=1.0):
    """Heat of one swept flame wing. (dir) points from the core toward
    the wing tip; (perp) is its 90-degree rotation. Flame tongues run
    ALONG the wing (ripples across v), so the wing reads as streaks of
    fire, not bands across it."""
    u = dx * dirx + dy * diry
    if u < 8.0 or u > ulen:
        return 0.0
    v = dx * perpx + dy * perpy
    # Sweep the wing tip upward: the centreline bends toward the sky
    # as u grows, so the wing arcs instead of ending in a straight edge.
    # The bend keys off the fixed outer length so every layer of the
    # wing shares one centreline (no notches where layers end).
    bend = (u / 138.0) * (u / 138.0)
    v -= 24.0 * bend
    width = (26.0 * (1.0 - u / 160.0) + 4.0) * wscale
    # Taper the width to a point at the tip (no flat chopped end).
    if u > ulen - 30.0:
        tt = 1.0 - (u - (ulen - 30.0)) / 30.0
        width *= tt ** 0.7
    av = v if v >= 0.0 else -v
    if av > width:
        return 0.0
    # Flame tongues streaking along the wing.
    tongue = 0.85 + 0.15 * math.sin(v * 0.35 + u * 0.06 + 1.3)
    along = 1.0 - u / (ulen + 12.0)
    across = 1.0 - (av / width) * (av / width)
    w = (along ** 0.8) * (0.35 + 0.65 * across) * tongue * 1.2 * boost
    # Bright leading edge near the tip.
    if u > ulen - 33.0:
        tip = (u - (ulen - 33.0)) / 33.0
        edge = 1.0 - av / (width + 6.0)
        if edge > 0.0 and tip * 0.55 * edge > w:
            w = tip * 0.55 * edge
    return w if w < 1.0 else 1.0


def _build_field():
    f = [0.0] * (FW * FH)
    for fy in range(FH):
        dy = fy - CY
        bg = 0.045 + 0.05 * (fy / FH)
        neb = 0.02 * math.sin(fy * 0.11)
        row = fy * FW
        for fx in range(FW):
            dx = fx - CX
            # --- background: indigo gradient + faint nebula bands ---
            h = bg + neb * math.sin(fx * 0.043 + 1.7)
            h += 0.012 * math.sin(fx * 0.021 + fy * 0.017)
            # --- vignette: darken the far corners ---
            nd = math.sqrt((dx / 128.0) * (dx / 128.0)
                           + (dy / 128.0) * (dy / 128.0))
            if nd > 0.72:
                t = (nd - 0.72) / 0.28
                h *= 1.0 - 0.30 * t * t
            # --- supernova core: blinding radial glow ---
            r2 = dx * dx + dy * dy
            core = 1.0 / (1.0 + r2 / 700.0)
            if core > h:
                h = core
            # --- tilted ring of starlight around the core ---
            rx = dx * 0.906 - dy * 0.423
            ry = dx * 0.423 + dy * 0.906
            er = math.sqrt((rx / 54.0) * (rx / 54.0)
                           + (ry / 17.0) * (ry / 17.0))
            d = (er - 1.0) * 11.0
            ring = 0.85 * math.exp(-d * d)
            if ring > h:
                h = ring
            # --- body: vertical flame teardrop above the core ---
            # Smooth taper to a point at the top; the edges wobble
            # (width modulated) instead of the heat banding along its
            # length, so it reads as one continuous flame, not beads.
            if dy < 6.0:
                up = -dy
                if up < 158.0:
                    wob = 1.0 + 0.12 * math.sin(up * 0.16 + 0.8)
                    bulge = 1.0 + 0.25 * math.exp(-((up - 135.0) / 10.0) ** 2)
                    wdt = (30.0 * (1.0 - up / 165.0) + 3.0) * wob * bulge
                    ax = dx / wdt
                    if ax < 1.0 and ax > -1.0:
                        body = (1.0 - ax * ax) * (1.0 - up / 160.0) ** 0.75
                        if body > h:
                            h = body
            # --- tail: flame tongues streaming down from the core ---
            elif dy > 4.0:
                down = dy
                if down < 72.0:
                    wdt = 24.0 * (1.0 - down / 78.0) + 3.0
                    ax = dx / wdt
                    if ax < 1.0 and ax > -1.0:
                        flick = 0.88 + 0.12 * math.sin(dy * 0.22 - dx * 0.09)
                        tail = ((1.0 - ax * ax) * (1.0 - down / 76.0) ** 0.8
                                * flick * 1.3)
                        if tail > h:
                            h = tail
            # --- wings: two huge swept flame wings, layered ---
            # (bright narrow inner flame inside a broad outer one)
            wl = _wing(dx, dy, -0.80, -0.60, 0.60, -0.80)
            if wl > h:
                h = wl
            wl2 = _wing(dx, dy, -0.80, -0.60, 0.60, -0.80,
                        ulen=105.0, wscale=0.50, boost=0.95)
            if wl2 > h:
                h = wl2
            wr = _wing(dx, dy, 0.80, -0.60, -0.60, -0.80)
            if wr > h:
                h = wr
            wr2 = _wing(dx, dy, 0.80, -0.60, -0.60, -0.80,
                        ulen=105.0, wscale=0.50, boost=0.95)
            if wr2 > h:
                h = wr2
            # --- mountain ridge silhouette along the bottom ---
            if fy > 228:
                ridge = (238.0 + 5.0 * math.sin(fx * 0.11)
                         + 3.5 * math.sin(fx * 0.031 + 2.0)
                         + 2.5 * math.sin(fx * 0.23 + 1.0))
                if fy > ridge:
                    h = 0.012
                elif fy > ridge - 2.0 and h > 0.05:
                    h = 0.05
            f[row + fx] = h if h < 1.0 else 1.0
    return f


# -------------------------------------------------------------- upscale
def _expand_row(src):
    """Bilinear horizontal expansion of one 256-wide field row to 1024."""
    out = []
    ap = out.append
    for i in range(FW - 1):
        a = src[i]
        b = src[i + 1]
        ap(a)
        ap(a * 0.75 + b * 0.25)
        ap(a * 0.5 + b * 0.5)
        ap(a * 0.25 + b * 0.75)
    last = src[FW - 1]
    ap(last)
    ap(last)
    ap(last)
    ap(last)
    return out


def _upscale(field):
    """256x256 heat field -> 1024x1024 RGB bytearray via the palette."""
    expanded = [_expand_row(field[y * FW:(y + 1) * FW]) for y in range(FH)]
    weights = ((1.0, 0.0), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75))
    img = bytearray(W * H * 3)
    for y in range(H):
        sy = y // 4
        wa, wb = weights[y % 4]
        row_a = expanded[sy]
        row_b = expanded[sy + 1] if sy + 1 < FH else row_a
        heat = bytes(
            int(min(1.0, a * wa + b * wb) * 255) for a, b in zip(row_a, row_b)
        )
        r = heat.translate(PAL_R)
        g = heat.translate(PAL_G)
        b = heat.translate(PAL_B)
        o = y * W * 3
        img[o:o + W * 3:3] = r
        img[o + 1:o + W * 3:3] = g
        img[o + 2:o + W * 3:3] = b
    return img


# ------------------------------------------------------- full-res detail
def _add(img, x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        o = (y * W + x) * 3
        v = img[o] + r
        img[o] = 255 if v > 255 else v
        v = img[o + 1] + g
        img[o + 1] = 255 if v > 255 else v
        v = img[o + 2] + b
        img[o + 2] = 255 if v > 255 else v


def _detail(img):
    rng = random.Random(20261116)
    # --- stars, mostly in the upper sky ---
    for _ in range(420):
        x = rng.randrange(W)
        y = rng.randrange(760)
        br = rng.randrange(60, 256)
        col = (br, br, 255) if rng.random() < 0.7 else (255, 225, 160)
        _add(img, x, y, col[0], col[1], col[2])
        if rng.random() < 0.12:  # a few bright stars get a cross sparkle
            _add(img, x - 1, y, br // 2, br // 2, br // 2)
            _add(img, x + 1, y, br // 2, br // 2, br // 2)
            _add(img, x, y - 1, br // 2, br // 2, br // 2)
            _add(img, x, y + 1, br // 2, br // 2, br // 2)
    # --- embers streaming up and out from the core ---
    for _ in range(300):
        ang = rng.uniform(-math.pi + 0.25, -0.25)  # upward fan
        dist = rng.uniform(60.0, 480.0)
        jx = rng.uniform(-26.0, 26.0)
        jy = rng.uniform(-26.0, 26.0)
        x = int(512 + math.cos(ang) * dist + jx)
        y = int(660 + math.sin(ang) * dist + jy)
        fade = 1.0 - dist / 560.0
        br = int(rng.uniform(120, 255) * fade) + 40
        gold = rng.random() < 0.75
        if gold:
            _add(img, x, y, br, int(br * 0.55), int(br * 0.15))
        else:
            _add(img, x, y, int(br * 0.25), int(br * 0.7), br)
        if rng.random() < 0.3:  # glowing halo around some embers
            _add(img, x - 1, y, br // 4, br // 6, 0)
            _add(img, x + 1, y, br // 4, br // 6, 0)
            _add(img, x, y - 1, br // 4, br // 6, 0)
            _add(img, x, y + 1, br // 4, br // 6, 0)
    # --- crisp ring of starlight, drawn at full resolution so it cuts
    # across the bright wings instead of being swallowed by them ---
    # (tilted ellipse around the core; the near arc burns brighter)
    steps = 1400
    for i in range(steps):
        t = 2.0 * math.pi * i / steps
        # ellipse in its own plane, then tilted -25 degrees
        ex = 232.0 * math.cos(t)
        ey = 72.0 * math.sin(t)
        x = int(512 + ex * 0.906 - ey * 0.423)
        y = int(660 + ex * 0.423 + ey * 0.906)
        near = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t))
        br = int(215 * near)
        _add(img, x, y, br, int(br * 0.62), int(br * 0.16))
        _add(img, x, y + 1, br // 2, br // 3, br // 8)
        _add(img, x, y - 1, br // 2, br // 3, br // 8)
    # --- cyan streaks flashing at the wing tips ---
    for _ in range(36):
        side = -1.0 if rng.random() < 0.5 else 1.0
        u = rng.uniform(95.0, 135.0)
        v = rng.uniform(-18.0, 18.0)
        # wing-tip point in field coords -> image coords
        fx = CX + side * 0.80 * u + side * 0.60 * v
        fy = CY - 0.60 * u - 0.80 * v
        x0 = int(fx * 4)
        y0 = int(fy * 4)
        ln = rng.randrange(8, 18)
        dx = int(side * 2)
        dy = -1
        for i in range(ln):
            fade = 1.0 - i / ln
            # 2x2 blocks tile into a continuous glowing slash
            for ox in (0, 1):
                for oy in (0, 1):
                    _add(img, x0 + dx * i + ox, y0 + dy * i + oy,
                         int(40 * fade), int(220 * fade), int(255 * fade))


# ------------------------------------------------------------------- PNG
def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _encode_png(rgb):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += rgb[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", comp)
            + _chunk(b"IEND", b""))


def main():
    import time
    t0 = time.time()
    field = _build_field()
    img = _upscale(field)
    _detail(img)
    png = _encode_png(img)
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(png)
    print("wrote %s (%d bytes) in %.2fs" % (path, len(png), time.time() - t0))


if __name__ == "__main__":
    main()
