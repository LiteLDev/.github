#!/usr/bin/env python3
"""Generate "LeviMC: Monet Edition" -- the org-profile animation (profile/levimc-monet.svg).

A Minecraft world painted in Monet's broken colour that grows a dimension as LeviMC grows:
  2D    -- 2021-2026 as a side-scrolling walk through six biomes (the LiteLoaderBDS years);
  2.5D  -- the camera swings up into textured isometric islands, one per project (the LeviLamina era);
  3D    -- a perspective, orbiting camera for the numbers and the finale.
Minecraft's own UI carries the story: title screen, /title, chat, advancement toasts, scoreboard,
crafting and brewing GUIs, item tooltips, the hotbar. Live numbers come from tools/data.json
(refreshed weekly by .github/workflows/refresh-profile.yml). GitHub shows README images through <img>,
so everything runs on one SMIL clock: no JavaScript, no web fonts, no external resources.

    python3 tools/gen_monet.py            # writes profile/levimc-monet.svg
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcpaint as mc  # noqa: E402
import pixfont as pf  # noqa: E402
import voxel as vx  # noqa: E402
from gen_portfolio import LOGO_BB, logo_color_at  # noqa: E402

W, H = 1200, 600
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))
HEADS = D["heads"]

WHITE, GRAY, DGRAY, BLACK = "#ffffff", "#aaaaaa", "#555555", "#000000"
GOLD, YELLOW, GREEN, AQUA, PINK, RED, BLUE = "#ffaa00", "#ffff55", "#55ff55", "#55ffff", "#ff55ff", "#ff5555", "#5555ff"
GUI, GUI_TXT, XP = "#c6c6c6", "#404040", "#80ff20"
INK = "#3a2a1a"
SERIF = "'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, 'Times New Roman', serif"

SC = {
    "title": (0.0, 12.0), "history": (12.0, 80.0), "lamina": (80.0, 101.0), "script": (101.0, 114.0),
    "stone": (114.0, 124.0), "launch": (124.0, 136.0), "mods": (136.0, 148.0), "tools": (148.0, 159.0),
    "people": (159.0, 184.0), "numbers": (184.0, 207.0), "finale": (207.0, 246.0),
}
T = 246.0
CHAPTERS = [  # (start, end, hotbar slot)
    (12.0, 80.0, 0), (80.0, 101.0, 1), (101.0, 114.0, 2), (114.0, 124.0, 3), (124.0, 136.0, 4),
    (136.0, 148.0, 5), (148.0, 159.0, 6), (159.0, 184.0, 7), (184.0, T, 8),
]

DEFS = []
VDEFS = vx.Defs()
_GLYPHS = set()
_ID = [0]


def uid(p):
    _ID[0] += 1
    return f"{p}{_ID[0]}"


# ----------------------------------------------------------------------------------- data

def R(name, key):
    return D["repos"].get(name, {}).get(key)


def k_fmt(n):
    if n is None:
        return "?"
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 10_000:
        return f"{round(n / 1000)}k"
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def comma(n):
    return f"{n:,}" if isinstance(n, int) else "?"


LL_VER = R("LeviLamina", "latest") or "v26"
DL_LAUNCH = (R("LeviLaunchroid", "downloads") or 0) + (R("LeviLauncher", "downloads") or 0)


# ------------------------------------------------------------------------------- SMIL basics

def f(v, nd=1):
    s = f"{v:.{nd}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def shade(c, k):
    v = [int(c[j:j + 2], 16) for j in (1, 3, 5)]
    return "#" + "".join(f"{int(clamp(round(x * k), 0, 255)):02x}" for x in v)


def kt(t):
    if t <= 0:
        return "0"
    if t >= T:
        return "1"
    s = f"{t / T:.6f}".rstrip("0")
    return s[1:] if s != "0." else "0"


def _pad(pairs):
    pairs = sorted(pairs, key=lambda p: p[0])
    if pairs[0][0] > 0:
        pairs.insert(0, (0, pairs[0][1]))
    if pairs[-1][0] < T:
        pairs.append((T, pairs[-1][1]))
    out = []
    for t, v in pairs:
        if out and t <= out[-1][0]:
            t = out[-1][0] + 0.01
        out.append((min(t, T), v))
    return out


def anim(attr, pairs, calc="linear"):
    pairs = _pad(pairs)
    return (f'<animate attributeName="{attr}" dur="{f(T)}s" repeatCount="indefinite" calcMode="{calc}" '
            f'keyTimes="{";".join(kt(t) for t, _ in pairs)}" values="{";".join(str(v) for _, v in pairs)}"/>')


def anim_tf(kind, pairs):
    pairs = _pad(pairs)
    return (f'<animateTransform attributeName="transform" type="{kind}" dur="{f(T)}s" repeatCount="indefinite" '
            f'keyTimes="{";".join(kt(t) for t, _ in pairs)}" values="{";".join(str(v) for _, v in pairs)}"/>')


def disp(t0, t1):
    t0, t1 = max(0.0, t0), min(T, t1)
    if t0 <= 0 and t1 >= T:
        return "", "inline"
    if t0 <= 0:
        vals, kts = "inline;none", f"0;{kt(t1)}"
    elif t1 >= T:
        vals, kts = "none;inline", f"0;{kt(t0)}"
    else:
        vals, kts = "none;inline;none", f"0;{kt(t0)};{kt(t1)}"
    a = (f'<animate attributeName="display" dur="{f(T)}s" repeatCount="indefinite" calcMode="discrete" '
         f'keyTimes="{kts}" values="{vals}"/>')
    return a, ("inline" if t0 <= 0 else "none")


def show(body, t_in, t_out, fade=0.3, dy=0, dx=0):
    a, d0 = disp(t_in - 0.01, t_out + 0.01)
    op = anim("opacity", [(t_in, 0), (t_in + fade, 1), (t_out - fade, 1), (t_out, 0)])
    mv = ""
    if dx or dy:
        mv = anim_tf("translate", [(t_in, f"{dx} {dy}"), (t_in + fade * 1.5, "0 0"), (t_out - fade, "0 0"),
                                   (t_out, f"{-dx * 0.5:.0f} {-dy * 0.5:.0f}")])
    return f'<g display="{d0}" opacity="0">{a}{op}{mv}{body}</g>'


def only(body, t_in, t_out):
    a, d0 = disp(t_in, t_out)
    return f'<g display="{d0}">{a}{body}</g>'


def pop(body, cx, cy, t_in, t_out, dur=0.3):
    a, d0 = disp(t_in - 0.01, t_out + 0.01)
    sc = anim_tf("scale", [(t_in, "0.01"), (t_in + dur * 0.7, "1.18"), (t_in + dur, "1"), (t_out - 0.2, "1"),
                           (t_out, "0.01")])
    return (f'<g display="{d0}">{a}<g transform="translate({f(cx)} {f(cy)})"><g>{sc}'
            f'<g transform="translate({f(-cx)} {f(-cy)})">{body}</g></g></g></g>')


def loop_disp(dur, on_frac, begin=0.0):
    return (f'<animate attributeName="display" dur="{f(dur, 2)}s" begin="{f(begin, 2)}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="0;{f(on_frac, 3)}" values="inline;none"/>')


def bob(body, amp=6, dur=4.0, begin=0.0):
    return (f'<g><animateTransform attributeName="transform" type="translate" dur="{f(dur)}s" begin="{f(begin)}s" '
            f'repeatCount="indefinite" values="0 0;0 {-amp};0 0" keyTimes="0;0.5;1" calcMode="spline" '
            f'keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>{body}</g>')


def scene(body, t0, t1, first=False, last=False, fade=0.6):
    if first:
        pairs = [(0, 0), (1.0, 1), (t1 + fade, 1), (t1 + fade + 0.01, 0)]
        a, d0 = disp(0, t1 + fade + 0.02)
    elif last:
        pairs = [(t0 - fade, 0), (t0 + fade, 1), (T - 2.2, 1), (T - 0.2, 0)]
        a, d0 = disp(t0 - fade, T)
    else:
        pairs = [(t0 - fade, 0), (t0 + fade, 1), (t1 + fade, 1), (t1 + fade + 0.01, 0)]
        a, d0 = disp(t0 - fade, t1 + fade + 0.02)
    return f'<g display="{d0}" opacity="0">{a}{anim("opacity", pairs)}{body}</g>'


# ------------------------------------------------------------------------------- pixel text

def gid(ch):
    ch = pf.ALIASES.get(ch, ch)
    _GLYPHS.add(ch)
    return f"c{ord(ch)}"


def tw(s, size=2):
    return pf.width(s) * size


def _line(s):
    lid = uid("t")
    cx, uses = 0, []
    for ch in s:
        if ch != " ":
            uses.append(f'<use href="#{gid(ch)}" x="{cx}"/>')
        cx += pf.advance(pf.ALIASES.get(ch, ch))
    DEFS.append(f'<g id="{lid}">{"".join(uses)}</g>')
    return lid


def ptext(x, y, s, size=2, fill=WHITE, shadow=True, anchor="start"):
    w = tw(s, size)
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    lid = _line(s)
    sh = ""
    if shadow:
        sh = f'<use href="#{lid}" x="1" y="1" fill="{shadow if isinstance(shadow, str) else shade(fill, 0.25)}"/>'
    return f'<g transform="translate({f(x)} {f(y)}) scale({size})">{sh}<use href="#{lid}" fill="{fill}"/></g>'


def prun(x, y, runs, size=2):
    cx, parts = 0, []
    for s, col in runs:
        uses = []
        for ch in s:
            if ch != " ":
                uses.append(f'<use href="#{gid(ch)}" x="{cx}"/>')
            cx += pf.advance(pf.ALIASES.get(ch, ch))
        if uses:
            parts.append(f'<g fill="{col}">{"".join(uses)}</g>')
    return f'<g transform="translate({f(x)} {f(y)}) scale({size})">{"".join(parts)}</g>', cx * size


def plines(x, y, lines, size=2, lh=None, fill=WHITE, shadow=True):
    lh = lh or size * 10
    out = []
    for i, ln in enumerate(lines):
        s, col = ln if isinstance(ln, tuple) else (ln, fill)
        if s:
            out.append(ptext(x, y + i * lh, s, size, col, shadow=shadow))
    return "".join(out)


def logo_text(x, y, s, size, t_in, t_out):
    """Minecraft title-screen lettering: a cobblestone face over a stepped, lilac-dark extrusion."""
    w = tw(s, size)
    x -= w / 2
    lid = _line(s)
    img = VDEFS.image("cobble", "top")
    tp = uid("tp")
    DEFS.append(f'<pattern id="{tp}" patternUnits="userSpaceOnUse" width="8" height="8" '
                f'patternTransform="scale(0.25)"><use href="#{img}"/></pattern>')
    ext = "".join(f'<use href="#{lid}" x="{k * 0.22:.2f}" y="{k * 0.22:.2f}" fill="{c}"/>'
                  for k, c in ((4, "#1a1626"), (3, "#2a2440"), (2, "#3c3456"), (1, "#56507a")))
    face = f'<use href="#{lid}" fill="url(#{tp})"/><use href="#{lid}" fill="#ffffff" fill-opacity="0.1"/>'
    return show(f'<g transform="translate({f(x)} {f(y)}) scale({size})">{ext}{face}</g>', t_in, t_out, dy=-20)


# ------------------------------------------------------------------------------ Minecraft UI

def tooltip(x, y, w, h, u=2, alpha=0.9):
    body = (f'<path d="M{f(x + u)} {f(y)}h{f(w - 2 * u)}v{f(h)}h{f(-(w - 2 * u))}z'
            f'M{f(x)} {f(y + u)}h{f(w)}v{f(h - 2 * u)}h{f(-w)}z" fill="#100010" fill-opacity="{alpha}"/>')
    rim = (f'<rect x="{f(x + 1.5 * u)}" y="{f(y + 1.5 * u)}" width="{f(w - 3 * u)}" height="{f(h - 3 * u)}" '
           f'fill="none" stroke="url(#ttb)" stroke-width="{u}"/>')
    return body + rim


def item_tooltip(x, y, name, lore, name_col=AQUA):
    lines = [(name, name_col)] + list(lore)
    w = max(tw(s) for s, _ in lines) + 24
    h = 18 + 22 + (len(lines) - 1) * 20 + 6
    return tooltip(x, y, w, h) + ptext(x + 12, y + 10, name, 2, name_col) + plines(x + 12, y + 36, lore, 2, 20), w, h


def gui_panel(x, y, w, h, u=3):
    return (f'<rect x="{x}" y="{y + u}" width="{w}" height="{h - 2 * u}" fill="{BLACK}"/>'
            f'<rect x="{x + u}" y="{y}" width="{w - 2 * u}" height="{h}" fill="{BLACK}"/>'
            f'<rect x="{x + u}" y="{y + u}" width="{w - 2 * u}" height="{h - 2 * u}" fill="{GUI}"/>'
            f'<path d="M{x + u} {y + u}h{w - 3 * u}v{u}h{-(w - 4 * u)}v{h - 4 * u}h{-u}z" fill="#ffffff"/>'
            f'<path d="M{x + w - u} {y + 2 * u}v{h - 3 * u}h{-(w - 3 * u)}v{-u}h{w - 4 * u}v{-(h - 4 * u)}z" fill="#555555"/>')


def slot(x, y, s=44, u=2):
    return (f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="#8b8b8b"/>'
            f'<path d="M{x} {y}h{s - u}v{u}h{-(s - 2 * u)}v{s - 2 * u}h{-u}z" fill="#373737"/>'
            f'<path d="M{x + s} {y + u}v{s - u}h{-(s - u)}v{-u}h{s - 2 * u}v{-(s - 2 * u)}z" fill="#ffffff"/>')


def book(x, y, w, h):
    """The book-and-quill page: Monet's cream paper, a leather edge."""
    return (f'<rect x="{x - 6}" y="{y - 6}" width="{w + 12}" height="{h + 12}" fill="#6b4a24"/>'
            f'<rect x="{x - 3}" y="{y - 3}" width="{w + 6}" height="{h + 6}" fill="#8a6234"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f3ead2"/>'
            f'<rect x="{x}" y="{y + h - 6}" width="{w}" height="6" fill="#e2d4b0"/>')


