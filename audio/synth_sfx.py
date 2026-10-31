"""Procedural sound set for all three scenes (hall, tea-party, croquet ground). Runs on Blender's bundled Python (numpy).
   blender -b --python audio/synth_sfx.py -- --out unity/Fable/Assets/Fable/Audio
   Every clip is synthesised: no third-party samples, no licence questions."""
import sys, os, wave, struct, argparse
import numpy as np
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser(); ap.add_argument("--out", default="audio/out"); a = ap.parse_args(argv)
SR = 44100
rng = np.random.default_rng(1865)
def t(sec): return np.arange(int(SR * sec)) / SR
def env(n, a=0.005, d=0.1, s=0.0, r=0.2, hold=0.0):
    ai, di, hi, ri = int(a*SR), int(d*SR), int(hold*SR), int(r*SR)
    e = np.zeros(n)
    def put(i, seg):
        seg = seg[:max(0, n - i)]
        e[i:i+len(seg)] = seg
    i = 0
    put(i, np.linspace(0, 1, ai)); i += ai
    put(i, np.linspace(1, s, di)); i += di
    put(i, np.full(hi, s)); i += hi
    put(i, np.linspace(s, 0, ri))
    return e
def lowpass(x, cutoff):
    rc = 1/(2*np.pi*cutoff); dt = 1/SR; al = dt/(rc+dt); y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)): acc += al*(x[i]-acc); y[i] = acc
    return y
def highpass(x, cutoff): return x - lowpass(x, cutoff)
def noise(n): return rng.standard_normal(n)
def norm(x, peak=0.8):
    m = np.max(np.abs(x)) or 1; return x/m*peak
