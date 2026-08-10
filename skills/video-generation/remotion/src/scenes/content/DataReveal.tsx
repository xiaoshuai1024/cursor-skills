import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * DataReveal - 关键数字 3D 揭示。
 *
 * 视觉:画面中央大幅数字从 0 递增到目标值,带标签。
 * 用途:强调文章中的关键数据点(380 页 / 407→4 / 1% 等)。
 *
 * Props:
 * - number: 目标数值
 * - label: 数字说明文字
 * - color: 数字颜色(默认从 theme.accent 读)
 * - durationInFrames: 数字增长动画时长,默认 120(2s @ 60fps)
 */

interface DataRevealProps {
  number: number;
  label: string;
  color?: string;
  durationInFrames?: number;
}

const DataReveal: React.FC<DataRevealProps> = ({
  number,
  label,
  color,
  durationInFrames = 120,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = color ?? theme.colors.accent;

  // 数字递增(前 durationInFrames 帧做 easing)。保留小数位（8.9 不显示成 9）。
  const progress = Math.min(1, frame / durationInFrames);
  const eased = 1 - Math.pow(1 - progress, 3);
  const decimals = String(number).split(".")[1]?.length ?? 0;
  const displayNum = (number * eased).toFixed(decimals);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
      }}
    >
      {/* 数字 */}
      <div
        style={{
          fontSize: 220,
          fontWeight: 900,
          color: c,
          fontFamily: theme.fonts.mono,
          textShadow: `0 0 60px ${c}80, 0 0 120px ${c}40`,
          lineHeight: 1,
          transition: "none",
        }}
      >
        {displayNum}
      </div>

      {/* 标签(稍晚淡入) */}
      <div
        style={{
          fontSize: 48,
          color: theme.colors.textMuted,
          fontFamily: theme.fonts.chinese,
          marginTop: 30,
          opacity: Math.min(1, Math.max(0, (frame - 30) / 20)),
        }}
      >
        {label}
      </div>
    </AbsoluteFill>
  );
};

registerScene("DataReveal", DataReveal);
