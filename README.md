<div align="center">

# 代码考古学家
### Code Archaeologist

**给它一个 git 仓库，它还你一段历史。**

*不只告诉你改了什么——而是推断出当年为什么要这么写。*

---

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-4D6BFE?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)
![Status](https://img.shields.io/badge/Status-MVP-f59e0b?style=flat-square)

</div>

---

## 它解决什么问题

你是否接手过这样的代码：

- 没有文档，没有注释，原作者早已离职
- 某个函数写得莫名其妙，却没人敢动
- 一个文件被改了几百次，但没人知道它的"前世今生"

**代码考古学家**把 git 历史当作侦探线索，结合 LLM 推断能力，替你还原出：

> *"这段绕弯子的代码，是 2019 年为了兼容某个已经下线的数据库 Bug 临时加的——后来没人记得删。"*

---

## 报告包含什么

| 章节 | 考古内容 |
|------|---------|
| **项目生命周期** | 自动划分时代（创业期 / 扩张 / 危机 / 成熟），还原每个阶段的业务压力 |
| **模块历史卡片** | 每个热点文件的生命故事：为什么诞生、经历了什么危机、现在的状态 |
| **关键事件解读** | 深夜救火、大规模回滚、紧急 hotfix 背后到底发生了什么 |
| **技术债地图** | TODO/FIXME 是谁留下的、为什么不敢动、哪些是定时炸弹 |
| **知识孤岛风险** | 谁掌握哪些模块的知识、离职后会形成什么空白 |

---

## 快速开始

**第一步：安装依赖**

```bash
git clone https://github.com/gaohan984526940/code-archaeology-agent.git
cd code-archaeology-agent
pip install -r requirements.txt
```

**第二步：配置 API Key**

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 DeepSeek API Key：

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

> 没有 Key？[免费申请](https://platform.deepseek.com/api_keys) — 新账户有免费额度，够跑几十次分析。

**第三步：开挖**

```bash
python archaeologist.py /path/to/your/repo
```

2~3 分钟后，报告生成在当前目录：`archaeology_report_{仓库名}_{时间戳}.md`

---

## 命令行参数

```bash
python archaeologist.py [OPTIONS] REPO_PATH

# 指定输出目录
python archaeologist.py ~/code/myproject --output ./reports

# 只分析最近 500 条提交（加快速度）
python archaeologist.py ~/code/myproject --depth 500
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `REPO_PATH` | 本地 git 仓库路径 | 必填 |
| `-o / --output` | 报告输出目录 | 当前目录 |
| `-d / --depth` | 分析最近 N 条提交 | 2000 |

---

## 真实案例：Flask 官方仓库

对 Flask（500 commits，2023-2026）运行分析，考古学家自动推断出：

**项目阶段划分**

```
Phase 1 · The Steady State (2023)         175 commits
          成熟框架的园丁期，团队在精心维护依赖生态

Phase 2 · The Long March to 3.1 (2024)   172 commits
          历时数月的大版本准备，secret key rotation、trusted hosts...

Phase 3 · The AI-Assisted Acceleration   90 commits
          一次 +1876 行的 uv 迁移，工具链现代化提速

Phase 4 · The Slow Fade or The Plateau   63 commits
          提交量下降，但每一次都是架构级的深水区操作
```

**深夜事件还原（真实案例）**

```
时间：2026-02-19  凌晨 03:56
作者：David Lord
标志：深夜提交 + emergency 关键词 + 连续 3 次提交（间隔 < 10 分钟）

推断：teardown 回调在异常时被静默跳过，生产环境出现资源泄漏
过程：通宵定位 → 修复 → 当夜发布 3.1.3 热补丁
规模：+194 / -80 行，触及核心请求处理逻辑
```

**知识孤岛警告**

```
David Lord：396 / 500 提交（79%）
Top 3 贡献者合计：88% 提交

结论：极高单点依赖风险。David Lord 掌握几乎所有核心模块知识。
```

---

## 工作原理

```
本地 git 仓库
      |
      v
git_extractor.py        提取提交时序、热点文件、异常提交识别、技术债扫描
      |
      v
analyzer.py             4 个并行 LLM 推断任务（DeepSeek API）
      |
      +-- 任务 1：整体业务演进时间线
      +-- 任务 2：核心模块历史卡片（Top 热点文件）
      +-- 任务 3：异常提交事件还原
      +-- 任务 4：技术债 + 知识孤岛分析
      |
      v
report_generator.py     拼装结构化 Markdown 报告
      |
      v
archaeology_report_*.md
```

**异常提交识别规则**

- 深夜提交（22:00 — 06:00）
- 单次变更超过 500 行
- 含高危关键词：`revert` / `hotfix` / `emergency` / `critical` / `hack`
- 10 分钟内连续多次提交

---

## 项目结构

```
code-archaeology-agent/
├── archaeologist.py       CLI 入口
├── git_extractor.py       git 数据采集层
├── analyzer.py            LLM 推断层（DeepSeek API）
├── report_generator.py    Markdown 报告生成
├── requirements.txt
└── .env.example
```

---

## 路线图

- [x] MVP：git 历史分析 + LLM 推断 + Markdown 报告
- [ ] 关联 GitHub Issue / PR 讨论，补全历史语境
- [ ] HTML 可视化报告（交互式时间轴）
- [ ] 支持 Ollama 本地模型（完全离线，无需 API Key）
- [ ] 增量分析（只处理新增提交，持续更新报告）

---

## License

MIT — 随意使用，欢迎 PR。
