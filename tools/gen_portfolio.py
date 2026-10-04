#!/usr/bin/env python3
"""Generate the animated LeviMC org-profile banner (profile/levimc-portfolio.svg).

GitHub renders README images through <img>: no JavaScript, no web fonts. Every 3D effect here
(voxel island, particle block, devices, repo constellation, leaf vortex) is projected through a
perspective camera in Python and baked into SMIL keyframes on one shared 48 s clock. Particle
keyframes are thinned with Douglas-Peucker, per channel, so the file stays reasonable.

    python3 tools/gen_portfolio.py            # writes profile/levimc-portfolio.svg
"""
import math
import os
import random
import re

W, H = 1200, 600
T = 48.0
FPS = 12
N = 400
rng = random.Random(20210127)  # LiteLDev's birthday

BG0, BG1, ZINC = "#09090b", "#18181b", "#27272a"
TXT, MUTED = "#f4f4f5", "#a1a1aa"
G200, G300, G400, G500, G600, G700, G800, G900, G950 = (
    "#bbf7d0", "#86efac", "#4ade80", "#22c55e", "#16a34a", "#15803d", "#166534", "#14532d", "#052e16")
LEAF_DARK, LEAF, CREAM = "#294c2d", "#7ba46d", "#f6f3ea"
GOLD = "#fde68a"
PCREAM = CREAM            # particle colour for the logo's veins (LEAF/CREAM above must stay = the artwork)
WHITE = "#ffffff"         # hottest point of glows and highlight gradients
TXT_STRONG = "#fafafa"
GOLD_HI = "#fffbeb"
NEB = (G700, 0.32, G900, 0.55, "#0e7490", 0.12)
GLASS = ("#ffffff", 0.07, 0.015)
VIGN = ("#000000", 0.6)
BG_STOPS = (BG0, "#0c0f0d", "#0a120c")
CODE = {"c": "#d4d4d8", "kw": "#c084fc", "ty": "#60a5fa", "cm": "#71717a"}

THEME = os.environ.get("THEME", "dark")
if THEME == "light":
    BG0, BG1, ZINC = "#fafafa", "#ffffff", "#e4e4e7"
    TXT, MUTED, TXT_STRONG = "#18181b", "#52525b", "#09090b"
    G200, G300, G400, G500, G600, G700 = "#166534", "#15803d", "#16a34a", "#16a34a", "#4ade80", "#86efac"
    GOLD, GOLD_HI, PCREAM, WHITE = "#d97706", "#92400e", "#65a30d", "#052e16"
    NEB = ("#86efac", 0.35, "#bbf7d0", 0.6, "#a5f3fc", 0.35)
    GLASS = ("#ffffff", 0.85, 0.55)
    VIGN = ("#14532d", 0.10)
    BG_STOPS = ("#fafafa", "#f3faf5", "#e9f7ee")
    CODE = {"c": "#3f3f46", "kw": "#9333ea", "ty": "#2563eb", "cm": "#a1a1aa"}

SANS = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


# ----------------------------------------------------------------------------------- helpers

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease(x):
    x = clamp(x)
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, u):
    return a + (b - a) * u


def f(v, nd=1):
    s = f"{v:.{nd}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def kt(t):
    if t <= 0:
        return "0"
    if t >= T:
        return "1"
    return f"{t / T:.4f}".rstrip("0")[1:]


def _pad(pairs):
    pairs = sorted(pairs, key=lambda p: p[0])
    if pairs[0][0] > 0:
        pairs.insert(0, (0, pairs[0][1]))
    if pairs[-1][0] < T:
        pairs.append((T, pairs[-1][1]))
    return pairs


def anim(attr, pairs, calc="linear"):
    pairs = _pad(pairs)
    return (f'<animate attributeName="{attr}" dur="{f(T)}s" repeatCount="indefinite" calcMode="{calc}" '
            f'keyTimes="{";".join(kt(t) for t, _ in pairs)}" values="{";".join(str(v) for _, v in pairs)}"/>')


def anim_tf(kind, pairs, additive=False):
    pairs = _pad(pairs)
    add = ' additive="sum"' if additive else ""
    return (f'<animateTransform attributeName="transform" type="{kind}" dur="{f(T)}s" repeatCount="indefinite" '
            f'keyTimes="{";".join(kt(t) for t, _ in pairs)}" values="{";".join(str(v) for _, v in pairs)}"{add}/>')


def window(t_in, t_out, fade=0.6, peak=1.0):
    return [(0, 0), (t_in, 0), (t_in + fade, peak), (t_out - fade, peak), (t_out, 0)]


def reveal(body, t_in, t_out, dy=14, fade=0.6, dx=0):
    op = anim("opacity", window(t_in, t_out, fade))
    mv = anim_tf("translate", [(0, f"{dx} {dy}"), (t_in, f"{dx} {dy}"), (t_in + fade * 1.4, "0 0"),
                               (t_out - fade, "0 0"), (t_out, f"{-dx} {-dy * 0.6:.0f}")])
    return f'<g opacity="0">{op}{mv}{body}</g>'


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, cls, anchor="start", raw=False):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return f'<text x="{f(x)}" y="{f(y)}" class="{cls}"{a}>{s if raw else esc(s)}</text>'


def frames(t0, t1, fps):
    n = max(2, int(round((t1 - t0) * fps)))
    return [t0 + (t1 - t0) * k / n for k in range(n + 1)]


def poly_d(pts, close=True):
    return "M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in pts) + ("Z" if close else "")


def mix(c1, c2, u):
    u = clamp(u)
    a = [int(c1[k:k + 2], 16) for k in (1, 3, 5)]
    b = [int(c2[k:k + 2], 16) for k in (1, 3, 5)]
    return "#" + "".join(f"{round(lerp(x, y, u)):02x}" for x, y in zip(a, b))


def shade(c, k):
    a = [int(c[j:j + 2], 16) for j in (1, 3, 5)]
    return "#" + "".join(f"{int(clamp(round(v * k), 0, 255)):02x}" for v in a)


# ------------------------------------------------------------------------------------ camera

def cam(p, yaw, pitch, cx, cy, dist=1000.0, focal=1000.0):
    x, y, z = p
    cyw, syw = math.cos(yaw), math.sin(yaw)
    x1 = x * cyw + z * syw
    z1 = -x * syw + z * cyw
    cp, sp = math.cos(pitch), math.sin(pitch)
    y2 = y * cp - z1 * sp
    z2 = y * sp + z1 * cp
    s = focal / (dist + z2)
    return cx + x1 * s, cy + y2 * s, s, z2


def rot_y(p, a):
    x, y, z = p
    c, s = math.cos(a), math.sin(a)
    return (x * c + z * s, y, -x * s + z * c)


def rot_x(p, a):
    x, y, z = p
    c, s = math.cos(a), math.sin(a)
    return (x, y * c - z * s, y * s + z * c)


def rot_z(p, a):
    x, y, z = p
    c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c, z)


def box_faces(x0, z0, sx, sz, h, yaw, pitch, C, y0=0.0, band=0.0):
    """Visible faces of an axis-aligned box standing on y=y0 (y down), seen from +x / -z / above.
    Returns top, right(+x), front(-z); with band > 0 each side is split into a top band and the rest."""
    def P(x, y, z):
        return cam((x, y, z), yaw, pitch, *C)[:2]
    x1, z1 = x0 + sx, z0 + sz
    yt = y0 - h
    top = [P(x0, yt, z0), P(x1, yt, z0), P(x1, yt, z1), P(x0, yt, z1)]
    if not band:
        return [top,
                [P(x1, yt, z0), P(x1, yt, z1), P(x1, y0, z1), P(x1, y0, z0)],
                [P(x0, yt, z0), P(x1, yt, z0), P(x1, y0, z0), P(x0, y0, z0)]]
    yb = yt + band
    return [top,
            [P(x1, yt, z0), P(x1, yt, z1), P(x1, yb, z1), P(x1, yb, z0)],
            [P(x1, yb, z0), P(x1, yb, z1), P(x1, y0, z1), P(x1, y0, z0)],
            [P(x0, yt, z0), P(x1, yt, z0), P(x1, yb, z0), P(x0, yb, z0)],
            [P(x0, yb, z0), P(x1, yb, z0), P(x1, y0, z0), P(x0, y0, z0)]]


def path_anim(ts, ds, t_in, t_out, fade=0.5, attrs=""):
    pairs = [(0, ds[0])] + list(zip(ts, ds)) + [(T, ds[-1])]
    da = (f'<animate attributeName="d" dur="{f(T)}s" repeatCount="indefinite" '
          f'keyTimes="{";".join(kt(t) for t, _ in pairs)}" values="{";".join(d for _, d in pairs)}"/>')
    return f'<path d="{ds[0]}" opacity="0" {attrs}>{da}{anim("opacity", window(t_in, t_out, fade))}</path>'


