import type { VideoConfig } from "../../core/types";
export const testDRConfig: VideoConfig = {
  id: "test-datareveal",
  title: "DataReveal Test",
  fps: 60,
  scenes: [{ type: "DataReveal", props: { number: 380, label: "页面" }, durationInFrames: 180 }],
};
