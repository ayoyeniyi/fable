import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { BRASS, INK, PAPER, SERIF } from "../theme";
import { SOURCE_LABEL, type StillShot } from "../shots";

const pill: React.CSSProperties = {
  position: "absolute",
  display: "flex",
  alignItems: "center",
  gap: 12,
  padding: "10px 18px 11px",
  backgroundColor: "rgba(243, 239, 230, 0.94)",
  color: INK,
  fontFamily: SERIF,
  fontSize: 24,
  lineHeight: 1,
  letterSpacing: 0.2,
  borderRadius: 4,
  boxShadow: "0 1px 0 rgba(43, 37, 32, 0.12)",
  whiteSpace: "nowrap",
};

/** The persistent source caption, top right of every still. */
export const SourceCaption: React.FC<{ shot: StillShot }> = ({ shot }) => {
  const text = shot.staging
    ? `${SOURCE_LABEL[shot.source]} · ${shot.staging}`
    : SOURCE_LABEL[shot.source];
  return (
    <div style={{ ...pill, top: 28, right: 32 }}>
      <span
        style={{
          width: 9,
          height: 9,
          borderRadius: 9,
          backgroundColor: BRASS,
          display: "inline-block",
        }}
      />
      <span>{text}</span>
    </div>
  );
};

/** Section badge, top left. */
export const SectionBadge: React.FC<{ text: string }> = ({ text }) => (
  <div
    style={{
      ...pill,
      top: 28,
      left: 32,
      fontSize: 24,
      fontStyle: "italic",
      color: BRASS,
    }}
  >
    {text}
  </div>
);

/** One narration line, bottom centre, fading in and out over its span. */
export const Narration: React.FC<{ text: string; durationInFrames: number }> = ({
  text,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [0, 8, Math.max(9, durationInFrames - 8), durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 44,
        display: "flex",
        justifyContent: "center",
        opacity,
      }}
    >
      <div
        style={{
          maxWidth: 1480,
          padding: "16px 34px 19px",
          backgroundColor: "rgba(243, 239, 230, 0.95)",
          borderTop: `2px solid ${BRASS}`,
          color: INK,
          fontFamily: SERIF,
          fontSize: 36,
          lineHeight: 1.25,
          textAlign: "center",
          borderRadius: 4,
        }}
      >
        {text}
      </div>
    </div>
  );
};

export { PAPER };
