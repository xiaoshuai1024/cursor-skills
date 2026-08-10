import type { VideoConfig } from "../../core/types";
export const testStyleBConfig: VideoConfig = {
  id: "test-style-b",
  title: "Style B Sample - PixelDiff + CodeAudit",
  fps: 60,
  scenes: [
    { type: "PixelDiff", props: { leftLabel: "原型", rightLabel: "实现", diffPercent: 60 }, durationInFrames: 400 },
    { type: "CodeAuditScan", props: { totalPages: 423, hardcodedPages: 4 }, durationInFrames: 400 },
  ],
  themeOverrides: {
    colors: { accent: "#2563eb", background: "#0f172a", backgroundAlt: "#1e293b", error: "#dc2626", success: "#0f766e", highlight: "#dbeafe" },
  },
};
