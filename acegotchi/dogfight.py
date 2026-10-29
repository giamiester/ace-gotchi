"""Auto-battler dogfight: simulation + animated LCD renderer."""

import math
import random

from . import factions, font, sprites
from .pixel import PixBuf, mix, shade, TRANSPARENT
from .state import TACTICS

INTRO = 1.25
EXCHANGE_GAP = 0.86
MISSILE_FLIGHT = 0.40
OUTRO = 1.9
MAX_EXCHANGES = 18

SKY_TOP = 0x101C30
SKY_BOT = 0x3E567A
SUN = 0xFFD9A0


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
def simulate(player, enemy, tactic="balanced", rng=None):
    rng = rng or random.Random()
    tac = TACTICS.get(tactic, TACTICS["balanced"])
    php, ehp = player["hp"], enemy["hp"]
    events = []
    t = INTRO
    order = 0
    ended = False

    for i in range(MAX_EXCHANGES):
        by = i % 2
        atk = (player if by == 0 else enemy)
        dfn = (enemy if by == 0 else player)
        a_atk = atk["atk"] * (tac["atk"] if by == 0 else 1.0)
        a_agi = atk["agi"] * (tac["eva"] if by == 0 else 1.0)
        d_agi = dfn["agi"] * (tac["eva"] if by == 1 else 1.0)

        ratio = a_agi / max(1.0, d_agi)
        chance = 0.72 * (ratio ** 0.85)
        chance = max(0.30, min(0.93, chance))
        hit = rng.random() < chance
        special = rng.random() < 0.16
        crit = rng.random() < 0.12

        dmg = 0
        if hit:
            dmg = a_atk * rng.uniform(0.82, 1.18) - dfn["dfn"] * 0.40
            if special:
                dmg *= 1.55
            if crit:
                dmg *= 1.45
            if by == 1:
                dmg *= tac["taken"]
            dmg = max(4, int(round(dmg)))
            if by == 0:
                ehp = max(0.0, ehp - dmg)
            else:
                php = max(0.0, php - dmg)

        events.append(dict(
            t=t, by=by, hit=hit, dmg=dmg, crit=crit, special=special,
            php=php, ehp=ehp,
        ))
        t += EXCHANGE_GAP
        if php <= 0 or ehp <= 0:
            ended = True
            break

    if php <= 0:
        winner = 1
    elif ehp <= 0:
        winner = 0
    else:
        winner = 0 if php / player["hp"] >= ehp / enemy["hp"] else 1
        ended = False

    end_t = events[-1]["t"] + OUTRO
    return dict(
        events=events, winner=winner, ended=ended, end_t=end_t,
        php=php, ehp=ehp, rounds=len(events),
        player=player, enemy=enemy, tactic=tactic,
    )


def hp_at(sim, when):
    php, ehp = sim["player"]["hp"], sim["enemy"]["hp"]
    for ev in sim["events"]:
        if ev["t"] <= when:
            php, ehp = ev["php"], ev["ehp"]
        else:
            break
    return php, ehp


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _sky(buf, t, y0, y1):
    for y in range(y0, y1):
        f = (y - y0) / max(1, (y1 - y0 - 1))
        c = mix(SKY_TOP, SKY_BOT, f ** 0.8)
        buf.hline(0, buf.w - 1, y, c)
    # dithered band boundaries
    for y in (y0 + 10, y0 + 22):
        for x in range(0, buf.w, 2):
            buf.px(x + (y % 2), y, mix(SKY_TOP, SKY_BOT, (y - y0) / (y1 - y0)))


def _sun(buf, x, y, t):
    buf.fill_ellipse(x, y, 7, 7, mix(SUN, SKY_BOT, 0.45))
    buf.fill_ellipse(x, y, 5, 5, SUN)
    buf.fill_ellipse(x, y - 1, 3, 3, 0xFFF3D6)
    # cloud bands across the sun
    for i, yy in enumerate((y + 1, y + 4)):
        buf.hline(x - 9 - i * 2, x + 9 + i * 2, yy, mix(SUN, SKY_TOP, 0.35))


def _cloud(buf, x, y, scale=1, col=0x6C87AE, seed=0):
    w = 10 * scale
    buf.fill_ellipse(x, y, w, 2.4 * scale, col)
    buf.fill_ellipse(x - w * 0.45, y - 1, w * 0.55, 2.0 * scale, col)
    buf.fill_ellipse(x + w * 0.35, y - 1.4, w * 0.6, 2.2 * scale, col)
    buf.fill_ellipse(x + w * 0.05, y - 2.2 * scale, w * 0.45, 1.8 * scale, mix(col, 0xFFFFFF, 0.18))


