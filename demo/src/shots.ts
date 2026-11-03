// The shot list for the stills cut. Every still is one of three sources and
// the caption says which, exactly as docs/PLAN.md step 10 asks:
//   blender -> "Blender render (prepared asset)"
//   unity   -> "Unity editor preview"
//   quest   -> "Quest 2 capture"
// Shots that show a staged scene (a SceneScript running) add "cached script".
// No shot in this cut shows live generation: HANDOVER confirms live
// interpretation ran on the owner's Mac but does not tie any capture to it,
// so "live generation" is never claimed here.

export type Source = "blender" | "unity" | "quest";
export type Staging = "cached script" | "live generation";

export type StillShot = {
  kind: "still";
  /** path under captures/, copied to public/stills/ by scripts/prepare-stills.mjs */
  file: string;
  /** natural pixel size of the file */
  w: number;
  h: number;
  source: Source;
  staging?: Staging;
  /** crop in natural pixels, used for the left eye of the Quest screencaps */
  crop?: { x: number; y: number; w: number; h: number };
  seconds: number;
  /** narration line shown under the shot; consecutive equal lines are merged */
  line: string;
  /** section badge, top left */
  section: string;
};

export type CardShot = {
  kind: "title" | "closing";
  seconds: number;
};

export type Shot = StillShot | CardShot;

const Q2 = { x: 0, y: 0, w: 1832, h: 1920 }; // left eye of a 3664x1920 screencap

const unity = (
  file: string,
  size: [number, number],
  seconds: number,
  line: string,
  section: string,
  staging?: Staging,
): StillShot => ({
  kind: "still",
  file: `desktop/${file}`,
  w: size[0],
  h: size[1],
  source: "unity",
  staging,
  seconds,
  line,
  section,
});

const blender = (
  file: string,
  size: [number, number],
  seconds: number,
  line: string,
  section: string,
): StillShot => ({
  kind: "still",
  file: `blender/${file}`,
  w: size[0],
  h: size[1],
  source: "blender",
  seconds,
  line,
  section,
});

const quest = (
  file: string,
  seconds: number,
  line: string,
  staging?: Staging,
): StillShot => ({
  kind: "still",
  file: `headset/${file}`,
  w: 3664,
  h: 1920,
  crop: Q2,
  source: "quest",
  staging,
  seconds,
  line,
  section: "Quest 2, 72 fps",
});

const SQ: [number, number] = [1400, 1400];
const WIDE: [number, number] = [1600, 900];
const HD: [number, number] = [1920, 1080];
const R720: [number, number] = [1280, 720];

