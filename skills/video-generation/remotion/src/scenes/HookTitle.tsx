import React from "react";
import { AbsoluteFill, useCurrentFrame, Sequence } from "remotion";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";
import { ParticleField } from "../primitives/ParticleField";
import { NeonText } from "../primitives/NeonText";

/**
 * HookTitle - 视频开场 Hook 场景。
 *
 * 视觉:标题从深处飞来,配合粒子背景 + 镜头推进感。
 * 用途:视频开头 3-5 秒,制造视觉 hook。
 *
 * Props:
 * - title: 主标题文字
 * - subtitle: 副标题(可选)
 * - enterFrom: 进入方向 "depth" | "top" | "bottom"(默认 depth)
 * - durationInFrames: 总时长(场景内部不读,由 VideoConfig 指定)
 */

interface HookTitleProps {
  title: string;
  subtitle?: string;
  enterFrom?: "depth" | "top" | "bottom";
}

const HookTitle: React.FC<HookTitleProps> = ({
  title,
  subtitle,
  enterFrom = "depth",
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 进入动画(前 30 帧 = 0.5 秒)
  const enterDuration = 30;
  const enterProgress = Math.min(1, frame / enterDuration);
  const eased = 1 - Math.pow(1 - enterProgress, 3); // ease-out cubic

  // 根据 enterFrom 计算起始位置和变换
  let transform = "";
  let initialOpacity = 0;
  if (enterFrom === "depth") {
    const scale = 0.2 + eased * 0.8;
    transform = `scale(${scale})`;
    initialOpacity = eased;
  } else if (enterFrom === "top") {
    const y = -200 + eased * 200;
    transform = `translateY(${y}px)`;
    initialOpacity = eased;
  } else {
    const y = 200 - eased * 200;
    transform = `translateY(${y}px)`;
    initialOpacity = eased;
  }

  // 标题发光强度(轻微呼吸)
  const glowIntensity = 1 + Math.sin(frame * 0.1) * 0.15;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      {/* 背景粒子 */}
      <ParticleField count={400} volumeSize={30} speed={0.015} />

      {/* 标题 */}
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            transform,
            opacity: initialOpacity,
            transition: "none",
          }}
        >
          <NeonText
            text={title}
            fontSize={140}
            glowIntensity={glowIntensity}
            fontFamily="chinese"
          />
        </div>

        {subtitle && (
          <Sequence from={enterDuration} durationInFrames={60}>
            <div
              style={{
                color: theme.colors.textMuted,
                fontSize: 40,
                fontFamily: theme.fonts.chinese,
                marginTop: 30,
                opacity: Math.min(1, (frame - enterDuration) / 20),
              }}
            >
              {subtitle}
            </div>
          </Sequence>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

registerScene("HookTitle", HookTitle);
