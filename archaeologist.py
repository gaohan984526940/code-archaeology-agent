"""Code Archaeologist — CLI entry point."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()

from git_extractor import extract_repo_data
from analyzer import analyze_repo
from report_generator import generate_report


@click.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--output", "-o", default=".", help="Output directory for the report (default: current dir)")
@click.option("--depth", "-d", default=2000, help="Max number of commits to analyze (default: 2000)")
def main(repo_path: str, output: str, depth: int) -> None:
    """Code Archaeologist — reconstruct the history hidden in git commits.

    REPO_PATH: local path to the git repository to analyze
    """
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"\n[Code Archaeologist]")
    click.echo(f"   Repository : {repo_path}")
    click.echo(f"   Depth      : {depth} commits max")
    click.echo(f"   Output dir : {output_path.resolve()}\n")

    t0 = time.time()

    click.echo("Phase 1/3: Extracting git history...")
    data = extract_repo_data(repo_path, max_commits=depth)
    click.echo(f"   OK {data.total_commits} commits | {len(data.contributors)} contributors | {len(data.anomalies)} anomalies")

    click.echo("\nPhase 2/3: LLM archaeology inference...")
    result = analyze_repo(data)
    click.echo("   OK 4 analysis tasks complete")

    click.echo("\nPhase 3/3: Generating Markdown report...")
    report_file = generate_report(data, result, output_dir=str(output_path))

    elapsed = time.time() - t0
    click.echo(f"\nDone in {elapsed:.1f}s")
    click.echo(f"   Report saved to: {report_file}\n")


if __name__ == "__main__":
    main()
