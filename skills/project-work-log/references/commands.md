# 命令说明（`scripts/journal.py`）

全部命令：`python scripts/journal.py <命令> [参数]`。
`ROOT` 可省略，默认当前目录；`--journal`（默认 `journal/`，回退 `work-log/`）与 `--lessons`（默认 `lessons/`）用于非标准目录名。
**只读命令**不修改任何文件；**写入命令**都支持 `--dry-run`，做外科式行级编辑（保留 CRLF 与其余字节）。

```bash
python scripts/journal.py --help          # 命令总览
python scripts/_selftest.py               # 自测：临时工程跑通全部命令（34 项）
```

## 一、少读：把上下文留给真正要看的内容

| 命令 | 作用 | 典型用法 |
|---|---|---|
| `brief` | **压缩上下文快照**：当前状态（每行截断）+ 未完成待办 + 最近 N 篇。替代整读 50 KB 索引 | `brief --entries 8 --max-status-lines 30 --width 200` |
| `show` | **单篇大纲**：元数据 + 触发/范围/结论 + 各小节行数，先看这个再决定要不要读全文 | `show 42` / `show ./proj 42` |
| `search` | **定向检索**：记录 + 经验里按子串/正则只回命中行 | `search "端口冲突"` / `search --regex "E10\d\d" --in journal` |
| `outline` | 全部记录一行表（编号/日期/变更集/行数/标题），可 `grep` 可排序 | `outline` |

> 用法建议：接手任务先 `brief`；知道大概在哪篇用 `search`；定位到单篇用 `show`；确实需要细节再 `read` 那一个文件。

## 二、少写：外科式维护台账（都支持 `--dry-run`）

| 命令 | 作用 | 典型用法 |
|---|---|---|
| `new` | 生成下一篇记录，可选自动进索引 | `new --title "…" --iter 154 --insert --stage "A. 起步"` |
| `status` | 当前状态块：查看 / 改字段 / 改日期 / 归档旧块 | `status --set "测试=312 PASS" --date` / `status --roll` |
| `todo` | 滚动待办：加 / 勾选 / 清理已完成 | `todo --add "…"` / `todo --done "PR #15"` / `todo --drop-done` |
| `index sync` | 把漏进索引的根目录记录补成表行（方面取自「结论：」） | `index sync --stage "B. 迭代"` |
| `lesson add` | 往经验分册追加一条并**校验来源存在** | `lesson add --volume 03-dsh-contracts.md --source 53 --topic profile --text "…"` |
| `append` | 给某篇追加小节（更正 / 遗留更新） | `append 42 --section 更正 --text "…" --bullet` |

约定要点：
- `status` 永远只维护**唯一**一个 `## 当前状态` 块；`--roll` 会把旧块整段搬进 `journal/archive/STATUS-HISTORY.md` 再写新骨架。
- `lesson add` 的 `--source` 必须指向真实存在的篇号，否则拒绝写入（防止无主结论）。
- `append` 若目标小节已存在则追加到该小节末尾，不会重复建标题。

## 三、可校验：两道门禁

| 命令 | 检查内容 | 退出码 |
|---|---|---|
| `check` | 结构：编号重复/断档、标题篇号一致、`日期：` 行、验证小节、md 死链、漏索引、状态块唯一且新鲜、lessons 来源可回指 | 有 ERROR → 1 |
| `lint` | 内容：占位符残留（`<验证命令>`/`TODO`…）、空小节、结论没数字、验证没命令、含糊措辞（"应该没问题"） | 有 ERROR → 1 |

`--strict` 把 WARN 当 ERROR（新项目/CI 建议开）；`--quiet` 不打印 INFO。
旧仓库首次跑会有大量 WARN（缺日期行等）——那正是待回填清单，不是工具坏了。

## 四、分析与生成：不止于记账

| 命令 | 作用 | 典型用法 |
|---|---|---|
| `stats` | 语料统计：总量、日期跨度、每周节奏、日期/验证合规率、体积、变更集字段覆盖、经验引用覆盖与 top cited | `stats` |
| `topics` | **同主题簇建议**：自动找"出现在 2–N 篇"的标识符；中文用 `--keywords` 指定 | `topics --limit 15` / `topics --keywords "会话格式,契约哨兵"` |
| `digest` | **生成交接摘要文档**：状态 + 待办 + 近期记录表 + 经验要点，`--out` 落盘可直接给新会话/新同事 | `digest --entries 12 --out HANDOFF.md` |
| `retro` | **阶段复盘骨架**：给篇号区间，自动生成阶段表 + 汇总区间内未完成项，用于 `lessons/99-retrospectives.md` | `retro --from 100 --to 151 --stage "第三阶段" --out retro.md` |
| `export` | 机器可读导出（JSON / CSV），供其它脚本消费 | `export --csv --out journal.csv` |

`topics` 的自动模式只认 ASCII 标识符（文件名、接口名、旗标、错误码），中文主题请用 `--keywords`——这是无依赖环境下的取舍，已在输出里说明。

## 五、组合套路（省上下文的标准动作）

```bash
# 1. 接手：一屏拿到坐标
python scripts/journal.py brief

# 2. 找旧结论：先检索，再只看那一篇的大纲
python scripts/journal.py search "会话格式" --in journal
python scripts/journal.py show 51

# 3. 收尾一篇：补索引 → 更新状态 → 抽经验 → 过门禁
python scripts/journal.py new --title "…" --iter 154 --insert --stage "新阶段"
python scripts/journal.py status --set "变更集=154" --set "测试=380 PASS" --date
python scripts/journal.py lesson add --volume 04-verification-and-safety.md --source 152 --text "…"
python scripts/journal.py check --strict && python scripts/journal.py lint --strict

# 4. 阶段结束：归档 + 复盘骨架
python scripts/journal.py retro --from 100 --to 151 --out lessons/99-retrospectives.md
python scripts/journal.py digest --out HANDOFF.md
```

## 六、内部脚本

| 文件 | 用途 |
|---|---|
| `_selftest.py` | 自测全部命令（临时目录，含 CRLF 保真与"只改目标行"断言） |
| `_measure.py` | 对现成 `work-log/`+`lessons/` 做一次性测量，`references/analysis.md` 的数字由它复现 |
