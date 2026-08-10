import type { VideoConfig } from "../core/types";

/**
 * ScenesShowcase - 每个场景各 3 秒,快速验证所有场景可渲染。
 * 6 个场景 × 3 秒 = 18 秒。
 */
export const scenesShowcaseConfig: VideoConfig = {
  id: "scenes-showcase",
  title: "Scenes Showcase",
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    {
      type: "HookTitle",
      props: {
        title: "HOOK 场景",
        subtitle: "开场 3 秒 · 抓住注意力",
        enterFrom: "depth",
      },
      durationInFrames: 180,
    },
    {
      type: "NetworkGraph",
      props: {
        nodeCount: 25,
        label: "NETWORK · 网络 / 参数 / 连接",
      },
      durationInFrames: 180,
    },
    {
      type: "TextShatter",
      props: {
        inputText: "解构问题",
        tokenList: ["解", "构", "问", "题"],
        scatterPattern: "explode",
      },
      durationInFrames: 180,
    },
    {
      type: "GlassFlythrough",
      props: {
        layerCount: 4,
      },
      durationInFrames: 180,
    },
    {
      type: "ParticleCollapse",
      props: {
        targetText: "答案",
        collapseDuration: 150,
        transitionTo2D: true,
      },
      durationInFrames: 180,
    },
    {
      type: "Outro",
      props: {
        ctaText: "关注,看懂 AI",
      },
      durationInFrames: 180,
    },
  ],
};
