import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * ChapterCard - 章节卡(大标题 + 小标签)。
 *
 * 用途:① 转场展示(每场景一个转场类型,配 transitionType 字段轮播);
 * ② 长视频章节切换卡(章节号 + 标题,替代硬切)。
 * 布局:中央大标题,上方 mono 小标签,底部 220px 字幕安全带。
 */

interface ChapterCardProps {
  title: string;
  /** 小标签(章节号 / 转场名),mono 字体,accent 色 */
  tag?: string;
}

const ChapterCard: React.FC<ChapterCardProps> = ({ title, tag }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const fade = Math.min(1, frame / 12);

  return (
    <AbsoluteFill
      style={{
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        paddingBottom: 220,
      }}
    >
      {tag ? (
        <div
          style={{
            fontSize: 22,
            fontFamily: theme.fonts.mono,
            letterSpacing: 6,
            color: theme.colors.accent,
            opacity: fade,
            marginBottom: 32,
          }}
        >
          {tag}
        </div>
      ) : null}
      <div
        style={{
          fontSize: 110,
          fontWeight: 900,
          color: theme.colors.text,
          fontFamily: theme.fonts.chinese,
          opacity: fade,
          textShadow: `0 0 60px ${theme.colors.accent}55`,
          letterSpacing: 2,
        }}
      >
        {title}
      </div>
    </AbsoluteFill>
  );
};

registerScene("ChapterCard", ChapterCard);