def _draw_jet(buf, art, x, y, flip, nozzle, canopy, t):
    nx = x + (art.w - 1 - nozzle if flip else nozzle)
    sprites.draw_flame(buf, nx, y + 9, t + (7 if flip else 0), flip=flip)
    buf.blit_art(art, x, y, palette=art.palette, flip=flip, outline=0x0A1018)
    # canopy glint
    if (t // 7) % 6 != 0:
        gx = x + (art.w - 1 - canopy if flip else canopy)
        buf.px(gx, y + 5, 0xEAF6FF)


def _contrail(buf, x0, x1, y, col=0x9FB6D4):
    step = 3
    n = max(0, (x1 - x0) // step)
    for i in range(n):
        px = x1 - i * step
        c = mix(col, SKY_BOT, min(1.0, i / max(1, n)))
        buf.px(px, y + (i % 2), c)
        if i % 2 == 0:
            buf.px(px, y + 1, mix(c, SKY_BOT, 0.4))


def _hp_bar(buf, x, y, w, frac, colour):
    buf.rect(x, y, w, 5, 0x0A1420)
    buf.box(x, y, w, 5, 0x0A1420, 0x2A4058)
    frac = max(0.0, min(1.0, frac))
    fill = max(0, int(round((w - 2) * frac)))
    if fill:
        buf.rect(x + 1, y + 1, fill, 2, colour)
        buf.hline(x + 1, x + fill, y + 1, mix(colour, 0xFFFFFF, 0.35))


def _hud_row(buf, y, flag_key, label, frac, bar_w=28):
    f = factions.get(flag_key)
    factions.draw_flag(buf, 2, y, flag_key, 9, 6, border=0x0A1420)
    font.draw_text(buf, 13, y, label, f["text"], shadow=0x0A1018)
    _hp_bar(buf, buf.w - bar_w - 2, y + 1, bar_w, frac,
            0x6BFF9E if frac > 0.5 else 0xFFC24A if frac > 0.25 else 0xE8564A)


def _explosion(buf, x, y, age, big=False):
    if age < 0 or age > 0.42:
        return
    f = age / 0.42
    r = (3 + 7 * f) * (1.5 if big else 1.0)
    cols = [0xFFF3C4, 0xFFC24A, 0xFF7A3A, 0xB03A28]
    for ring in range(3):
        rr = r - ring * 1.6
        if rr <= 0:
            continue
        col = cols[min(3, ring + int(f * 2))]
        for a in range(0, 360, 24):
            rad = math.radians(a + f * 60)
            buf.px(int(x + math.cos(rad) * rr), int(y + math.sin(rad) * rr * 0.8), col)
    if f < 0.35:
        buf.fill_ellipse(x, y, r * 0.5, r * 0.4, 0xFFF3C4)


def render(buf, sim, t, frame):
    player, enemy = sim["player"], sim["enemy"]
    events = sim["events"]
    end_t = sim["end_t"]

    # ---- who is where -------------------------------------------------
    shake_x = shake_y = 0
    near = None
    for ev in events:
        dt = t - ev["t"]
        if -MISSILE_FLIGHT - 0.1 <= dt <= 0.14 and ev["hit"]:
            shake_x = 1 if int(t * 40) % 2 else -1
            shake_y = 1 if int(t * 33) % 2 else 0
        if -MISSILE_FLIGHT <= dt <= 0.5:
            near = ev

    _sky(buf, t, 9, 56)
    _sun(buf, 84, 20, t)
    for i, (cx, cy, sc) in enumerate(((18, 34, 1.3), (52, 26, 1.0), (86, 40, 1.5), (34, 48, 0.9))):
        drift = (t * (3 + i) + i * 30) % (buf.w + 40) - 20
        _cloud(buf, int(drift), cy, sc, mix(0x5A7398, SKY_BOT, 0.25), i)
    # distant terrain
    for x in range(buf.w):
        h = 2 + int(1.5 * (1 + math.sin(x * 0.13 + 1.2)))
        buf.vline(x, 56 - h, 55, 0x1A2740)

    base_y = 22
    bob_p = int(round(math.sin(t * 2.3) * 1.2))
    bob_e = int(round(math.sin(t * 1.9 + 2.0) * 1.2))
    px, ex = 6, buf.w - 46
    if t < INTRO:
        k = t / INTRO
        px = int(-40 + (6 + 40) * k)
        ex = int(buf.w + (buf.w - 46 - buf.w) * k)
    # lunge toward each other when attacking
    if near is not None:
        dt = t - (near["t"] - MISSILE_FLIGHT)
        if 0 <= dt <= 0.55:
            amt = math.sin(min(1.0, dt / 0.55) * math.pi) * 6
            if near["by"] == 0:
                px += int(amt)
            else:
                ex -= int(amt)

    p_art = sprites.Art(sprites.AIRCRAFT[player["key"]]["grid"], sprites.LIVERIES[player["livery"]])
    e_art = sprites.Art(sprites.AIRCRAFT[enemy["key"]]["grid"], sprites.LIVERIES[enemy["livery"]])
    p_noz = sprites.nozzle_x(player["key"])
    e_noz = sprites.nozzle_x(enemy["key"])
    p_can = sprites.canopy_center(player["key"])[0]
    e_can = sprites.canopy_center(enemy["key"])[0]

    # contrails
    _contrail(buf, 0, px - 2, base_y + bob_p + 6)
    _contrail(buf, ex + 42, buf.w, base_y + bob_e + 6)

    _draw_jet(buf, p_art, px + shake_x, base_y + bob_p + shake_y, False, p_noz, p_can, t + frame)
    _draw_jet(buf, e_art, ex + shake_x, base_y + bob_e + shake_y, True, e_noz, e_can, t + frame + 3)

    # ---- missiles -----------------------------------------------------
    for ev in events:
        fire_t = ev["t"] - MISSILE_FLIGHT
        dt = t - fire_t
        if 0 <= dt <= MISSILE_FLIGHT:
            k = dt / MISSILE_FLIGHT
            ax = px + 38 if ev["by"] == 0 else ex + 2
            dx = ex + 2 if ev["by"] == 0 else px + 38
            mx = ax + (dx - ax) * k
            my = base_y + 9 + math.sin(k * math.pi) * (4 if ev["by"] == 0 else -4)
            for i in range(4):
                buf.px(int(mx) - (i if ev["by"] == 0 else -i), int(my) + (i % 2),
                       0xFFF3C4 if i == 0 else mix(0xFFC24A, SKY_BOT, i / 4))
            # smoke trail
            for i in range(5, 12):
                tx = int(mx) - (i if ev["by"] == 0 else -i)
                buf.px(tx, int(my) + (i % 2), mix(0xD8E4F0, SKY_BOT, min(0.9, i / 12)))

    # ---- explosions / damage -------------------------------------------
    for ev in events:
        age = t - ev["t"]
        if 0 <= age <= 0.45 and ev["hit"]:
            x = ex + 18 if ev["by"] == 0 else px + 20
            y = base_y + 8
            _explosion(buf, x, y, age, big=ev["special"] or ev["crit"])
        if 0 <= age <= 0.7 and ev["hit"]:
            x = ex + 10 if ev["by"] == 0 else px + 10
            y = base_y - 2 - int(age * 12)
            col = 0xFFC24A if not ev["crit"] else 0xFF6A4A
            txt = ("-%d" % ev["dmg"])
            font.draw_text(buf, x, y, txt, col, shadow=0x0A1018)
        if 0 <= age <= 0.45 and not ev["hit"]:
            font.draw_text(buf, (ex if ev["by"] == 0 else px) + 14, base_y - 3,
                           "MISS", 0x9FB6D4, shadow=0x0A1018)

    # ---- FOX 2 callouts --------------------------------------------------
    for ev in events:
        dt = t - (ev["t"] - MISSILE_FLIGHT)
        if 0 <= dt <= 0.5:
            x = 5 if ev["by"] == 0 else buf.w - 5 - font.micro_width("FOX 2")
            if int(t * 10) % 2 == 0 or dt > 0.2:
                font.draw_micro(buf, x, 11, "FOX 2", 0xFFC24A)

    # ---- HUD --------------------------------------------------------------
    php, ehp = hp_at(sim, t)
    _hud_row(buf, 1, enemy["faction"], factions.name(enemy["faction"]), ehp / enemy["hp"])
    _hud_row(buf, 57, player["faction"], factions.name(player["faction"]), php / player["hp"])

    # footer - our nation, their nation, and the tactic in play
    tac = TACTICS.get(sim["tactic"], TACTICS["balanced"])
    font.draw_micro(buf, 2, 67, tac["name"][:3], 0x7FE3FF)
    match = "%s VS %s" % (factions.code(player["faction"]), factions.code(enemy["faction"]))
    font.draw_micro(buf, (buf.w - font.micro_width(match)) // 2, 67, match, 0xFFE0A0)
    rd = "R%d" % sim["rounds"]
    font.draw_micro(buf, buf.w - 2 - font.micro_width(rd), 67, rd, 0x7FE3FF)
    if t > end_t - OUTRO + 0.5:
        win = sim["winner"] == 0
        label = "MISSION COMPLETE" if win else "MISSION FAILED"
        col = 0x6BFF9E if win else 0xE8564A
        if int(t * 4) % 2 == 0 or t > end_t - 1.0:
            buf.rect(0, 27, buf.w, 11, 0x060C14)
            buf.hline(0, buf.w - 1, 27, 0x1E3550)
            buf.hline(0, buf.w - 1, 37, 0x1E3550)
            font.draw_text_center(buf, buf.w // 2, 29, label, col, shadow=0x000000)
