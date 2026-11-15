"""
Fable: download the Noto fonts the preparation service draws translations with (content/fonts, not committed).

Translate shows Latin, Cyrillic and Greek translations as text in the book's own typeface on the headset. Scripts that
need shaping or right-to-left order (Arabic, Persian, Urdu, Hebrew, the Indic scripts, Thai), Ethiopic, and Chinese,
Japanese and Korean are drawn by the service (interpreter/internal/textimg) with these fonts and sent as a picture, so
none of them is in the app. All are SIL Open Font License 1.1 (content/fonts/OFL.txt); sources and hashes:
content/fonts/SOURCE.md. Each download is checked against its SHA-256 and refused if it differs.

  python3 tools/fetch_fonts.py            # then: ./out/fable-interpreter render-names (the picker's native names)
"""
import hashlib, os, sys, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DST = os.path.join(ROOT, "content", "fonts")
NOTO = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/cfa91e36c7240b622fa7fcd3a90eeff15e28ae1c/fonts/{0}/hinted/ttf/{0}-Regular.ttf"
CJK = "https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Serif/SubsetOTF/{0}/NotoSerif{0}-Regular.otf"
FONTS = [
    # (file, url, SHA-256)
    ("NotoSerif-Regular.ttf", NOTO.format("NotoSerif"), "19e72cd8d595fae5bd74a5206f5d938512e1183d4fed7abb1ec1be1d7efa5f88"),
    ("NotoNaskhArabic-Regular.ttf", NOTO.format("NotoNaskhArabic"), "6f0a92031367b2f5a2078fe9d24f3433122b61a0bad57c423aad8f3c39aa2e6e"),
    ("NotoNastaliqUrdu-Regular.ttf", NOTO.format("NotoNastaliqUrdu"), "4d05b6821862ca1f3c80c47c80a352b47dd349ab73814f60e377eea311e0e42c"),
    ("NotoSerifHebrew-Regular.ttf", NOTO.format("NotoSerifHebrew"), "dfd5a6aefe97a99f68fe43388342913d50bb9fbf6d3afc4d2c7725661bc4a2b1"),
    ("NotoSerifDevanagari-Regular.ttf", NOTO.format("NotoSerifDevanagari"), "e272d11d271c61a8d5d0f65764fd368ae53b9f9dabcce244a8941aa8f32ccc70"),
    ("NotoSerifBengali-Regular.ttf", NOTO.format("NotoSerifBengali"), "c1743dce480147e4563e479ddc31d5ff6544372437428622a54c7c867c50f55b"),
    ("NotoSerifGurmukhi-Regular.ttf", NOTO.format("NotoSerifGurmukhi"), "5ef2d04a6d6fd22959989d14148dcf0ffbb970cc35e6316ba63cd5c146f32667"),
    ("NotoSerifGujarati-Regular.ttf", NOTO.format("NotoSerifGujarati"), "b8961ff6faf8e5561e3d0109953c4a9798e9bb8e8d48f66c3d1ef038fe45c940"),
    ("NotoSerifTamil-Regular.ttf", NOTO.format("NotoSerifTamil"), "8a8cb015a3afec2998e01aabcb42fb365994132d95dbc2150208b4fefd8dc2e4"),
    ("NotoSerifTelugu-Regular.ttf", NOTO.format("NotoSerifTelugu"), "2b376e0351fb140f2edad9c54e8977f4f1effc4fe72443e152b3f6ad392c6f5f"),
    ("NotoSerifKannada-Regular.ttf", NOTO.format("NotoSerifKannada"), "95a78c95359dc59b9ec56bdc5bdf8a9642394d2ef87ded945fb3885893b3eac6"),
    ("NotoSerifMalayalam-Regular.ttf", NOTO.format("NotoSerifMalayalam"), "45c34ac8c169a37a4fbb5b8fbf507def328bbf36180b08095726d460d577ec1d"),
    ("NotoSerifThai-Regular.ttf", NOTO.format("NotoSerifThai"), "747b5bb1fdd329850ddd3218d872a3d2a96ab0dd544f51e5300c6d1b12071b62"),
    ("NotoSerifEthiopic-Regular.ttf", NOTO.format("NotoSerifEthiopic"), "4d14f10b7436e762d41ddd9486acdc708744bf377a575d855b81b847b9590779"),
    ("NotoSerifSC-Regular.otf", CJK.format("SC"), "e8f396decc1f0963a016a989c3d8852e863d1350996f573860a80767c83a1cd3"),
    ("NotoSerifTC-Regular.otf", CJK.format("TC"), "63515eb0622d589a2f4062e8757c598b3da3bffd053f69abd181c210158ef10c"),
    ("NotoSerifJP-Regular.otf", CJK.format("JP"), "2c9a12dbd4f2408c4610c7ee84a108b62d7236c3775baed618c64d9cb44b2f04"),
    ("NotoSerifKR-Regular.otf", CJK.format("KR"), "5ea012e15cb7eacc1f680aee1703f3b164791b1443ea3e52b65080cca5d179cf"),
]

os.makedirs(DST, exist_ok=True)
total = 0
for name, url, sha in FONTS:
    path = os.path.join(DST, name)
    if os.path.exists(path) and hashlib.sha256(open(path, "rb").read()).hexdigest() == sha:
        total += os.path.getsize(path); continue
    data = urllib.request.urlopen(url).read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha:
        sys.exit(f"[fonts] {name}: SHA-256 {got} does not match the recorded {sha}; check the source before using it")
    open(path, "wb").write(data); total += len(data)
    print(f"[fonts] {name}: {len(data) // 1024} kB, SHA-256 ok")
print(f"[fonts] {len(FONTS)} fonts in content/fonts, {total / 1e6:.1f} MB")
