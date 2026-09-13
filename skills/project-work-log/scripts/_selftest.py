#!/usr/bin/env python3
"""_selftest.py — journal.py 的自测（内部工具，不参与日常使用）。

在临时目录里搭一个最小项目，跑通全部子命令并断言行为，最后删除临时目录。
    python scripts/_selftest.py        # 全过退出码 0
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "journal.py")

INDEX = """# P 工作记录

## 文件索引

### A. 起步

| 文件 | 方面 |
|---|---|
| [0001-seed.md](0001-seed.md) | 起步 |

## 待办（滚动清单）

- [ ] keep me

## 当前状态（2026-09-13）

- 分支 / HEAD：main
- 变更集：-
- 构建：
- 测试：
- 交付物与指纹：
- 环境：
- 阻塞 / 等待：
"""

SEED = """# 0001 · Seed entry

日期：2026-09-13
变更集：1
触发：selftest
范围：none
结论：0 改动

---

## 一、背景与事实核查

seed

## 二、验证

- 命令：`true`
- 结果：0
- 未覆盖：none
"""

LESSONS_INDEX = """# 经验手册

| 分册 | 内容 |
|---|---|
| [01-topic.md](01-topic.md) | x |
"""

VOLUME = """# 01 · Seed topic

来源：wl/0001。

## 子主题

