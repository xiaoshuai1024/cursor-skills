import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * Cover - 视频封面（信息密度高，抓注意力）。
 *
 * 布局：flex column 流，各部分用 opacity 淡入（占位不挤压，布局稳定不重叠）。
 * 节奏：标题(0s) → 论点(1.5s) → 大纲(3s 起逐条) → 数字(4.5s)。
 */

interface Stat {
  num: string;
  label: string;
  color: "error" | "success" | "accent";
}
interface CoverProps {
  title: string;
  subtitle: string;
  thesis: string;
  outline: string[];
  stats: Stat[];
  /** 左上角标文字（默认 "AI 模型速报"） */
  cornerLabel?: string;
}

const fadeAt = (frame: number, start: number, dur = 20) =>
  Math.max(0, Math.min(1, (frame - start) / dur));

const Cover: React.FC<CoverProps> = ({ title, subtitle, thesis, outline, stats, cornerLabel }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const statColor = (c: Stat["color"]) =>
    c === "error" ? theme.colors.error : c === "success" ? theme.colors.success : theme.colors.accent;

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      flexDirection: "column",
      justifyContent: "flex-start",
      alignItems: "center",
      padding: "80px 120px 220px",   /* 底部 220px 留字幕安全带 */
    }}>
      {/* 顶部装饰线 + 角标 */}
      <div style={{
        position: "absolute", top: 44, left: 120, right: 120, height: 2,
        background: `linear-gradient(to right, transparent, ${theme.colors.accent}, transparent)`,
        opacity: 0.5 * fadeAt(frame, 0),
      }} />
      <div style={{
        position: "absolute", top: 36, left: 120,
        color: theme.colors.accent, fontSize: 15, fontFamily: theme.fonts.mono, letterSpacing: 3,
        opacity: fadeAt(frame, 0),
      }}>
        {cornerLabel ?? "AI 模型速报"}
      </div>

      {/* 1. 标题 + 副标题 */}
      <div style={{ textAlign: "center", opacity: fadeAt(frame, 0, 30) }}>
        <div style={{
          color: theme.colors.text,
          fontSize: 68, fontFamily: theme.fonts.chinese, fontWeight: 900,
          lineHeight: 1.2, letterSpacing: 2,
          textShadow: `0 0 40px ${theme.colors.accent}40`,
        }}>
          {title}
        </div>
        <div style={{
          color: theme.colors.textMuted, fontSize: 28, fontFamily: theme.fonts.chinese,
          marginTop: 12,
        }}>
          {subtitle}
        </div>
      </div>

      {/* 2. 核心论点 */}
      <div style={{
        marginTop: 28, padding: "12px 36px",
        border: `2px solid ${theme.colors.accent}`,
        borderRadius: 10,
        backgroundColor: `${theme.colors.accent}15`,
        boxShadow: `0 0 30px ${theme.colors.accent}40`,
        opacity: fadeAt(frame, 60),
      }}>
        <span style={{ color: theme.colors.textMuted, fontSize: 16, fontFamily: theme.fonts.chinese, marginRight: 14 }}>
          核心看点
        </span>
        <span style={{
          color: theme.colors.accent, fontSize: 30, fontFamily: theme.fonts.chinese, fontWeight: 800,
          textShadow: `0 0 20px ${theme.colors.accent}`,
        }}>
          {thesis}
        </span>
      </div>

      {/* 3. 大纲 */}
      <div style={{ marginTop: 28, width: "100%", maxWidth: 1100 }}>
        {outline.map((item, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 18,
            marginBottom: 12,
            opacity: fadeAt(frame, 120 + i * 40),
          }}>
            <div style={{
              width: 40, height: 40, borderRadius: 8,
              backgroundColor: `${theme.colors.accent}25`,
              border: `2px solid ${theme.colors.accent}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: theme.colors.accent, fontSize: 18, fontFamily: theme.fonts.mono, fontWeight: 800,
              flexShrink: 0,
            }}>
              {i + 1}
            </div>
            <div style={{ color: theme.colors.text, fontSize: 24, fontFamily: theme.fonts.chinese }}>
              {item}
            </div>
          </div>
        ))}
      </div>

      {/* 4. 关键数字 */}
      <div style={{
        marginTop: 24, display: "flex", gap: 50, alignItems: "center",
        padding: "14px 44px",
        backgroundColor: `${theme.colors.backgroundAlt}80`,
        borderRadius: 12, border: `1px solid ${theme.colors.textMuted}30`,
        opacity: fadeAt(frame, 240),
      }}>
        {stats.map((s, i) => (
          <React.Fragment key={i}>
            {i > 0 && <div style={{ color: theme.colors.textMuted, fontSize: 28 }}>·</div>}
            <div style={{ textAlign: "center" }}>
              <div style={{
                color: statColor(s.color), fontSize: 48, fontFamily: theme.fonts.mono, fontWeight: 900,
                textShadow: `0 0 22px ${statColor(s.color)}`,
              }}>
                {s.num}
              </div>
              <div style={{ color: theme.colors.textMuted, fontSize: 14, fontFamily: theme.fonts.chinese }}>
                {s.label}
              </div>
            </div>
          </React.Fragment>
        ))}
      </div>
    </AbsoluteFill>
  );
};

registerScene("Cover", Cover);
