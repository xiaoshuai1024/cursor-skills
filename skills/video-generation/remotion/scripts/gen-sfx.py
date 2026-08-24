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
  再扩 10 个(2026-08-24,对齐抖音科技/知识区高频音效类型,继续确定性合成零版权):
    sfx-transition-glitch.wav  数字故障抖动(配 glitch 转场) ~0.22s
    sfx-transition-tapestop.wav 磁带急停(音高快速下坠,悬念切断) ~0.35s
    sfx-impact.wav             低频重击(硬切强调/重点结论) ~0.5s
    sfx-coin.wav               金属双音(数据/收益/成本落地) ~0.3s
    sfx-ticktock.wav           时钟滴答两声(倒计时/时间线) ~0.9s
    sfx-heartbeat.wav          低频心跳(悬念/紧张铺垫) ~0.8s
    sfx-harp-gliss.wav         竖琴上行刮奏(揭晓/揭秘) ~0.7s
    sfx-ding.wav               清亮叮(里程碑/通知) ~0.6s
    sfx-typewriter.wav         打字机咔嗒(代码逐行/字幕) ~0.15s
    sfx-outro-chord.wav        终止式软和弦(收尾定格) ~1.4s

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


# ── 抖音风格扩充(2026-08-24:转场/功能/氛围音,继续"轻声"幅度纪律)─────────────

def gen_transition_glitch() -> list[float]:
    """数字故障抖动:3 段错位噪声碎片 + 方波跳频,配 glitch 转场,~0.22s。"""
    dur = 0.22
    n = int(RATE * dur)
    noise = _noise(dur, 20260826)
    out = []
    jumps = ((0.00, 0.05), (0.07, 0.04), (0.13, 0.09))  # (起点, 时长) 碎片错位
    freqs = (880.0, 1245.0, 660.0)
    for i in range(n):
        t = i / RATE
        v = 0.0
        for gi, (gs, gd) in enumerate(jumps):
            if gs <= t < gs + gd:
                # 方波跳频(数字感),载波随碎片切换
                v += 0.16 * math.copysign(1.0, math.sin(2 * math.pi * freqs[gi] * t))
        # 贯穿底噪(过中低通,像信号劣化)
        v += 0.14 * noise[int(i * 7.3) % n]
        env = min(1.0, t / 0.004) * max(0.0, 1.0 - t / dur)
        out.append(v * env)
    return out


def gen_transition_tapestop() -> list[float]:
    """磁带急停:音高快速下坠(高频→低频扫频 + 幅度骤收),悬念切断,~0.35s。"""
    dur = 0.35
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        # 下坠速率随时间加快(指数下坠感):相位积分用分段近似
        f = 900.0 * math.exp(-t * 14.0) + 90.0
        env = min(1.0, t / 0.01) * math.exp(-t * 9.0)
        v = env * (_note(f, t) + 0.3 * _note(f * 1.5, t))
        out.append(0.34 * v)
    return out


def gen_impact() -> list[float]:
    """低频重击:45Hz thump + 次谐波 + 5ms 噪声起音,硬切强调/重点结论,~0.5s。"""
    dur = 0.5
    n = int(RATE * dur)
    noise = _noise(dur, 20260827)
    lp = _lowpass_2pole(noise, 800.0)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.003) * math.exp(-t * 7.0)
        v = env * (math.sin(2 * math.pi * (45.0 + 30.0 * math.exp(-t * 25.0)) * t)
                   + 0.4 * math.sin(2 * math.pi * 90.0 * t))
        v += 0.10 * lp[i] * max(0.0, 1.0 - t / 0.05)  # 起音噪声
        out.append(0.38 * v)
    return out


def gen_coin() -> list[float]:
    """金属双音 B5→E6(短亮清脆,数据/收益/成本数字落地),~0.3s。"""
    dur = 0.3
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        v = 0.0
        for start, freq in ((0.0, 988.0), (0.07, 1318.5)):
            dt = t - start
            if dt >= 0:
                v += 0.32 * math.exp(-dt * 14.0) * _note(freq, dt, (1.0, 0.45, 0.18))
        out.append(v)
    return out


