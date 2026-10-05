"""Minecraft, painted by Monet: block textures, skies and the 2D side-view world, all in broken colour.

Every texture is 8x8 texels, laid down as a ground coat plus short dabs from a Monet palette -- warm gold
in the lights, lilac and blue in the shadows -- so a grass block still reads as a grass block, but up close
it is a little impressionist canvas. Images are indexed PNGs (stdlib zlib only), shown with
image-rendering: pixelated.
"""
import base64
import functools
import math
import random
import struct
import zlib

TEX = 8  # texels per block edge


# ------------------------------------------------------------------------------------ colour

def hx(s):
    return (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16))


def mix(a, b, u):
    u = 0.0 if u < 0 else 1.0 if u > 1 else u
    return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u)


def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def to_hex(c):
    return "#" + "".join(f"{int(clamp(round(v), 0, 255)):02x}" for v in c)


LILAC = hx("#6c64a8")
GOLD = hx("#ffd890")


def monet_shade(c, k):
    """Monet's shadows are coloured: darken toward lilac-blue instead of black."""
    return mix(tuple(v * k for v in c), LILAC, (1 - k) * 0.55)


def monet_light(c, k):
    return mix(c, GOLD, k)


class Noise:
    def __init__(self, seed):
        self.seed = seed * 1442695041 & 0xFFFFFFFF

    def _h(self, ix, iy):
        n = (ix * 374761393 + iy * 668265263 + self.seed) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

    def __call__(self, x, y):
        ix, iy = math.floor(x), math.floor(y)
        fx, fy = x - ix, y - iy
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = self._h(ix, iy), self._h(ix + 1, iy)
        c, d = self._h(ix, iy + 1), self._h(ix + 1, iy + 1)
        return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy

    def fbm(self, x, y, octaves=3):
        s, amp, norm = 0.0, 1.0, 0.0
        for k in range(octaves):
            s += amp * self(x * (2 ** k) + k * 17.3, y * (2 ** k) - k * 9.1)
            norm += amp
            amp *= 0.5
        return s / norm


# --------------------------------------------------------------------------------------- PNG

def png_uri(px, w, h):
    """px: flat list of RGB tuples or None (transparent). Indexed PNG with tRNS."""
    q = []
    for c in px:
        q.append(None if c is None else tuple(min(255, max(0, int(v / 4 + 0.5) * 4)) for v in c))
    pal = sorted({c for c in q if c is not None})
    step = 4
    while len(pal) > 255:
        step += 2
        q = [None if c is None else tuple(min(255, int(v / step + 0.5) * step) for v in c) for c in q]
        pal = sorted({c for c in q if c is not None})
    has_alpha = any(c is None for c in q)
    idx = {c: i + (1 if has_alpha else 0) for i, c in enumerate(pal)}
    plte = ([(0, 0, 0)] if has_alpha else []) + pal
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(0 if c is None else idx[c] for c in q[y * w:(y + 1) * w])

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
    png += chunk(b"PLTE", b"".join(bytes(c) for c in plte))
    if has_alpha:
        png += chunk(b"tRNS", b"\x00")
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode()


# ---------------------------------------------------------------------------------- textures

def P(*h):
    return [hx(c) for c in h]


