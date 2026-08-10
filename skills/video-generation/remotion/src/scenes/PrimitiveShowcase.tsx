import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";
import { ParticleField } from "../primitives/ParticleField";
import { NeonText } from "../primitives/NeonText";
import { GlassPanel } from "../primitives/GlassPanel";
import { Scanline } from "../primitives/Scanline";
import { CameraPath } from "../primitives/CameraPath";

/**
 * PrimitiveShowcase - 用于验证 5 个原语可编译、可渲染。
 *
 * 时间轴(12 秒 = 720 帧 @ 60fps):
 * - 0-6s: ParticleField 背景(独立层) + NeonText 标题
 * - 3-9s: GlassPanel + CameraPath 推进(Three.js 层)
 * - 6-9s: Scanline 揭示效果
 * - 9-12s: 组合展示
 *
 * 结构:
 * - ParticleField 作为独立的 ThreeCanvas 覆盖层(背景粒子)
 * - GlassPanel 在另一个 ThreeCanvas 内(配合 CameraPath)
 * - NeonText / Scanline 是纯 2D
 */

const GlassLayer: React.FC = () => {
  const theme = getCurrentTheme();

  return (
    <ThreeCanvas
      camera={{ position: [0, 0, 15], fov: 60 }}
      width={1920}
      height={1080}
      style={{ position: "absolute", inset: 0 }}
    >
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />

      {/* 摄像机路径:通过反向移动 group 模拟 */}
      <CameraPath
        keyframes={[
          { frame: 0, position: [0, 0, 15] },
          { frame: 360, position: [0, 0, 5] },
          { frame: 720, position: [2, 1, 8] },
        ]}
      >
        <GlassPanel width={6} height={4} opacity={0.2} position={[0, 0, -2]} />
        <GlassPanel
          width={4}
          height={3}
          opacity={0.15}
          position={[-2, 1, -5]}
          rotation={[0, 0.3, 0]}
        />
        <GlassPanel
          width={3}
          height={2}
          opacity={0.1}
          position={[3, -1, -8]}
          rotation={[0, -0.2, 0]}
        />
      </CameraPath>
    </ThreeCanvas>
  );
};

const PrimitiveShowcase: React.FC = () => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const scanProgress = Math.min(1, Math.max(0, (frame - 360) / 180));

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      {/* 背景粒子层(独立 ThreeCanvas,始终存在) */}
      <ParticleField count={300} volumeSize={25} />

      {/* 玻璃板层(独立 ThreeCanvas,前 9 秒) */}
      <Sequence from={0} durationInFrames={540}>
        <GlassLayer />
      </Sequence>

      {/* 2D 叠加:NeonText 标题(前 6 秒) */}
      <Sequence from={0} durationInFrames={360}>
        <AbsoluteFill
          style={{
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <NeonText text="PRIMITIVES" fontSize={120} glowIntensity={1.2} />
          <div
            style={{
              color: theme.colors.textMuted,
              fontSize: 32,
              fontFamily: theme.fonts.chinese,
              marginTop: 20,
            }}
          >
            5 个视觉原语验证
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* Scanline 揭示(6-9 秒) */}
      <Sequence from={360} durationInFrames={180}>
        <Scanline
          progress={scanProgress}
          revealContent={
            <AbsoluteFill
              style={{
                backgroundColor: theme.colors.backgroundAlt,
                justifyContent: "center",
                alignItems: "center",
              }}
            >
              <NeonText
                text="SCANLINE REVEAL"
                fontSize={100}
                color={theme.colors.accent}
              />
            </AbsoluteFill>
          }
        />
      </Sequence>
    </AbsoluteFill>
  );
};

registerScene("PrimitiveShowcase", PrimitiveShowcase);