def floating(label_svg, pos_fn, t_in, t_out, fps=10, fade_in=0.8, fade_out=0.6, min_op=0.2):
    """A group that follows a 3D point: pos_fn(t) -> (x, y, s, z). Depth drives scale and opacity."""
    tr, sc, op = [], [], []
    for t in frames(t_in, t_out, fps):
        x, y, s, z = pos_fn(t)
        tr.append((t, f"{x:.0f} {y:.0f}"))
        sc.append((t, f(s, 2)))
        env = smooth((t - t_in) / fade_in) * smooth((t_out - t) / fade_out)
        op.append((t, f((min_op + (1 - min_op) * clamp(0.5 - z / 500)) * env, 2)))
    return (f'<g opacity="0">{anim("opacity", op)}{anim_tf("translate", tr)}{anim_tf("scale", sc, True)}'
            f'{label_svg}</g>')


# --------------------------------------------------------------------------- the sprout logo

LOGO_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "levimc-logo.svg")
NUM = r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def parse_path(d):
    """Flatten an SVG path (M/L/H/V/Q/C/A/Z, absolute or relative) into polylines."""
    toks = re.findall(r"[a-zA-Z]|" + NUM, d)
    subs, cur = [], []
    x = y = sx = sy = 0.0
    cmd = None
    i = 0
    counts = {"m": 2, "l": 2, "h": 1, "v": 1, "q": 4, "c": 6, "a": 7, "z": 0, "t": 2, "s": 4}
    while i < len(toks):
        if re.match(r"[a-zA-Z]", toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in "zZ":
                if cur:
                    subs.append(cur)
                cur = []
                x, y = sx, sy
                continue
        lc = cmd.lower()
        n = counts[lc]
        a = [float(v) for v in toks[i:i + n]]
        i += n
        rel = cmd.islower()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if lc == "m":
            if cur:
                subs.append(cur)
            x, y = a[0] + ox, a[1] + oy
            sx, sy = x, y
            cur = [(x, y)]
            cmd = "l" if rel else "L"
        elif lc == "l" or lc == "t":
            x, y = a[0] + ox, a[1] + oy
            cur.append((x, y))
        elif lc == "h":
            x = a[0] + (x if rel else 0)
            cur.append((x, y))
        elif lc == "v":
            y = a[0] + (y if rel else 0)
            cur.append((x, y))
        elif lc in "qc" or lc == "s":
            if lc == "q":
                c1 = (a[0] + ox, a[1] + oy)
                e = (a[2] + ox, a[3] + oy)
                pts = [(x, y), c1, e]
            elif lc == "c":
                pts = [(x, y), (a[0] + ox, a[1] + oy), (a[2] + ox, a[3] + oy), (a[4] + ox, a[5] + oy)]
            else:
                pts = [(x, y), (x, y), (a[0] + ox, a[1] + oy), (a[2] + ox, a[3] + oy)]
            for k in range(1, 7):
                u = k / 6
                if len(pts) == 3:
                    bx = (1 - u) ** 2 * pts[0][0] + 2 * u * (1 - u) * pts[1][0] + u * u * pts[2][0]
                    by = (1 - u) ** 2 * pts[0][1] + 2 * u * (1 - u) * pts[1][1] + u * u * pts[2][1]
                else:
                    c = [(1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3]
                    bx = sum(c[j] * pts[j][0] for j in range(4))
                    by = sum(c[j] * pts[j][1] for j in range(4))
                cur.append((bx, by))
            x, y = pts[-1]
        elif lc == "a":  # the logo's arcs are sub-pixel corner roundings: a straight line is enough
            x, y = a[5] + ox, a[6] + oy
            cur.append((x, y))
    if cur:
        subs.append(cur)
    return subs


def inside(poly, x, y):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def load_logo():
    src = open(LOGO_SRC, encoding="utf-8").read()
    fills = re.findall(r'<path[^>]*?\sd="([^"]+)"[^>]*?fill="(#[0-9a-fA-F]{6})"', src)
    shapes = [(parse_path(d), col, d) for d, col in fills]
    xs = [p[0] for s, _, _ in shapes for sub in s for p in sub]
    ys = [p[1] for s, _, _ in shapes for sub in s for p in sub]
    return shapes, (min(xs), min(ys), max(xs), max(ys))


LOGO_SHAPES, LOGO_BB = load_logo()
LOGO_CX = (LOGO_BB[0] + LOGO_BB[2]) / 2
LOGO_CY = (LOGO_BB[1] + LOGO_BB[3]) / 2
LOGO_SPAN = LOGO_BB[3] - LOGO_BB[1]


def logo_color_at(x, y):
    """Colour of the topmost filled shape at (x, y), or None."""
    col = None
    for subs, c, _ in LOGO_SHAPES:
        hit = False
        for sub in subs:
            if inside(sub, x, y):
                hit = not hit
        if hit:
            col = c
    return col


def logo_svg(cx, cy, height, extra=""):
    sc = height / LOGO_SPAN
    paths = "".join(f'<path d="{d}" fill="{c}"/>' for _, c, d in LOGO_SHAPES)
    return (f'<g transform="translate({cx - LOGO_CX * sc:.2f} {cy - LOGO_CY * sc:.2f}) scale({sc:.5f})"{extra}>'
            f'{paths}</g>')


def logo_points(n, height):
    sc = height / LOGO_SPAN
    cand = []
    x0, y0, x1, y1 = LOGO_BB
    while len(cand) < n * 12:
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        c = logo_color_at(x, y)
        if c:
            cand.append(((x - LOGO_CX) * sc, (y - LOGO_CY) * sc, c))
    pts = [cand.pop()]
    while len(pts) < n:  # Mitchell's best candidate -> even, blue-noise coverage
        best, bd = None, -1
        for _ in range(12):
            c = cand[rng.randrange(len(cand))]
            d = min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 for p in pts)
            if d > bd:
                best, bd = c, d
        pts.append(best)
    return pts


# ------------------------------------------------------------------------------- particles

class P:
    pass


LOGO_C = (600, 222)
LOGO_H = 250
LOGO_PTS = logo_points(N, LOGO_H)
rng.shuffle(LOGO_PTS)

parts = []
for i in range(N):
    p = P()
    p.i = i
    lx, ly, lc = LOGO_PTS[i]
    p.logo = (lx, ly)
    p.region = {LEAF_DARK: "rim", LEAF: "leaf", CREAM: "vein"}.get(lc, "leaf")
    p.square = rng.random() < 0.55
    if p.region == "vein":
        p.paint = PCREAM if p.square else "gC"
    elif p.region == "rim":
        p.paint = G500 if p.square else "gG"
    else:
        p.paint = G300 if p.square else "gL"
    p.gold = rng.random() < 0.06
    if p.gold:
        p.paint = GOLD if p.square else "gY"
    p.base = rng.uniform(0.75, 1.45) * (0.8 if p.square else 1.0)
    p.ph = rng.random()
    p.ph2 = rng.random()
    p.th = rng.uniform(0, 2 * math.pi)
    p.jit = (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))
    p.R = rng.uniform(70, 760)
    p.z0 = rng.uniform(0, 2400)
    p.role = rng.random()
    parts.append(p)


def F_tunnel(p, t):
    z = 50 + ((p.z0 - 950 * t) % 2400)
    s = 520 / z
    x = 600 + p.R * math.cos(p.th) * s
    y = 300 + p.R * math.sin(p.th) * s * 0.86
    a = smooth((2450 - z) / 500) * smooth((z - 55) / 140)
    return x, y, p.base * clamp(s * 2.6, 0.5, 6), a


def F_logo(p, t):
    lx, ly = p.logo
    yaw = -0.95 * (1 - ease((t - 2.4) / 2.6)) + 0.18 * math.sin((t - 3.6) * 0.8) * smooth((t - 4.4) / 1.5)
    pitch = 0.10 * math.sin((t - 3.0) * 0.6)
    x, y, s, z = cam((lx, ly, p.jit[2] * 14), yaw, pitch, *LOGO_C, dist=900, focal=900)
    shimmer = 0.8 + 0.2 * math.sin(2 * math.pi * (p.ph + t * 0.45))
    return x, y, p.base * 1.8 * s, shimmer


# --- 02 LeviLamina: a floating voxel island --------------------------------------------------
ISL_C = (330, 352)
ISL_PITCH = 0.5
GRID, CELL, BLOCK = 6, 42, 24


def isl_yaw(t):
    return 0.28 + 0.075 * (t - 7.4)


def isl_bob(t):
    return 6 * math.sin(1.1 * t)


def col_height(i, j):
    v = 2.3 * math.exp(-((i - 2.0) ** 2 + (j - 3.2) ** 2) / 5.0) + 0.45 * math.sin(i * 1.7 + j * 0.9) + 0.6
    return int(clamp(round(v), 1, 3))


