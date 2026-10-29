"""Aircraft pixel art.

Jets are rasterised procedurally from a small spec (nose shape, tail height,
wing sweep, canards...) into a 40x18 glyph grid.  The grid stores *roles*
(``b`` = body, ``g`` = glass, ...), so the same silhouette can be re-skinned
with different liveries by swapping palettes.  That is how enemy aces fly the
same airframes as the player, only in hostile colours.
"""

from .pixel import PixBuf, Art, shade

GW, GH = 40, 18


# ---------------------------------------------------------------------------
# Role palettes
# ---------------------------------------------------------------------------
def _h(v):
    if isinstance(v, str):
        v = int(v.lstrip("#"), 16)
    return v


def livery(body, accent, dark=None, light=None, glass="#7fd8ff"):
    body = _h(body)
    accent = _h(accent)
    glass = _h(glass)
    dark = _h(dark) if dark is not None else shade(body, 0.62)
    light = _h(light) if light is not None else shade(body, 1.35)
    return {
        "o": 0x0B0E14,
        "d": dark,
        "b": body,
        "h": light,
        "g": glass,
        "G": shade(glass, 1.6),
        "a": accent,
        "e": shade(dark, 0.65),
        "m": shade(body, 0.8),
        "k": 0x1B2130,
    }


LIVERIES = {
    "player":  livery(0x93A1B8, 0x3FA9F5, dark=0x5B6880, light=0xCFDAEA, glass="#8EE6FF"),
    "galm":    livery(0xAFBBCD, 0xE8564A, dark=0x6E798C, light=0xE7EEF8, glass="#9FE9FF"),
    "belka":   livery(0x5A6070, 0xD23F3F, dark=0x323744, light=0x8B93A5, glass="#FF9B6B"),
    "osea":    livery(0x7C93B8, 0x5FE1B0, dark=0x495B79, light=0xC3D7F2, glass="#A8F0FF"),
    "yukt":    livery(0x6E7F63, 0xE0C060, dark=0x414F3B, light=0xA9BC9A, glass="#FFD98A"),
    "erusea":  livery(0x8A6E86, 0xE2A0E8, dark=0x53414E, light=0xC7A9C4, glass="#FFC2FF"),
    "ustio":   livery(0xA8A08C, 0xE86A3F, dark=0x6D6757, light=0xDDD6C2, glass="#9FE9FF"),
    "fcu":     livery(0xC0A878, 0x3FD0C0, dark=0x7C6A45, light=0xE9DBB8, glass="#B8FFF0"),
    "sotoa":   livery(0x4E7A5A, 0xEDEDED, dark=0x2B4633, light=0x8AB694, glass="#C8FFD8"),
    "ace":     livery(0x333A4A, 0xE03A3A, dark=0x191D27, light=0x5D6780, glass="#FF8A5C"),
}


# ---------------------------------------------------------------------------
# Shape construction
# ---------------------------------------------------------------------------
def _dome(b, cx, base_y, rx, ry, colour):
    """Upper half of an ellipse - the aircraft canopy bubble."""
    y0 = int(round(base_y - ry))
    y1 = int(round(base_y))
    for y in range(y0, y1):
        dy = (base_y - y) / ry
        if dy > 1:
            continue
        span = rx * (1 - dy * dy) ** 0.5
        b.hline(round(cx - span), round(cx + span), y, colour)


