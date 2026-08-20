import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * AuroraBackground - 无缝循环极光背景。
 *
 * 借鉴 HyperFrames 的 aurora-drift:3 个超大模糊色块按相位漂移,
 * 相位 = 2π * (frame % loopFrames) / loopFrames → t=0 与 t=loopFrames
 * 姿态严格一致,循环无缝。作为场景底层背景(TechBackground 的替代/叠加)。
 *
 * Props:
 * - loopFrames: 循环周期帧数,默认 = 视频总帧数(整片一个周期)
 * - colors: 色块颜色,默认 [accent, 紫, 蓝]
 * - blur: 模糊半径 px,默认 70
 * - opacity: 色块透明度,默认 0.3
 * - drift: 漂移幅度 %,默认 32
 */

interface AuroraBackgroundProps {
  loopFrames?: number;
  colors?: string[];
  blur?: number;
  opacity?: number;
  drift?: number;
}

export const AuroraBackground: React.FC<AuroraBackgroundProps> = ({
  loopFrames,
  colors,
  blur = 70,
  opacity = 0.3,
  drift = 32,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const theme = getCurrentTheme();
  const loop = loopFrames ?? durationInFrames;
  const cols = colors ?? [theme.colors.accent, "#a78bfa", "#3b82f6"];

  // 相位 0~2π,循环周期内单调推进(2π 归一化保证无缝)
  const phase = useMemo(() => (2 * Math.PI * (frame % loop)) / loop, [frame, loop]);

  // 3 个色块:频率不同(慢/中/快),相位互差 2π/3,位置 = 圆心 + 漂移 * 三角函数
  const blobs = useMemo(
    () =>
      [0, 1, 2].map((i) => {
        const p = phase + (i * 2 * Math.PI) / 3;
        const speed = [0.5, 0.8, 1.1][i];
        return {
          left: `${50 + drift * Math.sin(p * speed) * Math.cos(p * 0.7)}%`,
          top: `${50 + drift * Math.cos(p * speed * 1.3) * Math.sin(p * 0.9)}%`,
          size: 900 + i * 220,
          color: cols[i % cols.length],
        };
      }),
    [phase, drift, cols],
  );

  return (
    <AbsoluteFill style={{ overflow: "hidden", pointerEvents: "none" }}>
      {blobs.map((b, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: b.left,
            top: b.top,
            width: b.size,
            height: b.size,
            marginLeft: -b.size / 2,
            marginTop: -b.size / 2,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${b.color} 0%, transparent 70%)`,
            opacity,
            filter: `blur(${blur}px)`,
            mixBlendMode: "screen",
          }}
        />
      ))}
    </AbsoluteFill>
  );
};
