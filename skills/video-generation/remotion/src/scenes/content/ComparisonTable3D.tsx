import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { TimedLayer } from "../../primitives/TimedLayer";

/**
 * ComparisonTable3D - 两条路对照表（清晰扁平,去过度 3D）。
 * 表格行逐行淡入,左右列用蓝/绿边框区分。表头用 headers props（默认视觉验收旧标题）。
 */

interface Props {
  headers: string[];
  rows: Array<{ label: string; left: string; right: string }>;
}

const ComparisonTable3D: React.FC<Props> = ({ headers, rows }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <TimedLayer startFrame={0} duration={500}>
        <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 50 }}>
          <div style={{ color: theme.colors.text, fontSize: 32, fontFamily: theme.fonts.chinese }}>
            两条路 · 对照
          </div>
        </AbsoluteFill>
      </TimedLayer>

      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{ width: 1200 }}>
          {/* 表头（内容驱动，默认视觉验收旧标题） */}
          <div style={{ display: "flex", marginBottom: 4 }}>
            <Cell w={240} bg={`${theme.colors.highlight}30`} border={theme.colors.accent} bold>{headers[0] ?? "维度"}</Cell>
            <Cell w={480} bg={`${theme.colors.accent}20`} border={theme.colors.accent} bold color={theme.colors.accent}>{headers[1] ?? "新功能 · 像素比对"}</Cell>
            <Cell w={480} bg={`${theme.colors.success}15`} border={theme.colors.success} bold color={theme.colors.success}>{headers[2] ?? "老功能 · vision + 审计"}</Cell>
          </div>
          {/* 数据行逐行淡入 */}
          {rows.map((row, i) => {
            const startF = 30 + i * 20;
            const opacity = frame >= startF ? Math.min(1, (frame - startF) / 12) : 0;
            const ty = frame >= startF ? 0 : 15;
            return (
              <div key={i} style={{ display: "flex", marginBottom: 2, opacity, transform: `translateY(${ty}px)` }}>
                <Cell w={240} bg={`${theme.colors.highlight}10`} border={`${theme.colors.textMuted}30`} bold>{row.label}</Cell>
                <Cell w={480} bg={`${theme.colors.accent}08`} border={`${theme.colors.textMuted}20`}>{row.left}</Cell>
                <Cell w={480} bg={`${theme.colors.success}08`} border={`${theme.colors.textMuted}20`}>{row.right}</Cell>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Cell: React.FC<{
  children: React.ReactNode;
  w: number;
  bg: string;
  border: string;
  bold?: boolean;
  color?: string;
}> = ({ children, w, bg, border, bold, color }) => {
  const theme = getCurrentTheme();
  return (
    <div style={{
      width: w, minHeight: 52,
      backgroundColor: bg,
      border: `1px solid ${border}`,
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "8px 12px", textAlign: "center",
      color: color ?? theme.colors.text,
      fontSize: 17, fontFamily: theme.fonts.chinese,
      fontWeight: bold ? 700 : 400, lineHeight: 1.3,
    }}>
      {children}
    </div>
  );
};

registerScene("ComparisonTable3D", ComparisonTable3D);
