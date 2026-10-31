"""Procedural ambience and music for the lobby and the step 7 rooms. Runs on Blender's bundled Python (numpy).
   blender -b --python audio/synth_rooms.py -- --out unity/Fable/Assets/Fable/Resources/Audio
   Every clip is synthesised here: no third-party samples, no licence questions (CC0 like the rest of Fable's own work).

   amb.lobby              quiet panelled room: soft room tone, a slow clock, the oil lamp
   amb.kansas-storm       the farmhouse in the coming cyclone: "a low wail of the wind ... from the north", the long
                          grass bowing in waves, boards creaking, and "a sharp whistling in the air from the south"
   amb.calypsos-cave      Ogygia: surf on the shore, "four running rills of water", the cedar fire, sea-crows and birds
   music.calypsos-cave    a sparse plucked lyre in the Dorian mode, slow, for Calypso's cave (composed here)
   amb.glumdalclitchs-room  a giant's room heard from doll height: deep room tone, a huge slow clock, wind at the window
"""
import sys, os, wave, argparse
import numpy as np
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser(); ap.add_argument("--out", default="audio/out"); a = ap.parse_args(argv)
SR = 44100
rng = np.random.default_rng(1900)

def t(sec): return np.arange(int(SR * sec)) / SR
def noise(n): return rng.standard_normal(n)
def band(x, lo=None, hi=None, order=4):
    """Zero-phase band filter in the frequency domain (smooth roll-off; fine for noise beds)."""
    n = len(x); f = np.fft.rfftfreq(n, 1 / SR); X = np.fft.rfft(x); g = np.ones_like(f)
    if hi: g /= np.sqrt(1 + (f / hi) ** (2 * order))
    if lo: g /= np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    return np.fft.irfft(X * g, n)
def norm(x, peak=0.8): m = np.max(np.abs(x)) or 1; return x / m * peak
def env(n, a, r):
    e = np.ones(n); ai, ri = int(a * SR), int(r * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if ri: e[-ri:] *= np.linspace(1, 0, ri)
    return e
def place(dst, src, at):
    s = int(at * SR) % len(dst); k = min(len(src), len(dst) - s); dst[s:s + k] += src[:k]
    if k < len(src): dst[:len(src) - k] += src[k:]            # wrap: clips are loops
def loop_seam(x, sec=1.0):
    """Crossfade the tail into the head so the clip loops without a click."""
    k = int(sec * SR); y = x[:-k].copy(); y[:k] = y[:k] * np.linspace(0, 1, k) + x[-k:] * np.linspace(1, 0, k); return y
def save(name, x, stereo=None):
    os.makedirs(a.out, exist_ok=True); p = os.path.join(a.out, name + ".wav")
    x = np.clip(x, -1, 1); w = wave.open(p, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x * 32767).astype('<i2').tobytes()); w.close(); print("wrote", p, f"{len(x) / SR:.2f}s")
def slow(sec, rate, seed):
    """A smooth random curve in 0..1 (gusts, swells)."""
    r = np.random.default_rng(seed); pts = r.random(int(sec * rate) + 4)
    xs = np.linspace(0, len(pts) - 1, int(sec * SR)); return np.interp(xs, np.arange(len(pts)), pts)

# ---------------------------------------------------------------- lobby
def clock_tick(f=1800, dur=0.05, amp=1.0, body=420):
    k = int(dur * SR); tk = np.arange(k) / SR
    return (band(noise(k), f * 0.6, f * 1.6) * np.exp(-tk * 90) + 0.6 * np.sin(2 * np.pi * body * tk) * np.exp(-tk * 60)) * amp
sec = 24
x = band(noise(SR * sec), 60, 400) * 0.18                       # room tone
x += band(noise(SR * sec), 1200, 6000) * 0.012 * (0.8 + 0.2 * slow(sec, 3, 1))   # the lamp's faint hiss
for i in range(sec):                                            # a slow clock across the room: tick ... tock
    place(x, clock_tick(1700 if i % 2 else 1500, amp=0.10), i + 0.02 * rng.standard_normal())
save("amb.lobby", norm(loop_seam(np.concatenate([x, x[:SR]])), 0.32))

