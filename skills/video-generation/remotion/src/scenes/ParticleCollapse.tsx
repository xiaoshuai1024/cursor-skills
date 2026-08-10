import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";

/**
 * ParticleCollapse - 粒子汇聚成目标文字。
 *
 * 视觉:散布的粒子向画面中央汇聚,逐渐形成目标文字轮廓。可选转场到 2D 玻璃态卡片。
 * 用途:隐喻"收敛 / 答案生成 / 从混沌到秩序"。
 *
 * Props:
 * - targetText: 最终显示的文字
 * - collapseDuration: 汇聚时长(帧,默认 180 = 3 秒)
 * - transitionTo2D: 是否在汇聚完成后转场到 2D 卡片(默认 true)
 */

interface ParticleCollapseProps {
  targetText: string;
  collapseDuration?: number;
  transitionTo2D?: boolean;
}

const ParticleCollapse: React.FC<ParticleCollapseProps> = ({
  targetText,
  collapseDuration = 180,
  transitionTo2D = true,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 粒子数量
  const particleCount = 200;

  // 每个粒子的初始位置和目标位置
  const particles = useMemo(() => {
    return Array.from({ length: particleCount }, (_, i) => {
      // 初始:随机散布
      const startX = (Math.random() - 0.5) * 1600;
      const startY = (Math.random() - 0.5) * 900;
      // 目标:汇聚到中央(模拟文字轮廓,用简单圆形近似)
      const angle = (i / particleCount) * Math.PI * 2;
      const radius = 100 + Math.random() * 50;
      const targetX = Math.cos(angle) * radius;
      const targetY = Math.sin(angle) * radius;

      return { startX, startY, targetX, targetY };
    });
  }, [particleCount]);

  // 汇聚进度(0-1)
  const progress = Math.min(1, frame / collapseDuration);
  const eased = 1 - Math.pow(1 - progress, 3); // ease-out

  // 2D 卡片淡入(汇聚完成后)
  const cardOpacity = transitionTo2D
    ? Math.max(0, (frame - collapseDuration) / 30)
    : 0;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* 粒子 */}
      {particles.map((p, i) => {
        const x = p.startX + (p.targetX - p.startX) * eased;
        const y = p.startY + (p.targetY - p.startY) * eased;
        const size = 4 + (1 - progress) * 2;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `calc(50% + ${x}px)`,
              top: `calc(50% + ${y}px)`,
              width: size,
              height: size,
              borderRadius: "50%",
              backgroundColor: theme.colors.accent,
              boxShadow: `0 0 ${8 + progress * 12}px ${theme.colors.accent}`,
              opacity: 0.8,
              transform: "translate(-50%, -50%)",
            }}
          />
        );
      })}

      {/* 汇聚后的文字 */}
      {progress > 0.8 && (
        <div
          style={{
            position: "absolute",
            color: theme.colors.text,
            fontSize: 80,
            fontFamily: theme.fonts.chinese,
            fontWeight: 700,
            opacity: (progress - 0.8) * 5,
            textShadow: `0 0 40px ${theme.colors.accent}`,
          }}
        >
          {targetText}
        </div>
      )}

      {/* 2D 玻璃态卡片(可选) */}
      {cardOpacity > 0 && (
        <div
          style={{
            position: "absolute",
            backgroundColor: `${theme.colors.backgroundAlt}cc`,
            border: `2px solid ${theme.colors.accent}60`,
            borderRadius: 16,
            padding: "40px 80px",
            backdropFilter: "blur(10px)",
            opacity: Math.min(1, cardOpacity),
            boxShadow: `0 0 40px ${theme.colors.accent}40`,
          }}
        >
          <div
            style={{
              color: theme.colors.text,
              fontSize: 60,
              fontFamily: theme.fonts.chinese,
              fontWeight: 700,
              textAlign: "center",
            }}
          >
            {targetText}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

registerScene("ParticleCollapse", ParticleCollapse);