PAL = {  # base coat, accent dabs
    "grass": (P("#7fae4e", "#8cbc58", "#6f9f45"), P("#b8d070", "#5a8a50", "#9aa8d8", "#d8d07a", "#4f7a46")),
    "dirt": (P("#8f6a48", "#7f5c3e", "#9a7650"), P("#6e5a7a", "#b08a60", "#5e4632", "#a07a8a")),
    "stone": (P("#8e90a4", "#9a9cae", "#86889c"), P("#b4b6c8", "#6e7090", "#a8a0b8", "#c8c0d0")),
    "sand": (P("#e6d4a2", "#ecdcae", "#dcc896"), P("#f4e6c0", "#d8b890", "#e8c8b8", "#c8b8d0")),
    "snow": (P("#f2f2f6", "#e8e8f2"), P("#cdd4ec", "#ffffff", "#d8d0e8", "#c0c8e8")),
    "water": (P("#4c70b0", "#5a80c0", "#4a68a8"), P("#88a8e0", "#3a5a98", "#c8d8f0", "#7a7ac8", "#6a9ad0")),
    "leaves": (P("#4f8a3a", "#5e9a44", "#447a34"), P("#86b858", "#3e6a38", "#a8c870", "#7a8ab8")),
    "leaves_autumn": (P("#e0a048", "#d08a3a", "#e8b858"), P("#f4d070", "#b06a2a", "#c86a4a", "#9a8ab8")),
    "leaves_cherry": (P("#f0b4cc", "#e8a0bc", "#f6c8d8"), P("#fce0ea", "#d888a8", "#c8a0d8", "#ffffff")),
    "leaves_spruce": (P("#3e6050", "#4a6e5a", "#36584a"), P("#2c4a3c", "#e8eef4", "#6a8a78", "#8a9ac0")),
    "planks": (P("#b8945f", "#c4a06a", "#ae8a56"), P("#d8b47a", "#8a6a40", "#a88aa0")),
    "obsidian": (P("#1e1630", "#261c3c", "#18122a"), P("#3a2a5e", "#5a4488", "#120c20")),
    "end_stone": (P("#e6e2ae", "#ddd8a0", "#ece8bc"), P("#c8c48a", "#f6f2cc", "#b8b4c8")),
    "emerald": (P("#3ad06a", "#2ebc5c", "#48dc78"), P("#a6f8c0", "#1a8a40", "#7ad8c8")),
    "gold": (P("#f6d040", "#f0c030", "#fadc58"), P("#fff2a0", "#d09a20", "#f0b070")),
    "diamond": (P("#6ae0dc", "#5ad4d0", "#7ae8e4"), P("#d0fffc", "#3aa8b0", "#a0c8f0")),
    "lapis": (P("#2a4aa8", "#3456b8", "#24409a"), P("#6a8ae0", "#1a2a78", "#a0a0e0")),
    "redstone": (P("#c02818", "#d03020", "#b02010"), P("#f06a4a", "#801808", "#e08a8a")),
    "iron": (P("#dcdcdc", "#e8e8e8", "#d0d0d4"), P("#ffffff", "#b4b4c4", "#c8c0d8")),
    "amethyst": (P("#8a62c8", "#9a72d8", "#7a54b8"), P("#d0b0f8", "#5a3a98", "#e8c8ff")),
    "glass": (P("#c8e4f0", "#d8eef6"), P("#ffffff", "#a8c8e0")),
    "wool": (P("#eeeae4", "#e4e0da"), P("#ffffff", "#ccc8d8")),
    "hay": (P("#d4b03a", "#c9a12e", "#dcbc48"), P("#ecd468", "#a8822a", "#e0c070")),
    "pumpkin": (P("#e0862a", "#d4781e", "#e89438"), P("#f4b058", "#b05a14", "#c87a8a")),
    "terracotta": (P("#b86a4a", "#c47652", "#ae6244"), P("#d88a6a", "#8a4a3a", "#a87aa0")),
    "brick": (P("#a85a48", "#b4644e", "#9c5242"), P("#c87a68", "#7a4034", "#d8c8b8")),
    "mossy": (P("#7e8a84", "#6a8a5a", "#889488"), P("#4e7a40", "#a0b8a0", "#9a9ab8")),
    "netherrack": (P("#7a3434", "#6e2e2e", "#843a3a"), P("#a04a4a", "#4e1e24", "#8a4a6a")),
    "purpur": (P("#a87ca8", "#b088b0", "#9e709e"), P("#c8a0c8", "#7a5a8a", "#e0c8e8")),
}


def _paint(name, seed, strokes=12, dirn=None):
    base, acc = PAL[name]
    r = random.Random(f"{name}:{seed}")
    g = [[None] * TEX for _ in range(TEX)]
    for y in range(TEX):
        for x in range(TEX):
            c = base[r.randrange(len(base))]
            j = r.gauss(0, 5)
            g[y][x] = (c[0] + j, c[1] + j, c[2] + j)
    for _ in range(strokes):
        x, y = r.randrange(TEX), r.randrange(TEX)
        c = acc[r.randrange(len(acc))]
        dx, dy = dirn if dirn else ((1, 0) if r.random() < 0.6 else (0, 1))
        for k in range(r.choice((1, 2, 2, 3))):
            xx, yy = x + k * dx, y + k * dy
            if 0 <= xx < TEX and 0 <= yy < TEX:
                g[yy][xx] = c
    return g


