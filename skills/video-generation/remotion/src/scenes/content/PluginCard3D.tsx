import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { ParticleField } from "../../primitives/ParticleField";
import { NeonText } from "../../primitives/NeonText";

/**
 * PluginCard3D - 单个插件 3D 浮空卡片（左右分栏）。
 *
 * 左栏：排名徽章 + 插件名霓虹 + star 数大字 + 一句话价值。
 * 右栏：README 摘录面板 —— 从项目 README 前半段提取的"能做什么"，
 *       逐行展示真实能力点，带来源标注（README · <owner>/<repo>）。
 *
 * 背景粒子 + 全局 TechBackground。用途：插件排行视频中逐个介绍重点插件。
 *
 * Props:
 * - rank: 排名序号（显示 "TOP 01"）
 * - name: 插件名
 * - stars: star 数文案（如 "26万"）
 * - starsLabel: star 单位标签（默认 "GitHub Stars"）
 * - tagline: 一句话价值
 * - desc: README 前半段提取的能力点（逐行展示）
 * - readmeSrc: 摘录来源标注（如 "README · obra/superpowers"）
 * - accent: 强调色（默认 theme.accent）
 */

interface PluginCard3DProps {
  rank: string;
  name: string;
  stars: string;
  starsLabel?: string;
  tagline: string;
  desc?: string[];
  readmeSrc?: string;
  accent?: string;
}

