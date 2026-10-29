"""Low-resolution pixel drawing toolkit.

Everything in Ace Gotchi is authored on a tiny pixel canvas (the LCD is
120x80) and then blown up with nearest-neighbour scaling, which is what
gives the whole device its chunky pixel-art look.
"""

TRANSPARENT = -1


def rgb(r, g, b):
    return (r << 16) | (g << 8) | b


def _clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else v


def shade(colour, factor):
    """Multiply a colour's brightness (factor < 1 darkens, > 1 lightens)."""
    r = _clamp(int(((colour >> 16) & 0xFF) * factor))
    g = _clamp(int(((colour >> 8) & 0xFF) * factor))
    b = _clamp(int((colour & 0xFF) * factor))
    return (r << 16) | (g << 8) | b


def mix(a, b, t):
    """Linear blend between two colours, t=0 -> a, t=1 -> b."""
    ar, ag, ab = (a >> 16) & 0xFF, (a >> 8) & 0xFF, a & 0xFF
    br, bg, bb = (b >> 16) & 0xFF, (b >> 8) & 0xFF, b & 0xFF
    return (int(ar + (br - ar) * t) << 16) | (int(ag + (bg - ag) * t) << 8) | int(ab + (bb - ab) * t)


def hexs(colour):
    if colour == TRANSPARENT:
        return "#ff00ff"
    return "#%06x" % (colour & 0xFFFFFF)


