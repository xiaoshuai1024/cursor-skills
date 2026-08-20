import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

/**
 * TransitionFrame - 场景转场容器（替代 Scene3DFrame）。
 *
 * 设计哲学:转场 = 场景头部入场动画 + 尾部出场动画,时序不变、总时长不变、
 * 字幕绝对帧号严格对齐。视觉上相邻场景"前卡尾部退场 + 后卡头部入场"同时
 * 发生,等效于常见剪辑软件的交叉转场观感。
 *
 * 借鉴 HyperFrames 的转场手法(甩镜/闪白/故障/漏光/涟漪/交叉扭曲),
 * 但全部翻译成 useCurrentFrame 数学驱动(禁 CSS animation / wall-clock)。
 *
 * 时间语义（对齐原 Scene3DFrame）:
 *   enterT = frame / transitionFrames       头部 transitionFrames 帧内 0→1
 *   exitT  = (duration - frame) / transitionFrames  尾部 transitionFrames 帧内 1→0
 *   enter  = ease(enterT)                   入场进度 0→1（头部活跃）
 *   exit   = ease(1 - exitT)                退场进度 0→1（尾部活跃）
 * 头部: enter 0→1 且 exit=0;中部: 两项都静止;尾部: exit 0→1。
 *
 * transitionType 列表:
 *   rotate3d   3D 翻入翻出(默认,原有 Scene3DFrame 行为)
 *   fade       淡入淡出
 *   slide      右侧滑入 / 左侧滑出(可改 slideRight)
 *   wipe       从左揭示 / 向右关闭(可改 wipeUp)
 *   flip       卡片翻页
 *   clockWipe  钟表扫入
 *   iris       圆形光圈展开
 *   pushCut    闪切(白闪脉冲 + 快速淡入)
 *   glitch     数字故障抖动(确定性伪随机)
 *   flash      闪白进场 / 闪白退场
 *   whipPan    甩镜(横向甩入 + 拉伸模糊)
 *   lightLeak  暖色漏光扫过
 *   ripple     涟漪弹性入场
 *   crossWarp  交叉扭曲位移
 */

/** easeOutCubic:1-(1-t)^3 */
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
/** easeOutBack(1.7):弹性回弹 */
const easeOutBack = (t: number) => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};
/** 确定性伪随机(frame 播种,禁 Math.random):0~1 */
const seededRand = (seed: number) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
};

export type TransitionType =
  | "rotate3d" | "fade" | "slide" | "slideRight" | "wipe" | "wipeUp"
  | "flip" | "clockWipe" | "iris" | "pushCut" | "glitch"
  | "flash" | "whipPan" | "lightLeak" | "ripple" | "crossWarp";

export const TRANSITION_TYPES: TransitionType[] = [
  "rotate3d", "fade", "slide", "slideRight", "wipe", "wipeUp", "flip",
  "clockWipe", "iris", "pushCut", "glitch", "flash", "whipPan",
  "lightLeak", "ripple", "crossWarp",
];

