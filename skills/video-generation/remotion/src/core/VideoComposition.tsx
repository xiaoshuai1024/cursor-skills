import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig, Audio, staticFile, useCurrentFrame } from "remotion";
import type { VideoConfig } from "./types";
import { DEFAULTS, mergeTheme } from "./types";
import { setCurrentTheme, getCurrentTheme } from "./theme";
import { SubtitleOverlay } from "./SubtitleOverlay";
import { TechBackground } from "../primitives/TechBackground";
import { sceneRegistry } from "../scenes/registry";

/**
 * Scene3DFrame - 场景 3D 翻入/翻出过渡容器。
 *
 * 视觉:每个场景开场从 rotateY(60°) 翻入,结束翻出到 rotateY(-60°),
 * 配合 perspective 制造"从深处翻出/翻入"的 3D 过渡感。
 * 默认 transitionFrames=0 时不做任何变换(完全向后兼容)。
 */
const Scene3DFrame: React.FC<{
  transitionFrames: number;
  durationInFrames: number;
  children: React.ReactNode;
}> = ({ transitionFrames, durationInFrames, children }) => {
  const frame = useCurrentFrame();

  if (transitionFrames <= 0) return <>{children}</>;

  const enterT = Math.min(1, frame / transitionFrames);
  const exitT = Math.min(1, (durationInFrames - frame) / transitionFrames);
  const enterEased = 1 - Math.pow(1 - enterT, 3);   // ease-out 翻入
  const exitEased = 1 - Math.pow(1 - exitT, 3);     // ease-out 翻出

  // 翻入:rotateY 60°→0, scale 0.9→1, opacity 0→1
  // 翻出:rotateY 0→-60°, scale 1→0.9, opacity 1→0
  const rotY = 60 * (1 - enterEased) - 60 * (1 - exitEased);
  const scale = 0.9 + 0.1 * enterEased - 0.1 * exitEased;
  const opacity = Math.min(enterEased, exitEased) * 0.999;

  return (
    <AbsoluteFill
      style={{
        perspective: 1200,
      }}
    >
      <AbsoluteFill
        style={{
          transform: `rotateY(${rotY}deg) scale(${scale})`,
          transformStyle: "preserve-3d",
          opacity,
          backfaceVisibility: "hidden",
        }}
      >
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * 通用 VideoComposition:根据 VideoConfig 装配场景 + 字幕 + 音频。
 *
 * 设计:
 * - 启动时根据 config.themeOverrides 计算当前 theme(单例)
 * - 按 scenes 数组顺序,用 <Sequence> 在时间轴上依次装配
 * - 每个 scene 通过 sceneRegistry[type] 分发到对应组件
 * - 叠加 SubtitleOverlay(根据 config.subtitles)
 * - 叠加 <Audio>(如果 config.audioPath 存在)
 */
export const VideoComposition: React.FC<{ config: VideoConfig }> = ({
  config,
}) => {
  const videoConfig = useVideoConfig();

  // 初始化 theme(只在第一帧做,避免每帧重算)
  const theme = React.useMemo(
    () => mergeTheme(
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

  const transitionFrames = config.transitionFrames ?? 0;

  // 累计装配 scenes,计算每个 scene 的起始帧
  let cumulativeFrames = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      {/* 全局科技感背景层（所有场景共享，场景透明露出） */}
      <TechBackground />
      {config.scenes.map((scene, index) => {
        const SceneComponent = sceneRegistry[scene.type];
        const startFrame = cumulativeFrames;
        cumulativeFrames += scene.durationInFrames;

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
            <Scene3DFrame
              transitionFrames={transitionFrames}
              durationInFrames={scene.durationInFrames}
            >
              <SceneComponent {...(scene.props as any)} />
            </Scene3DFrame>
          </Sequence>
        );
      })}

      {config.subtitles && config.subtitles.length > 0 && (
        <SubtitleOverlay subtitles={config.subtitles} />
      )}

      {config.audioPath && (
        <Audio src={staticFile(config.audioPath)} volume={0.6} />
      )}
    </AbsoluteFill>
  );
};
