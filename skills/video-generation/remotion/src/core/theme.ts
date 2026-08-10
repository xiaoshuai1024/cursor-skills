import type { Theme } from "./types";

/**
 * 默认 Theme token——抽象科技风。
 *
 * 设计原则:
 * - 单主色(氖青 #00d9ff)+ 深色背景 + 白字
 * - 配色克制,避免"AI 味"的彩虹配色
 * - 字体选 OFL 开源许可(思源黑体 / Orbitron / JetBrains Mono)
 *
 * 视频可通过 VideoConfig.themeOverrides 局部覆盖。
 */
export const defaultTheme: Theme = {
  colors: {
    background: "#0a0e1a", // 深空黑
    backgroundAlt: "#0a1929", // 暗蓝(渐变/过渡)
    accent: "#00d9ff", // 氖青(主强调)
    text: "#ffffff",
    textMuted: "#94a3b8", // 弱化灰
    error: "#dc2626", // 差异/幻觉标注
    success: "#0f766e", // 审计通过绿
    highlight: "#dbeafe", // 面板背景
  },
  fonts: {
    chinese: '"Source Han Sans SC", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
    english: '"Orbitron", "Rajdhani", sans-serif',
    mono: '"JetBrains Mono", "Fira Code", monospace',
  },
};

/** 当前 theme(单例,VideoComposition 初始化时通过 mergeTheme 计算) */
let currentTheme: Theme = defaultTheme;

export function getCurrentTheme(): Theme {
  return currentTheme;
}

export function setCurrentTheme(theme: Theme): void {
  currentTheme = theme;
}
