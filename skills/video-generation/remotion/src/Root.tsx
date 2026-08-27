import React from "react";
import { Composition } from "remotion";
import { VideoComposition } from "./core/VideoComposition";
import { DEFAULTS } from "./core/types";

// 导入视频 config
import { dummyConfig } from "./videos/dummy-test/config";
import { minimal3dConfig } from "./videos/minimal-3d/config";
import { primitiveShowcaseConfig } from "./videos/primitive-showcase/config";
import { scenesShowcaseConfig } from "./videos/scenes-showcase/config";
import { llmThinkingConfig } from "./videos/llm-thinking/config";
import { dummy2Config } from "./videos/dummy-2/config";
import { testDRConfig } from "./videos/test-datareveal/config";
import { testStyleBConfig } from "./videos/test-style-b/config";
import { mascotTestConfig } from "./videos/mascot-test/config";
import {
  mascotSize180Config,
  mascotSize210Config,
  mascotSize240Config,
  mascotSize270Config,
} from "./videos/mascot-size/config";
import { CodewalkProbeComposition } from "./videos/codewalk-probe/CodeWalkDemo";
import { ScreenshotZoomComposition } from "./videos/screenshot-probe/ScreenshotZoomDemo";
// 内容视频（git 忽略的 .video-generation/remotion-videos/ 下，按需加载）：
// 由 scripts/sync-content-videos.ts 扫描生成注册表，缺失配置不会进入打包。
import { contentVideos } from "./videos/content-videos";

// 触发所有场景注册
import "./scenes";

/**
 * Remotion Root:注册所有视频 composition。
 *
 * 每个视频 = 一个 <Composition>,config 来自 videos/<id>/config.ts。
 * 加新视频 = 加一条 <Composition> + 导入对应 config + 导入场景注册。
 */
export const RemotionRoot: React.FC = () => {
  const allConfigs = [
    dummyConfig,
    minimal3dConfig,
    primitiveShowcaseConfig,
    scenesShowcaseConfig,
    llmThinkingConfig,
    dummy2Config,
    testDRConfig,
    testStyleBConfig,
    mascotTestConfig,
    mascotSize180Config,
    mascotSize210Config,
    mascotSize240Config,
    mascotSize270Config,
  ];

  return (
    <>
      {allConfigs.map((cfg) => (
        <Composition
          key={cfg.id}
          id={cfg.id}
          component={VideoComposition}
          durationInFrames={cfg.scenes.reduce(
            (sum, s) => sum + s.durationInFrames,
            0,
          )}
          fps={cfg.fps ?? DEFAULTS.fps}
          width={cfg.width ?? DEFAULTS.width}
          height={cfg.height ?? DEFAULTS.height}
          defaultProps={{ config: cfg }}
        />
      ))}
      {/* codewalk 模式小样（独立验证件，不走 VideoConfig 注册表） */}
      <CodewalkProbeComposition />
      <ScreenshotZoomComposition />
      {contentVideos.map((v) => (
        <Composition
          key={v.id}
          id={v.id}
          lazyComponent={v.lazyComponent}
          durationInFrames={v.durationInFrames}
          fps={v.fps}
          width={v.width}
          height={v.height}
        />
      ))}
    </>
  );
};
