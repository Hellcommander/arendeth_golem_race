"""Original procedural art for the Golem race mod (Pillow + numpy only).

Nothing here is copied from core_2: every sprite is drawn from primitives.
`part_icon(slot, tier)`  -> 256px RGBA drawing of one golem part (item icon + world glyph)
`figure(role)`           -> 256px RGBA drawing of a whole golem (NPC glyphs)
`pixelize(img, cell)`    -> hard-edged, palette-quantised pixel art (matches the game's 32px item style)
"""
from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

C = 256  # drawing canvas for glyph / item sprites (downsampled to the sheet cell)

# tier palettes: base / highlight / shadow / outline / glowing detail
PAL = {
    "Clay": dict(base=(184, 112, 74), hi=(226, 156, 110), lo=(122, 70, 46), dk=(58, 32, 22), glow=(255, 196, 92)),
    "Stone": dict(base=(132, 134, 142), hi=(184, 186, 194), lo=(86, 88, 98), dk=(40, 42, 52), glow=(120, 226, 255)),
    "Bronze": dict(base=(186, 130, 56), hi=(240, 196, 100), lo=(120, 76, 30), dk=(56, 34, 16), glow=(255, 232, 120)),
    "Steel": dict(base=(124, 140, 166), hi=(206, 222, 244), lo=(74, 88, 112), dk=(30, 36, 50), glow=(150, 255, 204)),
}
GREY = dict(base=(206, 206, 206), hi=(244, 244, 244), lo=(150, 150, 150), dk=(64, 64, 64), glow=(255, 255, 255))


def _blank(size=C):
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient(size, bbox, p):
    """Left-lit gradient over bbox: hi on the left/top, base in the middle, lo on the right/bottom."""
    x0, y0, x1, y1 = bbox
    xs = np.linspace(0.0, 1.0, size)[None, :]
    ys = np.linspace(0.0, 1.0, size)[:, None]
    tx = np.clip((xs * size - x0) / max(1, x1 - x0), 0, 1)
    ty = np.clip((ys * size - y0) / max(1, y1 - y0), 0, 1)
    t = np.clip(0.65 * tx + 0.35 * ty, 0, 1)  # 0 = lit corner, 1 = shaded corner
    base = np.array(p["base"], dtype=float)
    hi = np.array(p["hi"], dtype=float)
    lo = np.array(p["lo"], dtype=float)
    out = np.zeros((size, size, 3), dtype=float)
    upper = t < 0.5
    k = (t / 0.5)[..., None]
    out = np.where(upper[..., None], hi * (1 - k) + base * k, base * (1 - (t - 0.5)[..., None] / 0.5) + lo * ((t - 0.5)[..., None] / 0.5))
    alpha = np.full((size, size, 1), 255.0)
    return Image.fromarray(np.concatenate([out, alpha], axis=2).astype("uint8"), "RGBA")


OW_MUL = 1.0  # outline multiplier (pixel sprites use a thicker outline so it survives the downsample)


def shape(img, painter, p, bbox, ow=6):
    """Outline + shaded fill. `painter(draw, fill)` draws the silhouette onto a mask."""
    size = img.size[0]
    ow = int(round(ow * OW_MUL))
    mask = Image.new("L", img.size, 0)
    painter(ImageDraw.Draw(mask), 255)
    if ow > 0:
        k = ow * 2 + 1
        outline = mask.filter(ImageFilter.MaxFilter(k if k % 2 else k + 1))
        dark = Image.new("RGBA", img.size, p["dk"] + (255,))
        img.paste(dark, (0, 0), outline)
    img.paste(_gradient(size, bbox, p), (0, 0), mask)
    return mask


def box(img, rect, p, r=10, ow=6):
    x0, y0, x1, y1 = rect
    return shape(img, lambda d, f: d.rounded_rectangle(rect, radius=r, fill=f), p, rect, ow)


def poly(img, pts, p, ow=6):
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    return shape(img, lambda d, f: d.polygon(pts, fill=f), p, (min(xs), min(ys), max(xs), max(ys)), ow)


