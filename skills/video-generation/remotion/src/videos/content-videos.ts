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
    id: "deepseek-cheap-power",
    title: "DeepSeek 有多便宜？V4 Flash 能力世界第二，涨价却要来了",
    durationInFrames: 9317,
    fps: 60,
    width: 1920,
    height: 1080,
    lazyComponent: () => import("@videos/deepseek-cheap-power/config").then((m) => {
      const cfg = toConfig(m);
      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });
      return { default: Comp };
    }),
  },
];