class PixBuf:
    """A tiny RGB pixel buffer. Colour values are ints (0xRRGGBB);
    TRANSPARENT (-1) is used for holes and for the window cut-out."""

    __slots__ = ("w", "h", "data")

    def __init__(self, w, h, fill=TRANSPARENT):
        self.w = w
        self.h = h
        self.data = [fill] * (w * h)

    # -- primitives ---------------------------------------------------
    def px(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.data[y * self.w + x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.data[y * self.w + x]
        return TRANSPARENT

    def rect(self, x, y, w, h, c):
        x, y, w, h = int(x), int(y), int(w), int(h)
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = [c] * (x1 - x0)
        for yy in range(y0, y1):
            off = yy * self.w
            self.data[off + x0:off + x1] = row

    def box(self, x, y, w, h, c, line=None):
        """Filled rect with an optional 1px outline."""
        if line is None:
            self.rect(x, y, w, h, c)
            return
        self.rect(x, y, w, h, c)
        self.hline(x, x + w - 1, y, line)
        self.hline(x, x + w - 1, y + h - 1, line)
        self.vline(x, y, y + h - 1, line)
        self.vline(x + w - 1, y, y + h - 1, line)

    def hline(self, x0, x1, y, c):
        x0, x1, y = int(x0), int(x1), int(y)
        if 0 <= y < self.h:
            a, b = max(0, min(x0, x1)), min(self.w - 1, max(x0, x1))
            if b >= a:
                off = y * self.w
                self.data[off + a:off + b + 1] = [c] * (b - a + 1)

    def vline(self, x, y0, y1, c):
        x, y0, y1 = int(x), int(y0), int(y1)
        if 0 <= x < self.w:
            a, b = max(0, min(y0, y1)), min(self.h - 1, max(y0, y1))
            for y in range(a, b + 1):
                self.data[y * self.w + x] = c

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def fill_ellipse(self, cx, cy, rx, ry, c):
        if rx <= 0 or ry <= 0:
            return
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dy = (y - cy) / ry
            if abs(dy) > 1:
                continue
            span = rx * (1 - dy * dy) ** 0.5
            self.hline(int(round(cx - span)), int(round(cx + span)), y, c)

    def stroke_ellipse(self, cx, cy, rx, ry, c):
        steps = max(12, int((rx + ry) * 3))
        import math
        for i in range(steps):
            a = i * math.pi * 2 / steps
            self.px(int(round(cx + math.cos(a) * rx)), int(round(cy + math.sin(a) * ry)), c)

    def fill_poly(self, pts, c):
        if not pts:
            return
        ys = [p[1] for p in pts]
        y0, y1 = int(min(ys)), int(max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1a = pts[i]
                x2, y2a = pts[(i + 1) % n]
                if y1a == y2a:
                    continue
                if (y1a <= y < y2a) or (y2a <= y < y1a):
                    xs.append(x1 + (y - y1a) * (x2 - x1) / (y2a - y1a))
            if not xs:
                continue
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(round(xs[i])), int(round(xs[i + 1])), y, c)

    def poly_outline(self, pts, c):
        n = len(pts)
        for i in range(n):
            self.line(int(pts[i][0]), int(pts[i][1]), int(pts[(i + 1) % n][0]), int(pts[(i + 1) % n][1]), c)

    def dither_rect(self, x, y, w, h, ca, cb, phase=0):
        """2x2 checkerboard blend, for gradients with only two colours."""
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if ((xx + yy + phase) & 1) == 0:
                    self.px(xx, yy, ca)
                else:
                    self.px(xx, yy, cb)

    # -- compositing --------------------------------------------------
    def blit(self, other, x, y):
        for sy in range(other.h):
            ty = y + sy
            if ty < 0 or ty >= self.h:
                continue
            row = other.data[sy * other.w:(sy + 1) * other.w]
            for sx in range(other.w):
                c = row[sx]
                if c == TRANSPARENT:
                    continue
                tx = x + sx
                if 0 <= tx < self.w:
                    self.data[ty * self.w + tx] = c

    def blit_art(self, art, x, y, palette=None, flip=False, outline=None, alpha=None):
        """Draw char-art (list of equal-length strings).  '.'/' ' = transparent.
        `outline` draws a 1px dark border around every opaque pixel first."""
        pal = palette or art.palette
        lines = art.lines if hasattr(art, "lines") else art
        h = len(lines)
        w = len(lines[0]) if h else 0
        if outline is not None:
            mask = []
            for row in lines:
                mask.append([(ch not in ". ") for ch in row])
            for sy in range(h):
                for sx in range(w):
                    if mask[sy][sx]:
                        continue
                    near = False
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = sx + dx, sy + dy
                        if 0 <= nx < w and 0 <= ny < h and mask[ny][nx]:
                            near = True
                            break
                    if near:
                        tx = x + (w - 1 - sx if flip else sx)
                        ty = y + sy
                        if 0 <= tx < self.w and 0 <= ty < self.h:
                            self.data[ty * self.w + tx] = outline
        for sy, row in enumerate(lines):
            ty = y + sy
            if ty < 0 or ty >= self.h:
                continue
            for sx, ch in enumerate(row):
                if ch in ". ":
                    continue
                c = pal.get(ch)
                if c is None:
                    continue
                tx = x + (w - 1 - sx if flip else sx)
                if 0 <= tx < self.w:
                    if alpha is not None and alpha < 1.0:
                        below = self.data[ty * self.w + tx]
                        if below == TRANSPARENT:
                            continue
                        c = mix(below, c, alpha)
                    self.data[ty * self.w + tx] = c

    # -- output -------------------------------------------------------
    def to_photo_data(self, key="#ff00ff"):
        cache = {}
        rows = []
        w = self.w
        data = self.data
        for y in range(self.h):
            off = y * w
            row = data[off:off + w]
            parts = []
            for c in row:
                if c == TRANSPARENT:
                    parts.append(key)
                else:
                    s = cache.get(c)
                    if s is None:
                        s = "#%06x" % (c & 0xFFFFFF)
                        cache[c] = s
                    parts.append(s)
            rows.append("{" + " ".join(parts) + "}")
        return " ".join(rows)


def art_from(lines, palette=None):
    return Art(lines, palette or {})


class Art:
    """A character-grid sprite with a palette mapping glyphs to colours."""

    __slots__ = ("lines", "palette", "w", "h")

    def __init__(self, lines, palette):
        self.lines = [ln for ln in lines]
        self.palette = palette
        self.h = len(self.lines)
        self.w = len(self.lines[0]) if self.h else 0


def flip_lines(lines):
    return [ln[::-1] for ln in lines]