def ellipse(img, rect, p, ow=6):
    return shape(img, lambda d, f: d.ellipse(rect, fill=f), p, rect, ow)


def rivet(d, x, y, p, r=4):
    d.ellipse((x - r, y - r, x + r, y + r), fill=p["dk"])
    d.ellipse((x - r + 1.5, y - r + 1.5, x + r - 2, y + r - 2), fill=p["hi"])


def glow(img, rect, p, r=8, blur=7):
    """Glowing slit/eye with a soft halo."""
    halo = _blank(img.size[0])
    hd = ImageDraw.Draw(halo)
    x0, y0, x1, y1 = rect
    hd.rounded_rectangle((x0 - 6, y0 - 6, x1 + 6, y1 + 6), radius=r + 6, fill=p["glow"] + (150,))
    halo = halo.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(halo)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(rect, radius=r, fill=p["glow"] + (255,))
    inner = (x0 + 3, y0 + 3, x1 - 3, y1 - 3)
    if inner[2] > inner[0] and inner[3] > inner[1]:
        d.rounded_rectangle(inner, radius=max(1, r - 3), fill=(255, 255, 240, 255))


def crack(d, pts, p, w=3):
    d.line(pts, fill=p["dk"] + (255,), width=w, joint="curve")


def seed(name):
    return random.Random(sum(ord(c) * (i + 3) for i, c in enumerate(name)))


# ---------------------------------------------------------------- part icons
def head(p, tier):
    img = _blank()
    d = ImageDraw.Draw(img)
    rnd = seed("head" + tier)
    # neck stub
    box(img, (96, 190, 160, 236), p, r=8)
    if tier == "Clay":
        ellipse(img, (56, 28, 200, 204), p)
    elif tier == "Stone":
        box(img, (52, 32, 204, 204), p, r=14)
    elif tier == "Bronze":
        box(img, (54, 36, 202, 206), p, r=36)
        box(img, (112, 12, 144, 70), p, r=8)  # crest ridge
        box(img, (40, 104, 70, 190), p, r=10)  # cheek plates
        box(img, (186, 104, 216, 190), p, r=10)
    else:
        poly(img, [(60, 54), (128, 22), (196, 54), (204, 188), (170, 214), (86, 214), (52, 188)], p)
        box(img, (120, 8, 136, 60), p, r=4)
    d = ImageDraw.Draw(img)
    if tier == "Clay":
        glow(img, (86, 92, 114, 116), p, 10)
        glow(img, (142, 92, 170, 116), p, 10)
        crack(d, [(148, 44), (136, 70), (150, 92), (140, 112)], p)
        crack(d, [(88, 150), (104, 168), (98, 190)], p)
        d.arc((98, 140, 158, 184), 20, 160, fill=p["dk"] + (255,), width=5)
    elif tier == "Stone":
        d.rectangle((60, 78, 196, 94), fill=p["dk"] + (255,))  # brow ridge
        glow(img, (84, 100, 118, 122), p, 4)
        glow(img, (138, 100, 172, 122), p, 4)
        for x in (96, 114, 132, 150):
            d.rectangle((x, 156, x + 8, 188), fill=p["dk"] + (255,))
        for _ in range(6):  # lichen
            x, y = rnd.randint(64, 190), rnd.randint(40, 70)
            d.ellipse((x, y, x + rnd.randint(8, 16), y + rnd.randint(6, 10)), fill=(86, 128, 70, 255))
        crack(d, [(70, 120), (86, 150), (76, 176)], p)
    elif tier == "Bronze":
        glow(img, (82, 100, 116, 120), p, 6)
        glow(img, (140, 100, 174, 120), p, 6)
        d.rectangle((118, 126, 138, 172), fill=p["dk"] + (255,))  # nose guard
        for x in (88, 104, 152, 168):
            d.rectangle((x, 154, x + 6, 188), fill=p["dk"] + (255,))
        for (x, y) in ((70, 56), (186, 56), (56, 120), (200, 120)):
            rivet(d, x, y, p)
    else:
        d.rounded_rectangle((70, 92, 186, 124), radius=10, fill=p["dk"] + (255,))
        glow(img, (78, 98, 178, 118), p, 8)
        d.line((128, 126, 128, 196), fill=p["dk"] + (255,), width=6)
        for x in (92, 112, 144, 164):
            d.line((x, 150, x, 190), fill=p["dk"] + (255,), width=5)
        for (x, y) in ((74, 64), (182, 64), (70, 168), (186, 168)):
            rivet(d, x, y, p)
    return img