def save(name, x):
    os.makedirs(a.out, exist_ok=True); p = os.path.join(a.out, name + ".wav")
    x = np.clip(x, -1, 1); w = wave.open(p, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((x*32767).astype('<i2').tobytes()); w.close(); print("wrote", p, f"{len(x)/SR:.2f}s")
# ambience: oil lamp hiss + stone room tone + slow flicker modulation, seamless loop (12 s)
n = SR*12; tt = t(12)
hiss = highpass(lowpass(noise(n), 6000), 1800) * (0.5 + 0.5*np.sin(2*np.pi*0.37*tt) * np.sin(2*np.pi*1.3*tt + 1))
room = lowpass(noise(n), 120) * 3.0 + 0.4*np.sin(2*np.pi*55*tt) * (0.6+0.4*np.sin(2*np.pi*0.11*tt))
flick = lowpass(noise(n), 9) * 2.5
amb = 0.35*hiss*(1+0.5*flick) + 0.5*room
fade = np.minimum(1, tt/0.5) * np.minimum(1, (12-tt)/0.5)
# crossfade tail onto head for a clean loop
k = SR//2; amb[:k] = amb[:k]*np.linspace(0,1,k) + amb[-k:]*np.linspace(1,0,k)
save("amb.hall-lamps", norm(amb*fade, 0.5))
# footsteps on stone: 4 steps, each a filtered thump with a gritty tail
x = np.zeros(SR*3)
for i, at in enumerate([0.2, 0.85, 1.5, 2.15]):
    s = int(at*SR); m = int(0.35*SR)
    th = lowpass(noise(m), 180) * env(m, 0.002, 0.08, 0.0, 0.05) * 6
    gr = highpass(noise(m), 2500) * env(m, 0.001, 0.03, 0.1, 0.12) * 0.35
    x[s:s+m] += th + gr
save("sfx.footsteps-stone", norm(x, 0.7))
# locked door rattle: knob clack + wood shudder, three shakes
x = np.zeros(int(SR*1.4))
for at in [0.05, 0.32, 0.6]:
    s = int(at*SR); m = int(0.3*SR); tm = t(0.3)
    clack = (np.sin(2*np.pi*2100*tm) + 0.5*np.sin(2*np.pi*3300*tm)) * env(m, 0.0005, 0.02, 0, 0.02) * 0.6
    wood = lowpass(noise(m), 400) * env(m, 0.002, 0.12, 0, 0.1) * 3 * (1+0.6*np.sin(2*np.pi*38*tm))
    x[s:s+m] += clack + wood
save("sfx.door-locked-rattle", norm(x, 0.75))
# key fits: tiny metallic insertion then a satisfying click
m = int(0.8*SR); tm = t(0.8)
slide = highpass(noise(m), 4000) * env(m, 0.01, 0.15, 0.2, 0.1) * 0.25
click = (np.sin(2*np.pi*4200*tm) + 0.6*np.sin(2*np.pi*6900*tm) + 0.3*np.sin(2*np.pi*1500*tm)) * np.roll(env(m, 0.0003, 0.015, 0, 0.05), int(0.28*SR)) * 0.8
save("sfx.key-fits", norm(slide+click, 0.7))
# small door opening: a short hinge creak, pitch gliding, with a little wooden knock at the end
m = int(1.6*SR); tm = t(1.6)
f = 420 + 160*np.sin(2*np.pi*0.7*tm) + 90*tm
creak = np.sin(2*np.pi*np.cumsum(f)/SR) * (0.6 + 0.4*np.sin(2*np.pi*23*tm)) * env(m, 0.05, 0.4, 0.5, 0.5)
creak += 0.4*np.sin(2*np.pi*np.cumsum(f*2.01)/SR) * env(m, 0.05, 0.4, 0.3, 0.5)
creak = lowpass(creak, 1800) * 0.5
knock = lowpass(noise(m), 300) * np.roll(env(m, 0.001, 0.08, 0, 0.1), int(1.3*SR)) * 4
save("sfx.door-small-open", norm(creak+knock, 0.6))
# curtain slide: brass rings on a rod, a whoosh of velvet
m = int(1.3*SR); tm = t(1.3)
rings = np.zeros(m)
for at in np.linspace(0.05, 0.9, 9) + rng.uniform(-0.02, 0.02, 9):
    s = int(at*SR); k = int(0.06*SR); tk = t(0.06)
    rings[s:s+k] += (np.sin(2*np.pi*3100*tk) + 0.5*np.sin(2*np.pi*5200*tk)) * env(k, 0.0005, 0.02, 0, 0.03) * rng.uniform(0.3, 0.6)
whoosh = lowpass(highpass(noise(m), 600), 2500) * env(m, 0.15, 0.5, 0.3, 0.5) * 0.4
save("sfx.curtain-slide", norm(rings+whoosh, 0.6))
# cork pop: pressure release, a bright pop and a short bottle resonance
m = int(0.7*SR); tm = t(0.7)
pop = lowpass(noise(m), 900) * env(m, 0.0005, 0.03, 0, 0.05) * 5
res = np.sin(2*np.pi*620*tm) * env(m, 0.001, 0.15, 0, 0.2) * 0.5 + np.sin(2*np.pi*1240*tm) * env(m, 0.001, 0.08, 0, 0.1) * 0.2
save("sfx.cork-pop", norm(pop+res, 0.75))
# glass set down on glass: two partials ringing, damped
m = int(1.2*SR); tm = t(1.2)
g = (np.sin(2*np.pi*2870*tm)*np.exp(-tm*9) + 0.6*np.sin(2*np.pi*4310*tm)*np.exp(-tm*14) + 0.3*np.sin(2*np.pi*1180*tm)*np.exp(-tm*6)) * env(m, 0.0005, 0.5, 0.3, 0.6)
tap = lowpass(noise(m), 1500) * env(m, 0.0005, 0.01, 0, 0.02) * 2
save("sfx.glass-set-down", norm(g+tap, 0.6))
# garden birds: a loop of soft chirps, filtered to sound distant, through a small door
n = SR*10; tt = t(10); x = lowpass(noise(n), 300) * 0.6
for _ in range(26):
    at = rng.uniform(0, 9.5); s = int(at*SR); k = int(rng.uniform(0.08, 0.22)*SR); tk = np.arange(k)/SR
    f0 = rng.uniform(2200, 4200); gl = rng.uniform(-900, 900)
    chirp = np.sin(2*np.pi*(f0*tk + 0.5*gl*tk**2/ (k/SR))) * env(k, 0.01, 0.05, 0.5, 0.05) * rng.uniform(0.15, 0.35)
    seg = chirp[:len(x)-s]; x[s:s+len(seg)] += seg
x = lowpass(x, 3500)
k = SR//2; x[:k] = x[:k]*np.linspace(0,1,k) + x[-k:]*np.linspace(1,0,k)
save("sfx.garden-birds", norm(x, 0.45))

# ---------------------------------------------------------------- the two garden scenes
def band(x, lo, hi): return highpass(lowpass(x, hi), lo)
def place(dst, src, at):
    s = int(at*SR); seg = src[:max(0, len(dst)-s)]; dst[s:s+len(seg)] += seg
def loopify(x):
    k = SR//2; x[:k] = x[:k]*np.linspace(0,1,k) + x[-k:]*np.linspace(1,0,k); return x
def birds(sec, count, far):
    x = np.zeros(SR*sec)
    for _ in range(count):
        k = int(rng.uniform(0.06, 0.18)*SR); tk = np.arange(k)/SR; f0 = rng.uniform(2400, 4600); gl = rng.uniform(-1200, 1200)
        notes = rng.integers(1, 4)
        for j in range(notes):
            c = np.sin(2*np.pi*(f0*(1+0.06*j)*tk + 0.5*gl*tk**2/(k/SR))) * env(k, 0.008, 0.04, 0.5, 0.05) * rng.uniform(0.12, 0.3)
            place(x, c, rng.uniform(0, sec-0.6) if j == 0 else 0)
    return lowpass(x, 2600 if far else 6000)
def wind(sec, depth):
    n = SR*sec; tt = t(sec); gust = 0.6 + 0.4*np.sin(2*np.pi*0.07*tt + 1.3)*np.sin(2*np.pi*0.19*tt)
    return lowpass(noise(n), 380)*2.2*gust + band(noise(n), 1500, 5000)*0.12*gust*depth
def clink(f, dur=0.35, amp=0.5):
    k = int(dur*SR); tk = np.arange(k)/SR
    tone = sum(np.sin(2*np.pi*f*r*tk)*np.exp(-tk*(18+9*i))/(i+1) for i, r in enumerate([1, 2.32, 4.25, 6.63]))
    return tone*amp*env(k, 0.001, 0.02, 0.6, dur*0.8)

# afternoon by the March Hare's house: warm wind in the tree, birds, leaves
x = 0.5*wind(12, 1.0) + birds(12, 22, far=True)
save("amb.garden-afternoon", norm(loopify(x)*np.minimum(1, t(12)/0.4)*np.minimum(1, (12-t(12))/0.4), 0.45))
# the Queen's formal garden: stiller air, clipped hedges, birds further off
x = 0.35*wind(12, 0.6) + 0.7*birds(12, 12, far=True)
save("amb.formal-garden", norm(loopify(x)*np.minimum(1, t(12)/0.4)*np.minimum(1, (12-t(12))/0.4), 0.4))

x = np.zeros(int(SR*1.4))
for i in range(9): place(x, clink(rng.uniform(2300, 4300), 0.3, rng.uniform(0.3, 0.7)), 0.05 + i*0.13 + rng.uniform(-0.03, 0.03))
save("sfx.cups-rattle", norm(x, 0.7))

n = int(SR*2.6); tt = t(2.6); gurgle = band(noise(n), 500, 3200)*(0.7 + 0.3*np.sin(2*np.pi*23*tt))
fill = np.sin(2*np.pi*(380*tt + 160*tt**2))*0.15*(tt/2.6)
x = (gurgle + fill)*env(n, 0.15, 0.2, 0.8, 0.5, hold=1.6) + np.concatenate([clink(3100, 0.3, 0.4), np.zeros(n - int(0.3*SR))])
save("sfx.tea-pour", norm(x, 0.6))

n = int(SR*1.3); x = np.zeros(n); tt = t(1.3); rate = 40 + 110*np.sin(np.pi*tt/1.3)
ph = np.cumsum(rate/SR); pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)*(0.6+0.4*rng.random(n))
x = band(np.convolve(pulses, np.exp(-np.arange(int(0.004*SR))/40), 'same'), 250, 1800)*env(n, 0.05, 0.2, 0.7, 0.3, hold=0.6)
save("sfx.chair-creak", norm(x, 0.6))

