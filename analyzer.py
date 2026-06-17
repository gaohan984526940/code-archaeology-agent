"""LLM archaeology inference layer using Claude API."""

from __future__ import annotations

import os
from dataclasses import dataclass

import anthropic

from git_extractor import RepoData, CommitInfo


MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


@dataclass
class AnalysisResult:
    business_evolution: str
    module_stories: str
    anomaly_interpretations: str
    tech_debt_analysis: str


def analyze_repo(data: RepoData) -> AnalysisResult:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

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


def _call_claude(client: anthropic.Anthropic, system: str, user: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def _format_commit_list(commits: list[CommitInfo], limit: int = 300) -> str:
    lines = []
    for c in commits[:limit]:
        date_str = c.timestamp.strftime("%Y-%m-%d %H:%M")
        first_line = c.message.split("\n")[0][:120]
        lines.append(
            f"[{date_str}] {c.short_hash} | {c.author} | +{c.insertions}/-{c.deletions} | {first_line}"
        )
    return "\n".join(lines)


def _analyze_business_evolution(client: anthropic.Anthropic, data: RepoData) -> str:
    system = """You are a "Code Archaeologist" — an expert at reading git history like a detective reading a crime scene.
Your task: reconstruct the BUSINESS and PRODUCT story hidden inside commit history.

Rules:
- Infer WHY decisions were made, not just WHAT changed
- Look for patterns: burst activity (launch/crisis), quiet periods (maintenance), massive refactors (debt payment)
- Name specific time periods: "The Bootstrap Era (2018-2019)", "The Scaling Crisis (Q3 2020)"
- Write in vivid, narrative prose — this should read like a history book, not a changelog
- Output in the SAME language as the commit messages (if Chinese commits → Chinese output, if English → English)
- Be specific about dates and commit counts as evidence"""

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

Produce a vivid narrative of the project's lifecycle:
1. Identify distinct phases (Bootstrap / Growth / Crisis / Maturity / Decline etc.)
2. For each phase: what was the team building? what pressures were they under?
3. What were the 3-5 most pivotal moments in the project's history?
4. What does the commit rhythm tell us about the team culture?"""

    return _call_claude(client, system, user)


def _analyze_module_stories(client: anthropic.Anthropic, data: RepoData) -> str:
    system = """You are a Code Archaeologist specializing in module-level forensics.
For each file/module, tell its LIFE STORY: birth, struggles, transformations, and current state.
Focus on WHY the module evolved the way it did — what business needs drove each wave of changes?
Output in the SAME language as the commit messages."""

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

For each of the top 8 hotspot files, write a "Module History Card":
- When was it born and why?
- What major transformations did it undergo?
- Is it a "sacred cow" (touched constantly, never refactored) or a "zombie" (abandoned but still running)?
- What does the author pattern tell us? (single owner = knowledge silo? many authors = contested ground?)
- Current assessment: stable foundation, active development, or ticking time bomb?"""

    return _call_claude(client, system, user)


def _analyze_anomalies(client: anthropic.Anthropic, data: RepoData) -> str:
    system = """You are a Code Archaeologist reading between the lines of git history.
Anomalous commits are the MOST revealing artifacts — they capture moments of crisis, panic, and hard decisions.
For each anomaly cluster, reconstruct the INCIDENT: what probably happened, why, and what it reveals about the system.
Output in the SAME language as the commit messages."""

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

For each anomaly (or cluster of related anomalies):
1. What INCIDENT likely triggered this? (production outage? security breach? deadline pressure?)
2. What does the timing tell us? (late-night = small team under pressure, business hours = planned but risky)
3. What does the scale of change reveal? (massive revert = something went badly wrong upstream)
4. What systemic pattern do these anomalies reveal about the codebase's health?

End with: "Top 3 most revealing anomaly incidents and what they tell us about this project's history."
"""

    return _call_claude(client, system, user)


def _analyze_tech_debt(client: anthropic.Anthropic, data: RepoData) -> str:
    system = """You are a Code Archaeologist mapping the "technical debt landscape" of a legacy codebase.
TODO/FIXME/HACK comments are time capsules — they capture the moment a developer knew something was wrong but couldn't fix it.
Your job: interpret WHAT they were constrained by and WHY they left the debt.
Output in the SAME language as the commit messages."""

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

Analyze:
1. **Debt Clusters**: Group the TODOs/FIXMEs by theme — what categories of problems were systematically deferred?
2. **Historical Constraints**: Which debt items hint at external constraints? (legacy API? database limitations? browser compat?)
3. **Knowledge Silos**: Based on contributor patterns, who "owns" which parts? What happens if they leave?
4. **The "Untouchable" Zones**: Which files/modules appear frozen in time — many reads, no changes? Why?
5. **Risk Assessment**: Rank the top 5 most dangerous debt items and explain why they're ticking time bombs.

End with: "Recommendations for the next engineer who inherits this codebase."
"""

    return _call_claude(client, system, user)
