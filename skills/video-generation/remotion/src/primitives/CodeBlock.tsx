import React from "react";
import { useCurrentFrame } from "remotion";
import { getCurrentTheme } from "../core/theme";

/**
 * CodeBlock - 代码编辑器风格代码块 + 高亮 + 扫描。
 *
 * Props:
 * - lines: 代码行数组,每行 {text, type?: "normal"|"token"|"hardcoded"|"comment"}
 *   token=绿(合规引用), hardcoded=红(写死违规), comment=灰
 * - highlightLine: 当前高亮的行号(扫描位置)
 * - title: 文件名标签
 */
interface CodeLine {
  text: string;
  type?: "normal" | "token" | "hardcoded" | "comment";
}
interface CodeBlockProps {
  lines: CodeLine[];
  highlightLine?: number;
  title?: string;
  fontSize?: number;
}

const COLORS: Record<string, { fg: string; bg: string }> = {
  normal: { fg: "#e2e8f0", bg: "transparent" },
  token: { fg: "#34d399", bg: "rgba(15,118,110,0.25)" },   // 绿
  hardcoded: { fg: "#f87171", bg: "rgba(220,38,38,0.25)" }, // 红
  comment: { fg: "#64748b", bg: "transparent" },
};

export const CodeBlock: React.FC<CodeBlockProps> = ({
  lines,
  highlightLine,
  title,
  fontSize = 22,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  return (
    <div style={{
      width: "100%",
      backgroundColor: "#0d1117",
      borderRadius: 10,
      overflow: "hidden",
      border: `1px solid ${theme.colors.backgroundAlt}`,
      fontFamily: theme.fonts.mono,
    }}>
      {/* 编辑器标题栏 */}
      {title && (
        <div style={{
          backgroundColor: "#161b22",
          padding: "10px 16px",
          fontSize: 15,
          color: theme.colors.textMuted,
          borderBottom: `1px solid ${theme.colors.backgroundAlt}`,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}>
          <span style={{ color: theme.colors.accent }}>●</span>
          <span>{title}</span>
        </div>
      )}
      {/* 代码行 */}
      <div style={{ padding: "12px 0", position: "relative" }}>
        {lines.map((line, i) => {
          const c = COLORS[line.type ?? "normal"];
          const isHighlight = highlightLine === i;
          return (
            <div
              key={i}
              style={{
                display: "flex",
                fontSize,
                lineHeight: 1.6,
                backgroundColor: isHighlight ? c.bg : "transparent",
                transition: "none",
              }}
            >
              <span style={{
                width: 50,
                textAlign: "right",
                paddingRight: 16,
                color: "#484f58",
                userSelect: "none",
                flexShrink: 0,
              }}>
                {i + 1}
              </span>
              <span style={{
                color: c.fg,
                whiteSpace: "pre",
                paddingRight: 16,
                fontWeight: line.type === "token" || line.type === "hardcoded" ? 700 : 400,
              }}>
                {line.text || " "}
              </span>
            </div>
          );
        })}
        {/* 扫描线高亮条 */}
        {highlightLine !== undefined && highlightLine < lines.length && (
          <div style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 12 + highlightLine * (fontSize * 1.6),
            height: fontSize * 1.6,
            borderTop: `2px solid ${theme.colors.accent}`,
            borderBottom: `2px solid ${theme.colors.accent}`,
            boxShadow: `0 0 12px ${theme.colors.accent}`,
            pointerEvents: "none",
          }} />
        )}
      </div>
    </div>
  );
};
