"""Render every LCD screen to a contact sheet PNG for visual checking."""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acegotchi import dogfight, factions, screens, sprites
from acegotchi.pixel import PixBuf, mix
from acegotchi.screens import (BootScreen, BriefingScreen, HomeScreen, MenuScreen,
                               HangarScreen, FleetScreen, FactionScreen,
                               BattleScreen, ResultScreen, W, H)
from acegotchi.state import Game, TACTICS

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")


class FakeSound:
    def play(self, name):
        pass


class FakeApp:
    def __init__(self, game):
        self.game = game
        self.t = 3.0
        self.frame = 0
        self.sound = FakeSound()
        self.stack = []
        self.screen = None

    def toast(self, text, colour=0xFFFFFF):
        self._toast = (text, colour)

    def push(self, s):
        self.stack.append(s)
        self.screen = s
        s.enter(self)

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
        self.screen = self.stack[-1]

    def replace(self, s):
        if self.stack:
            self.stack[-1] = s
        else:
            self.stack.append(s)
        self.screen = s
        s.enter(self)

    def go_home(self):
        self.stack = []
        self.screen = None

    def launch_sortie(self, enemy, tactic):
        pass

    def finish_sortie(self, sim):
        return None


def blank():
    b = PixBuf(W, H, 0x000000)
    return b


def main():
    root = tk.Tk()
    root.withdraw()

    g = Game()
    g.data["credits"] = 1240
    g.data["faction"] = "osea"
    g.airframe["xp"] = 260
    g.data["unlocked"] = ["f15c", "f14d", "mig29"]
    g.data["stats"] = {"fuel": 68, "morale": 54, "condition": 81, "ammo": 70}
    app = FakeApp(g)

    shots = []

    def shot(screen, label, t=3.0, setup=None):
        app.t = t
        if setup:
            setup(screen)
        b = blank()
        if hasattr(screen, "draw"):
            screen.draw(b, app)
        shots.append((label, b))

    boot = BootScreen()
    boot.t0 = 0.0
    shot(boot, "BOOT", 1.9)

    home = HomeScreen()
    shot(home, "HOME", 3.0)

    menu = MenuScreen()
    shot(menu, "MENU", 3.0)

    br = BriefingScreen()
    br.enter(app)
    br.enemy = g.make_enemy()
    shot(br, "BRIEFING", 3.0)

    # battle, a few moments in
    payload = g.player_payload()
    enemy = g.make_enemy()
    sim = dogfight.simulate(payload, enemy, "balanced")
    for label, tt in (("BATTLE 1", 0.8), ("BATTLE 2", 2.4), ("BATTLE 3", sim["end_t"] - 0.9)):
        b = blank()
        dogfight.render(b, sim, tt, 0)
        shots.append((label, b))

    res = ResultScreen(sim, dict(credits=142, xp=38, rounds=sim["rounds"]))
    shot(res, "RESULT", 5.0)

    hangar = HangarScreen()
    hangar.enter(app)
    shot(hangar, "HANGAR", 3.0)

    fleet = FleetScreen()
    fleet.enter(app)
    shot(fleet, "FLEET", 3.0)

    fac = FactionScreen()
    fac.enter(app)
    shot(fac, "ALLEGIANCE", 3.0)
    fac.sel = 5
    shot(fac, "ALLEGIANCE 2", 3.0)

    # contact sheet
    cols = 3
    pad = 6
    label_h = 10
    cell_w = W + pad
    cell_h = H + pad + label_h
    rows = (len(shots) + cols - 1) // cols
    sheet = PixBuf(cols * cell_w + pad, rows * cell_h + pad, 0x1A1F28)
    for i, (label, b) in enumerate(shots):
        cx = pad + (i % cols) * cell_w
        cy = pad + (i // cols) * cell_h
        sheet.blit(b, cx, cy)
        screens.font.draw_micro(sheet, cx + 1, cy + H + 3, label, 0xFFC24A)

    img = tk.PhotoImage(width=sheet.w, height=sheet.h)
    img.put(sheet.to_photo_data())
    os.makedirs(OUT, exist_ok=True)
    img.zoom(4).write(os.path.join(OUT, "screens.png"), format="png")
    print("wrote screens.png", sheet.w, sheet.h, "shots:", len(shots))
    root.destroy()


if __name__ == "__main__":
    main()
