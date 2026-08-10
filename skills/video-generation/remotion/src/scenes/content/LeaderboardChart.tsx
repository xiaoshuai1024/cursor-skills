import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { TimedLayer } from "../../primitives/TimedLayer";

/**
 * LeaderboardChart - 编程能力排行榜（横向条形图，高亮指定项）。
 *
 * 视觉：模型名 + 横条 + 分数，按分数降序。highlightIndex 项用品牌色高亮 + 发光 + 标注。
 * 条目按节奏从上到下逐条生长。
 */

interface BarItem {
  label: string;
  score: number;
  note?: string;        // 附加标注（如"旧版"）
}
interface LeaderboardChartProps {
  title: string;
  unit?: string;        // 分数单位说明
  items: BarItem[];     // 已按降序排好
  highlightLabel: string; // 高亮哪个（按 label 匹配）
  highlightNote?: string;  // 高亮项的标注（如"仅低于 Opus"）
  /** 逐条点亮帧（场景局部帧），与口播对齐；缺省回退 15 + i*18 均匀节奏 */
  itemStarts?: number[];
}

const LeaderboardChart: React.FC<LeaderboardChartProps> = ({
  title, unit, items, highlightLabel, highlightNote, itemStarts,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  // 高亮色从主题读取：deepseek 主题 = 品牌蓝，claude-plugins 主题 = 珊瑚橙
  const brandBlue = theme.colors.accent;

  const maxScore = Math.max(...items.map((i) => i.score));
  const barMaxWidth = 1100;
  // 自适应紧凑模式：条目多（≥10）时压缩行高/字号，避免 12 行超出 1080p 屏幕
  // （claude-plugins 12 条用紧凑；deepseek 4-5 条保持原宽松布局）
  const many = items.length >= 10;
  const rowHeight = many ? 60 : 78;
  const rowMargin = many ? 5 : 8;
  const barHeight = many ? 36 : 40;
  const labelFont = many ? 20 : 22;
  const labelFontHl = many ? 24 : 26;
  const topPad = many ? 56 : 70;
  const bottomPad = many ? 60 : 200;
  const labelWidth = 280;

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      flexDirection: "column",
      justifyContent: "flex-start",
      alignItems: "center",
      padding: `${topPad}px 80px ${bottomPad}px`,
    }}>
      {/* 标题 */}
      <TimedLayer startFrame={0} duration={9999}>
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <div style={{ color: theme.colors.text, fontSize: 38, fontFamily: theme.fonts.chinese, fontWeight: 800 }}>
            {title}
          </div>
          {unit && (
            <div style={{ color: theme.colors.textMuted, fontSize: 18, fontFamily: theme.fonts.chinese, marginTop: 6 }}>
              {unit}
            </div>
          )}
        </div>
      </TimedLayer>

      {/* 条形图 */}
      <div style={{ width: "100%", maxWidth: 1500 }}>
        {items.map((item, i) => {
          const isHighlight = item.label === highlightLabel;
          const startF = itemStarts ? itemStarts[i] : 15 + i * 18;
          const grow = Math.max(0, Math.min(1, (frame - startF) / 25));
          const eased = 1 - Math.pow(1 - grow, 3);
          const width = (item.score / maxScore) * barMaxWidth * eased;
          const color = isHighlight ? brandBlue : theme.colors.textMuted;
          const bgOpacity = isHighlight ? 0.9 : 0.35;

          return (
            <div key={i} style={{
              display: "flex", alignItems: "center",
              height: rowHeight, marginBottom: rowMargin,
            }}>
              {/* 模型名 */}
              <div style={{
                width: labelWidth, textAlign: "right", paddingRight: 24,
                color: isHighlight ? brandBlue : theme.colors.text,
                fontSize: isHighlight ? labelFontHl : labelFont,
                fontFamily: theme.fonts.chinese,
                fontWeight: isHighlight ? 800 : 500,
                textShadow: isHighlight ? `0 0 16px ${brandBlue}80` : "none",
              }}>
                {item.label}
                {item.note && (
                  <span style={{ color: theme.colors.textMuted, fontSize: 14, marginLeft: 6 }}>{item.note}</span>
                )}
              </div>
              {/* 条 */}
              <div style={{ flex: 1, position: "relative", height: barHeight }}>
                <div style={{
                  width, height: "100%",
                  background: isHighlight
                    ? `linear-gradient(90deg, ${brandBlue}, ${brandBlue}cc)`
                    : `linear-gradient(90deg, ${theme.colors.textMuted}aa, ${theme.colors.textMuted}66)`,
                  opacity: bgOpacity,
                  borderRadius: 6,
                  boxShadow: isHighlight
                    ? `0 0 24px ${brandBlue}80, inset 0 0 12px ${brandBlue}40`
                    : "none",
                  border: isHighlight ? `2px solid ${brandBlue}` : "none",
                }} />
                {/* 分数 */}
                <div style={{
                  position: "absolute",
                  left: width + 12,
                  top: "50%", transform: "translateY(-50%)",
                  color: isHighlight ? brandBlue : theme.colors.textMuted,
                  fontSize: isHighlight ? 30 : 24,
                  fontFamily: theme.fonts.mono, fontWeight: 900,
                  opacity: grow > 0.9 ? 1 : 0,
                  textShadow: isHighlight ? `0 0 12px ${brandBlue}` : "none",
                }}>
                  {item.score}
                </div>
                {/* 高亮标注 */}
                {isHighlight && highlightNote && grow > 0.95 && (
                  <div style={{
                    position: "absolute",
                    left: width + 80, top: "50%", transform: "translateY(-50%)",
                    color: brandBlue, fontSize: 16, fontFamily: theme.fonts.chinese, fontWeight: 700,
                    backgroundColor: `${brandBlue}20`,
                    padding: "4px 12px", borderRadius: 4, border: `1px solid ${brandBlue}`,
                    whiteSpace: "nowrap",
                  }}>
                    {highlightNote}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

registerScene("LeaderboardChart", LeaderboardChart);
