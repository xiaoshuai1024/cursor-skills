import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * TechBackground - 科技感透明背景（全局底层）。
 *
 * 视觉：电路板网格 + 交叉点节点 + 沿网格流动的光点 + 极淡代码字符。
 * 半透明叠加在场景内容之下，提升科幻感但不喧宾夺主。
 *
 * 性能：纯 SVG + CSS，不用 ThreeCanvas（背景纹理无需 3D）。
 */

// 伪随机（确定性，避免每帧抖动）
function seeded(i: number, seed: number): number {
  const x = Math.sin(i * 12.9898 + seed * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

const GRID = 64;           // 网格间距（px）
const FLOW_COUNT = 8;      // 流动光点数

export const TechBackground: React.FC = () => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 流动光点（沿水平网格线移动）
  const flowDots = useMemo(
    () => Array.from({ length: FLOW_COUNT }, (_, i) => {
      const row = Math.floor(seeded(i, 1) * 17);          // 0-16 行
      const speed = 0.5 + seeded(i, 2) * 1.2;              // px/帧
      const startX = seeded(i, 3) * 1920;
      const x = (startX + frame * speed) % (1920 + 200) - 100;
      const y = row * GRID + (GRID / 2);
      const opacity = 0.25 + Math.sin(frame * 0.05 + i) * 0.15;
      return { x, y, opacity };
    }),
    [frame],
  );

  // 代码字符点缀（极淡）
  const codeSnippets = useMemo(
    () => Array.from({ length: 14 }, (_, i) => ({
      x: seeded(i, 11) * 1880 + 20,
      y: seeded(i, 22) * 1060 + 20,
      txt: ["01", "10", "0x4F", "{ }", "</>", "&&", "||", "=>", "fn", "##"][i % 10],
      opacity: 0.08 + seeded(i, 33) * 0.08,
    })),
    [],
  );

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      {/* 电路板网格 */}
      <svg width="1920" height="1080" style={{ position: "absolute", inset: 0 }}>
        <defs>
          <pattern id="circuit-grid" width={GRID} height={GRID} patternUnits="userSpaceOnUse">
            <path d={`M ${GRID} 0 L 0 0 0 ${GRID}`} fill="none" stroke={theme.colors.accent} strokeWidth="0.8" opacity="0.35" />
            <circle cx="0" cy="0" r="2" fill={theme.colors.accent} opacity="0.45" />
          </pattern>
        </defs>
        <rect width="1920" height="1080" fill="url(#circuit-grid)" />

        {/* 电路线条（部分加粗的"走线"，模拟电路板布线） */}
        <g stroke={theme.colors.accent} strokeWidth="1.5" opacity="0.3" fill="none">
          <path d={`M 0 ${GRID * 3} L ${GRID * 6} ${GRID * 3} L ${GRID * 6} ${GRID * 7} L ${GRID * 14} ${GRID * 7}`} />
          <path d={`M ${GRID * 20} ${GRID * 2} L ${GRID * 20} ${GRID * 10} L ${GRID * 26} ${GRID * 10}`} />
          <path d={`M ${GRID * 10} ${GRID * 13} L ${GRID * 18} ${GRID * 13}`} />
          <path d={`M ${GRID * 2} ${GRID * 11} L ${GRID * 8} ${GRID * 11} L ${GRID * 8} ${GRID * 15}`} />
        </g>
        {/* 走线节点（焊点） */}
        <g fill={theme.colors.accent} opacity="0.5">
          <circle cx={GRID * 6} cy={GRID * 3} r="3.5" />
          <circle cx={GRID * 6} cy={GRID * 7} r="3.5" />
          <circle cx={GRID * 20} cy={GRID * 10} r="3.5" />
          <circle cx={GRID * 18} cy={GRID * 13} r="3.5" />
          <circle cx={GRID * 8} cy={GRID * 11} r="3.5" />
        </g>
      </svg>

      {/* 流动光点（沿网格移动，带拖尾发光） */}
      {flowDots.map((d, i) => (
        <div key={i} style={{
          position: "absolute",
          left: d.x, top: d.y,
          width: 5, height: 5, borderRadius: "50%",
          backgroundColor: theme.colors.accent,
          boxShadow: `0 0 10px ${theme.colors.accent}, 0 0 20px ${theme.colors.accent}, -24px 0 14px ${theme.colors.accent}70`,
          opacity: 0.4 + d.opacity,
        }} />
      ))}

      {/* 代码字符点缀 */}
      {codeSnippets.map((c, i) => (
        <span key={i} style={{
          position: "absolute",
          left: c.x, top: c.y,
          color: theme.colors.accent,
          fontFamily: "monospace",
          fontSize: 16,
          opacity: c.opacity * 3,
          userSelect: "none",
        }}>{c.txt}</span>
      ))}

      {/* 暗角（仅边缘轻微压暗，中心保持可见） */}
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse at center, transparent 55%, ${theme.colors.background}99 100%)`,
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};
