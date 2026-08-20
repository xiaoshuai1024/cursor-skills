import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

/**
 * GrainOverlay - 胶片颗粒。
 *
 * 借鉴 HyperFrames 的 grain-overlay(纯 CSS 10 帧 keyframes 位移抖动):
 * SVG feTurbulence 噪点纹理做 data URI,位移按 frame%10 循环(确定性),
 * 轻微抖动产生胶片感,降低纯色背景的塑料感。
 *
 * Props:
 * - opacity: 颗粒强度,默认 0.06
 * - jitter: 位移抖动 px,默认 4
 */

const TURBULENCE_SVG = (seed: number) => {
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>
<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch' seed='${seed}'/></filter>
<rect width='240' height='240' filter='url(#n)'/>
</svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}")`;
};

interface GrainOverlayProps {
  opacity?: number;
  jitter?: number;
}

export const GrainOverlay: React.FC<GrainOverlayProps> = ({
  opacity = 0.06,
  jitter = 4,
}) => {
  const frame = useCurrentFrame();

  // 10 帧循环位移(与 HyperFrames grain 的 10 帧 keyframes 对齐)
  const seed = frame % 10;
  const tex = useMemo(() => TURBULENCE_SVG(seed), [seed]);
  const dx = (seed % 5) - 2;
  const dy = (Math.floor(seed / 5) - 1) * 2;

  return (
    <AbsoluteFill
      style={{
        backgroundImage: tex,
        backgroundSize: "240px 240px",
        transform: `translate(${dx * (jitter / 4)}px, ${dy * (jitter / 4)}px)`,
        opacity,
        pointerEvents: "none",
        mixBlendMode: "overlay",
      }}
    />
  );
};
