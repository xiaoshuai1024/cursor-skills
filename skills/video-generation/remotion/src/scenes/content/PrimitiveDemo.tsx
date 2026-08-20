import React from "react";
import type { ComponentType } from "react";
import { AbsoluteFill } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { KineticText } from "../../primitives/KineticText";
import { CountUp } from "../../primitives/CountUp";
import { ShimmerText } from "../../primitives/ShimmerText";
import { GlitchText } from "../../primitives/GlitchText";
import { HighlightBand } from "../../primitives/HighlightBand";
import { AuroraBackground } from "../../primitives/AuroraBackground";
import { GrainOverlay } from "../../primitives/GrainOverlay";

/**
 * PrimitiveDemo - 动画原语演示场景。
 *
 * 把 7 个文本/背景动画原语搬上演示台:顶部 mono 小标签 + 中间原语本体。
 * - aurora / grain 是全屏背景原语(铺满场景,标题叠在上层);
 * - 其余是文本原语(居中演示,标签在上)。
 * - primitive 组件 props 经 primitiveProps 透传,演示卡自行决定各原语的
 *   时长 / 循环 / 强度,保证动画窗口肉眼可见(替代早期静态 ChapterCard 占位)。
 */

type PrimitiveKind =
  | "kinetic" | "countup" | "shimmer" | "glitch"
  | "highlight" | "aurora" | "grain";

const PRIMITIVE_COMPONENTS: Record<PrimitiveKind, ComponentType<any>> = {
  kinetic: KineticText,
  countup: CountUp,
  shimmer: ShimmerText,
  glitch: GlitchText,
  highlight: HighlightBand,
  aurora: AuroraBackground,
  grain: GrainOverlay,
};

/** 全屏背景类:铺满整场景,标题叠在上层 */
const FULL_BLEED: PrimitiveKind[] = ["aurora", "grain"];

interface PrimitiveDemoProps {
  primitive: PrimitiveKind;
  /** 顶部小标签(mono + accent),如 "COUNT UP" */
  label?: string;
  /** 全屏背景原语的演示标题(如 "极光背景") */
  title?: string;
  /** 透传给 primitive 组件的 props */
  primitiveProps?: Record<string, unknown>;
}

const PrimitiveDemo: React.FC<PrimitiveDemoProps> = ({
  primitive,
  label,
  title,
  primitiveProps = {},
}) => {
  const theme = getCurrentTheme();
  const Primitive = PRIMITIVE_COMPONENTS[primitive];
  const fullBleed = FULL_BLEED.includes(primitive);

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        backgroundColor: theme.colors.background,
      }}
    >
      {fullBleed ? <Primitive {...primitiveProps} /> : null}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          paddingBottom: 220,
        }}
      >
        {label ? (
          <div
            style={{
              fontSize: 22,
              fontFamily: theme.fonts.mono,
              letterSpacing: 6,
              color: theme.colors.accent,
              marginBottom: 48,
            }}
          >
            {label}
          </div>
        ) : null}
        {fullBleed ? (
          title ? (
            <div
              style={{
                fontSize: 110,
                fontWeight: 900,
                color: theme.colors.text,
                fontFamily: theme.fonts.chinese,
                letterSpacing: 2,
                textShadow: `0 0 60px ${theme.colors.accent}55`,
              }}
            >
              {title}
            </div>
          ) : null
        ) : (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              flex: 1,
              width: "100%",
            }}
          >
            <Primitive {...primitiveProps} />
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

registerScene("PrimitiveDemo", PrimitiveDemo);
