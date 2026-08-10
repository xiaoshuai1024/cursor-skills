import { Config } from "@remotion/cli/config";
import path from "node:path";
import fs from "node:fs";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// 本机无 Remotion 自带 Chromium 时，优先复用系统 Chrome（macOS 兼容兜底）
const SYSTEM_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
if (fs.existsSync(SYSTEM_CHROME) && !process.env.REMOTION_DISABLE_SYSTEM_CHROME) {
  Config.setBrowserExecutable(SYSTEM_CHROME);
}

/** 从 cwd 向上找项目根（hugo.toml / .git 标记），定位 video-generation。 */
function findProjectRoot(start: string): string {
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
const outputRoot = path.join(projectRoot, "video-generation");

// Remotion public 目录 = 口播 mp3（video-generation/narration/）
Config.setPublicDir(path.resolve(outputRoot, "narration"));

// webpack alias：
//   @videos     → 内容视频实例（config.ts + narration.ts），在项目根 video-generation/remotion-videos/
//   @skill-src  → skill 内 core/primitives/scenes 框架（remotion/src/）
Config.overrideWebpackConfig((config) => {
  config.resolve = config.resolve || {};
  config.resolve.alias = {
    ...(config.resolve.alias || {}),
    "@videos": path.resolve(outputRoot, "remotion-videos"),
    "@skill-src": path.resolve(process.cwd(), "src"),
  };
  return config;
});
