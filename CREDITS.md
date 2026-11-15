# Credits

Everything Fable shows or plays, where it comes from, and under what licence. Fable's own code and content (the
environments, synthesised sounds, schemas, scripts and composed images) were made for this project; the
ambient recordings are credited below. Nothing is used without a
recorded licence; the per-folder `SOURCE.md` files hold the hashes and download details.

## Books (the text you read)

| Book | Edition | Licence |
|---|---|---|
| *Alice's Adventures in Wonderland*, Lewis Carroll (1865) | Standard Ebooks, https://standardebooks.org/ebooks/lewis-carroll/alices-adventures-in-wonderland/john-tenniel | text public domain (US); SE's edits and markup CC0 1.0 |
| *The Wonderful Wizard of Oz*, L. Frank Baum (1900) | Standard Ebooks, https://standardebooks.org/ebooks/l-frank-baum/the-wonderful-wizard-of-oz | text public domain (US); SE CC0 1.0 |
| *Gulliver's Travels*, Jonathan Swift (1726) | Standard Ebooks, https://standardebooks.org/ebooks/jonathan-swift/gullivers-travels | text public domain (US); SE CC0 1.0 |
| *Pride and Prejudice*, Jane Austen (1813) | Standard Ebooks, https://standardebooks.org/ebooks/jane-austen/pride-and-prejudice | text public domain (US); SE CC0 1.0 |
| *Moby-Dick*, Herman Melville (1851) | Standard Ebooks, https://standardebooks.org/ebooks/herman-melville/moby-dick | text public domain (US); SE CC0 1.0 |
| *The War of the Worlds*, H. G. Wells (1898) | Standard Ebooks, https://standardebooks.org/ebooks/h-g-wells/the-war-of-the-worlds | text public domain (US); SE CC0 1.0 |
| *Treasure Island*, Robert Louis Stevenson (1883) | Standard Ebooks, https://standardebooks.org/ebooks/robert-louis-stevenson/treasure-island | text public domain (US); SE CC0 1.0 |
| *Frankenstein*, Mary Shelley (1818; the 1831 revised text) | Standard Ebooks, https://standardebooks.org/ebooks/mary-shelley/frankenstein | text public domain (US); SE CC0 1.0 |
| *Around the World in Eighty Days*, Jules Verne (1873), translated by George Makepeace Towle | Standard Ebooks, https://standardebooks.org/ebooks/jules-verne/around-the-world-in-eighty-days/george-makepeace-towle | text public domain (US); SE CC0 1.0 |
| *The Odyssey*, Homer, translated by Samuel Butler (1900) | Project Gutenberg #1727, https://www.gutenberg.org/ebooks/1727 | text public domain (US); Gutenberg header and licence removed as its licence allows |

Details and file hashes: `content/books/<slug>/SOURCE.md`. Standard Ebooks is a volunteer project; the editions were
produced by Alex Cabal (Alice, Treasure Island, Frankenstein, Around the World in Eighty Days), Michael Atkinson (Oz, Gulliver), Alex Cabal and Alina Pyzowski
(Pride and Prejudice, The War of the Worlds) and Robin Whittleton (Moby-Dick). The Odyssey's Gutenberg text credits Jim Tinsley
and David Widger.

## Dictionary (Define)

*Webster's Revised Unabridged Dictionary* (G. & C. Merriam, 1913), the Project Gutenberg transcription #29765,
public domain (US), cut to the words Fable's ten books use. `content/dictionary/SOURCE.md`.

## Book covers (the lobby shelf)

