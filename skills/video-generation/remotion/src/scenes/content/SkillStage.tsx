import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * SkillStage - 研发生命周期某一阶段的 skill 卡片组（内容驱动设计）。
 *
 * 用于「清单 + 流程」型文章：把某阶段的一组 skill 逐张展开，
 * 每张卡 = skill 名 + 一句话「它管什么」。**全部卡片常显**：未来卡暗淡、
 * 当前卡高亮发光、已过卡弱化——观众一眼看到全貌与进度，高亮随口播移动，
 * 而不是看空画布等卡片逐张浮现（2026-08-10 用户定规：一次展示全部 + 高亮跟随）。
 *
 * Props:
 * - stageLabel: 阶段徽章文字（如 "A · 方向对齐"）
 * - stageNote: 阶段一句话（可选，阶段头下方小字）
 * - skills: 该阶段 skill 卡片 { name, desc }
 * - cardsOnFrames: 各卡激活的绝对帧（场景内），对齐口播单元时间戳
 */
interface SkillStageProps {
  stageLabel: string;
  stageNote?: string;
  skills: Array<{ name: string; desc: string }>;
  /** 逐张浮现的绝对帧（场景内），对齐口播单元时间戳；提供后优先于 cardInterval/firstDelay */
  cardsOnFrames?: number[];
}

const SkillStage: React.FC<SkillStageProps> = ({
  stageLabel,
  stageNote,
  skills,
  cardInterval = 22,
  firstDelay = 12,
  cardsOnFrames,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = theme.colors.accent;

  const fadeAt = (start: number, dur = 18) =>
    Math.max(0, Math.min(1, (frame - start) / dur));

  /** 当前卡 / 已过卡判定：对齐口播时 = 本卡出现到下卡出现之间；否则用固定窗口 */
  const stageOf = (i: number) => {
    if (!cardsOnFrames) {
      const appearAt = firstDelay + i * cardInterval;
      return {
        appearAt,
        isCurrent: frame >= appearAt - 4 && frame < appearAt + cardInterval + 4,
        isPast: frame >= appearAt + cardInterval + 4,
      };
    }
    const appearAt = cardsOnFrames[i];
    const nextAt = i === skills.length - 1 ? Number.POSITIVE_INFINITY : cardsOnFrames[i + 1];
    return { appearAt, isCurrent: frame >= appearAt && frame < nextAt, isPast: frame >= nextAt + 4 };
  };

  // 全量常显：场景开头整体淡入一次（15 帧），之后卡片不再逐个浮现。
  // 未来卡 opacity 0.35 暗淡可见，当前卡 1.0 高亮，已过卡 0.55 弱化。
  const containerOpacity = fadeAt(0, 15);
  const cardOpacity = (isCurrent: boolean, isPast: boolean) =>
    isCurrent ? 1 : isPast ? 0.55 : 0.35;

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      paddingBottom: 60,   // 让出字幕安全带
      opacity: containerOpacity,
    }}>
      {/* 阶段标题头 */}
      <div style={{ textAlign: "center", marginBottom: 34 }}>
        <div style={{
          display: "inline-block",
          padding: "8px 26px",
          borderRadius: 999,
          border: `1.5px solid ${c}66`,
          backgroundColor: `${c}18`,
          color: c,
          fontSize: 26,
          fontFamily: theme.fonts.mono,
          fontWeight: 700,
          letterSpacing: 6,
          textShadow: `0 0 16px ${c}70`,
          marginBottom: stageNote ? 14 : 0,
        }}>
          {stageLabel}
        </div>
        {stageNote && (
          <div style={{
            color: theme.colors.textMuted,
            fontSize: 22,
            fontFamily: theme.fonts.chinese,
            letterSpacing: 2,
            marginTop: 10,
          }}>
            {stageNote}
          </div>
        )}
      </div>

      {/* skill 卡片列表（全量常显，高亮跟随） */}
      <div style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        width: 1560,
      }}>
        {skills.map((sk, i) => {
          const { isCurrent, isPast } = stageOf(i);
          const opacity = cardOpacity(isCurrent, isPast);
          const pulse = isCurrent ? 1 + Math.sin(frame * 0.08) * 0.08 : 1;

          return (
            <div key={sk.name} style={{
              opacity,
              display: "flex",
              alignItems: "center",
              gap: 28,
              padding: "20px 36px",
              borderRadius: 18,
              background: `linear-gradient(135deg, ${theme.colors.backgroundAlt}ee, ${theme.colors.background}cc)`,
              border: isCurrent
                ? `2px solid ${c}`
                : isPast
                  ? `1px solid ${theme.colors.textMuted}33`
                  : `1px solid ${c}55`,
              boxShadow: isCurrent
                ? `0 0 ${34 * pulse}px ${c}38, 0 12px 40px rgba(0,0,0,0.4)`
                : "0 8px 24px rgba(0,0,0,0.3)",
              transform: `translateX(${isCurrent ? 0 : isPast ? -4 : 10}px)`,
            }}>
              {/* skill 名（霓虹） */}
              <div style={{
                width: 380,
                flexShrink: 0,
                color: isCurrent ? c : isPast ? theme.colors.textMuted : theme.colors.text,
                fontSize: sk.name.length > 24 ? 20 : sk.name.length > 18 ? 24 : 34,
                fontFamily: theme.fonts.mono,
                fontWeight: 700,
                letterSpacing: 1,
                textShadow: isCurrent ? `0 0 18px ${c}80` : "none",
              }}>
                {sk.name}
              </div>
              {/* 一句话说明 */}
              <div style={{
                flex: 1,
                color: isPast ? theme.colors.textMuted : theme.colors.text,
                fontSize: 26,
                fontFamily: theme.fonts.chinese,
                lineHeight: 1.5,
                opacity: isPast ? 0.75 : 1,
              }}>
                {sk.desc}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

registerScene("SkillStage", SkillStage);