def torso(p, tier):
    img = _blank()
    rnd = seed("torso" + tier)
    shoulder_r = {"Clay": 40, "Stone": 12, "Bronze": 22, "Steel": 8}[tier]
    # arms stubs & shoulders
    box(img, (14, 52, 82, 124), p, r=shoulder_r)
    box(img, (174, 52, 242, 124), p, r=shoulder_r)
    if tier == "Clay":
        poly(img, [(54, 56), (202, 56), (190, 214), (66, 214)], p, ow=6)
    elif tier == "Stone":
        poly(img, [(50, 50), (206, 50), (194, 218), (62, 218)], p)
    elif tier == "Bronze":
        poly(img, [(56, 54), (200, 54), (186, 214), (70, 214)], p)
        box(img, (64, 196, 192, 226), p, r=10)  # belt band
    else:
        poly(img, [(46, 52), (210, 52), (198, 150), (180, 222), (76, 222), (58, 150)], p)
    d = ImageDraw.Draw(img)
    # core socket
    cx, cy = 128, 120
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=p["dk"] + (255,))
    glow(img, (cx - 20, cy - 20, cx + 20, cy + 20), p, 20, 9)
    d = ImageDraw.Draw(img)
    if tier == "Clay":
        crack(d, [(84, 70), (100, 96), (90, 120), (102, 150)], p)
        crack(d, [(170, 180), (156, 200), (166, 214)], p)
        d.line((78, 186, 178, 186), fill=p["dk"] + (255,), width=4)
    elif tier == "Stone":
        d.line((72, 176, 184, 176), fill=p["dk"] + (255,), width=5)
        d.line((84, 198, 172, 198), fill=p["dk"] + (255,), width=5)
        for _ in range(7):
            x, y = rnd.randint(60, 180), rnd.randint(190, 214)
            d.ellipse((x, y, x + rnd.randint(8, 16), y + rnd.randint(5, 9)), fill=(86, 128, 70, 255))
        crack(d, [(166, 62), (154, 84), (166, 100)], p)
    elif tier == "Bronze":
        for x in (76, 96, 160, 180):
            d.line((x, 154, x, 192), fill=p["dk"] + (255,), width=4)
        for (x, y) in ((70, 68), (186, 68), (30, 70), (226, 70), (84, 212), (172, 212)):
            rivet(d, x, y, p)
    else:
        d.line((128, 160, 128, 222), fill=p["dk"] + (255,), width=5)
        d.line((74, 176, 182, 176), fill=p["dk"] + (255,), width=5)
        for (x, y) in ((64, 70), (192, 70), (34, 70), (222, 70), (90, 206), (166, 206)):
            rivet(d, x, y, p)
    return img


