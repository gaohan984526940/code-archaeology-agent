"""LLM archaeology inference layer — DeepSeek API (OpenAI-compatible)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

from git_extractor import RepoData, CommitInfo


MODEL = "deepseek-chat"
MAX_TOKENS = 4096


@dataclass
class AnalysisResult:
    business_evolution: str
    module_stories: str
    anomaly_interpretations: str
    tech_debt_analysis: str


def analyze_repo(data: RepoData) -> AnalysisResult:
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )

    print("  [1/4] Analyzing business evolution timeline...")
    business_evolution = _analyze_business_evolution(client, data)

    print("  [2/4] Analyzing core module histories...")
    module_stories = _analyze_module_stories(client, data)

    print("  [3/4] Interpreting anomalous commits...")
    anomaly_interpretations = _analyze_anomalies(client, data)

    print("  [4/4] Mapping technical debt...")
    tech_debt_analysis = _analyze_tech_debt(client, data)

    return AnalysisResult(
        business_evolution=business_evolution,
        module_stories=module_stories,
        anomaly_interpretations=anomaly_interpretations,
        tech_debt_analysis=tech_debt_analysis,
    )


def _call_claude(client: OpenAI, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


def _format_commit_list(commits: list[CommitInfo], limit: int = 300) -> str:
    lines = []
    for c in commits[:limit]:
        date_str = c.timestamp.strftime("%Y-%m-%d %H:%M")
        first_line = c.message.split("\n")[0][:120]
        lines.append(
            f"[{date_str}] {c.short_hash} | {c.author} | +{c.insertions}/-{c.deletions} | {first_line}"
        )
    return "\n".join(lines)


def _analyze_business_evolution(client: OpenAI, data: RepoData) -> str:
    system = """你是一名"代码考古学家"——像侦探勘察案发现场一样解读 git 历史。
你的任务：从提交历史中重建隐藏的业务演进故事。

规则：
- 推断决策背后的"为什么"，而不只是描述"做了什么"
- 识别规律：爆发式活跃（上线/危机）、平静期（维护）、大规模重构（还技术债）
- 给每个阶段命名，例如："创业期（2018-2019）"、"扩张危机（2020 年 Q3）"
- 用生动的叙事散文写作——读起来要像历史书，不是 changelog
- 【重要】无论提交信息是什么语言，报告必须全程用中文输出
- 用具体日期和提交数量作为证据支撑论点"""

    yearly = "\n".join(
        f"  {year}: {count} commits" for year, count in data.yearly_commit_counts.items()
    )

    commit_sample = _format_commit_list(data.sampled_commits)

    user = f"""Analyze this repository's business evolution:

**Repository**: {data.repo_name}
**Total commits**: {data.total_commits}
**Date range**: {data.date_range[0].strftime('%Y-%m-%d')} → {data.date_range[1].strftime('%Y-%m-%d')}

**Yearly commit activity**:
{yearly}

**Commit sample (time-balanced)**:
{commit_sample}

用中文写出项目生命周期的生动叙述：
1. 识别不同阶段（创业期 / 成长期 / 危机期 / 成熟期 / 衰退期等）
2. 每个阶段：团队在构建什么？面临什么压力？
3. 项目历史中最关键的 3-5 个转折点是什么？
4. 提交节奏揭示了怎样的团队文化？"""

    return _call_claude(client, system, user)


def _analyze_module_stories(client: OpenAI, data: RepoData) -> str:
    system = """你是一名专注于模块级取证的代码考古学家。
对每个文件/模块，讲述它的"生命故事"：诞生、挣扎、演变和当前状态。
重点关注该模块为何以这种方式演进——是什么业务需求推动了每一波变化？
【重要】无论提交信息是什么语言，输出必须全程用中文。"""

    hotspot_lines = []
    for h in data.hotspots[:15]:
        first = h.first_seen.strftime("%Y-%m-%d") if h.first_seen else "unknown"
        last = h.last_seen.strftime("%Y-%m-%d") if h.last_seen else "unknown"
        authors = ", ".join(h.top_authors[:3])
        hotspot_lines.append(
            f"- {h.path} | {h.change_count} changes | first: {first} | last: {last} | authors: {authors}"
        )

    directory_lines = []
    for directory, count in list(data.directory_activity.items())[:20]:
        directory_lines.append(f"  {directory}: {count} file-changes")

    user = f"""Repository: {data.repo_name}

**Most frequently changed files (hotspots)**:
{chr(10).join(hotspot_lines)}

