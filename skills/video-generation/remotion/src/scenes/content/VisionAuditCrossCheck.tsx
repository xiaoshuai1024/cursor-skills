import React from "react";
import { AbsoluteFill, useCurrentFrame, Sequence } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";
import { TimedLayer } from "../../primitives/TimedLayer";
import { MockScreen } from "../../primitives/MockScreen";
import { MockProductPage } from "../../primitives/MockProductPage";
import { VisionBubble, Stamp } from "../../primitives/Annotation";
import { CodeBlock } from "../../primitives/CodeBlock";

/**
 * VisionAuditCrossCheck - vision 巡查 + 代码审计交叉验证（真实素材）。
 *
 * 叙事：vision 在截图上报疑点（幻觉），代码审计逐一打叉否决。
 * 三个幻觉依次：红色角标→客服按钮 / 浅渐变→白底 / 紫色→主色。
 * 最后 407→4 真阳性率。
 */

interface Props {
  totalFindings: number;
  realIssues: number;
}

// 代码证据（脱敏）
const EVIDENCE_CART = [
  { text: "/* vision 说:客服悬浮按钮遮挡价格 */", type: "comment" as const },
  { text: "// 代码审计:全局无 fixed 悬浮按钮", type: "comment" as const },
  { text: "document.querySelectorAll('.fixed-fab')", type: "normal" as const },
  { text: "// → length: 0  (不存在)", type: "token" as const },
  { text: "", type: "normal" as const },
  { text: "// 真相:红色角标是购物车 badge", type: "comment" as const },
  { text: "<CartIcon> badge count=3", type: "token" as const },
];

const VisionAuditCrossCheck: React.FC<Props> = ({ totalFindings, realIssues }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      {/* 标题 */}
      <TimedLayer startFrame={0} duration={1072}>
        <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 32 }}>
          <div style={{ color: theme.colors.text, fontSize: 28, fontFamily: theme.fonts.chinese }}>
            老功能 · vision 看图找疑点 + 代码审计判真伪
          </div>
        </AbsoluteFill>
      </TimedLayer>

      {/* 左：真实截图 + vision 标注气泡 */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingLeft: 60 }}>
        <div style={{ position: "relative" }}>
          <MockScreen width={300} height={520}>
            <MockProductPage grayImages />
          </MockScreen>

          {/* 幻觉1 (0-360帧): 红色角标→客服按钮 */}
          <Sequence from={20} durationInFrames={340}>
            <VisionBubble x={78} y={90} text="客服悬浮按钮遮挡价格？" />
            <Stamp x={78} y={90} type="reject" delay={120} />
          </Sequence>

          {/* 幻觉2 (360-540帧): 浅渐变→白底 */}
          <Sequence from={360} durationInFrames={200}>
            <VisionBubble x={20} y={30} text="列表页纯白背景,无玻璃拟态？" />
            <Stamp x={40} y={45} type="reject" delay={100} />
          </Sequence>

          {/* 幻觉3 (560-720帧): 紫色→主色 */}
          <Sequence from={560} durationInFrames={180}>
            <VisionBubble x={50} y={55} text="用紫蓝色当主色？" />
            <Stamp x={50} y={55} type="reject" delay={100} />
          </Sequence>
        </div>
      </AbsoluteFill>

      {/* 右：代码审计证据（对应幻觉1，0-360帧显示） */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "flex-end", paddingRight: 60 }}>
        <div style={{ width: 520 }}>
          <Sequence from={140} durationInFrames={240}>
            <TimedLayer startFrame={0} duration={240}>
              <div>
                <div style={{ color: theme.colors.textMuted, fontSize: 16, fontFamily: theme.fonts.chinese, marginBottom: 10 }}>
                  代码审计 · 真相源
                </div>
                <CodeBlock title="audit.js — 幻觉1 取证" lines={EVIDENCE_CART} fontSize={16} />
              </div>
            </TimedLayer>
          </Sequence>

          {/* 幻觉2 证据 (360-540) */}
          <Sequence from={460} durationInFrames={120}>
            <CodeBlock
              title="variables.css — 幻觉2 取证"
              lines={[
                { text: "/* vision 说:纯白背景 */", type: "comment" },
                { text: "--brand-bg: linear-gradient(", type: "token" },
                { text: "  #e6eeea → #fafdfb); /* 浅渐变 */", type: "token" },
                { text: "/* 实际应用了,只是太浅 */", type: "comment" },
              ]}
              fontSize={16}
            />
          </Sequence>

          {/* 幻觉3 证据 (560-720) */}
          <Sequence from={660} durationInFrames={120}>
            <CodeBlock
              title="audit.js — 幻觉3 取证"
              lines={[
                { text: "/* vision 说:紫色主色 */", type: "comment" },
                { text: "getComputedStyle(el).color", type: "normal" },
                { text: "// → rgb(99,102,241) /* indigo */", type: "token" },
                { text: "// 12 文件一致使用同一 token", type: "token" },
                { text: "// 分类编码,非违规", type: "comment" },
              ]}
              fontSize={16}
            />
          </Sequence>
        </div>
      </AbsoluteFill>

      {/* 底部:407→4 真阳性率 */}
      <Sequence from={780} durationInFrames={292}>
        <TimedLayer startFrame={0} duration={292}>
          <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 200 }}>
            <div style={{ display: "flex", gap: 50, alignItems: "center" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ color: theme.colors.error, fontSize: 64, fontFamily: theme.fonts.mono, fontWeight: 900 }}>
                  {totalFindings}
                </div>
                <div style={{ color: theme.colors.error, fontSize: 16, fontFamily: theme.fonts.chinese }}>vision 疑点</div>
              </div>
              <div style={{ color: theme.colors.textMuted, fontSize: 36 }}>→</div>
              <div style={{ textAlign: "center" }}>
                <div style={{ color: theme.colors.success, fontSize: 64, fontFamily: theme.fonts.mono, fontWeight: 900 }}>
                  {realIssues}
                </div>
                <div style={{ color: theme.colors.success, fontSize: 16, fontFamily: theme.fonts.chinese }}>真问题</div>
              </div>
              <div style={{ borderLeft: `1px solid ${theme.colors.textMuted}`, height: 70, opacity: 0.4, margin: "0 10px" }} />
              <div style={{ textAlign: "center" }}>
                <div style={{ color: theme.colors.error, fontSize: 40, fontFamily: theme.fonts.mono, fontWeight: 900 }}>
                  {"<1%"}
                </div>
                <div style={{ color: theme.colors.textMuted, fontSize: 16, fontFamily: theme.fonts.chinese }}>真阳性率</div>
              </div>
            </div>
          </AbsoluteFill>
        </TimedLayer>
      </Sequence>
    </AbsoluteFill>
  );
};

registerScene("VisionAuditCrossCheck", VisionAuditCrossCheck);
