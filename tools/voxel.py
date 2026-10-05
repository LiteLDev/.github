"""Voxels for gen_profile.py: textured isometric blocks and a baked orbiting perspective camera.

World axes: x and y on the ground, z up. The viewer sits in the +x/+y/+z octant, so only the top (+z),
right (+x) and left (+y) faces can show, and painter's order is simply x+y+z.

Isometric faces are filled with <pattern>s whose patternTransform maps the 8x8 texture onto the face's
lattice; because every cube corner lies on that lattice, one pattern per (texture, face) serves every block
in every iso scene. The 3D camera can't use patterns (its face transforms change every frame), so there
faces are flat painterly colours whose paths are keyframed, thinned with a Douglas-Peucker-style pass.
"""
import math

import mcpaint as mc

S = 40.0                      # iso block edge (px): cx = S*cos30, cy = S/2
CX, CY = S * math.cos(math.pi / 6), S / 2
ISO_PITCH = math.atan(1 / math.sqrt(2))   # 35.26 deg: the orthographic camera that *is* our isometric
K_ISO = S / math.cos(ISO_PITCH)           # camera scale that matches CX/CY/S exactly

FACES = {  # block -> (top texture, side texture)
    "grass": ("grass_top", "grass_side"), "dirt": ("dirt", "dirt"), "stone": ("stone", "stone"),
    "sand": ("sand", "sand"), "snow": ("snow_top", "snow_side"), "water": ("water", "water"),
    "log": ("log_top", "log_side"), "birch": ("log_top", "birch_side"), "leaves": ("leaves", "leaves"),
    "cherry": ("leaves_cherry", "leaves_cherry"), "planks": ("planks", "planks"), "cobble": ("cobble", "cobble"),
    "obsidian": ("obsidian", "obsidian"), "end_stone": ("end_stone", "end_stone"),
    "crafting": ("crafting_top", "crafting_side"), "bookshelf": ("planks", "bookshelf"), "hay": ("hay_top", "hay_side"),
    "emerald": ("emerald", "emerald"), "gold": ("gold", "gold"), "diamond": ("diamond", "diamond"),
    "lapis": ("lapis", "lapis"), "redstone": ("redstone", "redstone"), "iron": ("iron", "iron"),
    "amethyst": ("amethyst", "amethyst"), "lamp_on": ("lamp_on", "lamp_on"), "lamp_off": ("lamp_off", "lamp_off"),
    "command": ("command", "command"), "tnt": ("tnt", "tnt"), "path": ("path_top", "path_side"),
    "glass": ("glass", "glass"), "wool": ("wool", "wool"), "pumpkin": ("pumpkin", "pumpkin"),
    "purpur": ("purpur", "purpur"), "mossy": ("mossy", "mossy"), "brick": ("brick", "brick"),
    "netherrack": ("netherrack", "netherrack"), "terracotta": ("terracotta", "terracotta"),
}
SHADE = {"top": 1.0, "right": 0.82, "left": 0.66}
LIGHT = {"top": 0.10, "right": 0.0, "left": 0.0}


