#!/usr/bin/env node
/**
 * 同步内容视频注册表（配置按需加载）。
 *
 * 背景：内容视频的 config.ts 位于 git 忽略的 .video-generation/remotion-videos/<id>/，
 * 目录被清理后 Root.tsx 的静态 import 会让打包直接失败。
 *
 * 方案：扫描 .video-generation/remotion-videos 下各 config.ts，逐个求值拿到
 * 静态元数据（id / duration / fps / 尺寸 / title），生成 src/videos/content-videos.ts。
 * - 不存在的配置不会出现在注册表里 → 打包不炸
 * - 新增/删除内容视频不用改 Root.tsx，重跑本脚本即可
 * - 每个条目用 lazyComponent 按需加载（Remotion 代码分包）
 *
 * 用法：
 *   pnpm exec tsx scripts/sync-content-videos.ts   # 手动同步
 *   pnpm render                                     # render.ts 渲染前自动同步
 */
import fs from "node:fs";
import path from "node:path";

const REMOTION_ROOT = path.resolve(__dirname, "..");
const OUT_FILE = path.join(REMOTION_ROOT, "src", "videos", "content-videos.ts");

function findProjectRoot(start: string): string {
  let dir = start;
  while (path.dirname(dir) !== dir) {
    if (fs.existsSync(path.join(dir, "hugo.toml")) || fs.existsSync(path.join(dir, ".git"))) {
      return dir;
    }
    dir = path.dirname(dir);
  }
  return path.resolve(start, "../../../..");
}

interface ContentVideoMeta {
  id: string;
  title: string;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
}

function pickVideoConfig(mod: Record<string, unknown>): Record<string, unknown> | null {
  const looksLike = (v: unknown): v is Record<string, unknown> =>
    !!v &&
    typeof v === "object" &&
    Array.isArray((v as Record<string, unknown>).scenes) &&
    typeof (v as Record<string, unknown>).id === "string";
  if (looksLike(mod.default)) return mod.default as Record<string, unknown>;
  for (const v of Object.values(mod)) {
    if (looksLike(v)) return v as Record<string, unknown>;
  }
  return null;
}

function metaOf(cfg: Record<string, unknown>): ContentVideoMeta {
  const scenes = cfg.scenes as Array<{ durationInFrames: number }>;
  return {
    id: cfg.id as string,
    title: (cfg.title as string) ?? "",
    durationInFrames: scenes.reduce((sum, s) => sum + (s.durationInFrames ?? 0), 0),
    fps: (cfg.fps as number) ?? 60,
    width: (cfg.width as number) ?? 1920,
    height: (cfg.height as number) ?? 1080,
  };
}

function renderRegistry(entries: Array<ContentVideoMeta & { configPath: string }>): string {
  const L: string[] = [];
  L.push("// 自动生成，勿手改：pnpm exec tsx scripts/sync-content-videos.ts");
  L.push("// 内容视频配置在 git 忽略的 .video-generation/remotion-videos/ 下，按需加载：");
  L.push("// 只登记当前存在的 config.ts；缺失的配置不会进入本文件，打包不会因引用被忽略的文件失败。");
  L.push('import React from "react";');
  L.push('import { VideoComposition } from "../core/VideoComposition";');
  L.push('import type { VideoConfig } from "../core/types";');
  L.push("");
  L.push("export interface ContentVideoEntry {");
  L.push("  id: string;");
  L.push("  title: string;");
  L.push("  durationInFrames: number;");
  L.push("  fps: number;");
  L.push("  width: number;");
  L.push("  height: number;");
  L.push("  lazyComponent: () => Promise<{ default: React.ComponentType }>;");
  L.push("}");
  L.push("");
  L.push("const toConfig = (m: Record<string, unknown>): VideoConfig => {");
  L.push("  const looksLike = (v: unknown): v is VideoConfig =>");
  L.push("    !!v && typeof v === 'object' && Array.isArray((v as VideoConfig).scenes) && typeof (v as VideoConfig).id === 'string';");
  L.push("  if (looksLike(m.default)) return m.default as VideoConfig;");
  L.push("  for (const v of Object.values(m)) { if (looksLike(v)) return v as VideoConfig; }");
  L.push("  throw new Error('config 模块未导出 VideoConfig');");
  L.push("};");
  L.push("");
  if (entries.length === 0) {
    L.push("// 当前没有内容视频配置（.video-generation/remotion-videos 为空或不存在）");
    L.push("export const contentVideos: ContentVideoEntry[] = [];");
  } else {
    L.push("export const contentVideos: ContentVideoEntry[] = [");
    for (const e of entries) {
      L.push("  {");
      L.push(`    id: ${JSON.stringify(e.id)},`);
      L.push(`    title: ${JSON.stringify(e.title)},`);
      L.push(`    durationInFrames: ${e.durationInFrames},`);
      L.push(`    fps: ${e.fps},`);
      L.push(`    width: ${e.width},`);
      L.push(`    height: ${e.height},`);
      L.push(`    lazyComponent: () => import("@videos/${e.id}/config").then((m) => {`);
      L.push("      const cfg = toConfig(m);");
      L.push("      const Comp: React.FC = () => React.createElement(VideoComposition, { config: cfg });");
      L.push("      return { default: Comp };");
      L.push("    }),");
      L.push("  },");
    }
    L.push("];");
  }
  L.push("");
  return L.join("\n");
}

export async function syncContentVideos(): Promise<number> {
  const projectRoot = findProjectRoot(REMOTION_ROOT);
  const contentDir = path.join(projectRoot, "video-generation", "remotion-videos");

  const ids: string[] = [];
  if (fs.existsSync(contentDir)) {
    for (const dir of fs.readdirSync(contentDir)) {
      if (fs.existsSync(path.join(contentDir, dir, "config.ts"))) {
        ids.push(dir);
      }
    }
  }
  ids.sort();

  const entries: Array<ContentVideoMeta & { configPath: string }> = [];
  for (const id of ids) {
    const configPath = path.join(contentDir, id, "config.ts");
    try {
      const mod = (await import(configPath)) as Record<string, unknown>;
      const cfg = pickVideoConfig(mod);
      if (!cfg) {
        console.warn(`[sync-content-videos] 跳过 ${id}: 未找到 VideoConfig 导出`);
        continue;
      }
      entries.push({ ...metaOf(cfg), configPath });
    } catch (err) {
      console.warn(`[sync-content-videos] 跳过 ${id}: ${(err as Error).message}`);
    }
  }

  fs.writeFileSync(OUT_FILE, renderRegistry(entries), "utf-8");
  console.log(
    `[sync-content-videos] ${entries.length} 个内容视频已登记 → ${path.relative(REMOTION_ROOT, OUT_FILE)}` +
      (entries.length ? ` (${entries.map((e) => e.id).join(", ")})` : ""),
  );
  return entries.length;
}

if (require.main === module) {
  syncContentVideos().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
