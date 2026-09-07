#!/usr/bin/env node
/**
 * 视频渲染脚本 - 支持通过 env 变量选择视频 ID。
 *
 * 用法:
 *   pnpm render                    # 默认渲染 llm-thinking
 *   VIDEO_ID=scenes-showcase pnpm render  # 渲染 scenes-showcase
 *   VIDEO_ID=dummy-test pnpm render       # 渲染 dummy-test
 */
import { execSync } from "child_process";
import path from "path";
import fs from "fs";
import { syncContentVideos } from "./sync-content-videos";

const videoId = process.env.VIDEO_ID || "llm-thinking";
const entryPoint = "src/index.ts";

/** 从 cwd 向上找项目根，定位 video-generation/build/。
 * 最高优先 VIDEO_PROJECT_ROOT（blog-src Makefile 显式传入）；未传再走向上探测 + 同级 blog-src 兜底。 */
function findProjectRoot(start: string): string {
  if (process.env.VIDEO_PROJECT_ROOT) return process.env.VIDEO_PROJECT_ROOT;
  let dir = start;
  while (path.dirname(dir) !== dir) {
    if (fs.existsSync(path.join(dir, "hugo.toml")) || fs.existsSync(path.join(dir, ".git"))) {
      // 命中 .git 但无 hugo.toml 的可能是 skill 源仓库自身（bind mount 场景：
      // cwd 物理路径在 codes/skills 下，向上找不到 blog-src 的 hugo.toml）。
      // 此时回退到同级目录里找含 hugo.toml 的项目。
      if (!fs.existsSync(path.join(dir, "hugo.toml"))) {
        const parent = path.dirname(dir);
        for (const name of fs.readdirSync(parent)) {
          if (name === "blog-src" && fs.existsSync(path.join(parent, name, "hugo.toml"))) {
            return path.join(parent, name);
          }
        }
      }
      return dir;
    }
    dir = path.dirname(dir);
  }
  return path.resolve(start, "../../../..");
}

const projectRoot = findProjectRoot(process.cwd());
// 产物固定到 video-generation/build/<videoId>/<videoId>.mp4（无时间戳，发布管线 find_video 据此定位）
const outputDir = path.join(projectRoot, "video-generation", "build", videoId);
const outputFile = `${videoId}.mp4`;
const outputPath = path.join(outputDir, outputFile);

/** 声音层素材(BGM + SFX,VideoComposition 原生渲染引用 public/ 即 narration/ 目录)。
 * 合成轨缺失时自动重跑 gen-sfx.py(纯 stdlib 确定性合成,重跑结果一致)——
 * 保证新视频零配置即有 BGM/音效,不会因素材被清而静默丢声。
 * 默认 BGM 是外部曲(gen-sfx 生成不了),从 skill scripts/assets/ 副本离线恢复。 */
function ensureSfxAssets(root: string): void {
  const narrationDir = path.join(root, "video-generation", "narration");
  // 默认 BGM(2026-09-06 定规 Mixkit Raising Me Higher,响度已校准)走 assets 副本恢复
  const DEFAULT_BGM_FILE = "bgm-raising-me-higher.mp3";
  const required = [
    DEFAULT_BGM_FILE,
    "bgm-bed.wav",
    "bgm-light-calm.wav",
    "bgm-light-walk.wav",
    "bgm-light-focus.wav",
    "bgm-light-bright.wav",
    "bgm-tense.wav",
    "bgm-epic.wav",
    "bgm-chiptune.wav",
    "bgm-lofi.wav",
    "sfx-opening-chime.wav",
    "sfx-transition-swoosh.wav",
    "sfx-question-up.wav",
    "sfx-emphasis.wav",
    "sfx-reveal.wav",
    "sfx-reveal-bloom.wav",
    "sfx-ding.wav",
  ];
  const missing = required.filter((f) => !fs.existsSync(path.join(narrationDir, f)));
  if (missing.length === 0) return;
  console.log(`\n🎵 声音素材缺失 ${missing.length} 个,自动重跑 gen-sfx.py ...`);
  try {
    execSync(
      `${process.env.PYTHON || "python"} scripts/gen-sfx.py`,
      {
        stdio: "inherit",
        cwd: process.cwd(),
        env: { ...process.env, VIDEO_PROJECT_ROOT: root, PYTHONIOENCODING: "utf-8" },
      },
    );
    console.log(`✅ 声音素材已再生成为 ${narrationDir}`);
  } catch (error) {
    // 不阻断渲染:视频若显式 sfx:{enabled:false} 或未引用缺失文件仍可出片,
    // 引用了缺失文件的会在 Remotion 取 staticFile 时大声报错(好过静默无声明)。
    console.error(`\n⚠️ gen-sfx.py 失败(引用缺失文件的音频层会渲染报错):`, error.message);
  }
  // 默认 BGM 是外部曲,gen-sfx 不产:从 skill 持久副本恢复(render.ts 位于
  // remotion/scripts/,assets 在 ../../scripts/video/assets/)
  const bgmDest = path.join(narrationDir, DEFAULT_BGM_FILE);
  if (!fs.existsSync(bgmDest)) {
    const bgmSrc = path.resolve(__dirname, "../../scripts/video/assets", DEFAULT_BGM_FILE);
    if (fs.existsSync(bgmSrc)) {
      fs.copyFileSync(bgmSrc, bgmDest);
      console.log(`✅ 默认 BGM 已从 skill assets 副本恢复: ${bgmDest}`);
    } else {
      console.error(`\n⚠️ 默认 BGM ${DEFAULT_BGM_FILE} 缺失且 skill assets 无副本(主仓 data/bgm-library 台账有人工恢复直链)`);
    }
  }
}

console.log(`\n🎬 渲染视频: ${videoId}`);
console.log(`📁 输出文件: ${outputPath}\n`);

async function main() {
  // 配置按需加载：渲染前重新同步内容视频注册表（缺失/新增自动增删）
  await syncContentVideos();

  try {
    fs.mkdirSync(outputDir, { recursive: true });
    // 声音层素材自检(缺失自动 gen-sfx.py 重生成),先于渲染
    ensureSfxAssets(projectRoot);
    // 本机 GL 环境不稳（EGL/CVDisplayLink 报错）导致渲染器随机卡死：
    // --gl=angle（Metal 加速）+ 单并发可稳定跑完；swiftshader 软件渲染是兜底
    // （2026-08-10 实测：并发 >1 在 angle/swiftshader 下都会卡首帧）。
    execSync(
      `remotion render ${entryPoint} ${videoId} ${outputPath} --concurrency=1 --gl=angle --timeout=120000`,
      {
        stdio: "inherit",
        cwd: process.cwd(),
      },
    );
    console.log(`\n✅ 渲染完成: ${outputPath}`);
  } catch (error) {
    console.error(`\n❌ 渲染失败:`, error.message);
    process.exit(1);
  }

  // 渲染成功后自动生成封面到视频同目录（.video-generation/build/<videoId>/<videoId>_cover.png）
  // PYTHON 环境变量指定解释器（Makefile 已传 Python311 绝对路径，内置 playwright）
  try {
    execSync(
      `${process.env.PYTHON || "python"} -m scripts.video.cover_video --slug ${videoId}`,
      {
        stdio: "inherit",
        cwd: projectRoot,
        env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      },
    );
    console.log(`\n✅ 封面已生成到: ${outputDir}/${videoId}_cover.png`);
  } catch (error) {
    console.error(`\n⚠️ 封面生成失败（可稍后手动补: make video-cover slug=${videoId}）:`, error.message);
  }
}

main();