# "No room! No room!": three voices, glottal saw through vowel formants (o -> oo); a chorus impression, not speech
def vowel(f0, formants, dur):
    k = int(dur*SR); tk = np.arange(k)/SR; vib = 1 + 0.02*np.sin(2*np.pi*5.5*tk)
    saw = 2*((f0*vib*tk) % 1) - 1; out = np.zeros(k)
    for (fc, bw, g) in formants: out += band(saw, fc - bw/2, fc + bw/2)*g
    a_, r_ = min(0.02, dur/4), min(0.08, dur/3)
    return out*env(k, a_, min(0.05, dur/4), 0.9, r_, hold=max(0.0, dur - a_ - r_ - 0.05))
x = np.zeros(int(SR*2.0))
for f0, dt in [(190, 0.0), (240, 0.02), (150, -0.015)]:
    for start in (0.05, 0.95):
        place(x, vowel(f0, [(250, 120, 1.0), (2200, 300, 0.15)], 0.08), start + dt)                      # n
        place(x, vowel(f0*1.08, [(520, 140, 1.0), (900, 200, 0.6), (2500, 300, 0.12)], 0.22), start + 0.08 + dt)   # o
        place(x, vowel(f0*0.95, [(330, 120, 0.9), (1300, 250, 0.35)], 0.06), start + 0.33 + dt)              # r
        place(x, vowel(f0*1.15, [(310, 120, 1.0), (870, 160, 0.4), (2250, 300, 0.08)], 0.3), start + 0.39 + dt)    # oo
        place(x, vowel(f0*0.8, [(280, 120, 0.8)], 0.07), start + 0.69 + dt)                                  # m
