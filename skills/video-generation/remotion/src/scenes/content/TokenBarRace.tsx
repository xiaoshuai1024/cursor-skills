import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * TokenBarRace - 上下双条竞速生长（token 成本对比的"对撞感"）。
 *
 * 视觉：
 * - 上下两条水平条按 easing 竞速生长，宽度正比 token 量
 * - 条内数字递增（保留格式），到达时数字弹跳放大
 * - 倍数徽章（如 13×）在两条长齐后从中间弹出
 */

interface TokenBarRaceProps {
  title: string;
  leftLabel: string;   // 上条名字（如 Claude Code）
  rightLabel: string;  // 下条名字（如 Pi）
  leftValue: number;   // token 数
  rightValue: number;
  unit?: string;       // "token"
  multiple?: string;   // "13×"
  leftNote?: string;
  rightNote?: string;
}

const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

const TokenBarRace: React.FC<TokenBarRaceProps> = ({
  title, leftLabel, rightLabel, leftValue, rightValue,
  unit = "token", multiple, leftNote, rightNote,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  const growT = easeOut(frame / 70);
  const leftNum = Math.round(leftValue * growT).toLocaleString();
  const rightNum = Math.round(rightValue * growT).toLocaleString();

  const barL = 360, maxW = 1180;
  const leftW = maxW * growT;
  const rightW = maxW * (rightValue / leftValue) * growT;

  const arrive = (v: number, scale: number) => {
    const t = (frame - 70) / 15;
    return t > 0 && v >= leftValue * 0.999 ? 1 + 0.18 * Math.sin(Math.min(1, t) * Math.PI) * (1 - Math.min(1, t)) * scale : 1;
  };

  const multT = easeOut((frame - 95) / 20);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <div style={{
        position: "absolute", left: 120, top: 80, right: 160,
        fontSize: 56, fontWeight: 800, color: theme.colors.text,
        fontFamily: theme.fonts.chinese,
        opacity: easeOut(frame / 18),
      }}>{title}</div>

      {/* 上条（重型） */}
      <div style={{ position: "absolute", left: barL, top: 320, width: leftW, height: 96,
        background: `linear-gradient(90deg, ${theme.colors.textMuted}cc, ${theme.colors.text}ee)`,
        borderRadius: 8, boxShadow: "0 0 30px rgba(255,255,255,0.15)" }}>
        <div style={{ position: "absolute", right: 20, top: 22, fontSize: 44, fontWeight: 800, color: theme.colors.background, fontFamily: theme.fonts.mono }}>
          {leftNum}
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, top: 344, width: 220, textAlign: "right", fontSize: 34, fontWeight: 700, color: theme.colors.text, fontFamily: theme.fonts.chinese }}>{leftLabel}</div>
      {leftNote ? <div style={{ position: "absolute", left: barL, top: 430, fontSize: 26, color: theme.colors.textMuted, fontFamily: theme.fonts.chinese, opacity: easeOut((frame - 40) / 20) }}>{leftNote}</div> : null}

      {/* 下条（Pi） */}
      <div style={{ position: "absolute", left: barL, top: 560, width: Math.max(2, rightW), height: 96,
        background: `linear-gradient(90deg, ${theme.colors.accent}dd, ${theme.colors.accent})`,
        borderRadius: 8, boxShadow: `0 0 40px ${theme.colors.accent}66` }}>
        <div style={{ position: "absolute", right: 20, top: 22, fontSize: 44, fontWeight: 800, color: theme.colors.background, fontFamily: theme.fonts.mono }}>
          {rightNum}
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, top: 584, width: 220, textAlign: "right", fontSize: 34, fontWeight: 700, color: theme.colors.accent, fontFamily: theme.fonts.chinese }}>{rightLabel}</div>
      {rightNote ? <div style={{ position: "absolute", left: barL, top: 670, fontSize: 26, color: theme.colors.accent, fontFamily: theme.fonts.chinese, opacity: easeOut((frame - 40) / 20) }}>{rightNote}</div> : null}

      {/* 倍数徽章 */}
      {multiple && multT > 0 ? (
        <div style={{
          position: "absolute", left: 1430, top: 440,
          fontSize: 92, fontWeight: 900, color: theme.colors.accent,
          fontFamily: theme.fonts.mono,
          textShadow: `0 0 50px ${theme.colors.accent}88`,
          transform: `scale(${0.5 + 0.5 * multT}) rotate(${(1 - multT) * -12}deg)`,
          opacity: multT,
        }}>{multiple}</div>
      ) : null}

      <div style={{ position: "absolute", left: barL, top: 250, fontSize: 24, color: theme.colors.textMuted, fontFamily: theme.fonts.chinese, opacity: easeOut(frame / 30) }}>
        同一比例尺 · 单位 {unit}
      </div>
    </AbsoluteFill>
  );
};

registerScene("TokenBarRace", TokenBarRace);
