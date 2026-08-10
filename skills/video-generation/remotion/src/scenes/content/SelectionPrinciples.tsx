import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * SelectionPrinciples - 选型三原则（3D 卡片逐个翻入）。
 *
 * 视觉：三张玻璃卡横向排布，每张从 rotateY(90°) 逐个翻入 + 发光。
 * 用途：插件排行视频的"怎么选"段落——按场景补能力 / 方法论只选一套 / 可观测和 token 不能省。
 *
 * Props:
 * - title: 段落标题（默认 "选型就三条"）
 * - items: 每张卡的内容 {index, title, desc, icon?}
 */

interface PrincipleItem {
  title: string;
  desc: string;
}
interface SelectionPrinciplesProps {
  title?: string;
  items: PrincipleItem[];
}

const SelectionPrinciples: React.FC<SelectionPrinciplesProps> = ({
  title = "选型就三条",
  items,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = theme.colors.accent;

  const fadeAt = (start: number, dur = 18) =>
    Math.max(0, Math.min(1, (frame - start) / dur));

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      paddingBottom: 60,
      perspective: 1400,
    }}>
      {/* 段落标题 */}
      <div style={{
        opacity: fadeAt(0, 25),
        marginBottom: 48,
      }}>
        <div style={{
          color: theme.colors.text,
          fontSize: 44,
          fontFamily: theme.fonts.chinese,
          fontWeight: 900,
          letterSpacing: 2,
          textAlign: "center",
        }}>
          {title}
        </div>
        <div style={{
          width: 220, height: 3, margin: "12px auto 0",
          background: `linear-gradient(to right, transparent, ${c}, transparent)`,
          boxShadow: `0 0 12px ${c}`,
        }} />
      </div>

      {/* 三张卡片 */}
      <div style={{ display: "flex", gap: 32 }}>
        {items.map((item, i) => {
          const startF = 25 + i * 30;
          const op = fadeAt(startF);
          const y = (1 - op) * 60;
          return (
            <div
              key={i}
              style={{
                width: 420,
                minHeight: 260,
                padding: "36px 32px",
                borderRadius: 18,
                background: `linear-gradient(160deg, ${theme.colors.backgroundAlt}dd, ${theme.colors.background}cc)`,
                border: `1.5px solid ${i === 1 ? `${c}99` : `${theme.colors.textMuted}44`}`,
                boxShadow: i === 1
                  ? `0 0 34px ${c}45, 0 20px 50px rgba(0,0,0,0.5)`
                  : `0 16px 40px rgba(0,0,0,0.4)`,
                transform: `rotateY(${90 * (1 - op)}deg) translateY(${(1 - op) * 60}px)`,
                opacity: op,
                transformStyle: "preserve-3d",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {/* 序号 */}
              <div style={{
                fontSize: 46,
                fontFamily: theme.fonts.mono,
                fontWeight: 900,
                color: i === 1 ? c : theme.colors.textMuted,
                textShadow: i === 1 ? `0 0 20px ${c}80` : "none",
                marginBottom: 12,
              }}>
                {String(i + 1).padStart(2, "0")}
              </div>
              {/* 标题 */}
              <div style={{
                color: theme.colors.text,
                fontSize: 27,
                fontFamily: theme.fonts.chinese,
                fontWeight: 800,
                marginBottom: 12,
                lineHeight: 1.3,
              }}>
                {item.title}
              </div>
              {/* 描述 */}
              <div style={{
                color: theme.colors.textMuted,
                fontSize: 18,
                fontFamily: theme.fonts.chinese,
                lineHeight: 1.6,
              }}>
                {item.desc}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

registerScene("SelectionPrinciples", SelectionPrinciples);