def nametag(cx, y, s, sub=None, size=2, col=WHITE):
    w = max(tw(s, size), tw(sub, size) if sub else 0) + 12
    h = 7 * size + 10 + (10 * size if sub else 0)
    out = (f'<rect x="{f(cx - w / 2)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="#000000" fill-opacity="0.5"/>'
           + ptext(cx, y + 5, s, size, col, anchor="middle"))
    if sub:
        out += ptext(cx, y + 5 + 10 * size, sub, size, GRAY, anchor="middle")
    return out


def mc_title(title, sub, t_in, t_out, y=78, col=WHITE, sub_col=GOLD, size=7):
    """The /title command: a big centred title and a subtitle."""
    body = ptext(600, y, title, size, col, anchor="middle")
    if sub:
        body += ptext(600, y + size * 7 + 14, sub, 3 if size >= 5 else 2, sub_col, anchor="middle")
    return show(body, t_in, t_out, fade=0.25)


def toast(icon_name, title, body, t_in, dur=2.3, x=868, y=18, title_col=YELLOW):
    w, h = 316, 64
    box = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#212121"/>'
           f'<rect x="{x + 2}" y="{y + 2}" width="{w - 4}" height="{h - 4}" fill="none" stroke="#5c5c5c" stroke-width="2"/>'
           + icon(icon_name, x + 14, y + 14, 4.5) + ptext(x + 64, y + 14, title, 2, title_col)
           + ptext(x + 64, y + 38, body, 2, WHITE))
    a, d0 = disp(t_in, t_in + dur)
    mv = anim_tf("translate", [(t_in, f"{w + 30} 0"), (t_in + 0.25, "0 0"), (t_in + dur - 0.25, "0 0"),
                               (t_in + dur, f"{w + 30} 0")])
    return f'<g display="{d0}">{a}<g>{mv}{box}</g></g>'


def chat_block(lines, t0, step=1.1, life=6.5, x=14, base_y=486, t_end=None, width=400):
    """Minecraft chat: each line appears at the bottom and older lines climb up."""
    out = []
    times = [t0 + i * step for i in range(len(lines))]
    for i, ((s, col), ti) in enumerate(zip(lines, times)):
        t_out = min(ti + life, t_end) if t_end else ti + life
        pairs = [(ti, "0 0")]
        for j in range(i + 1, len(lines)):
            if times[j] >= t_out:
                break
            pairs += [(times[j], f"0 {-(j - i - 1) * 22}"), (times[j] + 0.12, f"0 {-(j - i) * 22}")]
        body = (f'<rect x="{x}" y="{base_y}" width="{width}" height="22" fill="#000000" fill-opacity="0.42"/>'
                + ptext(x + 6, base_y + 4, s, 2, col))
        a, d0 = disp(ti, t_out)
        out.append(f'<g display="{d0}">{a}{anim("opacity", [(t_out - 0.4, 1), (t_out, 0)])}'
                   f'<g>{anim_tf("translate", pairs)}{body}</g></g>')
    return "".join(out)


def scoreboard(x, y, title, rows, t_in, t_out, w=210):
    h = 26 + len(rows) * 20 + 6
    body = (f'<rect x="{x}" y="{y}" width="{w}" height="22" fill="#000000" fill-opacity="0.5"/>'
            f'<rect x="{x}" y="{y + 22}" width="{w}" height="{h - 22}" fill="#000000" fill-opacity="0.32"/>'
            + ptext(x + w / 2, y + 4, title, 2, WHITE, anchor="middle"))
    for i, (k, v) in enumerate(rows):
        body += ptext(x + 8, y + 28 + i * 20, k, 2, WHITE) + ptext(x + w - 8, y + 28 + i * 20, v, 2, RED, anchor="end")
    return show(body, t_in, t_out, dx=20)


# ----------------------------------------------------------------------------------- sprites

def sprite(rows, pal, x=0, y=0, s=1):
    by_col = {}
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            ch = row[i]
            if ch in pal:
                i0 = i
                while i < len(row) and row[i] == ch:
                    i += 1
                by_col.setdefault(pal[ch], []).append(f"M{i0} {j}h{i - i0}v1h{i0 - i}z")
            else:
                i += 1
    paths = "".join(f'<path d="{"".join(d)}" fill="{c}"/>' for c, d in by_col.items())
    return f'<g transform="translate({f(x)} {f(y)}) scale({f(s, 3)})">{paths}</g>'


ICONS = {
    "grass": (["..gggg..", ".gGGGGg.", "gGGGGGGg", "dgGGGGgD", "ddggggDD", "dddddDDD", ".ddddDD.", "..ddDD.."],
              {"g": "#5f9a44", "G": "#8cc060", "d": "#8f6a48", "D": "#6e5038"}),
    "crafting": (["cccccccc", "cCCcCCCc", "cCCcCCCc", "cccccccc", "pPpPpPpP", "pkkpPiiP", "pkkpPiiP", "pppppppp"],
                 {"c": "#6e5232", "C": "#b8945f", "p": "#8a6a40", "P": "#a8864f", "k": "#7a7a90", "i": "#c8c8d8"}),
    "potion": (["...cc...", "...gg...", "..g..g..", ".gpppPg.", ".gppppg.", ".gppppg.", "..gggg..", "........"],
               {"c": "#8a5a30", "g": "#d8eef6", "p": "#f06ae0", "P": "#ffffff"}),
    "eye": (["..gggg..", ".gGGGGg.", "gGkkkkGg", "gGkYYkGg", "gGkYYkGg", "gGkkkkGg", ".gGGGGg.", "..gggg.."],
            {"g": "#1a6a4a", "G": "#3aa878", "k": "#0a2a20", "Y": "#d8f070"}),
    "minecart": (["........", "i......i", "iiiiiiii", "iIIIIIIi", "iIIIIIIi", "iiiiiiii", ".k....k.", "........"],
                 {"i": "#6a6a78", "I": "#9a9aa8", "k": "#2a2a2a"}),
    "ebook": ([".bbbbbb.", "bpppppbb", "bpBBBpbb", "bpppppbb", "bpBBBpbb", "bpppppbb", ".bbbbbb.", "........"],
              {"b": "#8a3ac8", "p": "#f3ead2", "B": "#a070d8"}),
    "redstone": (["........", "..r.....", ".rRr..r.", "..r..rRr", "...r..r.", "..rRr...", "...r....", "........"],
                 {"r": "#b02010", "R": "#ff5a3a"}),
    "head": (["HHHHHHHH", "HHHHHHHH", "HssssssH", "ssssssss", "sWBssBWs", "sssnnsss", "ssmmmmss", "ssssssss"],
             {"H": "#2f1f0f", "s": "#b5835a", "W": "#ffffff", "B": "#523d89", "n": "#8a5a3e", "m": "#6a3a2a"}),
    "star": (["...w....", "..wWw...", "wwWWWww.", ".wWWWw..", "..wWw...", ".w...w..", "........", "........"],
             {"w": "#e8e0f8", "W": "#fff8b0"}),
    "book": (["bbbbbbb.", "bpppppb.", "bpbbbpb.", "bpppppb.", "bpbbbpb.", "bpppppb.", "bbbbbbbq", "......qq"],
             {"b": "#6b3f1f", "p": "#efe6cf", "q": "#3a3a3a"}),
    "command": (["oooooooo", "oOOOOOOo", "oOkOOOOo", "oOOkOOOo", "oOkOkkOo", "oOOOOOOo", "oOOOOOOo", "oooooooo"],
                {"o": "#a8582a", "O": "#d8884a", "k": "#2a2a2a"}),
    "paper": (["........", ".pppppp.", ".pPPPPp.", ".pppppp.", ".pPPPpp.", ".pppppp.", ".pPPPPp.", "........"],
              {"p": "#f3ead2", "P": "#a89a80"}),
    "clock": (["..gggg..", ".gYYYYg.", "gYYkYYYg", "gYYkYYYg", "gYYkkYYg", "gYYYYYYg", ".gYYYYg.", "..gggg.."],
              {"g": "#c89a20", "Y": "#f6e080", "k": "#3a3a3a"}),
    "compass": (["..iiii..", ".iWWWWi.", "iWWrWWWi", "iWWrWWWi", "iWWkWWWi", "iWWkWWWi", ".iWWWWi.", "..iiii.."],
                {"i": "#6a6a78", "W": "#d8d8e0", "r": "#e03a2a", "k": "#3a3a4a"}),
    "hook": (["...ii...", "..i..i..", "..i..i..", "...ii...", "...ww...", "...ww...", "...ww...", "...ww..."],
             {"i": "#9a9aa8", "w": "#8a6a40"}),
    "pearl": (["..tttt..", ".tTTTTt.", "tTWTTTTt", "tTTTTTTt", "tTTTTTTt", "tTTTTTTt", ".tTTTTt.", "..tttt.."],
              {"t": "#0e5a50", "T": "#2a9a88", "W": "#c8fff0"}),
    "emerald": (["...gg...", "..gLLg..", ".gLGGLg.", "gLGGGGGg", "gGGGGGdg", ".gGGGdg.", "..gddg..", "...gg..."],
                {"g": "#0c6b2c", "G": "#17c54a", "L": "#a0f8b8", "d": "#0e8a36"}),
    "chest": (["cccccccc", "cCCCCCCc", "cCCCCCCc", "kkkGGkkk", "cCCGGCCc", "cCCCCCCc", "cCCCCCCc", "cccccccc"],
              {"c": "#6b4a1f", "C": "#a8782f", "k": "#3a2810", "G": "#d8d8d8"}),
    "feather": ([".......w", "......wW", ".....wW.", "....wW..", "...wW...", "..wW....", ".wW.....", "w......."],
                {"w": "#e8e8f0", "W": "#b8b8c8"}),
    "shield": ([".iiiiii.", "iWWBBWWi", "iWWBBWWi", "iBBBBBBi", "iWWBBWWi", ".iWBBWi.", "..iWWi..", "...ii..."],
               {"i": "#6a6a78", "W": "#e8e0d0", "B": "#3a5ab0"}),
    "map": (["pppppppp", "pBBGGBBp", "pBGGGGBp", "pGGBBGGp", "pGBBBBGp", "pBGGGGBp", "pBBGGBBp", "pppppppp"],
            {"p": "#e8dcb8", "B": "#6a9ad0", "G": "#7ab060"}),
    "tnt": (["rrrrrrrr", "rRrRrRrr", "wwwwwwww", "wkwkkwkw", "wwwwwwww", "rrRrrRrr", "rRrrRrrr", "rrrrrrrr"],
            {"r": "#c02818", "R": "#e8503a", "w": "#efe8dc", "k": "#2a2a2a"}),
    "sprout": (["....LL..", "...LlL..", "..LlL...", "CC.d....", "CcCd....", ".CCd....", "...d....", "..ddd..."],
               {"L": "#7ba46d", "l": "#f6f3ea", "C": "#294c2d", "c": "#7ba46d", "d": "#5a3a22"}),
}
POTIONS = {"JavaScript": "#f6d040", "Lua": "#3a5ad8", "Python": "#4a8ad8", "Node.js": "#4caf50"}


