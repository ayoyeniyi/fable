#!/usr/bin/env python3
"""Build Fable's ambient beds, positional loops and four Alice sfx from real field recordings.

Every source is a CC0 (or CC-BY) recording listed in audio/SOURCES.md, with its page URL, download URL and
SHA-256. This script never downloads anything: fetch the files listed in SOURCES.md into a folder first (one
subfolder per source, named as in SOURCES below, e.g. fs-425795/425795_2543152-hq.ogg), then run:

    python3 -m venv ~/fable-sound-tools-venv
    ~/fable-sound-tools-venv/bin/pip install numpy soundfile scipy
    ~/fable-sound-tools-venv/bin/python -I audio/make_ambience.py ~/fable-sound-downloads
    # options: --out DIR (default unity/Fable/Assets/Fable/Resources/Audio), --only amb.surf,amb.fire

What it does to each source (all choices are per output in SPECS):
  * decodes it (soundfile / libsndfile: OGG Vorbis, FLAC, WAV, MP3), checks the SHA-256 against SOURCES;
  * cuts a deliberately chosen section (start offsets were picked by inspecting the RMS / band-energy
    envelope over time, avoiding voices, engines, aircraft, handling noise, wind on the mic and clipping);
  * optionally mixes in a second section of the same or another source (to blur speech in the tavern
    walla, or to add the odd creak to the room tone);
  * high-pass (2nd-order Butterworth, ~40 Hz, removes rumble) and optional gentle low-pass;
  * beds and positional loops: a seamless loop made by an equal-power (sin/cos) crossfade of the tail
    that follows the loop into its head, so the last sample flows into the first;
    the clock loop is cut to a whole number of tick periods (detected from its onset envelope) with a
    short crossfade placed in the quiet between ticks;
  * sfx one-shots: short fade in / fade out, no loop;
  * mono outputs are downmixed (L+R)/2; beds stay stereo;
  * loudness normalised to a BS.1770 (K-weighted, gated) integrated-loudness target per kind, then the
    gain is lowered if needed so the sample peak stays at or below -1.5 dBFS (about -1 dBTP);
  * encoded OGG Vorbis at the source rate (44.1 kHz for Freesound HQ previews), quality 0.4 (about 100 kbps stereo, 75 kbps mono).
"""
import argparse
import hashlib
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "unity", "Fable", "Assets", "Fable", "Resources", "Audio")

# Target integrated loudness (LUFS, K-weighted) per kind. Everything is normalised to similar loudness;
# Unity's RoomSound mixes them. One-shots sit a little hotter than beds.
TARGET = {"bed": -23.0, "pos": -22.0, "sfx": -21.0}
PEAK_DBFS = -1.5