# ---------------------------------------------------------------- Kansas: the storm coming over the prairie
sec = 30; n = SR * sec; tt = t(sec)
gust = 0.35 + 0.65 * slow(sec, 0.25, 2) ** 1.5
wail = np.zeros(n)
for f0, w in [(170, 1.0), (240, 0.6), (330, 0.35)]:             # the low wail: resonant noise bands that slide with the gusts
    f = f0 * (0.85 + 0.35 * slow(sec, 0.3, int(f0)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    wail += band(noise(n), 60, 900) * (0.5 + 0.5 * np.sin(ph)) ** 6 * w
grass = band(noise(n), 1800, 7000) * (0.25 + 0.75 * slow(sec, 0.6, 3))   # the long grass bowing in waves
roar = band(noise(n), 30, 220) * 1.6
x = (roar + 0.9 * wail + 0.22 * grass) * gust
for at in rng.uniform(0, sec, 7):                               # boards creaking
    k = int(rng.uniform(0.4, 0.9) * SR); tk = np.arange(k) / SR; rate = rng.uniform(25, 60) * (1 + 0.6 * np.sin(np.pi * tk / tk[-1]))
    pulses = (np.diff(np.floor(np.cumsum(rate / SR)), prepend=0) > 0) * (0.5 + 0.5 * rng.random(k))
    place(x, band(np.convolve(pulses, np.exp(-np.arange(200) / 30), 'same'), 200, 1400) * env(k, 0.1, 0.2) * 0.9, at)
for at in (6.0, 19.5):                                          # the sharp whistle from the south
    k = int(3.2 * SR); tk = np.arange(k) / SR; f = 1900 + 500 * np.sin(np.pi * tk / tk[-1]) + 60 * np.sin(2 * np.pi * 5 * tk)
    place(x, np.sin(2 * np.pi * np.cumsum(f) / SR) * env(k, 0.9, 1.4) * 0.05 + band(noise(k), 1700, 2600) * env(k, 0.9, 1.4) * 0.05, at)
save("amb.kansas-storm", norm(loop_seam(x, 1.5), 0.5))

# ---------------------------------------------------------------- Ogygia: surf, rills, the cedar fire, birds
sec = 32; n = SR * sec; tt = t(sec)
surf = np.zeros(n)
for i, at in enumerate(np.arange(0, sec, 6.4) + rng.uniform(-0.6, 0.6, int(np.ceil(sec / 6.4)))):   # waves break and draw back
    k = int(5.6 * SR); tk = np.arange(k) / SR
    shape = (tk / 1.4) ** 2 * np.exp(-(tk - 1.4) / 1.6 * (tk > 1.4)) * (tk <= 1.4) + np.exp(-(tk - 1.4) / 1.6) * (tk > 1.4)
    place(surf, band(noise(k), 120, 2600) * shape * rng.uniform(0.7, 1.0) + band(noise(k), 3000, 9000) * shape * 0.25 * np.exp(-tk / 2.5), at)
surf += band(noise(n), 40, 300) * 0.35                          # the sea's low body
rills = np.zeros(n)
for at in rng.uniform(0, sec, 900):                             # running water: many tiny bubbles
    k = int(rng.uniform(0.008, 0.03) * SR); tk = np.arange(k) / SR; f0 = rng.uniform(700, 2600)
    rills_k = np.sin(2 * np.pi * (f0 * tk + f0 * 2.5 * tk ** 2 / (k / SR))) * np.exp(-tk * 160)
    place(rills, rills_k * rng.uniform(0.2, 1.0), at)
fire = band(noise(n), 80, 600) * 0.25 * (0.7 + 0.3 * slow(sec, 1.5, 5))
for at in rng.uniform(0, sec, 140):                             # cedar crackle
    k = int(rng.uniform(0.004, 0.02) * SR); place(fire, band(noise(k), 1200, 7000) * np.exp(-np.arange(k) / (k / 4)) * rng.uniform(0.3, 1.0), at)
birds = np.zeros(n)
for at in rng.uniform(0, sec, 9):                               # sea-crows and gulls: falling cries, far off
    k = int(rng.uniform(0.25, 0.5) * SR); tk = np.arange(k) / SR; f = rng.uniform(1100, 1600) * (1 - 0.35 * tk / tk[-1])
    birds_k = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(k, 0.02, 0.15)
    place(birds, band(birds_k, 600, 3500) * 0.12, at)
for at in rng.uniform(0, sec, 14):                              # small birds in the alder and cypress
    k = int(rng.uniform(0.08, 0.16) * SR); tk = np.arange(k) / SR; f0 = rng.uniform(3000, 4800)
    place(birds, np.sin(2 * np.pi * (f0 * tk + 900 * np.sin(2 * np.pi * 14 * tk) / 14)) * env(k, 0.01, 0.05) * 0.08, at)
x = 0.9 * surf + 0.10 * rills + 0.5 * fire + birds
save("amb.calypsos-cave", norm(loop_seam(x, 1.5), 0.5))

# a lyre in the Dorian mode, plucked (Karplus-Strong), sparse and slow, with a soft drone; 64 s loop
def pluck(f, dur=3.5, amp=0.5, bright=0.5):
    k = int(dur * SR); p = max(2, int(SR / f)); buf = band(rng.uniform(-1, 1, p * 4), None, 2000 + 5000 * bright)[:p]
    out = np.zeros(k); out[:p] = buf
    for i in range(p, k): out[i] = 0.4985 * (out[i - p] + out[i - p + 1]) if i - p + 1 < k else 0
    return out * amp * env(k, 0.002, 0.4)
D = 146.83; dorian = [1, 9 / 8, 6 / 5, 4 / 3, 3 / 2, 5 / 3, 16 / 9, 2]      # D Dorian, just intonation
phrases = [[0, 2, 4, 3, 2], [4, 5, 7, 5, 4, 3], [2, 3, 1, 0], [0, 4, 3, 5, 4, 2], [7, 6, 4, 5, 3, 2, 0]]
sec = 64; music = np.zeros(SR * sec); at = 1.0
for p in phrases * 2:
    for j, d in enumerate(p):
        if at > sec - 4: break
        oct_ = 2 if d < 4 and rng.random() < 0.3 else 1
        place(music, pluck(D * dorian[d] * oct_, amp=rng.uniform(0.35, 0.5), bright=rng.uniform(0.3, 0.6)), at)
        at += rng.choice([0.9, 1.2, 1.8])
    at += rng.uniform(3.0, 5.0)
tt = t(sec); drone = (np.sin(2 * np.pi * D / 2 * tt) + 0.5 * np.sin(2 * np.pi * D * 3 / 4 * tt)) * 0.05 * (0.7 + 0.3 * slow(sec, 0.2, 9))
music = music + drone
ir = band(noise(int(2.2 * SR)), 200, 5000) * np.exp(-np.arange(int(2.2 * SR)) / (0.55 * SR))   # a cave's soft reverb
wet = np.fft.irfft(np.fft.rfft(music, len(music) + len(ir)) * np.fft.rfft(ir, len(music) + len(ir)))[:len(music) + len(ir)]
wet[:len(ir)] += wet[len(music):len(music) + len(ir)]; wet = wet[:len(music)]
save("music.calypsos-cave", norm(loop_seam(norm(music, 0.6) + norm(wet, 0.35), 2.0), 0.5))

# ---------------------------------------------------------------- Brobdingnag: a girl's room heard at doll height
sec = 24; n = SR * sec
x = band(noise(n), 25, 180) * 0.6 + band(noise(n), 180, 900) * 0.06 * (0.6 + 0.4 * slow(sec, 0.3, 11))   # the room's deep air
for i in range(0, sec, 2):                                      # a tall clock, enormous and slow: one beat every two seconds
    for j, body in enumerate((95, 80)):
        place(x, clock_tick(700, dur=0.4, amp=0.5, body=body), i + j * 1.0 + 0.01 * rng.standard_normal())
x += band(noise(n), 400, 2500) * 0.05 * slow(sec, 0.2, 12) ** 2   # wind at the casement, far above
save("amb.glumdalclitchs-room", norm(loop_seam(np.concatenate([x, x[:SR]])), 0.4))
