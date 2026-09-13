# 如何发布到 GitHub

本仓库是**独立仓库**（工作区本身不是 git 仓库），可直接 `git init` 后推送；也可先推到私有仓库验证再转公开。

## 0. 发之前先确认三件事

| 项 | 说明 |
|---|---|
| **许可证** | `LICENSE` 现为 MIT，但版权人还是占位符 `<YOUR NAME OR GITHUB HANDLE>`——**必须改**（改成你的名字或 GitHub 用户名）。若不想用 MIT，换掉整个文件即可。 |
| **仓库名 / OWNER** | 下文用 `<OWNER>`、`project-work-log` 占位，按需替换。 |
| **`package.json` 的 `name`** | 现在是 `pi-project-work-log`。**如果只通过 git 安装，名字无所谓**；若要 `npm publish`，先去 npm 查是否重名。 |

## 1. 本地初始化并首次提交

```bash
cd <工作区>/publish/worklog

git init -b main
git add .
git status                 # 确认没有 __pycache__ / *.pyc 混进来
git commit -m "feat: project-work-log skill (journal + lessons + toolbox)"
```

## 2. 在 GitHub 建仓

**方式 A · 网页**（无需额外工具）

1. 打开 <https://github.com/new>
2. 填仓库名 `project-work-log`，选 Public / Private
3. **不要**勾选 "Add a README / .gitignore / license"（本地已有，避免冲突）
4. Create repository

**方式 B · GitHub CLI**（本机当前**未安装 `gh`**，需先装）

```bash
gh auth login
gh repo create worklog --public --source=. --remote=origin --push
```

## 3. 推送

```bash
git remote add origin https://github.com/<OWNER>/worklog.git
git branch -M main
git push -u origin main
```

## 4. 打 tag（推荐）

pi 安装时可以固定到 tag/commit，用户就不会被上游改动影响：

```bash
git tag -a v0.1.0 -m "project-work-log v0.1.0"
git push origin v0.1.0
```

之后别人可以这样装：

```bash
pi install git:github.com/<OWNER>/worklog@v0.1.0
```

## 5. 以后怎么更新

**skill 的唯一源是工作区的 `.pi/skills/project-work-log/`**，本仓库里的 `skills/project-work-log/` 是同步出来的副本。
改完 skill 后：

```bash
# 1) 同步（会打印新增/修改/删除）
python <工作区>/.pi/skills/project-work-log/scripts/_package.py

# 2) 只检查有没有漂移（有漂移退出码 1，可当提交前门禁）
python <工作区>/.pi/skills/project-work-log/scripts/_package.py --check

# 3) 提交并推送
cd <工作区>/publish/worklog
git add -A && git commit -m "chore: sync skill from source" && git push
git tag -a v0.1.1 -m "v0.1.1" && git push origin v0.1.1   # 有行为变化时
```

> 不要在 `publish/` 里直接改脚本——下次同步会被覆盖。改源，再同步。

## 6. 发布前自检（建议写进检查清单）

```bash
cd <工作区>/publish/worklog

# 包内路径下也能跑通（验证相对路径没有写死）
python skills/project-work-log/scripts/_selftest.py        # 期望 34/34 passed

# 源与包没有漂移
python ../../.pi/skills/project-work-log/scripts/_package.py --check

# 没有把缓存/临时文件带进仓库
git status --porcelain
```

## 7. 别人怎么装（写进 README 的三条路）

```bash
pi install git:github.com/<OWNER>/worklog          # pi 用户
cp -r skills/project-work-log ~/.pi/agent/skills/           # 手动
# 其它 harness：把 skills/ 加入它的技能搜索路径（Agent Skills 标准布局）
```

加上 `package.json` 里的 `pi-package` 关键词后，包会被 pi 的软件包画廊 <https://pi.dev/packages> 收录（若公开）。

## 8. 可选：发布到 npm

只有需要 `pi install npm:...` 或独立版本管理时才做：

```bash
npm login
npm publish --access public     # 名字重复就改 package.json 的 name 或加 scope
```
