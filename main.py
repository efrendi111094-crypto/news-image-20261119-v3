#!/usr/bin/env python3
"""Render the front page for Thursday 19 November 2026 -> entry.png.

One self-contained program, Python 3 standard library only. It paints a
1024x1024 newspaper front page into an RGB buffer with hand-rolled
drawing routines, sets the type with a 5x7 pixel font stored here as row
bitmasks (bit 4 is the leftmost pixel), and writes a deterministic PNG
with zlib. No network, no local imports, no files outside this folder.
Two runs write identical bytes.
"""

import sys

sys.dont_write_bytecode = True

import json
import os
import struct
import zlib

PAGE_W, PAGE_H = 1024, 1024

# Newsprint palette.
PAPER = (248, 244, 232)
INK = (20, 20, 20)
NAVY = (30, 58, 95)
NAVY_DEEP = (20, 40, 66)
RED = (185, 28, 28)
CARD_BG = (255, 255, 255)
EDGE = (216, 210, 192)
PANEL_BG = (232, 237, 243)
GREY = (90, 90, 90)
WHITE = (255, 255, 255)
GOLD = (212, 160, 32)
SKY = (120, 170, 220)
GREEN = (34, 120, 60)
ORANGE = (230, 120, 30)
BROWN = (150, 110, 60)