export const SHOTS: Shot[] = [
  { kind: "title", seconds: 6 },

  // 2. The lobby and the shelf
  blender(
    "lobby/lobby_shelf_cycles-160spp.png",
    WIDE,
    3.5,
    "The app opens in a reading room. Four public-domain books face out on the shelf.",
    "The lobby",
  ),
  unity(
    "desktop-preview_Lobby_lobby-shelf.png",
    SQ,
    3.5,
    "The app opens in a reading room. Four public-domain books face out on the shelf.",
    "The lobby",
  ),
  unity(
    "desktop-preview_Lobby_lobby-hover-alice.png",
    SQ,
    3,
    "Point at a book and it slides forward. Pinch to open it.",
    "The lobby",
  ),
  unity(
    "desktop-preview_Lobby_lobby-cards-close.png",
    SQ,
    3,
    "Point at a book and it slides forward. Pinch to open it.",
    "The lobby",
  ),
  unity(
    "desktop-preview_Lobby_book-menu-alice.png",
    SQ,
    3,
    "Each book opens with its menu: resume reading, reading rooms, chapter experiences.",
    "The lobby",
  ),

  // 3. Reading a whole book
  unity(
    "desktop-preview_HallOfDoors_book-epigraph.png",
    SQ,
    3,
    "A whole book, page by page. A pinch turns the page; a left pinch turns back.",
    "Reading",
  ),
  unity(
    "desktop-preview_HallOfDoors_book-chapter1-page2.png",
    SQ,
    3.5,
    "A whole book, page by page. A pinch turns the page; a left pinch turns back.",
    "Reading",
  ),
  unity(
    "desktop-preview_HallOfDoors_book-contents.png",
    SQ,
    3,
    "Contents, text size and a bookmark live on the page. Your place is kept across restarts.",
    "Reading",
  ),
  unity(
    "desktop-preview_HallOfDoors_book-largest-text.png",
    SQ,
    3,
    "Contents, text size and a bookmark live on the page. Your place is kept across restarts.",
    "Reading",
  ),
  unity(
    "desktop-preview_HallOfDoors_oz-page-shelf.png",
    SQ,
    3,
    "Gesture cues under the text say what a pinch will do. ‹ shelf goes back to the lobby.",
    "Reading",
  ),

  // 4. The highlight ring
  unity(
    "desktop-preview_HallOfDoors_highlight-drag-menu.png",
    SQ,
    3.5,
    "Pinch on the text and drag across the words. A ring opens: Define, Search, Peek, Step In.",
    "Highlight",
  ),
  unity(
    "desktop-preview_HallOfDoors_highlight-menu.png",
    SQ,
    3,
    "Pinch on the text and drag across the words. A ring opens: Define, Search, Peek, Step In.",
    "Highlight",
  ),
  unity(
    "desktop-preview_HallOfDoors_define-curtain.png",
    SQ,
    3.5,
    "Define: Webster's 1913 dictionary, cut to the words these books use, offline.",
    "Highlight",
  ),
  unity(
    "desktop-preview_HallOfDoors_search-key.png",
    SQ,
    3.5,
    "Search looks only through the sentences you have already read. Pinch a result to go there.",
    "Highlight",
  ),
  unity(
    "desktop-preview_HallOfDoors_peek-golden-key.png",
    SQ,
    3.5,
    "Peek: a small labelled model beside the page. Pinch and hold to turn it.",
    "Highlight",
  ),
  unity(
    "desktop-preview_HallOfDoors_peek-white-rabbit.png",
    SQ,
    3,
    "Peek: a small labelled model beside the page. Pinch and hold to turn it.",
    "Highlight",
  ),

  // 5. Step In: miniature, then immersive, then the other Alice rooms
  unity(
    "desktop-preview_KansasFarmhouse_chapter-end-card.png",
    SQ,
    3.5,
    "Step In is per chapter. Finish the chapter and its experience is ready.",
    "Step In",
  ),
  unity(
    "desktop-preview_HallOfDoors_book-step-in-offered.png",
    SQ,
    3,
    "Or from the ring: Step In stages the passage from the sentence you highlighted.",
    "Step In",
  ),
  unity(
    "desktop-preview_HallOfDoors_miniature.png",
    WIDE,
    4,
    "The passage is staged as a miniature on the table, beat by beat, from a validated SceneScript.",
    "Step In",
    "cached script",
  ),
  unity(
    "desktop-preview_HallOfDoors_immersive-beat4.png",
    WIDE,
    3.5,
    "Then the room grows around you. You never move; the world does.",
    "Step In",
    "cached script",
  ),
  unity(
    "desktop_table.png",
    HD,
    3,
    "Prebuilt assets only, and nothing past where you have read.",
    "Step In",
  ),
  unity(
    "desktop_little_door.png",
    HD,
    3,
    "Prebuilt assets only, and nothing past where you have read.",
    "Step In",
  ),
  blender(
    "hall-of-doors_entrance_cycles-160spp.png",
    WIDE,
    3,
    "The Hall of Doors is built as code in Blender: geometry, materials, baked light.",
    "Step In",
  ),
  blender(
    "hall-of-doors_table_cycles-160spp.png",
    WIDE,
    3,
    "The Hall of Doors is built as code in Blender: geometry, materials, baked light.",
    "Step In",
  ),
  unity(
    "desktop-preview_MadTeaParty_miniature.png",
    WIDE,
    3,
    "The Mad Tea-Party and the Queen's Croquet-Ground open the same way.",
    "Step In",
    "cached script",
  ),
  unity(
    "desktop-preview_MadTeaParty_immersive.png",
    WIDE,
    3.5,
    "The Mad Tea-Party and the Queen's Croquet-Ground open the same way.",
    "Step In",
    "cached script",
  ),
  blender(
    "mad-tea-party/mad-tea-party_hatter_cycles-96spp.png",
    R720,
    3,
    "The Mad Tea-Party and the Queen's Croquet-Ground open the same way.",
    "Step In",
  ),
  unity(
    "desktop-preview_QueensCroquetGround_miniature-beat7.png",
    WIDE,
    3,
    "Point at the little door and pinch to go through: hall, garden, tea party.",
    "Step In",
    "cached script",
  ),
  unity(
    "desktop-preview_queens-croquet-ground_reader.png",
    WIDE,
    3.5,
    "Point at the little door and pinch to go through: hall, garden, tea party.",
    "Step In",
    "cached script",
  ),

  // 6. The rooms for the other books
  unity(
    "desktop-preview_KansasFarmhouse_room-view.png",
    SQ,
    3.5,
    "Each book has its own room. Oz: the Kansas farmhouse, with the storm coming.",
    "Rooms",
  ),
  blender(
    "kansas-farmhouse/kansas-farmhouse_outside_cycles-160spp.png",
    WIDE,
    3,
    "Each book has its own room. Oz: the Kansas farmhouse, with the storm coming.",
    "Rooms",
  ),
  unity(
    "desktop-preview_KansasFarmhouse_room-reading.png",
    SQ,
    3,
    "Each book has its own room. Oz: the Kansas farmhouse, with the storm coming.",
    "Rooms",
  ),
  blender(
    "calypsos-cave/calypsos-cave_outside_cycles-160spp.png",
    WIDE,
    3,
    "The Odyssey: Calypso's cave on Ogygia, in Samuel Butler's translation.",
    "Rooms",
  ),
  unity(
    "desktop-preview_CalypsosCave_room-reading.png",
    SQ,
    3.5,
    "The Odyssey: Calypso's cave on Ogygia, in Samuel Butler's translation.",
    "Rooms",
  ),
  blender(
    "calypsos-cave/calypsos-cave_hearth_cycles-160spp.png",
    WIDE,
    3,
    "The Odyssey: Calypso's cave on Ogygia, in Samuel Butler's translation.",
    "Rooms",
  ),
  blender(
    "glumdalclitchs-room/glumdalclitchs-room_sewing_cycles-160spp.png",
    WIDE,
    3,
    "Gulliver: Glumdalclitch's room in Brobdingnag, read at doll scale.",
    "Rooms",
  ),
  unity(
    "desktop-preview_GlumdalclitchsRoom_room-reading.png",
    SQ,
    3.5,
    "Gulliver: Glumdalclitch's room in Brobdingnag, read at doll scale.",
    "Rooms",
  ),

  // 7. The personal library
  unity(
    "desktop-preview_Lobby_library-board.png",
    SQ,
    3.5,
    "The lobby is your library: a board lists the four editions and every book you add.",
    "Your library",
  ),
  unity(
    "desktop-preview_Lobby_library-add-card.png",
    SQ,
    3.5,
    "Pinch + add a book, then send an EPUB or a PDF from a phone on the same Wi-Fi.",
    "Your library",
  ),
  unity(
    "desktop-preview_LibraryRoom_imported-epub-menu.png",
    SQ,
    3,
    "Imported books open in the library room, with Define and Search like any other.",
    "Your library",
  ),
  unity(
    "desktop-preview_LibraryRoom_pdf-page-view.png",
    SQ,
    3,
    "PDFs show their pages as laid out, with a text view for highlighting.",
    "Your library",
  ),

  // 8. On the headset
  quest(
    "centred_1_032434.png",
    3.5,
    "On a Quest 2, with hands: 72 fps at the page and with the diorama.",
    "cached script",
  ),
  quest(
    "headset_02_reading.png",
    3,
    "On a Quest 2, with hands: 72 fps at the page and with the diorama.",
    "cached script",
  ),
  quest(
    "relit_now_030858.png",
    3,
    "On a Quest 2, with hands: 72 fps at the page and with the diorama.",
    "cached script",
  ),
  quest(
    "headset_11_turn.png",
    3,
    "The page holds still where you put it; gesture cues sit under the text.",
  ),
  quest(
    "point_052320.png",
    3,
    "Point and pinch acts on what you point at. One hand, seated.",
    "cached script",
  ),
  quest(
    "point_052351.png",
    3.5,
    "Point and pinch acts on what you point at. One hand, seated.",
    "cached script",
  ),

  { kind: "closing", seconds: 8 },
];

export const SOURCE_LABEL: Record<Source, string> = {
  blender: "Blender render (prepared asset)",
  unity: "Unity editor preview",
  quest: "Quest 2 capture",
};
