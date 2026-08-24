/**
 * 表情时间轴解算:字幕文本 → 形象表情。
 *
 * 用法(设计 D4):
 * - inferMood(text):单段文本关键词推断,命中返回表情,未命中返回 null(保持)
 * - resolveMoodTimeline(subtitles, opts):整段序列解算——段边界评估、命中才切、
 *   未命中保持上一表情(段内不闪切);moodTimeline 手工点帧优先,手工点后到
 *   下一手工点之间自动推断挂起
 *
 * 词表原则:词组优先于单字(「省一块」「踩坑」>「省」「坑」),避免
 * 「省份」误命中「省」这类单字陷阱。词表为初版,按真实视频校准(任务 4.5)。
 */
import type { SubtitleEntry } from "./types";
import type { MascotMood } from "../primitives/MascotFigure";

/** 关键词 → 表情。命中任意关键词即返回该表情;数组顺序即优先级 */
const MOOD_KEYWORDS: Array<{ mood: MascotMood; words: string[] }> = [
  // 疑惑:疑问词组 + 问号
  { mood: "huh", words: ["为什么", "怎么回事", "怎么才能", "怎么办", "怎么", "凭什么", "你知道吗", "？", "?"] },
  // 算钱:钱/成本/百分比语境(词组优先,减少「省」单字误命中)
  { mood: "money", words: ["省了", "省一半", "省得多", "省钱", "省下", "成本", "块钱", "美元", "花销", "开销", "预算", "免费", "价格", "收费", "降价", "68%", "%成本"] },
  // 崩溃:错误/坑/失败
  { mood: "dead", words: ["踩坑", "翻车", "报错", "崩了", "崩溃", "失败", "事故", "血泪", "教训", "bug 一把", "惨"] },
  // 惊讶:感叹/反差/震撼
  { mood: "wow", words: ["！", "厉害", "离谱的是", "没想到", "竟然", "居然", "震撼", "直接炸", "翻倍", "快了一倍", "牛"] },
  // 无语:吐槽(2026-08-24 真实讲解词校准:补「沉默」——「共同的沉默」=摊手语境)
  { mood: "meh", words: ["无语", "就这", "白瞎", "折腾半天", "一顿操作", "有意义吗", "沉默"] },
];

/** 单段文本推断。命中返回表情;未命中返回 null(调用方保持上一表情) */
export function inferMood(text: string): MascotMood | null {
  for (const { mood, words } of MOOD_KEYWORDS) {
    if (words.some((w) => text.includes(w))) return mood;
  }
  return null;
}

/** 手工点帧:moodTimeline 未排序输入也按 frame 升序解算 */
export interface MoodPoint {
  frame: number;
  mood: MascotMood;
}

export interface ResolveMoodOptions {
  /** 手工点帧(优先于自动推断;手工点后到下一手工点间自动推断挂起) */
  moodTimeline?: MoodPoint[];
  /** false 则全程不自动切表情(手工点仍生效)。默认 true */
  autoMood?: boolean;
}

/** 无字幕 / 无命中的兜底表情 */
export const DEFAULT_MOOD: MascotMood = "smile";

/**
 * 帧号 → 当前应显示的表情。
 *
 * 手工区间语义:最后一个 frame <= 当前帧的手工点生效;该手工点之后到
 * 下一手工点之间,自动推断挂起(保持手工点表情)。
 */
export function moodAtFrame(
  frame: number,
  subtitles: SubtitleEntry[],
  opts: ResolveMoodOptions = {},
): MascotMood {
  const manual = [...(opts.moodTimeline ?? [])].sort((a, b) => a.frame - b.frame);
  if (manual.length > 0) {
    const lastIdx = manual.findIndex((p) => p.frame > frame) - 1;
    const activeIdx = lastIdx >= 0 ? lastIdx : manual.length - 1;
    if (activeIdx >= 0) {
      const point = manual[activeIdx];
      const nextManual = manual[activeIdx + 1];
      // 手工段内:一律保持手工表情;手工段结束(过最后一手工点后无新点)也保持——
      // 手工是显式意图,只有出现下一手工点才覆盖
      if (!nextManual || frame < nextManual.frame) return point.mood;
    }
  }
  if (opts.autoMood === false) return DEFAULT_MOOD;
  // 自动推断:找覆盖当前帧的段,从该段起点向后逐段保持命中结果
  let mood: MascotMood = DEFAULT_MOOD;
  for (const seg of subtitles) {
    if (seg.endFrame <= frame) {
      // 段已结束:它的命中仍是「上一次表情」候选
      const hit = inferMood(seg.text);
      if (hit) mood = hit;
    } else if (seg.startFrame <= frame) {
      // 当前段:命中即切,未命中保持
      const hit = inferMood(seg.text);
      if (hit) mood = hit;
      break;
    } else {
      break; // 段都还没开始,后面更不用看
    }
  }
  return mood;
}
