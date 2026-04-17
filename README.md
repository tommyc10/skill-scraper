# skills-scraper

Bulk-download agent skills from [skills.sh](https://skills.sh) into a local repo.

Each skill on skills.sh maps to a folder in a public GitHub repo (e.g. `anthropics/skills/frontend-design/` → `https://github.com/anthropics/skills/tree/main/frontend-design`). This script:

1. Parses the skills.sh leaderboard page(s) to get `owner/repo/skill-name` triples
2. Uses the GitHub API to find each skill's folder
3. Downloads every file in that folder (SKILL.md + any scripts, templates, etc.)

Output layout (flat, one folder per skill):

```
skills/
  anthropics__skills__frontend-design/
    SKILL.md
    ...
  vercel-labs__agent-skills__vercel-react-best-practices/
    SKILL.md
    ...
  MANIFEST.md
```

## Setup

```bash
pip install httpx

# Strongly recommended — raises GitHub rate limit from 60/hr to 5000/hr
export GITHUB_TOKEN= # create at https://github.com/settings/tokens (no scopes needed)
```

## Usage

```bash
# Top 50 hot skills
python scrape_skills.py --leaderboard hot --limit 50

# Top 200 across hot + trending, merged and deduped
python scrape_skills.py --leaderboard hot trending --limit 200

# See what would be downloaded without actually downloading
python scrape_skills.py --leaderboard hot --limit 20 --dry-run

# Custom output directory
python scrape_skills.py --leaderboard hot --output my-skills
```

Re-running is safe — existing skill folders are skipped, so you can resume if you hit a rate limit.

## Notes on the approach

- **Why GitHub API, not HTML scraping of skills.sh?** The leaderboard page only gives us the skill identifiers, not the content. Content lives on GitHub. Using the GitHub API means we get clean JSON, proper binary handling for any non-text files, and decent rate limits with a token.
- **Why no `git clone`?** Most of these skills live inside large repos (e.g. `anthropics/skills` has dozens of skills). Cloning the whole repo just to grab one folder wastes bandwidth. The API lets us pull only the folder we want.
- **Folder-finding fallback.** Most repos follow the pattern `repo-root/{skill-name}/SKILL.md`, but some nest under `/skills/` or put a single skill at the repo root. The script checks those common paths first, then falls back to GitHub code search for weird layouts.

## Known limitations

- Code search (the fallback) is rate-limited separately at 30 req/min even with a token. If you're scraping a lot of weirdly-structured repos, you may need to add longer sleeps.
- Private repos won't work with a token that lacks access — all the popular skills appear to be public though.
- The leaderboard only shows the top 200 entries per view. To get more, you'd need to scrape skills.sh's paginated or search endpoints (not currently implemented here).
