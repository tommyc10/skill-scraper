"""
Scrape skills from skills.sh leaderboards and clone each skill's folder from GitHub.

Usage:
    # Set a GitHub token (optional but strongly recommended - raises rate limit from 60/hr to 5000/hr)
    export GITHUB_TOKEN=ghp_...

    # Scrape the top 50 from /hot
    python scrape_skills.py --leaderboard hot --limit 50

    # Scrape everything from multiple leaderboards
    python scrape_skills.py --leaderboard hot trending --limit 200

    # Dry run (just print what it would download)
    python scrape_skills.py --leaderboard hot --limit 10 --dry-run
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

SKILLS_SH = "https://skills.sh"
GITHUB_API = "https://api.github.com"
OUTPUT_DIR = Path("skills")

# Match href="/owner/repo/skill-name" links in skills.sh HTML
LINK_RE = re.compile(r'href="/([^/\s"]+)/([^/\s"]+)/([^/\s"]+)"')


def get_headers() -> dict[str, str]:
    """Build GitHub API headers. Token is optional but recommended."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "skills-scraper",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_leaderboard(client: httpx.Client, name: str) -> str:
    """Fetch a skills.sh leaderboard page (hot, trending, or root for all-time)."""
    url = f"{SKILLS_SH}/{name}" if name != "all" else SKILLS_SH
    print(f"Fetching leaderboard: {url}")
    r = client.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def parse_skills(html: str) -> list[tuple[str, str, str]]:
    """Pull (owner, repo, skill-name) triples out of the leaderboard HTML, preserving order."""
    seen = set()
    out: list[tuple[str, str, str]] = []
    for owner, repo, skill in LINK_RE.findall(html):
        # Skip non-skill links (docs, agents, etc.) - these all appear in /hot markup too
        if owner in {"docs", "trending", "hot", "agents"}:
            continue
        key = (owner, repo, skill)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def find_skill_folder(
    client: httpx.Client, owner: str, repo: str, skill: str
) -> str | None:
    """
    Find the folder inside the repo that holds SKILL.md for this skill.

    Some repos put skills at the root (e.g. owner/single-skill-repo/SKILL.md).
    Others nest them (e.g. anthropics/skills/frontend-design/SKILL.md).
    We check the obvious paths first, then fall back to the code-search API.
    """
    # Try common paths first — much faster than search
    candidates = [
        skill,                          # anthropics/skills/frontend-design
        f"skills/{skill}",              # some repos nest under /skills
        "",                             # single-skill repo, SKILL.md at root
    ]
    for path in candidates:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}".rstrip("/")
        r = client.get(url, headers=get_headers(), timeout=30)
        if r.status_code != 200:
            continue
        items = r.json()
        if not isinstance(items, list):
            continue
        if any(
            it.get("type") == "file" and it.get("name", "").upper() == "SKILL.md".upper()
            for it in items
        ):
            return path

    # Try listing skills/ and finding a subfolder whose name is a substring of
    # the skill slug or vice versa (e.g. slug "vercel-react-best-practices" → folder "react-best-practices")
    for prefix in ["skills", ""]:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{prefix}".rstrip("/")
        r = client.get(url, headers=get_headers(), timeout=30)
        if r.status_code != 200:
            continue
        items = r.json()
        if not isinstance(items, list):
            continue
        for item in items:
            if item.get("type") != "dir":
                continue
            folder_name = item["name"].lower()
            if folder_name in skill.lower() or skill.lower() in folder_name:
                candidate = f"{prefix}/{item['name']}".lstrip("/")
                # Verify SKILL.md is actually in this folder
                check = client.get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/contents/{candidate}",
                    headers=get_headers(), timeout=30
                )
                if check.status_code == 200:
                    sub = check.json()
                    if isinstance(sub, list) and any(
                        s.get("type") == "file" and s.get("name", "").upper() == "SKILL.MD"
                        for s in sub
                    ):
                        return candidate

    # Fallback: use GitHub code search to locate SKILL.md in this repo
    # (slower and rate-limited separately, but catches weird layouts)
    query = f"filename:SKILL.md repo:{owner}/{repo}"
    search_url = f"{GITHUB_API}/search/code?q={quote(query)}"
    r = client.get(search_url, headers=get_headers(), timeout=30)
    if r.status_code == 200:
        for item in r.json().get("items", []):
            path = item.get("path", "")
            folder = "/".join(path.split("/")[:-1])
            folder_name = folder.split("/")[-1].lower() if folder else ""
            if (skill.lower() in folder.lower() or folder_name in skill.lower()):
                return folder
    return None


