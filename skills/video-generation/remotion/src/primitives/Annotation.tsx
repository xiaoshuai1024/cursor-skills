import React from "react";
import { useCurrentFrame } from "remotion";
import { AbsoluteFill } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * 标注原语集合 —— 科普视频的核心视觉语言(红框/箭头/高亮/打钩打叉)。
 * 配合 MockScreen / CodeBlock 使用,指向具体位置。
 */

/** 脉冲红框:框出问题区域。position 用百分比定位。 */
export const RedBox: React.FC<{
  x: number; y: number; w: number; h: number; // 百分比 0-100
  label?: string;
}> = ({ x, y, w, h, label }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const pulse = 0.7 + Math.sin(frame * 0.12) * 0.3;
  return (
    <>
      <div style={{
        position: "absolute",
        left: `${x}%`, top: `${y}%`,
        width: `${w}%`, height: `${h}%`,
        border: `3px solid ${theme.colors.error}`,
        borderRadius: 4,
        boxShadow: `0 0 ${20 * pulse}px ${theme.colors.error}`,
        pointerEvents: "none",
      }} />
      {label && (
        <div style={{
          position: "absolute",
          left: `${x}%`, top: `${y - 4}%`,
          transform: "translateY(-100%)",
          color: "#fff",
          backgroundColor: theme.colors.error,
          fontSize: 16,
          fontFamily: "sans-serif",
          fontWeight: 700,
          padding: "3px 10px",
          borderRadius: 4,
          whiteSpace: "nowrap",
        }}>
          {label}
        </div>
      )}
    </>
  );
};

/** 绿框:框出合规/通过区域 */
export const GreenBox: React.FC<{
  x: number; y: number; w: number; h: number;
  label?: string;
}> = ({ x, y, w, h, label }) => {
  const theme = getCurrentTheme();
  return (
    <>
      <div style={{
        position: "absolute",
        left: `${x}%`, top: `${y}%`,
        width: `${w}%`, height: `${h}%`,
        border: `3px solid ${theme.colors.success}`,
        borderRadius: 4,
        boxShadow: `0 0 15px ${theme.colors.success}80`,
        pointerEvents: "none",
      }} />
      {label && (
        <div style={{
          position: "absolute",
          left: `${x}%`, top: `${y - 4}%`,
          transform: "translateY(-100%)",
          color: "#fff",
          backgroundColor: theme.colors.success,
          fontSize: 16, fontFamily: "sans-serif", fontWeight: 700,
          padding: "3px 10px", borderRadius: 4,
        }}>
          {label}
        </div>
      )}
    </>
  );
};

/** vision 标注气泡:浮在截图上,模拟 AI 看图的判断 */
export const VisionBubble: React.FC<{
  x: number; y: number; // 气泡尖角位置(百分比)
  text: string;
  rejected?: boolean; // true=被打叉否决
}> = ({ x, y, text, rejected }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const color = rejected ? theme.colors.textMuted : theme.colors.accent;
  return (
    <div style={{
      position: "absolute",
      left: `${x}%`, top: `${y}%`,
      transform: "translate(10px, -50%)",
      backgroundColor: rejected ? "rgba(30,41,59,0.9)" : "rgba(37,99,235,0.95)",
      border: `2px solid ${color}`,
      color: "#fff",
      fontSize: 15,
      fontFamily: "sans-serif",
      padding: "6px 12px",
      borderRadius: 8,
      maxWidth: 220,
      boxShadow: `0 0 15px ${color}80`,
      opacity: rejected ? 0.6 : 1,
    }}>
      {rejected && <span style={{ marginRight: 6 }}>✗</span>}
      {text}
    </div>
  );
};

/** 大号 ✗ / ✓ 戳记 */
export const Stamp: React.FC<{
  x: number; y: number; // 百分比中心
  type: "reject" | "approve";
  delay?: number; // 出现延迟(帧)
}> = ({ x, y, type, delay = 0 }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  if (frame < delay) return null;
  const progress = Math.min(1, (frame - delay) / 8);
  const scale = 0.3 + progress * 0.7;
  const opacity = progress;
  const color = type === "reject" ? theme.colors.error : theme.colors.success;
  const symbol = type === "reject" ? "✗" : "✓";
  return (
    <div style={{
      position: "absolute",
      left: `${x}%`, top: `${y}%`,
      transform: `translate(-50%,-50%) scale(${scale}) rotate(-12deg)`,
      opacity,
      color,
      fontSize: 64,
      fontWeight: 900,
      textShadow: `0 0 20px ${color}`,
      pointerEvents: "none",
    }}>
      {symbol}
    </div>
  );
};