def texture(kind, seed=0):
    """8x8 texel grid (rows of RGB or None) for a block face kind."""
    if kind in ("grass_top", "snow_top"):
        return _paint("grass" if kind == "grass_top" else "snow", seed, 14)
    if kind in ("grass_side", "snow_side", "path_side"):
        g = _paint("dirt", seed, 9)
        top = _paint({"grass_side": "grass", "snow_side": "snow", "path_side": "dirt"}[kind], seed + 7, 6)
        r = random.Random(f"{kind}{seed}")
        for x in range(TEX):
            depth = 2 + (r.random() < 0.45) + (r.random() < 0.15)
            if kind == "path_side":
                depth = 1
            for y in range(depth):
                g[y][x] = top[y][x] if kind != "path_side" else monet_light(top[y][x], 0.15)
        return g
    if kind == "path_top":
        return [[monet_light(c, 0.12) for c in row] for row in _paint("dirt", seed, 16)]
    if kind in ("log_side", "birch_side"):
        g = _paint("planks", seed, 0)
        r = random.Random(f"{kind}{seed}")
        cols = P("#6e5232", "#7e6038", "#5e4428", "#86683e") if kind == "log_side" else P("#ece6da", "#e0dacc", "#f4f0e8")
        for x in range(TEX):
            c = cols[r.randrange(len(cols))]
            for y in range(TEX):
                g[y][x] = mix(c, cols[r.randrange(len(cols))], 0.3)
        if kind == "birch_side":
            for _ in range(5):
                x, y = r.randrange(TEX - 1), r.randrange(TEX)
                g[y][x] = hx("#3a3634")
                g[y][x + 1] = hx("#5a5450")
        return g
    if kind == "log_top":
        g = [[None] * TEX for _ in range(TEX)]
        for y in range(TEX):
            for x in range(TEX):
                d = max(abs(x - 3.5), abs(y - 3.5))
                g[y][x] = hx("#6e5232") if d > 3 else hx("#b89060") if int(d) % 2 else hx("#a07c4c")
        return g
    if kind == "planks":
        g = _paint("planks", seed, 8, (1, 0))
        for x in range(TEX):
            g[3][x] = hx("#8a6a40")
            g[7][x] = hx("#7a5c38")
        for y, x in ((0, 2), (1, 2), (2, 2), (4, 6), (5, 6), (6, 6)):
            g[y][x] = hx("#9a7848")
        return g
    if kind == "cobble":
        g = _paint("stone", seed, 6)
        r = random.Random(f"cob{seed}")
        for _ in range(12):
            x, y = r.randrange(TEX), r.randrange(TEX)
            g[y][x] = hx("#5e6078")
        return g
    if kind.startswith("ore_"):
        g = _paint("stone", seed, 8)
        dot = {"ore_coal": "#2a2a34", "ore_iron": "#d8a888", "ore_gold": "#f6d040", "ore_diamond": "#6ae0dc",
               "ore_lapis": "#3456c8", "ore_emerald": "#3ad06a", "ore_redstone": "#e03a2a"}[kind]
        r = random.Random(kind + str(seed))
        for _ in range(4):
            x, y = r.randrange(1, TEX - 1), r.randrange(1, TEX - 1)
            g[y][x] = hx(dot)
            g[y][x + 1] = mix(hx(dot), (255, 255, 255), 0.35)
        return g
    if kind in ("crafting_top", "crafting_side"):
        g = texture("planks", seed)
        if kind == "crafting_top":
            for i in range(TEX):
                g[0][i] = g[TEX - 1][i] = g[i][0] = g[i][TEX - 1] = hx("#6e5232")
                g[i][4] = g[4][i] = hx("#8a6a40")
        else:
            for y in range(2, 6):
                g[y][1] = hx("#7a7a90")
                g[y][6] = hx("#6e5232")
            g[2][2] = g[2][3] = hx("#9a9ab0")
            for x in range(TEX):
                g[0][x] = hx("#6e5232")
        return g
    if kind in ("hay_side", "hay_top"):
        g = _paint("hay", seed, 10, (0, 1) if kind == "hay_side" else None)
        if kind == "hay_side":
            for x in range(TEX):
                g[1][x] = g[6][x] = hx("#7a3c1c") if x % 3 else hx("#924a22")
        return g
    if kind in ("bookshelf",):
        g = texture("planks", seed)
        cols = P("#c04a3a", "#3a6ab0", "#5a9a4a", "#d8b040", "#8a5ab0", "#e8e0d0")
        r = random.Random(seed)
        for row in (1, 5):
            for x in range(TEX):
                c = cols[r.randrange(len(cols))]
                g[row][x] = c
                g[row + 1][x] = mix(c, (0, 0, 0), 0.2)
        return g
    if kind in ("lamp_on", "lamp_off"):
        on = kind == "lamp_on"
        g = [[None] * TEX for _ in range(TEX)]
        r = random.Random(kind)
        for y in range(TEX):
            for x in range(TEX):
                frame = x in (0, 7) or y in (0, 7) or (x + y) % 4 == 0
                c = (hx("#a87a40") if on else hx("#5a3e2a")) if frame else (hx("#ffe6a0") if on else hx("#7a5a3a"))
                g[y][x] = mix(c, (255, 250, 220) if on else (40, 30, 30), r.random() * 0.2)
        return g
    if kind == "command":
        g = _paint("terracotta", seed, 6)
        for i in range(TEX):
            g[0][i] = g[7][i] = g[i][0] = g[i][7] = hx("#d8a070")
        for y, x in ((3, 2), (4, 3), (5, 2), (5, 4), (5, 5)):
            g[y][x] = hx("#2a2a2a")
        return g
    if kind == "tnt":
        g = _paint("redstone", seed, 4)
        for x in range(TEX):
            for y in (3, 4):
                g[y][x] = hx("#efe8dc")
        g[3][3] = g[3][4] = g[4][2] = g[4][5] = hx("#2a2a2a")
        return g
    if kind == "glass":
        g = [[None] * TEX for _ in range(TEX)]
        for i in range(TEX):
            g[0][i] = g[7][i] = g[i][0] = g[i][7] = hx("#d8eef6")
        g[2][2] = g[3][3] = g[2][3] = hx("#ffffff")
        return g
    if kind == "leaves_fancy" or kind.startswith("leaves"):
        base = kind if kind in PAL else "leaves"
        g = _paint(base, seed, 14)
        r = random.Random(kind + str(seed))
        for _ in range(5):
            x, y = r.randrange(TEX), r.randrange(TEX)
            g[y][x] = monet_shade(g[y][x], 0.7)
        return g
    if kind in PAL:
        return _paint(kind, seed, 12)
    raise KeyError(kind)


