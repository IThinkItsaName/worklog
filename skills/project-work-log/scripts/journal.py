#!/usr/bin/env python3
"""journal.py — 项目长期工作记录（journal + lessons）的工具箱。

设计目标：**少读、少写、可校验**。
- 少读：brief / show / search / outline 只吐出需要的那点内容，不必读 50 KB 的索引。
- 少写：status / todo / index / append / lesson 做外科式行级编辑（保留 CRLF 与其余字节）。
- 可校验：check 查结构，lint 查内容质量，两者都可当门禁（退出码 1）。

命令分组
--------
读写 · 上下文
    brief     压缩上下文快照（当前状态 + 待办 + 近期记录），替代整读索引
    show      单篇大纲（元数据 + 小节 + 行数），决定要不要读全文
    search    定向检索（记录 + 经验），只回命中行
    outline   全部记录的一行表（编号/日期/变更集/标题）

读写 · 维护
    new       生成下一篇记录（--insert 自动补索引行）
    status    当前状态块：show / set / date / roll
    todo      待办清单：list / add / done / drop-done
    index     索引：sync 补漏行
    lesson    经验：add 追加带来源的条目
    append    向某篇记录追加小节（更正 / 遗留）

读写 · 分析与生成
    check     结构门禁（编号、日期、验证、死链、漏索引、状态、来源）
    lint      内容质量（占位符残留、空小节、含糊措辞、结论缺数字）
    stats     语料统计（节奏、长度、合规率、引用覆盖）
    topics    同主题簇建议（关键词共现 / --keywords 指定）
    digest    生成交接摘要文档（--out 落盘）
    retro     阶段复盘骨架（篇号区间 → 阶段表 + 遗留汇总）
    export    机器可读导出（--json / --csv）

只用 Python 标准库。约定见 references/conventions.md，模板见 references/templates.md。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys

try:  # Windows 控制台默认码页可能不是 UTF-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

# 约定关键词（与 references/conventions.md 保持一致）
K_DATE = "日期"
K_ITER = "变更集"
K_VERIFY = "验证"
K_STATUS = "当前状态"
K_TODO = "待办"

ENTRY_RE = re.compile(r"^(\d+)-.*\.md$")
HEADING_RE = re.compile(r"^#\s*(\d+)\s*[·.、:：]")
H1_RE = re.compile(r"^#\s+(.+)$", re.M)
DATE_LINE_RE = re.compile(r"^日期\s*[：:]\s*(\S+)", re.M)
ISO_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
VERIFY_HEAD_RE = re.compile(r"^#{2,3}\s*.*(验证|实测|复核|Verification)", re.M)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
CITE_RE = re.compile(r"wl/(\d{1,4})")

STATUS_KEYS = ["分支 / HEAD", "变更集", "构建", "测试", "交付物与指纹", "环境", "阻塞 / 等待"]

PLACEHOLDERS = ["<验证命令>", "<一句话", "<标题", "<path>", "<项目>", "TODO", "TBD", "XXX", "待填", "待补充"]
VAGUE = ["应该没问题", "应该可以", "大概", "可能没问题", "似乎", "估计", "应该是"]

STOPWORDS = {
    "this", "that", "with", "from", "http", "https", "true", "false", "null", "none",
    "test", "tests", "todo", "readme", "index", "file", "files", "line", "lines",
    "data", "path", "name", "type", "value", "list", "item", "items", "https",
}

ENTRY_TEMPLATE = """# {num:04d} · {title}

日期：{date}
变更集：{iter}
触发：
范围：
结论：

---

## 一、背景与事实核查

## 二、方案与取舍

## 三、实施

| 文件 | 改动 |
|---|---|
|  |  |

## 四、验证

- 命令：`{cmd}`
- 结果：
- 未覆盖：

## 五、遗留与下一步

- [ ] 
"""

STATUS_SKELETON = """## {head}（{date}）

{fields}
"""


# --------------------------------------------------------------------------- #
# IO / 通用工具
# --------------------------------------------------------------------------- #
def read(path: str) -> str:
    """读取并归一换行（仅用于解析，不用于回写）。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def read_raw(path: str) -> str:
    """保留原始换行读取（外科式编辑用）。"""
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            return fh.read()
    except OSError:
        return ""