def build_grid(spec):
    b = PixBuf(GW, GH, ord("."))
    ny = spec.get("ny", 8.5)
    thick = spec.get("thick", 2.2)
    nose = spec.get("nose", 37)
    tail = spec.get("tail_x", 2)
    sweep = spec.get("sweep", 10.5)
    drop = spec.get("drop", 4.6)
    wing_root = spec.get("wing_root", 24)
    wing_chord = spec.get("wing_chord", 7)
    tip_chord = spec.get("tip_chord", 5)
    fin_h = spec.get("fin_h", 6.5)
    fin_sweep = spec.get("fin_sweep", 3.0)
    twin = spec.get("twin_fin", True)
    canard = spec.get("canard", False)
    straight = spec.get("straight_wing", False)
    hi_wing = spec.get("hi_wing", False)

    top_y = ny - thick
    bot_y = ny + thick

    def poly(pts, ch):
        b.fill_poly(pts, ord(ch))

    # ---- far wing ------------------------------------------------------
    fd = drop * 0.55
    far_le = (wing_root - 1, top_y + 0.3)
    far_te = (wing_root - 1 - wing_chord, top_y + 0.6)
    far_tip_le = (far_le[0] - sweep * 0.85, top_y - fd)
    poly([
        far_le,
        far_te,
        (far_tip_le[0] - tip_chord + 1, far_tip_le[1] + 0.4),
        far_tip_le,
    ], "d")
    b.line(far_le[0], far_le[1], far_tip_le[0], far_tip_le[1], ord("b"))

    # ---- far fin (twin tails only really) ------------------------------
    if twin:
        poly([
            (tail + fin_sweep + 1.5, top_y - 0.4),
            (tail + fin_sweep + 0.2, top_y - fin_h + 1.8),
            (tail + fin_sweep + 2.8, top_y - fin_h + 1.6),
            (tail + fin_sweep + 4.4, top_y - 0.4),
        ], "d")

    if hi_wing:
        # A-10 style engine pods riding above the fuselage
        for ex in (tail + 4, tail + 9):
            b.fill_ellipse(ex + 2, top_y - 0.4, 3.2, 2.0, ord("b"))
            b.hline(ex - 1, ex + 5, int(top_y - 0.4), ord("h"))
            b.rect(ex - 1.5, int(top_y - 1.2), 2, 2, ord("e"))
            b.px(ex - 2, int(top_y - 0.6), ord("k"))

    # ---- main wing ------------------------------------------------------
    root_le = (wing_root, bot_y - 0.7)
    root_te = (wing_root - wing_chord, bot_y - 0.3)
    if straight:
        tip_le = (wing_root + 1, bot_y + drop)
        tip_te = (tip_le[0] - tip_chord - 2, bot_y + drop + 0.3)
    else:
        tip_le = (wing_root - sweep, bot_y + drop)
        tip_te = (tip_le[0] - tip_chord, bot_y + drop + 0.3)
    poly([root_le, root_te, tip_te, tip_le], "d")
    b.line(tip_le[0], tip_le[1] - 1, root_le[0] - 1, root_le[1], ord("h"))
    b.line(tip_le[0], tip_le[1], tip_te[0], tip_te[1], ord("h"))
    # wingtip rail
    b.hline(tip_te[0] - 1, tip_le[0] + 1, tip_le[1] + 1, ord("m"))

    # ---- horizontal stabiliser -----------------------------------------
    poly([
        (tail + 9, bot_y - 1.0),
        (tail - 0.5, bot_y + 0.8),
        (tail + 0.5, bot_y + 1.8),
        (tail + 9.5, bot_y + 0.0),
    ], "b")

    # ---- canards --------------------------------------------------------
    if canard:
        poly([
            (wing_root + 8, top_y + 0.6),
            (wing_root + 4, top_y - 2.4),
            (wing_root + 5.6, top_y - 2.3),
            (wing_root + 9, top_y + 0.7),
        ], "b")
        b.line(wing_root + 8.5, top_y + 0.4, wing_root + 4.4, top_y - 2.2, ord("h"))

    # ---- fuselage -------------------------------------------------------
    upper = [
        (nose, ny - 0.5),
        (nose - 3, ny - 1.2),
        (nose - 6, ny - thick + 0.4),
        (nose - 10, top_y + 0.1),
        (nose - 15, top_y),
        (nose - 24, top_y + 0.1),
        (nose - 31, top_y + 0.8),
        (tail + 2, ny - 1.1),
        (tail, ny - 0.9),
    ]
    lower = [
        (tail, ny + 0.9),
        (tail + 2, ny + 1.1),
        (nose - 31, bot_y - 0.7),
        (nose - 24, bot_y - 0.1),
        (nose - 15, bot_y),
        (nose - 10, bot_y - 0.1),
        (nose - 6, bot_y - 0.4),
        (nose - 3, ny + 1.1),
        (nose, ny + 0.5),
    ]
    poly(upper + lower, "b")

    # spine highlight + shadowed belly
    b.hline(tail + 6, nose - 9, top_y, ord("h"))
    b.hline(tail + 4, nose - 8, bot_y, ord("d"))

    # ---- intake ---------------------------------------------------------
    if spec.get("intake", True):
        ix = spec.get("intake_x", nose - 14)
        poly([
            (ix + 3, bot_y - 0.8),
            (ix + 3.5, bot_y + 1.6),
            (ix - 2, bot_y + 1.4),
            (ix - 1.5, bot_y - 0.4),
        ], "d")
        b.hline(ix - 2, ix + 2, bot_y + 1, ord("b"))
        b.px(ix + 2, bot_y + 0.8, ord("k"))

    # ---- engine nozzles --------------------------------------------------
    if not hi_wing:
        n = spec.get("nozzles", 2)
        for i in range(n):
            y0 = int(round(ny - 1.2 + i * (thick - 0.2)))
            b.rect(tail - 1, y0, 3, 2, ord("e"))
            b.px(tail - 1, y0, ord("k"))

    # ---- near vertical fin ------------------------------------------------
    fin = [
        (tail + 1.5, top_y + 0.2),
        (tail + fin_sweep + 2.2, top_y - fin_h),
        (tail + fin_sweep + 5.0, top_y - fin_h + 0.3),
        (tail + 11.5, top_y + 0.4),
    ]
    poly(fin, "b")
    b.line(tail + fin_sweep + 2.4, top_y - fin_h + 1, tail + 10.6, top_y - 0.4, ord("h"))
    b.line(tail + fin_sweep + 4.0, top_y - fin_h + 1, tail + fin_sweep + 4.0, top_y - 1.2, ord("a"))

    # ---- canopy -----------------------------------------------------------
    cx = spec.get("canopy_x", nose - 11)
    cw = spec.get("canopy_w", 3.4)
    ch = spec.get("canopy_h", 2.5)
    _dome(b, cx, top_y + 0.6, cw, ch, ord("g"))
    b.hline(round(cx - cw * 0.5), round(cx + cw * 0.45), int(top_y - ch + 1.0), ord("G"))
    b.hline(round(cx - cw + 0.4), round(cx + cw - 0.2), int(top_y + 0.6), ord("o"))

    # ---- accent stripe ----------------------------------------------------
    sx = spec.get("stripe_x", nose - 19)
    b.vline(sx, int(top_y + 1.2), int(bot_y - 1.2), ord("a"))
    b.vline(sx + 1, int(top_y + 1.5), int(bot_y - 1.6), ord("a"))

    # ---- nose detail -------------------------------------------------------
    if spec.get("gun"):
        b.hline(nose - 1, nose + 2, int(ny), ord("k"))
    else:
        b.px(nose, int(ny), ord("k"))

    # ---- ordinance -----------------------------------------------------------
    for i in range(spec.get("missiles", 2)):
        mx = int(wing_root - sweep - 2 + i * 4)
        my = int(bot_y + drop + 0.6)
        b.hline(mx, mx + 4, my, ord("m"))
        b.px(mx - 1, my, ord("k"))

    return _outline(b)