# Sources: key -> (path in the downloads folder, SHA-256 of that file). Page URLs, authors and licences are
# in audio/SOURCES.md. Freesound files are the site's HQ previews (OGG Vorbis ~192 kbps, same licence as
# the original); "wm-" files are Wikimedia Commons originals.
SOURCES = {
    "surf-hallsands": ("fs-653395/653395_4893432-hq.ogg", "d58e68745bef41704d2979e084d71261b844adf65b5b37f738b2f810b6c895cd"),
    "lake-lap-boats": ("fs-637945/637945_612689-hq.ogg", "a7533d0afeadbc6aa851c32a7e2410c14e2a1b7fa8cd43c21807b676a05f093f"),
    "bow-wave": ("fs-360631/360631_627541-hq.ogg", "e485ba383d5592660aaa871585416763e4ce20544d8f594b5b5ab0dfba9480c4"),
    "stream-stones": ("fs-730159/730159_12768873-hq.ogg", "07bf4ee3b5055fcfc284bcf3b86cd216d4fa058a979caf6b53060b72e75325dd"),
    "wind-bush-kittpeak": ("fs-135193/135193_1661766-hq.ogg", "9baa931f58e0ebf8cf1613377739bf13c260c4f7927a1ecc35da95dd3b0c6a1a"),
    "wind-pine": ("fs-202989/202989_1667744-hq.ogg", "b23d29cf7f4561b7600b0bfcede0c0f2bea8b586f7f9b848a7f0301f539d8cd8"),
    "wind-open-field": ("fs-553733/553733_4905159-hq.ogg", "8c9922c67a20d18e742c5d59df791a7fc52cbecf15aebb163b2319f459d12fa9"),
    "dawn-hampshire": ("fs-466242/466242_1481531-hq.ogg", "3bcc0b55de833675bb93c24d1149d6d1916df9d1a9a219f91b6af59bfb8b22b8"),
    "harbour-burnham": ("wm-burnham-overy/Burnham_Overy_harbour_atmosphere.ogg", "a37f341b607bcd29a3d78bc7606125a090efabebeb0c70156a2d4e4d7c589dec"),
    "gulls-wildtrack": ("fs-462462/462462_2752236-hq.ogg", "660c7a8606f69b45230c4e982938046afec22264a58e884583b017df3ebe4e74"),
    "wooden-ship": ("fs-195193/195193_1731095-hq.ogg", "2e5e06a9efac098b1d800291a91e8f4a5d64834c09054dcf88a959cb616bf80f"),
    "castle-room": ("fs-774374/774374_16685170-hq.ogg", "938e6b9db51262d5145b4431c4f62bfec7de621bebff0fe4e154e57473024f3e"),
    "creak-v3": ("fs-502511/502511_4921277-hq.ogg", "e1837c077da9a2ff471c5e865a57eff63b947906f48fbbec809e97bc76a18bb4"),
    "creak-v1": ("fs-502505/502505_4921277-hq.ogg", "d0ad9a0ca41619e2d796f169969c732aba6a61d391bbb84016d9cd9cf729eb70"),
    "restaurant-crowd": ("fs-422097/422097_1661766-hq.ogg", "41a65563d08b6891b3db7b569d1aea2262bc8b447ea3b572f777e3d4c5bf9dd2"),
    "night-crickets": ("fs-431519/431519_7522579-hq.ogg", "e58820b1d2284b24223424c3cb8d7c57f0e012330cf28398f3a8d9253da9f51f"),
    "rain-light": ("fs-200273/200273_2322692-hq.ogg", "de245848efb46dd4b5c6a19ff20def6e2bcf78071966fb10faed10a9c8a1c95b"),
    "fire-near": ("fs-779877/779877_1661766-hq.ogg", "01286e6e884e7009ca7eadfdda38fe9fd05c8c94303773464fd3d824a31d523d"),
    "candle-wick": ("fs-680476/680476_12896641-hq.ogg", "f5cf9cb987753c51bb2d4c1831df1822a973a782aa73d843926953e377512d0b"),
    "wall-clock": ("wm-wws-wallclock/WWS_Wallclockwithweightticking.ogg", "cdd7590d2c06723475d16ec269711f5da9339bc4a62168fc351f0dea6ceaaa9f"),
    "blackbirds-dawn": ("fs-341675/341675_1149179-hq.ogg", "f3c56ba5ff49e7c260341430ba927de8270a8dd802fc665479a1434fe48c3600"),
    "blackbird-forest": ("fs-176746/176746_2295143-hq.ogg", "cc80060ad25b3a999c6c39931794509b3d45445edfd5b30735a8edf91f0bc568"),
    "trees-gusts": ("fs-523389/523389_2010973-hq.ogg", "d57fddeea123289a35edb5e98ce6f6e01187f356b8d79627a4b7d4f895040ba8"),
    "leaves-rustle": ("fs-437356/437356_1738686-hq.ogg", "4362fca57c6d7b3a9b1e5ce615d86aa6a1f1364ff6f11eaccfa63299c886734a"),
}

