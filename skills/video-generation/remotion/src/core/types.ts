/**
 * 视频管线的类型定义。
 *
 * 设计原则:
 * - VideoConfig 描述"这个视频是什么",不关心"怎么渲染"
 * - SceneConfig 是"场景类型 + 该场景的 props",框架层做类型分发
 * - 所有场景 props 用 unknown 兜底,具体场景组件自己 assert
 */

/** 单条字幕:在 [startFrame, endFrame] 区间显示 text */
export interface SubtitleEntry {
  text: string;
  startFrame: number;
  endFrame: number;
}

/** 单个场景的配置:type 决定渲染哪个组件,props 是该场景需要的参数 */
export interface SceneConfig<P = unknown> {
  /** 场景类型标识,对应 scenes/ 目录下的组件。如 "HookTitle" / "NetworkGraph" */
  type: string;
  /** 场景专属 props,由具体场景组件定义 */
  props: P;
  /** 该场景在视频时间轴上占的帧数 */
  durationInFrames: number;
}

/** Theme token:控制视觉风格的最小变量集 */
export interface Theme {
  colors: {
    /** 主背景色,默认深空黑 #0a0e1a */
    background: string;
    /** 次背景色,用于渐变 / 暗蓝过渡,默认 #0a1929 */
    backgroundAlt: string;
    /** 主强调色(霓虹/氖青),默认 #00d9ff */
    accent: string;
    /** 主文字色,默认 #ffffff */
    text: string;
    /** 次文字色(弱化说明文字),默认 #94a3b8 */
    textMuted: string;
    /** 错误/差异标注色,默认 #dc2626 */
    error: string;
    /** 成功/通过色,默认 #0f766e */
    success: string;
    /** 高亮/面板背景色,默认 #dbeafe */
    highlight: string;
  };
  fonts: {
    /** 中文字体,默认 "Source Han Sans SC", "Noto Sans SC", sans-serif */
    chinese: string;
    /** 英文 / 数字字体,默认 "Orbitron", sans-serif */
    english: string;
    /** 等宽字体(代码 / 数字),默认 "JetBrains Mono", monospace */
    mono: string;
  };
}

/**
 * 完整视频配置。
 *
 * 一个视频 = 一个 VideoConfig。
 * 加新视频 = 在 videos/<new>/config.ts 导出一个 VideoConfig,不改框架。
 */
export interface VideoConfig {
  /** 视频唯一标识,用作 Remotion composition id 和输出文件名 */
  id: string;
  /** 视频标题(元数据,不影响渲染) */
  title: string;
  /** 输出宽度(像素),默认 1920 */
  width?: number;
  /** 输出高度(像素),默认 1080 */
  height?: number;
  /** 帧率,默认 60 */
  fps?: number;
  /** 场景序列,按数组顺序装配到时间轴 */
  scenes: SceneConfig[];
  /** 字幕序列,时间轴覆盖式显示 */
  subtitles?: SubtitleEntry[];
  /** 背景音乐路径(相对 public/ 或 videos/<id>/assets/) */
  audioPath?: string;
  /** 场景间 3D 过渡帧数(默认 0 = 硬切)。>0 时每个场景翻入+翻出(rotateY+scale+perspective) */
  transitionFrames?: number;
  /** 覆盖默认 theme token(实现风格多样性) */
  themeOverrides?: Partial<{
    colors: Partial<Theme["colors"]>;
    fonts: Partial<Theme["fonts"]>;
  }>;
}

/** 默认尺寸 / 帧率常量 */
export const DEFAULTS = {
  width: 1920,
  height: 1080,
  fps: 60,
} as const;

/**
 * 把 partial theme overrides 合并到 base theme 上。
 * 只做一层深合并(colors / fonts 内部浅合并),够用。
 */
export function mergeTheme(base: Theme, overrides?: VideoConfig["themeOverrides"]): Theme {
  if (!overrides) return base;
  return {
    colors: { ...base.colors, ...(overrides.colors ?? {}) },
    fonts: { ...base.fonts, ...(overrides.fonts ?? {}) },
  };
}
