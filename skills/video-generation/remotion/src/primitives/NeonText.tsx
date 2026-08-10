import React from "react";
import { getCurrentTheme } from "../core/theme";

/**
 * NeonText - 2D 霓虹发光文字。
 *
 * 视觉:氖青色(可配)文字,边缘向外扩散的光晕,在深色背景下醒目。
 * 用法:标题、强调文字、CTA。
 *
 * 实现:CSS text-shadow 多层叠加模拟发光。
 */

interface NeonTextProps {
  text: string;
  color?: string;
  fontSize?: number;
  glowIntensity?: number;
  fontFamily?: "english" | "chinese" | "mono";
  fontWeight?: number;
}

export const NeonText: React.FC<NeonTextProps> = ({
  text,
  color,
  fontSize = 80,
  glowIntensity = 1,
  fontFamily = "english",
  fontWeight = 900,
}) => {
  const theme = getCurrentTheme();
  const c = color ?? theme.colors.accent;

  // 多层 text-shadow 模拟发光:近处亮 + 远处散
  const shadow = [
    `0 0 ${10 * glowIntensity}px ${c}`,
    `0 0 ${20 * glowIntensity}px ${c}`,
    `0 0 ${40 * glowIntensity}px ${c}80`,
    `0 0 ${80 * glowIntensity}px ${c}40`,
  ].join(", ");

  return (
    <div
      style={{
        color: c,
        fontSize,
        fontFamily: theme.fonts[fontFamily],
        fontWeight,
        textShadow: shadow,
        letterSpacing: 2,
        lineHeight: 1.2,
      }}
    >
      {text}
    </div>
  );
};