def gen_ticktock() -> list[float]:
    """时钟滴答两声:高频短噪 click + 2kHz 共振,第二声低一点(嗒),~0.9s。"""
    dur = 0.9
    n = int(RATE * dur)
    noise = _noise(dur, 20260828)
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        for start, f, amp in ((0.0, 2050.0, 0.30), (0.5, 1750.0, 0.24)):
            dt = t - start
            if 0 <= dt < 0.05:
                v += amp * math.exp(-dt * 60.0) * (_note(f, dt, (1.0, 0.3)) + 0.8 * noise[i])
        out.append(v)
    return out


def gen_heartbeat() -> list[float]:
    """低频心跳两下(咚-咚,第二下轻):悬念/紧张铺垫,~0.8s。"""
    dur = 0.8
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        v = 0.0
        for start, amp in ((0.0, 0.40), (0.28, 0.30)):
            dt = t - start
            if 0 <= dt < 0.22:
                env = min(1.0, dt / 0.012) * math.exp(-dt * 16.0)
                v += amp * env * (math.sin(2 * math.pi * 58.0 * dt)
                                  + 0.35 * math.sin(2 * math.pi * 116.0 * dt))
        out.append(v)
    return out


def gen_harp_gliss() -> list[float]:
    """竖琴上行刮奏:C 大调跨两个八度 8 音快速琶音,揭晓/揭秘,~0.7s。"""
    notes = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25, 587.33, 659.26]
    dur = 0.7
    n = int(RATE * dur)
    out = [0.0] * n
    step = 0.055
    for k, freq in enumerate(notes):
        a0 = int(k * step * RATE)
        for i in range(int(0.35 * RATE)):
            idx = a0 + i
            if idx >= n:
                break
            t = i / RATE
            out[idx] += 0.26 * math.exp(-t * 8.0) * _pluck(freq, t, decay=7.0, harmonics=(1.0, 0.35, 0.15))
    return out


def gen_ding() -> list[float]:
    """清亮叮:E6 纯高音慢衰减(比 emphasis 更亮更长),里程碑/通知,~0.6s。"""
    dur = 0.6
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        out.append(0.34 * min(1.0, t / 0.004) * math.exp(-t * 6.5)
                   * _note(1318.5, t, (1.0, 0.30, 0.10)))
    return out


def gen_typewriter() -> list[float]:
    """打字机双咔嗒:短噪 + 1.7kHz 板共振,代码逐行/字幕打出,~0.15s。"""
    dur = 0.15
    n = int(RATE * dur)
    noise = _noise(dur, 20260829)
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        for start, amp in ((0.0, 0.26), (0.06, 0.18)):
            dt = t - start
            if 0 <= dt < 0.03:
                v += amp * math.exp(-dt * 90.0) * (noise[i] + 0.6 * _note(1700.0, dt, (1.0, 0.2)))
        out.append(v)
    return out


def gen_outro_chord() -> list[float]:
    """终止式软和弦:G 和弦短推 → C 大三和弦长收(G→C resolution),收尾定格,~1.4s。"""
    dur = 1.4
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        v = 0.0
        # G 和弦(属)短推 0.35s
        if t < 0.4:
            env = min(1.0, t / 0.02) * math.exp(-t * 6.0)
            v += 0.20 * env * (_note(196.0, t) + 0.6 * _note(246.94, t) + 0.4 * _note(293.66, t))
        # C 大三和弦(主)长收 0.3s 起
        if t >= 0.3:
            dt = t - 0.3
            env = min(1.0, dt / 0.02) * math.exp(-dt * 2.8)
            v += 0.26 * env * (_note(261.63, dt) + 0.6 * _note(329.63, dt)
                               + 0.45 * _note(392.0, dt) + 0.3 * _note(523.25, dt))
        out.append(v)
    return out


