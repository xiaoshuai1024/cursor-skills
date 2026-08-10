import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";
import { NeonText } from "../primitives/NeonText";
import { Scanline } from "../primitives/Scanline";

/**
 * Outro - 视频结尾场景。
 *
 * 视觉:深色背景 + 账号 Logo + CTA 文案 + Scanline 扫过,霓虹风格。
 * 用途:视频最后 3-5 秒,引导关注。
 *
 * Props:
 * - logo: Logo 图片 URL(可选,没有则只显示文字)
 * - ctaText: 引导关注文案(默认 "关注,看懂 AI")
 */

interface OutroProps {
  logo?: string;
  ctaText?: string;
}

const Outro: React.FC<OutroProps> = ({ logo, ctaText = "关注,看懂 AI" }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // Scanline 进度(整个场景期间扫一次)
  const scanProgress = Math.min(1, frame / 150);

  // Logo / 文字淡入
  const fadeIn = Math.min(1, frame / 30);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <Scanline
        progress={scanProgress}
        revealContent={
          <AbsoluteFill
            style={{
              backgroundColor: "transparent",
              justifyContent: "center",
              alignItems: "center",
              flexDirection: "column",
            }}
          >
            {/* Logo */}
            {logo && (
              <img
                src={logo}
                alt="Logo"
                style={{
                  width: 200,
                  height: 200,
                  marginBottom: 40,
                  opacity: fadeIn,
                }}
              />
            )}

            {/* CTA 文字 */}
            <div style={{ opacity: fadeIn }}>
              <NeonText
                text={ctaText}
                fontSize={80}
                fontFamily="chinese"
                glowIntensity={1.2}
              />
            </div>

            {/* 装饰线 */}
            <div
              style={{
                width: 400,
                height: 2,
                backgroundColor: theme.colors.accent,
                marginTop: 40,
                boxShadow: `0 0 10px ${theme.colors.accent}`,
                opacity: fadeIn * 0.6,
              }}
            />
          </AbsoluteFill>
        }
      />
    </AbsoluteFill>
  );
};

registerScene("Outro", Outro);