def F_island(p, t):
    yaw = isl_yaw(t)
    bob = isl_bob(t)
    if p.role < 0.55:  # a disc of pixels orbiting the island
        ang = p.th + 0.5 * t
        rad = 215 + 45 * p.ph2
        w = (rad * math.cos(ang), -18 + p.jit[1] * 14 + bob, rad * math.sin(ang))
        x, y, s, z = cam(w, yaw, ISL_PITCH, *ISL_C)
        return x, y, p.base * 2.0 * s, 0.35 + 0.6 * clamp(0.5 - z / 500)
    # motes drifting up from the grass
    u = (p.ph + 0.32 * t) % 1.0
    gi, gj = int(p.ph2 * GRID) % GRID, int((p.jit[0] + 1) / 2 * GRID) % GRID
    x0 = (gi - GRID / 2 + 0.5) * CELL + p.jit[1] * 14
    z0 = (gj - GRID / 2 + 0.5) * CELL + p.jit[2] * 14
    top = -col_height(gi, gj) * BLOCK + bob
    w = (x0 + 10 * math.sin(6 * u + p.th), top - 8 - 170 * u, z0)
    x, y, s, z = cam(w, yaw, ISL_PITCH, *ISL_C)
    return x, y, p.base * 1.9 * s, smooth(u / 0.12) * (1 - u) * 0.95


# --- 03 Scripting: a block made of particles ----------------------------------------------------
CUBE_C = (330, 300)
CUBE_HALF = 112


def cube_world(v, t):
    v = rot_y(v, 0.55 * t)
    v = rot_x(v, 0.5)
    return rot_z(v, 0.12)


FACES = [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]
for k, p in enumerate(parts):
    if k < 384:
        ax, sgn = FACES[k // 64]
        a, b = (k % 64) // 8, k % 8
        u, v = -1 + (2 * a + 1) / 8, -1 + (2 * b + 1) / 8
        q = [0.0, 0.0, 0.0]
        q[ax] = sgn
        q[(ax + 1) % 3] = u
        q[(ax + 2) % 3] = v
        p.cube = tuple(c * CUBE_HALF for c in q)
    else:
        p.cube = None


def F_cube(p, t):
    if p.cube is None:
        ang = p.th + 1.0 * t
        w = rot_x((240 * math.cos(ang), 0, 240 * math.sin(ang)), 1.2)
        x, y, s, z = cam(w, 0, 0, *CUBE_C)
        return x, y, p.base * 2.0 * s, 0.7
    breathe = 1 + 0.06 * math.sin(2.2 * t + p.cube[1] * 0.02)
    w = cube_world(tuple(c * breathe for c in p.cube), t)
    x, y, s, z = cam(w, 0, 0, *CUBE_C)
    return x, y, p.base * 2.1 * s, 0.25 + 0.75 * clamp(0.5 - z / (2.4 * CUBE_HALF))


# --- 04 Launchers: a phone and a desktop -------------------------------------------------------
DEV_C = (318, 318)
DEV_PITCH = 0.16
PHONE = (-238, -118, -125, 125)      # x0, x1, y0(top), y1(bottom)
SCREEN = (-62, 248, -112, 82)        # monitor body
DEPTH = 9


def dev_yaw(t):
    return 0.3 + 0.16 * math.sin((t - 24.0) * 0.55)


def F_devices(p, t):
    yaw = dev_yaw(t)
    if p.role < 0.78:  # downloads raining into the screens
        if p.ph2 < 0.45:
            x0, x1, y0, y1 = PHONE
            m = 12
        else:
            x0, x1, y0, y1 = SCREEN
            m = 14
        tx = lerp(x0 + m, x1 - m, (p.jit[0] + 1) / 2)
        ty = lerp(y0 + m + 20, y1 - m, (p.jit[1] + 1) / 2)
        u = (p.ph + 0.55 * t) % 1.0
        w = (tx, ty - (1 - u) * 330, -DEPTH - 2 - (1 - u) * 90)
        x, y, s, z = cam(w, yaw, DEV_PITCH, *DEV_C)
        return x, y, p.base * 1.9 * s, smooth(u / 0.18) * smooth((1 - u) / 0.06)
    ang = p.th + 0.45 * t
    w = (5 + 330 * math.cos(ang), 150 + p.jit[1] * 6, 120 * math.sin(ang))
    x, y, s, z = cam(w, yaw, DEV_PITCH, *DEV_C)
    return x, y, p.base * 1.8 * s, 0.3 + 0.5 * clamp(0.5 - z / 300)


# --- 05 Ecosystem: a constellation of repos ---------------------------------------------------
NET_C = (318, 300)
REPOS = ["LegacyScriptEngine", "LeviLaunchroid", "LeviLauncher", "LeviOptimize", "LeviAntiCheat",
         "LeviStone", "MoreDimensions", "LeviSchematic", "CrashLogger", "PreLoader", "mod-template",
         "docker-server", "ScriptX", "LegacyMoney"]
NODES = []
for k in range(len(REPOS)):
    yy = 1 - 2 * (k + 0.5) / len(REPOS)
    rr = math.sqrt(1 - yy * yy)
    th = math.pi * (3 - 5 ** 0.5) * k
    NODES.append((215 * rr * math.cos(th), 150 * yy, 215 * rr * math.sin(th)))


def net_world(v, t):
    return rot_x(rot_y(v, 0.28 * t), 0.3)


def F_network(p, t):
    if p.role < 0.3:  # the core
        k = p.i
        yy = 1 - 2 * ((k * 0.618) % 1)
        rr = math.sqrt(max(0, 1 - yy * yy))
        th = p.th
        w = net_world((52 * rr * math.cos(th), 52 * yy, 52 * rr * math.sin(th)), t * 2.2)
        x, y, s, z = cam(w, 0, 0, *NET_C)
        return x, y, p.base * 2.0 * s, 0.5 + 0.5 * clamp(0.5 - z / 120)
    node = NODES[p.i % len(NODES)]
    u = (p.ph + 0.4 * t) % 1.0
    bend = math.sin(math.pi * u) * 18
    w = tuple(lerp(node[j], 0, u) for j in range(3))
    w = (w[0] + p.jit[0] * bend, w[1] + p.jit[1] * bend, w[2] + p.jit[2] * bend)
    x, y, s, z = cam(net_world(w, t), 0, 0, *NET_C)
    return x, y, p.base * 1.9 * s, smooth(u / 0.1) * smooth((1 - u) / 0.15) * (0.3 + 0.7 * clamp(0.5 - z / 450))


# --- 06 Community: a leaf vortex around the sprout ---------------------------------------------
VORT_C = (600, 238)


def F_vortex(p, t):
    if p.role < 0.25:  # ground ring
        ang = p.th - 0.35 * t
        rad = 250 + 30 * p.ph2
        w = (rad * math.cos(ang), 128 + p.jit[1] * 4, rad * math.sin(ang))
        x, y, s, z = cam(w, 0, 0.28, *VORT_C)
        return x, y, p.base * 1.8 * s, 0.25 + 0.55 * clamp(0.5 - z / 500)
    strand = p.i % 3
    u = (p.ph + 0.13 * t) % 1.0
    rad = 105 + 120 * u + p.jit[0] * 10
    ang = p.th * 0.15 + strand * 2.094 + 1.1 * t + 5.0 * u
    w = (rad * math.cos(ang), 125 - 290 * u, rad * math.sin(ang))
    x, y, s, z = cam(w, 0, 0.28, *VORT_C)
    return x, y, p.base * 2.0 * s, smooth(u / 0.12) * smooth((1 - u) / 0.2) * (0.3 + 0.7 * clamp(0.5 - z / 400))


def F_tunnel_end(p, t):
    return F_tunnel(p, t - T)


SEGS = [
    (F_tunnel, 0.0, 2.1),
    (F_logo, 3.5, 7.2),
    (F_island, 8.4, 15.7),
    (F_cube, 16.7, 23.5),
    (F_devices, 24.5, 31.3),
    (F_network, 32.3, 39.1),
    (F_vortex, 40.1, 46.2),
    (F_tunnel_end, 47.4, T),
]

for p in parts:
    p.trans = []
    for k in range(len(SEGS) - 1):
        g0, g1 = SEGS[k][2], SEGS[k + 1][1]
        dur = (g1 - g0) * rng.uniform(0.55, 0.75)
        st = g0 + rng.random() * (g1 - g0 - dur)
        p.trans.append((st, st + dur, rng.uniform(-1, 1), rng.uniform(0.6, 1.4)))


def particle_state(p, t):
    for k, (fn, a, b) in enumerate(SEGS):
        if a <= t <= b:
            return fn(p, t)
        if k + 1 < len(SEGS) and b < t < SEGS[k + 1][1]:
            st, en, swirl, boost = p.trans[k]
            A, B = fn(p, t), SEGS[k + 1][0](p, t)
            u = ease((t - st) / (en - st))
            dx, dy = B[0] - A[0], B[1] - A[1]
            dist = math.hypot(dx, dy) + 1e-6
            bump = math.sin(math.pi * u)
            x = lerp(A[0], B[0], u) - dy / dist * swirl * 0.38 * dist * bump
            y = lerp(A[1], B[1], u) + dx / dist * swirl * 0.38 * dist * bump
            r = lerp(A[2], B[2], u) * (1 + 0.7 * boost * bump)
            al = max(lerp(A[3], B[3], u), 0.75 * bump * max(A[3], B[3], 0.6))
            return x, y, r, al
    return SEGS[-1][0](p, t)


def simplify(ts, chans, tol, vis):
    n = len(ts)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        worst, wk = 1.0, -1
        span = ts[j] - ts[i]
        for k in range(i + 1, j):
            if not (vis[k] or vis[i] or vis[j]):
                continue
            u = (ts[k] - ts[i]) / span
            e = max(abs(lerp(c[i], c[j], u) - c[k]) for c in chans) / tol
            if e > worst:
                worst, wk = e, k
        if wk >= 0:
            keep[wk] = True
            stack += [(i, wk), (wk, j)]
    return [k for k in range(n) if keep[k]]


def keyed(attr, idx, ts, fmtv, kind=None, additive=False):
    keys = ";".join(kt(ts[k]) for k in idx)
    vals = ";".join(fmtv(k) for k in idx)
    add = ' additive="sum"' if additive else ""
    if kind:
        return (f'<animateTransform attributeName="transform" type="{kind}" dur="{f(T)}s" repeatCount="indefinite" '
                f'keyTimes="{keys}" values="{vals}"{add}/>')
    return f'<animate attributeName="{attr}" dur="{f(T)}s" repeatCount="indefinite" keyTimes="{keys}" values="{vals}"/>'


def particles_svg():
    out = []
    ts = [s / FPS for s in range(int(T * FPS) + 1)]
    for p in parts:
        X, Y, R, A = [], [], [], []
        for t in ts:
            x, y, r, a = particle_state(p, t)
            X.append(clamp(x, -60, W + 60))
            Y.append(clamp(y, -60, H + 60))
            R.append(r * (0.62 if p.square else 1.0))  # half-side of a pixel vs radius of a glow
            A.append(clamp(a))
        vis = [a > 0.03 and -20 < x < W + 20 and -20 < y < H + 20 for a, x, y in zip(A, X, Y)]
        i_pos = simplify(ts, [X, Y], 1.1, vis)
        i_r = simplify(ts, [R], 0.25, vis)
        i_a = simplify(ts, [A], 0.07, [True] * len(ts))
        if p.square:
            shape = f'<rect x="-1" y="-1" width="2" height="2" fill="{p.paint}"'
        else:
            shape = f'<circle r="1" fill="url(#{p.paint})"'
        out.append(
            f'{shape} opacity="{f(A[0], 2)}" transform="translate({X[0]:.0f} {Y[0]:.0f}) scale({f(R[0])})">'
            + keyed(None, i_pos, ts, lambda k: f"{X[k]:.0f} {Y[k]:.0f}", "translate")
            + keyed(None, i_r, ts, lambda k: f(R[k]), "scale", additive=True)
            + keyed("opacity", i_a, ts, lambda k: f(A[k], 2))
            + ("</rect>" if p.square else "</circle>"))
    return "\n".join(out)


# ------------------------------------------------------------------------------- text widgets

_IDS = [0]


def uid(prefix):
    _IDS[0] += 1
    return f"{prefix}{_IDS[0]}"


def typed(x, y, s, t_in, t_out, cls, width, caret_h=19):
    cid = uid("type")
    dur = 0.045 * len(s)
    clip = (f'<clipPath id="{cid}"><rect x="{x - 4}" y="{y - 22}" height="32" width="0">'
            + anim("width", [(0, 0), (t_in, 0), (t_in + dur, f(width + 8)), (T, f(width + 8))]) + "</rect></clipPath>")
    blinks = [(t_in + dur + 0.25 * k, (k + 1) % 2) for k in range(int((t_out - t_in - dur) / 0.25))]
    caret = (f'<rect x="{x}" y="{y - caret_h + 4}" width="9" height="{caret_h}" fill="{G400}">'
             + anim_tf("translate", [(0, "0 0"), (t_in, "0 0"), (t_in + dur, f"{width + 4:.0f} 0"), (T, f"{width + 4:.0f} 0")])
             + anim("opacity", [(0, 0), (t_in, 0)] + blinks + [(t_out, 0)], calc="discrete") + "</rect>")
    return (f'{clip}<g opacity="0">{anim("opacity", window(t_in, t_out, 0.3))}'
            f'<g clip-path="url(#{cid})">{text(x, y, s, cls)}</g>{caret}</g>')


def counter(x, y, finals, t0, cls, anchor="start", dur=1.1):
    n = len(finals)
    dt = dur / n
    out = []
    for k, s in enumerate(finals):
        a, b = t0 + k * dt, t0 + (k + 1) * dt
        pairs = [(0, 1), (b, 0)] if k == 0 else [(0, 0), (a, 1)] if k == n - 1 else [(0, 0), (a, 1), (b, 0)]
        out.append(f'<g opacity="{1 if k == 0 else 0}">{anim("opacity", pairs, calc="discrete")}{text(x, y, s, cls, anchor)}</g>')
    return "".join(out)


def roll(final, steps=9, fmt="{:.0f}", start=0.0, prefix="", suffix=""):
    vals = [start + (final - start) * ease(k / (steps - 1)) for k in range(steps)]
    return [prefix + fmt.format(v) + suffix for v in vals[:-1]] + [prefix + fmt.format(final) + suffix]


def card(x, y, w, h, nums, cap1, cap2, t_in, t_out, cap_x=None, big=True, accent=G400, num_cls=None):
    body = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="url(#glass)" stroke="{accent}" stroke-opacity="0.25"/>'
            f'<rect x="{x}" y="{y + 16}" width="3" height="{h - 32}" rx="1.5" fill="{accent}"/>')
    if big:
        body += counter(x + 24, y + h / 2 + 16, nums, t_in + 0.4, num_cls or "num")
        body += text(cap_x, y + h / 2 - 4, cap1, "lab") + text(cap_x, y + h / 2 + 18, cap2, "labs")
    else:
        body += counter(x + 22, y + 52, nums, t_in + 0.4, num_cls or "nums")
        body += text(x + 22, y + 78, cap1, "lab2") + text(x + 22, y + 97, cap2, "labs")
    return reveal(body, t_in, t_out, dx=30, dy=0)


