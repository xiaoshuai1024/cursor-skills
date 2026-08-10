import React from "react";
import { AbsoluteFill } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * Scanline - 2D 扫描线特效。
 *
 * 视觉:一条水平亮线从上至下扫过,扫过区域揭示下层内容。
 * 用法:Outro 收尾、揭示效果。
 *
 * 实现:
 * - 一条亮线:绝对定位的水平渐变条
 * - 揭示效果:通过 clip-path 让下层内容只在扫描线经过的区域显示
 * - progress 0-1 控制扫描位置
 */

interface ScanlineProps {
  progress: number; // 0-1
  color?: string;
  thickness?: number;
  children?: React.ReactNode;
  revealContent?: React.ReactNode;
}

export const Scanline: React.FC<ScanlineProps> = ({
  progress,
  color,
  thickness = 4,
  children,
  revealContent,
}) => {
  const theme = getCurrentTheme();
  const c = color ?? theme.colors.accent;

  // progress 0→1 映射到 y 轴 -10% → 110%(允许扫描到画面外)
  const yPos = -10 + progress * 120;

  return (
    <AbsoluteFill>
      {/* 下层内容(始终存在) */}
      {children}

      {/* 扫描线揭示的内容:只有扫描线经过的区域显示 */}
      {revealContent && (
        <AbsoluteFill
          style={{
            clipPath: `inset(0 0 ${100 - yPos - thickness / 2}% 0)`,
          }}
        >
          {revealContent}
        </AbsoluteFill>
      )}

      {/* 扫描线本身 */}
      <AbsoluteFill
        style={{
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: `${yPos}%`,
            height: thickness,
            background: `linear-gradient(to right, transparent, ${c}, transparent)`,
            boxShadow: `0 0 20px ${c}, 0 0 40px ${c}80`,
            opacity: progress > 0.98 ? (1 - progress) * 50 : 1,
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
