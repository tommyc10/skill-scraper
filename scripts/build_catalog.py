"""
Build the skills catalog by scraping skills.sh leaderboards and fetching
SKILL.md descriptions from raw.githubusercontent.com (no auth needed).

Usage:
    python scripts/build_catalog.py
    python scripts/build_catalog.py --leaderboard hot trending --limit 100
    python scripts/build_catalog.py --dry-run

Output: src/skill_cli/data/skills_catalog.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

SKILLS_SH = "https://skills.sh"
RAW_BASE = "https://raw.githubusercontent.com"
OUTPUT = Path(__file__).parent.parent / "src" / "skill_cli" / "data" / "skills_catalog.json"

LINK_RE = re.compile(r'href="/([^/\s"]+)/([^/\s"]+)/([^/\s"]+)"')
SKIP_OWNERS = {"docs", "trending", "hot", "agents"}

# Common paths where SKILL.md might live in a repo
RAW_PATH_TEMPLATES = [
    "{skill}/SKILL.md",
    "skills/{skill}/SKILL.md",
    "SKILL.md",
]
BRANCHES = ["main", "master"]


def fetch_leaderboard(client: httpx.Client, name: str) -> str:
    url = f"{SKILLS_SH}/{name}" if name != "all" else SKILLS_SH
    print(f"  Fetching {url}")
    r = client.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def parse_skills(html: str) -> list[tuple[str, str, str]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[tuple[str, str, str]] = []
    for owner, repo, skill in LINK_RE.findall(html):
        if owner in SKIP_OWNERS:
            continue
        key = (owner, repo, skill)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def fetch_skill_md(client: httpx.Client, owner: str, repo: str, skill: str) -> str | None:
    for branch in BRANCHES:
        for template in RAW_PATH_TEMPLATES:
            path = template.format(skill=skill)
            url = f"{RAW_BASE}/{owner}/{repo}/{branch}/{path}"
            try:
                r = client.get(url, timeout=15)
                if r.status_code == 200 and r.text.strip():
                    return r.text
            except httpx.TimeoutException:
                continue
    return None


def parse_skill_md(content: str) -> tuple[str, str]:
    """Extract (title, description) from SKILL.md content."""
    lines = content.splitlines()

    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    description = ""
    in_para = False
    para_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_para:
                break
            continue
        if stripped.startswith("#") or stripped.startswith("```") or stripped.startswith("|"):
            if in_para:
                break
            continue
        in_para = True
        para_lines.append(stripped)

    description = " ".join(para_lines)[:400]
    return title, description


def build_catalog(
    leaderboards: list[str],
    limit: int,
    sleep: float,
    dry_run: bool,
) -> list[dict]:
    skills_map: dict[tuple[str, str, str], None] = {}

    with httpx.Client(follow_redirects=True) as client:
        print("Scraping leaderboards...")
        for lb in leaderboards:
            html = fetch_leaderboard(client, lb)
            for triple in parse_skills(html):
                skills_map[triple] = None

        all_skills = list(skills_map.keys())[:limit]
        print(f"Found {len(all_skills)} unique skills (capped at {limit})\n")

        if dry_run:
            for owner, repo, skill in all_skills:
                print(f"  {owner}/{repo}/{skill}")
            return []

        catalog: list[dict] = []
        for i, (owner, repo, skill) in enumerate(all_skills, 1):
            print(f"[{i}/{len(all_skills)}] {owner}/{repo}/{skill}", end=" ", flush=True)

            content = fetch_skill_md(client, owner, repo, skill)
            if content:
                title, description = parse_skill_md(content)
                print(f"-> ok ({len(description)} chars)")
            else:
                title = skill.replace("-", " ").title()
                description = ""
                print("-> no SKILL.md found")

            catalog.append(
                {
                    "owner": owner,
                    "repo": repo,
                    "skill_slug": skill,
                    "title": title or skill.replace("-", " ").title(),
                    "description": description,
                    "skill_url": f"https://skills.sh/{owner}/{repo}/{skill}",
                }
            )
            time.sleep(sleep)

    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--leaderboard",
        nargs="+",
        default=["all", "hot", "trending"],
        choices=["hot", "trending", "all"],
    )
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    catalog = build_catalog(
        leaderboards=args.leaderboard,
        limit=args.limit,
        sleep=args.sleep,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "count": len(catalog),
        "skills": catalog,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nWrote {len(catalog)} skills to {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
