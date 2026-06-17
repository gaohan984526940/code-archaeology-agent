"""Git history data extraction layer."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from git import Repo
from git.exc import InvalidGitRepositoryError


ANOMALY_KEYWORDS = re.compile(
    r"\b(revert|hotfix|emergency|urgent|critical|fix!|bug|crash|broken|hack|workaround|temporary|temp)\b",
    re.IGNORECASE,
)

TECHNICAL_DEBT_PATTERN = re.compile(
    r"(TODO|FIXME|HACK|XXX|NOCOMMIT|TEMP|WORKAROUND)[:\s](.{0,200})",
    re.IGNORECASE,
)


@dataclass
class CommitInfo:
    hash: str
    short_hash: str
    author: str
    email: str
    timestamp: datetime
    message: str
    files_changed: list[str]
    insertions: int
    deletions: int
    is_anomaly: bool
    anomaly_reasons: list[str]


@dataclass
class FileHotspot:
    path: str
    change_count: int
    first_seen: datetime
    last_seen: datetime
    top_authors: list[str]
    directory: str


@dataclass
class ContributorInfo:
    name: str
    email: str
    commit_count: int
    first_commit: datetime
    last_commit: datetime
    primary_modules: list[str]
    is_likely_inactive: bool


@dataclass
class TechDebtItem:
    file_path: str
    line_content: str
    debt_type: str
    context: str


@dataclass
class RepoData:
    repo_name: str
    repo_path: str
    total_commits: int
    date_range: tuple[datetime, datetime]
    commits: list[CommitInfo]
    hotspots: list[FileHotspot]
    contributors: list[ContributorInfo]
    anomalies: list[CommitInfo]
    tech_debt_items: list[TechDebtItem]
    directory_activity: dict[str, int]
    yearly_commit_counts: dict[int, int]
    sampled_commits: list[CommitInfo] = field(default_factory=list)


def extract_repo_data(repo_path: str, max_commits: int = 2000) -> RepoData:
    try:
        repo = Repo(repo_path, search_parent_directories=True)
    except InvalidGitRepositoryError as e:
        raise ValueError(f"Not a valid git repository: {repo_path}") from e

    repo_name = Path(repo_path).name
    print(f"  Scanning repository: {repo_name}")

    commits = _extract_commits(repo, max_commits)
    print(f"  Extracted {len(commits)} commits")

    hotspots = _build_file_hotspots(commits)
    contributors = _build_contributors(commits, hotspots)
    anomalies = [c for c in commits if c.is_anomaly]
    tech_debt = _scan_tech_debt(repo_path)
    directory_activity = _compute_directory_activity(commits)
    yearly_counts = _compute_yearly_counts(commits)

    date_range = (
        commits[-1].timestamp if commits else datetime.now(timezone.utc),
        commits[0].timestamp if commits else datetime.now(timezone.utc),
    )

    sampled = _sample_commits(commits)

    return RepoData(
        repo_name=repo_name,
        repo_path=repo_path,
        total_commits=len(commits),
        date_range=date_range,
        commits=commits,
        hotspots=hotspots[:20],
        contributors=contributors,
        anomalies=anomalies,
        tech_debt_items=tech_debt[:50],
        directory_activity=directory_activity,
        yearly_commit_counts=yearly_counts,
        sampled_commits=sampled,
    )


def _extract_commits(repo: Repo, max_commits: int) -> list[CommitInfo]:
    commits = []
    prev_commit_time: datetime | None = None

    for commit in repo.iter_commits(max_count=max_commits):
        ts = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)
        hour = ts.hour

        files_changed = list(commit.stats.files.keys()) if commit.stats else []
        insertions = commit.stats.total.get("insertions", 0) if commit.stats else 0
        deletions = commit.stats.total.get("deletions", 0) if commit.stats else 0
        total_lines = insertions + deletions

        anomaly_reasons = []
        if hour >= 22 or hour < 6:
            anomaly_reasons.append(f"deep-night commit ({hour:02d}:xx)")
        if total_lines > 500:
            anomaly_reasons.append(f"massive change ({total_lines} lines)")
        if ANOMALY_KEYWORDS.search(commit.message):
            matched = ANOMALY_KEYWORDS.findall(commit.message)
            anomaly_reasons.append(f"emergency keywords: {', '.join(set(matched))}")
        if prev_commit_time and (prev_commit_time - ts).total_seconds() < 600:
            anomaly_reasons.append("rapid successive commit (<10 min)")

        info = CommitInfo(
            hash=commit.hexsha,
            short_hash=commit.hexsha[:8],
            author=commit.author.name,
            email=commit.author.email,
            timestamp=ts,
            message=commit.message.strip(),
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            is_anomaly=bool(anomaly_reasons),
            anomaly_reasons=anomaly_reasons,
        )
        commits.append(info)
        prev_commit_time = ts

    return commits


def _build_file_hotspots(commits: list[CommitInfo]) -> list[FileHotspot]:
    file_data: dict[str, dict] = defaultdict(lambda: {
        "count": 0,
        "first": None,
        "last": None,
        "authors": defaultdict(int),
    })

    for commit in commits:
        for f in commit.files_changed:
            d = file_data[f]
            d["count"] += 1
            if d["first"] is None or commit.timestamp < d["first"]:
                d["first"] = commit.timestamp
            if d["last"] is None or commit.timestamp > d["last"]:
                d["last"] = commit.timestamp
            d["authors"][commit.author] += 1

    hotspots = []
    for path, d in file_data.items():
        top_authors = sorted(d["authors"], key=lambda a: d["authors"][a], reverse=True)[:3]
        directory = str(Path(path).parent) if "/" in path or "\\" in path else "."
        hotspots.append(FileHotspot(
            path=path,
            change_count=d["count"],
            first_seen=d["first"],
            last_seen=d["last"],
            top_authors=top_authors,
            directory=directory,
        ))

    return sorted(hotspots, key=lambda h: h.change_count, reverse=True)


def _build_contributors(
    commits: list[CommitInfo], hotspots: list[FileHotspot]
) -> list[ContributorInfo]:
    contributor_data: dict[str, dict] = defaultdict(lambda: {
        "email": "",
        "count": 0,
        "first": None,
        "last": None,
        "files": defaultdict(int),
    })

    for commit in commits:
        d = contributor_data[commit.author]
        d["email"] = commit.email
        d["count"] += 1
        if d["first"] is None or commit.timestamp < d["first"]:
            d["first"] = commit.timestamp
        if d["last"] is None or commit.timestamp > d["last"]:
            d["last"] = commit.timestamp
        for f in commit.files_changed:
            directory = str(Path(f).parent) if "/" in f or "\\" in f else "."
            d["files"][directory] += 1

    now = datetime.now(timezone.utc)
    result = []
    for name, d in contributor_data.items():
        top_modules = sorted(d["files"], key=lambda m: d["files"][m], reverse=True)[:5]
        days_since_last = (now - d["last"]).days if d["last"] else 9999
        result.append(ContributorInfo(
            name=name,
            email=d["email"],
            commit_count=d["count"],
            first_commit=d["first"],
            last_commit=d["last"],
            primary_modules=top_modules,
            is_likely_inactive=days_since_last > 365,
        ))

    return sorted(result, key=lambda c: c.commit_count, reverse=True)


def _scan_tech_debt(repo_path: str) -> list[TechDebtItem]:
    items = []
    extensions = {".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cs", ".cpp", ".c"}

    for file_path in Path(repo_path).rglob("*"):
        if file_path.suffix not in extensions:
            continue
        if any(part.startswith(".") for part in file_path.parts):
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for match in TECHNICAL_DEBT_PATTERN.finditer(text):
                items.append(TechDebtItem(
                    file_path=str(file_path.relative_to(repo_path)),
                    line_content=match.group(0).strip(),
                    debt_type=match.group(1).upper(),
                    context=match.group(2).strip(),
                ))
        except (OSError, PermissionError):
            continue

    return items


def _compute_directory_activity(commits: list[CommitInfo]) -> dict[str, int]:
    activity: dict[str, int] = defaultdict(int)
    for commit in commits:
        for f in commit.files_changed:
            directory = str(Path(f).parent) if "/" in f or "\\" in f else "."
            activity[directory] += 1
    return dict(sorted(activity.items(), key=lambda x: x[1], reverse=True))


def _compute_yearly_counts(commits: list[CommitInfo]) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for commit in commits:
        counts[commit.timestamp.year] += 1
    return dict(sorted(counts.items()))


def _sample_commits(commits: list[CommitInfo], target: int = 400) -> list[CommitInfo]:
    """Return a time-balanced sample of commits for LLM context."""
    if len(commits) <= target:
        return commits

    head = commits[:100]
    tail = commits[-100:]
    middle = commits[100:-100]

    if not middle:
        return commits[:target]

    step = max(1, len(middle) // (target - 200))
    sampled_middle = middle[::step][: target - 200]

    seen = set()
    result = []
    for c in head + sampled_middle + tail:
        if c.hash not in seen:
            seen.add(c.hash)
            result.append(c)

    return sorted(result, key=lambda c: c.timestamp, reverse=True)
