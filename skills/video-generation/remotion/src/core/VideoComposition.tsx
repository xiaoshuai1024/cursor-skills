import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig, Audio, staticFile } from "remotion";
import type { SfxConfig, VideoConfig } from "./types";
import { DEFAULTS, DEFAULT_SFX, DEFAULT_MASCOT, mergeTheme } from "./types";
import { setCurrentTheme, getCurrentTheme } from "./theme";
import { SubtitleOverlay } from "./SubtitleOverlay";
import { TechBackground } from "../primitives/TechBackground";
import { MascotCompanion } from "../primitives/MascotCompanion";
import { sceneRegistry } from "../scenes/registry";
import TransitionFrame from "../transitions/TransitionFrame";
import { BGM_MOOD_FILES, type BgmMood } from "./sound-points";

/**
 * SoundLayer - 声音层(合成内原生渲染,非成片后混音):
 *
 * - BGM 整片循环垫底(淡入 1s / 尾部淡出 2s),音量低于口播人声
 * - 三档 SFX 全部 <Sequence from={帧号}> 定位(禁 wall-clock):
 *   开场音 @0;转场音按场景头稀疏触发(每 transitionEvery 个场景一次,
 *   场景 0 只放开场音不叠转场);提问音走 questionFrames 手工点帧
 * - config.sfx 未声明时由调用方套 DEFAULT_SFX——新视频零配置即有 BGM + 音效
 *
 * 设计依据 skill references/sound-design.md(参考片程序化拆解):
 * 能量靠 BGM 不靠音效,SFX 是稀疏点缀。
 */
const SoundLayer: React.FC<{
  sfx: SfxConfig;
  sceneStarts: number[];
  totalFrames: number;
}> = ({ sfx, sceneStarts, totalFrames }) => {
  const sfxVolume = sfx.volume ?? 0.4;
  const bgmVolume = sfx.bgmVolume ?? 0.35;
  const every = Math.max(1, sfx.transitionEvery ?? 4);
  // 提前收窄类型:map 回调里 TS 无法保持对 sfx.transition 等属性的 undefined 收窄
  const openingSfx = sfx.opening ?? null;
  const transitionSfx = sfx.transition ?? null;
  const questionSfx = sfx.question ?? null;
  const emphasisSfx = sfx.emphasis ?? null;
  const revealSfx = sfx.reveal ?? null;
  // BGM 文件:显式 bgm 优先,其次 bgmMood 情绪映射(无效 mood 忽略)
  const bgmFile = sfx.bgm ?? (sfx.bgmMood ? BGM_MOOD_FILES[sfx.bgmMood as BgmMood] : undefined) ?? null;

  const transitionAt = transitionSfx
    ? sceneStarts.filter((_, i) => i > 0 && i % every === 0)
    : [];

  // BGM 音量按帧计算:头部 60 帧淡入,尾部 120 帧淡出
  const bgmVolumeAt = React.useCallback(
    (frame: number) => {
      const fadeIn = Math.min(1, frame / 60);
      const fadeOut = Math.min(1, Math.max(0, totalFrames - frame) / 120);
      return bgmVolume * fadeIn * fadeOut;
    },
    [bgmVolume, totalFrames],
  );

  // 「一个 wav × 一组帧」的定点音效渲染
  const points = (
    file: string | null,
    frames: number[] | undefined,
    prefix: string,
  ) =>
    file
      ? (frames ?? []).map((start, i) => (
          <Sequence key={`${prefix}-${i}`} from={start}>
            <Audio src={staticFile(file)} volume={sfxVolume} />
          </Sequence>
        ))
      : [];

  return (
    <>
      {bgmFile && <Audio src={staticFile(bgmFile)} loop volume={bgmVolumeAt} />}
      {openingSfx && (
        <Sequence from={0}>
          <Audio src={staticFile(openingSfx)} volume={sfxVolume} />
        </Sequence>
      )}
      {transitionSfx &&
        transitionAt.map((start, i) => (
          <Sequence key={`sfx-transition-${i}`} from={start}>
            <Audio src={staticFile(transitionSfx)} volume={sfxVolume} />
          </Sequence>
        ))}
      {points(questionSfx, sfx.questionFrames, "sfx-question")}
      {points(emphasisSfx, sfx.emphasisFrames, "sfx-emphasis")}
      {points(revealSfx, sfx.revealFrames, "sfx-reveal")}
    </>
  );
};

