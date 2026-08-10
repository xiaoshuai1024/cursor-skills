import type { VideoConfig } from "../core/types";

export const minimal3dConfig: VideoConfig = {
  id: "minimal-3d",
  title: "Minimal 3D Test",
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    {
      type: "Minimal3D",
      props: {},
      durationInFrames: 120, // 2 秒
    },
  ],
};
