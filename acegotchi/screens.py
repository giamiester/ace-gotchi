"""Every screen of the LCD: home, menu, briefing, hangar, fleet, results."""

import math
import random
import time

from . import factions, font, sprites
from .pixel import PixBuf, mix, shade
from .state import (FLEET, TACTICS, UPGRADES, level_for_xp, rank_for,
                    xp_into_level, CHATTER)
from . import dogfight

W, H = 108, 74

BG = 0x08111C
PANEL = 0x0E1B2A
LINE = 0x1E3550
TEXT = 0x9FD8F0
DIM = 0x4E7590
ACCENT = 0x7FE3FF
GOLD = 0xFFC24A
GREEN = 0x6BFF9E
RED = 0xE8564A
PINK = 0xFF8FB0


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
ICONS = {
    "feed": ("...#...", "..###..", ".#####.", "#######", ".#####.", "..###..", "...#..."),
    "rest": ("..###..", ".##....", "##.....", "##.....", "##.....", ".##....", "..###.."),
    "polish": ("...#...", "...#...", "#..#..#", ".#####.", "#..#..#", "...#...", "...#..."),
    "train": (".#####.", "#.....#", "#..#..#", "#.###.#", "#..#..#", "#.....#", ".#####."),
    "rearm": (".#...#.", ".#...#.", "..#.#..", "...#...", "#######", "#.....#", "#######"),
    "repair": ("...#...", ".#####.", ".#####.", "#######", ".#####.", ".#####.", "...#..."),
    "sortie": ("...#...", "..###..", ".#####.", "##.#.##", "...#...", "..###..", ".#####."),
    "hangar": ("..#.#..", ".#####.", "###.###", ".#...#.", "###.###", ".#####.", "..#.#.."),
    "fleet": (".#...#.", "###.###", ".#...#.", ".......", ".#...#.", "###.###", ".#...#."),
    "identity": ("#######", "#.....#", "#.###.#", "#.###.#", "#.###.#", "#.....#", "#######"),
    "exit": ("#.....#", ".#...#.", "..#.#..", "...#...", "..#.#..", ".#...#.", "#.....#"),
}


def icon(buf, x, y, name, colour):
    art = ICONS.get(name)
    if art:
        buf.blit_art(art, x, y, {"#": colour})


def header(buf, left, right="", right_colour=DIM):
    buf.rect(0, 0, W, 9, PANEL)
    buf.hline(0, W - 1, 8, LINE)
    font.draw_micro(buf, 2, 2, left, ACCENT)
    if right:
        font.draw_micro(buf, W - 2 - font.micro_width(right), 2, right, right_colour)


def footer(buf, text, colour=DIM):
    buf.rect(0, H - 9, W, 9, PANEL)
    buf.hline(0, W - 1, H - 9, LINE)
    font.draw_micro(buf, 2, H - 7, text, colour)


def panel(buf, x, y, w, h, fill=PANEL, line=LINE):
    buf.rect(x, y, w, h, fill)
    buf.box(x, y, w, h, fill, line)
    buf.hline(x + 1, x + w - 2, y, mix(line, 0xFFFFFF, 0.25))


def bar(buf, x, y, w, h, frac, colour, back=0x122234, segments=0):
    buf.rect(x, y, w, h, back)
    frac = max(0.0, min(1.0, frac))
    fill = int(round(w * frac))
    if fill > 0:
        buf.rect(x, y, fill, h, colour)
        buf.hline(x, x + fill - 1, y, mix(colour, 0xFFFFFF, 0.35))
    if segments:
        for i in range(1, segments):
            buf.vline(x + int(w * i / segments), y, y + h - 1, back)


def wrap_micro(text, width):
    words = text.replace("\n", " \n ").split(" ")
    lines, cur = [], ""
    for wd in words:
        if wd == "\n":
            lines.append(cur)
            cur = ""
            continue
        test = wd if not cur else cur + " " + wd
        if len(test) <= width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def wrap_text(text, width):
    return wrap_micro(text, width)


def draw_wrapped(buf, x, y, text, colour, width, line_h=7, micro=False):
    lines = wrap_micro(text, width)
    for i, ln in enumerate(lines):
        if micro:
            font.draw_micro(buf, x, y + i * 6, ln, colour)
        else:
            font.draw_text(buf, x, y + i * line_h, ln, colour)
    return len(lines)


def toast_style(text):
    return text


def fmt_left(s, n):
    return s[:n]