def _outline(b):
    chars = [chr(v) for v in b.data]
    out = chars[:]
    for y in range(GH):
        for x in range(GW):
            i = y * GW + x
            if chars[i] != ".":
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < GW and 0 <= ny < GH and chars[ny * GW + nx] not in ".o":
                    out[i] = "o"
                    break
    return ["".join(out[y * GW:(y + 1) * GW]) for y in range(GH)]


# ---------------------------------------------------------------------------
# The roster
# ---------------------------------------------------------------------------
AIRCRAFT = {
    "f15c": dict(
        name="F-15C EAGLE", short="F-15C", grid=build_grid(
            dict(sweep=10, drop=4.8, wing_root=26, wing_chord=8, tip_chord=5,
                 fin_h=6.8, fin_sweep=2.4, canopy_x=26, canopy_w=3.7,
                 canopy_h=2.8, intake_x=21, stripe_x=13)),
    ),
    "f22a": dict(
        name="F-22A RAPTOR", short="F-22A", grid=build_grid(
            dict(sweep=12, drop=4.0, wing_root=25, wing_chord=8, tip_chord=4,
                 fin_h=5.2, fin_sweep=4.2, canopy_x=27, canopy_w=3.2,
                 canopy_h=2.4, intake_x=21, stripe_x=11, thick=2.1,
                 twin_fin=False)),
    ),
    "mig29": dict(
        name="MIG-29A FULCRUM", short="MIG-29", grid=build_grid(
            dict(sweep=9, drop=4.4, wing_root=24, wing_chord=7, tip_chord=5,
                 fin_h=6.2, fin_sweep=2.8, canopy_x=27, canopy_w=3.2,
                 canopy_h=2.5, intake_x=20, stripe_x=12, thick=2.3)),
    ),
    "su37": dict(
        name="SU-37 TERMINATOR", short="SU-37", grid=build_grid(
            dict(sweep=10, drop=4.6, wing_root=24, wing_chord=8, tip_chord=5,
                 fin_h=7.0, fin_sweep=2.2, canopy_x=23, canopy_w=3.3,
                 canopy_h=2.6, intake_x=20, canard=True, stripe_x=11)),
    ),
    "f14d": dict(
        name="F-14D TOMCAT", short="F-14D", grid=build_grid(
            dict(sweep=13, drop=5.0, wing_root=23, wing_chord=9, tip_chord=5,
                 fin_h=6.4, fin_sweep=3.4, canopy_x=25, canopy_w=3.9,
                 canopy_h=2.9, intake_x=18, stripe_x=9, thick=2.6)),
    ),
    "a10a": dict(
        name="A-10A WARTHOG", short="A-10A", grid=build_grid(
            dict(sweep=0, drop=3.8, wing_root=23, wing_chord=9, tip_chord=7,
                 fin_h=5.6, fin_sweep=1.0, canopy_x=29, canopy_w=2.9,
                 canopy_h=2.3, intake_x=22, straight_wing=True, hi_wing=True,
                 gun=True, stripe_x=7, thick=3.0)),
    ),
}

