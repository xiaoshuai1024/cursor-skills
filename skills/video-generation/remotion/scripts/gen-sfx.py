#!/usr/bin/env python3
"""gen-sfx.py - 生成视频短音效(纯 stdlib 合成,确定性,无外部音频文件/无版权风险)。

产物(写入 video-generation/narration/ = Remotion public 目录,staticFile 直接引用):
  旧 3 个(保留,向后兼容):
    sfx-opening.wav     开场提示音(上升扫频 + 钟声),~0.9s
    sfx-transition.wav  转场过渡音(二阶低通 whoosh,平缓+小声),~0.3s
    sfx-question.wav    提问提示音(轻快双音 ding),~0.45s
  新 10 个(2026-08-20 扩充,风格统一"轻声/柔和",内置幅度更小不归一化):
    sfx-opening-chime.wav   双音钟声引子(无扫频,更柔) ~1.0s
    sfx-opening-riser.wav   轻 riser 缓升 + 落点低音 ~0.5s
    sfx-transition-swoosh.wav  更轻的上扫 swoosh ~0.24s
    sfx-transition-pop.wav     轻 pop(快节奏/硬切) ~0.12s
    sfx-question-up.wav        上行三音(更轻快) ~0.5s
    sfx-question-down.wav      下行双音(收束/反思) ~0.5s
    sfx-emphasis.wav           单音软 ping(关键词落地) ~0.35s
    sfx-emphasis-tick.wav      极短 tick(数字/小词) ~0.08s
    sfx-reveal.wav             轻 whoosh-open + 上行(数据出现) ~0.4s
    sfx-reveal-bloom.wav       软和弦 bloom(结论/高光) ~0.8s

用法:
  python gen-sfx.py [输出目录]
不依赖 numpy/wave 之外的库(仅用标准库 wave/math/struct)。
"""
import math
import struct
import sys
import wave

RATE = 44100


def _write_wav(path: str, samples: list[float]) -> None:
    peak = max(1e-9, max(abs(s) for s in samples))
    scale = min(1.0, 0.9 / peak)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = bytearray()
        for s in samples:
            v = int(max(-1.0, min(1.0, s * scale)) * 32767)
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))


def _sine(freq: float, t: float, phase: float = 0.0) -> float:
    return math.sin(2 * math.pi * freq * t + phase)


def _sweep(f0: float, f1: float, t: float) -> float:
    """线性扫频:相位 = ∫freq dt = f0*t + (f1-f0)/2 * t^2"""
    return math.sin(2 * math.pi * (f0 * t + (f1 - f0) / 2 * t * t))


def _note(freq: float, t: float, harmonics: list[float] = (1.0, 0.35, 0.12)) -> float:
    """带泛音的钟声/拨弦音:基频 + 2 次 + 3 次谐波,轻微失谐更暖"""
    out = 0.0
    for i, amp in enumerate(harmonics):
        f = freq * (i + 1)
        det = 1.0 + 0.002 * i  # 轻微 detune,避免纯正弦的塑料感
        out += amp * math.sin(2 * math.pi * f * det * t)
    return out


def _lowpass_2pole(samples: list[float], fc: float) -> list[float]:
    """二阶低通(串联两个单极 IIR)。高频齿音削干净,听感丝滑不刺耳。"""
    a = 1.0 - math.exp(-2.0 * math.pi * fc / RATE)
    lp1 = 0.0
    lp2 = 0.0
    out = []
    for s in samples:
        lp1 += a * (s - lp1)
        lp2 += a * (lp1 - lp2)
        out.append(lp2)
    return out


def _noise(dur: float, seed: int) -> list[float]:
    """确定性白噪(LCG,固定 seed → 同输入同输出)。"""
    n = int(RATE * dur)
    x = seed & 0xFFFFFFFF
    out = []
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0xFFFFFFFF
        out.append((x / 0xFFFFFFFF) * 2.0 - 1.0)
    return out