def legs(p, tier):
    img = _blank()
    foot_r = {"Clay": 22, "Stone": 8, "Bronze": 14, "Steel": 6}[tier]
    box(img, (52, 18, 122, 206), p, r=16 if tier != "Steel" else 6)
    box(img, (134, 18, 204, 206), p, r=16 if tier != "Steel" else 6)
    box(img, (40, 192, 126, 240), p, r=foot_r)
    box(img, (130, 192, 216, 240), p, r=foot_r)
    d = ImageDraw.Draw(img)
    # knee blocks
    for x0 in (46, 128):
        box(img, (x0, 96, x0 + 82, 134), p, r=10 if tier != "Clay" else 18)
    d = ImageDraw.Draw(img)
    if tier == "Clay":
        crack(d, [(80, 28), (92, 60), (82, 84)], p)
        crack(d, [(176, 150), (166, 176), (178, 192)], p)
    elif tier == "Stone":
        for y in (58, 160):
            d.line((58, y, 118, y), fill=p["dk"] + (255,), width=4)
            d.line((140, y, 198, y), fill=p["dk"] + (255,), width=4)
    elif tier == "Bronze":
        for (x, y) in ((64, 112), (108, 112), (146, 112), (190, 112), (70, 216), (116, 216), (144, 216), (198, 216)):
            rivet(d, x, y, p, 3)
        d.line((87, 30, 87, 90), fill=p["dk"] + (255,), width=4)
        d.line((169, 30, 169, 90), fill=p["dk"] + (255,), width=4)
    else:
        for (x, y) in ((64, 112), (108, 112), (146, 112), (190, 112)):
            rivet(d, x, y, p, 3)
        d.line((87, 150, 87, 200), fill=p["dk"] + (255,), width=4)
        d.line((169, 150, 169, 200), fill=p["dk"] + (255,), width=4)
        d.rectangle((54, 220, 122, 232), fill=p["lo"] + (255,))
        d.rectangle((136, 220, 204, 232), fill=p["lo"] + (255,))
    return img


def _forearm(img, p, tier):
    box(img, (96, 130, 160, 250), p, r=18 if tier != "Steel" else 6)
    d = ImageDraw.Draw(img)
    d.line((96, 176, 160, 176), fill=p["dk"] + (255,), width=5)
    d.line((96, 206, 160, 206), fill=p["dk"] + (255,), width=5)
    return d


def hand_weapon(p, tier):
    img = _blank()
    if tier == "Clay":  # fist
        _forearm(img, p, tier)
        box(img, (66, 34, 190, 150), p, r=34)
        d = ImageDraw.Draw(img)
        for x in (104, 128, 152):
            d.line((x, 40, x, 82), fill=p["dk"] + (255,), width=5)
        d.arc((84, 80, 172, 134), 0, 180, fill=p["dk"] + (255,), width=5)
        crack(d, [(168, 112), (156, 130), (166, 146)], p)
    elif tier == "Stone":  # maul
        _forearm(img, p, tier)
        box(img, (46, 20, 210, 120), p, r=10)
        d = ImageDraw.Draw(img)
        d.line((46, 70, 210, 70), fill=p["dk"] + (255,), width=5)
        crack(d, [(150, 26), (138, 56), (152, 84)], p)
        d.rectangle((108, 118, 148, 136), fill=p["dk"] + (255,))
    elif tier == "Bronze":  # cleaver
        _forearm(img, p, tier)
        poly(img, [(96, 140), (96, 30), (214, 20), (222, 108), (160, 140)], p)
        d = ImageDraw.Draw(img)
        d.line((110, 38, 206, 30), fill=p["hi"] + (255,), width=6)
        for (x, y) in ((112, 128), (150, 132)):
            rivet(d, x, y, p)
        d.line((120, 90, 200, 84), fill=p["dk"] + (255,), width=4)
    else:  # steel hammer
        _forearm(img, p, tier)
        box(img, (38, 12, 218, 112), p, r=6)
        d = ImageDraw.Draw(img)
        d.rectangle((38, 12, 80, 112), fill=p["lo"] + (255,))
        d.rectangle((176, 12, 218, 112), fill=p["lo"] + (255,))
        glow(img, (96, 46, 160, 78), p, 8)
        d = ImageDraw.Draw(img)
        for (x, y) in ((58, 30), (58, 94), (198, 30), (198, 94)):
            rivet(d, x, y, p)
        d.rectangle((108, 112, 148, 136), fill=p["dk"] + (255,))
    return img