- **seed**：a。根因：b。做法：c。（`wl/0001`）
"""

results: list[tuple[bool, str]] = []


def run(root: str, *argv: str) -> subprocess.CompletedProcess:
    # 项目根默认取 cwd；journal/ 与 lessons/ 名字走默认解析
    return subprocess.run([sys.executable, TOOL, *argv],
                          cwd=root, capture_output=True, text=True, encoding="utf-8")


def ok(cond: bool, label: str, detail: str = "") -> None:
    results.append((bool(cond), label))
    print(("PASS  " if cond else "FAIL  ") + label + (f"   [{detail[:200]}]" if detail and not cond else ""))


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="journal-selftest-")
    try:
        os.makedirs(os.path.join(tmp, "journal", "archive"))
        os.makedirs(os.path.join(tmp, "lessons"))
        write(os.path.join(tmp, "journal", "README.md"), INDEX)
        write(os.path.join(tmp, "journal", "0001-seed.md"), SEED)
        write(os.path.join(tmp, "lessons", "README.md"), LESSONS_INDEX)
        write(os.path.join(tmp, "lessons", "01-topic.md"), VOLUME)

        # new --insert -----------------------------------------------------
        r = run(tmp, "new", "--title", "Add login rate limit", "--iter", "12",
                "--date", "2026-09-14", "--insert", "--stage", "A. 起步")
        ok(r.returncode == 0, "new --insert exits 0", r.stderr)
        entry = os.path.join(tmp, "journal", "0002-add-login-rate-limit.md")
        ok(os.path.exists(entry), "new --insert created 0002 file")
        idx = read(os.path.join(tmp, "journal", "README.md"))
        ok("0002-add-login-rate-limit.md" in idx, "index row auto-inserted")

        # index sync idempotent -------------------------------------------
        r = run(tmp, "index", "sync")
        ok(r.returncode == 0 and "已覆盖" in r.stdout, "index sync idempotent", r.stdout + r.stderr)

        # brief / outline / show / search ---------------------------------
        r = run(tmp, "brief", "--entries", "2", "--width", "120")
        ok(r.returncode == 0 and "BRIEF" in r.stdout and "Add login rate limit" in r.stdout,
           "brief shows recent entry", r.stdout)
        ok(len(r.stdout) < 2000, "brief stays compact", f"{len(r.stdout)} chars")
        r = run(tmp, "outline")
        ok(r.returncode == 0 and "0002" in r.stdout and "Add login rate limit" in r.stdout, "outline runs", r.stdout)
        ok(r.stdout.count("\t") >= 4, "outline has 5 columns")
        r = run(tmp, "show", "2")
        ok("Add login rate limit" in r.stdout and "sections:" in r.stdout, "show prints outline", r.stdout)
        r = run(tmp, "search", "rate limit")
        ok(r.returncode == 0 and "0002" in r.stdout, "search finds entry", r.stdout)

        # status -----------------------------------------------------------
        r = run(tmp, "status", "--set", "分支 / HEAD=main @ abc123", "--set", "测试=312 PASS", "--date", "2026-09-14")
        ok(r.returncode == 0, "status --set exits 0", r.stderr)
        idx = read(os.path.join(tmp, "journal", "README.md"))
        ok("分支 / HEAD：main @ abc123" in idx and "测试：312 PASS" in idx, "status values updated")
        ok("## 当前状态（2026-09-14）" in idx, "status date updated")
        ok(idx.count("## 当前状态") == 1, "still exactly one status block")
        r = run(tmp, "status")
        ok("main @ abc123" in r.stdout, "status --show prints block")

        # todo -------------------------------------------------------------
        run(tmp, "todo", "--add", "ship the thing")
        r = run(tmp, "todo", "--done", "ship the thing")
        ok(r.returncode == 0, "todo --done exits 0", r.stdout + r.stderr)
        idx = read(os.path.join(tmp, "journal", "README.md"))
        ok("- [x] ship the thing" in idx, "todo marked done")
        r = run(tmp, "todo", "--drop-done")
        ok("- [x] ship the thing" not in read(os.path.join(tmp, "journal", "README.md")), "todo --drop-done works")

        # append -----------------------------------------------------------
        r = run(tmp, "append", "2", "--section", "更正", "--text", "2026-09-14: changed mind", "--bullet")
        ok(r.returncode == 0 and "## 更正" in read(entry), "append creates section", r.stderr)
        r = run(tmp, "append", "2", "--section", "更正", "--text", "second note", "--bullet")
        ok(read(entry).count("## 更正") == 1 and "- second note" in read(entry),
           "append reuses existing section", r.stderr)

        # lesson add -------------------------------------------------------
        r = run(tmp, "lesson", "add", "--volume", "01-topic.md", "--source", "2",
                "--topic", "子主题", "--text", "**429 storm**：x。根因：y。做法：z")
        ok(r.returncode == 0 and "wl/0002" in read(os.path.join(tmp, "lessons", "01-topic.md")),
           "lesson add appends with citation", r.stderr)
        r = run(tmp, "lesson", "add", "--volume", "01-topic.md", "--source", "999", "--text", "bad")
        ok(r.returncode != 0, "lesson add rejects unknown source", r.stdout)

        # analysis / generation -------------------------------------------
        for argv, needle in ((("stats",), "compliance"), (("digest",), "交接摘要"),
                             (("topics", "--keywords", "seed"), "seed:"),
                             (("retro", "--from", "1", "--to", "2"), "阶段复盘"),
                             (("export",), '"num"')):
            r = run(tmp, *argv)
            ok(r.returncode == 0 and needle in r.stdout, f"{argv[0]} runs", r.stdout + r.stderr)

        # lint: placeholder present, then cleaned -------------------------
        r = run(tmp, "lint")
        ok("<验证命令>" in r.stdout or "占位符" in r.stdout, "lint flags template placeholder", r.stdout)
        text = read(entry)
        text = text.replace("- 命令：`<验证命令>`", "- 命令：`pytest -q`").replace("- 结果：", "- 结果：312 passed").replace(
            "结论：", "结论：312 项测试全绿")
        text = text.replace("## 一、背景与事实核查\n\n## 二、方案与取舍",
                            "## 一、背景与事实核查\n\nneed\n\n## 二、方案与取舍\n\nchoice")
        write(entry, text)
        r = run(tmp, "lint", "--strict")
        ok(r.returncode == 0, "lint clean after filling entry", r.stdout + r.stderr)

        # check ------------------------------------------------------------
        r = run(tmp, "check", "--strict", "--quiet")
        ok(r.returncode == 0, "check --strict clean", r.stdout + r.stderr)

        # CRLF fidelity ----------------------------------------------------
        index_path = os.path.join(tmp, "journal", "README.md")
        before = read(index_path).replace("\n", "\r\n")
        write(index_path, before)
        snapshot = read_bytes(index_path)
        r = run(tmp, "status", "--set", "测试=999 PASS")
        after = read_bytes(index_path)
        ok(r.returncode == 0, "status --set on CRLF file exits 0", r.stderr)
        ok(b"\r\n" in after, "CRLF preserved")
        ok(after.replace(b"\r\n", b"").count(b"\n") == 0, "no lone LF introduced")
        changed = [i for i, (a, b) in enumerate(zip(snapshot.split(b"\r\n"), after.split(b"\r\n"))) if a != b]
        ok(len(changed) == 1 and b"999 PASS" in after.split(b"\r\n")[changed[0]],
           "only the target line changed", f"changed lines={changed}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [label for good, label in results if not good]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


def read(path: str) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def read_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


if __name__ == "__main__":
    sys.exit(main())