@functools.lru_cache(maxsize=None)
def tex_uri(kind, seed=0, k=1.0, light=0.0):
    g = texture(kind, seed)
    px = []
    for row in g:
        for c in row:
            if c is None:
                px.append(None)
            else:
                c = monet_shade(c, k) if k < 1 else c
                px.append(monet_light(c, light) if light else c)
    return png_uri(px, TEX, TEX)


@functools.lru_cache(maxsize=None)
def avg(kind):
    g = texture(kind, 0)
    cs = [c for row in g for c in row if c is not None]
    return tuple(sum(c[i] for c in cs) / len(cs) for i in range(3))


# ------------------------------------------------------------------------------- flora sprites

SPRITES = {  # 8x8 cross-sprites shown in side view
    "poppy": ("........|..rr....|.rRRr...|..rrr...|...g....|...g.g..|..gg....|...g....",
              {"r": "#d83a2a", "R": "#2a1a1a", "g": "#4f8a3a"}),
    "dandelion": ("........|...yy...|..yYy...|...yy...|...g....|..gg....|...g.g..|...g....",
                  {"y": "#f6d040", "Y": "#fff2a0", "g": "#4f8a3a"}),
    "cornflower": ("........|..b.b...|...B....|..b.b...|...g....|...gg...|..g.....|...g....",
                   {"b": "#4a6ae0", "B": "#2a3aa8", "g": "#4f8a3a"}),
    "allium": ("..pPp...|.pPpPp..|..pPp...|...g....|...g....|...g....|..gg....|...g....",
               {"p": "#b070d8", "P": "#d8a8f0", "g": "#4f8a3a"}),
    "tulip_red": ("........|..r.r...|..rrr...|..rrr...|...g....|..gg.g..|...gg...|...g....",
                  {"r": "#e03a3a", "g": "#4f8a3a"}),
    "tulip_pink": ("........|..p.p...|..ppp...|..pPp...|...g....|..gg.g..|...gg...|...g....",
                   {"p": "#f0a0c0", "P": "#fce0ea", "g": "#4f8a3a"}),
    "tulip_orange": ("........|..o.o...|..ooo...|..ooo...|...g....|..gg.g..|...gg...|...g....",
                     {"o": "#f08a30", "g": "#4f8a3a"}),
    "grass_tuft": ("........|........|........|..g..g..|.g.gg.g.|..gGgg..|.gGggGg.|gggggggg",
                   {"g": "#6f9f45", "G": "#a8c870"}),
    "fern": ("........|........|...g....|.g.g.g..|..ggg...|.g.g.g..|..ggg...|...g....",
             {"g": "#4a7a48"}),
    "wheat": ("..y.y...|.yYyYy..|..y.y.y.|.y.yy...|..g.g.g.|.g.g.g..|..g.g...|.g.g.g..",
              {"y": "#e0b848", "Y": "#f4d878", "g": "#8aa040"}),
    "sugarcane": ("..g..g..|..G..g..|..g..G..|..g..g..|..G..g..|..g..g..|..g..G..|..g..g..",
                  {"g": "#7ac860", "G": "#a8e090"}),
    "lilypad": ("........|........|........|........|........|........|.gggggg.|gGggg.gg",
                {"g": "#3e7a2e", "G": "#6aa84a"}),
}


