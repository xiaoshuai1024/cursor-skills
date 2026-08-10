import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { TimedLayer } from "../../primitives/TimedLayer";

/**
 * ParallelPipeline - 双路并行（扁平流程图,去 3D）。
 * 左路(accent)/右路(success)两列节点逐个亮起,中心分流点脉冲。
 * 内容全部可配,默认值保留视觉验收主题(向后兼容)。
 */

interface Props {
  leftBranches: string[];
  rightBranches: string[];
  /** 场景标题（默认视觉验收旧标题） */
  header?: string;
  /** 分流点中心文字（默认 "380页"） */
  centerLabel?: string;
  leftTitle?: string;
  rightTitle?: string;
  /** 底部结论条（默认视觉验收旧结论） */
  bottomText?: string;
}

const ParallelPipeline: React.FC<Props> = ({ leftBranches, rightBranches, header, centerLabel, leftTitle, rightTitle, bottomText }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const nodeInterval = 40;

  const RenderColumn: React.FC<{
    title: string;
    color: string;
    branches: string[];
    baseFrame: number;
    align: "left" | "right";
  }> = ({ title, color, branches, baseFrame, align }) => (
    <div style={{ width: "44%" }}>
      <TimedLayer startFrame={baseFrame} duration={440}>
        <div style={{
          color, fontSize: 24, fontFamily: theme.fonts.chinese, fontWeight: 700,
          marginBottom: 16, textAlign: align === "right" ? "right" : "left",
        }}>
          {title}
        </div>
      </TimedLayer>
      {branches.map((label, i) => {
        const startF = baseFrame + 15 + i * nodeInterval;
        const active = frame >= startF;
        const opacity = active ? 1 : 0.25;
        return (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 12, marginBottom: 14,
            opacity, flexDirection: align === "right" ? "row-reverse" : "row",
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              backgroundColor: active ? `${color}25` : "transparent",
              border: `2px solid ${active ? color : theme.colors.textMuted}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              color, fontSize: 16, fontFamily: theme.fonts.mono, fontWeight: 700,
              boxShadow: active ? `0 0 16px ${color}60` : "none",
            }}>
              {i + 1}
            </div>
            <div style={{
              flex: 1, padding: "10px 16px",
              backgroundColor: active ? `${color}12` : "transparent",
              border: `1px solid ${active ? `${color}40` : `${theme.colors.textMuted}20`}`,
              borderRadius: 8,
              color: theme.colors.text, fontSize: 17, fontFamily: theme.fonts.chinese,
              textAlign: align === "right" ? "right" : "left",
            }}>
              {label}
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <TimedLayer startFrame={0} duration={600}>
        <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 40 }}>
          <div style={{ color: theme.colors.text, fontSize: 32, fontFamily: theme.fonts.chinese }}>
            {header ?? "并行验收 Pipeline · 380 页全覆盖"}
          </div>
        </AbsoluteFill>
      </TimedLayer>

      {/* 分流点 */}
      <div style={{ position: "absolute", left: "50%", top: "32%", transform: "translate(-50%,-50%)", zIndex: 2 }}>
        <div style={{
          width: 70, height: 70, borderRadius: "50%",
          backgroundColor: theme.colors.accent,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "#fff", fontSize: 16, fontFamily: theme.fonts.chinese, fontWeight: 700,
          boxShadow: `0 0 ${20 + Math.sin(frame * 0.08) * 8}px ${theme.colors.accent}`,
          transform: `scale(${1 + Math.sin(frame * 0.06) * 0.05})`,
        }}>
          {centerLabel ?? "380页"}
        </div>
      </div>

      {/* 左右两列 */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingTop: 80 }}>
        <div style={{ display: "flex", gap: 60, width: "84%", justifyContent: "space-between" }}>
          <RenderColumn title={leftTitle ?? "新功能 → 像素 diff"} color={theme.colors.accent} branches={leftBranches} baseFrame={10} align="left" />
          <RenderColumn title={rightTitle ?? "老功能 → vision + 审计"} color={theme.colors.success} branches={rightBranches} baseFrame={25} align="right" />
        </div>
      </AbsoluteFill>

      {/* 底部结果 */}
      <TimedLayer startFrame={300} duration={230}>
        <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 200 }}>
          <div style={{
            padding: "12px 28px", borderRadius: 8,
            backgroundColor: `${theme.colors.success}15`, border: `1px solid ${theme.colors.success}40`,
            color: theme.colors.text, fontSize: 18, fontFamily: theme.fonts.chinese,
          }}>
            {bottomText ?? "机器跑 2 小时 + 人审 30 分钟疑点 = 一个版本全覆盖"}
          </div>
        </AbsoluteFill>
      </TimedLayer>
    </AbsoluteFill>
  );
};

registerScene("ParallelPipeline", ParallelPipeline);
