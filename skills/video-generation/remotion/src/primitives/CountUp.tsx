import React, { useMemo } from "react";
import { useCurrentFrame } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * CountUp - 数字滚动(预烘焙帧表 + 落地脉冲)。
 *
 * 借鉴 HyperFrames 的 count-up 预烘焙帧表手法:sine.inOut 缓动按帧预生成
 * 文本数组(不每帧算 Math),seek 完全确定;落地帧 back.out 脉冲缩放。
 * 小数位保留(8.9 不显示成 9,对齐 DataReveal 的经验)。
 *
 * Props:
 * - end: 目标值
 * - start: 起始值,默认 0
 * - decimals: 小数位,默认取 end 的小数位
 * - durationInFrames: 滚动时长,默认 30
 * - startFrame: 开始帧(相对场景),默认 0
 * - suffix: 后缀("%" / "万" / "K" 等)
 * - fontSize / color
 */

const easeInOutSine = (t: number) => -(Math.cos(Math.PI * t) - 1) / 2;
const easeOutBack = (t: number) => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};

interface CountUpProps {
  end: number;
  start?: number;
  decimals?: number;
  durationInFrames?: number;
  startFrame?: number;
  suffix?: string;
  fontSize?: number;
  color?: string;
}

export const CountUp: React.FC<CountUpProps> = ({
  end,
  start = 0,
  decimals,
  durationInFrames = 30,
  startFrame = 0,
  suffix = "",
  fontSize = 120,
  color,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = color ?? theme.colors.accent;
  const d = decimals ?? String(end).split(".")[1]?.length ?? 0;

  // 预烘焙帧表:每帧的显示文本(含千分位),滚动窗口外是首/尾值
  const table = useMemo(() => {
    const arr: string[] = [];
    for (let i = 0; i <= durationInFrames; i++) {
      const t = i / durationInFrames;
      const eased = easeInOutSine(t);
      const v = start + (end - start) * eased;
      arr.push(v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }));
    }
    return arr;
  }, [end, start, durationInFrames, d]);

  const rel = frame - startFrame;
  const idx = Math.max(0, Math.min(table.length - 1, rel));
  const display = table[idx];

  // 落地脉冲:滚动结束后 12 帧内 scale 1.15→1(back.out)
  const settleT = Math.max(0, rel - durationInFrames);
  const pulse = settleT < 12 ? easeOutBack(1 - settleT / 12) : 1;

  return (
    <div
      style={{
        fontSize,
        fontWeight: 900,
        color: c,
        fontFamily: theme.fonts.mono,
        textShadow: `0 0 40px ${c}80`,
        lineHeight: 1,
        transform: `scale(${pulse})`,
        display: "inline-block",
      }}
    >
      {display}
      {suffix}
    </div>
  );
};
