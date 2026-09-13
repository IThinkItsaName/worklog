---
name: project-work-log
description: 为项目建立并维护长期工作记录体系（过程记录 journal/ + 索引台账 + lessons/ 经验手册）。当用户要「开始新任务并留下记录」「建工作日志 / 工作记录 / 开发日志」「总结项目经验 / 踩坑 / 教训」「整理台账 / 当前状态 / 待办」「阶段性复盘」「归档旧记录」时使用；也用于在每次改动收尾时按固定模板落一篇记录、抽取经验并更新状态。适用于任何需要跨会话、跨周持续开发的项目。
---

# 项目长期工作记录（project-work-log）

## 这是什么

把"项目里发生过什么、怎么验证的、留下了什么可复用经验"沉淀成**三层、可检索、可校验**的文档体系：

| 层 | 位置 | 职责 | 生命周期 |
|---|---|---|---|
| **过程层** | `journal/NNNN-*.md` | 一篇 = 一个变更集：背景 → 事实 → 方案 → 实施 → 验证 → 遗留 | append-only，收口后不改写 |
| **索引层** | `journal/README.md` | 分阶段索引 + 同主题簇 + 滚动待办 + **唯一**当前状态块 | 每次收尾更新 |
| **经验层** | `lessons/*.md` | 提炼后的可复用知识：症状 → 根因 → 做法 → 来源 | 持续追加，每条必须有来源 |

一句话：**过程留证据，索引管导航，经验可复用**。三层不互相复制内容。

本工作区的 `work-log/` + `lessons/` 就是这套体系的实例；基线分析（哪些沿用、哪些坑要避开）见
[references/analysis.md](references/analysis.md)。

## 何时用

- 用户说"开始一个新任务"——先确认/建立这套结构，再开工。
- 一个改动完成后要"收尾/留记录/更新台账"。
- 要"总结经验/整理踩坑/做复盘/归档旧东西"。
- 接手一个已有 `journal/`、`work-log/`、`lessons/`、`docs/` 记录体系的项目，要按既有约定续写。

## 铁律（先看这 8 条）

1. **先记录、后动手**（方案类）：先写清"要解决什么 + 选项 + 建议默认值"，用户确认后再实施；有疑问先记录，不擅自改。
2. **一篇一个变更集**。一次会话做了 3 个变更集 → 3 篇 + 1 篇收尾；纯调研/一次性记录在 `变更集:` 写 `-`。
3. **篇号与变更集号分开**：篇号是文件名/标题/回指用的地址（`wl/NNNN`），变更集号只写在 `变更集:` 字段。
4. **历史不改写**：收口后不抹旧结论；被推翻时**追加** `## 更正`（日期 / 原结论 / 新证据 / 现结论）。
5. **验证必须有命令与结果**，没验的必须写明"未覆盖 + 原因"。只有编译通过不算验证。
6. **经验必有来源**：lessons 每条带 `（wl/NNNN）`，来源不存在就不许写。
7. **台账只有一个 `## 当前状态`**，字段固定（见下）；换新块时旧块整段剪到 `journal/archive/STATUS-HISTORY.md`。
8. **编号永不复用，归档不改号**；归档只 move + 改链接。

完整约定见 [references/conventions.md](references/conventions.md)；模板见 [references/templates.md](references/templates.md)。

## 工作流 A · 初始化（项目第一次用）

1. 先查已有体系：`ls` 项目根，找 `journal/` `work-log/` `lessons/` `docs/` 以及根 `README.md` / `CLAUDE.md` / `AGENTS.md` 里的记录约定。
   **已有体系就沿用它的命名与编号，不新建平行目录。**
2. 没有则按 `references/templates.md` 落盘：
   - `journal/README.md`（台账模板）
   - `lessons/README.md` + `lessons/01-<topic>.md`（先建 3–5 个与本项目相关的分册）
   - `journal/archive/README.md`、`journal/archive/STATUS-HISTORY.md`
   - 在项目根 `README.md` 加一行指向 `journal/README.md`
3. 跑一次 `journal.py check` 确认骨架自洽（此时 0 篇记录也应通过）。

## 工作流 B · 一次改动（日常）

```
记录 → 确认 → 实施 → 验证 → 收尾
```

1. **记录**：`python scripts/journal.py new <项目根> --title "标题" [--iter N]` 生成下一篇；把入口 5 行（日期/变更集/触发/范围/结论）先填上。
2. **确认**：方案、口径、取舍写进记录；等用户拍板（涉及数据/破坏性操作必须确认）。
3. **实施**：小步改、每步可回退；改动面记进「实施」表。
4. **验证**：跑项目的测试/构建/harness，把**命令 + 结果 + 未覆盖**写进 `## 验证`。
5. **收尾**：见工作流 C。

## 工作流 C · 收尾清单（每篇记录都走一遍）