def icon(name, x, y, s):
    if name.startswith("potion:"):
        rows, pal = ICONS["potion"]
        return sprite(rows, dict(pal, p=name.split(":", 1)[1]), x, y, s)
    rows, pal = ICONS[name]
    return sprite(rows, pal, x, y, s)


def head_flat(login, x, y, size=32, outline=True):
    rows = HEADS.get(login)
    if not rows:
        return icon("head", x, y, size / 8)
    hid = f"h_{login.replace('-', '_')}"
    if not any(d.startswith(f'<g id="{hid}"') for d in DEFS):
        rects = "".join(f'<rect x="{i}" y="{j}" width="1" height="1" fill="#{row[i * 6:i * 6 + 6]}"/>'
                        for j, row in enumerate(rows) for i in range(8))
        DEFS.append(f'<g id="{hid}">{rects}</g>')
    s = size / 8
    ol = (f'<rect x="{f(x - s / 2)}" y="{f(y - s / 2)}" width="{f(size + s)}" height="{f(size + s)}" fill="#000000" '
          f'fill-opacity="0.55"/>') if outline else ""
    return f'{ol}<use href="#{hid}" transform="translate({f(x)} {f(y)}) scale({f(s, 3)})"/>'


MOBS = {
    "sheep": (["..wwwwwww...", ".wWwwwwWwff.", "wwwwwwwwwffe", "wwWwwwwwwff.", ".wwwwwwww...", ".k.k..k.k..."],
              {"w": "#f2efe8", "W": "#d4d0e4", "f": "#d8b898", "e": "#2a2a2a", "k": "#5a4a4a"}),
    "creeper": (["gGgg", "kgkg", "gkkg", "gkkG", "Gggg", "ggGg", "gGgg", "gggG", "gGgg", "ggGg", "g.gg", "gg.g"],
                {"g": "#5cb84a", "G": "#9ae070", "k": "#1a2a1a"}),
    "fox": (["......oo..", ".....oooo.", "oo..ooowke", "ooooooooww", ".oooooooo.", ".k.k..k.k."],
            {"o": "#e8862a", "w": "#f4f0e8", "k": "#2a2020", "e": "#1a1a1a"}),
    "villager": (["..bbbb..", "..ssss..", "..sese..", "..ssnn..", "..ssnn..", ".rrrrrr.", ".rrRRrr.", ".rRRRRr.",
                  ".rrrrrr.", ".rrrrrr.", "..rr.rr.", "..kk.kk."],
                 {"b": "#5a3a22", "s": "#c8946a", "e": "#2a6a3a", "n": "#a87050", "r": "#7a5232", "R": "#5a3a22",
                  "k": "#3a2a1a"}),
    "bee": (["..ww..", "yykyyk", "ykyykk", ".k..k."], {"w": "#e8f0ff", "y": "#f6c832", "k": "#2a2a2a"}),
}


def mob(name, x, y, s):
    rows, pal = MOBS[name]
    return sprite(rows, pal, x, y - len(rows) * s, s)


WALKER = {
    "top": ["..hhhh..", ".hhhhhhh", "..HHHH..", "..ssss..", "..ssse..", "..sbsss.", "..bbbb..", ".ccccc..",
            ".ccccc..", ".cCcccsB", ".cCccc.B", ".ccccc..", "..pppp.."],
    "a": [".pp..pp.", ".pp..pp.", ".kk..kk."],
    "b": ["...pp...", "...pp...", "...kk..."],
    "pal": {"h": "#e2c878", "H": "#6a4a2a", "s": "#e0b090", "e": "#2a2a3a", "b": "#f2f0e8", "c": "#4a6ab0",
            "C": "#3a5090", "p": "#5a5040", "k": "#2a2018", "B": "#8a5a30"},
}


def walker(x, y, s, t_walk0, t_walk1):
    """Claude Monet as a Minecraft player: straw hat, white beard, blue smock, brush in hand."""
    top = sprite(WALKER["top"], WALKER["pal"], x, y, s)
    legs_y = y + 13 * s
    a = sprite(WALKER["a"], WALKER["pal"], x, legs_y, s)
    b = sprite(WALKER["b"], WALKER["pal"], x, legs_y, s)
    walk = only(f'<g>{loop_disp(0.36, 0.5)}{a}</g><g>{loop_disp(0.36, 0.5, 0.18)}{b}</g>', t_walk0, t_walk1)
    idle = f'<g>{anim("display", [(0, "inline"), (t_walk0, "none"), (t_walk1, "inline")], calc="discrete")}{b}</g>'
    bounce = (f'<animateTransform attributeName="transform" type="translate" dur="0.36s" repeatCount="indefinite" '
              f'values="0 0;0 -{s};0 0" keyTimes="0;0.5;1"/>')
    return f'<g><g>{bounce}{top}</g>{walk}{idle}</g>'


def oak_sign(cx, ground, text, sub=None):
    bw, bh = 104, 54
    x, y = cx - bw / 2, ground - 44 - bh
    planks = "".join(f'<rect x="{f(x)}" y="{f(y + k * 13.5)}" width="{bw}" height="1.5" fill="#8f7448"/>' for k in (1, 2, 3))
    out = (f'<rect x="{f(cx - 4)}" y="{f(ground - 46)}" width="8" height="46" fill="#6b5130"/>'
           f'<rect x="{f(x - 3)}" y="{f(y - 3)}" width="{bw + 6}" height="{bh + 6}" fill="#4e3a22"/>'
           f'<rect x="{f(x)}" y="{f(y)}" width="{bw}" height="{bh}" fill="#b8945f"/>{planks}'
           + ptext(cx, y + 8, text, 3, BLACK, shadow=False, anchor="middle"))
    if sub:
        out += ptext(cx, y + 36, sub, 2, "#3a2a1a", shadow=False, anchor="middle")
    return out


def pixel_logo_rows(cells):
    x0, y0, x1, y1 = LOGO_BB
    span = max(x1 - x0, y1 - y0)
    ox, oy = (x0 + x1) / 2 - span / 2, (y0 + y1) / 2 - span / 2
    rows = []
    for j in range(cells):
        row = []
        for i in range(cells):
            votes = {}
            for a in range(4):
                for b in range(4):
                    c = logo_color_at(ox + (i + (a + 0.5) / 4) * span / cells, oy + (j + (b + 0.5) / 4) * span / cells)
                    if c:
                        votes[c] = votes.get(c, 0) + 1
            best = max(votes.items(), key=lambda kv: kv[1]) if votes else (None, 0)
            row.append(best[0] if best[1] >= 6 else None)
        rows.append(row)
    return rows


def canvas(uri, w=W, h=H, x=0):
    return (f'<image x="{x}" y="0" width="{w}" height="{h}" preserveAspectRatio="none" '
            f'style="image-rendering:pixelated" href="{uri}"/>')


def sky_canvas(*args, **kw):
    if len(args) < 6:
        kw.setdefault("clouds", 0.64)
    g = mc.sky(240, 120, *args, **kw)
    return canvas(mc.png_uri([c for row in g for c in row], 240, 120))


def particles(n, region, colors, seed, rise=60, size=6):
    r = random.Random(seed)
    x0, y0, x1, y1 = region
    out = []
    for _ in range(n):
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        d = r.uniform(1.8, 3.6)
        b = r.uniform(0, d)
        c = colors[r.randrange(len(colors))]
        out.append(f'<rect x="{f(x)}" y="{f(y)}" width="{size}" height="{size}" fill="{c}" opacity="0">'
                   f'<animate attributeName="opacity" dur="{f(d, 2)}s" begin="{f(b, 2)}s" repeatCount="indefinite" '
                   f'values="0;1;0" keyTimes="0;0.3;1"/>'
                   f'<animateTransform attributeName="transform" type="translate" dur="{f(d, 2)}s" begin="{f(b, 2)}s" '
                   f'repeatCount="indefinite" values="0 0;0 {-rise}"/></rect>')
    return "".join(out)


def mc_clouds(seed, y0=40, n=4, dur=70):
    """Minecraft's flat, blocky clouds, drifting across a Monet sky."""
    r = random.Random(seed)
    out = []
    for _ in range(n):
        cells = [(r.randint(0, 3), 0, r.randint(4, 8)), (0, 1, r.randint(7, 12)), (r.randint(1, 3), 2, r.randint(3, 7))]
        x, y = r.uniform(-200, 1100), y0 + r.uniform(0, 80)
        body = "".join(f'<rect x="{f(x + i_ * 16)}" y="{f(y + j * 16)}" width="{w * 16}" height="16" fill="#ffffff"/>'
                       for i_, j, w in cells)
        out.append(f'<g opacity="0.55"><animateTransform attributeName="transform" type="translate" dur="{dur}s" '
                   f'begin="-{r.uniform(0, dur):.1f}s" repeatCount="indefinite" values="-300 0;1300 0"/>{body}</g>')
    return "".join(out)


PLAQUES = []


def plaque(numeral, title, after, t_in, t_out):
    PLAQUES.append((numeral, title, after, t_in, t_out))


def plaques_svg():
    out = []
    for numeral, title, after, t_in, t_out in PLAQUES:
        txt = f"Plate {numeral}  ·  {title}  —  after Monet, {after}"
        w = len(txt) * 5.9 + 26
        body = (f'<rect x="20" y="556" width="{f(w)}" height="25" fill="#f1e8d2"/>'
                f'<rect x="21.5" y="557.5" width="{f(w - 3)}" height="22" fill="none" stroke="#b08d4a" stroke-width="1.5"/>'
                f'<text x="32" y="573" class="plq">{txt.replace("&", "&amp;")}</text>')
        out.append(show(body, t_in, t_out, fade=0.4))
    return "".join(out)