# ── 无版权轻音乐垫底(多轨,30-45s,确定性合成)────────────────────────
# 每轨: 软拨弦 arp(八分音符) + 慢起 pad + 正弦低音 + 主音旋律点 + 可选轻 shaker。
# 全部纯 stdlib,无版权风险。键位/和弦按"轻音乐"口粮设计,整体音量低于人声。
# 和弦表: 名字 -> (根音Hz, 三音Hz, 五音/七音Hz, 低音Hz)。七和弦省五音用七音(爵士省略法)
_CHORDS = {
    "C":  (261.63, 329.63, 392.00, 130.81),
    "G":  (196.00, 246.94, 293.66,  98.00),
    "Am": (220.00, 261.63, 329.63, 110.00),
    "F":  (174.61, 220.00, 261.63,  87.31),
    "D":  (293.66, 369.99, 440.00, 146.83),
    "Dm": (293.66, 349.23, 440.00, 146.83),
    "Em": (164.81, 196.00, 246.94,  82.41),
    # 七和弦(lofi 用):根/三/七/低音,省五音
    "Cmaj7":  (261.63, 329.63, 493.88, 130.81),
    "Am7":    (220.00, 261.63, 392.00, 110.00),
    "Fmaj7":  (174.61, 220.00, 329.63,  87.31),
    "G7":     (196.00, 246.94, 349.23,  98.00),
}

