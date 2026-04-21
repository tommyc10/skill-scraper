# skill-cli

`skill-cli` is an interactive command line tool for finding and installing agent skills from [skills.sh](https://skills.sh) into your project.

The flow is intentionally simple:

1. Launch the CLI inside your project.
2. Describe the project in plain English.
3. GPT-5.4 on Foundry reads the bundled [SKILL.md](./src/skill_cli/skill-finder/SKILL.md).
4. The model searches `skills.sh` for the best matches.
5. The CLI shows recommended skills with short reasons.
6. You approve the install.
7. The tool creates `./skills/` in the current workspace and downloads the selected skills there.

## Setup

Python 3.11+ is required.

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows PowerShell

# 2. Install the CLI (editable mode so edits take effect immediately)
pip install -e .

# 3. Set Foundry credentials
export FOUNDRY_API_KEY="your-key-here"
export FOUNDRY_ENDPOINT="https://your-foundry-endpoint/v1"

# 4. (Optional) GitHub token so the install step isn't rate-limited
export GITHUB_TOKEN="ghp_..."
```

To make the env vars permanent, add the `export` lines to `~/.zshrc` (macOS) or `$PROFILE` (Windows PowerShell).

## Usage

Interactive mode:

```bash
skill-cli
# or: python -m skill_cli
```

One-shot mode:

```bash
skill-cli "I'm building a React frontend with Azure. Keep the code simple and follow good habits."
```

Example output:

```text
$ skill-cli
Describe your project and the kinds of skills you want.
> I'm building a React frontend with Azure. Keep the code simple and follow good habits.

Recommended skills:
1. vercel-react-best-practices (vercel-labs/agent-skills)
   Matches the React frontend requirement and focuses on maintainable patterns.
   https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices
2. azure-ai (microsoft/github-copilot-for-azure)
   Covers Azure-specific project needs mentioned in the request.
   https://skills.sh/microsoft/github-copilot-for-azure/azure-ai

Install these into ./skills? (y/n)
```

Useful flags:

```bash
skill-cli --top-k 3
skill-cli --skills-dir .ai/skills
skill-cli --project-dir /path/to/project
skill-cli --yes "Find skills for a Next.js app with testing and clean code"
skill-cli --model gpt-5.4
```

## What gets written

After approval, the CLI writes:

- `./skills/<skill-name>/...` with the downloaded skill files
- `./skills/manifest.json` with the installed skill metadata

Because the folder lives in the workspace, VS Code can see it immediately.

## Project structure

- [`src/skill_cli/cli.py`](./src/skill_cli/cli.py) runs the interactive CLI flow
- [`src/skill_cli/skill-finder/SKILL.md`](./src/skill_cli/skill-finder/SKILL.md) is the bundled instruction file given to the model
- [`src/skill_cli/recommender.py`](./src/skill_cli/recommender.py) asks the model to search skills.sh
- [`src/skill_cli/github_install.py`](./src/skill_cli/github_install.py) downloads the selected skill folders from GitHub
- [`src/skill_cli/banner.py`](./src/skill_cli/banner.py) prints the launch banner

## Legacy scraper

The original bulk scraper still exists as [`scrape_skills.py`](./scrape_skills.py) if you want to download many skills directly from leaderboard pages.
