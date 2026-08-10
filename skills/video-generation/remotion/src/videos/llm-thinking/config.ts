import type { VideoConfig } from "../../core/types";

/**
 * "LLM 是怎么思考的" - 30 秒科普视频配置。
 *
 * 分镜:
 * - 0-3s  (180 帧) HookTitle:     "LLM 怎么思考?"
 * - 3-8s  (300 帧) NetworkGraph:  神经元网络亮起
 * - 8-15s (420 帧) TextShatter:   输入文字碎裂成 token
 * - 15-22s(420 帧) GlassFlythrough: 摄像机穿梭 Transformer 层
 * - 22-27s(300 帧) ParticleCollapse: 粒子汇聚成答案
 * - 27-30s(180 帧) Outro:         Logo + CTA
 *
 * 总时长:1800 帧 = 30 秒 @ 60fps
 */
export const llmThinkingConfig: VideoConfig = {
  id: "llm-thinking",
  title: "LLM 是怎么思考的",
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    {
      type: "HookTitle",
      props: {
        title: "LLM 怎么思考?",
        subtitle: "一个 30 秒的视觉解答",
        enterFrom: "depth",
      },
      durationInFrames: 180, // 0-3s
    },
    {
      type: "NetworkGraph",
      props: {
        nodeCount: 35,
        label: "首先,它是数十亿参数",
      },
      durationInFrames: 300, // 3-8s
    },
    {
      type: "TextShatter",
      props: {
        inputText: "什么是人工智能?",
        tokenList: ["什么", "是", "人工", "智能", "?"],
        scatterPattern: "explode",
      },
      durationInFrames: 420, // 8-15s
    },
    {
      type: "GlassFlythrough",
      props: {
        layerCount: 5,
      },
      durationInFrames: 420, // 15-22s
    },
    {
      type: "ParticleCollapse",
      props: {
        targetText: "概率 → 文字",
        collapseDuration: 240,
        transitionTo2D: true,
      },
      durationInFrames: 300, // 22-27s
    },
    {
      type: "Outro",
      props: {
        ctaText: "关注,看懂 AI",
      },
      durationInFrames: 180, // 27-30s
    },
  ],
  subtitles: [
    {
      text: "LLM 是怎么思考的?",
      startFrame: 60,
      endFrame: 180,
    },
    {
      text: "首先,它是数十亿参数构成的网络",
      startFrame: 240,
      endFrame: 480,
    },
    {
      text: "你的问题被拆成一个个碎片",
      startFrame: 540,
      endFrame: 780,
    },
    {
      text: "每一层都在问:谁和谁相关?",
      startFrame: 900,
      endFrame: 1140,
    },
    {
      text: "最后,概率坍缩成文字",
      startFrame: 1320,
      endFrame: 1560,
    },
    {
      text: "关注,看懂 AI",
      startFrame: 1650,
      endFrame: 1780,
    },
  ],
  // 注:BGM 需手动下载 CC0 音乐放到 src/videos/llm-thinking/assets/bgm.mp3
  // 推荐来源:Pixabay Music / YouTube Audio Library,选"低沉电子 / 科技感"
  // audioPath: "llm-thinking/assets/bgm.mp3",
};
