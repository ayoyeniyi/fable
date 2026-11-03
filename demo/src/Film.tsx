import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { DISSOLVE_FRAMES, FPS, PAPER } from "./theme";
import { SHOTS, type Shot, type StillShot } from "./shots";
import { Still } from "./components/Still";
import { Narration, SectionBadge, SourceCaption } from "./components/Captions";
import { ClosingCard, TitleCard } from "./components/Cards";

// TODO(music): this cut is silent on purpose. If a track is added, it needs a
// credited licence recorded in CREDITS.md (the two CC0 recordings fetched by
// tools/fetch_music.py are the obvious candidates) before it goes in here.

type Placed = { shot: Shot; from: number; duration: number };

/** Lays the shots end to end, each overlapping the previous by the dissolve. */
export const placeShots = (shots: Shot[]): Placed[] => {
  const placed: Placed[] = [];
  let cursor = 0;
  for (const shot of shots) {
    const duration = Math.round(shot.seconds * FPS);
    placed.push({ shot, from: cursor, duration });
    cursor += duration - DISSOLVE_FRAMES;
  }
  return placed;
};

export const totalFrames = (shots: Shot[]): number => {
  const placed = placeShots(shots);
  const last = placed[placed.length - 1];
  return last.from + last.duration;
};

/** Narration spans: consecutive stills with the same line share one band. */
const narrationSpans = (placed: Placed[]) => {
  const spans: { text: string; from: number; to: number }[] = [];
  for (const p of placed) {
    if (p.shot.kind !== "still") continue;
    const last = spans[spans.length - 1];
    const to = p.from + p.duration - DISSOLVE_FRAMES;
    if (last && last.text === p.shot.line && last.to >= p.from) {
      last.to = to;
    } else {
      spans.push({ text: p.shot.line, from: p.from + DISSOLVE_FRAMES, to });
    }
  }
  return spans;
};

const FadeIn: React.FC<{ children: React.ReactNode; enabled: boolean }> = ({
  children,
  enabled,
}) => {
  const frame = useCurrentFrame();
  const opacity = enabled
    ? interpolate(frame, [0, DISSOLVE_FRAMES], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};

export const Film: React.FC = () => {
  const placed = placeShots(SHOTS);
  const spans = narrationSpans(placed);

  return (
    <AbsoluteFill style={{ backgroundColor: PAPER }}>
      {placed.map((p, i) => {
        const shot = p.shot;
        return (
          <Sequence
            key={i}
            from={p.from}
            durationInFrames={p.duration}
            name={shot.kind === "still" ? shot.file : shot.kind}
          >
            <FadeIn enabled={i > 0}>
              {shot.kind === "still" ? (
                <StillWithCaptions shot={shot} duration={p.duration} index={i} />
              ) : shot.kind === "title" ? (
                <TitleCard />
              ) : (
                <ClosingCard />
              )}
            </FadeIn>
          </Sequence>
        );
      })}
      {spans.map((s, i) => (
        <Sequence
          key={`n${i}`}
          from={s.from}
          durationInFrames={Math.max(1, s.to - s.from)}
          name={`line: ${s.text.slice(0, 32)}`}
        >
          <Narration text={s.text} durationInFrames={s.to - s.from} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const StillWithCaptions: React.FC<{
  shot: StillShot;
  duration: number;
  index: number;
}> = ({ shot, duration, index }) => (
  <AbsoluteFill>
    <Still shot={shot} durationInFrames={duration} index={index} />
    <SectionBadge text={shot.section} />
    <SourceCaption shot={shot} />
  </AbsoluteFill>
);
