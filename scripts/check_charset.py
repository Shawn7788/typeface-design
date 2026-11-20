#!/usr/bin/env python3
"""Compare a font's preferred Unicode cmap with a supplied UTF-8 character list."""

import argparse
import re
import string
import struct
import sys
import unicodedata
from pathlib import Path


def describe(point):
    name = unicodedata.name(chr(point), "UNNAMED")
    return f"U+{point:04X} {name}"


def read_charset(path):
    points = set()
    for token in path.read_text(encoding="utf-8-sig").split():
        if token.upper().startswith("U+"):
            if not re.fullmatch(r"U\+[0-9A-Fa-f]{4,6}", token, re.IGNORECASE):
                raise ValueError(f"無效的 Unicode 碼位 {token!r}")
            point = int(token[2:], 16)
            if point > 0x10FFFF or 0xD800 <= point <= 0xDFFF:
                raise ValueError(f"無效的 Unicode 純量值 {token!r}")
            group = (point,)
        else:
            group = map(ord, token)
        for point in group:
            if point in points:
                raise ValueError(f"清單內字元重複　{describe(point)}")
            points.add(point)
    if not points:
        raise ValueError("字元清單為空。")
    return points


def check_assignment_list(points):
    if len(points) != 104:
        raise ValueError(f"清單有 {len(points)} 個不同字元，作業模板應有 104 個。")
    basic = set(map(ord, string.ascii_letters + string.digits))
    missing = sorted(basic - points)
    if missing:
        raise ValueError("清單欠缺基本字母或數字　" + " ".join(map(chr, missing)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path, help="要檢查的字檔")
    parser.add_argument("charset", type=Path, help="從模板轉錄的 UTF-8 純文字清單")
    parser.add_argument("--assignment-3", action="store_true",
                        help="檢查 104 字元、拉丁大小寫、數字及 .otf 檔案格式")
    args = parser.parse_args()
    try:
        from fontTools.ttLib import TTFont, TTLibError
    except ModuleNotFoundError:
        parser.exit(2, "此工具需要 fontTools。請在所用環境執行 python3 -m pip install fonttools。\n")

    try:
        expected = read_charset(args.charset)
        if args.assignment_3:
            check_assignment_list(expected)
            if args.font.suffix.lower() != ".otf":
                raise ValueError("作業模式需要副檔名為 .otf 的字檔。")
        with TTFont(args.font) as font:
            if args.assignment_3 and (font.flavor or font.sfntVersion not in ("OTTO", "\x00\x01\x00\x00")):
                raise ValueError("請使用從製字軟件匯出的桌面 OpenType 字檔。")
            cmap = font.getBestCmap()
            if not cmap:
                raise ValueError("字檔沒有可用的 Unicode cmap。")
            glyphs = set(font.getGlyphOrder()[1:])  # Glyph ID 0 is the missing-glyph fallback.
            glyphs.discard(".notdef")
            missing = sorted(point for point in expected if cmap.get(point) not in glyphs)
    except (OSError, ValueError, KeyError, TTLibError, struct.error) as error:
        parser.exit(2, f"無法完成核對　{error}\n")

    print(f"Unicode 映射覆蓋　{len(expected) - len(missing)}/{len(expected)}")
    for point in missing:
        print(f"欠缺　{describe(point)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