const TransitionFrame: React.FC<{
  transitionType: string;
  transitionFrames: number;
  durationInFrames: number;
  children: React.ReactNode;
}> = ({ transitionType, transitionFrames, durationInFrames, children }) => {
  const frame = useCurrentFrame();

  if (transitionFrames <= 0) return <>{children}</>;

  // 时间语义:enterT 头部 0→1;exitT 尾部 1→0(与原 Scene3DFrame 一致)
  const enterT = Math.min(1, frame / transitionFrames);
  const exitT = Math.min(1, (durationInFrames - frame) / transitionFrames);
  // enter 入场进度(头部活跃,0→1);exit 退场进度(尾部活跃,0→1)
  const enter = easeOutCubic(enterT);
  const exit = easeOutCubic(1 - exitT);

  const style: React.CSSProperties = {};
  let overlay: React.ReactNode = null;

  switch (transitionType) {
    case "fade": {
      style.opacity = enter * (1 - exit);
      break;
    }
    case "slide":
    case "slideRight": {
      const dir = transitionType === "slideRight" ? -1 : 1;
      // 头部从右滑入(enter 0→1);尾部向左滑出(exit 0→1)
      style.transform = `translateX(${dir * 100 * (1 - enter) - dir * 100 * exit}%)`;
      break;
    }
    case "wipe":
    case "wipeUp": {
      const horizontal = transitionType === "wipe";
      // enter:从左/下揭示(inset 右边距缩小);exit:向右/上关闭
      if (horizontal) {
        style.clipPath = `inset(0 ${(1 - enter) * 100}% 0 ${exit * 100}%)`;
      } else {
        style.clipPath = `inset(${exit * 100}% 0 ${(1 - enter) * 100}% 0)`;
      }
      break;
    }
    case "flip": {
      const rot = 90 * (1 - easeOutBack(enter)) - 90 * easeOutBack(exit);
      style.transform = `perspective(1200px) rotateY(${rot}deg)`;
      style.transformStyle = "preserve-3d";
      style.backfaceVisibility = "hidden";
      style.opacity = enter * (1 - exit);
      break;
    }
    case "clockWipe": {
      // 钟表扫入:conic-gradient 从 0° 展开;退场用黑层从底部收起
      overlay = (
        <AbsoluteFill
          style={{
            background: `conic-gradient(from 0deg, transparent ${(1 - enter) * 100}%, rgba(0,0,0,0.35) 0)`,
          }}
        />
      );
      style.clipPath = `polygon(0 0, 100% 0, 100% ${(1 - exit) * 100}%, 0 ${(1 - exit) * 100}%)`;
      break;
    }
    case "iris": {
      const r = 141; // 对角线半长 %,足够覆盖 16:9
      // 头部光圈展开;尾部黑圈收起
      style.clipPath = `circle(${(1 - enter) * r}% at 50% 50%)`;
      if (exit > 0) {
        overlay = (
          <AbsoluteFill
            style={{
              clipPath: `circle(${(1 - exit) * r}% at 50% 50%)`,
              backgroundColor: "#0a0e1a",
            }}
          />
        );
      }
      break;
    }
    case "pushCut": {
      // 闪切:进入前 3 帧白闪 + 快速淡入;退场尾部白闪
      const enterFlash = enterT < 0.25 ? 1 - enterT * 4 : 0;
      const exitFlash = exit > 0.8 ? (exit - 0.8) * 5 : 0;
      style.opacity = enter * (1 - exit);
      if (enterFlash > 0 || exitFlash > 0) {
        overlay = (
          <AbsoluteFill style={{ backgroundColor: "#ffffff", opacity: Math.max(enterFlash, exitFlash) }} />
        );
      }
      break;
    }
    case "glitch": {
      // 抖动窗口:头部进入 60% + 尾部退出 60%,中间稳定
      const headGlitch = enter < 0.6 ? 1 - enter / 0.6 : 0;
      const tailGlitch = exit > 0.4 ? (exit - 0.4) / 0.6 : 0;
      const jitter = Math.max(headGlitch, tailGlitch);
      const s = Math.floor(frame / 3) * 3;
      const dx = (seededRand(s) - 0.5) * 12 * jitter;
      const dy = (seededRand(s + 1) - 0.5) * 8 * jitter;
      const skew = (seededRand(s + 2) - 0.5) * 6 * jitter;
      style.transform = `translate(${dx}px, ${dy}px) skewX(${skew}deg)`;
      // RGB 分离色条(不复制 children,避免 3 倍渲染开销)
      if (jitter > 0.15) {
        const shift = 3 * jitter;
        overlay = (
          <AbsoluteFill style={{ mixBlendMode: "screen", opacity: 0.5 * jitter, pointerEvents: "none" }}>
            <div
              style={{
                position: "absolute",
                top: `${seededRand(s + 4) * 60 + 10}%`,
                height: `${8 + seededRand(s + 5) * 18}%`,
                left: 0,
                right: 0,
                background: "rgba(255,0,60,0.5)",
                transform: `translateX(${-shift}px)`,
              }}
            />
            <div
              style={{
                position: "absolute",
                top: `${seededRand(s + 6) * 60 + 10}%`,
                height: `${8 + seededRand(s + 7) * 18}%`,
                left: 0,
                right: 0,
                background: "rgba(0,255,255,0.5)",
                transform: `translateX(${shift}px)`,
              }}
            />
          </AbsoluteFill>
        );
      }
      break;
    }
    case "flash": {
      // flash-through-white:进场白层 1→0(从白中显形);退场白层 0→1(隐入白)
      const white = Math.max(1 - enter, exit);
      overlay = (
        <AbsoluteFill style={{ backgroundColor: "#ffffff", opacity: white }} />
      );
      break;
    }
    case "whipPan": {
      const x = 60 * (1 - enter) - 60 * exit;
      const stretch = 1.15 - 0.15 * enter + 0.15 * exit;
      style.transform = `translateX(${x}%) scaleX(${stretch})`;
      style.filter = `blur(${3 * (1 - Math.min(enter, 1 - exit))}px)`;
      break;
    }
    case "lightLeak": {
      // 暖色漏光从左上扫到右下(进场),退场反向
      const pos = Math.max(enter, exit) * 130 - 20;
      overlay = (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at ${pos}% 30%, rgba(255,180,80,0.35), transparent 55%)`,
            mixBlendMode: "screen",
          }}
        />
      );
      break;
    }
    case "ripple": {
      // 涟漪:弹性缩放入场 + 轻微正弦缩放;退场放大淡出
      const s = 0.9 + 0.1 * easeOutBack(enter);
      const wave = 1 + 0.025 * Math.sin(enter * Math.PI * 6) * (1 - enter);
      const exitS = 1 + 0.1 * easeOutBack(exit);
      style.transform = `scale(${s * wave * exitS})`;
      style.opacity = enter * (1 - exit);
      break;
    }
    case "crossWarp": {
      // 交叉扭曲:双方向位移错位 + 轻微缩放 + 饱和度增强
      const x = -4 * (1 - enter) + 4 * exit;
      const s = (1.04 - 0.04 * enter) * (1 + 0.04 * exit);
      style.transform = `translateX(${x}%) scale(${s})`;
      style.filter = `saturate(${1 + 0.3 * (1 - Math.min(enter, 1 - exit))})`;
      break;
    }
    case "rotate3d":
    default: {
      // 原有 Scene3DFrame 行为（逐字复刻，保证现有视频零回归）:
      // 翻入 rotateY 60°→0 scale 0.9→1;翻出 0→-60° scale 1→0.9
      const enterEased = 1 - Math.pow(1 - enterT, 3);
      const exitEased = 1 - Math.pow(1 - exitT, 3);
      const rotY = 60 * (1 - enterEased) - 60 * (1 - exitEased);
      const scale = 0.9 + 0.1 * enterEased - 0.1 * exitEased;
      style.transform = `rotateY(${rotY}deg) scale(${scale})`;
      style.transformStyle = "preserve-3d";
      style.backfaceVisibility = "hidden";
      style.opacity = Math.min(enterEased, exitEased) * 0.999;
      break;
    }
  }

  return (
    <AbsoluteFill style={{ perspective: 1200 }}>
      <AbsoluteFill style={style}>{children}</AbsoluteFill>
      {overlay}
    </AbsoluteFill>
  );
};

export default TransitionFrame;
