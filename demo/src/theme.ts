import { loadFont as loadFraunces } from "@remotion/google-fonts/Fraunces";

// A quiet paper palette. Nothing else in the film uses colour; the stills do.
export const PAPER = "#f3efe6";
export const INK = "#2b2520";
export const BRASS = "#9a6a1f";
export const INK_SOFT = "rgba(43, 37, 32, 0.62)";

export const WIDTH = 1920;
export const HEIGHT = 1080;
export const FPS = 30;

// 0.4 s cross dissolve between every pair of shots.
export const DISSOLVE_FRAMES = 12;

const upright = loadFraunces("normal", {
  weights: ["400", "600"],
  subsets: ["latin"],
});
loadFraunces("italic", {
  weights: ["400"],
  subsets: ["latin"],
});

// Fraunces when the font loads; a system serif when it does not (offline render).
export const SERIF = `${upright.fontFamily}, "Iowan Old Style", "Palatino", "Georgia", "Times New Roman", serif`;
