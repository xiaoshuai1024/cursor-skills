import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, staticFile } from "remotion";
import { registerScene } from "../registry";
import { getCurrentTheme } from "../../core/theme";

/** RepoShot - GitHub 仓库截图展示：截图 + 顶部名称/星数 + 底部「核心点」信息条 + 扫描线。 */
interface RepoShotProps {
  image: string;
  name: string;
  stars?: string;
  /** 项目最核心的点 / 项目说明（必填，让观众 3 秒看懂这个仓库是干什么的） */
  core: string;
}
const easeOut = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);
const RepoShot: React.FC<RepoShotProps> = ({ image, name, stars, core }) => {
  const frame = useCurrentFrame();
  const theme = getCurrentTheme();
  const t = easeOut(frame / 22);
  const coreT = easeOut((frame - 14) / 20);
  const scan = Math.min(1, frame / 50);
  return (
    <AbsoluteFill style={{ backgroundColor: theme.colors.background, justifyContent: "center", alignItems: "center" }}>
      <div style={{ position: "relative", transform: `scale(${0.86 + 0.14 * t})`, opacity: t, width: 1280 }}>
        <div style={{ position: "absolute", inset: -6, borderRadius: 18, border: `3px solid ${theme.colors.accent}`, boxShadow: `0 0 60px ${theme.colors.accent}55` }} />
        <Img src={staticFile(image)} style={{ width: 1280, height: 660, objectFit: "cover", borderRadius: 14, display: "block" }} />
        <div style={{ position: "absolute", left: 0, right: 0, top: `${scan * 100}%`, height: 4, background: `linear-gradient(90deg, transparent, ${theme.colors.accent}, transparent)`, opacity: scan < 1 ? 0.8 : 0 }} />
        <div style={{ position: "absolute", left: 20, top: 16, display: "flex", gap: 16, alignItems: "baseline", padding: "8px 18px", borderRadius: 10, background: "rgba(10,14,26,0.85)", border: `2px solid ${theme.colors.accent}88` }}>
          <span style={{ fontSize: 34, fontWeight: 900, color: theme.colors.text, fontFamily: theme.fonts.chinese }}>{name}</span>
          {stars ? <span style={{ fontSize: 28, color: theme.colors.accent, fontFamily: theme.fonts.mono }}>★ {stars}</span> : null}
        </div>
        <div style={{ marginTop: 18, padding: "18px 24px", borderRadius: 12, background: "rgba(0,217,255,0.07)", border: `2px solid ${theme.colors.accent}66`, opacity: coreT, transform: `translateY(${(1 - coreT) * 14}px)` }}>
          <div style={{ fontSize: 22, color: theme.colors.accent, fontFamily: theme.fonts.chinese, fontWeight: 700, marginBottom: 6 }}>这个仓库是什么</div>
          <div style={{ fontSize: 28, color: theme.colors.text, fontFamily: theme.fonts.chinese, lineHeight: 1.4 }}>{core}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
registerScene("RepoShot", RepoShot);
