# Ambient sound sources

Fable's ambient beds (`amb.<kind>.ogg`), positional loops (fire, candle, clock) and four Alice one-shots
(`sfx.garden-birds`, `sfx.birdsong`, `sfx.wind-hedges`, `sfx.leaves`) in
`unity/Fable/Assets/Fable/Resources/Audio/` are cut from real field recordings. Every other `sfx.*` clip is
still synthesised by `audio/synth_sfx.py` / `audio/synth_rooms.py`.

## Licence policy

Only CC0 / public domain, or CC-BY (attribution recorded below and in `CREDITS.md`). No NonCommercial, no
NoDerivatives, no ShareAlike, no Sampling+, nothing with an unclear licence. Each licence was read on the
file's own page (Freesound sound page, Wikimedia Commons file page), not from a search listing. Of the 24
sources, 22 are CC0 1.0 and 2 are CC BY 4.0.

Freesound originals need a login; the files used here are Freesound's HQ previews (OGG Vorbis, ~192 kbps,
same licence as the original, linked from each sound page). Wikimedia Commons files are the originals.

## Regenerating

1. Download every file in the table below into one folder, keeping the subfolder and file name shown
   (e.g. `~/fable-sound-downloads/fs-653395/653395_4893432-hq.ogg`). Treat it as untrusted data.
2. Run

   ```
   python3 -m venv ~/fable-sound-tools-venv
   ~/fable-sound-tools-venv/bin/pip install numpy soundfile scipy
   ~/fable-sound-tools-venv/bin/python -I audio/make_ambience.py ~/fable-sound-downloads
   ```

`make_ambience.py` checks each file's SHA-256, then for every output: cuts the section below, high-passes
(2nd-order Butterworth, zero phase), makes a seamless loop with an equal-power (sin/cos) crossfade of the tail
that follows the loop into its head (beds 3-4 s, positional loops 2 s; the clock is cut to a whole, even number
of detected ticks with a 30 ms crossfade in the quiet between two ticks), downmixes mono outputs, normalises
to a K-weighted integrated loudness (BS.1770, gated) of -23 LUFS for beds, -22 for positional loops and
-21 for one-shots, keeps the sample peak at or below -1.5 dBFS (a short look-ahead peak limiter tames only the
transients listed under "limit"; otherwise the gain is lowered), and encodes OGG Vorbis quality 0.4 at the
source rate (48 kHz, or 44.1 kHz where the source is 44.1 kHz; 96 kHz sources are resampled to 48 kHz).
Sections were chosen from RMS and band-energy envelopes over time (low-band energy for wind on the mic or
engines, 80-300 Hz for aircraft, crest factor for handling bumps), not by ear.

## Outputs

Beds are stereo loops; positional loops and sfx are mono. "Section" is in seconds of the source; a loop of
L seconds with an X-second crossfade reads L + X seconds from the start offset.

