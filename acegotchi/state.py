"""Game state: stats, decay, progression, upgrades and persistence."""

import json
import os
import random
import time

from . import factions

SAVE_VERSION = 3

# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------
FLEET = {
    "f15c": dict(
        name="F-15C EAGLE", short="F-15C", livery="galm", cost=0, req=1,
        blurb="GALM FLIGHT", hp=100, atk=13, agi=10, dfn=12,
        bio="A twin-engine air superiority fighter. Balanced, forgiving, and\n"
            "the machine every ace learns on.",
    ),
    "f14d": dict(
        name="F-14D TOMCAT", short="F-14D", livery="osea", cost=400, req=3,
        blurb="RAZGRIZ", hp=112, atk=14, agi=9, dfn=13,
        bio="Heavy fleet defender with swing wings. Slow to turn, hard to\n"
            "shoot down.",
    ),
    "mig29": dict(
        name="MIG-29A FULCRUM", short="MIG-29", livery="yukt", cost=520, req=5,
        blurb="YUKTOBANIAN AF", hp=90, atk=13, agi=15, dfn=8,
        bio="Lightning-fast interceptor. Fragile, but it dances around\n"
            "heavier opponents.",
    ),
    "a10a": dict(
        name="A-10A WARTHOG", short="A-10A", livery="ustio", cost=650, req=6,
        blurb="WARDEN FLIGHT", hp=150, atk=11, agi=4, dfn=18,
        bio="Flying gun. Cannot dodge to save its life, but it soaks up\n"
            "punishment and never misses twice.",
    ),
    "su37": dict(
        name="SU-37 TERMINATOR", short="SU-37", livery="erusea", cost=1000, req=9,
        blurb="YELLOW 13", hp=94, atk=17, agi=16, dfn=9,
        bio="Thrust-vectoring dogfighter with canards. The most agile\n"
            "airframe in the fleet.",
    ),
    "f22a": dict(
        name="F-22A RAPTOR", short="F-22A", livery="belka", cost=1500, req=12,
        blurb="MOBIUS 1", hp=108, atk=18, agi=15, dfn=12,
        bio="Fifth-generation stealth fighter. Expensive, lethal, and\n"
            "almost impossible to lock onto.",
    ),
}

UPGRADES = {
    "gun": dict(name="WEAPONS", short="GUN", desc="+3 ATK"),
    "armor": dict(name="ARMOR", short="ARM", desc="+12 HP"),
    "ecm": dict(name="ECM", short="ECM", desc="+2 AGI"),
}

RANKS = [
    (1, "RECRUIT"),
    (3, "WINGMAN"),
    (5, "FLIGHT LEAD"),
    (7, "SQUADRON LDR"),
    (10, "ACE"),
    (13, "ACE OF ACES"),
    (16, "LEGEND"),
]

ENEMY_CALLSIGNS = ["ACE", "RAID", "FLIGHT", "SQUADRON", "PATROL", "WING", "GUARD", "LANCE"]

TACTICS = {
    "aggressive": dict(name="AGGRESSIVE", atk=1.38, eva=0.92, taken=1.15, note="+ATK  -EVA"),
    "balanced": dict(name="BALANCED", atk=1.10, eva=1.00, taken=1.00, note="EVEN FIGHT"),
    "evasive": dict(name="EVASIVE", atk=0.86, eva=1.18, taken=0.92, note="+EVA  -ATK"),
}

CHATTER = [
    "AWACS: BANDITS 12 O'CLOCK.",
    "AWACS: ALL AIRCRAFT, GO.",
    "GALM 2: I'VE GOT YOUR SIX.",
    "AWACS: MISSILE INBOUND.",
    "TOWER: CLEARED TO LAUNCH.",
    "AWACS: GOOD KILL, PILOT.",
    "GALM 2: SOL SQUADRON!",
    "AWACS: RTB WHEN ABLE.",
    "TOWER: WATCH YOUR FUEL.",
    "AWACS: THE SKIES ARE YOURS",
]


