import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { TimedLayer } from "../../primitives/TimedLayer";

/**
 * GrowthChart - 跃升幅度对比（前后双柱 + 增长箭头）。
 *
 * 视觉：每个基准一组，左灰柱(旧) 右品牌蓝柱(新) + 增长倍数标注。
 */

interface GrowthItem {
  benchmark: string;
  before: number;
  after: number;
}
interface GrowthChartProps {
  title: string;
  items: GrowthItem[];
}

const GrowthChart: React.FC<GrowthChartProps> = ({ title, items }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const brandBlue = "#4D6BFE";

  const maxVal = Math.max(...items.flatMap((i) => [i.before, i.after]));
  const groupWidth = 280;
  const barMaxH = 360;

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      flexDirection: "column",
      justifyContent: "flex-start",
      alignItems: "center",
      padding: "70px 80px 200px",
    }}>
      <TimedLayer startFrame={0} duration={9999}>
        <div style={{ textAlign: "center", marginBottom: 30 }}>
          <div style={{ color: theme.colors.text, fontSize: 38, fontFamily: theme.fonts.chinese, fontWeight: 800 }}>
            {title}
          </div>
          <div style={{ color: theme.colors.textMuted, fontSize: 18, fontFamily: theme.fonts.chinese, marginTop: 6 }}>
            灰=预览版 · 蓝=Flash 正式版
          </div>
        </div>
      </TimedLayer>

      {/* 图例 + 图表 */}
      <div style={{ display: "flex", gap: 40, alignItems: "flex-end", marginTop: 20 }}>
        {items.map((item, i) => {
          const startF = 20 + i * 25;
          const grow = Math.max(0, Math.min(1, (frame - startF) / 30));
          const eased = 1 - Math.pow(1 - grow, 3);
          const beforeH = (item.before / maxVal) * barMaxH * eased;
          const afterH = (item.after / maxVal) * barMaxH * eased;
          const multiplier = (item.after / item.before).toFixed(1);

          return (
            <div key={i} style={{ width: groupWidth, display: "flex", flexDirection: "column", alignItems: "center" }}>
              {/* 倍数标注 */}
              <div style={{
                color: brandBlue, fontSize: 32, fontFamily: theme.fonts.mono, fontWeight: 900,
                marginBottom: 8, opacity: grow > 0.9 ? 1 : 0,
                textShadow: `0 0 16px ${brandBlue}80`,
              }}>
                ↑{multiplier}x
              </div>
              {/* 双柱 */}
              <div style={{ display: "flex", gap: 16, alignItems: "flex-end", height: barMaxH + 10 }}>
                {/* before */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <span style={{ color: theme.colors.textMuted, fontSize: 16, fontFamily: theme.fonts.mono, marginBottom: 4 }}>
                    {item.before}
                  </span>
                  <div style={{
                    width: 60, height: beforeH,
                    background: `linear-gradient(180deg, ${theme.colors.textMuted}99, ${theme.colors.textMuted}44)`,
                    borderRadius: "6px 6px 0 0",
                    border: `1px solid ${theme.colors.textMuted}66`,
                  }} />
                </div>
                {/* after */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <span style={{ color: brandBlue, fontSize: 20, fontFamily: theme.fonts.mono, fontWeight: 800, marginBottom: 4 }}>
                    {item.after}
                  </span>
                  <div style={{
                    width: 60, height: afterH,
                    background: `linear-gradient(180deg, ${brandBlue}, ${brandBlue}aa)`,
                    borderRadius: "6px 6px 0 0",
                    border: `2px solid ${brandBlue}`,
                    boxShadow: `0 0 20px ${brandBlue}60`,
                  }} />
                </div>
              </div>
              {/* 基准名 */}
              <div style={{
                color: theme.colors.text, fontSize: 18, fontFamily: theme.fonts.chinese,
                marginTop: 12, textAlign: "center", fontWeight: 600,
              }}>
                {item.benchmark}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

registerScene("GrowthChart", GrowthChart);
