import React from "react";
import { getCurrentTheme } from "../core/theme";

/**
 * MockScreen - 程序化模拟的手机/网页屏幕截图。
 *
 * 不用真实截图(脱敏 + 无视频生成模型约束),用 React 画"假的但真实的"页面。
 * 用于 PixelDiff 等场景的"原型 vs 实现"对比。
 *
 * Props:
 * - children: 屏幕内容(网页组件)
 * - width / height: 屏幕尺寸
 * - label: 屏幕标签(如"原型"/"实现")
 * - variant: "phone" 加手机外框 | "plain" 纯内容
 */
interface MockScreenProps {
  children: React.ReactNode;
  width?: number;
  height?: number;
  label?: string;
  variant?: "phone" | "plain";
}

export const MockScreen: React.FC<MockScreenProps> = ({
  children,
  width = 360,
  height = 640,
  label,
  variant = "phone",
}) => {
  const theme = getCurrentTheme();
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      {label && (
        <div style={{
          color: theme.colors.textMuted,
          fontSize: 22,
          fontFamily: theme.fonts.chinese,
          marginBottom: 12,
          letterSpacing: 2,
        }}>
          {label}
        </div>
      )}
      <div style={{
        width: variant === "phone" ? width + 16 : width,
        height: variant === "phone" ? height + 16 : height,
        backgroundColor: "#000",
        borderRadius: variant === "phone" ? 32 : 8,
        padding: variant === "phone" ? 8 : 0,
        boxShadow: `0 0 40px ${theme.colors.accent}30, 0 8px 30px rgba(0,0,0,0.5)`,
        border: `1px solid ${theme.colors.backgroundAlt}`,
      }}>
        <div style={{
          width,
          height,
          backgroundColor: "#ffffff",
          borderRadius: variant === "phone" ? 24 : 4,
          overflow: "hidden",
          position: "relative",
        }}>
          {children}
        </div>
      </div>
    </div>
  );
};
