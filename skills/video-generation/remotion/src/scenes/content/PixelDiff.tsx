import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { TimedLayer } from "../../primitives/TimedLayer";
import { MockScreen } from "../../primitives/MockScreen";
import { MockProductPage } from "../../primitives/MockProductPage";
import { RedBox } from "../../primitives/Annotation";

/**
 * PixelDiff - 真实截图对比 + 红框标注。
 *
 * 视觉:左边原型(规范)、右边实现(多功能区 + 按钮偏移),
 * 差异区域用脉冲红框框出。这是"像素 diff"概念的真实可视化。
 */

interface PixelDiffProps {
  leftLabel: string;
  rightLabel: string;
  diffPercent: number;
}

const PixelDiff: React.FC<PixelDiffProps> = ({ leftLabel, rightLabel, diffPercent }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 差异揭示节奏
  const showExtraBlock = frame >= 90;   // 1.5s 后框出新功能区
  const showShift = frame >= 180;       // 3s 后框出按钮偏移
  const showNumber = frame >= 270;      // 4.5s 后出数字

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      {/* 顶部说明 */}
      <TimedLayer startFrame={0} duration={400}>
        <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 40 }}>
          <div style={{ color: theme.colors.text, fontSize: 30, fontFamily: theme.fonts.chinese }}>
            新功能 · 原型 vs 实现像素比对
          </div>
        </AbsoluteFill>
      </TimedLayer>

      {/* 两个手机屏幕并排 */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 120, alignItems: "flex-start" }}>
          {/* 左:原型(规范) */}
          <div style={{ position: "relative" }}>
            <MockScreen label={leftLabel} width={320} height={560}>
              <MockProductPage grayImages />
            </MockScreen>
          </div>

          {/* 右:实现(有差异) */}
          <div style={{ position: "relative" }}>
            <MockScreen label={rightLabel} width={320} height={560}>
              <MockProductPage grayImages shifted extraBlock />
            </MockScreen>

            {/* 红框标注差异(叠加在实现屏上) */}
            {showExtraBlock && (
              <RedBox x={4} y={45} w={92} h={12} label="内容演进:多了功能区" />
            )}
            {showShift && (
              <RedBox x={2} y={88} w={96} h={10} label="按钮位置偏移" />
            )}
          </div>
        </div>
      </AbsoluteFill>

      {/* 差异数字 + 容差档说明 */}
      {showNumber && (
        <TimedLayer startFrame={0} duration={120}>
          <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 200 }}>
            <div style={{ display: "flex", gap: 50, alignItems: "center" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ color: theme.colors.error, fontSize: 72, fontFamily: theme.fonts.mono, fontWeight: 900, textShadow: `0 0 30px ${theme.colors.error}` }}>
                  {diffPercent}%
                </div>
                <div style={{ color: theme.colors.textMuted, fontSize: 18, fontFamily: theme.fonts.chinese }}>差异率 · 内容演进非样式崩坏</div>
              </div>
              <div style={{ borderLeft: `1px solid ${theme.colors.textMuted}`, height: 70, opacity: 0.4 }} />
              <div style={{ textAlign: "left" }}>
                <div style={{ color: theme.colors.textMuted, fontSize: 14, marginBottom: 4 }}>容差档</div>
                <div style={{ color: theme.colors.accent, fontSize: 16, fontFamily: theme.fonts.mono }}>strict 5%</div>
                <div style={{ color: theme.colors.text, fontSize: 16, fontFamily: theme.fonts.mono }}>standard 15%</div>
                <div style={{ color: theme.colors.textMuted, fontSize: 16, fontFamily: theme.fonts.mono }}>loose 30%</div>
              </div>
            </div>
          </AbsoluteFill>
        </TimedLayer>
      )}
    </AbsoluteFill>
  );
};

registerScene("PixelDiff", PixelDiff);
