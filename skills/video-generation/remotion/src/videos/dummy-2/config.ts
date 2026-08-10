import type { VideoConfig } from "../../core/types";

/**
 * Dummy-2 视频 - 验证可复用性:
 * - 只用 HookTitle + Outro 两个场景
 * - 完全不同的文案 / 配色
 * - 不改动框架代码
 */
export const dummy2Config: VideoConfig = {
  id: "dummy-2",
  title: "Dummy Video #2 - 验证可复用性",
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    {
      type: "HookTitle",
      props: {
        title: "这是另一个视频",
        subtitle: "同样的场景 · 不同的内容",
        enterFrom: "top",
      },
      durationInFrames: 180, // 3 秒
    },
    {
      type: "Outro",
      props: {
        ctaText: "关注,探索更多",
      },
      durationInFrames: 180, // 3 秒
    },
  ],
  subtitles: [
    {
      text: "这是另一个视频",
      startFrame: 30,
      endFrame: 150,
    },
    {
      text: "关注,探索更多",
      startFrame: 200,
      endFrame: 340,
    },
  ],
  // 主题覆盖:用紫色主色(验证 themeOverrides 工作)
  themeOverrides: {
    colors: {
      accent: "#a855f7", // 电光紫
      background: "#1a0a29", // 暗紫背景
    },
  },
};
