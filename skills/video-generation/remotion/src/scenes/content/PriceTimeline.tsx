import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * PriceTimeline - 调价时间线（2026 降价→涨价历史）。
 *
 * 视觉：左轨时间线，日期徽标 + 节点 + 右侧事件文案，逐条淡入上滑。
 * 最后一个里程碑可标红 highlight（如"宣布大幅涨价"）。
 * 帧级驱动，每条在 milestones[].start 帧点亮，由 config 从 narration 时间戳计算。
 */

interface Milestone {
  date: string;
  text: string;
  /** 点亮帧（场景局部帧） */
  start: number;
  /** 高亮里程碑（涨价事件，标红） */
  highlight?: boolean;
}
interface PriceTimelineProps {
  title: string;
  subtitle?: string;
  milestones: Milestone[];
  footer?: string;
}

const fadeAt = (frame: number, start: number, dur = 18) =>
  Math.max(0, Math.min(1, (frame - start) / dur));

const PriceTimeline: React.FC<PriceTimelineProps> = ({
  title,
  subtitle,
  milestones,
  footer,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = theme.colors.accent;
  const lineX = 210;   // 左侧轨道 x（徽标右缘、竖线所在）

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      justifyContent: "center",
      alignItems: "center",
      paddingBottom: 60,   /* 字幕安全带避让 */
    }}>
      <div style={{
        width: 1250,
        display: "flex",
        flexDirection: "column",
      }}>
        {/* 标题 */}
        <div style={{ textAlign: "center", marginBottom: 44, opacity: fadeAt(frame, 0, 25) }}>
          <div style={{
            color: theme.colors.text,
            fontSize: 44,
            fontFamily: theme.fonts.chinese,
            fontWeight: 900,
            letterSpacing: 2,
          }}>
            {title}
          </div>
          {subtitle && (
            <div style={{
              color: theme.colors.textMuted,
              fontSize: 18,
              fontFamily: theme.fonts.chinese,
              marginTop: 8,
            }}>
              {subtitle}
            </div>
          )}
          <div style={{
            width: 220, height: 3, margin: "14px auto 0",
            background: `linear-gradient(to right, transparent, ${c}, transparent)`,
            boxShadow: `0 0 12px ${c}`,
          }} />
        </div>

        {/* 时间线 */}
        <div style={{ position: "relative", paddingLeft: 0 }}>
          {/* 竖线（轨道） */}
          <div style={{
            position: "absolute",
            left: lineX - 2,
            top: 8, bottom: 8,
            width: 4,
            borderRadius: 2,
            background: `linear-gradient(to bottom, ${c}66, ${c}22)`,
          }} />
          {/* 里程碑 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 34 }}>
            {milestones.map((m, i) => {
              const op = fadeAt(m.start);
              const y = (1 - op) * 22;
              const col = m.highlight ? theme.colors.error : theme.colors.text;
              return (
                <div key={i} style={{
                  display: "flex",
                  alignItems: "center",
                  opacity: op,
                  transform: `translateY(${y}px)`,
                }}>
                  {/* 日期徽标 */}
                  <div style={{
                    width: lineX - 34,
                    textAlign: "right",
                    paddingRight: 24,
                    color: m.highlight ? theme.colors.error : theme.colors.textMuted,
                    fontSize: 22,
                    fontFamily: theme.fonts.mono,
                    fontWeight: 700,
                  }}>
                    {m.date}
                  </div>
                  {/* 节点 */}
                  <div style={{
                    position: "relative",
                    width: 20, height: 20, borderRadius: "50%",
                    backgroundColor: m.highlight ? theme.colors.error : c,
                    boxShadow: m.highlight
                      ? `0 0 18px ${theme.colors.error}`
                      : `0 0 14px ${c}80`,
                    marginLeft: 8,
                    flexShrink: 0,
                    zIndex: 1,
                  }} />
                  {/* 文案 */}
                  <div style={{
                    marginLeft: 30,
                    color: col,
                    fontSize: 28,
                    fontFamily: theme.fonts.chinese,
                    fontWeight: m.highlight ? 900 : 600,
                    textShadow: m.highlight ? `0 0 16px ${theme.colors.error}60` : "none",
                  }}>
                    {m.text}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 注脚 */}
        {footer && (
          <div style={{
            marginTop: 36,
            color: theme.colors.textMuted,
            fontSize: 16,
            fontFamily: theme.fonts.mono,
            textAlign: "center",
            opacity: fadeAt(frame, 0, 30),
          }}>
            {footer}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

registerScene("PriceTimeline", PriceTimeline);
