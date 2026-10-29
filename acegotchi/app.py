"""Tk application: frameless always-on-top device, input and main loop."""

import os
import sys
import time
import tkinter as tk

from . import dogfight, factions, screens, shell, sound, state
from .pixel import PixBuf, mix
from .screens import W as LCD_W, H as LCD_H

KEY = "#ff00ff"
FPS_MS = 66


class App:
    def __init__(self, root, folder):
        self.root = root
        self.folder = folder
        self.game = state.load(folder)
        self.game.apply_offline_decay()

        self.scale = max(2, min(5, int(self.game.settings.get("scale", 3))))
        self.sound = sound.Sound(self.game.settings.get("sound", True))
        self.t = 0.0
        self.frame = 0
        self.last = time.time()
        self.last_save = time.time()

        self.toast_text = ""
        self.toast_col = 0xFFFFFF
        self.toast_until = 0.0

        self.pressed = None
        self.hover = None
        self.dragging = False
        self.drag_off = (0, 0)
        self.led_on = True
        self.led_t = 0.0
        self._shell_key = None

        self._setup_window()
        self._build_images()
        self._bind()

        self.stack = [screens.BootScreen()]
        self.screen = self.stack[-1]
        self.screen.enter(self)

        self.render()
        self.root.after(FPS_MS, self.tick)

    # -- window -----------------------------------------------------------
    def _setup_window(self):
        r = self.root
        r.overrideredirect(True)
        r.attributes("-topmost", bool(self.game.settings.get("topmost", True)))
        try:
            r.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass
        r.configure(bg=KEY)
        r.title("Ace Gotchi")

        w, h = shell.W * self.scale, shell.H * self.scale
        self.canvas = tk.Canvas(r, width=w, height=h, bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack()

        x = self.game.settings.get("x")
        y = self.game.settings.get("y")
        if x is None or y is None:
            sw = r.winfo_screenwidth()
            sh = r.winfo_screenheight()
            x = sw - w - 60
            y = sh - h - 80
        x, y = self._clamp_pos(int(x), int(y), w, h)
        r.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def _clamp_pos(self, x, y, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(-w // 3, min(sw - w + w // 3, x))
        y = max(-h // 4, min(sh - h + h // 4, y))
        return x, y

    def _build_images(self):
        s = self.scale
        self.shell_src = tk.PhotoImage(width=shell.W, height=shell.H)
        self.lcd_src = tk.PhotoImage(width=LCD_W, height=LCD_H)
        self.shell_photo = None
        self.lcd_photo = None
        for attr in ("shell_item", "lcd_item"):
            if hasattr(self, attr):
                delattr(self, attr)
        self._shell_key = None
        self.canvas.delete("all")
        self._paint_shell(force=True)
        self.shell_item = self.canvas.create_image(0, 0, anchor="nw", image=self.shell_photo)
        self.lcd_item = self.canvas.create_image(
            shell.SCREEN_X * s, shell.SCREEN_Y * s, anchor="nw", image=self.lcd_photo)

    def _paint_shell(self, force=False):
        key = (self.pressed, self.hover, self.led_on)
        if not force and key == self._shell_key:
            return
        self._shell_key = key
        buf = shell.render(pressed=self.pressed, led_on=self.led_on, hover=self.hover)
        self.shell_src.put(buf.to_photo_data(KEY))
        self.shell_photo = self.shell_src.zoom(self.scale)
        if hasattr(self, "shell_item"):
            self.canvas.itemconfigure(self.shell_item, image=self.shell_photo)

    def set_scale(self, s):
        s = max(2, min(5, int(s)))
        self.scale = s
        self.game.settings["scale"] = s
        w, h = shell.W * s, shell.H * s
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.canvas.configure(width=w, height=h)
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self._build_images()
        self.render()
        self.save()

    # -- input ------------------------------------------------------------
    def _bind(self):
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Button-3>", self.on_menu)
        c.bind("<Motion>", self.on_motion)
        c.bind("<Enter>", lambda e: c.focus_set())
        self.root.bind("<KeyPress>", self.on_key)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def _logical(self, event):
        return event.x / self.scale, event.y / self.scale

    def on_press(self, event):
        self.root.focus_force()
        lx, ly = self._logical(event)
        hit = shell.hit(lx, ly)
        if hit:
            self.pressed = hit
            self.sound.play("click")
            self._paint_shell()
        else:
            self.dragging = True
            self.drag_off = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def on_motion(self, event):
        lx, ly = self._logical(event)
        h = shell.hit(lx, ly)
        if h != self.hover:
            self.hover = h
            self._paint_shell()
            self.canvas.configure(cursor="hand2" if h else "arrow")

    def on_drag(self, event):
        if not self.dragging:
            return
        x = event.x_root - self.drag_off[0]
        y = event.y_root - self.drag_off[1]
        self.root.geometry("+%d+%d" % (x, y))

    def on_release(self, event):
        if self.dragging:
            self.dragging = False
            x, y = self.root.winfo_x(), self.root.winfo_y()
            self.game.settings["x"] = x
            self.game.settings["y"] = y
            self.save()
            return
        if self.pressed:
            key = self.pressed
            self.pressed = None
            self._paint_shell()
            lx, ly = self._logical(event)
            if shell.hit(lx, ly) == key:
                self.handle_key(key)

    def on_key(self, event):
        k = event.keysym.lower()
        if k in ("a", "left"):
            self.handle_key("A")
        elif k in ("b", "return", "space"):
            self.handle_key("B")
        elif k in ("c", "right"):
            self.handle_key("C")
        elif k == "escape":
            self.on_menu(event)
        elif k == "q" and (event.state & 0x4):
            self.quit()

    def on_menu(self, event=None):
        m = tk.Menu(self.root, tearoff=0, bg="#141C26", fg="#CFE6F5",
                    activebackground="#254055", activeforeground="#FFFFFF",
                    bd=0, font=("Consolas", 9))
        m.add_command(label="Save now", command=self.save)
        m.add_checkbutton(label="Always on top", onvalue=1, offvalue=0,
                          variable=tk.IntVar(value=1 if self.game.settings.get("topmost") else 0),
                          command=self.toggle_topmost)
        m.add_checkbutton(label="Sound", onvalue=1, offvalue=0,
                          variable=tk.IntVar(value=1 if self.game.settings.get("sound") else 0),
                          command=self.toggle_sound)
        m.add_separator()
        size = tk.Menu(m, tearoff=0, bg="#141C26", fg="#CFE6F5",
                       activebackground="#254055", activeforeground="#FFFFFF", bd=0)
        for s in (2, 3, 4, 5):
            size.add_command(label="%dx" % s, command=lambda v=s: self.set_scale(v))
        m.add_cascade(label="Size", menu=size)
        m.add_command(label="Pause care", command=self.toggle_pause)
        m.add_separator()
        m.add_command(label="Reset device...", command=self.reset_confirm)
        m.add_command(label="Quit", command=self.quit)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def toggle_topmost(self):
        v = not bool(self.game.settings.get("topmost", True))
        self.game.settings["topmost"] = v
        self.root.attributes("-topmost", v)
        self.save()

    def toggle_sound(self):
        v = not bool(self.game.settings.get("sound", True))
        self.game.settings["sound"] = v
        self.sound.set_enabled(v)
        self.save()

    def toggle_pause(self):
        self.paused = not getattr(self, "paused", False)
        self.toast("CARE PAUSED" if self.paused else "CARE RESUMED", 0xFFC24A)

    def reset_confirm(self):
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.configure(bg="#0C1219")
        w, h = 240, 96
        x = self.root.winfo_x() + shell.W * self.scale // 2 - w // 2
        y = self.root.winfo_y() + shell.H * self.scale // 2 - h // 2
        top.geometry("%dx%d+%d+%d" % (w, h, x, y))
        tk.Label(top, text="Reset the device?", bg="#0C1219", fg="#FFFFFF",
                 font=("Consolas", 11, "bold")).pack(pady=(14, 2))
        tk.Label(top, text="All progress will be lost.", bg="#0C1219", fg="#8FA6B8",
                 font=("Consolas", 8)).pack()
        row = tk.Frame(top, bg="#0C1219")
        row.pack(pady=12)

        def do_reset():
            self.game = state.Game()
            self.game.apply_offline_decay()
            self.save()
            top.destroy()
            self.go_home()
            self.toast("DEVICE RESET", 0xE8564A)

        tk.Button(row, text="Reset", command=do_reset, bg="#3A2028", fg="#FF8A80",
                  relief="flat", font=("Consolas", 9), width=8).pack(side="left", padx=6)
        tk.Button(row, text="Cancel", command=top.destroy, bg="#1A2632", fg="#CFE6F5",
                  relief="flat", font=("Consolas", 9), width=8).pack(side="left", padx=6)
        top.focus_force()

    # -- screen flow --------------------------------------------------------
    def push(self, screen):
        self.stack.append(screen)
        self.screen = screen
        screen.enter(self)
        self.render()

    def pop(self):
        if len(self.stack) > 1:
            self.stack.pop()
        self.screen = self.stack[-1]
        self.render()

    def replace(self, screen):
        self.stack[-1] = screen
        self.screen = screen
        screen.enter(self)
        self.render()

    def go_home(self):
        home = screens.HomeScreen()
        self.stack = [home]
        self.screen = home
        home.enter(self)
        self.render()

    def handle_key(self, key):
        self.screen.press(key, self)

    def toast(self, text, colour=0xFFFFFF):
        self.toast_text = text
        self.toast_col = colour
        self.toast_until = self.t + 2.1

    # -- sorties -------------------------------------------------------------
    def launch_sortie(self, enemy, tactic):
        payload = self.game.player_payload()
        sim = dogfight.simulate(payload, enemy, tactic)
        self.push(screens.BattleScreen(sim, enemy))

    def finish_sortie(self, sim):
        g = self.game
        before_level = g.level
        won = sim["winner"] == 0
        hp_frac = sim["php"] / max(1.0, sim["player"]["hp"])
        if won:
            credits = 55 + sim["enemy"]["level"] * 14 + int(hp_frac * 70)
            xp = 22 + sim["enemy"]["level"] * 3
        else:
            credits = 12
            xp = 8
        entry = g.finish_sortie(sim["enemy"]["name"], won, sim["rounds"], sim["php"], credits, xp)
        self.save()
        if g.level > before_level:
            self.sound.play("levelup")
            self.toast("RANK UP: " + g.rank, 0xFFC24A)
        return entry

    # -- main loop ------------------------------------------------------------
    def tick(self):
        now = time.time()
        dt = min(0.25, now - self.last)
        self.last = now
        self.t += dt
        self.frame += 1

        if not getattr(self, "paused", False):
            self.game.tick(dt)
            self.game.data["last_seen"] = now

        self.led_t += dt
        if self.led_t > 0.9:
            self.led_t = 0.0
            self.led_on = not self.led_on
            self._paint_shell()

        self.screen.tick(dt, self)
        self.render()

        if now - self.last_save > 45:
            self.save()
        self.root.after(FPS_MS, self.tick)

    def render(self):
        buf = PixBuf(LCD_W, LCD_H, 0x000000)
        try:
            self.screen.draw(buf, self)
        except Exception as exc:  # keep the pet alive even if a screen glitches
            buf = PixBuf(LCD_W, LCD_H, 0x200000)
            screens.font.draw_text(buf, 3, 4, "SCREEN ERROR", 0xFF8080)
            screens.font.draw_micro(buf, 3, 14, str(exc)[:30], 0xFFB0B0)
        self.draw_toast(buf)
        self.lcd_src.put(buf.to_photo_data(KEY))
        self.lcd_photo = self.lcd_src.zoom(self.scale)
        self.canvas.itemconfigure(self.lcd_item, image=self.lcd_photo)

    def draw_toast(self, buf):
        if self.t < self.toast_until and self.toast_text:
            # The toast takes over the footer strip so it never covers content.
            y = LCD_H - 9
            buf.rect(0, y, LCD_W, 9, 0x0C1A26)
            buf.hline(0, LCD_W - 1, y, mix(self.toast_col, 0x000000, 0.55))
            text = self.toast_text[:26]
            screens.font.draw_micro(buf, (LCD_W - screens.font.micro_width(text)) // 2,
                                    y + 2, text, self.toast_col)

    # -- persistence ----------------------------------------------------------
    def save(self):
        self.game.settings["x"] = self.root.winfo_x()
        self.game.settings["y"] = self.root.winfo_y()
        state.save(self.game, self.folder)
        self.last_save = time.time()

    def quit(self):
        try:
            self.save()
        except Exception:
            pass
        self.sound.set_enabled(False)
        self.root.destroy()


def run(folder):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    app = App(root, folder)
    root.mainloop()
