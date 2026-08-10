import React, { useMemo } from "react";
import { useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { getCurrentTheme } from "../core/theme";

/**
 * ParticleField - 3D 粒子系统。
 *
 * 视觉:深空中的星尘感,白色/氖青色小粒子缓慢随机运动。
 * 用法:作为其他场景的背景。
 *
 * 实现:
 * - imperative 构建 THREE.Points(避免 R3F 9.x 声明式兼容问题)
 * - 每帧通过 useMemo 重新计算粒子位置(基于 frame 的确定性漂移)
 * - 粒子在体积框内循环
 */

interface ParticleFieldProps {
  count?: number;
  color?: string;
  speed?: number;
  volumeSize?: number;
  size?: number;
}

const ParticleFieldInner: React.FC<ParticleFieldProps> = ({
  count = 500,
  speed = 0.01,
  volumeSize = 20,
  size = 0.08,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 创建 Points 对象(imperative,避免 R3F 9.x 声明式兼容问题)
  const points = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * volumeSize;
      positions[i * 3 + 1] = (Math.random() - 0.5) * volumeSize;
      positions[i * 3 + 2] = (Math.random() - 0.5) * volumeSize;
    }
    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(positions, 3),
    );

    const material = new THREE.PointsMaterial({
      size,
      color: theme.colors.accent,
      transparent: true,
      opacity: 0.8,
      sizeAttenuation: true,
      depthWrite: false,
    });

    return new THREE.Points(geometry, material);
  }, [count, volumeSize, size, theme.colors.accent]);

  // 每帧更新粒子位置(基于 frame 的确定性漂移)
  useMemo(() => {
    const positions = points.geometry.attributes.position
      .array as Float32Array;
    for (let i = 0; i < count; i++) {
      const seed = i * 1.37;
      const drift = frame * speed;
      positions[i * 3] = Math.sin(seed + drift) * 2;
      positions[i * 3 + 1] = Math.cos(seed + drift * 0.7) * 2;
      positions[i * 3 + 2] = Math.sin(seed * 0.5 + drift * 0.3) * 2;
    }
    points.geometry.attributes.position.needsUpdate = true;
  }, [frame, points, count, speed, volumeSize]);

  return <primitive object={points} />;
};

export const ParticleField: React.FC<ParticleFieldProps> = (props) => {
  return (
    <ThreeCanvas
      camera={{ position: [0, 0, 15], fov: 60 }}
      width={1920}
      height={1080}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
      }}
    >
      <ambientLight intensity={0.5} />
      <ParticleFieldInner {...props} />
    </ThreeCanvas>
  );
};
