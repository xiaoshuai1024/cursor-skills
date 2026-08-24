// 自动生成，勿手改：pnpm exec tsx scripts/sync-content-videos.ts
// 内容视频配置在 git 忽略的 .video-generation/remotion-videos/ 下，按需加载：
// 只登记当前存在的 config.ts；缺失的配置不会进入本文件，打包不会因引用被忽略的文件失败。
import React from "react";
import { VideoComposition } from "../core/VideoComposition";
import type { VideoConfig } from "../core/types";

export interface ContentVideoEntry {
  id: string;
  title: string;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
  lazyComponent: () => Promise<{ default: React.ComponentType }>;
}

const toConfig = (m: Record<string, unknown>): VideoConfig => {
  const looksLike = (v: unknown): v is VideoConfig =>
    !!v && typeof v === 'object' && Array.isArray((v as VideoConfig).scenes) && typeof (v as VideoConfig).id === 'string';
  if (looksLike(m.default)) return m.default as VideoConfig;
  for (const v of Object.values(m)) { if (looksLike(v)) return v as VideoConfig; }
  throw new Error('config 模块未导出 VideoConfig');
};

export const contentVideos: ContentVideoEntry[] = [
  {
    id: "ai-agent-engineering-evolution",
    title: "Harness 工程：AI 编程从命令体系到自治体系的演进",
    durationInFrames: 19509,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/ai-agent-engineering-evolution/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "ai-buzzwords-one-line",
    title: "别再背 AI 黑话了：一条主线串起大模型、Agent、Skill、MCP",
    durationInFrames: 16803,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/ai-buzzwords-one-line/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "ai-dev-stop-discipline",
    title: "21 万 Star 的 25 个 Skill 把工程师自律焊进 AI 流程",
    durationInFrames: 19196,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/ai-dev-stop-discipline/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "claude-code-write-your-own-skill",
    title: "收藏 80 个 skill 不如写 1 个：Claude Code 从零到能跑",
    durationInFrames: 10312,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/claude-code-write-your-own-skill/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "claude-codex-arch-overview",
    title: "",
    durationInFrames: 12728,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/claude-codex-arch-overview/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "claude-codex-context-compaction",
    title: "",
    durationInFrames: 12354,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/claude-codex-context-compaction/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "claude-codex-permission-gating",
    title: "",
    durationInFrames: 13363,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/claude-codex-permission-gating/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "claude-codex-skill-mcp-loading",
    title: "",
    durationInFrames: 13658,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/claude-codex-skill-mcp-loading/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "claude-codex-subagent-scheduling",
    title: "",
    durationInFrames: 12767,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/claude-codex-subagent-scheduling/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "claude-codex-top10-plugins",
    title: "Claude 和 Codex 必装的 10 大插件",
    durationInFrames: 9495,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/claude-codex-top10-plugins/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "claude-codex-turn-loop",
    title: "",
    durationInFrames: 13145,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/claude-codex-turn-loop/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "deepseek-harness-first-look",
    title: "DeepSeek 开源自研 Harness：模型、工具、Agent Loop 一切皆插件",
    durationInFrames: 21925,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/deepseek-harness-first-look/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "ecc-agent-os",
    title: "黑客松冠军开源 24 万星的 ECC：把 agent 工程做成了操作系统",
    durationInFrames: 16467,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/ecc-agent-os/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "glm-5-3-coding-evaluation",
    title: "GLM-5.3 发布实测：编程暴涨 50%，开源第一的成色拆开看",
    durationInFrames: 9779,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/glm-5-3-coding-evaluation/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "motion-showcase",
    title: "Motion Showcase：动画原语与转场",
    durationInFrames: 2130,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/motion-showcase/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "pi-agent-beats-claude-code",
    title: "Pi Agent 凭什么打赢 Claude Code：极简内核与扩展系统的胜负手",
    durationInFrames: 12136,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/pi-agent-beats-claude-code/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "pipeline-arch",
    title: "一条技术视频是怎么自动做出来的",
    durationInFrames: 3613,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/pipeline-arch/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
  {
    id: "video-pipeline-6-skills",
    title: "",
    durationInFrames: 11412,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/video-pipeline-6-skills/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
];
