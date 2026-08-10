import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/**
 * ConclusionFocus - 结论汇聚（真 3D 粒子）。
 *
 * 视觉：数百个 3D 球粒子从球面随机位置向中心汇聚成光环，
 * 摄像机持续旋转，汇聚后核心文字淡入。
 */

interface Props {
  mainText: string;
}

const ConclusionFocus: React.FC<Props> = ({ mainText }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  const COUNT = 400;
  const convergeDuration = 150;

  const particles = useMemo(() => {
    return Array.from({ length: COUNT }, () => {
      const r = 6 + Math.random() * 4;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const start = new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi),
      );
      const geo = new THREE.SphereGeometry(0.05 + Math.random() * 0.04, 6, 6);
      const mat = new THREE.MeshBasicMaterial({ color: theme.colors.accent, transparent: true, opacity: 0.8 });
      const m = new THREE.Mesh(geo, mat);
      m.position.copy(start);
      return { mesh: m, start };
    });
  }, [theme.colors.accent]);

  // 中心核心环
  const coreRing = useMemo(() => {
    const geo = new THREE.TorusGeometry(0.8, 0.06, 16, 64);
    const mat = new THREE.MeshBasicMaterial({ color: theme.colors.accent, transparent: true, opacity: 0 });
    return new THREE.Mesh(geo, mat);
  }, [theme.colors.accent]);

  // 每帧：粒子向中心汇聚 + 旋转
  useMemo(() => {
    const rawProgress = Math.min(1, frame / convergeDuration);
    const eased = 1 - Math.pow(1 - rawProgress, 3);
    particles.forEach((p, i) => {
      const delay = (i / COUNT) * 0.3;
      const localProgress = Math.max(0, (rawProgress - delay) / (1 - delay));
      const e = 1 - Math.pow(1 - localProgress, 3);
      p.mesh.position.lerpVectors(p.start, new THREE.Vector3(0, 0, 0), e);
      (p.mesh.material as THREE.MeshBasicMaterial).opacity = 0.3 + e * 0.6;
      p.mesh.scale.setScalar(0.5 + e * 0.8);
    });
    const ringOpacity = Math.max(0, Math.min(1, (frame - convergeDuration * 0.5) / 30));
    (coreRing.material as THREE.MeshBasicMaterial).opacity = ringOpacity * 0.8;
    coreRing.scale.setScalar(1 + Math.sin(frame * 0.08) * 0.15);
    coreRing.rotation.x = frame * 0.02;
    coreRing.rotation.y = frame * 0.03;
  }, [frame, particles, coreRing, convergeDuration, COUNT]);

  const textOpacity = Math.max(0, Math.min(1, (frame - convergeDuration * 0.6) / 30));

  // 摄像机旋转
  const camAngle = frame * 0.005;
  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <ThreeCanvas camera={{ position: [Math.sin(camAngle) * 3, Math.cos(camAngle * 0.7) * 2, 8], fov: 55 }} width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <ambientLight intensity={0.4} />
        <pointLight position={[0, 0, 5]} intensity={0.8} />
        {particles.map((p, i) => <primitive key={i} object={p.mesh} />)}
        <primitive object={coreRing} />
      </ThreeCanvas>

      {textOpacity > 0 && (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <div style={{
            color: theme.colors.text,
            fontSize: 76,
            fontFamily: theme.fonts.chinese,
            fontWeight: 900,
            opacity: textOpacity,
            textShadow: `0 0 40px ${theme.colors.accent}, 0 0 80px ${theme.colors.accent}60`,
            letterSpacing: 4,
          }}>
            {mainText}
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

registerScene("ConclusionFocus", ConclusionFocus);