def heading(tag, title, sub, t_in, t_out, cls="h2"):
    return reveal(text(640, 82, tag, "tag") + text(638, 128, title, cls) + text(640, 154, sub, "sub"), t_in + 0.2, t_out)


# ----------------------------------------------------------------------------------- scenes

def scene_intro():
    out = []
    t_out = 7.5
    lx, ly = LOGO_C
    out.append(f'<circle cx="{lx}" cy="{ly}" r="10" fill="none" stroke="{G300}" stroke-width="2" opacity="0">'
               f'{anim("r", [(0, 10), (4.3, 10), (5.8, 560), (T, 560)])}'
               f'{anim("opacity", [(0, 0), (4.3, 0), (4.35, 0.8), (5.8, 0), (T, 0)])}'
               f'{anim("stroke-width", [(0, 6), (4.3, 6), (5.8, 0.5), (T, 0.5)])}</circle>')
    out.append(f'<ellipse cx="{lx}" cy="{ly}" rx="560" ry="2.4" fill="url(#streak)" opacity="0">'
               f'{anim("opacity", [(0, 0), (4.25, 0), (4.45, 0.95), (5.6, 0), (T, 0)])}'
               f'{anim("ry", [(0, 2.4), (4.25, 2.4), (4.45, 5), (5.6, 1), (T, 1)])}</ellipse>')
    # the real logo resolves under the particles
    out.append(f'<g opacity="0">{anim("opacity", [(0, 0), (4.9, 0), (6.0, 0.92), (t_out - 0.4, 0.92), (t_out, 0)])}'
               f'{logo_svg(lx, ly, LOGO_H)}</g>')
    out.append(reveal(text(600, 420, "LeviMC", "hero", "middle"), 4.6, t_out, dy=18))
    tl = "Mod Bedrock your way."
    out.append(typed(600 - 0.5 * 12.6 * len(tl), 462, tl, 5.1, t_out, "tagline", 12.6 * len(tl)))
    out.append(reveal(text(600, 504, "OPEN SOURCE · BEDROCK MODDING · FORMERLY LITELDEV · SINCE 2021", "kicker", "middle"),
                      5.7, t_out, dy=8))
    return "\n".join(out)


