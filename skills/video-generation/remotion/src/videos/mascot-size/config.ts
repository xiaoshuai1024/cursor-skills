import type { VideoConfig } from "../../core/types";

/**
 * 形象高度标定(video-mascot-narration 任务 6.1):同一真实内容 × 4 档高度,
 * 定 DEFAULT_MASCOT.height。场景 props 抄自 claude-codex-context-compaction
 * (密表格 + 大字结论两类遮挡敏感景别);两段字幕让两帧分别处于
 * money/讲话(f120)与 dead/讲话(f420)代表性状态。still 帧:120 / 420。
 */
const base = (height: number): VideoConfig => ({
  id: `mascot-size-h${height}`,
  width: 1920,
  height: 1080,
  fps: 60,
  scenes: [
    {
      type: "ComparisonTable3D",
      props: {
        headers: ["阈值体系", "数值", "说明"],
        rows: [
          { label: "自动压缩线", left: "可用窗口减一万三", right: "给一轮工具调用留缓冲" },
          { label: "警告线", left: "再宽两千", right: "给用户看的红黄牌" },
          { label: "窗口大小", left: "按模型动态查表", right: "没有硬编码数字" },
        ],
      },
      durationInFrames: 300,
    },
    {
      type: "ConclusionFocus",
      props: { mainText: "两边的共同沉默:都不做向量记忆" },
      durationInFrames: 300,
    },
  ],
  subtitles: [
    { text: "换个思路一个月省了 68% 成本", startFrame: 30, endFrame: 210 },
    { text: "这个坑我踩过,服务直接崩了", startFrame: 330, endFrame: 510 },
  ],
  mascot: { enabled: true, height, position: "bottom-right" },
});

export const mascotSize180Config = base(180);
export const mascotSize210Config = base(210);
export const mascotSize240Config = base(240);
export const mascotSize270Config = base(270);