HOTBAR = ["grass", "crafting", "potion", "eye", "minecart", "ebook", "redstone", "head", "star"]


def hud(t_in):
    """Hearts, hunger, XP and the hotbar; the selected slot is the chapter, the XP level its number."""
    bx, by = 600 - 182, 548
    out = [f'<rect x="{bx - 2}" y="{by - 2}" width="368" height="44" fill="#000000" fill-opacity="0.55"/>']
    for i, ic in enumerate(HOTBAR):
        x = bx + i * 40 + 2
        out.append(f'<rect x="{x}" y="{by}" width="38" height="38" fill="#8b8b8b" fill-opacity="0.35"/>'
                   f'<rect x="{x}" y="{by}" width="38" height="38" fill="none" stroke="#3a3a3a" stroke-width="2"/>')
        out.append(icon(ic, x + 7, by + 7, 3))
    out.append(f'<rect x="{bx - 1}" y="{by - 3}" width="44" height="44" fill="none" stroke="#ffffff" stroke-width="3">'
               f'<animate attributeName="x" dur="{f(T)}s" repeatCount="indefinite" calcMode="discrete" '
               f'keyTimes="0;{";".join(kt(c[0]) for c in CHAPTERS[1:])}" '
               f'values="{";".join(str(bx + c[2] * 40 - 1) for c in CHAPTERS)}"/></rect>')
    heart = [".rr.rr..", "rRrrrrr.", "rRrrrrr.", ".rrrrr..", "..rrr...", "...r...."]
    food = ["....bb..", "...bBb..", "..bBbb..", ".mmbb...", "mmm.....", "mm......"]
    for i in range(10):
        out.append(sprite(heart, {"r": "#e8302a", "R": "#ffb0a8"}, bx + i * 17, by - 32, 2))
        out.append(sprite(food, {"b": "#b06a3a", "B": "#e8a070", "m": "#e8e0d0"}, bx + 364 - 17 - i * 17, by - 32, 2))
    pairs = []
    for t0, t1, _ in CHAPTERS:
        pairs += [(t0, 0), (t1 - 0.02, 364)]
    out.append(f'<rect x="{bx}" y="{by - 12}" width="364" height="7" fill="#000000" fill-opacity="0.7"/>'
               f'<rect x="{bx}" y="{by - 11}" width="0" height="5" fill="{XP}">{anim("width", pairs)}</rect>')
    for t0, t1, s in CHAPTERS:
        n = str(s + 1)
        num = "".join(ptext(600 + ox, by - 30 + oy, n, 2, BLACK, shadow=False, anchor="middle")
                      for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2))) + ptext(600, by - 30, n, 2, XP, shadow=False,
                                                                                anchor="middle")
        out.append(only(num, t0, t1))
    return show("".join(out), t_in, T - 0.2, fade=0.5)


def frame():
    return (f'<rect x="4" y="4" width="{W - 8}" height="{H - 8}" fill="none" stroke="#8a6a2a" stroke-width="8"/>'
            f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" fill="none" stroke="#d8b464" stroke-width="2"/>'
            f'<rect x="8.5" y="8.5" width="{W - 17}" height="{H - 17}" fill="none" stroke="#4e3a14" stroke-width="1"/>'
            + "".join(f'<rect x="{x}" y="{y}" width="12" height="12" fill="#d8b464"/>'
                      f'<rect x="{x + 3}" y="{y + 3}" width="6" height="6" fill="#8a6a2a"/>'
                      for x, y in ((0, 0), (W - 12, 0), (0, H - 12), (W - 12, H - 12))))


# -------------------------------------------------------------------------- iso helpers

def island(w, d, top="grass", under="dirt", taper=2):
    vox = {}
    for x in range(w):
        for y in range(d):
            vox[(x, y, 0)] = under
            vox[(x, y, 1)] = top
    for k in range(1, taper + 1):
        for x in range(k, w - k):
            for y in range(k, d - k):
                vox[(x, y, -k)] = "dirt" if k == 1 else "stone"
    return vox


def strip(n, half=1):
    """An island running along the screen's horizontal: cells with |x + y - n| <= half.
    Along-strip index s maps to cell (s + a, n - s + a); a is depth (-half/2 .. half/2)."""
    vox = {}
    for x in range(n + 1):
        for y in range(n + 1):
            d = abs(x + y - n)
            if d <= half:
                vox[(x, y, 0)] = "dirt"
                vox[(x, y, 1)] = "grass"
                if d <= half - 1:
                    vox[(x, y, -1)] = "stone"
    return vox


def scell(n, s, a=0):
    return (s + a, n - s + a)


def strip_origin(n, cx, cy, z=1):
    """Translate so strip centre (s = n/2, top of layer z) lands on (cx, cy)."""
    return cx, cy - n * vx.CY + z * vx.S


def tree(vox, x, y, z, h=3, leaf="leaves", log="log"):
    for k in range(h):
        vox[(x, y, z + k)] = log
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            vox.setdefault((x + dx, y + dy, z + h - 1), leaf)
            vox.setdefault((x + dx, y + dy, z + h), leaf)
    vox[(x, y, z + h + 1)] = leaf


def iso_group(vox, ox, oy, heads=None, bobbing=True):
    body = vx.iso_svg(VDEFS, vox, heads=heads)
    inner = bob(body, 5, 4.6) if bobbing else body
    return f'<g transform="translate({f(ox)} {f(oy)})">{inner}</g>'


def iso_pt(ox, oy, x, y, z):
    px, py = vx.iso(x, y, z)
    return ox + px, oy + py


def centred(cx, cy, p):
    a, b = vx.iso(*p)
    return cx - a, cy - b


# ------------------------------------------------------------------------------------ scenes

def scene_title():
    t0, t1 = SC["title"]
    out = [f'<g transform="translate(-40 0)">{canvas(WORLD_URI, w=mc.COLS * 40)}</g>',
           '<rect width="1200" height="600" fill="#1a1428" fill-opacity="0.38"/>']
    out.append(logo_text(600, 62, "LEVIMC", 15, 0.4, t1 - 0.3))
    out.append(show(ptext(600, 188, "M O N E T   E D I T I O N", 3, "#f4e8c8", anchor="middle"), 1.0, t1 - 0.3))
    splashes = ["Since 2021!", f"{k_fmt(D['org']['stars'])} stars!", "Now on Android!", "Formerly LiteLDev!",
                f"{LL_VER} is out!"]
    for i, s in enumerate(splashes):
        a, b = 1.4 + i * 2.0, 1.4 + (i + 1) * 2.0
        body = (f'<g transform="translate(900 172) rotate(-18)"><g><animateTransform attributeName="transform" '
                f'type="scale" dur="0.5s" repeatCount="indefinite" values="1;1.08;1"/>'
                f'{ptext(0, -10, s, 3, YELLOW, anchor="middle")}</g></g>')
        out.append(only(body, a, min(b, t1 - 0.3)))
    labels = ["History", "Projects", "People", "Join us"]
    for i, lab in enumerate(labels):
        y = 254 + i * 52
        btn = (f'<rect x="400" y="{y}" width="400" height="40" fill="#000000"/>'
               f'<rect x="402" y="{y + 2}" width="396" height="36" fill="#6f6f6f"/>'
               f'<rect x="402" y="{y + 2}" width="396" height="3" fill="#a8a8a8"/>'
               f'<rect x="402" y="{y + 35}" width="396" height="3" fill="#4a4a4a"/>'
               + ptext(600, y + 13, lab, 2, "#e0e0e0", anchor="middle"))
        out.append(show(btn, 2.2 + i * 0.2, t1 - 0.3, dy=10))
    hover = (f'<rect x="400" y="254" width="400" height="40" fill="none" stroke="#ffffff" stroke-width="3"/>'
             f'<rect x="402" y="256" width="396" height="36" fill="#8a8ac8" fill-opacity="0.45"/>'
             + ptext(600, 267, "History", 2, YELLOW, anchor="middle"))
    out.append(only(hover, 9.0, t1 + 0.6))
    out.append(show(ptext(16, 574, f"LeviMC {LL_VER}", 2, WHITE), 1.0, t1 - 0.3))
    out.append(show(ptext(1184, 574, "Copyright LeviMC. Not affiliated with Mojang.", 2, WHITE, anchor="end"), 1.0,
                    t1 - 0.3))
    return scene("".join(out), t0, t1, first=True)


YEARS = [
    ("2021", "Seeds", "Poppy Plains", "Poppy Field (1873)", [
        ("2021-01-27", "chat", "<ShrBox> init", WHITE),
        ("2021-01-28", "toast", "LiteLoader 0.1.0", "grass"),
        ("2021-04-10", "toast", "LiteLoader 1.0.0", "book"),
        ("2021-12-09", "toast", "2.0 pre-release", "crafting")]),
    ("2022", "Full bloom", "Tulip Farm", "Tulip Fields at Sassenheim (1886)", [
        ("2022-02-11", "toast", "LLSE: JS & Lua", "potion:#f6d040"),
        ("2022-04-22", "toast", "LiteLoader.NET", "command"),
        ("2022-07-31", "toast", "ScriptX engine", "redstone"),
        ("2022-09-01", "toast", "Documentation site", "book")]),
    ("2023", "The rebuild", "Birch River", "Poplars on the Epte (1891)", [
        ("2023-01-27", "chat", "<RimuruChan> proj: init LiteLoader branch", WHITE),
        ("2023-03-20", "toast", "LLSE learns Python", "potion:#4a8ad8"),
        ("2023-03-28", "chat", "<RimuruChan> build: migrate to xmake", WHITE),
        ("2023-12-29", "toast", "LegacyScriptEngine", "potion:#f06ae0")]),
    ("2024", "Winter work", "Snowy Taiga", "The Magpie (1869)", [
        ("2024-01-24", "toast", "Crowdin translations", "paper")]),
    ("2025", "Bridges", "Cherry Grove", "The Japanese Footbridge (1899)", [
        ("2025-01-14", "toast", "LeviStone", "eye")]),
    ("2026", "Now", "Seaside Village", "Garden at Sainte-Adresse (1867)", [
        ("2026-01-25", "toast", "Client support", "sprout")]),
]
NEW_REPO_TOASTS = {"LeviOptimize": "feather", "MoreDimensions": "eye", "LeviAntiCheat": "shield",
                   "LegacyRemoteCall": "pearl", "LeviLaunchroid": "minecart", "LeviLauncher": "minecart",
                   "LeviSchematic": "map", "levimc.org": "compass", "lipr": "chest", "docker-levilamina-server": "chest",
                   "bedrock-runtime-data": "book", "CrashLogger": "tnt", "levilamina-mod-template": "crafting",
                   "LegacyMoney": "emerald"}