# ---- 5x7 pixel font ---------------------------------------------------
# Each character maps to seven row bitmasks. Unknown characters render
# as a blank (seven zero rows), never an error.
BLANK = (0, 0, 0, 0, 0, 0, 0)
FONT = {
    'A': (14, 17, 17, 31, 17, 17, 17),
    'B': (30, 17, 17, 30, 17, 17, 30),
    'C': (14, 17, 16, 16, 16, 17, 14),
    'D': (30, 17, 17, 17, 17, 17, 30),
    'E': (31, 16, 16, 30, 16, 16, 31),
    'F': (31, 16, 16, 30, 16, 16, 16),
    'G': (14, 17, 16, 23, 17, 17, 14),
    'H': (17, 17, 17, 31, 17, 17, 17),
    'I': (14, 4, 4, 4, 4, 4, 14),
    'J': (7, 2, 2, 2, 2, 18, 12),
    'K': (17, 18, 20, 24, 20, 18, 17),
    'L': (16, 16, 16, 16, 16, 16, 31),
    'M': (17, 27, 21, 21, 17, 17, 17),
    'N': (17, 25, 21, 19, 17, 17, 17),
    'O': (14, 17, 17, 17, 17, 17, 14),
    'P': (30, 17, 17, 30, 16, 16, 16),
    'Q': (14, 17, 17, 17, 21, 18, 13),
    'R': (30, 17, 17, 30, 20, 18, 17),
    'S': (15, 16, 16, 14, 1, 1, 30),
    'T': (31, 4, 4, 4, 4, 4, 4),
    'U': (17, 17, 17, 17, 17, 17, 14),
    'V': (17, 17, 17, 17, 17, 10, 4),
    'W': (17, 17, 17, 21, 21, 27, 17),
    'X': (17, 17, 10, 4, 10, 17, 17),
    'Y': (17, 17, 10, 4, 4, 4, 4),
    'Z': (31, 1, 2, 4, 8, 16, 31),
    '0': (14, 19, 21, 25, 17, 17, 14),
    '1': (4, 12, 4, 4, 4, 4, 14),
    '2': (14, 17, 1, 2, 4, 8, 31),
    '3': (14, 17, 1, 6, 1, 17, 14),
    '4': (2, 6, 10, 18, 31, 2, 2),
    '5': (31, 16, 30, 1, 1, 17, 14),
    '6': (14, 16, 16, 30, 17, 17, 14),
    '7': (31, 1, 2, 2, 4, 4, 4),
    '8': (14, 17, 17, 14, 17, 17, 14),
    '9': (14, 17, 17, 15, 1, 1, 14),
}
FONT.update({
    'a': (0, 0, 14, 1, 15, 17, 15),
    'b': (16, 16, 30, 17, 17, 17, 30),
    'c': (0, 0, 14, 16, 16, 16, 14),
    'd': (1, 1, 15, 17, 17, 17, 15),
    'e': (0, 0, 14, 17, 31, 16, 14),
    'f': (6, 9, 8, 28, 8, 8, 8),
    'g': (0, 0, 15, 17, 17, 15, 1),
    'h': (16, 16, 30, 17, 17, 17, 17),
    'i': (4, 0, 12, 4, 4, 4, 14),
    'j': (2, 0, 6, 2, 2, 2, 12),
    'k': (16, 16, 18, 20, 24, 20, 18),
    'l': (12, 4, 4, 4, 4, 4, 14),
    'm': (0, 0, 26, 21, 21, 21, 21),
    'n': (0, 0, 30, 17, 17, 17, 17),
    'o': (0, 0, 14, 17, 17, 17, 14),
    'p': (0, 0, 30, 17, 17, 30, 16),
    'q': (0, 0, 15, 17, 17, 15, 1),
    'r': (0, 0, 22, 25, 16, 16, 16),
    's': (0, 0, 15, 16, 14, 1, 30),
    't': (8, 8, 28, 8, 8, 8, 6),
    'u': (0, 0, 17, 17, 17, 19, 13),
    'v': (0, 0, 17, 17, 17, 10, 4),
    'w': (0, 0, 17, 21, 21, 21, 10),
    'x': (0, 0, 17, 10, 4, 10, 17),
    'y': (0, 0, 17, 17, 19, 15, 1),
    'z': (0, 0, 31, 2, 4, 8, 31),
    ' ': (0, 0, 0, 0, 0, 0, 0),
    '.': (0, 0, 0, 0, 0, 12, 12),
    ',': (0, 0, 0, 0, 12, 12, 8),
    ':': (0, 12, 12, 0, 12, 12, 0),
    ';': (0, 12, 12, 0, 12, 12, 8),
    '!': (4, 4, 4, 4, 4, 0, 4),
    '?': (14, 17, 1, 2, 4, 0, 4),
    "'": (4, 4, 8, 0, 0, 0, 0),
    '"': (10, 10, 10, 0, 0, 0, 0),
    '-': (0, 0, 0, 31, 0, 0, 0),
    '(': (3, 4, 4, 4, 4, 4, 3),
    ')': (24, 4, 4, 4, 4, 4, 24),
    '/': (1, 1, 2, 4, 8, 16, 16),
    '&': (12, 18, 20, 8, 21, 18, 13),
    '%': (25, 26, 2, 4, 8, 23, 19),
    '$': (4, 15, 20, 14, 5, 30, 4),
    '#': (10, 10, 31, 10, 31, 10, 10),
    '@': (14, 17, 23, 21, 20, 16, 14),
    '+': (0, 4, 4, 31, 4, 4, 0),
    '*': (0, 10, 4, 31, 4, 10, 0),
    '=': (0, 0, 31, 0, 31, 0, 0),
    '<': (2, 4, 8, 16, 8, 4, 2),
    '>': (16, 8, 4, 2, 4, 8, 16),
    '_': (0, 0, 0, 0, 0, 0, 31),
    '[': (14, 8, 8, 8, 8, 8, 14),
    ']': (14, 2, 2, 2, 2, 2, 14),
    '{': (6, 8, 8, 28, 8, 8, 6),
    '}': (24, 4, 4, 7, 4, 4, 24),
    '|': (4, 4, 4, 4, 4, 4, 4),
    '\\': (16, 16, 8, 4, 2, 1, 1),
    '~': (0, 0, 13, 21, 0, 0, 0),
    '^': (4, 10, 0, 0, 0, 0, 0),
    '`': (8, 4, 0, 0, 0, 0, 0),
    '\u2022': (0, 0, 14, 14, 14, 0, 0),
})


def rows_for(ch):
    """Bitmask rows for a character; blank for anything unlisted."""
    return FONT.get(ch, BLANK)


