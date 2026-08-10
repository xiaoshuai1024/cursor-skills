import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { registerScene } from "./registry";
import { getCurrentTheme } from "../core/theme";

/**
 * NetworkGraph - 3D 节点网络可视化。
 *
 * 视觉:3D 空间中节点逐个亮起,相互连接形成网络。
 * 用途:隐喻"参数 / 连接 / 神经网络 / 系统架构"。
 *
 * Props:
 * - nodeCount: 节点数量(默认 30)
 * - edgeStyle: 连线样式 "straight" | "curved"(默认 straight)
 * - label: 叠加的文字标签(可选)
 */

interface NetworkGraphProps {
  nodeCount?: number;
  edgeStyle?: "straight" | "curved";
  label?: string;
}

const NetworkGraphInner: React.FC<NetworkGraphProps> = ({
  nodeCount = 30,
  label,
}) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  // 生成节点位置(固定随机种子)
  const { nodes, edges } = useMemo(() => {
    const ns: Array<{ pos: THREE.Vector3; activateFrame: number }> = [];
    const volumeSize = 10;
    for (let i = 0; i < nodeCount; i++) {
      ns.push({
        pos: new THREE.Vector3(
          (Math.random() - 0.5) * volumeSize,
          (Math.random() - 0.5) * volumeSize,
          (Math.random() - 0.5) * volumeSize * 0.5,
        ),
        activateFrame: Math.floor((i / nodeCount) * 200), // 在 200 帧内逐个亮起
      });
    }

    // 连线:距离小于 4 的节点互连
    const es: Array<[number, number]> = [];
    for (let i = 0; i < ns.length; i++) {
      for (let j = i + 1; j < ns.length; j++) {
        if (ns[i].pos.distanceTo(ns[j].pos) < 4) {
          es.push([i, j]);
        }
      }
    }

    return { nodes: ns, edges: es };
  }, [nodeCount]);

  // 节点逐个亮起
  const nodeGroup = useMemo(() => {
    const g = new THREE.Group();
    nodes.forEach((node, i) => {
      const geometry = new THREE.SphereGeometry(0.15, 16, 16);
      const material = new THREE.MeshStandardMaterial({
        color: theme.colors.accent,
        emissive: theme.colors.accent,
        emissiveIntensity: 0,
        transparent: true,
        opacity: 0,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.copy(node.pos);
      g.add(mesh);
    });
    return g;
  }, [nodes, theme.colors.accent]);

  // 连线
  const edgeGroup = useMemo(() => {
    const g = new THREE.Group();
    edges.forEach(([i, j]) => {
      const material = new THREE.LineBasicMaterial({
        color: theme.colors.accent,
        transparent: true,
        opacity: 0,
      });
      const geometry = new THREE.BufferGeometry().setFromPoints([
        nodes[i].pos,
        nodes[j].pos,
      ]);
      const line = new THREE.Line(geometry, material);
      g.add(line);
    });
    return g;
  }, [edges, nodes, theme.colors.accent]);

  // 每帧更新节点/边的可见度
  useMemo(() => {
    nodes.forEach((node, i) => {
      const mesh = nodeGroup.children[i] as THREE.Mesh;
      const material = mesh.material as THREE.MeshStandardMaterial;
      if (frame >= node.activateFrame) {
        const fadeIn = Math.min(1, (frame - node.activateFrame) / 15);
        material.opacity = fadeIn;
        material.emissiveIntensity = fadeIn * 1.5;
      }
    });

    edges.forEach(([i, j], edgeIdx) => {
      const line = edgeGroup.children[edgeIdx] as THREE.Line;
      const material = line.material as THREE.LineBasicMaterial;
      const bothActive =
        frame >= nodes[i].activateFrame && frame >= nodes[j].activateFrame;
      if (bothActive) {
        const fadeIn = Math.min(
          1,
          (frame - Math.max(nodes[i].activateFrame, nodes[j].activateFrame)) /
            20,
        );
        material.opacity = fadeIn * 0.4;
      }
    });
  }, [frame, nodes, edges, nodeGroup, edgeGroup]);

  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <primitive object={nodeGroup} />
      <primitive object={edgeGroup} />
    </>
  );
};

const NetworkGraph: React.FC<NetworkGraphProps> = (props) => {
  const theme = getCurrentTheme();

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <ThreeCanvas
        camera={{ position: [0, 0, 12], fov: 60 }}
        width={1920}
        height={1080}
        style={{ position: "absolute", inset: 0 }}
      >
        <NetworkGraphInner {...props} />
      </ThreeCanvas>

      {props.label && (
        <AbsoluteFill
          style={{
            justifyContent: "flex-end",
            alignItems: "center",
            paddingBottom: 150,
          }}
        >
          <div
            style={{
              color: theme.colors.textMuted,
              fontSize: 36,
              fontFamily: theme.fonts.chinese,
            }}
          >
            {props.label}
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

registerScene("NetworkGraph", NetworkGraph);
