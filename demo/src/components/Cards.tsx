import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { BRASS, INK, INK_SOFT, PAPER, SERIF } from "../theme";
import { SOURCE_LABEL } from "../shots";

const rise = (frame: number, from: number, to: number) =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

export const TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const a = rise(frame, 4, 26);
  const b = rise(frame, 22, 46);
  const rule = rise(frame, 14, 40);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: PAPER,
        color: INK,
        fontFamily: SERIF,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          fontSize: 168,
          fontWeight: 600,
          letterSpacing: -2,
          lineHeight: 1,
          opacity: a,
          transform: `translateY(${(1 - a) * 18}px)`,
        }}
      >
        Fable
      </div>
      <div
        style={{
          width: 180 * rule,
          height: 2,
          backgroundColor: BRASS,
          marginTop: 34,
          marginBottom: 34,
        }}
      />
      <div
        style={{
          fontSize: 44,
          fontStyle: "italic",
          fontWeight: 400,
          opacity: b,
          transform: `translateY(${(1 - b) * 14}px)`,
        }}
      >
        Read a page. Pinch. The room unfolds around you.
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 48,
          fontSize: 24,
          color: INK_SOFT,
          opacity: b,
        }}
      >
        A reader for whole books on Meta Quest
      </div>
    </AbsoluteFill>
  );
};

const LABELS: { label: string; what: string }[] = [
  {
    label: SOURCE_LABEL.blender,
    what: "a Cycles still of a room built by the Blender scripts",
  },
  {
    label: SOURCE_LABEL.unity,
    what: "the Unity editor's desktop camera, no headset",
  },
  {
    label: SOURCE_LABEL.quest,
    what: "adb screencap on a Quest 2, left eye",
  },
];

export const ClosingCard: React.FC = () => {
  const frame = useCurrentFrame();
  const a = rise(frame, 2, 22);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: PAPER,
        color: INK,
        fontFamily: SERIF,
        alignItems: "center",
        justifyContent: "center",
        opacity: a,
      }}
    >
      <div style={{ fontSize: 72, fontWeight: 600, letterSpacing: -1 }}>
        Fable
      </div>
      <div
        style={{
          fontSize: 30,
          fontStyle: "italic",
          color: INK_SOFT,
          marginTop: 10,
          marginBottom: 44,
        }}
      >
        Every shot in this cut is a still from one of three sources.
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {LABELS.map((l, i) => {
          const o = rise(frame, 20 + i * 10, 38 + i * 10);
          return (
            <div
              key={l.label}
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 22,
                opacity: o,
                transform: `translateY(${(1 - o) * 10}px)`,
              }}
            >
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 10,
                  backgroundColor: BRASS,
                  display: "inline-block",
                  position: "relative",
                  top: -4,
                }}
              />
              <span style={{ fontSize: 34, fontWeight: 600, minWidth: 560 }}>
                {l.label}
              </span>
              <span style={{ fontSize: 28, color: INK_SOFT }}>{l.what}</span>
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 48,
          fontSize: 24,
          color: INK_SOFT,
          textAlign: "center",
          lineHeight: 1.5,
        }}
      >
        Staged scenes ran from cached SceneScripts; no live generation is shown.
        <br />
        Texts and covers are public domain; sources in CREDITS.md. Meta VR Start
        2026.
      </div>
    </AbsoluteFill>
  );
};