# Outputs. Fields:
#   src, start, length (s); kind bed|pos|sfx; xfade (s, loops); hp/lp (Hz or None);
#   mix: [(src, start, gain_db)] layered under the main section (same length);
#   events: [(src, src_start, dur, at, gain_db_vs_bed_rms, hp)] one-off sounds laid over the finished loop;
#   stereo_offset: pseudo-stereo from a mono source (right channel taken this many seconds later);
#   channel: use one channel of a stereo source (its channels partly cancel when summed);
#   limit: dB of transient peak limiting allowed; clock: tick-period-aligned loop; fade: sfx (in, out) s.
# Start offsets were chosen from RMS / band-energy envelopes (see SOURCES.md for the reasons).
SPECS = {
    # ---- beds: stereo, 40-60 s seamless loops
    "amb.surf": dict(src="surf-hallsands", start=413, length=50, xfade=3, kind="bed", hp=40),
    "amb.harbour": dict(src="lake-lap-boats", start=52, length=48, xfade=3, kind="bed", hp=40, limit=3),
    "amb.sea-open": dict(src="bow-wave", start=2, length=48, xfade=3, kind="bed", hp=40),
    "amb.river": dict(src="stream-stones", start=331, length=50, xfade=3, kind="bed", hp=40),
    "amb.wind-grass": dict(src="wind-bush-kittpeak", start=18, length=48, xfade=4, kind="bed", hp=60),
    "amb.wind-pines": dict(src="wind-pine", start=1, length=50, xfade=4, kind="bed", hp=60),
    "amb.wind-high": dict(src="wind-open-field", start=36, length=40, xfade=4, kind="bed", hp=80,
                          stereo_offset=-34),
    "amb.birds": dict(src="dawn-hampshire", start=140, length=50, xfade=3, kind="bed", hp=150),
    "amb.gulls": dict(src="harbour-burnham", start=1, length=50, xfade=3, kind="bed", hp=80,
                      events=[("gulls-wildtrack", 4.0, 9.0, 8.0, -4, 250),
                              ("gulls-wildtrack", 19.5, 9.5, 31.0, -6, 250)]),
    "amb.rigging": dict(src="wooden-ship", start=383, length=52, xfade=3, kind="bed", hp=45, limit=4),
    "amb.room-tone": dict(src="castle-room", start=180, length=50, xfade=4, kind="bed", hp=40,
                          limit=4,
                          events=[("creak-v3", 0.0, 1.15, 13.0, -6, 120),
                                  ("creak-v1", 0.0, 0.95, 37.5, -9, 120)]),
    "amb.tavern": dict(src="restaurant-crowd", start=199, length=50, xfade=3, kind="bed", hp=90, lp=3800,
                       mix=[("restaurant-crowd", 300, -3)]),
    "amb.night": dict(src="night-crickets", start=169, length=50, xfade=3, kind="bed", hp=60),
    "amb.rain": dict(src="rain-light", start=5, length=50, xfade=3, kind="bed", hp=60, stereo_offset=36, limit=3),
    # ---- positional: mono, 15-30 s loops
    "amb.fire": dict(src="fire-near", start=24, length=25, xfade=2, kind="pos", hp=50, limit=12),
    "amb.candle": dict(src="candle-wick", start=8, length=20, xfade=2, kind="pos", hp=60, limit=10),
    "amb.clock": dict(src="wall-clock", start=8, length=20, kind="pos", hp=60, clock=True, limit=6),
    # ---- Alice one-shots: mono, matching the old synthesised lengths
    "sfx.garden-birds": dict(src="blackbirds-dawn", start=140, length=10, kind="sfx", hp=200, channel=0,
                             fade=(0.3, 0.6)),
    "sfx.birdsong": dict(src="blackbird-forest", start=50.4, length=6, kind="sfx", hp=300, fade=(0.1, 0.4)),
    "sfx.wind-hedges": dict(src="trees-gusts", start=39.5, length=6, kind="sfx", hp=80, fade=(0.4, 0.8)),
    "sfx.leaves": dict(src="leaves-rustle", start=2.2, length=3, kind="sfx", hp=100, fade=(0.1, 0.3)),
}


# ---------------------------------------------------------------- loudness (ITU-R BS.1770-4)
def _k_weight(x, sr):
    # Stage 1: high-shelf (+4 dB above ~1.5 kHz); stage 2: high-pass (~38 Hz). Coefficients from the
    # analogue prototypes, bilinear-transformed for any sample rate (same as pyloudnorm).
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    K = np.tan(np.pi * fc / sr); Vh = 10 ** (G / 20); Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    y = signal.lfilter(b, a, x, axis=0)
    fc, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * fc / sr)
    a = [1, 2 * (K * K - 1) / (1 + K / Q + K * K), (1 - K / Q + K * K) / (1 + K / Q + K * K)]
    return signal.lfilter([1, -2, 1], a, y, axis=0)


def lufs(x, sr):
    x = x if x.ndim == 2 else x[:, None]
    y = _k_weight(x, sr)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if len(y) < blk:
        return -70.0
    z = np.array([(y[i:i + blk] ** 2).mean(0).sum() for i in range(0, len(y) - blk + 1, hop)])
    l = -0.691 + 10 * np.log10(z + 1e-20)
    z = z[l > -70]
    if not len(z):
        return -70.0
    rel = -0.691 + 10 * np.log10(z.mean()) - 10
    z2 = z[(-0.691 + 10 * np.log10(z)) > rel]
    return float(-0.691 + 10 * np.log10(z2.mean()))