| Output | What it is | Length | Source (page) | Author | Licence | Original | Section used and edits |
|---|---|---|---|---|---|---|---|
| `amb.surf` | waves on shingle and rock, Hallsands, south Devon | 50 s, st | [Waves on Shingle and Rock Mid Afternoon](https://freesound.org/people/leesparey/sounds/653395/) | leesparey | CC0 1.0 | WAV 48 kHz st, 776.9 s | 413-466; HP 40 Hz; 3 s crossfade |
| `amb.harbour` | gentle lake waves lapping at boats on a beach | 48 s, st | [water lake waves light gentle lap at boats on beach](https://freesound.org/people/kyles/sounds/637945/) | kyles | CC0 1.0 | FLAC 48 kHz st, 122.9 s | 52-103; HP 40 Hz; 3 s crossfade; 0.5 dB peak limiting |
| `amb.sea-open` | bow wave of an 8 m sailing boat, close (no engine) | 48 s, st | [Sailing boat, bow wave (close perspective)](https://freesound.org/people/Pfannkuchn/sounds/360631/) | Pfannkuchn | CC0 1.0 | WAV 48 kHz/24 st, 78.7 s | 2-53; HP 40 Hz; 3 s crossfade |
| `amb.river` | a stream over stones in fields, spring | 50 s, st | [Stream flow over the stones in the fields in spring](https://freesound.org/people/lastraindrop/sounds/730159/) | lastraindrop | CC0 1.0 | 48 kHz st, 833.7 s | 331-384; HP 40 Hz; 3 s crossfade |
| `amb.wind-grass` | wind in bushes and foliage, close (Kitt Peak, Arizona) | 48 s, st | [Wind blowing in the bush on the top of Kitt Peak mountain](https://freesound.org/people/felix.blume/sounds/135193/) | felix.blume (Felix Blume) | CC0 1.0 | 48 kHz MS→st, 120.3 s | 18-70; HP 60 Hz; 4 s crossfade |
| `amb.wind-pines` | strong wind in a pine tree (AB pair, Korčula) | 50 s, st | [Wind_pine.wav](https://freesound.org/people/sinewave1kHz/sounds/202989/) | sinewave1kHz | CC0 1.0 | WAV 48 kHz st, 94.4 s | 1-55; HP 60 Hz; 4 s crossfade |
| `amb.wind-high` | open-field wind, northern Mexico (airy, no foliage) | 40 s, st | [wind open field](https://freesound.org/people/Globofonia/sounds/553733/) | Globofonia | CC0 1.0 | 48 kHz dual-mono, 122.1 s | left 36-80, right 2-46 (pseudo-stereo from the mono signal); HP 80 Hz; 4 s crossfade |
| `amb.birds` | dawn chorus, Hampshire countryside, April | 50 s, st | [Dawn chorus - Hampshire countryside Springtime](https://freesound.org/people/richwise/sounds/466242/) | richwise | CC0 1.0 | 48 kHz st, 592.8 s | 140-193 (between the two distant aircraft); HP 150 Hz; 3 s crossfade |
| `amb.gulls` | harbour birds at Burnham Overy Staithe, Norfolk, plus two closer gull passages | 50 s, st | [Burnham Overy harbour atmosphere](https://commons.wikimedia.org/wiki/File:Burnham_Overy_harbour_atmosphere_(W_PALEARCTIC_COASTAL_R4_C4).ogg) + [Seagulls / gaviotas clean wildtrack](https://freesound.org/people/Soojay/sounds/462462/) | Richard Margoschis (recordist), The British Library; Soojay | CC BY 4.0; CC0 1.0 | OGG 44.1 kHz st, 55.9 s (Sept 1991); WAV 48 kHz st, 76.4 s | Burnham 1-54, HP 80 Hz, 3 s crossfade; gull calls 4-13 laid at 8 s (-4 dB vs bed RMS) and 19.5-29 at 31 s (-6 dB), both HP 250 Hz, resampled to 44.1 kHz |
| `amb.rigging` | large creaking wooden ship at sea: timbers, ropes, waves | 52 s, st | [LargeWoodenShip.mp3](https://freesound.org/people/PimFeijen/sounds/195193/) | PimFeijen | CC0 1.0 | MP3 44.1 kHz st, 600 s | 383-438; HP 45 Hz; 3 s crossfade |
| `amb.room-tone` | empty room of an old castle (Schloss), morning, with two faint floorboard creaks | 50 s, st | [AMB_INT_Old Castle_Schloß empty room morning](https://freesound.org/people/mogrm/sounds/774374/) + [Wood Creak Single V3](https://freesound.org/people/Rudmer_Rotteveel/sounds/502511/), [V1](https://freesound.org/people/Rudmer_Rotteveel/sounds/502505/) | mogrm; Rudmer_Rotteveel | CC0 1.0 | 48 kHz st, 487.8 s; creaks 1.2 s, 1.0 s | 180-234, HP 40 Hz, 4 s crossfade; creak V3 at 13 s (-6 dB vs bed RMS), V1 at 37.5 s (-9 dB), HP 120 Hz; no clock |
| `amb.tavern` | crowded restaurant walla, São Paulo (Portuguese, words blurred) | 50 s, st | [Restaurant Atmosphere (crowded)](https://freesound.org/people/felix.blume/sounds/422097/) | felix.blume (Felix Blume) | CC0 1.0 | WAV 96 kHz/24 MS st, 600.7 s | 199-252 overlaid with 300-353 at -3 dB (two crowds blur single voices); HP 90 Hz, LP 3.8 kHz; resampled to 48 kHz; 3 s crossfade |
| `amb.night` | country garden at night, central France: crickets, frogs, an owl now and then | 50 s, st | [COUNTRY_NIGHT_CRICKETS.wav](https://freesound.org/people/keng-wai-chane-chick-te/sounds/431519/) | keng-wai-chane-chick-te | CC0 1.0 | WAV 96 kHz st, 300.6 s | 169-222; HP 60 Hz; resampled to 48 kHz; 3 s crossfade |
| `amb.rain` | light rain, rural, no other sounds | 50 s, st | [Rain light 2 (rural)](https://freesound.org/people/jmbphilmes/sounds/200273/) | jmbphilmes | CC0 1.0 | 48 kHz mono, 95.1 s | left 5-58, right 41-94 (pseudo-stereo); HP 60 Hz; 3 s crossfade; 0.8 dB peak limiting |
| `amb.fire` | wood fire crackling, close to the flames | 25 s, mono | [Wood fire crackling, near flames](https://freesound.org/people/felix.blume/sounds/779877/) | felix.blume (Felix Blume) | CC0 1.0 | 48 kHz MS st, 181.0 s | 24-51; mono; HP 50 Hz; 2 s crossfade; 12 dB limiting of the pops (4 ms window); ends at -24.8 LUFS |
| `amb.candle` | double wood-wick candle flame, soft crackle | 20 s, mono | [Candle wood wick flame mono 01.wav](https://freesound.org/people/roisin.gleeson/sounds/680476/) | roisin.gleeson | CC0 1.0 | WAV 48 kHz mono, 64.4 s | 8-30; HP 60 Hz; 2 s crossfade; 10 dB limiting of the crackles; ends at -26.5 LUFS |
| `amb.clock` | office wall clock with weight in a wooden case (Celje, 2nd half of the 20th century) | 20.75 s, mono | [WWS Wallclockwithweightticking.ogg](https://commons.wikimedia.org/wiki/File:WWS_Wallclockwithweightticking.ogg) | Work With Sounds / Technical Museum of Slovenia; recordist Dušan Oblak | CC BY 4.0 | OGG 48 kHz mono, 53.9 s | from ~9 s: exactly 28 ticks (detected tick 0.741 s, tick/tock 0.728/0.752 s; an even count keeps the pattern), cut 45 % into a gap, 30 ms crossfade; HP 60 Hz; 2.2 dB limiting |
| `sfx.garden-birds` | blackbirds at dawn, UK | 10 s, mono | [blackbirds at dawn.wav](https://freesound.org/people/squashy555/sounds/341675/) | squashy555 | CC0 1.0 | WAV 44.1 kHz st, 291.3 s | 140-150, left channel only (the channels partly cancel when summed); HP 200 Hz; fades 0.3/0.6 s |
| `sfx.birdsong` | one blackbird phrase, Swedish forest | 6 s, mono | [Blackbird in forest.wav](https://freesound.org/people/carlito62/sounds/176746/) | carlito62 | CC0 1.0 | WAV 44.1 kHz st, 120.5 s | 50.4-56.4; HP 300 Hz; fades 0.1/0.4 s |
| `sfx.wind-hedges` | a gust through branches and leaves, close | 6 s, mono | [Forest, close up of trees rustling in the wind.wav](https://freesound.org/people/Anya_Media/sounds/523389/) | Anya_Media | CC0 1.0 | WAV 48 kHz st, 139.5 s | 39.5-45.5 (one gust); HP 80 Hz; fades 0.4/0.8 s |
| `sfx.leaves` | a short rustle of leaves | 3 s, mono | [Rustling leaves](https://freesound.org/people/giddster/sounds/437356/) | giddster | CC0 1.0 | 48 kHz st, 8.0 s | 2.2-5.2; HP 100 Hz; fades 0.1/0.3 s |

Licence texts: CC0 1.0 https://creativecommons.org/publicdomain/zero/1.0/ ; CC BY 4.0
https://creativecommons.org/licenses/by/4.0/ . The two CC BY 4.0 sources were edited (cut, filtered, looped,
level-normalised, re-encoded; Burnham Overy has gull calls from another recording laid over it).

## Downloaded files

Folder and file names as `make_ambience.py` expects them under the downloads folder.

| File | Direct download URL | SHA-256 |
|---|---|---|
| `fs-653395/653395_4893432-hq.ogg` | https://cdn.freesound.org/previews/653/653395_4893432-hq.ogg | `d58e68745bef41704d2979e084d71261b844adf65b5b37f738b2f810b6c895cd` |
| `fs-637945/637945_612689-hq.ogg` | https://cdn.freesound.org/previews/637/637945_612689-hq.ogg | `a7533d0afeadbc6aa851c32a7e2410c14e2a1b7fa8cd43c21807b676a05f093f` |
| `fs-360631/360631_627541-hq.ogg` | https://cdn.freesound.org/previews/360/360631_627541-hq.ogg | `e485ba383d5592660aaa871585416763e4ce20544d8f594b5b5ab0dfba9480c4` |
| `fs-730159/730159_12768873-hq.ogg` | https://cdn.freesound.org/previews/730/730159_12768873-hq.ogg | `07bf4ee3b5055fcfc284bcf3b86cd216d4fa058a979caf6b53060b72e75325dd` |
| `fs-135193/135193_1661766-hq.ogg` | https://cdn.freesound.org/previews/135/135193_1661766-hq.ogg | `9baa931f58e0ebf8cf1613377739bf13c260c4f7927a1ecc35da95dd3b0c6a1a` |
| `fs-202989/202989_1667744-hq.ogg` | https://cdn.freesound.org/previews/202/202989_1667744-hq.ogg | `b23d29cf7f4561b7600b0bfcede0c0f2bea8b586f7f9b848a7f0301f539d8cd8` |
| `fs-553733/553733_4905159-hq.ogg` | https://cdn.freesound.org/previews/553/553733_4905159-hq.ogg | `8c9922c67a20d18e742c5d59df791a7fc52cbecf15aebb163b2319f459d12fa9` |
| `fs-466242/466242_1481531-hq.ogg` | https://cdn.freesound.org/previews/466/466242_1481531-hq.ogg | `3bcc0b55de833675bb93c24d1149d6d1916df9d1a9a219f91b6af59bfb8b22b8` |
| `wm-burnham-overy/Burnham_Overy_harbour_atmosphere.ogg` | https://upload.wikimedia.org/wikipedia/commons/2/25/Burnham_Overy_harbour_atmosphere_%28W_PALEARCTIC_COASTAL_R4_C4%29.ogg | `a37f341b607bcd29a3d78bc7606125a090efabebeb0c70156a2d4e4d7c589dec` |
| `fs-462462/462462_2752236-hq.ogg` | https://cdn.freesound.org/previews/462/462462_2752236-hq.ogg | `660c7a8606f69b45230c4e982938046afec22264a58e884583b017df3ebe4e74` |
| `fs-195193/195193_1731095-hq.ogg` | https://cdn.freesound.org/previews/195/195193_1731095-hq.ogg | `2e5e06a9efac098b1d800291a91e8f4a5d64834c09054dcf88a959cb616bf80f` |
| `fs-774374/774374_16685170-hq.ogg` | https://cdn.freesound.org/previews/774/774374_16685170-hq.ogg | `938e6b9db51262d5145b4431c4f62bfec7de621bebff0fe4e154e57473024f3e` |
| `fs-502511/502511_4921277-hq.ogg` | https://cdn.freesound.org/previews/502/502511_4921277-hq.ogg | `e1837c077da9a2ff471c5e865a57eff63b947906f48fbbec809e97bc76a18bb4` |
| `fs-502505/502505_4921277-hq.ogg` | https://cdn.freesound.org/previews/502/502505_4921277-hq.ogg | `d0ad9a0ca41619e2d796f169969c732aba6a61d391bbb84016d9cd9cf729eb70` |
| `fs-422097/422097_1661766-hq.ogg` | https://cdn.freesound.org/previews/422/422097_1661766-hq.ogg | `41a65563d08b6891b3db7b569d1aea2262bc8b447ea3b572f777e3d4c5bf9dd2` |
| `fs-431519/431519_7522579-hq.ogg` | https://cdn.freesound.org/previews/431/431519_7522579-hq.ogg | `e58820b1d2284b24223424c3cb8d7c57f0e012330cf28398f3a8d9253da9f51f` |
| `fs-200273/200273_2322692-hq.ogg` | https://cdn.freesound.org/previews/200/200273_2322692-hq.ogg | `de245848efb46dd4b5c6a19ff20def6e2bcf78071966fb10faed10a9c8a1c95b` |
| `fs-779877/779877_1661766-hq.ogg` | https://cdn.freesound.org/previews/779/779877_1661766-hq.ogg | `01286e6e884e7009ca7eadfdda38fe9fd05c8c94303773464fd3d824a31d523d` |
| `fs-680476/680476_12896641-hq.ogg` | https://cdn.freesound.org/previews/680/680476_12896641-hq.ogg | `f5cf9cb987753c51bb2d4c1831df1822a973a782aa73d843926953e377512d0b` |
| `wm-wws-wallclock/WWS_Wallclockwithweightticking.ogg` | https://upload.wikimedia.org/wikipedia/commons/0/07/WWS_Wallclockwithweightticking.ogg | `cdd7590d2c06723475d16ec269711f5da9339bc4a62168fc351f0dea6ceaaa9f` |
| `fs-341675/341675_1149179-hq.ogg` | https://cdn.freesound.org/previews/341/341675_1149179-hq.ogg | `f3c56ba5ff49e7c260341430ba927de8270a8dd802fc665479a1434fe48c3600` |
| `fs-176746/176746_2295143-hq.ogg` | https://cdn.freesound.org/previews/176/176746_2295143-hq.ogg | `cc80060ad25b3a999c6c39931794509b3d45445edfd5b30735a8edf91f0bc568` |
| `fs-523389/523389_2010973-hq.ogg` | https://cdn.freesound.org/previews/523/523389_2010973-hq.ogg | `d57fddeea123289a35edb5e98ce6f6e01187f356b8d79627a4b7d4f895040ba8` |
| `fs-437356/437356_1738686-hq.ogg` | https://cdn.freesound.org/previews/437/437356_1738686-hq.ogg | `4362fca57c6d7b3a9b1e5ce615d86aa6a1f1364ff6f11eaccfa63299c886734a` |

## Considered and rejected

Wind recordings with heavy sub-80 Hz energy (wind on the microphone): Patagonian grass (felix.blume 139337),
Anatolian plain (167684), foliage shotgun (517773), clifftop herring gulls (818829). A mouth-blown "desert wind"
(697217, not a field recording). Room tones with 59-60 Hz mains hum (641306, 652415). Pub recordings with
music (398224) or close, probably intelligible English talk (403285). A torch "loop" that is a few seconds repeated (483692).