def scene_history():
    t0, t1 = SC["history"]
    p0, p1 = 13.0, 79.0
    pan_w = mc.COLS * 40
    ground = mc.SURF * 40
    world = [canvas(WORLD_URI, w=pan_w)]
    for k, (yr, title, *_r) in enumerate(YEARS):
        world.append(oak_sign(k * 1200 + 860, ground, yr, title))
    world.append(bob(mob("sheep", 480, ground, 5), 3, 1.4))
    world.append(bob(mob("sheep", 1000, ground, 4), 3, 1.7, 0.3))
    world.append(f'<g>{mob("creeper", 1200 + 940, ground, 5)}<rect x="{1200 + 940}" y="{ground - 60}" width="20" '
                 f'height="60" fill="#ffffff" opacity="0"><animate attributeName="opacity" dur="0.8s" '
                 f'repeatCount="indefinite" values="0;0.6;0"/></rect></g>')
    world.append(bob(mob("fox", 3600 + 600, ground, 5), 2, 0.8))
    for i in range(3):
        world.append(f'<g><animateMotion dur="{4 + i}s" repeatCount="indefinite" '
                     f'path="M0 0c40 -30 80 30 120 0s-80 30 -120 0"/>'
                     f'{mob("bee", 4800 + 300 + i * 260, ground - 120 - i * 30, 4)}</g>')
    world.append(mob("villager", 6000 + 560, ground, 5))
    for bxp in (6000 + 900, 6000 + 1100):
        pal = {"b": "#3a5ab0", "w": "#f4f0e8", "r": "#d83a2a"}
        pole = f'<rect x="{bxp}" y="{ground - 150}" width="5" height="150" fill="#6b5130"/>'
        fa = sprite(["bbbb", "bwwb", "bbbb", "bwwb", "bbbb", "rrrr"], pal, bxp - 30, ground - 148, 7)
        fb = sprite(["bbbb", "bwwb", "bbbb", "bwwb", "bbbb", ".rrr"], pal, bxp - 31, ground - 148, 7)
        world.append(pole + f'<g>{loop_disp(0.7, 0.5)}{fa}</g><g>{loop_disp(0.7, 0.5, 0.35)}{fb}</g>')
    pan = anim_tf("translate", [(p0, "0 0"), (p1, f"{-(pan_w - W)} 0")])
    out = [f'<g>{pan}{"".join(world)}</g>']
    out.append(walker(330, ground - 16 * 5, 5, p0, p1))
    created = {}
    for date, name, _archived in D["created"]:
        if name in NEW_REPO_TOASTS:
            created.setdefault(date[:4], []).append((date, name))
    joined = sorted((d, login) for login, (d, _repo) in D["joined"].items())
    marks = D.get("release_marks", [])
    for k, (yr, title, biome, after, events) in enumerate(YEARS):
        y0 = 12.5 + 11 * k
        y1 = y0 + 11.0 if k < 5 else t1
        out.append(mc_title(yr, title, y0 + 0.2, y0 + 2.8))
        items = list(events)
        for d, name in created.get(yr, []):
            items.append((d, "toast", f"New: {name}", NEW_REPO_TOASTS[name]))
        for d, name, tag in marks:
            if d.startswith(yr):
                items.append((d, "toast", f"LeviLamina {tag}", "sprout"))
        for d, login in joined:
            if d.startswith(yr):
                items.append((d, "join", login, YELLOW))
        items.sort(key=lambda e: e[0])
        toasts = [e for e in items if e[1] == "toast"]
        if len(toasts) > 4:
            toasts = toasts[:2] + toasts[-2:]
        for j, (d, _kind, txt, ic) in enumerate(toasts):
            out.append(toast(ic, "Advancement Made!", txt, y0 + 1.2 + j * 2.4))
        chat = []
        for e in items:
            if e[1] == "chat":
                chat.append((f"[{e[0][5:]}] {e[2]}", e[3]))
            elif e[1] == "join":
                chat.append((f"{e[2]} joined the game", YELLOW))
        if k == len(YEARS) - 1:
            chat.append((f"<LeviMCBot> released LeviLamina {LL_VER}", AQUA))
        chat = chat[:8]
        if chat:
            step = min(1.2, 8.4 / max(1, len(chat)))
            out.append(chat_block(chat, y0 + 1.0, step=step, life=6.0, t_end=y1 - 0.2))
        commits = sum(D["yearly_commits"].get(r, {}).get(yr, 0) for r in ("LiteLoaderBDS", "LeviLamina"))
        n_new = sum(1 for d, _n, _a in D["created"] if d.startswith(yr))
        n_join = sum(1 for d, _l in joined if d.startswith(yr))
        rows = [("Commits", comma(commits)), ("New repos", str(n_new)), ("Joined", str(n_join))]
        out.append(scoreboard(976, 100, yr, rows, y0 + 0.8, y1 - 0.3))
        plaque("II", biome, after, y0 if k else t0 + 0.4, y1)
    return scene("".join(out), t0, t1)