def scene_island():
    t_in, t_out = 7.6, 16.0
    out = []
    ts = frames(t_in - 0.2, t_out + 0.2, 5)
    cells = sorted(((i, j) for i in range(GRID) for j in range(GRID)), key=lambda c: c[0] - c[1])
    for (i, j) in cells:
        h = col_height(i, j)
        x0 = (i - GRID / 2) * CELL
        z0 = (j - GRID / 2) * CELL
        faces = [[] for _ in range(5)]
        for t in ts:
            fs = box_faces(x0, z0, CELL, CELL, h * BLOCK, isl_yaw(t), ISL_PITCH, ISL_C, y0=isl_bob(t), band=7)
            for k in range(5):
                faces[k].append(poly_d(fs[k]))
        var = (math.sin(i * 2.1 + j * 1.3) + 1) / 2
        grass = mix("#4f9a3a", "#6cc04a", var * 0.6 + h * 0.13)
        dirt = mix("#7a5233", "#8b6040", var)
        cols = [grass, shade(grass, 0.72), shade(dirt, 0.8), shade(grass, 0.55), shade(dirt, 0.6)]
        delay = 0.035 * (i + (GRID - j))
        for k in range(5):
            out.append(path_anim(ts, faces[k], t_in + 0.2 + delay, t_out - 0.1 - delay * 0.4,
                                 attrs=f'fill="{cols[k]}" stroke="{G950}" stroke-opacity="0.35" stroke-width="0.8"'))
    # API modules orbiting the island
    mods = ["Event", "Command", "Form", "Hook", "Memory", "Network", "Reflection", "Coroutine",
            "Config", "I18N", "Service", "Mod"]
    for n, name in enumerate(mods):
        ang0 = 2 * math.pi * n / len(mods)

        def pos(t, ang0=ang0):
            ang = ang0 + 0.3 * (t - t_in)
            return cam((262 * math.cos(ang), -12 + isl_bob(t), 262 * math.sin(ang)), isl_yaw(t), ISL_PITCH, *ISL_C)
        out.append(floating(f'<text class="mod" text-anchor="middle" y="4">{name}</text>', pos, t_in + 0.6, t_out - 0.2))
    out.append(heading("02 — LEVILAMINA", "LeviLamina", "Lightweight, modular, versatile — the mod loader for Bedrock.",
                       t_in, t_out, cls="h1"))
    cw = 166
    out.append(card(640, 184, cw, 112, roll(1.7, 9, "{:.1f}", suffix="k"), "GitHub stars", "on LeviLamina",
                    t_in + 0.6, t_out, big=False))
    out.append(card(640 + cw + 11, 184, cw, 112, roll(3108, 9, "{:,.0f}"), "commits", "and counting",
                    t_in + 0.85, t_out, big=False))
    out.append(card(640 + 2 * (cw + 11), 184, cw, 112, roll(133, 9), "releases", "latest v26.51",
                    t_in + 1.1, t_out, big=False))
    # history
    hist = [("2021.01", "LiteLoaderBDS"), ("2021.12", "v2.0"), ("2023.12", "LeviLamina"), ("2026", "v26.51")]
    body = f'<line x1="648" x2="1150" y1="372" y2="372" stroke="{G400}" stroke-opacity="0.35" stroke-dasharray="3 5"/>'
    out.append(reveal(body + text(640, 336, "THE STORY SO FAR", "tagb"), t_in + 1.4, t_out, dy=0))
    for k, (d, lab) in enumerate(hist):
        x = 660 + k * 160
        on = k == 2
        b = (f'<circle cx="{x}" cy="372" r="{6 if on else 4}" fill="{G400 if on else BG0}" stroke="{G400}" stroke-width="2"/>'
             + text(x - 6, 400, d, "date") + text(x - 6, 362, lab, "labon" if on else "labs"))
        out.append(reveal(b, t_in + 1.7 + 0.25 * k, t_out, dy=8))
    cmd = "> lip install github.com/LiteLDev/LeviLamina"
    out.append(typed(640, 470, cmd, t_in + 2.9, t_out, "cmd", 10.85 * len(cmd)))
    return "\n".join(out)


SNIPPETS = [
    ("main.cpp", [
        [("auto", "kw"), ("& bus = ", "c"), ("ll::event::EventBus", "ty"), ("::getInstance();", "c")],
        [("bus.", "c"), ("emplaceListener", "fn"), ("<", "c"), ("PlayerJoinEvent", "ty"), (">(", "c")],
        [("    [](", "c"), ("PlayerJoinEvent", "ty"), ("& ev) {", "c")],
        [("        ev.self().", "c"), ("sendMessage", "fn"), ("(", "c"), ('"Welcome!"', "st"), (");", "c")],
        [("    });", "c")]]),
    ("main.js", [
        [("// LegacyScriptEngine · JavaScript", "cm")],
        [("mc.", "c"), ("listen", "fn"), ("(", "c"), ('"onJoin"', "st"), (", (pl) => {", "c")],
        [("    pl.", "c"), ("tell", "fn"), ("(", "c"), ('"Welcome!"', "st"), (");", "c")],
        [("});", "c")]]),
    ("main.lua", [
        [("-- LegacyScriptEngine · Lua", "cm")],
        [("mc.", "c"), ("listen", "fn"), ("(", "c"), ('"onJoin"', "st"), (", ", "c"), ("function", "kw"), ("(pl)", "c")],
        [("    pl:", "c"), ("tell", "fn"), ("(", "c"), ('"Welcome!"', "st"), (")", "c")],
        [("end", "kw"), (")", "c")]]),
    ("main.py", [
        [("# LegacyScriptEngine · Python", "cm")],
        [("def", "kw"), (" ", "c"), ("on_join", "fn"), ("(pl):", "c")],
        [("    pl.", "c"), ("tell", "fn"), ("(", "c"), ('"Welcome!"', "st"), (")", "c")],
        [("mc.", "c"), ("listen", "fn"), ("(", "c"), ('"onJoin"', "st"), (", on_join)", "c")]]),
]


