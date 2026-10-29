"""Developer helper: render sprite sheets to PNG so the art can be eyeballed."""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acegotchi import font, sprites
from acegotchi.pixel import PixBuf, rgb, mix, shade

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")


def save(buf, name, scale=6, bg=None):
    os.makedirs(OUT, exist_ok=True)
    if bg is not None:
        base = PixBuf(buf.w, buf.h, bg)
        base.blit(buf, 0, 0)
        buf = base
    img = tk.PhotoImage(width=buf.w, height=buf.h)
    img.put(buf.to_photo_data())
    big = img.zoom(scale)
    path = os.path.join(OUT, name + ".png")
    big.write(path, format="png")
    print("wrote", path)


def sheet():
    keys = list(sprites.AIRCRAFT)
    cw, ch = 44, 26
    buf = PixBuf(cw * 2, ch * 3, 0x101823)
    for i, k in enumerate(keys):
        col, row = i % 2, i // 2
        x, y = col * cw + 2, row * ch + 2
        buf.blit_art(sprites.AIRCRAFT[k]["art"], x, y,
                     palette=sprites.livery(0xB0BCCE, 0x3FA9F5, dark=0x66728A, light=0xE8F0FA))
        font.draw_micro(buf, x, y + 20, sprites.AIRCRAFT[k]["short"], 0x7FE3FF)
        # livery swatches
    save(buf, "jets", 8)


def liveries():
    cw, ch = 44, 24
    names = ["galm", "belka", "osea", "yukt", "erusea", "ustio", "ace", "player"]
    buf = PixBuf(cw * 2, ch * 4, 0x101823)
    for i, n in enumerate(names):
        col, row = i % 2, i // 2
        x, y = col * cw, row * ch + 2
        buf.blit_art(sprites.AIRCRAFT["f15c"]["art"], x + 2, y,
                     palette=sprites.LIVERIES[n])
        font.draw_micro(buf, x + 2, y + 19, n.upper(), 0x7FE3FF)
    save(buf, "liveries", 7)


def fonts():
    txt = "ACE COMBAT 0123456789"
    buf = PixBuf(150, 40, 0x08111A)
    font.draw_text(buf, 2, 2, txt, 0x7FE3FF)
    font.draw_text(buf, 2, 12, "FOX 2 - MISSILE AWAY", 0xFFD24A)
    font.draw_text(buf, 2, 24, "ABCDEFG", 0x6BFF9E, scale=2)
    font.draw_micro(buf, 2, 36, "MICRO FONT 1234567890", 0xE8F0FA)
    save(buf, "fonts", 8)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    sheet()
    liveries()
    fonts()
    import acegotchi.shell as shell
    dev = shell.render(led_on=True)
    font.draw_text_center(dev, shell.CX, 30, "", 0)
    save(dev, "shell", 4, bg=0x20242C)
    root.destroy()
