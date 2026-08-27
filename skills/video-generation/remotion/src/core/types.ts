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
  /** 该场景的转场类型(覆盖全局 transitionType)。可选 15 种,见 transitions/TransitionFrame.tsx */
  transitionType?: string;
}

/** Theme token:控制视觉风格的最小变量集 */
export interface Theme {
  colors: {
    /** 主背景色,默认深空黑 #0a0e1a */
    background: string;
    /** 次背景色,用于渐变 / 暗蓝过渡,默认 #0a1929 */
    backgroundAlt: string;
    /** 主强调色(品牌主青),默认 #22d3ee(与 palette.py SSOT 对齐) */
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
/**
 * 声音层配置:BGM 垫底 + 三档 SFX(开场/转场/提问)。
 * 设计规范见 skill references/sound-design.md——能量靠 BGM 不靠音效,
 * SFX 稀疏点缀、全部用 <Sequence from={帧号}> 定位,音量低于口播人声。
 */
export interface SfxConfig {
  /** 关闭整个声音层(BGM + SFX 都不放),默认开启 */
  enabled?: boolean;
  /** 开场音文件名(相对 public/,即 video-generation/narration/)。默认 sfx-opening-chime.wav */
  opening?: string;
  /** 转场音文件名。默认 sfx-transition-swoosh.wav */
  transition?: string;
  /** 转场音稀疏度:每 N 个场景响一次(场景 0 只放开场音,不算转场)。默认 4 */
  transitionEvery?: number;
  /** 提问音文件名。仅当 questionFrames 提供时生效 */
  question?: string;
  /** 提问音绝对帧号(手工点帧,全片 2~4 个为宜) */
  questionFrames?: number[];
  /** SFX 音量(0~1)。口播片 0.4,不抢人声 */
  volume?: number;
  /** BGM 文件名。默认 bgm-bed.wav(gen-sfx.py 生成,calm 轨别名) */
  bgm?: string;
  /** BGM 情绪档(与 bgm 二选一,mood 自动映射文件名;见 core/sound-points.ts) */
  bgmMood?: string;
  /** BGM 音量(0~1)。口播片 0.3~0.4,无口播快剪可到 0.6。默认 0.35 */
  bgmVolume?: number;
  /** 强调音文件名(关键词/结论落地,配 emphasisFrames) */
  emphasis?: string;
  /** 强调音绝对帧号(用 keywordFrames(U, [...]) 自动算) */
  emphasisFrames?: number[];
  /** 揭示音文件名(数据/榜单/揭秘出现,配 revealFrames) */
  reveal?: string;
  /** 揭示音绝对帧号 */
  revealFrames?: number[];
}

/** 声音层默认值:config.sfx 未声明时自动套用,新视频零配置即有 BGM + 音效 */
export const DEFAULT_SFX: SfxConfig = {
  enabled: true,
  opening: "sfx-opening-chime.wav",
  transition: "sfx-transition-swoosh.wav",
  transitionEvery: 4,
  volume: 0.4,
  bgm: "bgm-bed.wav",
  bgmVolume: 0.35,
};

/** 形象表情/姿态(与封面 mascot.svg 同一语言);类型载体在 MascotFigure */
export type { MascotMood, MascotPose } from "../primitives/MascotFigure";

/**
 * 形象伴随层配置:终端小子全片常驻 + 随口播时间轴随动。
 * 对齐 DEFAULT_SFX 先例——config.mascot 未声明时自动套默认(即默认启用)。
 */
export interface MascotConfig {
  /** 关闭整个形象层。默认 true */
  enabled?: boolean;
  /** 形象高度 px(宽按 320/470 自动),默认 240(左侧净空区标定,openspec video-mascot-placement;
   *  右侧旧标定 210 不迁移:240 抢戏判定源于右下与内容贴脸,左侧无此冲突;场景左下有核心内容可降 210) */
  height?: number;
  /** 贴角位置,默认 bottom-left——四平台信息流右侧竖排互动栏遮挡右缘(抖音头像实测),左下为一致净空角 */
  position?: "bottom-right" | "bottom-left";
  /** 手工表情点帧(优先于自动推断;点后到下一手工点间自动推断挂起) */
  moodTimeline?: Array<{ frame: number; mood: import("../primitives/MascotFigure").MascotMood }>;
  /** 按字幕关键词自动切表情。默认 true;false 则全程 smile 只随动 */
  autoMood?: boolean;
  /** 字幕段边界微反应(点头/摆头/微跳轮换)。默认 true */
  reactToSegments?: boolean;
}

/** 形象层默认值:未声明 config.mascot 即左下角 240px 常驻,表情自动推断(2026-08-25 换边+放大) */
export const DEFAULT_MASCOT: MascotConfig = {
  enabled: true,
  height: 240,
  position: "bottom-left",
  autoMood: true,
  reactToSegments: true,
};

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
  /** 口播音量(0~1),默认 0.6 */
  audioVolume?: number;
  /** 声音层(BGM + SFX)。未声明时自动套用 DEFAULT_SFX,新视频零配置即有 BGM/音效 */
  sfx?: SfxConfig;
  /** 形象伴随层(终端小子随动)。未声明时自动套用 DEFAULT_MASCOT,零配置即有形象 */
  mascot?: MascotConfig;
  /** 场景间 3D 过渡帧数(默认 0 = 硬切)。>0 时每个场景翻入+翻出(rotateY+scale+perspective) */
  transitionFrames?: number;
  /** 全局转场类型(可被 SceneConfig.transitionType 逐场景覆盖),默认 rotate3d */
  transitionType?: string;
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