def draw_match_row(buf, y, pf, ef, border=LINE):
    """Draw '[flag] NATION  VS  [flag] NATION', centred, never overlapping."""
    pn, en = factions.name(pf), factions.name(ef)
    pw = 12 + font.micro_width(pn)
    ew = 12 + font.micro_width(en)
    vs_w = font.micro_width("VS")
    total = pw + 8 + vs_w + 8 + ew
    x = max(2, (W - total) // 2)

    factions.draw_flag(buf, x, y, pf, 9, 6, border=border)
    font.draw_micro(buf, x + 12, y + 1, pn, factions.colour(pf))
    x += pw + 8
    font.draw_micro(buf, x, y + 1, "VS", GOLD)
    x += vs_w + 8
    factions.draw_flag(buf, x, y, ef, 9, 6, border=border)
    font.draw_micro(buf, x + 12, y + 1, en, factions.colour(ef))


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Screen:
    icon_name = ""

    def __init__(self):
        self.t0 = 0.0

    def enter(self, app):
        self.t0 = app.t

    def press(self, key, app):
        pass

    def tick(self, dt, app):
        pass

    def draw(self, buf, app):
        pass

    @property
    def age(self):
        return 0.0


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
class HomeScreen(Screen):
    def __init__(self):
        super().__init__()
        self.chatter_i = random.randrange(len(CHATTER))
        self.chatter_t = 0.0

    def enter(self, app):
        super().enter(app)
        self.chatter_t = 0.0

    def press(self, key, app):
        g = app.game
        if key == "B":
            app.push(MenuScreen())
        elif key in ("A", "C"):
            owned = [k for k in FLEET if g.is_unlocked(k)]
            if len(owned) > 1:
                i = owned.index(g.active_key)
                step = -1 if key == "A" else 1
                g.select(owned[(i + step) % len(owned)])
                app.sound.play("click")
                app.toast(g.meta()["short"] + " SELECTED", ACCENT)

    def tick(self, dt, app):
        self.chatter_t += dt
        if self.chatter_t > 7.5:
            self.chatter_t = 0.0
            self.chatter_i = (self.chatter_i + 1) % len(CHATTER)

    def draw(self, buf, app):
        g = app.game
        m = g.meta()
        lvl = g.level
        buf.rect(0, 0, W, H, BG)
        header(buf, m["short"], "LV%02d %s" % (lvl, rank_for(lvl)), ACCENT)
        _home_scene(buf, g, app.t, m, g.active_key)
        # name plate
        buf.rect(0, 44, W, 10, mix(PANEL, BG, 0.15))
        buf.hline(0, W - 1, 44, LINE)
        mood, mcol = g.mood()
        font.draw_text(buf, 3, 46, g.data["pilot"][:11], TEXT)
        font.draw_micro(buf, W - 2 - font.micro_width(mood), 47, mood, mcol)
        # stat strip
        _stat_strip(buf, g, 55)
        # chatter ticker
        msg = CHATTER[self.chatter_i][:26]
        font.draw_micro(buf, 2, 66, msg, DIM)


def _home_scene(buf, game, t, meta, key):
    """Sky 9-32, mountains, runway 33-43, aircraft in the middle."""
    night = _is_night()
    top = 0x060B16 if night else 0x0E2038
    bot = 0x122A44 if night else 0x3A5C86
    for y in range(9, 33):
        f = (y - 9) / 23.0
        buf.hline(0, W - 1, y, mix(top, bot, f ** 1.1))
    if night:
        rng = random.Random(7)
        for i in range(24):
            sx = rng.randrange(0, W)
            sy = rng.randrange(10, 30)
            tw = (t * 1.7 + i) % 3 < 2.2
            if tw:
                buf.px(sx, sy, 0xBBD2F0 if i % 3 else 0x6E88AE)
        # moon with a soft halo and a couple of craters
        buf.fill_ellipse(90, 15, 5, 5, mix(0x3A4E70, top, 0.45))
        buf.fill_ellipse(90, 15, 3, 3, 0xE8F0FF)
        buf.px(89, 14, 0xC6D6EE)
        buf.px(91, 16, 0xC6D6EE)
        buf.px(90, 17, 0xD6E2F6)
    else:
        buf.fill_ellipse(91, 15, 5, 5, mix(0xFFE0A8, bot, 0.35))
        buf.fill_ellipse(91, 15, 3, 3, 0xFFE8BC)
    # clouds
    for i in range(3):
        cx = (i * 47 + t * (2 + i)) % (W + 30) - 15
        cy = 12 + i * 4
        col = mix(0x4C6E96 if not night else 0x22344E, bot, 0.35)
        buf.fill_ellipse(cx, cy, 7 + i, 1.8, col)
        buf.fill_ellipse(cx + 4, cy - 1, 5, 1.4, col)
    # mountains
    for x in range(W):
        h1 = 4 + int(3 * abs(math.sin(x * 0.07 + 0.4)))
        buf.vline(x, 32 - h1, 31, 0x1B3350 if not night else 0x101D30)
        h2 = 2 + int(2 * abs(math.sin(x * 0.11 + 2.1)))
        buf.vline(x, 32 - h2, 31, 0x122438 if not night else 0x0A1420)
    buf.hline(0, W - 1, 32, 0x0E1B2C)
    # runway
    buf.rect(0, 33, W, 11, 0x1A2230 if not night else 0x0D1420)
    buf.hline(0, W - 1, 33, 0x2C3A4E if not night else 0x1A2434)
    off = int(t * 14) % 12
    for i in range(-1, 11):
        x = i * 12 + off
        buf.hline(x, x + 6, 38, 0x5A6A80 if not night else 0x27364A)
    # edge lights
    for i in range(0, W, 18):
        c = 0xFFC24A if (int(t * 2) + i) % 6 < 3 else 0x7A5A18
        buf.px(i + 3, 34, c)
        buf.px(W - 4 - i, 34, c)

    # the aircraft itself
    bob = math.sin(t * 1.8) * 1.1
    art = _jet_art(game, key)
    jy = int(15 + bob)
    noz = sprites.nozzle_x(key)
    sprites.draw_flame(buf, 34 + noz, jy + 9, int(t * 10), hot=0xFFD27A, cool=0xFF7A3A)
    buf.blit_art(art, 34, jy, outline=0x060C14)
    # little pilot eyes in the canopy - the tamagotchi soul
    cx, cy = sprites.canopy_center(key)
    blink = (t % 4.6) < 0.18
    if not blink:
        buf.px(34 + cx - 1, jy + cy, 0x0A2A3A)
        buf.px(34 + cx + 1, jy + cy, 0x0A2A3A)
    # speed streaks
    for i in range(3):
        yy = jy + 4 + i * 4
        ln = 4 + (i * 3 + int(t * 20)) % 7
        x = 32 - ln
        buf.hline(x, 31, yy, mix(0x9FD8F0, bot, 0.55))
    _rank_marks(buf, game, 5, 26)


def _rank_marks(buf, game, x, y):
    """Little gold chevrons in the corner, one per promotion tier."""
    lvl = game.level
    if lvl < 3:
        return
    chevrons = min(6, 1 + (lvl - 3) // 3)
    for i in range(chevrons):
        cx = x + i * 5
        buf.px(cx, y, GOLD)
        buf.px(cx + 4, y, GOLD)
        buf.px(cx + 1, y + 1, GOLD)
        buf.px(cx + 3, y + 1, GOLD)
        buf.px(cx + 2, y + 2, GOLD)


def _jet_art(game, key):
    pal = dict(sprites.LIVERIES[game.livery()])
    lvl = game.level
    if lvl >= 10:
        pal["a"] = 0xFFC24A
        pal["h"] = mix(pal["h"], 0xFFE6A8, 0.35)
    if lvl >= 16:
        pal["g"] = 0xFFE9A8
    return sprites.Art(sprites.AIRCRAFT[key]["grid"], pal)


def _is_night():
    h = time.localtime().tm_hour
    return h >= 21 or h < 6


def _stat_strip(buf, game, y):
    s = game.stats
    items = [
        ("FUEL", s["fuel"], 0xFFC24A),
        ("MORL", s["morale"], PINK),
        ("COND", s["condition"], ACCENT),
        ("AMMO", s["ammo"], RED),
    ]
    cw = W // 4
    for i, (label, val, col) in enumerate(items):
        x = i * cw + 2
        font.draw_micro(buf, x, y, label, DIM)
        seg = int(round(val / 100 * 6))
        for k in range(6):
            bx = x + k * 4
            c = col if k < seg else 0x16283C
            buf.rect(bx, y + 6, 3, 4, c)
    buf.hline(0, W - 1, y - 2, LINE)


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------
MENU_ITEMS = [
    ("feed", "FEED", "feed"),
    ("rest", "REST", "rest"),
    ("polish", "POLISH", "polish"),
    ("train", "TRAIN", "train"),
    ("rearm", "REARM", "rearm"),
    ("repair", "REPAIR", "repair"),
    ("sortie", "SORTIE", "sortie"),
    ("hangar", "HANGAR", "hangar"),
    ("fleet", "FLEET", "fleet"),
    ("identity", "ALLEGIANCE", "identity"),
    ("exit", "BACK", "exit"),
]


class MenuScreen(Screen):
    def __init__(self):
        super().__init__()
        self.sel = 0
        self.scroll = 0

    def press(self, key, app):
        g = app.game
        n = len(MENU_ITEMS)
        if key == "A":
            self.sel = (self.sel - 1) % n
            app.sound.play("click")
        elif key == "C":
            self.sel = (self.sel + 1) % n
            app.sound.play("click")
        elif key == "B":
            self.activate(app)
        self._clamp()

    def _clamp(self):
        if self.sel < self.scroll:
            self.scroll = self.sel
        elif self.sel >= self.scroll + 4:
            self.scroll = self.sel - 3

    def activate(self, app):
        g = app.game
        _ic, label, action = MENU_ITEMS[self.sel]
        if action == "exit":
            app.pop()
            return
        if action == "sortie":
            if g.can_sortie():
                app.push(BriefingScreen())
            else:
                app.sound.play("error")
                app.toast(g.sortie_blocker(), RED)
            return
        if action == "hangar":
            app.push(HangarScreen())
            return
        if action == "fleet":
            app.push(FleetScreen())
            return
        if action == "identity":
            app.push(FactionScreen())
            return
        # care actions
        cd = g.cooldown_left(action)
        if cd > 0:
            app.sound.play("error")
            app.toast("WAIT %ds" % int(math.ceil(cd)), RED)
            return
        ok, msg, snd = g.act(action)
        app.sound.play(snd)
        app.toast(msg, GREEN if ok else RED)

    def draw(self, buf, app):
        g = app.game
        buf.rect(0, 0, W, H, BG)
        header(buf, "MAIN MENU", "CR %d" % g.data["credits"], GOLD)
        row_h = 13
        for i in range(4):
            idx = self.scroll + i
            if idx >= len(MENU_ITEMS):
                break
            ic, label, action = MENU_ITEMS[idx]
            y = 9 + i * row_h
            selected = idx == self.sel
            if selected:
                buf.rect(0, y, W, row_h, 0x14283E)
                buf.rect(0, y, 2, row_h, ACCENT)
            icon(buf, 6, y + 3, ic, ACCENT if selected else DIM)
            font.draw_text(buf, 17, y + 3, label, TEXT if selected else DIM)
            value, vcol = _menu_value(g, action)
            if value:
                font.draw_micro(buf, W - 5 - font.micro_width(value), y + 4, value, vcol)
        # slim scroll track on the right edge
        total = len(MENU_ITEMS)
        if total > 4:
            tx = W - 2
            buf.vline(tx, 12, H - 12, 0x1B2C40)
            thumb = max(6, int((H - 24) * 4 / total))
            span = (H - 24) - thumb
            ty = 12 + int(span * (self.scroll / max(1, total - 4)))
            buf.rect(tx - 1, ty, 3, thumb, mix(ACCENT, LINE, 0.55))
        footer(buf, "A/C SELECT   B OK")


def _menu_value(game, action):
    g = game
    s = g.stats
    if action in ("feed", "rest", "polish", "train"):
        cd = g.cooldown_left(action)
        if cd > 0:
            return "%ds" % int(math.ceil(cd)), DIM
        return "READY", GREEN
    if action == "sortie":
        blk = g.sortie_blocker()
        if blk:
            short = {"AIRFRAME DAMAGED": "DAMAGED",
                     "NO AMMUNITION": "NO AMMO",
                     "FUEL TOO LOW": "LOW FUEL"}.get(blk, blk[:7])
            return short, RED
        return "READY", GREEN
    if action == "rearm":
        if s["ammo"] >= 99:
            return "FULL", GREEN
        return "45 CR", GOLD if g.data["credits"] >= 45 else RED
    if action == "repair":
        if s["condition"] >= 96:
            return "OK", GREEN
        return "90 CR", GOLD if g.data["credits"] >= 90 else RED
    if action == "hangar":
        return g.meta()["short"], ACCENT
    if action == "fleet":
        return "%d/6" % len(g.data["unlocked"]), ACCENT
    if action == "identity":
        return factions.code(g.faction), factions.colour(g.faction)
    return "", DIM


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------
class BriefingScreen(Screen):
    def __init__(self):
        super().__init__()
        self.tactic_i = 1
        self.tactics = list(TACTICS.keys())
        self.enemy = None

    def enter(self, app):
        super().enter(app)
        self.enemy = app.game.make_enemy()

    def press(self, key, app):
        if key == "A":
            self.tactic_i = (self.tactic_i - 1) % len(self.tactics)
            app.sound.play("click")
        elif key == "C":
            self.tactic_i = (self.tactic_i + 1) % len(self.tactics)
            app.sound.play("click")
        elif key == "B":
            app.launch_sortie(self.enemy, self.tactics[self.tactic_i])

    def draw(self, buf, app):
        g = app.game
        e = self.enemy
        t = TACTICS[self.tactics[self.tactic_i]]
        buf.rect(0, 0, W, H, BG)
        header(buf, "SORTIE BRIEFING", t["note"], ACCENT)

        # --- the match-up: who we fly as, who we fly against ---
        pf = g.faction
        ef = e["faction"]
        font.draw_micro(buf, 2, 12, "YOU", DIM)
        factions.draw_flag(buf, 18, 10, pf, 9, 6, border=LINE)
        font.draw_text(buf, 31, 10, factions.name(pf), factions.colour(pf))

        buf.hline(2, W - 3, 19, LINE)
        vs = "VS"
        vx = (W - font.micro_width(vs)) // 2
        buf.rect(vx - 3, 17, font.micro_width(vs) + 6, 7, BG)
        font.draw_micro(buf, vx, 18, vs, GOLD)

        font.draw_micro(buf, 2, 26, "FOE", DIM)
        factions.draw_flag(buf, 18, 25, ef, 9, 6, border=LINE)
        font.draw_text(buf, 31, 25, factions.name(ef), factions.colour(ef))

        # enemy details
        buf.hline(2, W - 3, 33, 0x14263A)
        font.draw_micro(buf, 2, 36, "SQUAD", DIM)
        font.draw_micro(buf, 30, 36, e["name"][:18], TEXT)
        font.draw_micro(buf, 2, 44, "TYPE", DIM)
        font.draw_text(buf, 30, 43, FLEET[e["key"]]["short"], TEXT)
        threat = "LV%d" % e["level"]
        font.draw_micro(buf, W - 4 - font.micro_width(threat), 44, threat, GOLD)

        # tactic
        panel(buf, 2, 51, W - 4, 12)
        font.draw_micro(buf, 6, 55, "MODE", DIM)
        font.draw_text(buf, 30, 53, t["name"], ACCENT)
        font.draw_micro(buf, W - 4 - font.micro_width("< >"), 55, "< >", DIM)

        footer(buf, "A/C TACTIC    B LAUNCH", GREEN)


# ---------------------------------------------------------------------------
# Battle
# ---------------------------------------------------------------------------
class BattleScreen(Screen):
    def __init__(self, sim, enemy):
        super().__init__()
        self.sim = sim
        self.enemy = enemy
        self.t = 0.0
        self.finalized = False
        self.sfx_i = 0
        self.result = None

    def enter(self, app):
        super().enter(app)
        app.sound.play("sortie")

    def press(self, key, app):
        if key == "B":
            # skip ahead a little
            self.t = min(self.sim["end_t"] - 0.4, self.t + 1.2)

    def tick(self, dt, app):
        self.t += dt
        # event sounds
        while self.sfx_i < len(self.sim["events"]):
            ev = self.sim["events"][self.sfx_i]
            if self.t >= ev["t"] - 0.4:
                if ev["hit"]:
                    app.sound.play("explode" if (ev["crit"] or ev["special"]) else "hit")
                else:
                    app.sound.play("miss")
                self.sfx_i += 1
            else:
                break
        if not self.finalized and self.t > self.sim["end_t"]:
            self.finalized = True
            self.result = app.finish_sortie(self.sim)
            app.replace(ResultScreen(self.sim, self.result))

    def draw(self, buf, app):
        buf.rect(0, 0, W, H, BG)
        dogfight.render(buf, self.sim, min(self.t, self.sim["end_t"]), app.frame)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
class ResultScreen(Screen):
    def __init__(self, sim, entry):
        super().__init__()
        self.sim = sim
        self.entry = entry

    def enter(self, app):
        super().enter(app)
        app.sound.play("victory" if self.sim["winner"] == 0 else "defeat")

    def press(self, key, app):
        if key in ("B", "A", "C"):
            app.go_home()

    def draw(self, buf, app):
        g = app.game
        win = self.sim["winner"] == 0
        buf.rect(0, 0, W, H, BG)
        header(buf, "MISSION REPORT", "CR %d" % g.data["credits"], GOLD)
        col = GREEN if win else RED
        if int(app.t * 3) % 2 == 0 or app.t - self.t0 > 1.5:
            font.draw_text_center(buf, W // 2, 13, "MISSION COMPLETE" if win else "MISSION FAILED", col, shadow=0x05080C)

        # factions involved
        pf = self.sim["player"]["faction"]
        ef = self.sim["enemy"]["faction"]
        draw_match_row(buf, 23, pf, ef)

        rows = [
            ("EARNED", "+%d" % self.entry["credits"], 5, 55, 32, GOLD),
            ("XP", "+%d" % self.entry["xp"], 60, 104, 32, ACCENT),
            ("ROUNDS", "%d" % self.entry["rounds"], 5, 55, 44, TEXT),
            ("HULL", "%d%%" % int(self.sim["php"] / max(1, self.sim["player"]["hp"]) * 100),
             60, 104, 44, TEXT),
        ]
        for label, value, lx, rx, y, c in rows:
            font.draw_micro(buf, lx, y + 1, label, DIM)
            font.draw_text_right(buf, rx, y, value, c)

        # rank progress
        xp, need = xp_into_level(g.airframe["xp"])
        rk = rank_for(g.level)
        font.draw_micro(buf, 4, 58, rk, ACCENT)
        bar(buf, 4 + font.micro_width(rk) + 3, 58, W - 12 - font.micro_width(rk), 3,
            xp / max(1, need), ACCENT)
        footer(buf, "PRESS ANY BUTTON", DIM)


# ---------------------------------------------------------------------------
# Hangar
# ---------------------------------------------------------------------------
class HangarScreen(Screen):
    def __init__(self):
        super().__init__()
        self.sel = 0
        self.lines = list(UPGRADES.keys())

    def press(self, key, app):
        if key == "A":
            self.sel = (self.sel - 1) % (len(self.lines) + 1)
            app.sound.play("click")
        elif key == "C":
            self.sel = (self.sel + 1) % (len(self.lines) + 1)
            app.sound.play("click")
        elif key == "B":
            if self.sel == len(self.lines):
                app.pop()
                return
            line = self.lines[self.sel]
            ok, msg = app.game.buy_upgrade(line)
            app.sound.play("confirm" if ok else "error")
            app.toast(msg, GREEN if ok else RED)

    def draw(self, buf, app):
        g = app.game
        m = g.meta()
        buf.rect(0, 0, W, H, BG)
        header(buf, "HANGAR  " + m["short"], "CR %d" % g.data["credits"], GOLD)
        font.draw_text(buf, 3, 10, m["name"][:11], TEXT)
        font.draw_micro(buf, W - 4 - font.micro_width("LV%02d" % g.level), 11,
                        "LV%02d" % g.level, ACCENT)

        st = g.combat_stats()
        font.draw_micro(buf, 3, 19, "HP%d ATK%d AGI%d DEF%d" % (st["hp"], st["atk"], st["agi"], st["dfn"]), DIM)
        buf.hline(0, W - 1, 25, LINE)

        for i, line in enumerate(self.lines):
            y = 28 + i * 9
            selected = i == self.sel
            if selected:
                buf.rect(0, y - 1, W, 9, 0x14283E)
                buf.rect(0, y - 1, 2, 9, ACCENT)
            up = UPGRADES[line]
            lvl = g.airframe["up"][line]
            font.draw_text(buf, 5, y, up["name"], TEXT if selected else DIM)
            for k in range(5):
                bx = 52 + k * 5
                buf.rect(bx, y + 1, 4, 5, ACCENT if k < lvl else 0x22354E)
            cost = g.upgrade_cost(line)
            if lvl >= 5:
                font.draw_micro(buf, W - 4 - font.micro_width("MAX"), y + 1, "MAX", GOLD)
            else:
                font.draw_micro(buf, W - 4 - font.micro_width("%d CR" % cost), y + 1, "%d CR" % cost,
                                GOLD if g.data["credits"] >= cost else RED)
        # back row
        y = 28 + len(self.lines) * 9
        selected = self.sel == len(self.lines)
        if selected:
            buf.rect(0, y - 1, W, 9, 0x14283E)
            buf.rect(0, y - 1, 2, 9, ACCENT)
        icon(buf, 5, y, "exit", ACCENT if selected else DIM)
        font.draw_text(buf, 16, y, "BACK", TEXT if selected else DIM)
        footer(buf, "A/C SELECT   B BUY")


# ---------------------------------------------------------------------------
# Fleet
# ---------------------------------------------------------------------------
class FleetScreen(Screen):
    def __init__(self):
        super().__init__()
        self.keys = list(FLEET.keys())
        self.sel = 0
        self.scroll = 0

    @property
    def total(self):
        return len(self.keys) + 1          # jets + BACK row

    def enter(self, app):
        super().enter(app)
        try:
            self.sel = self.keys.index(app.game.active_key)
        except ValueError:
            self.sel = 0
        self.scroll = max(0, min(self.sel, self.total - 3))

    def press(self, key, app):
        g = app.game
        if key == "A":
            self.sel = (self.sel - 1) % self.total
            app.sound.play("click")
        elif key == "C":
            self.sel = (self.sel + 1) % self.total
            app.sound.play("click")
        elif key == "B":
            if self.sel >= len(self.keys):
                app.sound.play("click")
                app.pop()
                return
            k = self.keys[self.sel]
            if g.is_unlocked(k):
                g.select(k)
                app.sound.play("confirm")
                app.toast("NOW FLYING " + FLEET[k]["short"], GREEN)
            else:
                ok, msg = g.unlock(k)
                app.sound.play("confirm" if ok else "error")
                app.toast(msg, GREEN if ok else RED)
                if ok:
                    g.select(k)
        if self.sel < self.scroll:
            self.scroll = self.sel
        elif self.sel >= self.scroll + 3:
            self.scroll = self.sel - 2

    def draw(self, buf, app):
        g = app.game
        buf.rect(0, 0, W, H, BG)
        header(buf, "FLEET  %d/6" % len(g.data["unlocked"]), "CR %d" % g.data["credits"], GOLD)
        for i in range(3):
            idx = self.scroll + i
            if idx >= self.total:
                break
            y = 10 + i * 14
            selected = idx == self.sel
            if selected:
                buf.rect(0, y - 2, W, 13, 0x14283E)
                buf.rect(0, y - 2, 2, 13, ACCENT)
            if idx >= len(self.keys):
                # back row
                icon(buf, 6, y, "exit", ACCENT if selected else DIM)
                font.draw_text(buf, 18, y, "BACK", TEXT if selected else DIM)
                continue
            k = self.keys[idx]
            m = FLEET[k]
            font.draw_text(buf, 5, y, m["short"], TEXT if selected else (DIM if not g.is_unlocked(k) else 0x7FA8C0))
            if k == g.active_key:
                font.draw_micro(buf, W - 4 - font.micro_width("ACTIVE"), y + 1, "ACTIVE", GREEN)
            elif g.is_unlocked(k):
                font.draw_micro(buf, W - 4 - font.micro_width("OWNED"), y + 1, "OWNED", ACCENT)
            elif g.best_level < m["req"]:
                s = "REQ LV%d" % m["req"]
                font.draw_micro(buf, W - 4 - font.micro_width(s), y + 1, s, RED)
            else:
                s = "%d CR" % m["cost"]
                font.draw_micro(buf, W - 4 - font.micro_width(s), y + 1, s,
                                GOLD if g.data["credits"] >= m["cost"] else RED)
        # detail strip for the highlighted jet
        panel(buf, 2, 53, W - 4, 10)
        if self.sel < len(self.keys):
            m = FLEET[self.keys[self.sel]]
            font.draw_micro(buf, 5, 55, "HP%d ATK%d AGI%d DEF%d" % (m["hp"], m["atk"], m["agi"], m["dfn"]), TEXT)
        else:
            hint = "RETURN TO MAIN MENU"
            font.draw_micro(buf, (W - font.micro_width(hint)) // 2, 55, hint, DIM)
        footer(buf, "A/C SELECT   B BACK" if self.sel >= len(self.keys)
               else "A/C SELECT   B USE/UNLOCK")


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
class BootScreen(Screen):
    def __init__(self):
        super().__init__()
        self.dur = 2.3
        self.done = False

    def press(self, key, app):
        if key == "B":
            self.done = True

    def tick(self, dt, app):
        age = app.t - self.t0
        if not self.done and age > self.dur:
            self.done = True
        if self.done:
            if not app.game.data["flags"].get("booted"):
                app.replace(FactionScreen())
            else:
                app.replace(HomeScreen())

    def draw(self, buf, app):
        age = app.t - self.t0
        buf.rect(0, 0, W, H, BG)
        # scanlines
        for y in range(0, H, 3):
            buf.hline(0, W - 1, y, 0x0A1522)
        font.draw_text_center(buf, W // 2, 14, "ACE GOTCHI", ACCENT)
        tag = "TACTICAL AIRFRAME SYSTEM"
        font.draw_micro(buf, (W - font.micro_width(tag)) // 2, 25, tag, DIM)
        # emblem
        cx, cy = W // 2, 38
        buf.stroke_ellipse(cx, cy, 8, 8, LINE)
        buf.fill_ellipse(cx, cy, 6, 6, 0x11202F)
        buf.fill_poly([(cx - 4, cy + 2), (cx, cy - 3), (cx + 4, cy + 2), (cx, cy)], ACCENT)
        # progress
        p = min(1.0, age / self.dur)
        buf.rect(18, 52, W - 36, 4, 0x14263A)
        buf.rect(18, 52, int((W - 36) * p), 4, ACCENT)
        buf.box(18, 52, W - 36, 4, 0x14263A, LINE)
        msg = "SYSTEM CHECK" if p < 0.9 else "READY"
        font.draw_micro(buf, 18, 60, msg, DIM)
        font.draw_micro(buf, W - 22, 60, "MK.II", DIM)


# ---------------------------------------------------------------------------
# Allegiance
# ---------------------------------------------------------------------------
class FactionScreen(Screen):
    def __init__(self):
        super().__init__()
        self.sel = 0
        self.order = factions.FACTION_ORDER
        self.confirmed = False
        self.confirm_t = 0.0

    def enter(self, app):
        super().enter(app)
        try:
            self.sel = self.order.index(app.game.faction)
        except ValueError:
            self.sel = 0

    def press(self, key, app):
        if self.confirmed:
            return
        if key == "A":
            self.sel = (self.sel - 1) % len(self.order)
            app.sound.play("click")
        elif key == "C":
            self.sel = (self.sel + 1) % len(self.order)
            app.sound.play("click")
        elif key == "B":
            key_name = self.order[self.sel]
            app.game.set_faction(key_name)
            app.game.data["flags"]["booted"] = True
            app.save()
            self.confirmed = True
            self.confirm_t = app.t
            app.sound.play("confirm")

    def tick(self, dt, app):
        if self.confirmed and app.t - self.confirm_t > 1.1:
            app.toast("ALLEGIANCE: " + factions.name(app.game.faction), factions.colour(app.game.faction))
            app.go_home()

    def draw(self, buf, app):
        key = self.order[self.sel]
        f = factions.get(key)
        buf.rect(0, 0, W, H, BG)
        header(buf, "ALLEGIANCE", "B: CONFIRM" if not self.confirmed else "", ACCENT)

        # large flag
        factions.draw_flag(buf, 6, 12, key, 18, 12, border=LINE)
        font.draw_text(buf, 30, 12, f["name"], f["text"], shadow=0x05080C)
        font.draw_micro(buf, 6, 26, f["motto"][:25], DIM)
        buf.hline(4, W - 5, 32, 0x14263A)

        lines = wrap_micro(f["bio"], 20)
        for i, ln in enumerate(lines[:4]):
            font.draw_micro(buf, 4, 34 + i * 6, ln, TEXT)

        # faction selector dots
        for i, k in enumerate(self.order):
            x = 8 + i * 16
            if i == self.sel:
                buf.fill_ellipse(x, 57, 2, 2, factions.colour(k))
                buf.stroke_ellipse(x, 57, 3, 3, LINE)
            else:
                buf.px(x, 57, DIM)
        if self.confirmed:
            buf.rect(0, 37, W, 10, BG)
            buf.hline(0, W - 1, 37, LINE)
            buf.hline(0, W - 1, 46, LINE)
            font.draw_text_center(buf, W // 2, 39, "ALLEGIANCE SET", GREEN, shadow=0x05080C)
        footer(buf, "A/C CHANGE    B CONFIRM", GREEN)