def gen_opening() -> list[float]:
    dur = 0.9
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        # 上升扫频(0.0-0.32s):300→1200Hz,吸引注意
        if t < 0.32:
            env = math.sin(math.pi * t / 0.32)  # 0→1→0
            v += 0.55 * env * _sweep(300, 1200, t)
        # 钟声和弦(0.28s 起):C6 + G6,指数衰减
        if t >= 0.28:
            dt = t - 0.28
            decay = math.exp(-dt * 7.0)
            v += 0.4 * decay * (_note(1046.5, dt) + 0.7 * _note(1568.0, dt))
        out.append(v)
    return out


def gen_transition() -> list[float]:
    """柔和转场音:低通白噪 swish + 低频下扫,快起慢落但整体轻(音量低、高频被滤掉)。

    2026-08-20 用户反馈旧版太强(白噪 10.7kHz 质心刺耳)。新版:
    - 噪声过一阶低通(fc≈1800Hz),高频齿音被削掉,听感是"丝滑"而非"唰"
    - 幅度降到 0.26,起音带 40ms 斜升,不炸耳
    - 低频下扫 300→180Hz 只垫 0.12,给过渡一点点实体
    """
    dur = 0.32
    n = int(RATE * dur)
    # 确定性白噪(固定 seed 的 LCG)
    seed = 20260820
    noise = []
    x = seed & 0xFFFFFFFF
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0xFFFFFFFF
        noise.append((x / 0xFFFFFFFF) * 2.0 - 1.0)
    # 二阶低通(串联两个单极 IIR,fc≈1200Hz):斜率更陡,高频齿音削得更干净
    fc = 1200.0
    a = 1.0 - math.exp(-2.0 * math.pi * fc / RATE)
    lp1 = 0.0
    lp2 = 0.0
    out = []
    for i in range(n):
        t = i / RATE
        lp1 += a * (noise[i] - lp1)
        lp2 += a * (lp1 - lp2)
        # 斜升 40ms + 慢落
        env = min(1.0, t / 0.04) * max(0.0, 1.0 - t / dur)
        v = 0.30 * env * lp2
        # 低频下扫垫底(几乎听不见,只加"落地"感)
        v += 0.12 * env * _sweep(300, 180, t)
        out.append(v)
    return out


def gen_question() -> list[float]:
    dur = 0.45
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        # 双音上行:F#5 → B5,轻快活泼
        for start, freq in ((0.0, 740.0), (0.15, 988.0)):
            dt = t - start
            if dt >= 0:
                decay = math.exp(-dt * 11.0)
                v += 0.5 * decay * _note(freq, dt)
        out.append(v)
    return out


# ── 短音效库扩充(2026-08-20:多准备几个,风格统一"轻声/柔和",内置幅度更小)─────────
# 旧 3 个(sfx-opening/transition/question)保留不动;新增按功能分组,文件名 <功能>-<性格>。
# 音量策略:新变体内置幅度 0.22~0.4(峰值远低于 0.9 不触发归一化),天然比旧款轻,
# 配合模板 volume 0.4(原 0.5)再降 ~2dB——"音效声音再稍微低一点"。

def gen_opening_chime() -> list[float]:
    """双音钟声引子(比 sfx-opening 更柔:无扫频噪声,只有钟声),~1.0s。"""
    dur = 1.0
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        v = 0.0
        for start, freq in ((0.0, 784.0), (0.12, 1046.5)):
            dt = t - start
            if dt >= 0:
                env = min(1.0, dt / 0.01)  # 快起
                decay = math.exp(-dt * 4.5)
                v += 0.30 * env * decay * (_note(freq, dt, (1.0, 0.22, 0.08)) + 0.5 * _note(freq * 1.5, dt, (1.0, 0.15)))
        out.append(v)
    return out


