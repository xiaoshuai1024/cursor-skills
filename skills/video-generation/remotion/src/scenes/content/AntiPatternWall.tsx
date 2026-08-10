import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { TimedLayer } from "../../primitives/TimedLayer";
import { Stamp } from "../../primitives/Annotation";

/**
 * AntiPatternWall - 反模式墙（每个配真实小例子）。
 * **全部卡片常显**，当前卡高亮放大、已过卡弱化——高亮随口播移动，
 * 观众一眼看到全貌与进度（2026-08-10 用户定规：一次展示全部 + 高亮跟随）。
 */

interface Props {
  patterns: string[];
  /** 场景标题；缺省兼容视觉验收旧标题 */
  header?: string;
  /** 每张卡的迷你警示例子文字（内容驱动）；缺省回退视觉验收主题示例 */
  examples?: string[];
}

// 每个反模式的迷你可视化（内容驱动：有 example 则渲染警示行；缺省回退视觉验收主题）
const MiniExample: React.FC<{ example?: string; index: number }> = ({ example, index }) => {
  const theme = getCurrentTheme();
  const common = { width: "100%", height: 70, borderRadius: 6, marginTop: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontFamily: theme.fonts.mono };

  if (example) {
    return (
      <div style={{ ...common, backgroundColor: "#1e293b", gap: 10, padding: "0 12px" }}>
        <span style={{ color: theme.colors.error, fontSize: 18, fontWeight: 900, flexShrink: 0 }}>✗</span>
        <span style={{ color: theme.colors.text, fontSize: 14, fontFamily: theme.fonts.chinese, textAlign: "center", lineHeight: 1.4 }}>{example}</span>
      </div>
    );
  }

  switch (index) {
    case 0: // 全量截图丢给 vision
      return (
        <div style={{ ...common, backgroundColor: "#1e293b", gap: 4, flexWrap: "wrap", padding: 6 }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} style={{ width: 22, height: 16, backgroundColor: i % 3 === 0 ? theme.colors.error : theme.colors.textMuted, borderRadius: 2, opacity: 0.7 }} />
          ))}
        </div>
      );
    case 1: // 像素 diff 当结论
      return (
        <div style={{ ...common, backgroundColor: "#1e293b", gap: 16 }}>
          <span style={{ color: theme.colors.error, fontSize: 28, fontWeight: 900 }}>60%</span>
          <span style={{ color: theme.colors.textMuted }}>差异 → 不合格?</span>
        </div>
      );
    case 2: // 无真相源
      return (
        <div style={{ ...common, backgroundColor: "#1e293b", gap: 6, flexWrap: "wrap", padding: 6 }}>
          {["#00b341", "#16a34a", "#1a73e8", "#6366f1", "#dc2626"].map((c) => (
            <span key={c} style={{ width: 18, height: 18, backgroundColor: c, borderRadius: 3 }} />
          ))}
          <span style={{ color: theme.colors.textMuted }}>颜色散落</span>
        </div>
      );
    case 3: // 商业黑盒 AI
      return (
        <div style={{ ...common, backgroundColor: "#1e293b" }}>
          <span style={{ color: theme.colors.textMuted, fontSize: 28 }}>⬛</span>
          <span style={{ color: theme.colors.textMuted, marginLeft: 8 }}>Visual AI 黑盒 ?</span>
        </div>
      );
    case 4: // 无 token 扫描
      return (
        <div style={{ ...common, backgroundColor: "#1e293b", padding: 6 }}>
          <span style={{ color: theme.colors.error, fontSize: 11 }}>#00b341 #1a73e8 #6366f1 堆积</span>
        </div>
      );
    default:
      return null;
  }
};

const AntiPatternWall: React.FC<Props> = ({ patterns, header, examples }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const popInterval = 50;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <TimedLayer startFrame={0} duration={800}>
        <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 36 }}>
          <div style={{ color: theme.colors.text, fontSize: 30, fontFamily: theme.fonts.chinese }}>
            {header ?? "5 个反模式 · 这些不算视觉验收"}
          </div>
        </AbsoluteFill>
      </TimedLayer>

      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 18 }}>
          {patterns.map((text, i) => {
            const popFrame = 20 + i * popInterval;
            const popped = frame >= popFrame;
            // 全量常显：未来卡暗淡可见、当前卡高亮、已过卡弱化（2026-08-10 用户定规）
            const nextFrame = 20 + (i + 1) * popInterval;
            const isCurrent = popped && frame < nextFrame;
            const opacity = isCurrent ? 1 : popped ? 0.55 : 0.35;
            return (
              <div key={i} style={{
                width: 215, height: 280,
                backgroundColor: `${theme.colors.error}10`,
                border: `2px solid ${theme.colors.error}${isCurrent ? "cc" : "50"}`,
                borderRadius: 12,
                padding: 18,
                opacity,
                transform: `scale(${isCurrent ? 1.06 : 1})`,
                boxShadow: isCurrent ? `0 0 26px ${theme.colors.error}50` : "none",
                position: "relative",
                display: "flex", flexDirection: "column",
              }}>
                {/* 序号 + ✗ */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                  <span style={{ color: theme.colors.textMuted, fontSize: 14, fontFamily: theme.fonts.mono }}>0{i + 1}</span>
                  <span style={{ color: theme.colors.error, fontSize: 24, fontWeight: 900 }}>✗</span>
                </div>
                {/* 反模式标题（取第一行） */}
                <div style={{ color: isCurrent ? theme.colors.error : theme.colors.text, fontSize: 16, fontFamily: theme.fonts.chinese, fontWeight: 700, lineHeight: 1.3, whiteSpace: "pre-line" }}>
                  {text}
                </div>
                {/* 迷你例子 */}
                <MiniExample index={i} example={examples?.[i]} />
                {/* 戳记 */}
                <div style={{ position: "absolute", right: 10, bottom: 10 }}>
                  {frame >= popFrame + 30 && <StampLocal delay={popFrame + 30} />}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// 本地戳记（不受外层 frame 影响,用 Sequence 内的相对帧）
const StampLocal: React.FC<{ delay: number }> = ({ delay }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  if (frame < delay) return null;
  const p = Math.min(1, (frame - delay) / 8);
  return (
    <span style={{
      display: "inline-block",
      color: theme.colors.error,
      fontSize: 36, fontWeight: 900,
      transform: `scale(${0.3 + p * 0.9}) rotate(-12deg)`,
      opacity: p,
      textShadow: `0 0 12px ${theme.colors.error}`,
    }}>✗</span>
  );
};

registerScene("AntiPatternWall", AntiPatternWall);