1. 记录补齐：`日期/变更集/触发/范围/结论` + `## 验证` + `## 遗留与下一步`。
2. 台账：索引表加一行；涉及跨篇主题就更新「同主题簇」；滚动待办增删。
3. 状态：更新 `## 当前状态` 的字段（分支/HEAD、变更集、构建、测试、交付物指纹、环境、阻塞）。
4. 经验：本轮若有可复用结论，写进 `lessons/` 对应分册并回填 `（wl/NNNN）`。
5. 校验：`python scripts/journal.py check <项目根>` 必须 **0 error**（新项目/CI 加 `--strict`，warning 逐条判断）。
6. 提交：代码与文档一起提交；提交信息引用篇号（如 `journal: 0042 ...`）。

## 工作流 D · 归档与复盘

- **归档判据 = 阶段收口**（某个阶段结束、索引表不再增长），不再用"多少天没引用"这类经验值。
- 归档：整阶段 move 到 `journal/archive/<stage>/` → 改索引链接 → 写归档索引 → 跑 `check` 确认 0 死链。
- 复盘：写进 `lessons/99-retrospectives.md`（阶段表 / 成果 / 可复用发现 / 遗留），**不要**另建 SUMMARY 文档到处写同一批数字。

## 工具（`scripts/journal.py`，纯标准库）

**核心用法：少读、少写、可校验。** 完整命令说明见 [references/commands.md](references/commands.md)。

```bash
ROOT  # 可省略，默认当前目录

# —— 少读：别整读 50 KB 索引 ——
python scripts/journal.py brief                 # 一屏：当前状态 + 待办 + 近期记录
python scripts/journal.py show 42               # 单篇大纲（先看它再决定读不读全文）
python scripts/journal.py search "会话格式"      # 定向检索（记录+经验，只回命中行）
python scripts/journal.py outline               # 全部记录一行表

# —— 少写：外科式编辑，支持 --dry-run，保留 CRLF ——
python scripts/journal.py new --title "…" --iter 154 --insert --stage "A. 起步"
python scripts/journal.py status --set "测试=380 PASS" --date      # 改状态块（--roll 归档旧块）
python scripts/journal.py todo --add "…" | --done "子串" | --drop-done
python scripts/journal.py index sync --stage "B. 迭代"            # 补漏掉的索引行
python scripts/journal.py lesson add --volume 04-verification-and-safety.md --source 152 --text "…"
python scripts/journal.py append 42 --section 更正 --text "…" --bullet

# —— 可校验：两道门禁（有 ERROR 退出码 1）——
python scripts/journal.py check --strict        # 结构：编号/日期/验证/死链/漏索引/状态/来源
python scripts/journal.py lint --strict         # 内容：占位符/空小节/结论无数字/含糊措辞

# —— 分析与生成 ——
python scripts/journal.py stats                 # 语料统计（节奏/合规率/引用覆盖）
python scripts/journal.py topics --limit 15     # 同主题簇建议（中文用 --keywords）
python scripts/journal.py digest --out HANDOFF.md          # 交接摘要
python scripts/journal.py retro --from 100 --to 151 --out r.md  # 阶段复盘骨架
python scripts/journal.py export --csv --out journal.csv   # 机器可读导出
```

自测：`python scripts/_selftest.py`（临时工程跑通全部命令 + CRLF 保真，34 项）。

> 典型接手动作：`brief` → `search` → `show` → 需要细节才 `read` 那一个文件。
> 典型收尾动作：`new --insert` → 补正文 → `status` → `lesson add` → `check --strict` && `lint --strict`。

## 反模式（本工作区实测踩过的，别再来）

| 反模式 | 后果 | 正确做法 |
|---|---|---|
| 台账靠人肉同步、长期不更 | "当前状态"过期，看板不可信（`work-log/46` P2-7） | 收尾必更状态块，并用 `check` 判新鲜度 |
| 当前状态 + 一堆历史状态堆在索引 | 索引膨胀、改一处分多处 | 只有一块当前状态，旧块进 STATUS-HISTORY |
| 有的记录写日期、有的不写 | 无法机器校验、审计困难（基线 41/106） | `日期：` 必填，由 `check` 判 error |
| 篇号当变更集号引用 | 引用歧义 | 只在 `变更集:` 字段写变更集号，回指一律 `wl/NNNN` |
| README 与 SUMMARY 各写一份数字 | 改一处漏一处 | 复盘并入 `lessons/99-retrospectives.md`，数字只留一份 |
| lessons 写结论不带来源 | 追不回证据、无法证伪 | 每条带 `（wl/NNNN）`，`check` 校验来源存在 |
| 直接抹掉被推翻的旧结论 | 丢失演进与纠错价值 | 追加 `## 更正` 段 |
| 一次性调研随手建新目录 | 编号体系分裂 | 沿用既有 `journal/`，不占号就写 `变更集: -` |

## 参考文件

- [references/analysis.md](references/analysis.md) · 基线 `work-log/`+`lessons/` 的实测分析与改进对照
- [references/conventions.md](references/conventions.md) · 目录/编号/生命周期/台账/经验层的硬约定
- [references/commands.md](references/commands.md) · `journal.py` 全部命令与组合套路
- [references/templates.md](references/templates.md) · 记录、台账、归档、经验分册、复盘 全套模板
