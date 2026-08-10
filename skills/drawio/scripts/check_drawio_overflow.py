#!/usr/bin/env python3
"""批量检测 drawio 图中文字溢出框的问题。

检查每个 mxCell 的文字行数 vs geometry 高度。
行高估算: fontSize * 1.4 (含行间距)
"""
import io, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from pathlib import Path

DIAGRAMS_DIR = Path(__file__).resolve().parent.parent / "static" / "diagrams-src"

# 行高因子（经验值：fontSize * factor = 单行高度含行距）
LINE_HEIGHT_FACTOR = 1.5
PADDING = 8  # 上下内边距估计


def check_file(path: Path) -> list[dict]:
    """返回溢出的 cell 列表。"""
    issues = []
    content = path.read_text(encoding="utf-8")

    # 匹配每个 mxCell
    cell_pattern = re.compile(
        r'<mxCell\s+[^>]*?value="([^"]*?)"[^>]*?style="([^"]*?)"[^>]*?vertex="1"[^>]*?>\s*'
        r'<mxGeometry\s+x="([^"]+)"\s+y="([^"]+)"\s+width="([^"]+)"\s+height="([^"]+)"',
        re.DOTALL,
    )

    for match in cell_pattern.finditer(content):
        value, style, x, y, w, h = match.groups()
        if not value.strip():
            continue

        # 提取 fontSize
        fs_match = re.search(r'fontSize=(\d+)', style)
        font_size = int(fs_match.group(1)) if fs_match else 12

        # 计算文字行数
        # &#10; 是换行，&#xa; 也是
        lines_raw = re.split(r'&#10;|&#xa;|\n', value)
        # 去除 HTML 标签后计算每行实际显示宽度是否需要自动换行
        clean_lines = []
        for line in lines_raw:
            line = re.sub(r'<[^>]+>', '', line)
            line = line.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            clean_lines.append(line)

        # 估算每行需要的宽度（中文每字约 fontSize px，英文每字符约 fontSize*0.6 px）
        width = float(w)
        height = float(h)

        # 计算考虑自动换行后的实际行数
        total_lines = 0
        has_wrap = 'whiteSpace=wrap' in style
        for line in clean_lines:
            if not line.strip():
                total_lines += 1
                continue
            # 估算该行像素宽度
            cn_chars = len(re.findall(r'[一-鿿　-〿＀-￯]', line))
            en_chars = len(line) - cn_chars
            line_width = cn_chars * font_size + en_chars * font_size * 0.6
            if has_wrap and line_width > width - PADDING * 2:
                # 自动换行：估算需要几行
                wraps = max(1, int(line_width / (width - PADDING * 2)) + (1 if line_width % (width - PADDING * 2) else 0))
                total_lines += wraps
            else:
                total_lines += 1

        needed_height = total_lines * font_size * LINE_HEIGHT_FACTOR + PADDING * 2
        if needed_height > height + 2:  # 2px 容差
            issues.append({
                "value_preview": value[:80].replace('&#10;', '|'),
                "font_size": font_size,
                "lines": total_lines,
                "box_w": width,
                "box_h": height,
                "needed_h": round(needed_height),
                "overflow": round(needed_height - height),
                "x": x, "y": y,
            })
    return issues


def main():
    drawio_files = sorted(DIAGRAMS_DIR.glob("*.drawio"))
    if not drawio_files:
        print("No drawio files found.")
        return

    total_issues = 0
    for f in drawio_files:
        issues = check_file(f)
        if issues:
            print(f"\n{'='*60}")
            print(f"FILE: {f.name} ({len(issues)} issues)")
            print(f"{'='*60}")
            for i in issues:
                print(f"  [{i['x']},{i['y']}] {i['box_w']:.0f}x{i['box_h']:.0f} box, "
                      f"fs={i['font_size']}, {i['lines']} lines, "
                      f"needs {i['needed_h']}px → overflow {i['overflow']}px")
                print(f"    text: {i['value_preview']}")
            total_issues += len(issues)

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_issues} issues across {len(drawio_files)} files")


if __name__ == "__main__":
    main()
