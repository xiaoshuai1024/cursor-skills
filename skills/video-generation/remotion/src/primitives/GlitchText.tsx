import React from "react";
import { useCurrentFrame } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * GlitchText - RGB 故障字。
 *
 * 借鉴 HyperFrames 的 rgb-glitch-text:红/青幽灵副本 + 抖动撕裂。
 * 确定性实现:每 4 帧一个姿态(伪随机,frame 播种,禁 Math.random),
 * 主层抖动 translate + 两层色差副本 ±3px,撕裂用 clip-path 随机条带。
 *
 * Props:
 * - text: 显示文字
 * - intensity: 故障强度 0~1,默认 1
 * - startFrame: 开始帧,默认 0
 * - durationInFrames: 故障持续帧数(之后静止为正常文字),默认 40
 * - fontSize / color
 */

/** 确定性伪随机(与 TransitionFrame 同 seed 约定):0~1 */
const seededRand = (seed: number) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
};

interface GlitchTextProps {
  text: string;
  intensity?: number;
  startFrame?: number;
  durationInFrames?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
}

export const GlitchText: React.FC<GlitchTextProps> = ({
  text,
  intensity = 1,
  startFrame = 0,
  durationInFrames = 40,
  fontSize = 100,
  color,
  fontWeight = 900,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = color ?? theme.colors.text;

  const rel = frame - startFrame;
  const active = rel >= 0 && rel < durationInFrames;
  // 头部 8 帧 + 尾部 8 帧淡入淡出故障,中间全强度
  const fade = active
    ? Math.min(1, rel / 8, (durationInFrames - rel) / 8)
    : 0;
  const k = intensity * fade;

  const s = Math.floor(rel / 4) * 4;
  const dx = (seededRand(s) - 0.5) * 10 * k;
  const dy = (seededRand(s + 1) - 0.5) * 6 * k;
  const skew = (seededRand(s + 2) - 0.5) * 8 * k;
  const tearTop = seededRand(s + 3) * 55 + 15; // 撕裂条带位置 %

  const base: React.CSSProperties = {
    position: "absolute",
    inset: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize,
    fontWeight,
    fontFamily: theme.fonts.chinese,
    lineHeight: 1.2,
    whiteSpace: "nowrap",
  };

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      {/* 红 ghost(左偏) */}
      <div
        style={{
          ...base,
          color: "rgba(255,0,60,0.75)",
          transform: `translate(${-3 * k}px, ${dy}px) skewX(${skew}deg)`,
          opacity: k,
          clipPath: `inset(${tearTop}% 0 ${100 - tearTop - 12}% 0)`,
        }}
      >
        {text}
      </div>
      {/* 青 ghost(右偏) */}
      <div
        style={{
          ...base,
          color: "rgba(0,255,255,0.75)",
          transform: `translate(${3 * k}px, ${-dy}px) skewX(${-skew}deg)`,
          opacity: k,
          clipPath: `inset(${100 - tearTop - 8}% 0 ${tearTop - 4}% 0)`,
        }}
      >
        {text}
      </div>
      {/* 主层:轻微抖动 */}
      <div
        style={{
          ...base,
          position: "relative",
          color: c,
          transform: `translate(${dx}px, 0)`,
        }}
      >
        {text}
      </div>
    </div>
  );
};
