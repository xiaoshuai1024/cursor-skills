import React from "react";
import { useCurrentFrame } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * HighlightBand - 标记带(background-size 生长)。
 *
 * 借鉴 HyperFrames 的 caption-highlight(新闻编辑风招牌手法):
 * 文字下方的强调色带从 0% 生长到 100%,box-decoration-break: clone 支持跨行,
 * 生长完保持。用于观点句 / 结论句的视觉强调。
 *
 * Props:
 * - text: 高亮文本(可含多个标记带,用 | 分隔)
 * - startFrame / durationInFrames: 生长窗口
 * - bandColor: 标记带颜色,默认 theme.accent
 * - textColor: 文字颜色,默认 theme.text
 * - fontSize / padding
 */

interface HighlightBandProps {
  text: string;
  startFrame?: number;
  durationInFrames?: number;
  bandColor?: string;
  textColor?: string;
  fontSize?: number;
  padding?: string;
  rounded?: boolean;
}

export const HighlightBand: React.FC<HighlightBandProps> = ({
  text,
  startFrame = 0,
  durationInFrames = 24,
  bandColor,
  textColor,
  fontSize = 72,
  padding = "0 0.15em",
  rounded = true,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const band = bandColor ?? theme.colors.accent;
  const tc = textColor ?? theme.colors.text;

  const rel = Math.max(0, frame - startFrame);
  const grow = Math.min(1, rel / durationInFrames);

  return (
    <span
      style={{
        fontSize,
        fontWeight: 900,
        color: tc,
        fontFamily: theme.fonts.chinese,
        lineHeight: 1.6,
        // background-size 从 0 生长到 100%(从左到右)
        backgroundImage: `linear-gradient(${band}, ${band})`,
        backgroundSize: `${grow * 100}% 0.32em`,
        backgroundRepeat: "no-repeat",
        backgroundPosition: "left 0 bottom 0.08em",
        borderRadius: rounded ? "0.16em" : 0,
        boxDecorationBreak: "clone",
        WebkitBoxDecorationBreak: "clone",
        padding,
      }}
    >
      {text}
    </span>
  );
};
