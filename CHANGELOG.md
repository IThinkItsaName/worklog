# 更新日志

本文件记录 **worklog**（技能名 `project-work-log`）的版本变化。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

> **规矩**：只追加，不改写历史条目。发版时把 `## [未发布]` 下的内容整理成 `## [x.y.z] - YYYY-MM-DD`，
> 顶部再留一个空的 `## [未发布]`；tag 一旦推送就**不要移动**（别人可能已经钉着它安装）。

## [未发布]

### 新增

- **跨语言解析**：解析标签集中为常量并支持**英文别名**（写入仍默认中文）：
  `日期/Date`、`结论/Conclusion`、`触发/Trigger`、`范围/Scope`、`迭代/Iteration`、
  `验证/Verification`、`当前状态/Status`、`待办/TODO`、`文件索引/Index`——英文项目现在也能用 `check`/`lint`/`brief`
- SKILL.md 新增「**没有 Python 怎么办**（降级路径）」：把 Python 从硬依赖降为可选加速器
- README 新增「**支持矩阵**」：诚实标注验证范围（Python 3.12/3.14 实测、跨平台、UTF-8、双语解析）
- `_measure.py` 参数化：`[ROOT] [--journal NAME] [--lessons NAME]`（默认自动识别 `journal/` 或 `work-log/`）

### 变更

- 自测 53 → **57** 项（新增 4 项英文标签用例）
- `references/analysis.md` 的“验证小节”统计随词表放宽重测：88 → **95** / 106

## [0.1.0] - 2026-09-13

首次发布。

### 新增

- **三层记录体系**：`journal/`（过程记录）+ `journal/README.md`（索引台账）+ `lessons/`（经验手册）
- **工具箱 `journal.py`**：20 个子命令，纯 Python 标准库、零依赖、零配置
  - 少读：`brief` / `show` / `search` / `outline`
  - 少写：`new --insert` / `status` / `todo` / `index sync` / `lesson add` / `append`
  - 可校验：`check`（结构门禁）/ `lint`（内容质量门禁）
  - 分析生成：`stats` / `topics` / `digest` / `retro` / `export`
  - 整理清理：`archive` / `index compact` / `split` / `prune`
- **领域无关（不限于编程）**：迭代字段接受 `迭代 / 变更集 / 批次 / 阶段 / 版本 / 里程碑`；
  验证小节接受 `验证 / 复核 / 检查 / 评审 / 结果 / 证据 / 评估 / 确认`；
  "可核对的内容"包括命令 / 数据 / 引用 / 样本
- **整理能力只搬不删**：`archive` 移文件 + 重写全仓链接 + 死链自检；`index compact` 把已归档小节折叠成一行；
  `split --by-year` 按年分卷；`prune` 默认只报告，打包后才移出并留清单
- **自测** `scripts/_selftest.py`：53 项，覆盖 CRLF 保真、"只改目标行"、非编程场景与整理能力
- **文档**：`SKILL.md` + `references/`（`conventions` / `templates` / `commands` / `analysis`）
- **CI**：push / PR 触发，跑 53 项自测 + `SKILL.md` frontmatter + `package.json` 校验

### 说明

- 硬规则（目录与编号约定、"证据不删"、生命周期）见 `references/conventions.md`
- 设计依据（对一套真实长期项目记录的实测分析与改进对照）见 `references/analysis.md`
- 本技能整理自作者使用 **DeepSeek Flash 系列模型**处理内容时的常用操作，并**完全由该系列模型整理生成**；
  使用时请自行甄别，**不保证效果与适用性**

[未发布]: https://github.com/IThinkItsaName/worklog/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/IThinkItsaName/worklog/tree/v0.1.0
