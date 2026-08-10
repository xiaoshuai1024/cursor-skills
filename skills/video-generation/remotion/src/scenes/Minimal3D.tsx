import React from "react";
import { AbsoluteFill } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";

/**
 * Minimal3D - 最小 3D 测试,验证 Three.js 基础能渲染。
 */
const Minimal3D: React.FC = () => {
  const theme = getCurrentTheme();

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <ThreeCanvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        width={1920}
        height={1080}
        style={{ position: "absolute", inset: 0 }}
      >
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={0.8} />
        <mesh>
          <boxGeometry args={[2, 2, 2]} />
          <meshStandardMaterial color={theme.colors.accent} />
        </mesh>
      </ThreeCanvas>
    </AbsoluteFill>
  );
};

registerScene("Minimal3D", Minimal3D);
