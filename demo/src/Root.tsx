import React from "react";
import { Composition } from "remotion";
import { Film, totalFrames } from "./Film";
import { SHOTS } from "./shots";
import { FPS, HEIGHT, WIDTH } from "./theme";

export const Root: React.FC = () => (
  <Composition
    id="FableDemo"
    component={Film}
    durationInFrames={totalFrames(SHOTS)}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);