def gen_opening_riser() -> list[float]:
    """轻 riser:低通噪声缓升 + 落点低音(300→80Hz),~0.5s。"""
    dur = 0.5
    n = int(RATE * dur)
    noise = _noise(dur, 20260821)
    lp = _lowpass_2pole(noise, 900.0)
    out = []
    for i in range(n):
        t = i / RATE
        env = (t / dur) ** 2  # 缓升
        v = 0.26 * env * lp[i]
        if t >= 0.42:  # 落点低音,给一个"落地"感
            dt = t - 0.42
            v += 0.20 * math.exp(-dt * 10.0) * _sweep(300, 80, dt)
        out.append(v)
    return out


def gen_transition_swoosh() -> list[float]:
    """更轻的 swoosh(上扫低通噪声,比 sfx-transition 更透气),~0.24s。"""
    dur = 0.24
    n = int(RATE * dur)
    noise = _noise(dur, 20260822)
    lp = _lowpass_2pole(noise, 1400.0)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.03) * max(0.0, 1.0 - t / dur)
        out.append(0.20 * env * lp[i])
    return out


def gen_transition_pop() -> list[float]:
    """轻 pop(短促噪声 + 高频亮,快节奏/硬切场景用),~0.12s。"""
    dur = 0.12
    n = int(RATE * dur)
    noise = _noise(dur, 20260823)
    lp = _lowpass_2pole(noise, 2200.0)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.005) * math.exp(-t * 30.0)
        out.append(0.26 * env * lp[i])
    return out


def gen_question_up() -> list[float]:
    """上行三音 C6→E6→G6(比 sfx-question 更轻快),~0.5s。"""
    dur = 0.5
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        v = 0.0
        for start, freq in ((0.0, 1046.5), (0.13, 1318.5), (0.26, 1568.0)):
            dt = t - start
            if dt >= 0:
                v += 0.36 * math.exp(-dt * 11.0) * _note(freq, dt)
        out.append(v)
    return out


def gen_question_down() -> list[float]:
    """下行双音 B5→F#5(收束/反思感),~0.5s。"""
    dur = 0.5
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        v = 0.0
        for start, freq in ((0.0, 988.0), (0.16, 740.0)):
            dt = t - start
            if dt >= 0:
                v += 0.34 * math.exp(-dt * 10.0) * _note(freq, dt)
        out.append(v)
    return out


def gen_emphasis() -> list[float]:
    """单音软 ping A5(关键词/重点强调落地),~0.35s。"""
    dur = 0.35
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        out.append(0.36 * math.exp(-t * 13.0) * _note(880.0, t, (1.0, 0.20, 0.06)))
    return out


def gen_emphasis_tick() -> list[float]:
    """极短 tick(数字滚动/小词落地),~0.08s。"""
    dur = 0.08
    n = int(RATE * dur)
    noise = _noise(dur, 20260824)
    lp = _lowpass_2pole(noise, 3200.0)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.004) * math.exp(-t * 40.0)
        out.append(0.25 * env * lp[i])
    return out


def gen_reveal() -> list[float]:
    """轻 whoosh-open + 上行收尾(数据/图表出现),~0.4s。"""
    dur = 0.4
    n = int(RATE * dur)
    noise = _noise(dur, 20260825)
    lp = _lowpass_2pole(noise, 1100.0)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.05) * max(0.0, 1.0 - t / dur)
        v = 0.22 * env * lp[i]
        if t >= 0.18:  # 上行收尾音
            dt = t - 0.18
            v += 0.28 * math.exp(-dt * 12.0) * _note(1318.5, dt)
        out.append(v)
    return out


def gen_reveal_bloom() -> list[float]:
    """软和弦 bloom C6+E6+G6 齐响慢衰减(结论/高光出现),~0.8s。"""
    dur = 0.8
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        env = min(1.0, t / 0.03)
        decay = math.exp(-t * 3.5)
        v = 0.28 * env * decay * (_note(1046.5, t) + 0.6 * _note(1318.5, t) + 0.4 * _note(1568.0, t))
        out.append(v)
    return out