def download_folder(
    client: httpx.Client,
    owner: str,
    repo: str,
    path: str,
    dest: Path,
) -> int:
    """Recursively download a folder from GitHub into dest. Returns file count."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}".rstrip("/")
    r = client.get(url, headers=get_headers(), timeout=30)
    r.raise_for_status()
    items = r.json()
    if not isinstance(items, list):
        # Single file at this path — rare for skills but handle it
        items = [items]

    count = 0
    for item in items:
        itype = item.get("type")
        name = item["name"]
        sub_dest = dest / name
        if itype == "dir":
            sub_dest.mkdir(parents=True, exist_ok=True)
            count += download_folder(client, owner, repo, item["path"], sub_dest)
        elif itype == "file":
            download_url = item.get("download_url")
            if not download_url:
                continue
            fr = client.get(download_url, timeout=30)
            if fr.status_code == 200:
                sub_dest.parent.mkdir(parents=True, exist_ok=True)
                sub_dest.write_bytes(fr.content)
                count += 1
    return count


def check_rate_limit(client: httpx.Client) -> None:
    """Print current GitHub API rate limit status."""
    r = client.get(f"{GITHUB_API}/rate_limit", headers=get_headers(), timeout=10)
    if r.status_code == 200:
        core = r.json()["resources"]["core"]
        print(f"GitHub rate limit: {core['remaining']}/{core['limit']} remaining")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--leaderboard",
        nargs="+",
        default=["all"],
        choices=["hot", "trending", "all"],
        help="Which leaderboard(s) to scrape (default: all-time main page)",
    )
    parser.add_argument("--limit", type=int, default=50, help="Max skills to download")
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N skills (for paging, e.g. --offset 50 --limit 50 gets ranks 51-100)")
    parser.add_argument("--output", default="skills", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="List but don't download")
    parser.add_argument("--sleep", type=float, default=0.1, help="Seconds between API calls")
    args = parser.parse_args()

    global OUTPUT_DIR
    OUTPUT_DIR = Path(args.output)

    if not os.getenv("GITHUB_TOKEN"):
        print("WARNING: no GITHUB_TOKEN set. Unauthenticated API is capped at 60 req/hr.")
        print("         Create one at https://github.com/settings/tokens (no scopes needed for public repos).")
        print()

    with httpx.Client(follow_redirects=True) as client:
        if not args.dry_run:
            check_rate_limit(client)

        # Collect skills from each requested leaderboard
        all_skills: list[tuple[str, str, str]] = []
        seen = set()
        for lb in args.leaderboard:
            html = fetch_leaderboard(client, lb)
            for triple in parse_skills(html):
                if triple not in seen:
                    seen.add(triple)
                    all_skills.append(triple)

        skills = all_skills[args.offset : args.offset + args.limit]
        start, end = args.offset + 1, args.offset + len(skills)
        print(f"\nFound {len(all_skills)} unique skills; processing ranks {start}-{end}\n")

        if args.dry_run:
            for owner, repo, skill in skills:
                print(f"  {owner}/{repo}/{skill}")
            return 0

        OUTPUT_DIR.mkdir(exist_ok=True)
        successes = 0
        failures: list[tuple[str, str, str, str]] = []

        # Detect duplicate skill slugs across different repos so we can disambiguate
        slug_counts: dict[str, int] = {}
        for _, _, s in skills:
            slug_counts[s] = slug_counts.get(s, 0) + 1

        for i, (owner, repo, skill) in enumerate(skills, 1):
            # Use the skill slug as the folder name (matches skills.sh display).
            # If two repos share a slug, disambiguate by appending the owner.
            dest_name = skill if slug_counts[skill] == 1 else f"{skill}-{owner}"
            dest = OUTPUT_DIR / dest_name
            if dest.exists() and any(dest.iterdir()):
                print(f"[{i}/{len(skills)}] SKIP (exists): {dest_name}")
                successes += 1
                continue

            try:
                print(f"[{i}/{len(skills)}] {owner}/{repo}/{skill}", end=" ", flush=True)
                folder = find_skill_folder(client, owner, repo, skill)
                if folder is None:
                    print("-> NOT FOUND")
                    failures.append((owner, repo, skill, "SKILL.md folder not found"))
                    continue
                dest.mkdir(parents=True, exist_ok=True)
                n = download_folder(client, owner, repo, folder, dest)
                print(f"-> {n} files")
                successes += 1
                time.sleep(args.sleep)
            except httpx.HTTPStatusError as e:
                print(f"-> HTTP {e.response.status_code}")
                failures.append((owner, repo, skill, f"HTTP {e.response.status_code}"))
                # If we hit rate limit, stop early — no point in continuing
                if e.response.status_code == 403:
                    print("\nRate limit hit. Stopping. Set GITHUB_TOKEN and re-run to resume.")
                    break
            except Exception as e:
                print(f"-> ERROR: {e}")
                failures.append((owner, repo, skill, str(e)))

        # Summary
        print(f"\n{'=' * 60}")
        print(f"Done. {successes}/{len(skills)} skills downloaded to {OUTPUT_DIR}/")
        if failures:
            print(f"\n{len(failures)} failures:")
            for owner, repo, skill, err in failures:
                print(f"  {owner}/{repo}/{skill}: {err}")

        # Write a manifest so you can see what you got
        manifest = OUTPUT_DIR / "MANIFEST.md"
        with manifest.open("w") as f:
            f.write("# Skills Manifest\n\n")
            f.write(f"Scraped from: {', '.join(args.leaderboard)}\n\n")
            for owner, repo, skill in skills:
                dest_name = skill if slug_counts[skill] == 1 else f"{skill}-{owner}"
                if (OUTPUT_DIR / dest_name).exists():
                    f.write(f"- [`{skill}`](./{dest_name}/) — `{owner}/{repo}`\n")
        print(f"Manifest: {manifest}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
