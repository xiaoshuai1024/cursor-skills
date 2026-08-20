import React from "react";
import { useCurrentFrame } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * ShimmerText - 流光扫过字面。
 *
 * 借鉴 HyperFrames 的 shimmer-sweep:渐变亮带从 -20% 扫到 120%,
 * mix-blend-mode: overlay 叠加在文字上,产生金属漆面反光感。
 *
 * Props:
 * - text: 显示文字
 * - startFrame: 流光开始帧,默认 0
 * - durationInFrames: 单次扫过时长,默认 30
 * - repeat: 循环扫,默认 false(一次后静止)
 * - fontSize / color
 */

interface ShimmerTextProps {
  text: string;
  startFrame?: number;
  durationInFrames?: number;
  repeat?: boolean;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
}

export const ShimmerText: React.FC<ShimmerTextProps> = ({
  text,
  startFrame = 0,
  durationInFrames = 30,
  repeat = false,
  fontSize = 100,
  color,
  fontWeight = 900,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = color ?? theme.colors.text;

  // 流光位置:-20% → 120%(repeat 时取模循环)
  const rel = Math.max(0, frame - startFrame);
  const p = repeat ? (rel % durationInFrames) / durationInFrames : Math.min(1, rel / durationInFrames);
  const pos = -20 + p * 140;

  return (
    <div
      style={{
        position: "relative",
        display: "inline-block",
        fontSize,
        fontWeight,
        color: c,
        fontFamily: theme.fonts.chinese,
        lineHeight: 1.2,
      }}
    >
      {text}
      {/* 流光带:40% 宽渐变,overlay 混合只提亮不遮字 */}
      <div
        style={{
          position: "absolute",
          top: "-10%",
          bottom: "-10%",
          left: `${pos}%`,
          width: "40%",
          pointerEvents: "none",
          background:
            "linear-gradient(90deg, transparent, rgba(255,255,255,0.55), transparent)",
          mixBlendMode: "overlay",
        }}
      />
    </div>
  );
};