def level_for_xp(xp):
    """Level curve: each level costs a little more than the last."""
    lvl = 1
    need = 35
    while xp >= need and lvl < 30:
        xp -= need
        lvl += 1
        need = 20 + lvl * 15
    return lvl


def xp_into_level(xp):
    lvl = 1
    need = 35
    while xp >= need and lvl < 30:
        xp -= need
        lvl += 1
        need = 20 + lvl * 15
    return xp, need


def rank_for(level):
    name = RANKS[0][1]
    for req, r in RANKS:
        if level >= req:
            name = r
    return name


def clamp(v, lo=0, hi=100):
    return lo if v < lo else hi if v > hi else v


# ---------------------------------------------------------------------------
def new_state(pilot="CIPHER"):
    now = time.time()
    return {
        "version": SAVE_VERSION,
        "pilot": pilot,
        "credits": 300,
        "created": now,
        "last_seen": now,
        "active": "f15c",
        "unlocked": ["f15c"],
        "faction": "osea",
        "aircraft": {k: {"xp": 0, "up": {"gun": 0, "armor": 0, "ecm": 0}} for k in FLEET},
        "stats": {"fuel": 74, "morale": 70, "condition": 92, "ammo": 60},
        "career": {"sorties": 0, "kills": 0, "losses": 0, "earned": 0},
        "cool": {},
        "log": [],
        "settings": {"sound": True, "topmost": True, "scale": 3, "x": None, "y": None},
        "flags": {"booted": False, "grounded_warned": False},
        "last_sortie": None,
    }


def _defaults(data):
    base = new_state()
    for k, v in base.items():
        if k not in data:
            data[k] = v
        elif isinstance(v, dict) and isinstance(data[k], dict):
            for kk, vv in v.items():
                data[k].setdefault(kk, vv)
    data["version"] = SAVE_VERSION
    return data


