# 代码考古学家 / Code Archaeologist

> 给它一个 git 仓库，它还你一段历史。

把遗留代码库的 git 历史当作"时间胶囊"来解读——不只告诉你改了什么，而是推断出**为什么当年要这么写**。

---

## 它能做什么

输入一个本地 git 仓库路径，输出一份 Markdown 考古报告，包含：

| 报告章节 | 内容 |
|----------|------|
| 项目生命周期 | 自动划分阶段（创业期 / 扩张 / 危机 / 成熟），还原业务背景 |
| 模块历史卡片 | Top 热点文件的生命故事：为什么诞生、经历了什么危机 |
| 关键事件解读 | 深夜救火、大规模回滚、紧急 hotfix 背后发生了什么 |
| 技术债地图 | TODO/FIXME 是谁留下的、为什么不敢动 |
| 知识孤岛风险 | 谁掌握哪些模块、离职了会怎样 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key
# 申请地址：https://platform.deepseek.com/api_keys（新账户有免费额度）
```

### 3. 运行分析

```bash
python archaeologist.py /path/to/your/repo
```

报告会生成在当前目录，文件名格式：`archaeology_report_{仓库名}_{时间戳}.md`

---

## 命令行参数

```
python archaeologist.py [OPTIONS] REPO_PATH

参数:
  REPO_PATH             本地 git 仓库路径（必填）

选项:
  -o, --output TEXT     报告输出目录（默认：当前目录）
  -d, --depth INTEGER   分析最近 N 条提交（默认：2000）
  --help                显示帮助
```

**示例：**

```bash
# 分析 Flask 源码，报告输出到 ./reports/
python archaeologist.py ~/code/flask --output ./reports

# 只看最近 500 条提交
python archaeologist.py ~/code/myproject --depth 500
```

---

## 实际效果

以下是对 Flask 官方仓库（500 commits）的分析摘录：

**自动识别的项目阶段：**
```
Phase 1: The Steady State (2023)      — 175 commits，成熟框架的园丁期
Phase 2: The Long March to 3.1 (2024) — 172 commits，历时数月的大版本准备
Phase 3: The AI-Assisted Acceleration  — 迁移到 uv，单次 +1876 行
Phase 4: The Slow Fade or The Plateau  — 提交量降但质量升
```

**深夜事件还原（真实案例）：**
```
2026-02-19 凌晨 03:56
作者：David Lord
触发原因：teardown 回调在异常时被静默跳过 → 生产环境资源泄漏
处理过程：通宵定位 + 修复 + 当夜发布 3.1.3 热补丁
影响范围：+194/-80 行，触及核心请求处理逻辑
```

---

## 工作原理

```
本地 git 仓库
      │
      ▼
 git_extractor.py          ← 提取提交时序、热点文件、异常提交、技术债标记
      │
      ▼
   analyzer.py             ← 4 个 LLM 推断任务（DeepSeek API）
  ┌───┴────────────────────────────────┐
  │  任务1：整体业务演进时间线          │
  │  任务2：核心模块历史卡片            │
  │  任务3：异常提交事件还原            │
  │  任务4：技术债 + 知识孤岛分析       │
  └────────────────────────────────────┘
      │
      ▼
report_generator.py        ← 生成结构化 Markdown 报告
      │
      ▼
archaeology_report_*.md    ← 输出
```

**异常提交识别规则：**
- 深夜提交（22:00 - 06:00）
- 单次变更超过 500 行
- 含关键词：`revert` / `hotfix` / `emergency` / `critical` / `hack`
- 10 分钟内连续多次提交

---

## 项目结构

```
代码考古学家/
├── archaeologist.py       # CLI 入口
├── git_extractor.py       # git 数据采集
├── analyzer.py            # LLM 推断（DeepSeek API）
├── report_generator.py    # Markdown 报告生成
├── requirements.txt       # Python 依赖
└── .env.example           # 环境变量模板
```

---

## 依赖

| 包 | 用途 |
|----|------|
| `gitpython` | 读取 git 历史，无需系统 git 命令 |
| `openai` | 调用 DeepSeek API（OpenAI 兼容格式） |
| `python-dotenv` | 加载 `.env` 配置 |
| `click` | CLI 参数解析 |

---

## 路线图

- [x] MVP：git 历史分析 + LLM 推断 + Markdown 报告
- [ ] GitHub Issue/PR 关联分析
- [ ] HTML 可视化报告（时间轴图表）
- [ ] 支持 Ollama 本地模型（无需 API Key）
- [ ] 增量分析（只分析新增提交）

---

## License

MIT
