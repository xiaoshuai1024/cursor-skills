import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";

/**
 * CameraPath - 摄像机路径动画封装。
 *
 * 视觉:通过反向移动场景根节点来模拟摄像机移动(避免 useThree 上下文问题)。
 *
 * 用法:
 * - 把场景内容放在 <CameraPath><group>...</group></CameraPath> 内
 * - CameraPath 会反向应用变换,产生摄像机移动效果
 *
 * 实现:
 * - 接受关键帧数组 [{frame, position, lookAt, fov}, ...]
 * - 用 Remotion 的 interpolate 做分段插值
 * - 返回一个 group,其 position/rotation 是摄像机变换的"反向"
 */

interface CameraKeyframe {
  frame: number;
  position?: [number, number, number];
  lookAt?: [number, number, number];
  fov?: number;
}

interface CameraPathProps {
  keyframes: CameraKeyframe[];
  children: React.ReactNode;
}

export const CameraPath: React.FC<CameraPathProps> = ({
  keyframes,
  children,
}) => {
  const frame = useCurrentFrame();

  if (keyframes.length === 0) return <>{children}</>;

  // 找当前帧落在哪两个关键帧之间
  let fromIdx = 0;
  for (let i = 0; i < keyframes.length - 1; i++) {
    if (frame >= keyframes[i].frame && frame < keyframes[i + 1].frame) {
      fromIdx = i;
      break;
    }
    if (frame >= keyframes[keyframes.length - 1].frame) {
      fromIdx = keyframes.length - 1;
    }
  }

  const from = keyframes[fromIdx];
  const to = keyframes[Math.min(fromIdx + 1, keyframes.length - 1)];
  const duration = to.frame - from.frame;
  const progress = duration === 0 ? 1 : (frame - from.frame) / duration;

  // 平滑插值(ease-in-out)
  const t = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;

  // 位置插值(反向,模拟摄像机移动)
  const fromPos = from.position ?? [0, 0, 0];
  const toPos = to.position ?? [0, 0, 0];
  const pos = [
    -(fromPos[0] + (toPos[0] - fromPos[0]) * t),
    -(fromPos[1] + (toPos[1] - fromPos[1]) * t),
    -(fromPos[2] + (toPos[2] - fromPos[2]) * t),
  ] as [number, number, number];

  return <group position={pos}>{children}</group>;
};