class Defs:
    """Collects texture images and iso patterns once per document."""

    def __init__(self):
        self.items = []
        self.seen = set()

    def add(self, key, svg):
        if key not in self.seen:
            self.seen.add(key)
            self.items.append(svg)

    def image(self, tex, face):
        key = f"i_{tex}_{face}"
        uri = mc.tex_uri(tex, 0, SHADE[face], LIGHT[face])
        self.add(key, f'<image id="{key}" width="8" height="8" style="image-rendering:pixelated" href="{uri}"/>')
        return key

    def pattern(self, block, face):
        top, side = FACES[block]
        tex = top if face == "top" else side
        pid = f"p_{block}_{face}"
        if pid in self.seen:
            return pid
        img = self.image(tex, face)
        a, b, c, d = {
            "top": (CX / 8, CY / 8, -CX / 8, CY / 8),
            "right": (CX / 8, -CY / 8, 0, S / 8),
            "left": (CX / 8, CY / 8, 0, S / 8),
        }[face]
        self.add(pid, f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="8" height="8" '
                      f'patternTransform="matrix({a:.4f} {b:.4f} {c:.4f} {d:.4f} 0 0)"><use href="#{img}"/></pattern>')
        return pid

    def head_pattern(self, login, rows):
        pid = f"hp_{login.replace('-', '_')}"
        if pid in self.seen:
            return pid
        px = [mc.hx("#" + row[i * 6:i * 6 + 6]) for row in rows for i in range(8)]
        uri = mc.png_uri(px, 8, 8)
        a, b, c, d = CX / 8, CY / 8, 0, S / 8
        self.add(pid, f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="8" height="8" '
                      f'patternTransform="matrix({a:.4f} {b:.4f} {c:.4f} {d:.4f} 0 0)"><image width="8" height="8" '
                      f'style="image-rendering:pixelated" href="{uri}"/></pattern>')
        return pid


def iso(x, y, z):
    return ((x - y) * CX, (x + y) * CY - z * S)


def _poly(pts):
    return "M" + "L".join(f"{px:.1f} {py:.1f}" for px, py in pts) + "Z"


def face_pts(x, y, z, face):
    if face == "top":
        q = [(x, y, z + 1), (x + 1, y, z + 1), (x + 1, y + 1, z + 1), (x, y + 1, z + 1)]
    elif face == "right":
        q = [(x + 1, y, z + 1), (x + 1, y + 1, z + 1), (x + 1, y + 1, z), (x + 1, y, z)]
    else:
        q = [(x, y + 1, z + 1), (x + 1, y + 1, z + 1), (x + 1, y + 1, z), (x, y + 1, z)]
    return q


def visible_faces(vox):
    out = []
    for (x, y, z), b in vox.items():
        for face, nb in (("top", (x, y, z + 1)), ("right", (x + 1, y, z)), ("left", (x, y + 1, z))):
            if nb not in vox or vox[nb] in ("glass", "water") and b not in ("glass", "water"):
                out.append((x, y, z, face, b))
    out.sort(key=lambda f: (f[0] + f[1] + f[2], f[2], {"top": 2, "right": 1, "left": 0}[f[3]]))
    return out


def iso_svg(defs, vox, wrap=None, heads=None):
    """Textured isometric voxels in local coordinates (origin = iso(0,0,0)).
    wrap(key, svg) may wrap a block's faces (e.g. to animate it); heads maps (x,y,z) -> (login, rows)."""
    groups = {}
    order = []
    for x, y, z, face, b in visible_faces(vox):
        key = (x, y, z)
        if key not in groups:
            groups[key] = []
            order.append(key)
        if heads and key in heads and face == "left":
            fill = f"url(#{defs.head_pattern(*heads[key])})"
        elif heads and key in heads:
            rows = heads[key][1]
            col = mc.hx("#" + rows[0][6:12]) if face == "top" else mc.hx("#" + rows[3][42:48])
            fill = mc.to_hex(mc.tinted_shade(col, SHADE[face]))
        else:
            fill = f"url(#{defs.pattern(b, face)})"
        extra = ' fill-opacity="0.82"' if b == "water" else ""
        groups[key].append(f'<path d="{_poly([iso(*p) for p in face_pts(x, y, z, face)])}" fill="{fill}"{extra}/>')
    out = []
    for key in order:
        body = "".join(groups[key])
        out.append(wrap(key, body) if wrap else body)
    return "".join(out)


# --------------------------------------------------------------------------- the 3D camera

