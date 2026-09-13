#!/usr/bin/env python3
"""一次性测量：统计一个 journal/ + lessons/ 的现状（供 references/analysis.md 复现数字）。

不属于技能运行时；随包发布只为让 analysis.md 里的数字可复现。

    python scripts/_measure.py [ROOT] [--journal NAME] [--lessons NAME]

ROOT 默认为当前目录；`--journal` 默认自动在 `journal/` 与 `work-log/` 之间挑一个。
与 journal.py 一致：标签解析同时接受中文默认与英文别名。
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import re

DATE_KEYS = ("日期", "Date")
VERIFY_WORDS = ("验证", "实测", "复核", "检查", "审查", "评审", "结果", "证据", "评估", "确认",
                "Verification", "Review", "Results", "Evidence", "Tests")
STATUS_KEYS = ("当前状态", "Status", "Current Status")
HISTORY_KEYS = ("历史状态", "Status History")


def _any(aliases: tuple[str, ...]) -> str:
    return "|".join(re.escape(a) for a in aliases)


def resolve_journal(name: str | None, root: str) -> str:
    if name:
        return os.path.join(root, name)
    for cand in ("journal", "work-log"):
        if os.path.isdir(os.path.join(root, cand)):
            return os.path.join(root, cand)
    return os.path.join(root, "journal")


def main() -> int:
    ap = argparse.ArgumentParser(description="统计 journal/ + lessons/ 现状（一次性测量工具）")
    ap.add_argument("root", nargs="?", default=".", help="项目根，默认当前目录")
    ap.add_argument("--journal", default=None, help="记录目录名；默认自动识别 journal/ 或 work-log/")
    ap.add_argument("--lessons", default="lessons", help="经验目录名（默认 lessons）")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    wl = resolve_journal(args.journal, root)
    ls = os.path.join(root, args.lessons)
    print(f"root    : {root}")
    print(f"journal : {wl}" + ("" if os.path.isdir(wl) else "   (不存在)"))
    print(f"lessons : {ls}" + ("" if os.path.isdir(ls) else "   (不存在)"))
    print()

    nums: dict[int, list[str]] = {}
    for dp, _dn, fn in os.walk(wl):
        for f in fn:
            m = re.match(r"^(\d+)-.*\.md$", f)
            if m:
                nums.setdefault(int(m.group(1)), []).append(
                    os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    ks = sorted(nums)
    if not ks:
        print("没有找到编号记录。")
        return 0
    print("entries:", len(ks), "range", ks[0], "-", ks[-1])
    print("duplicate numbers:", {k: v for k, v in nums.items() if len(v) > 1})
    print("gaps:", [n for n in range(ks[0], ks[-1] + 1) if n not in nums])

    files = [f for f in glob.glob(os.path.join(wl, "*.md"))
             if re.match(r"^\d+-", os.path.basename(f))]
    print("root entries:", len(files))
    with_date = with_sec = with_ver = 0
    for f in files:
        t = open(f, encoding="utf-8").read()
        with_date += bool(re.search(rf"^(?:{_any(DATE_KEYS)})[：:]", t, re.M))
        with_sec += bool(re.search(r"^##\s", t, re.M))
        with_ver += bool(re.search(rf"^##.*(?:{_any(VERIFY_WORDS)})", t, re.M))
    print("with date:", with_date, "with ## section:", with_sec, "with verify section:", with_ver)

    index = os.path.join(wl, "README.md")
    if os.path.isfile(index):
        idx = open(index, encoding="utf-8").read()
        links = re.findall(r"\]\(([^)]+\.md)\)", idx)
        dead = [l for l in links if not os.path.exists(os.path.normpath(os.path.join(wl, l)))]
        print("index links:", len(links), "dead:", dead)
        print("has status block:", bool(re.search(rf"^#{{2,3}}\s*.*(?:{_any(STATUS_KEYS)}).*$", idx, re.M)))
        print("has history block:", any(("## " + h) in idx for h in HISTORY_KEYS))
        print("index size chars:", len(idx))

    vols = sorted(glob.glob(os.path.join(ls, "*.md"))) if os.path.isdir(ls) else []
    cites: collections.Counter[int] = collections.Counter()
    for v in vols:
        t = open(v, encoding="utf-8").read()
        for m in re.finditer(r"wl/(\d+)", t):
            cites[int(m.group(1))] += 1
    print("lessons files:", [os.path.basename(v) for v in vols])
    print("citation refs:", sum(cites.values()), "distinct:", len(cites),
          "missing targets:", sorted(n for n in cites if n not in nums))
    print("entries never cited from lessons:", len([n for n in ks if n not in cites]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
