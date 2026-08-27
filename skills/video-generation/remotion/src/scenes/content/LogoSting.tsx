import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * LogoSting - logo sting 场景:字标砸落 + 单帧白闪 + 光环扩散。
 *
 * 借鉴 HyperFrames 的 logo-sting(scale 1.15→1 expo.out 砸落 → 单帧白闪 →
 * accent 圆环 scale 0.34→2.4 扩散 → 完全静止 hold)。
 * 用于片头品牌露出 / 片尾收束。
 *
 * Props:
 * - title: 字标文本(主标题)
 * - subtitle: 副标题(白闪后淡入)
 * - info: 信息行数组(白闪后逐条浮现,每条错峰 14 帧)——片尾收束时展示
 *   仓库/原文/系列期数等可带走信息,避免定格空屏
 * - flashFrame: 白闪发生帧(相对场景),默认 18
 * - ringColor: 光环颜色,默认 theme.accent
 */

const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));

interface LogoStingProps {
  title: string;
  subtitle?: string;
  info?: string[];
  flashFrame?: number;
  ringColor?: string;
}

const LogoSting: React.FC<LogoStingProps> = ({
  title,
  subtitle,
  info,
  flashFrame = 18,
  ringColor,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const ring = ringColor ?? theme.colors.accent;

  // 字标砸落:0-12 帧 scale 1.15→1(expo.out),之后完全静止
  const dropT = Math.min(1, frame / 12);
  const scale = 1.15 - 0.15 * easeOutExpo(dropT);

  // 单帧白闪:flashFrame 那一帧全屏白
  const flash = frame === flashFrame ? 1 : 0;

  // 光环扩散:闪后一帧开始,scale 0.34→2.4 + opacity 1→0,20 帧
  const ringT = Math.min(1, Math.max(0, (frame - flashFrame - 1) / 20));
  const ringScale = 0.34 + 1.66 * ringT;
  const ringOpacity = 1 - ringT;

  // 副标题:闪后淡入
  const subT = Math.min(1, Math.max(0, (frame - flashFrame - 4) / 14));
  const subOpacity = subT;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        flexDirection: "column",
        backgroundColor: theme.colors.background,
        overflow: "hidden",
      }}
    >
      {/* 光环扩散层 */}
      <div
        style={{
          position: "absolute",
          width: 480,
          height: 480,
          borderRadius: "50%",
          border: `4px solid ${ring}`,
          transform: `scale(${ringScale})`,
          opacity: ringOpacity,
          boxShadow: `0 0 60px ${ring}66`,
        }}
      />
      {/* 字标 */}
      <div
        style={{
          transform: `scale(${scale})`,
          fontSize: 140,
          fontWeight: 900,
          color: theme.colors.text,
          fontFamily: theme.fonts.chinese,
          letterSpacing: 4,
          textShadow: `0 0 50px ${ring}99`,
        }}
      >
        {title}
      </div>
      {/* 副标题 */}
      {subtitle ? (
        <div
          style={{
            marginTop: 24,
            fontSize: 44,
            color: theme.colors.textMuted,
            fontFamily: theme.fonts.chinese,
            opacity: subOpacity,
          }}
        >
          {subtitle}
        </div>
      ) : null}
      {/* 信息行:白闪后逐条浮现,每条错峰 14 帧(片尾可带走信息,避免定格空屏) */}
      {info?.length ? (
        <div
          style={{
            marginTop: 56,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 14,
          }}
        >
          {info.map((line, i) => {
            const t = Math.min(
              1,
              Math.max(0, (frame - flashFrame - 22 - i * 14) / 16),
            );
            return (
              <div
                key={i}
                style={{
                  fontSize: 32,
                  color: i === 0 ? theme.colors.accent : theme.colors.textMuted,
                  fontFamily: theme.fonts.chinese,
                  opacity: t,
                  transform: `translateY(${(1 - t) * 8}px)`,
                  letterSpacing: 1,
                }}
              >
                {line}
              </div>
            );
          })}
        </div>
      ) : null}
      {/* 单帧白闪(在字标之上) */}
      {flash > 0 ? (
        <AbsoluteFill style={{ backgroundColor: "#ffffff" }} />
      ) : null}
    </AbsoluteFill>
  );
};

registerScene("LogoSting", LogoSting);
