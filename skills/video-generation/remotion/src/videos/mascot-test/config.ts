import type { VideoConfig } from "../core/types";

/**
 * Mascot 冒烟视频 - 验证形象伴随层(video-mascot-narration)。
 *
 * 时间轴设计(60fps,共 1200 帧 = 20s):
 * - f0   huh  「为什么」疑问词命中,讲话态
 * - f150 money「省了/成本」命中,讲话态
 * - f270-330 静默 gap(讲话态回落,表情保持 money)
 * - f330 dead 「踩坑/崩了」命中,讲话态;f400 emphasisFrames 命中 → point 姿态
 * - f480 wow  「居然/!」命中,讲话态
 * - f630 meh  「无语」命中,讲话态
 * - f780 「记住这个重点」EMPHASIS_WORDS 命中 → point 姿态(关键词路径)
 * 说话帧 vs 静默帧(如 210 vs 300)同表情,可做讲话态帧差验收。
 */
export const mascotTestConfig: VideoConfig = {
  id: "mascot-test",
  title: "Mascot Companion Smoke Test",
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    { type: "DummyA", props: { title: "Scene One" }, durationInFrames: 300 },
    { type: "DummyB", props: { label: "形象随动冒烟" }, durationInFrames: 300 },
    { type: "DummyA", props: { title: "Scene Three" }, durationInFrames: 300 },
    { type: "DummyB", props: { label: "讲话态与姿态" }, durationInFrames: 300 },
  ],
  subtitles: [
    { text: "上下文为什么会爆掉", startFrame: 0, endFrame: 120 },
    { text: "换个思路一个月省了 68% 成本", startFrame: 150, endFrame: 270 },
    { text: "这个坑我踩过,服务直接崩了", startFrame: 330, endFrame: 450 },
    { text: "实测结果居然翻倍!", startFrame: 480, endFrame: 600 },
    { text: "折腾半天真是无语", startFrame: 630, endFrame: 750 },
    { text: "记住这个重点", startFrame: 780, endFrame: 900 },
  ],
  sfx: {
    enabled: true,
    emphasisFrames: [400],
  },
};
