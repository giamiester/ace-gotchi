"""Tiny chiptune synth. Builds WAVs in memory and plays them with winsound."""

import math
import random
import struct

try:
    import winsound
except ImportError:  # not on Windows
    winsound = None

RATE = 22050
_cache = {}


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------
def _square(phase, duty=0.5):
    return 1.0 if (phase % 1.0) < duty else -1.0


def _saw(phase):
    return 2.0 * (phase % 1.0) - 1.0


def _sine(phase):
    return math.sin(phase * math.tau)


def _tri(phase):
    p = phase % 1.0
    return 4.0 * abs(p - 0.5) - 1.0


WAVES = {"square": _square, "saw": _saw, "sine": _sine, "tri": _tri}


def tone(freq, dur, wave="square", vol=0.35, decay=2.0, sweep=None, duty=0.5):
    n = max(1, int(RATE * dur))
    out = []
    phase = 0.0
    fn = WAVES.get(wave, _square)
    for i in range(n):
        t = i / n
        f = freq if sweep is None else freq + (sweep - freq) * t
        phase += f / RATE
        env = (1.0 - t) ** decay
        if t < 0.01:
            env *= t / 0.01
        if wave == "square":
            s = 1.0 if (phase % 1.0) < duty else -1.0
        else:
            s = fn(phase)
        out.append(s * env * vol)
    return out


def silence(dur):
    return [0.0] * int(RATE * dur)


def noise(dur, vol=0.5, decay=2.5, lowpass=0.25):
    n = max(1, int(RATE * dur))
    out = []
    last = 0.0
    for i in range(n):
        t = i / n
        s = random.uniform(-1, 1)
        last += (s - last) * lowpass
        out.append(last * vol * (1.0 - t) ** decay)
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, v in enumerate(t):
            out[i] += v
    return out


def seq(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def to_wav(samples):
    data = bytearray()
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 32767)
        data += struct.pack("<h", v)
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16)
    header += b"data" + struct.pack("<I", len(data))
    return bytes(header) + bytes(data)


# ---------------------------------------------------------------------------
# The sound bank
# ---------------------------------------------------------------------------
def _build(name):
    if name == "click":
        return seq(tone(1046, 0.035, "square", 0.22, 3), silence(0.01))
    if name == "confirm":
        return seq(tone(784, 0.05, "square", 0.25, 2),
                   tone(1175, 0.09, "square", 0.25, 2))
    if name == "error":
        return seq(tone(196, 0.10, "square", 0.28, 2), tone(147, 0.14, "square", 0.28, 2))
    if name == "feed":
        return seq(tone(523, 0.06, "tri", 0.3, 2), tone(784, 0.10, "tri", 0.3, 2))
    if name == "rest":
        return seq(tone(392, 0.12, "sine", 0.28, 2), tone(294, 0.22, "sine", 0.26, 2))
    if name == "clean":
        return seq(tone(1318, 0.04, "sine", 0.22, 3), silence(0.02),
                   tone(1760, 0.06, "sine", 0.2, 3), silence(0.02),
                   tone(2093, 0.08, "sine", 0.16, 3))
    if name == "train":
        return seq(tone(440, 0.06, "square", 0.24, 2), tone(587, 0.06, "square", 0.24, 2),
                   tone(880, 0.10, "square", 0.24, 2))
    if name == "sortie":
        return seq(tone(220, 0.42, "saw", 0.26, 0.6, sweep=880),
                   tone(660, 0.18, "square", 0.22, 2))
    if name == "hit":
        return mix(noise(0.13, 0.5, 2.5, 0.35), tone(110, 0.13, "square", 0.35, 2))
    if name == "explode":
        return mix(noise(0.45, 0.65, 2.0, 0.12),
                   tone(70, 0.40, "sine", 0.5, 2.0, sweep=40))
    if name == "miss":
        return seq(tone(880, 0.05, "square", 0.18, 3), tone(660, 0.06, "square", 0.14, 3))
    if name == "victory":
        return seq(tone(523, 0.11, "square", 0.26, 1.4),
                   tone(659, 0.11, "square", 0.26, 1.4),
                   tone(784, 0.11, "square", 0.26, 1.4),
                   tone(1046, 0.30, "square", 0.28, 1.2))
    if name == "defeat":
        return seq(tone(392, 0.16, "tri", 0.3, 1.2),
                   tone(311, 0.16, "tri", 0.3, 1.2),
                   tone(233, 0.34, "tri", 0.3, 1.2))
    if name == "levelup":
        return seq(tone(659, 0.06, "square", 0.24, 1.5), tone(784, 0.06, "square", 0.24, 1.5),
                   tone(988, 0.06, "square", 0.24, 1.5), tone(1318, 0.18, "square", 0.26, 1.5))
    return silence(0.01)


def wav_for(name):
    if name not in _cache:
        _cache[name] = to_wav(_build(name))
    return _cache[name]


class Sound:
    def __init__(self, enabled=True):
        self.enabled = enabled and winsound is not None

    def play(self, name):
        if not self.enabled:
            return
        try:
            winsound.PlaySound(wav_for(name), winsound.SND_MEMORY | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception:
            self.enabled = False

    def set_enabled(self, on):
        self.enabled = bool(on) and winsound is not None
