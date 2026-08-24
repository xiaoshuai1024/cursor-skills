import React from "react";
import { useCurrentFrame } from "remotion";

/**
 * MascotFigure - 终端小子(AI 形象)的 React 版单帧几何。
 *
 * 几何与表情/姿态/头顶符号组逐 path 同步自封面资产
 * scripts/yixiaoer/assets/mascot.svg(CSS 类互斥显隐版)。
 * 改几何时两处必须同步——封面走 CSS 类,这里走条件渲染。
 *
 * 与封面的差异:talking 态波形条即嘴——讲话时表情嘴隐去,嘴位 (y146-198) 显示
 * 翻动波形条(语音助手式,波形=讲话的标志);静默时恢复表情嘴。眼区 (y≤144) 两种
 * 状态都完整可见(讲话动画参数见 MascotCompanion)。
 *
 * Props:
 * - mood: 6 表情之一(默认 smile)
 * - pose: 3 姿态之一(默认 wave)
 * - talking: 说话段为 true 时屏幕脸底部出现翻动的波形条(伪随机,无 Math.random)
 * - height: 渲染高度 px(宽度按 viewBox 320/470 自动)
 * - style: 外层附加样式
 */
export type MascotMood = "smile" | "wow" | "meh" | "money" | "dead" | "huh";
export type MascotPose = "wave" | "point" | "cheer";

interface MascotFigureProps {
  mood?: MascotMood;
  pose?: MascotPose;
  talking?: boolean;
  height?: number;
  style?: React.CSSProperties;
}

/** 讲话态波形条高度:双正弦组合的伪随机序列,帧驱动、渲染确定 */
const barHeight = (frame: number, i: number): number => {
  const t = frame / 5;
  const wave = Math.sin(t + i * 1.7) * 0.5 + Math.sin(t * 0.63 + i * 2.9) * 0.5;
  return 8 + Math.abs(wave) * 16; // max≈24,占满嘴位带
};