# ---- Canvas ------------------------------------------------------------
class Screen:
    """An RGB raster with a small set of drawing routines."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.pxbuf = bytearray(bg * (w * h))

    def dot(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.pxbuf[i] = c[0]
            self.pxbuf[i + 1] = c[1]
            self.pxbuf[i + 2] = c[2]

    def box(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        fill = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            self.pxbuf[base:base + len(fill)] = fill

    def outline(self, x, y, w, h, c, t=2):
        self.box(x, y, w, t, c)
        self.box(x, y + h - t, w, t, c)
        self.box(x, y, t, h, c)
        self.box(x + w - t, y, t, h, c)

    def seg(self, x0, y0, x1, y1, c):
        """A line by Bresenham's algorithm."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.dot(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def spot(self, cx, cy, r, c):
        """A filled circle."""
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.box(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def halo(self, cx, cy, r, c, t=2):
        """A ring, drawn as four arcs of dots."""
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            for xx in (cx - dx, cx + dx):
                for k in range(t):
                    self.dot(xx - k if xx == cx - dx else xx + k,
                             cy + dy, c)
        for dx in range(-r, r + 1):
            dy = int((r * r - dx * dx) ** 0.5)
            for yy in (cy - dy, cy + dy):
                for k in range(t):
                    self.dot(cx + dx,
                             yy - k if yy == cy - dy else yy + k, c)

    def wedge(self, p1, p2, p3, c):
        """A filled triangle by horizontal scanlines."""
        pts = sorted((p1, p2, p3), key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        if ay == cy:
            return
        for y in range(ay, cy + 1):
            if y < by:
                f = (y - ay) / (by - ay) if by != ay else 0.0
                xa = ax + (bx - ax) * f
            else:
                f = (y - by) / (cy - by) if cy != by else 0.0
                xa = bx + (cx - bx) * f
            xb = ax + (cx - ax) * ((y - ay) / (cy - ay))
            lo, hi = sorted((int(xa), int(xb)))
            self.box(lo, y, hi - lo + 1, 1, c)


# ---- Text ---------------------------------------------------------------
def step(scale):
    return 5 * scale + 2


def measure(s, scale):
    return len(s) * step(scale) - 2 if s else 0


def put_text(sc, x, y, s, scale, c):
    """Draw a string; every set pixel is a scale x scale block."""
    cx = x
    for ch in s:
        rows = rows_for(ch)
        for row in range(7):
            bits = rows[row]
            for col in range(5):
                if bits & (16 >> col):
                    sc.box(cx + col * scale, y + row * scale,
                           scale, scale, c)
        cx += step(scale)


def put_text_mid(sc, cx, y, s, scale, c):
    put_text(sc, cx - measure(s, scale) // 2, y, s, scale, c)


def wrap(s, max_w, scale):
    """Greedy word wrap into lines no wider than max_w."""
    lines, cur = [], ''
    for word in s.split(' '):
        trial = word if not cur else cur + ' ' + word
        if measure(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---- PNG ----------------------------------------------------------------
def encode_png(sc):
    raw = bytearray()
    stride = sc.w * 3
    for y in range(sc.h):
        raw.append(0)
        raw += sc.pxbuf[y * stride:(y + 1) * stride]
    blob = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack('>I', len(data)) + kind + data
        out += struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack('>IIBBBBB', sc.w, sc.h, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', blob) + chunk(b'IEND', b''))

# ---- Pictograms ----------------------------------------------------------
# Twelve small original line drawings, one per story picture. Each takes
# the top-left corner of a square box and the box size, and draws only
# with the Screen primitives above.
def pct(s, p):
    return int(s * p / 100)


def pic_summit(sc, x, y, s):
    # Three flags above a round table: three leaders, one meeting.
    top = y + pct(s, 66)
    sc.box(x + pct(s, 10), top, pct(s, 80), pct(s, 8), NAVY)
    sc.box(x + pct(s, 46), top + pct(s, 8), pct(s, 8), pct(s, 22), NAVY)
    for i, col in enumerate((RED, GOLD, NAVY)):
        px = x + pct(s, 22 + i * 28)
        sc.seg(px, y + pct(s, 10), px, top, INK)
        sc.box(px, y + pct(s, 10), pct(s, 16), pct(s, 12), col)
        sc.spot(px + pct(s, 4), y + pct(s, 50), pct(s, 8), INK)


def pic_scales(sc, x, y, s):
    # Justice scales: a post, a beam, two pans, a base.
    cx = x + s // 2
    sc.box(cx - 2, y + pct(s, 12), 4, pct(s, 62), NAVY)
    sc.box(x + pct(s, 14), y + pct(s, 16), pct(s, 72), pct(s, 6), NAVY)
    for side in (-1, 1):
        px = cx + side * pct(s, 30)
        sc.seg(px, y + pct(s, 22), px - pct(s, 12), y + pct(s, 52), NAVY)
        sc.seg(px, y + pct(s, 22), px + pct(s, 12), y + pct(s, 52), NAVY)
        sc.seg(px - pct(s, 12), y + pct(s, 52), px + pct(s, 12),
               y + pct(s, 52), NAVY)
        sc.spot(px, y + pct(s, 22), 3, RED)
    sc.box(x + pct(s, 30), y + pct(s, 74), pct(s, 40), pct(s, 8), NAVY)
    sc.box(x + pct(s, 22), y + pct(s, 82), pct(s, 56), pct(s, 6), NAVY)


def pic_game(sc, x, y, s):
    # A game controller: body, grips, d-pad, two buttons.
    sc.box(x + pct(s, 10), y + pct(s, 28), pct(s, 80), pct(s, 40), NAVY)
    sc.spot(x + pct(s, 18), y + pct(s, 62), pct(s, 12), NAVY)
    sc.spot(x + pct(s, 82), y + pct(s, 62), pct(s, 12), NAVY)
    sc.box(x + pct(s, 20), y + pct(s, 42), pct(s, 6), pct(s, 18), WHITE)
    sc.box(x + pct(s, 14), y + pct(s, 48), pct(s, 18), pct(s, 6), WHITE)
    sc.spot(x + pct(s, 72), y + pct(s, 44), pct(s, 5), RED)
    sc.spot(x + pct(s, 82), y + pct(s, 54), pct(s, 5), GOLD)
    sc.box(x + pct(s, 44), y + pct(s, 34), pct(s, 12), pct(s, 5), SKY)


def pic_chartup(sc, x, y, s):
    # Rising bars under a climbing arrow: a market that jumped.
    base = y + pct(s, 82)
    for i, h in enumerate((26, 44, 62)):
        bx = x + pct(s, 14 + i * 24)
        sc.box(bx, base - pct(s, h), pct(s, 16), pct(s, h), GREEN)
    sc.seg(x + pct(s, 10), y + pct(s, 30), x + pct(s, 50),
           y + pct(s, 14), RED)
    sc.seg(x + pct(s, 50), y + pct(s, 14), x + pct(s, 88),
           y + pct(s, 6), RED)
    sc.seg(x + pct(s, 88), y + pct(s, 6), x + pct(s, 76),
           y + pct(s, 6), RED)
    sc.seg(x + pct(s, 88), y + pct(s, 6), x + pct(s, 88),
           y + pct(s, 18), RED)


def pic_bridge(sc, x, y, s):
    # A bridge deck with a blast bursting above it.
    deck = y + pct(s, 66)
    sc.box(x + pct(s, 6), deck, pct(s, 88), pct(s, 6), NAVY)
    sc.box(x + pct(s, 20), y + pct(s, 30), pct(s, 8), pct(s, 40), NAVY)
    sc.box(x + pct(s, 72), y + pct(s, 30), pct(s, 8), pct(s, 40), NAVY)
    sc.seg(x + pct(s, 24), y + pct(s, 30), x + pct(s, 50), deck, NAVY)
    sc.seg(x + pct(s, 76), y + pct(s, 30), x + pct(s, 50), deck, NAVY)
    bx, by = x + pct(s, 50), y + pct(s, 22)
    for dx, dy in ((-14, -6), (-6, -14), (0, -16), (6, -14), (14, -6),
                   (-14, 6), (14, 6)):
        sc.seg(bx, by, bx + pct(s, dx), by + pct(s, dy), RED)
    sc.spot(bx, by, pct(s, 6), ORANGE)


def pic_chartdown(sc, x, y, s):
    # Falling bars under a sinking arrow: a market that slid.
    base = y + pct(s, 82)
    for i, h in enumerate((62, 44, 26)):
        bx = x + pct(s, 14 + i * 24)
        sc.box(bx, base - pct(s, h), pct(s, 16), pct(s, h), RED)
    sc.seg(x + pct(s, 10), y + pct(s, 6), x + pct(s, 50),
           y + pct(s, 20), NAVY)
    sc.seg(x + pct(s, 50), y + pct(s, 20), x + pct(s, 88),
           y + pct(s, 34), NAVY)
    sc.seg(x + pct(s, 88), y + pct(s, 34), x + pct(s, 76),
           y + pct(s, 34), NAVY)
    sc.seg(x + pct(s, 88), y + pct(s, 34), x + pct(s, 88),
           y + pct(s, 22), NAVY)


def pic_storm(sc, x, y, s):
    # A cyclone: two spiral rings, a red eye, rain below.
    cx, cy = x + s // 2, y + pct(s, 38)
    sc.halo(cx, cy, pct(s, 26), NAVY, 4)
    sc.halo(cx + pct(s, 6), cy + pct(s, 4), pct(s, 16), NAVY, 4)
    sc.spot(cx, cy, pct(s, 6), RED)
    for rx in (18, 38, 58, 78):
        sc.seg(x + pct(s, rx), y + pct(s, 72), x + pct(s, rx - 6),
               y + pct(s, 88), SKY)


def pic_leaf(sc, x, y, s):
    # A young sprout: a stem, two leaves, a seedling dot.
    cx = x + s // 2
    sc.seg(cx, y + pct(s, 88), cx, y + pct(s, 46), GREEN)
    sc.wedge((cx, y + pct(s, 46)), (cx - pct(s, 30), y + pct(s, 30)),
             (cx - pct(s, 4), y + pct(s, 62)), GREEN)
    sc.wedge((cx, y + pct(s, 46)), (cx + pct(s, 30), y + pct(s, 30)),
             (cx + pct(s, 4), y + pct(s, 62)), GREEN)
    sc.spot(cx, y + pct(s, 34), pct(s, 8), GREEN)
    sc.box(x + pct(s, 20), y + pct(s, 88), pct(s, 60), pct(s, 6), BROWN)


def pic_flame(sc, x, y, s):
    # A flame: an orange teardrop with a golden tongue.
    cx = x + s // 2
    sc.spot(cx, y + pct(s, 62), pct(s, 26), ORANGE)
    sc.wedge((cx - pct(s, 22), y + pct(s, 66)),
             (cx + pct(s, 22), y + pct(s, 66)),
             (cx + pct(s, 6), y + pct(s, 12)), ORANGE)
    sc.spot(cx, y + pct(s, 66), pct(s, 14), GOLD)
    sc.wedge((cx - pct(s, 10), y + pct(s, 70)),
             (cx + pct(s, 10), y + pct(s, 70)),
             (cx, y + pct(s, 38)), GOLD)


def pic_rocket(sc, x, y, s):
    # A rocket climbing past four small stars.
    cx = x + s // 2
    sc.box(cx - pct(s, 10), y + pct(s, 26), pct(s, 20), pct(s, 38), NAVY)
    sc.wedge((cx - pct(s, 10), y + pct(s, 26)),
             (cx + pct(s, 10), y + pct(s, 26)),
             (cx, y + pct(s, 6)), RED)
    sc.wedge((cx - pct(s, 10), y + pct(s, 50)),
             (cx - pct(s, 22), y + pct(s, 70)),
             (cx - pct(s, 10), y + pct(s, 64)), RED)
    sc.wedge((cx + pct(s, 10), y + pct(s, 50)),
             (cx + pct(s, 22), y + pct(s, 70)),
             (cx + pct(s, 10), y + pct(s, 64)), RED)
    sc.wedge((cx - pct(s, 6), y + pct(s, 64)),
             (cx + pct(s, 6), y + pct(s, 64)),
             (cx, y + pct(s, 86)), ORANGE)
    sc.spot(cx, y + pct(s, 40), pct(s, 5), SKY)
    for sx, sy in ((12, 16), (86, 22), (80, 78), (14, 74)):
        sc.box(x + pct(s, sx), y + pct(s, sy), 3, 3, GOLD)


def pic_painting(sc, x, y, s):
    # A framed canvas: a sun, a swirling line, a green base.
    sc.outline(x + pct(s, 8), y + pct(s, 14), pct(s, 84), pct(s, 68),
               BROWN, 5)
    sc.spot(x + pct(s, 62), y + pct(s, 36), pct(s, 12), GOLD)
    sc.seg(x + pct(s, 16), y + pct(s, 62), x + pct(s, 40),
           y + pct(s, 48), SKY)
    sc.seg(x + pct(s, 40), y + pct(s, 48), x + pct(s, 60),
           y + pct(s, 62), SKY)
    sc.seg(x + pct(s, 60), y + pct(s, 62), x + pct(s, 84),
           y + pct(s, 48), SKY)
    sc.box(x + pct(s, 16), y + pct(s, 70), pct(s, 68), pct(s, 4), GREEN)


def pic_shield(sc, x, y, s):
    # A shield with a white star: security forces.
    cx = x + s // 2
    sc.box(cx - pct(s, 26), y + pct(s, 12), pct(s, 52), pct(s, 40), NAVY)
    sc.wedge((cx - pct(s, 26), y + pct(s, 52)),
             (cx + pct(s, 26), y + pct(s, 52)),
             (cx, y + pct(s, 88)), NAVY)
    sc.spot(cx, y + pct(s, 40), pct(s, 9), WHITE)
    sc.box(cx - 2, y + pct(s, 26), 4, pct(s, 28), WHITE)
    sc.box(cx - pct(s, 14), y + pct(s, 38), pct(s, 28), 4, WHITE)


PICS = {
    'summit': pic_summit,
    'scales': pic_scales,
    'game': pic_game,
    'chartup': pic_chartup,
    'bridge': pic_bridge,
    'chartdown': pic_chartdown,
    'storm': pic_storm,
    'leaf': pic_leaf,
    'flame': pic_flame,
    'rocket': pic_rocket,
    'painting': pic_painting,
    'shield': pic_shield,
}


def draw_pic(sc, name, x, y, s):
    fn = PICS.get(name)
    if fn is not None:
        fn(sc, x, y, s)

# ---- Page layout ----------------------------------------------------------
# 1024 x 1024: navy masthead, one wide hero, two half heroes, a 3x3 grid
# of illustrated cards, a two-column briefs list, a UTC timeline strip
# and a footer carrying the date check and the sources.
MARGIN = 24
CONTENT_W = PAGE_W - 2 * MARGIN


def panel(sc, x, y, w, h):
    sc.box(x, y, w, h, CARD_BG)
    sc.outline(x, y, w, h, EDGE, 2)


def icon_box(sc, x, y, s, name):
    sc.box(x, y, s, s, PANEL_BG)
    sc.outline(x, y, s, s, EDGE, 1)
    draw_pic(sc, name, x + 4, y + 4, s - 8)


def masthead(sc, data):
    sc.box(0, 0, PAGE_W, 100, NAVY)
    put_text_mid(sc, PAGE_W // 2, 10, data['masthead'], 6, WHITE)
    put_text_mid(sc, PAGE_W // 2, 58, data['date'], 2, GOLD)
    put_text_mid(sc, PAGE_W // 2, 76, data['tagline'], 2, WHITE)
    sc.box(0, 96, PAGE_W, 4, RED)


def hero_wide(sc, data):
    x, y, w, h = MARGIN, 106, CONTENT_W, 126
    panel(sc, x, y, w, h)
    story = data['heroes'][0]
    icon_box(sc, x + 8, y + 9, 108, story['icon'])
    tx, tw = x + 132, w - 132 - 12
    put_text(sc, tx, y + 10, story['kicker'], 2, RED)
    put_text(sc, tx, y + 30, story['headline'], 4, INK)
    for i, line in enumerate(wrap(story['summary'], tw, 2)[:3]):
        put_text(sc, tx, y + 64 + i * 18, line, 2, INK)


def hero_half(sc, data):
    half = (CONTENT_W - 24) // 2
    for k in (1, 2):
        story = data['heroes'][k]
        x, y, h = MARGIN + (k - 1) * (half + 24), 238, 134
        panel(sc, x, y, half, h)
        icon_box(sc, x + 8, y + 13, 108, story['icon'])
        tx, tw = x + 124, half - 124 - 12
        put_text(sc, tx, y + 10, story['kicker'], 2, RED)
        for i, line in enumerate(wrap(story['headline'], tw, 3)[:2]):
            put_text(sc, tx, y + 30 + i * 24, line, 3, INK)
        for i, line in enumerate(wrap(story['summary'], tw, 2)[:3]):
            put_text(sc, tx, y + 82 + i * 18, line, 2, INK)


def card_grid(sc, data):
    col = (CONTENT_W - 16) // 3
    for idx, story in enumerate(data['cards']):
        r, c = divmod(idx, 3)
        x, y = MARGIN + c * (col + 8), 378 + r * 80
        panel(sc, x, y, col, 74)
        icon_box(sc, x + 8, y + 8, 58, story['icon'])
        tx, tw = x + 74, col - 74 - 8
        put_text(sc, tx, y + 8, story['kicker'], 2, RED)
        for i, line in enumerate(wrap(story['headline'], tw, 2)[:3]):
            put_text(sc, tx, y + 26 + i * 18, line, 2, INK)


def briefs(sc, data):
    put_text(sc, MARGIN, 620, 'MORE OF THE DAY', 2, RED)
    sc.box(MARGIN, 636, CONTENT_W, 2, EDGE)
    bw = (CONTENT_W - 24) // 2
    for idx, item in enumerate(data['briefs']):
        r, c = divmod(idx, 2)
        bx = MARGIN + c * (bw + 24)
        by = 646 + r * 17
        sc.box(bx, by + 3, 8, 8, RED)
        put_text(sc, bx + 14, by, item['headline'], 2, INK)


def timeline(sc, data):
    sc.box(MARGIN, 848, CONTENT_W, 80, PANEL_BG)
    sc.outline(MARGIN, 848, CONTENT_W, 80, EDGE, 1)
    put_text(sc, MARGIN + 10, 854, 'THROUGH THE DAY  --  UTC', 2, NAVY)
    tw = (CONTENT_W - 20 - 24) // 2
    for idx, item in enumerate(data['timeline']):
        r, c = divmod(idx, 2)
        tx = MARGIN + 10 + c * (tw + 24)
        ty = 876 + r * 18
        put_text(sc, tx, ty, item['time'], 2, RED)
        put_text(sc, tx + 72, ty, item['text'], 2, INK)


def footer(sc, data):
    sc.box(MARGIN, 934, CONTENT_W, 4, RED)
    put_text(sc, MARGIN, 946,
             'DATE CHECK: Thursday 19 November 2026', 2, INK)
    put_text(sc, MARGIN, 964,
             'Every story above happened or was first reported on '
             'this day.', 2, INK)
    put_text(sc, MARGIN, 982, 'SOURCES: ' + data['sources'], 2, GREY)
    put_text(sc, MARGIN, 1000, data['footer'], 2, GREY)


def build_page(data):
    sc = Screen(PAGE_W, PAGE_H, PAPER)
    masthead(sc, data)
    hero_wide(sc, data)
    hero_half(sc, data)
    card_grid(sc, data)
    briefs(sc, data)
    timeline(sc, data)
    footer(sc, data)
    return sc


def load_data():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'news.json'), encoding='utf-8') as f:
        return json.load(f)


def main():
    data = load_data()
    total = (len(data['heroes']) + len(data['cards'])
             + len(data['briefs']))
    print(f'stories: {total} ({len(data["heroes"])} heroes, '
          f'{len(data["cards"])} cards, {len(data["briefs"])} briefs)')
    sc = build_page(data)
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, 'entry.png')
    with open(path, 'wb') as f:
        f.write(encode_png(sc))
    print(f'wrote {path} ({os.path.getsize(path)} bytes, '
          f'{PAGE_W}x{PAGE_H})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
