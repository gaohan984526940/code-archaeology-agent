"""Markdown report generation from analysis results."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from git_extractor import RepoData
from analyzer import AnalysisResult


def generate_report(data: RepoData, result: AnalysisResult, output_dir: str = ".") -> str:
    report_name = f"archaeology_report_{data.repo_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    output_path = Path(output_dir) / report_name

    content = _build_report(data, result)
    output_path.write_text(content, encoding="utf-8")

    return str(output_path)


def _build_report(data: RepoData, result: AnalysisResult) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    start = data.date_range[0].strftime("%Y-%m-%d")
    end = data.date_range[1].strftime("%Y-%m-%d")

    sections = [
        _header(data, now, start, end),
        _stats_summary(data),
        _section("项目生命周期 / Business Evolution", result.business_evolution),
        _section("模块历史卡片 / Module History Cards", result.module_stories),
        _section("关键事件解读 / Anomaly Interpretations", result.anomaly_interpretations),
        _section("技术债地图 / Technical Debt Map", result.tech_debt_analysis),
        _contributors_section(data),
        _hotspots_section(data),
        _footer(data),
    ]

    return "\n\n".join(sections)


def _header(data: RepoData, now: str, start: str, end: str) -> str:
    return f"""# {data.repo_name} — 代码考古报告

> **生成时间**: {now}
> **分析工具**: 代码考古学家 (Code Archaeologist)
> **仓库路径**: `{data.repo_path}`
> **历史跨度**: {start} → {end}
> **总提交数**: {data.total_commits:,}

---"""


def _stats_summary(data: RepoData) -> str:
    active = sum(1 for c in data.contributors if not c.is_likely_inactive)
    inactive = len(data.contributors) - active

    yearly_rows = "\n".join(
        f"| {year} | {count:,} | {'█' * min(count // 10, 50)} |"
        for year, count in data.yearly_commit_counts.items()
    )

    return f"""## 执行摘要 / Executive Summary

| 指标 | 数值 |
|------|------|
| 总提交数 | {data.total_commits:,} |
| 贡献者总数 | {len(data.contributors)} |
| 活跃贡献者 | {active} |
| 疑似离职贡献者 | {inactive} |
| 异常提交数 | {len(data.anomalies)} ({len(data.anomalies)/max(data.total_commits,1)*100:.1f}%) |
| 技术债标记 | {len(data.tech_debt_items)} |
| 热点文件 (Top 20) | {len(data.hotspots)} |

### 年度提交活跃度

| 年份 | 提交数 | 活跃度 |
|------|--------|--------|
{yearly_rows}"""


def _section(title: str, content: str) -> str:
    return f"""## {title}

{content}

---"""


def _contributors_section(data: RepoData) -> str:
    rows = []
    for c in data.contributors[:15]:
        first = c.first_commit.strftime("%Y-%m") if c.first_commit else "—"
        last = c.last_commit.strftime("%Y-%m") if c.last_commit else "—"
        status = "⚠️ 疑似离职" if c.is_likely_inactive else "✓ 活跃"
        modules = ", ".join(c.primary_modules[:2]) or "—"
        rows.append(f"| {c.name} | {c.commit_count:,} | {first} | {last} | {status} | {modules} |")

    table = "\n".join(rows)
    return f"""## 主要贡献者与知识传承

| 贡献者 | 提交数 | 首次提交 | 最后提交 | 状态 | 主要模块 |
|--------|--------|----------|----------|------|----------|
{table}

---"""


def _hotspots_section(data: RepoData) -> str:
    rows = []
    for h in data.hotspots[:15]:
        first = h.first_seen.strftime("%Y-%m") if h.first_seen else "—"
        last = h.last_seen.strftime("%Y-%m") if h.last_seen else "—"
        authors = ", ".join(h.top_authors[:2]) or "—"
        age_bar = "🔥" * min(h.change_count // 5, 10)
        rows.append(f"| `{h.path}` | {h.change_count} | {first} | {last} | {authors} | {age_bar} |")

    table = "\n".join(rows)
    return f"""## 代码热点地图 / Hotspot Map

> 变更次数越多 = 越核心 OR 越不稳定

| 文件路径 | 变更次数 | 创建时间 | 最后更新 | 主要作者 | 热度 |
|----------|----------|----------|----------|----------|------|
{table}

---"""


def _footer(data: RepoData) -> str:
    anomaly_pct = len(data.anomalies) / max(data.total_commits, 1) * 100
    if anomaly_pct > 20:
        health = "🔴 高风险 — 异常提交率偏高，历史危机频发"
    elif anomaly_pct > 10:
        health = "🟡 中等 — 有一定历史包袱，需要重点关注异常区域"
    else:
        health = "🟢 良好 — 提交历史相对健康"

    return f"""## 考古结论 / Archaeological Conclusion

**仓库健康度**: {health}

**关键数据**:
- 异常提交率: {anomaly_pct:.1f}%
- 技术债密度: {len(data.tech_debt_items)} 个标记
- 知识集中度: Top 3 贡献者占 {_top3_percentage(data):.0f}% 提交

---

*本报告由代码考古学家自动生成，所有推断基于 git 历史分析。
部分结论为 LLM 基于模式识别的推断，请结合实际业务背景判断。*"""


def _top3_percentage(data: RepoData) -> float:
    if not data.contributors or data.total_commits == 0:
        return 0.0
    top3 = sum(c.commit_count for c in data.contributors[:3])
    return top3 / data.total_commits * 100