export const MascotFigure: React.FC<MascotFigureProps> = ({
  mood = "smile",
  pose = "wave",
  talking = false,
  height = 210,
  style,
}) => {
  const frame = useCurrentFrame();
  // 每实例独立 filter id(多实例同帧并存时 url(#id) 不串)
  const glowId = `mglow-${React.useId().replace(/[:]/g, "")}`;

  return (
    <svg
      viewBox="0 -70 320 470"
      preserveAspectRatio="xMidYMid meet"
      style={{ height, aspectRatio: "320 / 470", display: "block", ...style }}
    >
      <defs>
        <filter id={glowId} x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="0" stdDeviation="10" floodColor="#22d3ee" floodOpacity="0.55" />
        </filter>
      </defs>

      {/* 天线 */}
      <rect x="156" y="12" width="8" height="34" fill="#22d3ee" />
      <circle cx="160" cy="10" r="9" fill="#22d3ee" filter={`url(#${glowId})`} />

      {/* ======== 头顶情绪符号层(随 mood 联动,浮夸放大) ======== */}
      {mood === "smile" && (
        <g>
          <path d="M 86 -48 L 96 -30 L 78 -36 Z" fill="#22d3ee" />
          <path d="M 234 -48 L 242 -36 L 224 -30 Z" fill="#22d3ee" opacity="0.85" />
        </g>
      )}
      {mood === "wow" && (
        <g>
          <rect x="110" y="-56" width="15" height="36" rx="7" fill="#facc15" transform="rotate(-9 117 -38)" />
          <circle cx="114" cy="-8" r="6" fill="#facc15" />
          <rect x="194" y="-60" width="15" height="40" rx="7" fill="#facc15" transform="rotate(11 201 -40)" />
          <circle cx="200" cy="-8" r="6" fill="#facc15" />
          <g stroke="#facc15" strokeWidth="4" strokeLinecap="round">
            <path d="M 146 -16 L 136 -30" />
            <path d="M 174 -16 L 184 -30" />
          </g>
        </g>
      )}
      {mood === "meh" && (
        <g fill="#64748b">
          <circle cx="128" cy="-18" r="6" />
          <circle cx="160" cy="-18" r="6" />
          <circle cx="192" cy="-18" r="6" />
        </g>
      )}
      {mood === "money" && (
        <g>
          <text x="108" y="-16" textAnchor="middle" fontFamily="Consolas, 'Courier New', monospace"
            fontSize="44" fontWeight="700" fill="#facc15" transform="rotate(-12 108 -32)">$</text>
          <text x="212" y="-26" textAnchor="middle" fontFamily="Consolas, 'Courier New', monospace"
            fontSize="34" fontWeight="700" fill="#f59e0b" transform="rotate(14 212 -38)">$</text>
          <circle cx="254" cy="-14" r="7" fill="none" stroke="#facc15" strokeWidth="3" />
          <circle cx="68" cy="-22" r="5" fill="none" stroke="#f59e0b" strokeWidth="3" />
        </g>
      )}
      {mood === "dead" && (
        <g>
          <g stroke="#64748b" strokeWidth="6" strokeLinecap="round">
            <path d="M 104 -46 L 126 -24" />
            <path d="M 126 -46 L 104 -24" />
            <path d="M 194 -46 L 216 -24" />
            <path d="M 216 -46 L 194 -24" />
          </g>
          <path d="M 160 -4 Q 150 -20 160 -34 Q 170 -48 160 -62" fill="none"
            stroke="rgba(148,163,184,0.65)" strokeWidth="4" strokeLinecap="round" />
        </g>
      )}
      {mood === "huh" && (
        <g>
          <text x="106" y="-12" textAnchor="middle" fontFamily="Consolas, 'Courier New', monospace"
            fontSize="48" fontWeight="700" fill="#22d3ee" transform="rotate(-10 106 -30)">?</text>
          <text x="214" y="-28" textAnchor="middle" fontFamily="Consolas, 'Courier New', monospace"
            fontSize="32" fontWeight="700" fill="#7dd3fc" transform="rotate(12 214 -40)">?</text>
        </g>
      )}

      {/* 头:方屏大脸 */}
      <rect x="50" y="46" width="220" height="168" rx="24" fill="#050810" stroke="#22d3ee" strokeWidth="5" filter={`url(#${glowId})`} />
      <rect x="66" y="62" width="188" height="136" rx="10" fill="#0a1428" stroke="rgba(34,211,238,0.35)" strokeWidth="2" />
      <g stroke="rgba(34,211,238,0.10)" strokeWidth="3">
        <line x1="66" y1="84" x2="254" y2="84" />
        <line x1="66" y1="108" x2="254" y2="108" />
        <line x1="66" y1="132" x2="254" y2="132" />
        <line x1="66" y1="156" x2="254" y2="156" />
      </g>

      {/* ======== 表情层(互斥) ======== */}
      {mood === "smile" && (
        <g>
          <g stroke="#22d3ee" strokeWidth="7" strokeLinecap="round">
            <path d="M 100 96 L 138 90" fill="none" />
            <path d="M 182 90 L 220 96" fill="none" />
          </g>
          <rect x="108" y="100" width="36" height="40" rx="12" fill="#22d3ee" filter={`url(#${glowId})`} />
          <rect x="120" y="114" width="14" height="16" rx="4" fill="#06202a" />
          <rect x="176" y="100" width="36" height="40" rx="12" fill="#22d3ee" filter={`url(#${glowId})`} />
          <rect x="188" y="114" width="14" height="16" rx="4" fill="#06202a" />
          {!talking && (
            <path d="M 130 150 Q 160 166 190 150" fill="none" stroke="#22d3ee" strokeWidth="7" strokeLinecap="round" />
          )}
        </g>
      )}
      {mood === "wow" && (
        <g>
          <g stroke="#22d3ee" strokeWidth="7" strokeLinecap="round" fill="none">
            <path d="M 100 84 Q 120 76 138 82" />
            <path d="M 182 82 Q 200 76 220 84" />
          </g>
          <circle cx="126" cy="120" r="17" fill="#22d3ee" filter={`url(#${glowId})`} />
          <circle cx="126" cy="124" r="6" fill="#06202a" />
          <circle cx="194" cy="120" r="17" fill="#22d3ee" filter={`url(#${glowId})`} />
          <circle cx="194" cy="124" r="6" fill="#06202a" />
          {!talking && (
            <ellipse cx="160" cy="158" rx="11" ry="12" fill="none" stroke="#22d3ee" strokeWidth="6" />
          )}
        </g>
      )}
      {mood === "meh" && (
        <g>
          <g stroke="#22d3ee" strokeWidth="7" strokeLinecap="round">
            <path d="M 100 92 L 138 98" fill="none" />
            <path d="M 182 98 L 220 92" fill="none" />
          </g>
          <rect x="108" y="112" width="36" height="20" rx="8" fill="#22d3ee" />
          <rect x="176" y="112" width="36" height="20" rx="8" fill="#22d3ee" />
          {!talking && (
            <path d="M 138 156 L 182 156" stroke="#22d3ee" strokeWidth="7" strokeLinecap="round" />
          )}
        </g>
      )}
      {mood === "money" && (
        <g>
          <g stroke="#22d3ee" strokeWidth="7" strokeLinecap="round">
            <path d="M 100 90 L 138 84" fill="none" />
            <path d="M 182 84 L 220 90" fill="none" />
          </g>
          <rect x="108" y="96" width="36" height="44" rx="12" fill="#22d3ee" filter={`url(#${glowId})`} />
          <text x="126" y="131" textAnchor="middle" fontFamily="Consolas, 'Courier New', monospace"
            fontSize="30" fontWeight="700" fill="#06202a">$</text>
          <rect x="176" y="96" width="36" height="44" rx="12" fill="#22d3ee" filter={`url(#${glowId})`} />
          <text x="194" y="131" textAnchor="middle" fontFamily="Consolas, 'Courier New', monospace"
            fontSize="30" fontWeight="700" fill="#06202a">$</text>
          {!talking && (
            <path d="M 126 148 Q 160 166 194 148" fill="none" stroke="#22d3ee" strokeWidth="7" strokeLinecap="round" />
          )}
        </g>
      )}
      {mood === "dead" && (
        <g>
          <g stroke="#22d3ee" strokeWidth="7" strokeLinecap="round">
            <path d="M 100 96 L 138 100" fill="none" />
            <path d="M 182 100 L 220 96" fill="none" />
            <path d="M 110 112 L 142 144" fill="none" />
            <path d="M 142 112 L 110 144" fill="none" />
            <path d="M 178 112 L 210 144" fill="none" />
            <path d="M 210 112 L 178 144" fill="none" />
          </g>
          {!talking && (
            <path d="M 132 158 Q 146 150 160 158 Q 174 166 188 158" fill="none" stroke="#22d3ee" strokeWidth="6" strokeLinecap="round" />
          )}
        </g>
      )}
      {mood === "huh" && (
        <g>
          <g stroke="#22d3ee" strokeWidth="7" strokeLinecap="round">
            <path d="M 100 86 L 138 80" fill="none" />
            <path d="M 182 96 L 220 94" fill="none" />
          </g>
          <rect x="108" y="100" width="36" height="40" rx="12" fill="#22d3ee" filter={`url(#${glowId})`} />
          <rect x="120" y="114" width="14" height="16" rx="4" fill="#06202a" />
          <rect x="176" y="112" width="36" height="22" rx="9" fill="#22d3ee" />
          {!talking && (
            <path d="M 138 160 L 182 152" stroke="#22d3ee" strokeWidth="6" strokeLinecap="round" />
          )}
          <text x="234" y="106" textAnchor="middle" fontFamily="Consolas, 'Courier New', monospace"
            fontSize="26" fontWeight="700" fill="#22d3ee" filter={`url(#${glowId})`}>?</text>
        </g>
      )}

      {/* 讲话态:波形条即嘴(占嘴位带 y146-198,表情嘴此时隐去——互斥不并存) */}
      {talking && (
        <g>
          <rect x="94" y="146" width="132" height="52" rx="10" fill="#041018" stroke="rgba(34,211,238,0.4)" strokeWidth="2" />
          {[0, 1, 2, 3, 4, 5, 6].map((i) => {
            const cx = 108 + i * 17;
            const h = barHeight(frame, i);
            return (
              <rect key={i} x={cx - 3.5} y={172 - h / 2} width="7" height={h} rx="3" fill="#22d3ee" opacity="0.95" />
            );
          })}
        </g>
      )}

      {/* 颈 */}
      <rect x="146" y="214" width="28" height="18" fill="rgba(34,211,238,0.6)" />

      {/* 躯干 */}
      <rect x="94" y="232" width="132" height="96" rx="14" fill="#050810" stroke="#22d3ee" strokeWidth="5" filter={`url(#${glowId})`} />
      <rect x="104" y="270" width="6" height="22" rx="3" fill="rgba(34,211,238,0.4)" />
      <rect x="210" y="270" width="6" height="22" rx="3" fill="rgba(34,211,238,0.4)" />

      {/* 挂脖工牌:品牌恒显 */}
      <path d="M 126 226 L 136 256" stroke="#22d3ee" strokeWidth="4" strokeLinecap="round" />
      <path d="M 194 226 L 184 256" stroke="#22d3ee" strokeWidth="4" strokeLinecap="round" />
      <rect x="116" y="256" width="88" height="68" rx="9" fill="#0a1428" stroke="#22d3ee" strokeWidth="3.5" filter={`url(#${glowId})`} />
      <line x1="116" y1="270" x2="204" y2="270" stroke="rgba(34,211,238,0.35)" strokeWidth="2" />
      <circle cx="129" cy="263" r="3.5" fill="#ff5f56" />
      <circle cx="140" cy="263" r="3.5" fill="#ffbd2e" />
      <circle cx="151" cy="263" r="3.5" fill="#27c93f" />
      <text x="160" y="292" textAnchor="middle" fontFamily="Consolas, 'Courier New', monospace"
        fontSize="21" fontWeight="700" fill="#22d3ee">1024</text>
      <text x="160" y="313" textAnchor="middle" fontFamily="'Microsoft YaHei', '微软雅黑', sans-serif"
        fontSize="16" fontWeight="700" fill="#7dd3fc" letterSpacing="3">工程笔记</text>

      {/* ======== 姿态层(手臂组,互斥) ======== */}
      {pose === "wave" && (
        <g>
          <path d="M 94 246 Q 58 272 54 306" fill="none" stroke="#22d3ee" strokeWidth="8" strokeLinecap="round" />
          <circle cx="54" cy="312" r="11" fill="#050810" stroke="#22d3ee" strokeWidth="5" />
          <path d="M 226 244 Q 266 226 282 192" fill="none" stroke="#22d3ee" strokeWidth="8" strokeLinecap="round" />
          <circle cx="285" cy="186" r="11" fill="#050810" stroke="#22d3ee" strokeWidth="5" />
          <path d="M 296 168 Q 304 178 300 190" fill="none" stroke="rgba(34,211,238,0.5)" strokeWidth="3" strokeLinecap="round" />
          <path d="M 306 158 Q 318 172 312 188" fill="none" stroke="rgba(34,211,238,0.35)" strokeWidth="3" strokeLinecap="round" />
        </g>
      )}
      {pose === "point" && (
        <g>
          <path d="M 94 246 Q 58 272 54 306" fill="none" stroke="#22d3ee" strokeWidth="8" strokeLinecap="round" />
          <circle cx="54" cy="312" r="11" fill="#050810" stroke="#22d3ee" strokeWidth="5" />
          <path d="M 226 242 Q 260 214 292 188" fill="none" stroke="#22d3ee" strokeWidth="8" strokeLinecap="round" />
          <circle cx="296" cy="184" r="11" fill="#050810" stroke="#22d3ee" strokeWidth="5" />
          <path d="M 303 177 L 316 164" stroke="#e2f7fb" strokeWidth="4" strokeLinecap="round" />
        </g>
      )}
      {pose === "cheer" && (
        <g>
          <path d="M 94 244 Q 60 216 46 188" fill="none" stroke="#22d3ee" strokeWidth="8" strokeLinecap="round" />
          <circle cx="44" cy="182" r="11" fill="#050810" stroke="#22d3ee" strokeWidth="5" />
          <path d="M 32 164 Q 38 174 35 184" fill="none" stroke="rgba(34,211,238,0.5)" strokeWidth="3" strokeLinecap="round" />
          <path d="M 226 244 Q 266 216 282 186" fill="none" stroke="#22d3ee" strokeWidth="8" strokeLinecap="round" />
          <circle cx="285" cy="180" r="11" fill="#050810" stroke="#22d3ee" strokeWidth="5" />
          <path d="M 296 162 Q 304 172 300 184" fill="none" stroke="rgba(34,211,238,0.5)" strokeWidth="3" strokeLinecap="round" />
        </g>
      )}

      {/* 双腿 + 靴子 */}
      <rect x="118" y="328" width="26" height="36" rx="10" fill="#050810" stroke="#22d3ee" strokeWidth="4" />
      <rect x="176" y="328" width="26" height="36" rx="10" fill="#050810" stroke="#22d3ee" strokeWidth="4" />
      <rect x="110" y="362" width="44" height="20" rx="10" fill="#050810" stroke="#22d3ee" strokeWidth="5" />
      <rect x="166" y="362" width="44" height="20" rx="10" fill="#050810" stroke="#22d3ee" strokeWidth="5" />
    </svg>
  );
};