def scene_cube():
    t_in, t_out = 16.0, 23.9
    out = []
    ts = frames(t_in - 0.2, t_out + 0.2, 10)
    corners = [(sx * CUBE_HALF, sy * CUBE_HALF, sz * CUBE_HALF) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    edges = [(a, b) for a in range(8) for b in range(a + 1, 8)
             if sum(1 for k in range(3) if corners[a][k] != corners[b][k]) == 1]
    for a, b in edges:
        ds, ops = [], []
        for t in ts:
            pa = cam(cube_world(corners[a], t), 0, 0, *CUBE_C)
            pb = cam(cube_world(corners[b], t), 0, 0, *CUBE_C)
            ds.append(f"M{pa[0]:.0f} {pa[1]:.0f}L{pb[0]:.0f} {pb[1]:.0f}")
            ops.append(0.15 + 0.6 * clamp(0.5 - (pa[3] + pb[3]) / (4 * CUBE_HALF)))
        op_pairs = [(0, 0), (t_in + 0.4, 0)] + [(t, f(o, 2)) for t, o in zip(ts, ops) if t_in + 1.0 <= t <= t_out - 0.8] + [(t_out - 0.2, 0)]
        keys = [(0, ds[0])] + list(zip(ts, ds)) + [(T, ds[-1])]
        out.append(f'<path d="{ds[0]}" stroke="{G300}" stroke-width="1.4" fill="none" opacity="0">'
                   f'<animate attributeName="d" dur="{f(T)}s" repeatCount="indefinite" '
                   f'keyTimes="{";".join(kt(t) for t, _ in keys)}" values="{";".join(d for _, d in keys)}"/>'
                   f'{anim("opacity", op_pairs)}</path>')
    langs = ["C++", "JavaScript", "Lua", "Python", "Node.js"]
    for n, lab in enumerate(langs):
        ang0 = 2 * math.pi * n / len(langs)
        incl = 0.35 + 0.5 * (n % 2)

        def pos(t, ang0=ang0, incl=incl):
            ang = ang0 + 0.35 * (t - t_in)
            return cam(rot_x((232 * math.cos(ang), 0, 232 * math.sin(ang)), incl), 0, 0, *CUBE_C)
        out.append(floating(f'<text class="lang" text-anchor="middle" y="6">{esc(lab)}</text>', pos, t_in + 0.6, t_out - 0.2))
    out.append(heading("03 — LEGACYSCRIPTENGINE", "Build mods your way.",
                       "Native C++ performance, or the flexibility of scripts — same capabilities.", t_in, t_out))
    # code card with tabs cycling through languages
    cx, cy, cw, ch = 640, 182, 520, 196
    body = (f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="12" fill="{BG1}" fill-opacity="0.85" stroke="{G400}" stroke-opacity="0.25"/>'
            f'<line x1="{cx}" x2="{cx + cw}" y1="{cy + 40}" y2="{cy + 40}" stroke="{ZINC}"/>')
    for k, c in enumerate(["#ef4444", "#eab308", G500]):
        body += f'<circle cx="{cx + 20 + 16 * k}" cy="{cy + 20}" r="5" fill="{c}" fill-opacity="0.8"/>'
    span = (t_out - t_in - 1.6) / len(SNIPPETS)
    t0 = t_in + 1.0
    tab_x = [cx + 82 + 100 * k for k in range(len(SNIPPETS))]
    hl = [(0, f"{tab_x[0] - 8} 0")]
    for k in range(len(SNIPPETS)):
        a = t0 + k * span
        hl += [(a, f"{tab_x[k] - 8} 0"), (a + span - 0.25, f"{tab_x[k] - 8} 0")]
    body += (f'<rect x="0" y="{cy + 8}" width="92" height="24" rx="6" fill="{G400}" fill-opacity="0.14" stroke="{G400}" stroke-opacity="0.5">'
             f'{anim_tf("translate", hl)}</rect>')
    for k, (name, _) in enumerate(SNIPPETS):
        body += text(tab_x[k] + 38, cy + 25, name, "tab", "middle")
    for k, (_, lines) in enumerate(SNIPPETS):
        a = t0 + k * span
        b = a + span
        op = [(0, 1 if k == 0 else 0)]
        if k:
            op += [(a - 0.01, 0), (a + 0.25, 1)]
        op += [(b - 0.25, 1), (b, 0 if k < len(SNIPPETS) - 1 else 1)]
        rows = ""
        for r, segs in enumerate(lines):
            tsp = "".join(f'<tspan class="k-{c}">{esc(s)}</tspan>' for s, c in segs)
            rows += f'<text x="{cx + 22}" y="{cy + 72 + 25 * r}" class="code" xml:space="preserve">{tsp}</text>'
        body += f'<g opacity="{1 if k == 0 else 0}">{anim("opacity", op)}{rows}</g>'
    out.append(reveal(body, t_in + 0.6, t_out, dx=30, dy=0))
    cw2 = 166
    out.append(card(640, 392, cw2, 108, roll(115, 8), "GitHub stars", "LegacyScriptEngine", t_in + 1.2, t_out, big=False))
    out.append(card(640 + cw2 + 11, 392, cw2, 108, roll(51, 8, suffix="k+"), "downloads", "JS · Lua · Python", t_in + 1.4, t_out, big=False))
    out.append(card(640 + 2 * (cw2 + 11), 392, cw2, 108, ["0", "1", "2", "3"], "more runtimes", "LeviStone · ScriptX",
                    t_in + 1.6, t_out, big=False))
    return "\n".join(out)


def scene_devices():
    t_in, t_out = 23.9, 31.7
    out = []
    ts = frames(t_in - 0.2, t_out + 0.2, 6)

    def box(x0, x1, y0, y1, z0, z1, colors, stroke=G400, so=0.4):
        faces = [[], [], []]
        for t in ts:
            fs = box_faces(x0, z0, x1 - x0, z1 - z0, y1 - y0, dev_yaw(t), DEV_PITCH, DEV_C, y0=y1)
            for k in range(3):
                faces[k].append(poly_d(fs[k]))
        for k in (1, 0, 2):
            out.append(path_anim(ts, faces[k], t_in + 0.2, t_out - 0.1,
                                 attrs=f'fill="{colors[k]}" stroke="{stroke}" stroke-opacity="{so}" stroke-width="1"'))

    def quad(x0, x1, y0, y1, z, attrs):
        ds = []
        for t in ts:
            pts = [cam((x, y, z), dev_yaw(t), DEV_PITCH, *DEV_C)[:2] for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
            ds.append(poly_d(pts))
        out.append(path_anim(ts, ds, t_in + 0.5, t_out - 0.1, attrs=attrs))

    body = ["#3f3f46", "#27272a", "#1f1f23"]
    # desktop: stand, base, body
    box(70, 110, 82, 132, -6, 6, body, so=0.25)
    box(10, 170, 132, 140, -40, 40, body, so=0.3)
    x0, x1, y0, y1 = SCREEN
    box(x0, x1, y0, y1, -DEPTH, DEPTH, body)
    m = 9
    quad(x0 + m, x1 - m, y0 + m, y1 - m, -DEPTH - 0.5, f'fill="url(#screen)" stroke="{G400}" stroke-opacity="0.35"')
    quad(x0 + m, x1 - m, y0 + m, y0 + m + 18, -DEPTH - 1, f'fill="{G400}" fill-opacity="0.18"')
    quad(x0 + m, x0 + m + 64, y0 + m + 18, y1 - m, -DEPTH - 1, f'fill="#ffffff" fill-opacity="0.04"')
    for r in range(3):
        quad(x0 + m + 80, x1 - m - 20 - 40 * r, y0 + 45 + 22 * r, y0 + 55 + 22 * r, -DEPTH - 1, f'fill="#ffffff" fill-opacity="0.12"')
    quad(x1 - m - 120, x1 - m - 16, y1 - m - 40, y1 - m - 12, -DEPTH - 1.5, f'fill="{G500}" stroke="{G300}" stroke-opacity="0.8"')
    # phone
    x0, x1, y0, y1 = PHONE
    box(x0, x1, y0, y1, -DEPTH, DEPTH - 2, body)
    m = 8
    quad(x0 + m, x1 - m, y0 + 22, y1 - 22, -DEPTH - 0.5, f'fill="url(#screen)" stroke="{G400}" stroke-opacity="0.35"')
    quad(x0 + 44, x1 - 44, y0 + 9, y0 + 14, -DEPTH - 0.5, f'fill="#000000" fill-opacity="0.6"')
    for r in range(4):
        quad(x0 + m + 10, x1 - m - 10 - 18 * (r % 2), y0 + 44 + 26 * r, y0 + 58 + 26 * r, -DEPTH - 1, f'fill="#ffffff" fill-opacity="0.11"')
    quad(x0 + m + 14, x1 - m - 14, y1 - 62, y1 - 36, -DEPTH - 1.5, f'fill="{G500}" stroke="{G300}" stroke-opacity="0.8"')
    # labels under devices
    yaw_mid = 0.3
    px = cam(((PHONE[0] + PHONE[1]) / 2, PHONE[3] + 30, -DEPTH), yaw_mid, DEV_PITCH, *DEV_C)
    dx = cam(((SCREEN[0] + SCREEN[1]) / 2, 172, -40), yaw_mid, DEV_PITCH, *DEV_C)
    out.append(reveal(text(px[0], px[1] + 6, "LeviLaunchroid", "devl", "middle") + text(px[0], px[1] + 24, "Android", "labs", "middle"),
                      t_in + 0.9, t_out, dy=8))
    out.append(reveal(text(dx[0], dx[1] + 6, "LeviLauncher", "devl", "middle") + text(dx[0], dx[1] + 24, "Windows · GDK", "labs", "middle"),
                      t_in + 1.1, t_out, dy=8))
    out.append(heading("04 — LAUNCHERS", "Play Bedrock anywhere.", "LeviLaunchroid for Android · LeviLauncher for Windows (GDK).", t_in, t_out))
    out.append(card(640, 186, 520, 92, roll(753, 9, suffix="k+"), "LeviLaunchroid · Android", "★ 610 · release downloads",
                    t_in + 0.6, t_out, cap_x=850))
    out.append(card(640, 292, 520, 92, roll(212, 9, suffix="k+"), "LeviLauncher · Windows GDK", "★ 413 · shipped Nov 2025",
                    t_in + 0.9, t_out, cap_x=850))
    out.append(card(640, 398, 520, 92, roll(1.08, 9, "{:.2f}", suffix="M"), "release downloads across LeviMC",
                    "launchers · LeviLamina · LegacyScriptEngine", t_in + 1.2, t_out, cap_x=850, accent=GOLD, num_cls="numg"))
    return "\n".join(out)


def scene_network():
    t_in, t_out = 31.7, 39.5
    out = []
    ts = frames(t_in - 0.2, t_out + 0.2, 8)
    for k, node in enumerate(NODES):
        ds, ops = [], []
        for t in ts:
            c = cam(net_world((0, 0, 0), t), 0, 0, *NET_C)
            q = cam(net_world(node, t), 0, 0, *NET_C)
            ds.append(f"M{c[0]:.0f} {c[1]:.0f}L{q[0]:.0f} {q[1]:.0f}")
            ops.append(0.08 + 0.32 * clamp(0.5 - q[3] / 400))
        op_pairs = [(0, 0), (t_in + 0.6, 0)] + [(t, f(o, 2)) for t, o in zip(ts, ops) if t_in + 1.2 <= t <= t_out - 0.8] + [(t_out - 0.2, 0)]
        keys = [(0, ds[0])] + list(zip(ts, ds)) + [(T, ds[-1])]
        out.append(f'<path d="{ds[0]}" stroke="{G400}" stroke-width="1" fill="none" opacity="0">'
                   f'<animate attributeName="d" dur="{f(T)}s" repeatCount="indefinite" '
                   f'keyTimes="{";".join(kt(t) for t, _ in keys)}" values="{";".join(d for _, d in keys)}"/>'
                   f'{anim("opacity", op_pairs)}</path>')
    out.append(f'<circle cx="{NET_C[0]}" cy="{NET_C[1]}" r="95" fill="url(#core)" opacity="0">{anim("opacity", window(t_in + 0.5, t_out, 0.8))}</circle>')
    for k, (node, name) in enumerate(zip(NODES, REPOS)):
        def pos(t, node=node):
            return cam(net_world(node, t), 0, 0, *NET_C)
        star = k < 3
        lab = (f'<circle r="{5 if star else 3.5}" fill="{GOLD if star else G400}"/>'
               f'<text class="{"node" if star else "nodes"}" text-anchor="middle" y="-10">{esc(name)}</text>')
        out.append(floating(lab, pos, t_in + 0.8 + 0.05 * k, t_out - 0.2, min_op=0.25))
    out.append(reveal(text(NET_C[0], NET_C[1] + 5, "LeviLamina", "core", "middle"), t_in + 1.0, t_out, dy=0))
    out.append(heading("05 — ECOSYSTEM", "The complete toolkit.", "Everything around the loader — open source, LGPL-3.0.", t_in, t_out))
    cw, ch = 252, 112
    out.append(card(640, 186, cw, ch, roll(3.5, 9, "{:.1f}", suffix="k+"), "stars across LeviMC", "and growing every week",
                    t_in + 0.6, t_out, big=False, accent=GOLD, num_cls="numsg"))
    out.append(card(908, 186, cw, ch, roll(72, 9), "public repositories", "loader · engines · tools", t_in + 0.85, t_out, big=False))
    out.append(card(640, 312, cw, ch, roll(33, 9), "LeviLamina contributors", "by the community", t_in + 1.1, t_out, big=False))
    out.append(card(908, 312, cw, ch, roll(5, 6, suffix="+ yrs"), "since Jan 27, 2021", "LiteLoaderBDS → LeviLamina", t_in + 1.35, t_out, big=False))
    out.append(reveal(text(640, 466, "Docker images · mod template · PreLoader · CrashLogger", "lab")
                      + text(640, 490, "C++ · JavaScript · Lua · Python · TypeScript · Java", "codeg"), t_in + 1.8, t_out))
    return "\n".join(out)


def scene_finale():
    t_in, t_out = 39.5, 46.8
    out = []
    gx, gy = VORT_C
    out.append(f'<circle cx="{gx}" cy="{gy}" r="190" fill="url(#core)" opacity="0">{anim("opacity", window(t_in + 0.4, t_out, 0.8))}</circle>')
    # the sprout grows from its stem
    hgt = 172
    base_y = gy + hgt / 2
    grow = anim_tf("scale", [(0, "0.05"), (t_in + 0.7, "0.05"), (t_in + 2.0, "1.06"), (t_in + 2.4, "1"), (T, "1")])
    out.append(f'<g opacity="0">{anim("opacity", window(t_in + 0.7, t_out - 0.2, 0.5))}'
               f'<g transform="translate({gx} {base_y})"><g>{grow}<g transform="translate({-gx} {-base_y})">'
               f'{logo_svg(gx, gy, hgt)}</g></g></g></g>')
    out.append(reveal(text(600, 440, "LeviMC", "hero2", "middle"), t_in + 1.0, t_out, dy=16))
    out.append(reveal(text(600, 472, "Open source tools for the community, by the community.", "tagline2", "middle"), t_in + 1.3, t_out, dy=10))
    chips = ["LeviLamina", "LegacyScriptEngine", "LeviLaunchroid", "LeviLauncher", "LeviOptimize", "MoreDimensions"]
    widths = [len(c) * 8.4 + 30 for c in chips]
    x = 600 - (sum(widths) + 10 * (len(chips) - 1)) / 2
    for k, (c, w) in enumerate(zip(chips, widths)):
        hl = k == 0
        b = (f'<rect x="{x:.0f}" y="490" width="{w:.0f}" height="28" rx="14" fill="{G400}" fill-opacity="{0.18 if hl else 0.07}" '
             f'stroke="{G400}" stroke-opacity="{0.8 if hl else 0.35}"/>' + text(x + w / 2, 509, c, "chipa" if hl else "chip", "middle"))
        out.append(reveal(b, t_in + 1.7 + 0.09 * k, t_out, dy=10))
        x += w + 10
    out.append(reveal(text(600, 546, "levimc.org   ·   lamina.levimc.org   ·   Discord · Telegram · QQ", "codeg", "middle"),
                      t_in + 2.5, t_out, dy=6))
    return "\n".join(out)


# ------------------------------------------------------------------------------ backdrop & HUD

def background():
    out = []
    for cx_, cy_, rx, ry, grad, mv in [(250, 160, 520, 320, "neb1", "60 30"), (980, 470, 560, 330, "neb2", "-70 -20"),
                                        (720, 70, 380, 220, "neb3", "-40 25")]:
        out.append(f'<ellipse cx="{cx_}" cy="{cy_}" rx="{rx}" ry="{ry}" fill="url(#{grad})">'
                   f'<animateTransform attributeName="transform" type="translate" dur="24s" repeatCount="indefinite" '
                   f'values="0 0;{mv};0 0" calcMode="spline" keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/></ellipse>')
    # perspective voxel floor
    hz = 430
    g = ['<g opacity="0.6" mask="url(#floorMask)">']
    for k in range(-14, 15):
        g.append(f'<line x1="{600 + k * 18}" y1="{hz}" x2="{600 + k * 150}" y2="{H + 20}" stroke="{G600}" stroke-opacity="0.35"/>')
    ys = [hz + 900 / z for z in [60 - 50 * k / 11 for k in range(12)]]
    vals = ";".join(f"{min(y, H + 30):.1f}" for y in ys)
    for k in range(9):
        g.append(f'<rect x="0" width="{W}" height="1" fill="{G600}" fill-opacity="0.4">'
                 f'<animate attributeName="y" dur="3s" begin="{-3 * k / 9:.2f}s" repeatCount="indefinite" values="{vals}"/></rect>')
    g.append("</g>")
    out.append("".join(g))
    for _ in range(90):  # twinkling pixel dust
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        s = rng.choice([1, 1, 1.5, 2])
        d = rng.uniform(2.5, 6)
        out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{s}" height="{s}" fill="{rng.choice([G200, PCREAM, G400])}" opacity="0.2">'
                   f'<animate attributeName="opacity" dur="{f(d)}s" begin="-{f(rng.uniform(0, d))}s" repeatCount="indefinite" '
                   f'values="0.06;{f(rng.uniform(0.35, 0.85), 2)};0.06"/></rect>')
    return "\n".join(out)


CHAPTERS = [("INTRO", 0.0, 7.6), ("LEVILAMINA", 7.6, 16.0), ("SCRIPTING", 16.0, 23.9), ("LAUNCHERS", 23.9, 31.7),
            ("ECOSYSTEM", 31.7, 39.5), ("COMMUNITY", 39.5, T)]


def hud():
    out = [logo_svg(48, 37, 26), text(68, 43, "LEVIMC", "hud"),
           text(W - 36, 43, "OPEN SOURCE BEDROCK MODDING", "hudr", "end")]
    for (x, y, sx, sy) in [(18, 18, 1, 1), (W - 18, 18, -1, 1), (18, H - 18, 1, -1), (W - 18, H - 18, -1, -1)]:
        out.append(f'<path d="M{x} {y + 22 * sy}V{y}H{x + 22 * sx}" fill="none" stroke="{G400}" stroke-opacity="0.45" stroke-width="1.5"/>')
    x0, x1, y = 60, W - 60, 582
    gap = 10
    seg_w = (x1 - x0 - gap * (len(CHAPTERS) - 1)) / len(CHAPTERS)
    for k, (name, a, b) in enumerate(CHAPTERS):
        x = x0 + k * (seg_w + gap)
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{seg_w:.1f}" height="2" rx="1" fill="{G400}" fill-opacity="0.15"/>')
        out.append(f'<rect x="{x:.1f}" y="{y}" width="0" height="2" rx="1" fill="url(#barFill)">'
                   + anim("width", [(0, 0), (a, 0), (b, f(seg_w)), (T - 0.001, f(seg_w)), (T, 0)]) + "</rect>")
        on = [(0, 0.35), (a, 0.35), (a + 0.3, 1), (b - 0.3, 1), (b, 0.35)] if k else [(0, 1), (b - 0.3, 1), (b, 0.35), (T - 0.4, 0.35), (T, 1)]
        out.append(f'<g opacity="0.35">{anim("opacity", on)}{text(x, y - 9, f"0{k + 1}  {name}", "chap")}</g>')
    return "\n".join(out)


DEFS = f"""
<defs>
  <radialGradient id="gG"><stop offset="0" stop-color="{WHITE}"/><stop offset="0.3" stop-color="{G400}"/><stop offset="1" stop-color="{G600}" stop-opacity="0"/></radialGradient>
  <radialGradient id="gL"><stop offset="0" stop-color="{WHITE}"/><stop offset="0.35" stop-color="{G300}"/><stop offset="1" stop-color="{G300}" stop-opacity="0"/></radialGradient>
  <radialGradient id="gC"><stop offset="0" stop-color="{WHITE}"/><stop offset="0.35" stop-color="{PCREAM}"/><stop offset="1" stop-color="{PCREAM}" stop-opacity="0"/></radialGradient>
  <radialGradient id="gY"><stop offset="0" stop-color="{GOLD_HI}"/><stop offset="0.35" stop-color="{GOLD}"/><stop offset="1" stop-color="#f59e0b" stop-opacity="0"/></radialGradient>
  <radialGradient id="neb1"><stop offset="0" stop-color="{NEB[0]}" stop-opacity="{NEB[1]}"/><stop offset="1" stop-color="{NEB[0]}" stop-opacity="0"/></radialGradient>
  <radialGradient id="neb2"><stop offset="0" stop-color="{NEB[2]}" stop-opacity="{NEB[3]}"/><stop offset="1" stop-color="{NEB[2]}" stop-opacity="0"/></radialGradient>
  <radialGradient id="neb3"><stop offset="0" stop-color="{NEB[4]}" stop-opacity="{NEB[5]}"/><stop offset="1" stop-color="{NEB[4]}" stop-opacity="0"/></radialGradient>
  <radialGradient id="core"><stop offset="0" stop-color="{G400}" stop-opacity="0.3"/><stop offset="0.55" stop-color="{G700}" stop-opacity="0.1"/><stop offset="1" stop-color="{G700}" stop-opacity="0"/></radialGradient>
  <radialGradient id="vign" cx="0.5" cy="0.45" r="0.75"><stop offset="0.6" stop-color="{VIGN[0]}" stop-opacity="0"/><stop offset="1" stop-color="{VIGN[0]}" stop-opacity="{VIGN[1]}"/></radialGradient>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG_STOPS[0]}"/><stop offset="0.65" stop-color="{BG_STOPS[1]}"/><stop offset="1" stop-color="{BG_STOPS[2]}"/></linearGradient>
  <linearGradient id="streak" x1="0" x2="1"><stop offset="0" stop-color="{G300}" stop-opacity="0"/><stop offset="0.5" stop-color="{WHITE}"/><stop offset="1" stop-color="{G300}" stop-opacity="0"/></linearGradient>
  <linearGradient id="screen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{G800}"/><stop offset="1" stop-color="{G950}"/></linearGradient>
  <linearGradient id="numFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{WHITE}"/><stop offset="1" stop-color="{G300}"/></linearGradient>
  <linearGradient id="numGold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GOLD_HI}"/><stop offset="1" stop-color="{GOLD}"/></linearGradient>
  <linearGradient id="heroFill" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{G300}"/><stop offset="0.5" stop-color="{WHITE}"/><stop offset="1" stop-color="{G300}"/></linearGradient>
  <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GLASS[0]}" stop-opacity="{GLASS[1]}"/><stop offset="1" stop-color="{GLASS[0]}" stop-opacity="{GLASS[2]}"/></linearGradient>
  <linearGradient id="barFill" x1="0" x2="1"><stop offset="0" stop-color="{G600}"/><stop offset="1" stop-color="{G300}"/></linearGradient>
  <linearGradient id="floorFade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="0.5"/></linearGradient>
  <mask id="floorMask"><rect x="0" y="430" width="{W}" height="{H - 430}" fill="url(#floorFade)"/></mask>
  <clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
</defs>
<style>
  text {{ font-family: {SANS}; }}
  .hero {{ font-size: 72px; font-weight: 800; letter-spacing: 6px; fill: url(#heroFill); }}
  .hero2 {{ font-size: 52px; font-weight: 800; letter-spacing: 5px; fill: url(#heroFill); }}
  .tagline {{ font-size: 22px; fill: {G200}; font-family: {MONO}; }}
  .tagline2 {{ font-size: 18px; fill: {G200}; }}
  .kicker {{ font-size: 13px; letter-spacing: 3px; fill: {G400}; font-family: {MONO}; opacity: 0.85; }}
  .h1 {{ font-size: 46px; font-weight: 800; fill: {TXT_STRONG}; letter-spacing: -0.5px; }}
  .h2 {{ font-size: 38px; font-weight: 800; fill: {TXT_STRONG}; letter-spacing: -0.5px; }}
  .sub {{ font-size: 16px; fill: {MUTED}; }}
  .tag {{ font-size: 13px; font-weight: 600; letter-spacing: 2.5px; fill: {G400}; font-family: {MONO}; }}
  .tagb {{ font-size: 12px; font-weight: 600; letter-spacing: 2.5px; fill: {MUTED}; font-family: {MONO}; }}
  .lab {{ font-size: 17px; font-weight: 650; fill: {TXT}; }}
  .lab2 {{ font-size: 15px; font-weight: 650; fill: {TXT}; }}
  .labs {{ font-size: 13.5px; fill: {MUTED}; }}
  .labon {{ font-size: 14px; font-weight: 700; fill: {G300}; }}
  .date {{ font-size: 12.5px; fill: {G400}; font-family: {MONO}; }}
  .num {{ font-size: 46px; font-weight: 800; fill: url(#numFill); letter-spacing: -1px; }}
  .numg {{ font-size: 46px; font-weight: 800; fill: url(#numGold); letter-spacing: -1px; }}
  .nums {{ font-size: 38px; font-weight: 800; fill: url(#numFill); letter-spacing: -1px; }}
  .numsg {{ font-size: 38px; font-weight: 800; fill: url(#numGold); letter-spacing: -1px; }}
  .mod {{ font-size: 14px; font-weight: 600; fill: {G200}; font-family: {MONO}; }}
  .lang {{ font-size: 20px; font-weight: 700; fill: {TXT}; font-family: {MONO}; }}
  .node {{ font-size: 14px; font-weight: 700; fill: {GOLD}; }}
  .nodes {{ font-size: 13px; font-weight: 600; fill: {G200}; }}
  .core {{ font-size: 15px; font-weight: 800; fill: {TXT_STRONG}; letter-spacing: 0.5px; }}
  .devl {{ font-size: 16px; font-weight: 700; fill: {TXT}; }}
  .cmd {{ font-size: 18px; fill: {TXT}; font-family: {MONO}; }}
  .code {{ font-size: 15px; font-family: {MONO}; white-space: pre; }}
  .codeg {{ font-size: 14px; fill: {G400}; font-family: {MONO}; }}
  .k-c {{ fill: {CODE["c"]}; }} .k-kw {{ fill: {CODE["kw"]}; }} .k-ty {{ fill: {CODE["ty"]}; }}
  .k-fn {{ fill: {G300}; }} .k-st {{ fill: {GOLD}; }} .k-cm {{ fill: {CODE["cm"]}; font-style: italic; }}
  .tab {{ font-size: 13px; fill: {MUTED}; font-family: {MONO}; }}
  .chip {{ font-size: 14px; font-weight: 600; fill: {G200}; font-family: {MONO}; }}
  .chipa {{ font-size: 14px; font-weight: 700; fill: {G300}; font-family: {MONO}; }}
  .hud {{ font-size: 14px; font-weight: 800; letter-spacing: 5px; fill: {TXT}; }}
  .hudr {{ font-size: 12px; letter-spacing: 3px; fill: {G400}; font-family: {MONO}; opacity: 0.75; }}
  .chap {{ font-size: 12px; letter-spacing: 2px; fill: {G200}; font-family: {MONO}; }}
</style>
"""


def main():
    body = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="ttl desc">',
        '<title id="ttl">LeviMC — mod Bedrock your way</title>',
        '<desc id="desc">Animated portfolio of LeviMC (formerly LiteLDev): LeviLamina mod loader (1.7k stars, 3,108 commits, '
        '133 releases), LegacyScriptEngine (JavaScript, Lua, Python), LeviLaunchroid and LeviLauncher (over a million '
        'release downloads), and the wider open-source ecosystem.</desc>',
        DEFS,
        '<g clip-path="url(#frame)">',
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        background(),
        scene_island(), scene_cube(), scene_devices(), scene_network(),
        scene_intro(), scene_finale(),
        '<g id="particles">', particles_svg(), '</g>',
        f'<rect width="{W}" height="{H}" fill="url(#vign)"/>',
        hud(),
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="{G400}" stroke-opacity="0.16"/>',
        '</g></svg>',
    ]
    svg = "\n".join(body)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "profile", f"levimc-portfolio-{THEME}.svg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {os.path.normpath(out)}  ({len(svg) / 1024:.0f} KiB)")


if __name__ == "__main__":
    if "THEME" in os.environ:
        main()
    else:  # build both variants; each run re-seeds the RNG so the two stay frame-for-frame identical
        import subprocess
        import sys
        for theme in ("dark", "light"):
            subprocess.run([sys.executable, os.path.abspath(__file__)], env={**os.environ, "THEME": theme}, check=True)
