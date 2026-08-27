import React from "react";
import {
  AbsoluteFill,
  Composition,
  Easing,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { getCurrentTheme } from "../../core/theme";

/**
 * ScreenshotZoomDemo — 实机截图 zoom-to-focus + 滚动窗口镜头语言小样
 * （openspec video-codewalk-pipeline：截图镜头语言 requirement 验证件）。
 *
 * 素材与坐标 100% 同源：Playwright 1600×900 会话一次截全页长图（full.png）
 * + bounding_box 实测（Star 1502/92、About 栏 1129/190、README H1 218/1823）。
 *
 * 镜头模型（统一「滚动 + zoom」）：
 * - 内容层（长图 + 热点框）随 translateY 滚动 → scale 层按视口热点 origin 放大
 * - 拍1 Star 区 / 拍2 About 项目说明栏（视口内 zoom）
 * - 拍3 README：平滑滚动 1319px 让 README 标题进视口，再 zoom 聚焦——「滑动窗口」
 * - 全程聚光遮罩（固定 gradient + transform 移动）+ 模拟光标 + 点击涟漪
 */

// @ts-ignore - webpack asset import（demo 素材拷贝进同目录；正式实现走运行时解析）
import fullUrl from "./segment_top.png";

const SCENE_END = 960; // 16s @60fps
const SHOT_W = 1320;
const SHOT_H = Math.round((SHOT_W * 9) / 16); // 742
const RATIO = SHOT_W / 1600; // 页面原坐标 → 显示坐标 0.825
const PAGE_H = Math.round(2500 * RATIO); // 段图显示高（源图 14135px 超 GPU 纹理预算，整层兄弟元素被丢弃——只切滚动所需 0-2500 段）
const M3 = (t: number) => 1 - Math.pow(1 - t, 3);

type Beat = {
  from: number;
  scale: number;
  scrollTop: number; // 显示像素
  hs: { x: number; y: number; w: number; h: number }; // 视口坐标%（滚动后）
  label: string;
  note: string;
  cursor: { x: number; y: number };
};

// 拍3 滚动量：README H1 在 full.png 会话实测 y≈1750（视觉复核，两次会话会漂移 ±100px——
// 滚动目标必须用素材截图自身会话的坐标，不跨会话借数）→ 视口 y 25%：scroll = (1750 - 225) * RATIO
const SCROLL_README = Math.round((1750 - 225) * RATIO); // ≈1258

const BEATS: Beat[] = [
  {
    from: 70, scale: 1.6, scrollTop: 0,
    hs: { x: 0.865, y: 0.068, w: 0.105, h: 0.08 },
    label: "① Star 区", note: "右上角 Star 数：第一信任状",
    cursor: { x: 0.9175, y: 0.108 },
  },
  {
    from: 310, scale: 1.5, scrollTop: 0,
    hs: { x: 0.695, y: 0.205, w: 0.205, h: 0.43 },
    label: "② About 项目说明栏", note: "右侧 About：一句话说清这仓库管什么",
    cursor: { x: 0.7975, y: 0.42 },
  },
  {
    from: 550, scale: 1.32, scrollTop: SCROLL_README,
    hs: { x: 0.13, y: 0.24, w: 0.55, h: 0.42 },
    label: "③ README 首屏", note: "往下滑——README 首屏 3 秒决定去留",
    cursor: { x: 0.405, y: 0.45 },
  },
];

/** 分段阶梯插值：点 p 表示「p.t 起的 dur 帧内从上一稳定值过渡到 p.v」，p.t 之后保持 p.v。
 *  过渡窗起点必须是 p.t（不是 prev.t——旧版让值在上一拍就开始漂向下一拍目标，
 *  导致稳态期所有镜头参数提前错位，白点/框/缩放中心互不对应，2026-08-26 像素级诊断实锤） */
function stepped(frame: number, points: { t: number; v: number }[], dur = 26): number {
  if (frame <= points[0].t) return points[0].v;
  let v = points[0].v;
  for (let i = 1; i < points.length; i++) {
    const p = points[i];
    if (frame >= p.t) {
      v = interpolate(frame, [p.t, p.t + dur], [points[i - 1].v, p.v], {
        easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp",
      });
    }
  }
  return v;
}

const px = (p: number) => `${(p * 100).toFixed(2)}%`;

export const ScreenshotZoomDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();

  const idx = BEATS.reduce((acc, b, i) => (frame >= b.from ? i : acc), -1);
  const beat = idx >= 0 ? BEATS[idx] : null;

  const scale = stepped(frame, [
    { t: 10, v: 1 }, ...BEATS.map((b) => ({ t: b.from, v: b.scale })),
    { t: SCENE_END - 70, v: 1 },
  ], 30);
  const scrollTop = stepped(frame, [
    { t: 10, v: 0 }, ...BEATS.map((b) => ({ t: b.from, v: b.scrollTop })),
    { t: SCENE_END - 70, v: 0 },
  ], 55); // 滚动动画更长（可感知的滑窗）
  const ox = stepped(frame, [
    { t: 10, v: 0.5 }, ...BEATS.map((b) => ({ t: b.from, v: b.hs.x + b.hs.w / 2 })),
    { t: SCENE_END - 70, v: 0.5 },
  ]);
  const oy = stepped(frame, [
    { t: 10, v: 0.5 }, ...BEATS.map((b) => ({ t: b.from, v: b.hs.y + b.hs.h / 2 })),
    { t: SCENE_END - 70, v: 0.5 },
  ]);

  // 聚光遮罩（固定 gradient + transform 移动，禁动态 gradient 字符串——渲染稳定性铁规）
  const dimOn = idx >= 0 && frame < SCENE_END - 70;
  const dim = interpolate(frame, [beat ? beat.from : 0, (beat ? beat.from : 0) + 20], [0, 1], {
    easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp",
  }) * (dimOn ? 1 : 0);
  const maskTX = ((ox - 0.75) / 3) * 100;
  const maskTY = ((oy - 0.75) / 3) * 100;

  // 模拟光标 + 点击涟漪
  // 光标与镜头同点位同节拍（from + dur，与 ox/oy 一致）——全程跟随框中心，尾段一并复位
  const curX = stepped(frame, [
    { t: 0, v: 0.5 }, ...BEATS.map((b) => ({ t: b.from, v: b.cursor.x })),
    { t: SCENE_END - 70, v: 0.5 },
  ], 30);
  const curY = stepped(frame, [
    { t: 0, v: 0.5 }, ...BEATS.map((b) => ({ t: b.from, v: b.cursor.y })),
    { t: SCENE_END - 70, v: 0.5 },
  ], 30);
  const ripple = beat
    ? interpolate(frame, [beat.from + 34, beat.from + 54], [0, 1], {
        easing: Easing.out(Easing.quad), extrapolateLeft: "clamp", extrapolateRight: "clamp",
      }) : 1;
  const rippleR = 18 + ripple * 46;
  const rippleOp = beat && ripple < 1 ? 1 - ripple : 0;

  // 滚动进度提示（拍3 滚动时右侧细滚动条可视——强化「滑窗」感知）
  const scrollbarOp = interpolate(scrollTop, [0, 100], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const scrollThumbTop = (scrollTop / (PAGE_H - SHOT_H)) * (SHOT_H - 120);

  const winIn = interpolate(frame, [0, 20], [0, 1], {
    easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 60% 50% at 30% 20%, rgba(34,211,238,0.10), transparent),
                       radial-gradient(ellipse 50% 45% at 75% 80%, rgba(167,139,250,0.08), transparent)`,
        }}
      />
      <div
        style={{
          position: "absolute", top: 40, left: 0, right: 0, textAlign: "center",
          fontFamily: theme.fonts.chinese, opacity: winIn,
          transform: `translateY(${(1 - winIn) * 14}px)`,
        }}
      >
        <div style={{ color: theme.colors.accent, fontSize: 19, letterSpacing: 3 }}>
          SCREENSHOT ZOOM PROBE · 实机截图镜头语言
        </div>
        <div style={{ color: "#fff", fontSize: 40, fontWeight: 700, marginTop: 4 }}>
          讲到哪，放大到哪；讲 README，滚动给你看
        </div>
      </div>

      <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 66 }}>
        <div
          style={{
            width: SHOT_W + 24, borderRadius: 18, overflow: "hidden",
            border: "1px solid rgba(148,163,184,0.25)",
            boxShadow: "0 24px 80px rgba(0,0,0,0.55), 0 0 70px rgba(34,211,238,0.06)",
            backgroundColor: "#0d1117", opacity: winIn,
            transform: `scale(${0.96 + winIn * 0.04})`,
          }}
        >
          <div
            style={{
              height: 44, backgroundColor: "#161b22", display: "flex", alignItems: "center",
              gap: 8, padding: "0 16px", borderBottom: "1px solid #21262d",
            }}
          >
            {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
              <span key={c} style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: c }} />
            ))}
            <div
              style={{
                flex: 1, margin: "0 auto", maxWidth: 480, textAlign: "center",
                background: "#0d1117", borderRadius: 8, padding: "5px 14px",
                color: "#94a3b8", fontSize: 15, fontFamily: theme.fonts.mono,
              }}
            >
              github.com/farion1231/cc-switch
            </div>
            <span style={{ width: 52 }} />
          </div>

          {/* 截图主体：scale 层（origin=视口热点）包滚动内容层（长图+热点框+光标） */}
          <div style={{ width: SHOT_W, height: SHOT_H, position: "relative", overflow: "hidden" }}>
            <div
              style={{
                position: "absolute", inset: 0,
                transform: `scale(${scale})`,
                transformOrigin: `${px(ox)} ${px(oy)}`,
                transition: "none",
              }}
            >
              <div
                style={{
                  position: "absolute", left: 0, top: 0, width: SHOT_W, height: PAGE_H,
                  transform: `translateY(${-scrollTop}px)`, transition: "none",
                }}
              >
                <img
                  src={fullUrl}
                  style={{ position: "absolute", left: 0, top: 0, width: SHOT_W, height: PAGE_H, transition: "none" }}
                />
              </div>
            </div>
            {/* 聚光遮罩（视口层，不随滚动；先于框/光标——标注层永远全亮不被场景遮罩压暗） */}
            <div
              style={{
                position: "absolute", left: "-100%", top: "-100%", width: "300%", height: "300%",
                background:
                  "radial-gradient(circle 260px at 50% 50%, transparent 0%, transparent 42%, rgba(4,8,16,0.55) 100%)",
                transform: `translate(${maskTX}%, ${maskTY}%)`,
                transition: "none", opacity: dim,
              }}
            />
            {/* 热点框（视口层渲染：中心=zoom origin，尺寸=内容尺寸×scale——
                内容层内嵌套长图 + transform 时子元素实测被丢弃，故移到视口层等价实现） */}
            {/* 热点框：四条裸色条画边（render 管线实测 border/boxShadow/borderRadius:999 触发
                小元素静默丢弃或渲染不完整——框与光标一律裸 div，同类元素保证对齐） */}
            {beat && (() => {
              const bw = beat.hs.w * 1600 * RATIO * scale;
              const bh = beat.hs.h * 900 * RATIO * scale;
              const bx = ox * SHOT_W - bw / 2;
              const by = oy * SHOT_H - bh / 2;
              const T = 4;
              const edge = { position: "absolute" as const, backgroundColor: theme.colors.accent, transition: "none" as const };
              const eIn = interpolate(frame, [beat.from + 20, beat.from + 34], [0, 1], {
                easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp",
              });
              return (
                <div style={{ opacity: eIn, transition: "none" }}>
                  <div style={{ ...edge, left: bx, top: by, width: bw, height: T }} />
                  <div style={{ ...edge, left: bx, top: by + bh - T, width: bw, height: T }} />
                  <div style={{ ...edge, left: bx, top: by, width: T, height: bh }} />
                  <div style={{ ...edge, left: bx + bw - T, top: by, width: T, height: bh }} />
                </div>
              );
            })()}
            {/* 模拟光标 + 点击涟漪（视口层）——render 管线实测坑（2026-08-26）：
                borderRadius:999 / border / boxShadow 均会触发小元素在 render 静默丢弃（still 正常），
                光标一律双层裸 div 画环、涟漪用固定色 + opacity 属性渐隐，禁 border/shadow/动态色字符串 */}
            {rippleOp > 0 && (
              <div
                style={{
                  position: "absolute",
                  left: curX * SHOT_W - rippleR, top: curY * SHOT_H - rippleR,
                  width: rippleR * 2, height: rippleR * 2, borderRadius: "50%",
                  backgroundColor: theme.colors.accent, opacity: 0.38 * rippleOp,
                  transition: "none",
                }}
              />
            )}
            <div
              style={{
                position: "absolute",
                left: curX * SHOT_W - 11, top: curY * SHOT_H - 11,
                width: 22, height: 22, borderRadius: "50%",
                backgroundColor: "rgba(10,14,26,0.65)", transition: "none",
              }}
            >
              <div
                style={{
                  width: 16, height: 16, margin: 3, borderRadius: "50%",
                  backgroundColor: "#ffffff",
                }}
              />
            </div>
            {/* 滚动条（滑窗感知） */}
            <div style={{ position: "absolute", right: 6, top: 10, bottom: 10, width: 5, borderRadius: "50%", backgroundColor: "rgba(148,163,184,0.18)", opacity: scrollbarOp }}>
              <div style={{ position: "absolute", left: 0, right: 0, top: scrollThumbTop, height: 120, borderRadius: "50%", backgroundColor: "rgba(34,211,238,0.75)" }} />
            </div>
          </div>
        </div>
      </div>

      {/* 拍标注条 */}
      {BEATS.map((b, i) => {
        const on = frame >= b.from && frame < (BEATS[i + 1]?.from ?? SCENE_END - 70);
        if (!on) return null;
        const e = interpolate(frame, [b.from, b.from + 14], [0, 1], {
          easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp",
        });
        return (
          <div
            key={i}
            style={{
              position: "absolute", right: 56, bottom: 150, width: 380,
              padding: "20px 24px", borderRadius: 12,
              background: "rgba(10,25,41,0.94)", border: "1px solid rgba(34,211,238,0.4)",
              fontFamily: theme.fonts.chinese, opacity: e,
              transform: `translateX(${(1 - e) * 30}px) scale(${0.96 + e * 0.04})`,
            }}
          >
            <div style={{ color: theme.colors.accent, fontSize: 22, fontWeight: 700 }}>{b.label}</div>
            <div style={{ color: "#e2e8f0", fontSize: 26, marginTop: 6 }}>{b.note}</div>
          </div>
        );
      })}

      <SubBand frame={frame} />
    </AbsoluteFill>
  );
};

const SubBand: React.FC<{ frame: number }> = ({ frame }) => {
  const cues = [
    { from: 30, to: 240, text: "实机截图不是贴图，是镜头" },
    { from: 250, to: 480, text: "Star 区先给信任状：9k 个开发者替你验过货" },
    { from: 490, to: 640, text: "右侧 About 栏一句话，说清这仓库管什么" },
    { from: 650, to: 860, text: "README 在首屏下面——滚动窗口滑过去看" },
    { from: 870, to: 950, text: "这就是 codewalk：讲到哪，镜头跟到哪" },
  ];
  const active = cues.find((c) => frame >= c.from && frame < c.to);
  if (!active) return null;
  const enter = interpolate(frame, [active.from, active.from + 10], [0, 1], {
    easing: M3, extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  return (
    <div style={{ position: "absolute", bottom: 44, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: enter }}>
      <div
        style={{
          background: "rgba(10,14,26,0.88)", border: "1px solid rgba(34,211,238,0.35)",
          borderRadius: "50%", padding: "14px 38px", fontSize: 30, color: "#fff",
          fontFamily: getCurrentTheme().fonts.chinese,
        }}
      >
        {active.text}
      </div>
    </div>
  );
};

export const ScreenshotZoomComposition: React.FC = () => (
  <Composition
    id="screenshot-zoom-probe"
    component={ScreenshotZoomDemo}
    durationInFrames={SCENE_END}
    fps={60}
    width={1920}
    height={1080}
  />
);