- **Alice:** Standard Ebooks cover (CC0 1.0), after *Amanita*, Ivan Shishkin, 1879 (public domain).
- **Oz:** Standard Ebooks cover (CC0 1.0), after *Heroic Landscape with Rainbow*, Joseph Anton Koch, 1824 (public domain).
- **Gulliver:** Standard Ebooks cover (CC0 1.0), after *Gulliver and the Lilliputians*, Jehan-Georges Vibert, 1870 (public domain).
- **Pride and Prejudice:** Standard Ebooks cover (CC0 1.0), after *A Wet Sunday Morning*, Edmund Blair Leighton, 1896 (public domain).
- **Moby-Dick:** Standard Ebooks cover (CC0 1.0), after *The Flying Dutchman*, Albert Pinkham Ryder, 1887 (public domain).
- **The War of the Worlds:** Standard Ebooks cover (CC0 1.0), after *The Great Fire of London*, unknown artist, 17th century (public domain).
- **Treasure Island:** Standard Ebooks cover (CC0 1.0), after *One More Step, Mr. Hands*, N. C. Wyeth, 1911 (public domain).
- **Frankenstein:** Standard Ebooks cover (CC0 1.0), after *Portrait of Adam*, Giuseppe Arcimboldo, 1578 (public domain).
- **Around the World in Eighty Days:** Standard Ebooks cover (CC0 1.0), after *Train on the Way*, Isaac Levitan, c. 1895 (public domain).
- **The Odyssey:** composed for Fable from *Ulysses and Calypso*, Arnold Böcklin, 1882, Kunstmuseum Basel (public
  domain; reproduction via Wikimedia Commons, https://commons.wikimedia.org/wiki/File:Arnold_B%C3%B6cklin_008.jpg).

`content/covers/SOURCE.md`.

## Book maps (Peek on a place)

Details, hashes and processing for each image: `content/maps/<slug>/SOURCE.md` and `content/maps/_globe/SOURCE.md`.
The contract is `docs/MAPS.md`.

| Map | Source | Licence |
|---|---|---|
| The globe (`content/maps/_globe/earth.jpg`) | NASA Blue Marble: *Whole world - land and oceans 12000.jpg* (NASA Goddard Space Flight Center), https://commons.wikimedia.org/wiki/File:Whole_world_-_land_and_oceans_12000.jpg, with the sea from *Blue Marble Next Generation + topography + bathymetry.jpg* (Reto Stöckli, NASA Earth Observatory), https://commons.wikimedia.org/wiki/File:Blue_Marble_Next_Generation_%2B_topography_%2B_bathymetry.jpg | public domain (NASA) |
| Treasure Island (`content/maps/treasure/island.jpg`) | Robert Louis Stevenson, map of Treasure Island (1883; 1885 Cassell printing, Beinecke Library copy), https://commons.wikimedia.org/wiki/File:Treasure-island-map.jpg | public domain |
| Gulliver's Travels, plates I–IV (`content/maps/gulliver/{lilliput,brobdingnag,laputa,houyhnhnms}.jpg`) | maps from the first edition, Benjamin Motte, London, 1726; Thomas Fisher Rare Book Library, University of Toronto, via the Internet Archive: https://archive.org/details/travelsintosever01swif (pages n21, n177), https://archive.org/details/travelsintosever02swif (pages n13, n181) | public domain |
| Wonderland and the Land of Oz (`content/maps/alice/wonderland.jpg`, `content/maps/oz/oz.jpg`) | drawn for Fable by `tools/draw_map.py` from hand-written layouts; lettering EB Garamond (SIL OFL 1.1) | CC0 1.0 (Fable's own) |

Coordinates of real places (all eight books' `map.json`): looked up with OpenStreetMap Nominatim and checked by
hand; coordinates © OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright). Positions of
invented and traditionally identified places are Fable's own.

## Typefaces

- **EB Garamond** (the reading page), Georg Duffner and Octavio Pardo, SIL Open Font License 1.1
  (`unity/Fable/Assets/Fable/Fonts/EBGaramond-OFL.txt`).
- **League Spartan Bold**, The League of Moveable Type / The League Spartan Project Authors, SIL Open Font License 1.1
  (`content/covers/fonts/OFL.txt`). Used only to letter the Odyssey cover image, in Standard Ebooks' style; it does
  not ship in the app.
- Standard Ebooks' covers carry League Spartan and Sorts Mill Goudy (The League of Moveable Type, SIL OFL 1.1),
  rendered into the images by Standard Ebooks.
- **Noto** (Noto Serif; Noto Serif Devanagari, Bengali, Gurmukhi, Gujarati, Tamil, Telugu, Kannada, Malayalam, Thai,
  Hebrew, Ethiopic; Noto Naskh Arabic; Noto Nastaliq Urdu; Noto Serif CJK SC, TC, JP, KR), The Noto Project Authors,
  SIL Open Font License 1.1 (`content/fonts/OFL.txt`; sources, commits and SHA-256 in `content/fonts/SOURCE.md`).
  Used by the preparation service to draw translations in scripts the headset's text cannot shape, and once at build
  time for the language picker's native names (`unity/Fable/Assets/Fable/Resources/LanguageNames.png`, the only part
  in the app). The fonts themselves do not ship in the app.

## Music

| Where | Piece | Performer / source | Licence |
|---|---|---|---|
| Lobby | Erik Satie, *Gymnopédie No. 1* (1888) | recording by Teknopazzo, Wikimedia Commons, https://commons.wikimedia.org/wiki/File:Gymnopedie_No._1..ogg (SHA-1 `1465775de774068e2d0d24b9ea852b323b4fb0d1`) | CC0 1.0 (recording); composition public domain |
| Glumdalclitch's room (Gulliver) | George Frideric Handel, *The Harmonious Blacksmith*, Air and variations from Suite No. 5 in E major, HWV 430 (1720) | Musopen (https://musopen.org/music/1183/georg-friedrich-handel/8-great-suites-hwv-426-433/), via Wikimedia Commons, https://commons.wikimedia.org/wiki/File:Handel_-_Suites_for_Harpsichord_-_No.5_in_E_major_-_The_Harmonious_Blacksmith.ogg (SHA-1 `b719b62f7f55088d624bd06f514d82ff9d41fb65`) | CC0 1.0 (recording); composition public domain |
| Calypso's cave (Odyssey) | a sparse lyre in the Dorian mode | composed and synthesised for Fable by `audio/synth_rooms.py` | CC0 1.0 (Fable's own) |

