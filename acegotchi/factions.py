"""The six nations of the Ace Gotchi world.

Every sortie is fought *as* one faction *against* another, and the dogfight
HUD always shows both flags so it is never ambiguous who is who.
"""

from .pixel import TRANSPARENT

FACTION_ORDER = ["osea", "belka", "yuktobania", "erusea", "fcu", "sotoa"]

FACTIONS = {
    "osea": dict(
        name="OSEA", code="OSEA", adj="OSEAN", livery="osea",
        c1=0x2F6FD6, c2=0xEAF3FF, text=0x6FB4FF,
        motto="DEFEND THE CONTINENT",
        bio="PACIFIC SUPERPOWER.\nBIG AIR FORCE,\nMANY WARS.",
    ),
    "belka": dict(
        name="BELKA", code="BELK", adj="BELKAN", livery="belka",
        c1=0x8E939F, c2=0xE03A3A, text=0xFF8A80,
        motto="THE NORTH REMEMBERS",
        bio="BITTER NORTH. ITS ACES\nNEVER FORGAVE OSEA.",
    ),
    "yuktobania": dict(
        name="YUKTOBANIA", code="YUKT", adj="YUKTOBANIAN", livery="yukt",
        c1=0x6E7F63, c2=0xE0C060, text=0xFFD98A,
        motto="STRENGTH THROUGH STEEL",
        bio="VAST EASTERN FED.\nHEAVY BOMBS ONLY.",
    ),
    "erusea": dict(
        name="ERUSEA", code="ERUS", adj="ERUSEAN", livery="erusea",
        c1=0x8A6E86, c2=0xE2A0E8, text=0xF0B6FF,
        motto="FOR THE PRINCESS",
        bio="PROUD KINGDOM.\nBRILLIANT, DOOMED\nPILOTS.",
    ),
    "fcu": dict(
        name="FCU", code="FCU", adj="FCU", livery="fcu",
        c1=0xC0A878, c2=0x3FD0C0, text=0x7FE3D0,
        motto="UNITY OF THE CENTRE",
        bio="COALITION AIR FORCE\nHELD TOGETHER BY\nPAPERWORK.",
    ),
    "sotoa": dict(
        name="SOTOA", code="SOTA", adj="SOTOAN", livery="sotoa",
        c1=0x4E7A5A, c2=0xF0F0F0, text=0x9BE07A,
        motto="GREEN SKIES, SHARP WINGS",
        bio="SMALL HIGHLAND\nNATION. EVERY PILOT\nA VOLUNTEER.",
    ),
}

# 5x5 national emblems, drawn onto the little flag
EMBLEMS = {
    "osea": ("..#..", ".###.", "#####", ".###.", "..#.."),
    "belka": ("#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "yuktobania": ("#####", "#####", "..#..", "..#..", "..#.."),
    "erusea": ("..#..", ".#.#.", "#...#", ".#.#.", "..#.."),
    "fcu": ("..#..", ".###.", "##.##", ".###.", "..#.."),
    "sotoa": (".###.", "#####", "#####", "#####", ".###."),
}


def get(key):
    return FACTIONS.get(key, FACTIONS["osea"])


def name(key):
    return get(key)["name"]


def code(key):
    return get(key).get("code", get(key)["name"][:4])


def adjective(key):
    return get(key)["adj"]


def colour(key):
    return get(key)["text"]


def flag_palette(key):
    f = get(key)
    return {"#": f["c2"], ".": TRANSPARENT}


def draw_flag(buf, x, y, key, w=9, h=6, border=None):
    """Draw a small national flag/banner."""
    f = get(key)
    buf.rect(x, y, w, h, f["c1"])
    if border is not None:
        buf.box(x, y, w, h, f["c1"], border)
    em = EMBLEMS.get(key, EMBLEMS["osea"])
    ex = x + (w - 5) // 2
    ey = y + (h - 5) // 2
    buf.blit_art(em, ex, ey, {"#": f["c2"]})


def other_factions(key):
    return [k for k in FACTION_ORDER if k != key]