def sprite_grid(name):
    rows, pal = SPRITES[name]
    return [[hx(pal[ch]) if ch in pal else None for ch in row] for row in rows.split("|")]


# ----------------------------------------------------------------------------------- skies

def sky(w, h, top, mid, low, sun=None, sun_col="#ffd890", clouds=0.55, seed=1, haze="#e8dce8"):
    """An impressionist sky at texel resolution; returns a function (x, y) -> RGB with dabs baked in."""
    n = Noise(seed)
    r = random.Random(seed)
    T, M, L = hx(top), hx(mid), hx(low)
    grid = [[None] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            u = y / max(1, h - 1)
            c = mix(T, M, u * 2) if u < 0.5 else mix(M, L, (u - 0.5) * 2)
            if sun:
                d = math.hypot((x - sun[0]) / 1.6, y - sun[1])
                c = mix(c, hx(sun_col), 0.7 * math.exp(-(d / (h * 0.45)) ** 2))
            cl = n.fbm(x / 26 + y / 60, y / 7)
            if cl > clouds:
                c = mix(c, hx("#fbf6ec"), min(1.0, (cl - clouds) * 5) * 0.85)
            c = mix(c, hx(haze), max(0.0, n(x / 9, y / 3 + 50) - 0.7))
            j = r.gauss(0, 4)
            grid[y][x] = (c[0] + j, c[1] + j, c[2] + j)
    for _ in range(w * h // 2):
        x, y = r.randrange(w), r.randrange(h)
        c = grid[y][x]
        tint = (mix(c, hx("#ffffff"), 0.18) if r.random() < 0.5 else mix(c, LILAC, 0.12)) if r.random() < 0.7 \
            else mix(c, hx("#f4c8b8"), 0.2)
        for k in range(r.choice((2, 3, 4))):
            if x + k < w:
                grid[y][x + k] = tint
    return grid


# ------------------------------------------------------------------------- the 2D history world

COLS, ROWS, SURF = 180, 15, 10   # 30 columns per year, surface row 10 (top edge at y = 400 px)


def history_world():
    """Six Minecraft biomes, one per year, in side view; returns (png uri, list of vector props)."""
    W, Hh = COLS * TEX, ROWS * TEX
    img = [[None] * W for _ in range(Hh)]
    skies = [
        sky(240, 80, "#8fb4dc", "#c4d8ea", "#eef0e6", (190, 20), seed=11),                       # 2021 spring
        sky(240, 80, "#7ea6dc", "#b8d0ec", "#f4ecd8", (60, 14), seed=12, clouds=0.58),           # 2022 summer
        sky(240, 80, "#a8a4c8", "#d4c4d4", "#f0d8c0", (140, 30), "#f6c890", 0.6, 13),            # 2023 autumn
        sky(240, 80, "#c8c8d8", "#e6dcc4", "#f2ead2", (200, 40), "#fff0c0", 0.62, 14),           # 2024 winter
        sky(240, 80, "#a0bce0", "#d8c8e4", "#f8e0e8", (40, 24), "#ffe8d0", 0.56, 15, "#f4d8e4"),  # 2025 cherry
        sky(240, 80, "#7aa4dc", "#a8c8ec", "#e8eef0", (120, 16), seed=16, clouds=0.6),           # 2026 seaside
    ]
    n = Noise(99)
    rr = random.Random(2021)
    # sky + distant painted scenery (rows 0..9)
    for y in range(SURF * TEX):
        for x in range(W):
            k = int((x + (n(x / 9, y / 6) - 0.5) * 40) // 240)
            k = 0 if k < 0 else 5 if k > 5 else k
            c = skies[k][y][x % 240]
            far = y - (SURF * TEX - 14 - 9 * n(x / 40, k * 3.1))
            if far > 0:  # far hills, Monet haze
                hill = [hx("#8aa07a"), hx("#9aaa6a"), hx("#b09a8a"), hx("#b8bcd0"), hx("#c8a8c8"), hx("#5a80c0")][k]
                c = mix(c, hill, min(0.75, 0.3 + far * 0.06))
                if k == 5 and far > 3:
                    c = mix(hx("#4a72b8"), hx("#7a9ad0"), n(x / 3, y / 2))
            img[y][x] = c

    blocks = {}   # (col,row) -> kind
    sprites = {}  # (col,row) -> sprite name
    props = []

    def put(c, r, kind):
        blocks[(c, r)] = kind

    for col in range(COLS):
        k = col // 30
        u = col % 30
        surf = {0: "grass", 1: "grass", 2: "grass", 3: "snow", 4: "grass", 5: "sand" if u > 20 else "grass"}[k]
        put(col, SURF, surf)
        for r in range(SURF + 1, ROWS):
            d = r - SURF
            if d <= 2:
                kind = "sand" if surf == "sand" else "dirt"
            else:
                kind = "stone"
                roll = rr.random()
                if roll < 0.05:
                    kind = "ore_coal"
                elif roll < 0.075:
                    kind = "ore_iron"
                elif roll < 0.088 and d >= 4:
                    kind = rr.choice(["ore_diamond", "ore_lapis", "ore_gold", "ore_emerald", "ore_redstone"])
            put(col, r, kind)
    # per-biome features
    def tree(c, kind_log, kind_leaf, h=4, wide=2):
        top = SURF - h
        for r in range(top, SURF):
            put(c, r, kind_log)
        if wide == 2:
            spans = {top - 3: 1, top - 2: 1, top - 1: 2, top: 2}
        elif wide == 1:
            spans = {top - 3: 0, top - 2: 1, top - 1: 1, top: 1}
        else:  # spruce cone
            spans = {top - 4: 0, top - 3: 1, top - 2: 1, top - 1: 2, top: 1, top + 1: 2}
        for r, span in spans.items():
            for dc in range(-span, span + 1):
                if (c + dc, r) in blocks:
                    continue
                corner = abs(dc) == span and span > 0 and rr.random() < 0.35
                if not corner:
                    put(c + dc, r, kind_leaf)

    flowers = {0: ["poppy", "poppy", "poppy", "dandelion", "cornflower", "grass_tuft"],
               1: ["tulip_red", "tulip_pink", "tulip_orange", "allium", "tulip_red", "grass_tuft"],
               2: ["fern", "grass_tuft", "dandelion"], 3: [], 4: ["tulip_pink", "allium", "grass_tuft"],
               5: ["poppy", "tulip_red", "tulip_orange", "dandelion"]}
    # 2021 plains
    tree(6, "log_side", "leaves", 4)
    tree(23, "log_side", "leaves", 5)
    # 2022 tulips, a wheat farm and hay
    for c in range(30 + 14, 30 + 21):
        put(c, SURF, "farmland")
        sprites[(c, SURF - 1)] = "wheat"
    for c, r in ((30 + 23, SURF - 1), (30 + 24, SURF - 1), (30 + 23, SURF - 2)):
        put(c, r, "hay")
    tree(30 + 3, "log_side", "leaves", 4)
    # 2023 autumn birches and a river under a plank bridge
    for c in (60 + 2, 60 + 6, 60 + 25, 60 + 28):
        tree(c, "birch_side", "leaves_autumn", 5, 1)
    for c in range(60 + 11, 60 + 20):
        put(c, SURF, "planks")
        for r in (SURF + 1, SURF + 2):
            put(c, r, "water")
        if c in (60 + 11, 60 + 19):
            for r in (SURF - 1, SURF - 2):
                put(c, r, "log_side")
    # 2024 snowy taiga, fence, igloo
    for c in (90 + 3, 90 + 9, 90 + 26):
        tree(c, "log_side", "leaves_spruce", 5, 0)
    for c in range(90 + 13, 90 + 18):
        put(c, SURF - 1, "snow_block")
    for c in range(90 + 14, 90 + 17):
        put(c, SURF - 2, "snow_block")
    put(90 + 15, SURF - 3, "snow_block")
    props.append(("fence", 90 + 19, 90 + 24))
    # 2025 cherry grove + pond with a bridge
    for c in (120 + 2, 120 + 7, 120 + 25):
        tree(c, "log_side", "leaves_cherry", 5, 2)
    for c in range(120 + 12, 120 + 21):
        put(c, SURF, "planks")
        for r in (SURF + 1, SURF + 2):
            put(c, r, "water")
        sprites[(c, SURF + 1)] = None
    for c in range(120 + 12, 120 + 21):
        if c % 2 == 0:
            put(c, SURF - 1, "fence_post")
    # 2026 seaside village
    hx0 = 150 + 6
    for c in range(hx0, hx0 + 7):
        for r in range(SURF - 4, SURF):
            edge = c in (hx0, hx0 + 6)
            put(c, r, "log_side" if edge else ("glass" if r in (SURF - 3, SURF - 2) and c in (hx0 + 2, hx0 + 4) else "planks"))
        put(c, SURF - 5, "brick")
    for c in range(hx0 + 1, hx0 + 6):
        put(c, SURF - 6, "brick")
    for c in range(hx0 + 2, hx0 + 5):
        put(c, SURF - 7, "brick")
    for c in range(150 + 22, 150 + 30):
        put(c, SURF + 1, "water")
    tree(150 + 2, "log_side", "leaves", 4)
    # scatter flowers
    for col in range(COLS):
        k = col // 30
        if (col, SURF - 1) in blocks or (col, SURF - 1) in sprites:
            continue
        if blocks.get((col, SURF)) in ("grass",) and flowers[k] and rr.random() < 0.55:
            sprites[(col, SURF - 1)] = rr.choice(flowers[k])
    # rasterise blocks (with a few texture variants each) and sprites
    tex_cache = {}

    def face(kind, var):
        key = (kind, var)
        if key not in tex_cache:
            m = {"grass": "grass_side", "snow": "snow_side", "farmland": "path_side", "fence_post": "planks", "hay": "hay_side", "snow_block": "snow"}
            tex_cache[key] = texture(m.get(kind, kind if kind != "leaves" else "leaves"), var)
        return tex_cache[key]

    for (c, r), kind in blocks.items():
        if kind == "fence_post":
            g = face("planks", 0)
            for y in range(TEX):
                for x in (3, 4):
                    img[r * TEX + y][c * TEX + x] = g[y][x]
            for x in range(TEX):
                img[r * TEX + 2][c * TEX + x] = g[2][x]
            continue
        g = face(kind, (c * 7 + r * 13) % 3)
        above_air = (c, r - 1) not in blocks
        if kind == "grass" and not above_air:
            g = face("dirt", (c + r) % 3)
        for y in range(TEX):
            for x in range(TEX):
                if g[y][x] is not None:
                    img[r * TEX + y][c * TEX + x] = g[y][x]
    for (c, r), name in sprites.items():
        if not name:
            continue
        g = sprite_grid(name)
        for y in range(TEX):
            for x in range(TEX):
                if g[y][x] is not None:
                    img[r * TEX + y][c * TEX + x] = g[y][x]
    # water shimmer + soft Monet light on the surface row
    for (c, r), kind in blocks.items():
        if kind == "water":
            for x in range(TEX):
                if rr.random() < 0.3:
                    img[r * TEX + rr.randrange(TEX)][c * TEX + x] = hx("#c8d8f0")
    flat = [img[y][x] for y in range(Hh) for x in range(W)]
    return png_uri(flat, W, Hh), props
