import type { ComponentType } from "react";

/**
 * 场景注册表:scene type 字符串 → React 组件。
 *
 * 每个场景组件在 scenes/<Name>.tsx 中定义,并在此处注册。
 * VideoComposition 通过 sceneRegistry[scene.type] 分发到对应组件。
 *
 * 加新场景 = 在 scenes/ 加组件 + 在此处注册。框架代码不动。
 */
export const sceneRegistry: Record<string, ComponentType<any>> = {};

/**
 * 注册一个场景组件。
 *
 * 用法:
 *   // scenes/HookTitle.tsx
 *   import { registerScene } from "./registry";
 *   export const HookTitle: React.FC<Props> = ...
 *   registerScene("HookTitle", HookTitle);
 */
export function registerScene(type: string, component: ComponentType<any>): void {
  if (sceneRegistry[type]) {
    console.warn(`[sceneRegistry] Overwriting existing scene: ${type}`);
  }
  sceneRegistry[type] = component;
}
