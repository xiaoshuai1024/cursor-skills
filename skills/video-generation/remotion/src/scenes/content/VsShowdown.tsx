import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * VsShowdown - 左右分屏对决场景（VS 徽章对撞 + 要点逐条揭示）。
 *
 * 视觉：
 * - 左右两个玻璃面板从两侧滑入对撞，中央 VS 徽章带电光边框
 * - 两侧要点列表按 delay 逐条打字机式浮现
 * - 顶部标题 + 底部结论条（最后弹出）
 * - 左侧 = 官方重型（白灰），右侧 = Pi（主色发光）
 */

interface VsSide {
  name: string;
  tag: string;
  items: { text: string; delay: number }[];
}

interface VsShowdownProps {
  title: string;
  left: VsSide;
  right: VsSide;
  verdict?: string;
  verdictDelay?: number;
}

const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

const VsShowdown: React.FC<VsShowdownProps> = ({ title, left, right, verdict, verdictDelay = 130 }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  const slideL = easeOut(frame / 26);
  const slideR = easeOut(frame / 26);
  const vsT = easeOut((frame - 22) / 22);
  const vsPulse = 1 + 0.05 * Math.sin(frame / 12);

  const Side: React.FC<{ side: VsSide; from: "left" | "right"; accent: boolean }> = ({ side, from, accent }) => {
    const slide = from === "left" ? slideL : slideR;
    const dir = from === "left" ? -1 : 1;
    const color = accent ? theme.colors.accent : theme.colors.text;
    return (
      <div style={{
        position: "absolute", top: 260, width: 700,
        left: from === "left" ? 110 + (1 - slide) * dir * 260 : undefined,
        right: from === "right" ? 110 + (1 - slide) * dir * 260 : undefined,
        padding: "34px 38px", borderRadius: 20, minHeight: 560,
        background: accent ? "rgba(0,217,255,0.06)" : "rgba(148,163,184,0.06)",
        border: `2.5px solid ${accent ? theme.colors.accent + "99" : theme.colors.textMuted + "66"}`,
        boxShadow: accent ? `0 0 60px ${theme.colors.accent}22` : "none",
        opacity: slide,
      }}>
        <div style={{ fontSize: 46, fontWeight: 900, color, fontFamily: theme.fonts.chinese }}>{side.name}</div>
        <div style={{ fontSize: 24, color: theme.colors.textMuted, fontFamily: theme.fonts.chinese, marginTop: 6, marginBottom: 26 }}>{side.tag}</div>
        {side.items.map((it, i) => {
          const t = easeOut((frame - it.delay) / 20);
          if (t <= 0) return null;
          return (
            <div key={i} style={{
              display: "flex", alignItems: "flex-start", gap: 14,
              marginTop: 22, opacity: t,
              transform: `translateX(${(1 - t) * (from === "left" ? -30 : 30)}px)`,
            }}>
              <div style={{
                width: 12, height: 12, borderRadius: 3, marginTop: 12,
                background: accent ? theme.colors.accent : theme.colors.textMuted,
                boxShadow: accent ? `0 0 12px ${theme.colors.accent}` : "none",
                flexShrink: 0,
              }} />
              <div style={{ fontSize: 30, color: theme.colors.text, fontFamily: theme.fonts.chinese, lineHeight: 1.45 }}>{it.text}</div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 70, textAlign: "center",
        fontSize: 54, fontWeight: 800, color: theme.colors.text,
        fontFamily: theme.fonts.chinese, opacity: easeOut(frame / 16),
      }}>{title}</div>

      {/* 中缝电光 */}
      <div style={{ position: "absolute", left: 959, top: 240, width: 2, height: 620, background: `linear-gradient(transparent, ${theme.colors.accent}55, transparent)` }} />

      <Side side={left} from="left" accent={false} />
      <Side side={right} from="right" accent />

      {/* VS 徽章 */}
      <div style={{
        position: "absolute", left: 960, top: 545,
        transform: `translate(-50%,-50%) scale(${(0.4 + 0.6 * vsT) * vsPulse}) rotate(${(1 - vsT) * -15}deg)`,
        width: 150, height: 150, borderRadius: "50%",
        background: theme.colors.background,
        border: `5px solid ${theme.colors.accent}`,
        boxShadow: `0 0 60px ${theme.colors.accent}aa, inset 0 0 30px ${theme.colors.accent}33`,
        display: "flex", justifyContent: "center", alignItems: "center",
        opacity: vsT,
      }}>
        <span style={{ fontSize: 58, fontWeight: 900, color: theme.colors.accent, fontFamily: theme.fonts.english, fontStyle: "italic" }}>VS</span>
      </div>

      {/* 结论条 */}
      {verdict ? (() => {
        const t = easeOut((frame - verdictDelay) / 22);
        if (t <= 0) return null;
        return (
          <div style={{
            position: "absolute", left: 360, right: 360, top: 920,
            padding: "20px 36px", borderRadius: 16, textAlign: "center",
            background: "rgba(0,217,255,0.08)",
            border: `2px solid ${theme.colors.accent}77`,
            fontSize: 34, fontWeight: 700, color: theme.colors.text,
            fontFamily: theme.fonts.chinese,
            opacity: t, transform: `translateY(${(1 - t) * 24}px)`,
          }}>{verdict}</div>
        );
      })() : null}
    </AbsoluteFill>
  );
};

registerScene("VsShowdown", VsShowdown);