const PluginCard3D: React.FC<PluginCard3DProps> = ({
  rank,
  name,
  stars,
  starsLabel = "GitHub Stars",
  tagline,
  desc = [],
  readmeSrc,
  accent,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const c = accent ?? theme.colors.accent;

  // 3D 浮动:rotateY 轻微摆动 + 上下浮动（呼吸感）
  const rotY = Math.sin(frame * 0.02) * 6 - 3;
  const rotX = Math.cos(frame * 0.015) * 3;
  const floatY = Math.sin(frame * 0.04) * 14;
  const glowPulse = 1 + Math.sin(frame * 0.05) * 0.15;

  // 元素逐层淡入（左栏 → 右栏 README 面板）
  const fadeAt = (start: number, dur = 20) =>
    Math.max(0, Math.min(1, (frame - start) / dur));
  const cardOpacity = fadeAt(0, 25);
  const rankOpacity = fadeAt(8);
  const nameOpacity = fadeAt(20);
  const starsOpacity = fadeAt(35);
  const taglineOpacity = fadeAt(50);
  const readmeOpacity = fadeAt(60);

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      justifyContent: "center",
      alignItems: "center",
      paddingBottom: 60,   // 略抬升,让出字幕安全带
      perspective: 1400,   // 3D 透视
    }}>
      {/* 背景粒子（3D 深空感） */}
      <AbsoluteFill style={{ opacity: 0.5 }}>
        <ParticleField count={220} volumeSize={26} speed={0.012} size={0.07} />
      </AbsoluteFill>

      {/* 3D 浮空卡片 */}
      <div
        style={{
          opacity: cardOpacity,
          transform: `rotateY(${rotY}deg) rotateX(${rotX}deg) translateY(${floatY}px)`,
          transformStyle: "preserve-3d",
          background: `linear-gradient(135deg, ${theme.colors.backgroundAlt}ee, ${theme.colors.background}cc)`,
          border: `2px solid ${c}88`,
          borderRadius: 24,
          padding: "48px 64px",
          minWidth: 1480,
          display: "flex",
          alignItems: "center",
          gap: 64,
          boxShadow: `0 0 ${60 * glowPulse}px ${c}40, 0 30px 80px rgba(0,0,0,0.5), inset 0 0 40px ${c}15`,
          backdropFilter: "blur(8px)",
        }}
      >
        {/* 顶部装饰线 */}
        <div style={{
          position: "absolute", top: 0, left: 60, right: 60, height: 3,
          background: `linear-gradient(to right, transparent, ${c}, transparent)`,
          boxShadow: `0 0 12px ${c}`,
        }} />

        {/* ===== 左栏：身份信息 ===== */}
        <div style={{
          width: 520,
          flexShrink: 0,
          textAlign: "center",
        }}>
          {/* 排名徽章 */}
          <div style={{
            display: "inline-block",
            opacity: rankOpacity,
            padding: "6px 20px",
            borderRadius: 999,
            border: `1px solid ${c}66`,
            backgroundColor: `${c}18`,
            color: c,
            fontSize: 18,
            fontFamily: theme.fonts.mono,
            fontWeight: 700,
            letterSpacing: 4,
            marginBottom: 18,
            textShadow: `0 0 12px ${c}80`,
          }}>
            TOP {rank}
          </div>

          {/* 插件名 */}
          <div style={{ opacity: nameOpacity, marginBottom: 16 }}>
            <NeonText
              text={name}
              fontSize={58}
              color={c}
              glowIntensity={glowPulse}
              fontFamily="chinese"
              fontWeight={900}
            />
          </div>

          {/* star 数大字 */}
          <div style={{ opacity: starsOpacity }}>
            <div style={{
              fontSize: 108,
              fontFamily: theme.fonts.mono,
              fontWeight: 900,
              color: "#ffffff",
              lineHeight: 1,
              textShadow: `0 0 40px ${c}, 0 0 90px ${c}60`,
              letterSpacing: 2,
            }}>
              {stars}
            </div>
            <div style={{
              color: theme.colors.textMuted,
              fontSize: 19,
              fontFamily: theme.fonts.chinese,
              letterSpacing: 3,
              marginTop: 6,
            }}>
              {starsLabel}
            </div>
          </div>

          {/* 一句话价值 */}
          <div style={{
            opacity: taglineOpacity,
            marginTop: 22,
            color: theme.colors.text,
            fontSize: 23,
            fontFamily: theme.fonts.chinese,
            fontWeight: 600,
            lineHeight: 1.5,
          }}>
            {tagline}
          </div>
        </div>

        {/* 竖分隔线 */}
        <div style={{
          width: 1, alignSelf: "stretch",
          background: `linear-gradient(to bottom, transparent, ${c}66, transparent)`,
        }} />

        {/* ===== 右栏：README 摘录 ===== */}
        <div style={{
          flex: 1,
          opacity: readmeOpacity,
          alignSelf: "stretch",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          backgroundColor: `${theme.colors.background}55`,
          border: `1px solid ${theme.colors.textMuted}44`,
          borderRadius: 16,
          padding: "30px 34px",
          minHeight: 380,
        }}>
          {/* README 面板头 */}
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 20,
          }}>
            <div style={{
              width: 10, height: 10, borderRadius: 2,
              backgroundColor: c,
              boxShadow: `0 0 10px ${c}`,
            }} />
            <div style={{
              color: c,
              fontSize: 18,
              fontFamily: theme.fonts.mono,
              fontWeight: 700,
              letterSpacing: 1,
            }}>
              README 摘录
            </div>
            {readmeSrc && (
              <div style={{
                marginLeft: "auto",
                color: theme.colors.textMuted,
                fontSize: 16,
                fontFamily: theme.fonts.mono,
              }}>
                {readmeSrc}
              </div>
            )}
          </div>

          {/* 能力点逐行 */}
          {desc.map((line, i) => (
            <div key={i} style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 14,
              marginBottom: 16,
            }}>
              <div style={{
                marginTop: 10,
                width: 7, height: 7, borderRadius: 999,
                backgroundColor: c,
                flexShrink: 0,
                opacity: 0.9,
              }} />
              <div style={{
                color: theme.colors.text,
                fontSize: 21,
                fontFamily: theme.fonts.chinese,
                lineHeight: 1.6,
                fontWeight: 500,
              }}>
                {line}
              </div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

registerScene("PluginCard3D", PluginCard3D);