def hand_guard(p, tier):
    img = _blank()
    _forearm(img, p, tier)
    if tier == "Clay":
        ellipse(img, (40, 24, 216, 188), p)
        d = ImageDraw.Draw(img)
        ellipse(img, (96, 80, 160, 140), p, ow=5)
        crack(d, [(70, 60), (86, 92), (74, 120)], p)
    elif tier == "Stone":
        box(img, (36, 14, 220, 190), p, r=14)
        d = ImageDraw.Draw(img)
        d.line((128, 20, 128, 184), fill=p["dk"] + (255,), width=5)
        d.line((42, 100, 214, 100), fill=p["dk"] + (255,), width=5)
        box(img, (98, 74, 158, 126), p, r=8, ow=5)
    elif tier == "Bronze":
        ellipse(img, (36, 20, 220, 196), p)
        d = ImageDraw.Draw(img)
        d.ellipse((58, 42, 198, 174), outline=p["dk"] + (255,), width=5)
        ellipse(img, (100, 82, 156, 134), p, ow=5)
        d = ImageDraw.Draw(img)
        for a in range(0, 360, 45):
            x = 128 + 78 * math.cos(math.radians(a))
            y = 108 + 68 * math.sin(math.radians(a))
            rivet(d, x, y, p, 4)
    else:
        poly(img, [(40, 18), (216, 18), (216, 120), (128, 200), (40, 120)], p)
        d = ImageDraw.Draw(img)
        d.line((128, 24, 128, 190), fill=p["dk"] + (255,), width=5)
        d.line((46, 78, 210, 78), fill=p["dk"] + (255,), width=5)
        glow(img, (104, 56, 152, 100), p, 18)
        d = ImageDraw.Draw(img)
        for (x, y) in ((58, 36), (198, 36), (58, 100), (198, 100)):
            rivet(d, x, y, p)
    return img


def putty(p=None):
    """Repair putty: a clay pot with a glowing seal."""
    p = PAL["Clay"]
    img = _blank()
    ellipse(img, (48, 90, 208, 236), p)
    box(img, (76, 54, 180, 112), p, r=14)
    d = ImageDraw.Draw(img)
    d.ellipse((72, 40, 184, 78), fill=p["dk"] + (255,))
    d.ellipse((82, 46, 174, 72), fill=(122, 130, 96, 255))
    d.ellipse((96, 50, 158, 66), fill=(160, 170, 120, 255))
    glow(img, (104, 146, 152, 190), PAL["Steel"], 14)
    d = ImageDraw.Draw(img)
    crack(d, [(74, 150), (86, 176), (76, 204)], p)
    return img


def cradle():
    """Assembly Cradle: a stone slab with iron clamps and a glowing socket."""
    p, m = PAL["Stone"], PAL["Steel"]
    img = _blank()
    box(img, (20, 150, 236, 232), p, r=12)
    box(img, (44, 120, 212, 168), p, r=10)
    box(img, (34, 40, 74, 150), m, r=8)
    box(img, (182, 40, 222, 150), m, r=8)
    box(img, (34, 40, 222, 66), m, r=8)
    d = ImageDraw.Draw(img)
    d.ellipse((92, 78, 164, 150), fill=p["dk"] + (255,))
    glow(img, (104, 90, 152, 138), PAL["Clay"], 24, 9)
    d = ImageDraw.Draw(img)
    for x in (60, 128, 196):
        rivet(d, x, 200, p)
    crack(d, [(80, 176), (92, 196), (84, 216)], p)
    return img


def book():
    """Book of Golemcraft: a clay-bound primer with a glowing heart socket on the cover."""
    p = PAL["Clay"]
    img = _blank()
    box(img, (64, 22, 214, 236), dict(base=(226, 214, 176), hi=(250, 244, 220), lo=(170, 156, 120), dk=p["dk"], glow=p["glow"]), r=8)  # page block
    box(img, (44, 26, 196, 232), p, r=12)  # cover
    box(img, (44, 26, 76, 232), dict(base=p["lo"], hi=p["base"], lo=p["dk"], dk=p["dk"], glow=p["glow"]), r=10)  # spine
    d = ImageDraw.Draw(img)
    d.ellipse((98, 84, 168, 154), fill=PAL["Stone"]["dk"] + (255,))
    glow(img, (110, 96, 156, 142), p, 22, 9)
    d = ImageDraw.Draw(img)
    for y in (52, 204):
        d.line((92, y, 176, y), fill=p["dk"] + (255,), width=6)
    return img


