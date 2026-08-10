import React, { useMemo } from "react";
import { useCurrentFrame } from "remotion";
import * as THREE from "three";
import { getCurrentTheme } from "../core/theme";

/**
 * GlassPanel - Three.js 玻璃态平面。
 *
 * 视觉:半透明 + 边缘光 + 氖青描边。呈现毛玻璃质感。
 * 用法:Transformer 层、信息卡片背景。
 *
 * 实现:
 * - imperative 构建 mesh + edges(避免 R3F 9.x 声明式兼容问题)
 * - 通过 <primitive object={group} /> 挂载
 * - 轻微呼吸动画:opacity 在 ±10% 范围内波动
 */

interface GlassPanelProps {
  width?: number;
  height?: number;
  opacity?: number;
  edgeColor?: string;
  position?: [number, number, number];
  rotation?: [number, number, number];
}

export const GlassPanel: React.FC<GlassPanelProps> = ({
  width = 8,
  height = 5,
  opacity = 0.15,
  edgeColor,
  position = [0, 0, 0],
  rotation = [0, 0, 0],
}) => {
  const theme = getCurrentTheme();
  const edge = edgeColor ?? theme.colors.accent;
  const frame = useCurrentFrame();

  const group = useMemo(() => {
    const g = new THREE.Group();

    // 主体玻璃平面
    const planeGeometry = new THREE.PlaneGeometry(width, height);
    const planeMaterial = new THREE.MeshStandardMaterial({
      color: edge,
      transparent: true,
      opacity,
      side: THREE.DoubleSide,
      emissive: edge,
      emissiveIntensity: 0.1,
    });
    const plane = new THREE.Mesh(planeGeometry, planeMaterial);
    g.add(plane);

    // 边缘描边
    const edgesGeometry = new THREE.EdgesGeometry(planeGeometry);
    const edgesMaterial = new THREE.LineBasicMaterial({
      color: edge,
      transparent: true,
      opacity: 0.9,
    });
    const edges = new THREE.LineSegments(edgesGeometry, edgesMaterial);
    g.add(edges);

    g.position.set(...position);
    g.rotation.set(...rotation);

    return g;
  }, [width, height, opacity, edge, position, rotation]);

  // 呼吸动画
  useMemo(() => {
    const plane = group.children[0] as THREE.Mesh;
    if (plane && plane.material instanceof THREE.MeshStandardMaterial) {
      const breathOpacity = opacity + Math.sin(frame * 0.05) * 0.02;
      plane.material.opacity = breathOpacity;
    }
  }, [frame, group, opacity]);

  return <primitive object={group} />;
};
