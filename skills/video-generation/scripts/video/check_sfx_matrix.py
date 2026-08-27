"""check_sfx_matrix.py - SFX 场景矩阵双管线同源一致性机检。

比对 config.py::SFX_SCENARIO_MATRIX（Python 管线）与 remotion core/sound-points.ts
::SFX_SCENARIOS（Remotion 管线）：场景集合、每场景条目顺序、文件名、mood 映射
必须逐条一致（同源镜像纪律，openspec video-sfx-scenario-palette）。
挂载 make video-lint；不一致 FAIL 阻断。

用法: python -m video.check_sfx_matrix
"""
import re
import sys
from pathlib import Path

from . import config as C

TS_PATH = C.ROOT / "remotion" / "src" / "core" / "sound-points.ts"


def parse_ts_matrix(ts_src: str) -> dict[str, list[tuple[str, tuple[str, ...]]]]:
    """从 sound-points.ts 提取 SFX_SCENARIOS 字面量(不引 ts 依赖,正则解析)。"""
    m = re.search(r"export const SFX_SCENARIOS[^=]*=\s*\{(.*?)\n\};", ts_src, re.S)
    if not m:
        raise SystemExit("❌ sound-points.ts 里找不到 SFX_SCENARIOS 导出")
    matrix: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    # 逐场景块切分: "scenario: [ {...}, {...} ]"
    for scen_m in re.finditer(r'(\w+):\s*\[((?:\s*\{[^}]*\},?)+)\s*\]', m.group(1)):
        scenario = scen_m.group(1)
        entries = []
        for e_m in re.finditer(r'\{\s*file:\s*"([^"]+)"\s*,\s*moods:\s*\[([^\]]*)\]\s*\}', scen_m.group(2)):
            file = e_m.group(1)
            moods = tuple(re.findall(r'"([^"]+)"', e_m.group(2)))
            entries.append((file, moods))
        matrix[scenario] = entries
    return matrix


def main() -> int:
    ts_matrix = parse_ts_matrix(TS_PATH.read_text(encoding="utf-8"))
    py_matrix = {k: [(f, tuple(m)) for f, m in v] for k, v in C.SFX_SCENARIO_MATRIX.items()}

    problems: list[str] = []
    py_only = set(py_matrix) - set(ts_matrix)
    ts_only = set(ts_matrix) - set(py_matrix)
    if py_only:
        problems.append(f"场景只在 config.py: {sorted(py_only)}")
    if ts_only:
        problems.append(f"场景只在 sound-points.ts: {sorted(ts_only)}")
    for scen in sorted(set(py_matrix) & set(ts_matrix)):
        if py_matrix[scen] != ts_matrix[scen]:
            problems.append(f"场景 {scen} 条目不一致:\n  py={py_matrix[scen]}\n  ts={ts_matrix[scen]}")

    if problems:
        print("❌ SFX 矩阵双源漂移(改一边必须同步另一边,文档 SSOT=references/sound-design.md §五):")
        for p in problems:
            print(f"  - {p}")
        return 1
    total = sum(len(v) for v in py_matrix.values())
    print(f"✅ SFX 场景矩阵同源一致: {len(py_matrix)} 场景 / {total} 条目"
          f"（config.py ↔ sound-points.ts）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