PART_DRAW = {"head": head, "torso": torso, "legs": legs, "hand": hand_weapon, "guard": hand_guard}


def part_icon(slot, tier):
    return PART_DRAW[slot](PAL[tier], tier)


# ---------------------------------------------------------------- full figures (NPC glyphs)
def figure(role):
    """Whole golem, front view, for NPC / player glyphs."""
    tier = {"adult": "Clay", "recruit": "Stone", "leader": "Steel", "adventurer": "Bronze", "rebel": "Stone"}[role]
    p = PAL[tier]
    img = _blank()
    # legs
    box(img, (78, 150, 120, 240), p, r=10)
    box(img, (136, 150, 178, 240), p, r=10)
    box(img, (70, 224, 124, 248), p, r=8)
    box(img, (132, 224, 186, 248), p, r=8)
    # arms
    box(img, (32, 84, 70, 190), p, r=14)
    box(img, (186, 84, 224, 190), p, r=14)
    box(img, (28, 176, 74, 214), p, r=16)
    box(img, (182, 176, 228, 214), p, r=16)
    # torso
    poly(img, [(66, 82), (190, 82), (180, 168), (76, 168)], p)
    # head
    box(img, (92, 22, 164, 90), p, r=18 if tier != "Steel" else 8)
    d = ImageDraw.Draw(img)
    glow(img, (104, 48, 124, 62), p, 5, 5)
    glow(img, (134, 48, 154, 62), p, 5, 5)
    d = ImageDraw.Draw(img)
    # core
    d.ellipse((108, 100, 148, 140), fill=p["dk"] + (255,))
    glow(img, (116, 108, 140, 132), p, 12, 6)
    d = ImageDraw.Draw(img)
    d.line((76, 154, 180, 154), fill=p["dk"] + (255,), width=4)
    if role == "recruit":
        poly(img, [(12, 86), (60, 86), (60, 150), (36, 176), (12, 150)], PAL["Bronze"], ow=5)
    elif role == "leader":
        box(img, (120, 4, 136, 40), p, r=3)
        poly(img, [(60, 84), (196, 84), (214, 150), (42, 150)], dict(base=(150, 40, 48), hi=(204, 76, 84), lo=(96, 22, 30), dk=(44, 10, 14), glow=p["glow"]), ow=4)
        poly(img, [(66, 82), (190, 82), (180, 168), (76, 168)], p)
        d = ImageDraw.Draw(img)
        d.ellipse((108, 100, 148, 140), fill=p["dk"] + (255,))
        glow(img, (116, 108, 140, 132), p, 12, 6)
    elif role == "adventurer":
        box(img, (176, 96, 232, 166), dict(base=(120, 82, 48), hi=(170, 124, 76), lo=(76, 50, 28), dk=(36, 22, 12), glow=p["glow"]), r=10, ow=5)
        d = ImageDraw.Draw(img)
        d.line((180, 120, 228, 120), fill=(36, 22, 12, 255), width=4)
    elif role == "rebel":
        d = ImageDraw.Draw(img)
        d.rectangle((68, 112, 188, 128), fill=(168, 38, 38, 255))
        crack(d, [(120, 30), (128, 52), (118, 76)], p)
    return img




# ---------------------------------------------------------------- pixel-art conversion
EXTRA_COLORS = [(255, 255, 240), (86, 128, 70), (120, 82, 48), (168, 38, 38), (150, 40, 48), (204, 76, 84), (160, 170, 120), (122, 130, 96)]


def tier_palette(*tiers):
    cols = []
    for t in tiers:
        p = PAL[t]
        cols += [p["dk"], p["lo"], p["base"], p["hi"], p["glow"]]
    return cols + EXTRA_COLORS