/**
 * 通用 VideoComposition:根据 VideoConfig 装配场景 + 转场 + 字幕 + 音频。
 *
 * 设计:
 * - 启动时根据 config.themeOverrides 计算当前 theme(单例)
 * - 按 scenes 数组顺序,用 <Sequence> 在时间轴上依次装配
 * - 每个 scene 通过 sceneRegistry[type] 分发到对应组件,
 *   外包 TransitionFrame 做场景头尾转场(rotate3d 复刻旧 Scene3DFrame 行为,
 *   per-scene transitionType 可逐场景覆盖,15 种见 transitions/TransitionFrame.tsx)
 * - 叠加 SubtitleOverlay(根据 config.subtitles)
 * - 叠加口播 <Audio>(config.audioPath,音量 audioVolume 默认 0.6)
 * - 叠加声音层 <SoundLayer>(BGM + SFX;config.sfx 未声明时自动套默认值)
 */
export const VideoComposition: React.FC<{ config: VideoConfig }> = ({
  config,
}) => {
  const videoConfig = useVideoConfig();

  // 初始化 theme(只在第一帧做,避免每帧重算)
  const theme = React.useMemo(
    () =>
      mergeTheme(
        {
          colors: {
            background: "#0a0e1a",
            backgroundAlt: "#0a1929",
            accent: "#00d9ff",
            text: "#ffffff",
            textMuted: "#94a3b8",
            error: "#dc2626",
            success: "#0f766e",
            highlight: "#dbeafe",
          },
          fonts: {
            chinese: '"Source Han Sans SC", "Noto Sans SC", sans-serif',
            english: '"Orbitron", sans-serif',
            mono: '"JetBrains Mono", monospace',
          },
        },
        config.themeOverrides,
      ),
    [config.themeOverrides],
  );

  // 在 render 期间同步设置主题单例（模块级变量，非 setState）。
  // 不能只放 useEffect：Remotion 每帧独立渲染，场景组件在 render 阶段
  // 就 getCurrentTheme()，effect 在 commit 后才执行，会拿到上一次主题。
  // 这里 render 时先 set，场景组件必然拿到正确主题。
  setCurrentTheme(theme);
  React.useEffect(() => {
    setCurrentTheme(theme);
  }, [theme]);

  // 转场默认开启:未配置时 16 帧(约 0.27s,与存量视频一致);显式 0 = 硬切
  const transitionFrames = config.transitionFrames ?? 16;
  const globalTransitionType = config.transitionType ?? "rotate3d";

  // 声音层:未声明套默认(自动 BGM/音效),声明了按字段浅覆盖;enabled=false 关闭
  const sfxEnabled = config.sfx?.enabled !== false;
  const sfx: SfxConfig = { ...DEFAULT_SFX, ...(config.sfx ?? {}) };

  // 形象伴随层:未声明套默认(右下角常驻 + 表情自动推断);enabled=false 关闭
  const mascotEnabled = config.mascot?.enabled !== false;
  const mascot = { ...DEFAULT_MASCOT, ...(config.mascot ?? {}) };

  // 预计算每个 scene 的起始帧(装配 + 转场音定位共用)
  const sceneStarts: number[] = [];
  let cumulativeFrames = 0;
  for (const scene of config.scenes) {
    sceneStarts.push(cumulativeFrames);
    cumulativeFrames += scene.durationInFrames;
  }

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      {/* 全局科技感背景层（所有场景共享，场景透明露出） */}
      <TechBackground />
      {config.scenes.map((scene, index) => {
        const SceneComponent = sceneRegistry[scene.type];
        const startFrame = sceneStarts[index];

        if (!SceneComponent) {
          console.warn(`[VideoComposition] Unknown scene type: ${scene.type}`);
          return null;
        }

        return (
          <Sequence
            key={`${scene.type}-${index}`}
            from={startFrame}
            durationInFrames={scene.durationInFrames}
            name={scene.type}
          >
            <TransitionFrame
              transitionType={scene.transitionType ?? globalTransitionType}
              transitionFrames={transitionFrames}
              durationInFrames={scene.durationInFrames}
            >
              <SceneComponent {...(scene.props as any)} />
            </TransitionFrame>
          </Sequence>
        );
      })}

      {/* 形象伴随层:场景之上、字幕之下(字幕永远最上);强调帧透传驱动 point 姿态 */}
      {mascotEnabled && (
        <MascotCompanion
          subtitles={config.subtitles ?? []}
          height={mascot.height ?? 240}
          position={mascot.position ?? "bottom-right"}
          moodTimeline={mascot.moodTimeline}
          autoMood={mascot.autoMood}
          reactToSegments={mascot.reactToSegments}
          emphasisFrames={sfxEnabled ? sfx.emphasisFrames : undefined}
        />
      )}

      {config.subtitles && config.subtitles.length > 0 && (
        <SubtitleOverlay subtitles={config.subtitles} />
      )}

      {config.audioPath && (
        <Audio src={staticFile(config.audioPath)} volume={config.audioVolume ?? 0.6} />
      )}

      {sfxEnabled && (
        <SoundLayer sfx={sfx} sceneStarts={sceneStarts} totalFrames={videoConfig.durationInFrames} />
      )}
    </AbsoluteFill>
  );
}