save("sfx.no-room-shout", norm(x, 0.7))

n = SR*3; x = np.zeros(n)
for _ in range(40):
    k = int(rng.uniform(0.02, 0.09)*SR); place(x, band(noise(k), 1800, 7000)*env(k, 0.004, 0.02, 0.4, 0.03)*rng.uniform(0.2, 0.6), rng.uniform(0, 2.8))
save("sfx.leaves", norm(x*env(n, 0.3, 0.1, 1, 0.8, hold=1.8), 0.5))

save("sfx.birdsong", norm(loopify(birds(6, 18, far=False) + 0.05*wind(6, 0.3)), 0.5))

n = SR*4; tt = t(4); breath = np.sin(np.pi*np.clip(tt/1.8, 0, 1))**2 + 0.6*np.sin(np.pi*np.clip((tt-2.1)/1.6, 0, 1))**2
rumble = band(noise(n), 60, 400)*(1 + 0.6*np.sin(2*np.pi*31*tt)); whistle = np.sin(2*np.pi*(1300 + 80*np.sin(2*np.pi*0.5*tt))*tt)*0.04
save("sfx.dormouse-snore", norm((rumble + whistle*(tt > 2.1))*breath, 0.45))

n = SR*3; x = np.zeros(n)
for i in range(7):
    k = int(0.28*SR); tk = np.arange(k)/SR
    place(x, band(noise(k), 1400, 5500)*np.sin(np.pi*tk/(k/SR))**1.5*rng.uniform(0.4, 0.7), 0.1 + i*0.4 + rng.uniform(-0.04, 0.04))
save("sfx.brush-strokes", norm(x, 0.55))

n = int(SR*1.6); tt = t(1.6); whoosh = band(noise(n), 400, 2500)*np.exp(-((tt-0.25)/0.12)**2)
clatter = np.zeros(n)
for i in range(6): place(clatter, clink(rng.uniform(700, 1300), 0.15, 0.4)*0.5, 0.55 + i*0.09*(1+i*0.3))
for i in range(6):
    k = int(0.06*SR); place(clatter, band(noise(k), 1000, 6000)*env(k, 0.001, 0.02, 0.3, 0.03)*0.5, 0.55 + i*0.09*(1+i*0.3))
save("sfx.brush-fling", norm(whoosh*0.8 + clatter, 0.7))

n = SR*3; x = np.zeros(n)
for step in range(5):
    at = 0.15 + step*0.55
    for g in range(60):
        k = int(rng.uniform(0.002, 0.008)*SR); place(x, band(noise(k), 1500, 8000)*rng.uniform(0.1, 0.5), at + rng.exponential(0.035))
    place(x, lowpass(noise(int(0.08*SR)), 200)*env(int(0.08*SR), 0.003, 0.05, 0.2, 0.03)*0.8, at)
save("sfx.gravel-steps", norm(x, 0.6))

save("sfx.wind-hedges", norm(loopify(wind(6, 1.6)), 0.5))

n = int(SR*1.2); x = np.zeros(n); at = 0.05; gap = 0.03
while at < 0.95:
    k = int(0.004*SR); place(x, band(noise(k), 2000, 9000)*rng.uniform(0.3, 0.7), at); at += gap; gap = max(0.006, gap*0.93)
place(x, band(noise(int(0.06*SR)), 600, 4000)*env(int(0.06*SR), 0.002, 0.03, 0.2, 0.02), 1.0)
save("sfx.card-shuffle", norm(x, 0.6))
print("ALL SOUNDS WRITTEN")
