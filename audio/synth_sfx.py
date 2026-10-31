"""Procedural sound set for the Hall of Doors. Runs on Blender's bundled Python (numpy).
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
print("ALL SOUNDS WRITTEN")
