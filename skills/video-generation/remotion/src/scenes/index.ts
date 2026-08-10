import React from "react";
import { registerScene, sceneRegistry } from "./registry";

// 导入所有场景,触发它们的 registerScene 副作用
import "./DummyScenes";
import "./Minimal3D";
import "./PrimitiveShowcase";
import "./HookTitle";
import "./NetworkGraph";
import "./TextShatter";
import "./GlassFlythrough";
import "./ParticleCollapse";
import "./Outro";
import "./content";

/**
 * 导出所有已注册的场景类型名(便于调试 / 文档)。
 */
export const registeredSceneTypes = () => Object.keys(sceneRegistry);
