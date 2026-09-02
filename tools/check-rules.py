#!/usr/bin/env python3
"""デザインルールの機械チェック。

使い方: python3 tools/check-rules.py design-rule/sample.html
        python3 tools/check-rules.py --baseline memo/sample.html ...

--baseline は違反を報告するが exit 0 で終わる（実物デッキの現状把握用）。
"""
import re
import sys

TOKENS = {
    "--surround": "#171410", "--paper": "#F8F6F2", "--card": "#FFFFFF",
    "--ink": "#26333F", "--ink-2": "#4E5F60", "--ink-3": "#8B98A4",
    "--line": "#E6E1D9", "--fill": "#F1ECE4", "--accent": "#D9822B",
    "--neg": "#DC4A4A", "--pos": "#12776A",
}
PALETTE = {v.upper() for v in TOKENS.values()}
SCALE = {"0.8", ".8", "1.2", "1.8", "2.8", "5.2"}


def check_palette(src):
    """パレット外の生 hex 値を拾う。"""
    bad = sorted({h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", src)} - PALETTE)
    return [f"パレット外の色: {h}" for h in bad]


def check_scale(src):
    """font-size / font: 短縮形の cqw 値が5段に収まっているか。"""
    sizes = set()
    for decl in re.findall(r"font(?:-size)?\s*:\s*[^;{}]*", src):
        for m in re.findall(r"(\d*\.?\d+)cqw", decl):
            sizes.add(m.rstrip("0").rstrip(".") if "." in m else m)
    bad = sorted(s for s in sizes if s not in SCALE and s.lstrip("0") not in SCALE)
    return [f"タイプスケール外の文字サイズ: {s}cqw" for s in bad]


def check_shadow(src):
    """影は2段のみ、drop-shadow は禁止。"""
    out = []
    if "drop-shadow" in src:
        out.append("drop-shadow は使わない（box-shadow の2段のみ）")
    allowed = {
        "0 .12cqw .8cqw rgba(38,51,63,.06)",
        "0 .2cqw 1cqw rgba(38,51,63,.14)",
    }
    for v in re.findall(r"box-shadow\s*:\s*([^;{}]+)", src):
        norm = " ".join(v.split()).rstrip()
        if norm not in allowed:
            out.append(f"規定外の影: {norm}")
    return out


def check_skeleton(src):
    """固定ゾーンがそのままコピーされているか。"""
    out = []
    checks = [
        (r"container-type\s*:\s*size", "`.deck` に container-type:size がない"),
        (r"width\s*:\s*min\(100vw,\s*177\.78vh\)", "16:9 の .deck 幅指定がない"),
        (r"padding\s*:\s*[\d.]+cqw\s+5\.2cqw", ".slide の横 padding が 5.2cqw でない"),
        (r"animation:\s*revealIn\s+\.55s", ".reveal が .55s でない"),
        (r"var\(--i,\s*0\)\s*\*\s*\.12s", ".reveal の遅延が .12s でない"),
    ]
    for pattern, msg in checks:
        if not re.search(pattern, src):
            out.append(msg)
    return out


def check_units(src):
    """レイアウトに px を混ぜていないか（線幅 1px と 999px の丸めは許す）。"""
    bad = set()
    for m in re.findall(r"(?:padding|margin|gap|width|height|top|left|right|bottom)\s*:\s*[^;{}]*?(\d*\.?\d+)px", src):
        if m not in {"1", "999"}:
            bad.add(m)
    return [f"レイアウトに px: {v}px（cqw を使う）" for v in sorted(bad)]


CHECKS = [check_palette, check_scale, check_shadow, check_skeleton, check_units]


def main(argv):
    baseline = "--baseline" in argv
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if not paths:
        print("使い方: check-rules.py [--baseline] <html...>", file=sys.stderr)
        return 2

    total = 0
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        problems = [p for check in CHECKS for p in check(src)]
        total += len(problems)
        mark = "OK" if not problems else f"{len(problems)}件"
        print(f"\n=== {path} — {mark} ===")
        for p in problems:
            print(f"  - {p}")

    print(f"\n合計 {total} 件")
    return 0 if (baseline or total == 0) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
