/**
 * sound-points.ts - 内容感知的声音选点助手。
 *
 * 在 config.ts 里用口播 narration units 的文本自动算音效帧号/选 BGM 情绪,
 * 代替手工点帧。规则与 Playwright 管线 config.py::suggest_bgm_mood 保持同口径
 * (改关键词两边同步改)。
 *
 * 用法(视频 config.ts):
 *   import { narration as N } from "./narration";
 *   import { autoQuestionFrames, suggestBgmMood } from "@skill-src/core/sound-points";
 *   const U = N.segments;
 *   sfx: {
 *     bgmMood: suggestBgmMood(N.audio + U.map(u => u.text)),
 *     questionFrames: autoQuestionFrames(U),
 *   }
 */

/** BGM 情绪档(文件名映射到 video-generation/narration/,gen-sfx.py 生成) */
export type BgmMood =
  | "calm" | "walk" | "focus" | "bright"
  | "tense" | "epic" | "chiptune" | "lofi";

export const BGM_MOOD_FILES: Record<BgmMood, string> = {
  calm: "bgm-light-calm.wav",
  walk: "bgm-light-walk.wav",
  focus: "bgm-light-focus.wav",
  bright: "bgm-light-bright.wav",
  tense: "bgm-tense.wav",
  epic: "bgm-epic.wav",
  chiptune: "bgm-chiptune.wav",
  lofi: "bgm-lofi.wav",
};

/** mood → 适用内容(选型参考,写 config 时对照) */
export const BGM_MOOD_USAGE: Record<BgmMood, string> = {
  calm: "沉稳科普,默认档,任何讲解都安全",
  walk: "轻快带节奏,教程/步骤/上手类",
  focus: "极简专注,深度解析/长讲解(存在感最低)",
  bright: "明亮进取,新发布/技巧/效率提升类",
  tense: "悬疑脉冲,源码内幕/揭秘/为什么类(抖音悬疑解说味)",
  epic: "史诗推进,对决/评测/跑分类(抖音热血盘点味)",
  chiptune: "8-bit 方波,程序员梗/终端命令行/装机类",
  lofi: "Lo-fi 七和弦,温和长教程/Vlog 式讲解",
};

/** 情绪关键词规则:按命中数计分,取最高;全部未命中回退 calm */
const MOOD_RULES: Array<{ mood: BgmMood; keywords: string[]; weight?: number }> = [
  { mood: "tense", keywords: ["源码", "内幕", "揭秘", "真相", "为什么", "原理", "底层", "事故", "翻车", "踩坑", "坑"] },
  { mood: "epic", keywords: ["对决", "对比", "排行", "榜单", "跑分", "评测", "性能", "倍", "吊打", "完胜"] },
  { mood: "chiptune", keywords: ["程序员", "终端", "命令行", "npm", "git", "代码", "编译", "安装包"] },
  { mood: "bright", keywords: ["新", "发布", "升级", "技巧", "效率", "提速", "省"] },
  { mood: "walk", keywords: ["教程", "步骤", "入门", "上手", "怎么", "如何", "零基础"] },
  { mood: "lofi", keywords: ["聊聊", "随笔", "体验", "一周", "记录"] },
];

/** 从口播文本推荐 BGM 情绪:关键词计数,同分靠前优先,无命中 calm */
export function suggestBgmMood(...texts: string[]): BgmMood {
  const corpus = texts.join(" ");
  let best: BgmMood = "calm";
  let bestScore = 0;
  for (const rule of MOOD_RULES) {
    const score = rule.keywords.reduce((acc, kw) => acc + (corpus.includes(kw) ? 1 : 0), 0);
    if (score > bestScore) {
      best = rule.mood;
      bestScore = score;
    }
  }
  return best;
}

/** narration unit 最小结构(字段与 narrate.py 产出的 narration.ts 一致) */
export interface SoundUnit {
  text: string;
  start_frame: number;
  end_frame: number;
}

/** 自动提问点:问句单元(？/? 结尾)的起始帧。自动配 sfx-question-up */
export function autoQuestionFrames(units: SoundUnit[], max = 4): number[] {
  return units
    .filter((u) => /[？?]\s*$/.test(u.text.trim()))
    .slice(0, max)
    .map((u) => u.start_frame);
}

/** 关键词落点:含任一关键词的单元起始帧(每关键词只取第一次出现),配 emphasis/reveal */
export function keywordFrames(units: SoundUnit[], keywords: string[], max = 4): number[] {
  const frames: number[] = [];
  const used = new Set<string>();
  for (const u of units) {
    for (const kw of keywords) {
      if (!used.has(kw) && u.text.includes(kw)) {
        used.add(kw);
        frames.push(u.start_frame);
        break;
      }
    }
    if (frames.length >= max) break;
  }
  return frames;
}
