import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { TimedLayer } from "../../primitives/TimedLayer";
import { CodeBlock } from "../../primitives/CodeBlock";

/**
 * CodeAuditScan - 真实代码审计(DOM token 扫描)。
 *
 * 视觉:展示 design token 基线代码(variables.css),
 * 扫描线逐行扫过,token 引用标绿、硬编码颜色标红。
 * 扫完后统计:423 走 token,4 个硬编码。
 */

interface CodeAuditScanProps {
  totalPages: number;
  hardcodedPages: number;
}

// 脱敏的代表性代码(符合 no-real-project-info,用泛称 brand-color)
const CODE_LINES: Array<{ text: string; type?: "normal" | "token" | "hardcoded" | "comment" }> = [
  { text: "/* variables.css — design token 基线(机器可读) */", type: "comment" },
  { text: ":root {", type: "normal" },
  { text: "  --brand-primary: #16a34a;   /* 主色 token */", type: "token" },
  { text: "  --brand-bg: linear-gradient(...);", type: "token" },
  { text: "  --radius-md: 8px;", type: "token" },
  { text: "}", type: "normal" },
  { text: "", type: "normal" },
  { text: "/* recruit-module.css — 招聘模块 */", type: "comment" },
  { text: ".brand-header {", type: "normal" },
  { text: "  color: #1a73e8;   /* ← 写死的蓝,没用 token */", type: "hardcoded" },
  { text: "}", type: "normal" },
  { text: "", type: "normal" },
  { text: "/* fab-button.css */", type: "comment" },
  { text: ".fab {", type: "normal" },
  { text: "  background: linear-gradient(#16a34a, #0ea5e9); /* 违规 */", type: "hardcoded" },
  { text: "}", type: "normal" },
];

const CodeAuditScan: React.FC<CodeAuditScanProps> = ({ totalPages, hardcodedPages }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 扫描节奏:每 8 帧扫一行,循环扫 2 轮
  const lineInterval = 8;
  const totalScan = CODE_LINES.length * lineInterval;
  const scanPos = (frame % totalScan) / lineInterval;
  const highlightLine = Math.floor(scanPos);

  // 统计数字在扫描后段出现
  const showStats = frame >= 60;

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <TimedLayer startFrame={0} duration={700}>
        <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 36 }}>
          <div style={{ color: theme.colors.text, fontSize: 28, fontFamily: theme.fonts.chinese }}>
            DOM computed-style 扫描 · token 泄漏审计
          </div>
        </AbsoluteFill>
      </TimedLayer>

      {/* 代码区 */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingTop: 30 }}>
        <div style={{ width: 1000 }}>
          <CodeBlock
            title="audit-scan.css"
            lines={CODE_LINES}
            highlightLine={highlightLine}
            fontSize={20}
          />
          {/* 图例 */}
          <div style={{ display: "flex", gap: 30, marginTop: 20, justifyContent: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 16, height: 16, backgroundColor: theme.colors.success, borderRadius: 3 }} />
              <span style={{ color: theme.colors.textMuted, fontSize: 16, fontFamily: theme.fonts.chinese }}>var(--token) 合规</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 16, height: 16, backgroundColor: theme.colors.error, borderRadius: 3 }} />
              <span style={{ color: theme.colors.textMuted, fontSize: 16, fontFamily: theme.fonts.chinese }}>写死颜色 违规</span>
            </div>
          </div>
        </div>
      </AbsoluteFill>

      {/* 统计 */}
      {showStats && (
        <TimedLayer startFrame={0} duration={640}>
          <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 200 }}>
            <div style={{ display: "flex", gap: 60, alignItems: "center" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ color: theme.colors.success, fontSize: 56, fontFamily: theme.fonts.mono, fontWeight: 900 }}>
                  {totalPages - hardcodedPages}
                </div>
                <div style={{ color: theme.colors.success, fontSize: 18, fontFamily: theme.fonts.chinese }}>页走 token ✓</div>
              </div>
              <div style={{ color: theme.colors.textMuted, fontSize: 30 }}>|</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ color: theme.colors.error, fontSize: 56, fontFamily: theme.fonts.mono, fontWeight: 900 }}>
                  {hardcodedPages}
                </div>
                <div style={{ color: theme.colors.error, fontSize: 18, fontFamily: theme.fonts.chinese }}>页硬编码 ✗</div>
              </div>
            </div>
          </AbsoluteFill>
        </TimedLayer>
      )}
    </AbsoluteFill>
  );
};

registerScene("CodeAuditScan", CodeAuditScan);