def project(p, cam):
    """cam: dict(yaw, pitch, k, dist, cx, cy, tx, ty, tz). Orthographic when dist is None."""
    x, y, z = p[0] - cam.get("tx", 0), p[1] - cam.get("ty", 0), p[2] - cam.get("tz", 0)
    cy_, sy_ = math.cos(cam["yaw"]), math.sin(cam["yaw"])
    xr = x * cy_ - y * sy_
    yr = x * sy_ + y * cy_
    cp, sp = math.cos(cam["pitch"]), math.sin(cam["pitch"])
    X = xr
    Y = yr * sp - z * cp
    depth = yr * cp + z * sp
    f = 1.0
    if cam.get("dist"):
        f = cam["dist"] / max(1e-3, cam["dist"] - depth)
    return cam["cx"] + cam["k"] * X * f, cam["cy"] + cam["k"] * Y * f, depth


def face_color(b, face, x, y, z):
    top, side = FACES.get(b, (b, b))
    base = mc.avg(top if face == "top" else side)
    j = ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791)) % 1000 / 1000.0 - 0.5
    c = tuple(v * (1 + j * 0.2) for v in base)
    c = mc.tinted_shade(c, {"right": 0.86, "left": 0.72}[face]) if face != "top" else mc.warm_light(c, 0.2)
    return mc.to_hex(c)


def _thin(frames, tol):
    """Indices of frames to keep so linear interpolation stays within tol for every coordinate."""
    n = len(frames)
    keep = {0, n - 1}
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b - a < 2:
            continue
        worst, wi = 0.0, -1
        fa, fb = frames[a], frames[b]
        for i in range(a + 1, b):
            u = (i - a) / (b - a)
            e = max(abs(fa[j] + (fb[j] - fa[j]) * u - frames[i][j]) for j in range(len(fa)))
            if e > worst:
                worst, wi = e, i
        if worst > tol:
            keep.add(wi)
            stack += [(a, wi), (wi, b)]
    return sorted(keep)


def baked(vox, cams, times, T, kt, colors=None, tol=0.9, extra_points=None):
    """Bake an animated camera over voxels: cams[i] at times[i]. Returns (svg, tracks) where tracks maps
    each extra 3D point name to its per-frame screen positions."""
    faces = visible_faces(vox)
    proj = []
    for cam in cams:
        proj.append({})
    out = []
    depth_avg = []
    for x, y, z, face, b in faces:
        pts = face_pts(x, y, z, face)
        fr, dsum = [], 0.0
        for cam in cams:
            row = []
            for p in pts:
                X, Y, dz = project(p, cam)
                row += [X, Y]
                dsum += dz
            fr.append(row)
        depth_avg.append(dsum / (len(cams) * 4))
        keep = _thin(fr, tol)
        col = (colors or {}).get((x, y, z, face)) or face_color(b, face, x, y, z)

        def d_of(row):
            return "M" + "L".join(f"{round(row[i])} {round(row[i + 1])}" for i in range(0, 8, 2)) + "Z"

        if len(keep) <= 1 or all(fr[k] == fr[0] for k in keep):
            out.append((depth_avg[-1], f'<path d="{d_of(fr[0])}" fill="{col}"/>'))
            continue
        kts = [times[k] for k in keep]
        if kts[0] > 0:
            kts = [0.0] + kts
            vals = [d_of(fr[0])] + [d_of(fr[k]) for k in keep]
        else:
            vals = [d_of(fr[k]) for k in keep]
        if kts[-1] < T:
            kts.append(T)
            vals.append(vals[-1])
        anim = (f'<animate attributeName="d" dur="{T:g}s" repeatCount="indefinite" keyTimes="{";".join(kt(t) for t in kts)}" '
                f'values="{";".join(vals)}"/>')
        out.append((depth_avg[-1], f'<path d="{vals[0]}" fill="{col}">{anim}</path>'))
    # painter's order: x+y+z is exact for the iso end of the move and holds for our orbits
    svg = ('<g stroke="#1e1830" stroke-opacity="0.28" stroke-width="1" stroke-linejoin="round">'
           + "".join(s for _, s in out) + "</g>")
    tracks = {}
    for name, p in (extra_points or {}).items():
        tracks[name] = [project(p, cam)[:2] for cam in cams]
    return svg, tracks
