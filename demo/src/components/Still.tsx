import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { HEIGHT, PAPER, WIDTH } from "../theme";
import type { StillShot } from "../shots";

type Props = {
  shot: StillShot;
  durationInFrames: number;
  /** alternates the direction of the Ken Burns move */
  index: number;
};

// Fits the (cropped) still inside the frame on the paper colour: pillarbox or
// letterbox, never stretched. A slow Ken Burns move (scale 1.0 to 1.06 and a
// gentle pan) runs inside an overflow-hidden box the size of the fitted image.
export const Still: React.FC<Props> = ({ shot, durationInFrames, index }) => {
  const frame = useCurrentFrame();
  const crop = shot.crop ?? { x: 0, y: 0, w: shot.w, h: shot.h };

  const s = Math.min(WIDTH / crop.w, HEIGHT / crop.h);
  const boxW = Math.round(crop.w * s);
  const boxH = Math.round(crop.h * s);

  const t = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const zoomIn = index % 2 === 0;
  const scale = zoomIn ? 1 + 0.06 * t : 1.06 - 0.06 * t;
  const dir = index % 4 < 2 ? 1 : -1;
  const panX = dir * (boxW * 0.012) * (t - 0.5);
  const panY = (index % 3 === 0 ? -1 : 1) * (boxH * 0.008) * (t - 0.5);

  return (
    <AbsoluteFill style={{ backgroundColor: PAPER }}>
      <div
        style={{
          position: "absolute",
          left: (WIDTH - boxW) / 2,
          top: (HEIGHT - boxH) / 2,
          width: boxW,
          height: boxH,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: boxW,
            height: boxH,
            transform: `translate(${panX}px, ${panY}px) scale(${scale})`,
            transformOrigin: "50% 50%",
          }}
        >
          <Img
            src={staticFile(`stills/${shot.file}`)}
            style={{
              position: "absolute",
              left: -crop.x * s,
              top: -crop.y * s,
              width: shot.w * s,
              height: shot.h * s,
              display: "block",
            }}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
