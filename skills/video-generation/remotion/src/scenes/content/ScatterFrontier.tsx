import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * ScatterFrontier - 成本 vs 通过率散点图（动效：点逐个飞入 + 前沿线生长扫描）。
 *
 * 视觉：
 * - 坐标轴先画出（横轴成本 / 纵轴通过率）
 * - 散点按 delay 逐个从中心飞入落位，Pi 点带发光
 * - 性价比前沿虚线从左上往右下生长，带 dashoffset 扫描
 * - 标注卡片（全场最高分 / GLM 价格）延迟浮现
 */

interface Point {
  x: number; // 0-1 归一化（成本）
  y: number; // 0-1 归一化（通过率）
  label?: string;
  kind: "pi" | "rival" | "other";
  delay: number;
}

interface ScatterFrontierProps {
  title: string;
  xAxisLabel: string;
  yAxisLabel: string;
  frontierNote?: string;
  points: Point[];
  badges?: { text: string; sub?: string; at: [number, number]; delay: number }[];
}

const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

const ScatterFrontier: React.FC<ScatterFrontierProps> = ({
  title,
  xAxisLabel,
  yAxisLabel,
  frontierNote,
  points,
  badges = [],
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 画布区域（留出字幕安全带）
  const L = 300, R = 1750, T = 200, B = 830;
  const W = R - L, H = B - T;

  const axisProgress = easeOut(frame / 30);

  // 前沿线：从 (0.05, 0.98) 到 (0.95, 0.15)（归一化坐标）
  const fx0 = 0.06, fy0 = 0.98, fx1 = 0.94, fy1 = 0.14;
  const frontierDelay = 60;
  const frontierT = easeOut((frame - frontierDelay) / 45);
  const fxEnd = fx0 + (fx1 - fx0) * frontierT;
  const fyEnd = fy0 + (fy1 - fy0) * frontierT;
  const x0 = L + fx0 * W, y0 = B - fy0 * H;
  const x1 = L + fxEnd * W, y1 = B - fyEnd * H;

  const dashOffset = -frame * 1.2; // 扫描流动

  const toPx = (p: Point) => ({ px: L + p.x * W, py: B - p.y * H });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background, padding: 0 }}>
      {/* 标题 */}
      <div
        style={{
          position: "absolute", left: 120, top: 70, right: 200,
          fontSize: 54, fontWeight: 800, color: theme.colors.text,
          fontFamily: theme.fonts.chinese,
          opacity: easeOut(frame / 20),
          transform: `translateY(${(1 - easeOut(frame / 20)) * 24}px)`,
        }}
      >
        {title}
      </div>

      {/* 纵轴 */}
      <div style={{ position: "absolute", left: L - 10, top: T - 40, width: 2 * axisProgress, height: H + 60, background: `linear-gradient(${theme.colors.textMuted}, transparent)`, transformOrigin: "top left" }} />
      <div style={{ position: "absolute", left: L, top: T - 40, width: 2, height: (H + 60) * axisProgress, background: theme.colors.textMuted }} />
      {/* 横轴 */}
      <div style={{ position: "absolute", left: L - 10, top: B + 20, width: W * axisProgress, height: 2, background: theme.colors.textMuted }} />
      <div style={{ position: "absolute", left: L - 30, top: T - 100, fontSize: 30, color: theme.colors.textMuted, fontFamily: theme.fonts.chinese, opacity: axisProgress }}>{yAxisLabel}</div>
      <div style={{ position: "absolute", left: R - 200, top: B + 40, fontSize: 30, color: theme.colors.textMuted, fontFamily: theme.fonts.chinese, opacity: axisProgress }}>{xAxisLabel}</div>

      {/* 前沿线 */}
      <svg style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, pointerEvents: "none" }}>
        <line x1={x0} y1={y0} x2={x1} y2={y1}
          stroke={theme.colors.accent} strokeWidth={4}
          strokeDasharray="16 12" strokeDashoffset={dashOffset}
          opacity={0.9} />
      </svg>
      {frontierNote && frontierT > 0.9 ? (
        <div style={{ position: "absolute", left: x0 + 460, top: y0 + 210, fontSize: 28, color: theme.colors.accent, fontFamily: theme.fonts.chinese, opacity: easeOut((frame - frontierDelay - 45) / 20) }}>
          {frontierNote}
        </div>
      ) : null}

      {/* 散点 */}
      {points.map((p, i) => {
        const t = easeOut((frame - p.delay) / 24);
        if (t <= 0) return null;
        const { px, py } = toPx(p);
        const isPi = p.kind === "pi";
        const size = isPi ? 26 : 20;
        const color = isPi ? theme.colors.accent : p.kind === "rival" ? theme.colors.text : theme.colors.textMuted;
        const pop = 1 + 0.6 * (1 - t); // 落位回弹
        return (
          <div key={i} style={{ position: "absolute", left: px - (size * pop) / 2, top: py - (size * pop) / 2 }}>
            {isPi ? (
              <div style={{
                width: size * pop * 2.2, height: size * pop * 2.2, borderRadius: "50%",
                position: "absolute", left: -size * pop * 0.6, top: -size * pop * 0.6,
                background: `radial-gradient(circle, ${theme.colors.accent}55 0%, transparent 70%)`,
              }} />
            ) : null}
            <div style={{
              width: size * pop, height: size * pop, borderRadius: "50%",
              background: isPi ? theme.colors.accent : theme.colors.background,
              border: `3px solid ${color}`,
              boxShadow: isPi ? `0 0 24px ${theme.colors.accent}aa` : "none",
            }} />
            {p.label ? (
              <div style={{
                position: "absolute", left: size + 10, top: -14, whiteSpace: "nowrap",
                fontSize: 26, color: isPi ? theme.colors.accent : theme.colors.textMuted,
                fontFamily: theme.fonts.mono, opacity: t,
              }}>{p.label}</div>
            ) : null}
          </div>
        );
      })}

      {/* 标注卡片 */}
      {badges.map((b, i) => {
        const t = easeOut((frame - b.delay) / 20);
        if (t <= 0) return null;
        return (
          <div key={i} style={{
            position: "absolute", left: b.at[0], top: b.at[1],
            padding: "18px 28px", borderRadius: 14,
            background: "rgba(10,25,41,0.92)",
            border: `2px solid ${theme.colors.accent}66`,
            boxShadow: `0 0 40px ${theme.colors.accent}33`,
            opacity: t, transform: `translateY(${(1 - t) * 18}px) scale(${0.92 + 0.08 * t})`,
          }}>
            <div style={{ fontSize: 32, fontWeight: 700, color: theme.colors.text, fontFamily: theme.fonts.chinese }}>{b.text}</div>
            {b.sub ? <div style={{ fontSize: 24, color: theme.colors.textMuted, fontFamily: theme.fonts.chinese, marginTop: 6 }}>{b.sub}</div> : null}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

registerScene("ScatterFrontier", ScatterFrontier);
