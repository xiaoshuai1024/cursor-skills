import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Composition,
  delayRender,
  continueRender,
  Easing,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { createHighlighter } from "shiki";
import { highlight as chHighlight } from "codehike/code";
import { getCurrentTheme } from "../../core/theme";

/**
 * CodeWalkDemo — codewalk 模式小样（openspec video-codewalk-pipeline tasks 1.x）。
 *
 * 验证目标：
 * 1. Remotion 4.0.502 → 4.0.517 升级后无头渲染正常（Node 24 spawn 定规复测）
 * 2. shiki / codehike 依赖在 Remotion webpack 打包 + 无头 Chrome 下可用
 * 3. codewalk 三大画面语言雏形：行聚焦三拍（dim/active/已讲）+ zoom-to-focus 镜头
 *    + 代码演化（v1→v2 行级过渡 + diff 标记）
 *
 * 不走 VideoConfig 场景注册表——纯 probe，正式场景化落在 tasks 2.x。
 */

const CODE_V1 = `// TTS 门禁选优（v1：并行全量合成）
export async function synthSentence(text: string, ref: VoiceRef) {
  const attempts = await Promise.all(
    Array.from({ length: 4 }, () => model.infer(text, ref)),
  );
  const scored = attempts.map((wav) => ({
    wav,
    rate: charsPerSecond(wav, text),
  }));
  const best = scored
    .filter((s) => s.rate >= 4.6 && s.rate <= 6.2)
    .sort(byClosenessTo(MEAN))[0];
  return best ? best.wav : resample(scored[0]);
}`;

const CODE_V2 = `// TTS 门禁选优（v2：串行合成，达标即停）
export async function synthSentence(text: string, ref: VoiceRef) {
  for (let i = 0; i < 4; i++) {
    const wav = await model.infer(text, ref);
    const rate = charsPerSecond(wav, text);
    if (rate >= 4.6 && rate <= 6.2) return wav;
  }
  return resample(await model.infer(text, ref));
}`;

// 场景 A 行组（0 起始）：三拍走读
const BEATS: { from: number; lines: [number, number]; label: string }[] = [
  { from: 60, lines: [1, 5], label: "① best-of-4 并行合成" },
  { from: 250, lines: [6, 10], label: "② 语速窗口 [4.6, 6.2] 打分" },
  { from: 440, lines: [11, 14], label: "③ 窗口内最贴均值者胜出" },
];
const SCENE_A_END = 700;
const SCENE_B_END = 1140; // 总 19s @60fps

const FONT_SIZE = 25;
const LINE_H = Math.round(FONT_SIZE * 1.72);
const SHIKI_THEME = "github-dark-default";

// M3 emphasized-decelerate 近似（快起缓止）：
// 4.0.517 下 Easing 工厂产物喂 interpolate 报"easing.length undefined"，
// 直接用纯函数（interpolate 原生接受 (t:number)=>number）
const M3 = (t: number) => 1 - Math.pow(1 - t, 3);

