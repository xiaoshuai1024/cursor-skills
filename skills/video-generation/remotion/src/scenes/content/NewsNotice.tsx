import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * NewsNotice - 新闻速报的官方通知/邮件要点面板（真实素材风格）。
 *
 * 视觉：居中一个「邮件/公告」卡片，顶部来源栏（速报标签 + 来源方时间），
 * 主题行，正文要点逐条三态揭示（done 白字 / active 主色发光 / future 暗淡），
 * 底部来源注脚。帧级驱动（useCurrentFrame），每条要点在 points[].start 帧点亮，
 * 由 config 从 narration 时间戳精确计算（音画对齐）。
 *
 * Props:
 * - label: 左上角速报标签（默认 "速报 · 官方邮件"）
 * - subject: 邮件/公告主题行
 * - meta: 来源方 · 时间（右上角）
 * - points: [{ text, start }] 要点 + 点亮帧（局部帧）
 * - footer: 底部来源注脚
 */

interface NoticePoint {
  text: string;
  /** 点亮帧（场景局部帧）——由 config 从 narration 时间戳算好传入 */
  start: number;
}
interface NewsNoticeProps {
  label?: string;
  subject: string;
  meta?: string;
  points: NoticePoint[];
  footer?: string;
}

const fadeAt = (frame: number, start: number, dur = 20) =>
  Math.max(0, Math.min(1, (frame - start) / dur));

const NewsNotice: React.FC<NewsNoticeProps> = ({
  label = "速报 · 官方邮件",
  subject,
  meta,
  points,
  footer,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = theme.colors.accent;

  // 当前已点亮的要点数（最后一个点亮的是 active，其余 done）
  let revealedCount = 0;
  for (const p of points) {
    if (frame >= p.start) revealedCount++;
    else break;
  }
  const activeIndex = revealedCount - 1;

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      justifyContent: "center",
      alignItems: "center",
      paddingBottom: 60,   /* 字幕安全带避让 */
    }}>
      {/* 邮件卡片 */}
      <div style={{
        width: 1280,
        minHeight: 600,
        padding: "44px 56px 40px",
        borderRadius: 20,
        background: `linear-gradient(165deg, ${theme.colors.backgroundAlt}ee, ${theme.colors.background}d9)`,
        border: `1.5px solid ${c}55`,
        boxShadow: `0 0 60px ${c}25, 0 30px 70px rgba(0,0,0,0.55)`,
        display: "flex",
        flexDirection: "column",
      }}>
        {/* 顶栏：速报标签 + 来源时间 */}
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 22,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{
              display: "inline-block",
              width: 12, height: 12, borderRadius: "50%",
              backgroundColor: theme.colors.error,
              boxShadow: `0 0 12px ${theme.colors.error}`,
            }} />
            <span style={{
              color: theme.colors.error,
              fontSize: 17,
              fontFamily: theme.fonts.mono,
              fontWeight: 800,
              letterSpacing: 2,
            }}>
              {label}
            </span>
          </div>
          {meta && (
            <span style={{
              color: theme.colors.textMuted,
              fontSize: 16,
              fontFamily: theme.fonts.mono,
            }}>
              {meta}
            </span>
          )}
        </div>

        {/* 分隔线 */}
        <div style={{
          height: 1,
          background: `linear-gradient(to right, transparent, ${c}66, transparent)`,
          marginBottom: 30,
          opacity: fadeAt(frame, 0),
        }} />

        {/* 主题行 */}
        <div style={{ opacity: fadeAt(frame, 0, 25) }}>
          <div style={{
            color: theme.colors.text,
            fontSize: 42,
            fontFamily: theme.fonts.chinese,
            fontWeight: 900,
            letterSpacing: 1,
            textAlign: "center",
          }}>
            {subject}
          </div>
          <div style={{
            width: 160, height: 3, margin: "16px auto 0",
            background: `linear-gradient(to right, transparent, ${c}, transparent)`,
            boxShadow: `0 0 12px ${c}`,
          }} />
        </div>

        {/* 要点列表（三态揭示） */}
        <div style={{
          marginTop: 44,
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}>
          {points.map((p, i) => {
            const active = i === activeIndex && revealedCount > 0;
            const revealed = frame >= p.start;
            const op = fadeAt(p.start);
            return (
              <div key={i} style={{
                display: "flex",
                alignItems: "center",
                gap: 22,
                opacity: op,
                transform: `translateY(${(1 - op) * 18}px)`,
              }}>
                {/* 序号徽标 */}
                <div style={{
                  width: 52, height: 52, borderRadius: 12, flexShrink: 0,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 22,
                  fontFamily: theme.fonts.mono,
                  fontWeight: 900,
                  color: active ? theme.colors.background : (revealed ? c : theme.colors.textMuted),
                  backgroundColor: active
                    ? c
                    : revealed ? `${c}22` : `${theme.colors.textMuted}14`,
                  border: `2px solid ${active ? c : revealed ? `${c}66` : `${theme.colors.textMuted}33`}`,
                  boxShadow: active ? `0 0 22px ${c}80` : "none",
                }}>
                  {String(i + 1).padStart(2, "0")}
                </div>
                {/* 要点文字 */}
                <div style={{
                  color: active ? c : (revealed ? theme.colors.text : theme.colors.textMuted),
                  fontSize: 30,
                  fontFamily: theme.fonts.chinese,
                  fontWeight: active ? 900 : 600,
                  textShadow: active ? `0 0 20px ${c}90` : "none",
                  letterSpacing: 1,
                }}>
                  {p.text}
                </div>
              </div>
            );
          })}
        </div>

        {/* 来源注脚 */}
        {footer && (
          <div style={{
            marginTop: "auto",
            paddingTop: 26,
            borderTop: `1px solid ${theme.colors.textMuted}30`,
            color: theme.colors.textMuted,
            fontSize: 16,
            fontFamily: theme.fonts.mono,
            opacity: fadeAt(frame, 0, 30),
          }}>
            {footer}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

registerScene("NewsNotice", NewsNotice);
