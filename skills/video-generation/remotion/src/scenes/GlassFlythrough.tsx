import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";
import { GlassPanel } from "../primitives/GlassPanel";
import { CameraPath } from "../primitives/CameraPath";

/**
 * GlassFlythrough - 摄像机穿梭穿过玻璃层。
 *
 * 视觉:多层 GlassPanel 沿 z 轴排列,摄像机穿梭穿过,每层显示 attention 光线。
 * 用途:隐喻"Transformer 层 / 多层处理 / 深度分析"。
 *
 * Props:
 * - layerCount: 玻璃层数(默认 5)
 * - attentionLines: 每层的连线数(默认 3)
 */

interface GlassFlythroughProps {
  layerCount?: number;
  attentionLines?: number;
}

const GlassFlythrough: React.FC<GlassFlythroughProps> = ({
  layerCount = 5,
  attentionLines = 3,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 每层 z 位置(从 0 到 -40,均匀分布)
  const layerPositions = Array.from({ length: layerCount }, (_, i) => -i * 8);

  // 摄像机路径:从 z=10 推进到 z=-40(穿过所有层)
  const totalFrames = 420; // 7 秒 @ 60fps
  const cameraPath = [
    { frame: 0, position: [0, 0, 10] as [number, number, number] },
    {
      frame: totalFrames,
      position: [0, 0, -40] as [number, number, number],
    },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <ThreeCanvas
        camera={{ position: [0, 0, 10], fov: 60 }}
        width={1920}
        height={1080}
        style={{ position: "absolute", inset: 0 }}
      >
        <ambientLight intensity={0.3} />
        <pointLight position={[10, 10, 10]} intensity={0.8} />

        <CameraPath keyframes={cameraPath}>
          {layerPositions.map((z, i) => (
            <GlassPanel
              key={i}
              width={10}
              height={7}
              opacity={0.15}
              position={[0, 0, z]}
              edgeColor={theme.colors.accent}
            />
          ))}
        </CameraPath>
      </ThreeCanvas>
    </AbsoluteFill>
  );
};

registerScene("GlassFlythrough", GlassFlythrough);