# 每轨配置: bpm / 和弦进行(每小节一个) / 音量 / 风格。
# 风格开关(2026-08-24): pulse=八分脉冲低音(悬疑) / square=方波 arp(8-bit) / kick=拍点底鼓(史诗)
_BGM_TRACKS: list[tuple] = [
    # name, bpm, progression, pluck, pad, bass, lead, shaker, bars [, pulse, square, kick]
    ("bgm-light-calm.wav",  90, ["C", "G", "Am", "F"] * 4,  0.20, 0.11, 0.17, 0.12, 0.00, 16),
    ("bgm-light-walk.wav", 108, ["G", "C", "D", "Em"] * 4,  0.22, 0.10, 0.18, 0.14, 0.04, 16),
    ("bgm-light-focus.wav", 84, ["Am", "F", "C", "G"] * 4,  0.18, 0.12, 0.16, 0.10, 0.00, 16),
    ("bgm-light-bright.wav", 120, ["F", "C", "G", "Am"] * 4, 0.22, 0.09, 0.18, 0.15, 0.06, 16),
    # ── 抖音风格扩充(2026-08-24):悬疑脉冲 / 史诗推进 / 8-bit / Lo-fi ──
    ("bgm-tense.wav",    76, ["Am", "F", "Dm", "Em"] * 4,      0.09, 0.12, 0.20, 0.06, 0.00, 16, 1, 0, 0),
    ("bgm-epic.wav",     96, ["Dm", "Am", "F", "C"] * 4,       0.15, 0.13, 0.18, 0.13, 0.05, 16, 0, 0, 1),
    ("bgm-chiptune.wav", 128, ["F", "G", "C", "Am"] * 4,       0.17, 0.06, 0.13, 0.12, 0.08, 16, 0, 1, 0),
    ("bgm-lofi.wav",     72, ["Cmaj7", "Am7", "Fmaj7", "G7"] * 4, 0.15, 0.14, 0.14, 0.07, 0.025, 16),
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
    t = next(t for t in _BGM_TRACKS if t[0] == name)
    bpm, prog, lv_p, lv_pd, lv_b, lv_l, lv_s, bars = t[1:9]
    pulse = t[9] if len(t) > 9 else 0
    square = t[10] if len(t) > 10 else 0
    kick = t[11] if len(t) > 11 else 0
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
        # 低音: 正弦 + 弱二次谐波,慢起(pulse=1 时改为八分音符短脉冲,悬疑驱动感)
        if pulse:
            for k in range(8):
                at = t0 + k * beat / 2
                a0 = int(at * RATE)
                for i in range(int(0.16 * RATE)):
                    idx = a0 + i
                    if idx >= n:
                        break
                    tt = i / RATE
                    env = min(1.0, tt / 0.008) * math.exp(-tt * 11.0)
                    out[idx] += lv_b * env * (math.sin(2 * math.pi * bass * tt)
                                              + 0.2 * math.sin(4 * math.pi * bass * tt))
        else:
            for i in range(b0, b1):
                t = i / RATE - t0
                env = _pad_env(t, bar)
                out[i] += lv_b * env * (math.sin(2 * math.pi * bass * t)
                                        + 0.25 * math.sin(4 * math.pi * bass * t))
        # 底鼓(kick=1): 每拍 48Hz 快衰减 thump,史诗推进的骨架
        if kick:
            for k in range(4):
                at = t0 + k * beat
                a0 = int(at * RATE)
                for i in range(int(0.18 * RATE)):
                    idx = a0 + i
                    if idx >= n:
                        break
                    tt = i / RATE
                    env = min(1.0, tt / 0.004) * math.exp(-tt * 9.0)
                    out[idx] += kick * env * math.sin(2 * math.pi * (48.0 + 26.0 * math.exp(-tt * 30.0)) * tt)
        # pad: 三音慢起(轻失谐)
        for f in (r3, r5, r7):
            det = f * 0.0015
            for i in range(b0, b1):
                t = i / RATE - t0
                out[i] += lv_pd * _pad_env(t, bar) * math.sin(2 * math.pi * (f + det) * t)
        # arp: 八分音符,根-五-三-五 循环(square=1 时用方波,8-bit 味)
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
                if square:
                    env = min(1.0, t / 0.004) * math.exp(-t * 10.0)
                    out[idx] += lv_p * env * 0.6 * math.copysign(1.0, math.sin(2 * math.pi * freq * 2 * t))
                else:
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
        # 短音效:旧 3 个(向后兼容) + 2026-08-20 扩充 10 个 + 2026-08-24 抖音风格 10 个
        "sfx-opening.wav": gen_opening(),
        "sfx-opening-chime.wav": gen_opening_chime(),
        "sfx-opening-riser.wav": gen_opening_riser(),
        "sfx-transition.wav": gen_transition(),
        "sfx-transition-swoosh.wav": gen_transition_swoosh(),
        "sfx-transition-pop.wav": gen_transition_pop(),
        "sfx-transition-glitch.wav": gen_transition_glitch(),
        "sfx-transition-tapestop.wav": gen_transition_tapestop(),
        "sfx-question.wav": gen_question(),
        "sfx-question-up.wav": gen_question_up(),
        "sfx-question-down.wav": gen_question_down(),
        "sfx-emphasis.wav": gen_emphasis(),
        "sfx-emphasis-tick.wav": gen_emphasis_tick(),
        "sfx-impact.wav": gen_impact(),
        "sfx-coin.wav": gen_coin(),
        "sfx-ticktock.wav": gen_ticktock(),
        "sfx-heartbeat.wav": gen_heartbeat(),
        "sfx-harp-gliss.wav": gen_harp_gliss(),
        "sfx-ding.wav": gen_ding(),
        "sfx-typewriter.wav": gen_typewriter(),
        "sfx-reveal.wav": gen_reveal(),
        "sfx-reveal-bloom.wav": gen_reveal_bloom(),
        "sfx-outro-chord.wav": gen_outro_chord(),
        # 无版权轻音乐垫底:4 轻 + 4 抖音风格(悬疑/史诗/8-bit/Lo-fi),
        # bgm-bed 保留为 calm 别名(旧配置兼容)
        "bgm-light-calm.wav": gen_bgm_track("bgm-light-calm.wav"),
        "bgm-light-walk.wav": gen_bgm_track("bgm-light-walk.wav"),
        "bgm-light-focus.wav": gen_bgm_track("bgm-light-focus.wav"),
        "bgm-light-bright.wav": gen_bgm_track("bgm-light-bright.wav"),
        "bgm-tense.wav": gen_bgm_track("bgm-tense.wav"),
        "bgm-epic.wav": gen_bgm_track("bgm-epic.wav"),
        "bgm-chiptune.wav": gen_bgm_track("bgm-chiptune.wav"),
        "bgm-lofi.wav": gen_bgm_track("bgm-lofi.wav"),
        "bgm-bed.wav": gen_bgm_track("bgm-light-calm.wav"),
    }
    for name, samples in specs.items():
        path = os.path.join(out_dir, name)
        _write_wav(path, samples)
        print(f"✅ {name}: {len(samples)/RATE:.2f}s -> {path}")


if __name__ == "__main__":
    main()
