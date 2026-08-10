import type { VideoConfig } from "../core/types";

/**
 * Dummy 视频配置 - 用于验证 VideoComposition 装配管线。
 *
 * 3 个场景:A(60帧 = 1s @ 60fps) + B(120帧 = 2s) + A(60帧 = 1s)
 * 总计 240 帧 = 4 秒。
 */
export const dummyConfig: VideoConfig = {
  id: "dummy-test",
  title: "Dummy Test Video",
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    {
      type: "DummyA",
      props: { title: "Scene One" },
      durationInFrames: 60,
    },
    {
      type: "DummyB",
      props: { label: "场景之间自动衔接" },
      durationInFrames: 120,
    },
    {
      type: "DummyA",
      props: { title: "Scene Three" },
      durationInFrames: 60,
    },
  ],
  subtitles: [
    { text: "这是第一条字幕", startFrame: 0, endFrame: 60 },
    { text: "第二条字幕 - 场景 B 期间", startFrame: 80, endFrame: 160 },
    { text: "最后一条字幕", startFrame: 200, endFrame: 240 },
  ],
};
