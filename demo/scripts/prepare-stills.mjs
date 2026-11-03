// Copies the stills named in src/shots.ts from ../captures into public/stills
// so Remotion can serve them with staticFile(). Only the files the cut uses are
// copied; public/stills is generated and ignored by git.
import { copyFile, mkdir, readFile, stat } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const demo = resolve(here, "..");
const captures = resolve(demo, "..", "captures");
const dest = join(demo, "public", "stills");

const shots = await readFile(join(demo, "src", "shots.ts"), "utf8");
const explicit = [...shots.matchAll(/file:\s*`(\w+)\/\$\{file\}`/g)].map(
  (m) => m[1],
);
const calls = [
  ...shots.matchAll(/\b(unity|blender|quest)\(\s*\n?\s*"([^"]+)"/g),
];
const prefix = { unity: "desktop", blender: "blender", quest: "headset" };
if (explicit.length === 0 && calls.length === 0) {
  throw new Error("no shots found in src/shots.ts");
}

let copied = 0;
for (const [, kind, file] of calls) {
  const rel = `${prefix[kind]}/${file}`;
  const src = join(captures, rel);
  const out = join(dest, rel);
  await stat(src); // throws if the capture is missing
  await mkdir(dirname(out), { recursive: true });
  await copyFile(src, out);
  copied += 1;
}
console.log(`prepare-stills: ${copied} stills copied to ${dest}`);