class Game:
    """Wrapper around the save dict with all the rules in one place."""

    def __init__(self, data=None):
        self.data = _defaults(data or new_state())
        self._dirty = False

    # -- convenience -----------------------------------------------------
    @property
    def stats(self):
        return self.data["stats"]

    @property
    def settings(self):
        return self.data["settings"]

    @property
    def active_key(self):
        return self.data["active"]

    @property
    def airframe(self):
        return self.data["aircraft"][self.data["active"]]

    @property
    def level(self):
        return level_for_xp(self.airframe["xp"])

    @property
    def best_level(self):
        return max(level_for_xp(a["xp"]) for a in self.data["aircraft"].values())

    @property
    def rank(self):
        return rank_for(self.level)

    def meta(self, key=None):
        return FLEET[key or self.data["active"]]

    def is_unlocked(self, key):
        return key in self.data["unlocked"]

    def upgrade_cost(self, line):
        lvl = self.airframe["up"][line]
        return 90 + lvl * 70

    def loadout_bonus(self, key=None):
        up = self.data["aircraft"][key or self.data["active"]]["up"]
        return up["gun"] * 3, up["armor"] * 12, up["ecm"] * 2

    def combat_stats(self, key=None):
        key = key or self.data["active"]
        m = FLEET[key]
        gun, armor, ecm = self.loadout_bonus(key)
        lvl = level_for_xp(self.data["aircraft"][key]["xp"])
        hp = m["hp"] + armor + lvl * 4
        atk = m["atk"] + gun + lvl * 0.8
        agi = m["agi"] + ecm + lvl * 0.5
        dfn = m["dfn"] + lvl * 0.35
        return dict(hp=hp, atk=atk, agi=agi, dfn=dfn, level=lvl, name=m["name"])

    # -- factions ----------------------------------------------------------
    @property
    def faction(self):
        return self.data.get("faction", "osea")

    def set_faction(self, key):
        self.data["faction"] = key
        self._dirty = True

    def livery(self, key=None):
        """Player aircraft wear the colours of their own nation."""
        return factions.get(self.faction)["livery"]

    def player_payload(self):
        st = self.combat_stats()
        return dict(
            key=self.data["active"],
            name=self.data["pilot"],
            callsign=self.meta()["blurb"],
            faction=self.faction,
            livery=self.livery(),
            hp=st["hp"], atk=st["atk"], agi=st["agi"], dfn=st["dfn"],
            level=st["level"], is_player=True,
        )

    def make_enemy(self, rng=None, faction=None):
        rng = rng or random
        fac = faction or rng.choice(factions.other_factions(self.faction))
        air = rng.choice(list(FLEET.keys()))
        lvl = max(1, self.best_level + rng.choice((-1, 0, 0, 1)))
        hp = FLEET[air]["hp"] * (0.86 + 0.055 * lvl) * rng.uniform(0.92, 1.08)
        atk = FLEET[air]["atk"] * (0.90 + 0.050 * lvl) * rng.uniform(0.92, 1.08)
        agi = FLEET[air]["agi"] * (0.92 + 0.025 * lvl) * rng.uniform(0.95, 1.05)
        dfn = FLEET[air]["dfn"] * (0.92 + 0.022 * lvl) * rng.uniform(0.95, 1.05)
        callsign = rng.choice(ENEMY_CALLSIGNS)
        return dict(
            key=air,
            name="%s %s" % (factions.adjective(fac), callsign),
            callsign=air,
            faction=fac,
            livery=factions.get(fac)["livery"],
            hp=hp, atk=atk, agi=agi, dfn=dfn,
            level=lvl,
            is_player=False,
        )

    # -- time --------------------------------------------------------------
    def apply_offline_decay(self, now=None):
        now = now or time.time()
        last = self.data.get("last_seen", now)
        hours = max(0.0, min(18.0, (now - last) / 3600.0))
        if hours <= 0:
            return 0.0
        s = self.stats
        s["fuel"] = clamp(s["fuel"] - hours * 5.2)
        s["morale"] = clamp(s["morale"] - hours * 3.1)
        s["condition"] = clamp(s["condition"] - hours * (1.1 + (0.9 if s["fuel"] < 25 else 0)))
        self.data["last_seen"] = now
        self._dirty = True
        return hours

    def tick(self, dt):
        """Live decay while the app is open (dt in seconds)."""
        s = self.stats
        s["fuel"] = clamp(s["fuel"] - dt * (5.2 / 3600.0))
        s["morale"] = clamp(s["morale"] - dt * (3.1 / 3600.0))
        s["condition"] = clamp(s["condition"] - dt * ((1.1 + (0.9 if s["fuel"] < 25 else 0)) / 3600.0))
        self.data["last_seen"] = time.time()
        self._dirty = True

    # -- derived state -----------------------------------------------------
    def mood(self):
        s = self.stats
        if s["condition"] < 22:
            return "CRITICAL", 0xE8564A
        if s["fuel"] < 20:
            return "HUNGRY", 0xFFC24A
        if s["morale"] < 22:
            return "LOW MORALE", 0xFFC24A
        if s["condition"] < 45:
            return "DAMAGED", 0xFFC24A
        if s["fuel"] > 78 and s["morale"] > 72 and s["condition"] > 70:
            return "READY", 0x6BFF9E
        return "STABLE", 0x7FE3FF

    def can_sortie(self):
        s = self.stats
        return s["fuel"] >= 18 and s["condition"] >= 20 and s["ammo"] >= 30

    def sortie_blocker(self):
        s = self.stats
        if s["condition"] < 20:
            return "AIRFRAME DAMAGED"
        if s["ammo"] < 30:
            return "NO AMMUNITION"
        if s["fuel"] < 18:
            return "FUEL TOO LOW"
        return None

    # -- actions -----------------------------------------------------------
    def cooldown_left(self, key, now=None):
        now = now or time.time()
        until = self.data["cool"].get(key, 0)
        return max(0.0, until - now)

    def _set_cooldown(self, key, secs):
        self.data["cool"][key] = time.time() + secs

    def act(self, key):
        """Run a care action. Returns (ok, message, sound)."""
        s = self.stats
        now = time.time()
        if key == "feed":
            if s["fuel"] >= 96:
                return False, "FUEL TANKS FULL", "error"
            s["fuel"] = clamp(s["fuel"] + 26)
            s["morale"] = clamp(s["morale"] + 2)
            self._set_cooldown("feed", 25)
            return True, "+26 FUEL", "feed"
        if key == "rest":
            s["condition"] = clamp(s["condition"] + 14)
            s["morale"] = clamp(s["morale"] + 8)
            self._set_cooldown("rest", 200)
            return True, "AIRFRAME RESTED", "rest"
        if key == "polish":
            s["condition"] = clamp(s["condition"] + 10)
            s["morale"] = clamp(s["morale"] + 5)
            self._set_cooldown("polish", 150)
            return True, "AIRFRAME POLISHED", "clean"
        if key == "train":
            if s["fuel"] < 12:
                return False, "NEEDS FUEL FIRST", "error"
            s["fuel"] = clamp(s["fuel"] - 7)
            s["condition"] = clamp(s["condition"] - 4)
            gain = 14 + self.level
            self.airframe["xp"] += gain
            self._set_cooldown("train", 70)
            return True, "+%d XP" % gain, "train"
        if key == "rearm":
            if s["ammo"] >= 99:
                return False, "MAGAZINES FULL", "error"
            cost = 45
            if self.data["credits"] < cost:
                return False, "NOT ENOUGH CREDITS", "error"
            self.data["credits"] -= cost
            s["ammo"] = 100
            return True, "REARMED", "confirm"
        if key == "repair":
            if s["condition"] >= 96:
                return False, "NO REPAIRS NEEDED", "error"
            cost = 90
            if self.data["credits"] < cost:
                return False, "NOT ENOUGH CREDITS", "error"
            self.data["credits"] -= cost
            s["condition"] = clamp(s["condition"] + 42)
            return True, "AIRFRAME REPAIRED", "confirm"
        return False, "UNKNOWN", "error"

    def buy_upgrade(self, line):
        if self.airframe["up"][line] >= 5:
            return False, "MAX LEVEL"
        cost = self.upgrade_cost(line)
        if self.data["credits"] < cost:
            return False, "NEED %d CR" % cost
        self.data["credits"] -= cost
        self.airframe["up"][line] += 1
        return True, "UPGRADED"

    def unlock(self, key):
        if key in self.data["unlocked"]:
            return True, "OWNED"
        m = FLEET[key]
        if self.best_level < m["req"]:
            return False, "REQ LEVEL %d" % m["req"]
        if self.data["credits"] < m["cost"]:
            return False, "NEED %d CR" % m["cost"]
        self.data["credits"] -= m["cost"]
        self.data["unlocked"].append(key)
        return True, "ACQUIRED"

    def select(self, key):
        if key in self.data["unlocked"]:
            self.data["active"] = key
            return True
        return False

    # -- dogfight results ---------------------------------------------------
    def finish_sortie(self, enemy_name, won, rounds, hp_left, credits, xp):
        s = self.stats
        s["ammo"] = clamp(s["ammo"] - 30)
        s["fuel"] = clamp(s["fuel"] - 8)
        self.data["credits"] += credits
        self.airframe["xp"] += xp
        self.data["career"]["sorties"] += 1
        if won:
            self.data["career"]["kills"] += 1
            s["morale"] = clamp(s["morale"] + 9)
            self.data["career"]["earned"] += credits
        else:
            self.data["career"]["losses"] += 1
            s["condition"] = clamp(s["condition"] - 16)
            s["morale"] = clamp(s["morale"] - 11)
        entry = dict(t=time.time(), enemy=enemy_name, won=won, rounds=rounds,
                     credits=credits, xp=xp, hp=hp_left)
        self.data["log"].insert(0, entry)
        del self.data["log"][6:]
        self.data["last_sortie"] = entry
        self._dirty = True
        return entry


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_path(folder):
    return os.path.join(folder, "save.json")


def load(folder):
    path = save_path(folder)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("version") != SAVE_VERSION:
            data = _defaults(data)
        return Game(_defaults(data))
    except (OSError, ValueError):
        return Game()


def save(game, folder):
    path = save_path(folder)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(game.data, fh, indent=1)
        os.replace(tmp, path)
        game._dirty = False
        return True
    except OSError:
        return False
