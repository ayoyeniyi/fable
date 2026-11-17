# Chapter step-in rooms

Stepping into a chapter takes the reader to the room of that chapter's **predominant scene**: the place where most of the chapter, or its key moment, happens. That place may be anywhere in the book, not just one of its three reading rooms. This plan covers the first 10 chapters of each of the 10 books. Rooms are built in Blender, served from the server and downloaded as the reader reaches the chapter.

The machine-readable copy is `schema/scene_rooms.json`. An existing room counts only if it really **is** that place (the same location and the same kind of space). A merely similar room does not count. Living-scene names (`water.*`, `fx.*`, `veg.*`, `cloth.*`, `sound.*`) follow `docs/LIVING_SCENES.md`, and every room follows `docs/ENVIRONMENT_BRIEF.md`.

**Which chapters count:** the first 10 entries in each `book.json` whose `kind` is `chapter`. That is the book's own numbering, so Frankenstein's c01–c04 are Letters I–IV and c05–c10 are Chapters I–VI. Gulliver's c01–c08 are Part I, Chapters I–VIII (Lilliput), and c09–c10 are Part II, Chapters I–II (Brobdingnag). The Odyssey's c01–c10 are Books I–X. Front matter (`kind: front`) is skipped.

## Summary

- Chapters: **100**
- Distinct places: **77**
- Already covered by an existing room: **21** places (32 chapters)
- New rooms needed: **56**

| Book | Places | Existing | New |
|---|---|---|---|
| alice | 8 | 3 | 5 |
| oz | 9 | 2 | 7 |
| odyssey | 10 | 2 | 8 |
| gulliver | 8 | 1 | 7 |
| pride | 6 | 2 | 4 |
| mobydick | 6 | 2 | 4 |
| worlds | 6 | 3 | 3 |
| treasure | 8 | 2 | 6 |
| eighty | 7 | 2 | 5 |
| frankenstein | 9 | 2 | 7 |

## Build order (new rooms)

Tier 1 holds the places first needed in chapters 1–3, tier 2 those in chapters 4–6, and tier 3 those in chapters 7–10. Within each tier the books are interleaved, so if building stops early every book still has its opening covered.

| # | Tier | Place id | Book | Name | Chapters |
|---|---|---|---|---|---|
| 1 | 1 | `pool-bank` | alice | The Bank of the Pool of Tears | c03 |
| 2 | 1 | `munchkin-house-landing` | oz | Where the House Landed | c02 |
| 3 | 1 | `ithaca-assembly` | odyssey | The place of assembly at Ithaca | c02 |
| 4 | 1 | `lilliput-binding-ground` | gulliver | Where Gulliver Lay Bound | c01 |
| 5 | 1 | `longbourn-drawing-room` | pride | Longbourn family drawing-room | c01, c02, c04, c05 |
| 6 | 1 | `new-bedford-spouter-corner` | mobydick | Dockside corner before the Spouter Inn, New Bedford, December night | c02 |
| 7 | 1 | `benbow-parlour` | treasure | Parlour of the Admiral Benbow inn | c01, c02, c03 |
| 8 | 1 | `saville-row-house` | eighty | Phileas Fogg's sitting room, No. 7 Saville Row | c01, c02, c04 |
| 9 | 1 | `petersburg-street` | frankenstein | A snowy street in St Petersburg | c01 |
| 10 | 1 | `munchkin-cornfield` | oz | Munchkin Cornfield | c03 |
| 11 | 1 | `pylos-shore` | odyssey | The sacrifice on the shore at Pylos | c03 |
| 12 | 1 | `meryton-assembly-room` | pride | Meryton assembly room | c03 |
| 13 | 1 | `archangel-quay` | frankenstein | The frozen harbour quay at Archangel | c02 |
| 14 | 1 | `walton-ship-deck` | frankenstein | The deck of Walton's ship among drifting ice | c03 |
| 15 | 2 | `white-rabbit-house` | alice | The White Rabbit’s Upstairs Room | c04 |
| 16 | 2 | `yellow-brick-roadside-brook` | oz | Roadside Brook | c04 |
| 17 | 2 | `menelaus-hall` | odyssey | Menelaus's palace hall at Lacedaemon | c04 |
| 18 | 2 | `mildendo-palace-court` | gulliver | Inner Court of the Palace at Mildendo | c04 |
| 19 | 2 | `lucas-lodge-drawing-room` | pride | Drawing-room at Lucas Lodge | c06 |
| 20 | 2 | `spouter-inn-bedroom` | mobydick | Upstairs bedroom at the Spouter-Inn | c04 |
| 21 | 2 | `chobham-road-common-edge` | worlds | The Road onto Horsell Common at Twilight | c06 |
| 22 | 2 | `benbow-captains-room` | treasure | The captain's room upstairs at the Admiral Benbow | c04 |
| 23 | 2 | `scotland-yard-office` | eighty | Commissioner of Police's office, Scotland Yard | c05 |
| 24 | 2 | `como-peasant-cot` | frankenstein | A peasant cottage by the Lake of Como | c05 |
| 25 | 2 | `caterpillar-mushroom` | alice | The Caterpillar’s Mushroom | c05 |
| 26 | 2 | `woodman-forest-clearing` | oz | Tin Woodman's Clearing | c05 |
| 27 | 2 | `scheria-washing-pools` | odyssey | The washing-cisterns by the river mouth on Scheria | c06 |
| 28 | 2 | `blefuscu-harbour-channel` | gulliver | The Channel off Blefuscu Harbour | c05 |
| 29 | 2 | `new-bedford-dock-street` | mobydick | New Bedford thoroughfare near the docks, Sunday morning | c06 |
| 30 | 2 | `benbow-road-bridge` | treasure | The road and little bridge below the Admiral Benbow | c05 |
| 31 | 2 | `suez-quay` | eighty | The quay at Suez | c06, c08 |
| 32 | 2 | `bellerive-oak` | frankenstein | The lightning-struck oak at Bellerive | c06 |
| 33 | 2 | `duchess-kitchen` | alice | The Duchess’s Kitchen | c06 |
| 34 | 2 | `forest-road-lion` | oz | Forest Road | c06 |
| 35 | 2 | `lilliput-temple-lodging` | gulliver | Inside Gulliver's Temple House | c06, c07 |
| 36 | 3 | `mock-turtle-rock` | alice | The Mock Turtle’s Ledge of Rock | c09, c10 |
| 37 | 3 | `kalidah-gulf` | oz | Kalidah Gulf | c07 |
| 38 | 3 | `alcinous-hall` | odyssey | King Alcinous's hall in Scheria | c07 |
| 39 | 3 | `blefuscu-shore-boat` | gulliver | Fitting Out the Boat at Blefuscu | c08 |
| 40 | 3 | `netherfield-breakfast-parlour` | pride | Netherfield breakfast parlour | c09 |
| 41 | 3 | `whalemans-chapel` | mobydick | The Whaleman's Chapel, New Bedford | c07, c08, c09 |
| 42 | 3 | `maybury-garden` | worlds | The Narrator's Garden and Summerhouse, Maybury Hill | c09 |
| 43 | 3 | `bristol-quays` | treasure | The Bristol quays | c07 |
| 44 | 3 | `suez-consulate` | eighty | British consul's office at Suez | c07 |
| 45 | 3 | `ingolstadt-lecture-room` | frankenstein | M. Waldman's lecturing room, Ingolstadt | c07 |
| 46 | 3 | `emerald-city-gate` | oz | Emerald City Gate Room | c10 |
| 47 | 3 | `phaeacian-games-ground` | odyssey | The Phaeacian place of assembly and games ground | c08 |
| 48 | 3 | `brobdingnag-farmhouse-table` | gulliver | The Farmer's Dinner Table | c09 |
| 49 | 3 | `maybury-hill-storm-road` | worlds | The Road below Maybury Hill in the Storm | c10 |
| 50 | 3 | `hispaniola-cabin` | treasure | The Hispaniola's after cabin at anchor | c09 |
| 51 | 3 | `malabar-hill-pagoda` | eighty | The pagoda on Malabar Hill, Bombay | c10 |
| 52 | 3 | `ingolstadt-sickroom` | frankenstein | Victor's sickroom in Ingolstadt in spring | c10 |
| 53 | 3 | `cyclops-cave` | odyssey | Polyphemus's cave | c09 |
| 54 | 3 | `green-eagle-inn-room` | gulliver | The Show Room at the Green Eagle | c10 |
| 55 | 3 | `hispaniola-deck` | treasure | The Hispaniola's deck at sea, by the apple barrel | c10 |
| 56 | 3 | `circes-house` | odyssey | Circe's house on Aeaea | c10 |

## Doubtful calls and changes to earlier mappings

These choices differ from the chapter lists in `schema/environments.json`, or are judgement calls:

- **Existing rooms that no longer get a chapter (from the first 10):** `benbow-cove`, because Treasure Island c01–c05 happen inside the inn, in the captain's room and on the road, not on the beach. `glumdalclitchs-room`, because Gulliver c09 is set at the farmer's dinner table. The rat fight on the bed in c09 could argue for the existing room. `longbourn-library`, because in Pride c02 the whole family is together and Mr Bennet "left the room", so it is not his library.
- **Remapped away from existing rooms:** mobydick c02 (the night street outside the inn) and c04 (the upstairs bedroom) are not the inn's entry and public room. worlds c08 is a montage with no dining room, so it maps to the sand pits at night, the chapter's own centre. eighty c08 happens on the Suez quay, not on the Mongolia. pride c09 is Netherfield's breakfast parlour by day, not the drawing-room.
- **Kept, with caveats:** reform-club for eighty c03. The text puts the whist table by the fire in the "reading-room", and the existing room's clock shows a quarter to nine, which matches c37. odyssey c05 is about half Ogygia and half raft and storm. mobydick c03 and c10 end in the bedroom. oz c09 is set on the grass by the river beside the poppies. pride c07 is set on the walk, its key moment, though more of its text is at Longbourn.
- **No single dominant place, so the most vivid moment was chosen:** alice c06 (the kitchen), alice c09 (the Mock Turtle's rock, merged with c10, although about 45% of c09 is still on the croquet ground), oz c07 (the Kalidah gulf), oz c10 (the gate room, though half the chapter is supper at a farmhouse), eighty c04, c05 and c10, worlds c01 (the observatory vigil inside an essay), frankenstein c01–c03 (where each letter is written) and c05–c07, treasure c07 (the Bristol quays).
- **Possible merges if building time runs short:** `new-bedford-spouter-corner` with `new-bedford-dock-street` (night and day streets of New Bedford), `phaeacian-games-ground` with `alcinous-hall`, `yellow-brick-roadside-brook` with `woodman-forest-clearing`, `hispaniola-cabin` with `hispaniola-deck`.
- **Pride c04** has no named room ("When Jane and Elizabeth were alone"). It is mapped to the Longbourn drawing-room instead of an invented bedroom.

## Per chapter

### alice

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `alice:c01` | Down the Rabbit-Hole | After a brief opening on the riverbank and the fall down the well, Alice wanders the long, low hall of locked doors, finds the golden key, the little door to the garden, and the 'Drink Me' bottle and 'Eat Me' cake *Note: The bank and the fall are brief; most of the chapter is in the hall.* | indoor | unstated: underground, lamp-lit (above ground it is a hot day, May) | unstated (above ground 'the hot day') | `hall-of-doors` (existing) |
| `alice:c02` | The Pool of Tears | In the same hall, nine-foot Alice weeps a pool 'about four inches deep and reaching half down the hall', shrinks with the Rabbit's fan, slips in and swims with the Mouse *Note: The pool forms inside the hall, so this is the existing room. A variant could flood the floor with shallow salt water.* | indoor | unstated: same day, lamp-lit hall | unstated ('the hall was very hot') | `hall-of-doors` (existing) |
| `alice:c03` | A Caucus-Race and a Long Tale | On the bank of the pool of tears the dripping party of birds and animals sits in a ring, runs the Caucus-race, gets comfits as prizes and hears the Mouse's tale *Note: The text gives almost no description of the bank. It is somewhere underground beside the pool, so this room needs the most invention.* | mixed | unstated: same day; Magpie mentions 'the night-air' | unstated | `pool-bank` (new #1) |
| `alice:c04` | The Rabbit Sends in a Little Bill | In the White Rabbit's house Alice drinks from a bottle and grows to fill the 'tidy little room', arm out of the window and foot up the chimney, while the Rabbit, Pat and Bill attack from outside *Note: The chapter ends in the wood with the puppy and the mushroom, but the house dominates.* | indoor | unstated: daytime | unstated | `white-rabbit-house` (new #15) |
| `alice:c05` | Advice from a Caterpillar | In the wood at a large mushroom, the blue Caterpillar smoking a hookah questions Alice; then her neck shoots up through the treetops and the Pigeon attacks her | outdoor | unstated: daytime | unstated | `caterpillar-mushroom` (new #25) |
| `alice:c06` | Pig and Pepper | The Duchess's smoky, peppery kitchen: Duchess on a stool nursing a baby, cook throwing pans, Cheshire Cat grinning on the hearth; afterwards the baby turns into a pig and the Cat talks to Alice in the wood *Note: Split between the kitchen, the outside of the house and the Cheshire Cat in the wood. Chose the kitchen because it is the most vivid moment and gives the chapter its title.* | mixed | unstated: daytime ('as this is May') | unstated | `duchess-kitchen` (new #33) |
| `alice:c07` | A Mad Tea-Party | A large tea table under a tree in front of the March Hare's house; Hatter, March Hare and sleeping Dormouse crowded at one corner; riddles, the buttered watch, the treacle-well story *Note: The short ending, back through a tree door to the hall and into the garden, is a transition.* | outdoor | 'It’s always six o’clock now' (always teatime) | unstated | `mad-tea-party` (existing) |
| `alice:c08` | The Queen’s Croquet-Ground | Gardeners paint the white rose-tree red, the card procession arrives, and the Queen's chaotic croquet game is played with flamingo mallets, hedgehog balls and soldier arches; the Cheshire Cat's head appears | outdoor | unstated: daytime ('a very fine day') | 'a very fine day' | `queens-croquet-ground` (existing) |
| `alice:c09` | The Mock Turtle’s Story | After walking with the Duchess and more croquet, Alice is taken by the Gryphon to the Mock Turtle 'sitting sad and lonely on a little ledge of rock', who tells his history of school in the sea *Note: About 45% is on the croquet ground (existing). Chose the rock because it is the title scene and shares a place with c10.* | outdoor | unstated: daytime (Gryphon 'lying fast asleep in the sun') | sunny ('asleep in the sun') | `mock-turtle-rock` (new #36) |
| `alice:c10` | The Lobster Quadrille | At the Mock Turtle's ledge of rock, the Mock Turtle and Gryphon dance the Lobster Quadrille round Alice, she recites, and he sings 'Beautiful Soup' until 'The trial’s beginning!' is called *Note: The text never says the rock is by the sea; the seashore and shingle are only in the dance description. A shingle shore is inferred.* | outdoor | unstated: afternoon, same day | unstated ('the breeze that followed them') | `mock-turtle-rock` (new #36) |

### oz

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `oz:c01` | The Cyclone | Inside the one-room Kansas farmhouse on the gray prairie as a cyclone lifts it into the sky with Dorothy and Toto aboard | indoor | unstated: daytime (Aunt Em washing dishes), then hours of darkness in the cyclone | cyclone; sky 'even grayer than usual', wind howling | `kansas-farmhouse` (existing) |
| `oz:c02` | The Council with the Munchkins | Outside the fallen farmhouse in the Munchkin country, morning; the Witch of the North and three Munchkins greet Dorothy beside the witch's silver shoes *Note: Opens briefly inside the house; the council itself is at the doorway and lawn outside.* | outdoor | morning ('bright sunshine came in at the window') | bright sunshine | `munchkin-house-landing` (new #2) |
| `oz:c03` | How Dorothy Saved the Scarecrow | Yellow brick road beside a Munchkin cornfield, day; Dorothy sits on the blue fence and lifts the Scarecrow off his pole *Note: Montage chapter (house, road, Boq's feast, cornfield); chose the cornfield as the key moment and title event.* | outdoor | unstated: daytime, after breakfast and 'several miles' of walking | unstated (previous day 'the sun shone bright') | `munchkin-cornfield` (new #10) |
| `oz:c04` | The Road Through the Forest | Roadside by a little brook on a broken stretch of yellow brick road at noon; Dorothy eats bread while the Scarecrow tells how he was made *Note: Journey chapter; the long noon rest/story is the most sustained scene. Ends at the Tin Woodman's log cottage (could alternatively merge into woodman-forest-clearing).* | outdoor | noon, then evening and night in the forest | unstated | `yellow-brick-roadside-brook` (new #16) |
| `oz:c05` | The Rescue of the Tin Woodman | Forest clearing near a spring and a log cottage, morning; Dorothy and the Scarecrow oil the rusted Tin Woodman standing by a half-chopped tree *Note: Second half is walking through forest while the Woodman tells his story.* | outdoor | morning ('the sun was shining through the trees') | sunny | `woodman-forest-clearing` (new #26) |
| `oz:c06` | The Cowardly Lion | Yellow brick road through thick woods, daytime; the Lion bounds out, strikes the Scarecrow and Woodman, and Dorothy slaps his nose | outdoor | unstated: daytime | unstated | `forest-road-lion` (new #34) |
| `oz:c07` | The Journey to the Great Oz | A deep rocky gulf across the yellow brick road in the dark forest; the Woodman fells a tree as a bridge and drops the Kalidahs into the chasm *Note: Multi-place journey (campfire, first ditch, second gulf, river); chose the Kalidah tree-bridge as the most vivid moment.* | outdoor | morning (within hours of daylight); chapter also covers a night camp and afternoon river | unstated (dew at night) | `kalidah-gulf` (new #37) |
| `oz:c08` | The Deadly Poppy Field | River crossing by raft, then the riverbank and the great meadow of scarlet poppies where Dorothy and the Lion fall asleep | outdoor | morning on the river, then daytime ('get back to the road ... before dark') | sunny ('flowers and fruit trees and sunshine') | `poppy-field` (existing) |
| `oz:c09` | The Queen of the Field Mice | Grassy riverbank beside the poppy field; the Woodman kills the Wildcat, and thousands of field mice haul the sleeping Lion out on a wooden truck *Note: Takes place on the green grass by the river just outside the poppy bed, which matches the existing poppy-field room (river bank + poppy meadow).* | outdoor | unstated: daytime (Dorothy eats fruit for dinner) | unstated (fresh breeze) | `poppy-field` (existing) |
| `oz:c10` | The Guardian of the Gate | The emerald-studded gate room of the Emerald City, afternoon; the green Guardian of the Gates locks green spectacles on each traveller *Note: Roughly half the chapter is supper at a green farmhouse; chose the gate room as the chapter's key/title moment. Not the existing throne room.* | indoor | afternoon ('it was afternoon before they came to the great wall') | sunny (gate 'glittered so in the sun') | `emerald-city-gate` (new #46) |

### odyssey

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `odyssey:c01` | Book I | Odysseus's house at Ithaca, one day: Minerva disguised as Mentes is welcomed by Telemachus while the suitors feast and Phemius sings; Penelope comes down the stair *Note: Opens on Olympus briefly; the rest is the hall (suitors first seen playing draughts in front of the house).* | mixed | day through to evening and nightfall | unstated | `ithaca-hall` (existing) |
| `odyssey:c02` | Book II | Ithaca's place of assembly at dawn: Telemachus calls the first assembly since Odysseus left, argues with the suitors, two eagles appear; later he readies the ship and sails at night *Note: About 60% is the assembly; the rest is split among the shore, the store-room and the night-time departure.* | outdoor | dawn and morning (assembly); sundown/night for the departure | unstated: fair; 'birds are always flying about in the sunshine'; west wind at night | `ithaca-assembly` (new #3) |
| `odyssey:c03` | Book III | Pylos shore at sunrise: the Pylians sacrifice black bulls to Neptune on the sands, and Nestor tells Telemachus about the homecomings *Note: The shore feast is the largest part; the night and the heifer sacrifice at Nestor's house come after it.* | outdoor | sunrise through to sunset at the shore; next morning at Nestor's house | unstated: fair ('heaven had smoothed the sea') | `pylos-shore` (new #11) |
| `odyssey:c04` | Book IV | Menelaus's palace at Lacedaemon, evening and the next day: a double wedding feast, Helen drugs the wine, and Menelaus tells of Proteus; at the end the suitors plot in Ithaca *Note: Not ithaca-hall: Menelaus's palace is a different place. The final ~20% happens at Ithaca (suitors, Penelope).* | indoor | evening arrival (after sunset, end of Book III); next morning | unstated | `menelaus-hall` (new #17) |
| `odyssey:c05` | Book V | Ogygia: Mercury brings Jove's order to Calypso at her cave; Odysseus builds a raft, sails, and is wrecked by Neptune's storm before reaching Scheria *Note: Roughly half is Ogygia (cave, wood, shore) and half is the raft voyage and storm; chose the cave as the home place of the first half and of the key exchange with Calypso.* | mixed | dawn (gods' council); days at Ogygia | fair on Ogygia; violent storm at sea later | `calypsos-cave` (existing) |
| `odyssey:c06` | Book VI | The washing-cisterns at the river mouth on Scheria: Nausicaa and her maids wash clothes, play ball, and meet the shipwrecked Odysseus *Note: The opening dream in Nausicaa's bedroom is short.* | outdoor | morning to afternoon (they leave at daybreak and wait for the sun to dry the clothes) | unstated: sunny (clothes dried by the sun) | `scheria-washing-pools` (new #27) |
| `odyssey:c07` | Book VII | King Alcinous's palace in Scheria at nightfall: Odysseus enters hidden in mist, clasps Queen Arete's knees, sits in the ashes of the hearth, and tells of Calypso *Note: The walk through town and the palace garden description come first; most of the action is in the hall.* | indoor | evening/night (chiefs making 'the last' drink-offerings to Mercury) | unstated | `alcinous-hall` (new #38) |
| `odyssey:c08` | Book VIII | The Phaeacian place of assembly by the ships: council, then athletic games where Odysseus throws the discus, Demodocus sings of Mars and Venus, and the young men dance; the evening feast follows in the palace *Note: About 60% is outdoors at the assembly/games ground. The banquets and the Trojan-horse song in the palace are the rest; could instead be merged with alcinous-hall if fewer rooms are wanted.* | mixed | dawn through to evening (supper in the palace) | unstated: fair (dust 'upon the plain') | `phaeacian-games-ground` (new #47) |
| `odyssey:c09` | Book IX | Told by Odysseus at Alcinous's court: in the Cyclops's cave on a cliff by the sea, Polyphemus eats his men, and Odysseus gets him drunk, blinds him and escapes under the rams *Note: Chose where the told action happens, not the Phaeacian frame. The Cicones and Lotus-eaters are short episodes; the cave fills about 60% of the book.* | indoor | evening and night in the cave (Polyphemus returns with his flocks); dawn escape | unstated | `cyclops-cave` (new #53) |
| `odyssey:c10` | Book X | Told by Odysseus: after Aeolus and the Laestrygonians, at Circe's stone house on Aeaea his men are turned into pigs, he resists her with Mercury's herb, and the crew stay a year *Note: Told-action choice again. Aeolus's island and the Laestrygonian harbour take up the first ~35%; Circe's house is the rest.* | mixed | unstated: day (the men approach in daylight; feasting 'till sundown') | unstated | `circes-house` (new #56) |

### gulliver

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `gulliver:c01` | Part I, Chapter I | Lilliput, the grassy ground half a mile inland from the shore, at dawn after the shipwreck: Gulliver wakes pinned down by strings and pegs, is shot with arrows, harangued from a stage and fed by tiny people climbing ladders onto him *Note: Chapter also covers the shipwreck, the overnight haul on the engine and arrival at the temple; the binding on the grass is the longest and most vivid part. The temple arrival at the end belongs to lilliput-beach, but it is only the closing paragraphs.* | outdoor | dawn into morning ('when I awaked, it was just daylight'; 'the sun began to grow hot') | clear and hot after a storm the night before ('the storm was much abated'; 'the heat of the weather') | `lilliput-binding-ground` (new #4) |
| `gulliver:c02` | Part I, Chapter II | Lilliput, the common before the north gate of the ancient temple where Gulliver is chained: he surveys the country, the emperor rides up, and officers search his pockets and take his scimitar and pistols *Note: Opening view ('enclosed fields... forty feet square', 'the town on my left hand') matches the existing room's description.* | outdoor | morning into evening ('Towards night I got with some difficulty into my house') | clear and sunny ('the sun shone clear') | `lilliput-beach` (existing) |
| `gulliver:c03` | Part I, Chapter III | Lilliput, before Gulliver's temple house while still chained: rope-dancers, horsemen drilling on his stretched handkerchief, troops marching between his legs, then he swears to the articles and the chains are unlocked *Note: The text never names where the shows happen, but he is still chained to the temple until the end of the chapter ('my chains were immediately unlocked'), so they must be within reach of the temple common.* | outdoor | unstated: daytime | unstated | `lilliput-beach` (existing) |
| `gulliver:c04` | Part I, Chapter IV | Mildendo, the Lilliputian capital: Gulliver steps over the wall, walks the two great streets, and uses two stools to reach the inmost palace court, where he lies down to look through the windows and kisses the empress's hand *Note: The second half is Reldresal's talk (Big-Endians, Blefuscu) at Gulliver's house one morning; the city/palace visit is the chapter's only vivid scene.* | outdoor | unstated: daytime | unstated | `mildendo-palace-court` (new #18) |
| `gulliver:c05` | Part I, Chapter V | The channel between Lilliput and Blefuscu, off the Blefuscu harbour: Gulliver wades out, hooks fifty men of war while arrows hit his spectacles, cuts their anchors and tows the fleet home *Note: Also includes the night fire at the empress's apartments ('a moonshine night'), which happens at the palace (mildendo-palace-court) and is shorter; the fleet seizure is the key moment.* | outdoor | unstated: daytime ('about half an hour before high water') | unstated | `blefuscu-harbour-channel` (new #28) |
| `gulliver:c06` | Part I, Chapter VI | Mostly a description of Lilliput's laws and education; its one scene is Gulliver's household in the temple, where he dines at his own table with the emperor's family set in chairs of state on it, and coaches are driven around his rimmed table *Note: Chapter is mostly essay. The dinner at his table is the only real scene; it happens in his house, which is the temple seen from the inside, not the outdoor common of lilliput-beach.* | indoor | unstated: afternoon ('I have passed many an afternoon very agreeably in these conversations') | unstated | `lilliput-temple-lodging` (new #35) |
| `gulliver:c07` | Part I, Chapter VII | Inside Gulliver's temple house at night: a lord arrives secretly in a close chair, Gulliver sets it on his table and hears the articles of impeachment and the sentence to blind him; he then flees across to Blefuscu *Note: The flight to Blefuscu and reception there are told briefly at the end.* | indoor | night ('came to my house very privately at night') | unstated | `lilliput-temple-lodging` (new #35) |
| `gulliver:c08` | Part I, Chapter VIII | Blefuscu: Gulliver finds a real ship's boat drifting off the northeast coast, drags it ashore, and a month of fitting it out at the royal port follows, with sails quilted from thirteen folds of linen, before he sails away *Note: The chapter ends with the voyage, rescue by an English ship and home to England; those are summaries. Kept separate from blefuscu-harbour-channel because that room must not show the boat and this one must not show the seized fleet scene.* | outdoor | unstated: daytime (departure 'at six in the morning') | unstated | `blefuscu-shore-boat` (new #39) |
| `gulliver:c09` | Part II, Chapter I | Brobdingnag, the farmer's house at noon: set on the 30-foot-high dining table, Gulliver eats from a trencher, drinks from a two-gallon dram cup, faces the purring cat, and is grabbed by the baby *Note: Opens with the storm at sea, the giant chasing the longboat and the barley field where a reaper picks him up; it ends with the rat fight on the mistress's bed. The dinner table is the central, longest scene. glumdalclitchs-room (farmhouse bedroom) is similar but is not the dining room, so it was not used.* | indoor | noon ('It was about twelve at noon, and a servant brought in dinner') | unstated (harvest time, barley 'rising at least forty feet') | `brobdingnag-farmhouse-table` (new #48) |
| `gulliver:c10` | Part II, Chapter II | Brobdingnag, market town: in the largest room of the inn at the sign of the Green Eagle, Gulliver performs on a table for crowds while Glumdalclitch stands by on a stool; a schoolboy throws a hazel nut at him *Note: Also covers Glumdalclitch's cradle in a drawer (arguably glumdalclitchs-room), the long journey and the show room in Lorbrulgrud. The first inn show is the most vivid moment. The Lorbrulgrud room (palisaded 60-ft table) is a different place.* | indoor | unstated: daytime (market day; 'shown to twelve sets of company') | unstated | `green-eagle-inn-room` (new #54) |

### pride

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `pride:c01` | Chapter I | Longbourn's family sitting/drawing-room, one day just after Mrs Long has called: Mrs Bennet presses Mr Bennet to visit the new tenant of Netherfield *Note: Room never named; inferred as the family room where Mrs Bennet receives callers. Not the library: nothing suggests Mr Bennet's own room.* | indoor | unstated: daytime, soon after a morning call ('Mrs. Long has just been here') | unstated | `longbourn-drawing-room` (new #5) |
| `pride:c02` | Chapter II | Longbourn family sitting-room, evening: Elizabeth trims a hat, Kitty coughs, Mr Bennet reveals he has already called on Bingley, then leaves the room *Note: Existing longbourn-library lists c02, but the whole family incl. the girls is present and Mr Bennet 'left the room' to escape them, so it is the family room, not his library. Room name inferred.* | indoor | evening ('till the evening after the visit was paid') | unstated | `longbourn-drawing-room` (new #5) |
| `pride:c03` | Chapter III | The Meryton assembly ball, evening: Bingley dances twice with Jane; Darcy slights Elizabeth as 'tolerable; but not handsome enough to tempt me' *Note: Opening and close happen at Longbourn (Bingley's ten minutes in the library; Mrs Bennet's report), but the assembly is the chapter's key moment and bulk.* | indoor | evening/night (ball; family returns late to find Mr Bennet 'still up') | unstated | `meryton-assembly-room` (new #12) |
| `pride:c04` | Chapter IV | Jane and Elizabeth alone at Longbourn after the assembly, Jane confessing her admiration of Bingley; then narration of the Bingley/Darcy friendship *Note: Location wholly inferred: 'When Jane and Elizabeth were alone' straight after the ball suggests their shared bedroom. Second half is narration with no setting; the sisters' talk is the only staged moment. The text only says Jane and Elizabeth were alone; no room is named. It is mapped to the Longbourn drawing-room rather than an invented bedroom.* | indoor | unstated: most likely late night after the ball | unstated | `longbourn-drawing-room` (new #5) |
| `pride:c05` | Chapter V | Longbourn sitting-room, the morning after the assembly: the Lucases call to talk over the ball, Darcy's pride debated *Note: Text says only 'brought the former to Longbourn'; a morning call implies the room where visitors are received (inferred).* | indoor | morning ('the morning after the assembly') | unstated | `longbourn-drawing-room` (new #5) |
| `pride:c06` | Chapter VI | Evening party at Sir William Lucas's (Lucas Lodge): Elizabeth plays and sings, Mary plays, younger girls dance a reel at one end, Elizabeth refuses to dance with Darcy *Note: First part is Elizabeth/Charlotte talk with no stated setting; the party 'at Sir William Lucas's, where a large party were assembled' is the dominant, vivid scene.* | indoor | evening (party) | unstated | `lucas-lodge-drawing-room` (new #19) |
| `pride:c07` | Chapter VII | Rain keeps Jane at Netherfield; next morning Elizabeth walks alone across muddy fields to Netherfield, 'jumping over stiles and springing over puddles' *Note: Much text is at Longbourn (breakfast, notes) and later in Jane's sickroom, but the walk is the iconic moment; existing room is exactly that place.* | mixed | morning (after breakfast; she arrives 'so early in the day') | heavy rain the evening before ('it rained hard'), 'dirty weather', muddy | `fields-to-netherfield` (existing) |
| `pride:c08` | Chapter VIII | Netherfield, evening: after dinner the party plays loo in the drawing-room; Elizabeth reads, then debates the 'accomplished woman' with Darcy and Miss Bingley *Note: The dinner-table gossip is in the dining-parlour, but the main confrontation is in the drawing-room.* | indoor | evening (dinner at half past six, then cards 'late in the evening') | unstated | `netherfield-drawing-room` (existing) |
| `pride:c09` | Chapter IX | Netherfield breakfast parlour, morning: Mrs Bennet with Kitty and Lydia visits sick Jane, embarrasses Elizabeth, and Lydia demands Bingley give a ball *Note: Existing netherfield-drawing-room lists c09, but the text explicitly sets it in 'the breakfast parlour' by day, with 'a charming prospect over that gravel walk' - a different room.* | indoor | morning ('soon after the family breakfast') | unstated | `netherfield-breakfast-parlour` (new #40) |
| `pride:c10` | Chapter X | Netherfield drawing-room, evening: Darcy writes to his sister while Miss Bingley flatters him; music at the pianoforte and Darcy's 'dancing a reel' question to Elizabeth *Note: Closing scene is next day in the Netherfield shrubbery/avenue (outdoor), but the drawing-room evening dominates.* | indoor | evening | unstated | `netherfield-drawing-room` (existing) |

### mobydick

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `mobydick:c01` | Loomings | Ishmael, restless and broke, muses on why men are drawn to water; the vivid image is the crowds of 'water-gazers' at the Battery, Manhattan's tip, on a dreamy Sabbath afternoon *Note: Essay chapter with no single setting; the Battery water-gazers are its most vivid concrete place. Existing room is that place.* | outdoor | afternoon ('dreamy Sabbath afternoon') | unstated: breezy ('cooled by breezes') | `battery-waterfront` (existing) |
| `mobydick:c02` | The Carpetbag | Saturday night in December, Ishmael walks the dark, frozen New Bedford streets waterward looking for cheap lodging and stops before the leaning, gable-ended Spouter Inn on a bleak corner *Note: Not the existing spouter-inn room: that is the interior; this chapter never goes inside (ends 'let us scrape the ice from our frosted feet'). Predominant space is the night street ending at the inn's exterior.* | outdoor | night ('a Saturday night in December') | bitter cold, frost 'ten inches thick', howling wind (Euroclydon) | `new-bedford-spouter-corner` (new #6) |
| `mobydick:c03` | The Spouter-Inn | December night in the Spouter-Inn: the besmoked painting and weapon wall of the entry, the whale-jaw bar and settle of the public room, the Grampus crew's arrival, the landlord's harpooneer jest; ends upstairs when Queequeg enters the bedroom *Note: Split chapter: most text is entry + public room (existing room); the final third (Queequeg's arrival) is in the upstairs bedroom, which is a separate new place.* | indoor | night, about nine to past twelve ('hard upon twelve o'clock') | howling wind outside ('such a howling night') | `spouter-inn` (existing) |
| `mobydick:c04` | The Counterpane | Daybreak Sunday in the small upstairs bedroom of the Spouter-Inn; Ishmael wakes under the patchwork counterpane with Queequeg's tattooed arm over him, then watches him dress *Note: A bedroom upstairs ('second floor back') is a different kind of space from the built entry/public room, so not the existing room.* | indoor | dawn ('upon waking next morning about daylight') | unstated: clear and cold (c07 says the sky was 'clear, sunny cold' that morning) | `spouter-inn-bedroom` (new #20) |
| `mobydick:c05` | Breakfast | Sunday morning: Ishmael comes down to the Spouter-Inn barroom full of whalemen, then a silent breakfast in the adjoining room where Queequeg spears beefsteaks with his harpoon *Note: Barroom is the existing public room; the breakfast room 'adjoins' it, same ground floor of the inn. Accepted as existing.* | indoor | morning | unstated | `spouter-inn` (existing) |
| `mobydick:c06` | The Street | Ishmael's first daylight stroll through New Bedford's dockside thoroughfares, full of cannibals, sailors and green bumpkins, past whale-oil mansions *Note: Mostly essay-like catalogue of the town. Kept separate from c02's night corner: different time/light and a busier thoroughfare; could be merged if one New Bedford street room must serve both.* | outdoor | morning ('my first daylight stroll') | unstated here; c07: 'clear, sunny cold' before turning to sleet | `new-bedford-dock-street` (new #29) |
| `mobydick:c07` | The Chapel | Sunday noon-ish in the Whaleman's Chapel; a scattered silent congregation of sailors and widows reads black-bordered marble cenotaphs while sleet storms outside; Ishmael finds Queequeg | indoor | unstated: late morning, 'murky light of that darkened, doleful day' | 'driving sleet and mist', storm | `whalemans-chapel` (new #41) |
| `mobydick:c08` | The Pulpit | Father Mapple enters dripping sleet, climbs the ship's side-ladder into the bow-shaped pulpit and pulls it up after him | indoor | unstated: late morning/midday Sunday | storm, sleet ('storm-pelted door', 'melting sleet') | `whalemans-chapel` (new #41) |
| `mobydick:c09` | The Sermon | Father Mapple's sermon on Jonah from the pulpit to the condensed congregation, the hymn rising 'above the howling of the storm' | indoor | unstated: midday Sunday | storm ('howling of the storm') | `whalemans-chapel` (new #41) |
| `mobydick:c10` | A Bosom Friend | Sunday evening back at the Spouter-Inn: Queequeg alone by the fire, feet on the stove hearth, counting pages of a book; he and Ishmael share the tomahawk pipe and become bosom friends; later they retire to their room *Note: Predominant space is the room with the stove/fire (public room in the existing build). The closing passage (gift of silver, idol worship, talk in bed) is in the bedroom, which could alternatively be used.* | indoor | dusk into evening ('evening shades and phantoms gathering round the casements') | storm ('the storm booming without in solemn swells') | `spouter-inn` (existing) |

### worlds

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `worlds:c01` | The Eve of the War | Ogilvy's dark observatory at Ottershaw near midnight; the narrator watches Mars through the clockwork telescope and sees a reddish flash as a gas jet leaves the planet *Note: About two thirds of the chapter is an essay about Mars and the Martians with no setting. The observatory vigil is the only scene that is described in detail, so it is the chapter's key moment. The existing room fits it.* | indoor | night, around midnight to one ("just as the chronometer struck midnight") | warm, clear starlit night ("The night was warm") | `ogilvys-observatory` (existing) |
| `worlds:c02` | The Falling Star | Horsell Common sand pit soon after dawn: Ogilvy, alone, finds the half-buried cylinder in its crater and watches the lid begin to unscrew *Note: The chapter opens with a short night scene in the narrator's study and later follows Ogilvy into Woking, but the pit at dawn is the core of the chapter. The existing room fits it, including the dawn light.* | outdoor | dawn to about six in the morning, plus a brief night opening in the study | still, clear, warming ("no breeze stirring", sun "already warm") | `horsell-sandpits` (existing) |
| `worlds:c03` | On Horsell Common | The cylinder's pit on Horsell Common, morning and hot afternoon: sightseers stand round the rim while Stent's workmen dig the cylinder out *Note: Same place as the existing room. It gets crowded and dug out later in the day, with flies, bicycles and a ginger-beer barrow.* | outdoor | morning (about 9 to 11) and afternoon until about 5:15 | "glaringly hot, not a cloud in the sky nor a breath of wind" | `horsell-sandpits` (existing) |
| `worlds:c04` | The Cylinder Opens | The pit at sunset, ringed by two or three hundred people; the lid falls off and the first Martians heave out, and the narrator flees to the young pines *Note: Same place, at sunset rather than dawn.* | outdoor | sunset ("black against the lemon yellow of the sky") | hot, clear ("the burning sky") | `horsell-sandpits` (existing) |
| `worlds:c05` | The Heat-Ray | Horsell Common round the sand pits at dusk; from a heathery knoll the narrator watches the white-flag Deputation burned by the Heat-Ray as it sweeps the common *Note: The narrator watches from a knoll in the heather some distance from the pit, so this is the same common seen at dusk with the heather and pines burning. It counts as the same place.* | outdoor | twilight into early night (about half past eight per c06) | still, clear evening; stars appearing; greenish afterglow in the west | `horsell-sandpits` (existing) |
| `worlds:c06` | The Heat-Ray in the Chobham Road | The hedged road from Horsell Bridge where it opens onto the common, at twilight; the Heat-Ray passes over a crowd of 300 sightseers, firing the roadside beeches and a corner house, and the crowd stampedes back toward Woking *Note: Part of the chapter is an essay on how the Heat-Ray works. The crowd scene on the road is the key moment. It is not the pit: it is a lane between hedges and high banks with beech trees and a house at the corner, so it is a new place.* | outdoor | twilight, about half past eight ("in the gloaming") | still summer evening, starlight | `chobham-road-common-edge` (new #21) |
| `worlds:c07` | How I Reached Home | After fleeing past the canal bridge and Oriental Terrace, the narrator sits at the cold dinner in his Maybury dining room under the pink lamp shade, reassuring his wife *Note: About half the chapter is the night walk home along the road, but the dinner table is the vivid, remembered moment ("photographically distinct"). The existing room fits. Caveat: the existing room has a low fire in the grate. The text never mentions a fire and the weather is hot August, so the fire would be better left unlit.* | mixed | night (after about nine) | unstated (warm summer night) | `maybury-dining-room` (existing) |
| `worlds:c08` | Friday Night | A montage of the Woking district on Friday night; at its centre the smouldering, body-strewn common where the Martians hammer all night in the cylinder pit, swept by a searchlight beam *Note: There is no single setting. The chapter's own framing image is the pit ("In the centre ... was this cylinder ... a patch of silent common, smouldering"), so it is mapped to the sand pits at night. The best alternative is the Woking junction platform at night, with shunting trains and a paper boy shouting "Men from Mars!". The dining room does NOT appear in this chapter, so the old c08 mapping to maybury-dining-room is wrong.* | outdoor | night, about nine o'clock to just after midnight | clear starlit night ("under the stars") | `horsell-sandpits` (existing) |
| `worlds:c09` | The Fighting Begins | The narrator's Maybury Hill house and garden on hot Saturday: strawberries over the fence in the morning, then six o'clock tea in the summerhouse when the Heat-Ray fires the Oriental College trees and knocks down his chimney *Note: There are excursions to the sappers under the railway bridge, the station and the Spotted Dog bar, but the chapter starts and peaks in the garden. That is a different space from the existing dining room, so it is a new place.* | outdoor | morning, then about six in the evening for the key moment | "hot and close", "extremely hot and dull"; blood-red sun through smoke | `maybury-garden` (new #42) |
| `worlds:c10` | In the Storm | Night road at the foot of Maybury Hill in a thunderstorm; the dog cart overturns into a pool as two tripods stride past by lightning, and the narrator crouches under furze *Note: The chapter also includes the summer drive to Leatherhead, the walk up the hill past the dead landlord, and an ending at the foot of his staircase. The tripod encounter at the overturned cart is the dominant, defining moment.* | outdoor | around and just after midnight ("midnight pealing out from Pyrford Church") | violent thunderstorm with rapid lightning, hail and torrential rain; hot and close beforehand | `maybury-hill-storm-road` (new #49) |

### treasure

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `treasure:c01` | At the Admiral Benbow | The parlour of the Admiral Benbow inn, Black Hill Cove: the old captain drinks rum by the fire, bullies the company with sea-songs, and draws his clasp-knife on Doctor Livesey one evening. *Note: Arrival happens at the inn door and the captain roams the cove by day, but the chapter's scenes and key confrontation are in the parlour.* | indoor | evening ("all evening he sat in a corner of the parlor next the fire"; the doctor came "late one afternoon") | unstated (stormy nights mentioned in general: "the wind shook the four corners of the house") | `benbow-parlour` (new #7) |
| `treasure:c02` | Black Dog Appears and Disappears | Early on a frosty January morning in the inn parlour: Jim lays the captain's breakfast table, Black Dog waits behind the door, a cutlass fight spills out to the signboard, and the captain collapses with a stroke. *Note: Opening lines are the captain walking the frosty beach (this is what the existing benbow-cove room depicts), but almost all of the chapter is inside the parlour.* | indoor | very early morning, sun still low | bitter cold, hard frost, hoarfrost on the cove; calm ("the ripple lapping softly on the stones") | `benbow-parlour` (new #7) |
| `treasure:c03` | The Black Spot | The day after the funeral, a foggy frosty afternoon: blind Pew forces Jim to lead him into the parlour and passes the black spot to the captain, who drops dead. *Note: First third is at the captain's bedside upstairs; chose the parlour for the most vivid moment (black spot, death). Could alternatively go to benbow-captains-room.* | indoor | noon (captain's room) then about three o'clock in the afternoon | bitter, foggy, frosty | `benbow-parlour` (new #7) |
| `treasure:c04` | The Sea-Chest | At candlelight, Jim and his mother return to the bolted inn, take the key from the dead captain, and open his sea-chest in his little upstairs room, counting coins until Pew's stick taps on the frozen road. *Note: Also includes the run to the hamlet and the flight to the bridge; the chest-opening is the core of the chapter.* | indoor | evening, about six o'clock ("our old clock began striking ... it was only six"), full moon rising | frosty fog, beginning to disperse at the end | `benbow-captains-room` (new #22) |
| `treasure:c05` | The Last of the Blind Man | Hidden behind a bush of broom by the little bridge, Jim watches the buccaneers ransack the inn by moonlight and Pew trampled by the revenue officers' horses on the road. *Note: Not the existing benbow-cove room: that is the shingle beach at dawn; this is the road and bridge in the dell before the inn door at night. Ends with a ride and brief return to the smashed inn.* | outdoor | night, moonlit | thin mist/fog in the dell, otherwise clear moonlight; frosty | `benbow-road-bridge` (new #30) |
| `treasure:c06` | The Captain's Papers | Night in the great library of Squire Trelawney's Hall: by a bright fire the doctor opens the oilskin packet, Bones's account book and Flint's map of the island. *Note: Brief arrival at Livesey's dark door first; the library dominates. Existing room matches.* | indoor | night, moonlit | unstated: clear ("long, leafless, moonlit avenue") | `squires-library` (existing) |
| `treasure:c07` | I Go to Bristol | Weeks of waiting at the Hall, the squire's letter, a farewell night at the Benbow, the mail coach, and at dawn Jim's delighted walk along the Bristol quays among ships of every nation. *Note: No single place dominates (Hall, Benbow, coach, Bristol). Chose the Bristol quays walk as the most vivid moment. The spyglass-tavern room shows a quay through its doors but is not this place (and the tavern only appears in c08).* | mixed | varied; Bristol arrival in the morning ("the day had already broken a long time") | unstated ("one fine day" the letter came; cold night air on the coach) | `bristol-quays` (new #43) |
| `treasure:c08` | At the Sign of the Spy-Glass | A busy morning on the Bristol docks: Jim delivers the squire's note to Long John Silver inside the Spy-glass tavern, spots Black Dog fleeing, and laughs with Silver over the unpaid score. *Note: Existing room matches. Ends with a walk along the quays and a brief scene at the squire's inn.* | indoor | morning, after breakfast | unstated: fair ("a bright enough little place") | `spyglass-tavern` (existing) |
| `treasure:c09` | Powder and Arms | Aboard the Hispaniola at anchor off Bristol, Captain Smollett confronts the squire and doctor in the after cabin about the crew and secrecy, then the powder and arms are shifted aft. *Note: About two-thirds in the cabin; the rest on deck. Picked the cabin for the predominant confrontation.* | mixed | unstated: afternoon ("All hands aboard by four this afternoon") into supper-time | unstated | `hispaniola-cabin` (new #50) |
| `treasure:c10` | The Voyage | The Hispaniola sails at dawn to the capstan shanty; on the last evening of the outward voyage Jim climbs into the apple barrel on deck and hears Silver's voice. *Note: Chapter is a summary of the voyage (galley, parrot, Arrow lost overboard); the apple-barrel moment on deck is the vivid key scene. At sea, not at anchor.* | outdoor | departure a little before dawn; key moment just after sundown | some heavy weather on passage; final evening a steady breeze abeam and a quiet sea | `hispaniola-deck` (new #55) |

### eighty

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `eighty:c01` | Chapter I | No. 7 Saville Row, London, Wed 2 Oct 1872: Fogg sits squarely in his armchair watching his complicated clock and engages Passepartout as valet | indoor | late morning (11:22-11:29 a.m.) | unstated | `saville-row-house` (new #8) |
| `eighty:c02` | Chapter II | Fogg's house in Saville Row just after 11:30 a.m.: Passepartout, alone, inspects the gas-lit house cellar to garret and finds his room with the electric clock and the routine card *Note: Strictly the vivid spot is Passepartout's second-storey room, but the chapter is a tour of the whole house; merged with c01/c04 as one Saville Row interior.* | indoor | late morning (from half-past eleven) | unstated | `saville-row-house` (new #8) |
| `eighty:c03` | Chapter III | Reform Club, Pall Mall: Fogg's day of breakfast and papers, then evening whist by the coal fire where the eighty-day wager is made and signed *Note: Text puts the whist table by the fireplace in the 'reading-room', not a named card-room; the existing room is that same club space (whist table, coal fire, papers) where the wager is made, so accepted. Existing room's clock at a quarter to nine fits c37 rather than c03 (wager ~6:10-7 p.m.). Dining room and large hall are separate spaces but only passing narration.* | indoor | day into evening (breakfast to 7 p.m. when the clock strikes) | unstated (autumn; garden trees 'gilded with an autumn colouring') | `reform-club` (existing) |
| `eighty:c04` | Chapter IV | Saville Row, 7:25-8:45 p.m.: Fogg tells Passepartout 'We are going round the world', the carpetbag is packed with banknotes; then cab to Charing Cross, beggar-woman, friends, and the night train to Dover *Note: Split between the house (announcement, packing) and Charing Cross station/train; chose the house as the key moment. Charing Cross would be a separate new place if wanted.* | mixed | evening (7:25 p.m. to 8:45 p.m.) | night dark, 'a fine, steady rain was falling' | `saville-row-house` (new #8) |
| `eighty:c05` | Chapter V | London over the following week: the wager becomes a public sensation in papers, clubs and on 'Change; it ends with the Commissioner of Police at Scotland Yard receiving Fix's telegram from Suez *Note: Montage with no dominant place; chose the most concrete vivid moment, the commissioner in his office at 9 p.m. with the dispatch. The Reform Club photograph examination is only reported.* | indoor | unstated: days of montage; final scene 'nine o'clock one evening' | unstated | `scotland-yard-office` (new #23) |
| `eighty:c06` | Chapter VI | Suez wharves, Wed 9 Oct, 10:30-11 a.m.: Fix paces among the crowd with the British consul, the Mongolia arrives, and Passepartout shows him Fogg's passport | outdoor | morning (half-past ten to eleven a.m.) | 'clear, and slightly chilly', pale sun | `suez-quay` (new #31) |
| `eighty:c07` | Chapter VII | British consulate at Suez: Fix urges the consul to refuse the visa; Fogg and Passepartout come in and the passport is signed and sealed; Fogg then breakfasts in his cabin with his itinerary *Note: Short coda in Fogg's cabin aboard Mongolia; consulate dominates.* | indoor | late morning (just after 11 a.m.) | unstated (clear per c06) | `suez-consulate` (new #44) |
| `eighty:c08` | Chapter VIII | Suez quay and streets around noon: Fix walks Passepartout to a shop, pumps him about the wager, then telegraphs London and boards the Mongolia as she steams into the Red Sea *Note: Not aboard the Mongolia: almost all on the Suez quay/streets, consulate and telegraph office; the ship only sails in the last line. Pre-mapping to mongolia-deck rejected; merged with c06.* | outdoor | midday ('it's only twelve o'clock' local; Passepartout's watch says 9:52 London time) | unstated (clear, per c06) | `suez-quay` (new #31) |
| `eighty:c09` | Chapter IX | Aboard the P&O Mongolia, Suez to Bombay, 9-20 Oct: Fogg plays whist below; Passepartout meets Fix on deck and they chat; Mocha sighted, coaling at Aden, arrival at Bombay *Note: Genuinely the Mongolia's deck; brief Aden ashore interlude. Minor mismatch: existing room has sails furled, text has sails set after Aden.* | mixed | various days; deck meeting 'the day after leaving Suez' (unstated hour) | Red Sea 'capricious, and often boisterous' with heavy rolling; after Aden favourable north-west wind, 'all sails aiding the engine' | `mongolia-deck` (existing) |
| `eighty:c10` | Chapter X | Bombay, 20 Oct, 4:30-8 p.m.: Fogg at passport office and station dinner; Passepartout watches a Parsee festival, blunders shod into the Malabar Hill pagoda and is beaten by three priests; the night train leaves for Calcutta *Note: Travel montage across Bombay; chose the most vivid and plot-critical moment, the pagoda incident. Station dinner/platform is the alternative.* | mixed | late afternoon into evening (4:30 p.m. to 8 p.m.) | unstated | `malabar-hill-pagoda` (new #51) |

### frankenstein

| Chapter | Title | Predominant scene | In/out | Time | Weather | Place |
|---|---|---|---|---|---|---|
| `frankenstein:c01` | Letter I | A snowy street in St Petersburg, December 17—: Walton, newly arrived and wrapped in furs, walks the streets feeling the cold northern breeze and dreams of the pole while sledges fly over the snow *Note: Letter is written from Petersburgh; the only physical scene described is walking 'in the streets of Petersburgh' with sledges flying 'quickly over the snow'. Rest is reflection.* | outdoor | unstated: daytime | cold, snow on the ground, a 'cold northern breeze' | `petersburg-street` (new #9) |
| `frankenstein:c02` | Letter II | Archangel in late winter: Walton, 'encompassed as I am by frost and snow', has hired a vessel and is collecting sailors among merchants and seamen, waiting for the ice to let him sail *Note: Almost entirely reflection (want of a friend, the master's story). Chose the harbour where the hired ship waits, since the letter's only concrete activity is hiring a vessel and engaging sailors in Archangel; no room interior is described.* | outdoor | unstated: daytime | frost and snow after a 'dreadfully severe' winter; early spring promised | `archangel-quay` (new #13) |
| `frankenstein:c03` | Letter III | On the deck of Walton's ship at a very high latitude in high summer, sailing north before southern gales as floating sheets of ice continually pass *Note: Very short letter written at sea. Not merged with arctic-ice: here the ship is under way in open water among drifting floes, not beset in pack ice.* | outdoor | unstated: perpetual polar summer daylight (stars mentioned figuratively) | southern gales with 'renovating warmth'; 'one or two stiff gales' | `walton-ship-deck` (new #14) |
| `frankenstein:c04` | Letter IV | The frozen sea, 31 July–1 August: Walton's ship beset by ice; after the fog clears the crew sees a gigantic figure on a dog-sledge cross the ice plains, and next morning they take aboard Victor from a sledge on a drifting ice fragment *Note: Later half is conversation in Walton's cabin and on deck, but the key moment (sledge sighting, rescue off the ice) is the floe/beset-ship scene the existing room depicts. Genuine match.* | mixed | two o'clock in the afternoon (sighting); morning (rescue) | 'a very thick fog' that clears; ice plains; later the ice breaks up | `arctic-ice` (existing) |
| `frankenstein:c05` | Chapter I | A poor peasant cottage in a fold of a vale by the Lake of Como, c. 1770s: Caroline Frankenstein and five-year-old Victor find the golden-haired orphan Elizabeth among five hungry children *Note: Childhood/family history with no dominant place. Most vivid moment chosen: the finding of Elizabeth at the 'poor cot in the foldings of a vale'. Alternative: Beaufort's chamber in Lucerne where Caroline kneels by his coffin.* | mixed | unstated: daytime (a walk/visit) | unstated | `como-peasant-cot` (new #24) |
| `frankenstein:c06` | Chapter II | The Frankenstein campagne at Bellerive on Lake Geneva: fifteen-year-old Victor stands at the door watching a violent thunderstorm from the Jura when lightning destroys the old oak twenty yards away *Note: Mostly childhood reflection. Two vivid moments: the rainy inn at Thonon (finding Agrippa) and the lightning-struck oak; chose the oak as the more vivid and visual. Reader stands at the house door, as Victor did.* | outdoor | unstated: evening/night storm | 'most violent and terrible thunderstorm' advancing from the Jura | `bellerive-oak` (new #32) |
| `frankenstein:c07` | Chapter III | The lecturing room at the University of Ingolstadt: M. Waldman gives his chemistry lecture and panegyric on modern science that 'decided my future destiny' *Note: Chapter also covers the mother's deathbed in Geneva and Krempe's study; the key turning point is Waldman's lecture. Not the garret: different space (public university lecture room).* | indoor | unstated: daytime | unstated | `ingolstadt-lecture-room` (new #45) |
| `frankenstein:c08` | Chapter IV | Victor's 'solitary chamber, or rather cell, at the top of the house' in Ingolstadt, over nearly two years: he discovers the secret of life and assembles his creation through summer and autumn *Note: Existing room fits: same workshop at top of the house. Its form under a sheet is acceptable here (the frame is being assembled).* | indoor | night ('the moon gazed on my midnight labours') | unstated (seasons pass; leaves withered by the end) | `ingolstadt-garret` (existing) |
| `frankenstein:c09` | Chapter V | The garret workshop at one in the morning on a dreary November night: the creature's dull yellow eye opens; Victor flees to his bedchamber, courtyard and rainy streets, meets Clerval and falls into a long fever *Note: Existing room is exactly the creation scene (one a.m., November, rain on panes, candle stub).* | mixed | one in the morning (creation); dawn at six; then months | rain pattering on the panes; morning 'dismal and wet', rain from 'a black and comfortless sky' | `ingolstadt-garret` (existing) |
| `frankenstein:c10` | Chapter VI | Victor's sickroom in Ingolstadt in spring: convalescent, he reads Elizabeth's long letter (dated 18 March) handed him by Clerval, with young buds shooting from the trees outside his window *Note: Most of the chapter is Elizabeth's letter read in the sickroom; chose that. Alternative vivid moment: the May pedestrian tour with Clerval ('flowers of spring bloomed in the hedges'). The sickroom is Victor's bedchamber, not the garret laboratory (text keeps them separate, and Clerval removes all apparatus), so it is a new place.* | indoor | unstated: daytime | 'a divine spring' | `ingolstadt-sickroom` (new #52) |

## Places

### alice

#### `hall-of-doors`: The Hall of Doors

- Book: alice
- Chapters: `alice:c01`, `alice:c02`
- Status: existing room `hall-of-doors`
- Living-scene hints: water: puddle; fire: lantern; cloth: curtain

#### `pool-bank`: The Bank of the Pool of Tears

- Book: alice
- Chapters: `alice:c03`
- Status: **NEW**, build priority #1 (tier 1)
- Living-scene hints: water: pond; foliage: grass, reeds; sound: wind
- Build brief:
  - Period & location: Victorian dream-underworld, the shore where the swimmers land after the pool of tears; English fairy-tale setting, about 1865.
  - Layout: a gently sloping earthen/grassy bank about 8x8 m running down to a broad still pool of salt water that fills the far half of the view; a rough circle about 4 m across on the flat part of the bank for the 'large ring' and Caucus-race course ('marked out a racecourse, in a sort of circle').
  - Key objects: the ring where they 'all sat down at once, in a large ring, with the Mouse in the middle'; a scuffed circular track in the turf; a few scattered comfits and Alice's thimble on a flat stone ('this elegant thimble'); damp patches and dripping marks where the party came out of the water.
  - Scale: the creatures are as big as Alice (she is small), so the grass tufts, pebbles and reeds should look oversized, as if seen at mouse height.
  - Materials: wet dark earth, rough tussocky grass, smooth pebbles at the waterline, still glassy water.
  - Lighting: subterranean dimness. It is underground near the hall, so use a soft warm glow with no visible sun, as if the hall's hanging lamps were still faintly in reach, and dusky edges ('the night-air').
  - Reader stands on the bank in the ring's centre (where the Mouse sat), facing the pool, with the scuffed race circle round them.
  - Mood: damp and chilly but comic; everyone is 'dripping wet, cross, and uncomfortable'.
  - Must NOT be there: the little door or garden view, the Rabbit's house, mushrooms, playing-card people, tea things; no modern objects; no ocean surf (it is a pool of tears, not the sea).

#### `white-rabbit-house`: The White Rabbit’s Upstairs Room

- Book: alice
- Chapters: `alice:c04`
- Status: **NEW**, build priority #15 (tier 2)
- Living-scene hints: foliage: shrub; cloth: curtain; sound: birds, wind-trees
- Build brief:
  - Period & location: a 'neat little house' with a 'bright brass plate with the name “W. Rabbit”' on the door, at the edge of a wood; Victorian cottage interior, about 1865.
  - Layout: one small upstairs bedroom/dressing room about 4x4 m with a low ceiling (about 2.4 m), at human scale so the reader feels oversized and cramped as Alice did; one window, one inward-opening door, one narrow fireplace.
  - Key objects: 'a tidy little room with a table in the window' holding 'a fan and two or three pairs of tiny white kid gloves'; 'a little bottle that stood near the looking-glass' (no label); a narrow fireplace and chimney ('this fireplace is narrow'); the door that 'opened inwards'.
  - Optional details from the attack: a few little pebbles on the floor ('a shower of little pebbles came rattling in at the window') with some already 'turning into little cakes'.
  - Through the window: a garden with cucumber-frames (glass cold-frames, some broken), a hedge and two ladders tied together leaning against the wall.
  - Materials: whitewashed plaster, dark oak floorboards, a chintz-draped dressing table, a gilt-framed looking-glass, a cast-iron grate with a brick hearth.
  - Lighting: daylight through the single sash window, warm and domestic; the grate is cold (they only threaten 'We must burn the house down!').
  - Reader stands in the middle of the room facing the window table, with the looking-glass and bottle beside it and the fireplace to one side.
  - Must NOT be there: the giant Alice's body, Bill the Lizard inside, the puppy, mushroom or Caterpillar; nothing from the Queen/croquet; no modern objects.

#### `caterpillar-mushroom`: The Caterpillar’s Mushroom

- Book: alice
- Chapters: `alice:c05`
- Status: **NEW**, build priority #25 (tier 2)
- Living-scene hints: foliage: grass, flowers, crown, leaves; sound: wind-trees, birds
- Build brief:
  - Period & location: 'a thick wood' near the Rabbit's house, English woodland in May (fairy-tale Victorian), seen at Alice's three-inch scale.
  - Layout: a small clearing about 8x8 m on the forest floor, with giant grass blades, flowers and a buttercup ('leant against a buttercup to rest herself') towering over the reader; one 'great thistle'.
  - Centrepiece: 'a large mushroom growing near her, about the same height as herself', 'perfectly round' cap, with the Caterpillar's spot on top and its 'long hookah' (a Victorian hubble-bubble water pipe) resting there.
  - Key objects: a bit broken off each side of the mushroom edge ('broke off a bit of the edge with each hand'); grass stalks and flowers at giant scale.
  - Overhead: 'the tops of the trees' as a distant canopy, with a hint of a pigeon's nest high above ('the highest tree in the wood').
  - Materials: mossy loam, leaf litter, pale suede-like mushroom gills, waxy buttercup petals, translucent grass blades.
  - Lighting: dappled midday light filtering through a high leaf canopy, soft green bounce light, slight haze around the hookah.
  - Reader stands at mushroom-cap height (about 1.2 m cap for drama), facing the cap edge where the Caterpillar sat, with the giant grass behind.
  - Must NOT be there: the Duchess's house, Cheshire Cat, tea table, playing cards; no giant Alice neck; no modern objects.

#### `duchess-kitchen`: The Duchess’s Kitchen

- Book: alice
- Chapters: `alice:c06`
- Status: **NEW**, build priority #33 (tier 2)
- Living-scene hints: fire: fire; sound: fire
- Build brief:
  - Period & location: inside a little house 'about four feet high' in an open place in the wood; a Victorian country kitchen (about 1865), here at full room scale for the reader.
  - Layout: one 'large kitchen' about 6x5 m; the door from outside leads straight in ('The door led right into a large kitchen'); a big open hearth on the far wall.
  - Key objects: 'a three-legged stool in the middle' (the Duchess's seat); a fire with 'a large cauldron which seemed to be full of soup'; the hearth where 'a large cat ... was sitting ... grinning from ear to ear' (an empty spot or a faint grin only); a pepper box.
  - Mess: 'fire-irons', 'saucepans, plates, and dishes' and a 'frying-pan' thrown about and lying broken on the flagstones.
  - Materials: rough stone flags, sooty plaster, a blackened iron cauldron on a crane, a copper pan rack, a deal table and dresser with crockery.
  - Lighting: firelight from the hearth through thick haze; the kitchen 'was full of smoke from one end to the other'; dim daylight from a small window and the door.
  - Atmosphere: hanging pepper haze; sneezing and howling sounds; a crash of crockery.
  - Reader stands just inside the door facing the hearth, with the stool and cauldron in front.
  - Must NOT be there: the pig, croquet things, the Queen; no modern stove or electrics; no Fish/Frog-Footmen inside (they are at the door outside).

#### `mad-tea-party`: The Mad Tea-Party

- Book: alice
- Chapters: `alice:c07`
- Status: existing room `mad-tea-party`
- Living-scene hints: foliage: crown, grass; sound: wind-trees, birds

#### `queens-croquet-ground`: The Queen’s Croquet-Ground

- Book: alice
- Chapters: `alice:c08`
- Status: existing room `queens-croquet-ground`
- Living-scene hints: foliage: shrub, flowers, grass; sound: birds, crowd

#### `mock-turtle-rock`: The Mock Turtle’s Ledge of Rock

- Book: alice
- Chapters: `alice:c09`, `alice:c10`
- Status: **NEW**, build priority #36 (tier 3)
- Living-scene hints: water: ocean; foliage: grass; sound: surf, wind, gulls
- Build brief:
  - Period & location: beyond the Queen's grounds, where the Mock Turtle sits 'sad and lonely on a little ledge of rock'; Victorian fairy-tale coast inferred from the 'school in the sea', the 'seashore' and 'the shingle' in the quadrille talk.
  - Layout: a low rocky ledge (about 2 m wide, knee to waist height) at the top of a shingle beach; playable flat area about 8x8 m of shingle and rock with open space to dance 'round and round Alice'.
  - Key objects: the ledge of rock as the Mock Turtle's seat; a flat sitting place beside it where 'they sat down'; a sunny patch of turf where the Gryphon was 'lying fast asleep in the sun'.
  - Shoreline: shingle sloping to calm sea at the far edge (no lobsters shown, as the dance is done 'without lobsters'); scattered seaweed and shells.
  - Materials: grey weathered limestone or granite ledge with lichen, rounded shingle pebbles, wet dark sand at the waterline, tufts of coarse grass at the landward edge.
  - Lighting: bright afternoon sun, warm and low enough for long soft shadows, sea glitter; a light breeze ('the breeze that followed them').
  - Reader stands on the shingle facing the ledge, with the sea beyond it and a distant hint of the garden hedges behind.
  - Must NOT be there: the courtroom, jury box or tarts (the trial is the next chapter); no card soldiers or croquet things; no piers, boats or modern objects; no actual soup tureen.

### oz

#### `kansas-farmhouse`: Kansas Farmhouse

- Book: oz
- Chapters: `oz:c01`
- Status: existing room `kansas-farmhouse`
- Living-scene hints: foliage: grass; sound: wind

#### `munchkin-house-landing`: Where the House Landed

- Book: oz
- Chapters: `oz:c02`
- Status: **NEW**, build priority #2 (tier 1)
- Living-scene hints: water: stream; foliage: grass, crown, flowers, shrub; sound: birds, river
- Build brief:
  - Period & location: fairy-tale Land of Oz, Munchkin country (East); timeless, rural, blue is the local colour.
  - Playable area ~10 x 10 m lawn in front of the gray, weathered Kansas farmhouse that has just landed; house doorway on one side.
  - Key objects: the plain gray one-room house sitting askew; 'two feet were sticking out, shod in silver shoes with pointed toes' under 'the corner of the great beam the house rested on'.
  - Surroundings: 'lovely patches of greensward', 'stately trees bearing rich and luscious fruits', 'Banks of gorgeous flowers'.
  - 'A little way off was a small brook, rushing and sparkling along between green banks' (visible at edge of area).
  - Birds 'with rare and brilliant plumage sang and fluttered in the trees and bushes'.
  - Materials: sun-blistered gray clapboard house (contrast!), lush grass, fruit trees, flowers in many colours.
  - Lighting: bright morning sunshine, saturated colours versus the drab house.
  - Reader stands on the grass a few metres from the doorway, facing the house corner with the silver-shoed feet.
  - Must NOT include: yellow brick road in the foreground, Scarecrow/Tin Woodman/Lion, Emerald City, green spectacles; no figures required (Munchkins/Witch optional at most).

#### `munchkin-cornfield`: Munchkin Cornfield

- Book: oz
- Chapters: `oz:c03`
- Status: **NEW**, build priority #10 (tier 1)
- Living-scene hints: foliage: crop, grass; sound: birds, wind
- Build brief:
  - Period & location: Land of Oz, Munchkin farmland several miles along the yellow brick road.
  - Playable area ~8 x 10 m: a strip of yellow brick road with a fence, and the edge of the cornfield beyond.
  - Road: 'the hard, yellow roadbed' of yellow bricks; 'neat fences at the sides of the road, painted a dainty blue color'.
  - Field: 'a great cornfield beyond the fence' of ripe corn taller than a child.
  - Scarecrow on 'a pole to keep the birds from the ripe corn': 'head was a small sack stuffed with straw', painted face, 'old, pointed blue hat', 'blue suit of clothes, worn and faded', 'old boots with blue tops'.
  - Distant: round blue Munchkin houses 'with a big dome for a roof', fields of grain and vegetables.
  - Materials: glazed yellow brick, blue-painted wooden rails, corn stalks, straw, faded blue cloth.
  - Lighting: bright daytime sun.
  - Reader stands on the road by the blue fence (where Dorothy sat), facing the Scarecrow on his pole a few metres into the corn.
  - Must NOT include: Tin Woodman, Lion, Emerald City, green-painted fences/houses (those come later), forest.

#### `yellow-brick-roadside-brook`: Roadside Brook

- Book: oz
- Chapters: `oz:c04`
- Status: **NEW**, build priority #16 (tier 2)
- Living-scene hints: water: stream; foliage: grass, shrub; sound: river, wind
- Build brief:
  - Period & location: Land of Oz, beyond the Munchkin farms where 'the more dismal and lonesome the country became'.
  - Playable area ~8 x 8 m roadside resting spot.
  - Road: rough yellow bricks 'very uneven', 'broken or missing altogether, leaving holes'.
  - 'they sat down by the roadside, near a little brook' — small brook running beside the road.
  - Sparse 'fewer houses and fewer fruit trees'; untended farmland, no fences ('There were no fences at all by the roadside now').
  - Props: Dorothy's 'little basket' with bread under 'a white cloth'.
  - Far horizon: dark edge of 'a great forest' ahead where branches meet over the road.
  - Lighting: noon sun, slightly muted, lonely mood.
  - Reader sits/stands on the grassy verge by the brook, facing along the road toward the distant forest.
  - Must NOT include: Tin Woodman, Lion, Kalidahs, Emerald City; no blue fences here.

#### `woodman-forest-clearing`: Tin Woodman's Clearing

- Book: oz
- Chapters: `oz:c05`
- Status: **NEW**, build priority #26 (tier 2)
- Living-scene hints: water: pond; foliage: crown, leaves, shrub; sound: birds, wind-trees
- Build brief:
  - Period & location: Land of Oz, deep forest near the yellow brick road.
  - Playable area ~10 x 10 m forest clearing.
  - Key: 'One of the big trees had been partly chopped through', and beside it a man of tin 'with an uplifted axe', motionless and rusted.
  - Nearby 'little cottage ... built of logs and branches' with 'a bed of dried leaves' and 'an oilcan on a shelf'.
  - 'a little spring of clear water' a few steps away.
  - Light: morning sun shining through the trees, 'a ray of sunshine that fell between the trees' striking the tin.
  - Materials: huge rough-barked trees, chopped wood chips, log-and-branch hut, leaf litter, rusty tin.
  - Sound/wildlife: Toto chased 'birds ... and squirrels'.
  - Reader stands at the clearing edge by the spring, facing the half-chopped tree and the tin man in the sunbeam.
  - Must NOT include: Lion, Kalidahs, poppies, Emerald City; no heart (the Woodman has none yet).

#### `forest-road-lion`: Forest Road

- Book: oz
- Chapters: `oz:c06`
- Status: **NEW**, build priority #34 (tier 2)
- Living-scene hints: foliage: crown, leaves, shrub; sound: wind-trees
- Build brief:
  - Period & location: Land of Oz, 'thick woods' along the yellow brick road.
  - Playable area ~6 x 12 m section of road with dense forest on both sides.
  - Road 'still paved with yellow brick, but these were much covered by dried branches and dead leaves'.
  - Few birds: 'birds love the open country'; 'a deep growl from some wild animal hidden among the trees'.
  - Dense dark trunks and undergrowth from which 'a great Lion bounded into the road'.
  - Materials: mossy yellow brick, leaf litter, dead branches, tall trunks, ferny undergrowth.
  - Lighting: daytime but shaded and gloomy under the canopy, scattered shafts of light.
  - Optional small detail: a tiny ant/beetle on the road (Tin Woodman's beetle).
  - Reader stands on the road facing the forest edge where the Lion emerges.
  - Must NOT include: Kalidahs, ditches, river, poppies, Emerald City.

#### `kalidah-gulf`: Kalidah Gulf

- Book: oz
- Chapters: `oz:c07`
- Status: **NEW**, build priority #37 (tier 3)
- Living-scene hints: foliage: crown, leaves, shrub; sound: wind-trees
- Build brief:
  - Period & location: Land of Oz, the dark forest where the Kalidahs live.
  - Playable area ~10 x 10 m on the near lip of a deep gulf cutting across the yellow brick road.
  - Gulf: 'so broad and deep', 'steep' sides with 'many big, jagged rocks at the bottom'; road continues on the far side.
  - 'a great tree, standing close to the ditch' / chopped and fallen 'with a crash across the ditch, with its top branches on the other side' as a bridge.
  - Fresh axe-cut stump and wood chips on the near side.
  - Forest 'very thick on this side, and it looked dark and gloomy'; 'strange noises in the depths of the forest'.
  - Materials: yellow brick, raw rock, broken earth, dark bark, leaf litter.
  - Lighting: daytime but dim under heavy canopy; cooler light down in the chasm.
  - Reader stands near the stump on the safe side, facing across the tree-bridge to the far bank.
  - Must NOT include: visible Kalidahs (optional at most), river, poppies, Emerald City; keep the chasm walled off for safety.

#### `poppy-field`: Poppy Field

- Book: oz
- Chapters: `oz:c08`, `oz:c09`
- Status: existing room `poppy-field`
- Living-scene hints: water: river; foliage: flowers, grass, reeds, crown; sound: river, birds

#### `emerald-city-gate`: Emerald City Gate Room

- Book: oz
- Chapters: `oz:c10`
- Status: **NEW**, build priority #46 (tier 3)
- Living-scene hints: none
- Build brief:
  - Period & location: Land of Oz, inside the great gate of the Emerald City.
  - Playable area ~8 x 10 m 'high arched room, the walls of which glistened with countless emeralds'.
  - Outer gate behind: 'a big gate, all studded with emeralds'; 'a bell beside the gate'.
  - Opposite: another gate/portal into the city streets.
  - Key prop: 'a large green box' 'filled with spectacles of every size and shape', all green glasses with 'two golden bands'.
  - 'a big golden key from a peg on the wall'.
  - Materials: green stone/marble, set emeralds, gold fittings, green-painted wood.
  - Lighting: afternoon; dazzling green glitter, high arched ceiling.
  - Reader stands just inside the entrance gate, facing the Guardian's box and the inner portal.
  - Must NOT include: the Throne Room, Oz himself, city streets in view, anything revealing Oz is a humbug.

### odyssey

#### `ithaca-hall`: Odysseus's hall at Ithaca

- Book: odyssey
- Chapters: `odyssey:c01`
- Status: existing room `ithaca-hall`
- Living-scene hints: fire: fire; sound: fire, crowd

#### `ithaca-assembly`: The place of assembly at Ithaca

- Book: odyssey
- Chapters: `odyssey:c02`
- Status: **NEW**, build priority #3 (tier 1)
- Living-scene hints: water: ocean; foliage: grass, shrub; sound: wind, birds, crowd
- Build brief:
  - Period & location: Bronze-Age Ithaca, the town's open-air meeting place above the harbour, on the first morning after Mentes's visit.
  - Layout: an open paved/earthen circle about 12 x 12 m ringed with stone seats for the elders, with a raised seat in the middle ('his father's seat', where 'even the oldest councillors made way for him').
  - Beyond the edge: low stone houses of the town, the harbour and grey sea below, and a mountain behind ('two eagles from the top of the mountain').
  - Key objects: a spear leaning by Odysseus's seat ('spear in hand'), two hounds lying near it ('his two hounds went with him'), a herald's staff, stone benches.
  - Materials: rough-dressed limestone seats, beaten earth, dry-stone walls, worn wood, rustic wool cloaks.
  - Lighting: early morning sun ('rosy-fingered Dawn'), low warm light and long shadows.
  - Sky: clear with two eagles circling high overhead ('they wheeled and circled about').
  - Reader stands on the edge of the circle beside Odysseus's empty seat, facing the benches, with the sea behind them.
  - Must NOT be there: Odysseus himself, a disguised beggar, a bow or axes (later books), Telemachus's ship already at sea, columns or a marble temple, coins or writing.

#### `pylos-shore`: The sacrifice on the shore at Pylos

- Book: odyssey
- Chapters: `odyssey:c03`
- Status: **NEW**, build priority #11 (tier 1)
- Living-scene hints: water: ocean; fire: fire; foliage: grass; cloth: sail; sound: surf, fire, gulls, crowd
- Build brief:
  - Period & location: Bronze-Age Pylos, the sandy shore below Nestor's citadel, at sunrise during a sacrifice to Neptune.
  - Layout: a strip of beach about 14 x 10 m between the waterline and dunes; Telemachus's ship has just landed and is anchored at one end ('furled their sails, brought their ship to anchor').
  - Key objects: spit-roasting fires ('putting pieces of meat on to the spits'), thigh bones 'burning... on the embers', 'soft sheepskins that were lying on the sands', 'a golden cup', mixing-bowls.
  - Sacrifice remains: black bull hides and horns at the edge; the nine guild groups shown as several fires spread along the shore (feasters only implied, not crowds).
  - Materials: pale sand, driftwood, bronze spits and cauldrons, a gold cup, fleeces, the black-hulled ship with a furled sail.
  - Lighting: sunrise over the sea ('the sun was rising from the fair sea'), warm low light, smoke drifting from the fires.
  - Background: the high citadel of Pylos on a hill above the shore.
  - Reader stands on the sheepskins by Nestor's fire, facing the sea and the anchored ship.
  - Must NOT be there: Menelaus or Sparta's splendour, chariots on the sand (they leave later), Odysseus, iron tools, a modern harbour.

#### `menelaus-hall`: Menelaus's palace hall at Lacedaemon

- Book: odyssey
- Chapters: `odyssey:c04`
- Status: **NEW**, build priority #17 (tier 2)
- Living-scene hints: fire: fire, torch; sound: fire, crowd
- Build brief:
  - Period & location: Bronze-Age Sparta (Lacedaemon), the great hall of Menelaus's palace, at evening during a double wedding feast.
  - Layout: a megaron about 12 x 9 m with a central hearth, four columns, and seats and tables along the walls.
  - Key objects: 'the gleam of bronze and gold—of amber, ivory, and silver'; 'a beautiful golden ewer' and 'a silver basin'; Helen's 'silver work box that ran on wheels, with a gold band round the top', and 'a distaff charged with violet coloured wool'.
  - Feast details: a bard's lyre on a peg, a mixing-bowl of wine (Helen's drugged wine), tables of meat and bread, woollen cloaks over the seats.
  - Materials: plastered and painted walls, bronze facings, ivory and amber inlay, polished wooden furniture, fleece rugs.
  - Lighting: evening; fire on the hearth and torchlight, rich gold reflections.
  - Helen's seat with a footstool beside her husband's chair, near a stair down from her 'high vaulted and perfumed room'.
  - Reader stands just inside the doorway (where Telemachus and Pisistratus enter), facing the hearth and Menelaus's seat.
  - Must NOT be there: the Ithaca suitors, Penelope, Odysseus, Proteus or seals (told only), Egyptian monuments, classical marble statues.

#### `calypsos-cave`: Calypso's cave on Ogygia

- Book: odyssey
- Chapters: `odyssey:c05`
- Status: existing room `calypsos-cave`
- Living-scene hints: water: ocean, stream; fire: fire; foliage: crown, leaves, grass; sound: fire, surf, birds, wind-trees

#### `scheria-washing-pools`: The washing-cisterns by the river mouth on Scheria

- Book: odyssey
- Chapters: `odyssey:c06`
- Status: **NEW**, build priority #27 (tier 2)
- Living-scene hints: water: river, ocean; foliage: grass, shrub, reeds, leaves; cloth: washing; sound: river, surf, birds
- Build brief:
  - Period & location: mythic Bronze-Age Scheria (land of the Phaeacians), where the river meets the sea, a morning's drive from the town.
  - Layout: about 14 x 12 m: stone washing-cisterns fed by the river ('through which there ran at all times enough pure water'), a grassy bank, and a shingle beach beyond.
  - Key objects: the mule waggon unharnessed ('turned them out to feed on the sweet juicy herbage'), clothes and linen spread to dry on the shingle ('where the waves had raised a high beach of shingle'), a ball, a flask of olive oil, picnic food.
  - Thicket: bushes and olive scrub at one side where Odysseus sleeps (no figure needed; flattened leaves).
  - Materials: rough stone basins, river pebbles, grey shingle, wicker baskets, woven wool and linen robes and girdles.
  - Lighting: bright midday/afternoon sun ('waited for the sun to finish drying the clothes').
  - Coast: the river mouth opening onto calm sea; 'spits that jutted out into the sea'.
  - Reader stands on the bank between the cisterns and the drying clothes, facing the sea.
  - Must NOT be there: Odysseus's raft (it broke up), Alcinous's palace, the Phaeacian ships, modern laundry items, iron.

#### `alcinous-hall`: King Alcinous's hall in Scheria

- Book: odyssey
- Chapters: `odyssey:c07`
- Status: **NEW**, build priority #38 (tier 3)
- Living-scene hints: fire: fire, torch; foliage: crown; sound: fire, crowd
- Build brief:
  - Period & location: mythic Bronze-Age Scheria, the great hall of Alcinous's palace, at nightfall.
  - Layout: hall about 12 x 10 m, with seats along the walls and a central hearth, entered across 'the threshold of bronze'.
  - Key objects: 'The walls on either side were of bronze from end to end, and the cornice was of blue enamel'; 'The doors were gold, and hung on pillars of silver'; seats 'with coverings of fine woven work'.
  - Light sources: 'golden figures of young men with lighted torches in their hands, raised on pedestals'.
  - Hearth: the fire and the ashes where Odysseus 'sat down on the hearth among the ashes'; Arete's and Alcinous's seats beside it.
  - Glimpse through the door: walled garden with 'pears, pomegranates, and the most delicious apples', figs and olives.
  - Materials: bronze wall plates, blue-enamel frieze, gold and silver door fittings, woven covers, a loom and spindles at the side.
  - Lighting: night, warm torch and hearth light glinting on bronze.
  - Reader stands on the hearth by the queen's seat, facing the doorway and bronze threshold.
  - Must NOT be there: Demodocus's games or discus (next book), Calypso, the Cyclops, a Phaeacian ship inside, modern lamps.

#### `phaeacian-games-ground`: The Phaeacian place of assembly and games ground

- Book: odyssey
- Chapters: `odyssey:c08`
- Status: **NEW**, build priority #47 (tier 3)
- Living-scene hints: water: ocean; foliage: grass; cloth: sail; sound: crowd, gulls, rigging, wind
- Build brief:
  - Period & location: mythic Bronze-Age Scheria, the open place of assembly 'which was near the ships', on a bright morning of games.
  - Layout: about 14 x 14 m of open level ground with a stone seating area at one side and a cleared space for the games; the ship sheds and harbour behind it.
  - Key objects: 'a seat of polished stone' for Alcinous and his guest; a stone discus lying where it landed far beyond the marks; a starting post for the foot race.
  - Dancing floor: a smoothed circle for the young dancers, with a seat for the blind bard Demodocus and his lyre.
  - Background: masts, oars and hulls of Phaeacian ships ('they pride themselves on their masts, oars, and ships').
  - Materials: polished and rough stone, packed earth with dust, timber ship sheds, ropes and furled sails.
  - Lighting: clear morning to midday sun; dust raised 'upon the plain'.
  - Reader stands beside the polished-stone seats, facing the games ground with the harbour behind it.
  - Must NOT be there: the Cyclops or any of the told adventures, Odysseus's own ship, Ithaca, bows and arrows in use (the Phaeacians 'know nothing about bows'), stadium architecture.

#### `cyclops-cave`: Polyphemus's cave

- Book: odyssey
- Chapters: `odyssey:c09`
- Status: **NEW**, build priority #53 (tier 3)
- Living-scene hints: fire: fire; sound: fire
- Build brief:
  - Period & location: the mythic land of the Cyclopes, inside the giant's cave 'on the face of a cliff near the sea', in the evening and night.
  - Layout: one large cavern about 14 x 10 m with a high ceiling; the mouth is blocked by a huge stone ('two and twenty strong four-wheeled waggons would not be enough to draw it').
  - Key objects: 'His cheese-racks were loaded with cheeses'; pens of lambs and kids 'kept in separate flocks'; milk bowls and 'wicker strainers'.
  - The 'great club... of green olive wood' lying 'near one of the sheep pens', as big as 'the mast of a twenty-oared' ship.
  - Firewood: 'a huge load of dry firewood' thrown down by the hearth, and a small fire.
  - Materials: rough limestone walls, dung-strewn earth floor, wicker, crude wooden and clay vessels, fleeces; everything giant-scaled.
  - Lighting: dim, a single fire's flicker; a thin line of daylight round the door stone.
  - Reader stands among the pens near the back of the cave, facing the fire and the blocked mouth.
  - Must NOT be there: dead men or gore (keep it implied), the blinding stake already in the eye, Circe's house, metal tools, the Phaeacian court.

#### `circes-house`: Circe's house on Aeaea

- Book: odyssey
- Chapters: `odyssey:c10`
- Status: **NEW**, build priority #56 (tier 3)
- Living-scene hints: fire: fire; foliage: crown, leaves, shrub, grass; sound: wind-trees, birds, fire
- Build brief:
  - Period & location: the mythic island of Aeaea, in front of and just inside Circe's house 'built of cut stones... in the middle of the forest'.
  - Layout: about 12 x 12 m: a forest clearing and courtyard before the open gates, with the hall's doorway and a pigsty at one side.
  - Key objects: tame 'wild mountain wolves and lions' near the gate (static or idle); Circe's loom with 'a web so fine, so soft, and of such dazzling colours'.
  - Inside the door: 'benches and seats' and a bowl of 'cheese, honey, meal, and Pramnian wine'.
  - The 'pigstye' with pigs in it at the side of the court.
  - Materials: dressed cut-stone walls, timber doors, rich woven textiles, bronze and wood vessels, forest oak.
  - Lighting: dappled daylight through the forest canopy; a fire inside the hall.
  - Reader stands in the clearing just outside the gates, facing the open doorway and the loom, with the pigsty to one side.
  - Must NOT be there: the Cyclops, the Laestrygonians, a ship (it is drawn up on the shore off-stage), the land of the dead or ghosts (later), modern fences.

### gulliver

#### `lilliput-binding-ground`: Where Gulliver Lay Bound

- Book: gulliver
- Chapters: `gulliver:c01`
- Status: **NEW**, build priority #4 (tier 1)
- Living-scene hints: foliage: grass, shrub, crown; cloth: flag; sound: crowd, wind, birds
- Build brief:
  - Period & location: imaginary Lilliput, early 18th-century fiction (voyage of 1699); open grassland about half a mile inland from the shore, 'about half a mile' from the capital.
  - Scale: the reader is Gulliver-size (normal human). Lilliputians are 'not six inches high', so everything is 1/12 scale. Playable area about 8 x 8 m of turf around a human-sized patch of flattened grass.
  - Layout: a body-shaped patch of flattened grass at the centre, ringed by tiny pegs with 'slender ligatures' and cut strings; 'about four yards from me... a stage erected about a foot and a half from the ground... with two or three ladders to mount it'.
  - Key objects: ladders laid against where his sides were; baskets of food; two empty hogsheads the size of mugs ('it did not hold half a pint'); spent arrows 'like so many needles' lying in the grass.
  - The 'engine': 'a frame of wood raised three inches from the ground, about seven feet long, and four wide, moving upon twenty-two wheels', with 'eighty poles, each of one foot high' and pulleys, can stand alongside.
  - Ground: 'the grass, which was very short and soft'; tiny hedges and a distant 1/12-scale wood at the edges; a faint glimpse of the city wall far off.
  - Materials: turf, unpainted wood (stage, ladders, engine), hemp packthread cord, small iron pegs, wicker baskets.
  - Lighting: early morning, low clear sun growing hot ('the sun began to grow hot, and the light offended my eyes'); clear sky after the night's storm.
  - Reader stands at the head end of the flattened patch, facing along it toward the stage on the right and the line of the carriage beyond.
  - Must NOT be there: the temple, chains or the turret (they come at the end of the chapter and in c02); the ship or the boat; any full-size people; crowds of 'a hundred thousand' (that is at the temple).

#### `lilliput-beach`: Temple Common before the North Gate

- Book: gulliver
- Chapters: `gulliver:c02`, `gulliver:c03`
- Status: existing room `lilliput-beach`
- Living-scene hints: water: ocean; foliage: grass, crown, crop; cloth: flag; sound: crowd, wind, surf

#### `mildendo-palace-court`: Inner Court of the Palace at Mildendo

- Book: gulliver
- Chapters: `gulliver:c04`
- Status: **NEW**, build priority #18 (tier 2)
- Living-scene hints: foliage: shrub, flowers; cloth: flag, curtain; sound: crowd, birds, wind
- Build brief:
  - Period & location: imaginary Lilliput, its capital Mildendo; the emperor's palace 'in the centre of the city where the two great streets meet'.
  - Scale: reader is Gulliver-size; buildings are 1/12 scale. Playable area about 8 x 8 m: the space 'between the first and second court, which was eight feet wide' and the inmost court.
  - Layout: outer court buildings 'at least five feet high', walls 'built of hewn stone, and four inches thick'; gates between courts 'but eighteen inches high, and seven inches wide'.
  - Key objects: Gulliver's two stools made from royal-park trees, 'each about three feet high', one standing in the gap between courts; a hooked stick.
  - Royal apartments with windows of the middle stories 'left open on purpose', showing 'the most splendid apartments that can be imagined', the empress and young princes inside.
  - Beyond the palace wall ('two feet high, and twenty feet distance from the buildings'): houses 'from three to five stories', garret windows and roofs 'crowded with spectators'.
  - Materials: hewn pale stone, roof tiles or slate, carved wooden gates, painted window frames, small gilded details.
  - Lighting: unstated daytime; use soft mid-morning sun casting short shadows in the court.
  - Reader stands on the stool zone in the inner court, facing the open windows of the royal apartments at about knee-to-waist height.
  - Must NOT be there: fire damage or a burnt wing of the empress's apartment (c05); the Blefuscu fleet; Gulliver's coat (he wore 'only in my short waistcoat'); full-size people.

#### `blefuscu-harbour-channel`: The Channel off Blefuscu Harbour

- Book: gulliver
- Chapters: `gulliver:c05`
- Status: **NEW**, build priority #28 (tier 2)
- Living-scene hints: water: ocean; cloth: sail, flag; sound: surf, gulls, rigging, crowd
- Build brief:
  - Period & location: imaginary Blefuscu, 'an island situated to the northeast of Lilliput... parted only by a channel of eight hundred yards wide'; its harbour where the fleet lay at anchor.
  - Scale: reader is Gulliver-size, standing waist-to-chest-deep in water (the channel is 'about six feet' at its deepest). Ships are 1/12 scale; the largest men of war are about 'nine feet long' (c01).
  - Layout: about 10 x 10 m of shallow sea around the reader, the anchored fleet bunched ahead, Blefuscu's shore and harbour buildings beyond; Lilliput's coast faint behind.
  - Key objects: 'about fifty men of war, and a great number of transports' at anchor; anchor cables; Gulliver's hooks of 'three of the iron bars together, bending the extremities into a hook' tied to cord 'as thick as packthread'.
  - Arrows stuck in the water and on the hulls ('the enemy discharged several thousand arrows'); empty decks (the crews 'leaped out of their ships, and swam to shore').
  - Shore: crowds of 'not... fewer than thirty thousand souls' and small harbour quays and warehouses.
  - Materials: tarred wooden hulls, linen sails furled on yards, hemp rigging, stone quays, wet sand.
  - Lighting: unstated daytime near high water; use bright late-morning light with sparkle on the water.
  - Reader stands in the channel facing the anchored fleet and the harbour, with the cable bundle within reach.
  - Must NOT be there: Gulliver's ship's boat (c08); a fire; Lilliputian ceremonies; full-size ships or people.

#### `lilliput-temple-lodging`: Inside Gulliver's Temple House

- Book: gulliver
- Chapters: `gulliver:c06`, `gulliver:c07`
- Status: **NEW**, build priority #35 (tier 2)
- Living-scene hints: fire: lantern, candle; cloth: curtain, washing; sound: crowd, wind
- Build brief:
  - Period & location: imaginary Lilliput; the interior of the 'ancient temple, esteemed to be the largest in the whole kingdom', stripped of 'all the ornaments and furniture', now Gulliver's house.
  - Scale: reader is Gulliver-size; the temple is the largest Lilliputian building, so its stone hall just fits him (inferred ceiling about 2.2 m; north gate 'about four feet high, and almost two feet wide'). Playable area about 6 x 5 m.
  - Floor 'of smooth stone'; his bed of 'six hundred beds of the common measure... sewn together... four double' with sheets, blankets and coverlets along one wall.
  - Key furniture: 'a table and chair... out of the largest trees in the royal park'; on the table 'a movable rim quite round, of five inches high, to prevent accidents'.
  - On the table: tiny 'chairs of state', a coach with two horses, 'twenty waiters', dishes and barrels drawn up 'by certain cords, as we draw the bucket up a well' (c06); for the night scene, the lord's 'close chair' set on it (c07).
  - Shirts and linen quilted 'in several folds' because 'the thickest was some degrees finer than lawn'; Gulliver's coat with deep pockets on the chair.
  - Materials: grey dressed stone walls with empty niches where ornaments were removed, rough-hewn timber furniture, quilted linen.
  - Lighting: one room, two moods — late-afternoon sun through the north gate and small windows (c06), or night lit by a few tiny lanterns (c07, not described in the text); default to dusk.
  - Reader sits/stands at the chair, facing the rimmed table, with the closed north gate to one side.
  - Must NOT be there: the chains (removed in c03); a burnt or ruined state; Blefuscu items or the boat; full-size people.

#### `blefuscu-shore-boat`: Fitting Out the Boat at Blefuscu

- Book: gulliver
- Chapters: `gulliver:c08`
- Status: **NEW**, build priority #39 (tier 3)
- Living-scene hints: water: ocean; foliage: grass; cloth: sail, flag; sound: surf, gulls, crowd, wind
- Build brief:
  - Period & location: imaginary Blefuscu, the royal port shore where Gulliver's found boat is fitted out, autumn 1701 before he sails on 'the twenty-fourth day of September 1701, at six in the morning'.
  - Scale: reader is Gulliver-size; the boat is a real full-size ship's boat, while Blefuscudians, ships and buildings are 1/12 scale. Playable area about 10 x 8 m of beach around the boat.
  - Key object: a full-size boat on the sand ('a real boat, which I supposed might by some tempest have been driven from a ship'), 'turned... on its bottom' and 'but little damaged'.
  - Fit-out: 'two sails... by quilting thirteen folds of their strongest linen together'; ropes made 'by twisting ten, twenty, or thirty of the thickest and strongest of theirs'.
  - 'A great stone that I happened to find... served me for an anchor'; 'the tallow of three hundred cows' in tiny barrels; masts and oars from 'the largest timber-trees', with paddles.
  - Around it: 1/12-scale ship-carpenters at work, a few of the 'twenty of the tallest vessels' moored offshore, 'two thousand men, with ropes and engines'.
  - Materials: weathered full-size oak planking, coarse quilted linen, twisted cordage, wet sand, tiny wooden scaffolds.
  - Lighting: unstated daytime; use clear early morning, as on the day of departure.
  - Reader stands on the beach beside the boat's bow, facing out to sea with the harbour town on one side.
  - Must NOT be there: the anchored Blefuscu war fleet being towed (c05); livestock already loaded or the English ship (later in the chapter); full-size people.

#### `brobdingnag-farmhouse-table`: The Farmer's Dinner Table

- Book: gulliver
- Chapters: `gulliver:c09`
- Status: **NEW**, build priority #48 (tier 3)
- Living-scene hints: fire: fire; cloth: curtain; sound: fire, crowd, clock
- Build brief:
  - Period & location: imaginary Brobdingnag, June 1703; the farmer's house, the room where the family dines at noon.
  - Scale: the reader is Gulliver-size among giants about twelve times larger; the table is 'thirty feet high from the floor'. Playable area about 10 x 8 m of the tabletop.
  - Key objects: 'one substantial dish of meat... in a dish of about four-and-twenty feet diameter'; a trencher of crumbled bread and minced meat; a 'small dram cup, which held about two gallons'.
  - Giant family at the edges, seen in part: 'the farmer and his wife, three children, and an old grandmother'.
  - The cat in the mistress's lap: 'three times larger than an ox', its purring 'like that of a dozen stocking-weavers at work'.
  - Edge danger: a sheer drop at the table edge (the reader 'kept as far as I could from the edge, for fear of falling').
  - Materials: scrubbed deal or oak tabletop with wood grain the size of floorboards, pewter/earthenware vessels, coarse bread, rough homespun clothes.
  - Lighting: midday daylight from a tall farmhouse window, warm and even.
  - Reader stands near the trencher at one end of the table, facing the huge dish and the mistress with the cat.
  - Must NOT be there: Glumdalclitch's box, cradle-drawer or the palisaded show table (c10); the Green Eagle crowd; any Lilliput items.

#### `green-eagle-inn-room`: The Show Room at the Green Eagle

- Book: gulliver
- Chapters: `gulliver:c10`
- Status: **NEW**, build priority #54 (tier 3)
- Living-scene hints: fire: fire, candle; cloth: curtain; sound: crowd, fire
- Build brief:
  - Period & location: imaginary Brobdingnag, summer 1703; a market town, 'the largest room of the inn' 'at the sign of the Green Eagle'.
  - Scale: reader is Gulliver-size among giants about twelve times larger; the room 'might be near three hundred feet square'. Playable area about 8 x 8 m of the tabletop.
  - Key layout: Gulliver 'placed upon a table'; Glumdalclitch, 'not above forty feet high', standing 'on a low stool close to the table'.
  - Around the table: 'benches were set round the table at such a distance as to put me out of everybody's reach', with the giant audience of about 'thirty people at a time'.
  - Props on the table: 'a thimble filled with liquor, which Glumdalclitch had given me for a cup'; 'a part of a straw, which I exercised as a pike'.
  - A 'hazel nut... almost as large as a small pumpkin' lying where it fell.
  - The carrying box nearby: 'close on every side, with a little door... and a few gimlet holes to let in air', lined with the quilt of her baby's bed.
  - Materials: timber-framed inn room, dark beams, worn plank table, rough benches, homespun and leather clothing.
  - Lighting: unstated daytime; daylight from tall leaded windows, slightly smoky interior.
  - Reader stands in the middle of the tabletop facing Glumdalclitch on her stool, with the benches of onlookers beyond.
  - Must NOT be there: the Lorbrulgrud palisade around the table or royal court items (later); the farmer's cat; any Lilliput items.

### pride

#### `longbourn-drawing-room`: Longbourn family drawing-room

- Book: pride
- Chapters: `pride:c01`, `pride:c02`, `pride:c04`, `pride:c05`
- Status: **NEW**, build priority #5 (tier 1)
- Living-scene hints: fire: fire, candle; foliage: leaves, shrub; cloth: curtain; sound: fire, clock, birds
- Build brief:
  - Period & location: c.1811-13 English Regency, Longbourn, a modest gentleman's house in a Hertfordshire village 'only one mile from Meryton'; the Bennets' everyday family room where Mrs Bennet receives callers.
  - Layout: one room about 6 x 5 m, ceiling ~3 m; playable area ~4 x 4 m in the centre; one door (Mr Bennet 'left the room... when the door was shut'), two sash windows on one long wall, fireplace opposite.
  - Key objects: a work table with a bonnet/hat being trimmed, ribbons and scissors ('his second daughter employed in trimming a hat'); a sofa and several upright chairs for a family of seven plus callers; a few books on a side table for Mary ('read great books, and make extracts').
  - Furnishing: painted or papered walls in soft green/cream, plain plaster cornice, oak or painted-pine floor with a worn Turkey rug, mahogany furniture of slightly old-fashioned country taste (comfortable, not grand).
  - Fireplace: simple painted wood or stone chimney-piece with a small coal fire, brass fender, a mantel clock.
  - Lighting: daylight through the sash windows (c01, c05 morning call); optionally a pair of candles on the work table for the c02 evening - pick daylight as default.
  - Window view: a gravel sweep, garden and lane, autumn trees (the family watches visitors 'from an upper window' elsewhere; here ground floor).
  - Reader stands near the work table, facing the fireplace with the sofa to one side, as if among the sisters.
  - Must NOT be: Mr Bennet's library (no wall of books, no writing desk/globe); no officers, red coats or militia items; no letters from Mr Collins, no wedding items; nothing Victorian (no gas lamps, no upright piano).

#### `meryton-assembly-room`: Meryton assembly room

- Book: pride
- Chapters: `pride:c03`
- Status: **NEW**, build priority #12 (tier 1)
- Living-scene hints: fire: candle; cloth: curtain; sound: crowd
- Build brief:
  - Period & location: c.1811 Regency, the public assembly room of Meryton, a small Hertfordshire market town; a country ball 'such an assembly as this'.
  - Layout: a long rectangular room ~14 x 8 m (only the end ~6 x 6 m needs to be playable); dancing floor down the middle, benches and chairs along the walls where ladies sit out ('obliged, by the scarcity of gentlemen, to sit down for two dances').
  - Key objects: wall benches/chairs; a small raised musicians' platform or gallery with fiddlers; a door through which 'the party entered the assembly room'; a card/refreshment table at one end.
  - Materials: plain plastered walls painted pale, simple pilasters, wooden board floor chalked for dancing, sash windows with plain curtains.
  - Lighting: night; candle chandeliers (2-3 brass/glass) and wall sconces giving warm, uneven light; windows dark.
  - Atmosphere: crowded country ball, couples in a longways set 'going down the dance'; country-town not fashionable ('little beauty and no fashion').
  - Reader stands at the wall near the seated ladies, facing the dance floor - the spot where Elizabeth overhears Darcy.
  - Must NOT be: London grandeur (no gilded ballroom); no militia red coats yet (regiment arrives later); no waltz-era decor; no Netherfield ball details.

#### `lucas-lodge-drawing-room`: Drawing-room at Lucas Lodge

- Book: pride
- Chapters: `pride:c06`
- Status: **NEW**, build priority #19 (tier 2)
- Living-scene hints: fire: fire, candle; cloth: curtain; sound: crowd, fire
- Build brief:
  - Period & location: c.1811 Regency, Lucas Lodge, Sir William Lucas's house 'about a mile from Meryton'; a sociable evening party, 'a large party were assembled'.
  - Layout: a good-sized drawing-room ~9 x 6 m; playable area ~5 x 5 m centred near the instrument; cleared floor at 'one end of the room' where the young people dance.
  - Key objects: a square pianoforte with music books ('I am going to open the instrument'); chairs grouped for conversation; card tables pushed aside; a bench before the instrument.
  - Character: a newly-knighted ex-tradesman's house - slightly showy, eager-to-please gentility; perhaps a framed print celebrating St. James's or the King's address.
  - Materials: papered walls, painted cornices, a patterned carpet rolled back at the dancing end, mahogany and satinwood furniture.
  - Lighting: evening; candles in sconces and on the pianoforte, a coal fire in a marble or painted chimney-piece.
  - Reader stands near the pianoforte facing the room, with the dancing end to one side - where Sir William tries to present Elizabeth to Darcy.
  - Must NOT be: Netherfield's elegance; no Mr Collins or Charlotte's engagement items (later); no harp; nothing Victorian.

#### `fields-to-netherfield`: Footpath across the fields to Netherfield

- Book: pride
- Chapters: `pride:c07`
- Status: existing room `fields-to-netherfield`
- Living-scene hints: water: puddle; foliage: grass, leaves, shrub; sound: wind-trees, birds

#### `netherfield-drawing-room`: Netherfield drawing-room

- Book: pride
- Chapters: `pride:c08`, `pride:c10`
- Status: existing room `netherfield-drawing-room`
- Living-scene hints: fire: fire, candle; cloth: curtain; sound: fire, clock

#### `netherfield-breakfast-parlour`: Netherfield breakfast parlour

- Book: pride
- Chapters: `pride:c09`
- Status: **NEW**, build priority #40 (tier 3)
- Living-scene hints: fire: fire; foliage: grass, shrub, leaves; cloth: curtain; sound: fire, birds, clock
- Build brief:
  - Period & location: c.1811 Regency, Netherfield Park, Hertfordshire - a fashionable country house let to Bingley; the morning room the family uses ('the breakfast parlour').
  - Layout: bright room ~7 x 5 m, ceiling ~3.5 m; playable area ~4 x 4 m; tall sash windows on the long wall.
  - Key objects: windows giving 'a charming prospect over that gravel walk' (Mrs Bennet: 'You have a sweet room here, Mr. Bingley'); a round or oval breakfast table, just cleared; chairs and a sofa where the visitors sit; a sideboard.
  - Materials: elegant light decor - pale painted walls, white plaster cornice, polished oak floor with a carpet, mahogany furniture, white marble chimney-piece.
  - Lighting: morning daylight from the windows, soft and clear; a small fire in the grate.
  - View outside: a raked gravel walk, lawn and shrubbery, autumn/early-winter trees of the park.
  - Reader stands by the window facing the room, where the Bennet visitors confront Darcy and Bingley.
  - Must NOT be: the drawing-room's loo table or evening candles; no ball preparations/decorations (the ball is only promised here); nothing anachronistic.

### mobydick

#### `battery-waterfront`: The Battery, Manhattan

- Book: mobydick
- Chapters: `mobydick:c01`
- Status: existing room `battery-waterfront`
- Living-scene hints: water: ocean; foliage: leaves, grass; cloth: flag, sail; sound: surf, gulls, wind, rigging

#### `new-bedford-spouter-corner`: Dockside corner before the Spouter Inn, New Bedford, December night

- Book: mobydick
- Chapters: `mobydick:c02`
- Status: **NEW**, build priority #6 (tier 1)
- Living-scene hints: water: ocean, puddle; fire: candle, lantern; sound: wind, surf, rigging
- Build brief:
  - Period & location: New Bedford, Massachusetts, c.1840s, a waterfront street 'not far from the docks', Saturday night in December.
  - Layout: ~14 x 10 m playable street corner; the Spouter Inn occupies the 'sharp bleak corner', a narrow street runs back uphill ('blocks of blackness, not houses'), glimpse of dock spiles/masts at the far end.
  - The inn exterior: 'a gable-ended old house, one side palsied as it were, and leaning over sadly'; 'dilapidated little wooden house' as if 'carted here from the ruins of some burnt district'.
  - Swinging sign over the door with 'a white painting upon it, faintly representing a tall straight jet of misty spray' and the words 'The Spouter Inn:—Peter Coffin.'; it creaks ('a forlorn creaking in the air').
  - Porch with an 'ash-box' just inside the open door; 'a dim sort of light' from the inn windows; frost on window glass.
  - Street surface: 'the congealed frost lay ten inches thick in a hard, asphaltic pavement' with 'flinty projections'; a curbstone before the door.
  - Other houses dark wooden clapboard, 'here and there a candle, like a candle moving about in a tomb'; optionally far up the street the warm 'bright red windows' of the Sword-Fish Inn.
  - Materials: weathered grey shingle/clapboard, iron sign bracket, packed ice/snow, granite curbs, plank sidewalks.
  - Lighting: deep cold night, starlit sky (Orion visible), dim candle/lamp glow from the Spouter's windows as key light; no gas street lamps in this quarter.
  - Reader stands in the middle of the street a few metres from the inn, carpetbag-eye view, facing the leaning inn and its creaking sign.
  - Must NOT include: the inn's interior, Queequeg or any figures, the Pequod or named ships, whales; no modern lighting, no paved asphalt road, no summer foliage.

#### `spouter-inn`: The Spouter-Inn (entry and public room)

- Book: mobydick
- Chapters: `mobydick:c03`, `mobydick:c05`, `mobydick:c10`
- Status: existing room `spouter-inn`
- Living-scene hints: fire: fire, candle, lantern; sound: wind, fire, clock

#### `spouter-inn-bedroom`: Upstairs bedroom at the Spouter-Inn

- Book: mobydick
- Chapters: `mobydick:c04`
- Status: **NEW**, build priority #20 (tier 2)
- Living-scene hints: fire: candle; sound: wind
- Build brief:
  - Period & location: Spouter-Inn, New Bedford, c.1840s, 'second floor back' room, Sunday dawn in December.
  - Layout: small room ~4 x 4.5 m, low ceiling, whole room playable; 'a small room, cold as a clam'.
  - Bed: 'a prodigious bed, almost big enough indeed for any four harpooneers to sleep abreast', with 'The counterpane was of patchwork, full of odd little parti-coloured squares and triangles'.
  - 'a crazy old sea chest that did double duty as a washstand and centre table' with a candle; 'a rude shelf'.
  - Fireplace closed by 'a papered fireboard representing a man striking a whale'; 'a parcel of outlandish bone fish hooks on the shelf over the fireplace'.
  - Queequeg's gear: 'a tall harpoon standing at the head of the bed', 'a hammock lashed up, and thrown upon the floor in one corner', 'a large seaman's bag', a chair with his heavy grego, his tall beaver hat and boots.
  - Window: 'there were no curtains to the window', 'the street being very narrow, the house opposite commanded a plain view into the room'.
  - Materials: bare wide pine floorboards, plaster walls, worn wood, faded patchwork quilt, iron hearth.
  - Lighting: cold pale dawn light through the uncurtained window; candle on the sea chest (unlit or guttered).
  - Reader stands beside the bed at the foot, facing the bed with the window to one side and the fireboard opposite.
  - Must NOT include: people (Queequeg's body), the embalmed head on display is optional/subtle at most; nothing of the Pequod or Ahab; no curtains; no modern fixtures.

#### `new-bedford-dock-street`: New Bedford thoroughfare near the docks, Sunday morning

- Book: mobydick
- Chapters: `mobydick:c06`
- Status: **NEW**, build priority #29 (tier 2)
- Living-scene hints: water: ocean; foliage: crown; cloth: flag, sail, washing; sound: gulls, crowd, rigging, wind
- Build brief:
  - Period & location: New Bedford, c.1840s, 'thoroughfares nigh the docks', Sunday morning in December.
  - Layout: ~16 x 10 m street segment sloping down toward the wharves; dock spiles and ship masts visible at the low end, finer houses uphill.
  - Street life is described ('actual cannibals stand chatting at street corners') but render as empty or with props only: sea chests, casks, hand-carts.
  - Uphill: 'yonder lofty mansion' fenced with 'iron emblematical harpoons'; 'brave houses and flowery gardens' (gardens dormant in December).
  - Trees: maples and horse-chestnuts lining the avenue — leafless now (text's 'green and gold' and August blossoms are summer, not this morning).
  - Shops/outfitters' fronts for whalemen's sea-outfits (the bumpkins ordering 'bell-buttons to his waistcoats'); clapboard and brick buildings.
  - Ground: packed snow and ice from the previous night ('the congealed frost lay ten inches thick'), cobbles near the docks.
  - Materials: brick, white clapboard, granite curbs, iron fencing, tarred wharf timber.
  - Lighting: low, clear winter morning sun ('clear, sunny cold' per c07), long shadows.
  - Reader stands mid-street partway down, facing downhill toward the docks and masts.
  - Must NOT include: sleet (arrives later, c07), the Pequod or Nantucket, summer foliage/flowers, gas or electric street lights, modern signage.

#### `whalemans-chapel`: The Whaleman's Chapel, New Bedford

- Book: mobydick
- Chapters: `mobydick:c07`, `mobydick:c08`, `mobydick:c09`
- Status: **NEW**, build priority #41 (tier 3)
- Living-scene hints: sound: wind, rain
- Build brief:
  - Period & location: Whaleman's Chapel, New Bedford, c.1840s, Sunday service in a December storm.
  - Layout: small chapel ('the already small area of the chapel') ~10 x 14 m; rows of benches either side of a central aisle ('Starboard gangway... larboard gangway'), door at the back, pulpit at the front.
  - Pulpit: 'a very lofty one' with no stairs but 'a perpendicular side ladder, like those used in mounting a ship from a boat at sea', with 'a handsome pair of red worsted man-ropes'; ladder sides 'of cloth-covered rope, only the rounds were of wood', 'stained with a mahogany colour'.
  - Pulpit front: 'Its panelled front was in the likeness of a ship's bluff bows, and the Holy Bible rested on a projecting piece of scroll work, fashioned after a ship's fiddle-headed beak'.
  - Cenotaphs: 'several marble tablets, with black borders, masoned into the wall on either side the pulpit' (e.g. John Talbot, the Eliza's boat crew, Captain Ezekiel Hardy).
  - Behind the pulpit: 'a large painting representing a gallant ship beating against a terrible storm off a lee coast of black rocks and snowy breakers', with an angel's face in 'a little isle of sunlight'.
  - A coat-hanging space 'in an adjacent corner' by the door (wet tarpaulin hat, pilot-cloth jacket); 'storm-pelted door'.
  - Materials: whitewashed plaster, plain painted pine benches and wainscot, white marble with black borders, worn floorboards.
  - Lighting: 'the murky light of that darkened, doleful day' — dim grey daylight from windows streaked with sleet; no bright sun.
  - Reader sits/stands 'near the door' at the back bench, facing up the aisle toward the pulpit and tablets.
  - Must NOT include: Father Mapple or congregation figures (optional empty benches), any whale or Pequod, stained-glass splendour or organ, modern lighting.

### worlds

#### `ogilvys-observatory`: Ogilvy's Observatory, Ottershaw

- Book: worlds
- Chapters: `worlds:c01`
- Status: existing room `ogilvys-observatory`
- Living-scene hints: fire: lantern; sound: clock

#### `horsell-sandpits`: The Sand Pits, Horsell Common

- Book: worlds
- Chapters: `worlds:c02`, `worlds:c03`, `worlds:c04`, `worlds:c05`, `worlds:c08`
- Status: existing room `horsell-sandpits`
- Living-scene hints: fire: fire; foliage: shrub, crown, grass; sound: wind-trees

#### `chobham-road-common-edge`: The Road onto Horsell Common at Twilight

- Book: worlds
- Chapters: `worlds:c06`
- Status: **NEW**, build priority #21 (tier 2)
- Living-scene hints: fire: fire; foliage: crown, leaves, shrub, grass; sound: fire, wind-trees, crowd
- Build brief:
  - Period & location: August, late 1890s Surrey. The road out of Woking over Horsell Bridge, at the point where it "runs out at last upon the common" between hedges and high banks. Friday, about 8:30 pm.
  - Layout: a playable area of about 12 x 16 m. A sandy, rutted lane about 5 m wide runs between hedge-topped banks and opens at one end onto open heath. A "hummock of heathery sand" stands between the road and the distant pit.
  - Key objects: "the beech trees that line the road"; "the house nearest the corner", a brick villa with a gable, sash windows and wooden window frames; hedges and high banks ("Where the road grows narrow and black between the high banks").
  - Distant view: across the darkening heath, the sand pits with the Martians' "spinning mirror" on a thin mast above them, seen only as a silhouette with no detail.
  - Crowd traces (no people needed): a few scattered hats, a dropped parasol or straw boater, hoof prints. The crowd was "shop people" out for the evening ("young people brushed up after the labours of the day").
  - Materials: sandy gravel road, red brick and slate for the house, smooth grey beech bark, hawthorn hedge, heather and furze on the banks.
  - Lighting: twilight after sunset, a deep blue sky with the first stars and a greenish afterglow low in the west. Option: the moment the beam passes, with the beech crowns alight and "Sparks and burning twigs" drifting down, and the corner gable cracked with its windows smashed.
  - Reader stands in the middle of the lane near the corner house, facing up the lane toward the open common and the pit, with the beeches overhead.
  - Must NOT include: tripods or fighting-machines (they first appear in c10); a visible Martian or cylinder interior; soldiers or Maxims (they arrive later that night); electric street lighting on the common; cars or any modern road markings.

#### `maybury-dining-room`: The Narrator's Dining Room, Maybury

- Book: worlds
- Chapters: `worlds:c07`
- Status: existing room `maybury-dining-room`
- Living-scene hints: fire: lantern; cloth: curtain; sound: clock

#### `maybury-garden`: The Narrator's Garden and Summerhouse, Maybury Hill

- Book: worlds
- Chapters: `worlds:c09`
- Status: **NEW**, build priority #42 (tier 3)
- Living-scene hints: fire: fire; foliage: grass, flowers, shrub, crown, crop; sound: birds, fire, wind-trees
- Build brief:
  - Period & location: late-1890s suburban villa garden on Maybury Hill, Woking. Saturday in hot summer, about six in the evening.
  - Layout: a playable area of about 14 x 14 m. A lawn with a small timber summerhouse at one side, the back of the house (with the study window) on another, a flower bed under that window, a side gate, and a fence to the neighbour's garden.
  - Key objects: tea laid in the summerhouse ("as I sat at tea with my wife in the summerhouse"); the lawn ("starting out upon the lawn"); the neighbour's fence with strawberry beds beyond ("extended a handful of strawberries"); "the flower bed by my study window".
  - Damage moment: "One of our chimneys cracked ... a piece of it came clattering down the tiles and made a heap of broken red fragments upon the flower bed".
  - View beyond the garden: "the trees about the Oriental College burst into smoky red flame", with "the tower of the little church beside it" collapsing and "The pinnacle of the mosque" gone. Show it as a distant backdrop silhouette, not a playable area.
  - Below the house: "The beech trees below the house were burning", and "the palings up the road glowed red".
  - Materials: a red brick villa with a tiled roof and brick chimney stacks, a white-painted timber summerhouse with a wicker table and chairs, a china tea set, a mown lawn, wooden palings.
  - Lighting: hot, hazy evening; "The sun, shining through the smoke ... seemed blood red, and threw an unfamiliar lurid light upon everything"; drifting smoke.
  - Reader stands on the lawn just outside the summerhouse, facing over the fence toward the burning Oriental College treetops.
  - Must NOT include: tripods or fighting-machines (not seen until c10); red weed (much later); the dog cart (it is fetched later from the Spotted Dog); any modern garden furniture or electric lighting.

#### `maybury-hill-storm-road`: The Road below Maybury Hill in the Storm

- Book: worlds
- Chapters: `worlds:c10`
- Status: **NEW**, build priority #49 (tier 3)
- Living-scene hints: water: puddle; foliage: shrub, crown, grass; sound: rain, wind-trees, wind
- Build brief:
  - Period & location: late-1890s Surrey countryside on the road from Pyrford toward the foot of Maybury Hill. Saturday, just after midnight, in a thunderstorm.
  - Layout: a playable area of about 14 x 14 m. A muddy country road on "A moderate incline", with a roadside bank, a clump of furze, a shallow pool at the verge, hedge tops, and the edge of a young pine wood. A field lies beyond the hedge.
  - Key objects: the wrecked dog cart ("the black bulk of the overturned dog cart and the silhouette of the wheel still spinning slowly", with smashed shafts); the dead horse lying in the road; "a shallow pool of water"; "a clump of furze".
  - Nearby: "a little one-roomed squatter's hut of wood, surrounded by a patch of potato garden", with a ditch running toward the pine woods.
  - Distant silhouettes revealed by lightning: a tripod "higher than many houses ... a walking engine of glittering metal" with "a brazen hood", "articulate ropes of steel" and "a huge mass of white metal like a gigantic fisherman's basket". Keep it at the edge of the area or beyond (a large static silhouette is fine; it must not cover the play space).
  - Skyline: "the silhouette of Maybury Hill, with its treetops and roofs black and sharp against the red", and "the red masses of the Orphanage near the crest"; a red glow and smoke over the common.
  - Materials: wet sandy mud, puddle water, furze, young Scots pines (some snapped and leaning), timber hut boards, the cart's wood and iron wheel, and wet horse hide.
  - Lighting: near-total darkness punctuated by frequent violet-white lightning flashes, a red glare on the horizon, a faint green afterglow where the third cylinder fell "into the field to my left"; hail and rain.
  - Reader stands at the furze clump beside the pool, facing the overturned cart, with the hill and the tripod silhouette beyond.
  - Must NOT include: black smoke, red weed, or handling-machines (later chapters); daylight; the landlord's body (that is further up the hill); modern road surfaces or lamps.

### treasure

#### `benbow-parlour`: Parlour of the Admiral Benbow inn

- Book: treasure
- Chapters: `treasure:c01`, `treasure:c02`, `treasure:c03`
- Status: **NEW**, build priority #7 (tier 1)
- Living-scene hints: fire: fire, candle; cloth: curtain; sound: fire, clock, wind
- Build brief:
  - Period & location: an isolated English coastal inn, "the Admiral Benbow, Black Hill Cove", mid-18th century ("the year of grace 17—"), in a bitter January winter.
  - Layout: one low-ceilinged public parlour about 6 x 5 m, playable area ~4 x 4 m; the inn door to the road on one side, a "curtained door" into the parlour, a doorway to "the bar" behind, and the foot of "our old stairs" leading up.
  - Fireplace with coal fire: the captain "sat in a corner of the parlor next the fire, and drank rum and water very strong"; the kitchen grate's "fall of coals" is heard.
  - Plain wooden tables and chairs/benches; the captain's breakfast table laid with a napkin; he "would slap his hand on the table for silence"; rum glasses, pewter, clay pipes.
  - A longcase clock ("the very ticking of the clock"; "our old clock began striking"); a window with a blind ("Draw down the blind, Jim").
  - Captain's props by his corner seat: brass telescope, his cutlass "laying it bare before him on the table", a stick "like a handspike".
  - Through the open door: the frosty road and the big signboard of Admiral Benbow hanging outside (a notched lower frame is allowed: "You may see the notch").
  - Materials: whitewashed plaster, dark oak beams and settles, flagstone or plank floor, worn country furniture.
  - Lighting: grey winter daylight through small windows plus warm firelight and a few candles; frosty, foggy light outside.
  - Reader stands near the parlour door, facing the fire corner and the captain's table, with the bar door to one side.
  - Must NOT include: the captain's dead body or the black spot paper on the floor, the smashed/thrown-down state from c05, the repainted sign or mother's new armchair from c07, any one-legged sailor, parrot, map or treasure; no modern fittings.

#### `benbow-captains-room`: The captain's room upstairs at the Admiral Benbow

- Book: treasure
- Chapters: `treasure:c04`
- Status: **NEW**, build priority #22 (tier 2)
- Living-scene hints: fire: candle; cloth: curtain; sound: clock, wind
- Build brief:
  - Period & location: the front upstairs bedroom of the Admiral Benbow inn, Black Hill Cove, mid-18th century, a frosty January evening.
  - Layout: "the little room where he had slept so long", about 4 x 3.5 m under a sloping/low ceiling; playable area ~3 x 3 m; door to the stair landing, one window onto the road below.
  - Centrepiece: the sea-chest, open: "the initial B burned on the top of it with a hot iron, and the corners somewhat smashed and broken".
  - Chest contents spilling out: "a suit of very good clothes, carefully brushed and folded", "a quadrant, a tin cannikin, several sticks of tobacco, two brace of very handsome pistols, a piece of bar silver, an old Spanish watch", "a pair of compasses mounted with brass, and five or six curious West Indian shells", "an old boat-cloak, whitened with sea-salt".
  - A canvas bag of mixed coins ("doubloons, and louis-d'ors, and guineas, and pieces of eight") and Mrs. Crossley's bag; the oilskin-wrapped bundle of papers on top, still tied.
  - The captain's narrow bed ("this old berth") with pillow; his patched blue coat hung on a peg; thread and big needles.
  - Materials: rough plaster walls, bare plank floor, old oak bed and stool, iron-bound weathered chest smelling of "tobacco and tar".
  - Lighting: a single candle ("leaving the candle by the empty chest") as the only warm light; cold blue moonlight through fog at the window.
  - Reader kneels/stands beside the open chest, facing it, with the window and door in peripheral view.
  - Must NOT include: the broken window glass (that happens in c05 after they leave), the opened map or account book (opened in c06), any pirates in the room, the captain's body (it lies downstairs).

#### `benbow-road-bridge`: The road and little bridge below the Admiral Benbow

- Book: treasure
- Chapters: `treasure:c05`
- Status: **NEW**, build priority #30 (tier 2)
- Living-scene hints: water: stream; fire: lantern, candle; foliage: grass, shrub; sound: wind, surf
- Build brief:
  - Period & location: the frozen coast road in the dell before the Admiral Benbow, mid-18th century, a moonlit frosty January night.
  - Layout: a playable area ~6 x 6 m on the bank beside "the little bridge", with the road running past; the inn sits ~30-40 m away up the road, its door and lit upper window visible.
  - Key objects: the low stone bridge ("too low to let me do more than crawl below it"), the bank, "a bush of broom" to hide behind, a roadside ditch, hedges ("We slipped along the hedges").
  - The inn in the distance: door open, the captain's upstairs window "thrown open" with a man leaning out "into the moonlight"; the signboard.
  - A pirate lantern lying or tossing on the road ("one of the newcomers carried a lantern"); the hillside rising toward the hamlet on the other side.
  - Materials: rimed packed-earth road, dry-stone/rubble bridge, frosted grass and gorse-like broom, bare hedgerow.
  - Lighting: bright full moon ("the moon shone quite clear on the high ground") with "a thin veil" of fog lying "in the exact bottom of the dell and round the tavern door"; a warm lantern/candle glow at the inn.
  - Reader crouches behind the broom bush on the bank by the bridge, facing up the road toward the inn door.
  - Must NOT include: Pew's body or riders frozen mid-gallop as static props (optional), daylight, the beach and shingle of the cove (different space), the Hispaniola or any later-chapter elements.

#### `squires-library`: Squire Trelawney's library

- Book: treasure
- Chapters: `treasure:c06`
- Status: existing room `squires-library`
- Living-scene hints: fire: fire, candle; cloth: curtain; sound: fire, clock

#### `bristol-quays`: The Bristol quays

- Book: treasure
- Chapters: `treasure:c07`
- Status: **NEW**, build priority #43 (tier 3)
- Living-scene hints: water: ocean; cloth: sail, flag; sound: gulls, rigging, crowd
- Build brief:
  - Period & location: the working quays of Bristol harbour, mid-18th century, March (the letter is dated "March 1, 17—"), the morning Jim arrives by mail coach.
  - Layout: a cobbled quayside strip ~8 x 6 m playable, water's edge along one long side, warehouse/inn frontages along the other; the squire's "large inn" door at one end.
  - Ships moored along the quay: "the great multitude of ships of all sizes and rigs and nations"; one or two hulls close enough to see "the most wonderful figureheads".
  - Rigging overhead with "men aloft, high over my head, hanging to threads that seemed no thicker than a spider's"; sailors singing at their work.
  - Quayside clutter (c08 also describes the docks): "carts and bales", barrels, coiled rope, bollards; old sailors "with rings in their ears".
  - Materials: wet granite/limestone cobbles, tarred timber hulls, hemp rope, canvas sails, brick and timber waterfront buildings.
  - Lighting: clear morning light well after dawn; smell cues of "tar and salt" (sound and props only).
  - Reader stands on the quay facing the water and the bowsprits/figureheads of the moored ships.
  - Must NOT include: the Spy-glass tavern sign (c08), the Hispaniola by name, Long John Silver, the parrot, any island or treasure, steam/modern craft.

#### `spyglass-tavern`: The Spy-glass tavern, Bristol docks

- Book: treasure
- Chapters: `treasure:c08`
- Status: existing room `spyglass-tavern`
- Living-scene hints: water: ocean; fire: fire; cloth: curtain; sound: crowd, gulls

#### `hispaniola-cabin`: The Hispaniola's after cabin at anchor

- Book: treasure
- Chapters: `treasure:c09`
- Status: **NEW**, build priority #50 (tier 3)
- Living-scene hints: water: ocean; fire: lantern; cloth: curtain; sound: rigging, gulls
- Build brief:
  - Period & location: the main cabin aft on the schooner Hispaniola ("two hundred tons"), lying "some way out" at anchor in Bristol harbour, mid-18th century, an afternoon before sailing.
  - Layout: one low cabin ~5 x 4 m, playable ~3.5 x 3 m; companion ladder/door forward ("shut the door behind him"); stern windows aft; doorways toward the six new berths astern.
  - A fixed cabin table with chairs or lockers where the squire and doctor sit to hear the captain; a hatch in the floor to "a good place under the cabin" for powder.
  - Stacked powder kegs and muskets being carried aft ("take out the arms and powder") visible through the door.
  - Low beams, hanging lantern, "six berths had been made astern"; bunks with curtains.
  - Materials: varnished and painted oak/pine panelling, brass fittings, deck beams overhead, canvas.
  - Lighting: daylight through small stern windows, harbour water reflections; a lit oil lantern for warmth.
  - Reader stands near the cabin door facing the table, as Captain Smollett did when he entered.
  - Must NOT include: the treasure map displayed (it is kept secret), the island, the apple barrel, mutineers' weapons drawn, any blood or later-voyage damage.

#### `hispaniola-deck`: The Hispaniola's deck at sea, by the apple barrel

- Book: treasure
- Chapters: `treasure:c10`
- Status: **NEW**, build priority #55 (tier 3)
- Living-scene hints: water: ocean; fire: lantern; cloth: sail, flag; sound: surf, wind, rigging
- Build brief:
  - Period & location: the main deck ("the waist") of the schooner Hispaniola on the open sea, the last evening of the outward voyage, mid-18th century.
  - Layout: a deck section ~8 x 4 m playable between the masts, bulwarks on both sides, open sea all around.
  - Key object: "a barrel of apples standing broached in the waist" ("scarce an apple left"), big enough for a boy to climb into.
  - The helm aft ("The man at the helm was watching the luff of the sail"), the capstan, the companion/roundhouse, and "a long brass nine" swivel gun amidships (from c09).
  - Sails drawing on a steady breeze: "All was drawing alow and aloft"; bowsprit "dipping ... now and then with a whiff of spray"; lines rigged across the deck ("Long John's earrings").
  - Materials: holystoned planking, tarred rigging and blocks, canvas sails, oak bulwarks, iron-hooped barrel.
  - Lighting: "just after sundown", fading dusk sky and deepening blue sea; ship's lanterns beginning to glimmer.
  - Reader stands (or sits) beside the apple barrel facing forward along the deck, where "the watch was all forward looking out for the island".
  - Must NOT include: any island on the horizon ("Land ho" comes later), the Jolly Roger, the stockade, Ben Gunn, weapons drawn; Mr. Arrow is gone; no modern equipment.

### eighty

#### `saville-row-house`: Phileas Fogg's sitting room, No. 7 Saville Row

- Book: eighty
- Chapters: `eighty:c01`, `eighty:c02`, `eighty:c04`
- Status: **NEW**, build priority #8 (tier 1)
- Living-scene hints: fire: fire; cloth: curtain; sound: clock
- Build brief:
  - Period & location: London, Wednesday 2 October 1872; the comfortable, 'not sumptuous' house at No. 7 Saville Row, Burlington Gardens ('the house in which Sheridan died').
  - Layout: one 'cosy apartment' (first-floor sitting room with a door through to Fogg's bedroom), about 5 x 6 m playable; door to the landing on one side, tall sash window onto Saville Row on another.
  - Centrepiece: Fogg's armchair facing 'a complicated clock which indicated the hours, the minutes, the seconds, the days, the months, and the years'.
  - House is 'lighted and warmed by gas': gas brackets and a gas fire; an electric bell push and speaking-tube mouthpiece by the door ('Electric bells and speaking-tubes').
  - Through the open bedroom door: 'A moderate-sized safe ... constructed so as to defy fire as well as burglars' and a wardrobe of numbered clothes.
  - Optional c04 props on a side table: the 'modest carpetbag', a 'red-bound copy of Bradshaw's Continental Railway Steam Transit and General Guide', mackintosh and travelling-cloak over a chair, Fogg's hat.
  - Materials: polished mahogany, Turkey carpet, papered walls, brass gas fittings, marble mantel; spotless, 'cosiness, comfort, and method idealised'.
  - Lighting: grey late-morning London daylight through the window plus warm gas glow.
  - Reader stands just inside the door (where Passepartout is presented), facing Fogg's armchair and the great clock beyond it.
  - Must NOT be there: books, bookcases or a study ('There was no study, nor were there books'); 'neither arms nor hunting weapons'; trunks; souvenirs, maps or anything from the journey; electric light bulbs (gas only).

#### `reform-club`: The Reform Club card-room, Pall Mall

- Book: eighty
- Chapters: `eighty:c03`
- Status: existing room `reform-club`
- Living-scene hints: fire: fire; cloth: curtain; sound: fire, clock

#### `scotland-yard-office`: Commissioner of Police's office, Scotland Yard

- Book: eighty
- Chapters: `eighty:c05`
- Status: **NEW**, build priority #23 (tier 2)
- Living-scene hints: fire: fire, lantern; cloth: curtain; sound: clock, fire
- Build brief:
  - Period & location: London, about 9 October 1872, Scotland Yard; the office of Rowan, Commissioner of Police, 'at nine o'clock one evening'.
  - Layout: a modest Victorian official office about 4 x 5 m; large desk centre, door at one side, one sash window onto the dark street.
  - Key object: the telegraphic dispatch on the desk: 'Suez to London. Rowan, Commissioner of Police, Scotland Yard: I've found the bank robber, Phileas Fogg. Send without delay warrant of arrest to Bombay. Fix, Detective.'
  - Desk clutter: newspapers on the wager ('The Times, Standard, Morning Post, and Daily News') and the bulletin of the Royal Geographical Society.
  - The Illustrated London News with Fogg's portrait, and the robber's description on file.
  - Materials: dark oak and leather, ledgers and pigeon-holes, iron fireplace, plain plaster walls.
  - Lighting: night; gas lamp on the desk and a low coal fire; window black with street gaslight beyond.
  - Reader stands across the desk from the commissioner's chair, facing the desk and the dispatch.
  - Must NOT be there: any sign of the warrant reaching Bombay or of an arrest; telephones, typewriters, electric light.

#### `suez-quay`: The quay at Suez

- Book: eighty
- Chapters: `eighty:c06`, `eighty:c08`
- Status: **NEW**, build priority #31 (tier 2)
- Living-scene hints: water: ocean; cloth: sail, flag; sound: crowd, gulls, wind, clock
- Build brief:
  - Period & location: Suez, Egypt, Wednesday 9 October 1872, morning to noon; once a 'straggling village', now 'a fast-growing town' thanks to Lesseps.
  - Layout: a stone wharf edge about 10 x 8 m playable, water on one side, town frontage on the other; 'A jetty pier, some two thousand yards along, extended into the roadstead' running off into the distance.
  - On the water: 'fishing-smacks and coasting boats, some retaining the fantastic fashion of ancient galleys'; ship's boats; the iron P&O steamer Mongolia anchored 'in the road' in the middle distance.
  - Quay life: 'sailors of various nations, merchants, ship-brokers, porters, fellahs'; bales, crates, coal sacks, bollards.
  - Town backdrop: flat-roofed houses, 'The minarets of the town loomed above the houses'; a port clock (it 'struck' the half-hour); the consulate 'on the corner of the square'.
  - Materials: sun-bleached limestone, mud-brick and whitewash, weathered timber, rope, canvas awnings.
  - Lighting: 'The weather was clear, and slightly chilly'; low morning sun, 'the pale rays of the sun'.
  - Reader stands on the quay near the landing steps where Fix waits, facing the water and the anchored Mongolia, town and minarets behind.
  - Must NOT be there: later-chapter elements (India, Aouda, elephants); modern cranes, steel structures, motor vessels.

#### `suez-consulate`: British consul's office at Suez

- Book: eighty
- Chapters: `eighty:c07`
- Status: **NEW**, build priority #44 (tier 3)
- Living-scene hints: cloth: curtain, flag; sound: crowd
- Build brief:
  - Period & location: the British consulate at Suez, 9 October 1872, just after 11 a.m.; a house on the corner of the square near the quay.
  - Layout: one consular office about 4 x 5 m; consul's desk centre, entry door to one side, and the corner from which Fix 'devoured, the stranger with his eyes'.
  - Window: the consul's 'office window', from which he sees 'English ships daily passing to and fro on the great canal'.
  - Desk objects: passports, the 'official seal', pen and inkstand, a fee register ('Mr. Fogg paid the customary fee').
  - Furnishings: royal arms, canal chart, pigeon-holes, cane chairs, louvred shutters.
  - Materials: whitewashed plaster, dark wood desk and shutters, tiled floor, brass fittings.
  - Lighting: bright clear late-morning light through half-closed shutters, slats of sun on the floor.
  - Reader stands just inside the door (where Fogg presents his passport), facing the consul's desk with the window behind it.
  - Must NOT be there: warrants or arrest papers, anything from later stops (Bombay, Hong Kong), electric fans or lighting.

#### `mongolia-deck`: Poop-deck of the P&O steamer Mongolia

- Book: eighty
- Chapters: `eighty:c09`
- Status: existing room `mongolia-deck`
- Living-scene hints: water: ocean; cloth: flag; sound: wind, rigging, gulls

#### `malabar-hill-pagoda`: The pagoda on Malabar Hill, Bombay

- Book: eighty
- Chapters: `eighty:c10`
- Status: **NEW**, build priority #51 (tier 3)
- Living-scene hints: fire: candle, torch; foliage: flowers; cloth: curtain; sound: crowd, birds
- Build brief:
  - Period & location: Bombay, Sunday 20 October 1872, early evening before 8 p.m.; inside 'the noble pagoda on Malabar Hill, with its two polygonal towers'.
  - Layout: entrance hall/sanctuary about 8 x 8 m playable; doorway and threshold on one side, inner shrine opposite, pillars around.
  - Key surfaces: 'the splendid Brahmin ornamentation which everywhere met his eyes': carved pillars, friezes, brass bells and oil lamps.
  - Floor: 'the sacred flagging' of stone where Passepartout ends up 'sprawling'; at the doorway shoes left by the faithful ('leaving their shoes outside the door').
  - Optional figures: 'three enraged priests', his 'long-gowned adversaries'.
  - Through the doorway: the city below and the tail of the Parsee festival crowd.
  - Materials: carved basalt and sandstone, brass, marigold garlands, painted plaster.
  - Lighting: low warm sunset light through the doorway mixing with flickering oil lamps inside.
  - Reader stands just inside the threshold (where Passepartout entered, shod), facing the inner shrine.
  - Must NOT be there: Passepartout's later trial or Fix's charge, railway/Calcutta elements, Kiouni the elephant, Pillaji/suttee imagery; electric light.

### frankenstein

#### `petersburg-street`: A snowy street in St Petersburg

- Book: frankenstein
- Chapters: `frankenstein:c01`
- Status: **NEW**, build priority #9 (tier 1)
- Living-scene hints: fire: lantern; cloth: flag; sound: wind, crowd
- Build brief:
  - Period & location: St Petersburg, Russia, a winter day in the 1790s ('17—'); Walton has 'arrived here yesterday'.
  - Layout: a short stretch of snowy city street about 12 m long x 8 m wide, packed-snow roadway between pavements, with a view down the street to the north.
  - Key objects: horse-drawn sledges ('They fly quickly over the snow in their sledges'), snow-banked kerbs, iron lamp posts, a posting-house sign suggesting 'the post-road between St. Petersburgh and Archangel'.
  - Buildings: stuccoed neoclassical townhouses in ochre, pale yellow and white with tall sash windows and pilastered facades, snow on roofs and sills.
  - Walton's furs: 'wrapped in furs—a dress which I have already adopted' (a fur coat on a passer-by or the reader's perspective).
  - Materials: packed snow, stucco, granite kerbs, wrought iron, timber sledges with fur rugs.
  - Lighting: clear cold daylight, low northern-winter sun, long blue shadows; breath-mist cold.
  - Reader stands on the pavement facing north up the street into 'a cold northern breeze', sledges passing.
  - Must NOT be there: ships, ice floes, Victor, the creature, any polar scenery; no modern vehicles, tramlines or electric light.

#### `archangel-quay`: The frozen harbour quay at Archangel

- Book: frankenstein
- Chapters: `frankenstein:c02`
- Status: **NEW**, build priority #13 (tier 1)
- Living-scene hints: water: river; fire: lantern; cloth: flag; sound: wind, gulls, rigging
- Build brief:
  - Period & location: Archangel (Arkhangelsk) on the Northern Dvina, late winter/early spring 1790s; 'encompassed as I am by frost and snow'.
  - Layout: a timber wharf about 14 m x 8 m running along the river edge, with the ice-bound river beyond.
  - Key objects: Walton's hired vessel ('I have hired a vessel') moored alongside, a three-masted ship with sails furled and yards bare, still held by ice; casks, coils of rope and crates for stores on the wharf.
  - Merchants' warehouses of dark timber behind the quay ('among merchants and seamen').
  - Snow drifts against bollards; ice on the river 'delayed until the weather shall permit my embarkation'.
  - Materials: weathered log and plank timber, tarred hemp rope, iron bollards and chains, snow and grey river ice.
  - Lighting: pale overcast daylight of a northern late-winter afternoon.
  - Reader stands on the quay facing the hired ship and the frozen river.
  - Must NOT be there: Victor, the creature, dog-sledges on pack ice, open polar sea; no steamships or modern port cranes.

#### `walton-ship-deck`: The deck of Walton's ship among drifting ice

- Book: frankenstein
- Chapters: `frankenstein:c03`
- Status: **NEW**, build priority #14 (tier 1)
- Living-scene hints: water: ocean; cloth: sail, flag; sound: surf, wind, rigging, gulls
- Build brief:
  - Period & location: Walton's hired three-masted ship 'well advanced on my voyage' at 'a very high latitude' north of Archangel, 'the height of summer', 1790s.
  - Layout: the quarterdeck/waist of the ship, about 10 m long x 6 m wide, rail on both sides with open sea all around.
  - Key objects: wheel or tiller, binnacle and compass, masts and set sails filled by 'southern gales', coiled ropes, a pump (the 'springing of a leak').
  - Outside the rail: 'the floating sheets of ice that continually pass us', white floes drifting on grey-blue sea.
  - Materials: scrubbed oak deck planks, tarred rigging, canvas sails, brass fittings.
  - Lighting: low, bright polar-summer sun near the horizon; long golden light, crisp air.
  - Reader stands at the rail amidships facing forward/north over the bow.
  - Must NOT be there: the ship beset in pack ice, any sledge, Victor or the creature (they appear only in Letter IV); no steam funnel or modern equipment.

#### `arctic-ice`: The frozen sea off Walton's ship

- Book: frankenstein
- Chapters: `frankenstein:c04`
- Status: existing room `arctic-ice`
- Living-scene hints: water: ocean; cloth: sail; sound: wind, rigging

#### `como-peasant-cot`: A peasant cottage by the Lake of Como

- Book: frankenstein
- Chapters: `frankenstein:c05`
- Status: **NEW**, build priority #24 (tier 2)
- Living-scene hints: water: pond; fire: fire; foliage: leaves, shrub, flowers, grass; cloth: washing; sound: birds, wind-trees
- Build brief:
  - Period & location: northern Italy, a 'poor cot in the foldings of a vale' near 'the shores of the Lake of Como', c. 1770s.
  - Layout: the cottage doorway and dooryard, about 10 m x 8 m: a low stone cottage on one side, the open threshold showing a single plain room, a glimpse of the lake down the vale.
  - Key objects: a rough table where the peasants were 'distributing a scanty meal to five hungry babes' (bowls, bread, a pot), a hearth, wooden stools, straw.
  - The cottage looks 'singularly disconsolate'; poverty shown in patched cloth and bare floors.
  - Surroundings: 'dark-leaved brambles' and a wild rose by the door ('fairer than a garden rose among dark-leaved brambles'), chestnut trees, terraced slope.
  - Materials: rough fieldstone, lime mortar, chestnut timber beams, terracotta/stone-slab roof, beaten-earth floor.
  - Lighting: warm Italian daylight, the interior dim beyond the door.
  - Reader stands in the dooryard facing the open door, the lake behind/below.
  - Must NOT be there: the creature or anything from Victor's later life; no Geneva villa, no laboratory; no modern items. People optional (children, peasants) if any are shown.

#### `bellerive-oak`: The lightning-struck oak at Bellerive

- Book: frankenstein
- Chapters: `frankenstein:c06`
- Status: **NEW**, build priority #32 (tier 2)
- Living-scene hints: water: pond; foliage: crown, grass, shrub; cloth: curtain; sound: rain, wind-trees, wind
- Build brief:
  - Period & location: the Frankenstein 'campagne on Bellerive, the eastern shore of the lake' of Geneva, about 1780s; Victor is 'about fifteen'.
  - Layout: the doorway/porch of the country house and the lawn in front, about 14 m deep x 10 m wide; the oak stands 'about twenty yards from our house'.
  - Key object: 'an old and beautiful oak' (or its 'blasted stump' reduced 'to thin ribbons of wood' if shown after the strike).
  - Background: the Jura mountains across the lake from which the storm 'advanced', and the grey lake surface.
  - House: pale stuccoed Swiss country house with shutters, stone steps and an open front door where Victor 'stood at the door'.
  - Materials: stucco, grey stone, painted wooden shutters, wet grass, oak bark.
  - Lighting: dark storm, lightning flashes; 'the thunder burst at once with frightful loudness from various quarters of the heavens'.
  - Reader stands at the house door facing the oak and the lake toward the Jura.
  - Must NOT be there: the creature, laboratory apparatus, William or Justine-era events; no lightning rod or modern items.

#### `ingolstadt-lecture-room`: M. Waldman's lecturing room, Ingolstadt

- Book: frankenstein
- Chapters: `frankenstein:c07`
- Status: **NEW**, build priority #45 (tier 3)
- Living-scene hints: fire: fire, candle; cloth: curtain; sound: clock, crowd
- Build brief:
  - Period & location: the University of Ingolstadt, Bavaria, 1780s–90s; Victor is seventeen and new to the town.
  - Layout: a modest lecturing room about 10 m x 8 m: tiered or plain wooden benches facing a demonstration table and a raised lectern; tall windows on one side.
  - Key objects: demonstration table with apparatus for 'a few preparatory experiments' (glass retorts, crucible, flasks, a small furnace, a microscope: eyes 'to pore over the microscope or crucible').
  - A lectern/pulpit (Krempe would 'deliver sentences out of a pulpit').
  - Shelves of books and specimen jars; a blackboard optional.
  - Materials: dark oak panelling, whitewashed walls, worn pine benches, glass and brass apparatus.
  - Lighting: daylight through tall windows; glimpse of 'the high white steeple of the town'.
  - Reader stands among the benches facing the demonstration table where Waldman speaks.
  - Must NOT be there: the creature, body parts or the garret's creation table, anatomical horrors; no electric lights or modern lab equipment.

#### `ingolstadt-garret`: Victor's garret laboratory, Ingolstadt

- Book: frankenstein
- Chapters: `frankenstein:c08`, `frankenstein:c09`
- Status: existing room `ingolstadt-garret`
- Living-scene hints: fire: candle, fire; cloth: curtain; sound: rain, clock

#### `ingolstadt-sickroom`: Victor's sickroom in Ingolstadt in spring

- Book: frankenstein
- Chapters: `frankenstein:c10`
- Status: **NEW**, build priority #52 (tier 3)
- Living-scene hints: fire: candle; foliage: leaves, crown; cloth: curtain; sound: birds, clock
- Build brief:
  - Period & location: Victor's bedchamber in his lodgings at Ingolstadt, March of the spring after the creation (Elizabeth's letter dated 'Geneva, March 18th, 17—').
  - Layout: a plain student bedchamber about 5 m x 4 m: bed against one wall, window opposite, a chair for Clerval beside the bed.
  - Key objects: the bed with curtains, a letter on the coverlet ('a letter that has been lying here some days for you'), pen, ink and paper on a small table (Victor 'wrote, and this exertion greatly fatigued me').
  - Outside the window: trees with 'young buds... shooting forth from the trees that shaded my window'.
  - Some books (Clerval's oriental languages: Persian, Arabic, Sanskrit) may sit on a shelf.
  - Materials: plastered walls, pine floorboards, simple oak furniture, linen bedding, wool blanket.
  - Lighting: soft spring daylight through the window; 'a divine spring'.
  - Reader stands by the bedside facing the window and the budding trees.
  - Must NOT be there: the creature, any chemical apparatus or instruments ('Henry ... had removed all my apparatus from my view'), the sheet-covered form; nothing from Justine's trial or William's death.