`tools/fetch_music.py` downloads the two recordings and refuses any file whose SHA-1 differs from the one above. The
Satie file is FLAC in Ogg, which Unity cannot import, so it is decoded to mono WAV; the music is otherwise unedited.

## Sound

The ambient beds, the fire, candle and clock loops, and four Alice one-shots (`sfx.garden-birds`,
`sfx.birdsong`, `sfx.wind-hedges`, `sfx.leaves`) are real field recordings (CC0 1.0 or CC BY 4.0), cut, looped
and levelled by `audio/make_ambience.py`; see "Ambient sound recordings" below and `audio/SOURCES.md`. The other
sound effects are still synthesised from code by `audio/synth_sfx.py` (the Alice rooms) and
`audio/synth_rooms.py`, CC0 1.0 (Fable's own).

## Ambient sound recordings

Edited (cut, filtered, looped, normalised, re-encoded). Section offsets, edits and SHA-256 hashes are in
`audio/SOURCES.md`.

| Output | Recording | Author | Licence |
|---|---|---|---|
| `amb.surf` | [Waves on Shingle and Rock Mid Afternoon](https://freesound.org/people/leesparey/sounds/653395/) | leesparey | CC0 1.0 |
| `amb.harbour` | [water lake waves light gentle lap at boats on beach](https://freesound.org/people/kyles/sounds/637945/) | kyles | CC0 1.0 |
| `amb.sea-open` | [Sailing boat, bow wave (close perspective)](https://freesound.org/people/Pfannkuchn/sounds/360631/) | Pfannkuchn | CC0 1.0 |
| `amb.river` | [Stream flow over the stones in the fields in spring](https://freesound.org/people/lastraindrop/sounds/730159/) | lastraindrop | CC0 1.0 |
| `amb.wind-grass` | [Wind blowing in the bush on the top of Kitt Peak mountain](https://freesound.org/people/felix.blume/sounds/135193/) | Felix Blume | CC0 1.0 |
| `amb.wind-pines` | [Wind_pine.wav](https://freesound.org/people/sinewave1kHz/sounds/202989/) | sinewave1kHz | CC0 1.0 |
| `amb.wind-high` | [wind open field](https://freesound.org/people/Globofonia/sounds/553733/) | Globofonia | CC0 1.0 |
| `amb.birds` | [Dawn chorus - Hampshire countryside Springtime](https://freesound.org/people/richwise/sounds/466242/) | richwise | CC0 1.0 |
| `amb.gulls` | [Burnham Overy harbour atmosphere](https://commons.wikimedia.org/wiki/File:Burnham_Overy_harbour_atmosphere_(W_PALEARCTIC_COASTAL_R4_C4).ogg), with gull calls from [Seagulls / gaviotas clean wildtrack](https://freesound.org/people/Soojay/sounds/462462/) | Richard Margoschis / The British Library; Soojay | CC BY 4.0; CC0 1.0 |
| `amb.rigging` | [LargeWoodenShip.mp3](https://freesound.org/people/PimFeijen/sounds/195193/) | PimFeijen | CC0 1.0 |
| `amb.room-tone` | [AMB_INT_Old Castle_Schloß empty room morning](https://freesound.org/people/mogrm/sounds/774374/), creaks from [Wood Creak Single V3](https://freesound.org/people/Rudmer_Rotteveel/sounds/502511/) and [V1](https://freesound.org/people/Rudmer_Rotteveel/sounds/502505/) | mogrm; Rudmer Rotteveel | CC0 1.0 |
| `amb.tavern` | [Restaurant Atmosphere (crowded)](https://freesound.org/people/felix.blume/sounds/422097/) | Felix Blume | CC0 1.0 |
| `amb.night` | [COUNTRY_NIGHT_CRICKETS.wav](https://freesound.org/people/keng-wai-chane-chick-te/sounds/431519/) | keng-wai-chane-chick-te | CC0 1.0 |
| `amb.rain` | [Rain light 2 (rural)](https://freesound.org/people/jmbphilmes/sounds/200273/) | jmbphilmes | CC0 1.0 |
| `amb.fire` | [Wood fire crackling, near flames](https://freesound.org/people/felix.blume/sounds/779877/) | Felix Blume | CC0 1.0 |
| `amb.candle` | [Candle wood wick flame mono 01.wav](https://freesound.org/people/roisin.gleeson/sounds/680476/) | roisin.gleeson | CC0 1.0 |
| `amb.clock` | [WWS Wallclockwithweightticking.ogg](https://commons.wikimedia.org/wiki/File:WWS_Wallclockwithweightticking.ogg) | Work With Sounds / Technical Museum of Slovenia (recordist Dušan Oblak) | CC BY 4.0 |
| `sfx.garden-birds` | [blackbirds at dawn.wav](https://freesound.org/people/squashy555/sounds/341675/) | squashy555 | CC0 1.0 |
| `sfx.birdsong` | [Blackbird in forest.wav](https://freesound.org/people/carlito62/sounds/176746/) | carlito62 | CC0 1.0 |
| `sfx.wind-hedges` | [Forest, close up of trees rustling in the wind.wav](https://freesound.org/people/Anya_Media/sounds/523389/) | Anya_Media | CC0 1.0 |
| `sfx.leaves` | [Rustling leaves](https://freesound.org/people/giddster/sounds/437356/) | giddster | CC0 1.0 |

CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ . CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/ .

## 3D environments and models

All built procedurally in Blender for Fable (`blender/build_*.py`): geometry, materials and baked textures. No
downloaded models, textures or HDRIs. Peek's clay models are Fable's own (`content/library/SOURCE.md`).

## Software

Unity 6000.3 (Universal Render Pipeline, TextMesh Pro, glTFast), Meta XR Core SDK and Meta XR Interaction SDK
(Meta's SDK licence), Newtonsoft Json.NET (MIT), Blender 5.2 (GPL; used as a tool, not shipped), Go and
anthropic-sdk-go (MIT) for the interpreter, which asks Claude (Anthropic) to write SceneScripts and Peek models.
