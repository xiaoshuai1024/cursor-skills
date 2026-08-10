import React from "react";
import { useCurrentFrame } from "remotion";

/**
 * TimedLayer - 在指定帧区间内淡入内容。
 *
 * 用途:内容场景的"逐层揭示"——每个 layer 在特定时间窗口出现,避免一次全显。
 *
 * Props:
 * - startFrame: 开始淡入的帧
 * - duration: 从 startFrame 起,内容保持可见的总帧数;之后淡出
 * - fadeFrames: 淡入/淡出过渡帧数(默认 15,约 0.25s @ 60fps)
 * - children: 淡入的内容
 */
interface TimedLayerProps {
  startFrame: number;
  duration: number;
  fadeFrames?: number;
  children: React.ReactNode;
}

export const TimedLayer: React.FC<TimedLayerProps> = ({
  startFrame,
  duration,
  fadeFrames = 15,
  children,
}) => {
  const frame = useCurrentFrame();
  const relativeFrame = frame - startFrame;

  // 窗口外不可见
  if (relativeFrame < 0 || relativeFrame > duration) return null;

  // 淡入
  let opacity: number;
  if (relativeFrame < fadeFrames) {
    opacity = relativeFrame / fadeFrames;
  }
  // 淡出
  else if (relativeFrame > duration - fadeFrames) {
    opacity = (duration - relativeFrame) / fadeFrames;
  }
  // 全可见
  else {
    opacity = 1;
  }

  return (
    <div style={{ opacity, position: "absolute", inset: 0 }}>
      {children}
    </div>
  );
};
