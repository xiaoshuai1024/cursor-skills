import React from "react";
import { useCurrentFrame } from "remotion";
import { MascotFigure, type MascotPose } from "./MascotFigure";
import { moodAtFrame, DEFAULT_MOOD, type MoodPoint } from "../core/mascot-mood";
import type { SubtitleEntry } from "../core/types";

/**
 * MascotCompanion - 形象伴随层:终端小子全片常驻,跟口播时间轴随动。
 *
 * 三层随动(设计 D3,全部帧号驱动、渲染确定):
 * - 待机浮动:sin bob + 容器辉光呼吸(全片不间断。2026-08-24 调参:bob ±6→±10px、
 *   周期 5.8→4.2s、辉光 4-12→2-18px——旧幅度在手机端缩放后不可感知,用户反馈「特效不明显」)
 * - 段落反应:每个字幕段边界 0.4s 内一次微动作,模式按段索引 %3 轮换
 *   (点头/摆头/微跳),sin 包络起落,不与下一反应叠加
 * - 讲话态:当前段进行中 MascotFigure talking=true(波形条替代嘴翻动——波形即讲话标志,
 *   静默时恢复表情嘴,两者互斥不并存)
 *
 * 表情:moodAtFrame 自动推断 + moodTimeline 手工覆盖(core/mascot-mood)。
 * 姿态:默认 wave;命中强调(emphasisFrames 或重点关键词段)切 point ≥1s。
 *
 * Props 由 VideoComposition 按 DEFAULT_MASCOT 浅合并后传入。
 */
const REACT_FRAMES = 30; // 段落反应时长 0.5s @60fps(2026-08-24: 24→30,加长更易感知)
const POINT_HOLD_FRAMES = 60; // 强调指屏保持 ≥1s
const EMPHASIS_WORDS = ["记住", "重点", "关键是", "核心是", "结论", "总结", "一句话"];

interface MascotCompanionProps {
  subtitles: SubtitleEntry[];
  height: number;
  position: "bottom-right" | "bottom-left";
  moodTimeline?: MoodPoint[];
  autoMood?: boolean;
  reactToSegments?: boolean;
  /** 强调帧(通常透传 sfx.emphasisFrames),命中切 point 姿态 */
  emphasisFrames?: number[];
}

/** 段边界反应:返回附加 transform(叠加在待机 bob 之上) */
const segmentReaction = (
  frame: number,
  subtitles: SubtitleEntry[],
): { dx: number; dy: number; rotate: number; scale: number } => {
  // 找最近一个已开始的段(字幕按 startFrame 升序)
  let idx = -1;
  for (let i = 0; i < subtitles.length; i++) {
    if (subtitles[i].startFrame <= frame) idx = i;
    else break;
  }
  if (idx < 0) return { dx: 0, dy: 0, rotate: 0, scale: 1 };
  const dt = frame - subtitles[idx].startFrame;
  if (dt >= REACT_FRAMES) return { dx: 0, dy: 0, rotate: 0, scale: 1 };
  const env = Math.sin((Math.PI * dt) / REACT_FRAMES); // 起落包络
  switch (idx % 3) {
    case 0: // 点头:下压回弹
      return { dx: 0, dy: env * 16, rotate: 0, scale: 1 };
    case 1: // 摆头:左右小角度
      return { dx: 0, dy: 0, rotate: env * 8 * (idx % 2 ? 1 : -1), scale: 1 };
    default: // 微跳:缩放+上移
      return { dx: 0, dy: -env * 18, rotate: 0, scale: 1 + env * 0.08 };
  }
};

/** 强调姿态判定:emphasisFrames 命中(保持 ≥1s)或当前段含重点词 */
const poseAtFrame = (
  frame: number,
  subtitles: SubtitleEntry[],
  emphasisFrames?: number[],
): MascotPose => {
  if (emphasisFrames?.some((ef) => ef <= frame && frame < ef + POINT_HOLD_FRAMES)) {
    return "point";
  }
  const seg = subtitles.find((s) => s.startFrame <= frame && frame < s.endFrame);
  if (seg && EMPHASIS_WORDS.some((w) => seg.text.includes(w))) return "point";
  return "wave";
};

export const MascotCompanion: React.FC<MascotCompanionProps> = ({
  subtitles,
  height,
  position,
  moodTimeline,
  autoMood = true,
  reactToSegments = true,
  emphasisFrames,
}) => {
  const frame = useCurrentFrame();

  // 待机浮动:呼吸 bob + 辉光脉冲(幅度加大,手机端可感知)
  const bobY = Math.sin(frame / 40) * 10;
  const glow = 10 + 8 * Math.sin(frame / 32);

  // 段落反应(可关)
  const react = reactToSegments
    ? segmentReaction(frame, subtitles)
    : { dx: 0, dy: 0, rotate: 0, scale: 1 };

  // 表情 + 切换帧小弹跳:回看 ≤12 帧找切换点,sin 包络起落(帧驱动确定)
  const hasTimeline = subtitles.length > 0 || (moodTimeline?.length ?? 0) > 0;
  const mood = hasTimeline
    ? moodAtFrame(frame, subtitles, { moodTimeline, autoMood })
    : DEFAULT_MOOD;
  let popScale = 1;
  if (hasTimeline) {
    for (let back = 1; back <= 12; back++) {
      const fPrev = frame - back;
      if (fPrev < 0) break;
      if (moodAtFrame(fPrev, subtitles, { moodTimeline, autoMood }) !== mood) {
        popScale = 1 + 0.12 * Math.sin((Math.PI * (back - 1)) / 12);
        break;
      }
    }
  }

  const pose = poseAtFrame(frame, subtitles, emphasisFrames);
  const talking = subtitles.some((s) => s.startFrame <= frame && frame < s.endFrame);

  const corner =
    position === "bottom-left" ? { left: 48, bottom: 36 } : { right: 48, bottom: 36 };

  return (
    <div
      style={{
        position: "absolute",
        ...corner,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          transform: `translate(${react.dx}px, ${bobY + react.dy}px) rotate(${react.rotate}deg) scale(${react.scale * popScale})`,
          transformOrigin: "50% 90%",
          filter: `drop-shadow(0 0 ${glow}px rgba(34, 211, 238, 0.35))`,
        }}
      >
        <MascotFigure mood={mood} pose={pose} talking={talking} height={height} />
      </div>
    </div>
  );
};