def pixelize(img, cell, palette, outline=None, opaque=False):
    """Area-downsample a 256px drawing to `cell` px, hard alpha, snap to a small palette, dark pixel outline."""
    arr = np.asarray(img.convert("RGBA"), dtype=float)
    n = arr.shape[0] // cell
    a = arr[..., 3:4] / 255.0
    pm = arr[..., :3] * a
    blocks = lambda x: x.reshape(cell, n, cell, n, -1).mean(axis=(1, 3))
    pa = blocks(a)[..., 0]
    prgb = blocks(pm)
    rgb = prgb / np.maximum(pa[..., None], 1e-4)
    solid = pa > (0.0 if opaque else 0.42)
    pal = np.array(palette, dtype=float)
    d = ((rgb[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(axis=3)
    snapped = pal[d.argmin(axis=2)]
    out = np.zeros((cell, cell, 4), dtype=np.uint8)
    out[..., :3] = snapped.astype(np.uint8)
    out[..., 3] = np.where(solid, 255, 0)
    if outline is not None and not opaque:
        pad = np.pad(solid, 1)
        edge = solid & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        out[edge, :3] = np.array(outline, dtype=np.uint8)
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------- icon emblems (ability / passive / skill tiles)
def _gear(img, cx, cy, r_out, r_in, teeth, p, hole=0.35):
    pts = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a0 = i * step
        for frac, rad in ((0.0, r_in), (0.18, r_in), (0.28, r_out), (0.62, r_out), (0.72, r_in)):
            a = a0 + frac * step
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    poly(img, pts, p, ow=8)
    d = ImageDraw.Draw(img)
    hr = r_in * hole * 2
    d.ellipse((cx - hr, cy - hr, cx + hr, cy + hr), fill=p["dk"] + (255,))


def subject(kind):
    img = _blank()
    S, G, B, K = PAL["Stone"], PAL["Steel"], PAL["Bronze"], PAL["Clay"]
    if kind == "core":  # heart socket
        ellipse(img, (40, 40, 216, 216), S)
        d = ImageDraw.Draw(img)
        d.ellipse((74, 74, 182, 182), fill=S["dk"] + (255,))
        glow(img, (92, 92, 164, 164), K, 36, 12)
    elif kind == "block":
        box(img, (36, 70, 220, 206), S, r=10)
        d = ImageDraw.Draw(img)
        d.line((36, 138, 220, 138), fill=S["dk"] + (255,), width=8)
        d.line((128, 70, 128, 138), fill=S["dk"] + (255,), width=8)
        d.line((84, 138, 84, 206), fill=S["dk"] + (255,), width=8)
        d.line((172, 138, 172, 206), fill=S["dk"] + (255,), width=8)
        box(img, (60, 36, 196, 84), S, r=8)
    elif kind == "gear":
        _gear(img, 128, 128, 104, 78, 8, G)
        glow(img, (104, 104, 152, 152), G, 24, 8)
    elif kind == "gearplus":
        _gear(img, 128, 128, 104, 78, 8, B)
        d = ImageDraw.Draw(img)
        d.rectangle((108, 76, 148, 180), fill=B["dk"] + (255,))
        d.rectangle((76, 108, 180, 148), fill=B["dk"] + (255,))
        d.rectangle((116, 84, 140, 172), fill=(255, 255, 240, 255))
        d.rectangle((84, 116, 172, 140), fill=(255, 255, 240, 255))
    elif kind == "shield":
        poly(img, [(44, 40), (212, 40), (212, 130), (128, 222), (44, 130)], G, ow=10)
        d = ImageDraw.Draw(img)
        d.line((128, 48, 128, 210), fill=G["dk"] + (255,), width=8)
        d.line((52, 100, 204, 100), fill=G["dk"] + (255,), width=8)
        glow(img, (100, 76, 156, 124), G, 20, 8)
    elif kind == "bolt":
        poly(img, [(150, 20), (70, 140), (118, 140), (92, 236), (190, 104), (138, 104)], B, ow=8)
    elif kind == "wrench":
        box(img, (110, 70, 146, 230), G, r=16)
        poly(img, [(70, 30), (186, 30), (186, 80), (160, 110), (96, 110), (70, 80)], G, ow=8)
        d = ImageDraw.Draw(img)
        d.rectangle((112, 24, 144, 66), fill=G["dk"] + (255,))
        d.rectangle((108, 150, 148, 180), fill=(255, 255, 240, 255))
        d.rectangle((120, 138, 136, 192), fill=(255, 255, 240, 255))
    elif kind == "heartcore":
        box(img, (50, 40, 206, 216), S, r=20)
        d = ImageDraw.Draw(img)
        d.ellipse((84, 78, 172, 166), fill=S["dk"] + (255,))
        glow(img, (100, 94, 156, 150), K, 28, 10)
        d = ImageDraw.Draw(img)
        for (x, y) in ((70, 60), (186, 60), (70, 196), (186, 196)):
            rivet(d, x, y, S)
    elif kind == "star":
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = 106 if i % 2 == 0 else 46
            pts.append((128 + rad * math.cos(ang), 132 + rad * math.sin(ang)))
        poly(img, pts, B, ow=8)
        glow(img, (108, 108, 148, 148), B, 18, 8)
    return img


BG_TINT = {"core": (70, 38, 22), "block": (36, 40, 52), "gear": (30, 40, 56), "gearplus": (60, 44, 22), "shield": (30, 44, 64),
           "bolt": (60, 46, 20), "wrench": (30, 46, 50), "heartcore": (66, 34, 22), "star": (58, 46, 20), "putty": (40, 56, 40)}


def emblem(kind, cell=32):
    """Full-bleed icon tile: dark vignette, thin frame, one bold subject."""
    s = 256
    yy, xx = np.mgrid[0:s, 0:s]
    dist = np.sqrt((xx - s / 2) ** 2 + (yy - s / 2) ** 2) / (s * 0.72)
    tint = np.array(BG_TINT[kind], dtype=float)
    bg = (tint[None, None, :] * np.clip(1.15 - dist, 0.12, 1.0)[..., None]).astype("uint8")
    img = Image.fromarray(np.concatenate([bg, np.full((s, s, 1), 255, "uint8")], axis=2), "RGBA")
    sub = putty() if kind == "putty" else subject(kind)
    sub = sub.resize((200, 200), Image.LANCZOS)
    img.alpha_composite(sub, (28, 30))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, s - 1, s - 1), outline=(18, 16, 18, 255), width=12)
    d.rectangle((12, 12, s - 13, s - 13), outline=(120, 100, 62, 255), width=4)
    pal = tier_palette("Clay", "Stone", "Bronze", "Steel") + [tuple(int(v) for v in np.array(t) * f) for t in BG_TINT.values() for f in (0.2, 0.5, 1.0)] + [(18, 16, 18), (120, 100, 62)]
    return pixelize(img, cell, pal, opaque=True)


def skill_banner(cell=64):
    s = 256
    yy, xx = np.mgrid[0:s, 0:s]
    dist = np.sqrt((xx - s / 2) ** 2 + (yy - s / 2) ** 2) / (s * 0.7)
    bg = (np.array((64, 44, 30), dtype=float)[None, None, :] * np.clip(1.2 - dist, 0.1, 1.0)[..., None]).astype("uint8")
    img = Image.fromarray(np.concatenate([bg, np.full((s, s, 1), 255, "uint8")], axis=2), "RGBA")
    old = globals()["OW_MUL"]
    globals()["OW_MUL"] = 1.0
    fig = figure("leader").resize((220, 220), Image.LANCZOS)
    globals()["OW_MUL"] = old
    img.alpha_composite(fig, (18, 20))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, s - 1, s - 1), outline=(18, 16, 18, 255), width=10)
    d.rectangle((10, 10, s - 11, s - 11), outline=(120, 100, 62, 255), width=3)
    return pixelize(img, cell, tier_palette("Clay", "Stone", "Bronze", "Steel") + [(64, 44, 30), (40, 28, 20), (18, 16, 18), (120, 100, 62)], opaque=True)
