import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";

/**
 * Dummy 场景 A:纯色背景 + 大字标题(用于验证装配管线)
 */
const SceneA: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const opacity = Math.min(1, frame / 20);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.backgroundAlt,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <h1
        style={{
          color: theme.colors.accent,
          fontSize: 100,
          fontFamily: theme.fonts.english,
          opacity,
          textShadow: `0 0 40px ${theme.colors.accent}80`,
        }}
      >
        {title}
      </h1>
    </AbsoluteFill>
  );
};

/**
 * Dummy 场景 B:计数动画(验证时间轴连续性)
 */
const SceneB: React.FC<{ label: string }> = ({ label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = getCurrentTheme();
  const seconds = (frame / fps).toFixed(1);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: theme.colors.background,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            color: theme.colors.text,
            fontSize: 160,
            fontFamily: theme.fonts.mono,
            fontWeight: 900,
          }}
        >
          {seconds}s
        </div>
        <div
          style={{
            color: theme.colors.textMuted,
            fontSize: 40,
            fontFamily: theme.fonts.chinese,
            marginTop: 20,
          }}
        >
          {label}
        </div>
      </div>
    </AbsoluteFill>
  );
};

registerScene("DummyA", SceneA);
registerScene("DummyB", SceneB);