# ── 无版权轻音乐垫底(多轨,30-45s,确定性合成)────────────────────────
# 每轨: 软拨弦 arp(八分音符) + 慢起 pad + 正弦低音 + 主音旋律点 + 可选轻 shaker。
# 全部纯 stdlib,无版权风险。键位/和弦按"轻音乐"口粮设计,整体音量低于人声。
# 和弦表: 名字 -> (根音Hz, 三音Hz, 五音Hz, 低音Hz)
_CHORDS = {
    "C":  (261.63, 329.63, 392.00, 130.81),
    "G":  (196.00, 246.94, 293.66,  98.00),
    "Am": (220.00, 261.63, 329.63, 110.00),
    "F":  (174.61, 220.00, 261.63,  87.31),
    "D":  (293.66, 369.99, 440.00, 146.83),
    "Dm": (293.66, 349.23, 440.00, 146.83),
    "Em": (164.81, 196.00, 246.94,  82.41),
}

# 每轨配置: bpm / 和弦进行(每小节一个) / 音量 / 风格
_BGM_TRACKS = [
    # name, bpm, progression, pluck, pad, bass, lead, shaker, bars
    ("bgm-light-calm.wav",  90, ["C", "G", "Am", "F"] * 4,  0.20, 0.11, 0.17, 0.12, 0.00, 16),
    ("bgm-light-walk.wav", 108, ["G", "C", "D", "Em"] * 4,  0.22, 0.10, 0.18, 0.14, 0.04, 16),
    ("bgm-light-focus.wav", 84, ["Am", "F", "C", "G"] * 4,  0.18, 0.12, 0.16, 0.10, 0.00, 16),
    ("bgm-light-bright.wav", 120, ["F", "C", "G", "Am"] * 4, 0.22, 0.09, 0.18, 0.15, 0.06, 16),
]


def _pluck(freq: float, t: float, decay: float = 13.0,
           harmonics: tuple = (1.0, 0.28, 0.09)) -> float:
    """软拨弦/琴键音: 指数衰减 + 泛音,比 _note 更柔(decay 更缓、泛音更少)。"""
    out = 0.0
    for i, amp in enumerate(harmonics):
        f = freq * (i + 1)
        det = 1.0 + 0.003 * i
        out += amp * math.sin(2 * math.pi * f * det * t)
    return math.exp(-t * decay) * out


def _pad_env(t: float, bar: float) -> float:
    """慢起慢落的 pad 包络(每个和弦小节内),避免音头噗、结尾咔。"""
    return max(0.0, min(1.0, t / 0.5)) * max(0.0, min(1.0, (bar - t) / 0.7))


