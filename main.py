#!/usr/bin/env python3
"""Phoenix Supernova - make.fun ai-excited-01 entry.

A colossal phoenix bursting from a supernova core: bold orange flame
plumes, a glowing orbit ring, an indigo starfield, mountain ridges below,
and the word RISE above. Drawn procedurally with the Python standard
library only. Deterministic: the same bytes on every run.

Run: python3 main.py  (writes entry.png into $MAKEFUN_OUTPUT_DIR or /output)
"""
import math
import os
import random
import struct
import zlib

W = H = 1024
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
SEED = 20261116

GOLD = (255, 205, 80)
ORANGE = (255, 120, 25)
DEEPRED = (190, 40, 12)
PALE = (255, 245, 205)
YELLOW = (255, 225, 120)

fb = bytearray(W * H * 3)


def _i(x, y):
    return (y * W + x) * 3


def add(x, y, r, g, b, a=1.0):
    if 0 <= x < W and 0 <= y < H:
        i = _i(x, y)
        fb[i] = min(255, fb[i] + int(r * a))
        fb[i + 1] = min(255, fb[i + 1] + int(g * a))
        fb[i + 2] = min(255, fb[i + 2] + int(b * a))


def setc(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = _i(x, y)
        fb[i] = r
        fb[i + 1] = g
        fb[i + 2] = b


def blend(x, y, r, g, b, a=1.0):
    """Opaque-ish layering: mix toward color instead of adding light."""
    if 0 <= x < W and 0 <= y < H:
        i = _i(x, y)
        fb[i] = min(255, int(fb[i] * (1 - a) + r * a))
        fb[i + 1] = min(255, int(fb[i + 1] * (1 - a) + g * a))
        fb[i + 2] = min(255, int(fb[i + 2] * (1 - a) + b * a))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp3(c0, c1, t):
    return (lerp(c0[0], c1[0], t), lerp(c0[1], c1[1], t), lerp(c0[2], c1[2], t))


def disc(cx, cy, rad, color, a=1.0, mode="add"):
    """Soft-edged filled disc; mode 'add' glows, 'blend' lays color down."""
    r = int(math.ceil(rad))
    r2 = rad * rad
    x0 = max(0, int(cx - r))
    x1 = min(W - 1, int(cx + r))
    y0 = max(0, int(cy - r))
    y1 = min(H - 1, int(cy + r))
    for yy in range(y0, y1 + 1):
        dy = yy - cy
        for xx in range(x0, x1 + 1):
            dx = xx - cx
            d2 = dx * dx + dy * dy
            if d2 <= r2:
                fall = 1.0 - 0.55 * d2 / r2
                if mode == "blend":
                    blend(xx, yy, color[0], color[1], color[2], a * fall)
                else:
                    add(xx, yy, color[0], color[1], color[2], a * fall)


def plume(p0, p1, p2, w0, w1, c0, c1, steps=44, a=0.85):
    """Tapered flame plume along a quadratic bezier: faint halo, then a
    solid color core so overlapping plumes stay orange/gold, not white."""
    for s in range(steps + 1):
        t = s / steps
        mt = 1.0 - t
        x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
        y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
        w = lerp(w0, w1, t) * 2.2
        col = lerp3(c0, c1, t)
        disc(x, y, w, col, 0.10, "add")
    for s in range(steps + 1):
        t = s / steps
        mt = 1.0 - t
        x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
        y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
        w = lerp(w0, w1, t)
        col = lerp3(c0, c1, t)
        disc(x, y, w, col, a, "blend")


def background(rng):
    cx, cy = 512.0, 470.0
    nebulae = [
        (200.0, 220.0, 260.0, (70, 40, 130)),
        (830.0, 180.0, 220.0, (30, 80, 120)),
        (760.0, 640.0, 240.0, (120, 50, 90)),
    ]
    for y in range(H):
        t = y / (H - 1)
        br = lerp(9, 46, t)
        bg = lerp(9, 24, t)
        bb = lerp(42, 82, t)
        for x in range(W):
            dx = x - cx
            dy = y - cy
            d2 = dx * dx + dy * dy
            glow = 1.0 / (1.0 + d2 / 150.0 ** 2)
            hot = 1.0 / (1.0 + d2 / 42.0 ** 2)
            r = br + 255 * glow * 0.42 + 205 * hot
            g = bg + 165 * glow * 0.42 + 185 * hot
            b = bb + 55 * glow * 0.42 + 150 * hot
            for (nx, ny, nr, nc) in nebulae:
                ndx = x - nx
                ndy = y - ny
                nd2 = ndx * ndx + ndy * ndy
                ng = 1.0 / (1.0 + nd2 / nr ** 2)
                r += nc[0] * ng * 0.35
                g += nc[1] * ng * 0.35
                b += nc[2] * ng * 0.35
            vx = (x - 512.0) / 512.0
            vy = (y - 512.0) / 512.0
            vig = 1.0 - 0.28 * max(0.0, vx * vx + vy * vy - 0.55)
            i = (y * W + x) * 3
            fb[i] = min(255, int(r * vig))
            fb[i + 1] = min(255, int(g * vig))
            fb[i + 2] = min(255, int(b * vig))
    # starfield
    for _ in range(650):
        x = rng.randrange(0, W)
        y = rng.randrange(0, 760)
        br = rng.randrange(120, 256)
        tint = rng.choice([(255, 255, 255), (220, 230, 255), (255, 240, 210)])
        s = br / 255.0
        setc(x, y, int(tint[0] * s), int(tint[1] * s), int(tint[2] * s))
        if rng.random() < 0.06:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                add(x + dx, y + dy, tint[0], tint[1], tint[2], 0.35)


def ridge_y(x, base, amps, freqs, phases):
    y = base
    for amp, fr, ph in zip(amps, freqs, phases):
        y += amp * math.sin(x * fr + ph)
    return y


def mountains(rng):
    ph1 = [rng.uniform(0, 6.283) for _ in range(3)]
    ph2 = [rng.uniform(0, 6.283) for _ in range(3)]
    for x in range(W):
        yb = ridge_y(x, 728, (26, 14, 7), (0.006, 0.013, 0.031), ph1)
        yf = ridge_y(x, 812, (30, 16, 8), (0.005, 0.011, 0.027), ph2)
        for y in range(int(yb), int(yf)):
            setc(x, y, 20, 12, 40)
        for y in range(int(yf), H):
            setc(x, y, 9, 6, 22)
        # warm rim light on the back ridge near the core
        d = abs(x - 512)
        if d < 300:
            a = 0.55 * (1 - d / 300.0)
            add(x, int(yb), 255, 130, 40, a)
            add(x, int(yb) + 1, 255, 130, 40, a * 0.6)


def ring(cx, cy, rx, ry, tilt_deg, front):
    """Glowing tilted orbit ring; front=True draws the lower (near) arc."""
    tilt = math.radians(tilt_deg)
    ct, st = math.cos(tilt), math.sin(tilt)
    for k in range(720):
        th = 2 * math.pi * k / 720
        ex = rx * math.cos(th)
        ey = ry * math.sin(th)
        x = cx + ex * ct - ey * st
        y = cy + ex * st + ey * ct
        if front and y <= cy:
            continue
        if not front and y > cy:
            continue
        a = 0.9 if front else 0.45
        disc(x, y, 12, GOLD, 0.10 * a)
        disc(x, y, 4.5, (255, 230, 150), 0.85 * a)


def phoenix():
    # tail plumes flowing down into the core
    for (p0, p1, p2) in [
        ((512, 560), (430, 660), (350, 740)),
        ((512, 560), (600, 660), (690, 740)),
        ((512, 580), (380, 640), (290, 700)),
        ((512, 580), (650, 640), (750, 700)),
    ]:
        plume(p0, p1, p2, 26, 6, DEEPRED, GOLD, a=0.8)
    # core flame column (narrower, so the bird keeps its shape)
    plume((512, 660), (512, 430), (512, 235), 44, 12, DEEPRED, PALE, a=0.85)
    # body
    plume((512, 570), (505, 410), (512, 250), 36, 11, ORANGE, YELLOW, a=0.85)
    # wings, left and mirrored right (broader, so they read as wings)
    for sgn in (-1, 1):
        m = lambda x: 512 + sgn * (x - 512)
        plume((m(500), 400), (m(330), 300), (m(150), 255), 46, 9, ORANGE, GOLD)
        plume((m(498), 415), (m(300), 385), (m(115), 385), 50, 10, DEEPRED, ORANGE)
        plume((m(505), 440), (m(330), 475), (m(185), 505), 40, 9, ORANGE, GOLD)
        plume((m(508), 415), (m(360), 330), (m(285), 300), 28, 7, YELLOW, PALE)
    # head: dark outline ring, then bright disc, beak pointing right
    disc(512, 232, 20, (120, 40, 10), 0.85, "blend")
    disc(512, 232, 16, PALE, 1.0, "blend")
    disc(512, 232, 9, (255, 255, 245), 1.0, "blend")
    for yy in range(226, 240):
        w = 12 - abs(yy - 232)
        for xx in range(524, 524 + w):
            setc(xx, yy, 255, 180, 40)
    # crest plumes
    plume((505, 220), (470, 190), (430, 175), 10, 3, GOLD, PALE, a=0.9)
    plume((520, 220), (555, 192), (595, 178), 10, 3, GOLD, PALE, a=0.9)
    setc(519, 229, 40, 20, 10)
    setc(520, 229, 40, 20, 10)
    setc(519, 230, 40, 20, 10)
    setc(520, 230, 40, 20, 10)


def embers(rng):
    for _ in range(150):
        ang = rng.uniform(-1.35, 1.35)
        dist = rng.uniform(60, 430)
        x = 512 + math.sin(ang) * dist * rng.uniform(0.4, 1.0)
        y = 470 - math.cos(ang) * dist * rng.uniform(0.5, 1.0)
        if y < 60 or y > 760:
            continue
        r = rng.choice([1, 1, 2, 2, 3])
        col = rng.choice([GOLD, ORANGE, (255, 160, 60)])
        disc(x, y, r, col, 0.95)
        if r >= 2:
            disc(x, y, r * 2.5, col, 0.12)


FONT = {
    "R": ["01110", "10001", "10001", "01110", "10100", "10010", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
}


def text(word, cx, y, scale, fg, shadow):
    total = len(word) * 5 * scale + (len(word) - 1) * scale
    x = cx - total // 2
    for ch in word:
        glyph = FONT[ch]
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == "1":
                    bx = x + col * scale
                    by = y + row * scale
                    for yy in range(by + 3, by + scale + 3):
                        for xx in range(bx + 3, bx + scale + 3):
                            setc(xx, yy, *shadow)
                    for yy in range(by, by + scale):
                        for xx in range(bx, bx + scale):
                            setc(xx, yy, *fg)
        x += 5 * scale + scale


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += fb[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        return out + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    rng = random.Random(SEED)
    background(rng)
    mountains(rng)
    # warm horizon glow band behind the ridges
    for y in range(700, 800):
        a = 0.20 * (1 - abs(y - 748) / 52.0)
        for x in range(300, 725):
            add(x, y, 255, 140, 50, a * (1 - abs(x - 512) / 260.0))
    ring(512, 470, 440, 115, -16, front=False)
    phoenix()
    ring(512, 470, 440, 115, -16, front=True)
    embers(rng)
    text("RISE", 512, 64, 12, (255, 205, 80), (70, 25, 0))
    path = os.path.join(OUT_DIR, "entry.png")
    n = write_png(path)
    print(f"wrote {path} {n} bytes")


if __name__ == "__main__":
    main()
