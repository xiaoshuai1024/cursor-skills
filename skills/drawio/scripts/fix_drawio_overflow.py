#!/usr/bin/env python3
"""批量修复 drawio 图中文字溢出框的问题。

对每个有文字的 vertex，计算所需高度，如果当前高度不够则增加到所需高度。
"""
import io, re, sys, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import xml.etree.ElementTree as ET
from pathlib import Path

DIAGRAMS_DIR = Path(__file__).resolve().parent.parent / "static" / "diagrams-src"
LINE_HEIGHT_FACTOR = 1.4  # 行高因子（drawio 实际渲染约 1.3-1.4）
PADDING = 10  # 上下内边距


def calc_needed_height(value: str, style: str, width: float) -> tuple[int, int]:
    """返回 (needed_height, line_count)。"""
    # 提取 fontSize
    fs_match = re.search(r'fontSize=(\d+)', style)
    font_size = int(fs_match.group(1)) if fs_match else 12

    has_wrap = 'whiteSpace=wrap' in style

    # 计算行数（考虑自动换行）
    lines_raw = re.split(r'&#10;|&#xa;|\n', value)
    total_lines = 0
    for line in lines_raw:
        clean = re.sub(r'<[^>]+>', '', line)
        clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        clean = clean.replace('&#160;', ' ').replace('&quot;', '"').replace('&nbsp;', ' ')
        if not clean.strip():
            total_lines += 1
            continue
        cn_chars = len(re.findall(r'[一-鿿　-〿＀-￯]', clean))
        en_chars = len(clean) - cn_chars
        line_width = cn_chars * font_size + en_chars * font_size * 0.6
        if has_wrap and line_width > width - PADDING * 2:
            wraps = max(1, -(-int(line_width) // int(width - PADDING * 2)))  # ceil div
            total_lines += wraps
        else:
            total_lines += 1

    needed = int(total_lines * font_size * LINE_HEIGHT_FACTOR + PADDING * 2)
    # 向上取整到 5 的倍数
    needed = ((needed + 4) // 5) * 5
    return needed, total_lines


def fix_file(path: Path) -> int:
    """修复单个 drawio 文件，返回修复的 cell 数。"""
    # 先备份
    backup = path.with_suffix('.drawio.bak')
    shutil.copy2(path, backup)

    tree = ET.parse(path)
    root = tree.getroot()

    fixes = 0
    for cell in root.iter('mxCell'):
        value = cell.get('value', '')
        style = cell.get('style', '')
        vertex = cell.get('vertex', '')

        if not value.strip() or vertex != '1':
            continue
        if not style:
            continue

        geom = cell.find('mxGeometry')
        if geom is None:
            continue

        w = float(geom.get('width', 200))
        h = float(geom.get('height', 50))

        needed, lines = calc_needed_height(value, style, w)
        if needed > h + 2:
            geom.set('height', str(needed))
            fixes += 1

    if fixes > 0:
        tree.write(path, encoding='utf-8', xml_declaration=False)
    else:
        backup.unlink()  # 没修复就删掉备份

    return fixes


def main():
    drawio_files = sorted(DIAGRAMS_DIR.glob("*.drawio"))
    if not drawio_files:
        print("No drawio files found.")
        return

    total_fixes = 0
    for f in drawio_files:
        if f.suffix == '.bak':
            continue
        try:
            fixes = fix_file(f)
            status = f"  {fixes} cells fixed" if fixes else "  OK"
            print(f"{f.name}: {status}")
            total_fixes += fixes
        except ET.ParseError as e:
            print(f"{f.name}: PARSE ERROR - {e}")

    print(f"\nTotal: {total_fixes} cells fixed across {len(drawio_files)} files")
    print("Backups saved as .drawio.bak")


if __name__ == "__main__":
    main()
