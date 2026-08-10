import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";

/**
 * TextShatter - 文字碎裂成 token 方块。
 *
 * 视觉:完整文字先显示,然后碎裂成多个彩色 token 方块,方块向 3D 空间散开。
 * 用途:隐喻"分词 / 解构 / 拆解问题"。
 *
 * Props:
 * - inputText: 要碎裂的完整文字
 * - tokenList: 碎裂后的 token 数组
 * - scatterPattern: 散开模式 "explode" | "drift"(默认 explode)
 */

interface TextShatterProps {
  inputText: string;
  tokenList: string[];
  scatterPattern?: "explode" | "drift";
}

const TextShatter: React.FC<TextShatterProps> = ({
  inputText,
  tokenList,
  scatterPattern = "explode",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = getCurrentTheme();

  // 阶段划分
  const holdFrames = 60; // 完整文字保持 1 秒
  const shatterFrames = 90; // 碎裂动画 1.5 秒
  const scatterFrames = 90; // 散开 1.5 秒

  // 碎裂进度
  const shatterProgress =
    frame < holdFrames
      ? 0
      : frame < holdFrames + shatterFrames
        ? (frame - holdFrames) / shatterFrames
        : 1;

  const scatterProgress =
    frame < holdFrames + shatterFrames
      ? 0
      : Math.min(
          1,
          (frame - holdFrames - shatterFrames) / scatterFrames,
        );

  // 每个 token 的随机散开方向
  const tokenStates = useMemo(() => {
    return tokenList.map((_, i) => {
      const angle = (i / tokenList.length) * Math.PI * 2;
      const distance = scatterPattern === "explode" ? 600 : 200;
      return {
        x: Math.cos(angle) * distance * (0.7 + Math.random() * 0.6),
        y: Math.sin(angle) * distance * (0.7 + Math.random() * 0.6),
        rotate: (Math.random() - 0.5) * 180,
        scale: 0.5 + Math.random() * 0.8,
        color: [
          theme.colors.accent,
          theme.colors.text,
          theme.colors.textMuted,
        ][i % 3],
      };
    });
  }, [tokenList, scatterPattern, theme.colors]);

  // 完整文字透明度(碎裂时淡出)
  const inputOpacity = 1 - shatterProgress;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {/* 完整文字(碎裂前) */}
      {inputOpacity > 0 && (
        <div
          style={{
            position: "absolute",
            color: theme.colors.text,
            fontSize: 120,
            fontFamily: theme.fonts.chinese,
            fontWeight: 700,
            opacity: inputOpacity,
            textShadow: `0 0 30px ${theme.colors.accent}80`,
          }}
        >
          {inputText}
        </div>
      )}

      {/* Token 方块(碎裂后) */}
      {shatterProgress > 0 &&
        tokenList.map((token, i) => {
          const state = tokenStates[i];
          const progress = scatterPattern === "explode" ? scatterProgress : shatterProgress;
          const eased = 1 - Math.pow(1 - progress, 3);

          return (
            <div
              key={i}
              style={{
                position: "absolute",
                color: state.color,
                fontSize: 48,
                fontFamily: theme.fonts.mono,
                fontWeight: 700,
                padding: "8px 16px",
                backgroundColor: `${theme.colors.accent}20`,
                border: `2px solid ${state.color}60`,
                borderRadius: 8,
                transform: `translate(${state.x * eased}px, ${state.y * eased}px) rotate(${state.rotate * eased}deg) scale(${state.scale})`,
                opacity: 1 - scatterProgress * 0.5,
                textShadow: `0 0 15px ${state.color}80`,
              }}
            >
              {token}
            </div>
          );
        })}
    </AbsoluteFill>
  );
};

registerScene("TextShatter", TextShatter);
