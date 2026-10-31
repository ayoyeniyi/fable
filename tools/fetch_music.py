"""
Fable: download the music tracks (CC0 / public-domain recordings from Wikimedia Commons) into the Unity project.

Each track is checked against the SHA-1 Commons records for the file, so a changed upload is refused rather than
shipped under a licence nobody checked. Sources, performers and licences: CREDITS.md. A track that is not Ogg Vorbis (Unity imports only
Vorbis in Ogg) is decoded to mono 22.05 kHz WAV with macOS afconvert.

  python3 tools/fetch_music.py
"""
import hashlib, os, shutil, subprocess, sys, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DST = os.path.join(ROOT, "unity", "Fable", "Assets", "Fable", "Resources", "Audio")
SRC = os.path.join(ROOT, "out", "sources", "music")              # the verified downloads (not committed)
UA = {"User-Agent": "FableBuild/1.0 (https://github.com/ayoyeniyi/fable)"}

TRACKS = [
    # (file in Resources/Audio, Commons original URL, Commons SHA-1)
    ("music.lobby.ogg",
     "https://upload.wikimedia.org/wikipedia/commons/b/b7/Gymnopedie_No._1..ogg",
     "1465775de774068e2d0d24b9ea852b323b4fb0d1"),
    ("music.glumdalclitchs-room.ogg",
     "https://upload.wikimedia.org/wikipedia/commons/d/db/Handel_-_Suites_for_Harpsichord_-_No.5_in_E_major_-_The_Harmonious_Blacksmith.ogg",
     "b719b62f7f55088d624bd06f514d82ff9d41fb65"),
]

os.makedirs(DST, exist_ok=True); os.makedirs(SRC, exist_ok=True)
for name, url, sha1 in TRACKS:
    src = os.path.join(SRC, name)
    if not (os.path.exists(src) and hashlib.sha1(open(src, "rb").read()).hexdigest() == sha1):
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read()
        got = hashlib.sha1(data).hexdigest()
        if got != sha1:
            sys.exit(f"[music] {name}: SHA-1 {got} does not match the recorded {sha1}; check the Commons page before using it")
        open(src, "wb").write(data)
    head = open(src, "rb").read(400)
    if b"vorbis" in head:                                       # Ogg Vorbis: Unity imports it as it is
        shutil.copyfile(src, os.path.join(DST, name)); print(f"[music] {name}: Ogg Vorbis, SHA-1 ok, copied")
    else:                                                       # e.g. FLAC in Ogg, which Unity cannot import: decode to WAV
        out = os.path.join(DST, os.path.splitext(name)[0] + ".wav")
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", "-c", "1", src, out], check=True)   # macOS
        print(f"[music] {name}: not Vorbis, SHA-1 ok, decoded to {os.path.basename(out)} (mono, 22.05 kHz)")
