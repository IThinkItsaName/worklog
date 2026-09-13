# project-work-log

> 给长期项目用的**工作记录体系**（Agent Skill）：过程记录 + 索引台账 + 经验手册，外加一套 13 个子命令的管理 / 分析工具箱。

适用于支持 [Agent Skills](https://agentskills.io/specification) 的编码代理（pi、Claude Code 等）。

## 它解决什么问题

长期项目里，真正难的不是写代码，而是三件事：

1. **下次接手时找不到上下文**——"当时为什么这么改？验证过没有？"
2. **经验留不下来**——踩过的坑换个人（或换一次会话）再踩一遍。
3. **台账会漂移**——状态、待办、索引越写越乱，最后没人信。

这套 skill 把它固化成**三层结构 + 一套约定 + 可机器校验的门禁**：

| 层 | 位置 | 职责 |
|---|---|---|
| 过程层 | `journal/NNNN-*.md` | 一篇 = 一个变更集：背景 → 事实 → 方案 → 实施 → 验证 → 遗留 |
| 索引层 | `journal/README.md` | 分阶段索引 + 同主题簇 + 滚动待办 + **唯一**当前状态块 |
| 经验层 | `lessons/*.md` | 可复用知识：症状 → 根因 → 做法 → 来源 |

配套脚本让代理**少读、少写、可校验**：不用整读几十 KB 的索引，改台账是外科式行级编辑（保留 CRLF），
结构问题（死链、断档、漏索引、来源悬空）和内容问题（占位符没清、结论没数字、"应该没问题"）都能自动查出来。

## 安装

### pi

```bash
# 全局
pi install git:github.com/<OWNER>/project-work-log

# 固定到 tag（推荐，避免上游变动）
pi install git:github.com/<OWNER>/project-work-log@v0.1.0

# 只装到当前项目（写入 .pi/settings.json，可随仓库共享给团队）
pi install -l git:github.com/<OWNER>/project-work-log
```

### 手动（任意 harness）

```bash
# 全局
cp -r skills/project-work-log ~/.pi/agent/skills/

# 项目级（项目受信任后生效）
mkdir -p <project>/.pi/skills && cp -r skills/project-work-log <project>/.pi/skills/
```

Claude Code 等其它 harness：把本仓库的 `skills/` 目录加入它的 skill 搜索路径即可（目录结构遵循 Agent Skills 标准）。

## 用法

代理在匹配到「开始新任务要留记录」「建工作日志」「总结踩坑/经验」「整理台账/当前状态」「阶段性复盘」「归档旧记录」
这类意图时会自动加载本 skill；也可以显式触发：

```
/skill:project-work-log
```

脚本可以独立使用（只依赖 Python 标准库）：

```bash
cd <你的项目根>   # 目录里应有 journal/ 与 lessons/（SKILL.md 的「工作流 A」会教你建）

# 一屏掌握当前坐标（替代整读索引）
python <skill>/scripts/journal.py brief

# 生成下一篇记录并自动补索引行
python <skill>/scripts/journal.py new --title "给登录加限流" --iter 42 --insert --stage "B. 迭代"

# 收尾：更新状态 → 抽经验 → 过门禁
python <skill>/scripts/journal.py status --set "测试=380 PASS" --date
python <skill>/scripts/journal.py lesson add --volume 04-verification-and-safety.md --source 42 --text "…"
python <skill>/scripts/journal.py check --strict && python <skill>/scripts/journal.py lint --strict
```

## 目录结构

```
.
├── README.md
├── LICENSE
├── package.json                 # pi 包声明（keywords: pi-package）
└── skills/
    └── project-work-log/
        ├── SKILL.md             # 技能入口：三层模型、铁律、工作流、反模式
        ├── references/
        │   ├── conventions.md   # 目录 / 编号 / 生命周期 / 台账 / 经验层的硬约定
        │   ├── templates.md     # 记录、台账、归档、经验分册、复盘 全套模板
        │   ├── commands.md      # 13 个子命令的完整说明与组合套路
        │   └── analysis.md      # 设计依据：对真实 151 篇记录的实测分析与改进对照
        └── scripts/
            ├── journal.py       # 工具箱（唯一入口，纯标准库）
            ├── _selftest.py     # 自测：临时工程跑通全部命令 + CRLF 保真
            └── _measure.py      # 对现成记录目录做一次性测量（analysis.md 的数字可复现）
```

## 命令一览

| 分类 | 命令 |
|---|---|
| 少读 | `brief`（压缩快照）、`show`（单篇大纲）、`search`（定向检索）、`outline`（全部一行表） |
| 少写 | `new --insert`、`status`、`todo`、`index sync`、`lesson add`、`append`（均支持 `--dry-run`） |
| 门禁 | `check`（结构）、`lint`（内容质量）——有 ERROR 时退出码 1 |
| 分析生成 | `stats`（语料统计）、`topics`（同主题簇建议）、`digest`（交接摘要）、`retro`（复盘骨架）、`export`（JSON/CSV） |

完整参数与套路见 [`skills/project-work-log/references/commands.md`](skills/project-work-log/references/commands.md)。

## 环境要求

- **Python**（仅标准库，无第三方依赖；开发与自测环境为 3.14）
- 脚本会读写 Markdown 文件；建议把 `journal/`、`lessons/` 纳入版本控制

## 自测

```bash
python skills/project-work-log/scripts/_selftest.py
```

会在临时目录里搭一个最小项目，跑通全部命令，并断言：CRLF 保真、**只改目标行**、来源校验会拒绝不存在的篇号等。

## 设计依据

不是凭空设计的约定，而是对一个真实项目 **151 篇记录 / 5 个经验分册**做实测后总结的：
哪些做法有效（编号即地址、三层不互相复制、证据优先）、哪些会腐坏（台账漂移、格式漂移、双份数字）。
详见 [`references/analysis.md`](skills/project-work-log/references/analysis.md)。

## 许可

MIT，见 [LICENSE](LICENSE)。