def scene_lamina():
    t0, t1 = SC["lamina"]
    m0, m1 = t0 + 0.4, t0 + 6.0
    out = [sky_canvas("#8fb4dc", "#c8d8ea", "#f2e8d8", (60, 30), seed=31)]
    out.append(mc_clouds(31))
    vox = island(7, 7)
    for x, y in ((4, 1), (5, 1), (4, 2), (5, 2)):
        vox[(x, y, 1)] = "water"
    vox[(3, 3, 2)] = "crafting"
    vox[(2, 3, 2)] = "bookshelf"
    vox[(2, 4, 2)] = "bookshelf"
    tree(vox, 1, 5, 2, 3)
    vox[(5, 5, 2)] = "hay"
    tgt = (3.5, 3.5, 1.0)
    cx, cy = 330, 300
    ox, oy = centred(cx, cy, tgt)
    # 2D -> 2.5D: the camera swings from a flat side view up into isometric
    times, cams = [], []
    n = 48
    for i in range(n + 1):
        u = ease(i / n)
        times.append(m0 + (m1 - m0) * i / n)
        cams.append(dict(yaw=math.radians(45) * u, pitch=vx.ISO_PITCH * u, k=vx.K_ISO, cx=cx, cy=cy,
                         tx=tgt[0], ty=tgt[1], tz=tgt[2]))
    svg, _ = vx.baked(vox, cams, times, T, kt, tol=0.8)
    out.append(only(svg, t0 - 0.7, m1 + 0.7))
    out.append(show(iso_group(vox, ox, oy), m1 - 0.2, t1 + 0.7, fade=0.5))
    out.append(mc_title("A new dimension", "2D → 2.5D  ·  LiteLoaderBDS → LeviLamina", t0 + 0.3, m1 - 0.5, y=40, size=5))
    out.append(particles(14, (120, 160, 540, 330), ["#c8ff90", "#80ff20", "#ffffff"], 3))
    ta = m1 + 0.2
    out.append(mc_title("LeviLamina", "the mod loader for Bedrock", ta, ta + 2.4, y=34, size=5, col=GREEN))
    gx, gy = 650, 140
    tb = t0 + 14.6
    gui = gui_panel(gx, gy, 512, 196) + ptext(gx + 16, gy + 12, "Crafting", 2, GUI_TXT, shadow=False)
    out.append(show(gui, ta + 0.3, tb, dy=12))
    ingredients = [("book", "Events"), ("command", "Commands"), ("paper", "Forms"), ("chest", "Config"),
                   ("compass", "I18n"), ("clock", "Coroutines"), ("hook", "Hooks"), ("pearl", "Services"),
                   ("map", "Client UI")]
    for i, (ic, lab) in enumerate(ingredients):
        sx, sy = gx + 24 + (i % 3) * 48, gy + 38 + (i // 3) * 48
        tp = ta + 0.6 + i * 0.2
        out.append(show(slot(sx, sy), ta + 0.3, tb))
        out.append(pop(slot(sx, sy) + icon(ic, sx + 6, sy + 6, 4), sx + 22, sy + 22, tp, tb))
        out.append(show(ptext(gx + 196, gy + 38 + i * 16, lab, 2, GUI_TXT, shadow=False), tp, tb))
    arrow = sprite(["....a...", "....aa..", "aaaaaaa.", "aaaaaaaa", "aaaaaaa.", "....aa..", "....a..."],
                   {"a": "#8b8b8b"}, gx + 330, gy + 72, 5)
    out.append(show(arrow, ta + 0.3, tb))
    rx, ry = gx + 424, gy + 72
    res = slot(rx - 8, ry - 8, 60) + icon("sprout", rx, ry, 5.5) + ptext(rx + 50, ry + 32, "1", 2, WHITE, anchor="end")
    tr = ta + 2.6
    out.append(pop(res, rx + 22, ry + 22, tr, tb))
    lore = [("Mod loader for Minecraft Bedrock", GRAY), ("formerly LiteLoaderBDS · LGPL-3.0", GRAY),
            (f"★ {comma(R('LeviLamina', 'stars'))}  ·  {comma(R('LeviLamina', 'commits'))} commits", YELLOW),
            (f"{R('LeviLamina', 'releases')} releases · latest {LL_VER}", GREEN),
            (f"{R('LeviLamina', 'contributors')} contributors · server & client", GRAY)]
    tt, _w, _h = item_tooltip(gx + 60, gy + 210, "LeviLamina", lore)
    out.append(show(tt, tr + 0.3, tb, dy=8))
    code = [
        [("using namespace ", "#7a3aa8"), ("ll::event", "#2a5aa8"), (";", INK)],
        [],
        [("EventBus", "#2a5aa8"), ("::", INK), ("getInstance", "#9a5a10"), ("()", INK)],
        [("  .", INK), ("emplaceListener", "#9a5a10"), ("<", INK), ("PlayerJoinEvent", "#2a5aa8"), (">(", INK)],
        [("    [](", INK), ("PlayerJoinEvent", "#2a5aa8"), ("& ev) {", INK)],
        [("      ev.", INK), ("self", "#9a5a10"), ("().", INK), ("sendMessage", "#9a5a10"), ("(", INK),
         ("\"Welcome!\"", "#2a7a3a"), (");", INK)],
        [("    });", INK)],
    ]
    bx_, by_ = 650, 150
    tc = tb + 0.2
    out.append(show(book(bx_, by_, 510, 190) + ptext(bx_ + 496, by_ + 8, "mod.cpp", 2, "#8a7a5a", shadow=False,
                                                                                   anchor="end"), tc, t1 - 0.3, dy=12))
    for i, runs in enumerate(code):
        if not runs:
            continue
        g, lw = prun(bx_ + 14, by_ + 30 + i * 22, runs, 2)
        cid = uid("k")
        t = tc + 0.3 + i * 0.4
        DEFS.append(f'<clipPath id="{cid}"><rect x="{bx_ + 10}" y="{by_ + 26 + i * 22}" width="0" height="22">'
                    f'{anim("width", [(t, 0), (t + 0.35, lw + 8)])}</rect></clipPath>')
        out.append(show(f'<g clip-path="url(#{cid})">{g}</g>', t, t1 - 0.3, fade=0.05))
    heads = [k for k, _ in (R("LeviLamina", "top") or [])][:6]
    row = "".join(head_flat(p, 664 + i * 40, 372, 28) for i, p in enumerate(heads))
    out.append(show(tooltip(650, 356, 510, 60) + row + ptext(664 + len(heads) * 40 + 8, 380, "most active", 2, GRAY),
                    tc + 2.6, t1 - 0.3, dy=8))
    plaque("III", "The Crafting Island", "Water Lilies (1906)", t0 + 0.4, t1)
    return scene("".join(out), t0, t1)


def scene_script():
    t0, t1 = SC["script"]
    out = [sky_canvas("#a8bce0", "#d8cce4", "#f4e4d0", (190, 26), "#ffe0c0", seed=41)]
    out.append(mc_clouds(41))
    vox = island(6, 6)
    for x, y in ((3, 4), (4, 4), (4, 3)):
        vox[(x, y, 1)] = "water"
    vox[(3, 2, 2)] = "planks"
    vox[(4, 1, 2)] = "amethyst"
    tree(vox, 1, 1, 2, 2, "cherry", "birch")
    ox, oy = 300, 190
    out.append(show(iso_group(vox, ox, oy), t0, t1 + 0.7, fade=0.4))
    bxs, bys = iso_pt(ox, oy, 3.5, 2.5, 3)
    stand = sprite(["...b...", "...b...", "..bbb..", ".b.b.b.", "b..b..b", "p.....p"],
                   {"b": "#4a4a5a", "p": "#d8b040"}, bxs - 14, bys - 22, 4)
    out.append(show(bob(stand, 5, 4.6), t0 + 0.4, t1))
    out.append(particles(16, (bxs - 30, bys - 90, bxs + 30, bys - 40), ["#f06ae0", "#f6d040", "#4a8ad8", "#4caf50"], 4,
                         rise=50, size=5))
    out.append(mc_title("LegacyScriptEngine", "brew mods in any language", t0 + 0.3, t0 + 2.6, y=34, size=5,
                        col=GREEN))
    gx, gy = 640, 140
    out.append(show(gui_panel(gx, gy, 520, 132) + ptext(gx + 16, gy + 12, "Brewing", 2, GUI_TXT, shadow=False),
                    t0 + 0.8, t1 - 0.4, dy=10))
    for i, (lang, col) in enumerate(POTIONS.items()):
        sx, sy = gx + 50 + i * 122, gy + 40
        out.append(pop(slot(sx, sy) + icon(f"potion:{col}", sx + 6, sy + 6, 4), sx + 22, sy + 22, t0 + 1.2 + i * 0.3,
                       t1 - 0.4))
        out.append(show(ptext(sx + 22, sy + 56, lang, 2, GUI_TXT, shadow=False, anchor="middle"), t0 + 1.2 + i * 0.3,
                        t1 - 0.4))
    lore = [("Runs LLSE plugins on LeviLamina", GRAY), ("QuickJS · Lua · Python · Node.js", BLUE),
            ("powered by ScriptX", GRAY),
            (f"★ {R('LegacyScriptEngine', 'stars')}  ·  {k_fmt(R('LegacyScriptEngine', 'downloads'))} downloads", YELLOW),
            (f"latest {R('LegacyScriptEngine', 'latest')}", GREEN)]
    tt, _, _ = item_tooltip(gx, gy + 146, "Potion of Scripting", lore, PINK)
    out.append(show(tt, t0 + 2.8, t1 - 0.4, dy=8))
    js = [[("mc", INK), (".", INK), ("listen", "#9a5a10"), ("(", INK), ("\"onJoin\"", "#2a7a3a"), (", (pl) => {", INK)],
          [("  pl.", INK), ("tell", "#9a5a10"), ("(", INK), ("\"Hi from LSE!\"", "#2a7a3a"), (");", INK)],
          [("});", INK)]]
    bx_, by_ = 640, 440
    code = "".join(prun(bx_ + 14, by_ + 10 + i * 20, r, 2)[0] for i, r in enumerate(js))
    out.append(show(book(bx_, by_, 330, 70) + code, t0 + 4.4, t1 - 0.4, dy=10))
    legacy = (tooltip(980, 436, 190, 78) + ptext(992, 446, "Also brewing:", 2, GOLD)
              + plines(992, 470, [("LegacyMoney", GREEN), ("LegacyRemoteCall", AQUA)], 2, 20))
    out.append(show(legacy, t0 + 5.6, t1 - 0.4, dy=10))
    plaque("IV", "The Brewing Garden", "Irises in Monet's Garden (1900)", t0 + 0.4, t1)
    return scene("".join(out), t0, t1)


def scene_stone():
    t0, t1 = SC["stone"]
    out = [sky_canvas("#3a3460", "#7a6098", "#e0a8a0", (200, 60), "#f6c890", 0.62, 51, "#c8a8c8")]
    out.append(particles(26, (40, 40, 1160, 420), ["#e8e0f8", "#c8a8f0"], 5, rise=10, size=3))
    left = island(5, 5)
    for x in range(0, 4):
        left[(x, 2, 2)] = "obsidian"
        left[(x, 2, 6)] = "obsidian"
    for z in range(2, 7):
        left[(0, 2, z)] = "obsidian"
        left[(3, 2, z)] = "obsidian"
    ox, oy = 250, 300
    out.append(show(iso_group(left, ox, oy), t0, t1 + 0.7, fade=0.4))
    sheet = []
    for x in (1, 2):
        for z in (3, 4, 5):
            pts = [vx.iso(*p) for p in vx.face_pts(x, 2, z, "left")]
            d = "M" + "L".join(f"{a:.1f} {b:.1f}" for a, b in pts) + "Z"
            sheet.append(f'<path d="{d}" fill="#8a3af0"><animate attributeName="fill" dur="1.6s" '
                         f'begin="{(x + z) * 0.2:.1f}s" repeatCount="indefinite" values="#8a3af0;#c070ff;#6a2ad0;#8a3af0"/>'
                         f'</path>')
    out.append(show(f'<g transform="translate({ox} {oy})">{bob(f"<g opacity=\'0.85\'>{chr(10).join(sheet)}</g>", 5, 4.6)}</g>',
                    t0 + 0.3, t1))
    end = {}
    for x in range(4):
        for y in range(4):
            end[(x, y, 0)] = "end_stone"
    for x in (1, 2):
        for y in (1, 2):
            end[(x, y, -1)] = "end_stone"
    end[(1, 1, 1)] = "purpur"
    end[(1, 1, 2)] = "purpur"
    heads = {}
    if "wu-vincent" in HEADS:
        end[(2, 2, 1)] = "wool"
        heads[(2, 2, 1)] = ("wu-vincent", HEADS["wu-vincent"])
    ex, ey = 800, 200
    out.append(show(f'<g transform="translate({ex} {ey})">{bob(vx.iso_svg(VDEFS, end, heads=heads), 8, 5.4, 1)}</g>',
                    t0 + 0.6, t1 + 0.7, dx=40))
    beam = (f'<path d="M{ox + 40} {oy - 120} Q 560 80 {ex} {ey + 20}" fill="none" stroke="#c8a8ff" '
            f'stroke-width="4" stroke-dasharray="8 10"><animate attributeName="stroke-dashoffset" dur="0.8s" '
            f'repeatCount="indefinite" values="18;0"/></path>')
    out.append(show(beam, t0 + 1.2, t1 - 0.3))
    out.append(mc_title("LeviStone", "Endstone plugins, through the portal", t0 + 0.3, t0 + 2.6, y=34, size=5,
                        col=PINK))
    lore = [("Runs Endstone plugins on LeviLamina", GRAY), ("Python & C++ plugin APIs", BLUE),
            ("built with Endstone's founder wu-vincent", GRAY),
            (f"★ {R('LeviStone', 'stars')}  ·  {R('LeviStone', 'releases')} releases · {R('LeviStone', 'latest')}", YELLOW)]
    tt, _, _ = item_tooltip(640, 380, "LeviStone", lore, PINK)
    out.append(show(tt, t0 + 2.0, t1 - 0.4, dy=8))
    plaque("V", "Portal to the End", "Charing Cross Bridge (1901)", t0 + 0.4, t1)
    return scene("".join(out), t0, t1)


def scene_launch():
    t0, t1 = SC["launch"]
    out = [sky_canvas("#5a4a7c", "#c88a6a", "#f0b070", (120, 50), "#f06a3a", 0.64, 61, "#d8a0b0")]
    n = 10
    vox = strip(n, 1)
    for k in range(1, n):
        vox[(*scell(n, k), 1)] = "path"
    vox[(*scell(n, 0), 2)] = "obsidian"
    vox[(*scell(n, 0), 3)] = "glass"
    for z in (2, 3, 4):
        vox[(*scell(n, n), z)] = "iron"
    vox[(9, 0, 2)] = "iron"
    vox[(9, 0, 3)] = "lapis"
    ox, oy = strip_origin(n, 600, 300)
    out.append(show(iso_group(vox, ox, oy, bobbing=False), t0, t1 + 0.7, fade=0.4))
    a = iso_pt(ox, oy, *scell(n, 1), 2)
    b = iso_pt(ox, oy, *scell(n, 9), 2)
    a, b = (a[0] + vx.CX, a[1] + vx.CY), (b[0] + vx.CX, b[1] + vx.CY)
    cart = icon("minecart", -32, -46, 8) + icon("emerald", -14, -70, 4)
    out.append(show(f'<g><animateMotion dur="3s" repeatCount="indefinite" path="M{f(a[0])} {f(a[1])}L{f(b[0])} {f(b[1])}L{f(a[0])} {f(a[1])}"/>'
                    f'{cart}</g>', t0 + 0.8, t1 - 0.2))
    out.append(mc_title("Launchers", "play Bedrock anywhere", t0 + 0.3, t0 + 2.6, y=34, size=5, col=GREEN))
    p1 = iso_pt(ox, oy, 0.5, 10.5, 4)
    p2 = iso_pt(ox, oy, 10.5, 0.5, 5)
    out.append(show(nametag(p1[0], p1[1] - 60, "LeviLaunchroid", "Android"), t0 + 2.6, t1 - 0.4, dy=6))
    out.append(show(nametag(p2[0], p2[1] - 60, "LeviLauncher", "Windows · GDK"), t0 + 2.8, t1 - 0.4, dy=6))
    l1 = [("Import your own APK; play without", GRAY), ("installing; isolated versions; .so mods", GRAY),
          (f"★ {R('LeviLaunchroid', 'stars')}  ·  {k_fmt(R('LeviLaunchroid', 'downloads'))} downloads", YELLOW),
          (f"latest {R('LeviLaunchroid', 'latest')}", GREEN)]
    tt, _, _ = item_tooltip(30, 392, "LeviLaunchroid", l1)
    out.append(show(tt, t0 + 3.0, t1 - 0.4, dy=8))
    l2 = [("The launcher for the new GDK", GRAY), ("builds of Bedrock on Windows", GRAY),
          (f"★ {R('LeviLauncher', 'stars')}  ·  {k_fmt(R('LeviLauncher', 'downloads'))} downloads", YELLOW),
          (f"latest {R('LeviLauncher', 'latest')}", GREEN)]
    w2 = max(tw(x) for x, _ in l2 + [("LeviLauncher", 0)]) + 24
    tt, w2, _ = item_tooltip(1170 - w2, 392, "LeviLauncher", l2)
    out.append(show(tt, t0 + 3.4, t1 - 0.4, dy=8))
    steps = [int(DL_LAUNCH * u) for u in (0, .12, .26, .41, .57, .7, .82, .91, .97, 1)]
    bx_, by_ = 450, 120
    out.append(show(tooltip(bx_, by_, 300, 70) + icon("emerald", bx_ + 14, by_ + 18, 4)
                    + ptext(bx_ + 170, by_ + 48, "release downloads", 2, GRAY, anchor="middle"), t0 + 4.0, t1 - 0.4))
    for i, v in enumerate(steps):
        a_ = t0 + 4.2 + i * 0.14
        b_ = t0 + 4.2 + (i + 1) * 0.14 if i < len(steps) - 1 else t1 - 0.4
        out.append(only(ptext(bx_ + 170, by_ + 12, comma(v), 3, GOLD if i == len(steps) - 1 else WHITE, anchor="middle"),
                        a_, b_))
    plaque("VI", "The Rail at Sunset", "Houses of Parliament, Sunset (1903)", t0 + 0.4, t1)
    return scene("".join(out), t0, t1)


MODS = [  # repo, pedestal block, floating icon, tag
    ("LeviOptimize", "gold", "feather", "performance"),
    ("LeviAntiCheat", "iron", "shield", "anti-cheat"),
    ("MoreDimensions", "obsidian", "eye", "dimensions"),
    ("LeviSchematic", "lapis", "map", "projections"),
    ("CrashLogger", "tnt", "book", "crash reports"),
]


def scene_mods():
    t0, t1 = SC["mods"]
    out = [sky_canvas("#c8bccc", "#ecd0b0", "#f6dca8", (40, 40), "#ffd890", 0.6, 71)]
    n = 10
    vox = strip(n, 1)
    for i, m in enumerate(MODS):
        vox[(*scell(n, 1 + i * 2), 2)] = m[1]
    for k in (0, n):
        vox[(*scell(n, k), 2)] = "hay"
    vox[(*scell(n, 0), 3)] = "hay"
    ox, oy = strip_origin(n, 600, 330)
    out.append(show(iso_group(vox, ox, oy, bobbing=False), t0, t1 + 0.7, fade=0.4))
    gx_, gy_ = scell(n, 7)
    ghost = {(gx_, gy_, 3): "glass", (gx_, gy_, 4): "glass", (gx_ + 1, gy_, 3): "glass", (gx_, gy_ + 1, 3): "glass"}
    out.append(show(f'<g transform="translate({f(ox)} {f(oy)})"><g opacity="0.6">'
                    f'<animate attributeName="opacity" dur="1.4s" repeatCount="indefinite" values="0.3;0.8;0.3"/>'
                    f'{vx.iso_svg(VDEFS, ghost)}</g></g>', t0 + 3.4, t1 - 0.3))
    out.append(mc_title("Mods", "enchanted for every server", t0 + 0.3, t0 + 2.4, y=34, size=5, col=AQUA))
    for i, (name, _blk, ic, tag) in enumerate(MODS):
        cxm, cym = scell(n, 1 + i * 2)
        px, py = iso_pt(ox, oy, cxm + 0.5, cym + 0.5, 3)
        item = bob(icon(ic, px - 18, py - 66, 4.5), 6, 2.0, i * 0.3)
        glint = (f'<rect x="{f(px - 20)}" y="{f(py - 68)}" width="40" height="40" fill="#c070ff" opacity="0">'
                 f'<animate attributeName="opacity" dur="1.2s" begin="{i * 0.2:.1f}s" repeatCount="indefinite" '
                 f'values="0;0.35;0"/></rect>')
        ta = t0 + 1.0 + i * 0.4
        out.append(pop(item + glint, px, py - 46, ta, t1 - 0.3))
        stars = R(name, "stars")
        sub = f"★ {stars} · {tag}" if stars else tag
        out.append(show(nametag(px, py - 118 - (i % 2) * 46, name, sub), t0 + 2.4 + i * 0.2, t1 - 0.3, dy=6))
    dls = "  ·  ".join(f"{n.replace('Levi', '')} {k_fmt(R(n, 'downloads'))}" for n, *_ in MODS if R(n, "downloads"))
    out.append(show(tooltip(30, 456, tw(dls) + 28, 60) + ptext(44, 466, "Release downloads", 2, GOLD)
                    + ptext(44, 490, dls, 2, WHITE), t0 + 4.0, t1 - 0.4, dy=8))
    plaque("VII", "Five Pedestals", "Haystacks, End of Summer (1891)", t0 + 0.4, t1)
    return scene("".join(out), t0, t1)


TOOLS = [("levilamina-mod-template", "command", "mod template"), ("docker-levilamina-server", "iron", "Docker"),
         ("bdsdown", "lapis", "bdsdown"), ("PreLoader", "obsidian", "PreLoader"), ("PeEditor", "command", "PeEditor"),
         ("bedrock-runtime-data", "bookshelf", "runtime data"), ("lipr", "emerald", "lip registry"),
         ("bedrinth", "diamond", "bedrinth")]


def scene_tools():
    t0, t1 = SC["tools"]
    out = [sky_canvas("#9ab4d8", "#c8d4e0", "#e8dcc8", (200, 34), seed=81, clouds=0.57)]
    out.append(mc_clouds(81))
    n = 16
    vox = strip(n, 1)
    spots = [scell(n, 1 + i * 2) for i in range(len(TOOLS))]
    for (x, y), (_r, blk, _lab) in zip(spots, TOOLS):
        vox[(x, y, 2)] = blk
        vox[(x, y, 3)] = "lamp_off"
    ox, oy = strip_origin(n, 600, 340)
    out.append(show(iso_group(vox, ox, oy, bobbing=False), t0, t1 + 0.7, fade=0.4))
    for i in range(len(TOOLS) - 1):
        (x0, y0), (x1, y1) = spots[i], spots[i + 1]
        a = iso_pt(ox, oy, x0 + 1.05, y0 - 0.05, 2)
        b = iso_pt(ox, oy, x1 - 0.05, y1 + 1.05, 2)
        out.append(show(f'<path d="M{f(a[0])} {f(a[1])}L{f(b[0])} {f(b[1])}" stroke="#7a1a10" stroke-width="5"/>'
                        f'<path d="M{f(a[0])} {f(a[1])}L{f(b[0])} {f(b[1])}" stroke="#ff4a2a" stroke-width="5" opacity="0">'
                        f'<animate attributeName="opacity" dur="2.4s" begin="{i * 0.3:.1f}s" repeatCount="indefinite" '
                        f'values="0;1;0" keyTimes="0;0.15;0.4"/></path>', t0 + 0.6, t1))
    for i, (x, y) in enumerate(spots):
        lit = vx.iso_svg(VDEFS, {(x, y, 3): "lamp_on"})
        out.append(show(f'<g transform="translate({f(ox)} {f(oy)})"><g opacity="0">'
                        f'<animate attributeName="opacity" dur="2.4s" begin="{i * 0.3:.1f}s" '
                        f'repeatCount="indefinite" values="0;1;0" keyTimes="0;0.3;0.7"/>{lit}</g></g>', t0 + 1.0, t1))
    out.append(mc_title("Tooling", "the redstone behind the scenes", t0 + 0.3, t0 + 2.4, y=34, size=5, col=RED))
    for i, ((x, y), (repo, _blk, lab)) in enumerate(zip(spots, TOOLS)):
        px, py = iso_pt(ox, oy, x + 0.5, y + 0.5, 4)
        stars, dl = R(repo, "stars"), R(repo, "downloads")
        sub = f"{k_fmt(dl)} downloads" if dl else (f"★ {stars}" if stars else None)
        out.append(show(nametag(px, py - 60 - (i % 2) * 46, lab, sub), t0 + 2.4 + i * 0.15, t1 - 0.3, dy=6))
    lines = [("And more:", GOLD), ("CI on every push", WHITE), ("xmake packages", WHITE), ("header generators", WHITE),
             ("translations", WHITE), (f"{D['org']['public_repos']} public repos", AQUA),
             (f"{comma(D['org']['stars'])} stars in total", YELLOW)]
    flat = "  ·  ".join(x for x, _ in lines[1:5])
    stat = f"{D['org']['public_repos']} public repos  ·  {comma(D['org']['stars'])} stars in total"
    out.append(show(tooltip(150, 440, 900, 60) + ptext(600, 450, "And more: " + flat, 2, WHITE, anchor="middle")
                    + ptext(600, 474, stat, 2, YELLOW, anchor="middle"), t0 + 3.0, t1 - 0.4, dy=8))
    plaque("VIII", "The Redstone Line", "The Railway Bridge at Argenteuil (1873)", t0 + 0.4, t1)
    return scene("".join(out), t0, t1)


def group_members():
    def top(repo, n):
        return [k for k, _ in (R(repo, "top") or [])][:n]
    g = {
        "LOADER": top("LeviLamina", 6),
        "SCRIPTING": top("LegacyScriptEngine", 3) + top("legacy-script-engine-api", 3) + top("LeviStone", 2),
        "LAUNCHERS": top("LeviLaunchroid", 3) + top("LeviLauncher", 3),
        "MODS": top("LeviOptimize", 2) + top("MoreDimensions", 1) + top("LeviAntiCheat", 2) + top("LeviSchematic", 1),
        "TOOLING": top("levilamina-mod-template", 2) + top("docker-levilamina-server", 2) + top("bedrinth", 2)
                   + top("PeEditor", 1),
    }
    out = {}
    for k, v in g.items():
        seen = []
        for p in v:
            if p not in seen:
                seen.append(p)
        out[k] = seen[:6]
    return out


def scene_people():
    t0, t1 = SC["people"]
    out = [sky_canvas("#7fa6d4", "#b8d0ea", "#eaf0e4", (200, 20), seed=91, clouds=0.5)]
    out.append(mc_clouds(91, 30, 5))
    n = 14
    plat = strip(n, 2)
    ox, oy = strip_origin(n, 600, 390)
    out.append(show(iso_group(plat, ox, oy, bobbing=False), t0, t1 + 0.7, fade=0.4))
    groups = group_members()
    ta, tb = t0 + 0.4, t0 + 11.8
    out.append(mc_title("The people", f"{D['org']['contributors']} contributors · {D['org']['public_members']} public members",
                        ta, ta + 2.2, y=30, size=5))
    for i, (gname, people) in enumerate(groups.items()):
        x = 36 + i * 228
        body = tooltip(x, 112, 218, 34 + len(people) * 26 + 6) + ptext(x + 12, 124, gname, 2, GOLD)
        for j, p in enumerate(people):
            body += head_flat(p, x + 12, 150 + j * 26, 18) + ptext(x + 38, 153 + j * 26, p, 2, WHITE)
        out.append(show(body, ta + 1.4 + i * 0.3, tb, dy=10))
    old = [k for k, _ in (R("LiteLoaderBDS", "top") or [])]
    new = [k for k, _ in (R("LeviLamina", "top") or [])]
    both = [p for p in old if p in new]
    only_old = [p for p in old if p not in new]
    only_new = [p for p in new if p not in old]
    for p in [k for k, _ in D["people"]]:
        if len(only_new) >= 6:
            break
        if p not in old and p not in new and p in HEADS:
            only_new.append(p)
    zones = [(only_old[:6], 2), (both[:6], 7), (only_new[:6], 12)]
    hb = t0 + 12.2
    cubes = []
    for members, x0 in zones:
        for j, p in enumerate(members):
            if p in HEADS:
                cubes.append(((*scell(n, x0 - 1 + (j % 3), -1 if j < 3 else 1), 2), p, x0, j))
    cubes.sort(key=lambda c: sum(c[0]))
    for (x, y, z), p, x0, j in cubes:
        cube = vx.iso_svg(VDEFS, {(x, y, z): "wool"}, heads={(x, y, z): (p, HEADS[p])})
        tp = hb + 0.6 + j * 0.18 + x0 * 0.06
        drop = anim_tf("translate", [(tp, "0 -300"), (tp + 0.35, "0 0"), (tp + 0.45, "0 -10"), (tp + 0.55, "0 0")])
        a_, d0 = disp(tp, t1 + 0.7)
        out.append(f'<g display="{d0}">{a_}<g transform="translate({f(ox)} {f(oy)})"><g>{drop}{cube}</g></g></g>')
    for lab, sub, s0 in (("LiteLoaderBDS era", "2021–2023", 2), ("both eras", "still shipping", 7),
                         ("LeviLamina era", "2023 →", 12)):
        px, py = iso_pt(ox, oy, *scell(n, s0, -1), 3)
        out.append(show(nametag(px + vx.CX, py - 96, lab, sub, col=YELLOW), hb + 0.4, t1 - 0.3, dy=6))
    out.append(mc_title("Two generations, one community", None, hb, hb + 2.6, y=40, size=5))
    out.append(show(tooltip(150, 120, 900, 50)
                    + ptext(600, 128, f"LiteLoaderBDS {R('LiteLoaderBDS', 'contributors')} contributors · "
                                      f"LeviLamina {R('LeviLamina', 'contributors')} · {D['org']['contributors']} across "
                                      f"{D['org']['public_repos']} repos", 2, WHITE, anchor="middle")
                    + ptext(600, 150, "+ translators, testers, plugin authors and server owners", 2, AQUA,
                            anchor="middle"), hb + 2.8, t1 - 0.4, dy=8))
    plaque("IX", "Gathering of Heads", "Luncheon on the Grass (1866)", t0 + 0.4, t1)
    return scene("".join(out), t0, t1)


TOWERS = [
    ("LeviLamina", "emerald"), ("LeviLaunchroid", "lapis"), ("LeviLauncher", "diamond"),
    ("LegacyScriptEngine", "redstone"), ("LeviOptimize", "gold"), ("LeviAntiCheat", "iron"),
    ("levilamina-mod-template", "planks"), ("LeviStone", "end_stone"), ("MoreDimensions", "obsidian"),
    ("LeviSchematic", "amethyst"),
]


def scene_numbers():
    t0, t1 = SC["numbers"]
    out = [sky_canvas("#6a7ab0", "#b8a8c8", "#f0c8a0", (120, 70), "#ffc890", 0.6, 101, "#e0c0d0")]
    out.append(mc_clouds(101, 20, 3))
    vox = {}
    for x in range(15):
        for y in range(7):
            vox[(x, y, 0)] = "grass"
            if 1 <= x <= 13 and 1 <= y <= 5:
                vox[(x, y, -1)] = "dirt"
    pts = {}
    for i, (repo, blk) in enumerate(TOWERS):
        stars = R(repo, "stars") or 1
        h = max(1, round(math.log10(stars + 1) * 3.0))
        x, y = 1 + (i % 5) * 3, 1 + (i // 5) * 4
        for z in range(1, h + 1):
            vox[(x, y, z)] = blk
        pts[repo] = (x + 0.5, y + 0.5, h + 1.0)
    tgt = (7.5, 3.5, 4.0)
    times, cams = [], []
    n = 140
    for i in range(n + 1):
        u = i / n
        a = ease(clamp(u / 0.3))
        yaw = math.radians(45 - 26 * math.sin(clamp((u - 0.15) / 0.85) * math.pi * 1.2))
        pitch = vx.ISO_PITCH + (math.radians(26) - vx.ISO_PITCH) * a
        times.append(t0 + (t1 - t0) * u)
        cams.append(dict(yaw=yaw, pitch=pitch, k=vx.K_ISO * (0.56 + 0.08 * a), dist=30 + 400 * (1 - a) ** 3,
                         cx=560, cy=350, tx=tgt[0], ty=tgt[1], tz=tgt[2]))
    svg, tracks = vx.baked(vox, cams, times, T, kt, tol=0.9, extra_points=pts)
    out.append(only(svg, t0 - 0.7, t1 + 0.7))
    for i, (repo, _blk) in enumerate(TOWERS):
        tr = tracks[repo]
        keep = vx._thin([[x, y] for x, y in tr], 1.0)
        pairs = [(times[j], f"{tr[j][0]:.0f} {tr[j][1]:.0f}") for j in keep]
        name = {"levilamina-mod-template": "mod template", "LegacyScriptEngine": "LSE"}.get(repo, repo)
        tag = nametag(0, -46 - (i % 2) * 44, name, f"★ {comma(R(repo, 'stars'))}", col=YELLOW if i == 0 else WHITE)
        out.append(show(f'<g>{anim_tf("translate", pairs)}{tag}</g>', t0 + 3.2 + i * 0.2, t1 - 0.3))
    out.append(mc_title("Another dimension", "2.5D → 3D  ·  the numbers, live", t0 + 0.3, t0 + 3.0, y=34, size=5))
    totals = [("Stars", comma(D["org"]["stars"])), ("Repos", str(D["org"]["public_repos"])),
              ("Contributors", str(D["org"]["contributors"])), ("Followers", str(D["org"]["followers"])),
              ("LL commits", comma(R("LeviLamina", "commits"))), ("LL releases", str(R("LeviLamina", "releases"))),
              ("Downloads", k_fmt(sum((v.get("downloads") or 0) for v in D["repos"].values())))]
    out.append(scoreboard(966, 120, "LeviMC", totals, t0 + 4.0, t1 - 0.4))
    plaque("X", "Towers of Stars", "the Rouen Cathedral series (1892–94)", t0 + 0.4, t1)
    return scene("".join(out), t0, t1)


def finale_island():
    vox = {}
    n = mc.Noise(5)
    rad = 5.2
    for x in range(-5, 6):
        for y in range(-5, 6):
            r = math.hypot(x, y)
            if r > rad:
                continue
            hgt = 1 + (1 if n(x / 3 + 9, y / 3) > 0.62 and r < 4 else 0)
            for z in range(0, hgt + 1):
                vox[(x, y, z)] = "grass" if z == hgt else "dirt"
            depth = int((rad - r) * 0.6)
            for z in range(-depth, 0):
                vox[(x, y, z)] = "stone" if z < -1 else "dirt"
    for x, y in ((2, 2), (3, 2), (2, 3), (3, 1)):
        if (x, y, 1) in vox and (x, y, 2) not in vox:
            vox[(x, y, 1)] = "water"
    tree(vox, -3, -3, 2, 3, "cherry", "birch")
    tree(vox, 3, -3, 2, 2)
    rows = pixel_logo_rows(11)
    colors = {}
    for j, row in enumerate(rows):
        for i, c in enumerate(row):
            if c:
                p = (i - 5, 0, 13 - j)
                vox[p] = "leaves"
                colors[p] = c
    return vox, colors


def scene_finale():
    t0, t1 = SC["finale"]
    out = [sky_canvas("#3a4a8a", "#c88aa0", "#f6c070", (120, 80), "#ffb060", 0.6, 111, "#f0c8c0")]
    out.append(particles(30, (60, 40, 1140, 300), ["#fff2c0", "#ffd890"], 11, rise=30, size=4))
    vox, logo_cols = finale_island()
    face_cols = {}
    for (x, y, z), c in logo_cols.items():
        base = mc.hx(c)
        face_cols[(x, y, z, "top")] = mc.to_hex(mc.monet_light(base, 0.1))
        face_cols[(x, y, z, "left")] = mc.to_hex(mc.monet_shade(base, 0.92))
        face_cols[(x, y, z, "right")] = mc.to_hex(mc.monet_shade(base, 0.72))
    times, cams = [], []
    n = 220
    for i in range(n + 1):
        u = i / n
        a = ease(clamp(u / 0.42))
        yaw = math.radians(clamp(50 - 26 * ease(u) + 5 * math.sin(u * 6), 5, 85))
        times.append(t0 + (t1 - t0) * u)
        cams.append(dict(yaw=yaw, pitch=math.radians(62 - 40 * a), k=20 + 3 * a, dist=48 - 14 * a,
                         cx=320 + 280 * a, cy=330 + 66 * a, tx=0, ty=0, tz=4))
    svg, _ = vx.baked(vox, cams, times, T, kt, colors=face_cols, tol=0.9)
    out.append(svg)
    ta, tb = t0 + 0.6, t0 + 14.0
    rows = [("Discord", "discord.gg/v5R5P4vRZk"), ("Telegram", "t.me/LiteLoader"),
            ("QQ", "656669024 · 937236109 · 850517473"), ("Docs", "lamina.levimc.org · lse.levimc.org"),
            ("Translate", "Crowdin"), ("Website", "levimc.org")]
    bx_, by_ = 640, 110
    page = book(bx_, by_, 520, 236) + ptext(bx_ + 260, by_ + 14, "Join us", 3, INK, shadow=False, anchor="middle")
    for i, (k, v) in enumerate(rows):
        page += (ptext(bx_ + 20, by_ + 58 + i * 28, k, 2, "#7a3aa8", shadow=False)
                 + ptext(bx_ + 150, by_ + 58 + i * 28, v, 2, INK, shadow=False))
    out.append(show(page, ta, tb, dy=12))
    out.append(chat_block([("<ShrBox> see you on Discord!", WHITE), ("You joined the game", YELLOW),
                           ("<OEOTYAN> welcome :)", WHITE)], ta + 2.0, step=1.6, life=8.0, t_end=tb))
    tc = t0 + 17.0
    out.append(show('<rect width="1200" height="240" fill="url(#hushtop)"/>', tc - 0.5, T))
    out.append(logo_text(600, 30, "LEVIMC", 11, tc, T - 0.2))
    out.append(show(ptext(600, 120, "Open-source tools for the community, by the community.", 2, YELLOW,
                          anchor="middle"), tc + 1.0, T - 0.2, dy=6))
    out.append(show(ptext(600, 146, f"levimc.org  ·  live data as of {D['as_of']}, refreshed weekly", 2, AQUA,
                          anchor="middle"), tc + 1.8, T - 0.2, dy=6))
    out.append(show(ptext(600, 172, "Thanks for playing.  Not affiliated with Mojang Studios or Microsoft.", 2,
                          "#f0e8d8", anchor="middle"), tc + 2.6, T - 0.2, dy=6))
    plaque("XI", "The Floating Garden", "Water Lilies, Setting Sun (1907)", t0 + 0.4, T - 0.8)
    return scene("".join(out), t0, t1, last=True)


# ------------------------------------------------------------------------------------- main

WORLD_URI = None


def defs_block():
    glyphs = "".join(f'<path id="c{ord(ch)}" d="{pf.glyph_path(ch)}"/>' for ch in sorted(_GLYPHS))
    return (
        "<defs>"
        '<linearGradient id="ttb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5000ff" stop-opacity="0.55"/>'
        '<stop offset="1" stop-color="#28007f" stop-opacity="0.55"/></linearGradient>'
        '<linearGradient id="hushtop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#140c24" stop-opacity="0.6"/>'
        '<stop offset="1" stop-color="#140c24" stop-opacity="0"/></linearGradient>'
        '<radialGradient id="vign" cx="0.5" cy="0.5" r="0.75"><stop offset="0.7" stop-color="#1a1408" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#1a1408" stop-opacity="0.3"/></radialGradient>'
        '<clipPath id="frm"><rect width="1200" height="600"/></clipPath>'
        f"{''.join(VDEFS.items)}{glyphs}{''.join(DEFS)}</defs>"
        f"<style>.plq{{font-family:{SERIF};font-style:italic;font-size:12.5px;fill:#3a2e1e;}}</style>"
    )


def main():
    global WORLD_URI
    WORLD_URI, _props = mc.history_world()
    scenes = [scene_title(), scene_history(), scene_lamina(), scene_script(), scene_stone(), scene_launch(),
              scene_mods(), scene_tools(), scene_people(), scene_numbers(), scene_finale()]
    overlay = hud(SC["history"][0]) + plaques_svg()
    m, s = divmod(int(T), 60)
    body = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        'shape-rendering="crispEdges" role="img" aria-labelledby="ttl desc">',
        '<title id="ttl">LeviMC: Monet Edition</title>',
        f'<desc id="desc">A {m}:{s:02d} animated tour of LeviMC (formerly LiteLDev): a Minecraft world painted in '
        "Monet's style that grows from 2D to isometric to 3D. It covers the history from LiteLoaderBDS (2021) to "
        'LeviLamina, the LeviLamina mod loader, LegacyScriptEngine, LeviStone, the LeviLaunchroid and LeviLauncher '
        'launchers, mods, tooling, the people, live statistics and how to join.</desc>',
        defs_block(),
        '<g clip-path="url(#frm)">',
        f'<rect width="{W}" height="{H}" fill="#0b0a0f"/>',
        *scenes,
        f'<rect width="{W}" height="{H}" fill="url(#vign)"/>',
        overlay,
        frame(),
        "</g></svg>",
    ]
    svg = "\n".join(body)
    out = os.path.join(HERE, "..", "profile", "levimc-monet.svg")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {os.path.normpath(out)}  ({len(svg) / 1024:.0f} KiB, {m}:{s:02d})")


if __name__ == "__main__":
    main()