def write_raw(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def nl_of(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def resolve_dir(root: str, name: str | None, fallbacks: tuple[str, ...]) -> str | None:
    for c in ([name] if name else list(fallbacks)):
        if c and os.path.isdir(os.path.join(root, c)):
            return os.path.join(root, c)
    return None


def find_entries(journal: str) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    for dp, dn, fn in os.walk(journal):
        dn[:] = [d for d in dn if d not in (".git", "node_modules")]
        for f in fn:
            m = ENTRY_RE.match(f)
            if m:
                found.setdefault(int(m.group(1)), []).append(os.path.join(dp, f))
    return found


def is_root_entry(journal: str, path: str) -> bool:
    return os.path.dirname(os.path.abspath(path)) == os.path.abspath(journal)


def max_date_in(text: str) -> _dt.date | None:
    best = None
    for m in ISO_DATE_RE.finditer(text):
        try:
            d = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if best is None or d > best:
            best = d
    return best


def today() -> str:
    return _dt.date.today().isoformat()


def slugify(title: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "-", title).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)[:48] or "entry"


def meta_of(path: str) -> dict:
    """解析一篇记录的元数据（不全量保留正文）。"""
    text = read(path)
    h1 = H1_RE.search(text)
    title = re.sub(r"^\d+\s*[·.、:：]\s*", "", h1.group(1)).strip() if h1 else os.path.basename(path)
    dm = DATE_LINE_RE.search(text)
    im = re.search(rf"^{K_ITER}\s*[：:]\s*(\S+)", text, re.M)
    cm = re.search(r"^结论\s*[：:]\s*(.+)$", text, re.M)
    sections = re.findall(r"^(#{2,3})\s+(.+?)\s*$", text, re.M)
    return {
        "title": title,
        "date": dm.group(1) if dm else "",
        "iter": im.group(1) if im else "",
        "conclusion": (cm.group(1).strip() if cm else ""),
        "sections": [s[1] for s in sections],
        "lines": text.count("\n") + 1,
        "bytes": len(text.encode("utf-8")),
        "has_date": bool(dm),
        "has_verify": bool(VERIFY_HEAD_RE.search(text)),
    }


def all_metas(entries: dict[int, list[str]]) -> dict[int, dict]:
    return {n: meta_of(paths[0]) for n, paths in entries.items()}


# --------------------------------------------------------------------------- #
# 行级小节工具（保留换行与其余内容）
# --------------------------------------------------------------------------- #
def heading_level(line: str):
    m = re.match(r"^(#{1,6})[ \t]+(.*?)[ \t]*\r?\n?$", line)
    return (len(m.group(1)), m.group(2)) if m else None


def find_section(lines: list[str], level: int, keyword: str):
    """返回 (head_idx, body_start, body_end_exclusive)；body_end 为下一个同级或更高级标题。"""
    for i, line in enumerate(lines):
        h = heading_level(line)
        if h and h[0] == level and keyword in h[1]:
            j = i + 1
            while j < len(lines):
                hj = heading_level(lines[j])
                if hj and hj[0] <= level:
                    break
                j += 1
            return i, i + 1, j
    return None


def last_content_line(lines: list[str], start: int, end: int) -> int:
    """[start, end) 内最后一个非空行的下标；全空返回 start-1。"""
    for i in range(end - 1, start - 1, -1):
        if lines[i].strip():
            return i
    return start - 1


def insert_at_end_of_section(lines: list[str], start: int, end: int, new_lines: list[str]) -> None:
    pos = last_content_line(lines, start, end) + 1
    lines[pos:pos] = new_lines


# --------------------------------------------------------------------------- #
# check：结构门禁
# --------------------------------------------------------------------------- #
class Report:
    def __init__(self, strict: bool) -> None:
        self.strict = strict
        self.rows: list[tuple[str, str]] = []
        self._seen: set[tuple[str, str]] = set()

    def add(self, level: str, where: str, msg: str) -> None:
        if self.strict and level == "WARN":
            level = "ERROR"
        key = (level, f"{where}: {msg}")
        if key in self._seen:
            return
        self._seen.add(key)
        self.rows.append((level, f"{where}: {msg}"))

    def errors(self) -> int:
        return sum(1 for lv, _ in self.rows if lv == "ERROR")

    def print(self, quiet: bool) -> None:
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        for lv, text in sorted(self.rows, key=lambda r: order[r[0]]):
            if quiet and lv == "INFO":
                continue
            print(f"[{lv}] {text}")
        n = {lv: sum(1 for l, _ in self.rows if l == lv) for lv in ("ERROR", "WARN", "INFO")}
        print(f"\nSummary: {n['ERROR']} error / {n['WARN']} warn / {n['INFO']} info"
              + ("  (--strict)" if self.strict else ""))


def _check_links(root: str, path: str, rep: Report) -> None:
    base = os.path.dirname(path)
    where = rel(root, path)
    seen = set()
    for target in LINK_RE.findall(read(path)):
        if target.startswith(("http://", "https://", "mailto:", "#")) or not target.endswith(".md"):
            continue
        clean = target.split("#", 1)[0].strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        if not os.path.exists(os.path.normpath(os.path.join(base, clean))):
            rep.add("ERROR", where, f"死链：{target}")


def check(root: str, journal_arg: str | None, lessons_arg: str | None, strict: bool) -> Report:
    rep = Report(strict)
    journal = resolve_dir(root, journal_arg, ("journal", "work-log"))
    if not journal:
        rep.add("ERROR", root, "找不到记录目录（journal/ 或 work-log/）；先按 templates.md 初始化")
        return rep
    jname = rel(root, journal)
    index = os.path.join(journal, "README.md")
    if not os.path.isfile(index):
        rep.add("ERROR", jname, "缺索引 README.md（台账）")

    entries = find_entries(journal)
    nums = sorted(entries)
    if not entries:
        rep.add("INFO", jname, "目录里还没有编号记录（新项目正常）")
    for n, paths in sorted(entries.items()):
        if len(paths) > 1:
            rep.add("ERROR", jname, f"编号 {n} 重复：{[rel(root, p) for p in paths]}")
    if nums:
        gaps = [n for n in range(nums[0], nums[-1] + 1) if n not in entries]
        if gaps:
            shown = ", ".join(str(g) for g in gaps[:10]) + (" …" if len(gaps) > 10 else "")
            rep.add("WARN", jname, f"编号断档 {len(gaps)} 处：{shown}")

    total = sum(len(v) for v in entries.values())
    date_missing = verify_missing = 0
    for n in nums:
        for path in entries[n]:
            text = read(path)
            where = rel(root, path)
            h1 = H1_RE.search(text)
            if not h1:
                rep.add("WARN", where, "缺一级标题（应为 `# NNNN · 标题`）")
            else:
                m = HEADING_RE.match("# " + h1.group(1))
                if not m:
                    rep.add("WARN", where, "一级标题未带篇号（应为 `# NNNN · 标题`）")
                elif int(m.group(1)) != n:
                    rep.add("ERROR", where, f"标题篇号 {m.group(1)} 与文件名 {n} 不一致")
            dm = DATE_LINE_RE.search(text)
            if not dm:
                date_missing += 1
                rep.add("WARN", where, f"缺 `{K_DATE}：YYYY-MM-DD` 入口行")
            elif not ISO_DATE_RE.fullmatch(dm.group(1)):
                rep.add("WARN", where, f"日期格式不是 YYYY-MM-DD：{dm.group(1)}")
            if not VERIFY_HEAD_RE.search(text):
                verify_missing += 1
                rep.add("WARN", where, "缺「验证」小节（命令 + 结果 + 未覆盖）")
    if total:
        if date_missing:
            rep.add("INFO", jname, f"{date_missing}/{total} 篇缺日期行")
        if verify_missing:
            rep.add("INFO", jname, f"{verify_missing}/{total} 篇缺验证小节")

    if os.path.isfile(index):
        idx_text = read(index)
        _check_links(root, index, rep)
        for n in nums:
            if is_root_entry(journal, entries[n][0]) and os.path.basename(entries[n][0]) not in idx_text:
                rep.add("WARN", jname, f"记录 {os.path.basename(entries[n][0])} 未出现在索引中")
        blocks = re.findall(r"^#{2,3}\s*.*当前状态.*$", idx_text, re.M)
        if not blocks:
            rep.add("WARN", jname, f"索引缺 `## {K_STATUS}` 块")
        elif len(blocks) > 1:
            rep.add("ERROR", jname, f"索引有 {len(blocks)} 个「{K_STATUS}」块（只能有一个，旧块移入 archive/STATUS-HISTORY.md）")
        else:
            after = idx_text.split(blocks[0], 1)[1]
            nxt = re.search(r"^#{2,3}\s", after, re.M)
            block = blocks[0] + (after[: nxt.start()] if nxt else after)
            sd = max_date_in(block)
            newest = None
            for n in nums:
                d = max_date_in(read(entries[n][0]))
                if d and (newest is None or d > newest):
                    newest = d
            if not sd:
                rep.add("WARN", jname, f"「{K_STATUS}」块没有日期（标题写 `## {K_STATUS}（YYYY-MM-DD）`）")
            elif newest and sd < newest:
                rep.add("WARN", jname, f"「{K_STATUS}」({sd}) 早于最新记录 ({newest})，台账可能过期")
        if f"## {K_TODO}" not in idx_text:
            rep.add("INFO", jname, f"索引没有「{K_TODO}」小节（滚动清单建议保留）")

    for dp, dn, fn in os.walk(journal):
        dn[:] = [d for d in dn if d not in (".git", "node_modules")]
        for f in fn:
            if f.endswith(".md"):
                _check_links(root, os.path.join(dp, f), rep)

    lessons = resolve_dir(root, lessons_arg, ("lessons",))
    if lessons:
        lname = rel(root, lessons)
        if not os.path.isfile(os.path.join(lessons, "README.md")):
            rep.add("ERROR", lname, "缺经验手册索引 README.md")
        for dp, dn, fn in os.walk(lessons):
            dn[:] = [d for d in dn if d not in (".git", "node_modules")]
            for f in fn:
                if not f.endswith(".md") or f == "README.md":
                    continue
                path = os.path.join(dp, f)
                where = rel(root, path)
                _check_links(root, path, rep)
                text = read(path)
                if not re.search(r"^#\s", text, re.M):
                    rep.add("WARN", where, "缺一级标题")
                cites = CITE_RE.findall(text)
                if not cites and "来源" not in text:
                    rep.add("WARN", where, "既没有 `wl/NNNN` 来源引用，也没有「来源」说明")
                for c in cites:
                    if int(c) not in entries:
                        rep.add("WARN", where, f"来源 `wl/{c}` 在记录目录里不存在")
    return rep


# --------------------------------------------------------------------------- #
# lint：内容质量门禁
# --------------------------------------------------------------------------- #
def lint(root: str, journal_arg: str | None, strict: bool) -> Report:
    rep = Report(strict)
    journal = resolve_dir(root, journal_arg, ("journal", "work-log"))
    if not journal:
        rep.add("ERROR", root, "找不到记录目录")
        return rep
    for n, paths in sorted(find_entries(journal).items()):
        path = paths[0]
        where = rel(root, path)
        text = read(path)
        lines = text.splitlines()
        for token in PLACEHOLDERS:
            if token in text:
                rep.add("WARN", where, f"占位符未清理：`{token}`")
        cm = re.search(r"^结论\s*[：:]\s*(.*)$", text, re.M)
        if not cm or not cm.group(1).strip():
            rep.add("WARN", where, "「结论：」为空")
        elif not re.search(r"\d", cm.group(1)):
            rep.add("WARN", where, "结论没有数字（写成可核对的结果）")
        span = find_section(lines, 4, K_VERIFY) or find_section(lines, 2, K_VERIFY) or find_section(lines, 3, K_VERIFY)
        if span:
            body = "".join(lines[span[1]:span[2]]).strip()
            if len(body) < 10:
                rep.add("WARN", where, "验证小节为空")
            elif "`" not in body:
                rep.add("WARN", where, "验证小节没有命令（反引号包起来的可复现命令）")
            for w in VAGUE:
                if w in body:
                    rep.add("WARN", where, f"验证含含糊措辞：`{w}`")
        for i, line in enumerate(lines):
            h = heading_level(line)
            if not h or h[0] < 2:
                continue
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or heading_level(lines[j]):
                rep.add("WARN", where, f"空小节：`{h[1]}`")
    return rep


# --------------------------------------------------------------------------- #
# brief / outline / show / search
# --------------------------------------------------------------------------- #
def status_block_text(journal: str) -> str:
    index = os.path.join(journal, "README.md")
    lines = read_raw(index).splitlines(keepends=True)
    span = find_section(lines, 2, K_STATUS)
    return "".join(lines[span[0]:span[2]]).strip() if span else ""


def todo_items(journal: str) -> tuple[list[str], list[str]]:
    index = os.path.join(journal, "README.md")
    lines = read_raw(index).splitlines()
    span = find_section(lines, 2, K_TODO)
    open_items, done_items = [], []
    if span:
        for line in lines[span[1]:span[2]]:
            if re.match(r"^\s*-\s*\[ \]", line):
                open_items.append(line.strip())
            elif re.match(r"^\s*-\s*\[[xX]\]", line):
                done_items.append(line.strip())
    return open_items, done_items


def _clip(text: str, width: int) -> str:
    text = text.rstrip()
    return text if len(text) <= width else text[: width - 1] + "…"


def cmd_brief(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    if not journal:
        print("ERROR: 找不到记录目录")
        return 1
    entries = find_entries(journal)
    nums = sorted(entries)
    root_nums = [n for n in nums if is_root_entry(journal, entries[n][0])]
    print(f"# BRIEF  {rel(root, journal)}  ({len(nums)} entries #{nums[0] if nums else '-'}–#{nums[-1] if nums else '-'};"
          f" root {len(root_nums)} / archive {len(nums) - len(root_nums)})")
    sb = status_block_text(journal)
    if sb:
        lines = sb.splitlines()
        cap = args.max_status_lines
        print("")
        print("\n".join(_clip(l, args.width) for l in lines[:cap]))
        if len(lines) > cap:
            print(f"… (+{len(lines) - cap} lines, use `status --show`)")
    else:
        print(f"\n(!) 索引里没有状态块")
    open_items, _ = todo_items(journal)
    print(f"\n## {K_TODO}（未完成 {len(open_items)}）")
    for it in open_items[: args.max_todo]:
        print(_clip(it, args.width))
    if len(open_items) > args.max_todo:
        print(f"… (+{len(open_items) - args.max_todo} more, use `todo --list`)")
    print(f"\n## 近期记录（{args.entries}）")
    for n in sorted(nums, reverse=True)[: args.entries]:
        m = meta_of(entries[n][0])
        it = f"变更集 {m['iter']}" if m["iter"] and m["iter"] != "-" else "不占号"
        print(f"#{n:<4d} {m['date'] or '(无日期)':10s} [{it}] {'OK ' if m['has_verify'] else 'NO '} {m['title'][:52]}")
    return 0


def cmd_outline(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    if not journal:
        print("ERROR: 找不到记录目录")
        return 1
    entries = find_entries(journal)
    for n in sorted(entries):
        m = meta_of(entries[n][0])
        tag = m["iter"] if m["iter"] and m["iter"] != "-" else "-"
        print(f"{n:04d}\t{m['date'] or '-'}\t{tag}\t{m['lines']:4d}L\t{m['title'][:64]}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root_arg, num = _root_and_num(args.paths)
    root = os.path.abspath(root_arg)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    entries = find_entries(journal) if journal else {}
    if num not in entries:
        print(f"ERROR: 找不到记录 #{num}")
        return 1
    path = entries[num][0]
    m = meta_of(path)
    text = read(path)
    print(f"#{num:04d}  {rel(root, path)}")
    print(f"title : {m['title']}")
    print(f"date  : {m['date'] or '-'}   变更集: {m['iter'] or '-'}   {m['lines']} lines / {m['bytes']} B"
          f"   verify: {'yes' if m['has_verify'] else 'no'}")
    for key in ("触发", "范围", "结论"):
        mm = re.search(rf"^{key}\s*[：:]\s*(.+)$", text, re.M)
        if mm:
            print(f"{key:<6}: {mm.group(1).strip()[:100]}")
    print("sections:")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        h = heading_level(line)
        if h and h[0] >= 2:
            j = i + 1
            while j < len(lines) and not heading_level(lines[j]):
                j += 1
            print(f"  {h[1]}  ({j - i - 1} lines)")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    lessons = resolve_dir(root, args.lessons, ("lessons",))
    targets: list[str] = []
    if args.in_ in ("journal", "all") and journal:
        targets.append(journal)
    if args.in_ in ("lessons", "all") and lessons:
        targets.append(lessons)
    pat = re.compile(args.pattern, re.I) if args.regex else None
    needle = args.pattern.lower()
    hits = 0
    for base in targets:
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in (".git", "node_modules")]
            for f in sorted(fn):
                if not f.endswith(".md"):
                    continue
                path = os.path.join(dp, f)
                for i, line in enumerate(read(path).splitlines(), 1):
                    ok = bool(pat.search(line)) if pat else needle in line.lower()
                    if not ok:
                        continue
                    hits += 1
                    if hits > args.limit:
                        continue
                    if args.files:
                        print(rel(root, path))
                        break
                    print(f"{rel(root, path)}:{i}: {line.strip()[:160]}")
    tail = f"  (showing first {args.limit})" if hits > args.limit else ""
    print(f"\n{hits} hit(s){tail}")
    return 0 if hits else 1


# --------------------------------------------------------------------------- #
# new / index sync
# --------------------------------------------------------------------------- #
def _table_rows_span(lines: list[str], start: int, end: int):
    rows = [i for i in range(start, end) if lines[i].lstrip().startswith("|")]
    return (rows[0], rows[-1]) if rows else None


def index_sync(journal: str, only: list[int] | None = None, stage: str | None = None,
               aspect: str | None = None, dry_run: bool = False) -> tuple[list[int], str]:
    index = os.path.join(journal, "README.md")
    text = read_raw(index)
    lines = text.splitlines(keepends=True)
    nl = nl_of(text)
    entries = find_entries(journal)
    root_nums = [n for n in sorted(entries) if is_root_entry(journal, entries[n][0])]
    missing = [n for n in root_nums if os.path.basename(entries[n][0]) not in text]
    if only is not None:
        missing = [n for n in missing if n in only]
    if not missing:
        return [], "索引已覆盖全部根目录记录"

    idx_span = find_section(lines, 2, "文件索引")
    search_from = idx_span[1] if idx_span else 0
    search_to = idx_span[2] if idx_span else len(lines)
    subs = [(i, heading_level(lines[i])[1]) for i in range(search_from, search_to) if heading_level(lines[i]) and heading_level(lines[i])[0] == 3]
    if stage:
        chosen = next((s for s in subs if stage in s[1]), None)
    else:
        chosen = subs[-1] if subs else None
    if chosen is None:
        return [], "索引里找不到可写入的表格小节（先在 `## 文件索引` 下加 `### <阶段>` 与表头）"
    _, sub_title = chosen
    sub_end = next((i for i in range(chosen[0] + 1, len(lines))
                    if heading_level(lines[i]) and heading_level(lines[i])[0] <= 2), len(lines))
    span = _table_rows_span(lines, chosen[0] + 1, sub_end)
    new_lines = []
    for n in missing:
        m = meta_of(entries[n][0])
        fname = os.path.basename(entries[n][0])
        label = aspect or m["conclusion"] or m["title"]
        label = re.sub(r"\s+", " ", label).strip()[:60] or m["title"][:60]
        new_lines.append(f"| [{fname}]({fname}) | {label} |{nl}")
    if dry_run:
        return missing, f"[dry-run] 将写入 `{sub_title}` {len(missing)} 行：" + "; ".join(f"#{n}" for n in missing)
    if span:
        lines[span[1] + 1: span[1] + 1] = new_lines
    else:
        lines[chosen[0] + 1: chosen[0] + 1] = [f"| 文件 | 方面 |{nl}", f"|---|---|{nl}"] + new_lines + [nl]
    write_raw(index, "".join(lines))
    return missing, f"已写入 `{sub_title}`：{', '.join('#' + str(n) for n in missing)}"


def cmd_new(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    if not journal:
        print("ERROR: 找不到记录目录（journal/ 或 work-log/），先按 templates.md 初始化")
        return 1
    entries = find_entries(journal)
    num = (max(entries) + 1) if entries else 1
    date = args.date or today()
    slug = args.slug or slugify(args.title)
    fname = f"{num:04d}-{slug}.md"
    path = os.path.join(journal, fname)
    body = ENTRY_TEMPLATE.format(num=num, title=args.title, date=date,
                                 iter=args.iter if args.iter is not None else "-",
                                 cmd=args.cmd or "<验证命令>")
    if os.path.exists(path):
        print(f"ERROR: 已存在 {rel(root, path)}")
        return 1
    if args.dry_run:
        print(f"[dry-run] 将创建 {rel(root, path)}\n")
        print(body)
        return 0
    write_raw(path, body)
    print(f"created {rel(root, path)}")
    if args.insert:
        _, msg = index_sync(journal, only=[num], stage=args.stage, dry_run=False)
        print(f"index: {msg}")
    else:
        print("索引建议行：")
        print(f"| [{fname}]({fname}) | {args.title} |")
    if slug == "entry":
        print("提示：标题没有可用的 ASCII slug，建议用 --slug 指定。")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    if not journal:
        print("ERROR: 找不到记录目录")
        return 1
    missing, msg = index_sync(journal, stage=args.stage, aspect=args.aspect, dry_run=args.dry_run)
    print(msg)
    for n in missing:
        print(f"  #{n}")
    return 0


# --------------------------------------------------------------------------- #
# status / todo / append
# --------------------------------------------------------------------------- #
def _index_lines(journal: str) -> tuple[str, list[str]]:
    index = os.path.join(journal, "README.md")
    text = read_raw(index)
    return text, text.splitlines(keepends=True)


def cmd_status(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    if not journal:
        print("ERROR: 找不到记录目录")
        return 1
    text, lines = _index_lines(journal)
    span = find_section(lines, 2, K_STATUS)
    if not span:
        print(f"ERROR: 索引里没有 `## {K_STATUS}` 块")
        return 1

    if args.roll:
        head_line = lines[span[0]].rstrip("\r\n")
        hist = os.path.join(journal, "archive", "STATUS-HISTORY.md")
        block = "".join(lines[span[0]:span[2]]).strip()
        if args.dry_run:
            print(f"[dry-run] 将当前状态块移入 {rel(root, hist)}，并写入新骨架")
            print(block)
            return 0
        os.makedirs(os.path.dirname(hist), exist_ok=True)
        htext = read_raw(hist) if os.path.exists(hist) else ""
        if not htext:
            htext = f"# 状态历史{nl_of(text)}{nl_of(text)}"
        hl = htext.splitlines(keepends=True)
        h1 = next((i for i, l in enumerate(hl) if heading_level(l) and heading_level(l)[0] == 1), -1)
        insert_at = h1 + 1
        while insert_at < len(hl) and not hl[insert_at].strip():
            insert_at += 1
        hl[insert_at:insert_at] = [nl_of(htext), block + nl_of(htext), nl_of(htext)]
        write_raw(hist, "".join(hl))
        head = re.sub(r"（[^）]*）", "", head_line)
        head = head.rsplit("（", 1)[0] if "（" in head else head
        new_block = STATUS_SKELETON.format(head=head.lstrip("# ").strip(), date=args.date or today(),
                                           fields="\n".join(f"- {k}：" for k in STATUS_KEYS))
        lines[span[0]:span[2]] = new_block.splitlines(keepends=True) + [nl_of(text)]
        write_raw(os.path.join(journal, "README.md"), "".join(lines))
        print(f"已归档旧状态块 → {rel(root, hist)}，并写入新骨架")
        return 0

    if args.set or args.date:
        head_line = lines[span[0]]
        if args.date:
            if re.search(r"（[^）]*）", head_line):
                head_line = re.sub(r"（[^）]*）", f"（{args.date}）", head_line)
            else:
                head_line = head_line.rstrip("\r\n") + f"（{args.date}）" + (nl_of(text))
            lines[span[0]] = head_line
        changed = []
        for pair in args.set:
            if "=" not in pair:
                print(f"WARN: 忽略无法解析的 --set '{pair}'（应为 key=value）")
                continue
            key, val = pair.split("=", 1)
            key = key.strip()
            found = False
            for i in range(span[1], span[2]):
                m = re.match(r"^(\s*-\s*)([^：:\r\n]+)[：:][ \t]*(.*?)(\r?\n?)$", lines[i])
                if m and m.group(2).strip() == key:
                    lines[i] = f"{m.group(1)}{key}：{val}{m.group(4)}"
                    found = True
                    changed.append(key)
                    break
            if not found:
                end = last_content_line(lines, span[1], span[2]) + 1
                lines.insert(end, f"- {key}：{val}{nl_of(text)}")
                span = (span[0], span[1], span[2] + 1)
                changed.append(key + "(新增)")
        if args.dry_run:
            print("[dry-run] 将更新：" + ", ".join(changed))
            return 0
        write_raw(os.path.join(journal, "README.md"), "".join(lines))
        print("status 已更新：" + ", ".join(changed))
        return 0

    print("".join(lines[span[0]:span[2]]).strip())
    return 0


def cmd_todo(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    if not journal:
        print("ERROR: 找不到记录目录")
        return 1
    text, lines = _index_lines(journal)
    index = os.path.join(journal, "README.md")
    span = find_section(lines, 2, K_TODO)
    if not span:
        print(f"ERROR: 索引里没有 `## {K_TODO}` 小节")
        return 1
    nl = nl_of(text)

    if args.add:
        end = last_content_line(lines, span[1], span[2]) + 1
        if args.dry_run:
            print(f"[dry-run] 将追加：- [ ] {args.add}")
            return 0
        lines.insert(end, f"- [ ] {args.add}{nl}")
        write_raw(index, "".join(lines))
        print(f"已追加待办：{args.add}")
        return 0

    if args.done:
        for i in range(span[1], span[2]):
            if re.match(r"^\s*-\s*\[ \]", lines[i]) and args.done in lines[i]:
                lines[i] = re.sub(r"\[ \]", "[x]", lines[i], count=1)
                if args.dry_run:
                    print(f"[dry-run] 将勾选：{lines[i].strip()}")
                    return 0
                write_raw(index, "".join(lines))
                print(f"已勾选：{lines[i].strip()}")
                return 0
        print(f"ERROR: 找不到匹配的未完成待办：{args.done}")
        return 1

    if args.drop_done:
        kept = [l for i, l in enumerate(lines) if not (span[1] <= i < span[2] and re.match(r"^\s*-\s*\[[xX]\]", l))]
        removed = len(lines) - len(kept)
        if args.dry_run:
            print(f"[dry-run] 将删除 {removed} 条已完成待办")
            return 0
        write_raw(index, "".join(kept))
        print(f"已删除 {removed} 条已完成待办")
        return 0

    open_items, done_items = todo_items(journal)
    print(f"未完成（{len(open_items)}）")
    for it in open_items:
        print(it)
    print(f"\n已完成（{len(done_items)}）")
    for it in done_items:
        print(it)
    return 0


def cmd_append(args: argparse.Namespace) -> int:
    root_arg, num = _root_and_num(args.paths)
    root = os.path.abspath(root_arg)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    entries = find_entries(journal) if journal else {}
    if num not in entries:
        print(f"ERROR: 找不到记录 #{num}")
        return 1
    path = entries[num][0]
    text = read_raw(path)
    nl = nl_of(text)
    lines = text.splitlines(keepends=True)
    span = find_section(lines, 2, args.section)
    body = args.text.strip("\n").splitlines()
    if args.bullet:
        body = ["- " + b if not b.lstrip().startswith("-") else b for b in body]
    if span:
        add = [b + nl for b in body]
        insert_at_end_of_section(lines, span[1], span[2], [nl] + add)
        action = f"追加到已有小节 `{args.section}`"
    else:
        if lines and lines[-1].strip():
            lines.append(nl)
        lines.append(f"## {args.section}{nl}")
        lines.append(nl)
        lines.extend(b + nl for b in body)
        action = f"新建小节 `{args.section}`"
    if args.dry_run:
        print(f"[dry-run] {rel(root, path)}：{action}")
        print("".join(body))
        return 0
    write_raw(path, "".join(lines))
    print(f"{rel(root, path)}：{action}")
    return 0


# --------------------------------------------------------------------------- #
# lesson add
# --------------------------------------------------------------------------- #
def cmd_lesson(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    lessons = resolve_dir(root, args.lessons, ("lessons",))
    if not lessons:
        print("ERROR: 找不到 lessons/ 目录")
        return 1
    volumes = [f for f in sorted(os.listdir(lessons)) if f.endswith(".md") and f != "README.md"]
    if args.volume:
        match = [v for v in volumes if v == args.volume] or [v for v in volumes if args.volume in v]
        if not match:
            print(f"ERROR: 找不到分册 `{args.volume}`，可选：{', '.join(volumes)}")
            return 1
        if len(match) > 1:
            print(f"ERROR: 分册名不唯一：{', '.join(match)}")
            return 1
        volume = match[0]
    elif len(volumes) == 1:
        volume = volumes[0]
    else:
        print(f"ERROR: 用 --volume 指定分册，可选：{', '.join(volumes)}")
        return 1

    entries = find_entries(journal) if journal else {}
    if args.source is None:
        print("ERROR: 必须用 --source <篇号> 标注来源")
        return 1
    if args.source not in entries:
        print(f"ERROR: 来源 `wl/{args.source}` 在记录目录里不存在")
        return 1

    path = os.path.join(lessons, volume)
    text = read_raw(path)
    nl = nl_of(text)
    lines = text.splitlines(keepends=True)
    line = args.text.strip()
    if not line.startswith("-"):
        line = "- " + line
    if "wl/" not in line:
        line = line.rstrip("。.") + f"（`wl/{args.source:04d}`）"
    payload = line + nl
    if args.topic:
        span = find_section(lines, 2, args.topic)
        if span:
            insert_at_end_of_section(lines, span[1], span[2], [payload])
            action = f"追加到 `{args.topic}`"
        else:
            if lines and lines[-1].strip():
                lines.append(nl)
            lines += [f"## {args.topic}{nl}", nl, payload]
            action = f"新建小节 `{args.topic}`"
    else:
        if lines and lines[-1].strip():
            lines.append(nl)
        lines.append(payload)
        action = "追加到文件末尾"
    if args.dry_run:
        print(f"[dry-run] {rel(root, path)}：{action}\n{payload.strip()}")
        return 0
    write_raw(path, "".join(lines))
    print(f"{rel(root, path)}：{action}")
    print(payload.strip())
    return 0


# --------------------------------------------------------------------------- #
# stats / topics / export / digest / retro
# --------------------------------------------------------------------------- #
def cmd_stats(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    lessons = resolve_dir(root, args.lessons, ("lessons",))
    entries = find_entries(journal) if journal else {}
    nums = sorted(entries)
    if not nums:
        print("没有记录")
        return 0
    metas = all_metas(entries)
    root_nums = [n for n in nums if is_root_entry(journal, entries[n][0])]
    dates = [max_date_in(read(entries[n][0])) for n in nums]
    dates = [d for d in dates if d]
    total_bytes = sum(m["bytes"] for m in metas.values())
    total_lines = sum(m["lines"] for m in metas.values())
    biggest = max(nums, key=lambda n: metas[n]["bytes"])
    print(f"entries     : {len(nums)}  (#{nums[0]}–#{nums[-1]}; root {len(root_nums)} / archive {len(nums) - len(root_nums)})")
    if dates:
        span_days = (max(dates) - min(dates)).days + 1
        print(f"date span   : {min(dates)} .. {max(dates)}  ({span_days} days, {len(dates)} dated)")
        buckets: dict[str, int] = {}
        for d in dates:
            wk = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
            buckets[wk] = buckets.get(wk, 0) + 1
        print("per week    : " + "  ".join(f"{k}:{v}" for k, v in sorted(buckets.items())))
    print(f"compliance  : 日期 {sum(1 for m in metas.values() if m['has_date'])}/{len(nums)}"
          f"   验证 {sum(1 for m in metas.values() if m['has_verify'])}/{len(nums)}")
    print(f"size        : {total_lines} lines / {total_bytes / 1024:.0f} KB"
          f"   avg {total_lines // len(nums)} lines   largest #{biggest} ({metas[biggest]['bytes'] / 1024:.0f} KB)")
    iters = [m["iter"] for m in metas.values() if m["iter"] and m["iter"] != "-"]
    print(f"变更集字段  : {len(iters)}/{len(nums)} 有值")
    if lessons:
        cites: dict[int, int] = {}
        for f in sorted(os.listdir(lessons)):
            if f.endswith(".md") and f != "README.md":
                for c in CITE_RE.findall(read(os.path.join(lessons, f))):
                    cites[int(c)] = cites.get(int(c), 0) + 1
        print(f"lessons     : {len([f for f in os.listdir(lessons) if f.endswith('.md') and f != 'README.md'])} volumes,"
              f" {sum(cites.values())} citations → {len(cites)} sources")
        top = sorted(cites.items(), key=lambda kv: -kv[1])[:8]
        print("top cited   : " + "  ".join(f"#{n}({c})" for n, c in top))
    return 0


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.\-]{3,}")


def cmd_topics(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    entries = find_entries(journal) if journal else {}
    nums = sorted(entries)
    if args.keywords:
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        for kw in kws:
            hit = [n for n in nums if kw.lower() in read(entries[n][0]).lower()]
            print(f"{kw}: " + (", ".join(f"#{n}" for n in hit) if hit else "(no hit)"))
        return 0
    df: dict[str, set[int]] = {}
    for n in nums:
        for tok in set(TOKEN_RE.findall(read(entries[n][0]))):
            t = tok.lower()
            if t in STOPWORDS or len(t) < 4:
                continue
            df.setdefault(t, set()).add(n)
    cand = [(t, ns) for t, ns in df.items() if 2 <= len(ns) <= args.max_df]
    cand.sort(key=lambda kv: (-len(kv[1]), kv[0]))
    print(f"同主题簇建议（出现 2–{args.max_df} 篇的标识符；用 `--keywords` 可查中文词）\n")
    for t, ns in cand[: args.limit]:
        shown = sorted(ns)
        print(f"{t:28s} {len(shown):2d} 篇  " + ", ".join(f"#{n}" for n in shown[:10])
              + (" …" if len(shown) > 10 else ""))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    entries = find_entries(journal) if journal else {}
    rows = []
    for n in sorted(entries):
        m = meta_of(entries[n][0])
        rows.append({"num": n, "path": rel(root, entries[n][0]), **{k: m[k] for k in
                     ("title", "date", "iter", "lines", "bytes", "has_date", "has_verify")}})
    if args.csv:
        import csv
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else ["num"])
        w.writeheader()
        w.writerows(rows)
        out = buf.getvalue()
    else:
        out = json.dumps(rows, ensure_ascii=False, indent=2)
    if args.out:
        write_raw(os.path.abspath(args.out), out + ("" if out.endswith("\n") else "\n"))
        print(f"wrote {args.out} ({len(rows)} rows)")
    else:
        print(out)
    return 0


def cmd_digest(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    lessons = resolve_dir(root, args.lessons, ("lessons",))
    entries = find_entries(journal) if journal else {}
    nums = sorted(entries)
    lines = [f"# 交接摘要（生成于 {today()}）", ""]
    sb = status_block_text(journal) if journal else ""
    lines += ["## " + K_STATUS, "", sb or "(索引里没有状态块)", ""]
    open_items, _ = todo_items(journal) if journal else ([], [])
    lines += ["## " + K_TODO, ""] + (open_items or ["(无未完成项)"]) + [""]
    lines += [f"## 近期记录（最近 {args.entries} 篇）", "", "| 篇号 | 日期 | 变更集 | 标题 |", "|---|---|---|---|"]
    for n in sorted(nums, reverse=True)[: args.entries]:
        m = meta_of(entries[n][0])
        lines.append(f"| {n:04d} | {m['date'] or '-'} | {m['iter'] or '-'} | {m['title']} |")
    lines.append("")
    if lessons:
        lines += ["## 经验要点", ""]
        for f in sorted(os.listdir(lessons)):
            if not f.endswith(".md") or f == "README.md":
                continue
            text = read(os.path.join(lessons, f))
            h1 = H1_RE.search(text)
            bullets = [l.strip() for l in text.splitlines() if l.strip().startswith("- ")][: args.per_volume]
            lines += [f"### {h1.group(1).strip() if h1 else f}", ""] + bullets + [""]
    out = "\n".join(lines).rstrip() + "\n"
    if args.out:
        write_raw(os.path.abspath(args.out), out)
        print(f"wrote {args.out} ({len(out)} B)")
    else:
        print(out)
    return 0


def cmd_retro(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    journal = resolve_dir(root, args.journal, ("journal", "work-log"))
    entries = find_entries(journal) if journal else {}
    nums = [n for n in sorted(entries) if args.from_num <= n <= args.to_num]
    if not nums:
        print("ERROR: 区间内没有记录")
        return 1
    stage = args.stage or "阶段"
    lessons = resolve_dir(root, args.lessons, ("lessons",))

    def link_for(path: str) -> str:
        base = lessons if lessons else journal
        return os.path.relpath(path, base).replace(os.sep, "/")

    out = [f"# 99 · 阶段复盘", "", f"## 一、阶段表（{stage}）", "",
           "| 变更集 | 日期 | 记录 | 产出 |", "|---|---|---|---|"]
    for n in nums:
        m = meta_of(entries[n][0])
        out.append(f"| {m['iter'] or '-'} | {m['date'] or '-'} | [wl/{n:04d}]({link_for(entries[n][0])}) | {m['title']} |")
    out += ["", "## 二、核心成果", "", "## 三、最有价值的可复用发现", ""]
    out += ["## 四、遗留事项", ""]
    leaves = 0
    for n in nums:
        text = read(entries[n][0])
        for line in text.splitlines():
            if re.match(r"^\s*-\s*\[ \]", line):
                out.append(f"- {line.strip()[5:].strip()}（`wl/{n:04d}`）")
                leaves += 1
    if not leaves:
        out.append("- （区间内记录没有未完成项）")
    out.append("")
    body = "\n".join(out)
    if args.out:
        write_raw(os.path.abspath(args.out), body)
        print(f"wrote {args.out} ({len(nums)} entries, {leaves} open items)")
    else:
        print(body)
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--journal", default=None, help="记录目录名，默认 journal/，回退 work-log/")
    p.add_argument("--lessons", default=None, help="经验目录名，默认 lessons/")


def _add_root(p: argparse.ArgumentParser) -> None:
    p.add_argument("root", nargs="?", default=".", help="项目根，默认当前目录")


def _root_and_num(paths: list[str]) -> tuple[str, int]:
    """支持 `show 42` 与 `show <root> 42` 两种写法。"""
    if len(paths) == 1:
        root, num = ".", paths[0]
    elif len(paths) == 2:
        root, num = paths[0], paths[1]
    else:
        raise SystemExit("用法：[ROOT] NUM（例如 `show 42` 或 `show ./proj 42`）")
    try:
        return root, int(num)
    except ValueError:
        raise SystemExit(f"NUM 必须是篇号（整数），收到：{num!r}")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="journal.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="项目长期工作记录工具箱：少读（brief/show/search）、少写（status/todo/index/append/lesson）、可校验（check/lint）。",
        epilog="约定见 skill 的 references/conventions.md；完整命令说明见 references/commands.md。",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name: str, func, help_text: str, root: bool = True):
        p = sub.add_parser(name, help=help_text)
        _add_common(p)
        if root:
            _add_root(p)
        p.set_defaults(func=func)
        return p

    p = add("new", cmd_new, "生成下一篇记录")
    p.add_argument("--title", required=True)
    p.add_argument("--iter", type=int, default=None, help="变更集号（默认 -）")
    p.add_argument("--slug", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--cmd", default=None, help="预填验证命令")
    p.add_argument("--insert", action="store_true", help="自动补进索引表")
    p.add_argument("--stage", default=None, help="配合 --insert 指定阶段小节")
    p.add_argument("--dry-run", action="store_true")

    p = add("check", lambda a: _run(Report(a.strict), lambda: check(os.path.abspath(a.root), a.journal, a.lessons, a.strict), a), "结构门禁")
    p.add_argument("--strict", action="store_true", help="把 WARN 当 ERROR")
    p.add_argument("--quiet", action="store_true")

    p = add("lint", lambda a: _run(Report(a.strict), lambda: lint(os.path.abspath(a.root), a.journal, a.strict), a), "内容质量门禁")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--quiet", action="store_true")

    p = add("brief", cmd_brief, "压缩上下文快照")
    p.add_argument("--entries", type=int, default=8, help="近期记录条数（默认 8）")
    p.add_argument("--max-status-lines", type=int, default=30)
    p.add_argument("--max-todo", type=int, default=10)
    p.add_argument("--width", type=int, default=200, help="每行截断宽度（默认 200 字符）")

    p = add("outline", cmd_outline, "全部记录一行表")

    p = add("show", cmd_show, "单篇记录大纲", root=False)
    p.add_argument("paths", nargs="+", metavar="[ROOT] NUM")

    p = add("search", cmd_search, "定向检索")
    p.add_argument("pattern")
    p.add_argument("--in", dest="in_", choices=["journal", "lessons", "all"], default="all")
    p.add_argument("--regex", action="store_true")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--files", action="store_true", help="只列命中文件")

    p = add("stats", cmd_stats, "语料统计")
    p = add("topics", cmd_topics, "同主题簇建议")
    p.add_argument("--keywords", default=None, help="逗号分隔的中文/任意关键词")
    p.add_argument("--limit", type=int, default=15)
    p.add_argument("--max-df", type=int, default=12, help="最多出现在多少篇里（默认 12）")

    p = add("export", cmd_export, "机器可读导出")
    p.add_argument("--json", action="store_true", help="JSON（默认）")
    p.add_argument("--csv", action="store_true")
    p.add_argument("--out", default=None)

    p = add("digest", cmd_digest, "生成交接摘要")
    p.add_argument("--entries", type=int, default=12)
    p.add_argument("--per-volume", type=int, default=3)
    p.add_argument("--out", default=None)

    p = add("retro", cmd_retro, "阶段复盘骨架")
    p.add_argument("--from", dest="from_num", type=int, required=True)
    p.add_argument("--to", dest="to_num", type=int, required=True)
    p.add_argument("--stage", default=None)
    p.add_argument("--out", default=None)

    p = add("status", cmd_status, "当前状态块")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--date", default=None, nargs="?", const="today")
    p.add_argument("--roll", action="store_true", help="旧块归档到 archive/STATUS-HISTORY.md 并写新骨架")
    p.add_argument("--dry-run", action="store_true")

    p = add("todo", cmd_todo, "待办清单")
    p.add_argument("--add", default=None)
    p.add_argument("--done", default=None, help="按子串勾选第一条匹配的未完成项")
    p.add_argument("--drop-done", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    p_index = sub.add_parser("index", help="索引维护")
    _add_common(p_index)
    _add_root(p_index)
    isub = p_index.add_subparsers(dest="index_cmd", required=True)
    p_sync = isub.add_parser("sync", help="把漏掉的记录补进索引表")
    _add_common(p_sync)
    p_sync.add_argument("--stage", default=None)
    p_sync.add_argument("--aspect", default=None)
    p_sync.add_argument("--dry-run", action="store_true")
    p_sync.set_defaults(func=cmd_index)

    p_lesson = sub.add_parser("lesson", help="经验层维护")
    _add_common(p_lesson)
    _add_root(p_lesson)
    lsub = p_lesson.add_subparsers(dest="lesson_cmd", required=True)
    p_ladd = lsub.add_parser("add", help="追加一条带来源的经验")
    _add_common(p_ladd)
    p_ladd.add_argument("--volume", default=None)
    p_ladd.add_argument("--topic", default=None)
    p_ladd.add_argument("--source", type=int, required=True, help="篇号（wl/NNNN）")
    p_ladd.add_argument("--text", required=True)
    p_ladd.add_argument("--dry-run", action="store_true")
    p_ladd.set_defaults(func=cmd_lesson)

    p = add("append", cmd_append, "向记录追加小节", root=False)
    p.add_argument("paths", nargs="+", metavar="[ROOT] NUM")
    p.add_argument("--section", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--bullet", action="store_true", help="每行自动加 `- ` 前缀")
    p.add_argument("--dry-run", action="store_true")

    return ap


def _run(rep: Report, fn, args: argparse.Namespace) -> int:
    rep = fn()
    rep.print(getattr(args, "quiet", False))
    return 1 if rep.errors() else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "date", None) == "today":
        args.date = today()
    result = args.func(args)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
