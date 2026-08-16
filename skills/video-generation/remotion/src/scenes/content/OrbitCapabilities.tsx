import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * OrbitCapabilities - 中心内核 + 卫星能力环绕轨道（逐个点亮 + 缓慢公转）。
 *
 * 视觉：
 * - 中心圆形内核（呼吸发光），点亮时放大弹跳
 * - 六个能力节点沿椭圆轨道分布，随全局缓慢公转，按 delay 逐个点亮（点亮 = 描边变主色 + 光晕 + 卡片浮现）
 * - 中心到 active 节点的连线用 svg 弧线描边生长
 */

interface OrbitNode {
  label: string;
  sub: string;
}

interface OrbitCapabilitiesProps {
  title: string;
  centerLabel: string;
  centerSub?: string;
  nodes: OrbitNode[];
}

const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

const OrbitCapabilities: React.FC<OrbitCapabilitiesProps> = ({
  title, centerLabel, centerSub, nodes,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  const cx = 960, cy = 545;
  const rx = 560, ry = 300;
  const breathe = 1 + 0.03 * Math.sin(frame / 40);

  const rotate = (frame / 60) * (Math.PI / 180) * 2.4; // 缓慢公转 ~0.4°/帧
  const baseAngle = (i: number) => (i / nodes.length) * Math.PI * 2 - Math.PI / 2;

  const titleT = easeOut(frame / 18);
  const centerT = easeOut(frame / 24);

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <div style={{
        position: "absolute", left: 120, top: 62, right: 160,
        fontSize: 54, fontWeight: 800, color: theme.colors.text,
        fontFamily: theme.fonts.chinese, opacity: titleT,
        transform: `translateY(${(1 - titleT) * 20}px)`,
      }}>{title}</div>

      {/* 轨道环 */}
      <svg style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, pointerEvents: "none" }}>
        <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none"
          stroke={theme.colors.textMuted} strokeWidth={2} strokeDasharray="6 10"
          opacity={0.45 * easeOut(frame / 40)} />
        {/* 连线：中心 → 已点亮节点 */}
        {nodes.map((_, i) => {
          const a = baseAngle(i) + rotate;
          const nx = cx + Math.cos(a) * rx, ny = cy + Math.sin(a) * ry;
          const delay = 40 + i * 22;
          const t = easeOut((frame - delay) / 26);
          if (t <= 0) return null;
          // 线段按 t 从中心生长到节点
          const ex = cx + (nx - cx) * t, ey = cy + (ny - cy) * t;
          return (
            <g key={i}>
              <line x1={cx} y1={cy} x2={ex} y2={ey}
                stroke={theme.colors.accent} strokeWidth={2.5} opacity={0.55 * t} />
            </g>
          );
        })}
      </svg>

      {/* 中心内核 */}
      <div style={{
        position: "absolute", left: cx, top: cy,
        transform: `translate(-50%,-50%) scale(${(0.7 + 0.3 * centerT) * breathe})`,
        width: 250, height: 250, borderRadius: "50%",
        border: `4px solid ${theme.colors.accent}`,
        background: `radial-gradient(circle, ${theme.colors.accent}33 0%, rgba(10,14,26,0.9) 75%)`,
        boxShadow: `0 0 70px ${theme.colors.accent}55`,
        display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center",
        opacity: centerT,
      }}>
        <div style={{ fontSize: 44, fontWeight: 900, color: theme.colors.text, fontFamily: theme.fonts.chinese, textAlign: "center" }}>{centerLabel}</div>
        {centerSub ? <div style={{ fontSize: 22, color: theme.colors.accent, fontFamily: theme.fonts.chinese, marginTop: 8, textAlign: "center" }}>{centerSub}</div> : null}
      </div>

      {/* 卫星节点 */}
      {nodes.map((n, i) => {
        const a = baseAngle(i) + rotate;
        const nx = cx + Math.cos(a) * rx, ny = cy + Math.sin(a) * ry;
        const delay = 40 + i * 22;
        const t = easeOut((frame - delay) / 26);
        if (t <= 0) return null;
        const pop = 1 + 0.25 * (1 - t);
        return (
          <div key={i} style={{
            position: "absolute", left: nx, top: ny,
            transform: `translate(-50%,-50%) scale(${pop})`,
            padding: "16px 26px", borderRadius: 14,
            background: "rgba(10,25,41,0.94)",
            border: `2px solid ${theme.colors.accent}`,
            boxShadow: `0 0 34px ${theme.colors.accent}44`,
            textAlign: "center", opacity: t,
          }}>
            <div style={{ fontSize: 30, fontWeight: 800, color: theme.colors.text, fontFamily: theme.fonts.chinese, whiteSpace: "nowrap" }}>{n.label}</div>
            <div style={{ fontSize: 21, color: theme.colors.accent, fontFamily: theme.fonts.chinese, marginTop: 6, whiteSpace: "nowrap" }}>{n.sub}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

registerScene("OrbitCapabilities", OrbitCapabilities);
