"""Render selected screens at 8x for close-up inspection.

Usage: python dev_zoom.py briefing hangar result allegiance
"""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acegotchi import dogfight, factions, screens
from acegotchi.pixel import PixBuf
from acegotchi.screens import (BriefingScreen, FactionScreen, FleetScreen,
                               HangarScreen, HomeScreen, MenuScreen,
                               ResultScreen, W, H)
from acegotchi.state import Game

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")


class FakeSound:
    def play(self, name):
        pass


class FakeApp:
    def __init__(self, game):
        self.game = game
        self.t = 6.0
        self.frame = 40
        self.sound = FakeSound()

    def toast(self, *a, **k):
        pass

    def push(self, s):
        s.enter(self)

    def pop(self):
        pass

    def replace(self, s):
        s.enter(self)

    def go_home(self):
        pass

    def launch_sortie(self, e, t):
        pass

    def finish_sortie(self, sim):
        return None


def make_app():
    g = Game()
    g.data["credits"] = 1240
    g.data["faction"] = "osea"
    g.airframe["xp"] = 260
    g.data["unlocked"] = ["f15c", "f14d", "mig29"]
    g.data["stats"] = {"fuel": 68, "morale": 54, "condition": 81, "ammo": 70}
    return FakeApp(g)


def main():
    names = sys.argv[1:] or ["home", "briefing", "result", "hangar", "fleet", "allegiance"]
    root = tk.Tk()
    root.withdraw()
    app = make_app()
    for name in names:
        b = PixBuf(W, H, 0)
        sim = None
        if name == "home":
            s = HomeScreen()
        elif name == "menu":
            s = MenuScreen()
            s.sel = 10
            s.scroll = 7
        elif name == "briefing":
            s = BriefingScreen()
            s.enter(app)
            s.tactic_i = 0
        elif name == "result":
            s = None
        elif name == "hangar":
            s = HangarScreen()
            s.enter(app)
        elif name == "fleet":
            s = FleetScreen()
            s.enter(app)
        elif name == "fleetback":
            s = FleetScreen()
            s.enter(app)
            s.sel = len(s.keys)
            s.scroll = max(0, min(s.sel, s.total - 3))
        elif name == "allegiance":
            s = FactionScreen()
            s.enter(app)
            s.sel = 2
        elif name == "battle":
            s = None
        if sim is None and s is not None:
            s.draw(b, app)
        if name == "result":
            p = app.game.player_payload()
            e = app.game.make_enemy(faction="yuktobania")
            sim = dogfight.simulate(p, e, "balanced")
            entry = dict(credits=142, xp=38, rounds=sim["rounds"],
                         sim=sim)
            rs = ResultScreen(sim, entry)
            rs.enter(app)
            rs.draw(b, app)
        if name == "battle":
            p = app.game.player_payload()
            e = app.game.make_enemy(faction="belka")
            sim = dogfight.simulate(p, e, "evasive")
            latest = sim["events"][2]
            dogfight.render(b, sim, latest["t"] + 0.1, 10)
        img = tk.PhotoImage(width=W, height=H)
        img.put(b.to_photo_data())
        path = os.path.join(OUT, "zoom_%s.png" % name)
        img.zoom(8).write(path, format="png")
        print("wrote", path)
    root.destroy()


if __name__ == "__main__":
    main()
