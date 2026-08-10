import React from "react";
import { useCurrentFrame, AbsoluteFill } from "remotion";
import type { SubtitleEntry } from "./types";
import { getCurrentTheme } from "./theme";

/**
 * 通用字幕叠加层。
 *
 * 设计约束：
 * - 横向一屏：长句按标点切分换行，每行 ≤ MAX_CHARS 字，最多 MAX_LINES 行。
 * - 底部安全带：固定占画面底部 SUBTITLE_BAND（15%），所有场景内容 MUST 避让此区域。
 *
 * 场景内容避让字幕区的约定：
 *   场景内底部元素 paddingBottom 应 ≥ SUBTITLE_BAND_PX（导出常量）。
 */

/** 字幕安全带：画面底部固定保留高度（像素） */
export const SUBTITLE_BAND_PX = 170;

/**
 * 字幕单元已在 narrate 阶段拆成 ≤18 字的意群（不截断、不省略）。
 * 这里直接显示，每次一句完整短句。
 */
function cleanText(text: string): string {
  return text.replace(/[，。！？、；：""''（）…—]/g, "");
}

export const SubtitleOverlay: React.FC<{ subtitles: SubtitleEntry[] }> = ({
  subtitles,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  const current = subtitles.find(
    (s) => frame >= s.startFrame && frame < s.endFrame,
  );
  if (!current) return null;

  const fadeIn = 10;
  const fadeOut = 10;
  const relativeFrame = frame - current.startFrame;
  const duration = current.endFrame - current.startFrame;
  let opacity = 1;
  if (relativeFrame < fadeIn) {
    opacity = relativeFrame / fadeIn;
  } else if (relativeFrame > duration - fadeOut) {
    opacity = (duration - relativeFrame) / fadeOut;
  }

  const line = cleanText(current.text);

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 40,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity,
          backgroundColor: "rgba(0, 0, 0, 0.55)",
          padding: "14px 36px",
          borderRadius: 8,
          color: theme.colors.text,
          fontSize: 38,
          fontFamily: theme.fonts.chinese,
          fontWeight: 500,
          letterSpacing: 1,
          textAlign: "center",
          whiteSpace: "nowrap",
        }}
      >
        {line}
      </div>
    </AbsoluteFill>
  );
};
