import React, { useMemo } from "react";
import { useCurrentFrame } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * KineticText - 逐词 slam 入场 / 槽内换词。
 *
 * 借鉴 HyperFrames 的 kinetic typography(caption-kinetic-slam / kinetic-type-swap),
 * 翻译成帧驱动:每词在 startFrame + i*frameGap 帧开始,back.out 缓动砸入。
 * swap 模式:旧词上甩出(yPercent -112)、新词从下方 +112 进入,重叠 ~10% 帧。
 *
 * Props:
 * - words: slam 模式逐词入场;swap 模式为 [旧词, 新词]
 * - mode: "slam" | "swap",默认 "slam"
 * - startFrame: 动画开始帧(相对场景),默认 0
 * - frameGap: 每词间隔帧,默认 6
 * - accentWords: 高亮词(用 theme.accent 着色),默认 []
 * - fontSize / fontWeight / color
 */

const easeOutBack = (t: number) => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};
const easeInQuad = (t: number) => t * t;

interface KineticTextProps {
  words: string[];
  mode?: "slam" | "swap";
  startFrame?: number;
  frameGap?: number;
  accentWords?: string[];
  fontSize?: number;
  fontWeight?: number;
  color?: string;
}

export const KineticText: React.FC<KineticTextProps> = ({
  words,
  mode = "slam",
  startFrame = 0,
  frameGap = 6,
  accentWords = [],
  fontSize = 88,
  fontWeight = 900,
  color,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = color ?? theme.colors.text;

  // slam:每词独立的进入进度(窗口 12 帧,back.out)
  const wordStyles = useMemo(() => {
    if (mode === "swap") return [];
    return words.map((_, i) => {
      const t0 = startFrame + i * frameGap;
      const t = Math.min(1, Math.max(0, (frame - t0) / 12));
      const eased = easeOutBack(t);
      return {
        opacity: t >= 1 ? 1 : t,
        transform: `translateY(${(1 - eased) * -120}px) scale(${0.92 + 0.08 * eased})`,
      };
    });
  }, [words, mode, startFrame, frameGap, frame]);

  if (mode === "swap") {
    // swap:旧词上甩出(前 60% 帧),新词从下方进入(后 60%,重叠 20%)
    const total = 48;
    const p = Math.min(1, Math.max(0, (frame - startFrame) / total));
    const oldOut = p < 0.6 ? easeInQuad(p / 0.6) : 1;
    const newIn = p > 0.4 ? easeOutBack(Math.min(1, (p - 0.4) / 0.6)) : 0;
    const [oldWord = "", newWord = ""] = words;
    return (
      <div
        style={{
          position: "relative",
          height: fontSize * 1.3,
          overflow: "hidden",
          fontSize,
          fontWeight,
          color: c,
          fontFamily: theme.fonts.chinese,
          lineHeight: 1.3,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            transform: `translateY(${-112 * oldOut}%)`,
            opacity: 1 - oldOut * 0.9,
          }}
        >
          {oldWord}
        </div>
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            transform: `translateY(${112 * (1 - newIn)}%)`,
            opacity: newIn,
          }}
        >
          {newWord}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: "0.25em",
        fontSize,
        fontWeight,
        fontFamily: theme.fonts.chinese,
        lineHeight: 1.3,
      }}
    >
      {words.map((w, i) => {
        const s = wordStyles[i] ?? {};
        const isAccent = accentWords.includes(w);
        return (
          <span key={i} style={{ ...s, color: isAccent ? theme.colors.accent : c }}>
            {w}
          </span>
        );
      })}
    </div>
  );
};
