"""The physical Ace Gotchi handheld: plastic egg shell, bezel, buttons, LED."""

import math

from . import font
from .pixel import PixBuf, mix, shade, TRANSPARENT

# --- device geometry (logical pixels; the app scales it up) -----------------
W, H = 168, 216
CX = W // 2

BODY_TOP = 6
BODY_BOTTOM = 215

SCREEN_X, SCREEN_Y = 30, 54
SCREEN_W, SCREEN_H = 108, 74

BEZEL_X, BEZEL_Y = 24, 44
BEZEL_W, BEZEL_H = 120, 96

BUTTONS = {
    "A": (48, 168, 11),
    "B": (84, 172, 12),
    "C": (120, 168, 11),
}
LABELS = {"A": "A", "B": "B", "C": "C"}

# --- palette ----------------------------------------------------------------
EDGE = 0x0E1219
PLASTIC_TOP = 0x515D73
PLASTIC_MID = 0x3B4557
PLASTIC_BOT = 0x232935
RIM_LIGHT = 0x8B9AB4
RIM_DARK = 0x171C25
BEZEL = 0x0C1016
BEZEL_EDGE = 0x03050A
GLASS = 0x05080C
ACCENT = 0x4FC3FF
ACCENT_DIM = 0x1E5A78
AMBER = 0xFFC24A
RED = 0xE8564A
GREEN = 0x6BFF9E
ENGRAVE = 0x1B2029
ENGRAVE_HI = 0x6E7C93


def egg_half(t):
    """Half-width of the egg silhouette at normalised height t (0=top)."""
    if t <= 0 or t >= 1:
        return 0
    v = math.sin(math.pi * t) ** 0.42
    v *= 0.84 + 0.16 * min(1.0, t / 0.6)
    return v * (W / 2 - 1)