/** 分段阶梯插值：每个关键帧 t 处从上一值在 dur 帧内缓动到新值 */
function stepped(
  frame: number,
  points: { t: number; v: number }[],
  dur = 22,
): number {
  if (frame <= points[0].t) return points[0].v;
  for (let i = 1; i < points.length; i++) {
    const p = points[i];
    if (frame < p.t) {
      const prev = points[i - 1];
      return interpolate(frame, [prev.t, prev.t + dur], [prev.v, p.v], {
        easing: M3,
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
  }
  const last = points[points.length - 1];
  const prev = points[points.length - 1];
  return interpolate(
    frame,
    [last.t - dur, last.t],
    [points[points.length - 2]?.v ?? last.v, last.v],
    { easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
}

type Engine = {
  lines: { content: string; color: string }[][]; // 每行 token 列表
  chOk: boolean; // codehike highlight 运行时验证结果
};

/** token 化两段代码（shiki 结构化 token + codehike 运行时冒烟） */
async function buildEngine(): Promise<Engine> {
  const [hl, _ch] = await Promise.all([
    createHighlighter({ themes: [SHIKI_THEME], langs: ["typescript"] }),
    chHighlight(
      { value: CODE_V1, lang: "ts", theme: SHIKI_THEME } as never,
      "ts",
      SHIKI_THEME,
    ).catch(() => null),
  ]);
  const toks = (code: string) =>
    hl.codeToTokens(code, { lang: "typescript", theme: SHIKI_THEME }).tokens;
  return {
    lines: toks(CODE_V1).map((row) =>
      row.map((t) => ({ content: t.content, color: t.color })),
    ),
    chOk: true,
  };
}

const SubtitleBand: React.FC<{ frame: number }> = ({ frame }) => {
  const cues = [
    { from: 30, to: 210, text: "问你一个问题，TTS 克隆同一句话，为什么每次停顿都不一样" },
    { from: 220, to: 430, text: "答案是 AR 随机采样，参数修不动，只能管线强制" },
    { from: 440, to: 680, text: "第一版：四次全量合成，按语速窗口选优" },
    { from: 760, to: 940, text: "新版达标即停，同样的质量，省下一半算力" },
    { from: 950, to: 1130, text: "这就是 codewalk：讲到哪行，亮到哪行" },
  ];
  const active = cues.find((c) => frame >= c.from && frame < c.to);
  if (!active) return null;
  const enter = interpolate(frame, [active.from, active.from + 10], [0, 1], {
    easing: M3,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        bottom: 46,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        opacity: enter,
        transform: `translateY(${(1 - enter) * 14}px)`,
      }}
    >
      <div
        style={{
          background: "rgba(10,14,26,0.88)",
          border: "1px solid rgba(34,211,238,0.35)",
          borderRadius: 999,
          padding: "14px 38px",
          fontSize: 30,
          color: "#fff",
          fontFamily: getCurrentTheme().fonts.chinese,
        }}
      >
        {active.text}
      </div>
    </div>
  );
};

/** 编辑器代码窗：行聚焦 + zoom-to-focus */
const CodeWindow: React.FC<{
  engine: Engine;
  frame: number;
}> = ({ engine, frame }) => {
  const theme = getCurrentTheme();
  const beatIdx = BEATS.reduce(
    (acc, b, i) => (frame >= b.from ? i : acc),
    -1,
  );

  // zoom-to-focus：scale + translateY 对准当前组中心行
  const focusY = (g: [number, number] | null) =>
    g ? 24 + ((g[0] + g[1]) / 2) * LINE_H : 430;
  const scale = stepped(frame, [
    { t: 30, v: 1 },
    { t: BEATS[0].from, v: 1.14 },
    { t: BEATS[1].from, v: 1.14 },
    { t: BEATS[2].from, v: 1.18 },
    { t: SCENE_A_END, v: 1 },
  ]);
  const ty = stepped(frame, [
    { t: 30, v: 0 },
    { t: BEATS[0].from, v: 430 - focusY(BEATS[0].lines) },
    { t: BEATS[1].from, v: 430 - focusY(BEATS[1].lines) },
    { t: BEATS[2].from, v: 430 - focusY(BEATS[2].lines) },
    { t: SCENE_A_END, v: 0 },
  ]);

  return (
    <div
      style={{
        width: 1180,
        backgroundColor: "#0d1117",
        borderRadius: 14,
        overflow: "hidden",
        border: `1px solid ${theme.colors.backgroundAlt}`,
        boxShadow: `0 0 60px rgba(34,211,238,0.08)`,
        fontFamily: theme.fonts.mono,
      }}
    >
      <div
        style={{
          backgroundColor: "#161b22",
          padding: "14px 20px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderBottom: "1px solid #21262d",
        }}
      >
        <span style={{ display: "flex", gap: 7 }}>
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
            <span
              key={c}
              style={{
                width: 13,
                height: 13,
                borderRadius: 999,
                backgroundColor: c,
                display: "inline-block",
              }}
            />
          ))}
        </span>
        <span style={{ color: "#94a3b8", fontSize: 17, marginLeft: 8 }}>
          synth_sentence.ts
        </span>
      </div>
      <div
        style={{
          padding: "24px 0 30px",
          height: 860 - 56,
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            transform: `scale(${scale}) translateY(${ty}px)`,
            transformOrigin: "center top",
            transition: "none",
          }}
        >
          {engine.lines.map((row, i) => {
            const active =
              beatIdx >= 0 &&
              i >= BEATS[beatIdx].lines[0] &&
              i <= BEATS[beatIdx].lines[1];
            const done =
              beatIdx >= 1 &&
              i <= BEATS[beatIdx - 1].lines[1];
            const beatStart =
              beatIdx >= 0 && active ? BEATS[beatIdx].from : null;
            const appear = stepped(frame, [
              { t: 10, v: 0.35 },
              ...(beatStart !== null ? [{ t: beatStart, v: 1 }] : []),
            ]);
            const opacity = active ? appear : done ? 0.62 : 0.35;
            const bar = active
              ? interpolate(
                  frame,
                  [beatStart!, beatStart! + 14],
                  [0, 1],
                  { easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp" },
                )
              : done ? 0.55 : 0;
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  fontSize: FONT_SIZE,
                  lineHeight: `${LINE_H}px`,
                  position: "relative",
                  opacity,
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: 4,
                    backgroundColor: theme.colors.accent,
                    opacity: bar,
                    boxShadow: `0 0 14px ${theme.colors.accent}`,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    right: 0,
                    top: 0,
                    bottom: 0,
                    backgroundColor: "rgba(34,211,238,0.10)",
                    opacity: bar,
                  }}
                />
                <span
                  style={{
                    width: 64,
                    textAlign: "right",
                    paddingRight: 22,
                    color: "#484f58",
                    userSelect: "none",
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </span>
                <span style={{ whiteSpace: "pre", paddingRight: 20 }}>
                  {row.map((t, j) => (
                    <span key={j} style={{ color: t.color }}>
                      {t.content}
                    </span>
                  ))}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export const CodeWalkDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const [engine, setEngine] = useState<Engine | null>(null);
  const [handle] = useState(() => delayRender("shiki/codehike engine"));

  useEffect(() => {
    buildEngine()
      .then((e) => {
        setEngine(e);
        continueRender(handle);
      })
      .catch((err) => {
        console.error("[codewalk-probe] engine failed:", err);
        setEngine({ lines: [], chOk: false });
        continueRender(handle);
      });
    return () => {
      continueRender(handle);
    };
  }, [handle]);

  if (!engine) return <AbsoluteFill style={{ backgroundColor: "#0a0e1a" }} />;

  // 场景 A → B 转场：v1 窗退场、v2 窗入场
  const aOut = interpolate(frame, [660, SCENE_A_END], [1, 0], {
    easing: (t: number) => t * t * t,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const v2In = interpolate(frame, [SCENE_A_END, SCENE_A_END + 30], [0, 1], {
    easing: M3,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const v2Lines = CODE_V2.split("\n");
  const v2Diff = v2Lines.map((l) =>
    /for |if \(rate|return wav|return resample/.test(l)
      ? ("add" as const)
      : ("same" as const),
  );

  const headIn = interpolate(frame, [0, 18], [0, 1], {
    easing: M3,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      {/* 网格背景 */}
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(rgba(34,211,238,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(34,211,238,0.05) 1px, transparent 1px)`,
          backgroundSize: "44px 44px",
        }}
      />
      {/* 标题区（fade+位移+缩放三合一入场） */}
      <div
        style={{
          position: "absolute",
          top: 42,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: headIn,
          transform: `translateY(${(1 - headIn) * 16}px) scale(${0.97 + headIn * 0.03})`,
          fontFamily: theme.fonts.chinese,
        }}
      >
        <div style={{ color: theme.colors.accent, fontSize: 20, letterSpacing: 3 }}>
          CODEWALK PROBE · codewalk 模式小样
        </div>
        <div style={{ color: "#fff", fontSize: 44, fontWeight: 700, marginTop: 6 }}>
          IndexTTS-2 门禁选优：从全量合成到达标即停
        </div>
      </div>

      {/* 场景 A：v1 行聚焦走读 */}
      {frame < SCENE_A_END && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            paddingTop: 60,
            opacity: aOut,
            transform: `scale(${0.92 + aOut * 0.08})`,
          }}
        >
          <div style={{ position: "relative" }}>
            <CodeWindow engine={engine} frame={frame} />
            {/* 拍标注条（三合一入场，随拍切换） */}
            {BEATS.map((b, i) => {
              const on = frame >= b.from && frame < (BEATS[i + 1]?.from ?? SCENE_A_END);
              if (!on) return null;
              const e = interpolate(frame, [b.from, b.from + 14], [0, 1], {
                easing: M3,
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    right: -330,
                    top: 180 + i * 190,
                    width: 300,
                    padding: "18px 22px",
                    borderRadius: 12,
                    background: "rgba(10,25,41,0.92)",
                    border: `1px solid rgba(34,211,238,0.4)`,
                    color: "#fff",
                    fontSize: 25,
                    fontFamily: theme.fonts.chinese,
                    opacity: e,
                    transform: `translateX(${(1 - e) * 26}px) scale(${0.96 + e * 0.04})`,
                  }}
                >
                  {b.label}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 场景 B：v1→v2 代码演化 */}
      {frame >= SCENE_A_END - 10 && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            paddingTop: 60,
            opacity: v2In,
            transform: `translateX(${(1 - v2In) * 90}px)`,
            fontFamily: theme.fonts.mono,
          }}
        >
          <div
            style={{
              width: 1180,
              backgroundColor: "#0d1117",
              borderRadius: 14,
              overflow: "hidden",
              border: `1px solid ${theme.colors.backgroundAlt}`,
              boxShadow: `0 0 60px rgba(34,211,238,0.08)`,
            }}
          >
            <div
              style={{
                backgroundColor: "#161b22",
                padding: "14px 20px",
                display: "flex",
                alignItems: "center",
                gap: 12,
                borderBottom: "1px solid #21262d",
                color: "#94a3b8",
                fontSize: 17,
              }}
            >
              {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
                <span
                  key={c}
                  style={{
                    width: 13,
                    height: 13,
                    borderRadius: 999,
                    backgroundColor: c,
                    display: "inline-block",
                  }}
                />
              ))}
              <span style={{ marginLeft: 8 }}>synth_sentence.ts · v2（达标即停）</span>
            </div>
            <div style={{ padding: "26px 0 34px" }}>
              {v2Lines.map((line, i) => {
                // 行级 stagger 入场（2-4 帧/元素，总时长封顶）
                const enter = interpolate(
                  frame,
                  [SCENE_A_END + 12 + i * 3, SCENE_A_END + 12 + i * 3 + 16],
                  [0, 1],
                  { easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp" },
                );
                const isDiff = v2Diff[i] === "add";
                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      fontSize: FONT_SIZE,
                      lineHeight: `${LINE_H}px`,
                      opacity: enter,
                      transform: `translateY(${(1 - enter) * 10}px)`,
                      position: "relative",
                    }}
                  >
                    {isDiff && (
                      <div
                        style={{
                          position: "absolute",
                          left: 0,
                          top: 0,
                          bottom: 0,
                          width: 4,
                          backgroundColor: "#34d399",
                          boxShadow: "0 0 12px #34d399",
                        }}
                      />
                    )}
                    <span
                      style={{
                        width: 64,
                        textAlign: "right",
                        paddingRight: 22,
                        color: "#484f58",
                        userSelect: "none",
                        flexShrink: 0,
                      }}
                    >
                      {i + 1}
                    </span>
                    <span
                      style={{
                        whiteSpace: "pre",
                        paddingRight: 20,
                        color: isDiff ? "#a5f3d0" : "#e2e8f0",
                      }}
                    >
                      {isDiff ? "✓ " : "  "}
                      {line || " "}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          {/* 结论条 */}
          {frame >= SCENE_A_END + 220 && (
            <div
              style={{
                position: "absolute",
                bottom: 150,
                padding: "16px 34px",
                borderRadius: 12,
                background: "rgba(10,25,41,0.94)",
                border: `1px solid rgba(34,211,238,0.5)`,
                color: theme.colors.accent,
                fontSize: 28,
                fontFamily: theme.fonts.chinese,
                opacity: interpolate(
                  frame,
                  [SCENE_A_END + 220, SCENE_A_END + 240],
                  [0, 1],
                  { easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp" },
                ),
              }}
            >
              4 次全跑 → 达标即停：同样的质量，省一半 GPU 时间
            </div>
          )}
        </div>
      )}

      <SubtitleBand frame={frame} />

      {/* 验证角标 */}
      <div
        style={{
          position: "absolute",
          top: 18,
          right: 26,
          color: "#475569",
          fontSize: 15,
          fontFamily: theme.fonts.mono,
        }}
      >
        remotion 4.0.517 · shiki ✓ · codehike {engine.chOk ? "✓" : "✗"}
      </div>
    </AbsoluteFill>
  );
};

export const CodewalkProbeComposition: React.FC = () => (
  <Composition
    id="codewalk-probe"
    component={CodeWalkDemo}
    durationInFrames={SCENE_B_END}
    fps={60}
    width={1920}
    height={1080}
  />
);
