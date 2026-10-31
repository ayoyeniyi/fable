# Credits

Everything Fable shows or plays, where it comes from, and under what licence. Fable's own code and content (the
environments, sounds, schemas, scripts and composed images) were made for this project. Nothing is used without a
recorded licence; the per-folder `SOURCE.md` files hold the hashes and download details.

## Books (the text you read)

| Book | Edition | Licence |
|---|---|---|
| *Alice's Adventures in Wonderland*, Lewis Carroll (1865) | Standard Ebooks, https://standardebooks.org/ebooks/lewis-carroll/alices-adventures-in-wonderland/john-tenniel | text public domain (US); SE's edits and markup CC0 1.0 |
| *The Wonderful Wizard of Oz*, L. Frank Baum (1900) | Standard Ebooks, https://standardebooks.org/ebooks/l-frank-baum/the-wonderful-wizard-of-oz | text public domain (US); SE CC0 1.0 |
| *Gulliver's Travels*, Jonathan Swift (1726) | Standard Ebooks, https://standardebooks.org/ebooks/jonathan-swift/gullivers-travels | text public domain (US); SE CC0 1.0 |
| *The Odyssey*, Homer, translated by Samuel Butler (1900) | Project Gutenberg #1727, https://www.gutenberg.org/ebooks/1727 | text public domain (US); Gutenberg header and licence removed as its licence allows |

Details and file hashes: `content/books/<slug>/SOURCE.md`. Standard Ebooks is a volunteer project; the editions were
produced by Alex Cabal (Alice) and Michael Atkinson (Oz, Gulliver). The Odyssey's Gutenberg text credits Jim Tinsley
and David Widger.

## Dictionary (Define)

*Webster's Revised Unabridged Dictionary* (G. & C. Merriam, 1913), the Project Gutenberg transcription #29765,
public domain (US), cut to the words the four books use. `content/dictionary/SOURCE.md`.

## Book covers (the lobby shelf)

- **Alice:** Standard Ebooks cover (CC0 1.0), after *Amanita*, Ivan Shishkin, 1879 (public domain).
- **Oz:** Standard Ebooks cover (CC0 1.0), after *Heroic Landscape with Rainbow*, Joseph Anton Koch, 1824 (public domain).
- **Gulliver:** Standard Ebooks cover (CC0 1.0), after *Gulliver and the Lilliputians*, Jehan-Georges Vibert, 1870 (public domain).
- **The Odyssey:** composed for Fable from *Ulysses and Calypso*, Arnold Böcklin, 1882, Kunstmuseum Basel (public
  domain; reproduction via Wikimedia Commons, https://commons.wikimedia.org/wiki/File:Arnold_B%C3%B6cklin_008.jpg).

`content/covers/SOURCE.md`.

## Typefaces

- **EB Garamond** (the reading page), Georg Duffner and Octavio Pardo, SIL Open Font License 1.1
  (`unity/Fable/Assets/Fable/Fonts/EBGaramond-OFL.txt`).
- **League Spartan Bold**, The League of Moveable Type / The League Spartan Project Authors, SIL Open Font License 1.1
  (`content/covers/fonts/OFL.txt`). Used only to letter the Odyssey cover image, in Standard Ebooks' style; it does
  not ship in the app.
- Standard Ebooks' covers carry League Spartan and Sorts Mill Goudy (The League of Moveable Type, SIL OFL 1.1),
  rendered into the images by Standard Ebooks.

## Music

| Where | Piece | Performer / source | Licence |
|---|---|---|---|
| Lobby | Erik Satie, *Gymnopédie No. 1* (1888) | recording by Teknopazzo, Wikimedia Commons, https://commons.wikimedia.org/wiki/File:Gymnopedie_No._1..ogg (SHA-1 `1465775de774068e2d0d24b9ea852b323b4fb0d1`) | CC0 1.0 (recording); composition public domain |
| Glumdalclitch's room (Gulliver) | George Frideric Handel, *The Harmonious Blacksmith*, Air and variations from Suite No. 5 in E major, HWV 430 (1720) | Musopen (https://musopen.org/music/1183/georg-friedrich-handel/8-great-suites-hwv-426-433/), via Wikimedia Commons, https://commons.wikimedia.org/wiki/File:Handel_-_Suites_for_Harpsichord_-_No.5_in_E_major_-_The_Harmonious_Blacksmith.ogg (SHA-1 `b719b62f7f55088d624bd06f514d82ff9d41fb65`) | CC0 1.0 (recording); composition public domain |
| Calypso's cave (Odyssey) | a sparse lyre in the Dorian mode | composed and synthesised for Fable by `audio/synth_rooms.py` | CC0 1.0 (Fable's own) |

`tools/fetch_music.py` downloads the two recordings and refuses any file whose SHA-1 differs from the one above. The
Satie file is FLAC in Ogg, which Unity cannot import, so it is decoded to mono WAV; the music is otherwise unedited.

## Sound

Every ambience and sound effect is synthesised from code: `audio/synth_sfx.py` (the Alice rooms) and
`audio/synth_rooms.py` (the lobby, the Kansas storm, Ogygia's surf, rills, fire and birds, the giant room in
Brobdingnag). No samples, no recordings. CC0 1.0 (Fable's own).

## 3D environments and models

All built procedurally in Blender for Fable (`blender/build_*.py`): geometry, materials and baked textures. No
downloaded models, textures or HDRIs. Peek's clay models are Fable's own (`content/library/SOURCE.md`).

## Software

Unity 6000.3 (Universal Render Pipeline, TextMesh Pro, glTFast), Meta XR Core SDK and Meta XR Interaction SDK
(Meta's SDK licence), Newtonsoft Json.NET (MIT), Blender 5.2 (GPL; used as a tool, not shipped), Go and
anthropic-sdk-go (MIT) for the interpreter, which asks Claude (Anthropic) to write SceneScripts and Peek models.
