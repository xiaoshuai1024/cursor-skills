import type { VideoConfig } from "../core/types";

/**
 * 原语验证视频 - 渲染 12 秒,展示 5 个原语。
 */
export const primitiveShowcaseConfig: VideoConfig = {
  id: "primitive-showcase",
  title: "Primitive Showcase",
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    {
      type: "PrimitiveShowcase",
      props: {},
      durationInFrames: 720, // 12 秒
    },
  ],
};
