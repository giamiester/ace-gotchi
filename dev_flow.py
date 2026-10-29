"""Headless-ish playthrough test: drives the real App through every screen.

Run with: python dev_flow.py
Creates a throwaway save folder so your real save is untouched.
"""
import os
import shutil
import sys
import tempfile
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acegotchi import app as appmod, screens, state


def step(app, label):
    app.t += 0.05
    app.screen.tick(0.05, app)
    app.render()
    print("  %-28s -> %s" % (label, type(app.screen).__name__))


def main():
    tmp = tempfile.mkdtemp(prefix="acegotchi_")
    root = tk.Tk()
    try:
        a = appmod.App(root, tmp)
        a.sound.set_enabled(False)
        print("boot:", type(a.screen).__name__)
        assert isinstance(a.screen, screens.BootScreen)

        for s in (2, 4, 5, 3):
            a.set_scale(s)
            print("  scale %dx ok (%dx%d)" % (s, a.canvas.winfo_reqwidth(), a.canvas.winfo_reqheight()))
        assert a.scale == 3

        a.screen.t0 = a.t - 9
        step(a, "boot timeout")
        assert isinstance(a.screen, screens.FactionScreen), a.screen

        a.screen.press("C", a)
        a.screen.press("B", a)
        for _ in range(25):
            step(a, "pledge allegiance")
        assert isinstance(a.screen, screens.HomeScreen), a.screen

        a.handle_key("B")
        assert isinstance(a.screen, screens.MenuScreen)
        print("  menu open")

        # feed (selection starts at FEED)
        a.handle_key("B")
        print("  feed ->", a.toast_text)
        assert a.game.stats["fuel"] > 60

        # travel down to SORTIE (index 6)
        for _ in range(6):
            a.handle_key("C")
        assert a.screen.sel == 6, a.screen.sel
        a.handle_key("B")
        assert isinstance(a.screen, screens.BriefingScreen), a.screen
        print("  briefing:", a.screen.enemy["faction"], a.screen.enemy["name"])

        a.handle_key("C")   # change tactic
        a.handle_key("B")   # launch
        assert isinstance(a.screen, screens.BattleScreen), a.screen
        print("  battle started")

        for i in range(600):
            step(a, "battle frame %d" % i) if i % 100 == 0 else None
            a.t += 0.05
            a.screen.tick(0.05, a)
            if isinstance(a.screen, screens.ResultScreen):
                break
        a.render()
        assert isinstance(a.screen, screens.ResultScreen), a.screen
        won = a.screen.sim["winner"] == 0
        print("  result: %s  credits=%s xp=%s" % (
            "WIN" if won else "LOSS", a.screen.entry["credits"], a.screen.entry["xp"]))

        a.handle_key("B")
        assert isinstance(a.screen, screens.HomeScreen)

        # rearm + repair from the menu (care economy)
        ammo_before = a.game.stats["ammo"]
        a.game.stats["condition"] = 40
        a.handle_key("B")                       # open menu
        for _ in range(4):
            a.handle_key("C")                   # -> REARM
        a.handle_key("B")
        print("  rearm %d -> %d (%s)" % (ammo_before, a.game.stats["ammo"], a.toast_text))
        assert a.game.stats["ammo"] == 100
        a.handle_key("C")                       # -> REPAIR
        a.handle_key("B")
        print("  repair 40 -> %d (%s)" % (a.game.stats["condition"], a.toast_text))
        assert a.game.stats["condition"] > 40

        # hangar purchase
        for _ in range(2):
            a.handle_key("C")                   # -> HANGAR (index 7)
        assert a.screen.sel == 7, a.screen.sel
        a.handle_key("B")
        assert isinstance(a.screen, screens.HangarScreen)
        before = a.game.airframe["up"]["gun"]
        a.handle_key("B")
        print("  upgrade gun %d -> %d (%s)" % (before, a.game.airframe["up"]["gun"], a.toast_text))
        for _ in range(3):
            a.handle_key("C")          # back row
        a.handle_key("B")              # leave hangar
        assert isinstance(a.screen, screens.MenuScreen), a.screen

        # fleet
        a.handle_key("C")              # HANGAR -> FLEET
        a.handle_key("B")
        assert isinstance(a.screen, screens.FleetScreen), a.screen
        a.handle_key("C")
        print("  fleet sel:", a.screen.keys[a.screen.sel])
        a.handle_key("B")              # use / unlock the highlighted jet
        for _ in range(10):            # walk down to the BACK row
            if a.screen.sel == len(a.screen.keys):
                break
            a.handle_key("C")
        assert a.screen.sel == len(a.screen.keys), a.screen.sel
        a.handle_key("B")              # leave the fleet screen
        assert isinstance(a.screen, screens.MenuScreen), a.screen
        print("  fleet back ok")

        # allegiance: change nation
        a.screen = screens.HomeScreen()
        a.screen.enter(a)
        a.handle_key("B")
        for _ in range(9):
            a.handle_key("C")
        a.handle_key("B")
        assert isinstance(a.screen, screens.FactionScreen), a.screen
        a.handle_key("C")
        chosen = a.screen.order[a.screen.sel]
        a.handle_key("B")
        step(a, "confirm nation")
        assert a.game.faction == chosen, (a.game.faction, chosen)
        print("  faction now:", a.game.faction)

        a.save()
        path = state.save_path(tmp)
        assert os.path.exists(path)
        g2 = state.load(tmp)
        assert g2.faction == a.game.faction
        assert g2.data["credits"] == a.game.data["credits"]
        assert g2.data["career"]["sorties"] == a.game.data["career"]["sorties"]
        print("save reload ok:", g2.faction, g2.data["credits"], "CR",
              g2.data["career"]["sorties"], "sorties")
        print("FLOW OK")
    finally:
        try:
            root.destroy()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
