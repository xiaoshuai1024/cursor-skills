import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * PricePrediction - 涨价预测：价格轴 + 预测落点区间。
 *
 * 视觉：横向价格轴（0→axisMax），轴上刻度。
 *   - 「现价/参照」标记（now/ref）在轴下方：V4 Flash(accent) / V4 Pro / GLM(参照)
 *   - 「预测」标记（predict）在轴上方：涨 3 倍 / 涨 10 倍
 *   - 预测落点：轴上渐变亮带（zone），最后落结论 caption
 * 帧级驱动，各元素在 start 帧点亮（config 从 narration 时间戳计算）。
 */

interface PriceMark {
  value: number;
  label: string;
  kind: "now" | "ref" | "predict";
  /** 点亮帧（场景局部帧） */
  start: number;
}
interface PricePredictionProps {
  title: string;
  subtitle?: string;
  axisMax?: number;
  markers: PriceMark[];
  zone?: { from: number; to: number; label: string; start: number };
  conclusion?: { text: string; start: number };
}

const fadeAt = (frame: number, start: number, dur = 20) =>
  Math.max(0, Math.min(1, (frame - start) / dur));

const PricePrediction: React.FC<PricePredictionProps> = ({
  title,
  subtitle,
  axisMax = 30,
  markers,
  zone,
  conclusion,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  const AXIS_LEFT = 80;
  const AXIS_W = 1120;
  const axisX = (v: number) => AXIS_LEFT + (v / axisMax) * AXIS_W;

  const colorOf = (kind: PriceMark["kind"]) =>
    kind === "predict" ? theme.colors.error
      : kind === "ref" ? theme.colors.textMuted
      : theme.colors.accent;

  return (
    <AbsoluteFill style={{
      backgroundColor: "transparent",
      justifyContent: "center",
      alignItems: "center",
      paddingBottom: 60,   /* 字幕安全带避让 */
    }}>
      <div style={{
        width: 1280,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}>
        {/* 标题 */}
        <div style={{ textAlign: "center", opacity: fadeAt(frame, 0, 25) }}>
          <div style={{
            color: theme.colors.text,
            fontSize: 42,
            fontFamily: theme.fonts.chinese,
            fontWeight: 900,
            letterSpacing: 2,
          }}>
            {title}
          </div>
          {subtitle && (
            <div style={{
              color: theme.colors.textMuted,
              fontSize: 18,
              fontFamily: theme.fonts.chinese,
              marginTop: 8,
            }}>
              {subtitle}
            </div>
          )}
        </div>

        {/* 价格轴区域 */}
        <div style={{
          position: "relative",
          width: AXIS_LEFT + AXIS_W + 40,
          height: 360,
          marginTop: 30,
        }}>
          {/* 预测落点带（zone，悬在轴线之上、预测标记之下） */}
          {zone && (
            <div style={{
              position: "absolute",
              left: axisX(zone.from),
              width: axisX(zone.to) - axisX(zone.from),
              top: 118, height: 46,
              borderRadius: 10,
              background: `linear-gradient(90deg, ${theme.colors.error}30, ${theme.colors.error}18)`,
              border: `2px dashed ${theme.colors.error}80`,
              opacity: fadeAt(frame, zone.start),
              boxShadow: `0 0 30px ${theme.colors.error}30`,
            }}>
              <div style={{
                position: "absolute",
                top: -34, left: "50%", transform: "translateX(-50%)",
                color: theme.colors.error,
                fontSize: 22,
                fontFamily: theme.fonts.chinese,
                fontWeight: 900,
                textShadow: `0 0 14px ${theme.colors.error}80`,
                whiteSpace: "nowrap",
              }}>
                {zone.label}
              </div>
            </div>
          )}

          {/* 预测标记（轴上方，predict） */}
          {markers.filter((m) => m.kind === "predict").map((m, i) => {
            const op = fadeAt(frame, m.start);
            const x = axisX(m.value);
            const col = colorOf(m.kind);
            return (
              <div key={`p-${i}`} style={{
                position: "absolute",
                left: x, top: 30,
                transform: "translateX(-50%)",
                display: "flex", flexDirection: "column", alignItems: "center",
                opacity: op,
              }}>
                <div style={{
                  color: col,
                  fontSize: 24,
                  fontFamily: theme.fonts.chinese,
                  fontWeight: 900,
                  whiteSpace: "nowrap",
                  textShadow: `0 0 12px ${col}90`,
                }}>
                  {m.label}
                </div>
                <div style={{
                  width: 3, height: 58,
                  background: col,
                  boxShadow: `0 0 12px ${col}`,
                  marginTop: 6,
                }} />
                <div style={{
                  color: col,
                  fontSize: 22,
                  fontFamily: theme.fonts.mono,
                  fontWeight: 900,
                  marginTop: 4,
                }}>
                  ¥{m.value}
                </div>
              </div>
            );
          })}

          {/* 轴线 */}
          <div style={{
            position: "absolute",
            left: AXIS_LEFT, top: 170, width: AXIS_W, height: 4,
            borderRadius: 2,
            background: theme.colors.textMuted,
            opacity: 0.6,
          }}>
            {/* 刻度 0/10/20/30 */}
            {[0, 10, 20, 30].map((t) => {
              const x = axisX(t) - AXIS_LEFT;
              return (
                <div key={t} style={{ position: "absolute", left: x, top: -12, transform: "translateX(-50%)" }}>
                  <div style={{ width: 2, height: 28, background: theme.colors.textMuted, opacity: 0.5 }} />
                  <div style={{
                    color: theme.colors.textMuted,
                    fontSize: 16, fontFamily: theme.fonts.mono,
                    textAlign: "center", marginTop: 2,
                  }}>
                    {t}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 现价/参照标记（轴下方，now/ref） */}
          {markers.filter((m) => m.kind !== "predict").map((m, i) => {
            const op = fadeAt(frame, m.start);
            const x = axisX(m.value);
            const col = colorOf(m.kind);
            const isFlash = m.kind === "now" && m.value === 2;
            return (
              <div key={`n-${i}`} style={{
                position: "absolute",
                left: x,
                top: 180,
                transform: "translateX(-50%)",
                display: "flex", flexDirection: "column", alignItems: "center",
                opacity: op,
              }}>
                <div style={{ width: 3, height: 46, background: col, boxShadow: `0 0 12px ${col}` }} />
                <div style={{
                  marginTop: 8,
                  padding: isFlash ? "6px 14px" : "4px 10px",
                  borderRadius: 8,
                  backgroundColor: isFlash ? `${col}22` : "transparent",
                  border: isFlash ? `2px solid ${col}` : `1px solid ${col}55`,
                  color: isFlash ? col : theme.colors.textMuted,
                  fontSize: isFlash ? 24 : 19,
                  fontFamily: theme.fonts.chinese,
                  fontWeight: isFlash ? 900 : 600,
                  textShadow: isFlash ? `0 0 14px ${col}` : "none",
                  whiteSpace: "nowrap",
                }}>
                  {m.label}
                </div>
              </div>
            );
          })}
        </div>

        {/* 结论 */}
        {conclusion && (
          <div style={{
            marginTop: 20,
            padding: "14px 40px",
            borderRadius: 10,
            border: `2px solid ${theme.colors.accent}80`,
            backgroundColor: `${theme.colors.accent}12`,
            boxShadow: `0 0 30px ${theme.colors.accent}30`,
            opacity: fadeAt(frame, conclusion.start, 25),
          }}>
            <div style={{
              color: theme.colors.text,
              fontSize: 30,
              fontFamily: theme.fonts.chinese,
              fontWeight: 900,
              letterSpacing: 1,
            }}>
              {conclusion.text}
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

registerScene("PricePrediction", PricePrediction);