**Directory activity map**:
{chr(10).join(directory_lines)}

对 Top 8 热点文件，用中文各写一张"模块历史卡片"：
- 它何时诞生，为什么诞生？
- 经历了哪些重大变化？
- 是"神圣之牛"（频繁修改但从不重构）还是"僵尸"（已废弃但仍在运行）？
- 作者模式说明了什么？（单一所有者 = 知识孤岛？多人争抢 = 高风险地带？）
- 当前评估：稳定基础、活跃开发，还是定时炸弹？"""

    return _call_claude(client, system, user)


def _analyze_anomalies(client: OpenAI, data: RepoData) -> str:
    system = """你是一名从 git 历史字里行间读取信息的代码考古学家。
异常提交是最具揭示性的文物——它们记录了危机、恐慌和艰难决策的瞬间。
对每个异常提交群，还原"事件经过"：可能发生了什么、为什么、它揭示了系统的哪些问题。
【重要】无论提交信息是什么语言，输出必须全程用中文。"""

    if not data.anomalies:
        return "No significant anomalies detected in the commit history."

    anomaly_lines = []
    for c in data.anomalies[:50]:
        date_str = c.timestamp.strftime("%Y-%m-%d %H:%M")
        first_line = c.message.split("\n")[0][:150]
        reasons = "; ".join(c.anomaly_reasons)
        anomaly_lines.append(
            f"[{date_str}] {c.short_hash} | {c.author}\n"
            f"  Message: {first_line}\n"
            f"  Flags: {reasons}\n"
            f"  Scale: +{c.insertions}/-{c.deletions} lines in {len(c.files_changed)} files"
        )

    user = f"""Repository: {data.repo_name}
Total anomalies detected: {len(data.anomalies)} / {data.total_commits} commits

**Anomalous commits**:
{chr(10).join(anomaly_lines)}

对每个异常提交（或一组相关异常），用中文分析：
1. 是什么事件可能触发了这次提交？（生产故障？安全漏洞？deadline 压力？）
2. 时间点说明了什么？（深夜 = 小团队高压状态，工作时间 = 有计划但有风险）
3. 变更规模揭示了什么？（大规模回滚 = 上游出了严重问题）
4. 这些异常揭示了代码库健康状况的哪些系统性规律？

最后用中文总结："最具揭示性的 Top 3 异常事件，以及它们对理解这个项目历史的意义。"
"""

    return _call_claude(client, system, user)


def _analyze_tech_debt(client: OpenAI, data: RepoData) -> str:
    system = """你是一名绘制遗留代码库"技术债地图"的代码考古学家。
TODO/FIXME/HACK 注释是时间胶囊——它们记录了开发者发现问题却无法修复的那个瞬间。
你的任务：解读当时受到了什么约束、为什么留下这些债务。
【重要】无论提交信息是什么语言，输出必须全程用中文。"""

    if not data.tech_debt_items:
        return "No TODO/FIXME/HACK markers found in the codebase."

    debt_lines = []
    for item in data.tech_debt_items[:40]:
        debt_lines.append(f"[{item.debt_type}] {item.file_path}\n  → {item.context}")

    contributor_lines = []
    for c in data.contributors[:10]:
        status = "⚠️ INACTIVE" if c.is_likely_inactive else "✓ active"
        last = c.last_commit.strftime("%Y-%m-%d") if c.last_commit else "unknown"
        modules = ", ".join(c.primary_modules[:3])
        contributor_lines.append(
            f"  {c.name} ({status}) | {c.commit_count} commits | last: {last} | domains: {modules}"
        )

    user = f"""Repository: {data.repo_name}

**Technical debt markers**:
{chr(10).join(debt_lines)}

**Contributor knowledge map**:
{chr(10).join(contributor_lines)}

用中文分析以下内容：
1. **债务聚类**：按主题分组 TODO/FIXME——哪些类型的问题被系统性地推迟了？
2. **历史约束**：哪些债务项暗示了外部约束？（旧 API？数据库限制？浏览器兼容？）
3. **知识孤岛**：根据贡献者模式，谁"拥有"哪些模块？他们离职后会发生什么？
4. **"禁区"**：哪些文件/模块看似被冻结——被大量依赖却从不修改？为什么？
5. **风险评估**：列出最危险的 Top 5 债务项，并解释为什么它们是定时炸弹。

最后用中文给出："写给下一个接手这个代码库的工程师的建议。"
"""

    return _call_claude(client, system, user)