def gen_bgm_track(name: str) -> list[float]:
    bpm, prog, lv_p, lv_pd, lv_b, lv_l, lv_s, bars = next(
        t for t in _BGM_TRACKS if t[0] == name)[1:]
    beat = 60.0 / bpm
    bar = 4 * beat
    dur = bars * bar
    n = int(RATE * dur)
    out = [0.0] * n
    # 确定性 shaker 噪声(高频短噪,极轻)
    seed = sum(ord(c) for c in name) | 0x8000
    x = seed & 0xFFFFFFFF
    shk = []
    for _ in range(int(0.03 * RATE)):
        x = (1103515245 * x + 12345) & 0xFFFFFFFF
        shk.append((x / 0xFFFFFFFF) * 2.0 - 1.0)
    shk_len = len(shk)
    for b_i, chord_name in enumerate(prog):
        r3, r5, r7, bass = _CHORDS[chord_name]
        t0 = b_i * bar
        b0 = int(t0 * RATE)
        b1 = int((t0 + bar) * RATE)
        # 低音: 正弦 + 弱二次谐波,慢起
        for i in range(b0, b1):
            t = i / RATE - t0
            env = _pad_env(t, bar)
            out[i] += lv_b * env * (math.sin(2 * math.pi * bass * t)
                                    + 0.25 * math.sin(4 * math.pi * bass * t))
        # pad: 三音慢起(轻失谐)
        for f in (r3, r5, r7):
            det = f * 0.0015
            for i in range(b0, b1):
                t = i / RATE - t0
                out[i] += lv_pd * _pad_env(t, bar) * math.sin(2 * math.pi * (f + det) * t)
        # arp: 八分音符拨弦,根-五-三-五 循环
        arp_notes = (r3, r5, r7, r5)
        for k in range(8):
            freq = arp_notes[k % 4]
            at = t0 + k * beat / 2
            a0 = int(at * RATE)
            for i in range(int(0.32 * RATE)):
                idx = a0 + i
                if idx >= n:
                    break
                t = i / RATE
                out[idx] += lv_p * _pluck(freq, t)
        # 主音旋律点: 每小节第 1、3 拍,高八度的根/五音,稀疏轻灵
        for k in (0, 2):
            freq = (r3 * 2, r7 * 2)[k // 2]
            at = t0 + k * beat
            a0 = int(at * RATE)
            for i in range(int(0.4 * RATE)):
                idx = a0 + i
                if idx >= n:
                    break
                t = i / RATE
                out[idx] += lv_l * _pluck(freq, t, decay=9.0, harmonics=(1.0, 0.2, 0.05))
        # 轻 shaker: 每拍后半 30ms 高频短噪,给节奏一点空气感
        if lv_s > 0:
            for k in range(8):
                at = t0 + k * beat / 2 + beat / 4
                a0 = int(at * RATE)
                for j in range(shk_len):
                    idx = a0 + j
                    if idx >= n:
                        break
                    env = 1.0 - j / shk_len
                    out[idx] += lv_s * env * shk[j]
    # 整体 -7.5dB 头程: 垫底素材源 RMS 降到 ~-24dB,给混音留余量(peak 不再逼近 0dB)
    return [s * 0.42 for s in out]


def main() -> None:
    import os

    # 输出目录 = Remotion public 目录(与口播 mp3 同目录)。
    # 优先取 VIDEO_PROJECT_ROOT/narration(与 make video-remotion 一致),其次是
    # 显式 argv[1],最后退化为脚本所在仓的 video-generation/narration。
    proj_root = os.environ.get("VIDEO_PROJECT_ROOT")
    out_dir = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.join(proj_root, "video-generation", "narration")
        if proj_root
        else os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "narration",
        )
    )
    os.makedirs(out_dir, exist_ok=True)
    specs = {
        # 短音效:旧 3 个(向后兼容) + 新 10 个(2026-08-20 扩充)
        "sfx-opening.wav": gen_opening(),
        "sfx-opening-chime.wav": gen_opening_chime(),
        "sfx-opening-riser.wav": gen_opening_riser(),
        "sfx-transition.wav": gen_transition(),
        "sfx-transition-swoosh.wav": gen_transition_swoosh(),
        "sfx-transition-pop.wav": gen_transition_pop(),
        "sfx-question.wav": gen_question(),
        "sfx-question-up.wav": gen_question_up(),
        "sfx-question-down.wav": gen_question_down(),
        "sfx-emphasis.wav": gen_emphasis(),
        "sfx-emphasis-tick.wav": gen_emphasis_tick(),
        "sfx-reveal.wav": gen_reveal(),
        "sfx-reveal-bloom.wav": gen_reveal_bloom(),
        # 无版权轻音乐垫底:4 轨 30-45s(不同调性/节奏),bgm-bed 保留为 calm 别名(旧配置兼容)
        "bgm-light-calm.wav": gen_bgm_track("bgm-light-calm.wav"),
        "bgm-light-walk.wav": gen_bgm_track("bgm-light-walk.wav"),
        "bgm-light-focus.wav": gen_bgm_track("bgm-light-focus.wav"),
        "bgm-light-bright.wav": gen_bgm_track("bgm-light-bright.wav"),
        "bgm-bed.wav": gen_bgm_track("bgm-light-calm.wav"),
    }
    for name, samples in specs.items():
        path = os.path.join(out_dir, name)
        _write_wav(path, samples)
        print(f"✅ {name}: {len(samples)/RATE:.2f}s -> {path}")


if __name__ == "__main__":
    main()
