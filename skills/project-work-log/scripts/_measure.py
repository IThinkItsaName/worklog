#!/usr/bin/env python3
"""One-off measurement of the existing work-log/ + lessons/ layout.

Not part of the skill runtime; kept so the analysis in references/analysis.md
can be re-derived. Run from the project root:
    python .pi/skills/project-work-log/scripts/_measure.py
"""
import collections
import glob
import os
import re

ROOT = os.getcwd()
WL = os.path.join(ROOT, "work-log")
LS = os.path.join(ROOT, "lessons")

nums = {}
for dp, _dn, fn in os.walk(WL):
    for f in fn:
        m = re.match(r"^(\d+)-.*\.md$", f)
        if m:
            nums.setdefault(int(m.group(1)), []).append(
                os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/"))
ks = sorted(nums)
print("entries:", len(ks), "range", ks[0], "-", ks[-1])
print("duplicate numbers:", {k: v for k, v in nums.items() if len(v) > 1})
print("gaps:", [n for n in range(ks[0], ks[-1] + 1) if n not in nums])

files = [f for f in glob.glob(os.path.join(WL, "*.md"))
         if re.match(r"^\d+-", os.path.basename(f))]
print("root entries:", len(files))
with_date = with_sec = with_ver = 0
for f in files:
    t = open(f, encoding="utf-8").read()
    with_date += bool(re.search(r"^日期[：:]", t, re.M))
    with_sec += bool(re.search(r"^##\s", t, re.M))
    with_ver += bool(re.search(r"^##.*(验证|实测|复核)", t, re.M))
print("with 日期:", with_date, "with ## section:", with_sec, "with verify section:", with_ver)

# links in the work-log index
idx = open(os.path.join(WL, "README.md"), encoding="utf-8").read()
links = re.findall(r"\]\(([^)]+\.md)\)", idx)
dead = [l for l in links if not os.path.exists(os.path.normpath(os.path.join(WL, l)))]
print("index links:", len(links), "dead:", dead)

# lessons citations and coverage
vols = sorted(glob.glob(os.path.join(LS, "*.md")))
cites = collections.Counter()
for v in vols:
    t = open(v, encoding="utf-8").read()
    for m in re.finditer(r"wl/(\d+)", t):
        cites[int(m.group(1))] += 1
print("lessons files:", [os.path.basename(v) for v in vols])
print("citation refs:", sum(cites.values()), "distinct:", len(cites),
      "missing targets:", sorted(n for n in cites if n not in nums))
print("entries never cited from lessons:", len([n for n in ks if n not in cites]))

# status block sanity
m = re.search(r"## 当前状态[^\n]*\n(.*?)(?=\n## )", idx, re.S)
print("has 当前状态 block:", bool(m), "block chars:", len(m.group(1)) if m else 0)
print("has 历史状态 block:", "## 历史状态" in idx)
print("index size chars:", len(idx))