# ---------------------------------------------------------------- processing
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(root, key, sr_want=None, cache={}):
    """Decode a source (checked against its SHA-256); resample above 48 kHz down to 48 kHz, or to sr_want."""
    if key not in cache:
        rel, digest = SOURCES[key][:2]
        path = os.path.join(root, rel)
        got = sha256(path)
        if digest and got != digest:
            sys.exit(f"{key}: SHA-256 mismatch for {path}\n  expected {digest}\n  got      {got}")
        x, sr = sf.read(path, always_2d=True, dtype="float64")
        if x.shape[1] == 1:
            x = np.repeat(x, 2, axis=1)
        cache[key] = (x[:, :2], sr)
    x, sr = cache[key]
    want = sr_want or min(sr, 48000)
    if want != sr:
        ck = (key, want)
        if ck not in cache:
            g = np.gcd(int(sr), int(want))
            cache[ck] = (signal.resample_poly(x, want // g, sr // g, axis=0), want)
        return cache[ck]
    return x, sr


def section(root, key, start, dur, sr_out, channel=None):
    x, sr = load(root, key, sr_out)
    a, n = int(round(start * sr)), int(round(dur * sr))
    if a + n > len(x):
        sys.exit(f"{key}: section {start}+{dur}s runs past the end ({len(x) / sr:.1f}s)")
    y = x[a:a + n].copy()
    if channel is not None:  # use one capsule only (for sources whose channels partly cancel when summed)
        y = np.repeat(y[:, channel:channel + 1], 2, axis=1)
    return y


def limit(x, sr, thr_db, window_s=0.004):
    """Transparent peak limiter for short transients (fire pops, clock ticks): the gain is the moving average
    of a running minimum of thr/|x|, so it is at most thr/|x| at every sample (no overshoot)."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    thr = 10 ** (thr_db / 20)
    L = max(3, int(window_s * sr)) | 1
    g = np.minimum(1.0, thr / (np.abs(x).max(axis=1) + 1e-12))
    g = uniform_filter1d(minimum_filter1d(g, L), L)
    return x * g[:, None]


def filt(x, sr, hp, lp):
    if hp:
        x = signal.sosfiltfilt(signal.butter(2, hp, "highpass", fs=sr, output="sos"), x, axis=0)
    if lp:
        x = signal.sosfiltfilt(signal.butter(2, lp, "lowpass", fs=sr, output="sos"), x, axis=0)
    return x


def loop_xfade(seg, n_loop, n_x):
    """seg has n_loop + n_x samples. Blend the tail (seg[n_loop:]) into the head with equal power."""
    t = (np.arange(n_x) + 0.5) / n_x
    fin, fout = np.sin(t * np.pi / 2)[:, None], np.cos(t * np.pi / 2)[:, None]
    out = seg[:n_loop].copy()
    out[:n_x] = seg[:n_x] * fin + seg[n_loop:n_loop + n_x] * fout
    return out


def tick_onsets(m, sr):
    env = np.abs(signal.hilbert(filt(m[:, None], sr, 1000, None)[:, 0]))
    env = signal.sosfiltfilt(signal.butter(2, 200, fs=sr, output="sos"), env)
    peaks, _ = signal.find_peaks(env, height=np.percentile(env, 99) * 0.35, distance=int(0.2 * sr))
    return peaks, env


def clock_loop(root, spec, sr):
    """Cut a loop holding a whole number of tick periods, joined in the quiet between two ticks."""
    x = section(root, spec["src"], spec["start"], spec["length"] + 5.0, sr, spec.get("channel"))
    x = filt(x, sr, spec.get("hp"), spec.get("lp"))
    m = x.mean(1)
    peaks, env = tick_onsets(m, sr)
    d = np.diff(peaks)
    per = float(np.median(d))  # one tick
    # tick and tock can differ; keep an even number of ticks so the tick-tock pattern repeats
    n_ticks = int(round(spec["length"] * sr / per / 2)) * 2
    i0 = 1
    i1 = i0 + n_ticks
    if i1 >= len(peaks):
        sys.exit("clock: not enough detected ticks in the section")
    # cut point: in the gap 45% of the way after a tick
    a = peaks[i0] + int(0.45 * (peaks[i0 + 1] - peaks[i0]))
    b = peaks[i1] + int(0.45 * (peaks[i1 + 1] - peaks[i1]))
    n_x = int(0.03 * sr)
    seg = x[a:b + n_x]
    out = loop_xfade(seg, b - a, n_x)
    spec["_clock"] = dict(tick_s=per / sr, ticks=n_ticks, cv=float(np.std(d) / np.mean(d)))
    return out


def build(root, name, spec, out_dir):
    sr = load(root, spec["src"])[1]
    kind = spec["kind"]
    ch = spec.get("channel")
    if spec.get("clock"):
        y = clock_loop(root, spec, sr)
    else:
        xf = spec.get("xfade", 0) if kind != "sfx" else 0
        n = int(round(spec["length"] * sr)); nx = int(round(xf * sr))
        dur = (n + nx) / sr
        y = section(root, spec["src"], spec["start"], dur, sr, ch)
        if "stereo_offset" in spec:  # pseudo-stereo from a mono source: right channel from a later section
            r = section(root, spec["src"], spec["start"] + spec["stereo_offset"], dur, sr)
            y = np.stack([y.mean(1), r.mean(1)], axis=1)
        for (k2, s2, g2) in spec.get("mix", []):
            y = y + section(root, k2, s2, dur, sr) * 10 ** (g2 / 20)
        y = filt(y, sr, spec.get("hp"), spec.get("lp"))
        if kind == "sfx":
            fi, fo = spec.get("fade", (0.15, 0.3))
            y[: int(fi * sr)] *= np.sin(np.linspace(0, np.pi / 2, int(fi * sr)))[:, None] ** 2
            y[len(y) - int(fo * sr):] *= np.cos(np.linspace(0, np.pi / 2, int(fo * sr)))[:, None] ** 2
        else:
            y = loop_xfade(y, n, nx)
    # one-off events laid over the finished loop, clear of the seam: (src, src_start, dur, at, gain_db, hp)
    ref = 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-12)
    for (k2, s2, d2, at, g2, hp2) in spec.get("events", []):
        e = filt(section(root, k2, s2, d2, sr), sr, hp2, None)
        f = int(0.02 * sr)
        e[:f] *= np.linspace(0, 1, f)[:, None]; e[-f:] *= np.linspace(1, 0, f)[:, None]
        erms = 20 * np.log10(np.sqrt((e ** 2).mean()) + 1e-12)
        i = int(at * sr)
        assert i + len(e) <= len(y), (name, at)
        y[i:i + len(e)] += e * 10 ** ((ref + g2 - erms) / 20)  # gain_db relative to the bed's RMS
    if kind in ("pos", "sfx") or spec.get("mono"):
        y = y.mean(1, keepdims=True)
    # loudness: measure a doubled copy for loops so the seam is counted like the listener hears it
    meas = np.concatenate([y, y]) if kind != "sfx" else y
    g = TARGET[kind] - lufs(meas, sr)
    pk = 20 * np.log10(np.abs(y).max() + 1e-12) + g
    lim = min(spec.get("limit", 0.0), max(0.0, pk - PEAK_DBFS))  # dB of peak limiting allowed
    y = y * 10 ** (g / 20)
    if lim > 0:
        y = limit(y, sr, pk - lim)
        pk -= lim
    if pk > PEAK_DBFS:
        y = y * 10 ** ((PEAK_DBFS - pk) / 20)
    path = os.path.join(out_dir, name + ".ogg")
    q = 0.4
    sf.write(path, y.astype(np.float32), sr, format="OGG", subtype="VORBIS", compression_level=1 - q)
    info = dict(file=os.path.basename(path), seconds=len(y) / sr, channels=y.shape[1], sr=sr,
                lufs=lufs(np.concatenate([y, y]) if kind != "sfx" else y, sr),
                peak=20 * np.log10(np.abs(y).max() + 1e-12), kb=os.path.getsize(path) / 1024, lim=lim)
    info.update(spec.get("_clock", {}))
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("downloads")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    only = set(filter(None, a.only.split(",")))
    os.makedirs(a.out, exist_ok=True)
    for name, spec in SPECS.items():
        if only and name not in only:
            continue
        info = build(os.path.expanduser(a.downloads), name, spec, a.out)
        extra = f" tick={info['tick_s']:.4f}s x{info['ticks']} cv={info['cv']:.3f}" if "tick_s" in info else ""
        print(f"{info['file']:24} {info['seconds']:6.2f}s ch={info['channels']} {info['sr']}Hz "
              f"{info['lufs']:6.1f} LUFS peak {info['peak']:5.1f} dBFS lim {info['lim']:4.1f} dB {info['kb']:6.0f} KB{extra}")


if __name__ == "__main__":
    main()