for _k, _v in AIRCRAFT.items():
    _v["art"] = Art(_v["grid"], LIVERIES["galm"])


def jet_art(key):
    return AIRCRAFT[key]["art"]


def jet_with_livery(key, livery_name):
    return Art(AIRCRAFT[key]["grid"], LIVERIES[livery_name])


def draw_flame(buf, x, y, t, flip=False, hot=0xFFC24A, cool=0xFF5A2A):
    """Flickering exhaust. x = the nozzle pixel; flip mirrors the plume."""
    t = int(t)
    length = 2 + (t // 3) % 3
    d = 1 if flip else -1
    for i in range(length):
        col = hot if i < length - 1 else cool
        yy = y + ((t + i) % 2)
        buf.px(x + d * i, yy, col)
        if i < length - 2:
            buf.px(x + d * i, yy + 1, cool)
    if (t // 2) % 3 == 0:
        buf.px(x + d * length, y + 1, 0xFFF2B0)


_CANOPY = {}
_NOZZLE = {}


def canopy_center(key):
    """Centre of the glass pixels - used to place the pilot's eyes."""
    if key in _CANOPY:
        return _CANOPY[key]
    grid = AIRCRAFT[key]["grid"]
    xs, ys = [], []
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch in "gG":
                xs.append(x)
                ys.append(y)
    c = (sum(xs) // len(xs), sum(ys) // len(ys)) if xs else (24, 6)
    _CANOPY[key] = c
    return c


def nozzle_x(key):
    if key in _NOZZLE:
        return _NOZZLE[key]
    grid = AIRCRAFT[key]["grid"]
    xs = [x for y, row in enumerate(grid) for x, ch in enumerate(row) if ch == "e"]
    v = min(xs) if xs else 1
    _NOZZLE[key] = v
    return v