def radius_corners(w, h, r):
    """Yield (inset, row_count) for each row of a rounded rectangle."""
    r = min(r, w // 2, h // 2)
    rows = []
    for y in range(h):
        if y < r:
            dy = r - y - 0.5
            inset = r - math.sqrt(max(0.0, r * r - dy * dy))
        elif y >= h - r:
            dy = y - (h - r) + 0.5
            inset = r - math.sqrt(max(0.0, r * r - dy * dy))
        else:
            inset = 0
        rows.append(int(round(inset)))
    return rows


def rounded_rect(buf, x, y, w, h, r, colour):
    for i, inset in enumerate(radius_corners(w, h, r)):
        buf.hline(x + inset, x + w - 1 - inset, y + i, colour)


def draw_body(b):
    for y in range(BODY_TOP, BODY_BOTTOM):
        t = (y - BODY_TOP) / (BODY_BOTTOM - BODY_TOP)
        half = egg_half(t)
        if half < 0.6:
            continue
        x0 = int(round(CX - half))
        x1 = int(round(CX + half))
        base = mix(PLASTIC_TOP, PLASTIC_BOT, t ** 0.85)
        span = x1 - x0 + 1
        for x in range(x0, x1 + 1):
            d = min(x - x0, x1 - x)
            c = base
            left = x < CX
            if d == 0:
                c = EDGE
            elif d == 1:
                c = mix(base, RIM_LIGHT if left else RIM_DARK, 0.62)
            elif d <= 3:
                c = mix(base, RIM_LIGHT if left else RIM_DARK, 0.26)
            # subtle plastic dither sheen on the upper left
            if d > 3 and t < 0.5 and (x + y) % 2 == 0 and left:
                c = mix(c, RIM_LIGHT, 0.08)
            b.data[y * b.w + x] = c


def draw_loop(b):
    """The little strap loop at the top of the device."""
    rounded_rect(b, CX - 12, 0, 24, 14, 6, PLASTIC_MID)
    rounded_rect(b, CX - 12, 0, 24, 13, 6, PLASTIC_TOP)
    rounded_rect(b, CX - 7, 3, 14, 6, 2, 0x0A0D12)
    b.hline(CX - 9, CX + 8, 1, RIM_LIGHT)
    b.hline(CX - 10, CX + 9, 12, 0x1A202B)
    b.px(CX - 12, 9, EDGE)
    b.px(CX + 11, 9, EDGE)


def draw_bezel(b):
    # raised plate
    rounded_rect(b, BEZEL_X - 1, BEZEL_Y - 1, BEZEL_W + 2, BEZEL_H + 2, 7, EDGE)
    rounded_rect(b, BEZEL_X, BEZEL_Y, BEZEL_W, BEZEL_H, 6, BEZEL)
    # inner bevel: dark top/left, light bottom
    for i, inset in enumerate(radius_corners(BEZEL_W, BEZEL_H, 6)):
        y = BEZEL_Y + i
        b.px(BEZEL_X + inset, y, 0x05070C)
        b.px(BEZEL_X + BEZEL_W - 1 - inset, y, 0x1B2431)
    b.hline(BEZEL_X + 6, BEZEL_X + BEZEL_W - 7, BEZEL_Y + BEZEL_H - 1, 0x232D3D)

    # screen recess
    rounded_rect(b, SCREEN_X - 2, SCREEN_Y - 2, SCREEN_W + 4, SCREEN_H + 4, 3, BEZEL_EDGE)
    rounded_rect(b, SCREEN_X - 1, SCREEN_Y - 1, SCREEN_W + 2, SCREEN_H + 2, 2, 0x1A2230)
    b.rect(SCREEN_X, SCREEN_Y, SCREEN_W, SCREEN_H, GLASS)

    # brand text on the top bezel strip
    font.draw_text_center(b, CX, BEZEL_Y + 3, "ACE GOTCHI", ACCENT, shadow=0x0A1A24)
    b.px(BEZEL_X + 20, BEZEL_Y + 6, ACCENT_DIM)
    b.px(BEZEL_X + BEZEL_W - 21, BEZEL_Y + 6, ACCENT_DIM)

    # screws
    for sx, sy in ((BEZEL_X + 5, BEZEL_Y + 5), (BEZEL_X + BEZEL_W - 6, BEZEL_Y + 5),
                   (BEZEL_X + 5, BEZEL_Y + BEZEL_H - 6), (BEZEL_X + BEZEL_W - 6, BEZEL_Y + BEZEL_H - 6)):
        b.rect(sx - 2, sy - 2, 5, 5, 0x2B3444)
        b.hline(sx - 1, sx + 1, sy, 0x10151D)
        b.vline(sx, sy - 1, sy + 1, 0x10151D)
        b.px(sx - 2, sy - 2, 0x48566C)

    # LCD glass reflection streaks
    b.hline(SCREEN_X + 3, SCREEN_X + 22, SCREEN_Y + 1, 0x12222E)
    b.hline(SCREEN_X + 6, SCREEN_X + 15, SCREEN_Y + 2, 0x0E1A24)


def draw_button(b, key, pressed=False, hot=False):
    cx, cy, r = BUTTONS[key]
    dy = 1 if pressed else 0
    # recessed well
    b.fill_ellipse(cx, cy + 1, r + 2, r + 2, 0x1A2029)
    b.stroke_ellipse(cx, cy + 1, r + 2, r + 2, EDGE)
    # cap
    cap = 0x39435A if not pressed else 0x2A3245
    if hot and not pressed:
        cap = mix(cap, ACCENT, 0.18)
    b.fill_ellipse(cx, cy + dy, r, r, cap)
    b.stroke_ellipse(cx, cy + dy, r, r, 0x151A23)
    # top-left bevel highlight
    b.fill_ellipse(cx, cy + dy - 1, r - 2, r - 2, mix(cap, RIM_LIGHT, 0.32))
    b.fill_ellipse(cx, cy + dy + 1, r - 3, r - 3, cap)
    # bottom shadow crescent
    for dx in range(-r + 2, r - 1):
        y = int(cy + dy + math.sqrt(max(0, (r - 1) ** 2 - dx * dx)) - 1)
        b.px(cx + dx, y, mix(cap, 0x000000, 0.35))
    # engraved label
    label = LABELS[key]
    lw = font.text_width(label)
    lx = cx - lw // 2
    ly = cy + dy - 3
    font.draw_text(b, lx, ly + 1, label, mix(cap, RIM_LIGHT, 0.35))
    font.draw_text(b, lx, ly, label, mix(cap, 0x000000, 0.55))


def draw_hazard(b, x, y, w, h=4):
    b.rect(x, y, w, h, 0x1A1F29)
    for i in range(0, w, 4):
        for j in range(h):
            for k in range(2):
                if 0 <= x + i + k + j < x + w:
                    b.px(x + i + k + j, y + j, AMBER if (i // 4) % 2 == 0 else 0x2A3040)
    b.hline(x, x + w - 1, y - 1, 0x0D1016)
    b.hline(x, x + w - 1, y + h, 0x0D1016)


def draw_speaker(b, x, y, cols=5, rows=4):
    for r in range(rows):
        for c in range(cols):
            px = x + c * 5
            py = y + r * 4
            b.rect(px, py, 3, 2, 0x0B0E14)
            b.hline(px, px + 2, py + 2, 0x3F4A5E)


def draw_led(b, on=False):
    x, y = 56, 194
    b.fill_ellipse(x, y, 4, 4, 0x151A22)
    b.stroke_ellipse(x, y, 4, 4, 0x090C11)
    c = GREEN if on else 0x1E4A32
    b.fill_ellipse(x, y, 3, 3, shade(c, 0.45))
    b.fill_ellipse(x, y - 1, 2, 2, c)
    if on:
        b.px(x - 1, y - 1, 0xD8FFE8)


def draw_roundel(b, x, y):
    b.fill_ellipse(x, y, 5, 5, 0x2A3242)
    b.stroke_ellipse(x, y, 5, 5, 0x0E1219)
    b.fill_ellipse(x, y, 3, 3, ACCENT_DIM)
    b.fill_ellipse(x, y, 1, 1, ACCENT)


def draw_badge(b, x, y):
    """Small squadron badge above the screen."""
    b.fill_ellipse(x, y, 8, 8, 0x333E52)
    b.stroke_ellipse(x, y, 8, 8, 0x11151C)
    b.stroke_ellipse(x, y, 6, 6, mix(0x333E52, RIM_LIGHT, 0.4))
    b.fill_ellipse(x, y, 4, 4, 0x1B2230)
    # chevron / jet glyph
    pts = [(x - 4, y + 1), (x, y - 3), (x + 4, y + 1), (x + 2, y + 1), (x, y - 1), (x - 2, y + 1)]
    b.fill_poly(pts, ACCENT)
    b.hline(x - 3, x + 3, y + 2, ACCENT_DIM)


def render(pressed=None, led_on=True, hover=None):
    """Build the full device shell as a logical-resolution PixBuf."""
    b = PixBuf(W, H, TRANSPARENT)
    draw_body(b)

    draw_bezel(b)
    draw_badge(b, CX, 31)
    font.draw_micro(b, 38, 30, "AC-01", 0x8B9AB4)
    font.draw_micro(b, 116, 30, "MK.II", 0x8B9AB4)
    draw_hazard(b, CX - 30, 143, 60, 4)
    font.draw_micro(b, CX - 45, 152, "TACTICAL AIRFRAME SYSTEM", 0x7D8CA6)

    for key in BUTTONS:
        draw_button(b, key, pressed=(pressed == key), hot=(hover == key))

    draw_speaker(b, 92, 187, rows=3)
    draw_led(b, led_on)
    draw_roundel(b, CX, 204)

    _clip_to_body(b)
    draw_loop(b)
    return b


def _clip_to_body(b):
    """Trim anything that pokes outside the shell silhouette."""
    for y in range(b.h):
        t = (y - BODY_TOP) / (BODY_BOTTOM - BODY_TOP)
        half = egg_half(t)
        if half < 0.6:
            for x in range(b.w):
                b.data[y * b.w + x] = TRANSPARENT
            continue
        x0 = int(round(CX - half))
        x1 = int(round(CX + half))
        for x in range(b.w):
            if x < x0 or x > x1:
                b.data[y * b.w + x] = TRANSPARENT


def hit(x, y):
    """Return the button key under a logical device coordinate, or None."""
    for key, (cx, cy, r) in BUTTONS.items():
        if (x - cx) ** 2 + (y - cy) ** 2 <= (r + 3) ** 2:
            return key
    return None


def in_body(x, y):
    t = (y - BODY_TOP) / (BODY_BOTTOM - BODY_TOP)
    if t < 0 or t > 1:
        return False
    return abs(x - CX) <= egg_half(t) + 1
